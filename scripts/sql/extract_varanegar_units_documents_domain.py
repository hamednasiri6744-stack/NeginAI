"""Extract Varanegar unit, shipping, stock, and document-type evidence.

This third information-base slice keeps product units, packaging labels,
shipping classes, stock-operation encodings, inventory vouchers, sales order
types, and general-ledger voucher types as separate contracts.  It is pinned to
the local read-only clone through the safety gate shared by the first slice.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _decode_fields,
    _json_default,
    _rows,
    _table_metadata,
)


DOMAIN_TABLES: tuple[dict[str, str], ...] = (
    {"object": "GNR.tblUnit", "role": "legacy_goods_and_package_unit"},
    {"object": "dbo.MeasurementUnitType", "role": "physical_measurement_unit_type"},
    {"object": "dbo.GeneralUnitType", "role": "general_unit_type"},
    {"object": "GNR.tblShipType", "role": "shipping_temperature_class"},
    {"object": "GNR.tblLookup", "role": "inventory_voucher_and_stock_type_lookup"},
    {"object": "inv.tblVocherStockType", "role": "inventory_voucher_stock_channel_bridge"},
    {"object": "dbo.DocumentType", "role": "personnel_identity_attachment_type"},
    {"object": "dbo.VoucherType", "role": "general_ledger_voucher_type"},
    {"object": "dbo.ExternalVoucherType", "role": "source_to_general_ledger_voucher_mapping"},
    {"object": "Acc.ManualVoucherType", "role": "manual_accounting_voucher_type"},
    {"object": "SLE.tblOrderType", "role": "sales_order_type"},
    {"object": "dbo.POrderType", "role": "secondary_order_type"},
)

BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"


def _object_ids_sql() -> str:
    return ",".join(f"OBJECT_ID(N'{item['object']}', 'U')" for item in DOMAIN_TABLES)


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    object_ids = _object_ids_sql()
    return _rows(
        cursor,
        f"""
        SELECT fk.name AS constraint_name,
               OBJECT_SCHEMA_NAME(fk.parent_object_id) AS parent_schema,
               OBJECT_NAME(fk.parent_object_id) AS parent_table,
               pc.name AS parent_column,
               OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS referenced_schema,
               OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
               rc.name AS referenced_column,
               fk.delete_referential_action_desc AS on_delete,
               fk.update_referential_action_desc AS on_update,
               fk.is_disabled,fk.is_not_trusted
        FROM sys.foreign_keys AS fk
        JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.columns AS pc
          ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns AS rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE fk.parent_object_id IN ({object_ids})
           OR fk.referenced_object_id IN ({object_ids})
        ORDER BY referenced_schema,referenced_table,parent_schema,parent_table,
                 fk.name,fkc.constraint_column_id
        """,
    )


def _module_consumers(cursor: Any) -> list[dict[str, Any]]:
    object_ids = _object_ids_sql()
    return _rows(
        cursor,
        f"""
        SELECT DISTINCT
               OBJECT_SCHEMA_NAME(d.referencing_id) AS consumer_schema,
               OBJECT_NAME(d.referencing_id) AS consumer_name,
               o.type_desc AS consumer_type,
               OBJECT_SCHEMA_NAME(d.referenced_id) AS source_schema,
               OBJECT_NAME(d.referenced_id) AS source_table,
               d.is_schema_bound_reference,
               o.modify_date AS consumer_modify_date
        FROM sys.sql_expression_dependencies AS d
        JOIN sys.objects AS o ON o.object_id=d.referencing_id
        WHERE d.referenced_id IN ({object_ids})
        ORDER BY source_schema,source_table,consumer_schema,consumer_name
        """,
    )


def _implicit_link_candidates(cursor: Any) -> list[dict[str, Any]]:
    object_ids = _object_ids_sql()
    return _rows(
        cursor,
        f"""
        WITH candidates AS (
            SELECT c.object_id,c.column_id,s.name AS schema_name,t.name AS table_name,
                   c.name AS column_name,TYPE_NAME(c.user_type_id) AS data_type
            FROM sys.columns AS c
            JOIN sys.tables AS t ON t.object_id=c.object_id
            JOIN sys.schemas AS s ON s.schema_id=t.schema_id
            WHERE LOWER(c.name) LIKE '%unit%'
               OR LOWER(c.name) LIKE '%shiptype%'
               OR LOWER(c.name) LIKE '%stocktype%'
               OR LOWER(c.name) LIKE '%vouchertype%'
               OR LOWER(c.name) LIKE '%vochertype%'
               OR LOWER(c.name) LIKE '%ordertype%'
               OR LOWER(c.name) LIKE '%documenttype%'
        )
        SELECT cc.schema_name,cc.table_name,cc.column_name,cc.data_type,
               CASE WHEN fkc.constraint_object_id IS NULL THEN 0 ELSE 1 END AS has_formal_fk,
               OBJECT_SCHEMA_NAME(fkc.referenced_object_id) AS formal_target_schema,
               OBJECT_NAME(fkc.referenced_object_id) AS formal_target_table,
               rc.name AS formal_target_column
        FROM candidates AS cc
        LEFT JOIN sys.foreign_key_columns AS fkc
          ON fkc.parent_object_id=cc.object_id AND fkc.parent_column_id=cc.column_id
        LEFT JOIN sys.columns AS rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE cc.object_id NOT IN ({object_ids})
        ORDER BY has_formal_fk,cc.schema_name,cc.table_name,cc.column_name
        """,
    )


def _units_and_shipping(cursor: Any) -> dict[str, Any]:
    units = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,UnitCode,CONVERT(varbinary(max),UnitName) AS UnitName,
                   ModifiedDateBeforeSend,UniqueId
            FROM GNR.tblUnit ORDER BY ID
            """,
        ),
        ("UnitName",),
    )
    shipping_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,CONVERT(varbinary(max),ShipTypeName) AS ShipTypeName,Priority
            FROM GNR.tblShipType ORDER BY ID
            """,
        ),
        ("ShipTypeName",),
    )
    goods_unit_usage = _decode_fields(
        _rows(
            cursor,
            """
            SELECT 'UnitRef' AS reference_kind,g.UnitRef AS source_id,
                   CONVERT(varbinary(max),u.UnitName) AS source_title,
                   COUNT_BIG(*) AS goods_count
            FROM GNR.tblGoods AS g
            LEFT JOIN GNR.tblUnit AS u ON u.ID=g.UnitRef
            GROUP BY g.UnitRef,u.UnitName
            UNION ALL
            SELECT 'PackUnitRef',g.PackUnitRef,
                   CONVERT(varbinary(max),u.UnitName),COUNT_BIG(*)
            FROM GNR.tblGoods AS g
            LEFT JOIN GNR.tblUnit AS u ON u.ID=g.PackUnitRef
            GROUP BY g.PackUnitRef,u.UnitName
            ORDER BY reference_kind,goods_count DESC,source_id
            """,
        ),
        ("source_title",),
    )
    ship_usage = _decode_fields(
        _rows(
            cursor,
            """
            SELECT 'goods' AS consumer,g.ShipTypeRef AS ship_type_id,
                   CONVERT(varbinary(max),s.ShipTypeName) AS ship_type_name,
                   COUNT_BIG(*) AS row_count
            FROM GNR.tblGoods AS g
            LEFT JOIN GNR.tblShipType AS s ON s.ID=g.ShipTypeRef
            GROUP BY g.ShipTypeRef,s.ShipTypeName
            UNION ALL
            SELECT 'stock_center',d.ShipTypeRef,
                   CONVERT(varbinary(max),s.ShipTypeName),COUNT_BIG(*)
            FROM GNR.tblStockDC AS d
            LEFT JOIN GNR.tblShipType AS s ON s.ID=d.ShipTypeRef
            GROUP BY d.ShipTypeRef,s.ShipTypeName
            ORDER BY consumer,row_count DESC,ship_type_id
            """,
        ),
        ("ship_type_name",),
    )
    return {
        "legacy_units": units,
        "measurement_unit_types": _rows(
            cursor,
            "SELECT Id,MeasurementUnitName FROM dbo.MeasurementUnitType ORDER BY Id",
        ),
        "general_unit_types": _rows(
            cursor,
            "SELECT Id,GeneralUnitName FROM dbo.GeneralUnitType ORDER BY Id",
        ),
        "shipping_types": shipping_types,
        "goods_unit_usage": goods_unit_usage,
        "shipping_type_usage": ship_usage,
        "goods_unit_population": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_goods,
                   SUM(CASE WHEN UnitRef IS NOT NULL THEN 1 ELSE 0 END) AS unit_ref_populated,
                   SUM(CASE WHEN PackUnitRef IS NOT NULL THEN 1 ELSE 0 END) AS pack_unit_ref_populated,
                   SUM(CASE WHEN ShipTypeRef IS NOT NULL THEN 1 ELSE 0 END) AS ship_type_ref_populated,
                   SUM(CASE WHEN MeasurementUnit IS NOT NULL THEN 1 ELSE 0 END) AS measurement_unit_populated,
                   SUM(CASE WHEN GeneralUnit IS NOT NULL THEN 1 ELSE 0 END) AS general_unit_populated,
                   SUM(CASE WHEN sdpmsMeasurementUnit IS NOT NULL THEN 1 ELSE 0 END) AS sdpms_measurement_unit_populated
            FROM GNR.tblGoods
            """,
        )[0],
    }


