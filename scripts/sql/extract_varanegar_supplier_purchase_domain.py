"""Extract Varanegar supplier-purchase, return, and payable evidence.

Read-only by design. The JSON contains schema metadata, safe reference labels,
aggregate counts, reconciliation results, and selected SQL contracts. It never
persists supplier rows, contact/tax identifiers, comments, usernames,
hostnames, credentials, instrument identifiers, or raw settlement records.
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
    {"object": "ICA.TblSupInvoiceHdr", "role": "supplier_invoice_header"},
    {"object": "ICA.TblSupInvoiceItm", "role": "supplier_invoice_item"},
    {"object": "ICA.TblSupInvoiceTolls", "role": "supplier_invoice_header_toll"},
    {"object": "ICA.TblSupInvoiceItmXToll", "role": "supplier_invoice_item_toll_allocation"},
    {"object": "ICA.tblSupInvInvoiceRelation", "role": "supplier_invoice_inventory_receipt_link"},
    {"object": "ICA.TblICABuyPrice", "role": "applied_purchase_price_history"},
    {"object": "ICA.tblRetSupInvoiceHdr", "role": "supplier_return_header"},
    {"object": "ICA.tblRetSupInvoiceItm", "role": "supplier_return_item"},
    {"object": "ICA.tblRetSupInvoiceTolls", "role": "supplier_return_header_toll"},
    {"object": "ICA.tblRetSupInvoiceItmXToll", "role": "supplier_return_item_toll_allocation"},
    {"object": "ICA.tblRetSupInvRelation", "role": "unused_supplier_return_relation"},
    {"object": "GNR.tblSupplier", "role": "supplier_master"},
    {"object": "GNR.tblGoodsSupplier", "role": "goods_supplier_master"},
    {"object": "Acc.tblSupSettlement", "role": "direct_supplier_invoice_allocation"},
    {"object": "Acc.tblSupSettlementType", "role": "supplier_settlement_type_master"},
    {"object": "Inv.tblVocherHdr", "role": "inventory_voucher_header"},
    {"object": "Inv.tblVocherItm", "role": "inventory_voucher_item"},
    {"object": "Inv.tblVocherItmPrice", "role": "inventory_item_cost_allocation"},
    {"object": "dbo.POrder", "role": "legacy_purchase_order_header"},
    {"object": "dbo.POrderLine", "role": "legacy_purchase_order_item"},
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
    excluded = {
        "comment", "suppliername", "address", "tel", "mobile", "fax", "email",
        "nationalcode", "economiccode", "moadiancode", "taxcode", "bankaccount",
        "accountno", "cardno", "iban", "appuserid", "sqlusername", "winusername",
        "hostname", "applicationname",
    }
    result = dict(metadata)
    result["columns"] = [
        c for c in metadata.get("columns", [])
        if str(c.get("column_name", "")).lower() not in excluded
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
          WHERE LOWER(c.name) LIKE '%supinvoiceref%'
             OR LOWER(c.name) LIKE '%retsup%'
             OR LOWER(c.name) LIKE '%supsettlement%'
             OR LOWER(c.name) LIKE '%supplierref%'
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
    settlement_types = _decode_fields(_rows(cursor, """
        SELECT t.ID,t.Code,CONVERT(varbinary(max),t.Name) Name,t.IsManual,t.PlusMinus,
               t.IsDisabled,COUNT_BIG(s.ID) direct_settlement_usage
        FROM Acc.tblSupSettlementType t
        LEFT JOIN Acc.tblSupSettlement s ON s.SupSettlementTypeRef=t.ID
        GROUP BY t.ID,t.Code,t.Name,t.IsManual,t.PlusMinus,t.IsDisabled
        ORDER BY t.ID
    """), ("Name",))
    return {
        "supplier_invoice_statuses": [
            {"id": 0, "meaning_fa": "مرتبط نشده", "semantic": "not_applied"},
            {"id": 1, "meaning_fa": "مرتبط شده", "semantic": "applied"},
        ],
        "supplier_settlement_types": settlement_types,
        "inventory_voucher_types_observed": [
            {"code": 20, "semantic": "supplier_purchase_receipt"},
            {"code": 55, "semantic": "supplier_purchase_return_exit"},
        ],
    }


def _supplier_invoice_profile(cursor: Any) -> dict[str, Any]:
    header = _rows(cursor, """
        SELECT Status,COUNT_BIG(*) invoices,COUNT(DISTINCT SupplierRef) suppliers,
               COUNT(DISTINCT DCRef) organization_dcs,
               SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirm_date_present,
               SUM(CASE WHEN IsNew=1 THEN 1 ELSE 0 END) is_new,
               SUM(CASE WHEN TSupInvoiceRef IS NOT NULL THEN 1 ELSE 0 END) temporary_source_present,
               SUM(CASE WHEN CurrencyRef IS NOT NULL THEN 1 ELSE 0 END) currency_present,
               COUNT(DISTINCT ExchangeRate) exchange_rates,
               MIN(VchDate) minimum_voucher_date,MAX(VchDate) maximum_voucher_date,
               MIN(SupInvoiceDate) minimum_supplier_invoice_date,
               MAX(SupInvoiceDate) maximum_supplier_invoice_date,
               MIN(InsDate) minimum_insert_date,MAX(InsDate) maximum_insert_date
        FROM ICA.TblSupInvoiceHdr GROUP BY Status ORDER BY Status
    """)
    integrity = _rows(cursor, """
        SELECT COUNT_BIG(*) invoices,
               SUM(CASE WHEN s.ID IS NULL THEN 1 ELSE 0 END) orphan_supplier,
               SUM(CASE WHEN d.ID IS NULL THEN 1 ELSE 0 END) orphan_dc,
               SUM(CASE WHEN c.ID IS NULL AND h.CurrencyRef IS NOT NULL THEN 1 ELSE 0 END) orphan_currency,
               SUM(CASE WHEN h.ExchangeRate IS NULL OR h.ExchangeRate<=0 THEN 1 ELSE 0 END) invalid_exchange_rate,
               SUM(CASE WHEN h.ExchangeRate=1 THEN 1 ELSE 0 END) exchange_rate_one
        FROM ICA.TblSupInvoiceHdr h
        LEFT JOIN GNR.tblSupplier s ON s.ID=h.SupplierRef
        LEFT JOIN GNR.tblDC d ON d.ID=h.DCRef
        LEFT JOIN GNR.tblCurrency c ON c.ID=h.CurrencyRef
    """)[0]
    items = _rows(cursor, """
        SELECT COUNT_BIG(*) items,COUNT(DISTINCT i.GoodsRef) goods,
               SUM(CASE WHEN i.Qty>0 THEN 1 ELSE 0 END) positive_qty,
               SUM(CASE WHEN i.Qty<=0 OR i.Qty IS NULL THEN 1 ELSE 0 END) nonpositive_qty,
               SUM(CASE WHEN ISNULL(i.PrizeQty,0)<>0 THEN 1 ELSE 0 END) prize_used,
               SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) orphan_header,
               SUM(CASE WHEN g.ID IS NULL THEN 1 ELSE 0 END) orphan_goods,
               SUM(CASE WHEN u.ID IS NULL THEN 1 ELSE 0 END) orphan_unit,
               SUM(CASE WHEN ABS(CONVERT(float,i.Amount-(i.Qty*i.Price)))<0.01 THEN 1 ELSE 0 END) naive_qty_price_exact,
               SUM(CASE WHEN ABS(CONVERT(float,i.Amount-(i.Qty*i.Price)))>=0.01 THEN 1 ELSE 0 END) naive_qty_price_mismatch
        FROM ICA.TblSupInvoiceItm i
        LEFT JOIN ICA.TblSupInvoiceHdr h ON h.ID=i.HdrRef
        LEFT JOIN GNR.tblGoods g ON g.ID=i.GoodsRef
        LEFT JOIN GNR.tblUnit u ON u.ID=i.UnitRef
    """)[0]
    official_amount = _rows(cursor, """
        SELECT COUNT_BIG(*) items,
               SUM(CASE WHEN g.GoodsTypeRef IN (2,3) THEN 1
                        WHEN ISNULL(i.Qty,0)-ISNULL(i.PrizeQty,0)=0 THEN 0
                        WHEN FLOOR(i.Amount/(i.Qty-ISNULL(i.PrizeQty,0))/10/h.ExchangeRate)=FLOOR(i.Price/10) THEN 1
                        WHEN ROUND(i.Amount/(i.Qty-ISNULL(i.PrizeQty,0))/10/h.ExchangeRate,0)=ROUND(i.Price/10,0) THEN 1
                        ELSE 0 END) official_price_valid,
               SUM(CASE WHEN g.GoodsTypeRef NOT IN (2,3)
                              AND ISNULL(i.Qty,0)-ISNULL(i.PrizeQty,0)=0 THEN 1 ELSE 0 END) zero_chargeable_qty
        FROM ICA.TblSupInvoiceItm i
        JOIN ICA.TblSupInvoiceHdr h ON h.ID=i.HdrRef
        JOIN GNR.tblGoods g ON g.ID=i.GoodsRef
    """)[0]
    credit = _rows(cursor, """
        WITH x AS (
          SELECT h.ID,h.Status,
                 SUM(ISNULL(i.TotalAmount,0)) total_amount,
                 SUM(ISNULL(i.TotalAmount,0)-ISNULL(i.InEffectiveOnSupplierAddition,0)+ISNULL(i.InEffectiveOnSupplierDiscount,0)) cardex_amount,
                 SUM(ISNULL(i.InEffectiveOnSupplierAddition,0)) ineffective_addition,
                 SUM(ISNULL(i.InEffectiveOnSupplierDiscount,0)) ineffective_discount
          FROM ICA.TblSupInvoiceHdr h JOIN ICA.TblSupInvoiceItm i ON i.HdrRef=h.ID
          GROUP BY h.ID,h.Status
        )
        SELECT Status,COUNT_BIG(*) invoices,
               SUM(CASE WHEN ABS(CONVERT(float,total_amount-cardex_amount))<0.01 THEN 1 ELSE 0 END) same_amount,
               SUM(CASE WHEN ABS(CONVERT(float,total_amount-cardex_amount))>=0.01 THEN 1 ELSE 0 END) different_amount,
               SUM(total_amount) total_amount,SUM(cardex_amount) supplier_cardex_amount,
               SUM(ineffective_addition) ineffective_addition,
               SUM(ineffective_discount) ineffective_discount,
               MAX(ABS(CONVERT(float,total_amount-cardex_amount))) maximum_difference
        FROM x GROUP BY Status ORDER BY Status
    """)
    return {
        "header_status_profile": header,
        "header_reference_integrity": integrity,
        "item_profile": items,
        "official_item_price_validation": official_amount,
        "supplier_credit_amount_reconciliation": credit,
        "status_contract": (
            "Status 0/1 is the supplier-invoice application/link state. Inventory receipt "
            "confirmation is a separate earlier state and must not be collapsed into it."
        ),
    }


def _inventory_receipt_relation(cursor: Any) -> dict[str, Any]:
    cardinality = _rows(cursor, """
        WITH i AS (SELECT SupInvoiceHdrRef,COUNT_BIG(*) relations,
                          COUNT(DISTINCT InvVchHdrRef) vouchers
                   FROM ICA.tblSupInvInvoiceRelation GROUP BY SupInvoiceHdrRef),
             v AS (SELECT InvVchHdrRef,COUNT_BIG(*) relations,
                          COUNT(DISTINCT SupInvoiceHdrRef) invoices
                   FROM ICA.tblSupInvInvoiceRelation GROUP BY InvVchHdrRef)
        SELECT
          (SELECT COUNT_BIG(*) FROM ICA.tblSupInvInvoiceRelation) relations,
          (SELECT COUNT_BIG(*) FROM ICA.TblSupInvoiceHdr) invoices,
          (SELECT COUNT_BIG(*) FROM i) invoices_with_relation,
          (SELECT COUNT_BIG(*) FROM i WHERE vouchers=1) invoices_one_voucher,
          (SELECT COUNT_BIG(*) FROM i WHERE vouchers>1) invoices_multiple_vouchers,
          (SELECT MAX(vouchers) FROM i) maximum_vouchers_per_invoice,
          (SELECT COUNT_BIG(*) FROM v) distinct_vouchers,
          (SELECT COUNT_BIG(*) FROM v WHERE invoices=1) vouchers_one_invoice,
          (SELECT COUNT_BIG(*) FROM v WHERE invoices>1) vouchers_multiple_invoices
    """)[0]
    integrity = _rows(cursor, """
        SELECT COUNT_BIG(*) relations,
               SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) orphan_invoice,
               SUM(CASE WHEN v.ID IS NULL THEN 1 ELSE 0 END) orphan_voucher,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.VocherTypeCode<>20 THEN 1 ELSE 0 END) unexpected_voucher_type,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.ConfirmDate IS NULL THEN 1 ELSE 0 END) unconfirmed_voucher,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.AccYear<>h.AccYear THEN 1 ELSE 0 END) accyear_mismatch,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.SupplierRef<>h.SupplierRef THEN 1 ELSE 0 END) supplier_mismatch,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.DCRef IS NULL THEN 1 ELSE 0 END) voucher_dc_null,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.DCRef IS NOT NULL AND v.DCRef<>h.DCRef THEN 1 ELSE 0 END) nonnull_dc_mismatch
        FROM ICA.tblSupInvInvoiceRelation r
        LEFT JOIN ICA.TblSupInvoiceHdr h ON h.ID=r.SupInvoiceHdrRef
        LEFT JOIN Inv.tblVocherHdr v ON v.ID=r.InvVchHdrRef
    """)[0]
    status_relation = _rows(cursor, """
        SELECT h.Status,COUNT(DISTINCT h.ID) invoices,COUNT_BIG(*) relations,
               SUM(CASE WHEN v.ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirmed_receipt_relations
        FROM ICA.TblSupInvoiceHdr h
        JOIN ICA.tblSupInvInvoiceRelation r ON r.SupInvoiceHdrRef=h.ID
        JOIN Inv.tblVocherHdr v ON v.ID=r.InvVchHdrRef
        GROUP BY h.Status ORDER BY h.Status
    """)
    quantities = _rows(cursor, """
        WITH si AS (
          SELECT i.HdrRef,i.GoodsRef,SUM(ISNULL(i.Qty,0)) Qty
          FROM ICA.TblSupInvoiceItm i GROUP BY i.HdrRef,i.GoodsRef
        ),vi AS (
          SELECT r.SupInvoiceHdrRef HdrRef,i.GoodsRef,SUM(ISNULL(i.TotalQty,0)) Qty
          FROM ICA.tblSupInvInvoiceRelation r
          JOIN Inv.tblVocherItm i ON i.HdrRef=r.InvVchHdrRef
          GROUP BY r.SupInvoiceHdrRef,i.GoodsRef
        ),x AS (
          SELECT COALESCE(si.HdrRef,vi.HdrRef) HdrRef,
                 ISNULL(si.Qty,0) invoice_qty,ISNULL(vi.Qty,0) voucher_qty,
                 CASE WHEN si.HdrRef IS NULL THEN 'voucher_only'
                      WHEN vi.HdrRef IS NULL THEN 'invoice_only'
                      WHEN ABS(CONVERT(float,si.Qty-vi.Qty))<0.0001 THEN 'exact'
                      ELSE 'mismatch' END result
          FROM si FULL JOIN vi ON vi.HdrRef=si.HdrRef AND vi.GoodsRef=si.GoodsRef
        )
        SELECT result,COUNT_BIG(*) goods_groups,COUNT(DISTINCT HdrRef) invoices,
               SUM(invoice_qty) invoice_qty,SUM(voucher_qty) voucher_qty,
               MAX(ABS(CONVERT(float,invoice_qty-voucher_qty))) maximum_difference
        FROM x GROUP BY result ORDER BY result
    """)
    order_path = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM dbo.POrder) legacy_order_headers,
          (SELECT COUNT_BIG(*) FROM dbo.POrderLine) legacy_order_items,
          (SELECT COUNT_BIG(*) FROM Inv.tblVocherHdr WHERE VocherTypeCode=20) purchase_receipt_vouchers,
          (SELECT COUNT_BIG(*) FROM Inv.tblVocherHdr WHERE VocherTypeCode=20 AND PurchaseOrderRef IS NOT NULL) purchase_receipts_with_order_ref,
          (SELECT COUNT_BIG(*) FROM Inv.tblVocherHdr WHERE VocherTypeCode=20 AND ConfirmDate IS NOT NULL) confirmed_purchase_receipts
    """)[0]
    return {
        "relation_cardinality": cardinality,
        "relation_integrity": integrity,
        "relation_by_invoice_status": status_relation,
        "invoice_to_inventory_quantity_reconciliation": quantities,
        "purchase_order_path_usage": order_path,
        "contract": (
            "Supplier invoices may link to one or several confirmed type-20 receipts. "
            "Status 1 applies purchase cost; it is not proof that the stock receipt first appeared then."
        ),
    }


