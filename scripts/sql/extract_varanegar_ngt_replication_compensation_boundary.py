"""Extract the deployed NGT replication-compensation boundary safely.

Only read-only clone catalog metadata, procedure text held in memory, and
anonymous aggregates are used. SQL definitions, GUID literals, business rows,
and identifiers are never persisted. No stored procedure is executed.
"""

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
from extract_varanegar_ngt_payment_replication_boundary import (
    GUID_LITERAL,
    MUTATION,
    _procedure_definition,
    _procedure_profile,
)


PROC_NAMES = (
    "dbo.NGT_RollBackTour",
    "dbo.USP_NGT_UndoReplicateTour",
    "dbo.NGT_RollBackGetDistibutionTour",
    "dbo.usp_CanUndoTour",
)
REFERENCED_TARGETS = (
    ("dbo", "Receipt"),
    ("dbo", "RCash"),
    ("Acc", "TblCheque"),
    ("Acc", "TblBankOrders"),
    ("Acc", "tblPayments"),
)
SIGNALS = (
    "RCashDetail",
    "tblChqHist",
    "tblPayments",
    "TblBankOrders",
    "TblCheque",
    "Receipt",
    "TourHistory",
    "#EntityUniqueIdList",
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _comment_spans(definition: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in re.finditer(r"/\*.*?\*/", definition, re.S)]


def _inside_any(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)


def _control_flow_profile(definition: str) -> dict[str, Any]:
    spans = _comment_spans(definition)
    returns = list(re.finditer(r"(?im)^\s*RETURN\s*;?\s*$", definition))
    mutations = list(MUTATION.finditer(definition))
    first_return = None if not returns else returns[0].start()
    first_mutation = None if not mutations else mutations[0].start()
    prefix = definition if first_return is None else definition[: returns[0].end()]
    return {
        "first_standalone_return_normalized_position": None
        if first_return is None
        else round(first_return / max(len(definition), 1), 6),
        "first_mutation_normalized_position": None
        if first_mutation is None
        else round(first_mutation / max(len(definition), 1), 6),
        "standalone_return_precedes_first_mutation": bool(
            first_return is not None
            and first_mutation is not None
            and first_return < first_mutation
        ),
        "profiled_mutation_count": len(mutations),
        "profiled_mutation_inside_block_comment_count": sum(
            1 for match in mutations if _inside_any(match.start(), spans)
        ),
        "all_profiled_mutations_are_inside_block_comments": bool(mutations)
        and all(_inside_any(match.start(), spans) for match in mutations),
        "executable_prefix_through_first_return_sha256": _sha256(prefix),
        "sql_definition_persisted": 0,
    }


def _signal_contract(definition: str) -> list[dict[str, Any]]:
    spans = _comment_spans(definition)
    result = []
    for signal in SIGNALS:
        matches = list(re.finditer(re.escape(signal), definition, re.I))
        result.append(
            {
                "signal": signal,
                "occurrence_count": len(matches),
                "inside_block_comment_count": sum(
                    1 for match in matches if _inside_any(match.start(), spans)
                ),
                "outside_block_comment_count": sum(
                    1 for match in matches if not _inside_any(match.start(), spans)
                ),
            }
        )
    return result


def _dependencies(cursor: Any, qualified_name: str) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT referenced_schema_name,referenced_entity_name,referenced_class_desc,
               is_caller_dependent,is_ambiguous
        FROM sys.sql_expression_dependencies
        WHERE referencing_id=OBJECT_ID(%s)
        ORDER BY referenced_schema_name,referenced_entity_name
        """,
        (qualified_name,),
    )


def _referential_delete_contract(cursor: Any) -> list[dict[str, Any]]:
    predicates = " OR ".join(
        f"(rs.name=N'{schema}' AND rt.name=N'{table}')"
        for schema, table in REFERENCED_TARGETS
    )
    return _rows(
        cursor,
        f"""
        SELECT fk.name constraint_name,ps.name parent_schema,pt.name parent_table,
               pc.name parent_column,rs.name referenced_schema,rt.name referenced_table,
               rc.name referenced_column,fk.delete_referential_action_desc,
               fk.is_disabled,fk.is_not_trusted
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.tables pt ON pt.object_id=fk.parent_object_id
        JOIN sys.schemas ps ON ps.schema_id=pt.schema_id
        JOIN sys.columns pc ON pc.object_id=pt.object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.tables rt ON rt.object_id=fk.referenced_object_id
        JOIN sys.schemas rs ON rs.schema_id=rt.schema_id
        JOIN sys.columns rc ON rc.object_id=rt.object_id AND rc.column_id=fkc.referenced_column_id
        WHERE {predicates}
        ORDER BY rs.name,rt.name,ps.name,pt.name,fk.name,fkc.constraint_column_id
        """,
    )


def _history_population(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH resolved AS (
          SELECT h.Type,h.EntityUniqueId,
                 CASE WHEN h.Type=1 AND oh.ID IS NOT NULL THEN 1
                      WHEN h.Type=2 AND roh.ID IS NOT NULL THEN 1
                      WHEN h.Type IN(8,16,17) AND sh.ID IS NOT NULL THEN 1
                      WHEN h.Type=10 AND r.ReceiptId IS NOT NULL THEN 1
                      WHEN h.Type=11 AND p.ID IS NOT NULL THEN 1
                      WHEN h.Type=12 AND rsh.ID IS NOT NULL THEN 1
                      ELSE 0 END known_target_resolved
          FROM dbo.TourHistory h
          LEFT JOIN SLE.tblOrderHdr oh ON h.Type=1 AND oh.ID=h.BackOfficeRef
          LEFT JOIN SLE.tblRetOrderHdr roh ON h.Type=2 AND roh.ID=h.BackOfficeRef
          LEFT JOIN SLE.tblSaleHdr sh ON h.Type IN(8,16,17) AND sh.ID=h.BackOfficeRef
          LEFT JOIN dbo.Receipt r ON h.Type=10 AND r.ReceiptId=h.BackOfficeRef
          LEFT JOIN Acc.tblPayments p ON h.Type=11 AND p.ID=h.BackOfficeRef
          LEFT JOIN SLE.tblRetSaleHdr rsh ON h.Type=12 AND rsh.ID=h.BackOfficeRef
        )
        SELECT Type history_type,COUNT_BIG(*) history_count,
               COUNT(DISTINCT EntityUniqueId) distinct_entity_count,
               SUM(known_target_resolved) known_target_resolved_count
        FROM resolved GROUP BY Type ORDER BY Type
        """,
    )


