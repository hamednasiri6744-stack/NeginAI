"""Extract Varanegar receipt, collection, allocation, and open-invoice evidence.

The extractor is intentionally read-only. It persists schema metadata, safe
reference labels, aggregate counts, reconciliation results, and selected SQL
contracts. It never persists payer/customer rows, cheque/account/Sayad values,
device serials, comments, usernames, hostnames, credentials, or raw payment
records.
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
    {"object": "dbo.Receipt", "role": "receipt_header"},
    {"object": "dbo.ReceiptStatus", "role": "receipt_status_master"},
    {"object": "dbo.RPReason", "role": "receipt_payment_reason_master"},
    {"object": "dbo.RCash", "role": "cash_receipt_instrument"},
    {"object": "dbo.RCashDetail", "role": "cash_receipt_customer_split"},
    {"object": "dbo.RBankDraft", "role": "legacy_received_bank_draft"},
    {"object": "Acc.TblCheque", "role": "received_cheque_instrument"},
    {"object": "Acc.TblBankOrders", "role": "bank_deposit_or_transfer_instrument"},
    {"object": "Acc.tblPayments", "role": "customer_invoice_allocation_ledger"},
    {"object": "Acc.tblPayType", "role": "allocation_type_and_sign_master"},
    {"object": "SLE.tblOpenInvoice", "role": "materialized_open_invoice_projection"},
    {"object": "SLE.tblOpenInvoicePrepareHistory", "role": "per_customer_projection_refresh_log"},
    {"object": "SLE.tblOpenInvoiceLastRun", "role": "projection_full_refresh_checkpoint"},
    {"object": "NGT.CustomerCallPayments", "role": "mobile_collection_header"},
    {"object": "NGT.CustomerCallPaymentDetails", "role": "mobile_collection_allocation_detail"},
    {"object": "GNR.tblPaymentType", "role": "order_payment_type_group_master"},
    {"object": "GNR.tblPaymentUsance", "role": "order_payment_term_master"},
    {"object": "NGT.DealerPaymentTypes", "role": "dealer_allowed_payment_term_bridge"},
    {"object": "NGT.Pos", "role": "mobile_pos_device_master"},
)

BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"


def _object_ids_sql() -> str:
    return ",".join(f"OBJECT_ID(N'{item['object']}', 'U')" for item in DOMAIN_TABLES)


def _public_safety(context: dict[str, Any]) -> dict[str, Any]:
    """Retain safety evidence without persisting machine or login identity."""
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
          WHERE LOWER(c.name) LIKE '%receiptref%'
             OR LOWER(c.name) LIKE '%receiptid%'
             OR LOWER(c.name) LIKE '%receiptuniqueid%'
             OR LOWER(c.name) LIKE '%paymentref%'
             OR LOWER(c.name) LIKE '%payref%'
             OR LOWER(c.name) LIKE '%chqref%'
             OR LOWER(c.name) LIKE '%bankorderref%'
             OR LOWER(c.name) LIKE '%rcashid%'
             OR LOWER(c.name) LIKE '%openinvoice%'
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
    receipt_statuses = _decode_fields(_rows(cursor, """
        SELECT s.ReceiptStatusId,
               CONVERT(varbinary(max),s.ReceiptStatusName) ReceiptStatusName,
               COUNT_BIG(r.ReceiptId) usage
        FROM dbo.ReceiptStatus s
        LEFT JOIN dbo.Receipt r ON r.ReceiptStatusId=s.ReceiptStatusId
        GROUP BY s.ReceiptStatusId,s.ReceiptStatusName
        ORDER BY s.ReceiptStatusId
    """), ("ReceiptStatusName",))
    reasons = _decode_fields(_rows(cursor, """
        SELECT x.RPReasonId,CONVERT(varbinary(max),x.RPReasonName) RPReasonName,
               x.IsReceivable,x.IsPayable,x.IsActive,x.BuiltIn,x.IsSettlement,
               x.SettlementWayId,x.IsPayGroup,x.ByRef,x.IsChequeTransfer,
               x.ChqChangeStatus,x.GroupCharging,x.IsRPTransfer,x.RPReasonCode,
               x.IsUnknownBankOrders,COUNT_BIG(r.ReceiptId) receipt_usage
        FROM dbo.RPReason x LEFT JOIN dbo.Receipt r ON r.RPReasonId=x.RPReasonId
        GROUP BY x.RPReasonId,x.RPReasonName,x.IsReceivable,x.IsPayable,x.IsActive,
                 x.BuiltIn,x.IsSettlement,x.SettlementWayId,x.IsPayGroup,x.ByRef,
                 x.IsChequeTransfer,x.ChqChangeStatus,x.GroupCharging,x.IsRPTransfer,
                 x.RPReasonCode,x.IsUnknownBankOrders
        ORDER BY receipt_usage DESC,x.RPReasonId
    """), ("RPReasonName",))
    pay_types = _decode_fields(_rows(cursor, """
        SELECT p.ID,p.Code,CONVERT(varbinary(max),p.Name) Name,p.IsManual,p.PlusMinus,
               p.IsDisabled,p.RefToInvoice,p.PayTypeRef,p.Builtin,p.UseInSettlement,
               p.IsAutomatic,p.FactorRef,p.DontshowReport,p.IsShowCardex,p.IsUsedInFRU,
               COUNT_BIG(x.ID) payment_usage
        FROM Acc.tblPayType p LEFT JOIN Acc.tblPayments x ON x.PayTypeRef=p.ID
        GROUP BY p.ID,p.Code,p.Name,p.IsManual,p.PlusMinus,p.IsDisabled,p.RefToInvoice,
                 p.PayTypeRef,p.Builtin,p.UseInSettlement,p.IsAutomatic,p.FactorRef,
                 p.DontshowReport,p.IsShowCardex,p.IsUsedInFRU
        ORDER BY payment_usage DESC,p.ID
    """), ("Name",))
    ngt_settlement_types = _rows(cursor, """
        SELECT b.BaseValueName,b.Number_ID,COUNT_BIG(*) payment_usage
        FROM NGT.CustomerCallPayments p
        JOIN NGT.BaseValues b ON b.Id=p.SettlementTypeUniqueId
        GROUP BY b.BaseValueName,b.Number_ID ORDER BY payment_usage DESC
    """)
    return {
        "receipt_statuses": receipt_statuses,
        "receipt_payment_reasons": reasons,
        "allocation_pay_types": pay_types,
        "ngt_settlement_types_in_use": ngt_settlement_types,
    }


def _receipt_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) receipts,COUNT(DISTINCT UniqueId) distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuids,
               SUM(CASE WHEN IsManual=1 THEN 1 ELSE 0 END) manual,
               SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirm_date_present,
               SUM(CASE WHEN TourId IS NOT NULL AND TourId<>0 THEN 1 ELSE 0 END) tour_linked,
               SUM(CASE WHEN ReceiptAmount>0 THEN 1 ELSE 0 END) positive_amount,
               SUM(CASE WHEN ReceiptAmount=0 THEN 1 ELSE 0 END) zero_amount,
               SUM(CASE WHEN ReceiptAmount<0 THEN 1 ELSE 0 END) negative_amount,
               MIN(ReceiptDate) minimum_business_date,MAX(ReceiptDate) maximum_business_date
        FROM dbo.Receipt
    """)[0]
    statuses = _rows(cursor, """
        SELECT ReceiptStatusId,COUNT_BIG(*) receipts,
               SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirm_date_present,
               SUM(CASE WHEN IsManual=1 THEN 1 ELSE 0 END) manual,
               SUM(CASE WHEN TourId IS NOT NULL AND TourId<>0 THEN 1 ELSE 0 END) tour_linked
        FROM dbo.Receipt GROUP BY ReceiptStatusId ORDER BY ReceiptStatusId
    """)
    business_window = _rows(cursor, f"""
        SELECT COUNT_BIG(*) receipts,
               SUM(CASE WHEN ReceiptStatusId=2 THEN 1 ELSE 0 END) confirmed,
               SUM(CASE WHEN ReceiptStatusId=4 THEN 1 ELSE 0 END) cancelled,
               SUM(CASE WHEN IsManual=1 THEN 1 ELSE 0 END) manual,
               SUM(CASE WHEN TourId IS NOT NULL AND TourId<>0 THEN 1 ELSE 0 END) tour_linked,
               COUNT(DISTINCT RPReasonId) reasons
        FROM dbo.Receipt
        WHERE ReceiptDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
    """)[0]
    keys = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM (SELECT UniqueId FROM dbo.Receipt
             WHERE UniqueId IS NOT NULL GROUP BY UniqueId HAVING COUNT_BIG(*)>1)x)
                duplicate_uuid_groups,
          (SELECT COUNT_BIG(*) FROM (SELECT AccYearId,DCId,SaleOfficeRef,ReceiptNo
             FROM dbo.Receipt GROUP BY AccYearId,DCId,SaleOfficeRef,ReceiptNo
             HAVING COUNT_BIG(*)>1)x) duplicate_composite_number_groups,
          (SELECT SUM(CASE WHEN ReceiptNo=0 THEN 1 ELSE 0 END) FROM dbo.Receipt)
                zero_number_receipts,
          (SELECT SUM(CASE WHEN ReceiptNo>0 THEN 1 ELSE 0 END) FROM dbo.Receipt)
                positive_number_receipts
    """)[0]
    return {
        "population": population,
        "status_distribution": statuses,
        "business_window": {
            "from": BUSINESS_DATE_FROM,
            "to": BUSINESS_DATE_TO,
            "summary": business_window,
        },
        "key_quality": keys,
    }


def _receipt_instruments(cursor: Any) -> dict[str, Any]:
    composition = _rows(cursor, """
        WITH cash AS (
          SELECT ReceiptId,COUNT_BIG(*) n,SUM(RCashAmount) amount
          FROM dbo.RCash GROUP BY ReceiptId
        ),chq AS (
          SELECT ReceiptId,COUNT_BIG(*) n,SUM(ChqAmount) amount
          FROM Acc.TblCheque WHERE ReceiptId IS NOT NULL GROUP BY ReceiptId
        ),bank_order AS (
          SELECT ReceiptId,COUNT_BIG(*) n,SUM(Amount) amount
          FROM Acc.TblBankOrders WHERE ReceiptId IS NOT NULL GROUP BY ReceiptId
        ),x AS (
          SELECT r.ReceiptId,r.ReceiptAmount,
                 ISNULL(cash.n,0) cash_count,ISNULL(chq.n,0) cheque_count,
                 ISNULL(bank_order.n,0) bank_order_count,
                 ISNULL(cash.amount,0)+ISNULL(chq.amount,0)+ISNULL(bank_order.amount,0)
                   instrument_amount
          FROM dbo.Receipt r
          LEFT JOIN cash ON cash.ReceiptId=r.ReceiptId
          LEFT JOIN chq ON chq.ReceiptId=r.ReceiptId
          LEFT JOIN bank_order ON bank_order.ReceiptId=r.ReceiptId
        )
        SELECT COUNT_BIG(*) receipts,
               SUM(CASE WHEN cash_count=0 AND cheque_count=0 AND bank_order_count=0
                        THEN 1 ELSE 0 END) no_instrument,
               SUM(CASE WHEN cash_count>0 AND cheque_count=0 AND bank_order_count=0
                        THEN 1 ELSE 0 END) cash_only,
               SUM(CASE WHEN cash_count=0 AND cheque_count>0 AND bank_order_count=0
                        THEN 1 ELSE 0 END) cheque_only,
               SUM(CASE WHEN cash_count=0 AND cheque_count=0 AND bank_order_count>0
                        THEN 1 ELSE 0 END) bank_order_only,
               SUM(CASE WHEN (CASE WHEN cash_count>0 THEN 1 ELSE 0 END+
                                   CASE WHEN cheque_count>0 THEN 1 ELSE 0 END+
                                   CASE WHEN bank_order_count>0 THEN 1 ELSE 0 END)>1
                        THEN 1 ELSE 0 END) mixed,
               SUM(CASE WHEN ReceiptAmount=instrument_amount THEN 1 ELSE 0 END)
                    exact_receipt_amount,
               SUM(CASE WHEN ReceiptAmount<>instrument_amount THEN 1 ELSE 0 END)
                    mismatched_receipt_amount,
               SUM(ABS(CONVERT(decimal(38,2),ReceiptAmount)-
                       CONVERT(decimal(38,2),instrument_amount))) absolute_difference
        FROM x
    """)[0]
    cash_details = _rows(cursor, """
        WITH d AS (
          SELECT RCashId,COUNT_BIG(*) n,SUM(RCashDetailAmount) amount
          FROM dbo.RCashDetail GROUP BY RCashId
        )
        SELECT COUNT_BIG(*) cash_headers,
               SUM(CASE WHEN d.RCashId IS NULL THEN 1 ELSE 0 END) without_detail,
               SUM(CASE WHEN d.n=1 THEN 1 ELSE 0 END) one_detail,
               SUM(CASE WHEN d.n>1 THEN 1 ELSE 0 END) multiple_details,
               SUM(CASE WHEN d.amount=x.RCashAmount THEN 1 ELSE 0 END) exact_amount,
               SUM(CASE WHEN d.RCashId IS NOT NULL AND d.amount<>x.RCashAmount
                        THEN 1 ELSE 0 END) mismatched_amount,
               (SELECT COUNT_BIG(*) FROM dbo.RCashDetail z LEFT JOIN dbo.RCash x2
                  ON x2.RCashId=z.RCashId WHERE x2.RCashId IS NULL) orphan_details
        FROM dbo.RCash x LEFT JOIN d ON d.RCashId=x.RCashId
    """)[0]
    orphans = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM dbo.RCash x LEFT JOIN dbo.Receipt r
             ON r.ReceiptId=x.ReceiptId WHERE r.ReceiptId IS NULL) cash_orphans,
          (SELECT COUNT_BIG(*) FROM Acc.TblCheque x LEFT JOIN dbo.Receipt r
             ON r.ReceiptId=x.ReceiptId
             WHERE x.ReceiptId IS NOT NULL AND r.ReceiptId IS NULL) cheque_orphans,
          (SELECT COUNT_BIG(*) FROM Acc.TblBankOrders x LEFT JOIN dbo.Receipt r
             ON r.ReceiptId=x.ReceiptId
             WHERE x.ReceiptId IS NOT NULL AND r.ReceiptId IS NULL) bank_order_orphans,
          (SELECT COUNT_BIG(*) FROM Acc.TblCheque WHERE ReceiptId IS NULL)
                cheques_without_receipt,
          (SELECT COUNT_BIG(*) FROM Acc.TblBankOrders WHERE ReceiptId IS NULL)
                bank_orders_without_receipt
    """)[0]
    return {
        "receipt_composition_and_amount_reconciliation": composition,
        "cash_detail_reconciliation": cash_details,
        "orphan_checks": orphans,
    }


