import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_BOUNDARY = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "configuration_precedence_boundary_20260829.json"
)
RUNTIME_BOUNDARY = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "ngt_configuration_runtime_boundary_20260829.json"
)
RISK = (
    ROOT / "artifacts" / "varanegar_analysis" / "ui"
    / "negin_erp_risk_register_20260829.json"
)
TRACE = (
    ROOT / "artifacts" / "varanegar_analysis" / "ui"
    / "negin_erp_requirements_traceability_20260829.json"
)
CHECKPOINT = (
    ROOT / "artifacts" / "varanegar_analysis"
    / "varanegar_configuration_checkpoint_20260829.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_configuration_sql_boundary_is_read_only_and_value_free():
    payload = _load(SQL_BOUNDARY)
    assert payload["artifact"] == "varanegar_configuration_precedence_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_CATALOG_DEFINITION_FINGERPRINTS_AND_ANONYMOUS_NULL_AGGREGATES",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "configuration_values_old_values_secrets_hosts_paths_or_identities_persisted": 0,
        "raw_configuration_or_history_rows_persisted": 0,
        "sql_definitions_persisted": 0,
        "safe_configuration_key_or_column_identifiers_persisted": True,
        "source_or_target_state_changed": 0,
    }
    text = SQL_BOUNDARY.read_text(encoding="utf-8")
    assert not re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        text,
    )
    assert '"definition":' not in text


def test_configuration_storage_layers_and_null_boundaries_are_explicit():
    payload = _load(SQL_BOUNDARY)
    summary = payload["summary"]
    assert summary["target_table_count"] == 8
    assert summary["catalog_column_count"] == 347
    assert summary["general_server_exact_key_overlap_count"] == 4
    assert summary["server_null_value_count"] == 3
    profiles = {row["qualified_name"]: row for row in payload["table_catalog_profiles"]}
    assert profiles["NGT.AppSettings"]["anonymous_counts"]["active_count"] == 1
    assert profiles["NGT.DeviceSettings"]["anonymous_counts"] == {
        "row_count": 40,
        "removed_count": 23,
        "active_count": 17,
        "distinct_dataownercenterid_count": 1,
        "null_dataownercenterid_count": 0,
        "distinct_dataownerid_count": 1,
        "null_dataownerid_count": 0,
        "distinct_applicationownerid_count": 1,
        "null_applicationownerid_count": 0,
    }
    assert all(
        row["key_columns"] == ["Id"]
        for row in payload["target_unique_index_contracts"]
        if row["qualified_table"] in {"NGT.AppSettings", "NGT.DeviceSettings"}
    )


def test_mandatory_customer_visit_source_drift_is_current_and_anonymous():
    payload = _load(SQL_BOUNDARY)
    rows = {row["field_name"]: row for row in payload["app_device_same_name_parity"]}
    mandatory = rows["MandatoryCustomerVisit"]
    assert mandatory == {
        "field_name": "MandatoryCustomerVisit",
        "app_transport_view_references_field": True,
        "device_transport_view_references_field": False,
        "active_device_count": 17,
        "device_null_count": 2,
        "app_null_projection_count": 0,
        "exact_or_both_null_match_count": 0,
        "mismatch_count": 17,
    }
    display = rows["DisplayunitbyBasedOnUniqueId"]
    assert display["app_transport_view_references_field"] is False
    assert display["device_transport_view_references_field"] is True
    assert display["mismatch_count"] == 1


def test_back_office_live_and_transport_contracts_are_not_flattened():
    payload = _load(SQL_BOUNDARY)
    summary = payload["summary"]
    assert summary["back_office_procedure_output_count"] == 36
    assert summary["back_office_replication_output_count"] == 30
    assert summary["configuration_delivery_static_omission_count"] == 1
    assert summary["configuration_delivery_current_absence_count"] == 6
    assert summary["configuration_delivery_semantic_mismatch_count"] == 7
    names = payload["back_office_output_identifier_contract"]
    assert names["known_semantic_rename"] == {"DCName": "DistributionCenterName"}
    assert set(names["procedure_only_exact_name_outputs"]) == {
        "CompanyEconCode",
        "CustomerCounty",
        "CustomerState",
        "CustStatusAfterUpdate",
        "DCName",
        "SendInactiveDealerForInvoiceReturn",
        "SettlementDiscountPercent",
    }
    parity = {row["delivery_name"]: row for row in payload["configuration_delivery_parity"]}
    assert parity["SettlementDiscountPercent"]["delivery_declared_in_unpivot_contract"] is False
    for name in (
        "MaximumOrderAmount", "MinimumOrderAmount",
        "MaximumOrderItemCount", "MinimumOrderItemCount", "RefRetOrder",
    ):
        assert parity[name]["replication_row_count"] == 1
        assert parity[name]["semantic_mismatch_count"] == 0
    assert sum(
        row["semantic_mismatch_count"]
        for row in parity.values()
        if row["delivery_declared_in_unpivot_contract"]
    ) == 7


