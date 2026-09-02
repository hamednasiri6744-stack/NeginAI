import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/distribution_exit_lifecycle_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/distribution_exit_runtime_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_distribution_exit_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_boundary_is_read_only_redacted_and_hash_pinned():
    payload = _load(SQL)
    assert payload["validation"] == "PASS"
    safety = payload["safety"]
    assert safety["database_updateability"] == "READ_ONLY"
    assert safety["can_update"] == 0
    assert safety["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert safety["distribution_exit_sale_voucher_reason_user_host_or_raw_log_values_persisted"] == 0
    assert safety["sql_definitions_operation_scripts_or_business_identifiers_persisted"] == 0
    assert len(payload["sql_module_profiles"]) == 10
    assert all(len(row["definition_sha256"]) == 64 for row in payload["sql_module_profiles"])
    raw = SQL.read_text(encoding="utf-8")
    assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", raw) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_current_exit_voucher_and_cancel_cleanup_are_exact():
    payload = _load(SQL)
    state = payload["current_exit_state"]
    assert state["population"] == {
        "exit_count": 33945,
        "cancelled_count": 9910,
        "active_count": 24035,
        "cancelled_without_date_count": 0,
        "active_with_cancel_date_count": 0,
    }
    assert state["active_dist_stock_uniqueness"]["duplicate_dist_stock_group_count"] == 0
    assert state["active_type60_crosswalk"] == {
        "active_exit_count": 24035,
        "type60_voucher_count": 24035,
        "matched_active_exit_count": 24035,
        "active_exit_without_type60_count": 0,
        "duplicate_type60_docref_group_count": 0,
    }
    assert state["cancelled_cleanup"]["lingering_type60_voucher_count"] == 0
    assert state["cancelled_cleanup"]["lingering_sale_link_count"] == 0
    assert state["cancelled_cleanup"]["retained_full_history_row_count"] == 233535


def test_cancel_to_type60_delete_reconciliation_is_complete_and_recently_adjacent():
    contract = _load(SQL)["cancelled_exit_to_type60_delete_reconciliation"]
    coverage = contract["type60_delete_coverage"]
    assert coverage["type60_delete_docref_count"] == 9917
    assert coverage["matched_cancelled_exit_count"] == 9910
    assert coverage["matched_active_exit_count"] == 0
    assert coverage["absent_exit_count"] == 7
    assert coverage["cancelled_within_5_seconds_count"] == 9895
    assert coverage["recent_matched_cancelled_count"] == 1442
    assert contract["cancelled_exit_coverage"]["without_type60_delete_log_count"] == 0
    buckets = {row["time_bucket"]: row for row in contract["cancel_to_voucher_delete_time_buckets"]}
    assert buckets["LE_1S"]["recent_count"] == 1438
    assert buckets["LE_5S"]["recent_count"] == 4


def test_historical_absence_is_pretrigger_and_not_misattributed():
    payload = _load(SQL)
    lifecycle = payload["generic_exit_log_lifecycle"]
    operations = {row["OperationType"]: row for row in lifecycle["operation_counts"]}
    assert operations["INSERT"]["event_count"] == 33953
    assert operations["UPDATE"]["event_count"] == 9922
    assert "DELETE" not in operations
    coverage = lifecycle["logged_id_coverage"]
    assert coverage["absent_count"] == 8
    assert coverage["recent_absent_count"] == 0
    assert coverage["absent_with_update_log_count"] == 7
    assert coverage["absent_without_update_log_count"] == 1
    assert payload["summary"]["historically_absent_distribution_count"] == 6
    assert payload["distribution_state_and_audit"]["status_chain"]["chain_break_count"] == 0
    assert any("before the current delete audit triggers" in limit for limit in payload["evidence_limits"])


def test_sql_issue_cancel_and_physical_delete_shapes_are_distinct():
    payload = _load(SQL)
    contract = payload["static_exit_contract"]
    assert contract["create_validates_before_first_exit_insert"]
    assert contract["create_has_no_local_transaction_or_savepoint"]
    assert contract["create_writes_exit_sale_type60_items_and_history"]
    assert contract["create_checks_cardex_after_voucher_items"]
    assert contract["remove_validates_before_soft_cancel"]
    assert contract["remove_has_no_local_begin_or_commit_but_has_catch_rollback"]
    assert contract["remove_deletes_voucher_graph_unlinks_sales_soft_cancels_exit_and_resets_dist"]
    assert contract["three_direct_physical_delete_candidates_are_separate_from_soft_cancel"]
    assert contract["only_vsa_direct_delete_candidate_has_local_transaction"]
    assert contract["current_delete_audit_triggers_are_active_and_replication_bypassable"]
    assert payload["direct_physical_exit_delete_candidates"] == [
        "dbo.DoPOrder_RollBackReplicatePOrder",
        "dbo.usp_RollBackSalesReceipt",
        "dbo.USP_VSA_ChangeDistStatus",
    ]


def test_runtime_boundary_is_static_hash_pinned_and_complete():
    payload = _load(RUNTIME)
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 3,
        "selected_method_count": 11,
        "selected_instruction_count": 1201,
        "source_hash_mismatch_count": 0,
        "method_or_coverage_error_count": 0,
    }
    assert all(row["inventory_sha256_match"] for row in payload["source"])
    safety = payload["safety"]
    assert safety["assembly_loads_or_executions"] == 0
    assert safety["database_connections"] == 0
    assert safety["raw_string_sql_or_identifier_literals_persisted"] == 0


def test_runtime_contract_preserves_transaction_ownership_limits():
    contract = _load(RUNTIME)["managed_exit_contract"]
    assert contract["business_methods_are_thin_adapter_delegates"]
    assert contract["create_adapter_queries_named_procedure_without_local_commit"]
    assert contract["remove_validation_adapter_queries_named_procedure_without_local_commit"]
    assert contract["remove_adapter_queries_named_procedure_without_local_commit"]
    assert contract["merge_adapter_executes_named_procedure_without_local_commit"]
    assert contract["normal_issue_ui_constructs_context_then_calls_create_then_commits"]
    assert contract["normal_remove_ui_validates_then_constructs_context_removes_and_commits"]
    assert contract["merge_ui_delegates_without_explicit_context_or_commit"]
    assert contract["selected_methods_have_no_explicit_rollback_signal"]
    assert contract["normal_ui_route_selection_proven_for_issue_and_remove"]
    assert not contract["physical_transaction_enlistment_across_ui_and_nested_adapter_contexts_proven"]
    assert not contract["alternate_direct_sql_callsite_selection_proven"]


def test_r078_traceability_and_checkpoint_are_current_and_caveated():
    risks = _load(RISKS)
    trace = _load(TRACE)
    checkpoint = _load(CHECKPOINT)
    assert risks["summary"]["risk_count"] == 84
    assert risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    risk = next(row for row in risks["risks"] if row["id"] == "R-078")
    assert risk["severity"] == "CRITICAL"
    assert "no current partial issue, cancellation, or unauthorized delete incident is asserted" in risk["failure_mode"]
    assert "physical enlistment" in risk["failure_mode"]
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"]["risk_count"] == 84
    assert checkpoint["summary"]["mapped_risk_assignment_count"] == 343
