"""Build the offline supplier unlink/delete evidence checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/supplier_unapply_delete_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/supplier_unapply_delete_runtime_boundary_20260829.json",
    "cost_boundary": "artifacts/varanegar_analysis/domains/supplier_cost_apply_boundary_20260829.json",
    "cost_checkpoint": "artifacts/varanegar_analysis/varanegar_supplier_cost_apply_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_supplier_unapply_delete_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_supplier_unapply_delete_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_supplier_unapply_delete_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_supplier_unapply_delete_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/SUPPLIER_UNAPPLY_DELETE_AND_COST_REVERSAL_BOUNDARY_20260829_FA.md",
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
    unlink = sql["unlink_reverse_contract"]
    states = {row["Status"]: row for row in sql["invoice_relation_state"]}
    prices = {
        row["Status"]: row
        for row in sql["voucher_item_price_state"]["related_items_by_invoice_status"]
    }
    lifecycle = sql["retained_relation_lifecycle_log"]["lifecycle"]
    managed = runtime["managed_unlink_delete_contract"]
    r072 = next(row for row in risks["risks"] if row["id"] == "R-072")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_zero_execution": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0,
        "sql_redacted": sql["safety"]["business_rows_identifiers_amounts_prices_or_operator_values_persisted"] == 0
        and sql["safety"]["sql_definitions_or_log_scripts_persisted"] == 0,
        "path_transaction_variance": sql["summary"]["selected_sql_module_count"] == 8
        and sql["summary"]["selected_module_with_local_transaction_count"] == 3,
        "unlink_destructive_sequence": unlink["unlink_sets_whole_invoice_status_zero"]
        and unlink["unlink_clears_whole_invoice_confirm_date"]
        and unlink["unlink_zeros_selected_voucher_item_price_and_unit_price"]
        and unlink["status_zero_precedes_price_zero"]
        and not unlink["unlink_owns_local_transaction"],
        "unlink_final_date_and_app_branch": unlink["unlink_reads_purchase_final_date"]
        and unlink["unlink_reads_last_closed_purchase_date"]
        and unlink["unlink_has_application_specific_rollback_branch"],
        "unapplied_n_to_m_state": states[0]["header_count"] == 141
        and states[0]["multi_relation_count"] == 17
        and states[0]["no_relation_count"] == 0,
        "applied_n_to_m_state": states[1]["header_count"] == 3285
        and states[1]["multi_relation_count"] == 192
        and states[1]["no_relation_count"] == 0,
        "clean_status_price_parity": prices[0]["price_present_count"] == 0
        and prices[0]["price_absent_count"] == 1354
        and prices[1]["price_present_count"] == 29078
        and prices[1]["price_absent_count"] == 0,
        "relation_log_counts": sql["summary"]["retained_relation_insert_event_count"] == 3902
        and sql["summary"]["retained_relation_delete_event_count"] == 213
        and sql["summary"]["recent_relation_delete_event_count"] == 15,
        "relation_last_event_projects_current": lifecycle["currently_present_count"] == 3689
        and lifecycle["currently_absent_count"] == 203
        and sql["retained_relation_lifecycle_log"]["last_event_projection"] == [
            {"last_event": "DELETE", "current_present": 0, "relation_id_count": 203},
            {"last_event": "INSERT", "current_present": 1, "relation_id_count": 3689},
        ],
        "storage_audit_gap": all(
            row["temporal_type_desc"] == "NON_TEMPORAL_TABLE"
            and not row["is_tracked_by_cdc"]
            and row["change_tracking_enabled"] == 0
            for row in sql["storage_guard_contract"]["table_capabilities"]
        )
        and len(sql["storage_guard_contract"]["active_triggers"]) == 4,
        "runtime_hash_pinned": runtime["validation"] == "PASS"
        and runtime["summary"]["source_hash_mismatch_count"] == 0
        and runtime["summary"]["selected_method_count"] == 4,
        "runtime_managed_unlink_order": managed["unlink_relation_save_precedes_operation_call"]
        and managed["unlink_operation_code_three_precedes_operation_call"]
        and managed["unlink_operation_call_precedes_commit_in_linear_il"]
        and managed["unlink_adapter_data_context_execute_call_count"] == 2
        and not managed["unlink_adapter_has_commit_signal"],
        "runtime_claim_limits": not managed["generic_save_command_exact_table_mutation_semantics_proven"]
        and not managed["branch_specific_commit_and_rollback_reachability_proven"],
        "r072_registered_and_caveated": r072["severity"] == "HIGH"
        and "Current snapshot parity remains clean" in r072["failure_mode"]
        and "not attributed to unlink" in r072["failure_mode"],
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
        "artifact": "varanegar_supplier_unapply_delete_checkpoint_20260829",
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
            "business_rows_configuration_values_or_identifiers_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "selected_sql_module_count": sql["summary"]["selected_sql_module_count"],
            "retained_relation_delete_count": sql["summary"]["retained_relation_delete_event_count"],
            "recent_relation_delete_count": sql["summary"]["recent_relation_delete_event_count"],
            "current_relation_count": sql["summary"]["current_relation_count"],
            "unapplied_multi_receipt_invoice_count": sql["summary"]["unapplied_multi_receipt_invoice_count"],
            "applied_multi_receipt_invoice_count": sql["summary"]["applied_multi_receipt_invoice_count"],
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
