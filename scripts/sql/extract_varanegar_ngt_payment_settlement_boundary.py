"""Extract a privacy-safe NGT payment and settlement boundary from the clone.

Only catalog metadata, semantic reference labels, aggregate counts, and module
fingerprints are persisted. No customer, user, cheque, Sayad, account, device,
comment, configuration, credential, or raw business-row value is retained.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


TARGET_TABLES = (
    "NGT.CustomerCallPayments",
    "NGT.CustomerCallPaymentDetails",
    "NGT.PaymentTypeOrders",
    "NGT.DealerPaymentTypes",
    "NGT.Pos",
)


def _public_safety(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "READ_ONLY_CLONE_CATALOG_AND_ANONYMOUS_STATE_AGGREGATES",
        "target_is_local": True,
        "database_name": context["database_name"],
        "expected_analysis_login_verified": True,
        "database_updateability": context["updateability"],
        "can_select": context["can_select"],
        "can_view_definition": context["can_view_definition"],
        "can_update": context["can_update"],
        "denies_data_writes": context["denies_data_writes"],
        "stored_procedure_or_application_command_executions": 0,
        "business_rows_customer_user_cheque_sayad_account_device_comment_configuration_values_or_identifiers_persisted": 0,
        "sql_definitions_persisted": 0,
        "safe_schema_table_column_status_label_and_module_identifiers_persisted": True,
        "source_or_target_state_changed": 0,
    }


def _catalog(cursor: Any) -> dict[str, Any]:
    objects = ",".join(f"OBJECT_ID(N'{name}', 'U')" for name in TARGET_TABLES)
    columns = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
               TYPE_NAME(c.user_type_id) data_type,c.max_length,c.precision,c.scale,
               c.is_nullable,c.is_identity
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        WHERE t.object_id IN ({objects})
        ORDER BY s.name,t.name,c.column_id
        """,
    )
    indexes = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,i.name index_name,i.is_primary_key,
               i.is_unique,i.is_unique_constraint,i.type_desc,i.has_filter,
               ic.key_ordinal,c.name column_name
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.indexes i ON i.object_id=t.object_id AND i.index_id>0
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE t.object_id IN ({objects}) AND ic.is_included_column=0
        ORDER BY s.name,t.name,i.index_id,ic.key_ordinal
        """,
    )
    foreign_keys = _rows(
        cursor,
        f"""
        SELECT fk.name constraint_name,
               OBJECT_SCHEMA_NAME(fk.parent_object_id) parent_schema,
               OBJECT_NAME(fk.parent_object_id) parent_table,pc.name parent_column,
               OBJECT_SCHEMA_NAME(fk.referenced_object_id) referenced_schema,
               OBJECT_NAME(fk.referenced_object_id) referenced_table,rc.name referenced_column,
               fk.is_disabled,fk.is_not_trusted,
               fk.delete_referential_action_desc on_delete,
               fk.update_referential_action_desc on_update
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id
                           AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id
                           AND rc.column_id=fkc.referenced_column_id
        WHERE fk.parent_object_id IN ({objects})
        ORDER BY parent_schema,parent_table,fk.name,fkc.constraint_column_id
        """,
    )
    triggers = _rows(
        cursor,
        f"""
        SELECT OBJECT_SCHEMA_NAME(tr.parent_id) parent_schema,
               OBJECT_NAME(tr.parent_id) parent_table,tr.name trigger_name,
               tr.is_disabled,tr.is_instead_of_trigger,
               CONVERT(varchar(64),HASHBYTES('SHA2_256',CONVERT(varbinary(max),m.definition)),2)
                    definition_sha256,
               LEN(m.definition) definition_length
        FROM sys.triggers tr LEFT JOIN sys.sql_modules m ON m.object_id=tr.object_id
        WHERE tr.parent_id IN ({objects})
        ORDER BY parent_schema,parent_table,tr.name
        """,
    )
    modules = _rows(
        cursor,
        f"""
        WITH target_modules AS (
          SELECT DISTINCT d.referencing_id
          FROM sys.sql_expression_dependencies d
          WHERE d.referenced_id IN ({objects})
          UNION
          SELECT DISTINCT m.object_id
          FROM sys.sql_modules m
          WHERE m.definition LIKE '%NGT.CustomerCallPayment%'
             OR m.definition LIKE '%NGT.PaymentTypeOrder%'
             OR m.definition LIKE '%NGT.DealerPaymentType%'
        )
        SELECT OBJECT_SCHEMA_NAME(o.object_id) schema_name,o.name module_name,
               o.type_desc,o.modify_date,
               CONVERT(varchar(64),HASHBYTES('SHA2_256',CONVERT(varbinary(max),m.definition)),2)
                    definition_sha256,
               LEN(m.definition) definition_length,
               (LEN(UPPER(m.definition))-LEN(REPLACE(UPPER(m.definition),'BEGIN TRAN','')))
                    /LEN('BEGIN TRAN') begin_transaction_tokens,
               (LEN(UPPER(m.definition))-LEN(REPLACE(UPPER(m.definition),'COMMIT TRAN','')))
                    /LEN('COMMIT TRAN') commit_transaction_tokens,
               (LEN(UPPER(m.definition))-LEN(REPLACE(UPPER(m.definition),'ROLLBACK TRAN','')))
                    /LEN('ROLLBACK TRAN') rollback_transaction_tokens
        FROM target_modules x JOIN sys.objects o ON o.object_id=x.referencing_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        ORDER BY schema_name,module_name
        """,
    )
    return {
        "columns": columns,
        "indexes": indexes,
        "foreign_keys": foreign_keys,
        "triggers": triggers,
        "sql_module_fingerprints": modules,
    }


def _population(cursor: Any) -> dict[str, Any]:
    headers = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) headers,
               SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed,
               SUM(CASE WHEN Amount>0 THEN 1 ELSE 0 END) positive_amount,
               SUM(CASE WHEN Amount=0 THEN 1 ELSE 0 END) zero_amount,
               SUM(CASE WHEN Amount<0 THEN 1 ELSE 0 END) negative_amount,
               COUNT(DISTINCT CustomerCallUniqueId) customer_calls,
               COUNT(DISTINCT SettlementTypeUniqueId) settlement_types,
               SUM(CASE WHEN BackOfficeReceiptUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                    receipt_uuid_present,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(BackOfficeReceiptRef)),'') IS NOT NULL
                        THEN 1 ELSE 0 END) receipt_ref_present,
               MIN(Date) minimum_payment_date,MAX(Date) maximum_payment_date,
               MIN(CreatedDate) minimum_created_date,MAX(CreatedDate) maximum_created_date,
               MAX(ConcurrencyCheckField) maximum_concurrency_version
        FROM NGT.CustomerCallPayments
        """,
    )[0]
    details = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) details,
               SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed,
               COUNT(DISTINCT CustomerCallPaymentUniqueId) payment_headers,
               SUM(CASE WHEN PaidAmount>0 THEN 1 ELSE 0 END) positive_paid_amount,
               SUM(CASE WHEN PaidAmount=0 THEN 1 ELSE 0 END) zero_paid_amount,
               SUM(CASE WHEN PaidAmount<0 THEN 1 ELSE 0 END) negative_paid_amount,
               SUM(CASE WHEN IsOldInvoice=1 THEN 1 ELSE 0 END) old_invoice,
               SUM(CASE WHEN CustomerCallOrderUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                    order_reference_present,
               SUM(CASE WHEN BackOfficeSaleId IS NOT NULL THEN 1 ELSE 0 END)
                    sale_uuid_present,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(SaleRef)),'') IS NOT NULL THEN 1 ELSE 0 END)
                    sale_ref_present,
               MAX(ConcurrencyCheckField) maximum_concurrency_version
        FROM NGT.CustomerCallPaymentDetails
        """,
    )[0]
    monthly = _rows(
        cursor,
        """
        WITH max_date AS (
          SELECT DATEFROMPARTS(YEAR(MAX(Date)),MONTH(MAX(Date)),1) maximum_month
          FROM NGT.CustomerCallPayments
        )
        SELECT CONVERT(char(7),p.Date,126) calendar_month,b.BaseValueName settlement_type,
               COUNT_BIG(*) payments,
               SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                    receipt_linked
        FROM NGT.CustomerCallPayments p
        JOIN NGT.BaseValues b ON b.Id=p.SettlementTypeUniqueId
        CROSS JOIN max_date x
        WHERE p.Date>=DATEADD(month,-5,x.maximum_month)
        GROUP BY CONVERT(char(7),p.Date,126),b.BaseValueName
        ORDER BY calendar_month,settlement_type
        """,
    )
    settlement = _rows(
        cursor,
        """
        SELECT b.BaseValueName settlement_type,bt.BaseTypeName base_type,
               COUNT_BIG(*) payments,
               SUM(CASE WHEN p.IsRemoved=0 THEN 1 ELSE 0 END) active,
               SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                    receipt_linked
        FROM NGT.CustomerCallPayments p
        LEFT JOIN NGT.BaseValues b ON b.Id=p.SettlementTypeUniqueId
        LEFT JOIN NGT.BaseTypes bt ON bt.Id=b.BaseTypeId
        GROUP BY b.BaseValueName,bt.BaseTypeName
        ORDER BY payments DESC,settlement_type
        """,
    )
    return {
        "payment_headers": headers,
        "payment_details": details,
        "recent_six_calendar_months_by_settlement_type": monthly,
        "semantic_settlement_type_usage": settlement,
    }


def _integrity(cursor: Any) -> dict[str, Any]:
    referential = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPayments p
           LEFT JOIN NGT.CustomerCalls c ON c.Id=p.CustomerCallUniqueId
           WHERE c.Id IS NULL) orphan_payment_call,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPayments p
           JOIN NGT.CustomerCalls c ON c.Id=p.CustomerCallUniqueId
           WHERE p.IsRemoved=0 AND c.IsRemoved=1) active_payment_removed_call,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPayments p
           JOIN NGT.CustomerCalls c ON c.Id=p.CustomerCallUniqueId
           WHERE p.ApplicationOwnerId<>c.ApplicationOwnerId
              OR p.DataOwnerId<>c.DataOwnerId
              OR p.DataOwnerCenterId<>c.DataOwnerCenterId) payment_call_scope_mismatch,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPaymentDetails d
           LEFT JOIN NGT.CustomerCallPayments p ON p.Id=d.CustomerCallPaymentUniqueId
           WHERE p.Id IS NULL) orphan_detail_payment,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPaymentDetails d
           JOIN NGT.CustomerCallPayments p ON p.Id=d.CustomerCallPaymentUniqueId
           WHERE d.IsRemoved=0 AND p.IsRemoved=1) active_detail_removed_payment,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPaymentDetails d
           JOIN NGT.CustomerCallPayments p ON p.Id=d.CustomerCallPaymentUniqueId
           WHERE d.ApplicationOwnerId<>p.ApplicationOwnerId
              OR d.DataOwnerId<>p.DataOwnerId
              OR d.DataOwnerCenterId<>p.DataOwnerCenterId) detail_payment_scope_mismatch,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPaymentDetails d
           LEFT JOIN NGT.CustomerCallOrders o ON o.Id=d.CustomerCallOrderUniqueId
           WHERE d.CustomerCallOrderUniqueId IS NOT NULL AND o.Id IS NULL)
                orphan_detail_order,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPaymentDetails d
           JOIN NGT.CustomerCallOrders o ON o.Id=d.CustomerCallOrderUniqueId
           WHERE d.IsRemoved=0 AND o.IsRemoved=1) active_detail_removed_order,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPaymentDetails d
           JOIN NGT.CustomerCallPayments p ON p.Id=d.CustomerCallPaymentUniqueId
           JOIN NGT.CustomerCallOrders o ON o.Id=d.CustomerCallOrderUniqueId
           WHERE p.CustomerCallUniqueId<>o.CustomerCallUniqueId)
                detail_order_belongs_to_other_call,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPayments p
           LEFT JOIN NGT.BaseValues b ON b.Id=p.SettlementTypeUniqueId
           WHERE b.Id IS NULL) unresolved_settlement_type,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCallPayments p
           JOIN NGT.BaseValues b ON b.Id=p.SettlementTypeUniqueId
           JOIN NGT.BaseTypes bt ON bt.Id=b.BaseTypeId
           WHERE bt.BaseTypeName<>'SettlementType') wrong_settlement_base_type
        """,
    )[0]
    uniqueness = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM (
             SELECT CustomerCallUniqueId,SettlementTypeUniqueId,Amount,Date,COUNT_BIG(*) n
             FROM NGT.CustomerCallPayments WHERE IsRemoved=0
             GROUP BY CustomerCallUniqueId,SettlementTypeUniqueId,Amount,Date
             HAVING COUNT_BIG(*)>1) x) exact_header_fingerprint_duplicate_groups,
          (SELECT COALESCE(SUM(n),0) FROM (
             SELECT COUNT_BIG(*) n FROM NGT.CustomerCallPayments WHERE IsRemoved=0
             GROUP BY CustomerCallUniqueId,SettlementTypeUniqueId,Amount,Date
             HAVING COUNT_BIG(*)>1) x) headers_in_exact_fingerprint_duplicate_groups,
          (SELECT COUNT_BIG(*) FROM (
             SELECT BackOfficeReceiptUniqueId,COUNT_BIG(*) n
             FROM NGT.CustomerCallPayments
             WHERE BackOfficeReceiptUniqueId IS NOT NULL AND IsRemoved=0
             GROUP BY BackOfficeReceiptUniqueId HAVING COUNT_BIG(*)>1) x)
                duplicate_receipt_uuid_groups,
          (SELECT COALESCE(SUM(n),0) FROM (
             SELECT COUNT_BIG(*) n FROM NGT.CustomerCallPayments
             WHERE BackOfficeReceiptUniqueId IS NOT NULL AND IsRemoved=0
             GROUP BY BackOfficeReceiptUniqueId HAVING COUNT_BIG(*)>1) x)
                headers_in_duplicate_receipt_uuid_groups,
          (SELECT COUNT_BIG(*) FROM (
             SELECT CustomerCallPaymentUniqueId,CustomerCallOrderUniqueId,BackOfficeSaleId,
                    IsOldInvoice,PaidAmount,COUNT_BIG(*) n
             FROM NGT.CustomerCallPaymentDetails WHERE IsRemoved=0
             GROUP BY CustomerCallPaymentUniqueId,CustomerCallOrderUniqueId,BackOfficeSaleId,
                      IsOldInvoice,PaidAmount HAVING COUNT_BIG(*)>1) x)
                exact_detail_fingerprint_duplicate_groups,
          (SELECT MAX(n) FROM (
             SELECT COUNT_BIG(*) n FROM NGT.CustomerCallPayments WHERE IsRemoved=0
             GROUP BY CustomerCallUniqueId) x) maximum_payments_per_customer_call
        """,
    )[0]
    cross_call_context = _rows(
        cursor,
        """
        SELECT b.BaseValueName settlement_type,
               CASE WHEN pc.TourUniqueId=oc.TourUniqueId THEN 1 ELSE 0 END same_tour,
               CASE WHEN pc.CustomerUniqueId=oc.CustomerUniqueId THEN 1 ELSE 0 END same_customer,
               d.IsOldInvoice,o.IsRemoved order_removed,
               CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL THEN 1 ELSE 0 END receipt_linked,
               COUNT_BIG(*) details
        FROM NGT.CustomerCallPaymentDetails d
        JOIN NGT.CustomerCallPayments p ON p.Id=d.CustomerCallPaymentUniqueId
        JOIN NGT.CustomerCalls pc ON pc.Id=p.CustomerCallUniqueId
        JOIN NGT.CustomerCallOrders o ON o.Id=d.CustomerCallOrderUniqueId
        JOIN NGT.CustomerCalls oc ON oc.Id=o.CustomerCallUniqueId
        JOIN NGT.BaseValues b ON b.Id=p.SettlementTypeUniqueId
        WHERE p.CustomerCallUniqueId<>o.CustomerCallUniqueId
        GROUP BY b.BaseValueName,
                 CASE WHEN pc.TourUniqueId=oc.TourUniqueId THEN 1 ELSE 0 END,
                 CASE WHEN pc.CustomerUniqueId=oc.CustomerUniqueId THEN 1 ELSE 0 END,
                 d.IsOldInvoice,o.IsRemoved,
                 CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL THEN 1 ELSE 0 END
        ORDER BY details DESC,settlement_type
        """,
    )
    return {
        "referential_and_scope": referential,
        "duplicate_candidates": uniqueness,
        "cross_call_detail_context_without_identifiers": cross_call_context,
    }


def _allocation(cursor: Any) -> dict[str, Any]:
    overall = _rows(
        cursor,
        """
        WITH detail_sum AS (
          SELECT CustomerCallPaymentUniqueId,COUNT_BIG(*) detail_count,
                 SUM(CONVERT(float,PaidAmount)) paid_amount
          FROM NGT.CustomerCallPaymentDetails WHERE IsRemoved=0
          GROUP BY CustomerCallPaymentUniqueId
        )
        SELECT COUNT_BIG(*) active_payments,
               SUM(CASE WHEN d.CustomerCallPaymentUniqueId IS NULL THEN 1 ELSE 0 END)
                    without_detail,
               SUM(CASE WHEN d.detail_count=1 THEN 1 ELSE 0 END) one_detail,
               SUM(CASE WHEN d.detail_count>1 THEN 1 ELSE 0 END) multiple_details,
               SUM(CASE WHEN ABS(CONVERT(float,p.Amount)-ISNULL(d.paid_amount,0))<0.01
                        THEN 1 ELSE 0 END) amount_exact_to_cent,
               SUM(CASE WHEN ABS(CONVERT(float,p.Amount)-ISNULL(d.paid_amount,0))>=0.01
                        THEN 1 ELSE 0 END) amount_mismatch_to_cent,
               SUM(CASE WHEN ISNULL(d.paid_amount,0)<CONVERT(float,p.Amount)-0.01
                        THEN 1 ELSE 0 END) underallocated,
               SUM(CASE WHEN ISNULL(d.paid_amount,0)>CONVERT(float,p.Amount)+0.01
                        THEN 1 ELSE 0 END) overallocated
        FROM NGT.CustomerCallPayments p LEFT JOIN detail_sum d
          ON d.CustomerCallPaymentUniqueId=p.Id
        WHERE p.IsRemoved=0
        """,
    )[0]
    by_type = _rows(
        cursor,
        """
        WITH detail_sum AS (
          SELECT CustomerCallPaymentUniqueId,COUNT_BIG(*) detail_count,
                 SUM(CONVERT(float,PaidAmount)) paid_amount
          FROM NGT.CustomerCallPaymentDetails WHERE IsRemoved=0
          GROUP BY CustomerCallPaymentUniqueId
        )
        SELECT b.BaseValueName settlement_type,COUNT_BIG(*) active_payments,
               SUM(CASE WHEN d.CustomerCallPaymentUniqueId IS NULL THEN 1 ELSE 0 END)
                    without_detail,
               SUM(CASE WHEN ABS(CONVERT(float,p.Amount)-ISNULL(d.paid_amount,0))<0.01
                        THEN 1 ELSE 0 END) exact_to_cent,
               SUM(CASE WHEN ISNULL(d.paid_amount,0)<CONVERT(float,p.Amount)-0.01
                        THEN 1 ELSE 0 END) underallocated,
               SUM(CASE WHEN ISNULL(d.paid_amount,0)>CONVERT(float,p.Amount)+0.01
                        THEN 1 ELSE 0 END) overallocated
        FROM NGT.CustomerCallPayments p
        JOIN NGT.BaseValues b ON b.Id=p.SettlementTypeUniqueId
        LEFT JOIN detail_sum d ON d.CustomerCallPaymentUniqueId=p.Id
        WHERE p.IsRemoved=0
        GROUP BY b.BaseValueName ORDER BY active_payments DESC,settlement_type
        """,
    )
    detail_targets = _rows(
        cursor,
        """
        SELECT
          SUM(CASE WHEN IsOldInvoice=1 AND BackOfficeSaleId IS NOT NULL THEN 1 ELSE 0 END)
                old_invoice_with_sale_uuid,
          SUM(CASE WHEN IsOldInvoice=1 AND CustomerCallOrderUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                old_invoice_with_ngt_order,
          SUM(CASE WHEN IsOldInvoice=0 AND CustomerCallOrderUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                current_order_with_ngt_order,
          SUM(CASE WHEN IsOldInvoice=0 AND BackOfficeSaleId IS NOT NULL THEN 1 ELSE 0 END)
                current_order_with_sale_uuid,
          SUM(CASE WHEN CustomerCallOrderUniqueId IS NULL AND BackOfficeSaleId IS NULL
                        AND NULLIF(LTRIM(RTRIM(SaleRef)),'') IS NULL THEN 1 ELSE 0 END)
                no_order_or_sale_target,
          SUM(CASE WHEN CustomerCallOrderUniqueId IS NOT NULL AND BackOfficeSaleId IS NOT NULL
                   THEN 1 ELSE 0 END) both_order_and_sale_uuid
        FROM NGT.CustomerCallPaymentDetails WHERE IsRemoved=0
        """,
    )[0]
    return {"header_detail_reconciliation": overall, "by_settlement_type": by_type, "detail_target_modes": detail_targets}


def _receipt_crosswalk(cursor: Any) -> dict[str, Any]:
    return {
        "identity_and_amount": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) linked,
                   COUNT(DISTINCT r.ReceiptId) distinct_receipts,
                   SUM(CASE WHEN by_ref.ReceiptId=r.ReceiptId THEN 1 ELSE 0 END)
                        numeric_and_uuid_agree,
                   SUM(CASE WHEN ABS(CONVERT(float,p.Amount)-CONVERT(float,r.ReceiptAmount))<0.01
                            THEN 1 ELSE 0 END) amount_exact_to_cent,
                   SUM(CASE WHEN ABS(CONVERT(float,p.Amount)-CONVERT(float,r.ReceiptAmount))>=0.01
                            THEN 1 ELSE 0 END) amount_scope_differs,
                   SUM(CASE WHEN TRY_CONVERT(int,p.BackOfficeReceiptNo)=r.ReceiptNo
                            THEN 1 ELSE 0 END) receipt_number_agrees,
                   SUM(CASE WHEN r.ReceiptStatusId=2 THEN 1 ELSE 0 END) confirmed_receipts
            FROM NGT.CustomerCallPayments p
            JOIN dbo.Receipt r ON r.UniqueId=p.BackOfficeReceiptUniqueId
            LEFT JOIN dbo.Receipt by_ref ON by_ref.ReceiptId=TRY_CONVERT(int,p.BackOfficeReceiptRef)
            WHERE p.IsRemoved=0
            """,
        )[0],
        "unmatched_and_ambiguous": _rows(
            cursor,
            """
            SELECT
              SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL AND r.ReceiptId IS NULL
                       THEN 1 ELSE 0 END) unmatched_receipt_uuid,
              SUM(CASE WHEN NULLIF(LTRIM(RTRIM(p.BackOfficeReceiptRef)),'') IS NOT NULL
                            AND rr.ReceiptId IS NULL THEN 1 ELSE 0 END) unmatched_receipt_ref,
              SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NULL
                            AND NULLIF(LTRIM(RTRIM(p.BackOfficeReceiptRef)),'') IS NOT NULL
                       THEN 1 ELSE 0 END) ref_without_uuid,
              SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL
                            AND NULLIF(LTRIM(RTRIM(p.BackOfficeReceiptRef)),'') IS NULL
                       THEN 1 ELSE 0 END) uuid_without_ref
            FROM NGT.CustomerCallPayments p
            LEFT JOIN dbo.Receipt r ON r.UniqueId=p.BackOfficeReceiptUniqueId
            LEFT JOIN dbo.Receipt rr ON rr.ReceiptId=TRY_CONVERT(int,p.BackOfficeReceiptRef)
            WHERE p.IsRemoved=0
            """,
        )[0],
    }


