import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/sale_conversion_state_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/sale_conversion_runtime_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_sale_conversion_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_boundary_is_read_only_redacted_and_hash_pinned():
    payload = _load(SQL)
    assert payload["validation"] == "PASS"
    safety = payload["safety"]
    assert safety["database_updateability"] == "READ_ONLY"
    assert safety["can_update"] == 0
    assert safety["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert safety["order_sale_customer_goods_user_host_or_raw_log_values_persisted"] == 0
    assert safety["sql_definitions_error_texts_or_business_identifiers_persisted"] == 0
    assert len(payload["sql_module_profiles"]) == 7
    assert all(len(row["definition_sha256"]) == 64 for row in payload["sql_module_profiles"])
    raw = SQL.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_sql_orchestrator_core_and_trigger_ownership_are_explicit():
    contract = _load(SQL)["static_conversion_and_projection_contract"]
    assert contract["orchestrator_has_with_out_rollback_parameter_and_branches"]
    assert contract["orchestrator_has_local_transaction_try_catch_commit_and_rollback"]
    assert contract["orchestrator_calls_core_before_order_selected_sale_pointer_update"]
    assert contract["orchestrator_writes_conversion_timing_and_order_sale_pointer"]
    assert contract["orchestrator_mutates_payment_batch_reserved_prize_and_item_detail"]
    assert contract["orchestrator_contains_dynamic_sql"]
    assert contract["core_has_no_local_transaction"]
    assert contract["core_inserts_sale_header_and_items"]
    assert contract["detail_trigger_inserts_sale_detail_on_header_change"]
    assert contract["cancel_trigger_deletes_payment_on_cancel_flag_change"]
    assert contract["stock_trigger_mutates_stock_goods_from_sale_header"]
    assert contract["current_replication_delete_trigger_is_bypassable"]


def test_current_order_sale_attempt_invariants_preserve_multi_version_semantics():
    payload = _load(SQL)
    population = payload["current_sale_state"]["population"]
    assert population["sale_count"] == 275995
    assert population["active_count"] == 214973
    assert population["cancelled_count"] == 61022
    assert population["recent_sale_date_count"] == 40059
    assert population["recent_cancelled_count"] == 7702
    relation = payload["current_sale_state"]["order_relationship"]
    assert relation["multi_attempt_order_count"] == 18009
    assert relation["multi_active_attempt_order_count"] == 0
    assert relation["order_without_selected_sale_count"] == 4561
    assert relation["selected_pointer_missing_count"] == 0
    assert relation["selected_reverse_mismatch_count"] == 0
    assert relation["selected_cancelled_count"] == 34630


def test_detail_projection_separates_expected_cancel_shape_from_real_exceptions():
    payload = _load(SQL)
    overview = payload["sale_detail_projection"]["overview"]
    assert overview["detail_count"] == 540888
    assert overview["sale_count"] == 275995
    assert overview["absent_sale_count"] == 0
    assert overview["latest_status_mismatch_count"] == 26624
    assert overview["cancelled_header_expected_terminal_detail_count"] == 61019
    assert overview["cancelled_header_status0_detail_count"] == 26612
    assert overview["cancelled_header_status3_detail_count"] == 34407
    assert overview["active_header_latest_status_mismatch_count"] == 6
    assert overview["cancelled_header_unexpected_latest_status_count"] == 3
    assert payload["summary"]["recent_projection_exception_count"] == 0


def test_timing_is_incomplete_attempt_evidence_and_not_an_idempotency_ledger():
    timing = _load(SQL)["conversion_attempt_timing_reconciliation"]
    assert timing == {
        "order_count": 254173,
        "equal_attempt_count_order_count": 244353,
        "more_sale_than_timing_order_count": 9811,
        "more_timing_than_sale_order_count": 9,
        "sale_attempt_count": 275995,
        "timed_attempt_count": 266202,
        "sale_order_without_timing_count": 9809,
        "timing_order_without_sale_count": 9,
    }


def test_physical_delete_audit_and_unlogged_historical_gap_remain_distinct():
    payload = _load(SQL)
    operations = {row["OperationType"]: row for row in payload["generic_sale_log_lifecycle"]["operation_counts"]}
    assert operations["DELETE"]["event_count"] == 640
    assert operations["DELETE"]["id_count"] == 640
    assert operations["DELETE"]["recent_event_count"] == 112
    coverage = payload["generic_sale_log_lifecycle"]["logged_id_coverage"]
    assert coverage["logged_sale_count"] == 276653
    assert coverage["current_count"] == 275995
    assert coverage["absent_count"] == 658
    assert coverage["absent_with_delete_count"] == 640
    assert coverage["absent_without_delete_count"] == 18
    assert coverage["recent_absent_without_delete_count"] == 0
    candidates = payload["direct_physical_sale_delete_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["qualified_name"] == "SLE.usp_sdsnet_ConfirmFreeInvoice"
    assert candidates[0]["begin_transaction_signal_count"] == 1
    assert any("not attribution" in limit for limit in payload["evidence_limits"])


def test_runtime_route_is_hash_pinned_and_preserves_nested_transaction_limits():
    payload = _load(RUNTIME)
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 3,
        "selected_method_count": 5,
        "selected_instruction_count": 1055,
        "order_business_create_overload_count": 2,
        "source_hash_mismatch_count": 0,
        "method_or_coverage_error_count": 0,
    }
    assert all(row["inventory_sha256_match"] for row in payload["source"])
    contract = payload["managed_conversion_contract"]
    assert contract["ui_save_delegates_without_explicit_context_commit_or_rollback"]
    assert contract["sale_business_constructs_context_calls_create_then_commits"]
    assert not contract["sale_business_has_explicit_rollback_signal"]
    assert contract["order_business_has_two_overloads_and_one_thin_adapter_delegate"]
    assert contract["adapter_uses_named_orchestrator_and_commits"]
    assert contract["selected_methods_have_nested_business_and_adapter_commit_signals"]
    assert contract["normal_ui_to_business_route_selection_proven"]
    assert not contract["with_out_rollback_runtime_value_and_branch_proven"]
    assert not contract["physical_transaction_enlistment_across_business_and_adapter_contexts_proven"]


def test_r079_traceability_and_checkpoint_are_current_and_caveated():
    risks = _load(RISKS)
    trace = _load(TRACE)
    checkpoint = _load(CHECKPOINT)
    assert risks["summary"]["risk_count"] == 84
    assert risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    risk = next(row for row in risks["risks"] if row["id"] == "R-079")
    assert risk["severity"] == "CRITICAL"
    assert "no current duplicate-active-sale or recent state-projection exception is asserted" in risk["failure_mode"]
    assert "do not prove attribution" in risk["failure_mode"]
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"]["risk_count"] == 84
    assert checkpoint["summary"]["mapped_risk_assignment_count"] == 343