def _allocation_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) payments,COUNT(DISTINCT UniqueId) distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuids,
               SUM(CASE WHEN Amount>0 THEN 1 ELSE 0 END) positive_amount,
               SUM(CASE WHEN Amount=0 THEN 1 ELSE 0 END) zero_amount,
               SUM(CASE WHEN Amount<0 THEN 1 ELSE 0 END) negative_amount,
               SUM(CASE WHEN SaleRef IS NOT NULL THEN 1 ELSE 0 END) sale_linked,
               SUM(CASE WHEN ChqRef IS NOT NULL THEN 1 ELSE 0 END) cheque_linked,
               SUM(CASE WHEN BankOrderRef IS NOT NULL THEN 1 ELSE 0 END) bank_order_linked,
               SUM(CASE WHEN RCashId IS NOT NULL THEN 1 ELSE 0 END) cash_linked,
               SUM(CASE WHEN RBankDraftId IS NOT NULL THEN 1 ELSE 0 END) bank_draft_linked,
               MIN(PayDate) minimum_business_date,MAX(PayDate) maximum_business_date
        FROM Acc.tblPayments
    """)[0]
    shape = _rows(cursor, """
        SELECT
          SUM(CASE WHEN (CASE WHEN ChqRef IS NOT NULL THEN 1 ELSE 0 END+
                              CASE WHEN BankOrderRef IS NOT NULL THEN 1 ELSE 0 END+
                              CASE WHEN RCashId IS NOT NULL THEN 1 ELSE 0 END+
                              CASE WHEN RBankDraftId IS NOT NULL THEN 1 ELSE 0 END)=0
                   THEN 1 ELSE 0 END) without_receipt_instrument,
          SUM(CASE WHEN (CASE WHEN ChqRef IS NOT NULL THEN 1 ELSE 0 END+
                              CASE WHEN BankOrderRef IS NOT NULL THEN 1 ELSE 0 END+
                              CASE WHEN RCashId IS NOT NULL THEN 1 ELSE 0 END+
                              CASE WHEN RBankDraftId IS NOT NULL THEN 1 ELSE 0 END)=1
                   THEN 1 ELSE 0 END) one_receipt_instrument,
          SUM(CASE WHEN (CASE WHEN ChqRef IS NOT NULL THEN 1 ELSE 0 END+
                              CASE WHEN BankOrderRef IS NOT NULL THEN 1 ELSE 0 END+
                              CASE WHEN RCashId IS NOT NULL THEN 1 ELSE 0 END+
                              CASE WHEN RBankDraftId IS NOT NULL THEN 1 ELSE 0 END)>1
                   THEN 1 ELSE 0 END) multiple_receipt_instruments
        FROM Acc.tblPayments
    """)[0]
    receipt_mapping = _rows(cursor, """
        WITH x AS (
          SELECT p.ID,p.Amount,q.ReceiptId cheque_receipt_id,
                 b.ReceiptId bank_order_receipt_id,c.ReceiptId cash_receipt_id
          FROM Acc.tblPayments p
          LEFT JOIN Acc.TblCheque q ON q.ID=p.ChqRef
          LEFT JOIN Acc.TblBankOrders b ON b.ID=p.BankOrderRef
          LEFT JOIN dbo.RCash c ON c.RCashId=p.RCashId
        )
        SELECT COUNT_BIG(*) payments,
               SUM(CASE WHEN COALESCE(cheque_receipt_id,bank_order_receipt_id,
                                      cash_receipt_id) IS NOT NULL THEN 1 ELSE 0 END)
                    mapped_to_receipt,
               SUM(CASE WHEN cheque_receipt_id IS NOT NULL
                              AND bank_order_receipt_id IS NOT NULL
                              AND cheque_receipt_id<>bank_order_receipt_id
                          OR cheque_receipt_id IS NOT NULL
                              AND cash_receipt_id IS NOT NULL
                              AND cheque_receipt_id<>cash_receipt_id
                          OR bank_order_receipt_id IS NOT NULL
                              AND cash_receipt_id IS NOT NULL
                              AND bank_order_receipt_id<>cash_receipt_id
                        THEN 1 ELSE 0 END) conflicting_parent_receipts,
               COUNT(DISTINCT COALESCE(cheque_receipt_id,bank_order_receipt_id,
                                       cash_receipt_id)) receipts_with_allocations
        FROM x
    """)[0]
    business_window = _rows(cursor, f"""
        SELECT COUNT_BIG(*) payments,COUNT(DISTINCT CustRef) customers,
               COUNT(DISTINCT SaleRef) sales,COUNT(DISTINCT PayTypeRef) pay_types,
               SUM(CASE WHEN ChqRef IS NOT NULL THEN 1 ELSE 0 END) cheque_linked,
               SUM(CASE WHEN BankOrderRef IS NOT NULL THEN 1 ELSE 0 END) bank_order_linked,
               SUM(CASE WHEN RCashId IS NOT NULL THEN 1 ELSE 0 END) cash_linked
        FROM Acc.tblPayments
        WHERE PayDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
    """)[0]
    per_sale = _rows(cursor, """
        SELECT COUNT_BIG(*) sales,MIN(n) minimum_payments,MAX(n) maximum_payments,
               AVG(CONVERT(float,n)) average_payments,
               SUM(CASE WHEN n=1 THEN 1 ELSE 0 END) one_payment,
               SUM(CASE WHEN n>1 THEN 1 ELSE 0 END) multiple_payments
        FROM (SELECT SaleRef,COUNT_BIG(*) n FROM Acc.tblPayments
              WHERE SaleRef IS NOT NULL GROUP BY SaleRef)x
    """)[0]
    orphans = _rows(cursor, """
        SELECT SUM(CASE WHEN p.SaleRef IS NOT NULL AND s.ID IS NULL THEN 1 ELSE 0 END)
                    orphan_sales,
               SUM(CASE WHEN c.ID IS NULL THEN 1 ELSE 0 END) orphan_customers,
               SUM(CASE WHEN pt.ID IS NULL THEN 1 ELSE 0 END) orphan_pay_types,
               SUM(CASE WHEN p.ChqRef IS NOT NULL AND q.ID IS NULL THEN 1 ELSE 0 END)
                    orphan_cheques,
               SUM(CASE WHEN p.BankOrderRef IS NOT NULL AND b.ID IS NULL THEN 1 ELSE 0 END)
                    orphan_bank_orders,
               SUM(CASE WHEN p.RCashId IS NOT NULL AND r.RCashId IS NULL THEN 1 ELSE 0 END)
                    orphan_cash
        FROM Acc.tblPayments p
        LEFT JOIN SLE.tblSaleHdr s ON s.ID=p.SaleRef
        LEFT JOIN GNR.tblCust c ON c.ID=p.CustRef
        LEFT JOIN Acc.tblPayType pt ON pt.ID=p.PayTypeRef
        LEFT JOIN Acc.TblCheque q ON q.ID=p.ChqRef
        LEFT JOIN Acc.TblBankOrders b ON b.ID=p.BankOrderRef
        LEFT JOIN dbo.RCash r ON r.RCashId=p.RCashId
    """)[0]
    return {
        "population": population,
        "instrument_link_shape": shape,
        "receipt_mapping": receipt_mapping,
        "business_window": {
            "from": BUSINESS_DATE_FROM,
            "to": BUSINESS_DATE_TO,
            "summary": business_window,
        },
        "payments_per_sale": per_sale,
        "orphan_checks": orphans,
    }


def _instrument_allocation(cursor: Any) -> dict[str, Any]:
    cash = _rows(cursor, """
        WITH p AS (
          SELECT RCashId,SUM(Amount) allocated FROM Acc.tblPayments
          WHERE RCashId IS NOT NULL GROUP BY RCashId
        )
        SELECT COUNT_BIG(*) instruments,
               SUM(CASE WHEN p.RCashId IS NULL THEN 1 ELSE 0 END) without_allocation,
               SUM(CASE WHEN p.allocated=x.RCashAmount THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN p.allocated<x.RCashAmount THEN 1 ELSE 0 END) underallocated,
               SUM(CASE WHEN p.allocated>x.RCashAmount THEN 1 ELSE 0 END) overallocated
        FROM dbo.RCash x LEFT JOIN p ON p.RCashId=x.RCashId
    """)[0]
    cheque = _rows(cursor, """
        WITH p AS (
          SELECT ChqRef,SUM(Amount) allocated FROM Acc.tblPayments
          WHERE ChqRef IS NOT NULL GROUP BY ChqRef
        )
        SELECT COUNT_BIG(*) instruments,
               SUM(CASE WHEN p.ChqRef IS NULL THEN 1 ELSE 0 END) without_allocation,
               SUM(CASE WHEN p.allocated=x.ChqAmount THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN p.allocated<x.ChqAmount THEN 1 ELSE 0 END) underallocated,
               SUM(CASE WHEN p.allocated>x.ChqAmount THEN 1 ELSE 0 END) overallocated
        FROM Acc.TblCheque x LEFT JOIN p ON p.ChqRef=x.ID
    """)[0]
    bank_order = _rows(cursor, """
        WITH p AS (
          SELECT BankOrderRef,SUM(Amount) allocated FROM Acc.tblPayments
          WHERE BankOrderRef IS NOT NULL GROUP BY BankOrderRef
        )
        SELECT COUNT_BIG(*) instruments,
               SUM(CASE WHEN p.BankOrderRef IS NULL THEN 1 ELSE 0 END) without_allocation,
               SUM(CASE WHEN p.allocated=x.Amount THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN p.allocated<x.Amount THEN 1 ELSE 0 END) underallocated,
               SUM(CASE WHEN p.allocated>x.Amount THEN 1 ELSE 0 END) overallocated
        FROM Acc.TblBankOrders x LEFT JOIN p ON p.BankOrderRef=x.ID
    """)[0]
    receipt = _rows(cursor, """
        WITH cash AS (SELECT RCashId,ReceiptId FROM dbo.RCash),
        chq AS (SELECT ID,ReceiptId FROM Acc.TblCheque),
        bank_order AS (SELECT ID,ReceiptId FROM Acc.TblBankOrders),
        allocation AS (
          SELECT COALESCE(cash.ReceiptId,chq.ReceiptId,bank_order.ReceiptId) ReceiptId,
                 SUM(p.Amount) allocated
          FROM Acc.tblPayments p
          LEFT JOIN cash ON cash.RCashId=p.RCashId
          LEFT JOIN chq ON chq.ID=p.ChqRef
          LEFT JOIN bank_order ON bank_order.ID=p.BankOrderRef
          WHERE cash.ReceiptId IS NOT NULL OR chq.ReceiptId IS NOT NULL
             OR bank_order.ReceiptId IS NOT NULL
          GROUP BY COALESCE(cash.ReceiptId,chq.ReceiptId,bank_order.ReceiptId)
        )
        SELECT COUNT_BIG(*) receipts,
               SUM(CASE WHEN a.ReceiptId IS NULL THEN 1 ELSE 0 END) without_allocation,
               SUM(CASE WHEN a.allocated=r.ReceiptAmount THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN a.allocated<r.ReceiptAmount THEN 1 ELSE 0 END) underallocated,
               SUM(CASE WHEN a.allocated>r.ReceiptAmount THEN 1 ELSE 0 END) overallocated
        FROM dbo.Receipt r LEFT JOIN allocation a ON a.ReceiptId=r.ReceiptId
    """)[0]
    return {"cash": cash, "cheque": cheque, "bank_order": bank_order, "receipt": receipt}


def _open_invoice_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT ID) distinct_ids,
               SUM(CASE WHEN OpenAmount>0 THEN 1 ELSE 0 END) positive_open,
               SUM(CASE WHEN OpenAmount=0 THEN 1 ELSE 0 END) zero_open,
               SUM(CASE WHEN OpenAmount<0 THEN 1 ELSE 0 END) negative_open,
               SUM(CASE WHEN PayAmount IS NULL THEN 1 ELSE 0 END) null_pay_amount,
               SUM(CASE WHEN RetSaleAmount<>0 THEN 1 ELSE 0 END) return_rows,
               SUM(CASE WHEN RetChequeRemainAmount<>0 THEN 1 ELSE 0 END)
                    returned_cheque_rows,
               SUM(CASE WHEN LastPayDate IS NOT NULL THEN 1 ELSE 0 END)
                    last_pay_date_present,
               SUM(CASE WHEN PassDate IS NOT NULL THEN 1 ELSE 0 END) pass_date_present,
               MIN(SaleDate) minimum_sale_date,MAX(SaleDate) maximum_sale_date,
               MIN(ExecTime) minimum_execution_time,MAX(ExecTime) maximum_execution_time
        FROM SLE.tblOpenInvoice
    """)[0]
    formula = _rows(cursor, """
        SELECT COUNT_BIG(*) rows,
               SUM(CASE WHEN OpenAmount=TotalAmount-ISNULL(PayAmount,0)
                        THEN 1 ELSE 0 END) exact_official_projection_formula,
               SUM(CASE WHEN OpenAmount<>TotalAmount-ISNULL(PayAmount,0)
                        THEN 1 ELSE 0 END) mismatched_official_projection_formula,
               SUM(CASE WHEN OpenAmount<=0 AND PassDate IS NOT NULL
                        THEN 1 ELSE 0 END) closed_with_pass_date,
               SUM(CASE WHEN OpenAmount<=0 AND PassDate IS NULL
                        THEN 1 ELSE 0 END) closed_without_pass_date,
               SUM(CASE WHEN OpenAmount>0 AND PassDate IS NOT NULL
                        THEN 1 ELSE 0 END) open_with_pass_date
        FROM SLE.tblOpenInvoice
    """)[0]
    naive_comparison = _rows(cursor, """
        WITH payment_sum AS (
          SELECT x.SaleRef,SUM(x.Amount) raw_amount,
                 SUM(x.Amount*t.PlusMinus) signed_amount
          FROM Acc.tblPayments x JOIN Acc.tblPayType t ON t.ID=x.PayTypeRef
          WHERE x.SaleRef IS NOT NULL GROUP BY x.SaleRef
        )
        SELECT COUNT_BIG(*) invoice_rows,
               SUM(CASE WHEN ISNULL(o.PayAmount,0)=ISNULL(p.raw_amount,0)
                        THEN 1 ELSE 0 END) raw_sum_exact,
               SUM(CASE WHEN ISNULL(o.PayAmount,0)<>ISNULL(p.raw_amount,0)
                        THEN 1 ELSE 0 END) raw_sum_mismatch,
               SUM(CASE WHEN ISNULL(o.PayAmount,0)=ISNULL(p.signed_amount,0)
                        THEN 1 ELSE 0 END) signed_sum_exact,
               SUM(CASE WHEN ISNULL(o.PayAmount,0)<>ISNULL(p.signed_amount,0)
                        THEN 1 ELSE 0 END) signed_sum_mismatch,
               SUM(ABS(CONVERT(decimal(38,2),ISNULL(o.PayAmount,0))-
                       CONVERT(decimal(38,2),ISNULL(p.raw_amount,0)))) raw_absolute_difference,
               SUM(ABS(CONVERT(decimal(38,2),ISNULL(o.PayAmount,0))-
                       CONVERT(decimal(38,2),ISNULL(p.signed_amount,0))))
                    signed_absolute_difference
        FROM SLE.tblOpenInvoice o LEFT JOIN payment_sum p ON p.SaleRef=o.ID
    """)[0]
    coverage = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr WHERE CancelFlag=0) active_sales,
          (SELECT COUNT_BIG(*) FROM SLE.tblOpenInvoice) projection_rows,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr s WHERE s.CancelFlag=0
             AND NOT EXISTS(SELECT 1 FROM SLE.tblOpenInvoice o WHERE o.ID=s.ID))
                active_sales_missing_from_projection,
          (SELECT COUNT_BIG(*) FROM SLE.tblOpenInvoice o LEFT JOIN SLE.tblSaleHdr s
             ON s.ID=o.ID WHERE s.ID IS NULL) orphan_projection_rows,
          (SELECT COUNT_BIG(*) FROM SLE.tblOpenInvoice o JOIN SLE.tblSaleHdr s
             ON s.ID=o.ID WHERE s.CancelFlag<>0) cancelled_sales_in_projection
    """)[0]
    refresh_history = _rows(cursor, """
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT CustRef) customers,
               COUNT(DISTINCT DealerRef) dealers,
               SUM(CASE WHEN CustRef IS NULL THEN 1 ELSE 0 END) null_customer,
               SUM(CASE WHEN DealerRef IS NULL THEN 1 ELSE 0 END) null_dealer,
               MIN(PrepareTime) minimum_prepare_time,MAX(PrepareTime) maximum_prepare_time
        FROM SLE.tblOpenInvoicePrepareHistory
    """)[0]
    last_run = _rows(cursor, """
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT DCRef) distribution_centers,
               MIN(LastRun) minimum_last_run,MAX(LastRun) maximum_last_run,
               MIN(DATEDIFF(millisecond,StartTime,EndTime)) minimum_duration_ms,
               MAX(DATEDIFF(millisecond,StartTime,EndTime)) maximum_duration_ms
        FROM SLE.tblOpenInvoiceLastRun
    """)[0]
    return {
        "population": population,
        "projection_formula_reconciliation": formula,
        "naive_payment_sum_comparison": naive_comparison,
        "sale_coverage": coverage,
        "per_customer_prepare_history": refresh_history,
        "full_refresh_checkpoint": last_run,
    }


def _ngt_crosswalk(cursor: Any) -> dict[str, Any]:
    payments = _rows(cursor, """
        SELECT COUNT_BIG(*) payments,COUNT(DISTINCT Id) distinct_ids,
               SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed,
               SUM(CASE WHEN Amount>0 THEN 1 ELSE 0 END) positive_amount,
               SUM(CASE WHEN Amount=0 THEN 1 ELSE 0 END) zero_amount,
               SUM(CASE WHEN Amount<0 THEN 1 ELSE 0 END) negative_amount,
               SUM(CASE WHEN BackOfficeReceiptUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                    receipt_uuid_present,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(BackOfficeReceiptRef)),'') IS NOT NULL
                        THEN 1 ELSE 0 END) receipt_ref_present,
               COUNT(DISTINCT SettlementTypeUniqueId) settlement_types,
               MIN(Date) minimum_payment_date,MAX(Date) maximum_payment_date,
               MIN(CreatedDate) minimum_created_date,MAX(CreatedDate) maximum_created_date
        FROM NGT.CustomerCallPayments
    """)[0]
    parent_crosswalk = _rows(cursor, """
        SELECT COUNT_BIG(*) payments,
               SUM(CASE WHEN cc.Id IS NULL THEN 1 ELSE 0 END) orphan_customer_calls,
               SUM(CASE WHEN by_uuid.ReceiptId IS NOT NULL THEN 1 ELSE 0 END)
                    uuid_receipt_matches,
               SUM(CASE WHEN by_ref.ReceiptId IS NOT NULL THEN 1 ELSE 0 END)
                    numeric_receipt_matches,
               SUM(CASE WHEN by_uuid.ReceiptId=by_ref.ReceiptId THEN 1 ELSE 0 END)
                    receipt_id_uuid_agree,
               SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL
                              AND by_uuid.ReceiptId IS NULL THEN 1 ELSE 0 END)
                    unmatched_receipt_uuid,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(p.BackOfficeReceiptRef)),'') IS NOT NULL
                              AND by_ref.ReceiptId IS NULL THEN 1 ELSE 0 END)
                    unmatched_receipt_ref
        FROM NGT.CustomerCallPayments p
        LEFT JOIN NGT.CustomerCalls cc ON cc.Id=p.CustomerCallUniqueId
        LEFT JOIN dbo.Receipt by_uuid ON by_uuid.UniqueId=p.BackOfficeReceiptUniqueId
        LEFT JOIN dbo.Receipt by_ref ON by_ref.ReceiptId=TRY_CONVERT(int,p.BackOfficeReceiptRef)
    """)[0]
    details = _rows(cursor, """
        SELECT COUNT_BIG(*) details,COUNT(DISTINCT d.Id) distinct_ids,
               SUM(CASE WHEN d.IsRemoved=1 THEN 1 ELSE 0 END) removed,
               SUM(CASE WHEN p.Id IS NULL THEN 1 ELSE 0 END) orphan_parent,
               SUM(CASE WHEN d.BackOfficeSaleId IS NOT NULL THEN 1 ELSE 0 END)
                    sale_uuid_present,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(d.SaleRef)),'') IS NOT NULL
                        THEN 1 ELSE 0 END) sale_ref_present,
               SUM(CASE WHEN by_uuid.ID IS NOT NULL THEN 1 ELSE 0 END) uuid_sale_matches,
               SUM(CASE WHEN by_ref.ID IS NOT NULL THEN 1 ELSE 0 END) numeric_sale_matches,
               SUM(CASE WHEN by_uuid.ID=by_ref.ID THEN 1 ELSE 0 END) sale_id_uuid_agree,
               SUM(CASE WHEN d.IsOldInvoice=1 THEN 1 ELSE 0 END) old_invoice,
               SUM(CASE WHEN d.PaidAmount>0 THEN 1 ELSE 0 END) positive_paid_amount,
               SUM(CASE WHEN d.PaidAmount=0 THEN 1 ELSE 0 END) zero_paid_amount,
               SUM(CASE WHEN d.PaidAmount<0 THEN 1 ELSE 0 END) negative_paid_amount
        FROM NGT.CustomerCallPaymentDetails d
        LEFT JOIN NGT.CustomerCallPayments p ON p.Id=d.CustomerCallPaymentUniqueId
        LEFT JOIN SLE.tblSaleHdr by_uuid ON by_uuid.UniqueId=d.BackOfficeSaleId
        LEFT JOIN SLE.tblSaleHdr by_ref ON by_ref.ID=TRY_CONVERT(int,d.SaleRef)
    """)[0]
    detail_reconciliation = _rows(cursor, """
        WITH detail_sum AS (
          SELECT CustomerCallPaymentUniqueId,COUNT_BIG(*) detail_count,SUM(PaidAmount) paid
          FROM NGT.CustomerCallPaymentDetails WHERE IsRemoved=0
          GROUP BY CustomerCallPaymentUniqueId
        )
        SELECT COUNT_BIG(*) payments,
               SUM(CASE WHEN d.CustomerCallPaymentUniqueId IS NULL THEN 1 ELSE 0 END)
                    without_detail,
               SUM(CASE WHEN d.detail_count=1 THEN 1 ELSE 0 END) one_detail,
               SUM(CASE WHEN d.detail_count>1 THEN 1 ELSE 0 END) multiple_details,
               SUM(CASE WHEN ABS(CONVERT(float,p.Amount)-ISNULL(d.paid,0))<0.01
                        THEN 1 ELSE 0 END) amount_exact_to_cent,
               SUM(CASE WHEN ABS(CONVERT(float,p.Amount)-ISNULL(d.paid,0))>=0.01
                        THEN 1 ELSE 0 END) amount_mismatch_to_cent,
               SUM(CASE WHEN d.paid<p.Amount THEN 1 ELSE 0 END) underallocated,
               SUM(CASE WHEN d.paid>p.Amount THEN 1 ELSE 0 END) overallocated
        FROM NGT.CustomerCallPayments p LEFT JOIN detail_sum d
          ON d.CustomerCallPaymentUniqueId=p.Id
        WHERE p.IsRemoved=0
    """)[0]
    backoffice_receipt = _rows(cursor, """
        SELECT COUNT_BIG(*) linked,
               SUM(CASE WHEN ABS(CONVERT(float,p.Amount)-CONVERT(float,r.ReceiptAmount))<0.01
                        THEN 1 ELSE 0 END) amount_exact_to_cent,
               SUM(CASE WHEN ABS(CONVERT(float,p.Amount)-CONVERT(float,r.ReceiptAmount))>=0.01
                        THEN 1 ELSE 0 END) amount_mismatch_to_cent,
               SUM(CASE WHEN TRY_CONVERT(int,p.BackOfficeReceiptNo)=r.ReceiptNo
                        THEN 1 ELSE 0 END) receipt_number_agrees,
               SUM(CASE WHEN r.ReceiptStatusId=2 THEN 1 ELSE 0 END) confirmed_status,
               COUNT(DISTINCT r.ReceiptId) receipts,
               COUNT(DISTINCT r.RPReasonId) receipt_reasons
        FROM NGT.CustomerCallPayments p
        JOIN dbo.Receipt r ON r.UniqueId=p.BackOfficeReceiptUniqueId
    """)[0]
    return {
        "payment_headers": payments,
        "customer_call_and_receipt_crosswalk": parent_crosswalk,
        "payment_details_and_sale_crosswalk": details,
        "header_detail_amount_reconciliation": detail_reconciliation,
        "linked_backoffice_receipt_reconciliation": backoffice_receipt,
    }


def _ngt_payment_configuration(cursor: Any) -> dict[str, Any]:
    summary = _rows(cursor, """
        SELECT COUNT_BIG(*) payment_terms,
               SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed,
               SUM(CASE WHEN IsRemoved=0 AND AllowReceipt=1 THEN 1 ELSE 0 END)
                    active_allow_receipt,
               COUNT(DISTINCT CASE WHEN IsRemoved=0 THEN GroupBackOfficeId END) active_groups,
               MIN(CASE WHEN IsRemoved=0 THEN PaymentTime END) active_minimum_payment_time,
               MAX(CASE WHEN IsRemoved=0 THEN PaymentTime END) active_maximum_payment_time
        FROM NGT.PaymentTypeOrders
    """)[0]
    active_terms = _decode_fields(_rows(cursor, """
        SELECT CONVERT(varbinary(max),PaymentTypeOrderName) PaymentTypeOrderName,
               BackOfficeId,PaymentDeadLine,PaymentTime,GroupBackOfficeId,Code,AllowReceipt
        FROM NGT.PaymentTypeOrders WHERE IsRemoved=0
        ORDER BY GroupBackOfficeId,PaymentTime
    """), ("PaymentTypeOrderName",))
    dealer_mapping = _rows(cursor, """
        SELECT COUNT_BIG(*) mappings,COUNT(DISTINCT d.DealerUniqueId) dealers,
               COUNT(DISTINCT d.PaymentTypeOrderUniqueId) payment_types,
               SUM(CASE WHEN d.IsRemoved=1 THEN 1 ELSE 0 END) removed,
               SUM(CASE WHEN p.Id IS NULL THEN 1 ELSE 0 END) orphan_payment_type,
               SUM(CASE WHEN p.IsRemoved=1 AND d.IsRemoved=0 THEN 1 ELSE 0 END)
                    active_mapping_to_removed_type
        FROM NGT.DealerPaymentTypes d
        LEFT JOIN NGT.PaymentTypeOrders p ON p.Id=d.PaymentTypeOrderUniqueId
    """)[0]
    pos = _rows(cursor, """
        SELECT COUNT_BIG(*) devices,SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed,
               COUNT(DISTINCT BankAccountUniqueId) bank_accounts,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(DeviceSerial)),'') IS NOT NULL
                        THEN 1 ELSE 0 END) serial_present
        FROM NGT.Pos
    """)[0]
    return {
        "payment_term_summary": summary,
        "active_payment_terms": active_terms,
        "dealer_payment_term_bridge": dealer_mapping,
        "pos_summary_without_device_values": pos,
    }


def _data_quality(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM (SELECT UniqueId FROM Acc.tblPayments
             WHERE UniqueId IS NOT NULL GROUP BY UniqueId HAVING COUNT_BIG(*)>1)x)
                duplicate_payment_uuid_groups,
          (SELECT COUNT_BIG(*) FROM dbo.RBankDraft) legacy_received_bank_drafts,
          (SELECT COUNT_BIG(*) FROM dbo.Receipt WHERE ReceiptStatusId=2
             AND ConfirmDate IS NULL) confirmed_status_without_confirm_timestamp,
          (SELECT COUNT_BIG(*) FROM dbo.Receipt WHERE ReceiptStatusId<>2
             AND ConfirmDate IS NOT NULL) nonconfirmed_status_with_confirm_timestamp,
          (SELECT COUNT_BIG(*) FROM SLE.tblOpenInvoice WHERE OpenAmount<0)
                negative_open_invoice_rows,
          (SELECT COUNT_BIG(*) FROM SLE.tblOpenInvoice WHERE OpenAmount>0
             AND PassDate IS NOT NULL) positive_open_invoice_with_pass_date,
          (SELECT COUNT_BIG(*) FROM NGT.DealerPaymentTypes d
             JOIN NGT.PaymentTypeOrders p ON p.Id=d.PaymentTypeOrderUniqueId
             WHERE d.IsRemoved=0 AND p.IsRemoved=1) active_dealer_links_to_removed_terms
    """)[0]


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition,o.modify_date
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE (s.name='SLE' AND o.name='usp_Prepare_OpenInvoice')
           OR (s.name='Acc' AND o.name IN
              ('usp_GetSalePayAmount','GetSalePayAmount','GetRetSalePayAmount',
               'GetRetChequeRemAmount','vwtblPayments','CheckReceiptRemainAmount',
               'Receipt_settlement'))
           OR (s.name='dbo' AND o.name IN ('RCheque','RCheque2'))
           OR (s.name='FRU' AND o.name='CustomerCallPaymentsModel')
           OR (s.name='NGT' AND o.name='PaymentTypeOrders')
        ORDER BY s.name,o.name
    """)


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        private_safety = _assert_safe_target(cursor)
        tables = [_table_metadata(cursor, x["object"], x["role"]) for x in DOMAIN_TABLES]
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "collections_payments_and_open_invoices",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata and aggregate collection evidence",
                "privacy_policy": (
                    "no payer/customer rows, cheque/account/Sayad values, device serials, "
                    "comments, usernames, hostnames, credentials, or raw payments"
                ),
            },
            "safety": _public_safety(private_safety),
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "reference_masters": _reference_masters(cursor),
            "receipts": _receipt_profile(cursor),
            "receipt_instruments": _receipt_instruments(cursor),
            "allocation_ledger": _allocation_profile(cursor),
            "instrument_allocation": _instrument_allocation(cursor),
            "open_invoice_projection": _open_invoice_profile(cursor),
            "ngt_crosswalk": _ngt_crosswalk(cursor),
            "ngt_payment_configuration": _ngt_payment_configuration(cursor),
            "data_quality": _data_quality(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "evidence_limits": [
                "Receipt is the collection header; tblPayments is an allocation and adjustment ledger, not a cash ledger.",
                "OpenInvoice is a materialized projection. Its PayAmount must follow the official procedure, including cheque state and return/settlement rules.",
                "Receipt status and ConfirmDate disagree for legacy rows; status is authoritative for workflow and the timestamp remains optional evidence.",
                "A mobile payment can exist before a back-office receipt or sale crosswalk is populated.",
                "NGT linked payment amount is not generally equal to the linked team-settlement receipt amount.",
                "Device serials, cheque/account/Sayad fields, payer/customer identity, and raw monetary records are intentionally excluded.",
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
