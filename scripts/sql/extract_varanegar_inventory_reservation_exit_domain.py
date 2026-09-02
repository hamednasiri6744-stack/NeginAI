"""Extract Varanegar inventory, reservation, and warehouse-exit evidence.

The extractor is pinned to the local read-only clone.  It persists schema,
safe reference labels, aggregate balances, reconciliation results, and the SQL
modules that define inventory semantics.  It intentionally excludes comments,
user/host names, customer/personnel rows, credentials, and raw operational PII.
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
    {"object": "GNR.tblStockDC", "role": "warehouse_or_stock_center_master"},
    {"object": "GNR.tblStockGoods", "role": "operational_stock_balance_snapshot"},
    {"object": "GNR.tblStockGoodsDetail", "role": "batch_level_stock_balance_snapshot"},
    {"object": "inv.tblCardexType", "role": "inventory_movement_effect_contract"},
    {"object": "inv.tblVocherStockType", "role": "voucher_type_stock_channel_bridge"},
    {"object": "inv.tblVocherHdr", "role": "inventory_voucher_header"},
    {"object": "inv.tblVocherItm", "role": "inventory_voucher_line"},
    {"object": "inv.tblVocherItmPrice", "role": "inventory_voucher_line_value"},
    {"object": "inv.tblVocherItmDetail", "role": "inventory_voucher_batch_line"},
    {"object": "inv.tblExit", "role": "warehouse_exit_header"},
    {"object": "dbo.PreSaleStockOnHandQty", "role": "bounded_presale_stock_projection"},
    {"object": "NGT.StockLevels", "role": "tour_or_vehicle_stock_sync_snapshot"},
    {"object": "NGT.BatchOnHands", "role": "ngt_batch_stock_snapshot"},
)

BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"
CURRENT_ACC_YEAR = 1405


def _object_ids_sql() -> str:
    return ",".join(f"OBJECT_ID(N'{item['object']}', 'U')" for item in DOMAIN_TABLES)


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    ids = _object_ids_sql()
    return _rows(cursor, f"""
        SELECT fk.name constraint_name,
               OBJECT_SCHEMA_NAME(fk.parent_object_id) parent_schema,
               OBJECT_NAME(fk.parent_object_id) parent_table,pc.name parent_column,
               OBJECT_SCHEMA_NAME(fk.referenced_object_id) referenced_schema,
               OBJECT_NAME(fk.referenced_object_id) referenced_table,rc.name referenced_column,
               fk.delete_referential_action_desc on_delete,
               fk.update_referential_action_desc on_update,
               fk.is_disabled,fk.is_not_trusted
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE fk.parent_object_id IN ({ids}) OR fk.referenced_object_id IN ({ids})
        ORDER BY referenced_schema,referenced_table,parent_schema,parent_table,
                 fk.name,fkc.constraint_column_id
    """)


def _module_consumers(cursor: Any) -> list[dict[str, Any]]:
    ids = _object_ids_sql()
    return _rows(cursor, f"""
        SELECT DISTINCT OBJECT_SCHEMA_NAME(d.referencing_id) consumer_schema,
               OBJECT_NAME(d.referencing_id) consumer_name,o.type_desc consumer_type,
               OBJECT_SCHEMA_NAME(d.referenced_id) source_schema,
               OBJECT_NAME(d.referenced_id) source_table,
               d.is_schema_bound_reference,o.modify_date consumer_modify_date
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects o ON o.object_id=d.referencing_id
        WHERE d.referenced_id IN ({ids})
        ORDER BY source_schema,source_table,consumer_schema,consumer_name
    """)


def _implicit_link_candidates(cursor: Any) -> list[dict[str, Any]]:
    ids = _object_ids_sql()
    return _rows(cursor, f"""
        WITH candidates AS (
          SELECT c.object_id,c.column_id,s.name schema_name,t.name table_name,
                 c.name column_name,TYPE_NAME(c.user_type_id) data_type
          FROM sys.columns c
          JOIN sys.tables t ON t.object_id=c.object_id
          JOIN sys.schemas s ON s.schema_id=t.schema_id
          WHERE LOWER(c.name) LIKE '%stockdcref%'
             OR LOWER(c.name) LIKE '%stockid%'
             OR LOWER(c.name) LIKE '%goodsref%'
             OR LOWER(c.name) LIKE '%productuniqueid%'
             OR LOWER(c.name) LIKE '%vocherref%'
             OR LOWER(c.name) LIKE '%voucherref%'
             OR LOWER(c.name) LIKE '%exitref%'
             OR LOWER(c.name) LIKE '%touruniqueid%'
        )
        SELECT c.schema_name,c.table_name,c.column_name,c.data_type,
               CASE WHEN fkc.constraint_object_id IS NULL THEN 0 ELSE 1 END has_formal_fk,
               OBJECT_SCHEMA_NAME(fkc.referenced_object_id) formal_target_schema,
               OBJECT_NAME(fkc.referenced_object_id) formal_target_table,
               rc.name formal_target_column
        FROM candidates c
        LEFT JOIN sys.foreign_key_columns fkc
          ON fkc.parent_object_id=c.object_id AND fkc.parent_column_id=c.column_id
        LEFT JOIN sys.columns rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE c.object_id NOT IN ({ids})
        ORDER BY has_formal_fk,c.schema_name,c.table_name,c.column_name
    """)


def _reference_masters(cursor: Any) -> dict[str, Any]:
    stock_centers = _decode_fields(_rows(cursor, """
        SELECT ID,DCRef,StockDCCode,CONVERT(varbinary(max),StockDCName) StockDCName,
               StockType,ShipTypeRef,InActiveAccYear,
               AllowNegativeOnHandQty,AllowNegativeCardexQty
        FROM GNR.tblStockDC ORDER BY ID
    """), ("StockDCName",))
    voucher_types = _decode_fields(_rows(cursor, """
        SELECT Code,CONVERT(varbinary(max),Title) Title,Value1,Value2
        FROM GNR.tblLookup WHERE CodeType=14 ORDER BY Code
    """), ("Title",))
    cardex_types = _decode_fields(_rows(cursor, """
        SELECT c.VocherTypeCode,CONVERT(varbinary(max),l.Title) voucher_title,
               c.HealthCode,c.CardexType,c.EffectType,
               c.EffectOnHandQty,c.EffectDamagedQty,c.EffectReservedQty
        FROM inv.tblCardexType c
        LEFT JOIN GNR.tblLookup l ON l.CodeType=14 AND l.Code=c.VocherTypeCode
        ORDER BY c.VocherTypeCode,c.HealthCode,c.CardexType
    """), ("voucher_title",))
    reservation_reasons = _decode_fields(_rows(cursor, """
        SELECT Code,CONVERT(varbinary(max),Title) Title,Value1,Value2
        FROM GNR.tblLookup WHERE CodeType=1009 ORDER BY Code
    """), ("Title",))
    return {
        "stock_centers": stock_centers,
        "inventory_voucher_types": voucher_types,
        "cardex_effect_contract": cardex_types,
        "reservation_reason_lookup": reservation_reasons,
    }


def _stock_snapshot(cursor: Any) -> dict[str, Any]:
    history = _rows(cursor, """
        SELECT AccYear,COUNT_BIG(*) rows,COUNT(DISTINCT StockDCRef) stock_centers,
               COUNT(DISTINCT GoodsRef) goods,
               SUM(CASE WHEN OnHandQty>0 THEN 1 ELSE 0 END) positive_onhand_rows,
               SUM(CASE WHEN OnHandQty<0 THEN 1 ELSE 0 END) negative_onhand_rows,
               SUM(CASE WHEN ReservedQty<>0 THEN 1 ELSE 0 END) reserved_rows,
               SUM(CASE WHEN DamagedQty<>0 THEN 1 ELSE 0 END) damaged_rows
        FROM GNR.tblStockGoods GROUP BY AccYear ORDER BY AccYear
    """)
    current = _rows(cursor, f"""
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT StockDCRef) stock_centers,
               COUNT(DISTINCT GoodsRef) goods,
               SUM(CASE WHEN OnHandQty>0 THEN 1 ELSE 0 END) positive_onhand_rows,
               SUM(CASE WHEN OnHandQty<0 THEN 1 ELSE 0 END) negative_onhand_rows,
               SUM(CASE WHEN ReservedQty<>0 THEN 1 ELSE 0 END) reserved_rows,
               SUM(CASE WHEN ReservedQty<0 THEN 1 ELSE 0 END) negative_reserved_rows,
               SUM(CASE WHEN ReservedQty>OnHandQty THEN 1 ELSE 0 END) reserved_over_onhand_rows,
               SUM(CASE WHEN OnHandQty-ReservedQty<0 THEN 1 ELSE 0 END) negative_after_reserved_rows,
               SUM(CASE WHEN DamagedQty<>0 THEN 1 ELSE 0 END) damaged_rows,
               SUM(CASE WHEN UnDeliveredQty<>0 THEN 1 ELSE 0 END) undelivered_rows,
               SUM(CASE WHEN IsBatch=1 THEN 1 ELSE 0 END) batch_enabled_rows
        FROM GNR.tblStockGoods WHERE AccYear={CURRENT_ACC_YEAR}
    """)[0]
    by_stock = _rows(cursor, f"""
        SELECT s.StockDCRef,COUNT_BIG(*) rows,COUNT(DISTINCT s.GoodsRef) goods,
               SUM(CASE WHEN s.OnHandQty>0 THEN 1 ELSE 0 END) positive_onhand_rows,
               SUM(CASE WHEN s.ReservedQty<>0 THEN 1 ELSE 0 END) reserved_rows,
               SUM(CASE WHEN s.OnHandQty-s.ReservedQty<0 THEN 1 ELSE 0 END) negative_after_reserved_rows,
               SUM(CASE WHEN s.DamagedQty<>0 THEN 1 ELSE 0 END) damaged_rows
        FROM GNR.tblStockGoods s WHERE s.AccYear={CURRENT_ACC_YEAR}
        GROUP BY s.StockDCRef ORDER BY s.StockDCRef
    """)
    return {"by_accounting_year": history, "current": current, "current_by_stock": by_stock}


def _voucher_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) headers,COUNT(DISTINCT UniqueId) distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuids,
               SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirmed,
               SUM(CASE WHEN ConfirmDate IS NULL THEN 1 ELSE 0 END) unconfirmed,
               SUM(CASE WHEN SupplierRef IS NOT NULL THEN 1 ELSE 0 END) supplier_links,
               SUM(CASE WHEN CustRef IS NOT NULL THEN 1 ELSE 0 END) customer_links,
               SUM(CASE WHEN TStockDCRef IS NOT NULL THEN 1 ELSE 0 END) target_stock_links,
               SUM(CASE WHEN IsMerge=1 THEN 1 ELSE 0 END) merged,
               MIN(VocherDate) minimum_business_date,MAX(VocherDate) maximum_business_date
        FROM inv.tblVocherHdr
    """)[0]
    lines = _rows(cursor, """
        SELECT COUNT_BIG(*) lines,COUNT(DISTINCT HdrRef) headers,
               COUNT(DISTINCT GoodsRef) goods,
               SUM(CASE WHEN TotalQty IS NULL THEN 1 ELSE 0 END) null_qty,
               SUM(CASE WHEN TotalQty=0 THEN 1 ELSE 0 END) zero_qty,
               SUM(CASE WHEN TotalQty<0 THEN 1 ELSE 0 END) negative_qty,
               SUM(CASE WHEN UnitCapacity<=0 THEN 1 ELSE 0 END) nonpositive_unit_capacity
        FROM inv.tblVocherItm
    """)[0]
    business_window = _decode_fields(_rows(cursor, f"""
        SELECT h.VocherTypeCode,CONVERT(varbinary(max),l.Title) voucher_title,
               COUNT(DISTINCT h.ID) headers,COUNT_BIG(*) lines,
               SUM(CASE WHEN h.ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirmed_lines
        FROM inv.tblVocherHdr h
        JOIN inv.tblVocherItm i ON i.HdrRef=h.ID
        LEFT JOIN GNR.tblLookup l ON l.CodeType=14 AND l.Code=h.VocherTypeCode
        WHERE h.VocherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
        GROUP BY h.VocherTypeCode,l.Title ORDER BY headers DESC
    """), ("voucher_title",))
    return {"population": population, "lines": lines,
            "business_window": {"from": BUSINESS_DATE_FROM, "to": BUSINESS_DATE_TO,
                                "by_type": business_window}}


