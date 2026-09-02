"""Extract Varanegar sales-return, stock-return, and credit-settlement evidence.

This extractor is read-only.  It stores schema metadata, safe Persian reference
labels, aggregate counts, reconciliation results, and selected SQL contracts.
It never stores customer/personnel rows, comments, usernames, hostnames,
credentials, raw invoice/payment records, or document identifiers.
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
    {"object": "SLE.tblRetCause", "role": "return_reason_master"},
    {"object": "SLE.tblRetSaleHdr", "role": "sales_return_header"},
    {"object": "SLE.tblRetSaleItm", "role": "sales_return_item"},
    {"object": "SLE.tblRetSaleItmDisAcc", "role": "return_item_discount_account_split"},
    {"object": "SLE.tblRetOrderHdr", "role": "return_request_header"},
    {"object": "SLE.tblRetOrderItm", "role": "return_request_item"},
    {"object": "SLE.tblRetSaleHdr_RD", "role": "distribution_return_staging_header"},
    {"object": "SLE.tblRetSaleItm_RD", "role": "distribution_return_staging_item"},
    {"object": "INV.tblVocherHdr", "role": "inventory_voucher_header"},
    {"object": "INV.tblVocherItm", "role": "inventory_voucher_item"},
    {"object": "Acc.tblPayments", "role": "return_credit_allocation_ledger"},
    {"object": "dbo.tblPayWithPaymentRelation", "role": "payment_pair_relation"},
    {"object": "NGT.CustomerCallReturns", "role": "mobile_return_header"},
    {"object": "NGT.CustomerCallReturnLines", "role": "mobile_return_line"},
    {"object": "NGT.CustomerCallReturnLineQtyDetails", "role": "mobile_return_quantity_detail"},
    {"object": "NGT.CustomerCallReturnLineRequestQtyDetails", "role": "mobile_return_request_quantity_detail"},
)

BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"


def _object_ids_sql() -> str:
    return ",".join(f"OBJECT_ID(N'{x['object']}', 'U')" for x in DOMAIN_TABLES)


def _public_safety(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_is_local": True,
        "database_name": context["database_name"],
        "expected_analysis_login_verified": True,
        "updateability": context["updateability"],
        "can_select": context["can_select"],
        "can_view_definition": context["can_view_definition"],
        "can_update": context["can_update"],
        "denies_data_writes": context["denies_data_writes"],
    }


def _public_table_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Drop audit-identity columns from persisted schema metadata."""
    excluded = {"sqlusername", "winusername", "hostname", "applicationname", "comment"}
    result = dict(metadata)
    result["columns"] = [
        column
        for column in metadata.get("columns", [])
        if str(column.get("column_name", "")).lower() not in excluded
    ]
    result["redacted_column_count"] = len(metadata.get("columns", [])) - len(result["columns"])
    return result


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
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id
                           AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id
                           AND rc.column_id=fkc.referenced_column_id
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
          WHERE LOWER(c.name) LIKE '%retsaleref%'
             OR LOWER(c.name) LIKE '%retorderref%'
             OR LOWER(c.name) LIKE '%returninvoice%'
             OR LOWER(c.name) LIKE '%returnorder%'
             OR LOWER(c.name) LIKE '%customercallreturn%'
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
    lookups = _decode_fields(_rows(cursor, """
        SELECT CodeType,Code,CONVERT(varbinary(max),Title) Title,Value1,Value2
        FROM GNR.tblLookup WHERE CodeType IN (10,17,1003,1004)
        ORDER BY CodeType,Code
    """), ("Title",))
    causes = _decode_fields(_rows(cursor, """
        SELECT c.ID,CONVERT(varbinary(max),c.Name) Name,c.IsActive,
               c.ShowFollowUpSale,c.ShowRetSale,c.ShowForNgt,
               COUNT_BIG(h.ID) header_usage,
               SUM(CASE WHEN h.CancelFlag=0 THEN 1 ELSE 0 END) active_header_usage
        FROM SLE.tblRetCause c
        LEFT JOIN SLE.tblRetSaleHdr h ON h.RetCauseRef=c.ID
        GROUP BY c.ID,c.Name,c.IsActive,c.ShowFollowUpSale,c.ShowRetSale,c.ShowForNgt
        ORDER BY header_usage DESC,c.ID
    """), ("Name",))
    return {
        "lookup_sets": lookups,
        "lookup_code_types": {
            "10": "sales_return_health",
            "17": "sales_return_type",
            "1003": "return_request_type",
            "1004": "return_request_health",
        },
        "return_causes": causes,
    }


