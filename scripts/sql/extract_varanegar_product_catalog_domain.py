"""Extract Varanegar product-catalog evidence from the local read-only clone.

The slice preserves the legacy GNR goods/group model, the UUID-based NGT
product-group/catalog model, packaging units, promotional goods packages, and
all observed barcode surfaces as distinct contracts.  It never connects to the
live operational database and reuses the established safety gate.
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
    {"object": "GNR.tblGoods", "role": "legacy_product_master"},
    {"object": "GNR.tblGoodsGroup", "role": "legacy_nested_set_product_group"},
    {"object": "GNR.tblBrand", "role": "brand_master"},
    {"object": "GNR.tblManufacturer", "role": "manufacturer_master"},
    {"object": "GNR.tblGoodsType", "role": "built_in_goods_type"},
    {"object": "GNR.tblGoodsCtgr", "role": "pricing_goods_category"},
    {"object": "GNR.tblMainType", "role": "legacy_main_product_classification"},
    {"object": "GNR.tblSubType", "role": "legacy_sub_product_classification"},
    {"object": "GNR.tblGoodsMainSubType", "role": "goods_classification_bridge"},
    {"object": "GNR.tblPackage", "role": "goods_unit_and_quantity_package"},
    {"object": "GNR.tblGoodsBarcode", "role": "additional_goods_barcode"},
    {"object": "GNR.tblGoodsSupplier", "role": "goods_supplier_bridge"},
    {"object": "SLE.tblGoodsPackage", "role": "promotional_or_discount_goods_package"},
    {"object": "SLE.tblGoodsPackageItem", "role": "promotional_package_item"},
    {"object": "NGT.ProductGroups", "role": "uuid_product_group_tree"},
    {"object": "NGT.Catalogs", "role": "ngt_product_catalog"},
    {"object": "NGT.CatalogProducts", "role": "ngt_catalog_product_bridge"},
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
            WHERE LOWER(c.name) LIKE '%goodsref%'
               OR LOWER(c.name) LIKE '%productid%'
               OR LOWER(c.name) LIKE '%productuniqueid%'
               OR LOWER(c.name) LIKE '%goodsgroup%'
               OR LOWER(c.name) LIKE '%productgroup%'
               OR LOWER(c.name) LIKE '%brandref%'
               OR LOWER(c.name) LIKE '%manufacturerref%'
               OR LOWER(c.name) LIKE '%packageref%'
               OR LOWER(c.name) LIKE '%barcode%'
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


def _legacy_masters(cursor: Any) -> dict[str, Any]:
    groups = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,ParentRef,CONVERT(varbinary(max),GoodsGroupName) AS GoodsGroupName,
                   BarCode,DLCode,NLeft,NRight,NLevel,UniqueId
            FROM GNR.tblGoodsGroup ORDER BY NLeft,ID
            """,
        ),
        ("GoodsGroupName",),
    )
    brands = _decode_fields(
        _rows(
            cursor,
            """
            SELECT id,CONVERT(varbinary(max),BrandName) AS BrandName,UniqueId,
                   SLId,DLId,FifthLedgerId,SixthLedgerId,SeventhLedgerId
            FROM GNR.tblBrand ORDER BY id
            """,
        ),
        ("BrandName",),
    )
    manufacturers = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Id,ManufacturerCode,
                   CONVERT(varbinary(max),ManufacturerName) AS ManufacturerName,
                   ManufacturerCode2,ManufacturerType,UsanceDay,UniqueId,SLId,DLId
            FROM GNR.tblManufacturer ORDER BY Id
            """,
        ),
        ("ManufacturerName",),
    )
    goods_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Id,CONVERT(varbinary(max),GoodsTypeName) AS GoodsTypeName,BuiltIn
            FROM GNR.tblGoodsType ORDER BY Id
            """,
        ),
        ("GoodsTypeName",),
    )
    goods_categories = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,GoodsCtgrCode,
                   CONVERT(varbinary(max),GoodsCtgrName) AS GoodsCtgrName
            FROM GNR.tblGoodsCtgr ORDER BY ID
            """,
        ),
        ("GoodsCtgrName",),
    )
    main_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Id,MainCode,CONVERT(varbinary(max),MainName) AS MainName,LookUpId
            FROM GNR.tblMainType ORDER BY Id
            """,
        ),
        ("MainName",),
    )
    sub_types = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Id,SubCode,CONVERT(varbinary(max),SubName) AS SubName,MainTypeRef
            FROM GNR.tblSubType ORDER BY MainTypeRef,Id
            """,
        ),
        ("SubName",),
    )
    return {
        "legacy_goods_groups": groups,
        "brands": brands,
        "manufacturers": manufacturers,
        "goods_types": goods_types,
        "pricing_goods_categories": goods_categories,
        "main_types": main_types,
        "sub_types": sub_types,
        "goods_main_sub_type_links": _rows(
            cursor,
            """
            SELECT Id,GoodsRef,MainTypeRef,SubTypeRef,UniqueId
            FROM GNR.tblGoodsMainSubType ORDER BY GoodsRef,MainTypeRef,SubTypeRef,Id
            """,
        ),
    }


def _goods_snapshot(cursor: Any) -> list[dict[str, Any]]:
    return _decode_fields(
        _rows(
            cursor,
            """
            SELECT g.ID,g.GoodsCode,
                   CONVERT(varbinary(max),g.GoodsName) AS GoodsName,
                   CONVERT(varbinary(max),g.PreName) AS PreName,
                   g.UniqueId,g.GoodsGroupRef,
                   CONVERT(varbinary(max),gg.GoodsGroupName) AS GoodsGroupName,
                   g.BrandRef,CONVERT(varbinary(max),b.BrandName) AS BrandName,
                   g.ManufacturerRef,
                   CONVERT(varbinary(max),m.ManufacturerName) AS ManufacturerName,
                   g.GoodsTypeRef,
                   CONVERT(varbinary(max),gt.GoodsTypeName) AS GoodsTypeName,
                   g.UnitRef,g.PackUnitRef,g.ShipTypeRef,g.GoodsWeight,g.CartonType,
                   g.CartonPrizeQty,g.Barcode,g.Barcode2,g.GTIN,g.IRC,
                   g.ShowInSale,g.ShowInBuy,g.CanBeFree,g.IsQRCodeRequired,
                   g.UseBatchPackage,g.MinOrderCount,g.MaxOrderCount,
                   g.POLNotShowInApp,g.ProductMainGroupUniqueId,
                   g.ProductSubGroupUniqueId,g.ProductSubGroupRef,g.ModifiedDate
            FROM GNR.tblGoods AS g
            LEFT JOIN GNR.tblGoodsGroup AS gg ON gg.ID=g.GoodsGroupRef
            LEFT JOIN GNR.tblBrand AS b ON b.id=g.BrandRef
            LEFT JOIN GNR.tblManufacturer AS m ON m.Id=g.ManufacturerRef
            LEFT JOIN GNR.tblGoodsType AS gt ON gt.Id=g.GoodsTypeRef
            ORDER BY g.ID
            """,
        ),
        ("GoodsName", "PreName", "GoodsGroupName", "BrandName", "ManufacturerName", "GoodsTypeName"),
    )


def _goods_master_usage(cursor: Any) -> dict[str, Any]:
    return {
        "population": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_goods,
                   SUM(CASE WHEN ShowInSale=1 THEN 1 ELSE 0 END) AS show_in_sale,
                   SUM(CASE WHEN ShowInBuy=1 THEN 1 ELSE 0 END) AS show_in_buy,
                   SUM(CASE WHEN POLNotShowInApp=1 THEN 1 ELSE 0 END) AS hidden_in_pol,
                   SUM(CASE WHEN UniqueId IS NOT NULL THEN 1 ELSE 0 END) AS uuid_populated,
                   SUM(CASE WHEN ProductMainGroupUniqueId IS NOT NULL THEN 1 ELSE 0 END) AS ngt_main_group_populated,
                   SUM(CASE WHEN ProductSubGroupUniqueId IS NOT NULL THEN 1 ELSE 0 END) AS ngt_sub_group_populated,
                   SUM(CASE WHEN Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>'' THEN 1 ELSE 0 END) AS barcode1_populated,
                   SUM(CASE WHEN Barcode2 IS NOT NULL AND LTRIM(RTRIM(Barcode2))<>'' THEN 1 ELSE 0 END) AS barcode2_populated,
                   SUM(CASE WHEN GTIN IS NOT NULL AND LTRIM(RTRIM(GTIN))<>'' THEN 1 ELSE 0 END) AS gtin_populated,
                   SUM(CASE WHEN IRC IS NOT NULL AND LTRIM(RTRIM(IRC))<>'' THEN 1 ELSE 0 END) AS irc_populated
            FROM GNR.tblGoods
            """,
        )[0],
        "group_usage": _decode_fields(
            _rows(
                cursor,
                """
                SELECT gg.ID,CONVERT(varbinary(max),gg.GoodsGroupName) AS GoodsGroupName,
                       COUNT_BIG(g.ID) AS goods_count
                FROM GNR.tblGoodsGroup AS gg
                LEFT JOIN GNR.tblGoods AS g ON g.GoodsGroupRef=gg.ID
                GROUP BY gg.ID,gg.GoodsGroupName
                ORDER BY goods_count DESC,gg.ID
                """,
            ),
            ("GoodsGroupName",),
        ),
        "brand_usage": _decode_fields(
            _rows(
                cursor,
                """
                SELECT b.id,CONVERT(varbinary(max),b.BrandName) AS BrandName,
                       COUNT_BIG(g.ID) AS goods_count
                FROM GNR.tblBrand AS b
                LEFT JOIN GNR.tblGoods AS g ON g.BrandRef=b.id
                GROUP BY b.id,b.BrandName
                ORDER BY goods_count DESC,b.id
                """,
            ),
            ("BrandName",),
        ),
        "manufacturer_usage": _decode_fields(
            _rows(
                cursor,
                """
                SELECT m.Id,CONVERT(varbinary(max),m.ManufacturerName) AS ManufacturerName,
                       COUNT_BIG(g.ID) AS goods_count
                FROM GNR.tblManufacturer AS m
                LEFT JOIN GNR.tblGoods AS g ON g.ManufacturerRef=m.Id
                GROUP BY m.Id,m.ManufacturerName
                ORDER BY goods_count DESC,m.Id
                """,
            ),
            ("ManufacturerName",),
        ),
        "goods_type_usage": _decode_fields(
            _rows(
                cursor,
                """
                SELECT t.Id,CONVERT(varbinary(max),t.GoodsTypeName) AS GoodsTypeName,
                       t.BuiltIn,COUNT_BIG(g.ID) AS goods_count
                FROM GNR.tblGoodsType AS t
                LEFT JOIN GNR.tblGoods AS g ON g.GoodsTypeRef=t.Id
                GROUP BY t.Id,t.GoodsTypeName,t.BuiltIn
                ORDER BY goods_count DESC,t.Id
                """,
            ),
            ("GoodsTypeName",),
        ),
    }