def _balance_reconciliation(cursor: Any) -> dict[str, Any]:
    healthy = _rows(cursor, f"""
        WITH v AS (
          SELECT AccYear,StockDCRef,GoodsRef,SUM(CONVERT(decimal(38,6),Qty)) calculated
          FROM inv.vwHealthyCardex WHERE AccYear={CURRENT_ACC_YEAR}
          GROUP BY AccYear,StockDCRef,GoodsRef
        ), z AS (
          SELECT s.StockDCRef,s.GoodsRef,ISNULL(s.OnHandQty,0) stored,
                 ISNULL(v.calculated,0) calculated,
                 CASE WHEN v.GoodsRef IS NULL THEN 1 ELSE 0 END no_ledger
          FROM GNR.tblStockGoods s
          LEFT JOIN v ON v.AccYear=s.AccYear AND v.StockDCRef=s.StockDCRef
                     AND v.GoodsRef=s.GoodsRef
          WHERE s.AccYear={CURRENT_ACC_YEAR}
        )
        SELECT COUNT_BIG(*) compared_keys,
               SUM(CASE WHEN stored=calculated THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN stored<>calculated THEN 1 ELSE 0 END) mismatch,
               SUM(CASE WHEN stored>calculated THEN 1 ELSE 0 END) stored_greater,
               SUM(CASE WHEN stored<calculated THEN 1 ELSE 0 END) ledger_greater,
               SUM(no_ledger) stock_rows_without_ledger,
               SUM(ABS(stored-calculated)) absolute_difference
        FROM z
    """)[0]
    healthy_by_stock = _rows(cursor, f"""
        WITH v AS (
          SELECT AccYear,StockDCRef,GoodsRef,SUM(CONVERT(decimal(38,6),Qty)) calculated
          FROM inv.vwHealthyCardex WHERE AccYear={CURRENT_ACC_YEAR}
          GROUP BY AccYear,StockDCRef,GoodsRef
        ), z AS (
          SELECT s.StockDCRef,s.GoodsRef,ISNULL(s.OnHandQty,0) stored,
                 ISNULL(v.calculated,0) calculated
          FROM GNR.tblStockGoods s
          LEFT JOIN v ON v.AccYear=s.AccYear AND v.StockDCRef=s.StockDCRef
                     AND v.GoodsRef=s.GoodsRef
          WHERE s.AccYear={CURRENT_ACC_YEAR}
        )
        SELECT StockDCRef,COUNT_BIG(*) stock_rows,
               SUM(CASE WHEN stored<>calculated THEN 1 ELSE 0 END) mismatch,
               SUM(stored-calculated) signed_difference,
               SUM(ABS(stored-calculated)) absolute_difference
        FROM z GROUP BY StockDCRef ORDER BY StockDCRef
    """)
    damaged = _rows(cursor, f"""
        WITH v AS (
          SELECT AccYear,StockDCRef,GoodsRef,SUM(CONVERT(decimal(38,6),Qty)) calculated
          FROM inv.vwDamagedCardex WHERE AccYear={CURRENT_ACC_YEAR}
          GROUP BY AccYear,StockDCRef,GoodsRef
        ), z AS (
          SELECT s.GoodsRef,ISNULL(s.DamagedQty,0) stored,ISNULL(v.calculated,0) calculated
          FROM GNR.tblStockGoods s
          LEFT JOIN v ON v.AccYear=s.AccYear AND v.StockDCRef=s.StockDCRef
                     AND v.GoodsRef=s.GoodsRef
          WHERE s.AccYear={CURRENT_ACC_YEAR}
        )
        SELECT COUNT_BIG(*) compared_keys,
               SUM(CASE WHEN stored=calculated THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN stored<>calculated THEN 1 ELSE 0 END) mismatch,
               SUM(ABS(stored-calculated)) absolute_difference FROM z
    """)[0]
    reserved = _rows(cursor, f"""
        WITH v AS (
          SELECT AccYear,StockDCRef,GoodsRef,SUM(CONVERT(decimal(38,6),Qty)) calculated
          FROM inv.vwReservedCardex WHERE AccYear={CURRENT_ACC_YEAR}
          GROUP BY AccYear,StockDCRef,GoodsRef
        ), z AS (
          SELECT s.GoodsRef,ISNULL(s.ReservedQty,0) stored,ISNULL(v.calculated,0) calculated
          FROM GNR.tblStockGoods s
          LEFT JOIN v ON v.AccYear=s.AccYear AND v.StockDCRef=s.StockDCRef
                     AND v.GoodsRef=s.GoodsRef
          WHERE s.AccYear={CURRENT_ACC_YEAR}
        )
        SELECT COUNT_BIG(*) compared_keys,
               SUM(CASE WHEN stored=calculated THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN stored<>calculated THEN 1 ELSE 0 END) mismatch,
               SUM(ABS(stored-calculated)) absolute_difference FROM z
    """)[0]
    return {"healthy_onhand": healthy, "healthy_onhand_by_stock": healthy_by_stock,
            "damaged": damaged, "reserved": reserved,
            "method": "current StockGoods snapshots compared with official cardex views"}