def _tour_approval(cursor: Any) -> dict[str, Any]:
    return {
        "tour_payment_presence_vs_approval": _rows(
            cursor,
            """
            WITH payment_tours AS (
              SELECT c.TourUniqueId,COUNT_BIG(*) payment_count,
                     SUM(CASE WHEN p.BackOfficeReceiptUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                          receipt_linked
              FROM NGT.CustomerCallPayments p
              JOIN NGT.CustomerCalls c ON c.Id=p.CustomerCallUniqueId
              WHERE p.IsRemoved=0 AND c.IsRemoved=0
              GROUP BY c.TourUniqueId
            )
            SELECT COUNT_BIG(*) tours,
                   SUM(CASE WHEN t.PaymentApproved=1 THEN 1 ELSE 0 END) approved,
                   SUM(CASE WHEN p.TourUniqueId IS NOT NULL THEN 1 ELSE 0 END) with_payment,
                   SUM(CASE WHEN t.PaymentApproved=1 AND p.TourUniqueId IS NULL THEN 1 ELSE 0 END)
                        approved_without_payment,
                   SUM(CASE WHEN t.PaymentApproved=0 AND p.TourUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                        unapproved_with_payment,
                   SUM(CASE WHEN t.PaymentApproved=1 AND p.TourUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                        approved_with_payment
            FROM NGT.Tours t LEFT JOIN payment_tours p ON p.TourUniqueId=t.Id
            WHERE t.IsRemoved=0
            """,
        )[0],
        "approval_by_tour_status": _rows(
            cursor,
            """
            WITH payment_tours AS (
              SELECT DISTINCT c.TourUniqueId
              FROM NGT.CustomerCallPayments p
              JOIN NGT.CustomerCalls c ON c.Id=p.CustomerCallUniqueId
              WHERE p.IsRemoved=0 AND c.IsRemoved=0
            )
            SELECT b.BaseValueName tour_status,t.PaymentApproved,
                   COUNT_BIG(*) tours,
                   SUM(CASE WHEN p.TourUniqueId IS NOT NULL THEN 1 ELSE 0 END) with_payment
            FROM NGT.Tours t JOIN NGT.BaseValues b ON b.Id=t.TourStatusUniqueId
            LEFT JOIN payment_tours p ON p.TourUniqueId=t.Id
            WHERE t.IsRemoved=0
            GROUP BY b.BaseValueName,t.PaymentApproved
            ORDER BY tour_status,t.PaymentApproved
            """,
        ),
    }