def _packaging_and_barcodes(cursor: Any) -> dict[str, Any]:
    packages = _rows(
        cursor,
        """
        SELECT ID,GoodsRef,UnitRef,Qty,Status,ForSale,ForRetSale,ForInv,
               Barcode,DefaultForSale,DefaultForInventory,DefaultForRetSale,UniqueId
        FROM GNR.tblPackage ORDER BY GoodsRef,ID
        """,
    )
    additional_barcodes = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Id,GoodsRef,BarCode,IsDefault,GoodsBarcodeQty,
                   CONVERT(varbinary(max),GoodsBarcodeName) AS GoodsBarcodeName,
                   IsActive,BatchId
            FROM GNR.tblGoodsBarcode ORDER BY GoodsRef,Id
            """,
        ),
        ("GoodsBarcodeName",),
    )
    return {
        "unit_packages": packages,
        "additional_goods_barcodes": additional_barcodes,
        "promotional_packages": _rows(
            cursor,
            "SELECT Id,DiscountRef,UniqueId FROM SLE.tblGoodsPackage ORDER BY Id",
        ),
        "promotional_package_items": _rows(
            cursor,
            """
            SELECT Id,GoodsPackageRef,GoodsRef,UnitQty,UnitRef,TotalQty,
                   ReplaceGoodsRef,PrizePriority,UniqueId
            FROM SLE.tblGoodsPackageItem ORDER BY GoodsPackageRef,Id
            """,
        ),
        "unit_package_profile": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS total_package_rows,
                   COUNT(DISTINCT GoodsRef) AS goods_with_package,
                   SUM(CASE WHEN Status=1 THEN 1 ELSE 0 END) AS status_1_rows,
                   SUM(CASE WHEN ForSale=1 THEN 1 ELSE 0 END) AS for_sale_rows,
                   SUM(CASE WHEN ForRetSale=1 THEN 1 ELSE 0 END) AS for_return_sale_rows,
                   SUM(CASE WHEN ForInv=1 THEN 1 ELSE 0 END) AS for_inventory_rows,
                   SUM(CASE WHEN DefaultForSale=1 THEN 1 ELSE 0 END) AS default_sale_rows,
                   SUM(CASE WHEN DefaultForInventory=1 THEN 1 ELSE 0 END) AS default_inventory_rows,
                   SUM(CASE WHEN DefaultForRetSale=1 THEN 1 ELSE 0 END) AS default_return_sale_rows,
                   SUM(CASE WHEN Qty IS NULL THEN 1 ELSE 0 END) AS null_qty_rows,
                   SUM(CASE WHEN Qty<=0 THEN 1 ELSE 0 END) AS nonpositive_qty_rows,
                   SUM(CASE WHEN Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>'' THEN 1 ELSE 0 END) AS barcode_populated
            FROM GNR.tblPackage
            """,
        )[0],
        "default_package_anomalies": _rows(
            cursor,
            """
            SELECT
              SUM(CASE WHEN sale_defaults=0 THEN 1 ELSE 0 END) AS goods_without_sale_default,
              SUM(CASE WHEN sale_defaults>1 THEN 1 ELSE 0 END) AS goods_with_multiple_sale_defaults,
              SUM(CASE WHEN inventory_defaults=0 THEN 1 ELSE 0 END) AS goods_without_inventory_default,
              SUM(CASE WHEN inventory_defaults>1 THEN 1 ELSE 0 END) AS goods_with_multiple_inventory_defaults,
              SUM(CASE WHEN return_defaults=0 THEN 1 ELSE 0 END) AS goods_without_return_default,
              SUM(CASE WHEN return_defaults>1 THEN 1 ELSE 0 END) AS goods_with_multiple_return_defaults
            FROM (
              SELECT GoodsRef,
                     SUM(CASE WHEN DefaultForSale=1 THEN 1 ELSE 0 END) AS sale_defaults,
                     SUM(CASE WHEN DefaultForInventory=1 THEN 1 ELSE 0 END) AS inventory_defaults,
                     SUM(CASE WHEN DefaultForRetSale=1 THEN 1 ELSE 0 END) AS return_defaults
              FROM GNR.tblPackage GROUP BY GoodsRef
            ) AS x
            """,
        )[0],
        "duplicate_package_groups": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS duplicate_groups FROM (
              SELECT GoodsRef,UnitRef,Qty FROM GNR.tblPackage
              GROUP BY GoodsRef,UnitRef,Qty HAVING COUNT_BIG(*)>1
            ) AS d
            """,
        )[0],
        "barcode_profile": _rows(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM GNR.tblGoods WHERE Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>'') AS goods_barcode1_rows,
              (SELECT COUNT_BIG(*) FROM GNR.tblGoods WHERE Barcode2 IS NOT NULL AND LTRIM(RTRIM(Barcode2))<>'') AS goods_barcode2_rows,
              (SELECT COUNT_BIG(*) FROM GNR.tblGoods WHERE GTIN IS NOT NULL AND LTRIM(RTRIM(GTIN))<>'') AS goods_gtin_rows,
              (SELECT COUNT_BIG(*) FROM GNR.tblPackage WHERE Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>'') AS package_barcode_rows,
              (SELECT COUNT_BIG(*) FROM GNR.tblGoodsBarcode WHERE BarCode IS NOT NULL AND LTRIM(RTRIM(BarCode))<>'') AS additional_barcode_rows,
              (SELECT COUNT_BIG(*) FROM (
                 SELECT Barcode FROM GNR.tblGoods WHERE Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>''
                 GROUP BY Barcode HAVING COUNT(DISTINCT ID)>1
               ) d) AS barcode1_cross_goods_duplicates,
              (SELECT COUNT_BIG(*) FROM (
                 SELECT Barcode FROM GNR.tblPackage WHERE Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>''
                 GROUP BY Barcode HAVING COUNT(DISTINCT GoodsRef)>1
               ) d) AS package_barcode_cross_goods_duplicates,
              (SELECT COUNT_BIG(*) FROM (
                 SELECT BarCode FROM GNR.tblGoodsBarcode WHERE BarCode IS NOT NULL AND LTRIM(RTRIM(BarCode))<>''
                 GROUP BY BarCode HAVING COUNT(DISTINCT GoodsRef)>1
               ) d) AS additional_barcode_cross_goods_duplicates
            """,
        )[0],
        "barcode_format_profile": _rows(
            cursor,
            """
            SELECT
              SUM(CASE WHEN Barcode='0' THEN 1 ELSE 0 END) AS zero_sentinel_rows,
              SUM(CASE WHEN Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>''
                            AND PATINDEX('%[^0-9]%',Barcode)=0 THEN 1 ELSE 0 END) AS digit_only_rows,
              SUM(CASE WHEN Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>''
                            AND PATINDEX('%[^0-9]%',Barcode)>0 THEN 1 ELSE 0 END) AS nondigit_rows,
              (SELECT COUNT_BIG(*) FROM (
                 SELECT Barcode FROM GNR.tblGoods
                 WHERE Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>'' AND Barcode<>'0'
                 GROUP BY Barcode HAVING COUNT(DISTINCT ID)>1
               ) d) AS duplicate_groups_excluding_zero
            FROM GNR.tblGoods
            """,
        )[0],
        "barcode_length_distribution": _rows(
            cursor,
            """
            SELECT LEN(Barcode) AS barcode_length,COUNT_BIG(*) AS row_count
            FROM GNR.tblGoods
            WHERE Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>''
            GROUP BY LEN(Barcode) ORDER BY barcode_length
            """,
        ),
        "duplicate_goods_barcodes": _rows(
            cursor,
            """
            SELECT TOP (100) Barcode,COUNT_BIG(*) AS goods_count,
                   MIN(ID) AS min_goods_id,MAX(ID) AS max_goods_id
            FROM GNR.tblGoods
            WHERE Barcode IS NOT NULL AND LTRIM(RTRIM(Barcode))<>''
            GROUP BY Barcode HAVING COUNT(DISTINCT ID)>1
            ORDER BY goods_count DESC,Barcode
            """,
        ),
        "duplicate_additional_barcodes": _rows(
            cursor,
            """
            SELECT BarCode,COUNT_BIG(*) AS goods_count,
                   MIN(GoodsRef) AS min_goods_id,MAX(GoodsRef) AS max_goods_id
            FROM GNR.tblGoodsBarcode
            WHERE BarCode IS NOT NULL AND LTRIM(RTRIM(BarCode))<>''
            GROUP BY BarCode HAVING COUNT(DISTINCT GoodsRef)>1
            ORDER BY goods_count DESC,BarCode
            """,
        ),
    }


