from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/supplier_unapply_delete_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/supplier_unapply_delete_runtime_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_supplier_unapply_delete_checkpoint_20260829.json"
GUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_unapply_sql_boundary_is_read_only_and_redacted():
    payload = _load(SQL)
    assert payload["artifact"] == "varanegar_supplier_unapply_delete_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] == 1
    assert payload["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert payload["safety"]["business_rows_identifiers_amounts_prices_or_operator_values_persisted"] == 0
    raw = SQL.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"definition"' not in raw
    assert "OperationScript" not in raw


def test_unlink_marks_header_before_zeroing_selected_voucher_price():
    payload = _load(SQL)
    assert payload["summary"]["selected_sql_module_count"] == 8
    assert payload["summary"]["selected_module_with_local_transaction_count"] == 3
    assert payload["unlink_reverse_contract"] == {
        "unlink_sets_whole_invoice_status_zero": True,
        "unlink_clears_whole_invoice_confirm_date": True,
        "unlink_zeros_selected_voucher_item_price_and_unit_price": True,
        "status_zero_precedes_price_zero": True,
        "unlink_reads_purchase_final_date": True,
        "unlink_reads_last_closed_purchase_date": True,
        "unlink_raises_domain_error": True,
        "unlink_has_application_specific_rollback_branch": True,
        "unlink_owns_local_transaction": False,
    }


def test_current_n_to_m_state_and_status_price_parity_are_clean():
    payload = _load(SQL)
    states = {row["Status"]: row for row in payload["invoice_relation_state"]}
    assert states[0] == {
        "Status": 0,
        "header_count": 141,
        "no_relation_count": 0,
        "one_relation_count": 124,
        "multi_relation_count": 17,
        "max_relation_count": 3,
        "confirm_null_count": 141,
        "confirm_present_count": 0,
    }
    assert states[1]["header_count"] == 3285
    assert states[1]["multi_relation_count"] == 192
    assert states[1]["max_relation_count"] == 7
    prices = {row["Status"]: row for row in payload["voucher_item_price_state"]["related_items_by_invoice_status"]}
    assert prices[0]["price_present_count"] == 0
    assert prices[0]["price_absent_count"] == 1354
    assert prices[1]["price_present_count"] == 29078
    assert prices[1]["price_absent_count"] == 0
    assert payload["voucher_item_price_state"]["all_price_rows"]["both_zero_count"] == 83


def test_relation_log_is_active_and_last_event_exactly_projects_current_state():
    payload = _load(SQL)
    assert payload["summary"]["retained_relation_insert_event_count"] == 3902
    assert payload["summary"]["retained_relation_delete_event_count"] == 213
    assert payload["summary"]["recent_relation_delete_event_count"] == 15
    lifecycle = payload["retained_relation_lifecycle_log"]["lifecycle"]
    assert lifecycle == {
        "logged_id_count": 3892,
        "currently_present_count": 3689,
        "currently_absent_count": 203,
        "multi_insert_id_count": 8,
        "multi_delete_id_count": 6,
        "both_event_id_count": 207,
        "deleted_but_currently_present_count": 4,
        "insert_only_but_currently_absent_count": 0,
    }
    assert payload["retained_relation_lifecycle_log"]["last_event_projection"] == [
        {"last_event": "DELETE", "current_present": 0, "relation_id_count": 203},
        {"last_event": "INSERT", "current_present": 1, "relation_id_count": 3689},
    ]


def test_dependencies_and_storage_audit_gap_remain_explicit():
    payload = _load(SQL)
    assert payload["current_dependency_state"]["settlement"] == {
        "settlement_count": 2,
        "applied_invoice_settlement_count": 2,
        "unapplied_invoice_settlement_count": 0,
    }
    assert payload["current_dependency_state"]["return_source_by_invoice_status"] == [
        {"Status": 0, "return_header_count": 1, "source_invoice_count": 1},
        {"Status": 1, "return_header_count": 26, "source_invoice_count": 11},
    ]
    storage = payload["storage_guard_contract"]
    assert len(storage["table_capabilities"]) == 3
    assert all(row["temporal_type_desc"] == "NON_TEMPORAL_TABLE" for row in storage["table_capabilities"])
    assert all(not row["is_tracked_by_cdc"] for row in storage["table_capabilities"])
    assert len(storage["active_triggers"]) == 4
    assert len(storage["foreign_keys"]) == 3
    assert all(row["is_not_trusted"] for row in storage["foreign_keys"])


def test_managed_runtime_boundary_is_hash_pinned_and_caveated():
    payload = _load(RUNTIME)
    assert payload["artifact"] == "varanegar_supplier_unapply_delete_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 3,
        "selected_method_count": 4,
        "selected_instruction_count": 369,
        "source_hash_mismatch_count": 0,
        "method_or_coverage_error_count": 0,
    }
    assert all(row["inventory_sha256_match"] for row in payload["source"])
    assert payload["safety"]["assembly_loads_or_executions"] == 0
    assert payload["safety"]["database_connections"] == 0
    assert payload["safety"]["raw_string_or_sql_literals_persisted"] == 0
    assert not GUID.search(RUNTIME.read_text(encoding="utf-8"))
    contract = payload["managed_unlink_delete_contract"]
    assert contract["list_delete_checks_last_closed_purchase_date"] is True
    assert contract["list_delete_generic_save_precedes_commit_in_linear_il"] is True
    assert contract["list_delete_has_settlement_diagnostic_signal"] is True
    assert contract["unlink_relation_save_precedes_operation_call"] is True
    assert contract["unlink_operation_code_three_precedes_operation_call"] is True
    assert contract["unlink_operation_call_precedes_commit_in_linear_il"] is True
    assert contract["unlink_adapter_data_context_execute_call_count"] == 2
    assert contract["unlink_adapter_has_commit_signal"] is False
    assert contract["generic_save_command_exact_table_mutation_semantics_proven"] is False


def test_r072_is_high_and_does_not_claim_current_incident_or_zero_price_cause():
    risks = _load(RISKS)
    row = next(item for item in risks["risks"] if item["id"] == "R-072")
    assert row["severity"] == "HIGH"
    assert "Current snapshot parity remains clean" in row["failure_mode"]
    assert "not attributed to unlink" in row["failure_mode"]
    assert risks["summary"] == {
        "risk_count": 84,
        "critical_count": 50,
        "high_count": 31,
        "medium_count": 3,
        "open_count": 84,
        "covered_module_count": 14,
        "risk_with_exit_criteria_count": 84,
        "validation_error_count": 0,
    }
    trace = _load(TRACE)
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_unapply_checkpoint_hashes_sources_and_passes_all_gates():
    payload = _load(CHECKPOINT)
    assert payload["artifact"] == "varanegar_supplier_unapply_delete_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 16,
        "passed_check_count": 17,
        "failed_check_count": 0,
        "selected_sql_module_count": 8,
        "retained_relation_delete_count": 213,
        "recent_relation_delete_count": 15,
        "current_relation_count": 3689,
        "unapplied_multi_receipt_invoice_count": 17,
        "applied_multi_receipt_invoice_count": 192,
        "runtime_selected_method_count": 4,
        "risk_count": 84,
        "critical_risk_count": 50,
        "high_risk_count": 31,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
