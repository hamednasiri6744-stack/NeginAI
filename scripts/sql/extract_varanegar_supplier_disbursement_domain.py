"""Extract supplier disbursement and payable-cheque lifecycle evidence.

Read-only by design. The JSON contains schema metadata, reference labels,
aggregate counts, reconciliation results, and selected SQL contracts. It never
persists cheque numbers, Sayad/account values, payee/supplier rows, comments,
user/host identities, credentials, or raw payment records.
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
    {"object": "dbo.Pay", "role": "outgoing_payment_header"},
    {"object": "dbo.PayStatus", "role": "outgoing_payment_status_master"},
    {"object": "dbo.RPReason", "role": "receipt_payment_reason_master"},
    {"object": "dbo.PCash", "role": "cash_disbursement_instrument"},
    {"object": "dbo.PWithdraw", "role": "bank_withdrawal_disbursement_instrument"},
    {"object": "dbo.PCheque", "role": "payable_cheque_master"},
    {"object": "dbo.PChequeHistory", "role": "payable_cheque_state_event"},
    {"object": "dbo.PChequeStatus", "role": "payable_cheque_status_master"},
    {"object": "dbo.PChequeWorkflow", "role": "payable_cheque_transition_master"},
    {"object": "dbo.PChequeBook", "role": "payable_cheque_book_master"},
    {"object": "dbo.PChequeBookItem", "role": "payable_cheque_leaf_master"},
    {"object": "dbo.PChequeRefund", "role": "payable_cheque_refund_process"},
    {"object": "dbo.PChequeChangeStatus", "role": "bulk_payable_cheque_state_change"},
    {"object": "dbo.PChequeChangeStatusItm", "role": "bulk_payable_cheque_state_item"},
    {"object": "Acc.TblBankBranches", "role": "bank_account_branch_master"},
    {"object": "GNR.tblSupplier", "role": "supplier_master"},
    {"object": "Acc.tblSupSettlement", "role": "supplier_invoice_allocation_bridge"},
    {"object": "Acc.tblPayments", "role": "cross_domain_payment_allocation_ledger"},
)

BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"


def _ids() -> str:
    return ",".join(f"OBJECT_ID(N'{x['object']}', 'U')" for x in DOMAIN_TABLES)


def _public_safety(context: dict[str, Any]) -> dict[str, Any]:
    return {k: context[k] for k in (
        "database_name", "updateability", "can_select", "can_view_definition",
        "can_update", "denies_data_writes",
    )} | {"target_is_local": True, "expected_analysis_login_verified": True}


def _public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    excluded = {
        "issuedfor", "pchequecomment", "sayadno", "pchequebookitemno",
        "pchequebookserialno", "startno", "comment", "pwithdrawcomment",
        "pwithdrawno", "pcashcomment", "paycomment", "payeeid", "suppliername",
        "address", "address2", "mobile", "mobile2", "tel", "fax", "email",
        "nationalcode", "economiccode", "econcode", "moadiancode", "taxcode",
        "accountno", "cardno", "iban", "appuserid", "sqlusername", "winusername",
        "hostname", "applicationname",
    }
    result = dict(metadata)
    result["columns"] = [c for c in metadata.get("columns", [])
                         if str(c.get("column_name", "")).lower() not in excluded]
    result["redacted_column_count"] = len(metadata.get("columns", [])) - len(result["columns"])
    return result


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
      WITH c AS (
        SELECT col.object_id,col.column_id,s.name schema_name,t.name table_name,
               col.name column_name,TYPE_NAME(col.user_type_id) data_type
        FROM sys.columns col JOIN sys.tables t ON t.object_id=col.object_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE LOWER(col.name) LIKE '%pcheque%' OR LOWER(col.name) LIKE '%pwithdraw%'
           OR LOWER(col.name) LIKE '%pcash%' OR LOWER(col.name) LIKE '%paycommandid%'
      )
      SELECT c.schema_name,c.table_name,c.column_name,c.data_type,
             CASE WHEN fkc.constraint_object_id IS NULL THEN 0 ELSE 1 END has_formal_fk,
             OBJECT_SCHEMA_NAME(fkc.referenced_object_id) formal_target_schema,
             OBJECT_NAME(fkc.referenced_object_id) formal_target_table,
             rc.name formal_target_column
      FROM c LEFT JOIN sys.foreign_key_columns fkc
        ON fkc.parent_object_id=c.object_id AND fkc.parent_column_id=c.column_id
      LEFT JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id
                              AND rc.column_id=fkc.referenced_column_id
      WHERE c.object_id NOT IN ({ids})
      ORDER BY has_formal_fk,c.schema_name,c.table_name,c.column_name
    """)