def _toll_and_cost_profile(cursor: Any) -> dict[str, Any]:
    allocation = _rows(cursor, """
        SELECT COUNT_BIG(*) allocations,COUNT(DISTINCT x.SupInvoiceItmRef) items,
               SUM(CASE WHEN i.ID IS NULL THEN 1 ELSE 0 END) orphan_item,
               SUM(CASE WHEN t.ID IS NULL THEN 1 ELSE 0 END) orphan_toll,
               SUM(CASE WHEN i.ID IS NOT NULL AND t.ID IS NOT NULL AND i.HdrRef<>t.InvoiceRef THEN 1 ELSE 0 END) cross_invoice_allocation
        FROM ICA.TblSupInvoiceItmXToll x
        LEFT JOIN ICA.TblSupInvoiceItm i ON i.ID=x.SupInvoiceItmRef
        LEFT JOIN ICA.TblSupInvoiceTolls t ON t.ID=x.SupInvoiceTollsRef
    """)[0]
    header_sum = _rows(cursor, """
        WITH x AS (
          SELECT t.ID,t.UserPrice,SUM(CASE WHEN b.IsAdding=1 THEN a.Amount ELSE -a.Amount END) allocated
          FROM ICA.TblSupInvoiceTolls t
          JOIN ICA.TblBuyToll b ON b.ID=t.TollRef
          LEFT JOIN ICA.TblSupInvoiceItmXToll a ON a.SupInvoiceTollsRef=t.ID
          GROUP BY t.ID,t.UserPrice
        )
        SELECT COUNT_BIG(*) tolls,
               SUM(CASE WHEN ABS(CONVERT(float,UserPrice-ISNULL(allocated,0)))<0.01 THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN ABS(CONVERT(float,UserPrice-ISNULL(allocated,0)))>=0.01 THEN 1 ELSE 0 END) mismatch,
               MAX(ABS(CONVERT(float,UserPrice-ISNULL(allocated,0)))) maximum_difference
        FROM x
    """)[0]
    item_sum = _rows(cursor, """
        WITH a AS (
          SELECT x.SupInvoiceItmRef,
                 SUM(CASE WHEN b.AffectionOnStockReceipt=1 AND b.IsAdding=1 THEN x.Amount ELSE 0 END) effective_addition,
                 SUM(CASE WHEN b.AffectionOnStockReceipt=1 AND b.IsAdding=0 THEN x.Amount ELSE 0 END) effective_discount,
                 SUM(CASE WHEN b.AffectionOnStockReceipt=0 AND b.IsAdding=1 THEN x.Amount ELSE 0 END) other_addition,
                 SUM(CASE WHEN b.AffectionOnStockReceipt=0 AND b.IsAdding=0 THEN x.Amount ELSE 0 END) other_discount
          FROM ICA.TblSupInvoiceItmXToll x
          JOIN ICA.TblSupInvoiceTolls t ON t.ID=x.SupInvoiceTollsRef
          JOIN ICA.TblBuyToll b ON b.ID=t.TollRef
          GROUP BY x.SupInvoiceItmRef
        )
        SELECT COUNT_BIG(*) allocated_items,
               SUM(CASE WHEN ABS(CONVERT(float,ISNULL(i.EffectiveAddition,0)-a.effective_addition))<0.01
                              AND ABS(CONVERT(float,ISNULL(i.EffectiveDiscount,0)-a.effective_discount))<0.01
                              AND ABS(CONVERT(float,ISNULL(i.OtherAddition,0)-a.other_addition))<0.01
                              AND ABS(CONVERT(float,ISNULL(i.OtherDiscount,0)-a.other_discount))<0.01
                        THEN 1 ELSE 0 END) all_components_exact,
               SUM(CASE WHEN ABS(CONVERT(float,ISNULL(i.EffectiveAddition,0)-a.effective_addition))>=0.01
                              OR ABS(CONVERT(float,ISNULL(i.EffectiveDiscount,0)-a.effective_discount))>=0.01
                              OR ABS(CONVERT(float,ISNULL(i.OtherAddition,0)-a.other_addition))>=0.01
                              OR ABS(CONVERT(float,ISNULL(i.OtherDiscount,0)-a.other_discount))>=0.01
                        THEN 1 ELSE 0 END) component_mismatch
        FROM a JOIN ICA.TblSupInvoiceItm i ON i.ID=a.SupInvoiceItmRef
    """)[0]
    return {
        "item_toll_allocation_integrity": allocation,
        "header_toll_to_item_allocation_reconciliation": header_sum,
        "item_toll_component_reconciliation": item_sum,
        "cost_application_contract": (
            "usp_ApplySupInvoice allocates FinalEffectiveAmount into inventory item-price rows, "
            "updates purchase cost, rejects effective unit price below one, and applies rounding correction."
        ),
    }


