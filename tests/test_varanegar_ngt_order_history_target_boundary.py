from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "artifacts/varanegar_analysis/domains/ngt_order_history_target_boundary_20260829.json"
RUNTIME_PATH = ROOT / "artifacts/varanegar_analysis/domains/ngt_order_history_runtime_boundary_20260829.json"
RISK_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT_PATH = ROOT / "artifacts/varanegar_analysis/varanegar_ngt_order_history_checkpoint_20260829.json"
GUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_order_history_sql_boundary_is_read_only_and_redacted():
    payload = _load(SQL_PATH)
    assert payload["artifact"] == "varanegar_ngt_order_history_target_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] == 1
    assert payload["safety"]["stored_procedure_or_application_command_executions"] == 0
    assert payload["safety"]["business_rows_or_identifiers_persisted"] == 0
    raw = SQL_PATH.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"definition"' not in raw


def test_type1_target_resolution_counts_are_exact():
    payload = _load(SQL_PATH)
    assert payload["summary"] == {
        "type1_history_count": 1118244,
        "resolved_target_count": 1112711,
        "missing_target_history_count": 5533,
        "distinct_missing_target_pair_count": 1024,
        "parent_with_missing_target_count": 1022,
        "recent_three_month_missing_history_count": 634,
        "recent_three_month_parent_with_missing_target_count": 114,
    }
    contract = payload["order_history_contract"]
    assert contract["uuid_only_target_match_count"] == 0
    assert contract["ref_only_target_match_count"] == 0
    assert contract["uuid_ref_conflict_target_count"] == 0


def test_missing_targets_retain_exact_active_uncanceled_crosswalks():
    contract = _load(SQL_PATH)["order_history_contract"]
    assert contract["missing_target_line_crosswalk_match_count"] == 5533
    assert contract["missing_target_removed_line_count"] == 0
    assert contract["missing_target_removed_parent_count"] == 0
    assert contract["missing_target_canceled_parent_count"] == 0
    assert contract["missing_target_parent_with_type8_count"] == 0
    assert contract["target_shared_by_multiple_parent_count"] == 0
    assert contract["max_parent_per_missing_target"] == 1


def test_parent_shape_preserves_one_mixed_and_split_cases():
    contract = _load(SQL_PATH)["order_history_contract"]
    assert contract["all_targets_missing_parent_count"] == 1021
    assert contract["mixed_resolved_missing_parent_count"] == 1
    assert contract["mixed_parent_history_line_count"] == 16
    assert contract["mixed_parent_missing_line_count"] == 1
    assert contract["split_target_parent_count"] == 7
    assert contract["missing_and_split_parent_count"] == 3
    assert contract["max_line_per_missing_target"] == 87
    assert contract["type1_entity_unique_index_present"] is True


def test_runtime_places_replication_before_order_crosswalk_setters():
    payload = _load(RUNTIME_PATH)
    assert payload["artifact"] == "varanegar_ngt_order_history_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 3,
        "selected_method_count": 2,
        "selected_instruction_count": 17361,
        "method_body_error_count": 0,
        "order_line_crosswalk_setter_count": 3,
    }
    contract = payload["order_history_runtime_contract"]
    assert contract["new_replication_call_count"] == 1
    assert contract["order_line_crosswalk_setter_count"] == 3
    assert contract["new_replication_precedes_managed_transaction_in_linear_il"] is True
    assert contract["new_replication_precedes_order_crosswalk_setters_in_linear_il"] is True
    assert contract["managed_commit_exists_before_order_crosswalk_setters_in_linear_il"] is True
    assert contract["managed_commit_exists_after_order_crosswalk_setters_in_linear_il"] is True
    assert payload["safety"]["assembly_loads_or_execution"] == 0
    assert not GUID.search(RUNTIME_PATH.read_text(encoding="utf-8"))


def test_r069_is_critical_and_does_not_authorize_recreation():
    risks = _load(RISK_PATH)
    assert risks["validation"] == "PASS"
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
    risk = next(row for row in risks["risks"] if row["id"] == "R-069")
    assert risk["severity"] == "CRITICAL"
    assert "does not authorize recreation" in risk["failure_mode"]
    assert len(risk["controls"]) == 6
    assert len(risk["exit_criteria"]) == 6
    trace = _load(TRACE_PATH)
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_order_history_checkpoint_hashes_sources_and_passes_all_gates():
    payload = _load(CHECKPOINT_PATH)
    assert payload["artifact"] == "varanegar_ngt_order_history_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 17,
        "passed_check_count": 18,
        "failed_check_count": 0,
        "type1_history_count": 1118244,
        "missing_target_history_count": 5533,
        "affected_parent_count": 1022,
        "recent_missing_parent_count": 114,
        "order_crosswalk_setter_count": 3,
        "risk_count": 84,
        "critical_risk_count": 50,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 17
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
