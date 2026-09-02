from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT / "artifacts" / "varanegar_analysis" / "domains"
SQL_PATH = DOMAIN / "ngt_replication_compensation_boundary_20260829.json"
RUNTIME_PATH = DOMAIN / "ngt_replication_compensation_runtime_boundary_20260829.json"
RISK_PATH = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "negin_erp_risk_register_20260829.json"
TRACE_PATH = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "negin_erp_requirements_traceability_20260829.json"
CHECKPOINT_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "varanegar_ngt_replication_compensation_checkpoint_20260829.json"
)
GUID = re.compile(
    r"(?i)(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-f])"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_sql_boundary_is_read_only_redacted_and_complete():
    payload = _load(SQL_PATH)
    assert payload["artifact"] == "varanegar_ngt_replication_compensation_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
        "database_updateability": "READ_ONLY",
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
        "procedure_definition_length": 17395,
        "active_rollback_mutation_statement_count": 7,
        "active_rollback_mutation_object_count": 5,
        "active_rollback_dependency_count": 25,
        "dead_legacy_undo_profiled_mutation_count": 21,
        "foreign_key_edge_count": 34,
        "enabled_no_action_foreign_key_edge_count": 29,
        "tour_history_type_count": 4,
        "distinct_existing_type_10_receipt_count": 342,
        "type_10_receipt_with_blocker_candidate_count": 342,
    }
    raw = SQL_PATH.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"definition"' not in raw


def test_deployed_rollback_is_active_while_named_legacy_undo_is_dead_code():
    payload = _load(SQL_PATH)
    derived = payload["derived_compensation_contract"]
    assert derived["active_entry_point"] == "dbo.NGT_RollBackTour"
    assert derived["active_entry_point_has_local_transaction"] is False
    assert derived["active_entry_point_requires_entity_temp_table"] is True
    assert derived["active_entry_point_deletes_tour_history"] is True
    assert derived["active_entry_point_mentions_cash_detail_cleanup"] is False
    assert derived["active_entry_point_mentions_cheque_history_cleanup"] is False
    assert derived["dead_legacy_entry_point"] == "dbo.USP_NGT_UndoReplicateTour"
    assert derived["dead_legacy_entry_point_returns_before_mutations"] is True
    assert derived["dead_legacy_cleanup_is_commented"] is True
    assert derived["dead_legacy_mentions_cash_detail_cleanup"] is True
    assert derived["dead_legacy_mentions_cheque_history_cleanup"] is True


def test_current_history_has_no_type_11_payment_crosswalk_for_active_cleanup():
    population = _load(SQL_PATH)["tour_history_target_population"]
    assert population == [
        {
            "history_type": 1,
            "history_count": 1118244,
            "distinct_entity_count": 1118244,
            "known_target_resolved_count": 1112711,
        },
        {
            "history_type": 2,
            "history_count": 1,
            "distinct_entity_count": 1,
            "known_target_resolved_count": 0,
        },
        {
            "history_type": 8,
            "history_count": 3731,
            "distinct_entity_count": 3593,
            "known_target_resolved_count": 3731,
        },
        {
            "history_type": 10,
            "history_count": 447,
            "distinct_entity_count": 344,
            "known_target_resolved_count": 438,
        },
    ]


def test_every_existing_type_10_receipt_has_enabled_no_action_dependency_candidates():
    payload = _load(SQL_PATH)
    assert payload["type_10_receipt_dependency_shape"] == {
        "distinct_existing_receipt_count": 342,
        "receipt_with_cash_count": 72,
        "receipt_with_cash_detail_count": 72,
        "receipt_with_cheque_count": 64,
        "receipt_with_cheque_history_count": 64,
        "receipt_with_bank_order_count": 330,
        "receipt_with_doc_receipt_payment_count": 342,
        "receipt_with_cash_payment_count": 72,
        "receipt_with_cheque_payment_count": 64,
        "receipt_with_bank_order_payment_count": 330,
        "receipt_with_no_action_blocker_candidate_count": 342,
    }
    assert payload["derived_compensation_contract"][
        "all_current_existing_type_10_receipts_have_blocker_candidates"
    ] is True
    edges = payload["referential_delete_contract"]
    expected = {
        ("dbo", "RCashDetail", "RCashId", "dbo", "RCash"),
        ("Acc", "tblChqHist", "ChqRef", "Acc", "TblCheque"),
        ("Acc", "tblPayments", "RCashId", "dbo", "RCash"),
        ("Acc", "tblPayments", "ChqRef", "Acc", "TblCheque"),
        ("Acc", "tblPayments", "BankOrderRef", "Acc", "TblBankOrders"),
    }
    observed = {
        (
            row["parent_schema"],
            row["parent_table"],
            row["parent_column"],
            row["referenced_schema"],
            row["referenced_table"],
        )
        for row in edges
        if row["delete_referential_action_desc"] == "NO_ACTION"
        and not row["is_disabled"]
    }
    assert expected <= observed
    assert all(not row["is_instead_of_trigger"] for row in payload["trigger_contract"])


