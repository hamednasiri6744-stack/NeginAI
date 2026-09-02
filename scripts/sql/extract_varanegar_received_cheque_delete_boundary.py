"""Extract received-cheque master deletion and receipt-cleanup boundaries read-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)
from extract_varanegar_ngt_order_target_deletion_boundary import _executable_text


MODULES = (
    ("Acc", "uspCHQDelete"),
    ("Acc", "uspCHQDeleteIsValid"),
    ("Acc", "UspChequeOperation"),
    ("dbo", "BeforeRCheque"),
    ("dbo", "DeleteDataFromAccyear"),
    ("dbo", "DoPOrder_ReSendPayment"),
    ("dbo", "NGT_RollBackTour"),
    ("dbo", "Trg_RCheque_TblCheque"),
    ("dbo", "usp_RollbackTourToReceivedStatue"),
    ("dbo", "usp_sdsnet_Receipt_Save"),
)

DIRECT_MASTER_DELETE_MODULES = {
    "Acc.uspCHQDelete",
    "dbo.DeleteDataFromAccyear",
    "dbo.DoPOrder_ReSendPayment",
    "dbo.NGT_RollBackTour",
    "dbo.Trg_RCheque_TblCheque",
    "dbo.usp_RollbackTourToReceivedStatue",
    "dbo.usp_sdsnet_Receipt_Save",
}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pos(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


def _count(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code, re.I | re.S))


def _profiles(cursor: Any) -> list[dict[str, Any]]:
    profiles = []
    for schema, name in MODULES:
        row = _rows(
            cursor,
            """
            SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,m.definition
            FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
            LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
            WHERE s.name=%s AND o.name=%s
            """,
            (schema, name),
        )[0]
        definition = row.pop("definition") or ""
        code = " ".join(
            _executable_text(definition).replace("[", "").replace("]", "").casefold().split()
        )
        qualified_name = f"{schema}.{name}"
        history_delete = _pos(code, r"\bdelete\s+(?:from\s+)?(?:acc\.)?tblchqhist\b")
        master_delete = _pos(
            code,
            r"\bdelete\s+(?:from\s+)?(?:(?:acc\.)?tblcheque|(?:dbo\.)?rcheque)\b",
        )
        receipt_delete = _pos(code, r"\bdelete\s+(?:from\s+)?(?:dbo\.)?receipt\b")
        begin_tx = _pos(code, r"\bbegin\s+(?:tran|transaction)\b")
        profiles.append(
            {
                **row,
                "qualified_name": qualified_name,
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "expected_direct_master_delete_candidate": qualified_name
                in DIRECT_MASTER_DELETE_MODULES,
                "owns_explicit_transaction": begin_tx is not None,
                "has_commit_signal": bool(re.search(r"\bcommit\b", code)),
                "has_rollback_signal": bool(re.search(r"\brollback\b", code)),
                "has_try_catch": "begin try" in code and "begin catch" in code,
                "history_delete_statement_count": _count(
                    code, r"\bdelete\s+(?:from\s+)?(?:acc\.)?tblchqhist\b"
                ),
                "master_delete_statement_count": _count(
                    code,
                    r"\bdelete\s+(?:from\s+)?(?:(?:acc\.)?tblcheque|(?:dbo\.)?rcheque)\b",
                ),
                "receipt_delete_statement_count": _count(
                    code, r"\bdelete\s+(?:from\s+)?(?:dbo\.)?receipt\b"
                ),
                "cash_detail_delete_statement_count": _count(
                    code, r"\bdelete\s+(?:from\s+)?(?:dbo\.)?rcashdetail\b"
                ),
                "cash_delete_statement_count": _count(
                    code, r"\bdelete\s+(?:from\s+)?(?:dbo\.)?rcash\b"
                ),
                "history_delete_precedes_master_delete": history_delete is not None
                and master_delete is not None
                and history_delete < master_delete,
                "master_delete_precedes_receipt_delete": master_delete is not None
                and receipt_delete is not None
                and master_delete < receipt_delete,
                "has_full_receipt_delete_branch_sequence": bool(
                    re.search(
                        r"delete\s+ch\s+from\s+acc\.tblchqhist.*?"
                        r"delete\s+from\s+acc\.tblcheque.*?"
                        r"delete\s+from\s+receipt\b",
                        code,
                        re.I | re.S,
                    )
                ),
                "calls_delete_validator": bool(
                    re.search(r"\b(?:exec|execute)\s+(?:acc\.)?uspchqdeleteisvalid\b", code)
                ),
                "calls_before_rcheque": bool(
                    re.search(r"\b(?:exec|execute)\s+(?:dbo\.)?beforercheque\b", code)
                ),
                "calls_usp_chq_delete": bool(
                    re.search(r"\b(?:exec|execute)\s+(?:acc\.)?uspchqdelete\b", code)
                ),
                "uses_transaction_savepoint_signal": "save transaction" in code,
                "definition_or_offsets_persisted": False,
            }
        )
    return profiles


def _master_log(cursor: Any) -> dict[str, Any]:
    events = _rows(
        cursor,
        """
        SELECT OperationType,COUNT_BIG(*) event_count,COUNT(DISTINCT OperationId) distinct_id_count,
          SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_event_count,MIN(TransDate) first_event_date,MAX(TransDate) last_event_date
        FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
        WHERE OperationTable='Acc.TblCheque'
        GROUP BY OperationType ORDER BY OperationType
        """,
    )
    coverage = _rows(
        cursor,
        """
        WITH l AS (
          SELECT OperationId,
            SUM(CASE WHEN OperationType='INSERT' THEN 1 ELSE 0 END) insert_count,
            SUM(CASE WHEN OperationType='DELETE' THEN 1 ELSE 0 END) delete_count
          FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='Acc.TblCheque' GROUP BY OperationId
        )
        SELECT COUNT_BIG(*) logged_id_count,
          SUM(CASE WHEN c.ID IS NOT NULL THEN 1 ELSE 0 END) currently_present_count,
          SUM(CASE WHEN c.ID IS NULL THEN 1 ELSE 0 END) currently_absent_count,
          SUM(CASE WHEN insert_count>0 AND delete_count>0 THEN 1 ELSE 0 END) both_event_count,
          SUM(CASE WHEN insert_count=0 AND delete_count>0 THEN 1 ELSE 0 END) delete_only_count,
          SUM(CASE WHEN insert_count>0 AND delete_count=0 AND c.ID IS NULL THEN 1 ELSE 0 END)
            insert_only_but_absent_count,
          SUM(CASE WHEN delete_count>0 AND c.ID IS NOT NULL THEN 1 ELSE 0 END)
            deleted_but_present_count
        FROM l LEFT JOIN Acc.TblCheque c ON c.ID=l.OperationId
        """,
    )[0]
    tails = _rows(
        cursor,
        """
        WITH d AS (
          SELECT ID,SPID,TransDate FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
          WHERE OperationTable='Acc.TblCheque' AND OperationType='DELETE'
        ), p AS (
          SELECT d.ID delete_id,d.TransDate,
            ROW_NUMBER() OVER(PARTITION BY d.ID ORDER BY l.ID DESC) rn,
            l.OperationTable,l.OperationType
          FROM d LEFT JOIN GNR.tblLog l WITH (INDEX(PK_tblLog))
            ON l.ID<d.ID AND l.ID>=d.ID-100 AND l.SPID=d.SPID
           AND l.TransDate<=d.TransDate AND l.TransDate>=DATEADD(second,-30,d.TransDate)
        ), n AS (
          SELECT d.ID delete_id,
            ROW_NUMBER() OVER(PARTITION BY d.ID ORDER BY l.ID) rn,
            l.OperationTable,l.OperationType
          FROM d LEFT JOIN GNR.tblLog l WITH (INDEX(PK_tblLog))
            ON l.ID>d.ID AND l.ID<=d.ID+30 AND l.SPID=d.SPID
           AND l.TransDate>=d.TransDate AND l.TransDate<DATEADD(second,30,d.TransDate)
        ), a AS (
          SELECT d.ID,d.TransDate,
            MAX(CASE WHEN p.rn=1 THEN p.OperationTable+':'+p.OperationType END) previous_event,
            SUM(CASE WHEN p.OperationTable='Acc.tblChqHist' AND p.OperationType='DELETE'
              THEN 1 ELSE 0 END) history_delete_lookback
          FROM d LEFT JOIN p ON p.delete_id=d.ID GROUP BY d.ID,d.TransDate
        ), b AS (
          SELECT n.delete_id,
            MAX(CASE WHEN rn=1 THEN OperationTable+':'+OperationType END) next_event,
            MAX(CASE WHEN rn=2 THEN OperationTable+':'+OperationType END) second_next_event,
            SUM(CASE WHEN OperationTable='dbo.Receipt' AND OperationType='DELETE'
              THEN 1 ELSE 0 END) receipt_delete_lookahead,
            SUM(CASE WHEN OperationTable='dbo.Receipt' AND OperationType='UPDATE'
              THEN 1 ELSE 0 END) receipt_update_lookahead,
            SUM(CASE WHEN OperationTable='dbo.RCashDetail' AND OperationType='UPDATE'
              THEN 1 ELSE 0 END) cash_detail_update_lookahead
          FROM n GROUP BY n.delete_id
        ), x AS (
          SELECT CASE WHEN a.TransDate>='20260601' AND a.TransDate<'20260901'
              THEN 'RECENT_THREE_MONTHS' ELSE 'RETAINED_OLDER' END period,
            previous_event,next_event,second_next_event,history_delete_lookback,
            receipt_delete_lookahead,receipt_update_lookahead,cash_detail_update_lookahead
          FROM a JOIN b ON b.delete_id=a.ID
        )
        SELECT period,previous_event,next_event,second_next_event,history_delete_lookback,
          receipt_delete_lookahead,receipt_update_lookahead,cash_detail_update_lookahead,
          COUNT_BIG(*) master_delete_event_count
        FROM x GROUP BY period,previous_event,next_event,second_next_event,
          history_delete_lookback,receipt_delete_lookahead,receipt_update_lookahead,
          cash_detail_update_lookahead
        ORDER BY period,master_delete_event_count DESC
        """,
    )
    categories = _rows(
        cursor,
        """
        WITH d AS (
          SELECT ID,SPID,TransDate FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
          WHERE OperationTable='Acc.TblCheque' AND OperationType='DELETE'
        ), x AS (
          SELECT d.ID,d.TransDate,
            MAX(CASE WHEN l.OperationTable='dbo.Receipt' AND l.OperationType='DELETE'
              THEN 1 ELSE 0 END) has_receipt_delete,
            MAX(CASE WHEN l.OperationTable='dbo.Receipt' AND l.OperationType='UPDATE'
              THEN 1 ELSE 0 END) has_receipt_update,
            MAX(CASE WHEN l.OperationTable='dbo.RCashDetail' AND l.OperationType='UPDATE'
              THEN 1 ELSE 0 END) has_cash_detail_update,
            COUNT(l.ID) following_event_count
          FROM d LEFT JOIN GNR.tblLog l WITH (INDEX(PK_tblLog))
            ON l.ID>d.ID AND l.ID<=d.ID+30 AND l.SPID=d.SPID
           AND l.TransDate>=d.TransDate AND l.TransDate<DATEADD(second,30,d.TransDate)
          GROUP BY d.ID,d.TransDate
        )
        SELECT CASE WHEN TransDate>='20260601' AND TransDate<'20260901'
            THEN 'RECENT_THREE_MONTHS' ELSE 'RETAINED_OLDER' END period,
          CASE WHEN has_receipt_delete=1 THEN 'RECEIPT_DELETE_TAIL'
               WHEN has_receipt_update=1 THEN 'RECEIPT_UPDATE_TAIL'
               WHEN has_cash_detail_update=1 THEN 'CASH_DETAIL_UPDATE_TAIL'
               WHEN following_event_count=0 THEN 'ISOLATED_TAIL'
               ELSE 'OTHER_TAIL' END tail_category,
          COUNT_BIG(*) master_delete_event_count
        FROM x GROUP BY CASE WHEN TransDate>='20260601' AND TransDate<'20260901'
            THEN 'RECENT_THREE_MONTHS' ELSE 'RETAINED_OLDER' END,
          CASE WHEN has_receipt_delete=1 THEN 'RECEIPT_DELETE_TAIL'
               WHEN has_receipt_update=1 THEN 'RECEIPT_UPDATE_TAIL'
               WHEN has_cash_detail_update=1 THEN 'CASH_DETAIL_UPDATE_TAIL'
               WHEN following_event_count=0 THEN 'ISOLATED_TAIL'
               ELSE 'OTHER_TAIL' END
        ORDER BY period,tail_category
        """,
    )
    return {
        "event_counts": events,
        "logged_id_coverage": coverage,
        "anonymous_adjacent_tail_shapes": tails,
        "tail_categories": categories,
    }


def _receipt_delete_batches(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH d AS (
          SELECT ID,SPID,TransDate FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
          WHERE OperationTable='dbo.Receipt' AND OperationType='DELETE'
        ), p AS (
          SELECT d.ID,d.TransDate,
            SUM(CASE WHEN l.OperationTable='Acc.TblCheque' AND l.OperationType='DELETE'
              THEN 1 ELSE 0 END) master_delete_count,
            SUM(CASE WHEN l.OperationTable='Acc.tblChqHist' AND l.OperationType='DELETE'
              THEN 1 ELSE 0 END) history_delete_count,
            SUM(CASE WHEN l.OperationTable='dbo.RCashDetail' AND l.OperationType='DELETE'
              THEN 1 ELSE 0 END) cash_detail_delete_count,
            SUM(CASE WHEN l.OperationTable='dbo.RCash' AND l.OperationType='DELETE'
              THEN 1 ELSE 0 END) cash_delete_count
          FROM d LEFT JOIN GNR.tblLog l WITH (INDEX(PK_tblLog))
            ON l.ID<d.ID AND l.ID>=d.ID-150 AND l.SPID=d.SPID
           AND l.TransDate<=d.TransDate AND l.TransDate>=DATEADD(second,-30,d.TransDate)
          GROUP BY d.ID,d.TransDate
        )
        SELECT CASE WHEN TransDate>='20260601' AND TransDate<'20260901'
            THEN 'RECENT_THREE_MONTHS' ELSE 'RETAINED_OLDER' END period,
          master_delete_count,history_delete_count,cash_detail_delete_count,cash_delete_count,
          COUNT_BIG(*) receipt_delete_batch_count
        FROM p WHERE master_delete_count>0
        GROUP BY CASE WHEN TransDate>='20260601' AND TransDate<'20260901'
            THEN 'RECENT_THREE_MONTHS' ELSE 'RETAINED_OLDER' END,
          master_delete_count,history_delete_count,cash_detail_delete_count,cash_delete_count
        ORDER BY period,receipt_delete_batch_count DESC
        """,
    )


