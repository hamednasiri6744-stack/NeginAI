import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/sale_cancellation_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/sale_cancellation_runtime_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_sale_cancellation_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_cancellation_evidence_is_read_only_redacted_and_hash_pinned():
    payload = _load(SQL)
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert payload["safety"]["sale_order_payment_exit_customer_user_host_or_raw_values_persisted"] == 0
    assert len(payload["sql_module_profiles"]) == 5
    assert all(len(row["definition_sha256"]) == 64 for row in payload["sql_module_profiles"])
    raw = SQL.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_sql_owner_and_trigger_effects_are_explicit():
    contract = _load(SQL)["static_cancellation_contract"]
    assert contract["cancel_has_local_transaction_try_catch_commit_and_rollback"]
    assert contract["cancel_updates_sale_before_or_without_order_pointer_update"]
    assert contract["cancel_directly_references_sale_order_payment_and_detail_domains"]
    assert contract["cancel_has_no_direct_exit_or_distribution_dependency"]
    assert not contract["cancel_has_dynamic_sql_capability"]
    assert contract["ebtal_trigger_reacts_to_cancel_flag_and_updates_order_or_sale_state"]
    assert contract["payment_trigger_deletes_direct_sale_payments_on_cancel"]
    assert contract["detail_trigger_records_header_state_change"]
    assert contract["stock_trigger_updates_stock_projection_on_cancel_or_state_change"]


def test_cancelled_sales_have_no_retained_direct_payments_but_keep_state_links():
    payload = _load(SQL)
    assert payload["summary"]["cancelled_sale_count"] == 61022
    assert payload["summary"]["cancelled_sale_with_payment_count"] == 0
    assert payload["summary"]["cancelled_sale_with_exit_link_count"] == 34401
    assert payload["summary"]["cancelled_sale_with_dist_link_count"] == 34401
    assert payload["summary"]["cancelled_sale_selected_by_order_count"] == 34630
    assert payload["summary"]["cancelled_sale_selected_by_active_order_count"] == 34397
    cancelled = next(row for row in payload["current_sale_cancellation_links"]["by_cancel_flag"] if row["CancelFlag"] == 1)
    assert cancelled["sale_with_active_exit_count"] == 34401
    assert cancelled["sale_with_cancelled_exit_count"] == 0


def test_status_three_is_the_observed_exit_distribution_link_shape():
    rows = _load(SQL)["current_sale_cancellation_links"]["cancelled_by_status"]
    assert [(row["Status"], row["sale_count"]) for row in rows] == [(1, 324), (2, 26297), (3, 34401)]
    assert rows[0]["sale_with_exit_link_count"] == 0
    assert rows[1]["sale_with_exit_link_count"] == 0
    assert rows[2]["sale_with_exit_link_count"] == 34401
    assert rows[2]["sale_with_dist_link_count"] == 34401


def test_terminal_detail_projection_separates_recent_health_from_historical_exceptions():
    payload = _load(SQL)
    overview = payload["terminal_detail_projection"]["overview"]
    assert overview["cancelled_sale_count"] == 61022
    assert overview["terminal_status0_count"] == 26612
    assert overview["terminal_status3_count"] == 34407
    assert overview["unexpected_terminal_count"] == 3
    assert overview["recent_unexpected_terminal_count"] == 0
    assert overview["recent_terminal_count"] == 7286


def test_managed_route_is_hash_pinned_and_sql_local_transaction_remains_the_proven_owner():
    payload = _load(RUNTIME)
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 3,
        "selected_method_count": 4,
        "selected_instruction_count": 390,
        "source_hash_mismatch_count": 0,
        "method_or_coverage_error_count": 0,
    }
    assert all(row["inventory_sha256_match"] for row in payload["source"])
    contract = payload["managed_cancellation_contract"]
    assert contract["ui_cancel_collects_cancel_reason_before_business_call"]
    assert contract["ui_cancel_has_no_explicit_context_commit_or_rollback"]
    assert contract["business_is_thin_adapter_delegate_without_explicit_context"]
    assert contract["adapter_uses_named_cancel_procedure"]
    assert contract["adapter_constructs_context_and_queries_or_executes"]
    assert not contract["adapter_has_explicit_commit_signal"]
    assert not contract["adapter_has_explicit_rollback_signal"]
    assert not contract["physical_transaction_enlistment_between_managed_context_and_sql_local_transaction_proven"]


def test_r080_and_checkpoint_are_current_and_do_not_classify_retained_links_as_corruption():
    risks, trace, checkpoint = _load(RISKS), _load(TRACE), _load(CHECKPOINT)
    assert risks["summary"]["risk_count"] == 84
    assert risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    risk = next(row for row in risks["risks"] if row["id"] == "R-080")
    assert risk["severity"] == "CRITICAL"
    assert "state shape, not asserted corruption" in risk["failure_mode"]
    assert "No live failure or unauthorized cancellation is asserted" in risk["failure_mode"]
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"]["risk_count"] == 84
    assert checkpoint["summary"]["mapped_risk_assignment_count"] == 343
