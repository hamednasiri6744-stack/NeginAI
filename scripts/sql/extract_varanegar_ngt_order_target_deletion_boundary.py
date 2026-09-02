"""Profile deletion and tombstone coverage around SLE.tblOrderHdr, read-only."""

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


TARGET_TOKEN = re.compile(r"(?i)(?:\[?sle\]?\s*\.\s*)?\[?tblorderhdr\]?")
DIRECT_DELETE = re.compile(
    r"(?is)\bdelete\s+(?:from\s+)?(?:\[?sle\]?\s*\.\s*)?\[?tblorderhdr\]?\b"
)
ALIASED_DELETE = re.compile(
    r"(?is)\bdelete\s+(?:top\s*\([^)]*\)\s+)?\[?\w+\]?\s+from\s+"
    r"(?:\[?sle\]?\s*\.\s*)?\[?tblorderhdr\]?\b"
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _executable_text(definition: str) -> str:
    """Remove comments and string literals before static mutation matching."""
    text = re.sub(r"(?s)/\*.*?\*/", " ", definition)
    text = re.sub(r"(?m)--.*$", " ", text)
    return re.sub(r"'(?:''|[^'])*'", "<literal>", text)


def _module_profiles(cursor: Any) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition,o.modify_date
        FROM sys.sql_modules m
        JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE LOWER(m.definition) LIKE '%tblorderhdr%'
        ORDER BY s.name,o.name
        """,
    )
    profiles = []
    for row in rows:
        definition = row.pop("definition") or ""
        code = _executable_text(definition)
        lower = code.lower()
        delete_match = DIRECT_DELETE.search(code) or ALIASED_DELETE.search(code)
        direct_delete = bool(delete_match)
        early_return = bool(
            direct_delete
            and re.search(
                r"(?is)\bas\s+begin\s+(?:set\s+nocount\s+on\s*;?\s*)?return\b",
                code[: delete_match.start()],
            )
        )
        profiles.append(
            {
                **row,
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "direct_order_header_delete_signal": direct_delete,
                "unconditional_early_return_before_delete_signal": early_return,
                "executable_delete_keyword_count": len(re.findall(r"(?i)\bdelete\b", code)),
                "transaction_signal": any(
                    token in lower
                    for token in ("begin tran", "begin transaction", "commit", "rollback")
                ),
                "try_catch_signal": "begin try" in lower and "begin catch" in lower,
                "xact_abort_signal": "xact_abort" in lower,
                "tour_history_signal": "tourhistory" in lower,
                "ngt_order_line_signal": "customercallorderline" in lower,
                "ngt_order_header_signal": "customercallorders" in lower,
                "order_crosswalk_signal": any(
                    token in lower
                    for token in (
                        "backofficeorderuniqueid",
                        "backofficeorderref",
                        "backofficeorderno",
                    )
                ),
                "replication_log_signal": "inserttolog" in lower,
                "deleted_pseudotable_signal": bool(re.search(r"(?i)\bdeleted\b", code)),
                "dynamic_sql_signal": "sp_executesql" in definition.lower()
                or "exec(" in definition.lower(),
            }
        )
    return profiles


def _target_triggers(cursor: Any) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,tr.name trigger_name,tr.is_disabled,tr.is_instead_of_trigger,
               te.type_desc event_type,m.definition,tr.modify_date
        FROM sys.triggers tr
        JOIN sys.tables t ON t.object_id=tr.parent_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.trigger_events te ON te.object_id=tr.object_id
        LEFT JOIN sys.sql_modules m ON m.object_id=tr.object_id
        WHERE s.name='SLE' AND t.name='tblOrderHdr'
        ORDER BY tr.name,te.type_desc
        """,
    )
    result = []
    for row in rows:
        definition = row.pop("definition") or ""
        lower = definition.lower()
        result.append(
            {
                **row,
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "tour_history_signal": "tourhistory" in lower,
                "ngt_crosswalk_signal": any(
                    token in lower
                    for token in (
                        "customercallorderline",
                        "backofficeorderuniqueid",
                        "backofficeorderref",
                    )
                ),
                "replication_log_signal": "inserttolog" in lower,
                "deleted_pseudotable_signal": bool(re.search(r"(?i)\bdeleted\b", definition)),
            }
        )
    return result


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT fk.name constraint_name,ps.name parent_schema,pt.name parent_table,
               fk.delete_referential_action_desc,fk.update_referential_action_desc,
               fk.is_disabled,fk.is_not_trusted
        FROM sys.foreign_keys fk
        JOIN sys.tables rt ON rt.object_id=fk.referenced_object_id
        JOIN sys.schemas rs ON rs.schema_id=rt.schema_id
        JOIN sys.tables pt ON pt.object_id=fk.parent_object_id
        JOIN sys.schemas ps ON ps.schema_id=pt.schema_id
        WHERE rs.name='SLE' AND rt.name='tblOrderHdr'
        ORDER BY ps.name,pt.name,fk.name
        """,
    )


def _table_features(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        SELECT t.temporal_type_desc,t.is_tracked_by_cdc,
               CASE WHEN ct.object_id IS NULL THEN 0 ELSE 1 END change_tracking_enabled,
               CASE WHEN t.history_table_id<>0 THEN 1 ELSE 0 END temporal_history_present
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        LEFT JOIN sys.change_tracking_tables ct ON ct.object_id=t.object_id
        WHERE s.name='SLE' AND t.name='tblOrderHdr'
        """,
    )[0]


