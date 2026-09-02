import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/received_cheque_delete_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/received_cheque_delete_runtime_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_received_cheque_delete_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_evidence_is_read_only_and_redacted():
    payload = _load(SQL)
    assert payload["validation"] == "PASS"
    safety = payload["safety"]
    assert safety["database_updateability"] == "READ_ONLY"
    assert safety["can_update"] == 0
    assert safety["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert safety[
        "cheque_receipt_customer_amount_bank_comment_operator_or_log_script_values_persisted"
    ] == 0
    assert safety["sql_definitions_or_log_ids_persisted"] == 0
    raw = SQL.read_text(encoding="utf-8")
    assert re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        raw,
    ) is None
    assert re.search(r"(?i)(password|pwd)\s*[=:]", raw) is None


def test_static_delete_routes_have_distinct_transaction_and_cleanup_contracts():
    payload = _load(SQL)
    assert payload["summary"]["selected_sql_module_count"] == 10
    assert payload["summary"]["direct_master_delete_candidate_count"] == 7
    contract = payload["static_delete_contract"]
    assert contract["all_expected_direct_candidates_delete_master"]
    assert contract["usp_chq_delete_validates_then_owns_atomic_history_master_delete"]
    assert contract["view_delete_trigger_directly_deletes_master_without_history_or_receipt"]
    assert contract["receipt_save_owns_transaction_or_savepoint"]
    assert contract["receipt_save_has_history_master_receipt_delete_sequence"]
    assert contract["receipt_save_calls_before_rcheque"]


def test_retained_master_log_is_exactly_reconciled_to_current_absence():
    payload = _load(SQL)
    summary = payload["summary"]
    coverage = payload["retained_master_lifecycle_log"]["logged_id_coverage"]
    assert summary["retained_master_delete_event_count"] == 31
    assert summary["recent_master_delete_event_count"] == 11
    assert summary["logged_master_current_absence_mismatch_count"] == 0
    assert coverage == {
        "logged_id_count": 8261,
        "currently_present_count": 8230,
        "currently_absent_count": 31,
        "both_event_count": 31,
        "delete_only_count": 0,
        "insert_only_but_absent_count": 0,
        "deleted_but_present_count": 0,
    }


def test_master_delete_tails_remain_three_distinct_evidence_states():
    summary = _load(SQL)["summary"]
    assert summary["receipt_delete_tail_master_count"] == 23
    assert summary["receipt_update_tail_master_count"] == 7
    assert summary["isolated_tail_master_count"] == 1
    assert summary["master_delete_without_history_lookback_count"] == 0
    assert summary["master_delete_immediately_preceded_by_history_delete_count"] == 27
    assert 23 + 7 + 1 == summary["retained_master_delete_event_count"]


def test_receipt_delete_batches_preserve_master_history_cardinality():
    payload = _load(SQL)
    summary = payload["summary"]
    assert summary["retained_receipt_delete_event_count"] == 2351
    assert summary["recent_receipt_delete_event_count"] == 238
    assert summary["receipt_delete_batch_count"] == 19
    assert summary["receipt_delete_tail_master_count"] == 23
    assert summary["receipt_delete_tail_history_count"] == 23
    rows = payload["receipt_delete_batches_with_master_cleanup"]
    assert sum(row["receipt_delete_batch_count"] for row in rows) == 19
    assert sum(
        row["master_delete_count"] * row["receipt_delete_batch_count"] for row in rows
    ) == 23
    assert sum(
        row["history_delete_count"] * row["receipt_delete_batch_count"] for row in rows
    ) == 23


def test_storage_has_no_temporal_audit_and_mixed_fk_delete_actions():
    storage = _load(SQL)["storage_contract"]
    assert len(storage["table_capabilities"]) == 5
    assert all(
        row["temporal_type_desc"] == "NON_TEMPORAL_TABLE"
        and not row["is_tracked_by_cdc"]
        and row["change_tracking_enabled"] == 0
        for row in storage["table_capabilities"]
    )
    actions = {row["delete_referential_action_desc"] for row in storage["incoming_foreign_keys"]}
    assert actions == {"NO_ACTION", "CASCADE"}
    cascade_children = {
        row["child_table"]
        for row in storage["incoming_foreign_keys"]
        if row["delete_referential_action_desc"] == "CASCADE"
    }
    assert "tblRChequeLog" in cascade_children
    assert "TblCheque" in cascade_children


def test_runtime_forms_have_asymmetric_delete_implementation_and_preserved_limits():
    payload = _load(RUNTIME)
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 1,
        "selected_method_count": 2,
        "selected_instruction_count": 34,
        "source_hash_mismatch_count": 0,
        "method_or_coverage_error_count": 0,
    }
    contract = payload["managed_delete_contract"]
    assert contract["legacy_delete_has_confirmation"]
    assert contract["legacy_delete_marks_dataset_row_deleted"]
    assert contract["legacy_delete_flushes_rcheque_dataset"]
    assert contract["legacy_confirmation_precedes_row_delete_and_update_in_linear_il"]
    assert not contract["legacy_delete_has_explicit_transaction_signal"]
    assert contract["new_delete_has_confirmation"]
    assert not contract["new_delete_has_dataset_delete_or_update_signal"]
    assert not contract["runtime_form_selection_proven"]
    assert not contract["dataset_update_to_sql_trigger_branch_reachability_proven"]


def test_r075_and_traceability_are_registered_with_causal_limits():
    risks = _load(RISKS)
    trace = _load(TRACE)
    assert risks["summary"]["risk_count"] == 84
    assert risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    risk = next(row for row in risks["risks"] if row["id"] == "R-075")
    assert risk["severity"] == "HIGH"
    assert "not proving its invocation" in risk["failure_mode"]
    assert "attribution must not be fabricated" in risk["failure_mode"]
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_checkpoint_is_complete_and_current():
    checkpoint = _load(CHECKPOINT)
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"]["risk_count"] == 84
    assert checkpoint["summary"]["mapped_risk_assignment_count"] == 343
