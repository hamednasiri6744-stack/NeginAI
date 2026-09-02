"""Extract Varanegar order-to-sale lifecycle evidence from the read-only clone.

The extractor persists schema, non-personal reference labels, lifecycle counts,
cross-system identifiers, and module definitions.  It intentionally excludes
customer/personnel rows, free-text comments, addresses, usernames, and secrets.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE, SERVER, _assert_safe_target, _connect, _decode_fields,
    _json_default, _rows, _table_metadata,
)


DOMAIN_TABLES: tuple[dict[str, str], ...] = (
    {"object": "SLE.tblOrderType", "role": "order_type_master"},
    {"object": "SLE.tblOrderHdr", "role": "sales_order_header"},
    {"object": "SLE.tblOrderItm", "role": "sales_order_line"},
    {"object": "SLE.tblOrderHdrCustPathInfo", "role": "order_route_snapshot"},
    {"object": "SLE.tblOrderToSaleTime", "role": "order_conversion_attempt_timing"},
    {"object": "SLE.tblOrderPrize", "role": "order_prize_snapshot"},
    {"object": "SLE.tblSaleHdr", "role": "sale_or_voucher_header"},
    {"object": "SLE.tblSaleItm", "role": "sale_or_voucher_line"},
    {"object": "SLE.tblSaleHdrDetail", "role": "sale_customer_and_calculation_snapshot"},
    {"object": "SLE.tblSaleVocherHdr", "role": "immutable_sale_voucher_header_snapshot"},
    {"object": "SLE.tblSaleVocherItm", "role": "immutable_sale_voucher_line_snapshot"},
    {"object": "SLE.tblSaleDistHist", "role": "sale_distribution_history"},
    {"object": "NGT.CustomerCallOrders", "role": "ngt_order_header"},
    {"object": "NGT.CustomerCallOrderLines", "role": "ngt_order_line"},
    {"object": "NGT.CustomerCallOrderLineOrderQtyDetails", "role": "ngt_requested_unit_quantity"},
    {"object": "NGT.CustomerCallOrderLineInvoiceQtyDetails", "role": "ngt_invoiced_unit_quantity"},
    {"object": "NGT.CustomerCallOrderStatus", "role": "ngt_legacy_order_status_event"},
)

BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"


def _object_ids_sql() -> str:
    return ",".join(f"OBJECT_ID(N'{item['object']}', 'U')" for item in DOMAIN_TABLES)


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    ids = _object_ids_sql()
    return _rows(cursor, f"""
        SELECT fk.name AS constraint_name,
               OBJECT_SCHEMA_NAME(fk.parent_object_id) AS parent_schema,
               OBJECT_NAME(fk.parent_object_id) AS parent_table,pc.name AS parent_column,
               OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS referenced_schema,
               OBJECT_NAME(fk.referenced_object_id) AS referenced_table,rc.name AS referenced_column,
               fk.delete_referential_action_desc AS on_delete,
               fk.update_referential_action_desc AS on_update,
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
        SELECT DISTINCT OBJECT_SCHEMA_NAME(d.referencing_id) AS consumer_schema,
               OBJECT_NAME(d.referencing_id) AS consumer_name,o.type_desc AS consumer_type,
               OBJECT_SCHEMA_NAME(d.referenced_id) AS source_schema,
               OBJECT_NAME(d.referenced_id) AS source_table,
               d.is_schema_bound_reference,o.modify_date AS consumer_modify_date
        FROM sys.sql_expression_dependencies d JOIN sys.objects o ON o.object_id=d.referencing_id
        WHERE d.referenced_id IN ({ids})
        ORDER BY source_schema,source_table,consumer_schema,consumer_name
    """)


def _implicit_link_candidates(cursor: Any) -> list[dict[str, Any]]:
    ids = _object_ids_sql()
    return _rows(cursor, f"""
        WITH candidates AS (
          SELECT c.object_id,c.column_id,s.name schema_name,t.name table_name,
                 c.name column_name,TYPE_NAME(c.user_type_id) data_type
          FROM sys.columns c JOIN sys.tables t ON t.object_id=c.object_id
          JOIN sys.schemas s ON s.schema_id=t.schema_id
          WHERE LOWER(c.name) LIKE '%orderref%' OR LOWER(c.name) LIKE '%orderid%'
             OR LOWER(c.name) LIKE '%orderuniqueid%' OR LOWER(c.name) LIKE '%saleref%'
             OR LOWER(c.name) LIKE '%saleid%' OR LOWER(c.name) LIKE '%saleuniqueid%'
             OR LOWER(c.name) LIKE '%itemref%' OR LOWER(c.name) LIKE '%lineuniqueid%'
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
    order_types = _decode_fields(_rows(cursor, """
        SELECT ID,CONVERT(varbinary(max),Title) Title,Selectable,IsDefault,UniqueId,
               OrderTypeSerialType,SLId,IsFreeInvoice,DontCheckMojodi,
               EffectOrderOnStockGoods
        FROM SLE.tblOrderType ORDER BY ID
    """), ("Title",))
    lookups = _decode_fields(_rows(cursor, """
        SELECT CodeType,Code,CONVERT(varbinary(max),Title) Title,Value1,Value2
        FROM GNR.tblLookup WHERE CodeType IN (6,7,25)
        ORDER BY CodeType,Code
    """), ("Title",))
    return {
        "order_types": order_types,
        "discount_calculation_types": [x for x in lookups if x["CodeType"] == 6],
        "sale_statuses": [x for x in lookups if x["CodeType"] == 7],
        "order_line_statuses": [x for x in lookups if x["CodeType"] == 25],
    }


def _order_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) total_orders,COUNT(DISTINCT UniqueId) distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuids,
               SUM(CASE WHEN CancelFlag=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN CancelFlag<>0 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirmed,
               SUM(CASE WHEN SaleHdrRef IS NOT NULL THEN 1 ELSE 0 END) selected_sale_link,
               SUM(CASE WHEN CustomerCallOrderId IS NOT NULL THEN 1 ELSE 0 END) customer_call_numeric_link,
               SUM(CASE WHEN ImportFromExcel=1 THEN 1 ELSE 0 END) excel_import,
               SUM(CASE WHEN POrderId IS NOT NULL THEN 1 ELSE 0 END) porder_link
        FROM SLE.tblOrderHdr
    """)[0]
    lifecycle = _rows(cursor, """
        SELECT CASE WHEN o.CancelFlag<>0 THEN 'order_cancelled'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.CancelFlag<>0 THEN 'selected_sale_cancelled'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.SaleNo IS NOT NULL THEN 'active_final_sale'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.SaleNo IS NULL THEN 'active_sale_voucher'
                    WHEN o.ConfirmDate IS NOT NULL THEN 'confirmed_no_sale'
                    ELSE 'unconfirmed_no_sale' END lifecycle_state,
               COUNT_BIG(*) orders
        FROM SLE.tblOrderHdr o LEFT JOIN SLE.tblSaleHdr s ON s.ID=o.SaleHdrRef
        GROUP BY CASE WHEN o.CancelFlag<>0 THEN 'order_cancelled'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.CancelFlag<>0 THEN 'selected_sale_cancelled'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.SaleNo IS NOT NULL THEN 'active_final_sale'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.SaleNo IS NULL THEN 'active_sale_voucher'
                    WHEN o.ConfirmDate IS NOT NULL THEN 'confirmed_no_sale'
                    ELSE 'unconfirmed_no_sale' END
        ORDER BY orders DESC
    """)
    item_status = _rows(cursor, """
        SELECT IsDeleted,IsUsed,COUNT_BIG(*) lines,COUNT(DISTINCT HdrRef) orders,
               SUM(CASE WHEN SoldQty IS NULL THEN 1 ELSE 0 END) sold_qty_null,
               SUM(CASE WHEN ISNULL(SoldQty,0)=0 THEN 1 ELSE 0 END) sold_qty_zero
        FROM SLE.tblOrderItm GROUP BY IsDeleted,IsUsed ORDER BY lines DESC
    """)
    type_usage = _rows(cursor, """
        SELECT h.OrderType,COUNT_BIG(*) total_orders,
               SUM(CASE WHEN h.CancelFlag<>0 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN h.SaleHdrRef IS NOT NULL THEN 1 ELSE 0 END) selected_sale_link
        FROM SLE.tblOrderHdr h GROUP BY h.OrderType ORDER BY total_orders DESC
    """)
    return {"population": population, "lifecycle_states": lifecycle,
            "line_status_distribution": item_status, "order_type_usage": type_usage}


def _order_route_snapshot(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, f"""
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT p.OrderRef) orders,
               SUM(CASE WHEN p.SalePathRef IS NOT NULL THEN 1 ELSE 0 END) sale_path,
               SUM(CASE WHEN p.SaleAreaRef IS NOT NULL THEN 1 ELSE 0 END) sale_area,
               SUM(CASE WHEN p.SaleZoneRef IS NOT NULL THEN 1 ELSE 0 END) sale_zone,
               SUM(CASE WHEN p.DealerRef IS NOT NULL THEN 1 ELSE 0 END) dealer,
               SUM(CASE WHEN p.AreaRef IS NOT NULL THEN 1 ELSE 0 END) geographic_area,
               (SELECT COUNT_BIG(*) FROM (SELECT OrderRef FROM SLE.tblOrderHdrCustPathInfo
                  GROUP BY OrderRef HAVING COUNT_BIG(*)>1)x) duplicate_order_groups,
               (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdrCustPathInfo x
                  LEFT JOIN SLE.tblOrderHdr o ON o.ID=x.OrderRef WHERE o.ID IS NULL) orphan_orders,
               (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr o
                  LEFT JOIN SLE.tblOrderHdrCustPathInfo x ON x.OrderRef=o.ID
                  WHERE o.OrderDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
                    AND x.OrderRef IS NOT NULL) business_window_orders_with_snapshot,
               (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr o
                  WHERE o.OrderDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}')
                    business_window_orders
        FROM SLE.tblOrderHdrCustPathInfo p
    """)[0]


def _sale_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) total_sales,COUNT(DISTINCT UniqueId) distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuids,
               SUM(CASE WHEN CancelFlag=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN CancelFlag<>0 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN SaleNo IS NOT NULL THEN 1 ELSE 0 END) final_sale_number,
               SUM(CASE WHEN SaleNo IS NULL THEN 1 ELSE 0 END) without_final_sale_number,
               SUM(CASE WHEN SaleVocherNo IS NOT NULL THEN 1 ELSE 0 END) voucher_number,
               SUM(CASE WHEN OrderRef IS NOT NULL THEN 1 ELSE 0 END) order_link,
               SUM(CASE WHEN ExitRef IS NOT NULL THEN 1 ELSE 0 END) exit_link,
               SUM(CASE WHEN DistRef IS NOT NULL THEN 1 ELSE 0 END) distribution_link
        FROM SLE.tblSaleHdr
    """)[0]
    status = _rows(cursor, """
        SELECT Status,CancelFlag,CASE WHEN SaleNo IS NULL THEN 0 ELSE 1 END has_final_sale_number,
               COUNT_BIG(*) sales
        FROM SLE.tblSaleHdr
        GROUP BY Status,CancelFlag,CASE WHEN SaleNo IS NULL THEN 0 ELSE 1 END
        ORDER BY sales DESC
    """)
    relationship = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr o LEFT JOIN SLE.tblSaleHdr s ON s.ID=o.SaleHdrRef
           WHERE o.SaleHdrRef IS NOT NULL AND s.ID IS NULL) orphan_order_selected_sale,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr s LEFT JOIN SLE.tblOrderHdr o ON o.ID=s.OrderRef
           WHERE o.ID IS NULL) orphan_sale_order,
          (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr o JOIN SLE.tblSaleHdr s ON s.ID=o.SaleHdrRef
           WHERE s.OrderRef<>o.ID) selected_sale_reverse_pointer_mismatch,
          (SELECT COUNT_BIG(*) FROM (SELECT OrderRef FROM SLE.tblSaleHdr
             GROUP BY OrderRef HAVING COUNT_BIG(*)>1)x) orders_with_multiple_sale_attempts,
          (SELECT COUNT_BIG(*) FROM (SELECT OrderRef FROM SLE.tblSaleHdr WHERE CancelFlag=0
             GROUP BY OrderRef HAVING COUNT_BIG(*)>1)x) orders_with_multiple_active_sales,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr s JOIN SLE.tblOrderHdr o ON o.ID=s.OrderRef
           WHERE (o.SaleHdrRef IS NULL OR o.SaleHdrRef<>s.ID) AND s.CancelFlag=0) active_sales_not_selected,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr s JOIN SLE.tblOrderHdr o ON o.ID=s.OrderRef
           WHERE (o.SaleHdrRef IS NULL OR o.SaleHdrRef<>s.ID) AND s.CancelFlag<>0) cancelled_sales_not_selected,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr s JOIN SLE.tblOrderHdr o ON o.ID=s.OrderRef
           WHERE o.SaleHdrRef=s.ID AND s.CancelFlag<>0) selected_cancelled_sales
    """)[0]
    voucher_snapshot = _rows(cursor, """
        SELECT (SELECT COUNT_BIG(*) FROM SLE.tblSaleVocherHdr) headers,
               (SELECT COUNT(DISTINCT SaleRef) FROM SLE.tblSaleVocherHdr) sales,
               (SELECT COUNT_BIG(*) FROM SLE.tblSaleVocherItm) lines,
               (SELECT COUNT_BIG(*) FROM SLE.tblSaleVocherHdr v LEFT JOIN SLE.tblSaleHdr s
                 ON s.ID=v.SaleRef WHERE s.ID IS NULL) orphan_sales,
               (SELECT COUNT_BIG(*) FROM (SELECT SaleRef FROM SLE.tblSaleVocherHdr
                 GROUP BY SaleRef HAVING COUNT_BIG(*)>1)x) duplicate_sale_groups
    """)[0]
    return {"population": population, "status_distribution": status,
            "order_sale_relationship": relationship,
            "voucher_snapshot": voucher_snapshot}


def _conversion_timing(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT OrderRef) orders,
               SUM(CASE WHEN StartTime IS NOT NULL THEN 1 ELSE 0 END) has_start,
               SUM(CASE WHEN EndTime IS NOT NULL THEN 1 ELSE 0 END) has_end,
               SUM(CASE WHEN EndTime<StartTime THEN 1 ELSE 0 END) negative_time,
               AVG(CONVERT(float,DATEDIFF(millisecond,StartTime,EndTime))/1000.0) average_seconds,
               MAX(CONVERT(float,DATEDIFF(millisecond,StartTime,EndTime))/1000.0) maximum_seconds,
               SUM(CASE WHEN DATEDIFF(second,StartTime,EndTime)=0 THEN 1 ELSE 0 END) zero_second_rows,
               SUM(CASE WHEN DATEDIFF(second,StartTime,EndTime)>60 THEN 1 ELSE 0 END) over_sixty_seconds,
               (SELECT COUNT_BIG(*) FROM (SELECT OrderRef FROM SLE.tblOrderToSaleTime
                  GROUP BY OrderRef HAVING COUNT_BIG(*)>1)x) orders_with_multiple_attempts
        FROM SLE.tblOrderToSaleTime
    """)[0]


