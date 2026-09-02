from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "artifacts/varanegar_analysis/domains/supplier_cost_apply_boundary_20260829.json"
RUNTIME_PATH = ROOT / "artifacts/varanegar_analysis/domains/supplier_cost_apply_runtime_boundary_20260829.json"
RISK_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT_PATH = ROOT / "artifacts/varanegar_analysis/varanegar_supplier_cost_apply_checkpoint_20260829.json"
GUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_boundary_is_read_only_and_redacted():
    payload = _load(SQL_PATH)
    assert payload["artifact"] == "varanegar_supplier_cost_apply_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] == 1
    assert payload["safety"]["stored_procedure_form_or_application_command_executions"] == 0
    assert payload["safety"]["business_rows_identifiers_amounts_or_prices_persisted"] == 0
    raw = SQL_PATH.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"definition"' not in raw


def test_core_sql_sequence_exposes_reapply_failure_window():
    payload = _load(SQL_PATH)
    assert payload["summary"]["core_apply_module_count"] == 5
    assert payload["summary"]["core_module_with_local_transaction_count"] == 0
    sequence = payload["apply_reapply_sequence_contract"]
    assert sequence == {
        "apply_deletes_then_inserts_price": True,
        "apply_updates_header_status": False,
        "fast_apply_deletes_then_inserts_price_then_sets_status": True,
        "reapply_sets_status_before_fast_apply": True,
        "sdsnet_wrapper_calls_apply": True,
        "core_local_transaction_count": 0,
    }
    callers = {row["qualified_name"]: row for row in payload["caller_module_profiles"]}
    assert callers["SLE.usp_CheckSupInvoice"]["calls_apply"] is True
    assert callers["SLE.usp_CheckSupInvoice"]["owns_explicit_transaction"] is False
    assert sum(row["owns_explicit_transaction"] for row in callers.values()) == 4


def test_current_snapshot_has_exact_status_price_parity():
    payload = _load(SQL_PATH)
    assert payload["summary"] == {
        "core_apply_module_count": 5,
        "core_module_with_local_transaction_count": 0,
        "applied_invoice_count": 3285,
        "unapplied_invoice_count": 141,
        "applied_related_item_count": 29078,
        "applied_item_without_price_count": 0,
        "unapplied_related_item_count": 1354,
        "unapplied_item_with_price_count": 0,
        "orphan_price_row_count": 95,
        "recent_three_month_confirm_count": 2110,
    }
    parity = {row["Status"]: row for row in payload["status_price_parity"]}
    assert parity[1]["item_with_price_count"] == parity[1]["distinct_item_count"] == 29078
    assert parity[1]["item_without_price_count"] == 0
    assert parity[0]["item_without_price_count"] == parity[0]["distinct_item_count"] == 1354
    assert parity[0]["item_with_price_count"] == 0
    assert payload["cross_status_item_contract"] == {
        "related_item_count": 30432,
        "cross_status_item_count": 0,
    }


def test_confirm_months_and_price_integrity_are_bounded_not_attributed():
    payload = _load(SQL_PATH)
    assert payload["confirm_monthly_counts"] == [
        {"month_bucket": "2025-07", "header_count": 1175},
        {"month_bucket": "2026-06", "header_count": 370},
        {"month_bucket": "2026-07", "header_count": 1740},
    ]
    price = payload["voucher_item_price_integrity"]
    assert price["price_row_count"] == price["distinct_price_id_count"] == 1419656
    assert price["orphan_price_row_count"] == 95
    assert price["unique_primary_key_on_item_id"] is True
    assert price["foreign_key_to_voucher_item_present"] is False
    assert any("not attributed" in row for row in payload["evidence_limits"])


def test_runtime_boundary_is_hash_pinned_static_il_only():
    payload = _load(RUNTIME_PATH)
    assert payload["artifact"] == "varanegar_supplier_cost_apply_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 2,
        "selected_method_count": 4,
        "selected_instruction_count": 464,
        "source_hash_mismatch_count": 0,
        "method_or_coverage_error_count": 0,
    }
    assert all(row["inventory_sha256_match"] for row in payload["source"])
    assert payload["safety"]["assembly_loads_or_executions"] == 0
    assert payload["safety"]["database_connections"] == 0
    assert payload["safety"]["raw_string_or_sql_literals_persisted"] == 0
    raw = RUNTIME_PATH.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert "ICA.usp_ReApplySupInvoice" not in raw


def test_runtime_distinguishes_reapply_gap_from_apply_commit_signal():
    contract = _load(RUNTIME_PATH)["managed_apply_reapply_contract"]
    assert contract == {
        "reapply_business_calls_adapter": True,
        "reapply_adapter_queries_allowlisted_reapply_procedure": True,
        "reapply_selected_path_has_data_context_commit_signal": False,
        "reapply_selected_path_has_begin_transaction_signal": False,
        "apply_business_calls_adapter": True,
        "apply_adapter_calls_data_context_execute": True,
        "apply_business_has_commit_signal": True,
        "apply_adapter_call_precedes_business_commit_in_linear_il": True,
        "managed_data_context_constructor_transaction_semantics_proven": False,
        "branch_specific_commit_reachability_proven": False,
    }


def test_r071_is_critical_but_does_not_claim_current_incident():
    risks = _load(RISK_PATH)
    row = next(item for item in risks["risks"] if item["id"] == "R-071")
    assert row["severity"] == "CRITICAL"
    assert "structural failure window" in row["failure_mode"]
    assert "not a current partial-apply incident" in row["failure_mode"]
    assert "cause is not attributed" in row["failure_mode"]
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
    trace = _load(TRACE_PATH)
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_supplier_cost_checkpoint_hashes_sources_and_passes_all_gates():
    payload = _load(CHECKPOINT_PATH)
    assert payload["artifact"] == "varanegar_supplier_cost_apply_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 16,
        "passed_check_count": 16,
        "failed_check_count": 0,
        "applied_invoice_count": 3285,
        "applied_related_item_count": 29078,
        "unapplied_invoice_count": 141,
        "unapplied_related_item_count": 1354,
        "orphan_price_row_count": 95,
        "runtime_selected_method_count": 4,
        "risk_count": 84,
        "critical_risk_count": 50,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 16
    assert all(len(row["sha256"]) == 64 for row in payload["source_manifest"])
