"""Extract Varanegar general-ledger staging, posting, and status contracts.

Read-only by design. Persists schema metadata and aggregate accounting evidence
only. It never persists comments, references, account codes, user/device
identities, party identities, or individual journal rows.
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
    {"object": "dbo.PreVoucher", "role": "cross_domain_accounting_staging_line"},
    {"object": "dbo.ExternalVoucherHeader", "role": "external_posting_batch_header"},
    {"object": "dbo.ExternalVoucher", "role": "external_posting_batch_line"},
    {"object": "dbo.ExternalVoucherType", "role": "source_to_ledger_type_mapping"},
    {"object": "dbo.VoucherCreator", "role": "domain_to_accounting_source_definition"},
    {"object": "dbo.VoucherCreatorField", "role": "source_projection_field_definition"},
    {"object": "dbo.Voucher", "role": "general_ledger_journal_header"},
    {"object": "dbo.VoucherItem", "role": "general_ledger_journal_line"},
    {"object": "dbo.VoucherStatus", "role": "journal_status_master"},
    {"object": "dbo.VoucherStatusHistory", "role": "journal_status_event"},
    {"object": "dbo.VoucherType", "role": "journal_type_master"},
    {"object": "dbo.FiscalYear", "role": "general_ledger_fiscal_year"},
    {"object": "dbo.DCFiscalYear", "role": "dc_fiscal_year_numbering_scope"},
)

BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"


def _ids() -> str:
    return ",".join(f"OBJECT_ID(N'{x['object']}', 'U')" for x in DOMAIN_TABLES)


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    ids = _ids()
    return _rows(cursor, f"""
      SELECT fk.name constraint_name,
             OBJECT_SCHEMA_NAME(fk.parent_object_id) parent_schema,
             OBJECT_NAME(fk.parent_object_id) parent_table,pc.name parent_column,
             OBJECT_SCHEMA_NAME(fk.referenced_object_id) referenced_schema,
             OBJECT_NAME(fk.referenced_object_id) referenced_table,rc.name referenced_column,
             fk.delete_referential_action_desc on_delete,
             fk.update_referential_action_desc on_update,fk.is_disabled,fk.is_not_trusted
      FROM sys.foreign_keys fk
      JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
      JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
      JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
      WHERE fk.parent_object_id IN ({ids}) OR fk.referenced_object_id IN ({ids})
      ORDER BY referenced_schema,referenced_table,parent_schema,parent_table,fk.name,fkc.constraint_column_id
    """)


def _consumers(cursor: Any) -> list[dict[str, Any]]:
    ids = _ids()
    return _rows(cursor, f"""
      SELECT DISTINCT OBJECT_SCHEMA_NAME(d.referencing_id) consumer_schema,
             OBJECT_NAME(d.referencing_id) consumer_name,o.type_desc consumer_type,
             OBJECT_SCHEMA_NAME(d.referenced_id) source_schema,
             OBJECT_NAME(d.referenced_id) source_table,d.is_schema_bound_reference,
             o.modify_date consumer_modify_date
      FROM sys.sql_expression_dependencies d JOIN sys.objects o ON o.object_id=d.referencing_id
      WHERE d.referenced_id IN ({ids})
      ORDER BY source_schema,source_table,consumer_schema,consumer_name
    """)


def _implicit_links(cursor: Any) -> list[dict[str, Any]]:
    ids = _ids()
    return _rows(cursor, f"""
      SELECT OBJECT_SCHEMA_NAME(c.object_id) source_schema,
             OBJECT_NAME(c.object_id) source_table,c.name source_column,
             TYPE_NAME(c.user_type_id) data_type,c.is_nullable,
             CASE
               WHEN c.name LIKE '%VoucherId%' OR c.name LIKE '%Vocher%Id%' THEN 'voucher_or_inventory_document_candidate'
               WHEN c.name LIKE '%FiscalYear%' OR c.name='AccYear' THEN 'fiscal_year_candidate'
               WHEN c.name IN ('SLId','DLId','FifthLedgerId','SixthLedgerId','SeventhLedgerId') THEN 'ledger_dimension_candidate'
               ELSE 'cross_domain_source_candidate' END inferred_role
      FROM sys.columns c
      WHERE c.object_id IN ({ids}) AND (
        c.name LIKE '%VoucherId%' OR c.name LIKE '%Vocher%Id%' OR
        c.name LIKE '%FiscalYear%' OR c.name='AccYear' OR
        c.name IN ('SLId','DLId','FifthLedgerId','SixthLedgerId','SeventhLedgerId',
                   'SaleId','RetSaleId','ReceiptId','PayId','PaymentId','TransferId',
                   'FundId','RChequeHistoryId','PChequeHistoryId','SupInvoiceHdrId',
                   'RetSupInvoiceHdrId','CustId','SupplierId','ContactId','ManualVoucherId'))
      ORDER BY source_schema,source_table,c.column_id
    """)


def _journal_profile(cursor: Any) -> dict[str, Any]:
    header = _rows(cursor, """
      SELECT COUNT_BIG(*) headers,
             SUM(CASE WHEN IsDeleted=0 THEN 1 ELSE 0 END) active_headers,
             SUM(CASE WHEN IsDeleted=1 THEN 1 ELSE 0 END) deleted_headers,
             SUM(CASE WHEN IsManual=1 THEN 1 ELSE 0 END) manual_headers,
             SUM(CASE WHEN ExternalVoucherHeaderId IS NOT NULL THEN 1 ELSE 0 END) external_linked_headers,
             SUM(CASE WHEN VoucherNo IS NULL THEN 1 ELSE 0 END) without_voucher_no,
             MIN(VoucherDate) minimum_business_date,MAX(VoucherDate) maximum_business_date,
             COUNT(DISTINCT FiscalYearId) fiscal_years,COUNT(DISTINCT DCId) dcs
      FROM dbo.Voucher
    """)[0]
    item = _rows(cursor, """
      SELECT COUNT_BIG(*) items,
             SUM(CASE WHEN IsDeleted=0 THEN 1 ELSE 0 END) active_items,
             SUM(CASE WHEN IsDeleted=1 THEN 1 ELSE 0 END) deleted_items,
             SUM(CASE WHEN DebitAmount<0 OR CreditAmount<0 THEN 1 ELSE 0 END) negative_amount_items,
             SUM(CASE WHEN DebitAmount>0 AND CreditAmount>0 THEN 1 ELSE 0 END) double_sided_items,
             SUM(CASE WHEN DebitAmount=0 AND CreditAmount=0 THEN 1 ELSE 0 END) zero_sided_items,
             SUM(CASE WHEN FifthLedgerId IS NOT NULL THEN 1 ELSE 0 END) fifth_ledger_items,
             SUM(CASE WHEN SixthLedgerId IS NOT NULL THEN 1 ELSE 0 END) sixth_ledger_items,
             SUM(CASE WHEN SeventhLedgerId IS NOT NULL THEN 1 ELSE 0 END) seventh_ledger_items
      FROM dbo.VoucherItem
    """)[0]
    balance = _rows(cursor, """
      WITH x AS (
        SELECT v.VoucherId,v.IsDeleted,
               SUM(CASE WHEN i.IsDeleted=0 THEN i.DebitAmount ELSE 0 END) debit,
               SUM(CASE WHEN i.IsDeleted=0 THEN i.CreditAmount ELSE 0 END) credit,
               SUM(CASE WHEN i.IsDeleted=0 THEN 1 ELSE 0 END) active_lines
        FROM dbo.Voucher v LEFT JOIN dbo.VoucherItem i ON i.VoucherId=v.VoucherId
        GROUP BY v.VoucherId,v.IsDeleted
      )
      SELECT COUNT_BIG(*) vouchers,
             SUM(CASE WHEN active_lines=0 THEN 1 ELSE 0 END) without_active_lines,
             SUM(CASE WHEN debit<>credit THEN 1 ELSE 0 END) unbalanced_all,
             SUM(CASE WHEN IsDeleted=0 AND debit<>credit THEN 1 ELSE 0 END) unbalanced_active,
             SUM(CASE WHEN IsDeleted=0 AND debit=credit THEN 1 ELSE 0 END) balanced_active,
             SUM(CASE WHEN IsDeleted=0 THEN debit ELSE 0 END) active_debit,
             SUM(CASE WHEN IsDeleted=0 THEN credit ELSE 0 END) active_credit,
             MAX(ABS(debit-credit)) maximum_absolute_imbalance
      FROM x
    """)[0]
    type_rows = _decode_fields(_rows(cursor, """
      SELECT v.VoucherTypeId,CONVERT(varbinary(max),t.VoucherTypeName) voucher_type_name,
             COUNT_BIG(*) headers,SUM(CASE WHEN v.IsDeleted=0 THEN 1 ELSE 0 END) active_headers,
             SUM(CASE WHEN v.IsManual=1 THEN 1 ELSE 0 END) manual_headers,
             SUM(CASE WHEN v.ExternalVoucherHeaderId IS NOT NULL THEN 1 ELSE 0 END) external_headers
      FROM dbo.Voucher v LEFT JOIN dbo.VoucherType t ON t.VoucherTypeId=v.VoucherTypeId
      GROUP BY v.VoucherTypeId,t.VoucherTypeName ORDER BY headers DESC,v.VoucherTypeId
    """), ("voucher_type_name",))
    fiscal_dc = _rows(cursor, """
      SELECT FiscalYearId,DCId,COUNT_BIG(*) headers,
             SUM(CASE WHEN IsDeleted=0 THEN 1 ELSE 0 END) active_headers,
             MIN(VoucherNo) minimum_no,MAX(VoucherNo) maximum_no,
             MIN(SerialNo) minimum_serial,MAX(SerialNo) maximum_serial
      FROM dbo.Voucher GROUP BY FiscalYearId,DCId ORDER BY FiscalYearId,DCId
    """)
    origin_balance = _rows(cursor, """
      SELECT v.IsManual,COUNT(DISTINCT v.VoucherId) headers,COUNT_BIG(i.VoucherItemId) lines,
             SUM(i.DebitAmount) debit,SUM(i.CreditAmount) credit
      FROM dbo.Voucher v JOIN dbo.VoucherItem i ON i.VoucherId=v.VoucherId
      WHERE v.IsDeleted=0 AND i.IsDeleted=0
      GROUP BY v.IsManual ORDER BY v.IsManual
    """)
    return {"header_population": header, "item_population": item,
            "double_entry_balance": balance, "by_voucher_type": type_rows,
            "numbering_by_fiscal_year_and_dc": fiscal_dc,
            "balance_by_manual_origin": origin_balance}


def _status_profile(cursor: Any) -> dict[str, Any]:
    status = _decode_fields(_rows(cursor, """
      SELECT s.VoucherStatusId,CONVERT(varbinary(max),s.VoucherStatusName) status_name,
             COUNT_BIG(h.VoucherStatusHistoryId) history_rows,
             COUNT(DISTINCT h.VoucherId) vouchers_ever_in_status,
             SUM(CASE WHEN v.VoucherStatusHistoryId=h.VoucherStatusHistoryId THEN 1 ELSE 0 END) current_vouchers
      FROM dbo.VoucherStatus s
      LEFT JOIN dbo.VoucherStatusHistory h ON h.VoucherStatusId=s.VoucherStatusId
      LEFT JOIN dbo.Voucher v ON v.VoucherId=h.VoucherId
      GROUP BY s.VoucherStatusId,s.VoucherStatusName ORDER BY s.VoucherStatusId
    """), ("status_name",))
    integrity = _rows(cursor, """
      SELECT
        (SELECT COUNT_BIG(*) FROM dbo.Voucher WHERE VoucherStatusHistoryId IS NULL) null_current_pointer,
        (SELECT COUNT_BIG(*) FROM dbo.Voucher v LEFT JOIN dbo.VoucherStatusHistory h ON h.VoucherStatusHistoryId=v.VoucherStatusHistoryId WHERE v.VoucherStatusHistoryId IS NOT NULL AND h.VoucherStatusHistoryId IS NULL) orphan_current_pointer,
        (SELECT COUNT_BIG(*) FROM dbo.Voucher v JOIN dbo.VoucherStatusHistory h ON h.VoucherStatusHistoryId=v.VoucherStatusHistoryId WHERE h.VoucherId<>v.VoucherId) current_pointer_wrong_voucher,
        (SELECT COUNT_BIG(*) FROM dbo.VoucherStatusHistory h LEFT JOIN dbo.Voucher v ON v.VoucherId=h.VoucherId WHERE v.VoucherId IS NULL) orphan_history_voucher,
        (SELECT COUNT_BIG(*) FROM dbo.VoucherStatusHistory h LEFT JOIN dbo.VoucherStatus s ON s.VoucherStatusId=h.VoucherStatusId WHERE s.VoucherStatusId IS NULL) orphan_history_status,
        (SELECT COUNT_BIG(*) FROM dbo.Voucher v JOIN (SELECT VoucherId,MAX(VoucherStatusHistoryId) maximum_id FROM dbo.VoucherStatusHistory GROUP BY VoucherId)x ON x.VoucherId=v.VoucherId WHERE v.VoucherStatusHistoryId<>x.maximum_id) pointer_not_maximum_history,
        (SELECT COUNT_BIG(*) FROM (SELECT VoucherId,COUNT_BIG(*) n FROM dbo.VoucherStatusHistory GROUP BY VoucherId HAVING COUNT_BIG(*)>1)x) vouchers_with_multiple_status_events
    """)[0]
    return {"status_population_without_actor_or_comments": status,
            "current_pointer_integrity": integrity}


def _external_profile(cursor: Any) -> dict[str, Any]:
    header = _rows(cursor, """
      SELECT COUNT_BIG(*) headers,
             SUM(CASE WHEN Confirmed=1 THEN 1 ELSE 0 END) confirmed_headers,
             SUM(CASE WHEN h.VoucherId IS NOT NULL THEN 1 ELSE 0 END) header_voucher_id_populated,
             SUM(CASE WHEN canonical.VoucherId IS NOT NULL THEN 1 ELSE 0 END) canonical_reverse_linked_to_ledger,
             SUM(CASE WHEN h.Confirmed=1 AND canonical.VoucherId IS NULL THEN 1 ELSE 0 END) confirmed_without_canonical_ledger,
             SUM(CASE WHEN h.VoucherId IS NOT NULL AND h.VoucherId=canonical.VoucherId THEN 1 ELSE 0 END) header_voucher_id_agrees_with_canonical,
             SUM(CASE WHEN h.VoucherId IS NOT NULL AND h.VoucherId=canonical.VoucherNo THEN 1 ELSE 0 END) header_voucher_id_matches_canonical_voucher_no,
             SUM(CASE WHEN h.VoucherId IS NOT NULL AND canonical.VoucherId IS NOT NULL AND h.VoucherId<>canonical.VoucherId THEN 1 ELSE 0 END) header_voucher_id_disagrees_with_canonical,
             SUM(CASE WHEN h.VoucherId IS NOT NULL AND legacy.VoucherId IS NULL THEN 1 ELSE 0 END) header_voucher_id_not_a_ledger_pk,
             SUM(CASE WHEN h.ExternalVoucherTypeId IS NULL THEN 1 ELSE 0 END) without_external_type,
             COUNT(DISTINCT AccYear) accounting_years,COUNT(DISTINCT h.DCId) dcs,
             MIN(EndDate) minimum_business_date,MAX(EndDate) maximum_business_date
      FROM dbo.ExternalVoucherHeader h
      LEFT JOIN dbo.Voucher canonical ON canonical.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId AND canonical.IsDeleted=0
      LEFT JOIN dbo.Voucher legacy ON legacy.VoucherId=h.VoucherId
    """)[0]
    line_balance = _rows(cursor, """
      WITH x AS (
        SELECT h.ExternalVoucherHeaderId,h.Confirmed,h.VoucherId,
               COALESCE(SUM(e.DebitAmount),0) debit,COALESCE(SUM(e.CreditAmount),0) credit,
               COUNT_BIG(e.ExternalVoucherId) lines,
               MAX(h.DebitAmountHdr) header_debit,MAX(h.CreditAmountHdr) header_credit
        FROM dbo.ExternalVoucherHeader h LEFT JOIN dbo.ExternalVoucher e
          ON e.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId
        GROUP BY h.ExternalVoucherHeaderId,h.Confirmed,h.VoucherId
      )
      SELECT COUNT_BIG(*) headers,
             SUM(CASE WHEN lines=0 THEN 1 ELSE 0 END) without_lines,
             SUM(CASE WHEN debit<>credit THEN 1 ELSE 0 END) unbalanced_headers,
             SUM(CASE WHEN Confirmed=1 AND debit<>credit THEN 1 ELSE 0 END) unbalanced_confirmed,
             SUM(CASE WHEN header_debit IS NOT NULL AND header_debit<>debit THEN 1 ELSE 0 END) header_debit_mismatch,
             SUM(CASE WHEN header_credit IS NOT NULL AND header_credit<>credit THEN 1 ELSE 0 END) header_credit_mismatch,
             SUM(lines) lines,SUM(debit) total_debit,SUM(credit) total_credit,
             MAX(ABS(debit-credit)) maximum_absolute_imbalance
      FROM x
    """)[0]
    by_type = _rows(cursor, """
      WITH line_count AS (
        SELECT ExternalVoucherHeaderId,COUNT_BIG(*) lines
        FROM dbo.ExternalVoucher GROUP BY ExternalVoucherHeaderId
      )
      SELECT h.ExternalVoucherTypeId,COUNT_BIG(*) headers,
             SUM(CASE WHEN h.Confirmed=1 THEN 1 ELSE 0 END) confirmed,
             SUM(CASE WHEN v.VoucherId IS NOT NULL THEN 1 ELSE 0 END) canonical_ledger_linked,
             SUM(COALESCE(l.lines,0)) lines
      FROM dbo.ExternalVoucherHeader h
      LEFT JOIN line_count l ON l.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId
      LEFT JOIN dbo.Voucher v ON v.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId AND v.IsDeleted=0
      GROUP BY h.ExternalVoucherTypeId ORDER BY headers DESC,h.ExternalVoucherTypeId
    """)
    integrity = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.ExternalVoucher e LEFT JOIN dbo.ExternalVoucherHeader h ON h.ExternalVoucherHeaderId=e.ExternalVoucherHeaderId WHERE h.ExternalVoucherHeaderId IS NULL) orphan_lines,
       (SELECT COUNT_BIG(*) FROM dbo.ExternalVoucherHeader h LEFT JOIN dbo.ExternalVoucherType t ON t.ExternalVoucherTypeId=h.ExternalVoucherTypeId WHERE h.ExternalVoucherTypeId IS NOT NULL AND t.ExternalVoucherTypeId IS NULL) orphan_header_types,
       (SELECT COUNT_BIG(*) FROM dbo.Voucher v LEFT JOIN dbo.ExternalVoucherHeader h ON h.ExternalVoucherHeaderId=v.ExternalVoucherHeaderId WHERE v.ExternalVoucherHeaderId IS NOT NULL AND h.ExternalVoucherHeaderId IS NULL) ledger_headers_with_orphan_external_ref,
       (SELECT COUNT_BIG(*) FROM (SELECT ExternalVoucherHeaderId,COUNT_BIG(*) n FROM dbo.Voucher WHERE ExternalVoucherHeaderId IS NOT NULL AND IsDeleted=0 GROUP BY ExternalVoucherHeaderId HAVING COUNT_BIG(*)>1)x) external_headers_linked_to_multiple_active_ledgers
    """)[0]
    return {"header_population": header, "line_double_entry_balance": line_balance,
            "by_external_type": by_type, "link_integrity": integrity}


