import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/stock_voucher_state_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/stock_voucher_state_runtime_boundary_20260829.json"
INVENTORY = ROOT / "artifacts/varanegar_analysis/domains/inventory_reservation_and_exit_20260826.json"
RECONCILIATION = ROOT / "artifacts/varanegar_analysis/ui/varanegar_stock_reconciliation_diagnostic_contract_20260827.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_stock_voucher_state_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_and_runtime_evidence_are_read_only_redacted_and_hash_pinned():
    sql = _load(SQL)
    runtime = _load(RUNTIME)
    assert sql["validation"] == runtime["validation"] == "PASS"
    assert sql["safety"]["database_updateability"] == "READ_ONLY"
    assert sql["safety"]["can_update"] == 0
    assert sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert sql["safety"]["voucher_goods_stock_supplier_document_comment_user_host_or_log_row_values_persisted"] == 0
    assert sql["safety"]["sql_definitions_or_business_identifiers_persisted"] == 0
    assert runtime["safety"]["assembly_loads_or_executions"] == 0
    assert runtime["safety"]["application_endpoint_form_or_command_executions"] == 0
    assert runtime["summary"]["source_hash_mismatch_count"] == 0
    raw = SQL.read_text(encoding="utf-8") + RUNTIME.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_static_confirm_and_unconfirm_have_route_dependent_transaction_contracts():
    payload = _load(SQL)
    assert payload["summary"]["selected_sql_module_count"] == 10
    contract = payload["static_state_contract"]
    assert contract["confirm_validates_before_transaction"]
    assert contract["confirm_uses_cursor_transaction_or_savepoint"]
    assert contract["confirm_commits_header_before_after_hook_without_ambient_transaction"]
    assert contract["save_wraps_confirm_in_outer_transaction"]
    assert contract["unconfirm_validates_before_transaction"]
    assert contract["unconfirm_owns_transaction_and_rollback"]
    assert contract["unconfirm_deletes_linked_detail_item_header"]
    assert contract["unconfirm_after_hook_precedes_commit"]


def test_stock_projection_is_trigger_owned_with_explicit_special_route_signals():
    payload = _load(SQL)
    contract = payload["static_state_contract"]
    assert contract["header_trigger_projects_confirm_transition_with_special_type_skips"]
    assert contract["item_trigger_projects_confirmed_item_mutations"]
    assert contract["projection_triggers_have_replication_bypass_and_xact_abort_off"]
    assert contract["domain_audit_triggers_cover_insert_update_delete"]
    assert contract["audit_iu_has_confirmed_voucher_date_suppression"]
    assert len(payload["storage_contract"]["table_capabilities"]) == 5
    assert all(
        row["temporal_type_desc"] == "NON_TEMPORAL_TABLE"
        and not row["is_tracked_by_cdc"]
        and row["change_tracking_enabled"] == 0
        for row in payload["storage_contract"]["table_capabilities"]
    )


def test_current_voucher_snapshot_has_exact_confirmed_partition():
    payload = _load(SQL)
    assert payload["summary"]["current_voucher_count"] == 96502
    assert payload["summary"]["current_confirmed_voucher_count"] == 96495
    assert payload["summary"]["current_unconfirmed_voucher_count"] == 7
    aggregate = payload["current_state"]["aggregate"]
    assert aggregate["confirmed_count"] + aggregate["unconfirmed_count"] == aggregate["voucher_count"]


def test_retained_audit_reconstructs_confirm_unconfirm_and_delete_counts():
    payload = _load(SQL)
    transitions = {
        row["transition_shape"]: (row["event_count"], row["recent_three_month_event_count"])
        for row in payload["domain_audit"]["derived_transition_counts"]
    }
    assert transitions["CONFIRM"] == (75569, 8822)
    assert transitions["UNCONFIRM"] == (13021, 1771)
    assert transitions["D"] == (27450, 3200)
    assert transitions["DRAFT_UPDATE"] == (17777, 1810)
    assert transitions["CONFIRMED_UPDATE"] == (46688, 4193)