def _header_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) returns,COUNT(DISTINCT UniqueId) distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuids,
               SUM(CASE WHEN CancelFlag=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN CancelFlag=1 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN IsNew=1 THEN 1 ELSE 0 END) new_semantics,
               SUM(CASE WHEN ISNULL(IsNew,0)=0 THEN 1 ELSE 0 END) legacy_semantics,
               SUM(CASE WHEN RetOrderRef IS NOT NULL THEN 1 ELSE 0 END) request_linked,
               SUM(CASE WHEN TSaleRef IS NOT NULL THEN 1 ELSE 0 END) source_sale_linked,
               SUM(CASE WHEN SaleSettlementRef IS NOT NULL THEN 1 ELSE 0 END)
                    settlement_sale_linked,
               SUM(CASE WHEN DistRef IS NOT NULL THEN 1 ELSE 0 END) distribution_linked,
               SUM(CASE WHEN CustomerCallReturnId IS NOT NULL THEN 1 ELSE 0 END)
                    fru_mobile_linked,
               SUM(CASE WHEN FreeInvoiceHdrRef IS NOT NULL THEN 1 ELSE 0 END)
                    free_invoice_linked,
               MIN(RetSaleDate) minimum_business_date,MAX(RetSaleDate) maximum_business_date
        FROM SLE.tblRetSaleHdr
    """)[0]
    workflow = _rows(cursor, """
        SELECT RetTypeCode,HealthCode,CancelFlag,COUNT_BIG(*) returns,
               SUM(CASE WHEN TSaleRef IS NOT NULL THEN 1 ELSE 0 END) source_sale_linked,
               SUM(CASE WHEN SaleSettlementRef IS NOT NULL THEN 1 ELSE 0 END)
                    settlement_sale_linked,
               SUM(CASE WHEN RetOrderRef IS NOT NULL THEN 1 ELSE 0 END) request_linked
        FROM SLE.tblRetSaleHdr
        GROUP BY RetTypeCode,HealthCode,CancelFlag
        ORDER BY returns DESC,RetTypeCode,HealthCode,CancelFlag
    """)
    window = _rows(cursor, f"""
        SELECT COUNT_BIG(*) returns,
               SUM(CASE WHEN CancelFlag=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN CancelFlag=1 THEN 1 ELSE 0 END) cancelled,
               COUNT(DISTINCT CustRef) customers,COUNT(DISTINCT DealerRef) dealers,
               COUNT(DISTINCT RetCauseRef) causes,
               SUM(CASE WHEN TSaleRef IS NOT NULL THEN 1 ELSE 0 END) source_sale_linked
        FROM SLE.tblRetSaleHdr
        WHERE RetSaleDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
    """)[0]
    keys = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM (SELECT UniqueId FROM SLE.tblRetSaleHdr
             WHERE UniqueId IS NOT NULL GROUP BY UniqueId HAVING COUNT_BIG(*)>1)x)
                duplicate_uuid_groups,
          (SELECT COUNT_BIG(*) FROM (SELECT AccYear,DCRef,DCSaleOfficeRef,RetSaleNo
             FROM SLE.tblRetSaleHdr GROUP BY AccYear,DCRef,DCSaleOfficeRef,RetSaleNo
             HAVING COUNT_BIG(*)>1)x) duplicate_business_key_groups,
          (SELECT COUNT_BIG(*) FROM SLE.tblRetSaleHdr WHERE RetSaleNo=0)
                zero_return_numbers
    """)[0]
    links = _rows(cursor, """
        SELECT COUNT_BIG(*) returns,
               SUM(CASE WHEN h.TSaleRef IS NOT NULL AND src.ID IS NULL THEN 1 ELSE 0 END)
                    orphan_source_sale,
               SUM(CASE WHEN h.SaleSettlementRef IS NOT NULL AND settle.ID IS NULL THEN 1 ELSE 0 END)
                    orphan_settlement_sale,
               SUM(CASE WHEN h.RetOrderRef IS NOT NULL AND ro.ID IS NULL THEN 1 ELSE 0 END)
                    orphan_return_request,
               SUM(CASE WHEN h.DistRef IS NOT NULL AND d.ID IS NULL THEN 1 ELSE 0 END)
                    orphan_distribution,
               SUM(CASE WHEN src.ID IS NOT NULL AND src.CustRef<>h.CustRef THEN 1 ELSE 0 END)
                    source_customer_mismatch,
               SUM(CASE WHEN settle.ID IS NOT NULL AND settle.CustRef<>h.CustRef THEN 1 ELSE 0 END)
                    settlement_customer_mismatch,
               SUM(CASE WHEN h.TSaleRef=h.SaleSettlementRef AND h.TSaleRef IS NOT NULL THEN 1 ELSE 0 END)
                    source_equals_settlement,
               SUM(CASE WHEN h.TSaleRef IS NOT NULL AND h.SaleSettlementRef IS NOT NULL
                              AND h.TSaleRef<>h.SaleSettlementRef THEN 1 ELSE 0 END)
                    source_differs_from_settlement
        FROM SLE.tblRetSaleHdr h
        LEFT JOIN SLE.tblSaleHdr src ON src.ID=h.TSaleRef
        LEFT JOIN SLE.tblSaleHdr settle ON settle.ID=h.SaleSettlementRef
        LEFT JOIN SLE.tblRetOrderHdr ro ON ro.ID=h.RetOrderRef
        LEFT JOIN SLE.tblDist d ON d.ID=h.DistRef
    """)[0]
    return {
        "population": population,
        "workflow_distribution": workflow,
        "business_window": {"from": BUSINESS_DATE_FROM, "to": BUSINESS_DATE_TO, "summary": window},
        "key_quality": keys,
        "reference_integrity": links,
    }