def _receipt_log(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT OperationType,COUNT_BIG(*) event_count,COUNT(DISTINCT OperationId) distinct_id_count,
          SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_event_count,MIN(TransDate) first_event_date,MAX(TransDate) last_event_date
        FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
        WHERE OperationTable='dbo.Receipt'
        GROUP BY OperationType ORDER BY OperationType
        """,
    )


def _storage(cursor: Any) -> dict[str, Any]:
    tables = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,t.temporal_type_desc,t.is_tracked_by_cdc,
          CASE WHEN ct.object_id IS NULL THEN 0 ELSE 1 END change_tracking_enabled
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        LEFT JOIN sys.change_tracking_tables ct ON ct.object_id=t.object_id
        WHERE t.object_id IN (OBJECT_ID(N'Acc.TblCheque'),OBJECT_ID(N'Acc.tblChqHist'),
          OBJECT_ID(N'dbo.Receipt'),OBJECT_ID(N'dbo.RCashDetail'),OBJECT_ID(N'dbo.RCash'))
        ORDER BY s.name,t.name
        """,
    )
    triggers = _rows(
        cursor,
        """
        SELECT ps.name schema_name,po.name parent_name,t.name trigger_name,t.is_disabled,
          t.is_instead_of_trigger
        FROM sys.triggers t JOIN sys.objects po ON po.object_id=t.parent_id
        JOIN sys.schemas ps ON ps.schema_id=po.schema_id
        WHERE t.parent_id IN (OBJECT_ID(N'Acc.TblCheque'),OBJECT_ID(N'Acc.tblChqHist'),
          OBJECT_ID(N'dbo.RCheque'),OBJECT_ID(N'dbo.Receipt'))
        ORDER BY ps.name,po.name,t.name
        """,
    )
    foreign_keys = _rows(
        cursor,
        """
        SELECT OBJECT_SCHEMA_NAME(fk.parent_object_id) child_schema,
          OBJECT_NAME(fk.parent_object_id) child_table,fk.name foreign_key_name,
          fk.delete_referential_action_desc,fk.update_referential_action_desc
        FROM sys.foreign_keys fk
        WHERE fk.referenced_object_id IN (OBJECT_ID(N'Acc.TblCheque'),OBJECT_ID(N'dbo.Receipt'))
        ORDER BY child_schema,child_table,foreign_key_name
        """,
    )
    return {
        "table_capabilities": tables,
        "active_triggers": triggers,
        "incoming_foreign_keys": foreign_keys,
    }


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safe = _assert_safe_target(cursor)
        profiles = _profiles(cursor)
        master_log = _master_log(cursor)
        receipt_batches = _receipt_delete_batches(cursor)
        receipt_log = _receipt_log(cursor)
        storage = _storage(cursor)
    finally:
        connection.close()

    by_name = {row["qualified_name"]: row for row in profiles}
    delete_events = next(
        row for row in master_log["event_counts"] if row["OperationType"] == "DELETE"
    )
    receipt_delete_events = next(
        row for row in receipt_log if row["OperationType"] == "DELETE"
    )
    categories = {
        (row["period"], row["tail_category"]): row["master_delete_event_count"]
        for row in master_log["tail_categories"]
    }
    receipt_delete_batch_count = sum(row["receipt_delete_batch_count"] for row in receipt_batches)
    receipt_tail_master_count = sum(
        row["master_delete_count"] * row["receipt_delete_batch_count"]
        for row in receipt_batches
    )
    receipt_tail_history_count = sum(
        row["history_delete_count"] * row["receipt_delete_batch_count"]
        for row in receipt_batches
    )
    direct = [row for row in profiles if row["expected_direct_master_delete_candidate"]]
    tail_shapes = master_log["anonymous_adjacent_tail_shapes"]
    receipt_save = by_name["dbo.usp_sdsnet_Receipt_Save"]
    chq_delete = by_name["Acc.uspCHQDelete"]
    view_trigger = by_name["dbo.Trg_RCheque_TblCheque"]
    return {
        "artifact": "varanegar_received_cheque_delete_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_LOG_AGGREGATES",
            "database_updateability": safe["updateability"],
            "can_select": safe["can_select"],
            "can_view_definition": safe["can_view_definition"],
            "can_update": safe["can_update"],
            "denies_data_writes": safe["denies_data_writes"],
            "stored_procedure_trigger_form_or_application_command_executions": 0,
            "cheque_receipt_customer_amount_bank_comment_operator_or_log_script_values_persisted": 0,
            "sql_definitions_or_log_ids_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "selected_sql_module_count": len(profiles),
            "direct_master_delete_candidate_count": len(direct),
            "retained_master_delete_event_count": delete_events["event_count"],
            "recent_master_delete_event_count": delete_events["recent_three_month_event_count"],
            "retained_receipt_delete_event_count": receipt_delete_events["event_count"],
            "recent_receipt_delete_event_count": receipt_delete_events[
                "recent_three_month_event_count"
            ],
            "receipt_delete_batch_count": receipt_delete_batch_count,
            "receipt_delete_tail_master_count": receipt_tail_master_count,
            "receipt_delete_tail_history_count": receipt_tail_history_count,
            "receipt_update_tail_master_count": sum(
                count
                for (period, category), count in categories.items()
                if category == "RECEIPT_UPDATE_TAIL"
            ),
            "isolated_tail_master_count": sum(
                count
                for (period, category), count in categories.items()
                if category == "ISOLATED_TAIL"
            ),
            "master_delete_without_history_lookback_count": sum(
                row["master_delete_event_count"]
                for row in tail_shapes
                if row["history_delete_lookback"] == 0
            ),
            "master_delete_immediately_preceded_by_history_delete_count": sum(
                row["master_delete_event_count"]
                for row in tail_shapes
                if row["previous_event"] == "Acc.tblChqHist:DELETE"
            ),
            "logged_master_current_absence_mismatch_count": master_log["logged_id_coverage"][
                "insert_only_but_absent_count"
            ]
            + master_log["logged_id_coverage"]["deleted_but_present_count"],
        },
        "sql_module_profiles": profiles,
        "static_delete_contract": {
            "all_expected_direct_candidates_delete_master": all(
                row["master_delete_statement_count"] >= 1 for row in direct
            ),
            "usp_chq_delete_validates_then_owns_atomic_history_master_delete": chq_delete[
                "calls_delete_validator"
            ]
            and chq_delete["owns_explicit_transaction"]
            and chq_delete["has_commit_signal"]
            and chq_delete["has_rollback_signal"]
            and chq_delete["history_delete_precedes_master_delete"],
            "view_delete_trigger_directly_deletes_master_without_history_or_receipt": view_trigger[
                "master_delete_statement_count"
            ]
            >= 1
            and view_trigger["history_delete_statement_count"] == 0
            and view_trigger["receipt_delete_statement_count"] == 0,
            "receipt_save_owns_transaction_or_savepoint": receipt_save[
                "owns_explicit_transaction"
            ]
            and receipt_save["has_rollback_signal"],
            "receipt_save_has_history_master_receipt_delete_sequence": receipt_save[
                "has_full_receipt_delete_branch_sequence"
            ],
            "receipt_save_calls_before_rcheque": receipt_save["calls_before_rcheque"],
        },
        "retained_master_lifecycle_log": master_log,
        "retained_receipt_event_counts": receipt_log,
        "receipt_delete_batches_with_master_cleanup": receipt_batches,
        "storage_contract": storage,
        "evidence_limits": [
            "Adjacent same-session log tails prove retained structural event order, not the invoking procedure, form, user or business reason.",
            "The receipt-delete batch shape matches the full-delete branch of dbo.usp_sdsnet_Receipt_Save, but procedure attribution remains a bounded inference because retained logs store table operations rather than call stacks.",
            "Direct-delete SQL candidates prove reachable mutation capability; they do not prove that each candidate executed in the retained period.",
            "The 30-second and bounded-ID adjacency windows are used only for anonymous shape classification and may merge unusually dense same-session work.",
            "No procedure, trigger, form or application command was executed and no cheque, receipt, customer, amount, bank, comment, operator, log identifier or OperationScript value was persisted.",
        ],
    }


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
    print(json.dumps(payload["static_delete_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
