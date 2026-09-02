import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "ngt_operation_date_boundary_20260829.json"
)
RISK = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_risk_register_20260829.json"
)
TRACE = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_requirements_traceability_20260829.json"
)
CHECKPOINT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "varanegar_operation_date_checkpoint_20260829.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_operation_date_boundary_is_static_read_only_and_identity_free():
    payload = _load(BOUNDARY)
    assert payload["artifact"] == "varanegar_ngt_customer_return_operation_date_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_AND_STATIC_TARGETED_IL",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "assemblies_loaded_or_executed": 0,
        "runtime_requests_or_raw_configuration_ids_read": 0,
        "semantic_non_secret_configuration_labels_persisted": 4,
        "raw_business_rows_identities_or_document_numbers_persisted": 0,
        "non_allowlisted_string_literals_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    assert not re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        BOUNDARY.read_text(encoding="utf-8"),
    )


def test_operation_date_schema_and_current_population_are_bounded():
    payload = _load(BOUNDARY)
    summary = payload["summary"]
    assert summary["analyzed_assembly_count"] == 4
    assert summary["method_body_count"] == 27788
    assert summary["signal_named_method_body_error_count"] == 0
    assert summary["operation_date_setter_caller_count"] == 1
    assert summary["operation_date_getter_caller_count"] == 4
    assert summary["ngt_row_count"] == 2
    assert summary["fru_row_count"] == 0
    assert summary["ngt_sentinel_operation_date_count"] == 0
    assert summary["ngt_to_fru_exact_crosswalk_count"] == 0
    contract = payload["contract"]
    assert contract["ngt_operation_date_type"] == "datetime"
    assert contract["ngt_operation_date_nullable"] is False
    assert contract["ngt_operation_date_default_definition"] == "('1900-01-01T00:00:00.000')"
    assert contract["operation_date_check_constraint_count"] == 0
    assert contract["table_trigger_count"] == 0


def test_ingest_paths_do_not_make_the_database_default_safe():
    contract = _load(BOUNDARY)["ingest_persistence_contract"]
    assert contract["save_tour_data_rejects_dotnet_default_datetime"] is True
    assert contract["add_distribution_tour_assigns_captured_now_to_operation_date"] is True
    assert contract["database_default_is_1900_sentinel_not_dotnet_default"] is True
    assert contract["database_operation_date_check_constraint_count"] == 0
    assert contract["table_trigger_count"] == 0
    assert contract["current_rows_same_calendar_day_as_created_count"] == 2
    assert contract["current_sentinel_count"] == 0


def test_current_selector_is_valid_but_implementations_are_not_flattened():
    payload = _load(BOUNDARY)
    assert payload["contract"]["current_date_selector_semantic_label"] == "تاريخ درخواست"
    assert payload["contract"]["current_date_selector_code_enum_name"] == "CallDate"
    date_contract = payload["date_source_contract"]
    assert date_contract["available_code_enum_names"] == [
        "ActiveDate",
        "CallDate",
        "OperationDate",
        "ServerDate",
    ]
    assert date_contract["current_selection"] == {
        "semantic_label": "تاريخ درخواست",
        "code_enum_name": "CallDate",
        "sql_replication_source": "CALL_ACTIVITY_DATE",
    }
    assert date_contract["business_il_replication_overrides"] == {
        "OperationDate": "NGT_RETURN_OPERATION_DATE",
        "ActiveDate": "BACK_OFFICE_RETRIEVED_ACTIVE_DATE",
        "ServerDate": "SERVER_NOW_FORMATTED_TO_SERVER_CULTURE",
        "CallDate": "NO_EXPLICIT_OVERRIDE_BRANCH_OBSERVED_IN_REPLICATE_TOUR",
    }
    assert date_contract["sql_replication_case_sources"] == {
        "CallDate": "CALL_ACTIVITY_DATE",
        "OperationDate": "CALL_ACTIVITY_DATE_FALLBACK_TOUR_ACTIVITY_DATE",
        "ServerDate": "SERVER_TODAY_SOLAR",
        "ActiveDate": "GLOBAL_OPEN_SALES_OPERATION_DATE",
    }
    assert date_contract["global_operation_date_branch_guard"] == {
        "sales_sysref_1": True,
        "is_closed_zero": True,
        "after_last_or_last_null": True,
    }
    assert date_contract["current_snapshot_incident_claim"].startswith("NONE:")


def test_sql_selector_has_no_else_and_is_distinct_from_table_triggering():
    payload = _load(BOUNDARY)
    replication = next(
        row for row in payload["sql_consumers"]
        if row["qualified_name"] == "dbo.NGT_DoReplicateTour"
    )
    assert replication["date_selector_case_count"] == 3
    assert replication["date_selector_case_without_else_count"] == 3
    assert replication["has_explicit_transaction"] is True
    assert replication["has_try_catch"] is True
    assert payload["summary"]["sql_consumer_count"] == 11
    assert payload["summary"]["sql_consumer_references_global_tbl_opr_date_count"] == 5
    assert payload["summary"]["table_trigger_references_global_tbl_opr_date_count"] == 0


def test_temporal_selector_drift_is_caveated_and_traced():
    risks = _load(RISK)
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
    risk = next(row for row in risks["risks"] if row["id"] == "R-060")
    assert risk["severity"] == "HIGH"
    assert risk["category"] == "temporal_configuration_integrity"
    assert "No current wrong-date or accounting incident is asserted" in risk["failure_mode"]
    assert risk["phase_gate"] == "P0_BEFORE_RETURN_OR_ORDER_REPLICATION_REWRITE"
    checkpoint = risks["source_checkpoint"]
    assert checkpoint["ngt_operation_date_current_selector"] == "CallDate"
    assert checkpoint["ngt_operation_date_current_sentinel_count"] == 0
    trace = _load(TRACE)
    assert trace["validation"] == "PASS"
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_operation_date_checkpoint_hashes_sources_and_passes_all_gates():
    payload = _load(CHECKPOINT)
    assert payload["artifact"] == "varanegar_operation_date_checkpoint_20260829"
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
        "business_rows_raw_ids_or_configuration_ids_read": 0,
    }
    assert payload["summary"] == {
        "source_count": 17,
        "passed_check_count": 36,
        "failed_check_count": 0,
        "analyzed_assembly_count": 4,
        "method_body_count": 27788,
        "ngt_return_row_count": 2,
        "current_selector": "CallDate",
        "sql_consumer_count": 11,
        "risk_count": 84,
        "high_risk_count": 31,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 17
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert __import__("hashlib").sha256(path.read_bytes()).hexdigest() == row["sha256"]