def _item_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) items,COUNT(DISTINCT i.UniqueId) distinct_uuids,
               SUM(CASE WHEN i.UniqueId IS NULL THEN 1 ELSE 0 END) null_uuids,
               COUNT(DISTINCT i.GoodsRef) goods,
               SUM(CASE WHEN i.TotalQty>0 THEN 1 ELSE 0 END) positive_qty,
               SUM(CASE WHEN i.TotalQty<=0 THEN 1 ELSE 0 END) nonpositive_qty,
               SUM(CASE WHEN i.SaleRef IS NOT NULL THEN 1 ELSE 0 END) legacy_line_sale_ref_present,
               SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) orphan_header,
               SUM(CASE WHEN g.ID IS NULL THEN 1 ELSE 0 END) orphan_goods,
               SUM(CASE WHEN u.ID IS NULL THEN 1 ELSE 0 END) orphan_unit,
               SUM(CASE WHEN i.RetCauseRef=h.RetCauseRef THEN 1 ELSE 0 END) cause_agrees_header,
               SUM(CASE WHEN i.RetCauseRef<>h.RetCauseRef THEN 1 ELSE 0 END) cause_differs_header
        FROM SLE.tblRetSaleItm i
        LEFT JOIN SLE.tblRetSaleHdr h ON h.ID=i.HdrRef
        LEFT JOIN GNR.tblGoods g ON g.ID=i.GoodsRef
        LEFT JOIN GNR.tblUnit u ON u.ID=i.UnitRef
    """)[0]
    cardinality = _rows(cursor, """
        WITH x AS (SELECT HdrRef,COUNT_BIG(*) items FROM SLE.tblRetSaleItm GROUP BY HdrRef)
        SELECT COUNT_BIG(*) headers,MIN(items) minimum_items,MAX(items) maximum_items,
               AVG(CONVERT(decimal(18,4),items)) average_items,
               SUM(CASE WHEN items=1 THEN 1 ELSE 0 END) one_item,
               SUM(CASE WHEN items>1 THEN 1 ELSE 0 END) multiple_items,
               (SELECT COUNT_BIG(*) FROM (SELECT HdrRef,RowOrder FROM SLE.tblRetSaleItm
                  GROUP BY HdrRef,RowOrder HAVING COUNT_BIG(*)>1)d) duplicate_row_order_groups
        FROM x
    """)[0]
    source_candidates = _rows(cursor, """
        WITH r AS (
          SELECT h.TSaleRef,i.ID item_id,i.GoodsRef,i.PrizeType,
                 ISNULL(i.FreeReasonId,0) FreeReasonId
          FROM SLE.tblRetSaleHdr h JOIN SLE.tblRetSaleItm i ON i.HdrRef=h.ID
          WHERE h.CancelFlag=0 AND h.TSaleRef IS NOT NULL
        ),c AS (
          SELECT r.item_id,COUNT(s.ID) candidates
          FROM r LEFT JOIN SLE.tblSaleItm s
            ON s.HdrRef=r.TSaleRef AND s.GoodsRef=r.GoodsRef
           AND s.PrizeType=r.PrizeType
           AND ISNULL(s.FreeReasonId,0)=r.FreeReasonId
          GROUP BY r.item_id
        )
        SELECT COUNT_BIG(*) source_linked_return_items,
               SUM(CASE WHEN candidates=0 THEN 1 ELSE 0 END) no_candidate,
               SUM(CASE WHEN candidates=1 THEN 1 ELSE 0 END) unique_candidate,
               SUM(CASE WHEN candidates>1 THEN 1 ELSE 0 END) ambiguous_candidate,
               MAX(candidates) maximum_candidates
        FROM c
    """)[0]
    cumulative_source_qty = _rows(cursor, """
        WITH r AS (
          SELECT h.TSaleRef SaleRef,i.GoodsRef,i.PrizeType,
                 ISNULL(i.FreeReasonId,0) FreeReasonId,SUM(i.TotalQty) returned
          FROM SLE.tblRetSaleHdr h JOIN SLE.tblRetSaleItm i ON i.HdrRef=h.ID
          WHERE h.CancelFlag=0 AND h.TSaleRef IS NOT NULL
          GROUP BY h.TSaleRef,i.GoodsRef,i.PrizeType,ISNULL(i.FreeReasonId,0)
        ),s AS (
          SELECT HdrRef SaleRef,GoodsRef,PrizeType,ISNULL(FreeReasonId,0) FreeReasonId,
                 SUM(TotalQty) sold
          FROM SLE.tblSaleItm
          GROUP BY HdrRef,GoodsRef,PrizeType,ISNULL(FreeReasonId,0)
        )
        SELECT COUNT_BIG(*) groups,
               SUM(CASE WHEN s.SaleRef IS NULL THEN 1 ELSE 0 END) no_source,
               SUM(CASE WHEN r.returned<s.sold THEN 1 ELSE 0 END) partial_return,
               SUM(CASE WHEN r.returned=s.sold THEN 1 ELSE 0 END) full_return,
               SUM(CASE WHEN r.returned>s.sold THEN 1 ELSE 0 END) exceeded,
               MAX(CASE WHEN s.sold<>0 THEN CONVERT(float,r.returned/s.sold) END)
                    maximum_return_to_sale_ratio
        FROM r LEFT JOIN s
          ON s.SaleRef=r.SaleRef AND s.GoodsRef=r.GoodsRef
         AND s.PrizeType=r.PrizeType AND s.FreeReasonId=r.FreeReasonId
    """)[0]
    return {
        "population_and_integrity": population,
        "header_item_cardinality": cardinality,
        "source_sale_composite_match": source_candidates,
        "cumulative_source_quantity_reconciliation": cumulative_source_qty,
        "source_line_contract": (
            "The item SaleRef field is dormant. For a source-linked return, match through "
            "header TSaleRef plus GoodsRef, PrizeType, and normalized FreeReasonId."
        ),
    }


def _amount_reconciliation(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        WITH a AS (
          SELECT HdrRef,SUM(Amount) gross_item_amount,
                 SUM(AmountNut) stored_net_item_amount,
                 SUM(Amount-Discount+AddAmount) calculated_net_item_amount,
                 SUM(Dis1) dis1,SUM(Dis2) dis2,SUM(Dis3) dis3,
                 SUM(Add1) add1,SUM(Add2) add2,SUM(Tax) tax,SUM(Charge) charge,
                 SUM(OtherDiscount) other_discount,SUM(OtherAddition) other_addition,
                 SUM(Discount) discount,SUM(AddAmount) add_amount
          FROM SLE.tblRetSaleItm GROUP BY HdrRef
        )
        SELECT COUNT_BIG(*) returns,
               SUM(CASE WHEN ABS(CONVERT(float,h.TotalAmount-a.gross_item_amount))>=0.01
                        THEN 1 ELSE 0 END) gross_comparison_differences_not_errors,
               SUM(CASE WHEN ABS(CONVERT(float,h.TotalAmount-a.stored_net_item_amount))>=0.01
                        THEN 1 ELSE 0 END) official_stored_net_differences,
               SUM(CASE WHEN ABS(CONVERT(float,h.TotalAmount-a.calculated_net_item_amount))>=0.01
                        THEN 1 ELSE 0 END) official_calculated_net_differences,
               SUM(CASE WHEN ABS(CONVERT(float,a.stored_net_item_amount-
                              a.calculated_net_item_amount))>=0.01
                        THEN 1 ELSE 0 END) item_net_formula_differences,
               SUM(CASE WHEN h.CancelFlag=0 AND
                              ABS(CONVERT(float,h.TotalAmount-a.gross_item_amount))>=0.01
                        THEN 1 ELSE 0 END) active_gross_comparison_differences_not_errors,
               SUM(CASE WHEN h.CancelFlag=1 AND
                              ABS(CONVERT(float,h.TotalAmount-a.gross_item_amount))>=0.01
                        THEN 1 ELSE 0 END) cancelled_gross_comparison_differences_not_errors,
               SUM(CASE WHEN ABS(CONVERT(float,h.Dis1-a.dis1))<0.01
                              AND ABS(CONVERT(float,h.Dis2-a.dis2))<0.01
                              AND ABS(CONVERT(float,h.Dis3-a.dis3))<0.01
                              AND ABS(CONVERT(float,h.Add1-a.add1))<0.01
                              AND ABS(CONVERT(float,h.Add2-a.add2))<0.01
                              AND ABS(CONVERT(float,h.Tax-a.tax))<0.01
                              AND ABS(CONVERT(float,h.Charge-a.charge))<0.01
                              AND ABS(CONVERT(float,h.OtherDiscount-a.other_discount))<0.01
                              AND ABS(CONVERT(float,h.OtherAddition-a.other_addition))<0.01
                        THEN 1 ELSE 0 END) all_header_components_equal_item_sums,
               SUM(CASE WHEN ABS(CONVERT(float,a.discount-
                              (a.dis1+a.dis2+a.dis3+a.other_discount)))>=0.01
                        THEN 1 ELSE 0 END) discount_component_rollup_differences,
               SUM(CASE WHEN ABS(CONVERT(float,a.add_amount-
                              (a.add1+a.add2+a.other_addition)))>=0.01
                        THEN 1 ELSE 0 END) addition_component_rollup_differences,
               MAX(ABS(CONVERT(float,h.TotalAmount-a.stored_net_item_amount)))
                    maximum_official_net_difference,
               SUM(a.gross_item_amount-h.TotalAmount) gross_minus_official_net_total
        FROM SLE.tblRetSaleHdr h JOIN a ON a.HdrRef=h.ID
    """)[0]