def _supplier_return_profile(cursor: Any) -> dict[str, Any]:
    header = _rows(cursor, """
        SELECT COUNT_BIG(*) headers,COUNT(DISTINCT SupplierRef) suppliers,
               SUM(CASE WHEN SupplierRef IS NULL THEN 1 ELSE 0 END) supplier_null,
               SUM(CASE WHEN SupInvoiceRef IS NOT NULL THEN 1 ELSE 0 END) source_invoice_present,
               SUM(CASE WHEN InvVocherRef IS NOT NULL THEN 1 ELSE 0 END) inventory_voucher_present,
               SUM(CASE WHEN IsNew=1 THEN 1 ELSE 0 END) is_new,
               SUM(CASE WHEN CurrencyRef IS NOT NULL THEN 1 ELSE 0 END) currency_present,
               MIN(RetInvoiceDate) minimum_return_date,MAX(RetInvoiceDate) maximum_return_date
        FROM ICA.tblRetSupInvoiceHdr
    """)[0]
    integrity = _rows(cursor, """
        SELECT COUNT_BIG(*) headers,
               SUM(CASE WHEN s.ID IS NULL THEN 1 ELSE 0 END) orphan_supplier,
               SUM(CASE WHEN si.ID IS NULL AND h.SupInvoiceRef IS NOT NULL THEN 1 ELSE 0 END) orphan_source_invoice,
               SUM(CASE WHEN v.ID IS NULL THEN 1 ELSE 0 END) orphan_inventory_voucher,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.VocherTypeCode<>55 THEN 1 ELSE 0 END) unexpected_voucher_type,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.ConfirmDate IS NULL THEN 1 ELSE 0 END) unconfirmed_inventory_voucher,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.AccYear<>h.AccYear THEN 1 ELSE 0 END) accyear_mismatch,
               SUM(CASE WHEN si.ID IS NOT NULL AND si.SupplierRef<>h.SupplierRef THEN 1 ELSE 0 END) source_supplier_mismatch,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.DCRef=h.DCRef THEN 1 ELSE 0 END) voucher_dc_exact,
               SUM(CASE WHEN v.ID IS NOT NULL AND v.DCRef IS NOT NULL AND v.DCRef<>h.DCRef THEN 1 ELSE 0 END) voucher_dc_different
        FROM ICA.tblRetSupInvoiceHdr h
        LEFT JOIN GNR.tblSupplier s ON s.ID=h.SupplierRef
        LEFT JOIN ICA.TblSupInvoiceHdr si ON si.ID=h.SupInvoiceRef
        LEFT JOIN Inv.tblVocherHdr v ON v.ID=h.InvVocherRef
    """)[0]
    items = _rows(cursor, """
        SELECT COUNT_BIG(*) items,COUNT(DISTINCT i.GoodsRef) goods,
               SUM(CASE WHEN i.Qty>0 THEN 1 ELSE 0 END) positive_qty,
               SUM(CASE WHEN i.Qty<=0 OR i.Qty IS NULL THEN 1 ELSE 0 END) nonpositive_qty,
               SUM(CASE WHEN ISNULL(i.PrizeQty,0)<>0 THEN 1 ELSE 0 END) prize_used,
               SUM(CASE WHEN ABS(CONVERT(float,i.Amount-(i.Qty*i.Price)))<0.01 THEN 1 ELSE 0 END) naive_amount_exact,
               SUM(CASE WHEN ABS(CONVERT(float,i.TotalAmount-(i.EffectiveAmount+i.OtherAddition-i.OtherDiscount)))<0.01 THEN 1 ELSE 0 END) total_formula_exact,
               SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) orphan_header,
               SUM(CASE WHEN g.ID IS NULL THEN 1 ELSE 0 END) orphan_goods
        FROM ICA.tblRetSupInvoiceItm i
        LEFT JOIN ICA.tblRetSupInvoiceHdr h ON h.ID=i.HdrRef
        LEFT JOIN GNR.tblGoods g ON g.ID=i.GoodsRef
    """)[0]
    quantities = _rows(cursor, """
        WITH ri AS (
          SELECT HdrRef,GoodsRef,SUM(ISNULL(Qty,0)) Qty
          FROM ICA.tblRetSupInvoiceItm GROUP BY HdrRef,GoodsRef
        ),vi AS (
          SELECT h.ID HdrRef,i.GoodsRef,SUM(ISNULL(i.TotalQty,0)) Qty
          FROM ICA.tblRetSupInvoiceHdr h JOIN Inv.tblVocherItm i ON i.HdrRef=h.InvVocherRef
          GROUP BY h.ID,i.GoodsRef
        ),x AS (
          SELECT COALESCE(ri.HdrRef,vi.HdrRef) HdrRef,
                 ISNULL(ri.Qty,0) return_qty,ISNULL(vi.Qty,0) voucher_qty,
                 CASE WHEN ri.HdrRef IS NULL THEN 'voucher_only'
                      WHEN vi.HdrRef IS NULL THEN 'return_only'
                      WHEN ABS(CONVERT(float,ri.Qty-vi.Qty))<0.0001 THEN 'exact'
                      ELSE 'mismatch' END result
          FROM ri FULL JOIN vi ON vi.HdrRef=ri.HdrRef AND vi.GoodsRef=ri.GoodsRef
        )
        SELECT result,COUNT_BIG(*) goods_groups,COUNT(DISTINCT HdrRef) headers,
               SUM(return_qty) return_qty,SUM(voucher_qty) voucher_qty,
               MAX(ABS(CONVERT(float,return_qty-voucher_qty))) maximum_difference
        FROM x GROUP BY result ORDER BY result
    """)
    source = _rows(cursor, """
        WITH r AS (
          SELECT h.ID,h.SupInvoiceRef,i.GoodsRef,SUM(ISNULL(i.Qty,0)) Qty
          FROM ICA.tblRetSupInvoiceHdr h JOIN ICA.tblRetSupInvoiceItm i ON i.HdrRef=h.ID
          WHERE h.SupInvoiceRef IS NOT NULL GROUP BY h.ID,h.SupInvoiceRef,i.GoodsRef
        ),s AS (
          SELECT HdrRef,GoodsRef,SUM(ISNULL(Qty,0)) Qty
          FROM ICA.TblSupInvoiceItm GROUP BY HdrRef,GoodsRef
        )
        SELECT COUNT_BIG(*) return_goods_groups,
               SUM(CASE WHEN s.HdrRef IS NULL THEN 1 ELSE 0 END) missing_source_goods,
               SUM(CASE WHEN s.HdrRef IS NOT NULL AND r.Qty<=s.Qty THEN 1 ELSE 0 END) within_source_qty,
               SUM(CASE WHEN s.HdrRef IS NOT NULL AND r.Qty>s.Qty THEN 1 ELSE 0 END) exceeds_source_qty,
               COUNT(DISTINCT r.ID) linked_return_headers
        FROM r LEFT JOIN s ON s.HdrRef=r.SupInvoiceRef AND s.GoodsRef=r.GoodsRef
    """)[0]
    amount = _rows(cursor, """
        WITH x AS (
          SELECT h.ID,h.SupInvoiceRef,SUM(i.TotalAmount) total_amount,
                 SUM(i.FinalEffectiveAmount) final_effective_amount
          FROM ICA.tblRetSupInvoiceHdr h JOIN ICA.tblRetSupInvoiceItm i ON i.HdrRef=h.ID
          GROUP BY h.ID,h.SupInvoiceRef
        )
        SELECT COUNT_BIG(*) returns,
               SUM(CASE WHEN ABS(CONVERT(float,total_amount-final_effective_amount))<0.01 THEN 1 ELSE 0 END) total_equals_final,
               SUM(CASE WHEN ABS(CONVERT(float,total_amount-final_effective_amount))>=0.01 THEN 1 ELSE 0 END) total_differs_final,
               SUM(total_amount) total_amount,SUM(final_effective_amount) final_effective_amount,
               SUM(CASE WHEN SupInvoiceRef IS NOT NULL THEN 1 ELSE 0 END) linked_to_source_invoice
        FROM x
    """)[0]
    return {
        "header_profile": header,
        "reference_and_inventory_integrity": integrity,
        "item_profile": items,
        "return_to_inventory_quantity_reconciliation": quantities,
        "optional_source_invoice_goods_reconciliation": source,
        "amount_profile": amount,
        "contract": (
            "Every supplier return directly references a confirmed type-55 inventory exit. "
            "SupInvoiceRef is optional provenance, not the operational inventory link."
        ),
    }