def test_removed_device_profiles_are_exposed_raw_but_not_overclaimed_as_user_delivery():
    contract = _load(SQL_BOUNDARY)["device_setting_state_and_reference_contract"]
    assert contract["device_setting_number_cardinality"] == {
        "row_count": 40,
        "distinct_number_count": 40,
        "null_number_count": 0,
        "duplicate_number_group_count": 0,
        "maximum_rows_per_number": 1,
        "duplicate_active_number_group_count": 0,
        "mixed_active_removed_number_group_count": 0,
        "removed_only_number_group_count": 23,
    }
    transport = contract["transport_emission_state"]
    assert transport["emitted_device_number_count"] == 40
    assert transport["emitted_removed_only_number_count"] == 23
    assert transport["emitted_removed_only_output_row_count"] == 2184
    refs = {row["referencing_table"]: row for row in contract["inbound_reference_state"]}
    assert refs["NGT.DeviceUsers"]["removed_setting_reference_count"] == 0
    assert refs["NGT.DeviceOrderTypes"]["removed_setting_reference_count"] == 51
    assert refs["NGT.DeviceOrderTypes"]["active_child_to_removed_setting_reference_count"] == 51


def test_configuration_runtime_boundary_is_static_and_exposes_selection_semantics():
    payload = _load(RUNTIME_BOUNDARY)
    assert payload["artifact"] == "varanegar_ngt_configuration_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "STATIC_PE_METADATA_AND_IL_ONLY",
        "assemblies_loaded_or_executed": 0,
        "application_endpoints_or_commands_called": 0,
        "configuration_files_or_values_read": 0,
        "non_allowlisted_literals_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["assembly_count"] == 4
    assert summary["method_body_count"] == 27788
    assert summary["method_body_error_count"] == 3
    assert summary["signal_named_body_error_count"] == 1
    assert summary["runtime_selection_method_count"] == 92
    assert summary["runtime_selection_method_with_is_removed_signal_count"] == 13
    methods = payload["key_runtime_method_contracts"]
    resolver = next(
        row for row in methods
        if row["owner"] == "NGT.Business.Domain.DeviceSettingDomain"
        and row["method"] == "GetDeviceSettings"
        and row["parameter_count"] == 2
    )
    assert "TypeSpecRow.GetQueryByOwner" in resolver["selection_calls"]
    assert "Anatoli.Common.DataAccess.Models.BaseModel.get_IsRemoved" in resolver["semantic_references"]
    assert "NGT.DataAccess.Models.SettingModel.DeviceUser.get_UserUniqueId" in resolver["semantic_references"]
    app = next(
        row for row in methods
        if row["owner"] == "NGT.Business.Domain.AppSettingDomain"
        and row["method"] == "GetAppSetting"
    )
    assert app["selection_calls"] == ["TypeSpecRow.GetById"]
    assert "NGT.Common.PublicValues.get_AppSettingUniqueId" in app["semantic_references"]


def test_runtime_composition_and_lifecycle_are_hash_pinned():
    methods = _load(RUNTIME_BOUNDARY)["key_runtime_method_contracts"]
    composer = next(
        row for row in methods
        if "<GetDeviceSettings>d__5" in row["owner"] and row["method"] == "MoveNext"
    )
    config_calls = [
        name.rsplit(".", 1)[-1]
        for name in composer["composition_call_sequence"]
        if name != "TypeSpecRow.AddRange"
    ]
    assert config_calls == [
        "GetAppSettingConfigs", "GetGeneralConfigs", "GetTrackingConfigs",
        "GetPreSaleConfigs", "GetHotSaleConfigs", "GetDistConfigs",
        "GetTaskPriorityConfigs", "GetReportConfigs", "GetPrintConfigs",
        "GetBackOfficeConfigs", "GetInquiryConfigs",
    ]
    for action in ("Add", "Update", "Remove"):
        method = next(
            row for row in methods
            if f"<{action}>" in row["owner"] and row["method"] == "MoveNext"
        )
        assert "System.Data.Entity.Database.BeginTransaction" in method["behavior_calls_in_order"]
        assert "System.Data.Entity.DbContextTransaction.Commit" in method["behavior_calls_in_order"]
        assert "System.Data.Entity.DbContextTransaction.Rollback" in method["behavior_calls_in_order"]


def test_configuration_resolution_risk_is_caveated_and_traced():
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
    risk = next(row for row in risks["risks"] if row["id"] == "R-061")
    assert risk["severity"] == "HIGH"
    assert risk["category"] == "configuration_replication_integrity"
    assert "a current end-user incident or delivery of a removed profile is not asserted" in risk["failure_mode"]
    assert risk["phase_gate"] == "P0_BEFORE_CONFIGURATION_OR_DEVICE_SYNC_REWRITE"
    trace = _load(TRACE)
    assert trace["validation"] == "PASS"
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_configuration_checkpoint_hashes_sources_and_passes_every_gate():
    payload = _load(CHECKPOINT)
    assert payload["artifact"] == "varanegar_configuration_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert payload["safety"] == {
        "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "operational_commands_executed": 0,
        "configuration_values_business_rows_or_identifiers_read": 0,
    }
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 15,
        "passed_check_count": 39,
        "failed_check_count": 0,
        "configuration_table_count": 8,
        "configuration_column_count": 347,
        "active_device_profile_count": 17,
        "removed_device_profile_count": 23,
        "configuration_delivery_mismatch_count": 7,
        "runtime_selection_method_count": 92,
        "risk_count": 84,
        "high_risk_count": 31,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 15
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        import hashlib

        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