def _masters(cursor: Any) -> dict[str, Any]:
    pay_statuses = _decode_fields(_rows(cursor, """
      SELECT s.PayStatusId,CONVERT(varbinary(max),s.PayStatusName) PayStatusName,
             COUNT_BIG(p.PayId) usage
      FROM dbo.PayStatus s LEFT JOIN dbo.Pay p ON p.PayStatusId=s.PayStatusId
      GROUP BY s.PayStatusId,s.PayStatusName ORDER BY s.PayStatusId
    """), ("PayStatusName",))
    cheque_statuses = _decode_fields(_rows(cursor, """
      SELECT s.PChequeStatusId,CONVERT(varbinary(max),s.PChequeStatusName) PChequeStatusName,
             COUNT_BIG(h.PChequeHistoryId) history_usage,
             SUM(CASE WHEN c.PChequeId IS NOT NULL THEN 1 ELSE 0 END) current_usage
      FROM dbo.PChequeStatus s
      LEFT JOIN dbo.PChequeHistory h ON h.PChequeStatusId=s.PChequeStatusId
      LEFT JOIN dbo.PCheque c ON c.PChequeHistoryId=h.PChequeHistoryId
      GROUP BY s.PChequeStatusId,s.PChequeStatusName ORDER BY s.PChequeStatusId
    """), ("PChequeStatusName",))
    workflow = _rows(cursor, """
      SELECT PChequeWorkflowId,PChequeStatusId from_status,
             PChequeNextStatusId to_status,PChequeWorkflowCode,ProcessTypeId
      FROM dbo.PChequeWorkflow ORDER BY PChequeWorkflowId
    """)
    reason_usage = _decode_fields(_rows(cursor, """
      SELECT r.RPReasonId,CONVERT(varbinary(max),r.RPReasonName) RPReasonName,
             r.IsReceivable,r.IsPayable,r.IsActive,r.BuiltIn,r.IsSettlement,
             r.IsPayGroup,r.IsChequeTransfer,r.GroupCharging,r.IsRPTransfer,
             COUNT_BIG(p.PayId) pay_usage
      FROM dbo.RPReason r LEFT JOIN dbo.Pay p ON p.RPReasonId=r.RPReasonId
      GROUP BY r.RPReasonId,r.RPReasonName,r.IsReceivable,r.IsPayable,r.IsActive,
               r.BuiltIn,r.IsSettlement,r.IsPayGroup,r.IsChequeTransfer,
               r.GroupCharging,r.IsRPTransfer
      HAVING COUNT_BIG(p.PayId)>0
      ORDER BY pay_usage DESC,r.RPReasonId
    """), ("RPReasonName",))
    return {"pay_statuses": pay_statuses, "payable_cheque_statuses": cheque_statuses,
            "payable_cheque_workflow": workflow, "used_payment_reasons": reason_usage}


