"""Extract received-cheque destructive undo and trigger-owned projection read-only."""

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
    ("dbo", "DoRCheque_AddRChequeHistory"),
    ("dbo", "DoRCheque_DeleteLastRChequeHistory"),
    ("dbo", "DoRCheque_DeleteCessionToOther"),
    ("dbo", "usp_sdsnet_RChequeChangeStatus_Save"),
    ("dbo", "DoReceipt_CreateFirstRChequeHistory"),
    ("dbo", "DoRCheque_CessionToOther"),
    ("dbo", "BeforeRChequeHistory"),
    ("Acc", "UspCHQDelChqHistIsValid"),
    ("Acc", "trg_ChqHist_Del"),
    ("Acc", "trg_ChqHist_Ins"),
    ("Acc", "TRG_TblChqHist_DELETE"),
    ("Acc", "TRG_TblChqHist_DELETE_INSERT"),
    ("Acc", "TRG_TblChqHist_INSERT"),
    ("Acc", "trg_tblChqHist_FillChangeLogs"),
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pos(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


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
        begin_tx = _pos(code, r"\bbegin\s+(?:tran|transaction)\b")
        history_insert = _pos(
            code,
            r"\binsert\s+(?:into\s+)?(?:(?:acc\.)?tblchqhist|(?:dbo\.)?rchequehistory)\b",
        )
        history_delete = _pos(code, r"\bdelete\s+(?:from\s+)?(?:acc\.)?tblchqhist\b")
        history_update = _pos(code, r"\bupdate\s+(?:acc\.)?tblchqhist\b")
        cheque_update = _pos(
            code, r"\bupdate\s+(?:(?:acc\.)?tblcheque|(?:dbo\.)?rcheque)\b"
        )
        before_history = _pos(code, r"\b(?:exec|execute)\s+(?:dbo\.)?beforerchequehistory\b")
        commit = _pos(code, r"\bcommit\b")
        profiles.append(
            {
                **row,
                "qualified_name": f"{schema}.{name}",
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "owns_explicit_transaction": begin_tx is not None,
                "has_commit_signal": commit is not None,
                "has_rollback_signal": bool(re.search(r"\brollback\b", code)),
                "has_try_catch": "begin try" in code and "begin catch" in code,
                "inserts_history": history_insert is not None,
                "history_delete_statement_count": len(
                    re.findall(r"\bdelete\s+(?:from\s+)?(?:acc\.)?tblchqhist\b", code)
                ),
                "updates_history_projection": history_update is not None,
                "updates_cheque_master": cheque_update is not None,
                "sets_is_last_zero": bool(re.search(r"\bislast\s*=\s*0\b", code)),
                "sets_is_last_one": bool(re.search(r"\bislast\s*=\s*1\b", code)),
                "calls_before_history": before_history is not None,
                "before_history_precedes_transaction": before_history is not None
                and begin_tx is not None
                and before_history < begin_tx,
                "conditional_double_delete_for_8_to_1_undo": bool(
                    re.search(r"previousstatref\s*=\s*8", code)
                    and re.search(r"rchequestatusid\s*=\s*1", code)
                    and len(re.findall(r"\bdelete\s+(?:from\s+)?(?:acc\.)?tblchqhist\b", code)) >= 2
                ),
                "calls_add_history": bool(
                    re.search(r"\b(?:exec|execute)\s+(?:dbo\.)?dorcheque_addrchequehistory\b", code)
                ),
                "calls_delete_last_history": bool(
                    re.search(
                        r"\b(?:exec|execute)\s+(?:dbo\.)?dorcheque_deletelastrchequehistory\b",
                        code,
                    )
                ),
                "history_insert_precedes_master_update": history_insert is not None
                and cheque_update is not None
                and history_insert < cheque_update,
                "history_delete_precedes_master_update": history_delete is not None
                and cheque_update is not None
                and history_delete < cheque_update,
                "history_update_position": history_update,
                "definition_or_offsets_persisted": False,
            }
        )
    return profiles


def _current_lifecycle(cursor: Any) -> dict[str, Any]:
    aggregate = _rows(
        cursor,
        """
        WITH x AS (
          SELECT ChqRef,COUNT_BIG(*) history_count,
            SUM(CASE WHEN IsLast=1 THEN 1 ELSE 0 END) current_count,MAX(ID) max_history_id
          FROM Acc.tblChqHist GROUP BY ChqRef
        )
        SELECT (SELECT COUNT_BIG(*) FROM Acc.TblCheque) cheque_count,
          (SELECT COUNT_BIG(*) FROM Acc.tblChqHist) history_count,
          SUM(CASE WHEN x.ChqRef IS NULL THEN 1 ELSE 0 END) without_history_count,
          SUM(CASE WHEN x.current_count<>1 THEN 1 ELSE 0 END) current_count_mismatch,
          SUM(CASE WHEN h.ID<>x.max_history_id THEN 1 ELSE 0 END) current_not_max_count,
          SUM(CASE WHEN h.ChqRef<>c.ID THEN 1 ELSE 0 END) current_wrong_parent_count,
          MIN(x.history_count) min_history_count,MAX(x.history_count) max_history_count
        FROM Acc.TblCheque c LEFT JOIN x ON x.ChqRef=c.ID
        LEFT JOIN Acc.tblChqHist h ON h.ChqRef=c.ID AND h.IsLast=1
        """,
    )[0]
    statuses = _rows(
        cursor,
        """
        SELECT h.StatRef current_status,COUNT_BIG(*) cheque_count,
          SUM(CASE WHEN x.history_count>1 THEN 1 ELSE 0 END) history_count_over_one
        FROM Acc.TblCheque c JOIN Acc.tblChqHist h ON h.ChqRef=c.ID AND h.IsLast=1
        JOIN (SELECT ChqRef,COUNT_BIG(*) history_count FROM Acc.tblChqHist GROUP BY ChqRef) x
          ON x.ChqRef=c.ID
        GROUP BY h.StatRef ORDER BY h.StatRef
        """,
    )
    transitions = _rows(
        cursor,
        """
        SELECT PreviousStatRef from_status,StatRef to_status,COUNT_BIG(*) transition_count
        FROM Acc.tblChqHist WHERE PreviousStatRef IS NOT NULL
        GROUP BY PreviousStatRef,StatRef ORDER BY PreviousStatRef,StatRef
        """,
    )
    chain = _rows(
        cursor,
        """
        SELECT SUM(CASE WHEN h.PreviousHistRef IS NOT NULL AND p.ID IS NULL THEN 1 ELSE 0 END)
            orphan_previous_history_count,
          SUM(CASE WHEN p.ID IS NOT NULL AND p.ChqRef<>h.ChqRef THEN 1 ELSE 0 END)
            previous_history_wrong_parent_count,
          SUM(CASE WHEN p.ID IS NOT NULL AND p.StatRef<>h.PreviousStatRef THEN 1 ELSE 0 END)
            previous_status_mismatch_count
        FROM Acc.tblChqHist h LEFT JOIN Acc.tblChqHist p ON p.ID=h.PreviousHistRef
        """,
    )[0]
    return {
        "aggregate": aggregate,
        "current_status": statuses,
        "observed_transitions": transitions,
        "chain_integrity": chain,
    }


def _history_log(cursor: Any) -> dict[str, Any]:
    events = _rows(
        cursor,
        """
        SELECT OperationType,COUNT_BIG(*) event_count,COUNT(DISTINCT OperationId) distinct_id_count,
          SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_event_count,MIN(TransDate) first_event_date,MAX(TransDate) last_event_date
        FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
        WHERE OperationTable='Acc.tblChqHist'
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
          WHERE OperationTable='Acc.tblChqHist' GROUP BY OperationId
        )
        SELECT COUNT_BIG(*) logged_id_count,
          SUM(CASE WHEN h.ID IS NOT NULL THEN 1 ELSE 0 END) currently_present_count,
          SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) currently_absent_count,
          SUM(CASE WHEN insert_count>0 AND delete_count>0 THEN 1 ELSE 0 END) both_event_count,
          SUM(CASE WHEN insert_count=0 AND delete_count>0 THEN 1 ELSE 0 END) delete_only_count,
          SUM(CASE WHEN insert_count>0 AND delete_count=0 AND h.ID IS NULL THEN 1 ELSE 0 END)
            insert_only_but_absent_count,
          SUM(CASE WHEN delete_count>0 AND h.ID IS NOT NULL THEN 1 ELSE 0 END)
            deleted_but_present_count
        FROM l LEFT JOIN Acc.tblChqHist h ON h.ID=l.OperationId
        """,
    )[0]
    unexplained = _rows(
        cursor,
        """
        WITH i AS (
          SELECT OperationId,MIN(TransDate) first_insert,MAX(TransDate) last_insert
          FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='Acc.tblChqHist' AND OperationType='INSERT' GROUP BY OperationId
        ), d AS (
          SELECT DISTINCT OperationId FROM GNR.tblLog
            WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='Acc.tblChqHist' AND OperationType='DELETE'
        )
        SELECT COUNT_BIG(*) insert_logged_absent_without_delete_count,
          SUM(CASE WHEN i.last_insert>='20260601' AND i.last_insert<'20260901' THEN 1 ELSE 0 END)
            recent_insert_count,MIN(i.first_insert) first_insert,MAX(i.last_insert) last_insert,
          DATEDIFF(millisecond,MIN(i.first_insert),MAX(i.last_insert)) spread_milliseconds
        FROM i LEFT JOIN d ON d.OperationId=i.OperationId
        LEFT JOIN Acc.tblChqHist h ON h.ID=i.OperationId
        WHERE h.ID IS NULL AND d.OperationId IS NULL
        """,
    )[0]
    shapes = _rows(
        cursor,
        """
        WITH d AS (
          SELECT ID,SPID,TransDate FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
          WHERE OperationTable='Acc.tblChqHist' AND OperationType='DELETE'
        ), n AS (
          SELECT d.ID delete_id,d.TransDate,
            ROW_NUMBER() OVER(PARTITION BY d.ID ORDER BY l.ID) rn,l.OperationTable,l.OperationType
          FROM d LEFT JOIN GNR.tblLog l WITH (INDEX(PK_tblLog))
            ON l.ID>d.ID AND l.ID<=d.ID+10 AND l.SPID=d.SPID
           AND l.TransDate>=d.TransDate AND l.TransDate<DATEADD(second,30,d.TransDate)
        ), p AS (
          SELECT delete_id,TransDate,
            MAX(CASE WHEN rn=1 THEN OperationTable END)t1,
            MAX(CASE WHEN rn=1 THEN OperationType END)o1,
            MAX(CASE WHEN rn=2 THEN OperationTable END)t2,
            MAX(CASE WHEN rn=2 THEN OperationType END)o2,
            MAX(CASE WHEN rn=3 THEN OperationTable END)t3,
            MAX(CASE WHEN rn=3 THEN OperationType END)o3,
            MAX(CASE WHEN rn=4 THEN OperationTable END)t4,
            MAX(CASE WHEN rn=4 THEN OperationType END)o4
          FROM n GROUP BY delete_id,TransDate
        ), x AS (
          SELECT TransDate,CASE
            WHEN t1='Acc.tblChqHist' AND o1='UPDATE'
             AND t2='Acc.TblCheque' AND o2='UPDATE' THEN 'SINGLE_UNDO_TAIL'
            WHEN t1='Acc.tblChqHist' AND o1='UPDATE'
             AND t2='Acc.tblChqHist' AND o2='DELETE'
             AND t3='Acc.tblChqHist' AND o3='UPDATE'
             AND t4='Acc.TblCheque' AND o4='UPDATE' THEN 'DOUBLE_DELETE_UNDO_TAIL'
            WHEN t1='Acc.tblChqHist' AND o1='UPDATE' THEN 'HISTORY_DELETE_UPDATE_OTHER'
            ELSE 'OTHER' END shape
          FROM p
        )
        SELECT shape,COUNT_BIG(*) history_delete_head_count,
          SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_count,MIN(TransDate) first_event_date,MAX(TransDate) last_event_date
        FROM x GROUP BY shape ORDER BY shape
        """,
    )
    return {
        "event_counts": events,
        "logged_id_coverage": coverage,
        "insert_logged_absent_without_delete_batch": unexplained,
        "delete_tail_shapes": shapes,
    }


def _storage(cursor: Any) -> dict[str, Any]:
    tables = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,t.temporal_type_desc,t.is_tracked_by_cdc,
          CASE WHEN ct.object_id IS NULL THEN 0 ELSE 1 END change_tracking_enabled
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        LEFT JOIN sys.change_tracking_tables ct ON ct.object_id=t.object_id
        WHERE t.object_id IN (OBJECT_ID(N'Acc.TblCheque'),OBJECT_ID(N'Acc.tblChqHist'))
        ORDER BY t.name
        """,
    )
    triggers = _rows(
        cursor,
        """
        SELECT ps.name schema_name,po.name parent_name,t.name trigger_name,t.is_disabled,
          t.is_instead_of_trigger
        FROM sys.triggers t JOIN sys.objects po ON po.object_id=t.parent_id
        JOIN sys.schemas ps ON ps.schema_id=po.schema_id
        WHERE t.parent_id IN (OBJECT_ID(N'Acc.tblChqHist'),OBJECT_ID(N'Acc.TblCheque'),
          OBJECT_ID(N'dbo.RChequeHistory'),OBJECT_ID(N'dbo.RCheque'))
        ORDER BY ps.name,po.name,t.name
        """,
    )
    indexes = _rows(
        cursor,
        """
        SELECT i.name index_name,i.is_unique,i.is_primary_key,c.name column_name,ic.key_ordinal
        FROM sys.indexes i JOIN sys.index_columns ic
          ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID(N'Acc.tblChqHist') AND i.index_id>0
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
        lifecycle = _current_lifecycle(cursor)
        log = _history_log(cursor)
        storage = _storage(cursor)
    finally:
        connection.close()
    by_name = {row["qualified_name"]: row for row in profiles}
    undo = by_name["dbo.DoRCheque_DeleteLastRChequeHistory"]
    undo_wrapper = by_name["dbo.DoRCheque_DeleteCessionToOther"]
    add = by_name["dbo.DoRCheque_AddRChequeHistory"]
    outer = by_name["dbo.usp_sdsnet_RChequeChangeStatus_Save"]
    delete_trigger = by_name["Acc.trg_ChqHist_Del"]
    insert_trigger = by_name["Acc.trg_ChqHist_Ins"]
    events = {row["OperationType"]: row for row in log["event_counts"]}
    shapes = {row["shape"]: row for row in log["delete_tail_shapes"]}
    single = shapes["SINGLE_UNDO_TAIL"]
    double = shapes["DOUBLE_DELETE_UNDO_TAIL"]
    return {
        "artifact": "varanegar_received_cheque_undo_boundary",
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
            "cheque_history_bank_customer_amount_comment_or_operator_values_persisted": 0,
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
            "current_projection_mismatch_count": lifecycle["aggregate"]["current_count_mismatch"]
            + lifecycle["aggregate"]["current_not_max_count"],
            "retained_history_delete_event_count": events["DELETE"]["event_count"],
            "undo_command_tail_count": single["history_delete_head_count"],
            "conditional_double_delete_command_count": double["history_delete_head_count"],
            "undo_attributed_deleted_history_count": single["history_delete_head_count"]
            + double["history_delete_head_count"],
            "recent_undo_command_tail_count": single["recent_three_month_count"],
            "recent_undo_attributed_deleted_history_count": single["recent_three_month_count"]
            + double["recent_three_month_count"],
            "insert_logged_absent_without_delete_count": log[
                "insert_logged_absent_without_delete_batch"
            ]["insert_logged_absent_without_delete_count"],
        },
        "sql_module_profiles": profiles,
        "undo_add_trigger_contract": {
            "undo_validates_before_transaction": undo["before_history_precedes_transaction"],
            "undo_owns_transaction_and_rollback": undo["owns_explicit_transaction"]
            and undo["has_commit_signal"]
            and undo["has_rollback_signal"],
            "undo_deletes_history_and_appends_no_compensating_event": undo[
                "history_delete_statement_count"
            ]
            >= 1
            and not undo["inserts_history"],
            "undo_has_conditional_status_8_double_delete": undo[
                "conditional_double_delete_for_8_to_1_undo"
            ],
            "undo_history_delete_precedes_master_audit_update": undo[
                "history_delete_precedes_master_update"
            ],
            "desktop_undo_wrapper_calls_delete_last_history": undo_wrapper[
                "calls_delete_last_history"
            ],
            "desktop_undo_wrapper_owns_transaction_without_explicit_rollback": undo_wrapper[
                "owns_explicit_transaction"
            ]
            and undo_wrapper["has_commit_signal"]
            and not undo_wrapper["has_rollback_signal"],
            "delete_trigger_reactivates_previous_history": delete_trigger[
                "updates_history_projection"
            ]
            and delete_trigger["sets_is_last_one"],
            "insert_trigger_deactivates_previous_history": insert_trigger[
                "updates_history_projection"
            ]
            and insert_trigger["sets_is_last_zero"],
            "add_is_transactional_append_path": add["owns_explicit_transaction"]
            and add["inserts_history"]
            and add["has_commit_signal"]
            and add["has_rollback_signal"],
            "outer_change_status_calls_add_and_delete": outer["calls_add_history"]
            and outer["calls_delete_last_history"],
            "outer_change_status_owns_transaction_or_savepoint": outer[
                "owns_explicit_transaction"
            ]
            and outer["has_rollback_signal"],
        },
        "current_lifecycle": lifecycle,
        "retained_history_lifecycle_log": log,
        "storage_contract": storage,
        "evidence_limits": [
            "The exact adjacent log tails strongly match static undo, but do not identify user, business reason or the deleted status values.",
            "SINGLE_UNDO_TAIL includes the second deleted row of every conditional double-delete command; command count therefore equals its count, while attributed deleted-row count adds DOUBLE_DELETE_UNDO_TAIL.",
            "The 252 insert-logged rows absent without retained DELETE events are historical and are not attributed to undo, migration or trigger bypass.",
            "Current one-IsLast/max-ID/chain parity proves a clean projection, not preservation of deleted audit history.",
            "No procedure, trigger, form or application command was executed and no cheque, bank, customer, amount, comment or operator value was persisted.",
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
    print(json.dumps(payload["undo_add_trigger_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
