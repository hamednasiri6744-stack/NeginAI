from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "artifacts/varanegar_analysis/domains/payable_cheque_undo_boundary_20260829.json"
RUNTIME = ROOT / "artifacts/varanegar_analysis/domains/payable_cheque_undo_runtime_boundary_20260829.json"
RISKS = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT = ROOT / "artifacts/varanegar_analysis/varanegar_payable_cheque_undo_checkpoint_20260829.json"
GUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_boundary_is_read_only_and_redacted():
    payload = _load(SQL)
    assert payload["artifact"] == "varanegar_payable_cheque_undo_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] == 1
    assert payload["safety"]["stored_procedure_trigger_form_or_application_command_executions"] == 0
    assert payload["safety"]["cheque_leaf_history_identifiers_amounts_bank_or_operator_values_persisted"] == 0
    raw = SQL.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"definition"' not in raw
    assert "OperationScript" not in raw


def test_undo_deletes_history_then_updates_projection_and_leaf_atomically():
    payload = _load(SQL)
    assert payload["summary"]["selected_sql_module_count"] == 10
    assert payload["summary"]["selected_module_with_local_transaction_count"] == 4
    assert payload["undo_add_sequence_contract"] == {
        "undo_voucher_check_precedes_transaction": True,
        "undo_deletes_history": True,
        "undo_delete_precedes_current_projection_update": True,
        "undo_projection_update_precedes_leaf_update": True,
        "undo_leaf_update_precedes_commit": True,
        "undo_has_try_catch_commit_rollback": True,
        "undo_appends_compensating_history": False,
        "add_inserts_history_before_projection": True,
        "add_projection_precedes_leaf_update": True,
        "change_status_outer_calls_add_and_delete": True,
        "change_status_outer_owns_transaction": True,
    }


def test_current_projection_is_exact_but_history_is_destructive():
    payload = _load(SQL)
    assert payload["current_lifecycle"]["aggregate"] == {
        "cheque_count": 4672,
        "history_count": 13108,
        "min_history_count": 2,
        "max_history_count": 4,
        "current_pointer_not_max_count": 0,
        "current_pointer_wrong_parent_count": 0,
    }
    assert payload["current_lifecycle"]["current_status"] == [
        {"current_status": 2, "cheque_count": 1, "history_count_over_two": 1},
        {"current_status": 3, "cheque_count": 3637, "history_count_over_two": 3637},
        {"current_status": 4, "cheque_count": 81, "history_count_over_two": 63},
        {"current_status": 5, "cheque_count": 953, "history_count_over_two": 0},
    ]
    assert sum(row["transition_count"] for row in payload["current_lifecycle"]["observed_transitions"]) == 8436


def test_1537_delete_logs_match_exact_undo_tail_including_78_recent():
    payload = _load(SQL)
    assert payload["summary"]["retained_history_delete_event_count"] == 1668
    assert payload["summary"]["exact_undo_tail_history_delete_count"] == 1537
    assert payload["summary"]["recent_exact_undo_tail_count"] == 78
    shapes = {row["shape"]: row for row in payload["retained_history_lifecycle_log"]["delete_session_tail_shapes"]}
    assert shapes == {
        "CHEQUE_DELETE_PRESENT": {
            "shape": "CHEQUE_DELETE_PRESENT",
            "history_delete_count": 117,
            "recent_three_month_count": 0,
        },
        "PARTIAL_UPDATE_TAIL": {
            "shape": "PARTIAL_UPDATE_TAIL",
            "history_delete_count": 14,
            "recent_three_month_count": 0,
        },
        "UNDO_EXACT_TAIL": {
            "shape": "UNDO_EXACT_TAIL",
            "history_delete_count": 1537,
            "recent_three_month_count": 78,
        },
    }


def test_402_absent_insert_logged_histories_are_one_nonrecent_unattributed_batch():
    payload = _load(SQL)
    coverage = payload["retained_history_lifecycle_log"]["logged_id_coverage"]
    assert coverage == {
        "logged_id_count": 15178,
        "currently_present_count": 13108,
        "currently_absent_count": 2070,
        "both_event_count": 1668,
        "delete_only_count": 0,
        "insert_only_but_absent_count": 402,
        "deleted_but_present_count": 0,
    }
    batch = payload["retained_history_lifecycle_log"]["insert_logged_absent_without_delete_batch"]
    assert batch["insert_logged_absent_without_delete_count"] == 402
    assert batch["recent_insert_count"] == 0
    assert batch["first_insert"].startswith("2024-03-27T11:01:35")
    assert batch["last_insert"].startswith("2024-03-27T11:01:37")
    assert any("not attributed" in row for row in payload["evidence_limits"])


def test_runtime_boundary_is_hash_pinned_and_exposes_legacy_new_form_difference():
    payload = _load(RUNTIME)
    assert payload["artifact"] == "varanegar_payable_cheque_undo_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 2,
        "selected_method_count": 5,
        "selected_instruction_count": 714,
        "source_hash_mismatch_count": 0,
        "method_or_coverage_error_count": 0,
    }
    assert all(row["inventory_sha256_match"] for row in payload["source"])
    assert payload["safety"]["assembly_loads_or_executions"] == 0
    assert payload["safety"]["database_connections"] == 0
    assert not GUID.search(RUNTIME.read_text(encoding="utf-8"))
    c = payload["managed_undo_contract"]
    assert c["legacy_undo_checks_can_do_undo"] is True
    assert c["legacy_undo_starts_transaction_before_delete_call"] is True
    assert c["legacy_undo_delete_call_precedes_optional_reapprove_signal"] is True
    assert c["legacy_undo_has_rollback_signal"] is True
    assert c["adapter_starts_nested_transaction_before_execute"] is True
    assert c["adapter_execute_precedes_nested_commit"] is True
    assert c["new_tracking_undo_method_is_one_instruction_stub"] is True
    assert c["new_tracking_form_runtime_selection_proven"] is False


def test_r073_is_high_and_does_not_overattribute_402_or_claim_projection_mismatch():
    risks = _load(RISKS)
    row = next(item for item in risks["risks"] if item["id"] == "R-073")
    assert row["severity"] == "HIGH"
    assert "current projection is clean" in row["failure_mode"]
    assert "not attributed to undo or trigger bypass" in row["failure_mode"]
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
    assert payload["artifact"] == "varanegar_payable_cheque_undo_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 17,
        "passed_check_count": 20,
        "failed_check_count": 0,
        "current_cheque_count": 4672,
        "current_history_count": 13108,
        "retained_history_delete_count": 1668,
        "exact_undo_tail_count": 1537,
        "recent_exact_undo_tail_count": 78,
        "absent_without_delete_log_count": 402,
        "runtime_selected_method_count": 5,
        "risk_count": 84,
        "critical_risk_count": 50,
        "high_risk_count": 31,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 17
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