def _inventory_reconciliation(cursor: Any) -> dict[str, Any]:
    headers = _rows(cursor, """
        WITH v AS (
          SELECT DocRef,COUNT_BIG(*) vouchers,
                 SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirmed,
                 MIN(AccYear) AccYear,MIN(StockDCRef) StockDCRef,MIN(HealthCode) HealthCode
          FROM INV.tblVocherHdr WHERE VocherTypeCode=10 GROUP BY DocRef
        )
        SELECT COUNT_BIG(*) active_returns,
               SUM(CASE WHEN v.DocRef IS NULL THEN 1 ELSE 0 END) without_type10_voucher,
               SUM(CASE WHEN v.vouchers=1 THEN 1 ELSE 0 END) exactly_one_voucher,
               SUM(CASE WHEN v.vouchers>1 THEN 1 ELSE 0 END) multiple_vouchers,
               SUM(CASE WHEN v.confirmed=v.vouchers THEN 1 ELSE 0 END) all_vouchers_confirmed,
               SUM(CASE WHEN v.DocRef IS NOT NULL AND
                              (v.AccYear<>h.AccYear OR v.StockDCRef<>h.StockDCRef
                               OR v.HealthCode<>h.HealthCode) THEN 1 ELSE 0 END)
                    header_context_mismatch
        FROM SLE.tblRetSaleHdr h LEFT JOIN v ON v.DocRef=h.ID
        WHERE h.CancelFlag=0
    """)[0]
    goods = _rows(cursor, """
        WITH r AS (
          SELECT h.ID DocRef,i.GoodsRef,SUM(i.TotalQty) qty
          FROM SLE.tblRetSaleHdr h
          JOIN SLE.tblRetSaleItm i ON i.HdrRef=h.ID
          JOIN GNR.tblGoods g ON g.ID=i.GoodsRef
          WHERE h.CancelFlag=0 AND g.GoodsTypeRef<>4
          GROUP BY h.ID,i.GoodsRef
        ),v AS (
          SELECT h.DocRef,i.GoodsRef,SUM(i.TotalQty) qty
          FROM INV.tblVocherHdr h JOIN INV.tblVocherItm i ON i.HdrRef=h.ID
          WHERE h.VocherTypeCode=10 GROUP BY h.DocRef,i.GoodsRef
        ),x AS (
          SELECT COALESCE(r.DocRef,v.DocRef) DocRef,
                 COALESCE(r.GoodsRef,v.GoodsRef) GoodsRef,r.qty return_qty,v.qty voucher_qty
          FROM r FULL JOIN v ON v.DocRef=r.DocRef AND v.GoodsRef=r.GoodsRef
        )
        SELECT COUNT_BIG(*) compared_return_goods,
               SUM(CASE WHEN return_qty IS NULL THEN 1 ELSE 0 END) voucher_only,
               SUM(CASE WHEN voucher_qty IS NULL THEN 1 ELSE 0 END) return_only,
               SUM(CASE WHEN return_qty IS NOT NULL AND voucher_qty IS NOT NULL
                              AND ABS(return_qty-voucher_qty)<0.0001 THEN 1 ELSE 0 END) exact_qty,
               SUM(CASE WHEN return_qty IS NOT NULL AND voucher_qty IS NOT NULL
                              AND ABS(return_qty-voucher_qty)>=0.0001 THEN 1 ELSE 0 END) qty_mismatch,
               MAX(ABS(ISNULL(return_qty,0)-ISNULL(voucher_qty,0))) maximum_absolute_qty_difference
        FROM x
    """)[0]
    exclusions = _rows(cursor, """
        SELECT COUNT_BIG(*) nonstock_item_lines,COUNT(DISTINCT h.ID) nonstock_return_headers,
               SUM(i.TotalQty) nonstock_total_qty
        FROM SLE.tblRetSaleHdr h JOIN SLE.tblRetSaleItm i ON i.HdrRef=h.ID
        JOIN GNR.tblGoods g ON g.ID=i.GoodsRef
        WHERE h.CancelFlag=0 AND g.GoodsTypeRef=4
    """)[0]
    return {
        "voucher_header_projection": headers,
        "goods_level_quantity_reconciliation": goods,
        "nonstock_goods_excluded_by_official_generator": exclusions,
        "contract": (
            "Voucher type 10 is generated as a new goods-level aggregate projection; "
            "voucher item IDs and RowOrder are not return-item crosswalks."
        ),
    }