def _sale_detail_history(cursor: Any) -> dict[str, Any]:
    summary = _rows(cursor, """
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT HdrRef) sales,
               SUM(CASE WHEN GoodsGroupTree IS NOT NULL THEN 1 ELSE 0 END) goods_group_snapshots,
               SUM(CASE WHEN GoodsDetail IS NOT NULL THEN 1 ELSE 0 END) goods_snapshots,
               SUM(CASE WHEN GoodsMainSubTypeDetail IS NOT NULL THEN 1 ELSE 0 END) goods_class_snapshots,
               SUM(CASE WHEN CustMainSubTypeDetail IS NOT NULL THEN 1 ELSE 0 END) customer_class_snapshots,
               (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdrDetail d LEFT JOIN SLE.tblSaleHdr h
                  ON h.ID=d.HdrRef WHERE h.ID IS NULL) orphan_sales,
               (SELECT COUNT_BIG(*) FROM (SELECT HdrRef FROM SLE.tblSaleHdrDetail
                  GROUP BY HdrRef HAVING COUNT_BIG(*)>1)x) sales_with_multiple_detail_events,
               (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr h WHERE NOT EXISTS
                  (SELECT 1 FROM SLE.tblSaleHdrDetail d WHERE d.HdrRef=h.ID)) sales_without_detail
        FROM SLE.tblSaleHdrDetail
    """)[0]
    transitions = _rows(cursor, """
        SELECT Status,CancelFlag,CASE WHEN GoodsDetail IS NULL THEN 0 ELSE 1 END has_goods_snapshot,
               COUNT_BIG(*) rows,COUNT(DISTINCT HdrRef) sales
        FROM SLE.tblSaleHdrDetail
        GROUP BY Status,CancelFlag,CASE WHEN GoodsDetail IS NULL THEN 0 ELSE 1 END
        ORDER BY rows DESC
    """)
    return {"summary": summary, "status_event_distribution": transitions}


