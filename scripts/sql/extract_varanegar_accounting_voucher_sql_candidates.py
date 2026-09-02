"""Extract clone catalog candidates for external/manual accounting vouchers."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from extract_varanegar_org_domain import _assert_safe_target, _connect, _rows


TOKENS = ("ExternalVoucher", "ManualVoucher", "CreateVoucher")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    errors = []
    candidates = []
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            rows = _rows(
                cursor,
                """
                SELECT o.object_id,s.name AS schema_name,o.name,o.type,o.type_desc,
                       o.create_date,o.modify_date,
                       (SELECT COUNT(*) FROM sys.parameters p WHERE p.object_id=o.object_id) AS parameter_count,
                       (SELECT COUNT(*) FROM sys.sql_expression_dependencies d WHERE d.referencing_id=o.object_id) AS dependency_count,
                       (SELECT COUNT(*) FROM sys.triggers t WHERE t.parent_id=o.object_id AND t.is_disabled=0) AS enabled_child_trigger_count
                FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE o.is_ms_shipped=0
                  AND (o.name LIKE '%ExternalVoucher%' OR o.name LIKE '%ManualVoucher%' OR o.name LIKE '%CreateVoucher%')
                ORDER BY s.name,o.name
                """,
            )
            for row in rows:
                full_name = f"{row['schema_name']}.{row['name']}"
                matched = [token for token in TOKENS if token.casefold() in row["name"].casefold()]
                candidates.append({
                    "object": full_name,
                    "object_type": row["type"],
                    "object_type_desc": row["type_desc"],
                    "matched_name_tokens": matched,
                    "parameter_count": int(row["parameter_count"]),
                    "dependency_count": int(row["dependency_count"]),
                    "enabled_child_trigger_count": int(row["enabled_child_trigger_count"]),
                    "binding_confidence": "NAME_MATCH_ONLY_NOT_UI_OR_HANDLER_BINDING",
                    "definition_or_result_persisted": False,
                    "runtime_executed": False,
                })
    counts = Counter(row["object_type_desc"] for row in candidates)
    artifact = {
        "artifact": "varanegar_accounting_external_manual_create_voucher_clone_sql_name_candidate_surface",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_NAME_CANDIDATE_EXTRACTION",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "module_definitions_persisted": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "procedures_functions_views_or_triggers_executed": 0,
            "application_commands_executed": 0,
        },
        "summary": {
            "candidate_object_count": len(candidates),
            "object_type_counts": dict(sorted(counts.items())),
            "total_parameter_count": sum(row["parameter_count"] for row in candidates),
            "total_dependency_count": sum(row["dependency_count"] for row in candidates),
            "enabled_child_trigger_count": sum(row["enabled_child_trigger_count"] for row in candidates),
            "exact_static_ui_or_handler_binding_count": 0,
            "runtime_execution_or_result_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "name_tokens": list(TOKENS),
        "candidates": candidates,
        "validation_errors": errors,
        "limits": [
            "Catalog name matches are discovery candidates and do not prove binding to any selected UI or handler command.",
            "Definitions, result rows, parameter values and business values were not read or persisted.",
            "No SQL module, trigger or application command was executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
