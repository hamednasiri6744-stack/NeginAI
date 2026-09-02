"""Build the offline payable-cheque destructive-undo checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/payable_cheque_undo_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/payable_cheque_undo_runtime_boundary_20260829.json",
    "leaf_diagnostic": "artifacts/varanegar_analysis/ui/varanegar_payable_cheque_leaf_usage_diagnostic_contract_20260827.json",
    "supplier_domain": "artifacts/varanegar_analysis/domains/supplier_disbursement_and_payable_cheques_20260826.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_supplier_unapply_delete_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_payable_cheque_undo_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_payable_cheque_undo_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_payable_cheque_undo_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_payable_cheque_undo_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/PAYABLE_CHEQUE_DESTRUCTIVE_UNDO_BOUNDARY_20260829_FA.md",
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
    leaf = _load("leaf_diagnostic")
    risks = _load("risk_register")
    trace = _load("traceability")
    sequence = sql["undo_add_sequence_contract"]
    lifecycle = sql["current_lifecycle"]["aggregate"]
    coverage = sql["retained_history_lifecycle_log"]["logged_id_coverage"]
    shapes = {
        row["shape"]: row
        for row in sql["retained_history_lifecycle_log"]["delete_session_tail_shapes"]
    }
    managed = runtime["managed_undo_contract"]
    r073 = next(row for row in risks["risks"] if row["id"] == "R-073")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_zero_execution": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0,
        "sql_redacted": sql["safety"]["cheque_leaf_history_identifiers_amounts_bank_or_operator_values_persisted"] == 0
        and sql["safety"]["sql_definitions_or_log_scripts_persisted"] == 0,
        "undo_is_destructive_but_transactional": sequence["undo_deletes_history"]
        and not sequence["undo_appends_compensating_history"]
        and sequence["undo_delete_precedes_current_projection_update"]
        and sequence["undo_projection_update_precedes_leaf_update"]
        and sequence["undo_leaf_update_precedes_commit"]
        and sequence["undo_has_try_catch_commit_rollback"],
        "undo_voucher_guard_precedes_transaction": sequence[
            "undo_voucher_check_precedes_transaction"
        ],
        "add_is_append_then_projection": sequence["add_inserts_history_before_projection"]
        and sequence["add_projection_precedes_leaf_update"],
        "outer_change_status_calls_both_paths": sequence[
            "change_status_outer_calls_add_and_delete"
        ]
        and sequence["change_status_outer_owns_transaction"],
        "current_pointer_parity": lifecycle["cheque_count"] == 4672
        and lifecycle["history_count"] == 13108
        and lifecycle["current_pointer_not_max_count"] == 0
        and lifecycle["current_pointer_wrong_parent_count"] == 0,
        "retained_delete_count": sql["summary"]["retained_history_delete_event_count"] == 1668,
        "exact_undo_tail": shapes["UNDO_EXACT_TAIL"]["history_delete_count"] == 1537
        and shapes["UNDO_EXACT_TAIL"]["recent_three_month_count"] == 78,
        "non_undo_delete_shapes_separate": shapes["CHEQUE_DELETE_PRESENT"]["history_delete_count"] == 117
        and shapes["PARTIAL_UPDATE_TAIL"]["history_delete_count"] == 14,
        "logged_coverage_gap": coverage["currently_present_count"] == 13108
        and coverage["currently_absent_count"] == 2070
        and coverage["both_event_count"] == 1668
        and coverage["insert_only_but_absent_count"] == 402,
        "historical_batch_not_recent": sql["retained_history_lifecycle_log"][
            "insert_logged_absent_without_delete_batch"
        ]["insert_logged_absent_without_delete_count"] == 402
        and sql["retained_history_lifecycle_log"]["insert_logged_absent_without_delete_batch"][
            "recent_insert_count"
        ] == 0,
        "storage_non_temporal": len(sql["storage_contract"]["table_capabilities"]) == 3
        and all(
            row["temporal_type_desc"] == "NON_TEMPORAL_TABLE"
            and not row["is_tracked_by_cdc"]
            and row["change_tracking_enabled"] == 0
            for row in sql["storage_contract"]["table_capabilities"]
        ),
        "runtime_hash_pinned": runtime["validation"] == "PASS"
        and runtime["summary"]["source_hash_mismatch_count"] == 0
        and runtime["summary"]["selected_method_count"] == 5,
        "runtime_legacy_undo_and_nested_adapter": managed[
            "legacy_undo_checks_can_do_undo"
        ]
        and managed["legacy_undo_starts_transaction_before_delete_call"]
        and managed["legacy_undo_commit_follows_delete_in_linear_il"]
        and managed["adapter_starts_nested_transaction_before_execute"]
        and managed["adapter_execute_precedes_nested_commit"]
        and managed["adapter_has_rollback_signal"],
        "runtime_form_limits": managed["new_tracking_undo_method_is_one_instruction_stub"]
        and not managed["branch_specific_reapprove_and_rollback_reachability_proven"]
        and not managed["new_tracking_form_runtime_selection_proven"],
        "leaf_partition_preserved": leaf["summary"]["used_leaf_count"] == 4827
        and leaf["summary"]["current_cheque_link_count"] == 4672
        and leaf["summary"]["source_used_unlinked_count"] == 155,
        "r073_registered_and_caveated": r073["severity"] == "HIGH"
        and "current projection is clean" in r073["failure_mode"]
        and "not attributed to undo or trigger bypass" in r073["failure_mode"],
        "current_register_and_trace": risks["summary"]["risk_count"] == 84
        and risks["summary"]["critical_count"] == 50
        and risks["summary"]["high_count"] == 31
        and trace["summary"]["unique_risk_count"] == 84
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["command_ready_module_count"] == 0,
        "no_uuid_literals": re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            raw,
        ) is None,
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
        "artifact": "varanegar_payable_cheque_undo_checkpoint_20260829",
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
            "cheque_leaf_history_bank_or_operator_values_read": 0,
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
            "exact_undo_tail_count": sql["summary"]["exact_undo_tail_history_delete_count"],
            "recent_exact_undo_tail_count": sql["summary"]["recent_exact_undo_tail_count"],
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