def _prevoucher_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
      SELECT COUNT_BIG(*) lines,COUNT(DISTINCT VoucherCreatorId) voucher_creators,
             COUNT(DISTINCT ExternalVoucherTypeId) external_types,
             COUNT(DISTINCT VoucherTypeId) ledger_types,
             COUNT(DISTINCT FiscalYearId) fiscal_years,COUNT(DISTINCT DCId) dcs,
             MIN(PreVoucherDate) minimum_business_date,MAX(PreVoucherDate) maximum_business_date,
             SUM(CASE WHEN DebitAmount<0 OR CreditAmount<0 THEN 1 ELSE 0 END) negative_amount_lines,
             SUM(CASE WHEN DebitAmount>0 AND CreditAmount>0 THEN 1 ELSE 0 END) double_sided_lines,
             SUM(CASE WHEN DebitAmount=0 AND CreditAmount=0 THEN 1 ELSE 0 END) zero_sided_lines,
             SUM(DebitAmount) total_debit,SUM(CreditAmount) total_credit
      FROM dbo.PreVoucher
    """)[0]
    sources = _rows(cursor, """
      SELECT
       SUM(CASE WHEN ExternalVoucherHeaderId IS NOT NULL THEN 1 ELSE 0 END) external_header_lines,
       SUM(CASE WHEN SaleId IS NOT NULL THEN 1 ELSE 0 END) sale_lines,
       SUM(CASE WHEN RetSaleId IS NOT NULL THEN 1 ELSE 0 END) return_sale_lines,
       SUM(CASE WHEN ReceiptId IS NOT NULL THEN 1 ELSE 0 END) receipt_lines,
       SUM(CASE WHEN PayId IS NOT NULL THEN 1 ELSE 0 END) pay_lines,
       SUM(CASE WHEN PaymentId IS NOT NULL THEN 1 ELSE 0 END) payment_lines,
       SUM(CASE WHEN TransferId IS NOT NULL THEN 1 ELSE 0 END) transfer_lines,
       SUM(CASE WHEN FundId IS NOT NULL THEN 1 ELSE 0 END) fund_lines,
       SUM(CASE WHEN RChequeHistoryId IS NOT NULL THEN 1 ELSE 0 END) received_cheque_history_lines,
       SUM(CASE WHEN PChequeHistoryId IS NOT NULL THEN 1 ELSE 0 END) payable_cheque_history_lines,
       SUM(CASE WHEN VocherHdrId IS NOT NULL THEN 1 ELSE 0 END) inventory_voucher_lines,
       SUM(CASE WHEN SupInvoiceHdrId IS NOT NULL THEN 1 ELSE 0 END) supplier_invoice_lines,
       SUM(CASE WHEN RetSupInvoiceHdrId IS NOT NULL THEN 1 ELSE 0 END) supplier_return_lines,
       SUM(CASE WHEN GuaranteeReceivedId IS NOT NULL THEN 1 ELSE 0 END) guarantee_received_lines,
       SUM(CASE WHEN CustId IS NOT NULL THEN 1 ELSE 0 END) customer_dimension_lines,
       SUM(CASE WHEN SupplierId IS NOT NULL THEN 1 ELSE 0 END) supplier_dimension_lines,
       SUM(CASE WHEN ContactId IS NOT NULL THEN 1 ELSE 0 END) contact_dimension_lines,
       SUM(CASE WHEN ManualVoucherId IS NOT NULL THEN 1 ELSE 0 END) manual_voucher_lines
      FROM dbo.PreVoucher
    """)[0]
    group_balance = _rows(cursor, """
      WITH x AS (
        SELECT VoucherCreatorId,ReferenceId,FiscalYearId,DCId,
               SUM(DebitAmount) debit,SUM(CreditAmount) credit,COUNT_BIG(*) lines
        FROM dbo.PreVoucher
        GROUP BY VoucherCreatorId,ReferenceId,FiscalYearId,DCId
      )
      SELECT COUNT_BIG(*) source_groups,
             SUM(CASE WHEN debit<>credit THEN 1 ELSE 0 END) unbalanced_source_groups,
             SUM(CASE WHEN debit=credit THEN 1 ELSE 0 END) balanced_source_groups,
             MAX(ABS(debit-credit)) maximum_absolute_imbalance,
             MAX(lines) maximum_lines_per_source_group
      FROM x
    """)[0]
    integrity = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.PreVoucher p LEFT JOIN dbo.ExternalVoucherType t ON t.ExternalVoucherTypeId=p.ExternalVoucherTypeId WHERE t.ExternalVoucherTypeId IS NULL) orphan_external_types,
       (SELECT COUNT_BIG(*) FROM dbo.PreVoucher p LEFT JOIN dbo.VoucherType t ON t.VoucherTypeId=p.VoucherTypeId WHERE t.VoucherTypeId IS NULL) orphan_ledger_types,
       (SELECT COUNT_BIG(*) FROM dbo.PreVoucher p LEFT JOIN dbo.FiscalYear f ON f.FiscalYearId=p.FiscalYearId WHERE f.FiscalYearId IS NULL) orphan_fiscal_years,
       (SELECT COUNT_BIG(*) FROM dbo.PreVoucher p LEFT JOIN GNR.tblDC d ON d.ID=p.DCId WHERE d.ID IS NULL) orphan_dcs,
       (SELECT COUNT_BIG(*) FROM dbo.PreVoucher p LEFT JOIN dbo.ExternalVoucherHeader h ON h.ExternalVoucherHeaderId=p.ExternalVoucherHeaderId WHERE p.ExternalVoucherHeaderId IS NOT NULL AND h.ExternalVoucherHeaderId IS NULL) orphan_external_headers
    """)[0]
    return {"population_without_codes_comments_or_identities": population,
            "cross_domain_source_coverage": sources,
            "balance_by_source_group": group_balance,
            "master_and_posting_link_integrity": integrity}