def test_delete_lifecycle_has_no_retained_direct_confirmed_delete():
    payload = _load(SQL)
    lifecycle = {
        row["delete_shape"]: (row["delete_count"], row["recent_three_month_count"])
        for row in payload["domain_audit"]["delete_lifecycle_counts"]
    }
    assert lifecycle == {
        "IMMEDIATE_UNCONFIRM_DELETE": (10169, 1454),
        "NEVER_CONFIRMED_DELETE": (16992, 1722),
        "PRIOR_UNCONFIRM_DELETE": (289, 24),
    }
    assert 10169 + 289 == payload["summary"]["deleted_after_any_unconfirm_count"]
    assert 10169 + 289 + 16992 == payload["summary"]["retained_delete_count"]
    assert payload["summary"]["direct_confirmed_delete_without_unconfirm_count"] == 0


def test_audit_coverage_keeps_historical_gaps_and_type_patterns_separate():
    payload = _load(SQL)
    coverage = payload["domain_audit"]["logged_voucher_coverage"]
    assert coverage == {
        "logged_voucher_count": 123967,
        "currently_present_count": 96502,
        "currently_absent_count": 27465,
        "both_event_count": 27450,
        "delete_only_count": 0,
        "insert_only_but_absent_count": 15,
        "deleted_but_present_count": 0,
    }
    gap = payload["domain_audit"]["insert_logged_absent_without_delete_batch"]
    assert gap["insert_logged_absent_without_delete_count"] == 15
    assert gap["recent_three_month_count"] == 0
    patterns = {
        (row["VocherTypeCode"], row["transition_shape"]): (
            row["event_count"], row["recent_three_month_count"]
        )
        for row in payload["domain_audit"]["recent_activity_by_voucher_type"]
    }
    assert patterns[(60, "D")] == patterns[(60, "UNCONFIRM")] == (9917, 1442)
    assert patterns[(12, "D")] == (16764, 1682)


def test_managed_routes_are_distinct_and_preserve_unproven_runtime_limits():
    payload = _load(RUNTIME)
    assert payload["summary"] == {
        "assembly_count": 2,
        "selected_method_count": 12,
        "selected_instruction_count": 596,
        "main_confirm_overload_count": 2,
        "source_hash_mismatch_count": 0,
        "method_or_coverage_error_count": 0,
    }
    contract = payload["managed_state_contract"]
    assert contract["main_confirm_has_separate_validation_and_writer_overloads"]
    assert contract["main_validator_checks_cardex_onhand_and_projection"]
    assert contract["main_writer_calls_direct_update_routes_before_commit"]
    assert contract["main_writer_has_no_adapter_confirm_or_unconfirm_call"]
    assert contract["direct_update_method_uses_dynamic_header_sql_without_local_commit"]
    assert contract["thin_business_confirm_and_unconfirm_delegate_to_adapter"]
    assert contract["adapter_confirm_executes_named_procedure_then_commits"]
    assert contract["adapter_unconfirm_executes_named_procedure_then_commits"]
    assert contract["selected_methods_have_no_explicit_rollback_signal"]
    assert not contract["main_writer_runtime_callsite_and_branch_selection_proven"]
    assert not contract["physical_transaction_enlistment_across_dynamic_and_adapter_routes_proven"]


def test_r076_traceability_reconciliation_and_checkpoint_are_current():
    risks = _load(RISKS)
    trace = _load(TRACE)
    inventory = _load(INVENTORY)["balance_reconciliation"]
    reconciliation = _load(RECONCILIATION)
    checkpoint = _load(CHECKPOINT)
    assert risks["summary"]["risk_count"] == 84
    assert risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    risk = next(row for row in risks["risks"] if row["id"] == "R-076")
    assert risk["severity"] == "CRITICAL"
    assert "physical transaction enlistment" in risk["failure_mode"]
    assert "do not prove route safety" in risk["failure_mode"]
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0
    assert inventory["healthy_onhand"]["mismatch"] == 1594
    assert inventory["damaged"]["mismatch"] == 0
    assert inventory["reserved"]["mismatch"] == 0
    assert reconciliation["summary"]["cardex_only_mismatch_count"] == 1594
    assert reconciliation["summary"]["official_formula_mismatch_count"] == 0
    assert reconciliation["official_legacy_formula_reconciliation"]["overview"]["obligation_keys"] == 1594
    assert reconciliation["official_legacy_formula_reconciliation"]["overview"]["absolute_obligation"] == "104470"
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"]["risk_count"] == 84
    assert checkpoint["summary"]["mapped_risk_assignment_count"] == 343