def _business_window(cursor: Any) -> dict[str, Any]:
    states = _rows(cursor, f"""
        SELECT CASE WHEN o.CancelFlag<>0 THEN 'order_cancelled'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.CancelFlag<>0 THEN 'selected_sale_cancelled'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.SaleNo IS NOT NULL THEN 'active_final_sale'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.SaleNo IS NULL THEN 'active_sale_voucher'
                    WHEN o.ConfirmDate IS NOT NULL THEN 'confirmed_no_sale'
                    ELSE 'unconfirmed_no_sale' END lifecycle_state,
               COUNT_BIG(*) orders
        FROM SLE.tblOrderHdr o LEFT JOIN SLE.tblSaleHdr s ON s.ID=o.SaleHdrRef
        WHERE o.OrderDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
        GROUP BY CASE WHEN o.CancelFlag<>0 THEN 'order_cancelled'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.CancelFlag<>0 THEN 'selected_sale_cancelled'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.SaleNo IS NOT NULL THEN 'active_final_sale'
                    WHEN o.SaleHdrRef IS NOT NULL AND s.SaleNo IS NULL THEN 'active_sale_voucher'
                    WHEN o.ConfirmDate IS NOT NULL THEN 'confirmed_no_sale'
                    ELSE 'unconfirmed_no_sale' END ORDER BY orders DESC
    """)
    types = _rows(cursor, f"""
        SELECT o.OrderType,COUNT_BIG(*) orders,
               SUM(CASE WHEN o.CancelFlag<>0 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN o.SaleHdrRef IS NOT NULL THEN 1 ELSE 0 END) selected_sale_link
        FROM SLE.tblOrderHdr o
        WHERE o.OrderDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
        GROUP BY o.OrderType ORDER BY orders DESC
    """)
    sales = _rows(cursor, f"""
        SELECT COUNT_BIG(*) sales,COUNT(DISTINCT OrderRef) orders,
               SUM(CASE WHEN CancelFlag=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN CancelFlag<>0 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN SaleNo IS NOT NULL THEN 1 ELSE 0 END) final_sale_number,
               SUM(CASE WHEN SaleNo IS NULL THEN 1 ELSE 0 END) voucher_only
        FROM SLE.tblSaleHdr
        WHERE SaleDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
    """)[0]
    return {"basis": "Persian document business dates", "from": BUSINESS_DATE_FROM,
            "to": BUSINESS_DATE_TO, "order_states": states,
            "order_type_usage": types, "sales_by_sale_date": sales}


