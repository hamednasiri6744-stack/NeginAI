"""Build the offline received-cheque destructive-undo checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/received_cheque_undo_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/received_cheque_undo_runtime_boundary_20260829.json",
    "received_domain": "artifacts/varanegar_analysis/domains/received_cheque_lifecycle_20260826.json",
    "projection_diagnostic": "artifacts/varanegar_analysis/ui/varanegar_received_cheque_projection_and_legal_type_diagnostic_contract_20260827.json",
    "returned_diagnostic": "artifacts/varanegar_analysis/ui/varanegar_returned_cheque_cross_customer_diagnostic_contract_20260827.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_payable_cheque_undo_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_received_cheque_undo_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_received_cheque_undo_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_received_cheque_undo_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_received_cheque_undo_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/RECEIVED_CHEQUE_DESTRUCTIVE_UNDO_AND_TRIGGER_PROJECTION_BOUNDARY_20260829_FA.md",
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
    risks = _load("risk_register")
    trace = _load("traceability")
    previous = _load("previous_checkpoint")
    aggregate = sql["current_lifecycle"]["aggregate"]
    chain = sql["current_lifecycle"]["chain_integrity"]
    coverage = sql["retained_history_lifecycle_log"]["logged_id_coverage"]
    gap = sql["retained_history_lifecycle_log"]["insert_logged_absent_without_delete_batch"]
    shapes = {
        row["shape"]: row
        for row in sql["retained_history_lifecycle_log"]["delete_tail_shapes"]
    }
    contract = sql["undo_add_trigger_contract"]
    managed = runtime["managed_undo_contract"]
    r074 = next(row for row in risks["risks"] if row["id"] == "R-074")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_and_redacted": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
        and sql["safety"]["cheque_history_bank_customer_amount_comment_or_operator_values_persisted"] == 0
        and sql["safety"]["sql_definitions_or_log_scripts_persisted"] == 0,
        "undo_destructive_and_transactional": contract["undo_validates_before_transaction"]
        and contract["undo_owns_transaction_and_rollback"]
        and contract["undo_deletes_history_and_appends_no_compensating_event"]
        and contract["undo_history_delete_precedes_master_audit_update"],
        "conditional_double_delete_proven": contract["undo_has_conditional_status_8_double_delete"],
        "trigger_owned_projection": contract["delete_trigger_reactivates_previous_history"]
        and contract["insert_trigger_deactivates_previous_history"],
        "desktop_wrapper_boundary": contract["desktop_undo_wrapper_calls_delete_last_history"]
        and contract["desktop_undo_wrapper_owns_transaction_without_explicit_rollback"],
        "forward_and_bulk_routes": contract["add_is_transactional_append_path"]
        and contract["outer_change_status_calls_add_and_delete"]
        and contract["outer_change_status_owns_transaction_or_savepoint"],
        "current_projection_parity": aggregate["cheque_count"] == 23822
        and aggregate["history_count"] == 106131
        and aggregate["without_history_count"] == 0
        and aggregate["current_count_mismatch"] == 0
        and aggregate["current_not_max_count"] == 0
        and aggregate["current_wrong_parent_count"] == 0,
        "current_chain_parity": all(value == 0 for value in chain.values()),
        "retained_delete_population": sql["summary"]["retained_history_delete_event_count"] == 14711,
        "undo_command_and_row_cardinality": shapes["SINGLE_UNDO_TAIL"]["history_delete_head_count"] == 1502
        and shapes["DOUBLE_DELETE_UNDO_TAIL"]["history_delete_head_count"] == 22
        and sql["summary"]["undo_attributed_deleted_history_count"] == 1524,
        "recent_undo_cardinality": sql["summary"]["recent_undo_command_tail_count"] == 471
        and sql["summary"]["recent_undo_attributed_deleted_history_count"] == 475,
        "logged_coverage": coverage["logged_id_count"] == 121094
        and coverage["currently_present_count"] == 106131
        and coverage["currently_absent_count"] == 14963
        and coverage["both_event_count"] == 14711
        and coverage["insert_only_but_absent_count"] == 252,
        "historical_gap_not_recent": gap["insert_logged_absent_without_delete_count"] == 252
        and gap["recent_insert_count"] == 0,
        "storage_non_temporal": len(sql["storage_contract"]["table_capabilities"]) == 2
        and all(
            row["temporal_type_desc"] == "NON_TEMPORAL_TABLE"
            and not row["is_tracked_by_cdc"]
            and row["change_tracking_enabled"] == 0
            for row in sql["storage_contract"]["table_capabilities"]
        ),
        "runtime_hash_and_coverage": runtime["validation"] == "PASS"
        and runtime["summary"]["source_hash_mismatch_count"] == 0
        and runtime["summary"]["selected_method_count"] == 6,
        "runtime_both_forms_use_wrapper": managed["legacy_undo_starts_transaction_before_delete_call"]
        and managed["legacy_undo_delete_precedes_commit_in_linear_il"]
        and managed["new_undo_starts_transaction_before_delete_call"]
        and managed["new_undo_delete_precedes_commit_in_linear_il"]
        and managed["desktop_forms_call_cession_wrapper_not_direct_delete_adapter"],
        "runtime_nested_adapters": managed["adapter_starts_nested_transaction_before_execute"]
        and managed["adapter_execute_precedes_nested_commit"]
        and managed["adapter_has_rollback_signal"]
        and managed["cession_wrapper_adapter_starts_nested_transaction_before_execute"]
        and managed["cession_wrapper_adapter_execute_precedes_nested_commit"]
        and managed["cession_wrapper_adapter_has_rollback_signal"],
        "runtime_limits_preserved": not managed["branch_specific_delete_cession_and_rollback_reachability_proven"]
        and not managed["runtime_form_selection_proven"],
        "previous_checkpoint_chain": previous["validation"] == "PASS"
        and previous["summary"]["risk_count"] == 84,
        "r074_registered_and_caveated": r074["severity"] == "HIGH"
        and "current projection is clean" in r074["failure_mode"]
        and "are not attributed to undo" in r074["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "no_uuid_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            raw,
        )
        is None,
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
        "artifact": "varanegar_received_cheque_undo_checkpoint_20260829",
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
            "cheque_history_bank_customer_amount_comment_or_operator_values_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "current_cheque_count": sql["summary"]["current_cheque_count"],
            "current_history_count": sql["summary"]["current_history_count"],
            "retained_history_delete_count": sql["summary"]["retained_history_delete_event_count"],
            "undo_command_tail_count": sql["summary"]["undo_command_tail_count"],
            "conditional_double_delete_command_count": sql["summary"]["conditional_double_delete_command_count"],
            "undo_attributed_deleted_history_count": sql["summary"]["undo_attributed_deleted_history_count"],
            "recent_undo_command_tail_count": sql["summary"]["recent_undo_command_tail_count"],
            "absent_without_delete_log_count": sql["summary"]["insert_logged_absent_without_delete_count"],
            "runtime_selected_method_count": runtime["summary"]["selected_method_count"],
            "risk_count": risks["summary"]["risk_count"],
            "critical_risk_count": risks["summary"]["critical_count"],
            "high_risk_count": risks["summary"]["high_count"],
            "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"],
            "command_ready_module_count": trace["summary"]["command_ready_module_count"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if payload["failed_checks"]:
        print(json.dumps(payload["failed_checks"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