def _availability_contracts(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, f"""
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT GoodsRef) goods,
               COUNT(DISTINCT StockDCRef) stock_centers,
               SUM(CASE WHEN ISNULL(ReservedQty,0)<>0 THEN 1 ELSE 0 END) reserved_nonzero,
               SUM(CASE WHEN ISNULL(OpenOrderQty,0)<>0 THEN 1 ELSE 0 END) open_order_nonzero,
               SUM(CASE WHEN ISNULL(ReservedQty,0)<>0 AND ISNULL(OpenOrderQty,0)<>0
                        THEN 1 ELSE 0 END) both_nonzero,
               SUM(ISNULL(OpenOrderQty,0)) open_order_qty,
               SUM(CASE WHEN OnHandQty-ISNULL(ReservedQty,0)<0 THEN 1 ELSE 0 END)
                    negative_onhand_minus_reserved,
               SUM(CASE WHEN RemQty<0 THEN 1 ELSE 0 END) negative_onhand_minus_open_order
        FROM FRU.StockGoodsModel WHERE AccYear={CURRENT_ACC_YEAR}
    """)[0]


def _exit_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) exits,
               SUM(CASE WHEN IsCanceled=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN IsCanceled<>0 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN DistRef IS NOT NULL THEN 1 ELSE 0 END) distribution_links,
               SUM(CASE WHEN DriverRef IS NOT NULL THEN 1 ELSE 0 END) direct_driver_links
        FROM inv.tblExit
    """)[0]
    type60 = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM inv.tblVocherHdr WHERE VocherTypeCode=60) type60_headers,
          (SELECT COUNT(DISTINCT DocRef) FROM inv.tblVocherHdr WHERE VocherTypeCode=60) distinct_exit_refs,
          (SELECT COUNT_BIG(*) FROM inv.tblVocherHdr h JOIN inv.tblExit e ON e.ID=h.DocRef
             WHERE h.VocherTypeCode=60 AND e.IsCanceled=0) active_exit_matches,
          (SELECT COUNT_BIG(*) FROM inv.tblVocherHdr h JOIN inv.tblExit e ON e.ID=h.DocRef
             WHERE h.VocherTypeCode=60 AND h.StockDCRef=e.StockDCRef) stock_center_agreements,
          (SELECT COUNT_BIG(*) FROM inv.tblExit e WHERE e.IsCanceled=0 AND NOT EXISTS
             (SELECT 1 FROM inv.tblVocherHdr h WHERE h.VocherTypeCode=60 AND h.DocRef=e.ID))
             active_exits_without_type60,
          (SELECT COUNT_BIG(*) FROM (SELECT DocRef FROM inv.tblVocherHdr WHERE VocherTypeCode=60
             GROUP BY DocRef HAVING COUNT_BIG(*)>1)x) duplicate_exit_ref_groups
    """)[0]
    business_window = _rows(cursor, f"""
        SELECT COUNT_BIG(*) exits,
               SUM(CASE WHEN IsCanceled<>0 THEN 1 ELSE 0 END) cancelled,
               COUNT(DISTINCT StockDCRef) stock_centers,
               COUNT(DISTINCT DistRef) distributions
        FROM inv.tblExit WHERE ExitDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
    """)[0]
    sale_links = _rows(cursor, """
        SELECT COUNT_BIG(*) sale_rows,COUNT(DISTINCT ExitRef) exits,
               SUM(CASE WHEN e.ID IS NULL THEN 1 ELSE 0 END) orphan_exit_links,
               SUM(CASE WHEN e.IsCanceled<>0 THEN 1 ELSE 0 END) links_to_cancelled_exits
        FROM SLE.tblSaleHdr s LEFT JOIN inv.tblExit e ON e.ID=s.ExitRef
        WHERE s.ExitRef IS NOT NULL
    """)[0]
    return {"population": population, "type60_exit_crosswalk": type60,
            "business_window": business_window, "sale_links": sale_links}