def _ngt_crosswalk(cursor: Any) -> dict[str, Any]:
    headers = _rows(cursor, """
        SELECT COUNT_BIG(*) total_rows,SUM(CASE WHEN n.IsRemoved=0 THEN 1 ELSE 0 END) active_rows,
               SUM(CASE WHEN n.IsCanceled=1 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN n.IsInvoice=1 THEN 1 ELSE 0 END) invoice_flag,
               SUM(CASE WHEN TRY_CONVERT(int,n.BackOfficeOrderId)=0 THEN 1 ELSE 0 END) zero_order_id,
               SUM(CASE WHEN TRY_CONVERT(int,n.BackOfficeOrderId)>0 THEN 1 ELSE 0 END) positive_order_id,
               SUM(CASE WHEN oid.ID IS NOT NULL THEN 1 ELSE 0 END) order_id_matches,
               SUM(CASE WHEN n.BackOfficeOrderUniqueId IS NULL THEN 1 ELSE 0 END) null_order_uuid,
               SUM(CASE WHEN ou.ID IS NOT NULL THEN 1 ELSE 0 END) order_uuid_matches,
               SUM(CASE WHEN n.BackOfficeInvoiceId IS NULL OR LTRIM(RTRIM(n.BackOfficeInvoiceId))=''
                        THEN 1 ELSE 0 END) blank_invoice_id,
               SUM(CASE WHEN sid.ID IS NOT NULL THEN 1 ELSE 0 END) sale_id_matches,
               SUM(CASE WHEN su.ID IS NOT NULL THEN 1 ELSE 0 END) sale_uuid_matches,
               SUM(CASE WHEN sid.ID=su.ID THEN 1 ELSE 0 END) sale_id_uuid_agree,
               MIN(n.Number_ID) minimum_number_id,MAX(n.Number_ID) maximum_number_id
        FROM NGT.CustomerCallOrders n
        LEFT JOIN SLE.tblOrderHdr oid ON oid.ID=TRY_CONVERT(int,n.BackOfficeOrderId)
        LEFT JOIN SLE.tblOrderHdr ou ON ou.UniqueId=n.BackOfficeOrderUniqueId
        LEFT JOIN SLE.tblSaleHdr sid ON sid.ID=TRY_CONVERT(int,n.BackOfficeInvoiceId)
        LEFT JOIN SLE.tblSaleHdr su ON su.UniqueId=n.BackOfficeInvoiceUniqueId
    """)[0]
    lines = _rows(cursor, """
        SELECT COUNT_BIG(*) total_rows,SUM(CASE WHEN n.IsRemoved=0 THEN 1 ELSE 0 END) active_rows,
               SUM(CASE WHEN g.ID IS NOT NULL THEN 1 ELSE 0 END) product_uuid_matches,
               SUM(CASE WHEN n.PriceUniqueId='00000000-0000-0000-0000-000000000000'
                        THEN 1 ELSE 0 END) zero_price_uuid,
               SUM(CASE WHEN p.ID IS NOT NULL THEN 1 ELSE 0 END) price_history_uuid_matches,
               SUM(CASE WHEN cp0.ID IS NOT NULL THEN 1 ELSE 0 END) price_uuid_matches_contract_price,
               SUM(CASE WHEN n.CPriceUniqueId IS NULL THEN 1 ELSE 0 END) null_contract_price_uuid,
               SUM(CASE WHEN cp.ID IS NOT NULL THEN 1 ELSE 0 END) contract_price_uuid_matches,
               SUM(CASE WHEN n.ItemRef IS NULL THEN 1 ELSE 0 END) null_item_ref,
               SUM(CASE WHEN oi.ID IS NOT NULL THEN 1 ELSE 0 END) item_ref_matches,
               SUM(CASE WHEN oh.ID IS NOT NULL THEN 1 ELSE 0 END) backoffice_order_ref_matches,
               SUM(CASE WHEN ohu.ID IS NOT NULL THEN 1 ELSE 0 END) backoffice_order_uuid_matches,
               SUM(CASE WHEN oh.ID IS NOT NULL AND oh.UniqueId=n.BackOfficeOrderUniqueId
                        THEN 1 ELSE 0 END) order_id_uuid_agree,
               SUM(CASE WHEN n.IsRequestPrizeItem=1 THEN 1 ELSE 0 END) prize_lines,
               SUM(CASE WHEN n.IsRequestFreeItem=1 THEN 1 ELSE 0 END) free_lines
        FROM NGT.CustomerCallOrderLines n
        LEFT JOIN GNR.tblGoods g ON g.UniqueId=n.ProductUniqueId
        LEFT JOIN SLE.tblPrice p ON p.UniqueId=n.PriceUniqueId
        LEFT JOIN SLE.tblCPrice cp0 ON cp0.UniqueId=n.PriceUniqueId
        LEFT JOIN SLE.tblCPrice cp ON cp.UniqueId=n.CPriceUniqueId
        LEFT JOIN SLE.tblOrderItm oi ON oi.ID=n.ItemRef
        LEFT JOIN SLE.tblOrderHdr oh ON oh.ID=n.BackOfficeOrderRef
        LEFT JOIN SLE.tblOrderHdr ohu ON ohu.UniqueId=n.BackOfficeOrderUniqueId
    """)[0]
    parent_mapping = _rows(cursor, """
        SELECT COUNT_BIG(*) ngt_orders_with_lines,
               SUM(CASE WHEN x.matched_lines>0 THEN 1 ELSE 0 END) with_backoffice_line_mapping,
               SUM(CASE WHEN x.matched_lines=x.lines THEN 1 ELSE 0 END) all_lines_mapped,
               (SELECT COUNT_BIG(*) FROM (
                  SELECT CustomerCallOrderUniqueId FROM NGT.CustomerCallOrderLines
                  WHERE BackOfficeOrderRef IS NOT NULL AND BackOfficeOrderRef<>0
                  GROUP BY CustomerCallOrderUniqueId
                  HAVING COUNT(DISTINCT BackOfficeOrderRef)>1)y) ngt_orders_split_to_multiple_backoffice_orders
        FROM (SELECT n.CustomerCallOrderUniqueId,COUNT_BIG(*) lines,
                     SUM(CASE WHEN o.ID IS NOT NULL THEN 1 ELSE 0 END) matched_lines
              FROM NGT.CustomerCallOrderLines n
              LEFT JOIN SLE.tblOrderHdr o ON o.ID=n.BackOfficeOrderRef
              GROUP BY n.CustomerCallOrderUniqueId)x
    """)[0]
    quantities = _rows(cursor, """
        SELECT (SELECT COUNT_BIG(*) FROM NGT.CustomerCallOrderLineOrderQtyDetails) requested_rows,
               (SELECT COUNT_BIG(*) FROM NGT.CustomerCallOrderLineInvoiceQtyDetails) invoiced_rows,
               (SELECT COUNT_BIG(*) FROM NGT.CustomerCallOrderLineOrderQtyDetails q
                 LEFT JOIN NGT.CustomerCallOrderLines l ON l.ID=q.CustomerCallOrderLineUniqueId
                 WHERE l.ID IS NULL) orphan_requested_lines,
               (SELECT COUNT_BIG(*) FROM NGT.CustomerCallOrderLineInvoiceQtyDetails q
                 LEFT JOIN NGT.CustomerCallOrderLines l ON l.ID=q.CustomerCallOrderLineUniqueId
                 WHERE l.ID IS NULL) orphan_invoiced_lines
    """)[0]
    return {"headers": headers, "lines": lines,
            "parent_line_mapping": parent_mapping, "unit_quantity_details": quantities}