def test_runtime_routes_request_type_20_to_both_transactional_adapters():
    payload = _load(RUNTIME_PATH)
    assert payload["artifact"] == "varanegar_ngt_replication_compensation_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "assembly_count": 5,
        "selected_method_count": 31,
        "method_body_error_count": 0,
        "instruction_count": 93912,
        "target_caller_method_count": 2,
        "target_event_count": 3,
        "target_literal_profile_count": 0,
        "target_crosswalk_setter_count": 0,
        "target_retrieve_info_result_pop_count": 1,
        "tour_adapter_method_count": 2,
        "adapter_request_type_20_contract_count": 2,
        "adapter_case_20_active_rollback_signal_count": 2,
        "case20_entity_selector_count": 2,
        "case20_temp_row_appender_count": 2,
    }
    contract = payload["rollback_tour_contract"]
    assert contract["target_method_present"] is True
    assert contract["target_instruction_count"] == 20
    assert contract["business_request_type_20_assignment_count"] == 1
    assert contract["caller_method_count"] == 2
    assert contract["retrieve_info_call_count"] == 1
    assert contract["retrieve_info_result_pop_count"] == 1
    assert contract["adapter_result_is_discarded"] is True
    assert contract["backoffice_crosswalk_setter_count"] == 0
    cases = contract["adapter_request_type_20_contracts"]
    assert {row["file"] for row in cases} == {
        "NGT.VnLite.DataAccess.dll",
        "NGT.VnSds.DataAccess.dll",
    }
    for row in cases:
        assert row["request_type"] == 20
        assert row["active_rollback_sql_signal_count"] == 1
        assert row["entity_temp_table_signal_count"] == 1
        assert row["execute_event_count"] == 3
        assert row["commit_event_count"] == 1
        assert row["rollback_event_count"] == 1


def test_runtime_case_20_uses_replication_result_entity_ids_and_persists_no_literals():
    payload = _load(RUNTIME_PATH)
    contract = payload["rollback_tour_contract"]
    assert len(contract["case20_entity_selector_contracts"]) == 2
    assert all(
        row["entity_unique_id_getter_count"] == 1
        for row in contract["case20_entity_selector_contracts"]
    )
    assert len(contract["case20_temp_row_appender_contracts"]) == 2
    assert all(
        row["entity_collection_reference_count"] == 1
        for row in contract["case20_temp_row_appender_contracts"]
    )
    assert payload["safety"] == {
        "mode": "STATIC_PE_METADATA_AND_IL_ONLY",
        "assembly_loads_or_execution": 0,
        "application_endpoint_or_command_executions": 0,
        "database_connections": 0,
        "configuration_or_business_data_reads": 0,
        "raw_string_or_sql_literals_persisted": 0,
        "guid_literals_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    raw = RUNTIME_PATH.read_text(encoding="utf-8")
    assert not GUID.search(raw)
    assert '"raw_literal"' not in raw
    assert '"sql_literal"' not in raw


def test_r065_is_critical_caveated_and_traced_to_four_modules():
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
    risk = next(row for row in risks["risks"] if row["id"] == "R-065")
    assert risk["severity"] == "CRITICAL"
    assert risk["category"] == "replication_compensation"
    assert risk["modules"] == [
        "sales",
        "distribution",
        "receivables_treasury",
        "integration_migration",
    ]
    assert "all 342 have at least one enabled NO_ACTION dependency candidate" in risk["failure_mode"]
    assert "does not prove which rollback attempts occurred" in risk["failure_mode"]
    assert len(risk["controls"]) == 6
    assert len(risk["exit_criteria"]) == 6
    trace = _load(TRACE_PATH)
    assert trace["validation"] == "PASS"
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_compensation_checkpoint_hashes_sources_and_passes_all_gates():
    payload = _load(CHECKPOINT_PATH)
    assert payload["artifact"] == "varanegar_ngt_replication_compensation_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert all(payload["checks"].values())
    assert payload["safety"] == {
        "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "operational_commands_executed": 0,
        "business_rows_configuration_values_or_identifiers_read": 0,
    }
    assert payload["summary"] == {
        "source_count": 16,
        "passed_check_count": 20,
        "failed_check_count": 0,
        "type_10_history_count": 447,
        "distinct_existing_receipt_count": 342,
        "receipt_with_blocker_candidate_count": 342,
        "cash_detail_receipt_count": 72,
        "cheque_history_receipt_count": 64,
        "bank_order_payment_receipt_count": 330,
        "adapter_request_type_20_contract_count": 2,
        "risk_count": 84,
        "critical_risk_count": 50,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 16
    import hashlib

    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