def _voucher_creator_profile(cursor: Any) -> dict[str, Any]:
    creators = _decode_fields(_rows(cursor, """
      WITH fa AS (
        SELECT VoucherCreatorId,COUNT_BIG(*) field_definitions
        FROM dbo.VoucherCreatorField GROUP BY VoucherCreatorId
      ),pa AS (
        SELECT VoucherCreatorId,COUNT_BIG(*) pre_voucher_lines,
               COUNT(DISTINCT ReferenceId) source_references,
               MIN(PreVoucherDate) minimum_business_date,MAX(PreVoucherDate) maximum_business_date,
               SUM(CASE WHEN SaleId IS NOT NULL THEN 1 ELSE 0 END) sale_lines,
               SUM(CASE WHEN RetSaleId IS NOT NULL THEN 1 ELSE 0 END) return_sale_lines,
               SUM(CASE WHEN ReceiptId IS NOT NULL THEN 1 ELSE 0 END) receipt_lines,
               SUM(CASE WHEN PayId IS NOT NULL THEN 1 ELSE 0 END) pay_lines,
               SUM(CASE WHEN PaymentId IS NOT NULL THEN 1 ELSE 0 END) payment_lines,
               SUM(CASE WHEN TransferId IS NOT NULL THEN 1 ELSE 0 END) transfer_lines,
               SUM(CASE WHEN RChequeHistoryId IS NOT NULL THEN 1 ELSE 0 END) received_cheque_lines,
               SUM(CASE WHEN PChequeHistoryId IS NOT NULL THEN 1 ELSE 0 END) payable_cheque_lines,
               SUM(CASE WHEN VocherHdrId IS NOT NULL THEN 1 ELSE 0 END) inventory_lines,
               SUM(CASE WHEN SupInvoiceHdrId IS NOT NULL THEN 1 ELSE 0 END) supplier_invoice_lines,
               SUM(CASE WHEN RetSupInvoiceHdrId IS NOT NULL THEN 1 ELSE 0 END) supplier_return_lines
        FROM dbo.PreVoucher GROUP BY VoucherCreatorId
      )
      SELECT c.VoucherCreatorId,c.ViewName,
             CONVERT(varbinary(max),c.ViewCaption) view_caption,
             c.ReferenceObjectName,c.HasCustId,c.HasSupplierId,c.HasContactId,
             COALESCE(fa.field_definitions,0) field_definitions,
             COALESCE(pa.pre_voucher_lines,0) pre_voucher_lines,
             COALESCE(pa.source_references,0) source_references,
             pa.minimum_business_date,pa.maximum_business_date,
             COALESCE(pa.sale_lines,0) sale_lines,
             COALESCE(pa.return_sale_lines,0) return_sale_lines,
             COALESCE(pa.receipt_lines,0) receipt_lines,
             COALESCE(pa.pay_lines,0) pay_lines,
             COALESCE(pa.payment_lines,0) payment_lines,
             COALESCE(pa.transfer_lines,0) transfer_lines,
             COALESCE(pa.received_cheque_lines,0) received_cheque_lines,
             COALESCE(pa.payable_cheque_lines,0) payable_cheque_lines,
             COALESCE(pa.inventory_lines,0) inventory_lines,
             COALESCE(pa.supplier_invoice_lines,0) supplier_invoice_lines,
             COALESCE(pa.supplier_return_lines,0) supplier_return_lines
      FROM dbo.VoucherCreator c
      LEFT JOIN fa ON fa.VoucherCreatorId=c.VoucherCreatorId
      LEFT JOIN pa ON pa.VoucherCreatorId=c.VoucherCreatorId
      ORDER BY pre_voucher_lines DESC,c.VoucherCreatorId
    """), ("view_caption",))
    integrity = _rows(cursor, """
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.PreVoucher p LEFT JOIN dbo.VoucherCreator c ON c.VoucherCreatorId=p.VoucherCreatorId WHERE c.VoucherCreatorId IS NULL) orphan_creator_lines,
       (SELECT COUNT_BIG(*) FROM dbo.VoucherCreatorField f LEFT JOIN dbo.VoucherCreator c ON c.VoucherCreatorId=f.VoucherCreatorId WHERE c.VoucherCreatorId IS NULL) orphan_field_definitions,
       (SELECT COUNT_BIG(*) FROM dbo.VoucherCreator c WHERE NOT EXISTS (SELECT 1 FROM dbo.PreVoucher p WHERE p.VoucherCreatorId=c.VoucherCreatorId)) unused_creators,
       (SELECT COUNT_BIG(*) FROM dbo.VoucherCreator c WHERE EXISTS (SELECT 1 FROM dbo.PreVoucher p WHERE p.VoucherCreatorId=c.VoucherCreatorId)) used_creators
    """)[0]
    return {"creator_contracts_without_queries_or_row_identities": creators,
            "integrity": integrity,
            "boundary": "View/reference object names describe code contracts; SimpleQuery text and individual source rows are excluded."}


