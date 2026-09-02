from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "artifacts/varanegar_analysis/domains/ngt_return_replication_boundary_20260829.json"
RUNTIME_PATH = ROOT / "artifacts/varanegar_analysis/domains/ngt_return_runtime_boundary_20260829.json"
RISK_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE_PATH = ROOT / "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT_PATH = ROOT / "artifacts/varanegar_analysis/varanegar_ngt_return_checkpoint_20260829.json"
GUID = re.compile(
    r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-"
    r"[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_sql_boundary_is_read_only_redacted_and_current():
    payload = _load(SQL_PATH)
    assert payload["artifact"] == "varanegar_ngt_return_replication_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "business_rows_or_identifiers_persisted": 0,
        "sql_definitions_persisted": 0,
        "guid_literals_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    assert payload["summary"] == {
        "procedure_count": 4,
        "active_mobile_return_header_count": 2,
        "active_mobile_return_line_count": 2,
        "line_with_history_count": 1,
        "line_without_history_count": 1,
        "historical_result_current_target_missing_count": 1,
        "current_order_target_count": 0,
        "history_type_count": 1,
    }
    raw = SQL_PATH.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"definition"' not in raw


def test_sql_proves_commit_before_return_order_writeback():
    payload = _load(SQL_PATH)
    contract = payload["replication_contract"]
    assert contract["do_replicate_tour_commits_before_return_order_writeback"] is True
    assert contract["do_replicate_tour_commits_before_return_invoice_writeback"] is False
    procedures = {row["qualified_name"]: row for row in payload["procedure_profiles"]}
    assert set(procedures) == {
        "dbo.NGT_DoReplicateTour",
        "dbo.NGT_ReplicateTour",
        "dbo.NGT_ReplicateReturnOrderMaster",
        "dbo.NGT_CreateRetSale_ForDistInfo",
    }
    do_replicate = procedures["dbo.NGT_DoReplicateTour"]
    assert do_replicate["has_explicit_transaction"] is True
    assert do_replicate["has_try_catch"] is True
    assert do_replicate["has_explicit_rollback"] is True


def test_return_history_and_crosswalk_have_no_relevant_unique_guard():
    contract = _load(SQL_PATH)["replication_contract"]
    assert contract["return_tour_history_entity_unique_index_present"] is False
    assert contract["return_line_backoffice_crosswalk_unique_constraint_present"] is False
    history = _load(SQL_PATH)["tour_history_population"]
    assert history == [
        {
            "history_type": 2,
            "history_count": 1,
            "distinct_entity_count": 1,
            "current_ngt_line_match_count": 1,
            "current_target_match_count": 0,
            "history_in_duplicate_entity_group_count": 0,
            "retry_ambiguity_history_count": 0,
        }
    ]


def test_current_two_lines_are_pending_or_historical_target_missing():
    contract = _load(SQL_PATH)["replication_contract"]
    assert contract["active_return_line_count"] == 2
    assert contract["active_line_without_history_count"] == 1
    assert contract["active_line_with_history_count"] == 1
    assert contract["historical_result_current_order_missing_count"] == 1
    assert contract["current_order_target_count"] == 0
    assert contract["order_writeback_present_count"] == 1
    assert contract["invoice_writeback_present_count"] == 0


def test_runtime_places_replication_before_managed_transaction_and_crosswalk():
    payload = _load(RUNTIME_PATH)
    assert payload["artifact"] == "varanegar_ngt_return_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 5,
        "parsed_method_body_count": 28181,
        "selected_method_count": 18,
        "selected_instruction_count": 35452,
        "method_body_error_count": 0,
        "return_crosswalk_setter_count": 9,
    }
    contract = payload["return_runtime_contract"]
    assert contract["replicate_tour_new_replication_call_count"] == 1
    assert contract["replicate_tour_return_crosswalk_setter_count"] == 8
    assert contract["replicate_tour_line_crosswalk_setter_count"] == 6
    assert contract["replicate_tour_call_collection_setter_count"] == 2
    assert contract["new_replication_call_precedes_managed_transaction_in_linear_il"] is True
    assert contract["new_replication_call_precedes_return_crosswalk_setters_in_linear_il"] is True
    assert contract["managed_commit_exists_before_return_crosswalk_setters_in_linear_il"] is True
    assert contract["managed_commit_exists_after_return_crosswalk_setters_in_linear_il"] is True
    assert payload["safety"]["assembly_loads_or_execution"] == 0
    assert payload["safety"]["raw_string_or_sql_literals_persisted"] == 0
    assert not GUID.search(RUNTIME_PATH.read_text(encoding="utf-8"))


def test_update_from_ngt_has_four_save_boundaries_without_transaction_signal():
    contract = _load(RUNTIME_PATH)["return_runtime_contract"]
    assert contract["update_from_ngt_present"] is True
    assert contract["update_from_ngt_save_changes_count"] == 3
    assert contract["update_from_ngt_is_removed_setter_count"] == 4
    assert contract["update_from_ngt_is_canceled_setter_count"] == 1
    assert contract["update_from_ngt_transaction_event_count"] == 0
    assert contract["update_from_ngt_caller_count"] == 1
    assert contract["update_from_ngt_caller_save_changes_count"] == 1
    assert contract["update_from_ngt_caller_transaction_event_count"] == 0


def test_r066_r067_are_caveated_and_traced():
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
    by_id = {row["id"]: row for row in risks["risks"]}
    assert by_id["R-066"]["severity"] == "CRITICAL"
    assert "not that a duplicate return currently exists" in by_id["R-066"]["failure_mode"]
    assert by_id["R-067"]["severity"] == "HIGH"
    assert "does not prove that a partial update incident occurred" in by_id["R-067"]["failure_mode"]
    trace = _load(TRACE_PATH)
    assert trace["validation"] == "PASS"
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_return_checkpoint_hashes_sources_and_passes_all_gates():
    payload = _load(CHECKPOINT_PATH)
    assert payload["artifact"] == "varanegar_ngt_return_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 17,
        "passed_check_count": 21,
        "failed_check_count": 0,
        "active_return_line_count": 2,
        "line_without_history_count": 1,
        "historical_target_missing_count": 1,
        "return_crosswalk_setter_count": 8,
        "update_save_boundary_count": 4,
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
        import hashlib

        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
