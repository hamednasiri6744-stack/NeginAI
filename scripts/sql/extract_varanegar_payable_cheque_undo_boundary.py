"""Extract payable-cheque destructive undo and projection boundary read-only."""

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
    "DoPCheque_AddPChequeHistory",
    "DoPCheque_DeleteLastPChequeHistory",
    "usp_sdsnet_PChequeChangeStatus_Save",
    "DoPay_CreateApprovePChequeHistory",
    "DoPay_CreateFirstPChequeHistory",
    "CheckBalanceBeforePchequeHistory",
    "PChequeHistoryWithPreviousHistory",
    "BeforePCheque",
    "AfterPCheque",
    "Usp_Sdsnet_PCheque_Save",
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pos(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


def _profiles(cursor: Any) -> list[dict[str, Any]]:
    profiles = []
    for name in MODULES:
        row = _rows(
            cursor,
            """
            SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,m.definition
            FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
            JOIN sys.schemas s ON s.schema_id=o.schema_id WHERE o.name=%s
            """,
            (name,),
        )[0]
        definition = row.pop("definition") or ""
        code = " ".join(
            _executable_text(definition).replace("[", "").replace("]", "").casefold().split()
        )
        insert_history = _pos(
            code, r"\binsert\s+into\s+(?:dbo\.)?pchequehistory\b"
        )
        delete_history = _pos(
            code, r"\bdelete\s+(?:from\s+)?(?:dbo\.)?pchequehistory\b"
        )
        update_cheque = _pos(code, r"\bupdate\s+(?:dbo\.)?pcheque\b")
        update_leaf = _pos(code, r"\bupdate\s+(?:dbo\.)?pchequebookitem\b")
        begin_tx = _pos(code, r"\bbegin\s+(?:tran|transaction)\b")
        commit = _pos(code, r"\bcommit\b")
        voucher_check = _pos(code, r"usp_checkvoucherforform")
        profiles.append(
            {
                **row,
                "qualified_name": f"{row['schema_name']}.{row['object_name']}",
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "owns_explicit_transaction": begin_tx is not None,
                "has_commit_signal": commit is not None,
                "has_rollback_signal": bool(re.search(r"\brollback\b", code)),
                "has_try_catch": "begin try" in code and "begin catch" in code,
                "has_xact_abort": "xact_abort" in code,
                "raises_domain_error": "raiserror" in code or "throw" in code,
                "inserts_cheque_history": insert_history is not None,
                "deletes_cheque_history": delete_history is not None,
                "updates_current_cheque_projection": update_cheque is not None,
                "updates_cheque_leaf_usage": update_leaf is not None,
                "calls_voucher_dependency_check": voucher_check is not None,
                "calls_add_history": bool(
                    re.search(r"\b(?:exec|execute)\s+(?:dbo\.)?dopcheque_addpchequehistory\b", code)
                ),
                "calls_delete_last_history": bool(
                    re.search(r"\b(?:exec|execute)\s+(?:dbo\.)?dopcheque_deletelastpchequehistory\b", code)
                ),
                "history_insert_precedes_projection_update": insert_history is not None
                and update_cheque is not None
                and insert_history < update_cheque,
                "history_delete_precedes_projection_update": delete_history is not None
                and update_cheque is not None
                and delete_history < update_cheque,
                "projection_update_precedes_leaf_update": update_cheque is not None
                and update_leaf is not None
                and update_cheque < update_leaf,
                "voucher_check_precedes_transaction": voucher_check is not None
                and begin_tx is not None
                and voucher_check < begin_tx,
                "leaf_update_precedes_commit": update_leaf is not None
                and commit is not None
                and update_leaf < commit,
                "definition_or_offsets_persisted": False,
            }
        )
    return profiles


def _call_graph(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT DISTINCT OBJECT_NAME(d.referencing_id) caller_name,
          COALESCE(OBJECT_SCHEMA_NAME(d.referenced_id),d.referenced_schema_name) callee_schema,
          COALESCE(OBJECT_NAME(d.referenced_id),d.referenced_entity_name) callee_name
        FROM sys.sql_expression_dependencies d
        WHERE OBJECT_NAME(d.referencing_id) IN (
          'DoPCheque_AddPChequeHistory','DoPCheque_DeleteLastPChequeHistory',
          'usp_sdsnet_PChequeChangeStatus_Save','DoPay_CreateApprovePChequeHistory',
          'DoPay_CreateFirstPChequeHistory','CheckBalanceBeforePchequeHistory',
          'PChequeHistoryWithPreviousHistory','BeforePCheque','AfterPCheque',
          'Usp_Sdsnet_PCheque_Save')
        ORDER BY caller_name,callee_schema,callee_name
        """,
    )


def _current_lifecycle(cursor: Any) -> dict[str, Any]:
    aggregate = _rows(
        cursor,
        """
        WITH hc AS (
          SELECT PChequeId,COUNT_BIG(*) history_count,MAX(PChequeHistoryId) max_history_id
          FROM dbo.PChequeHistory GROUP BY PChequeId
        )
        SELECT COUNT_BIG(*) cheque_count,
          SUM(hc.history_count) history_count,
          MIN(hc.history_count) min_history_count,MAX(hc.history_count) max_history_count,
          SUM(CASE WHEN p.PChequeHistoryId<>hc.max_history_id THEN 1 ELSE 0 END)
            current_pointer_not_max_count,
          SUM(CASE WHEN ch.PChequeId<>p.PChequeId THEN 1 ELSE 0 END)
            current_pointer_wrong_parent_count
        FROM dbo.PCheque p JOIN hc ON hc.PChequeId=p.PChequeId
        LEFT JOIN dbo.PChequeHistory ch ON ch.PChequeHistoryId=p.PChequeHistoryId
        """,
    )[0]
    status = _rows(
        cursor,
        """
        SELECT h.PChequeStatusId current_status,COUNT_BIG(*) cheque_count,
          SUM(CASE WHEN x.history_count>2 THEN 1 ELSE 0 END) history_count_over_two
        FROM dbo.PCheque p JOIN dbo.PChequeHistory h ON h.PChequeHistoryId=p.PChequeHistoryId
        JOIN (SELECT PChequeId,COUNT_BIG(*) history_count FROM dbo.PChequeHistory GROUP BY PChequeId) x
          ON x.PChequeId=p.PChequeId
        GROUP BY h.PChequeStatusId ORDER BY h.PChequeStatusId
        """,
    )
    transitions = _rows(
        cursor,
        """
        WITH x AS (
          SELECT PChequeId,PChequeStatusId,
            LAG(PChequeStatusId) OVER(PARTITION BY PChequeId ORDER BY PChequeHistoryId) prior_status
          FROM dbo.PChequeHistory
        )
        SELECT prior_status,PChequeStatusId next_status,COUNT_BIG(*) transition_count
        FROM x WHERE prior_status IS NOT NULL
        GROUP BY prior_status,PChequeStatusId ORDER BY prior_status,PChequeStatusId
        """,
    )
    return {"aggregate": aggregate, "current_status": status, "observed_transitions": transitions}


def _history_log(cursor: Any) -> dict[str, Any]:
    events = _rows(
        cursor,
        """
        SELECT OperationType,COUNT_BIG(*) event_count,COUNT(DISTINCT OperationId) distinct_id_count,
          SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_event_count,MIN(TransDate) first_event_date,MAX(TransDate) last_event_date
        FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
        WHERE OperationTable='dbo.PChequeHistory'
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
          WHERE OperationTable='dbo.PChequeHistory' GROUP BY OperationId
        )
        SELECT COUNT_BIG(*) logged_id_count,
          SUM(CASE WHEN h.PChequeHistoryId IS NOT NULL THEN 1 ELSE 0 END) currently_present_count,
          SUM(CASE WHEN h.PChequeHistoryId IS NULL THEN 1 ELSE 0 END) currently_absent_count,
          SUM(CASE WHEN insert_count>0 AND delete_count>0 THEN 1 ELSE 0 END) both_event_count,
          SUM(CASE WHEN insert_count=0 AND delete_count>0 THEN 1 ELSE 0 END) delete_only_count,
          SUM(CASE WHEN insert_count>0 AND delete_count=0 AND h.PChequeHistoryId IS NULL THEN 1 ELSE 0 END)
            insert_only_but_absent_count,
          SUM(CASE WHEN delete_count>0 AND h.PChequeHistoryId IS NOT NULL THEN 1 ELSE 0 END)
            deleted_but_present_count
        FROM l LEFT JOIN dbo.PChequeHistory h ON h.PChequeHistoryId=l.OperationId
        """,
    )[0]
    unexplained_batch = _rows(
        cursor,
        """
        WITH i AS (
          SELECT OperationId,MIN(TransDate) first_insert,MAX(TransDate) last_insert
          FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='dbo.PChequeHistory' AND OperationType='INSERT'
          GROUP BY OperationId
        ), d AS (
          SELECT DISTINCT OperationId FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='dbo.PChequeHistory' AND OperationType='DELETE'
        )
        SELECT COUNT_BIG(*) insert_logged_absent_without_delete_count,
          SUM(CASE WHEN i.last_insert>='20260601' AND i.last_insert<'20260901' THEN 1 ELSE 0 END)
            recent_insert_count,MIN(i.first_insert) first_insert,MAX(i.last_insert) last_insert
        FROM i LEFT JOIN d ON d.OperationId=i.OperationId
        LEFT JOIN dbo.PChequeHistory h ON h.PChequeHistoryId=i.OperationId
        WHERE h.PChequeHistoryId IS NULL AND d.OperationId IS NULL
        """,
    )[0]
    shapes = _rows(
        cursor,
        """
        WITH d AS (
          SELECT ID,SPID,TransDate FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
          WHERE OperationTable='dbo.PChequeHistory' AND OperationType='DELETE'
        ), x AS (
          SELECT d.ID,d.TransDate,
            MIN(CASE WHEN l.OperationTable='dbo.PCheque' AND l.OperationType='UPDATE' THEN l.ID END) cheque_update_id,
            MIN(CASE WHEN l.OperationTable='dbo.PChequeBookItem' AND l.OperationType='UPDATE' THEN l.ID END) leaf_update_id,
            MIN(CASE WHEN l.OperationTable='dbo.PCheque' AND l.OperationType='DELETE' THEN l.ID END) cheque_delete_id
          FROM d LEFT JOIN GNR.tblLog l WITH (INDEX(PK_tblLog))
            ON l.ID BETWEEN d.ID+1 AND d.ID+30 AND l.SPID=d.SPID
           AND l.TransDate>=d.TransDate AND l.TransDate<DATEADD(second,30,d.TransDate)
          GROUP BY d.ID,d.TransDate
        )
        SELECT CASE
          WHEN cheque_delete_id IS NOT NULL THEN 'CHEQUE_DELETE_PRESENT'
          WHEN cheque_update_id IS NOT NULL AND leaf_update_id IS NOT NULL
            AND cheque_update_id<leaf_update_id THEN 'UNDO_EXACT_TAIL'
          WHEN cheque_update_id IS NOT NULL OR leaf_update_id IS NOT NULL THEN 'PARTIAL_UPDATE_TAIL'
          ELSE 'NO_TAIL' END shape,
          COUNT_BIG(*) history_delete_count,
          SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_count
        FROM x GROUP BY CASE
          WHEN cheque_delete_id IS NOT NULL THEN 'CHEQUE_DELETE_PRESENT'
          WHEN cheque_update_id IS NOT NULL AND leaf_update_id IS NOT NULL
            AND cheque_update_id<leaf_update_id THEN 'UNDO_EXACT_TAIL'
          WHEN cheque_update_id IS NOT NULL OR leaf_update_id IS NOT NULL THEN 'PARTIAL_UPDATE_TAIL'
          ELSE 'NO_TAIL' END ORDER BY shape
        """,
    )
    return {
        "event_counts": events,
        "logged_id_coverage": coverage,
        "insert_logged_absent_without_delete_batch": unexplained_batch,
        "delete_session_tail_shapes": shapes,
    }


def _storage(cursor: Any) -> dict[str, Any]:
    tables = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,t.temporal_type_desc,t.is_tracked_by_cdc,
          CASE WHEN ct.object_id IS NULL THEN 0 ELSE 1 END change_tracking_enabled
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        LEFT JOIN sys.change_tracking_tables ct ON ct.object_id=t.object_id
        WHERE t.object_id IN (OBJECT_ID(N'dbo.PCheque'),OBJECT_ID(N'dbo.PChequeHistory'),
          OBJECT_ID(N'dbo.PChequeBookItem')) ORDER BY t.name
        """,
    )
    triggers = _rows(
        cursor,
        """
        SELECT OBJECT_NAME(t.parent_id) table_name,t.name trigger_name,t.is_disabled
        FROM sys.triggers t WHERE t.parent_id IN (OBJECT_ID(N'dbo.PCheque'),
          OBJECT_ID(N'dbo.PChequeHistory'),OBJECT_ID(N'dbo.PChequeBookItem'))
        ORDER BY table_name,trigger_name
        """,
    )
    indexes = _rows(
        cursor,
        """
        SELECT i.name index_name,i.is_unique,i.is_primary_key,c.name column_name,ic.key_ordinal
        FROM sys.indexes i JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID(N'dbo.PChequeHistory') AND i.index_id>0
        ORDER BY i.index_id,ic.key_ordinal
        """,
    )
    return {"table_capabilities": tables, "active_triggers": triggers, "history_indexes": indexes}


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safe = _assert_safe_target(cursor)
        profiles = _profiles(cursor)
        graph = _call_graph(cursor)
        lifecycle = _current_lifecycle(cursor)
        log = _history_log(cursor)
        storage = _storage(cursor)
    finally:
        connection.close()
    by_name = {row["object_name"]: row for row in profiles}
    undo = by_name["DoPCheque_DeleteLastPChequeHistory"]
    add = by_name["DoPCheque_AddPChequeHistory"]
    outer = by_name["usp_sdsnet_PChequeChangeStatus_Save"]
    events = {row["OperationType"]: row for row in log["event_counts"]}
    shapes = {row["shape"]: row for row in log["delete_session_tail_shapes"]}
    return {
        "artifact": "varanegar_payable_cheque_undo_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": safe["updateability"],
            "can_select": safe["can_select"],
            "can_view_definition": safe["can_view_definition"],
            "can_update": safe["can_update"],
            "denies_data_writes": safe["denies_data_writes"],
            "stored_procedure_trigger_form_or_application_command_executions": 0,
            "cheque_leaf_history_identifiers_amounts_bank_or_operator_values_persisted": 0,
            "sql_definitions_or_log_scripts_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "selected_sql_module_count": len(profiles),
            "selected_module_with_local_transaction_count": sum(
                row["owns_explicit_transaction"] for row in profiles
            ),
            "current_cheque_count": lifecycle["aggregate"]["cheque_count"],
            "current_history_count": lifecycle["aggregate"]["history_count"],
            "current_pointer_mismatch_count": lifecycle["aggregate"][
                "current_pointer_not_max_count"
            ],
            "retained_history_delete_event_count": events["DELETE"]["event_count"],
            "exact_undo_tail_history_delete_count": shapes["UNDO_EXACT_TAIL"][
                "history_delete_count"
            ],
            "recent_exact_undo_tail_count": shapes["UNDO_EXACT_TAIL"][
                "recent_three_month_count"
            ],
            "insert_logged_absent_without_delete_count": log[
                "insert_logged_absent_without_delete_batch"
            ]["insert_logged_absent_without_delete_count"],
        },
        "sql_module_profiles": profiles,
        "catalog_call_graph": graph,
        "undo_add_sequence_contract": {
            "undo_voucher_check_precedes_transaction": undo[
                "voucher_check_precedes_transaction"
            ],
            "undo_deletes_history": undo["deletes_cheque_history"],
            "undo_delete_precedes_current_projection_update": undo[
                "history_delete_precedes_projection_update"
            ],
            "undo_projection_update_precedes_leaf_update": undo[
                "projection_update_precedes_leaf_update"
            ],
            "undo_leaf_update_precedes_commit": undo["leaf_update_precedes_commit"],
            "undo_has_try_catch_commit_rollback": undo["has_try_catch"]
            and undo["has_commit_signal"]
            and undo["has_rollback_signal"],
            "undo_appends_compensating_history": undo["inserts_cheque_history"],
            "add_inserts_history_before_projection": add[
                "history_insert_precedes_projection_update"
            ],
            "add_projection_precedes_leaf_update": add[
                "projection_update_precedes_leaf_update"
            ],
            "change_status_outer_calls_add_and_delete": outer["calls_add_history"]
            and outer["calls_delete_last_history"],
            "change_status_outer_owns_transaction": outer["owns_explicit_transaction"],
        },
        "current_lifecycle": lifecycle,
        "retained_history_lifecycle_log": log,
        "storage_contract": storage,
        "evidence_limits": [
            "The exact undo-tail log shape is a strong static/log match but does not identify the user, business reason or deleted status value.",
            "The 402 insert-logged rows absent without a retained delete event are one historical batch and are not attributed to undo or trigger bypass.",
            "Current pointer parity proves the snapshot projection is consistent, not that destructive undo preserves a complete audit history.",
            "Static SQL transaction structure does not prove every caller or nested failure path completed atomically.",
            "No procedure, trigger, form or application command was executed and no cheque, bank, leaf, history or operator identifier was persisted.",
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
    print(json.dumps(payload["undo_add_sequence_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