def _creator_view_contracts(cursor: Any) -> dict[str, Any]:
    objects = _rows(cursor, """
      SELECT c.VoucherCreatorId,c.ViewName,
             OBJECT_SCHEMA_NAME(o.object_id) view_schema,o.name view_object,o.type_desc,
             o.modify_date,DATALENGTH(m.definition) definition_bytes,
             CONVERT(varchar(64),HASHBYTES('SHA2_256',CONVERT(varbinary(max),m.definition)),2) definition_sha256,
             (SELECT COUNT_BIG(*) FROM sys.columns x WHERE x.object_id=o.object_id) output_columns,
             (SELECT COUNT_BIG(*) FROM sys.sql_expression_dependencies d WHERE d.referencing_id=o.object_id) dependency_rows
      FROM dbo.VoucherCreator c
      LEFT JOIN sys.objects o ON o.object_id=OBJECT_ID(c.ViewName)
      LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
      WHERE EXISTS (SELECT 1 FROM dbo.PreVoucher p WHERE p.VoucherCreatorId=c.VoucherCreatorId)
      ORDER BY c.VoucherCreatorId
    """)
    columns = _rows(cursor, """
      SELECT c.VoucherCreatorId,x.column_id,x.name output_column,
             TYPE_NAME(x.user_type_id) data_type,x.is_nullable
      FROM dbo.VoucherCreator c
      JOIN sys.columns x ON x.object_id=OBJECT_ID(c.ViewName)
      WHERE EXISTS (SELECT 1 FROM dbo.PreVoucher p WHERE p.VoucherCreatorId=c.VoucherCreatorId)
      ORDER BY c.VoucherCreatorId,x.column_id
    """)
    dependencies = _rows(cursor, """
      SELECT DISTINCT c.VoucherCreatorId,
             d.referenced_schema_name,d.referenced_entity_name,
             OBJECT_SCHEMA_NAME(d.referenced_id) resolved_schema,
             OBJECT_NAME(d.referenced_id) resolved_object,
             o.type_desc referenced_type,d.is_schema_bound_reference
      FROM dbo.VoucherCreator c
      JOIN sys.sql_expression_dependencies d ON d.referencing_id=OBJECT_ID(c.ViewName)
      LEFT JOIN sys.objects o ON o.object_id=d.referenced_id
      WHERE EXISTS (SELECT 1 FROM dbo.PreVoucher p WHERE p.VoucherCreatorId=c.VoucherCreatorId)
      ORDER BY c.VoucherCreatorId,d.referenced_schema_name,d.referenced_entity_name
    """)
    integrity = _rows(cursor, """
      SELECT
       SUM(CASE WHEN OBJECT_ID(c.ViewName) IS NULL THEN 1 ELSE 0 END) used_creators_without_resolved_view,
       SUM(CASE WHEN OBJECT_ID(c.ViewName) IS NOT NULL AND m.definition IS NULL THEN 1 ELSE 0 END) used_creator_views_without_visible_definition
      FROM dbo.VoucherCreator c
      LEFT JOIN sys.sql_modules m ON m.object_id=OBJECT_ID(c.ViewName)
      WHERE EXISTS (SELECT 1 FROM dbo.PreVoucher p WHERE p.VoucherCreatorId=c.VoucherCreatorId)
    """)[0]
    return {"used_creator_view_fingerprints": objects,
            "used_creator_output_schema": columns,
            "used_creator_dependencies": dependencies,
            "integrity": integrity,
            "privacy_boundary": "Definition text and SimpleQuery are excluded; only object names, output schema, dependencies, size, timestamp, and SHA-256 are persisted."}