def _callers(cursor: Any, direct_names: list[tuple[str, str]]) -> list[dict[str, Any]]:
    if not direct_names:
        return []
    rows = _rows(
        cursor,
        """
        SELECT DISTINCT caller_schema.name caller_schema,caller.name caller_name,
               caller.type_desc caller_type,callee_schema.name callee_schema,
               callee.name callee_name
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects caller ON caller.object_id=d.referencing_id
        JOIN sys.schemas caller_schema ON caller_schema.schema_id=caller.schema_id
        JOIN sys.objects callee ON callee.object_id=d.referenced_id
        JOIN sys.schemas callee_schema ON callee_schema.schema_id=callee.schema_id
        ORDER BY callee_schema.name,callee.name,caller_schema.name,caller.name
        """,
    )
    wanted = {(schema.lower(), name.lower()) for schema, name in direct_names}
    return [
        row
        for row in rows
        if (row["callee_schema"].lower(), row["callee_name"].lower()) in wanted
    ]


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        profiles = _module_profiles(cursor)
        triggers = _target_triggers(cursor)
        foreign_keys = _foreign_keys(cursor)
        features = _table_features(cursor)
        direct_names = [
            (row["schema_name"], row["object_name"])
            for row in profiles
            if row["direct_order_header_delete_signal"]
        ]
        callers = _callers(cursor, direct_names)
    finally:
        connection.close()

    direct = [row for row in profiles if row["direct_order_header_delete_signal"]]
    executable_candidates = [
        row
        for row in direct
        if row["type_desc"] != "SQL_TRIGGER"
        and not row["unconditional_early_return_before_delete_signal"]
    ]
    active_delete_triggers = [
        row for row in triggers if row["event_type"] == "DELETE" and not row["is_disabled"]
    ]
    contract = {
        "module_referencing_target_count": len(profiles),
        "direct_delete_module_count": len(direct),
        "executable_static_delete_candidate_count": len(executable_candidates),
        "early_return_dead_delete_module_count": sum(
            row["unconditional_early_return_before_delete_signal"] for row in direct
        ),
        "direct_delete_with_tour_history_count": sum(row["tour_history_signal"] for row in direct),
        "direct_delete_with_ngt_line_count": sum(row["ngt_order_line_signal"] for row in direct),
        "direct_delete_with_crosswalk_count": sum(row["order_crosswalk_signal"] for row in direct),
        "direct_delete_with_transaction_count": sum(row["transaction_signal"] for row in direct),
        "direct_delete_with_try_catch_count": sum(row["try_catch_signal"] for row in direct),
        "direct_delete_with_xact_abort_count": sum(row["xact_abort_signal"] for row in direct),
        "direct_delete_dynamic_sql_count": sum(row["dynamic_sql_signal"] for row in direct),
        "target_trigger_event_count": len(triggers),
        "active_delete_trigger_count": len(active_delete_triggers),
        "active_delete_trigger_with_replication_log_count": sum(
            row["replication_log_signal"] for row in active_delete_triggers
        ),
        "active_delete_trigger_with_ngt_crosswalk_count": sum(
            row["ngt_crosswalk_signal"] for row in active_delete_triggers
        ),
        "active_delete_trigger_with_tour_history_count": sum(
            row["tour_history_signal"] for row in active_delete_triggers
        ),
        "referencing_foreign_key_count": len(foreign_keys),
        "cascade_delete_foreign_key_count": sum(
            row["delete_referential_action_desc"] == "CASCADE" and not row["is_disabled"]
            for row in foreign_keys
        ),
        "no_action_delete_foreign_key_count": sum(
            row["delete_referential_action_desc"] == "NO_ACTION" and not row["is_disabled"]
            for row in foreign_keys
        ),
        "direct_delete_caller_count": len(callers),
    }
    return {
        "artifact": "varanegar_ngt_order_target_deletion_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE, "target": "SLE.tblOrderHdr"},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_ONLY",
            "database_updateability": safety["updateability"],
            "can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "business_rows_or_identifiers_persisted": 0,
            "sql_definitions_persisted": 0,
            "configuration_values_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": contract,
        "table_features": features,
        "direct_delete_module_profiles": direct,
        "target_trigger_profiles": triggers,
        "referencing_foreign_keys": foreign_keys,
        "direct_delete_callers": callers,
        "evidence_limits": [
            "Static definition signals do not prove that a module or branch executed for any missing target.",
            "Text matching can miss dynamic or encrypted deletion paths and cannot establish runtime reachability.",
            "Replication log signaling is not equivalent to a durable NGT crosswalk tombstone or reconciliation workflow.",
            "No SQL definition, raw row, identifier or configuration value is persisted.",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