def _stock_and_inventory_types(cursor: Any) -> dict[str, Any]:
    stock_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT CodeType,Code,CONVERT(varbinary(max),Title) AS Title,Value1
            FROM GNR.tblLookup WHERE CodeType=70 ORDER BY Code
            """,
        ),
        ("Title",),
    )
    voucher_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT CodeType,Code,CONVERT(varbinary(max),Title) AS Title,Value1 AS IsManual
            FROM GNR.tblLookup WHERE CodeType=14 ORDER BY Code
            """,
        ),
        ("Title",),
    )
    voucher_stock_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT m.ID,m.VocherTypeCode,
                   CONVERT(varbinary(max),v.Title) AS VocherTypeTitle,m.StockType,
                   CASE m.StockType
                     WHEN 1 THEN N'پیش ویزیت'
                     WHEN 2 THEN N'فروش گرم'
                     WHEN 4 THEN N'انبارک'
                     WHEN 8 THEN N'فروش فروشگاهی'
                     WHEN 16 THEN N'ایستگاه کاری'
                     ELSE N'ترکیبی یا ناشناخته'
                   END AS StockTypeBitTitle
            FROM inv.tblVocherStockType AS m
            LEFT JOIN GNR.tblLookup AS v
              ON v.CodeType=14 AND v.Code=m.VocherTypeCode
            ORDER BY m.VocherTypeCode,m.StockType,m.ID
            """,
        ),
        ("VocherTypeTitle",),
    )
    return {
        "stock_type_ordinal_lookup": stock_types,
        "stock_type_bit_contract": [
            {"bit": 1, "title": "پیش ویزیت"},
            {"bit": 2, "title": "فروش گرم"},
            {"bit": 4, "title": "انبارک"},
            {"bit": 8, "title": "فروش فروشگاهی"},
            {"bit": 16, "title": "ایستگاه کاری"},
        ],
        "inventory_voucher_types": voucher_types,
        "inventory_voucher_stock_type_links": voucher_stock_types,
        "stock_center_stock_type_usage": _rows(
            cursor,
            "SELECT StockType,COUNT_BIG(*) AS stock_center_count FROM GNR.tblStockDC GROUP BY StockType ORDER BY StockType",
        ),
    }


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    """Capture the SQL definitions that prove the two stock-type encodings."""
    return _rows(
        cursor,
        """
        SELECT s.name AS schema_name,o.name AS object_name,o.type_desc,
               m.definition,o.modify_date
        FROM sys.objects AS o
        JOIN sys.schemas AS s ON s.schema_id=o.schema_id
        LEFT JOIN sys.sql_modules AS m ON m.object_id=o.object_id
        WHERE (s.name='GNR' AND o.name IN (
                 'vwStockType','vwVocherType','vwVocherStockType','HasStockType'
              ))
           OR (s.name='FRU' AND o.name IN (
                 'StockTypeModel','ShipTypeModel','InvVocherTypeModel',
                 'VocherTypeModel','VoucherTypeModel'
              ))
        ORDER BY s.name,o.name
        """,
    )


def _document_types(cursor: Any) -> dict[str, Any]:
    order_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,CONVERT(varbinary(max),Title) AS Title,Selectable,IsDefault,
                   OrderTypeSerialType,SLId,IsFreeInvoice,DontCheckMojodi,
                   EffectOrderOnStockGoods,UniqueId
            FROM SLE.tblOrderType ORDER BY ID
            """,
        ),
        ("Title",),
    )
    return {
        "identity_attachment_types": _rows(
            cursor,
            "SELECT DocumentTypeId,DocumentTypeName FROM dbo.DocumentType ORDER BY DocumentTypeId",
        ),
        "sales_order_types": order_types,
        "secondary_order_types": _rows(
            cursor,
            "SELECT POrderTypeId,POrderTypeName FROM dbo.POrderType ORDER BY POrderTypeId",
        ),
        "general_ledger_voucher_types": _rows(
            cursor,
            """
            SELECT VoucherTypeId,VoucherTypeName,BuiltIn,Insertable,Modifiable,
                   Deleteable,VnSystemId,FormVoucherType,RowIndex
            FROM dbo.VoucherType ORDER BY VoucherTypeId
            """,
        ),
        "external_to_general_ledger_mappings": _rows(
            cursor,
            """
            SELECT ExternalVoucherTypeId,VNSystemId,VoucherTypeId,SystemType
            FROM dbo.ExternalVoucherType ORDER BY ExternalVoucherTypeId
            """,
        ),
    }