def _pay_and_instruments(cursor: Any) -> dict[str, Any]:
    pay_profile = _rows(cursor, """
      SELECT PayStatusId,COUNT_BIG(*) pays,COUNT(DISTINCT PayeeId) payees,
             SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirm_date_present,
             SUM(CASE WHEN IsNew=1 THEN 1 ELSE 0 END) is_new,
             MIN(PayDate) minimum_date,MAX(PayDate) maximum_date
      FROM dbo.Pay GROUP BY PayStatusId ORDER BY PayStatusId
    """)
    population = _rows(cursor, """
      SELECT
        (SELECT COUNT_BIG(*) FROM dbo.PCash) cash_rows,
        (SELECT COUNT_BIG(*) FROM dbo.PWithdraw) withdrawal_rows,
        (SELECT COUNT_BIG(*) FROM dbo.PCheque) payable_cheque_rows,
        (SELECT COUNT_BIG(*) FROM dbo.PCash x LEFT JOIN dbo.Pay p ON p.PayId=x.PayId WHERE p.PayId IS NULL) cash_orphan_pay,
        (SELECT COUNT_BIG(*) FROM dbo.PWithdraw x LEFT JOIN dbo.Pay p ON p.PayId=x.PayId WHERE p.PayId IS NULL) withdrawal_orphan_pay,
        (SELECT COUNT_BIG(*) FROM dbo.PCheque x LEFT JOIN dbo.Pay p ON p.PayId=x.PayId WHERE p.PayId IS NULL) cheque_orphan_pay,
        (SELECT COUNT_BIG(*) FROM dbo.Pay p WHERE NOT EXISTS(SELECT 1 FROM dbo.PCash x WHERE x.PayId=p.PayId) AND NOT EXISTS(SELECT 1 FROM dbo.PWithdraw x WHERE x.PayId=p.PayId) AND NOT EXISTS(SELECT 1 FROM dbo.PCheque x WHERE x.PayId=p.PayId)) pays_without_these_three
    """)[0]
    quality = _rows(cursor, """
      SELECT 'cash' instrument,COUNT_BIG(*) rows,COUNT(DISTINCT UniqueId) distinct_uuids,
             SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuid,
             SUM(CASE WHEN PCashAmount>0 THEN 1 ELSE 0 END) positive_amount,
             SUM(CASE WHEN PCashAmount<=0 THEN 1 ELSE 0 END) nonpositive_amount,
             CAST(NULL AS bigint) reconciled
      FROM dbo.PCash
      UNION ALL
      SELECT 'withdrawal',COUNT_BIG(*),COUNT(DISTINCT UniqueId),
             SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END),
             SUM(CASE WHEN PWithDrawAmount>0 THEN 1 ELSE 0 END),
             SUM(CASE WHEN PWithDrawAmount<=0 THEN 1 ELSE 0 END),
             SUM(CASE WHEN IsReconciled=1 THEN 1 ELSE 0 END)
      FROM dbo.PWithdraw
      UNION ALL
      SELECT 'payable_cheque',COUNT_BIG(*),COUNT(DISTINCT UniqueId),
             SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END),
             SUM(CASE WHEN PChequeAmount>0 THEN 1 ELSE 0 END),
             SUM(CASE WHEN PChequeAmount<=0 THEN 1 ELSE 0 END),
             SUM(CASE WHEN IsReconciled=1 THEN 1 ELSE 0 END)
      FROM dbo.PCheque
    """)
    cardinality = _rows(cursor, """
      WITH x AS (
        SELECT p.PayId,
          (SELECT COUNT_BIG(*) FROM dbo.PCash c WHERE c.PayId=p.PayId) cash_count,
          (SELECT COUNT_BIG(*) FROM dbo.PWithdraw w WHERE w.PayId=p.PayId) withdrawal_count,
          (SELECT COUNT_BIG(*) FROM dbo.PCheque q WHERE q.PayId=p.PayId) cheque_count
        FROM dbo.Pay p
      )
      SELECT COUNT_BIG(*) pays,
             SUM(CASE WHEN cash_count+withdrawal_count+cheque_count=0 THEN 1 ELSE 0 END) none_of_three,
             SUM(CASE WHEN cash_count+withdrawal_count+cheque_count=1 THEN 1 ELSE 0 END) one_instrument,
             SUM(CASE WHEN cash_count+withdrawal_count+cheque_count>1 THEN 1 ELSE 0 END) multiple_instruments,
             SUM(CASE WHEN (CASE WHEN cash_count>0 THEN 1 ELSE 0 END + CASE WHEN withdrawal_count>0 THEN 1 ELSE 0 END + CASE WHEN cheque_count>0 THEN 1 ELSE 0 END)>1 THEN 1 ELSE 0 END) mixed_instrument_types,
             MAX(cash_count) max_cash,MAX(withdrawal_count) max_withdrawal,
             MAX(cheque_count) max_cheque,MAX(cash_count+withdrawal_count+cheque_count) max_total
      FROM x
    """)[0]
    return {"pay_status_profile": pay_profile, "instrument_population_and_integrity": population,
            "instrument_quality": quality, "per_pay_instrument_cardinality": cardinality,
            "contract": "Pay is the approved envelope; cash, withdrawal, and cheque are child instruments. One Pay may contain many instruments."}


