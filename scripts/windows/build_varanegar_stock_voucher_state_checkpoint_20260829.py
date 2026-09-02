"""Build the offline stock-voucher confirm/unconfirm/delete state checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/stock_voucher_state_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/stock_voucher_state_runtime_boundary_20260829.json",
    "inventory_boundary": "artifacts/varanegar_analysis/domains/inventory_reservation_and_exit_20260826.json",
    "stock_reconciliation": "artifacts/varanegar_analysis/ui/varanegar_stock_reconciliation_diagnostic_contract_20260827.json",
    "stock_command_contract": "artifacts/varanegar_analysis/ui/varanegar_stock_voucher_command_contract_20260827.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_received_cheque_delete_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_stock_voucher_state_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_stock_voucher_state_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_stock_voucher_state_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_stock_voucher_state_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/STOCK_VOUCHER_CONFIRM_UNCONFIRM_DELETE_STATE_BOUNDARY_20260829_FA.md",
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
    inventory = _load("inventory_boundary")
    stock_reconciliation = _load("stock_reconciliation")
    previous = _load("previous_checkpoint")
    risks = _load("risk_register")
    trace = _load("traceability")
    static = sql["static_state_contract"]
    managed = runtime["managed_state_contract"]
    audit = sql["domain_audit"]
    coverage = audit["logged_voucher_coverage"]
    transitions = {
        row["transition_shape"]: (row["event_count"], row["recent_three_month_event_count"])
        for row in audit["derived_transition_counts"]
    }
    lifecycle = {
        row["delete_shape"]: (row["delete_count"], row["recent_three_month_count"])
        for row in audit["delete_lifecycle_counts"]
    }
    cardex_only = inventory["balance_reconciliation"]
    official_reconciliation = stock_reconciliation["official_legacy_formula_reconciliation"]["overview"]
    r076 = next(row for row in risks["risks"] if row["id"] == "R-076")
    raw = (ROOT / SOURCES["sql_boundary"]).read_text(encoding="utf-8") + (
        ROOT / SOURCES["runtime_boundary"]
    ).read_text(encoding="utf-8")
    checks = {
        "sql_read_only_and_redacted": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
        and sql["safety"]["voucher_goods_stock_supplier_document_comment_user_host_or_log_row_values_persisted"] == 0
        and sql["safety"]["sql_definitions_or_business_identifiers_persisted"] == 0,
        "static_confirm_contract": static["confirm_validates_before_transaction"]
        and static["confirm_uses_cursor_transaction_or_savepoint"]
        and static["confirm_commits_header_before_after_hook_without_ambient_transaction"]
        and static["save_wraps_confirm_in_outer_transaction"],
        "static_unconfirm_contract": static["unconfirm_validates_before_transaction"]
        and static["unconfirm_owns_transaction_and_rollback"]
        and static["unconfirm_deletes_linked_detail_item_header"]
        and static["unconfirm_after_hook_precedes_commit"],
        "trigger_projection_contract": static["header_trigger_projects_confirm_transition_with_special_type_skips"]
        and static["item_trigger_projects_confirmed_item_mutations"]
        and static["projection_triggers_have_replication_bypass_and_xact_abort_off"],
        "current_state_partition": sql["summary"]["current_voucher_count"] == 96502
        and sql["summary"]["current_confirmed_voucher_count"] == 96495
        and sql["summary"]["current_unconfirmed_voucher_count"] == 7,
        "retained_transition_counts": transitions["CONFIRM"] == (75569, 8822)
        and transitions["UNCONFIRM"] == (13021, 1771)
        and transitions["D"] == (27450, 3200),
        "delete_lifecycle_partition": lifecycle["IMMEDIATE_UNCONFIRM_DELETE"] == (10169, 1454)
        and lifecycle["PRIOR_UNCONFIRM_DELETE"] == (289, 24)
        and lifecycle["NEVER_CONFIRMED_DELETE"] == (16992, 1722)
        and sql["summary"]["direct_confirmed_delete_without_unconfirm_count"] == 0,
        "audit_coverage_and_historical_gap": coverage["logged_voucher_count"] == 123967
        and coverage["currently_present_count"] == 96502
        and coverage["both_event_count"] == 27450
        and coverage["insert_only_but_absent_count"] == 15
        and coverage["deleted_but_present_count"] == 0
        and audit["insert_logged_absent_without_delete_batch"]["recent_three_month_count"] == 0,
        "storage_non_temporal": len(sql["storage_contract"]["table_capabilities"]) == 5
        and all(
            row["temporal_type_desc"] == "NON_TEMPORAL_TABLE"
            and not row["is_tracked_by_cdc"]
            and row["change_tracking_enabled"] == 0
            for row in sql["storage_contract"]["table_capabilities"]
        ),
        "runtime_hash_and_coverage": runtime["validation"] == "PASS"
        and runtime["summary"]["assembly_count"] == 2
        and runtime["summary"]["selected_method_count"] == 12
        and runtime["summary"]["selected_instruction_count"] == 596
        and runtime["summary"]["source_hash_mismatch_count"] == 0,
        "managed_route_separation": managed["main_confirm_has_separate_validation_and_writer_overloads"]
        and managed["main_writer_calls_direct_update_routes_before_commit"]
        and managed["main_writer_has_no_adapter_confirm_or_unconfirm_call"]
        and managed["thin_business_confirm_and_unconfirm_delegate_to_adapter"]
        and managed["adapter_confirm_executes_named_procedure_then_commits"]
        and managed["adapter_unconfirm_executes_named_procedure_then_commits"],
        "managed_limits_preserved": not managed["main_writer_runtime_callsite_and_branch_selection_proven"]
        and not managed["physical_transaction_enlistment_across_dynamic_and_adapter_routes_proven"],
        "official_reconciliation_preserved_without_false_mismatch": cardex_only["healthy_onhand"]["mismatch"] == 1594
        and cardex_only["damaged"]["mismatch"] == 0
        and cardex_only["reserved"]["mismatch"] == 0
        and stock_reconciliation["summary"]["official_formula_mismatch_count"] == 0
        and official_reconciliation["mismatch"] == 0
        and official_reconciliation["obligation_keys"] == 1594
        and official_reconciliation["absolute_obligation"] == "104470",
        "previous_checkpoint_chain": previous["validation"] == "PASS"
        and previous["summary"]["risk_count"] == 84,
        "r076_registered_and_caveated": r076["severity"] == "CRITICAL"
        and "physical transaction enlistment" in r076["failure_mode"]
        and "do not prove route safety" in r076["failure_mode"],
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
        "artifact": "varanegar_stock_voucher_state_checkpoint_20260829",
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
            "voucher_goods_stock_supplier_document_user_host_or_log_row_values_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "current_voucher_count": sql["summary"]["current_voucher_count"],
            "retained_confirm_transition_count": sql["summary"]["retained_confirm_transition_count"],
            "retained_unconfirm_transition_count": sql["summary"]["retained_unconfirm_transition_count"],
            "retained_delete_count": sql["summary"]["retained_delete_count"],
            "cardex_only_difference_count": cardex_only["healthy_onhand"]["mismatch"],
            "open_sale_obligation_key_count": official_reconciliation["obligation_keys"],
            "official_formula_residual_count": official_reconciliation["mismatch"],
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
