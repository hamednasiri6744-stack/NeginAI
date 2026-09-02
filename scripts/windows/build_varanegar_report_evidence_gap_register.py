"""Build an offline closure register for the 20 known Varanegar report surfaces."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-contracts", required=True, type=Path)
    parser.add_argument("--dependency-graph", required=True, type=Path)
    parser.add_argument("--method-paths", required=True, type=Path)
    parser.add_argument("--sql-candidates", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    contracts = _load(args.target_contracts)
    dependency = _load(args.dependency_graph)
    methods = _load(args.method_paths)
    sql = _load(args.sql_candidates)
    errors: list[str] = []
    inputs = (contracts, dependency, methods, sql)
    if any(payload.get("validation") != "PASS" for payload in inputs):
        errors.append("one or more source artifacts are not PASS")

    dep_by_type = {row["report_type"]: row for row in dependency["reports"]}
    method_by_type = {row["report_type"]: row for row in methods["reports"]}
    sql_by_type = {row["report_type"]: row for row in sql["reports"]}
    contract_types = {row["legacy_type"] for row in contracts["contracts"]}
    if contract_types != set(dep_by_type) or contract_types != set(method_by_type) or contract_types != set(sql_by_type):
        errors.append("report type sets differ across evidence sources")

    rows = []
    for contract in contracts["contracts"]:
        legacy_type = contract["legacy_type"]
        dep = dep_by_type[legacy_type]
        method = method_by_type[legacy_type]
        candidate = sql_by_type[legacy_type]
        terminal = method["terminal_data_access_method_count"]
        execution = method["terminal_method_with_execution_signal_count"]
        mutation = method["terminal_method_with_mutation_signal_count"]
        candidate_count = candidate["candidate_object_count"]
        direct = method["direct_ui_to_data_access_terminal_count"]

        gaps = ["RESULT_PARITY_MISSING", "OWNER_GOLDEN_VALUES_MISSING", "EFFECTIVE_SCOPE_SEMANTICS_UNPROVEN"]
        if terminal == 0:
            gaps.append("STATIC_METHOD_PATH_MISSING")
        if execution == 0:
            gaps.append("TERMINAL_EXECUTION_SIGNAL_MISSING")
        if candidate_count == 0:
            gaps.append("SQL_CANDIDATE_MISSING")
        gaps.append("SQL_IDENTITY_AND_PARAMETER_BINDING_UNPROVEN")
        if direct:
            gaps.append("DIRECT_UI_TO_DATA_ACCESS_COUPLING")
        if mutation:
            gaps.append("QUERY_COMMAND_BOUNDARY_REQUIRED")

        if execution and candidate_count:
            evidence_level = "L3_METHOD_EXECUTION_SIGNAL_PLUS_NAME_CANDIDATES"
        elif execution:
            evidence_level = "L2_TERMINAL_METHOD_EXECUTION_SIGNAL"
        elif terminal:
            evidence_level = "L1_TERMINAL_METHOD_PATH_ONLY"
        else:
            evidence_level = "L0_REPORT_SHELL_OR_UNRESOLVED_PATH"

        closure = [
            "obtain_owner_approved_filter_and_result_golden_values",
            "prove_role_branch_and_effective_scope_with_safe_observation_or_specification",
            "bind_terminal_method_to_exact_query_or_view_without executing legacy report",
            "reconcile row_count_totals_null_rounding_and_business_date_on_frozen_snapshot",
        ]
        if "STATIC_METHOD_PATH_MISSING" in gaps:
            closure.insert(0, "trace caller_base_report_engine_delegate_or_inherited_path")
        if "SQL_CANDIDATE_MISSING" in gaps:
            closure.insert(1, "resolve dynamic_sql_or_external_report_definition_by_fingerprint")
        if mutation:
            closure.append("split_and_test_idempotent_versioned_command_separately_from_query")

        rows.append(
            {
                "contract_id": contract["contract_id"],
                "legacy_type": legacy_type,
                "query_surface": contract["query_surface"],
                "primary_domain_id": contract["primary_domain_id"],
                "classification": contract["legacy_classification"],
                "static_one_hop_path_status": dep["static_query_path_status"],
                "terminal_data_access_method_count": terminal,
                "terminal_execution_signal_count": execution,
                "terminal_mutation_signal_count": mutation,
                "direct_ui_to_data_access_terminal_count": direct,
                "sql_candidate_object_count": candidate_count,
                "sql_candidate_link_status": candidate["link_status"],
                "evidence_level": evidence_level,
                "gap_codes": gaps,
                "closure_tasks": closure,
                "result_parity_proven": False,
                "implementation_ready": False,
                "pilot_ready": False,
            }
        )

    levels = Counter(row["evidence_level"] for row in rows)
    gap_counts = Counter(gap for row in rows for gap in row["gap_codes"])
    artifact = {
        "artifact": "varanegar_report_evidence_gap_and_closure_register",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_CROSSWALK_OF_REDACTED_STATIC_REPORT_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "legacy_reports_queries_or_commands_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "implementation_pilot_or_result_parity_inferred": 0,
        },
        "summary": {
            "report_surface_count": len(rows),
            "evidence_level_counts": dict(sorted(levels.items())),
            "report_with_terminal_method_path_count": sum(row["terminal_data_access_method_count"] > 0 for row in rows),
            "report_with_execution_signal_count": sum(row["terminal_execution_signal_count"] > 0 for row in rows),
            "report_with_sql_candidate_count": sum(row["sql_candidate_object_count"] > 0 for row in rows),
            "report_with_direct_ui_data_access_count": sum(row["direct_ui_to_data_access_terminal_count"] > 0 for row in rows),
            "report_with_mutation_boundary_count": sum(row["terminal_mutation_signal_count"] > 0 for row in rows),
            "result_parity_proven_count": 0,
            "implementation_ready_count": 0,
            "pilot_ready_count": 0,
            "gap_code_counts": dict(sorted(gap_counts.items())),
            "validation_error_count": len(errors),
        },
        "reports": rows,
        "closure_sequence": [
            "resolve L0 shell/base/caller paths without invoking the application",
            "bind exact query identity and parameters using read-only metadata or owner specification",
            "freeze a privacy-safe source snapshot with provenance and watermarks",
            "capture owner-approved golden inputs and expected aggregates",
            "run target query parity and authorization/fault/concurrency suites",
            "approve pilot only after all P0 gaps close",
        ],
        "validation_errors": errors,
        "limits": [
            "A static call edge or execution-call signal is not runtime execution proof.",
            "Name-based SQL candidates are discovery hints and may contain false positives.",
            "No production or clone report was executed, so result parity remains zero.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