def _business_date_usage(cursor: Any) -> dict[str, Any]:
    inventory = _decode_fields(
        _rows(
            cursor,
            f"""
            SELECT h.VocherTypeCode AS type_id,
                   CONVERT(varbinary(max),l.Title) AS type_title,
                   COUNT_BIG(*) AS document_count
            FROM inv.tblVocherHdr AS h
            LEFT JOIN GNR.tblLookup AS l ON l.CodeType=14 AND l.Code=h.VocherTypeCode
            WHERE h.VocherDate>='{BUSINESS_DATE_FROM}' AND h.VocherDate<='{BUSINESS_DATE_TO}'
            GROUP BY h.VocherTypeCode,l.Title
            ORDER BY document_count DESC,h.VocherTypeCode
            """,
        ),
        ("type_title",),
    )
    orders = _decode_fields(
        _rows(
            cursor,
            f"""
            SELECT h.OrderType AS type_id,
                   CONVERT(varbinary(max),t.Title) AS type_title,
                   COUNT_BIG(*) AS document_count
            FROM SLE.tblOrderHdr AS h
            LEFT JOIN SLE.tblOrderType AS t ON t.ID=h.OrderType
            WHERE h.OrderDate>='{BUSINESS_DATE_FROM}' AND h.OrderDate<='{BUSINESS_DATE_TO}'
            GROUP BY h.OrderType,t.Title
            ORDER BY document_count DESC,h.OrderType
            """,
        ),
        ("type_title",),
    )
    ledger = _rows(
        cursor,
        f"""
        SELECT h.VoucherTypeId AS type_id,t.VoucherTypeName AS type_title,
               COUNT_BIG(*) AS document_count
        FROM dbo.Voucher AS h
        LEFT JOIN dbo.VoucherType AS t ON t.VoucherTypeId=h.VoucherTypeId
        WHERE h.VoucherDate>='{BUSINESS_DATE_FROM}' AND h.VoucherDate<='{BUSINESS_DATE_TO}'
        GROUP BY h.VoucherTypeId,t.VoucherTypeName
        ORDER BY document_count DESC,h.VoucherTypeId
        """,
    )
    date_ranges = _rows(
        cursor,
        """
        SELECT 'inventory_voucher' AS document_family,
               MIN(VocherDate) AS min_business_date,MAX(VocherDate) AS max_business_date,
               MIN(CreationDate) AS min_created_at,MAX(CreationDate) AS max_created_at
        FROM inv.tblVocherHdr
        UNION ALL
        SELECT 'sales_order',MIN(OrderDate),MAX(OrderDate),MIN(CreationDate),MAX(CreationDate)
        FROM SLE.tblOrderHdr
        UNION ALL
        SELECT 'general_ledger_voucher',MIN(VoucherDate),MAX(VoucherDate),MIN(CreatedDate),MAX(CreatedDate)
        FROM dbo.Voucher
        """,
    )
    return {
        "basis": "Persian business-date strings; CreatedDate is excluded from usage semantics",
        "from": BUSINESS_DATE_FROM,
        "to": BUSINESS_DATE_TO,
        "date_ranges": date_ranges,
        "inventory_vouchers": inventory,
        "sales_orders": orders,
        "general_ledger_vouchers": ledger,
        "totals": {
            "inventory_vouchers": sum(row["document_count"] for row in inventory),
            "sales_orders": sum(row["document_count"] for row in orders),
            "general_ledger_vouchers": sum(row["document_count"] for row in ledger),
        },
    }