def _supplier_disbursement(cursor: Any) -> dict[str, Any]:
    instruments = _rows(cursor, """
      SELECT 'cash' instrument,COUNT_BIG(*) rows,COUNT(DISTINCT p.PayId) pays,
             COUNT(DISTINCT s.Id) suppliers,SUM(x.PCashAmount) amount
      FROM dbo.PCash x JOIN dbo.Pay p ON p.PayId=x.PayId
      JOIN GNR.tblSupplier s ON s.ContactId=p.PayeeId
      UNION ALL
      SELECT 'withdrawal',COUNT_BIG(*),COUNT(DISTINCT p.PayId),COUNT(DISTINCT s.Id),SUM(x.PWithDrawAmount)
      FROM dbo.PWithdraw x JOIN dbo.Pay p ON p.PayId=x.PayId
      JOIN GNR.tblSupplier s ON s.ContactId=p.PayeeId
      UNION ALL
      SELECT 'payable_cheque',COUNT_BIG(*),COUNT(DISTINCT p.PayId),COUNT(DISTINCT s.Id),SUM(x.PChequeAmount)
      FROM dbo.PCheque x JOIN dbo.Pay p ON p.PayId=x.PayId
      JOIN GNR.tblSupplier s ON s.ContactId=p.PayeeId
    """)
    cheque_effect = _rows(cursor, """
      SELECT h.PChequeStatusId,COUNT_BIG(*) cheques,SUM(c.PChequeAmount) amount,
             SUM(CASE WHEN c.PChequeIsCertified=1 THEN 1 ELSE 0 END) certified,
             SUM(CASE WHEN c.PChequeIsCertified=0 AND h.PChequeStatusId IN (3,5) THEN c.PChequeAmount ELSE 0 END) official_bed_amount,
             SUM(CASE WHEN c.PChequeIsCertified=0 AND h.PChequeStatusId=2 THEN c.PChequeAmount ELSE 0 END) official_bes_amount
      FROM dbo.PCheque c JOIN dbo.Pay p ON p.PayId=c.PayId
      JOIN GNR.tblSupplier s ON s.ContactId=p.PayeeId
      JOIN dbo.PChequeHistory h ON h.PChequeHistoryId=c.PChequeHistoryId
      GROUP BY h.PChequeStatusId ORDER BY h.PChequeStatusId
    """)
    return {"supplier_directed_instruments": instruments,
            "supplier_payable_cheque_current_cardex_effect": cheque_effect,
            "supplier_link_contract": "Pay.PayeeId joins Supplier.ContactId. Official supplier cardex excludes certified cheques, treats current states 3/5 as Bed and state 2 as Bes, and ignores state 4."}