def _ngt_catalog_snapshot(cursor: Any) -> dict[str, Any]:
    groups = _decode_fields(
        _rows(
            cursor,
            """
            SELECT Id,CONVERT(varbinary(max),ProductGroupName) AS ProductGroupName,
                   ParentUniqueId,Number_ID,IsRemoved,OrderOf,RowIndex,
                   CreatedDate,LastUpdate,DataOwnerId,DataOwnerCenterId
            FROM NGT.ProductGroups ORDER BY ParentUniqueId,OrderOf,RowIndex,Id
            """,
        ),
        ("ProductGroupName",),
    )
    return {
        "product_groups": groups,
        "catalogs": _rows(
            cursor,
            """
            SELECT Id,CatalogName,ProductMainGroupUniqueId,IsActive,Number_ID,
                   IsRemoved,CreatedDate,LastUpdate,DataOwnerId,DataOwnerCenterId
            FROM NGT.Catalogs ORDER BY CatalogName,Id
            """,
        ),
        "catalog_products": _rows(
            cursor,
            """
            SELECT Id,CatalogUniqueId,ProductUniqueId,OrderOf,Number_ID,
                   IsRemoved,CreatedDate,LastUpdate,DataOwnerId,DataOwnerCenterId
            FROM NGT.CatalogProducts ORDER BY CatalogUniqueId,OrderOf,Id
            """,
        ),
        "crosswalk_summary": _rows(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM NGT.CatalogProducts) AS catalog_product_rows,
              (SELECT COUNT_BIG(*) FROM NGT.CatalogProducts WHERE IsRemoved=0) AS active_catalog_product_rows,
              (SELECT COUNT_BIG(*) FROM NGT.CatalogProducts c JOIN GNR.tblGoods g
                 ON g.UniqueId=c.ProductUniqueId) AS catalog_products_matching_goods_uuid,
              (SELECT COUNT_BIG(*) FROM NGT.CatalogProducts c JOIN GNR.tblGoods g
                 ON g.ID=c.Number_ID) AS catalog_products_matching_goods_number_id,
              (SELECT COUNT_BIG(*) FROM NGT.CatalogProducts
                 WHERE ProductUniqueId='00000000-0000-0000-0000-000000000000'
                   AND Number_ID=0) AS zero_product_placeholders,
              (SELECT COUNT_BIG(*) FROM GNR.tblGoods g JOIN NGT.ProductGroups n
                 ON n.Id=g.ProductMainGroupUniqueId) AS goods_matching_ngt_main_group,
              (SELECT COUNT_BIG(*) FROM GNR.tblGoods g JOIN NGT.ProductGroups n
                 ON n.Id=g.ProductSubGroupUniqueId) AS goods_matching_ngt_sub_group,
              (SELECT COUNT_BIG(*) FROM GNR.tblGoods g
                 JOIN GNR.tblBrand b ON b.id=g.BrandRef
                 JOIN NGT.ProductGroups n ON n.Id=g.ProductMainGroupUniqueId
                 WHERE LTRIM(RTRIM(b.BrandName))=LTRIM(RTRIM(n.ProductGroupName))) AS goods_main_group_name_matching_brand,
              (SELECT COUNT_BIG(*) FROM NGT.ProductGroups n
                 JOIN GNR.tblBrand b
                   ON LTRIM(RTRIM(b.BrandName))=LTRIM(RTRIM(n.ProductGroupName))
                 WHERE n.IsRemoved=0 AND n.ParentUniqueId IS NULL) AS active_root_names_matching_brand,
              (SELECT COUNT_BIG(*) FROM (
                 SELECT g.BrandRef FROM GNR.tblGoods g
                 GROUP BY g.BrandRef HAVING COUNT(DISTINCT g.ProductMainGroupUniqueId)>1
               ) d) AS brands_mapping_multiple_main_groups,
              (SELECT COUNT_BIG(*) FROM (
                 SELECT g.ProductMainGroupUniqueId FROM GNR.tblGoods g
                 GROUP BY g.ProductMainGroupUniqueId HAVING COUNT(DISTINCT g.BrandRef)>1
               ) d) AS main_groups_mapping_multiple_brands,
              (SELECT COUNT_BIG(*) FROM GNR.tblGoods g JOIN NGT.ProductGroups s
                 ON s.Id=g.ProductSubGroupUniqueId
                 WHERE s.ParentUniqueId<>g.ProductMainGroupUniqueId
                    OR s.ParentUniqueId IS NULL) AS goods_with_main_sub_group_mismatch,
              (SELECT COUNT_BIG(*) FROM NGT.ProductGroups g LEFT JOIN NGT.ProductGroups p
                 ON p.Id=g.ParentUniqueId
                 WHERE g.ParentUniqueId IS NOT NULL AND p.Id IS NULL) AS orphan_group_parents,
              (SELECT COUNT_BIG(*) FROM NGT.CatalogProducts cp LEFT JOIN NGT.Catalogs c
                 ON c.Id=cp.CatalogUniqueId WHERE c.Id IS NULL) AS orphan_catalog_products,
              (SELECT COUNT_BIG(*) FROM NGT.Catalogs c LEFT JOIN NGT.ProductGroups g
                 ON g.Id=c.ProductMainGroupUniqueId
                 WHERE c.ProductMainGroupUniqueId IS NOT NULL AND g.Id IS NULL) AS orphan_catalog_main_groups
            """,
        )[0],
        "unmatched_catalog_products": _rows(
            cursor,
            """
            SELECT cp.Id,cp.CatalogUniqueId,cp.ProductUniqueId,cp.Number_ID,
                   cp.IsRemoved,cp.CreatedDate,cp.LastUpdate
            FROM NGT.CatalogProducts AS cp
            LEFT JOIN GNR.tblGoods AS g ON g.UniqueId=cp.ProductUniqueId
            WHERE g.ID IS NULL
            ORDER BY cp.CatalogUniqueId,cp.OrderOf,cp.Id
            """,
        ),
        "group_counts": _rows(
            cursor,
            """
            SELECT
              (SELECT COUNT_BIG(*) FROM NGT.ProductGroups) AS total_groups,
              (SELECT COUNT_BIG(*) FROM NGT.ProductGroups WHERE IsRemoved=0) AS active_groups,
              (SELECT COUNT_BIG(*) FROM NGT.ProductGroups WHERE ParentUniqueId IS NULL) AS root_groups,
              (SELECT COUNT_BIG(*) FROM NGT.ProductGroups WHERE IsRemoved=0 AND ParentUniqueId IS NULL) AS active_root_groups,
              (SELECT COUNT_BIG(*) FROM NGT.ProductGroups c JOIN NGT.ProductGroups p
                 ON p.Id=c.ParentUniqueId WHERE p.ParentUniqueId IS NOT NULL) AS groups_below_second_level,
              (SELECT COUNT(DISTINCT ProductMainGroupUniqueId) FROM GNR.tblGoods) AS used_main_groups,
              (SELECT COUNT(DISTINCT ProductSubGroupUniqueId) FROM GNR.tblGoods) AS used_sub_groups,
              (SELECT COUNT_BIG(*) FROM NGT.Catalogs) AS total_catalogs,
              (SELECT COUNT_BIG(*) FROM NGT.Catalogs WHERE IsRemoved=0 AND IsActive=1) AS active_catalogs
            """,
        )[0],
        "main_group_usage": _decode_fields(
            _rows(
                cursor,
                """
                SELECT n.Id,CONVERT(varbinary(max),n.ProductGroupName) AS ProductGroupName,
                       n.IsRemoved,COUNT_BIG(g.ID) AS goods_count
                FROM NGT.ProductGroups AS n
                LEFT JOIN GNR.tblGoods AS g ON g.ProductMainGroupUniqueId=n.Id
                WHERE n.ParentUniqueId IS NULL
                GROUP BY n.Id,n.ProductGroupName,n.IsRemoved
                ORDER BY goods_count DESC,n.Id
                """,
            ),
            ("ProductGroupName",),
        ),
        "brand_main_group_pairs": _decode_fields(
            _rows(
                cursor,
                """
                SELECT g.BrandRef,CONVERT(varbinary(max),b.BrandName) AS BrandName,
                       g.ProductMainGroupUniqueId,
                       CONVERT(varbinary(max),n.ProductGroupName) AS ProductMainGroupName,
                       COUNT_BIG(*) AS goods_count
                FROM GNR.tblGoods AS g
                JOIN GNR.tblBrand AS b ON b.id=g.BrandRef
                JOIN NGT.ProductGroups AS n ON n.Id=g.ProductMainGroupUniqueId
                GROUP BY g.BrandRef,b.BrandName,g.ProductMainGroupUniqueId,n.ProductGroupName
                ORDER BY goods_count DESC,g.BrandRef,g.ProductMainGroupUniqueId
                """,
            ),
            ("BrandName", "ProductMainGroupName"),
        ),
        "sub_group_usage": _decode_fields(
            _rows(
                cursor,
                """
                SELECT n.Id,CONVERT(varbinary(max),n.ProductGroupName) AS ProductGroupName,
                       n.ParentUniqueId,n.IsRemoved,COUNT_BIG(g.ID) AS goods_count
                FROM NGT.ProductGroups AS n
                LEFT JOIN GNR.tblGoods AS g ON g.ProductSubGroupUniqueId=n.Id
                WHERE n.ParentUniqueId IS NOT NULL
                GROUP BY n.Id,n.ProductGroupName,n.ParentUniqueId,n.IsRemoved
                ORDER BY goods_count DESC,n.Id
                """,
            ),
            ("ProductGroupName",),
        ),
    }


def _business_date_activity(cursor: Any) -> dict[str, Any]:
    activity = _decode_fields(
        _rows(
            cursor,
            f"""
            WITH order_use AS (
              SELECT i.GoodsRef,COUNT_BIG(*) AS order_line_count,
                     SUM(CONVERT(decimal(28,6),i.OrderTotalQty)) AS ordered_qty
              FROM SLE.tblOrderItm AS i
              JOIN SLE.tblOrderHdr AS h ON h.ID=i.HdrRef
              WHERE h.OrderDate>='{BUSINESS_DATE_FROM}' AND h.OrderDate<='{BUSINESS_DATE_TO}'
                AND ISNULL(i.IsDeleted,0)=0
              GROUP BY i.GoodsRef
            ), sale_use AS (
              SELECT i.GoodsRef,COUNT_BIG(*) AS sale_line_count,
                     SUM(CONVERT(decimal(28,6),i.TotalQty)) AS sold_qty
              FROM SLE.tblSaleItm AS i
              JOIN SLE.tblSaleHdr AS h ON h.ID=i.HdrRef
              WHERE h.SaleDate>='{BUSINESS_DATE_FROM}' AND h.SaleDate<='{BUSINESS_DATE_TO}'
                AND ISNULL(i.IsDeleted,0)=0
              GROUP BY i.GoodsRef
            ), inventory_use AS (
              SELECT i.GoodsRef,COUNT_BIG(*) AS inventory_line_count,
                     SUM(CONVERT(decimal(28,6),i.TotalQty)) AS inventory_qty
              FROM inv.tblVocherItm AS i
              JOIN inv.tblVocherHdr AS h ON h.ID=i.HdrRef
              WHERE h.VocherDate>='{BUSINESS_DATE_FROM}' AND h.VocherDate<='{BUSINESS_DATE_TO}'
              GROUP BY i.GoodsRef
            )
            SELECT g.ID,g.GoodsCode,CONVERT(varbinary(max),g.GoodsName) AS GoodsName,
                   ISNULL(o.order_line_count,0) AS order_line_count,o.ordered_qty,
                   ISNULL(s.sale_line_count,0) AS sale_line_count,s.sold_qty,
                   ISNULL(v.inventory_line_count,0) AS inventory_line_count,v.inventory_qty
            FROM GNR.tblGoods AS g
            LEFT JOIN order_use AS o ON o.GoodsRef=g.ID
            LEFT JOIN sale_use AS s ON s.GoodsRef=g.ID
            LEFT JOIN inventory_use AS v ON v.GoodsRef=g.ID
            WHERE o.GoodsRef IS NOT NULL OR s.GoodsRef IS NOT NULL OR v.GoodsRef IS NOT NULL
            ORDER BY order_line_count DESC,sale_line_count DESC,inventory_line_count DESC,g.ID
            """,
        ),
        ("GoodsName",),
    )
    active_ids = {row["ID"] for row in activity}
    goods_flags = _rows(cursor, "SELECT ID,ShowInSale FROM GNR.tblGoods")
    return {
        "basis": "Persian business dates; master ModifiedDate/LastUpdate is not transaction activity",
        "from": BUSINESS_DATE_FROM,
        "to": BUSINESS_DATE_TO,
        "active_goods": activity,
        "summary": {
            "distinct_active_goods": len(activity),
            "goods_with_orders": sum(1 for row in activity if row["order_line_count"] > 0),
            "goods_with_sales": sum(1 for row in activity if row["sale_line_count"] > 0),
            "goods_with_inventory": sum(1 for row in activity if row["inventory_line_count"] > 0),
            "order_lines": sum(row["order_line_count"] for row in activity),
            "sale_lines": sum(row["sale_line_count"] for row in activity),
            "inventory_lines": sum(row["inventory_line_count"] for row in activity),
            "goods_without_any_activity": sum(1 for row in goods_flags if row["ID"] not in active_ids),
            "show_in_sale_without_activity": sum(
                1 for row in goods_flags if row["ShowInSale"] == 1 and row["ID"] not in active_ids
            ),
            "not_show_in_sale_but_active": sum(
                1 for row in goods_flags if row["ShowInSale"] != 1 and row["ID"] in active_ids
            ),
        },
        "master_changes_90d": _rows(
            cursor,
            """
            SELECT 'GNR.tblGoods.ModifiedDate' AS source,COUNT_BIG(*) AS changed_90d
              FROM GNR.tblGoods WHERE ModifiedDate>=DATEADD(day,-90,SYSDATETIME())
            UNION ALL SELECT 'NGT.ProductGroups.LastUpdate',COUNT_BIG(*)
              FROM NGT.ProductGroups WHERE LastUpdate>=DATEADD(day,-90,SYSDATETIME())
            UNION ALL SELECT 'NGT.Catalogs.LastUpdate',COUNT_BIG(*)
              FROM NGT.Catalogs WHERE LastUpdate>=DATEADD(day,-90,SYSDATETIME())
            UNION ALL SELECT 'NGT.CatalogProducts.LastUpdate',COUNT_BIG(*)
              FROM NGT.CatalogProducts WHERE LastUpdate>=DATEADD(day,-90,SYSDATETIME())
            """,
        ),
    }


def _data_quality(cursor: Any) -> dict[str, Any]:
    referential = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g LEFT JOIN GNR.tblGoodsGroup x
             ON x.ID=g.GoodsGroupRef WHERE x.ID IS NULL) AS orphan_goods_groups,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g LEFT JOIN GNR.tblBrand x
             ON x.id=g.BrandRef WHERE x.id IS NULL) AS orphan_goods_brands,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g LEFT JOIN GNR.tblManufacturer x
             ON x.Id=g.ManufacturerRef WHERE g.ManufacturerRef IS NOT NULL AND x.Id IS NULL) AS orphan_goods_manufacturers,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g LEFT JOIN GNR.tblGoodsType x
             ON x.Id=g.GoodsTypeRef WHERE x.Id IS NULL) AS orphan_goods_types,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsGroup g LEFT JOIN GNR.tblGoodsGroup p
             ON p.ID=g.ParentRef WHERE g.ParentRef IS NOT NULL AND p.ID IS NULL) AS orphan_legacy_group_parents,
          (SELECT COUNT_BIG(*) FROM GNR.tblSubType s LEFT JOIN GNR.tblMainType m
             ON m.Id=s.MainTypeRef WHERE m.Id IS NULL) AS orphan_subtype_main_types,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsMainSubType x LEFT JOIN GNR.tblGoods g
             ON g.ID=x.GoodsRef WHERE g.ID IS NULL) AS orphan_classification_goods,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsMainSubType x LEFT JOIN GNR.tblMainType m
             ON m.Id=x.MainTypeRef WHERE m.Id IS NULL) AS orphan_classification_main_types,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsMainSubType x LEFT JOIN GNR.tblSubType s
             ON s.Id=x.SubTypeRef WHERE s.Id IS NULL) AS orphan_classification_sub_types,
          (SELECT COUNT_BIG(*) FROM GNR.tblPackage p LEFT JOIN GNR.tblGoods g
             ON g.ID=p.GoodsRef WHERE g.ID IS NULL) AS orphan_package_goods,
          (SELECT COUNT_BIG(*) FROM GNR.tblPackage p LEFT JOIN GNR.tblUnit u
             ON u.ID=p.UnitRef WHERE u.ID IS NULL) AS orphan_package_units,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsBarcode b LEFT JOIN GNR.tblGoods g
             ON g.ID=b.GoodsRef WHERE g.ID IS NULL) AS orphan_additional_barcode_goods,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsSupplier x LEFT JOIN GNR.tblGoods g
             ON g.ID=x.GoodsRef WHERE g.ID IS NULL) AS orphan_goods_supplier_goods,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsSupplier x LEFT JOIN GNR.tblSupplier s
             ON s.Id=x.SupplierRef WHERE s.Id IS NULL) AS orphan_goods_supplier_suppliers,
          (SELECT COUNT_BIG(*) FROM SLE.tblGoodsPackageItem x LEFT JOIN SLE.tblGoodsPackage p
             ON p.Id=x.GoodsPackageRef WHERE p.Id IS NULL) AS orphan_promotional_package_headers,
          (SELECT COUNT_BIG(*) FROM SLE.tblGoodsPackageItem x LEFT JOIN GNR.tblGoods g
             ON g.ID=x.GoodsRef WHERE g.ID IS NULL) AS orphan_promotional_package_goods
        """,
    )[0]
    duplicates = _rows(
        cursor,
        """
        SELECT 'goods_code' AS check_name,COUNT_BIG(*) AS duplicate_groups FROM (
          SELECT GoodsCode FROM GNR.tblGoods GROUP BY GoodsCode HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'goods_uuid',COUNT_BIG(*) FROM (
          SELECT UniqueId FROM GNR.tblGoods WHERE UniqueId IS NOT NULL GROUP BY UniqueId HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'goods_group_uuid',COUNT_BIG(*) FROM (
          SELECT UniqueId FROM GNR.tblGoodsGroup WHERE UniqueId IS NOT NULL GROUP BY UniqueId HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'brand_name',COUNT_BIG(*) FROM (
          SELECT BrandName FROM GNR.tblBrand GROUP BY BrandName HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'manufacturer_code',COUNT_BIG(*) FROM (
          SELECT ManufacturerCode FROM GNR.tblManufacturer GROUP BY ManufacturerCode HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'classification_triplet',COUNT_BIG(*) FROM (
          SELECT GoodsRef,MainTypeRef,SubTypeRef FROM GNR.tblGoodsMainSubType
          GROUP BY GoodsRef,MainTypeRef,SubTypeRef HAVING COUNT_BIG(*)>1
        ) d
        """,
    )
    hierarchy = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsGroup WHERE ParentRef IS NULL) AS root_groups,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsGroup WHERE NLeft>=NRight) AS invalid_nested_set_bounds,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsGroup c JOIN GNR.tblGoodsGroup p
             ON p.ID=c.ParentRef
             WHERE NOT (p.NLeft<c.NLeft AND p.NRight>c.NRight)) AS parent_interval_mismatches,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsGroup c JOIN GNR.tblGoodsGroup p
             ON p.ID=c.ParentRef
             WHERE c.NLevel<>p.NLevel+1) AS parent_level_mismatches,
          (SELECT COUNT_BIG(*) FROM (
             SELECT NLeft FROM GNR.tblGoodsGroup GROUP BY NLeft HAVING COUNT_BIG(*)>1
           ) d) AS duplicate_left_values,
          (SELECT COUNT_BIG(*) FROM (
             SELECT NRight FROM GNR.tblGoodsGroup GROUP BY NRight HAVING COUNT_BIG(*)>1
           ) d) AS duplicate_right_values,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsMainSubType) AS classification_rows,
          (SELECT COUNT(DISTINCT GoodsRef) FROM GNR.tblGoodsMainSubType) AS classified_goods,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoodsMainSubType x LEFT JOIN GNR.tblGoods g
             ON g.ID=x.GoodsRef WHERE g.ID IS NULL) AS stale_classification_rows,
          (SELECT COUNT(DISTINCT x.GoodsRef) FROM GNR.tblGoodsMainSubType x LEFT JOIN GNR.tblGoods g
             ON g.ID=x.GoodsRef WHERE g.ID IS NULL) AS distinct_missing_classification_goods,
          (SELECT COUNT_BIG(*) FROM GNR.tblGoods g LEFT JOIN GNR.tblGoodsMainSubType x
             ON x.GoodsRef=g.ID WHERE x.Id IS NULL) AS goods_without_main_sub_classification
        """,
    )[0]
    return {
        "referential_integrity": referential,
        "duplicate_key_groups": duplicates,
        "legacy_hierarchy": hierarchy,
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
            "domain": "product_catalog",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata, aggregates, and non-sensitive product master data",
            },
            "safety": safety,
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "legacy_masters": _legacy_masters(cursor),
            "goods": _goods_snapshot(cursor),
            "goods_master_usage": _goods_master_usage(cursor),
            "packaging_and_barcodes": _packaging_and_barcodes(cursor),
            "ngt_catalog": _ngt_catalog_snapshot(cursor),
            "business_date_activity": _business_date_activity(cursor),
            "data_quality": _data_quality(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() AS captured_at")[0],
            "evidence_limits": [
                "GNR GoodsGroupRef and NGT UUID group references are parallel classifications, not interchangeable IDs.",
                "NGT CatalogProducts.Number_ID does not match GNR.tblGoods.ID in the current snapshot.",
                "GNR.tblPackage is a product-unit conversion master; SLE.tblGoodsPackage is a promotional/discount bundle.",
                "Barcode uniqueness must be reconciled across goods, package, GTIN, and additional-barcode surfaces.",
                "Three-month product activity uses Persian business dates and does not treat master LastUpdate as sales activity.",
                "Formal dependencies do not capture dynamic SQL or every UUID and Ref/Id convention.",
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