def _receipt_dependency_shape(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH target AS (
          SELECT DISTINCT r.ReceiptId
          FROM dbo.TourHistory h
          JOIN dbo.Receipt r ON r.ReceiptId=h.BackOfficeRef
          WHERE h.Type=10
        ), f AS (
          SELECT t.ReceiptId,
                 CASE WHEN EXISTS(SELECT 1 FROM dbo.RCash x WHERE x.ReceiptId=t.ReceiptId) THEN 1 ELSE 0 END has_cash,
                 CASE WHEN EXISTS(SELECT 1 FROM dbo.RCash x JOIN dbo.RCashDetail d ON d.RCashId=x.RCashId WHERE x.ReceiptId=t.ReceiptId) THEN 1 ELSE 0 END has_cash_detail,
                 CASE WHEN EXISTS(SELECT 1 FROM Acc.TblCheque x WHERE x.ReceiptId=t.ReceiptId) THEN 1 ELSE 0 END has_cheque,
                 CASE WHEN EXISTS(SELECT 1 FROM Acc.TblCheque x JOIN Acc.tblChqHist h ON h.ChqRef=x.ID WHERE x.ReceiptId=t.ReceiptId) THEN 1 ELSE 0 END has_cheque_history,
                 CASE WHEN EXISTS(SELECT 1 FROM Acc.TblBankOrders x WHERE x.ReceiptId=t.ReceiptId) THEN 1 ELSE 0 END has_bank_order,
                 CASE WHEN EXISTS(SELECT 1 FROM Acc.tblPayments x WHERE x.DocReceiptId=t.ReceiptId) THEN 1 ELSE 0 END has_doc_receipt_payment,
                 CASE WHEN EXISTS(SELECT 1 FROM Acc.tblPayments x JOIN dbo.RCash rc ON rc.RCashId=x.RCashId WHERE rc.ReceiptId=t.ReceiptId) THEN 1 ELSE 0 END has_cash_payment,
                 CASE WHEN EXISTS(SELECT 1 FROM Acc.tblPayments x JOIN Acc.TblCheque ch ON ch.ID=x.ChqRef WHERE ch.ReceiptId=t.ReceiptId) THEN 1 ELSE 0 END has_cheque_payment,
                 CASE WHEN EXISTS(SELECT 1 FROM Acc.tblPayments x JOIN Acc.TblBankOrders b ON b.ID=x.BankOrderRef WHERE b.ReceiptId=t.ReceiptId) THEN 1 ELSE 0 END has_bank_order_payment
          FROM target t
        )
        SELECT COUNT_BIG(*) distinct_existing_receipt_count,
               SUM(has_cash) receipt_with_cash_count,
               SUM(has_cash_detail) receipt_with_cash_detail_count,
               SUM(has_cheque) receipt_with_cheque_count,
               SUM(has_cheque_history) receipt_with_cheque_history_count,
               SUM(has_bank_order) receipt_with_bank_order_count,
               SUM(has_doc_receipt_payment) receipt_with_doc_receipt_payment_count,
               SUM(has_cash_payment) receipt_with_cash_payment_count,
               SUM(has_cheque_payment) receipt_with_cheque_payment_count,
               SUM(has_bank_order_payment) receipt_with_bank_order_payment_count,
               SUM(CASE WHEN has_cash_detail=1 OR has_cheque_history=1
                              OR has_cash_payment=1 OR has_cheque_payment=1 OR has_bank_order_payment=1
                        THEN 1 ELSE 0 END) receipt_with_no_action_blocker_candidate_count
        FROM f
        """,
    )[0]


def _trigger_contract(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,tr.name trigger_name,
               tr.is_disabled,tr.is_instead_of_trigger
        FROM sys.triggers tr
        JOIN sys.tables t ON t.object_id=tr.parent_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE (s.name=N'dbo' AND t.name IN(N'TourHistory',N'Receipt',N'RCash',N'RCashDetail'))
           OR (s.name=N'Acc' AND t.name IN(N'TblCheque',N'tblChqHist',N'TblBankOrders',N'tblPayments'))
        ORDER BY s.name,t.name,tr.name
        """,
    )