def _data_quality(cursor: Any) -> dict[str, Any]:
    referential = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g LEFT JOIN GNR.tblUnit u
             ON u.ID=g.UnitRef WHERE g.UnitRef IS NOT NULL AND u.ID IS NULL) AS orphan_goods_units,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g LEFT JOIN GNR.tblUnit u
             ON u.ID=g.PackUnitRef WHERE g.PackUnitRef IS NOT NULL AND u.ID IS NULL) AS orphan_goods_pack_units,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g LEFT JOIN GNR.tblShipType s
             ON s.ID=g.ShipTypeRef WHERE g.ShipTypeRef IS NOT NULL AND s.ID IS NULL) AS orphan_goods_ship_types,
          (SELECT COUNT_BIG(*) FROM GNR.tblStockDC d LEFT JOIN GNR.tblShipType s
             ON s.ID=d.ShipTypeRef WHERE d.ShipTypeRef IS NOT NULL AND s.ID IS NULL) AS orphan_stock_ship_types,
          (SELECT COUNT_BIG(*) FROM inv.tblVocherStockType m LEFT JOIN GNR.tblLookup l
             ON l.CodeType=14 AND l.Code=m.VocherTypeCode WHERE l.Code IS NULL) AS orphan_inventory_voucher_type_links,
          (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr h LEFT JOIN SLE.tblOrderType t
             ON t.ID=h.OrderType WHERE h.OrderType IS NOT NULL AND t.ID IS NULL) AS orphan_sales_order_types,
          (SELECT COUNT_BIG(*) FROM dbo.ExternalVoucherType e LEFT JOIN dbo.VoucherType v
             ON v.VoucherTypeId=e.VoucherTypeId WHERE e.VoucherTypeId IS NOT NULL AND v.VoucherTypeId IS NULL) AS orphan_external_voucher_types,
          (SELECT COUNT_BIG(*) FROM dbo.Voucher h LEFT JOIN dbo.VoucherType v
             ON v.VoucherTypeId=h.VoucherTypeId WHERE h.VoucherTypeId IS NOT NULL AND v.VoucherTypeId IS NULL) AS orphan_general_ledger_voucher_types
        """,
    )[0]
    duplicates = _rows(
        cursor,
        """
        SELECT 'unit_id' AS check_name,COUNT_BIG(*) AS duplicate_groups FROM (
          SELECT ID FROM GNR.tblUnit GROUP BY ID HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'ship_type_id',COUNT_BIG(*) FROM (
          SELECT ID FROM GNR.tblShipType GROUP BY ID HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'inventory_voucher_code',COUNT_BIG(*) FROM (
          SELECT Code FROM GNR.tblLookup WHERE CodeType=14 GROUP BY Code HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'stock_type_ordinal_code',COUNT_BIG(*) FROM (
          SELECT Code FROM GNR.tblLookup WHERE CodeType=70 GROUP BY Code HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'sales_order_type_id',COUNT_BIG(*) FROM (
          SELECT ID FROM SLE.tblOrderType GROUP BY ID HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'general_ledger_voucher_type_id',COUNT_BIG(*) FROM (
          SELECT VoucherTypeId FROM dbo.VoucherType GROUP BY VoucherTypeId HAVING COUNT_BIG(*)>1
        ) d
        """,
    )
    invalid_stock_bits = _rows(
        cursor,
        """
        SELECT 'stock_center' AS source,StockType,COUNT_BIG(*) AS row_count
        FROM GNR.tblStockDC
        WHERE StockType IS NOT NULL AND (StockType<0 OR StockType>=32)
        GROUP BY StockType
        UNION ALL
        SELECT 'voucher_stock_bridge',StockType,COUNT_BIG(*)
        FROM inv.tblVocherStockType
        WHERE StockType IS NOT NULL AND StockType NOT IN (1,2,4,8,16)
        GROUP BY StockType
        ORDER BY source,StockType
        """,
    )
    missing_inventory_lookup_usage = _rows(
        cursor,
        f"""
        SELECT m.VocherTypeCode,
               COUNT_BIG(*) AS bridge_row_count,
               (SELECT COUNT_BIG(*) FROM inv.tblVocherHdr h
                 WHERE h.VocherTypeCode=m.VocherTypeCode) AS all_time_document_count,
               (SELECT COUNT_BIG(*) FROM inv.tblVocherHdr h
                 WHERE h.VocherTypeCode=m.VocherTypeCode
                   AND h.VocherDate>='{BUSINESS_DATE_FROM}'
                   AND h.VocherDate<='{BUSINESS_DATE_TO}') AS business_window_document_count
        FROM inv.tblVocherStockType AS m
        LEFT JOIN GNR.tblLookup AS l
          ON l.CodeType=14 AND l.Code=m.VocherTypeCode
        WHERE l.Code IS NULL
        GROUP BY m.VocherTypeCode
        ORDER BY m.VocherTypeCode
        """,
    )
    return {
        "referential_integrity": referential,
        "duplicate_key_groups": duplicates,
        "invalid_or_composite_stock_type_values": invalid_stock_bits,
        "missing_inventory_lookup_usage": missing_inventory_lookup_usage,
    }


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        tables = [
            _table_metadata(cursor, item["object"], item["role"])
            for item in DOMAIN_TABLES
        ]
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "units_stock_and_document_types",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata, aggregates, and non-sensitive type labels",
            },
            "safety": safety,
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "units_and_shipping": _units_and_shipping(cursor),
            "stock_and_inventory_types": _stock_and_inventory_types(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "document_types": _document_types(cursor),
            "business_date_usage": _business_date_usage(cursor),
            "data_quality": _data_quality(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() AS captured_at")[0],
            "evidence_limits": [
                "The 1405/03/01 through 1405/05/31 window is based on Persian business dates, not record creation timestamps.",
                "GNR stock-type lookup codes are ordinal 0..4 while operational contracts use bit flags 1,2,4,8,16.",
                "GNR.HasStockType appears offset against the observed ordinal lookup and must not be copied without UI/runtime confirmation.",
                "DocumentType contains personnel attachment categories and is not an operational or accounting voucher-type master.",
                "Formal dependencies do not capture dynamic SQL or every implicit Ref/Id convention.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON output path")
    args = parser.parse_args()
    result = collect()
    payload = json.dumps(result, ensure_ascii=False, indent=2, default=_json_default)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(args.output.resolve())
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