def _supplier_settlement_profile(cursor: Any) -> dict[str, Any]:
    ledger = _rows(cursor, """
        SELECT COUNT_BIG(*) settlements,COUNT(DISTINCT s.SupplierRef) suppliers,
               COUNT(DISTINCT s.SupInvoiceRef) invoices,
               SUM(CASE WHEN s.SupSettlementAmount>0 THEN 1 ELSE 0 END) positive_amount,
               SUM(CASE WHEN s.SupSettlementAmount<=0 OR s.SupSettlementAmount IS NULL THEN 1 ELSE 0 END) nonpositive_amount,
               SUM(CASE WHEN i.ID IS NULL AND s.SupInvoiceRef IS NOT NULL THEN 1 ELSE 0 END) orphan_invoice,
               SUM(CASE WHEN p.ID IS NULL AND s.SupplierRef IS NOT NULL THEN 1 ELSE 0 END) orphan_supplier,
               SUM(CASE WHEN i.ID IS NOT NULL AND i.SupplierRef<>s.SupplierRef THEN 1 ELSE 0 END) supplier_mismatch,
               SUM(CASE WHEN s.RChequeId IS NOT NULL THEN 1 ELSE 0 END) received_cheque_instrument,
               SUM(CASE WHEN s.PWithDrawId IS NOT NULL THEN 1 ELSE 0 END) withdrawal_instrument,
               SUM(CASE WHEN s.PCashId IS NOT NULL THEN 1 ELSE 0 END) cash_instrument,
               SUM(CASE WHEN s.PChequeId IS NOT NULL THEN 1 ELSE 0 END) payable_cheque_instrument,
               SUM(CASE WHEN s.DocPayId IS NOT NULL THEN 1 ELSE 0 END) accounting_document_link
        FROM Acc.tblSupSettlement s
        LEFT JOIN ICA.TblSupInvoiceHdr i ON i.ID=s.SupInvoiceRef
        LEFT JOIN GNR.tblSupplier p ON p.ID=s.SupplierRef
    """)[0]
    coverage = _rows(cursor, """
        WITH inv AS (
          SELECT h.ID,h.Status,h.TasviehDate,SUM(ISNULL(i.TotalAmount,0)) amount
          FROM ICA.TblSupInvoiceHdr h JOIN ICA.TblSupInvoiceItm i ON i.HdrRef=h.ID
          GROUP BY h.ID,h.Status,h.TasviehDate
        ),st AS (
          SELECT SupInvoiceRef,SUM(ISNULL(SupSettlementAmount,0)) settled
          FROM Acc.tblSupSettlement WHERE SupInvoiceRef IS NOT NULL GROUP BY SupInvoiceRef
        )
        SELECT inv.Status,COUNT_BIG(*) invoices,
               SUM(CASE WHEN st.SupInvoiceRef IS NULL THEN 1 ELSE 0 END) no_direct_settlement,
               SUM(CASE WHEN st.settled>0 AND st.settled<inv.amount THEN 1 ELSE 0 END) partial,
               SUM(CASE WHEN st.settled=inv.amount THEN 1 ELSE 0 END) fully_settled,
               SUM(CASE WHEN st.settled>inv.amount THEN 1 ELSE 0 END) over_settled,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(inv.TasviehDate)),'') IS NOT NULL THEN 1 ELSE 0 END) tasvieh_date_present
        FROM inv LEFT JOIN st ON st.SupInvoiceRef=inv.ID
        GROUP BY inv.Status ORDER BY inv.Status
    """)
    by_type = _rows(cursor, """
        SELECT SupSettlementTypeRef,COUNT_BIG(*) settlements,
               SUM(SupSettlementAmount) amount,
               SUM(CASE WHEN DocPayId IS NOT NULL THEN 1 ELSE 0 END) document_linked
        FROM Acc.tblSupSettlement GROUP BY SupSettlementTypeRef ORDER BY SupSettlementTypeRef
    """)
    return {
        "direct_invoice_allocation_ledger": ledger,
        "direct_allocation_coverage": coverage,
        "direct_allocation_by_type": by_type,
        "contract": (
            "tblSupSettlement is an allocation bridge, not the supplier balance ledger. "
            "Usp_GetSupplierRemAmount composes invoices, returns, payment instruments, sales, "
            "manual accounting vouchers, opening balance, and direct allocations."
        ),
    }