def collect() -> dict[str, Any]:
    with _connect() as connection:
        cursor = connection.cursor()
        _assert_safe_target(cursor)
        state = _rows(
            cursor,
            """
            SELECT CONVERT(varchar(30),DATABASEPROPERTYEX(DB_NAME(),'Updateability')) updateability,
                   HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','UPDATE') can_update
            """,
        )[0]
        definitions = {name: _procedure_definition(cursor, name) for name in PROC_NAMES}
        profiles = [_procedure_profile(name, definitions[name]) for name in PROC_NAMES]
        controls = {name: _control_flow_profile(definitions[name]) for name in PROC_NAMES}
        signals = {name: _signal_contract(definitions[name]) for name in PROC_NAMES}
        dependencies = {name: _dependencies(cursor, name) for name in PROC_NAMES}
        foreign_keys = _referential_delete_contract(cursor)
        history = _history_population(cursor)
        receipt_shape = _receipt_dependency_shape(cursor)
        triggers = _trigger_contract(cursor)

    active = next(row for row in profiles if row["qualified_name"] == "dbo.NGT_RollBackTour")
    dead = controls["dbo.USP_NGT_UndoReplicateTour"]
    active_signal = {row["signal"]: row for row in signals["dbo.NGT_RollBackTour"]}
    dead_signal = {row["signal"]: row for row in signals["dbo.USP_NGT_UndoReplicateTour"]}
    no_action = [
        row
        for row in foreign_keys
        if row["delete_referential_action_desc"] == "NO_ACTION" and not row["is_disabled"]
    ]
    validation = "PASS" if (
        state["can_update"] == 0
        and dead["standalone_return_precedes_first_mutation"]
        and dead["all_profiled_mutations_are_inside_block_comments"]
        and active_signal["TourHistory"]["outside_block_comment_count"] > 0
    ) else "FAIL"
    return {
        "artifact": "varanegar_ngt_replication_compensation_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": validation,
        "source": {"server": SERVER, "database": DATABASE, "approved_target": True},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": state["updateability"],
            "can_update": state["can_update"],
            "denies_data_writes": 1 if state["can_update"] == 0 else 0,
            "stored_procedure_or_application_command_executions": 0,
            "business_rows_or_identifiers_persisted": 0,
            "sql_definitions_persisted": 0,
            "guid_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "procedure_count": len(profiles),
            "procedure_definition_length": sum(row["definition_length"] for row in profiles),
            "active_rollback_mutation_statement_count": len(active["mutation_ledger"]),
            "active_rollback_mutation_object_count": len(active["mutation_object_counts"]),
            "active_rollback_dependency_count": len(dependencies["dbo.NGT_RollBackTour"]),
            "dead_legacy_undo_profiled_mutation_count": dead["profiled_mutation_count"],
            "foreign_key_edge_count": len(foreign_keys),
            "enabled_no_action_foreign_key_edge_count": len(no_action),
            "tour_history_type_count": len(history),
            "distinct_existing_type_10_receipt_count": receipt_shape["distinct_existing_receipt_count"],
            "type_10_receipt_with_blocker_candidate_count": receipt_shape["receipt_with_no_action_blocker_candidate_count"],
        },
        "procedure_profiles": profiles,
        "procedure_control_flow_contract": controls,
        "procedure_signal_contract": signals,
        "procedure_dependency_contract": dependencies,
        "referential_delete_contract": foreign_keys,
        "trigger_contract": triggers,
        "tour_history_target_population": history,
        "type_10_receipt_dependency_shape": receipt_shape,
        "derived_compensation_contract": {
            "active_entry_point": "dbo.NGT_RollBackTour",
            "active_entry_point_has_local_transaction": active["has_explicit_begin_transaction"],
            "active_entry_point_requires_entity_temp_table": active_signal["#EntityUniqueIdList"]["outside_block_comment_count"] > 0,
            "active_entry_point_deletes_tour_history": active_signal["TourHistory"]["outside_block_comment_count"] > 0,
            "active_entry_point_mentions_cash_detail_cleanup": active_signal["RCashDetail"]["outside_block_comment_count"] > 0,
            "active_entry_point_mentions_cheque_history_cleanup": active_signal["tblChqHist"]["outside_block_comment_count"] > 0,
            "dead_legacy_entry_point": "dbo.USP_NGT_UndoReplicateTour",
            "dead_legacy_entry_point_returns_before_mutations": dead["standalone_return_precedes_first_mutation"],
            "dead_legacy_cleanup_is_commented": dead["all_profiled_mutations_are_inside_block_comments"],
            "dead_legacy_mentions_cash_detail_cleanup": dead_signal["RCashDetail"]["inside_block_comment_count"] > 0,
            "dead_legacy_mentions_cheque_history_cleanup": dead_signal["tblChqHist"]["inside_block_comment_count"] > 0,
            "all_current_existing_type_10_receipts_have_blocker_candidates": receipt_shape["distinct_existing_receipt_count"] > 0
            and receipt_shape["distinct_existing_receipt_count"]
            == receipt_shape["receipt_with_no_action_blocker_candidate_count"],
            "warning": (
                "NO_ACTION dependencies and aggregate child presence prove a deletion blocker candidate, "
                "not a controlled execution result. Caller-side cleanup outside the profiled SQL must be "
                "excluded before declaring every rollback attempt failed."
            ),
        },
        "evidence_limits": [
            "Procedure text is fingerprinted and reduced; no operational procedure was executed.",
            "Current anonymous dependency aggregates do not identify which rollback attempts were made.",
            "A NO_ACTION edge plus child presence is a blocker candidate; trigger/caller cleanup may alter the runtime outcome.",
            "Commented SQL documents historical intent but is not executable behavior.",
            f"GUID literals were counted in memory ({sum(row['distinct_guid_literal_count'] for row in profiles)}) but none were persisted.",
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
    print(json.dumps(payload["summary"], ensure_ascii=False, default=_json_default))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