def _credit_settlement(cursor: Any) -> dict[str, Any]:
    payment_types = _rows(cursor, """
        SELECT p.PayTypeRef,COUNT_BIG(*) payments,COUNT(DISTINCT p.RetSaleRef) returns,
               SUM(CASE WHEN p.SaleRef IS NOT NULL THEN 1 ELSE 0 END) with_sale,
               SUM(CASE WHEN p.PaymentRef IS NOT NULL THEN 1 ELSE 0 END) with_payment_ref,
               SUM(CASE WHEN p.Amount>0 THEN 1 ELSE 0 END) positive,
               SUM(CASE WHEN p.Amount<0 THEN 1 ELSE 0 END) negative
        FROM Acc.tblPayments p WHERE p.RetSaleRef IS NOT NULL
        GROUP BY p.PayTypeRef ORDER BY payments DESC
    """)
    links = _rows(cursor, """
        SELECT COUNT_BIG(*) payments,
               SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) orphan_return,
               SUM(CASE WHEN h.CancelFlag=1 THEN 1 ELSE 0 END) linked_cancelled_return,
               SUM(CASE WHEN p.CustRef<>h.CustRef THEN 1 ELSE 0 END) customer_mismatch,
               SUM(CASE WHEN p.PayTypeRef=1006 AND p.SaleRef=h.SaleSettlementRef
                        THEN 1 ELSE 0 END) allocation_sale_matches_header_settlement_sale,
               SUM(CASE WHEN p.PayTypeRef=1006
                              AND ISNULL(p.SaleRef,-1)<>ISNULL(h.SaleSettlementRef,-1)
                        THEN 1 ELSE 0 END) allocation_sale_differs_from_header_settlement_sale
        FROM Acc.tblPayments p LEFT JOIN SLE.tblRetSaleHdr h ON h.ID=p.RetSaleRef
        WHERE p.RetSaleRef IS NOT NULL
    """)[0]
    counter_pair = _rows(cursor, """
        WITH p AS (
          SELECT * FROM Acc.tblPayments WHERE PayTypeRef=1006 AND RetSaleRef IS NOT NULL
        ),c AS (
          SELECT p.ID,COUNT(n.ID) counters,
                 SUM(CASE WHEN n.PayTypeRef=97 THEN 1 ELSE 0 END) type97,
                 SUM(CASE WHEN n.PayTypeRef=97
                                AND ABS(CONVERT(float,n.Amount-p.Amount))<0.01
                          THEN 1 ELSE 0 END) amount_exact,
                 SUM(CASE WHEN n.PayTypeRef=97 AND n.CustRef=p.CustRef
                          THEN 1 ELSE 0 END) customer_exact
          FROM p LEFT JOIN Acc.tblPayments n ON n.PaymentRef=p.ID GROUP BY p.ID
        )
        SELECT COUNT_BIG(*) source_payments,
               SUM(CASE WHEN counters=0 THEN 1 ELSE 0 END) no_counter,
               SUM(CASE WHEN counters=1 THEN 1 ELSE 0 END) one_counter,
               SUM(CASE WHEN counters>1 THEN 1 ELSE 0 END) multiple_counters,
               SUM(type97) type97_counters,SUM(amount_exact) amount_exact,
               SUM(customer_exact) customer_exact
        FROM c
    """)[0]
    coverage = _rows(cursor, """
        WITH p AS (
          SELECT RetSaleRef,SUM(CASE WHEN PayTypeRef IN (1006,17) THEN Amount ELSE 0 END) applied,
                 COUNT_BIG(*) allocations
          FROM Acc.tblPayments WHERE RetSaleRef IS NOT NULL GROUP BY RetSaleRef
        )
        SELECT COUNT_BIG(*) active_returns,
               SUM(CASE WHEN p.RetSaleRef IS NULL THEN 1 ELSE 0 END) no_payment_rows,
               SUM(CASE WHEN ISNULL(p.applied,0)=0 THEN 1 ELSE 0 END) zero_applied,
               SUM(CASE WHEN ISNULL(p.applied,0)>0 AND ISNULL(p.applied,0)<h.TotalAmount
                        THEN 1 ELSE 0 END) partially_applied,
               SUM(CASE WHEN ABS(CONVERT(float,ISNULL(p.applied,0)-h.TotalAmount))<0.01
                        THEN 1 ELSE 0 END) fully_applied,
               SUM(CASE WHEN ISNULL(p.applied,0)>h.TotalAmount THEN 1 ELSE 0 END) over_applied,
               SUM(CASE WHEN h.SaleSettlementRef IS NULL THEN 1 ELSE 0 END)
                    header_without_settlement_sale,
               SUM(CASE WHEN h.SaleSettlementRef IS NOT NULL AND p.RetSaleRef IS NULL
                        THEN 1 ELSE 0 END) settlement_sale_without_payment,
               MAX(ISNULL(p.allocations,0)) maximum_allocations_per_return
        FROM SLE.tblRetSaleHdr h LEFT JOIN p ON p.RetSaleRef=h.ID
        WHERE h.CancelFlag=0
    """)[0]
    relation = _rows(cursor, """
        SELECT COUNT_BIG(*) relations,COUNT(DISTINCT PayId) pay_ids,
               COUNT(DISTINCT PaymentId) payment_ids,COUNT(DISTINCT RetSaleId) returns,
               SUM(CASE WHEN PaymentAmount>0 THEN 1 ELSE 0 END) positive_amount,
               SUM(CASE WHEN PaymentAmount<=0 THEN 1 ELSE 0 END) nonpositive_amount
        FROM dbo.tblPayWithPaymentRelation
    """)[0]
    return {
        "return_linked_payment_types": payment_types,
        "return_payment_integrity": links,
        "type1006_to_type97_counter_pair": counter_pair,
        "active_return_credit_coverage_against_header_total": coverage,
        "pay_with_payment_relation_summary": relation,
        "contract": (
            "PayType 1006 applies return credit to an invoice; a same-amount PayType 97 "
            "counter-entry points back through PaymentRef. Header SaleSettlementRef is not "
            "the complete allocation set and must not be used as an immutable one-invoice key."
        ),
    }


