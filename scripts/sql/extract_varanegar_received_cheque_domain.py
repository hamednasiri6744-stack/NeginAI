"""Extract Varanegar received-cheque lifecycle and returned-cheque evidence.

Read-only by design. The JSON contains schema metadata, safe reference labels,
aggregate counts, reconciliation results, and selected SQL contracts. It never
persists cheque/account/Sayad/national-code values, payer/customer rows,
comments, usernames, hostnames, credentials, or raw payment records.
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
    {"object": "Acc.TblCheque", "role": "received_cheque_master"},
    {"object": "Acc.tblChqHist", "role": "received_cheque_state_event"},
    {"object": "Acc.tblChqStatus", "role": "current_state_master"},
    {"object": "Acc.tblChqStatFlow", "role": "minimal_state_transition_master"},
    {"object": "dbo.RchequeStatus", "role": "legacy_compatible_state_master"},
    {"object": "dbo.RChequeWorkflow", "role": "allowed_state_transition_master"},
    {"object": "dbo.RChequeAllWorkflow", "role": "transition_process_mapping"},
    {"object": "dbo.RChequeUnpaidReason", "role": "unpaid_reason_master"},
    {"object": "dbo.ChequeUnpaidPlace", "role": "unpaid_location_master"},
    {"object": "dbo.ChequeType", "role": "cheque_type_master"},
    {"object": "Acc.tblPayments", "role": "invoice_and_returned_cheque_allocation_ledger"},
    {"object": "dbo.Receipt", "role": "collection_header"},
    {"object": "dbo.tblRChequeLog", "role": "received_cheque_edit_audit_log"},
    {"object": "Acc.tblChqChangeStatus", "role": "bulk_state_change_header"},
    {"object": "Acc.tblChqChangeStatusItm", "role": "bulk_state_change_item"},
    {"object": "dbo.RChequeRefund", "role": "refund_process_record"},
    {"object": "dbo.CessionToOther", "role": "cession_process_record"},
    {"object": "dbo.CessionToOtherRefund", "role": "cession_refund_process_record"},
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
    """Remove schema fields whose values are deliberately outside the artifact."""
    excluded = {
        "chqno", "accno", "branchname", "accountname", "issuedfor", "sayadno",
        "nationalcode", "comment", "chequeunpaidplacecomment", "rchequeno",
        "rchequebranchname", "rchequecomment", "appuserid", "sqlusername",
        "winusername", "hostname", "applicationname",
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
          WHERE LOWER(c.name) LIKE '%chqref%'
             OR LOWER(c.name) LIKE '%chequeref%'
             OR LOWER(c.name) LIKE '%retcheque%'
             OR LOWER(c.name) LIKE '%mainchq%'
             OR LOWER(c.name) LIKE '%previoushist%'
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
    statuses = _decode_fields(_rows(cursor, """
        SELECT s.ID,CONVERT(varbinary(max),s.Stat) Stat,COUNT_BIG(h.ID) history_usage,
               SUM(CASE WHEN h.IsLast=1 THEN 1 ELSE 0 END) current_usage
        FROM Acc.tblChqStatus s LEFT JOIN Acc.tblChqHist h ON h.StatRef=s.ID
        GROUP BY s.ID,s.Stat ORDER BY s.ID
    """), ("Stat",))
    legacy_statuses = _decode_fields(_rows(cursor, """
        SELECT RChequeStatusId,
               CONVERT(varbinary(max),RChequeStatusName) RChequeStatusName,
               CONVERT(varbinary(max),RchequeStatusAct) RchequeStatusAct
        FROM dbo.RchequeStatus ORDER BY RChequeStatusId
    """), ("RChequeStatusName", "RchequeStatusAct"))
    minimal_flow = _decode_fields(_rows(cursor, """
        SELECT f.Id,f.FromStat,CONVERT(varbinary(max),fs.Stat) FromStatusName,
               f.ToStat,CONVERT(varbinary(max),ts.Stat) ToStatusName
        FROM Acc.tblChqStatFlow f
        LEFT JOIN Acc.tblChqStatus fs ON fs.ID=f.FromStat
        LEFT JOIN Acc.tblChqStatus ts ON ts.ID=f.ToStat
        ORDER BY f.Id
    """), ("FromStatusName", "ToStatusName"))
    workflow = _rows(cursor, """
        SELECT w.RChequeWorkflowId,w.RChequeStatusId,w.RChequeNextStatusId
        FROM dbo.RChequeWorkflow w ORDER BY w.RChequeWorkflowId
    """)
    process_flow = _rows(cursor, """
        SELECT RChequeAllWorkflowId,OldStatusId,NewStatusId,IsActiveInForm,
               RChequeAllWorkflowCode,ProcessTypeId
        FROM dbo.RChequeAllWorkflow ORDER BY RChequeAllWorkflowId
    """)
    reasons = _decode_fields(_rows(cursor, """
        SELECT RChequeUnpaidReasonId,RChequeStatusId,
               CONVERT(varbinary(max),RChequeUnpaidReasonName) RChequeUnpaidReasonName,
               IsActive
        FROM dbo.RChequeUnpaidReason ORDER BY RChequeUnpaidReasonId
    """), ("RChequeUnpaidReasonName",))
    places = _decode_fields(_rows(cursor, """
        SELECT ChequeUnpaidPlaceId,
               CONVERT(varbinary(max),ChequeUnpaidPlaceName) ChequeUnpaidPlaceName,
               IsActive
        FROM dbo.ChequeUnpaidPlace ORDER BY ChequeUnpaidPlaceId
    """), ("ChequeUnpaidPlaceName",))
    types = _decode_fields(_rows(cursor, """
        SELECT t.ChequeTypeId,CONVERT(varbinary(max),t.ChequeTypeName) ChequeTypeName,
               COUNT_BIG(c.ID) cheque_usage
        FROM dbo.ChequeType t LEFT JOIN Acc.TblCheque c ON c.ChequeTypeId=t.ChequeTypeId
        GROUP BY t.ChequeTypeId,t.ChequeTypeName ORDER BY t.ChequeTypeId
    """), ("ChequeTypeName",))
    return {
        "current_status_master": statuses,
        "legacy_compatible_status_master": legacy_statuses,
        "minimal_flow": minimal_flow,
        "allowed_workflow": workflow,
        "process_transition_map": process_flow,
        "unpaid_reasons": reasons,
        "unpaid_places": places,
        "cheque_types": types,
    }


def _cheque_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) cheques,COUNT(DISTINCT UniqueId) distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuids,
               SUM(CASE WHEN ChqAmount>0 THEN 1 ELSE 0 END) positive_amount,
               SUM(CASE WHEN ChqAmount<=0 THEN 1 ELSE 0 END) nonpositive_amount,
               SUM(CASE WHEN ReceiptId IS NOT NULL THEN 1 ELSE 0 END) receipt_linked,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(SayadNo)),'') IS NOT NULL
                        THEN 1 ELSE 0 END) sayad_present,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(NationalCode)),'') IS NOT NULL
                        THEN 1 ELSE 0 END) national_code_present,
               SUM(CASE WHEN MainChqRef IS NOT NULL THEN 1 ELSE 0 END)
                    replacement_child,
               SUM(CASE WHEN IsReconciled=1 THEN 1 ELSE 0 END) reconciled,
               SUM(CASE WHEN IsConvert=1 THEN 1 ELSE 0 END) converted,
               MIN(ChqDate) minimum_due_date,MAX(ChqDate) maximum_due_date,
               MIN(InsDate) minimum_insert_date,MAX(InsDate) maximum_insert_date
        FROM Acc.TblCheque
    """)[0]
    integrity = _rows(cursor, """
        SELECT COUNT_BIG(*) cheques,
               SUM(CASE WHEN r.ReceiptId IS NULL THEN 1 ELSE 0 END) orphan_receipt,
               SUM(CASE WHEN b.BankId IS NULL THEN 1 ELSE 0 END) orphan_bank,
               SUM(CASE WHEN t.ChequeTypeId IS NULL THEN 1 ELSE 0 END) orphan_type,
               SUM(CASE WHEN c.MainChqRef IS NOT NULL AND m.ID IS NULL THEN 1 ELSE 0 END)
                    orphan_main_cheque,
               SUM(CASE WHEN c.MainChqRef=c.ID THEN 1 ELSE 0 END) self_main_ref
        FROM Acc.TblCheque c
        LEFT JOIN dbo.Receipt r ON r.ReceiptId=c.ReceiptId
        LEFT JOIN dbo.Bank b ON b.BankId=c.BankRef
        LEFT JOIN dbo.ChequeType t ON t.ChequeTypeId=c.ChequeTypeId
        LEFT JOIN Acc.TblCheque m ON m.ID=c.MainChqRef
    """)[0]
    keys = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM (SELECT UniqueId FROM Acc.TblCheque
             WHERE UniqueId IS NOT NULL GROUP BY UniqueId HAVING COUNT_BIG(*)>1)x)
                duplicate_uuid_groups,
          (SELECT COUNT_BIG(*) FROM (SELECT BankRef,ChqNo,ChqDate,AccNo
             FROM Acc.TblCheque GROUP BY BankRef,ChqNo,ChqDate,AccNo
             HAVING COUNT_BIG(*)>1)x) duplicate_bank_number_date_account_groups
    """)[0]
    receipt_status = _rows(cursor, """
        SELECT r.ReceiptStatusId,COUNT_BIG(*) cheques
        FROM Acc.TblCheque c JOIN dbo.Receipt r ON r.ReceiptId=c.ReceiptId
        GROUP BY r.ReceiptStatusId ORDER BY r.ReceiptStatusId
    """)
    sayad_coverage = _rows(cursor, """
        SELECT LEFT(InsDate,4) insert_year,COUNT_BIG(*) cheques,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(SayadNo)),'') IS NOT NULL
                        THEN 1 ELSE 0 END) sayad_present,
               SUM(CASE WHEN IsConvert=1 THEN 1 ELSE 0 END) converted
        FROM Acc.TblCheque GROUP BY LEFT(InsDate,4) ORDER BY insert_year
    """)
    return {
        "population": population,
        "reference_integrity": integrity,
        "key_quality_without_key_values": keys,
        "receipt_status_distribution": receipt_status,
        "sayad_presence_by_insert_year_without_values": sayad_coverage,
    }


def _history_profile(cursor: Any) -> dict[str, Any]:
    cardinality = _rows(cursor, """
        WITH x AS (
          SELECT ChqRef,COUNT_BIG(*) histories,
                 SUM(CASE WHEN IsLast=1 THEN 1 ELSE 0 END) current_rows
          FROM Acc.tblChqHist GROUP BY ChqRef
        )
        SELECT COUNT_BIG(*) cheques,
               SUM(CASE WHEN x.ChqRef IS NULL THEN 1 ELSE 0 END) without_history,
               SUM(CASE WHEN x.current_rows=1 THEN 1 ELSE 0 END) exactly_one_current,
               SUM(CASE WHEN x.current_rows=0 THEN 1 ELSE 0 END) no_current,
               SUM(CASE WHEN x.current_rows>1 THEN 1 ELSE 0 END) multiple_current,
               MIN(x.histories) minimum_history,MAX(x.histories) maximum_history,
               AVG(CONVERT(decimal(18,4),x.histories)) average_history
        FROM Acc.TblCheque c LEFT JOIN x ON x.ChqRef=c.ID
    """)[0]
    links = _rows(cursor, """
        SELECT COUNT_BIG(*) histories,
               SUM(CASE WHEN c.ID IS NULL THEN 1 ELSE 0 END) orphan_cheque,
               SUM(CASE WHEN s.ID IS NULL THEN 1 ELSE 0 END) orphan_status,
               SUM(CASE WHEN h.PreviousHistRef IS NOT NULL THEN 1 ELSE 0 END)
                    previous_history_present,
               SUM(CASE WHEN h.PreviousHistRef IS NOT NULL AND prev.ID IS NULL THEN 1 ELSE 0 END)
                    orphan_previous_history,
               SUM(CASE WHEN prev.ID IS NOT NULL AND prev.ChqRef<>h.ChqRef THEN 1 ELSE 0 END)
                    previous_history_other_cheque,
               SUM(CASE WHEN prev.ID IS NOT NULL AND h.PreviousStatRef<>prev.StatRef
                        THEN 1 ELSE 0 END) previous_status_mismatch,
               SUM(CASE WHEN h.TransitionId IS NOT NULL THEN 1 ELSE 0 END)
                    transition_present,
               SUM(CASE WHEN h.TransitionId IS NOT NULL
                              AND w.RChequeAllWorkflowId IS NULL THEN 1 ELSE 0 END)
                    orphan_transition,
               MIN(h.ChangeDate) minimum_change_date,MAX(h.ChangeDate) maximum_change_date
        FROM Acc.tblChqHist h
        LEFT JOIN Acc.TblCheque c ON c.ID=h.ChqRef
        LEFT JOIN Acc.tblChqStatus s ON s.ID=h.StatRef
        LEFT JOIN Acc.tblChqHist prev ON prev.ID=h.PreviousHistRef
        LEFT JOIN dbo.RChequeAllWorkflow w ON w.RChequeAllWorkflowId=h.TransitionId
    """)[0]
    current_sequence = _rows(cursor, """
        WITH x AS (SELECT ChqRef,MAX(ID) maximum_id FROM Acc.tblChqHist GROUP BY ChqRef)
        SELECT COUNT_BIG(*) cheques,
               SUM(CASE WHEN h.ID=x.maximum_id THEN 1 ELSE 0 END) current_is_maximum_id,
               SUM(CASE WHEN h.ID<>x.maximum_id THEN 1 ELSE 0 END) current_not_maximum_id
        FROM x JOIN Acc.tblChqHist h ON h.ChqRef=x.ChqRef AND h.IsLast=1
    """)[0]
    initial = _rows(cursor, """
        WITH x AS (SELECT ChqRef,MIN(ID) minimum_id FROM Acc.tblChqHist GROUP BY ChqRef)
        SELECT h.StatRef,COUNT_BIG(*) cheques,
               SUM(CASE WHEN h.PreviousStatRef IS NULL THEN 1 ELSE 0 END)
                    previous_status_null,
               SUM(CASE WHEN h.PreviousHistRef IS NULL THEN 1 ELSE 0 END)
                    previous_history_null
        FROM x JOIN Acc.tblChqHist h ON h.ID=x.minimum_id
        GROUP BY h.StatRef ORDER BY cheques DESC
    """)
    transitions = _rows(cursor, """
        SELECT h.PreviousStatRef from_status,h.StatRef to_status,COUNT_BIG(*) transitions,
               SUM(CASE WHEN h.TransitionId IS NOT NULL THEN 1 ELSE 0 END)
                    with_transition_id,
               SUM(CASE WHEN w.RChequeAllWorkflowId IS NOT NULL
                              AND w.OldStatusId=h.PreviousStatRef
                              AND w.NewStatusId=h.StatRef THEN 1 ELSE 0 END)
                    transition_definition_matches
        FROM Acc.tblChqHist h
        LEFT JOIN dbo.RChequeAllWorkflow w ON w.RChequeAllWorkflowId=h.TransitionId
        WHERE h.PreviousStatRef IS NOT NULL
        GROUP BY h.PreviousStatRef,h.StatRef ORDER BY transitions DESC
    """)
    window = _rows(cursor, f"""
        SELECT COUNT_BIG(*) events,COUNT(DISTINCT ChqRef) cheques,
               COUNT(DISTINCT StatRef) statuses,
               SUM(CASE WHEN IsLast=1 THEN 1 ELSE 0 END) current_events
        FROM Acc.tblChqHist
        WHERE ChangeDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
    """)[0]
    optionals = _rows(cursor, """
        SELECT
          SUM(CASE WHEN RChequeUnpaidReasonId IS NOT NULL THEN 1 ELSE 0 END)
                unpaid_reason_present,
          SUM(CASE WHEN ChequeUnpaidPlaceId IS NOT NULL THEN 1 ELSE 0 END)
                unpaid_place_present,
          SUM(CASE WHEN LegalType IS NOT NULL THEN 1 ELSE 0 END) legal_type_present,
          SUM(CASE WHEN ChqChangeStatusRef IS NOT NULL THEN 1 ELSE 0 END)
                bulk_change_ref_present,
          SUM(CASE WHEN CessionToOtherRefundRef IS NOT NULL THEN 1 ELSE 0 END)
                cession_refund_present,
          SUM(CASE WHEN RChequeRefundRef IS NOT NULL THEN 1 ELSE 0 END) refund_ref_present,
          SUM(CASE WHEN CessionToOtherRef IS NOT NULL THEN 1 ELSE 0 END) cession_present,
          SUM(CASE WHEN DepBranchRef IS NOT NULL THEN 1 ELSE 0 END)
                bank_deposit_branch_present,
          SUM(CASE WHEN SafeId IS NOT NULL THEN 1 ELSE 0 END) safe_present,
          SUM(CASE WHEN FromSafeId IS NOT NULL THEN 1 ELSE 0 END) from_safe_present,
          SUM(CASE WHEN DestinationSafeId IS NOT NULL THEN 1 ELSE 0 END)
                destination_safe_present
        FROM Acc.tblChqHist
    """)[0]
    return {
        "event_cardinality": cardinality,
        "chain_and_transition_integrity": links,
        "current_event_is_latest": current_sequence,
        "initial_status_distribution": initial,
        "actual_transition_distribution": transitions,
        "business_window": {"from": BUSINESS_DATE_FROM, "to": BUSINESS_DATE_TO, "summary": window},
        "optional_context_presence_without_values": optionals,
    }


def _current_state_profile(cursor: Any) -> dict[str, Any]:
    states = _rows(cursor, """
        SELECT h.StatRef,COUNT_BIG(*) cheques,SUM(c.ChqAmount) total_amount,
               SUM(CASE WHEN c.PayId IS NOT NULL THEN 1 ELSE 0 END) cheque_pay_link,
               SUM(CASE WHEN h.DepBranchRef IS NOT NULL THEN 1 ELSE 0 END)
                    deposit_branch_present,
               SUM(CASE WHEN h.SafeId IS NOT NULL THEN 1 ELSE 0 END) safe_present,
               SUM(CASE WHEN h.RChequeUnpaidReasonId IS NOT NULL THEN 1 ELSE 0 END)
                    unpaid_reason_present,
               SUM(CASE WHEN h.ChequeUnpaidPlaceId IS NOT NULL THEN 1 ELSE 0 END)
                    unpaid_place_present,
               SUM(CASE WHEN h.LegalType IS NOT NULL THEN 1 ELSE 0 END) legal_type_present
        FROM Acc.TblCheque c JOIN Acc.tblChqHist h ON h.ChqRef=c.ID AND h.IsLast=1
        GROUP BY h.StatRef ORDER BY h.StatRef
    """)
    status7_pay = _rows(cursor, """
        SELECT COUNT_BIG(*) cessioned_cheques,
               SUM(CASE WHEN c.PayId IS NOT NULL THEN 1 ELSE 0 END) with_pay,
               SUM(CASE WHEN c.PayId IS NOT NULL AND p.PayId IS NULL THEN 1 ELSE 0 END)
                    orphan_pay
        FROM Acc.TblCheque c
        JOIN Acc.tblChqHist h ON h.ChqRef=c.ID AND h.IsLast=1
        LEFT JOIN dbo.Pay p ON p.PayId=c.PayId
        WHERE h.StatRef=7
    """)[0]
    return {
        "status_distribution_and_context": states,
        "cessioned_status_pay_link": status7_pay,
        "current_state_contract": (
            "Current state is the sole IsLast history event, not a column on TblCheque. "
            "Status 8 is a transient safe-transfer event and has no current rows."
        ),
    }


def _invoice_payment_effect(cursor: Any) -> dict[str, Any]:
    by_status = _rows(cursor, """
        SELECT h.StatRef,COUNT_BIG(p.ID) payment_rows,COUNT(DISTINCT p.ChqRef) cheques,
               COUNT(DISTINCT p.SaleRef) sales,
               SUM(CASE WHEN p.PayTypeRef IN (2,1008) THEN 1 ELSE 0 END)
                    cheque_pay_type_rows,
               SUM(CASE WHEN p.PayTypeRef IN (2,1008) THEN p.Amount ELSE 0 END)
                    cheque_allocation_amount
        FROM Acc.tblPayments p
        JOIN Acc.tblChqHist h ON h.ChqRef=p.ChqRef AND h.IsLast=1
        WHERE p.ChqRef IS NOT NULL
        GROUP BY h.StatRef ORDER BY h.StatRef
    """)
    excluded = _rows(cursor, """
        SELECT COUNT_BIG(*) payment_rows,COUNT(DISTINCT p.ChqRef) cheques,
               COUNT(DISTINCT p.SaleRef) sales,SUM(p.Amount) allocation_amount
        FROM Acc.tblPayments p
        JOIN Acc.tblChqHist h ON h.ChqRef=p.ChqRef AND h.IsLast=1
        WHERE p.ChqRef IS NOT NULL AND p.PayTypeRef IN (2,1008)
          AND h.StatRef IN (4,5,9)
    """)[0]
    return {
        "allocation_by_current_cheque_status": by_status,
        "officially_excluded_returned_refunded_legal_allocations": excluded,
        "contract": (
            "usp_GetSalePayAmount includes cheque PayTypes 2/1008 only while the effective "
            "current cheque state is not 4, 5, or 9. Status 7 remains effective payment."
        ),
    }


def _returned_cheque_settlement(cursor: Any) -> dict[str, Any]:
    ledger = _rows(cursor, """
        SELECT COUNT_BIG(*) payments,COUNT(DISTINCT p.RetChequeRef) cheques,
               COUNT(DISTINCT p.CustRef) customers,
               SUM(CASE WHEN c.ID IS NULL THEN 1 ELSE 0 END) orphan_cheque,
               SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) missing_current_history,
               SUM(CASE WHEN p.CustRef<>c.CustRef THEN 1 ELSE 0 END)
                    customer_mismatch_rows,
               SUM(CASE WHEN p.Amount>0 THEN 1 ELSE 0 END) positive_amount,
               SUM(CASE WHEN p.Amount<=0 THEN 1 ELSE 0 END) nonpositive_amount
        FROM Acc.tblPayments p
        LEFT JOIN Acc.TblCheque c ON c.ID=p.RetChequeRef
        LEFT JOIN Acc.tblChqHist h ON h.ChqRef=c.ID AND h.IsLast=1
        WHERE p.RetChequeRef IS NOT NULL
    """)[0]
    by_status = _rows(cursor, """
        SELECT h.StatRef,COUNT_BIG(p.ID) payments,COUNT(DISTINCT p.RetChequeRef) cheques,
               SUM(p.Amount) settled_amount
        FROM Acc.tblPayments p
        JOIN Acc.tblChqHist h ON h.ChqRef=p.RetChequeRef AND h.IsLast=1
        WHERE p.RetChequeRef IS NOT NULL
        GROUP BY h.StatRef ORDER BY h.StatRef
    """)
    coverage = _rows(cursor, """
        WITH p AS (
          SELECT RetChequeRef,SUM(Amount) settled
          FROM Acc.tblPayments WHERE RetChequeRef IS NOT NULL GROUP BY RetChequeRef
        )
        SELECT COUNT_BIG(*) current_returned_refunded_or_legal,
               SUM(CASE WHEN p.RetChequeRef IS NULL THEN 1 ELSE 0 END) no_settlement,
               SUM(CASE WHEN p.settled>0 AND p.settled<c.ChqAmount THEN 1 ELSE 0 END)
                    partial,
               SUM(CASE WHEN p.settled=c.ChqAmount THEN 1 ELSE 0 END) fully_settled,
               SUM(CASE WHEN p.settled>c.ChqAmount THEN 1 ELSE 0 END) over_settled
        FROM Acc.TblCheque c
        JOIN Acc.tblChqHist h ON h.ChqRef=c.ID AND h.IsLast=1
        LEFT JOIN p ON p.RetChequeRef=c.ID
        WHERE h.StatRef IN (4,5,9)
    """)[0]
    pay_types = _rows(cursor, """
        SELECT p.PayTypeRef,COUNT_BIG(*) payments,COUNT(DISTINCT p.RetChequeRef) cheques,
               SUM(p.Amount) amount
        FROM Acc.tblPayments p WHERE p.RetChequeRef IS NOT NULL
        GROUP BY p.PayTypeRef ORDER BY payments DESC
    """)
    projection = _rows(cursor, """
        WITH invalid AS (
          SELECT p.SaleRef,SUM(p.Amount) amount
          FROM Acc.tblPayments p
          JOIN Acc.tblChqHist h ON h.ChqRef=p.ChqRef AND h.IsLast=1
                              AND h.StatRef IN (4,5,9)
          WHERE p.SaleRef IS NOT NULL GROUP BY p.SaleRef
        ),settled AS (
          SELECT SaleRef,SUM(Amount) amount FROM Acc.tblPayments
          WHERE RetChequeRef IS NOT NULL AND SaleRef IS NOT NULL GROUP BY SaleRef
        ),x AS (
          SELECT o.ID,o.RetChequeRemainAmount,
                 CASE WHEN ISNULL(i.amount,0)-ISNULL(s.amount,0)>0
                      THEN ISNULL(i.amount,0)-ISNULL(s.amount,0) ELSE 0 END expected
          FROM SLE.tblOpenInvoice o
          LEFT JOIN invalid i ON i.SaleRef=o.ID
          LEFT JOIN settled s ON s.SaleRef=o.ID
        )
        SELECT COUNT_BIG(*) projection_rows,
               SUM(CASE WHEN ABS(CONVERT(float,RetChequeRemainAmount-expected))<0.01
                        THEN 1 ELSE 0 END) exact,
               SUM(CASE WHEN ABS(CONVERT(float,RetChequeRemainAmount-expected))>=0.01
                        THEN 1 ELSE 0 END) mismatch,
               SUM(CASE WHEN expected>0 THEN 1 ELSE 0 END) positive_remaining,
               MAX(ABS(CONVERT(float,RetChequeRemainAmount-expected))) maximum_difference
        FROM x
    """)[0]
    mismatch_context = _rows(cursor, """
        SELECT COUNT_BIG(*) mismatch_payments,COUNT(DISTINCT p.RetChequeRef) cheques,
               COUNT(DISTINCT p.CustRef) payment_customers,
               COUNT(DISTINCT c.CustRef) cheque_customers,
               SUM(CASE WHEN c.ManualCustRef IS NOT NULL THEN 1 ELSE 0 END)
                    cheque_has_manual_customer,
               SUM(CASE WHEN c.ManualCustRef=p.CustRef THEN 1 ELSE 0 END)
                    matches_manual_customer
        FROM Acc.tblPayments p JOIN Acc.TblCheque c ON c.ID=p.RetChequeRef
        WHERE p.CustRef<>c.CustRef
    """)[0]
    return {
        "returned_cheque_settlement_ledger": ledger,
        "settlement_by_current_state": by_status,
        "per_cheque_settlement_coverage": coverage,
        "settlement_pay_types": pay_types,
        "open_invoice_sale_level_projection_reconciliation": projection,
        "cross_customer_settlement_review": mismatch_context,
        "contract": (
            "Per-cheque remaining amount is cheque amount minus RetChequeRef allocations. "
            "OpenInvoice instead pools invalid cheque allocations and RetChequeRef settlements "
            "by SaleRef, clamps only negative remainder to zero, and reconciles exactly."
        ),
    }


def _audit_and_inactive_paths(cursor: Any) -> dict[str, Any]:
    edit_log = _rows(cursor, """
        SELECT COUNT_BIG(*) log_rows,COUNT(DISTINCT ChequeID) cheques,
               SUM(CASE WHEN c.ID IS NULL THEN 1 ELSE 0 END) orphan_cheque,
               MIN(l.ModifiedDate) minimum_modified,MAX(l.ModifiedDate) maximum_modified
        FROM dbo.tblRChequeLog l LEFT JOIN Acc.TblCheque c ON c.ID=l.ChequeID
    """)[0]
    empty_paths = _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM Acc.tblChqChangeStatus) bulk_change_headers,
          (SELECT COUNT_BIG(*) FROM Acc.tblChqChangeStatusItm) bulk_change_items,
          (SELECT COUNT_BIG(*) FROM dbo.RChequeRefund) refund_records,
          (SELECT COUNT_BIG(*) FROM dbo.CessionToOther) cession_records,
          (SELECT COUNT_BIG(*) FROM dbo.CessionToOtherRefund) cession_refund_records
    """)[0]
    return {
        "edit_audit_log_without_raw_values": edit_log,
        "currently_empty_process_tables": empty_paths,
        "boundary": (
            "Empty process tables do not remove the capability: active state transitions and "
            "legacy PayId links prove that the workflow has alternative historical paths."
        ),
    }


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition,o.modify_date
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE (s.name='Acc' AND o.name IN
              ('usp_GetSalePayAmount','GetRetChequeRemAmount','vwTransferCheque',
               'UspCHQAddChqHist','UspCHQAddChqHistIsValid',
               'usp_CustReturnedChequeValidation'))
           OR (s.name='SLE' AND o.name='usp_Prepare_OpenInvoice')
           OR (s.name='dbo' AND o.name IN
              ('RCheque','RCheque2','DoReceipt_CreateFirstRChequeHistory',
               'DoRCheque_AddRChequeHistory','Usp_Sdsnet_Rcheque_BeforeSave',
               'Usp_Sdsnet_Rcheque_Save','usp_sdsnet_RChequeChangeStatus_BeforeSave',
               'usp_sdsnet_RChequeChangeStatus_Save','Usp_CheckRemRetChequeRef'))
        ORDER BY s.name,o.name
    """)


def _data_quality(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        WITH current_count AS (
          SELECT ChqRef,SUM(CASE WHEN IsLast=1 THEN 1 ELSE 0 END) current_rows
          FROM Acc.tblChqHist GROUP BY ChqRef
        )
        SELECT
          (SELECT COUNT_BIG(*) FROM Acc.TblCheque c LEFT JOIN current_count x ON x.ChqRef=c.ID
             WHERE ISNULL(x.current_rows,0)<>1) cheques_without_exactly_one_current_event,
          (SELECT COUNT_BIG(*) FROM Acc.tblChqHist h LEFT JOIN Acc.tblChqHist p
             ON p.ID=h.PreviousHistRef WHERE h.PreviousHistRef IS NOT NULL AND p.ID IS NULL)
                orphan_previous_history,
          (SELECT COUNT_BIG(*) FROM Acc.tblChqHist h LEFT JOIN dbo.RChequeAllWorkflow w
             ON w.RChequeAllWorkflowId=h.TransitionId
             WHERE h.TransitionId IS NOT NULL AND
                  (w.RChequeAllWorkflowId IS NULL OR w.OldStatusId<>h.PreviousStatRef
                   OR w.NewStatusId<>h.StatRef)) invalid_transition_mapping,
          (SELECT COUNT_BIG(*) FROM Acc.TblCheque c JOIN Acc.tblChqHist h
             ON h.ChqRef=c.ID AND h.IsLast=1 WHERE h.StatRef=7 AND c.PayId IS NULL)
                cessioned_current_cheques_without_pay_link,
          (SELECT COUNT_BIG(*) FROM Acc.TblCheque WHERE MainChqRef IS NOT NULL)
                current_replacement_child_rows,
          (SELECT COUNT_BIG(*) FROM Acc.tblPayments p JOIN Acc.TblCheque c
             ON c.ID=p.RetChequeRef WHERE p.RetChequeRef IS NOT NULL AND p.CustRef<>c.CustRef)
                cross_customer_returned_cheque_settlement_rows
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
            "domain": "received_cheque_lifecycle_and_returned_cheque_settlement",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata and aggregate received-cheque evidence",
                "privacy_policy": (
                    "no cheque/account/Sayad/national-code values, payer/customer rows, "
                    "comments, usernames, hostnames, credentials, or raw payments"
                ),
            },
            "safety": _public_safety(private_safety),
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "reference_masters": _reference_masters(cursor),
            "received_cheques": _cheque_profile(cursor),
            "state_history": _history_profile(cursor),
            "current_state": _current_state_profile(cursor),
            "invoice_payment_effect": _invoice_payment_effect(cursor),
            "returned_cheque_settlement": _returned_cheque_settlement(cursor),
            "audit_and_inactive_paths": _audit_and_inactive_paths(cursor),
            "data_quality": _data_quality(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "evidence_limits": [
                "Cheque state is event-sourced through tblChqHist; TblCheque has no current-state column.",
                "Status 6 exists only in the legacy-compatible master and is absent from the active Acc status master and data.",
                "Status 8 is a transient safe-transfer event and is never current in this snapshot.",
                "Current MainChqRef usage is zero, although official payment logic supports replacement cheques.",
                "OpenInvoice returned-cheque remainder is pooled by SaleRef, not derived per individual cheque.",
                "Cross-customer RetChequeRef allocations require business review and are not automatically classified as defects.",
                "Cheque/account/Sayad/national-code values and raw audit/payment rows are intentionally excluded.",
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