def _business_window(cursor: Any) -> dict[str, Any]:
    summary = _rows(cursor, f"""
        SELECT
          (SELECT COUNT_BIG(*) FROM ICA.TblSupInvoiceHdr WHERE VchDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') supplier_invoices,
          (SELECT COUNT_BIG(*) FROM ICA.TblSupInvoiceItm i JOIN ICA.TblSupInvoiceHdr h ON h.ID=i.HdrRef WHERE h.VchDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') supplier_invoice_items,
          (SELECT COUNT(DISTINCT SupplierRef) FROM ICA.TblSupInvoiceHdr WHERE VchDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') suppliers,
          (SELECT COUNT_BIG(*) FROM ICA.tblRetSupInvoiceHdr WHERE VchDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') supplier_returns,
          (SELECT COUNT_BIG(*) FROM ICA.tblRetSupInvoiceItm i JOIN ICA.tblRetSupInvoiceHdr h ON h.ID=i.HdrRef WHERE h.VchDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') supplier_return_items,
          (SELECT COUNT_BIG(*) FROM ICA.tblSupInvInvoiceRelation r JOIN ICA.TblSupInvoiceHdr h ON h.ID=r.SupInvoiceHdrRef WHERE h.VchDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') inventory_relations,
          (SELECT COUNT_BIG(*) FROM Acc.tblSupSettlement WHERE SupSettlementDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') direct_settlements
    """)[0]
    return {"from": BUSINESS_DATE_FROM, "to": BUSINESS_DATE_TO, "summary": summary}