def _return_requests(cursor: Any) -> dict[str, Any]:
    headers = _rows(cursor, """
        SELECT COUNT_BIG(*) requests,
               SUM(CASE WHEN IsConfirm=1 THEN 1 ELSE 0 END) confirmed,
               SUM(CASE WHEN CancelFlag=1 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN SaleRef IS NOT NULL THEN 1 ELSE 0 END) source_sale_linked,
               SUM(CASE WHEN DistRef IS NOT NULL THEN 1 ELSE 0 END) distribution_linked,
               SUM(CASE WHEN CustomerCallReturnId IS NOT NULL THEN 1 ELSE 0 END) mobile_linked,
               MIN(RetOrderDate) minimum_business_date,MAX(RetOrderDate) maximum_business_date,
               COUNT(DISTINCT UniqueId) distinct_uuids
        FROM SLE.tblRetOrderHdr
    """)[0]
    workflow = _rows(cursor, """
        SELECT RetTypeCode,HealthCode,IsConfirm,CancelFlag,COUNT_BIG(*) requests
        FROM SLE.tblRetOrderHdr
        GROUP BY RetTypeCode,HealthCode,IsConfirm,CancelFlag
        ORDER BY requests DESC
    """)
    items = _rows(cursor, """
        SELECT COUNT_BIG(*) items,COUNT(DISTINCT HdrRef) requests,
               COUNT(DISTINCT GoodsRef) goods,
               SUM(CASE WHEN TotalQty>0 THEN 1 ELSE 0 END) positive_qty,
               SUM(CASE WHEN TotalQty<=0 THEN 1 ELSE 0 END) nonpositive_qty,
               COUNT(DISTINCT UniqueId) distinct_uuids
        FROM SLE.tblRetOrderItm
    """)[0]
    conversion = _rows(cursor, """
        SELECT COUNT_BIG(*) linked_returns,
               SUM(CASE WHEN h.CancelFlag=0 THEN 1 ELSE 0 END) active_linked_returns,
               SUM(CASE WHEN h.CancelFlag=1 THEN 1 ELSE 0 END) cancelled_linked_returns,
               COUNT(DISTINCT h.RetOrderRef) linked_requests
        FROM SLE.tblRetSaleHdr h WHERE h.RetOrderRef IS NOT NULL
    """)[0]
    return {
        "request_headers": headers,
        "request_workflow": workflow,
        "request_items": items,
        "conversion_to_sales_return": conversion,
    }