def _cheque_lifecycle(cursor: Any) -> dict[str, Any]:
    profile = _rows(cursor, """
      SELECT COUNT_BIG(*) cheques,COUNT(DISTINCT UniqueId) distinct_uuids,
             SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuid,
             SUM(CASE WHEN PChequeAmount>0 THEN 1 ELSE 0 END) positive_amount,
             SUM(CASE WHEN PChequeBookItemId IS NOT NULL THEN 1 ELSE 0 END) book_item_present,
             SUM(CASE WHEN NULLIF(LTRIM(RTRIM(SayadNo)),'') IS NOT NULL THEN 1 ELSE 0 END) sayad_present,
             SUM(CASE WHEN PChequeIsCertified=1 THEN 1 ELSE 0 END) certified,
             SUM(CASE WHEN IsReconciled=1 THEN 1 ELSE 0 END) reconciled,
             MIN(PChequeDate) minimum_due_date,MAX(PChequeDate) maximum_due_date
      FROM dbo.PCheque
    """)[0]
    history = _rows(cursor, """
      WITH x AS (SELECT PChequeId,COUNT_BIG(*) events,MAX(PChequeHistoryId) max_id
                 FROM dbo.PChequeHistory GROUP BY PChequeId)
      SELECT COUNT_BIG(*) cheques,
             (SELECT COUNT_BIG(*) FROM dbo.PChequeHistory) events,
             SUM(CASE WHEN x.PChequeId IS NULL THEN 1 ELSE 0 END) without_history,
             SUM(CASE WHEN h.PChequeHistoryId IS NULL THEN 1 ELSE 0 END) invalid_current_ref,
             SUM(CASE WHEN h.PChequeId<>c.PChequeId THEN 1 ELSE 0 END) current_other_cheque,
             SUM(CASE WHEN c.PChequeHistoryId=x.max_id THEN 1 ELSE 0 END) current_is_maximum_id,
             SUM(CASE WHEN c.PChequeHistoryId<>x.max_id THEN 1 ELSE 0 END) current_not_maximum_id,
             MIN(x.events) minimum_events,MAX(x.events) maximum_events,
             AVG(CONVERT(decimal(18,5),x.events)) average_events
      FROM dbo.PCheque c LEFT JOIN x ON x.PChequeId=c.PChequeId
      LEFT JOIN dbo.PChequeHistory h ON h.PChequeHistoryId=c.PChequeHistoryId
    """)[0]
    current = _rows(cursor, """
      SELECT h.PChequeStatusId,COUNT_BIG(*) cheques,SUM(c.PChequeAmount) amount,
             SUM(CASE WHEN c.PChequeIsCertified=1 THEN 1 ELSE 0 END) certified
      FROM dbo.PCheque c JOIN dbo.PChequeHistory h ON h.PChequeHistoryId=c.PChequeHistoryId
      GROUP BY h.PChequeStatusId ORDER BY h.PChequeStatusId
    """)
    initial = _rows(cursor, """
      WITH x AS (SELECT PChequeId,MIN(PChequeHistoryId) min_id FROM dbo.PChequeHistory GROUP BY PChequeId)
      SELECT h.PChequeStatusId,COUNT_BIG(*) cheques
      FROM x JOIN dbo.PChequeHistory h ON h.PChequeHistoryId=x.min_id
      GROUP BY h.PChequeStatusId ORDER BY h.PChequeStatusId
    """)
    transitions = _rows(cursor, """
      WITH x AS (
        SELECT PChequeId,PChequeStatusId,
               LAG(PChequeStatusId) OVER(PARTITION BY PChequeId ORDER BY PChequeHistoryId) previous_status
        FROM dbo.PChequeHistory
      )
      SELECT x.previous_status from_status,x.PChequeStatusId to_status,
             COUNT_BIG(*) transitions,
             SUM(CASE WHEN w.PChequeWorkflowId IS NOT NULL THEN 1 ELSE 0 END) allowed_by_workflow
      FROM x LEFT JOIN dbo.PChequeWorkflow w ON w.PChequeStatusId=x.previous_status
                                              AND w.PChequeNextStatusId=x.PChequeStatusId
      WHERE x.previous_status IS NOT NULL
      GROUP BY x.previous_status,x.PChequeStatusId ORDER BY transitions DESC
    """)
    books = _rows(cursor, """
      SELECT
        (SELECT COUNT_BIG(*) FROM dbo.PChequeBook) books,
        (SELECT COUNT_BIG(*) FROM dbo.PChequeBookItem) book_items,
        (SELECT COUNT_BIG(*) FROM dbo.PChequeBookItem WHERE IsUsed=1) marked_used,
        (SELECT COUNT_BIG(*) FROM dbo.PCheque c WHERE c.PChequeBookItemId IS NOT NULL) cheques_with_item,
        (SELECT COUNT_BIG(*) FROM dbo.PCheque c LEFT JOIN dbo.PChequeBookItem i ON i.PChequeBookItemId=c.PChequeBookItemId WHERE c.PChequeBookItemId IS NOT NULL AND i.PChequeBookItemId IS NULL) orphan_book_item,
        (SELECT COUNT_BIG(*) FROM dbo.PChequeBookItem i WHERE i.IsUsed=1 AND NOT EXISTS(SELECT 1 FROM dbo.PCheque c WHERE c.PChequeBookItemId=i.PChequeBookItemId)) used_without_cheque,
        (SELECT COUNT_BIG(*) FROM (SELECT PChequeBookItemId FROM dbo.PCheque WHERE PChequeBookItemId IS NOT NULL GROUP BY PChequeBookItemId HAVING COUNT_BIG(*)>1)x) reused_item_groups
    """)[0]
    return {"cheque_profile": profile, "history_integrity": history,
            "current_status_distribution": current, "initial_status_distribution": initial,
            "actual_transitions": transitions, "cheque_book_integrity": books,
            "contract": "PCheque.PChequeHistoryId is the current-state pointer and equals the maximum history id for every cheque; history rows are the state event ledger."}


