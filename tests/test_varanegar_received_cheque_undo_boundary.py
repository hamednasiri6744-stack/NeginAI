import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/received_cheque_undo_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/received_cheque_undo_runtime_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_received_cheque_undo_checkpoint_20260829.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_evidence_is_read_only_and_redacted():
    payload = _load(SQL)
    assert payload["validation"] == "PASS"
    safety = payload["safety"]
    assert safety["database_updateability"] == "READ_ONLY"
    assert safety["can_update"] == 0
    assert safety["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert safety["cheque_history_bank_customer_amount_comment_or_operator_values_persisted"] == 0
    assert safety["sql_definitions_or_log_scripts_persisted"] == 0
    raw = SQL.read_text(encoding="utf-8")
    assert re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        raw,
    ) is None


def test_undo_is_destructive_variable_cardinality_and_trigger_projected():
    contract = _load(SQL)["undo_add_trigger_contract"]
    assert contract["undo_validates_before_transaction"]
    assert contract["undo_owns_transaction_and_rollback"]
    assert contract["undo_deletes_history_and_appends_no_compensating_event"]
    assert contract["undo_has_conditional_status_8_double_delete"]
    assert contract["delete_trigger_reactivates_previous_history"]
    assert contract["insert_trigger_deactivates_previous_history"]


def test_desktop_wrapper_and_bulk_route_are_distinct_transaction_boundaries():
    contract = _load(SQL)["undo_add_trigger_contract"]
    assert contract["desktop_undo_wrapper_calls_delete_last_history"]
    assert contract["desktop_undo_wrapper_owns_transaction_without_explicit_rollback"]
    assert contract["add_is_transactional_append_path"]
    assert contract["outer_change_status_calls_add_and_delete"]
    assert contract["outer_change_status_owns_transaction_or_savepoint"]


def test_current_projection_and_chain_are_clean_without_claiming_complete_audit():
    payload = _load(SQL)
    aggregate = payload["current_lifecycle"]["aggregate"]
    assert aggregate == {
        "cheque_count": 23822,
        "history_count": 106131,
        "without_history_count": 0,
        "current_count_mismatch": 0,
        "current_not_max_count": 0,
        "current_wrong_parent_count": 0,
        "min_history_count": 1,
        "max_history_count": 10,
    }
    assert all(value == 0 for value in payload["current_lifecycle"]["chain_integrity"].values())


def test_log_reconciles_command_count_double_delete_and_recent_activity():
    payload = _load(SQL)
    assert payload["summary"]["retained_history_delete_event_count"] == 14711
    assert payload["summary"]["undo_command_tail_count"] == 1502
    assert payload["summary"]["conditional_double_delete_command_count"] == 22
    assert payload["summary"]["undo_attributed_deleted_history_count"] == 1524
    assert payload["summary"]["recent_undo_command_tail_count"] == 471
    assert payload["summary"]["recent_undo_attributed_deleted_history_count"] == 475


def test_insert_only_absent_gap_is_historical_and_unattributed():
    log = _load(SQL)["retained_history_lifecycle_log"]
    coverage = log["logged_id_coverage"]
    assert coverage["logged_id_count"] == 121094
    assert coverage["currently_present_count"] == 106131
    assert coverage["currently_absent_count"] == 14963
    assert coverage["both_event_count"] == 14711
    assert coverage["insert_only_but_absent_count"] == 252
    assert log["insert_logged_absent_without_delete_batch"]["recent_insert_count"] == 0


def test_runtime_proves_both_forms_use_wrapper_and_nested_adapters():
    payload = _load(RUNTIME)
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 2,
        "selected_method_count": 6,
        "selected_instruction_count": 700,
        "source_hash_mismatch_count": 0,
        "method_or_coverage_error_count": 0,
    }
    contract = payload["managed_undo_contract"]
    assert contract["legacy_undo_starts_transaction_before_delete_call"]
    assert contract["new_undo_starts_transaction_before_delete_call"]
    assert contract["desktop_forms_call_cession_wrapper_not_direct_delete_adapter"]
    assert contract["adapter_starts_nested_transaction_before_execute"]
    assert contract["cession_wrapper_adapter_starts_nested_transaction_before_execute"]
    assert not contract["branch_specific_delete_cession_and_rollback_reachability_proven"]
    assert not contract["runtime_form_selection_proven"]


def test_r074_is_caveated_and_traced_without_command_readiness():
    risks = _load(RISKS)
    row = next(item for item in risks["risks"] if item["id"] == "R-074")
    assert row["severity"] == "HIGH"
    assert "current projection is clean" in row["failure_mode"]
    assert "are not attributed to undo" in row["failure_mode"]
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


def test_checkpoint_hashes_sources_and_passes_every_gate():
    payload = _load(CHECKPOINT)
    assert payload["artifact"] == "varanegar_received_cheque_undo_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 18,
        "passed_check_count": 22,
        "failed_check_count": 0,
        "current_cheque_count": 23822,
        "current_history_count": 106131,
        "retained_history_delete_count": 14711,
        "undo_command_tail_count": 1502,
        "conditional_double_delete_command_count": 22,
        "undo_attributed_deleted_history_count": 1524,
        "recent_undo_command_tail_count": 471,
        "absent_without_delete_log_count": 252,
        "runtime_selected_method_count": 6,
        "risk_count": 84,
        "critical_risk_count": 50,
        "high_risk_count": 31,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 18
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