def _distribution_staging(cursor: Any) -> dict[str, Any]:
    headers = _rows(cursor, """
        SELECT COUNT_BIG(*) headers,COUNT(DISTINCT ID) distinct_ids,
               COUNT(DISTINCT DistRef) distributions,
               SUM(CASE WHEN CancelFlag=1 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN TSaleRef IS NOT NULL THEN 1 ELSE 0 END) source_sale_linked,
               SUM(CASE WHEN RetOrderRef IS NOT NULL THEN 1 ELSE 0 END) request_linked,
               MIN(RetSaleDate) minimum_business_date,MAX(RetSaleDate) maximum_business_date
        FROM SLE.tblRetSaleHdr_RD
    """)[0]
    statuses = _rows(cursor, """
        SELECT RDStatus,CancelFlag,RetTypeCode,HealthCode,COUNT_BIG(*) headers
        FROM SLE.tblRetSaleHdr_RD
        GROUP BY RDStatus,CancelFlag,RetTypeCode,HealthCode
        ORDER BY headers DESC
    """)
    items = _rows(cursor, """
        SELECT COUNT_BIG(*) items,COUNT(DISTINCT HdrRef) headers,
               SUM(CASE WHEN TotalQty>0 THEN 1 ELSE 0 END) positive_qty,
               SUM(CASE WHEN SaleRef IS NOT NULL THEN 1 ELSE 0 END) legacy_sale_ref_populated
        FROM SLE.tblRetSaleItm_RD
    """)[0]
    main_crosswalk = _rows(cursor, """
        SELECT COUNT_BIG(*) staging_headers,
               SUM(CASE WHEN h.ID IS NOT NULL THEN 1 ELSE 0 END) main_business_key_match,
               SUM(CASE WHEN h.DistRef=rd.DistRef THEN 1 ELSE 0 END)
                    matching_distribution,
               COUNT(DISTINCT h.ID) matched_main_returns
        FROM SLE.tblRetSaleHdr_RD rd
        LEFT JOIN SLE.tblRetSaleHdr h
          ON h.AccYear=rd.AccYear AND h.DCRef=rd.DCRef
         AND h.DCSaleOfficeRef=rd.DCSaleOfficeRef AND h.RetSaleNo=rd.RetSaleNo
    """)[0]
    return {
        "headers": headers,
        "status_distribution": statuses,
        "items": items,
        "main_return_business_key_crosswalk": main_crosswalk,
        "boundary": (
            "RD tables are mutable distribution-day staging. They are not official sales "
            "returns until the finalize procedure creates main return and voucher records."
        ),
    }