def _window_and_inactive(cursor: Any) -> dict[str, Any]:
    window = _rows(cursor, f"""
      SELECT
       (SELECT COUNT_BIG(*) FROM dbo.Pay WHERE PayDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') pays,
       (SELECT COUNT_BIG(*) FROM dbo.PCash x JOIN dbo.Pay p ON p.PayId=x.PayId WHERE p.PayDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') cash,
       (SELECT COUNT_BIG(*) FROM dbo.PWithdraw x JOIN dbo.Pay p ON p.PayId=x.PayId WHERE p.PayDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') withdrawals,
       (SELECT COUNT_BIG(*) FROM dbo.PCheque x JOIN dbo.Pay p ON p.PayId=x.PayId WHERE p.PayDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') cheques,
       (SELECT COUNT_BIG(*) FROM dbo.PChequeHistory WHERE StatusDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}') cheque_events
    """)[0]
    inactive = _rows(cursor, """
      SELECT (SELECT COUNT_BIG(*) FROM dbo.PChequeRefund) refund_records,
             (SELECT COUNT_BIG(*) FROM dbo.PChequeChangeStatus) bulk_change_headers,
             (SELECT COUNT_BIG(*) FROM dbo.PChequeChangeStatusItm) bulk_change_items,
             (SELECT COUNT_BIG(*) FROM dbo.RPTransferPCheque) transfer_records
    """)[0]
    return {"business_window": {"from": BUSINESS_DATE_FROM, "to": BUSINESS_DATE_TO, "summary": window},
            "currently_empty_process_tables": inactive}