def _data_quality(cursor: Any) -> dict[str, Any]:
    duplicate_keys = _rows(cursor, """
        SELECT 'order_uuid' check_name,COUNT_BIG(*) duplicate_groups FROM (
          SELECT UniqueId FROM SLE.tblOrderHdr GROUP BY UniqueId HAVING COUNT_BIG(*)>1)x
        UNION ALL SELECT 'sale_uuid',COUNT_BIG(*) FROM (
          SELECT UniqueId FROM SLE.tblSaleHdr GROUP BY UniqueId HAVING COUNT_BIG(*)>1)x
        UNION ALL SELECT 'order_no_global',COUNT_BIG(*) FROM (
          SELECT OrderNo FROM SLE.tblOrderHdr GROUP BY OrderNo HAVING COUNT_BIG(*)>1)x
        UNION ALL SELECT 'order_no_year_dc',COUNT_BIG(*) FROM (
          SELECT AccYear,DCRef,OrderNo FROM SLE.tblOrderHdr GROUP BY AccYear,DCRef,OrderNo HAVING COUNT_BIG(*)>1)x
        UNION ALL SELECT 'sale_no_global',COUNT_BIG(*) FROM (
          SELECT SaleNo FROM SLE.tblSaleHdr WHERE SaleNo IS NOT NULL GROUP BY SaleNo HAVING COUNT_BIG(*)>1)x
        UNION ALL SELECT 'sale_no_year_dc',COUNT_BIG(*) FROM (
          SELECT AccYear,DCRef,SaleNo FROM SLE.tblSaleHdr WHERE SaleNo IS NOT NULL
          GROUP BY AccYear,DCRef,SaleNo HAVING COUNT_BIG(*)>1)x
        UNION ALL SELECT 'voucher_no_year_dc',COUNT_BIG(*) FROM (
          SELECT AccYear,DCRef,SaleVocherNo FROM SLE.tblSaleHdr WHERE SaleVocherNo IS NOT NULL
          GROUP BY AccYear,DCRef,SaleVocherNo HAVING COUNT_BIG(*)>1)x
        UNION ALL SELECT 'order_line_number',COUNT_BIG(*) FROM (
          SELECT HdrRef,RowOrder FROM SLE.tblOrderItm WHERE IsDeleted=0
          GROUP BY HdrRef,RowOrder HAVING COUNT_BIG(*)>1)x
        UNION ALL SELECT 'sale_line_number',COUNT_BIG(*) FROM (
          SELECT HdrRef,RowOrder FROM SLE.tblSaleItm WHERE IsDeleted=0
          GROUP BY HdrRef,RowOrder HAVING COUNT_BIG(*)>1)x
    """)
    orphans = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM SLE.tblOrderItm i LEFT JOIN SLE.tblOrderHdr h ON h.ID=i.HdrRef
           WHERE h.ID IS NULL) orphan_order_lines,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleItm i LEFT JOIN SLE.tblSaleHdr h ON h.ID=i.HdrRef
           WHERE h.ID IS NULL) orphan_sale_lines,
          (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr h LEFT JOIN GNR.tblCust c ON c.ID=h.CustRef
           WHERE c.ID IS NULL) orphan_order_customers,
          (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr h LEFT JOIN dbo.Personnel p ON p.PersonnelId=h.DealerRef
           WHERE p.PersonnelId IS NULL) orphan_order_dealers,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr h LEFT JOIN GNR.tblCust c ON c.ID=h.CustRef
           WHERE c.ID IS NULL) orphan_sale_customers,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr h LEFT JOIN dbo.Personnel p ON p.PersonnelId=h.DealerRef
           WHERE p.PersonnelId IS NULL) orphan_sale_dealers
    """)[0]
    return {"duplicate_key_groups": duplicate_keys, "referential_integrity": orphans}


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition,o.modify_date
        FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE (s.name='FRU' AND o.name IN
              ('OrderModel','OrderHdrModel','OrderItmModel','SaleHdrModel',
               'SaleHistoryModel','SaleVocherHdrModel','CustomerCallOrdersModel'))
           OR (s.name='SLE' AND o.name IN ('usp_FillEVCByOrder','usp_DoEVC'))
           OR (s.name='dbo' AND o.name IN
              ('NGT_ReplicateOrderMaster','NGT_CreateOrderAndSale','NGT_CreateSale'))
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
            "domain": "order_to_sale_lifecycle",
            "scope": {"server": SERVER, "database": DATABASE,
                      "mode": "read-only metadata and aggregate lifecycle evidence",
                      "privacy_policy": "no customer/personnel rows, comments, addresses, usernames, or credentials"},
            "safety": safety,
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "reference_masters": _reference_masters(cursor),
            "orders": _order_profile(cursor),
            "order_route_snapshot": _order_route_snapshot(cursor),
            "sales": _sale_profile(cursor),
            "sale_detail_history": _sale_detail_history(cursor),
            "conversion_timing": _conversion_timing(cursor),
            "business_window": _business_window(cursor),
            "ngt_crosswalk": _ngt_crosswalk(cursor),
            "data_quality": _data_quality(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "evidence_limits": [
                "ConfirmDate is a stored state marker; aggregate prevalence does not prove a human approval step.",
                "An order can retain multiple cancelled sale attempts while selecting at most one active sale.",
                "SaleNo NULL and SaleVocherNo populated represent a distinct voucher-stage state, not a missing number error.",
                "NGT header and line crosswalk fields have different coverage and must not be collapsed into one identifier.",
                "NGT PriceUniqueId is historically polymorphic across price history, contract price, and zero sentinel.",
                "Conversion timing rows measure execution attempts, not end-to-end customer lead time.",
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