def _presale_projection(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT ProductId) products,
               COUNT(DISTINCT StockId) stock_centers,
               SUM(CASE WHEN OnHandQty<0 THEN 1 ELSE 0 END) negative_onhand,
               SUM(CASE WHEN HasAllocation=1 THEN 1 ELSE 0 END) allocation_flag,
               SUM(CASE WHEN g.ID IS NOT NULL THEN 1 ELSE 0 END) product_uuid_matches,
               SUM(CASE WHEN s.ID IS NOT NULL THEN 1 ELSE 0 END) stock_uuid_matches
        FROM dbo.PreSaleStockOnHandQty p
        LEFT JOIN GNR.tblGoods g ON g.UniqueId=p.ProductId
        LEFT JOIN GNR.tblStockDC s ON s.UniqueId=p.StockId
    """)[0]


def _ngt_tour_stock(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT TourUniqueId) tours,
               COUNT(DISTINCT ProductUniqueId) products,
               SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed,
               SUM(CASE WHEN HasConflict=1 THEN 1 ELSE 0 END) conflict,
               SUM(CASE WHEN Number_ID=0 THEN 1 ELSE 0 END) zero_number_id,
               SUM(CASE WHEN InitialQty IS NOT NULL THEN 1 ELSE 0 END) initial_present,
               SUM(CASE WHEN InitialQty<>0 THEN 1 ELSE 0 END) initial_nonzero,
               SUM(CASE WHEN RenewQty IS NOT NULL THEN 1 ELSE 0 END) renew_present,
               SUM(CASE WHEN SoldQty IS NOT NULL THEN 1 ELSE 0 END) sold_present,
               SUM(CASE WHEN RemainQty IS NOT NULL THEN 1 ELSE 0 END) remain_present,
               SUM(CASE WHEN ActualQty IS NOT NULL THEN 1 ELSE 0 END) actual_present,
               MIN(CreatedDate) minimum_created,MAX(CreatedDate) maximum_created,
               MAX(LastUpdate) maximum_updated
        FROM NGT.StockLevels
    """)[0]
    links = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM NGT.StockLevels n LEFT JOIN GNR.tblGoods g
             ON g.UniqueId=n.ProductUniqueId WHERE g.ID IS NULL) orphan_product_uuid,
          (SELECT COUNT_BIG(*) FROM NGT.StockLevels n LEFT JOIN NGT.Tours t
             ON t.Id=n.TourUniqueId WHERE t.Id IS NULL) orphan_tour_uuid,
          (SELECT COUNT_BIG(*) FROM (SELECT TourUniqueId,ProductUniqueId FROM NGT.StockLevels
             GROUP BY TourUniqueId,ProductUniqueId HAVING COUNT_BIG(*)>1)x)
             duplicate_tour_product_groups,
          (SELECT COUNT_BIG(*) FROM (SELECT Id FROM NGT.StockLevels
             GROUP BY Id HAVING COUNT_BIG(*)>1)x) duplicate_ids,
          (SELECT COUNT_BIG(*) FROM FRU.StockLevels) fru_source_rows
    """)[0]
    return {"population": population, "crosswalk_quality": links}


def _data_quality(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM (SELECT AccYear,StockDCRef,GoodsRef
             FROM GNR.tblStockGoods GROUP BY AccYear,StockDCRef,GoodsRef
             HAVING COUNT_BIG(*)>1)x) duplicate_stock_keys,
          (SELECT COUNT_BIG(*) FROM GNR.tblStockGoods s LEFT JOIN GNR.tblGoods g
             ON g.ID=s.GoodsRef WHERE g.ID IS NULL) orphan_stock_goods,
          (SELECT COUNT_BIG(*) FROM GNR.tblStockGoods s LEFT JOIN GNR.tblStockDC d
             ON d.ID=s.StockDCRef WHERE d.ID IS NULL) orphan_stock_centers,
          (SELECT COUNT_BIG(*) FROM inv.tblVocherItm i LEFT JOIN inv.tblVocherHdr h
             ON h.ID=i.HdrRef WHERE h.ID IS NULL) orphan_voucher_lines,
          (SELECT COUNT_BIG(*) FROM inv.tblVocherItm i LEFT JOIN GNR.tblGoods g
             ON g.ID=i.GoodsRef WHERE g.ID IS NULL) orphan_voucher_goods,
          (SELECT COUNT_BIG(*) FROM (SELECT UniqueId FROM inv.tblVocherHdr
             WHERE UniqueId IS NOT NULL GROUP BY UniqueId HAVING COUNT_BIG(*)>1)x)
             duplicate_voucher_uuid_groups,
          (SELECT COUNT_BIG(*) FROM (SELECT AccYear,StockDCRef,VocherTypeCode,VocherNo
             FROM inv.tblVocherHdr GROUP BY AccYear,StockDCRef,VocherTypeCode,VocherNo
             HAVING COUNT_BIG(*)>1)x) duplicate_voucher_composite_number_groups
    """)[0]


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition,o.modify_date
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE (s.name='inv' AND o.name IN
              ('vwHealthyCardexFast','vwHealthyCardex','vwDamagedCardex',
               'vwReservedCardex','UspListOfReservedGoods',
               'trg_tblVocherHdr_UpdateStockGoods'))
           OR (s.name='GNR' AND o.name IN
              ('trg_StockGoods_CheckOnHandQty','trg_StockGoods_ReservedQty',
               'usp_CopyCardexToNewYear'))
           OR (s.name='FRU' AND o.name IN ('StockGoodsModel','StockLevelsModel'))
           OR (s.name='dbo' AND o.name IN
              ('NGT_ReplicateTour','NGT_DoReplicateTour','USP_NGT_ModifyActualStockLevel'))
        ORDER BY s.name,o.name
    """)


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        tables = [_table_metadata(cursor, x["object"], x["role"]) for x in DOMAIN_TABLES]
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "inventory_reservation_and_exit",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata and aggregate inventory evidence",
                "privacy_policy": "no comments, users, hosts, party rows, credentials, or raw PII",
                "current_accounting_year": CURRENT_ACC_YEAR,
            },
            "safety": safety,
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "reference_masters": _reference_masters(cursor),
            "stock_snapshot": _stock_snapshot(cursor),
            "inventory_vouchers": _voucher_profile(cursor),
            "balance_reconciliation": _balance_reconciliation(cursor),
            "availability_contracts": _availability_contracts(cursor),
            "warehouse_exits": _exit_profile(cursor),
            "presale_projection": _presale_projection(cursor),
            "ngt_tour_stock": _ngt_tour_stock(cursor),
            "data_quality": _data_quality(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "evidence_limits": [
                "GNR.tblStockGoods is an operational snapshot; a naive sum of voucher rows is not an interchangeable source.",
                "ReservedQty and open-order quantity are independent contracts and must not share one destination field.",
                "The current healthy-cardex mismatch is a reconciliation finding, not proof that either side can be overwritten.",
                "DocRef is polymorphic by inventory voucher type; only type 60 to inv.tblExit is proven here.",
                "NGT.StockLevels is tour/vehicle stock synchronization, not the warehouse balance master.",
                "PreSaleStockOnHandQty is a bounded projection and does not cover every current stock/goods key.",
                "Formal dependencies do not capture dynamic SQL or every Ref/Id/UUID convention.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON output path")
    args = parser.parse_args()
    payload = json.dumps(collect(), ensure_ascii=False, indent=2, default=_json_default)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(args.output.resolve())
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