def _configuration(cursor: Any) -> dict[str, Any]:
    return {
        "payment_terms": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) terms,
                   SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active,
                   SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed,
                   SUM(CASE WHEN IsRemoved=0 AND IsEnabled=1 THEN 1 ELSE 0 END) active_enabled,
                   SUM(CASE WHEN IsRemoved=0 AND AllowReceipt=1 THEN 1 ELSE 0 END)
                        active_allow_receipt,
                   SUM(CASE WHEN IsRemoved=0 AND IsCertifiedPayment=1 THEN 1 ELSE 0 END)
                        active_certified,
                   COUNT(DISTINCT CASE WHEN IsRemoved=0 THEN GroupBackOfficeId END)
                        active_groups,
                   MIN(CASE WHEN IsRemoved=0 THEN PaymentTime END) active_minimum_payment_time,
                   MAX(CASE WHEN IsRemoved=0 THEN PaymentTime END) active_maximum_payment_time
            FROM NGT.PaymentTypeOrders
            """,
        )[0],
        "dealer_bridge": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) mappings,
                   SUM(CASE WHEN d.IsRemoved=0 THEN 1 ELSE 0 END) active,
                   COUNT(DISTINCT CASE WHEN d.IsRemoved=0 THEN d.DealerUniqueId END)
                        active_dealers,
                   COUNT(DISTINCT CASE WHEN d.IsRemoved=0 THEN d.PaymentTypeOrderUniqueId END)
                        active_payment_types,
                   SUM(CASE WHEN d.IsRemoved=0 AND p.Id IS NULL THEN 1 ELSE 0 END)
                        active_orphan_payment_type,
                   SUM(CASE WHEN d.IsRemoved=0 AND p.IsRemoved=1 THEN 1 ELSE 0 END)
                        active_mapping_to_removed_type,
                   SUM(CASE WHEN d.IsRemoved=0 AND p.IsEnabled=0 THEN 1 ELSE 0 END)
                        active_mapping_to_disabled_type
            FROM NGT.DealerPaymentTypes d
            LEFT JOIN NGT.PaymentTypeOrders p ON p.Id=d.PaymentTypeOrderUniqueId
            """,
        )[0],
        "pos_without_values": _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) devices,
                   SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active,
                   SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed,
                   COUNT(DISTINCT CASE WHEN IsRemoved=0 THEN BankAccountUniqueId END)
                        active_bank_accounts,
                   SUM(CASE WHEN IsRemoved=0 AND NULLIF(LTRIM(RTRIM(DeviceSerial)),'') IS NOT NULL
                            THEN 1 ELSE 0 END) active_serial_present
            FROM NGT.Pos
            """,
        )[0],
    }


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety_context = _assert_safe_target(cursor)
        catalog = _catalog(cursor)
        population = _population(cursor)
        integrity = _integrity(cursor)
        allocation = _allocation(cursor)
        receipt = _receipt_crosswalk(cursor)
        approval = _tour_approval(cursor)
        configuration = _configuration(cursor)
        summary = {
            "target_table_count": len(TARGET_TABLES),
            "catalog_column_count": len(catalog["columns"]),
            "payment_header_count": population["payment_headers"]["headers"],
            "payment_detail_count": population["payment_details"]["details"],
            "allocation_mismatch_count": allocation["header_detail_reconciliation"]["amount_mismatch_to_cent"],
            "underallocated_count": allocation["header_detail_reconciliation"]["underallocated"],
            "overallocated_count": allocation["header_detail_reconciliation"]["overallocated"],
            "receipt_linked_count": receipt["identity_and_amount"]["linked"],
            "receipt_amount_scope_differs_count": receipt["identity_and_amount"]["amount_scope_differs"],
            "exact_header_fingerprint_duplicate_group_count": integrity["duplicate_candidates"]["exact_header_fingerprint_duplicate_groups"],
            "related_foreign_key_count": len(catalog["foreign_keys"]),
            "untrusted_related_foreign_key_count": sum(
                1 for row in catalog["foreign_keys"] if row["is_not_trusted"]
            ),
            "disabled_related_foreign_key_count": sum(
                1 for row in catalog["foreign_keys"] if row["is_disabled"]
            ),
            "non_primary_unique_business_index_count": len(
                {
                    (row["schema_name"], row["table_name"], row["index_name"])
                    for row in catalog["indexes"]
                    if row["is_unique"] and not row["is_primary_key"]
                }
            ),
            "sql_module_fingerprint_count": len(catalog["sql_module_fingerprints"]),
            "target_trigger_count": len(catalog["triggers"]),
        }
        return {
            "artifact": "varanegar_ngt_payment_settlement_boundary",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone(),
            "validation": "PASS",
            "scope": list(TARGET_TABLES),
            "safety": _public_safety(safety_context),
            "summary": summary,
            "catalog": catalog,
            "population": population,
            "integrity": integrity,
            "allocation": allocation,
            "backoffice_receipt_crosswalk": receipt,
            "tour_payment_approval": approval,
            "payment_configuration": configuration,
            "evidence_limits": [
                "This is a read-only clone snapshot, not a production incident log.",
                "Exact duplicate fingerprints are diagnostic candidates; repeated same-value payments may be legitimate.",
                "Header/detail mismatch does not by itself prove missing money because allocation scope can differ, but the runtime must define and enforce the intended invariant.",
                "NGT payment amount and detail paid amount are float columns; comparisons use a one-cent tolerance and the target should use fixed-precision money types.",
                "A matching BackOffice receipt identity does not imply the NGT header has the same aggregation grain as the receipt.",
                "PaymentApproved is a Tour workflow flag, not proof that every payment has a durable receipt or complete allocation.",
                "SQL module fingerprints prove catalogued dependency presence, not execution frequency or branch outcome.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
