"""Build an offline hash-pinned checkpoint for NGT configuration resolution."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/configuration_precedence_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/ngt_configuration_runtime_boundary_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_configuration_precedence_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_ngt_configuration_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "trace_builder": "scripts/windows/build_negin_erp_requirements_traceability.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_configuration_checkpoint_20260829.py",
    "configuration_tests": "tests/test_varanegar_configuration_precedence_boundary.py",
    "configuration_doc": "docs/varanegar_reconstruction/NGT_CONFIGURATION_PRECEDENCE_AND_TRANSPORT_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "reconstruction_readme": "docs/varanegar_reconstruction/README_FA.md",
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _method(
    methods: list[dict[str, Any]], owner: str, method: str, parameter_count: int | None = None
) -> dict[str, Any] | None:
    for row in methods:
        if row["owner"] != owner or row["method"] != method:
            continue
        if parameter_count is None or row["parameter_count"] == parameter_count:
            return row
    return None


def build() -> dict[str, Any]:
    missing = [value for value in SOURCES.values() if not (ROOT / value).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})

    sql = _load("sql_boundary")
    runtime = _load("runtime_boundary")
    risks = _load("risk_register")
    trace = _load("traceability")
    sql_summary = sql["summary"]
    runtime_summary = runtime["summary"]
    profiles = {row["qualified_name"]: row for row in sql["table_catalog_profiles"]}
    parity = {row["delivery_name"]: row for row in sql["configuration_delivery_parity"]}
    same_name = {row["field_name"]: row for row in sql["app_device_same_name_parity"]}
    state = sql["device_setting_state_and_reference_contract"]
    refs = {row["referencing_table"]: row for row in state["inbound_reference_state"]}
    methods = runtime["key_runtime_method_contracts"]
    resolver = _method(
        methods,
        "NGT.Business.Domain.DeviceSettingDomain",
        "GetDeviceSettings",
        2,
    )
    app = _method(methods, "NGT.Business.Domain.AppSettingDomain", "GetAppSetting")
    composer = next(
        (
            row
            for row in methods
            if "<GetDeviceSettings>d__5" in row["owner"] and row["method"] == "MoveNext"
        ),
        None,
    )
    composition = [] if composer is None else [
        name.rsplit(".", 1)[-1]
        for name in composer["composition_call_sequence"]
        if name != "TypeSpecRow.AddRange"
    ]
    lifecycle = {
        action: next(
            (
                row
                for row in methods
                if f"<{action}>" in row["owner"] and row["method"] == "MoveNext"
            ),
            None,
        )
        for action in ("Add", "Update", "Remove")
    }
    risk = next((row for row in risks["risks"] if row["id"] == "R-061"), None)

    direct_fields = (
        "MaximumOrderAmount",
        "MinimumOrderAmount",
        "MaximumOrderItemCount",
        "MinimumOrderItemCount",
        "RefRetOrder",
    )
    checks = {
        "sql_artifact_valid": sql["validation"] == "PASS",
        "sql_artifact_read_only": sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["denies_data_writes"] == 1,
        "sql_artifact_did_not_execute_commands": sql["safety"][
            "stored_procedure_or_application_command_executions"
        ]
        == 0,
        "sql_artifact_persisted_no_values_or_definitions": sql["safety"][
            "configuration_values_old_values_secrets_hosts_paths_or_identities_persisted"
        ]
        == 0
        and sql["safety"]["raw_configuration_or_history_rows_persisted"] == 0
        and sql["safety"]["sql_definitions_persisted"] == 0,
        "eight_target_tables": sql_summary["target_table_count"] == 8,
        "347_catalog_columns": sql_summary["catalog_column_count"] == 347,
        "four_general_server_overlaps": sql_summary[
            "general_server_exact_key_overlap_count"
        ]
        == 4,
        "three_server_nulls": sql_summary["server_null_value_count"] == 3,
        "single_active_app_setting": profiles["NGT.AppSettings"]["anonymous_counts"][
            "active_count"
        ]
        == 1,
        "device_state_40_17_23": profiles["NGT.DeviceSettings"]["anonymous_counts"]
        ["row_count"]
        == 40
        and profiles["NGT.DeviceSettings"]["anonymous_counts"]["active_count"] == 17
        and profiles["NGT.DeviceSettings"]["anonymous_counts"]["removed_count"] == 23,
        "app_and_device_only_primary_key_id": all(
            row["key_columns"] == ["Id"]
            for row in sql["target_unique_index_contracts"]
            if row["qualified_table"] in {"NGT.AppSettings", "NGT.DeviceSettings"}
        ),
        "mandatory_transport_source_drift": same_name["MandatoryCustomerVisit"][
            "app_transport_view_references_field"
        ]
        and not same_name["MandatoryCustomerVisit"][
            "device_transport_view_references_field"
        ],
        "mandatory_17_current_mismatches": same_name["MandatoryCustomerVisit"][
            "mismatch_count"
        ]
        == 17,
        "mandatory_two_active_device_nulls": same_name["MandatoryCustomerVisit"][
            "device_null_count"
        ]
        == 2,
        "backoffice_output_counts_36_and_30": sql_summary[
            "back_office_procedure_output_count"
        ]
        == 36
        and sql_summary["back_office_replication_output_count"] == 30,
        "backoffice_one_static_omission": sql_summary[
            "configuration_delivery_static_omission_count"
        ]
        == 1,
        "backoffice_six_current_absences": sql_summary[
            "configuration_delivery_current_absence_count"
        ]
        == 6,
        "backoffice_seven_semantic_mismatches": sql_summary[
            "configuration_delivery_semantic_mismatch_count"
        ]
        == 7,
        "settlement_discount_omitted_from_unpivot": not parity[
            "SettlementDiscountPercent"
        ]["delivery_declared_in_unpivot_contract"],
        "five_direct_delivery_fields_match": all(
            parity[name]["replication_row_count"] == 1
            and parity[name]["semantic_mismatch_count"] == 0
            for name in direct_fields
        ),
        "23_removed_only_device_profiles": state["device_setting_number_cardinality"]
        ["removed_only_number_group_count"]
        == 23,
        "raw_transport_emits_2184_removed_profile_rows": state[
            "transport_emission_state"
        ]["emitted_removed_only_output_row_count"]
        == 2184,
        "device_users_do_not_reference_removed_profiles": refs["NGT.DeviceUsers"][
            "removed_setting_reference_count"
        ]
        == 0,
        "51_active_order_type_children_reference_removed_profiles": refs[
            "NGT.DeviceOrderTypes"
        ]["active_child_to_removed_setting_reference_count"]
        == 51,
        "runtime_artifact_valid_and_static": runtime["validation"] == "PASS"
        and runtime["safety"]["mode"] == "STATIC_PE_METADATA_AND_IL_ONLY",
        "runtime_did_not_execute_or_read_configuration": runtime["safety"][
            "assemblies_loaded_or_executed"
        ]
        == 0
        and runtime["safety"]["application_endpoints_or_commands_called"] == 0
        and runtime["safety"]["configuration_files_or_values_read"] == 0,
        "four_assemblies_27788_methods": runtime_summary["assembly_count"] == 4
        and runtime_summary["method_body_count"] == 27788,
        "one_signal_named_body_error_is_explicit": runtime_summary[
            "signal_named_body_error_count"
        ]
        == 1,
        "92_runtime_selection_methods": runtime_summary[
            "runtime_selection_method_count"
        ]
        == 92,
        "13_selection_methods_signal_removed_filter": runtime_summary[
            "runtime_selection_method_with_is_removed_signal_count"
        ]
        == 13,
        "agent_device_resolver_is_owner_user_and_removed_aware": resolver is not None
        and "TypeSpecRow.GetQueryByOwner" in resolver["selection_calls"]
        and "Anatoli.Common.DataAccess.Models.BaseModel.get_IsRemoved"
        in resolver["semantic_references"]
        and "NGT.DataAccess.Models.SettingModel.DeviceUser.get_UserUniqueId"
        in resolver["semantic_references"],
        "app_setting_uses_fixed_public_id": app is not None
        and app["selection_calls"] == ["TypeSpecRow.GetById"]
        and "NGT.Common.PublicValues.get_AppSettingUniqueId" in app["semantic_references"],
        "configuration_composition_order_is_explicit": composition
        == [
            "GetAppSettingConfigs",
            "GetGeneralConfigs",
            "GetTrackingConfigs",
            "GetPreSaleConfigs",
            "GetHotSaleConfigs",
            "GetDistConfigs",
            "GetTaskPriorityConfigs",
            "GetReportConfigs",
            "GetPrintConfigs",
            "GetBackOfficeConfigs",
            "GetInquiryConfigs",
        ],
        "device_lifecycle_methods_are_transactional": all(
            row is not None
            and "System.Data.Entity.Database.BeginTransaction"
            in row["behavior_calls_in_order"]
            and "System.Data.Entity.DbContextTransaction.Commit"
            in row["behavior_calls_in_order"]
            and "System.Data.Entity.DbContextTransaction.Rollback"
            in row["behavior_calls_in_order"]
            for row in lifecycle.values()
        ),
        "risk_register_valid_65": risks["validation"] == "PASS"
        and risks["summary"]["risk_count"] == 84
        and risks["summary"]["high_count"] == 31,
        "risk_061_high_and_caveated": risk is not None
        and risk["severity"] == "HIGH"
        and "a current end-user incident or delivery of a removed profile is not asserted"
        in risk["failure_mode"],
        "risk_061_has_configuration_gate": risk is not None
        and risk["phase_gate"] == "P0_BEFORE_CONFIGURATION_OR_DEVICE_SYNC_REWRITE",
        "traceability_valid_256": trace["validation"] == "PASS"
        and trace["summary"]["mapped_risk_assignment_count"] == 343
        and trace["summary"]["unique_risk_count"] == 84,
        "zero_command_ready_modules": trace["summary"]["command_ready_module_count"] == 0,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    manifest = [
        {
            "name": name,
            "path": relative,
            "size_bytes": (ROOT / relative).stat().st_size,
            "sha256": _sha(ROOT / relative),
        }
        for name, relative in sorted(SOURCES.items())
    ]
    return {
        "artifact": "varanegar_configuration_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {
            "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "operational_commands_executed": 0,
            "configuration_values_business_rows_or_identifiers_read": 0,
        },
        "source_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "summary": {
            "source_count": len(manifest),
            "passed_check_count": sum(checks.values()),
            "failed_check_count": len(failed),
            "configuration_table_count": sql_summary["target_table_count"],
            "configuration_column_count": sql_summary["catalog_column_count"],
            "active_device_profile_count": profiles["NGT.DeviceSettings"][
                "anonymous_counts"
            ]["active_count"],
            "removed_device_profile_count": profiles["NGT.DeviceSettings"][
                "anonymous_counts"
            ]["removed_count"],
            "configuration_delivery_mismatch_count": sql_summary[
                "configuration_delivery_semantic_mismatch_count"
            ],
            "runtime_selection_method_count": runtime_summary[
                "runtime_selection_method_count"
            ],
            "risk_count": risks["summary"]["risk_count"],
            "high_risk_count": risks["summary"]["high_count"],
            "mapped_risk_assignment_count": trace["summary"][
                "mapped_risk_assignment_count"
            ],
            "command_ready_module_count": trace["summary"]["command_ready_module_count"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