def _data_quality(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM ICA.TblSupInvoiceHdr h LEFT JOIN GNR.tblSupplier s ON s.ID=h.SupplierRef WHERE s.ID IS NULL) orphan_supplier_invoices,
          (SELECT COUNT_BIG(*) FROM ICA.TblSupInvoiceItm i LEFT JOIN ICA.TblSupInvoiceHdr h ON h.ID=i.HdrRef WHERE h.ID IS NULL) orphan_supplier_invoice_items,
          (SELECT COUNT_BIG(*) FROM ICA.TblSupInvoiceHdr h WHERE NOT EXISTS (SELECT 1 FROM ICA.tblSupInvInvoiceRelation r WHERE r.SupInvoiceHdrRef=h.ID)) invoices_without_inventory_relation,
          (SELECT COUNT_BIG(*) FROM ICA.tblSupInvInvoiceRelation r LEFT JOIN Inv.tblVocherHdr v ON v.ID=r.InvVchHdrRef WHERE v.ID IS NULL) orphan_purchase_inventory_relations,
          (SELECT COUNT_BIG(*) FROM ICA.tblRetSupInvoiceHdr h LEFT JOIN Inv.tblVocherHdr v ON v.ID=h.InvVocherRef WHERE v.ID IS NULL) supplier_returns_without_inventory_voucher,
          (SELECT COUNT_BIG(*) FROM ICA.tblRetSupInvoiceItm i LEFT JOIN ICA.tblRetSupInvoiceHdr h ON h.ID=i.HdrRef WHERE h.ID IS NULL) orphan_supplier_return_items,
          (SELECT COUNT_BIG(*) FROM Acc.tblSupSettlement s LEFT JOIN ICA.TblSupInvoiceHdr h ON h.ID=s.SupInvoiceRef WHERE s.SupInvoiceRef IS NOT NULL AND h.ID IS NULL) orphan_direct_settlement_invoices,
          (SELECT COUNT_BIG(*) FROM ICA.tblRetSupInvRelation) unused_return_relation_rows
    """)[0]


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition,o.modify_date
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE (s.name='ICA' AND o.name IN
              ('uspLinkUnlinkSupInvoiceInv','usp_ValidateSupInvoiceAmount',
               'usp_ApplySupInvoice','BeforeRetSupInvoiceHdr',
               'vwCreateVoucherRetSupInvoice','UspRetSupInvoiceHdrBeforeInsert'))
           OR (s.name='Acc' AND o.name IN
              ('Usp_GetSupplierRemAmount','USP_SDSNET_SupplierCredit_GetList',
               'USP_SDSNET_SupplierDebit_GetList'))
           OR (s.name='dbo' AND o.name IN
              ('usp_sdsnet_RetSupInvoice_BeforeSave','usp_sdsnet_RetSupInvoice_Save'))
        ORDER BY s.name,o.name
    """)


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
            "domain": "supplier_purchase_returns_and_payables",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata and aggregate supplier-purchase evidence",
                "privacy_policy": (
                    "no supplier/contact/tax rows, comments, usernames, hostnames, credentials, "
                    "instrument identifiers, or raw settlement records"
                ),
            },
            "safety": _public_safety(private_safety),
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "reference_masters": _reference_masters(cursor),
            "supplier_invoices": _supplier_invoice_profile(cursor),
            "inventory_receipt_relation": _inventory_receipt_relation(cursor),
            "tolls_and_cost_application": _toll_and_cost_profile(cursor),
            "supplier_returns": _supplier_return_profile(cursor),
            "supplier_settlement": _supplier_settlement_profile(cursor),
            "business_window": _business_window(cursor),
            "data_quality": _data_quality(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "evidence_limits": [
                "Supplier invoice status represents application/linking, not original stock receipt confirmation.",
                "The legacy dbo.POrder path is empty in this snapshot; this does not prove it never existed elsewhere.",
                "Five inventory-only purchase goods groups require business review and are not automatically defects.",
                "Supplier-return SupInvoiceRef is optional; inventory truth is the direct type-55 voucher link.",
                "tblSupSettlement alone cannot reproduce supplier balance or payable cardex.",
                "Supplier identities, contact/tax fields, comments, raw instruments, and raw settlements are intentionally excluded.",
                "Formal dependencies do not capture dynamic SQL or every legacy Ref convention.",
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