def _quality(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
      WITH seq AS (
        SELECT PChequeId,PChequeStatusId,
               LAG(PChequeStatusId) OVER(PARTITION BY PChequeId ORDER BY PChequeHistoryId) previous_status
        FROM dbo.PChequeHistory
      )
      SELECT
        (SELECT COUNT_BIG(*) FROM dbo.PCash x LEFT JOIN dbo.Pay p ON p.PayId=x.PayId WHERE p.PayId IS NULL) orphan_cash_pay,
        (SELECT COUNT_BIG(*) FROM dbo.PWithdraw x LEFT JOIN dbo.Pay p ON p.PayId=x.PayId WHERE p.PayId IS NULL) orphan_withdrawal_pay,
        (SELECT COUNT_BIG(*) FROM dbo.PCheque x LEFT JOIN dbo.Pay p ON p.PayId=x.PayId WHERE p.PayId IS NULL) orphan_cheque_pay,
        (SELECT COUNT_BIG(*) FROM dbo.PCheque c LEFT JOIN dbo.PChequeHistory h ON h.PChequeHistoryId=c.PChequeHistoryId WHERE h.PChequeHistoryId IS NULL OR h.PChequeId<>c.PChequeId) invalid_current_history,
        (SELECT COUNT_BIG(*) FROM seq x LEFT JOIN dbo.PChequeWorkflow w ON w.PChequeStatusId=x.previous_status AND w.PChequeNextStatusId=x.PChequeStatusId WHERE x.previous_status IS NOT NULL AND w.PChequeWorkflowId IS NULL) observed_transitions_outside_workflow,
        (SELECT COUNT_BIG(*) FROM dbo.PCheque c LEFT JOIN dbo.PChequeBookItem i ON i.PChequeBookItemId=c.PChequeBookItemId WHERE i.PChequeBookItemId IS NULL) cheque_without_valid_book_item,
        (SELECT COUNT_BIG(*) FROM dbo.PChequeBookItem i WHERE i.IsUsed=1 AND NOT EXISTS(SELECT 1 FROM dbo.PCheque c WHERE c.PChequeBookItemId=i.PChequeBookItemId)) used_book_items_without_cheque
    """)[0]


def _sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
      SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition,o.modify_date
      FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
      JOIN sys.sql_modules m ON m.object_id=o.object_id
      WHERE (s.name='dbo' AND o.name IN
        ('BeforePCash','AfterPCash','BeforePWithDraw','BeforePCheque','AfterPCheque',
         'DoPay_CreateFirstPChequeHistory','DoPay_CreateApprovePChequeHistory',
         'DoPCheque_AddPChequeHistory','CheckBalanceBeforePchequeHistory',
         'Usp_Sdsnet_PCheque_Save','usp_sdsnet_PChequeChangeStatus_Save',
         'PChequeHistoryWithPreviousHistory'))
         OR (s.name='Acc' AND o.name='Usp_GetSupplierRemAmount')
      ORDER BY s.name,o.name
    """)


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "supplier_disbursement_and_payable_cheque_lifecycle",
            "scope": {"server": SERVER, "database": DATABASE,
                      "mode": "read-only metadata and aggregate outgoing-payment evidence",
                      "privacy_policy": "no cheque/Sayad/account values, payee/supplier rows, comments, user/host identities, credentials, or raw payments"},
            "safety": _public_safety(safety),
            "tables": [_public_metadata(_table_metadata(cursor, x["object"], x["role"])) for x in DOMAIN_TABLES],
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _consumers(cursor),
            "implicit_link_candidates": _implicit_links(cursor),
            "reference_masters": _masters(cursor),
            "pay_and_instruments": _pay_and_instruments(cursor),
            "supplier_disbursement": _supplier_disbursement(cursor),
            "payable_cheque_lifecycle": _cheque_lifecycle(cursor),
            "activity_and_inactive_paths": _window_and_inactive(cursor),
            "data_quality": _quality(cursor),
            "semantic_contract_sources": _sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "evidence_limits": [
                "PayStatusId=2 is authoritative in this snapshot; ConfirmDate is absent on many confirmed legacy payments.",
                "Supplier disbursements are selected through Pay.PayeeId to Supplier.ContactId and are not equivalent to tblSupSettlement rows.",
                "Certified payable cheques are excluded from the official supplier-cardex cheque branch.",
                "Used cheque-book leaves without a current PCheque require business review and are not automatically defects.",
                "Empty refund/bulk-change tables do not remove workflow capabilities evidenced by status history and procedure contracts.",
                "Cheque/Sayad/account values, payee identities, comments, raw instruments, and raw payments are intentionally excluded.",
                "Formal dependencies do not capture dynamic SQL or every legacy Ref convention.",
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