def _sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
      SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,
             DATALENGTH(m.definition) definition_bytes
      FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
      JOIN sys.sql_modules m ON m.object_id=o.object_id
      WHERE o.name IN ('DoExternalVoucher_Create','usp_DoPreVoucher',
        'Usp_TransferExternalVoucherToLedger','Usp_Sdsnet_Voucher_BeforeSave',
        'Usp_Sdsnet_Voucher_Save','Get_ChangeVoucherStatus','DoVoucher_SetVoucherNo',
        'Get_GLBook','Get_GLTrialBalance','DoFiscalYear_ClosingAccount',
        'DoFiscalYear_InsertInitialVoucher','DoFiscalYear_InsertConclusiveVoucher')
      ORDER BY s.name,o.name
    """)


def _business_window(cursor: Any) -> dict[str, Any]:
    summary = _rows(cursor, f"""
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.PreVoucher WHERE PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') pre_voucher_lines,
       (SELECT COUNT_BIG(*) FROM (SELECT VoucherCreatorId,ReferenceId,FiscalYearId,DCId FROM dbo.PreVoucher WHERE PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' GROUP BY VoucherCreatorId,ReferenceId,FiscalYearId,DCId)x) pre_voucher_source_groups,
       (SELECT SUM(DebitAmount) FROM dbo.PreVoucher WHERE PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') pre_voucher_debit,
       (SELECT SUM(CreditAmount) FROM dbo.PreVoucher WHERE PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') pre_voucher_credit,
       (SELECT COUNT_BIG(*) FROM dbo.ExternalVoucherHeader WHERE EndDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') external_headers,
       (SELECT COUNT_BIG(*) FROM dbo.ExternalVoucher e JOIN dbo.ExternalVoucherHeader h ON h.ExternalVoucherHeaderId=e.ExternalVoucherHeaderId WHERE h.EndDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') external_lines,
       (SELECT SUM(e.DebitAmount) FROM dbo.ExternalVoucher e JOIN dbo.ExternalVoucherHeader h ON h.ExternalVoucherHeaderId=e.ExternalVoucherHeaderId WHERE h.EndDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') external_debit,
       (SELECT SUM(e.CreditAmount) FROM dbo.ExternalVoucher e JOIN dbo.ExternalVoucherHeader h ON h.ExternalVoucherHeaderId=e.ExternalVoucherHeaderId WHERE h.EndDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') external_credit,
       (SELECT COUNT_BIG(*) FROM dbo.Voucher WHERE VoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') journal_headers,
       (SELECT COUNT_BIG(*) FROM dbo.Voucher WHERE VoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' AND IsManual=1) manual_journal_headers,
       (SELECT COUNT_BIG(*) FROM dbo.Voucher WHERE VoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' AND ExternalVoucherHeaderId IS NOT NULL) external_linked_journal_headers,
       (SELECT COUNT_BIG(*) FROM dbo.VoucherItem i JOIN dbo.Voucher v ON v.VoucherId=i.VoucherId WHERE v.VoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') journal_lines,
       (SELECT SUM(i.DebitAmount) FROM dbo.VoucherItem i JOIN dbo.Voucher v ON v.VoucherId=i.VoucherId WHERE v.VoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') journal_debit,
       (SELECT SUM(i.CreditAmount) FROM dbo.VoucherItem i JOIN dbo.Voucher v ON v.VoucherId=i.VoucherId WHERE v.VoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') journal_credit,
       (SELECT SUM(i.DebitAmount) FROM dbo.VoucherItem i JOIN dbo.Voucher v ON v.VoucherId=i.VoucherId WHERE v.VoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' AND v.IsManual=1) manual_journal_debit,
       (SELECT SUM(i.CreditAmount) FROM dbo.VoucherItem i JOIN dbo.Voucher v ON v.VoucherId=i.VoucherId WHERE v.VoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' AND v.IsManual=1) manual_journal_credit
    """)[0]
    return {"from": BUSINESS_DATE_FROM, "to": BUSINESS_DATE_TO,
            "basis": "Persian document business date at each posting layer",
            "summary": summary}


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "general_ledger_staging_and_posting",
            "scope": {"server": SERVER, "database": DATABASE,
                      "mode": "read-only aggregate ledger and posting evidence",
                      "privacy_policy": "no comments, references, account codes, user/device identities, party identities, or journal rows"},
            "safety": {"target_is_local": True, "database_name": safety["database_name"],
                       "updateability": safety["updateability"], "can_select": safety["can_select"],
                       "can_view_definition": safety["can_view_definition"], "can_update": safety["can_update"],
                       "denies_data_writes": safety["denies_data_writes"]},
            "tables": [_table_metadata(cursor, x["object"], x["role"]) for x in DOMAIN_TABLES],
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _consumers(cursor),
            "implicit_link_candidates": _implicit_links(cursor),
            "general_ledger": _journal_profile(cursor),
            "voucher_status_lifecycle": _status_profile(cursor),
            "external_voucher_pipeline": _external_profile(cursor),
            "pre_voucher_staging": _prevoucher_profile(cursor),
            "voucher_creator_crosswalk": _voucher_creator_profile(cursor),
            "voucher_creator_view_contracts": _creator_view_contracts(cursor),
            "business_window": _business_window(cursor),
            "semantic_contract_sources": _sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "migration_contract": (
                "Source domain event -> immutable PreVoucher staging lines -> balanced ExternalVoucher batch -> "
                "posted Voucher/VoucherItem with explicit status event and fiscal/DC numbering scope."
            ),
            "evidence_limits": [
                "No accounting comments, reference text/numbers, account codes, user/device identities, party identities, or individual journal lines are persisted.",
                "Aggregate balance parity proves arithmetic integrity, not account classification or business approval.",
                "PreVoucher source grouping is inferred from creator/reference/fiscal/DC uniqueness and requires procedure-level confirmation for every creator.",
                "VoucherStatusHistory has no explicit predecessor field; the maximum identifier is an observed ordering proxy, not a universal event-time guarantee.",
                "Client-side posting orchestration and encrypted modules may add rules outside visible SQL definitions.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
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