def _ngt_crosswalk(cursor: Any) -> dict[str, Any]:
    profile = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturns) return_headers,
          (SELECT SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END)
             FROM NGT.CustomerCallReturns) removed_headers,
          (SELECT SUM(CASE WHEN IsCanceled=1 THEN 1 ELSE 0 END)
             FROM NGT.CustomerCallReturns) cancelled_headers,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturnLines) return_lines,
          (SELECT SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END)
             FROM NGT.CustomerCallReturnLines) removed_lines,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturnLineQtyDetails) quantity_details,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturnLineRequestQtyDetails)
                request_quantity_details,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallreturnLineBatchQtyDetails)
                batch_quantity_details
    """)[0]
    crosswalk = _rows(cursor, """
        SELECT COUNT_BIG(*) lines,
               SUM(CASE WHEN h.Id IS NULL THEN 1 ELSE 0 END) orphan_parent,
               SUM(CASE WHEN l.BackOfficeReturnOrderUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                    request_uuid_present,
               SUM(CASE WHEN l.BackOfficeReturnOrderRef IS NOT NULL THEN 1 ELSE 0 END)
                    request_ref_present,
               SUM(CASE WHEN l.BackOfficeReturnInvoiceUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                    return_uuid_present,
               SUM(CASE WHEN l.BackOfficeReturnInvoiceRef IS NOT NULL THEN 1 ELSE 0 END)
                    return_ref_present,
               SUM(CASE WHEN ro.ID IS NOT NULL THEN 1 ELSE 0 END) request_uuid_match,
               SUM(CASE WHEN ri.ID IS NOT NULL THEN 1 ELSE 0 END) return_item_uuid_match
        FROM NGT.CustomerCallReturnLines l
        LEFT JOIN NGT.CustomerCallReturns h ON h.Id=l.CustomerCallReturnUniqueId
        LEFT JOIN SLE.tblRetOrderHdr ro ON ro.UniqueId=l.BackOfficeReturnOrderUniqueId
        LEFT JOIN SLE.tblRetSaleItm ri ON ri.UniqueId=l.BackOfficeReturnInvoiceUniqueId
    """)[0]
    return {
        "mobile_population": profile,
        "backoffice_crosswalk": crosswalk,
        "boundary": (
            "Current NGT return rows are not linked into SLE main return records in this clone; "
            "presence in NGT cannot be treated as an official return invoice."
        ),
    }


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition,o.modify_date
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE (s.name='SLE' AND o.name IN
              ('usp_AfterSaveRetSale','USP_CreatePaymentFromRetSale','usp_FinalizeRetDist',
               'usp_RD_InsertRetSale','usp_sdsnet_CreateRetSaleFromRetOrder',
               'usp_RetSaleUpdateDisAdd','Check_AmountOfRetSaleHdr'))
           OR (s.name='dbo' AND o.name IN
              ('USP_SDSNET_GenerateRetSaleVocher','NGT_GenerateRetSaleVocher_ForDistInfo',
               'Ufn_GetPayFromRetSaleAndPayments'))
           OR (s.name='Acc' AND o.name='GetRetSalePayAmount')
           OR (s.name='FRU' AND o.name IN ('RetSaleItmModel','RetSaleHdrModel'))
        ORDER BY s.name,o.name
    """)


def _data_quality(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        WITH a AS (
          SELECT HdrRef,SUM(Amount) item_amount FROM SLE.tblRetSaleItm GROUP BY HdrRef
        )
        SELECT
          (SELECT COUNT_BIG(*) FROM SLE.tblRetSaleHdr h JOIN a ON a.HdrRef=h.ID
             WHERE ABS(CONVERT(float,h.TotalAmount-a.item_amount))>=0.01)
                header_total_item_sum_mismatches,
          (SELECT COUNT_BIG(*) FROM SLE.tblRetSaleItm i JOIN SLE.tblRetSaleHdr h ON h.ID=i.HdrRef
             WHERE i.RetCauseRef<>h.RetCauseRef) item_header_cause_mismatches,
          (SELECT COUNT_BIG(*) FROM SLE.tblRetSaleItm WHERE SaleRef IS NOT NULL)
                populated_legacy_line_sale_refs,
          (SELECT COUNT_BIG(*) FROM SLE.tblRetSaleHdr h LEFT JOIN INV.tblVocherHdr v
             ON v.DocRef=h.ID AND v.VocherTypeCode=10
             WHERE h.CancelFlag=0 AND v.ID IS NULL) active_returns_without_type10_voucher,
          (SELECT COUNT_BIG(*) FROM Acc.tblPayments p JOIN SLE.tblRetSaleHdr h ON h.ID=p.RetSaleRef
             WHERE h.CancelFlag=1) payment_rows_linked_to_cancelled_returns,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallReturnLines l
             LEFT JOIN NGT.CustomerCallReturns h ON h.Id=l.CustomerCallReturnUniqueId
             WHERE h.Id IS NULL) orphan_mobile_return_lines
    """)[0]


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        private_safety = _assert_safe_target(cursor)
        tables = [
            _public_table_metadata(_table_metadata(cursor, x["object"], x["role"]))
            for x in DOMAIN_TABLES
        ]
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "sales_returns_stock_entry_and_credit_settlement",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata and aggregate sales-return evidence",
                "privacy_policy": (
                    "no customer/personnel rows, comments, usernames, hostnames, credentials, "
                    "raw invoice/payment records, or document identifiers"
                ),
            },
            "safety": _public_safety(private_safety),
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "reference_masters": _reference_masters(cursor),
            "sales_return_headers": _header_profile(cursor),
            "sales_return_items": _item_profile(cursor),
            "header_item_amount_reconciliation": _amount_reconciliation(cursor),
            "inventory_entry_projection": _inventory_reconciliation(cursor),
            "return_credit_settlement": _credit_settlement(cursor),
            "return_requests": _return_requests(cursor),
            "distribution_return_staging": _distribution_staging(cursor),
            "ngt_return_crosswalk": _ngt_crosswalk(cursor),
            "data_quality": _data_quality(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "evidence_limits": [
                "Return type, return health, request type, and request health use distinct lookup code sets.",
                "Header TSaleRef means source sale; SaleSettlementRef is only a settlement hint and is not the complete allocation set.",
                "Return-item SaleRef is unpopulated; source lines use a composite business match.",
                "Inventory voucher type 10 is a goods-level aggregation and not a row-by-row copy.",
                "Header TotalAmount is operationally used but does not equal item Amount sum for every historical row.",
                "RD records are distribution staging, while current NGT rows have no confirmed main-return crosswalk.",
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
