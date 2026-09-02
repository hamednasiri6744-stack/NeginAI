"""Build the offline order-to-sale conversion checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/sale_conversion_state_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/sale_conversion_runtime_boundary_20260829.json",
    "order_sale_domain": "artifacts/varanegar_analysis/domains/order_sale_lifecycle_20260826.json",
    "order_sale_commands": "artifacts/varanegar_analysis/ui/varanegar_order_sale_entry_command_contracts_20260827.json",
    "order_sale_graph": "artifacts/varanegar_analysis/ui/varanegar_order_sale_command_dependency_graph_20260827.json",
    "order_sale_sql": "artifacts/varanegar_analysis/ui/varanegar_order_sale_sql_semantics_20260827.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_distribution_exit_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_sale_conversion_state_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_sale_conversion_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_sale_conversion_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_sale_conversion_state_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/ORDER_TO_SALE_CONVERSION_TRANSACTION_AND_STATE_BOUNDARY_20260829_FA.md",
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
    static = sql["static_conversion_and_projection_contract"]
    state = sql["current_sale_state"]
    detail = sql["sale_detail_projection"]
    timing = sql["conversion_attempt_timing_reconciliation"]
    audit = sql["generic_sale_log_lifecycle"]
    managed = runtime["managed_conversion_contract"]
    r079 = next(row for row in risks["risks"] if row["id"] == "R-079")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_redacted": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
        and sql["safety"]["order_sale_customer_goods_user_host_or_raw_log_values_persisted"] == 0
        and sql["safety"]["sql_definitions_error_texts_or_business_identifiers_persisted"] == 0,
        "sql_hash_coverage": sql["summary"]["selected_sql_module_count"] == 7
        and len(sql["sql_module_profiles"]) == 7
        and all(len(row["definition_sha256"]) == 64 for row in sql["sql_module_profiles"]),
        "orchestrator_and_core_shapes": static["orchestrator_has_with_out_rollback_parameter_and_branches"]
        and static["orchestrator_has_local_transaction_try_catch_commit_and_rollback"]
        and static["orchestrator_calls_core_before_order_selected_sale_pointer_update"]
        and static["orchestrator_writes_conversion_timing_and_order_sale_pointer"]
        and static["orchestrator_mutates_payment_batch_reserved_prize_and_item_detail"]
        and static["orchestrator_contains_dynamic_sql"]
        and static["core_has_no_local_transaction"]
        and static["core_inserts_sale_header_and_items"],
        "trigger_owned_projection_shapes": static["detail_trigger_inserts_sale_detail_on_header_change"]
        and static["cancel_trigger_deletes_payment_on_cancel_flag_change"]
        and static["stock_trigger_mutates_stock_goods_from_sale_header"]
        and static["current_replication_delete_trigger_is_bypassable"],
        "current_order_sale_invariants": state["population"]["sale_count"] == 275995
        and state["order_relationship"]["multi_attempt_order_count"] == 18009
        and state["order_relationship"]["multi_active_attempt_order_count"] == 0
        and state["order_relationship"]["selected_pointer_missing_count"] == 0
        and state["order_relationship"]["selected_reverse_mismatch_count"] == 0,
        "semantic_detail_projection": detail["overview"]["cancelled_header_expected_terminal_detail_count"] == 61019
        and detail["overview"]["active_header_latest_status_mismatch_count"] == 6
        and detail["overview"]["cancelled_header_unexpected_latest_status_count"] == 3
        and sql["summary"]["recent_projection_exception_count"] == 0,
        "attempt_timing_gaps_preserved": timing["sale_attempt_count"] == 275995
        and timing["timed_attempt_count"] == 266202
        and timing["sale_order_without_timing_count"] == 9809
        and timing["timing_order_without_sale_count"] == 9,
        "delete_audit_and_gaps_preserved": sql["summary"]["retained_sale_delete_log_count"] == 640
        and sql["summary"]["recent_retained_sale_delete_log_count"] == 112
        and sql["summary"]["logged_sale_absent_count"] == 658
        and sql["summary"]["absent_without_delete_log_count"] == 18
        and audit["logged_id_coverage"]["recent_absent_without_delete_count"] == 0
        and sql["summary"]["direct_physical_sale_delete_candidate_count"] == 1,
        "runtime_hash_pinned": runtime["validation"] == "PASS"
        and runtime["summary"]["assembly_count"] == 3
        and runtime["summary"]["selected_method_count"] == 5
        and runtime["summary"]["selected_instruction_count"] == 1055
        and runtime["summary"]["source_hash_mismatch_count"] == 0
        and runtime["safety"]["assembly_loads_or_executions"] == 0,
        "runtime_nested_ownership_shape": managed["ui_save_delegates_without_explicit_context_commit_or_rollback"]
        and managed["sale_business_constructs_context_calls_create_then_commits"]
        and not managed["sale_business_has_explicit_rollback_signal"]
        and managed["order_business_has_two_overloads_and_one_thin_adapter_delegate"]
        and managed["adapter_uses_named_orchestrator_and_commits"]
        and managed["selected_methods_have_nested_business_and_adapter_commit_signals"],
        "runtime_limits_preserved": not managed["with_out_rollback_runtime_value_and_branch_proven"]
        and not managed["physical_transaction_enlistment_across_business_and_adapter_contexts_proven"],
        "previous_checkpoint_chain": previous["validation"] == "PASS"
        and previous["summary"]["risk_count"] == 84,
        "r079_registered_and_caveated": r079["severity"] == "CRITICAL"
        and "no current duplicate-active-sale or recent state-projection exception is asserted" in r079["failure_mode"]
        and "do not prove attribution" in r079["failure_mode"],
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
        "artifact": "varanegar_sale_conversion_checkpoint_20260829",
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
            "order_sale_customer_goods_user_host_error_or_raw_values_read": 0,
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
            "current_sale_count": sql["summary"]["current_sale_count"],
            "current_active_sale_count": sql["summary"]["current_active_sale_count"],
            "current_cancelled_sale_count": sql["summary"]["current_cancelled_sale_count"],
            "active_projection_mismatch_count": sql["summary"]["active_latest_detail_status_mismatch_count"],
            "retained_sale_delete_count": sql["summary"]["retained_sale_delete_log_count"],
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
