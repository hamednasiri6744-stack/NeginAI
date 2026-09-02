"""Extract redacted semantics for the treasury edit source-model triggers."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from extract_varanegar_extension_sql_semantics import _module_contract
from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.source_model.read_text(encoding="utf-8-sig"))
    expected = {
        (row["object"], trigger["name"]): trigger
        for row in source["objects"]
        for trigger in row["triggers"]
    }

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            catalog = _rows(
                cursor,
                "SELECT s.name AS schema_name,o.name AS object_name FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id WHERE o.is_ms_shipped=0",
            )
            catalog_names: dict[str, list[str]] = {}
            for row in catalog:
                full = f"{row['schema_name']}.{row['object_name']}"
                catalog_names.setdefault(full.casefold(), []).append(full)
                catalog_names.setdefault(str(row["object_name"]).casefold(), []).append(full)
            trigger_rows = _rows(
                cursor,
                """
                SELECT OBJECT_SCHEMA_NAME(tr.object_id) AS trigger_schema,tr.name AS trigger_name,
                       ps.name+'.'+po.name AS parent_object,tr.is_instead_of_trigger,tr.is_disabled,
                       OBJECTPROPERTYEX(tr.object_id,'ExecIsInsertTrigger') AS is_insert,
                       OBJECTPROPERTYEX(tr.object_id,'ExecIsUpdateTrigger') AS is_update,
                       OBJECTPROPERTYEX(tr.object_id,'ExecIsDeleteTrigger') AS is_delete
                FROM sys.triggers tr
                JOIN sys.objects po ON po.object_id=tr.parent_id
                JOIN sys.schemas ps ON ps.schema_id=po.schema_id
                WHERE tr.parent_class=1 AND tr.is_ms_shipped=0
                ORDER BY parent_object,trigger_name
                """,
            )
            selected = []
            for row in trigger_rows:
                key = (row["parent_object"], row["trigger_name"])
                if key not in expected:
                    continue
                item = {
                    "object": f"{row['trigger_schema']}.{row['trigger_name']}",
                    "capability": "treasury.edit",
                    "role": "writable-view bridge" if row["is_instead_of_trigger"] else "table guard audit replication or synchronization",
                }
                contract = _module_contract(cursor, item, catalog_names)
                contract.update({
                    "parent_object": row["parent_object"],
                    "is_instead_of": bool(row["is_instead_of_trigger"]),
                    "is_disabled": bool(row["is_disabled"]),
                    "events": [event for event, field in (("INSERT", "is_insert"), ("UPDATE", "is_update"), ("DELETE", "is_delete")) if row[field]],
                })
                selected.append(contract)

    missing = sorted(f"{parent}.{name}" for parent, name in expected if not any(row["parent_object"] == parent and row["object"].endswith("." + name) for row in selected))
    errors = []
    if source.get("validation") != "PASS":
        errors.append("source model is not PASS")
    if missing:
        errors.append("source-model triggers missing from catalog semantic scan")
    operation_counts = Counter(
        verb
        for row in selected
        for verb, count in row.get("lexical_operation_counts", {}).items()
        for _ in range(count)
    )
    summary = {
        "expected_trigger_count": len(expected),
        "resolved_trigger_count": len(selected),
        "instead_of_trigger_count": sum(row["is_instead_of"] for row in selected),
        "disabled_trigger_count": sum(row["is_disabled"] for row in selected),
        "dependency_count": sum(row.get("dependency_count", 0) for row in selected),
        "lexical_operation_count": sum(row.get("lexical_operation_count", 0) for row in selected),
        "lexical_operation_counts": dict(sorted(operation_counts.items())),
        "resolved_mutation_target_count": len({target for row in selected for target in row.get("resolved_mutation_targets", [])}),
        "trigger_with_explicit_transaction_envelope_count": sum(row.get("has_explicit_transaction_envelope", False) for row in selected),
        "trigger_with_explicit_error_handler_count": sum(row.get("has_explicit_error_handler", False) for row in selected),
        "trigger_with_dynamic_sql_signal_count": sum(row.get("has_dynamic_sql_signal", False) for row in selected),
        "definition_persisted_count": sum(row.get("definition_persisted", False) for row in selected),
        "runtime_trigger_execution_or_effect_parity_proven_count": 0,
        "missing_trigger_count": len(missing),
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_treasury_edit_trigger_redacted_semantic_footprints",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_CLONE_TRIGGER_DEFINITION_IN_MEMORY_REDACTED_SEMANTIC_PARSE",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "business_row_values_read_or_persisted": 0,
            "module_definitions_or_string_literals_persisted": 0,
            "triggers_procedures_functions_views_or_application_commands_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": summary,
        "triggers": selected,
        "missing_triggers": missing,
        "validation_errors": errors,
        "limits": [
            "Lexical operations are static candidates after comments and strings are masked.",
            "Dynamic SQL and nested trigger or procedure effects need bounded transitive analysis.",
            "No trigger was executed and effect/result parity remains unproven.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
