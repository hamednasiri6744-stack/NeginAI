"""Build the offline distribution-exit lifecycle checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/distribution_exit_lifecycle_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/distribution_exit_runtime_boundary_20260829.json",
    "distribution_diagnostic": "artifacts/varanegar_analysis/ui/varanegar_distribution_path_diagnostic_contract_20260827.json",
    "distribution_sql": "artifacts/varanegar_analysis/ui/varanegar_distribution_sql_semantics_20260827.json",
    "distribution_source": "artifacts/varanegar_analysis/ui/varanegar_distribution_mutation_source_model_20260827.json",
    "distribution_triggers": "artifacts/varanegar_analysis/ui/varanegar_distribution_trigger_transitive_graph_20260827.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_stock_projection_validation_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_distribution_exit_lifecycle_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_distribution_exit_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_distribution_exit_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_distribution_exit_lifecycle_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/DISTRIBUTION_EXIT_ISSUE_CANCEL_AND_PHYSICAL_DELETE_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name: str) -> dict:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    missing = [path for path in SOURCES.values() if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})
    sql = _load("sql_boundary")
    runtime = _load("runtime_boundary")
    previous = _load("previous_checkpoint")
    risks = _load("risk_register")
    trace = _load("traceability")
    state = sql["current_exit_state"]
    cancel = sql["cancelled_exit_to_type60_delete_reconciliation"]
    lifecycle = sql["generic_exit_log_lifecycle"]
    dist = sql["distribution_state_and_audit"]
    static = sql["static_exit_contract"]
    managed = runtime["managed_exit_contract"]
    r078 = next(row for row in risks["risks"] if row["id"] == "R-078")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_redacted": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
        and sql["safety"]["distribution_exit_sale_voucher_reason_user_host_or_raw_log_values_persisted"] == 0
        and sql["safety"]["sql_definitions_operation_scripts_or_business_identifiers_persisted"] == 0,
        "sql_module_hash_coverage": sql["summary"]["selected_sql_module_count"] == 10
        and len(sql["sql_module_profiles"]) == 10
        and all(len(row["definition_sha256"]) == 64 for row in sql["sql_module_profiles"]),
        "issue_and_cancel_static_shapes": all(static.values()),
        "active_exit_type60_one_to_one": state["population"]["active_count"] == 24035
        and state["active_type60_crosswalk"]["matched_active_exit_count"] == 24035
        and state["active_type60_crosswalk"]["active_exit_without_type60_count"] == 0
        and state["active_type60_crosswalk"]["duplicate_type60_docref_group_count"] == 0,
        "cancel_cleanup_complete": state["population"]["cancelled_count"] == 9910
        and state["cancelled_cleanup"]["lingering_type60_voucher_count"] == 0
        and state["cancelled_cleanup"]["lingering_sale_link_count"] == 0
        and state["cancelled_cleanup"]["retained_full_history_row_count"] == 233535,
        "cancel_delete_adjacency": cancel["cancelled_exit_coverage"]["without_type60_delete_log_count"] == 0
        and cancel["type60_delete_coverage"]["cancelled_within_5_seconds_count"] == 9895
        and cancel["type60_delete_coverage"]["recent_matched_cancelled_count"] == 1442,
        "historical_absence_caveated": lifecycle["logged_id_coverage"]["absent_count"] == 8
        and lifecycle["logged_id_coverage"]["recent_absent_count"] == 0
        and sql["summary"]["retained_exit_delete_log_count"] == 0
        and dist["log_coverage"]["absent_count"] == 6
        and dist["status_chain"]["chain_break_count"] == 0,
        "runtime_static_hash_pinned": runtime["validation"] == "PASS"
        and runtime["summary"]["assembly_count"] == 3
        and runtime["summary"]["selected_method_count"] == 11
        and runtime["summary"]["source_hash_mismatch_count"] == 0
        and runtime["safety"]["assembly_loads_or_executions"] == 0,
        "normal_ui_and_adapter_shapes": managed["business_methods_are_thin_adapter_delegates"]
        and managed["normal_issue_ui_constructs_context_then_calls_create_then_commits"]
        and managed["normal_remove_ui_validates_then_constructs_context_removes_and_commits"]
        and managed["merge_ui_delegates_without_explicit_context_or_commit"]
        and managed["selected_methods_have_no_explicit_rollback_signal"],
        "transaction_limits_preserved": not managed["physical_transaction_enlistment_across_ui_and_nested_adapter_contexts_proven"]
        and not managed["alternate_direct_sql_callsite_selection_proven"],
        "physical_delete_paths_separated": sql["summary"]["direct_physical_exit_delete_candidate_count"] == 3
        and len(sql["direct_physical_exit_delete_candidates"]) == 3,
        "previous_checkpoint_chain": previous["validation"] == "PASS"
        and previous["summary"]["risk_count"] == 84,
        "r078_registered_and_caveated": r078["severity"] == "CRITICAL"
        and "no current partial issue, cancellation, or unauthorized delete incident is asserted" in r078["failure_mode"]
        and "physical enlistment" in r078["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "no_uuid_or_secret_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            raw,
        ) is None
        and re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None,
    }
    failed = sorted(key for key, value in checks.items() if not value)
    manifest = [
        {
            "name": name,
            "path": relative,
            "size_bytes": (ROOT / relative).stat().st_size,
            "sha256": _sha(ROOT / relative),
        }
        for name, relative in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_distribution_exit_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_commands_executed": 0,
            "distribution_exit_sale_voucher_reason_user_host_or_raw_values_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "selected_sql_module_count": sql["summary"]["selected_sql_module_count"],
            "selected_runtime_method_count": runtime["summary"]["selected_method_count"],
            "current_exit_count": sql["summary"]["current_exit_count"],
            "current_active_exit_count": sql["summary"]["current_active_exit_count"],
            "current_cancelled_exit_count": sql["summary"]["current_cancelled_exit_count"],
            "historical_absent_exit_count": sql["summary"]["logged_exit_absent_count"],
            "direct_physical_delete_candidate_count": sql["summary"]["direct_physical_exit_delete_candidate_count"],
            "risk_count": risks["summary"]["risk_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(payload["validation"])
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if payload["failed_checks"]:
        print(json.dumps(payload["failed_checks"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
