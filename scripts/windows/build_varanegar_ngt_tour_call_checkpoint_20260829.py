"""Build an offline hash-pinned checkpoint for NGT tour/customer-call state."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sql_boundary": "artifacts/varanegar_analysis/domains/ngt_tour_call_state_boundary_20260829.json",
    "runtime_boundary": "artifacts/varanegar_analysis/domains/ngt_tour_call_runtime_boundary_20260829.json",
    "authorization_endpoints": "artifacts/varanegar_analysis/domains/ngt_authorization_endpoint_coverage_20260828.json",
    "order_boundary": "artifacts/varanegar_analysis/domains/ngt_order_persistence_boundary_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "sql_extractor": "scripts/sql/extract_varanegar_ngt_tour_call_state_boundary.py",
    "runtime_extractor": "scripts/sql/extract_varanegar_ngt_tour_call_runtime_boundary.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "trace_builder": "scripts/windows/build_negin_erp_requirements_traceability.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_ngt_tour_call_checkpoint_20260829.py",
    "tour_call_tests": "tests/test_varanegar_ngt_tour_call_state_boundary.py",
    "tour_call_doc": "docs/varanegar_reconstruction/NGT_TOUR_CUSTOMER_CALL_STATE_AND_COMMAND_BOUNDARY_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "reconstruction_readme": "docs/varanegar_reconstruction/README_FA.md",
}

LIFECYCLE_ENDPOINT_NAMES = {
    "ActivateDistTour", "ActivateHotSaleTour", "ActivatePreSaleTour", "ActivateVanSaleTour",
    "CancelTour", "ConfirmDistTour", "ConfirmDistTourPayments", "ConfirmDistTourReceived",
    "ConfirmHotSaleTourPayments", "ConfirmHotSaleTourReceived",
    "ConfirmPreSaleTourPayments", "ConfirmPreSaleTourReceived", "ConfirmTourReceived",
    "ConfirmVanSaleTourPayments", "DeactivateDistTour", "DeactivateHotSaleTour",
    "DeactivatePreSaleTour", "DeactivateVanSaleTour", "ReplicateDistTour",
    "ReplicateHotSaleTour", "ReplicatePreSaleTour", "ReplicateVanSaleTour",
    "TourReceived", "TourSent", "WithdrawDistTourPayments", "WithdrawHotSaleTourPayments",
    "WithdrawPreSaleTourPayments", "WithdrawVanSaleTourPayments",
    "backToReadySendStatusTour",
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / SOURCES[name]).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    missing = [value for value in SOURCES.values() if not (ROOT / value).is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})

    sql = _load("sql_boundary")
    runtime = _load("runtime_boundary")
    endpoints = _load("authorization_endpoints")
    order = _load("order_boundary")
    risks = _load("risk_register")
    trace = _load("traceability")
    sql_summary = sql["summary"]
    runtime_summary = runtime["summary"]
    status_integrity = sql["semantic_status_contract"]["reference_integrity"]
    status_rows = sql["semantic_status_contract"]["semantic_status_rows"]
    tour = sql["tour_state_contract"]
    tour_aggregate = tour["aggregate"]
    call = sql["customer_call_state_contract"]
    call_aggregate = call["aggregate"]
    duplicates = call["duplicate_tour_customer_contract"]
    counters = sql["tour_counter_candidate_contract"]["aggregate_candidate_matches"]
    lifecycle = runtime["lifecycle_method_contracts"]
    lifecycle_endpoints = [
        row
        for row in endpoints["endpoints"]
        if row["controller"] == "NGT.WebApi.Controllers.V2.TourController"
        and row["method"] in LIFECYCLE_ENDPOINT_NAMES
    ]
    state_risk = next((row for row in risks["risks"] if row["id"] == "R-008"), None)
    get_risk = next((row for row in risks["risks"] if row["id"] == "R-062"), None)

    tour_status_totals: dict[str, int] = {}
    for row in tour["current_previous_status_matrix"]:
        tour_status_totals[row["current_status_name"]] = (
            tour_status_totals.get(row["current_status_name"], 0) + row["tour_count"]
        )
    delivery_status_count = sum(
        row["visit_status_count"]
        for row in status_rows
        if row["base_type_name"] == "DistributionDeliveryStatus"
    )

    checks = {
        "sql_artifact_valid_and_read_only": sql["validation"] == "PASS"
        and sql["safety"]["database_updateability"] == "READ_ONLY"
        and sql["safety"]["can_update"] == 0
        and sql["safety"]["denies_data_writes"] == 1,
        "sql_executed_no_procedure_or_command": sql["safety"][
            "stored_procedure_or_application_command_executions"
        ]
        == 0,
        "sql_persisted_no_business_rows_or_definitions": sql["safety"][
            "business_rows_customer_user_location_comment_configuration_values_or_identifiers_persisted"
        ]
        == 0
        and sql["safety"]["sql_definitions_persisted"] == 0,
        "four_tables_and_162_columns": sql_summary["target_table_count"] == 4
        and sql_summary["catalog_column_count"] == 162,
        "64561_tours_and_2471250_calls": sql_summary["tour_count"] == 64561
        and sql_summary["customer_call_count"] == 2471250,
        "only_two_id_primary_or_unique_indexes": sql_summary[
            "unique_or_primary_index_count"
        ]
        == 2
        and all(row["key_columns"] == ["Id"] for row in sql["target_unique_index_contracts"]),
        "tour_call_status_references_all_resolve": status_integrity[
            "unresolved_tour_status_count"
        ]
        == 0
        and status_integrity["unresolved_call_status_count"] == 0
        and status_integrity["unresolved_visit_status_count"] == 0,
        "tour_and_call_status_use_expected_base_types": status_integrity[
            "wrong_base_type_tour_status_count"
        ]
        == 0
        and status_integrity["wrong_base_type_call_status_count"] == 0,
        "772_visit_references_use_delivery_base_type": status_integrity[
            "wrong_base_type_visit_status_count"
        ]
        == 772
        and delivery_status_count == 772,
        "no_current_removed_status_reference": status_integrity[
            "removed_tour_status_reference_count"
        ]
        == 0
        and status_integrity["removed_call_status_reference_count"] == 0
        and status_integrity["removed_visit_status_reference_count"] == 0,
        "six_current_tour_status_totals_are_exact": tour_status_totals
        == {
            "ارسال شده": 16,
            "انصراف داده": 3419,
            "خاتمه يافته": 49354,
            "در حال دريافت اطلاعات": 78,
            "دريافت شده": 10659,
            "غيرفعال": 1035,
        },
        "455_tours_have_previous_status": tour_aggregate[
            "previous_status_present_count"
        ]
        == 455
        and tour_aggregate["unresolved_previous_status_count"] == 0,
        "tour_status_lookup_differs_only_at_center_scope": tour_aggregate[
            "status_application_owner_difference_count"
        ]
        == 0
        and tour_aggregate["status_data_owner_difference_count"] == 0
        and tour_aggregate["status_center_difference_count"] == 64561,
        "two_current_tour_time_reversals": tour_aggregate["end_before_start_count"] == 2,
        "call_parent_and_scope_integrity_currently_zero": call_aggregate[
            "orphan_tour_count"
        ]
        == 0
        and call_aggregate["active_call_under_removed_tour_count"] == 0
        and call_aggregate["tour_scope_mismatch_count"] == 0,
        "three_current_negative_visit_durations": call_aggregate[
            "negative_visit_duration_count"
        ]
        == 3
        and call_aggregate["end_before_start_count"] == 0,
        "manual_call_times_currently_absent": call_aggregate["manual_started_count"] == 0
        and call_aggregate["manual_ended_count"] == 0,
        "tour_customer_pair_is_not_unique": duplicates[
            "duplicate_tour_customer_group_count"
        ]
        == 26613
        and duplicates["calls_in_duplicate_tour_customer_groups"] == 57391
        and duplicates["maximum_calls_per_tour_customer"] == 14,
        "stored_counter_matches_are_not_universal": counters[
            "customer_count_matches_call_count"
        ]
        == 17926
        and counters["order_count_matches_ordered_call_count"] == 63073
        and counters["invoice_count_matches_invoiced_call_count"] == 64136,
        "only_named_status_history_candidate_is_empty_order_status": sql_summary[
            "history_or_status_named_table_count"
        ]
        == 1
        and sql["history_or_status_named_table_candidates"][0]["table_name"]
        == "CustomerCallOrderStatus"
        and order["summary"]["order_status_event_count"] == 0,
        "tour_status_trigger_is_enabled_and_fingerprinted": sql_summary[
            "target_trigger_count"
        ]
        == 1
        and not sql["target_trigger_contracts"][0]["is_disabled"]
        and sql["target_trigger_contracts"][0]["uuid_literal_count"] == 2,
        "95_related_sql_modules_are_hashed_not_persisted": sql_summary[
            "target_sql_module_count"
        ]
        == 95,
        "runtime_artifact_valid_and_static": runtime["validation"] == "PASS"
        and runtime["safety"]["mode"] == "STATIC_PE_METADATA_AND_IL_ONLY",
        "runtime_executed_nothing_and_read_no_values": runtime["safety"][
            "assemblies_loaded_or_executed"
        ]
        == 0
        and runtime["safety"]["application_endpoints_or_commands_called"] == 0
        and runtime["safety"]["configuration_files_or_values_read"] == 0
        and runtime["safety"]["business_rows_or_identifiers_read"] == 0,
        "runtime_scanned_27788_bodies_with_no_signal_error": runtime_summary[
            "method_body_count"
        ]
        == 27788
        and runtime_summary["signal_named_body_error_count"] == 0,
        "all_20_target_lifecycle_bodies_resolve": runtime_summary[
            "lifecycle_method_count"
        ]
        == 20
        and runtime_summary["missing_lifecycle_method_count"] == 0,
        "deactivate_saves_previous_and_activate_restores_it": (
            "NGT.DataAccess.Models.TourModel.Tour.set_PreviousStatusUniqueId"
            in lifecycle["DeactivateTour"]["state_references_in_order"]
            and "NGT.DataAccess.Models.TourModel.Tour.get_PreviousStatusUniqueId"
            in lifecycle["ActivateTour"]["state_references_in_order"]
        ),
        "tour_received_can_reference_received_and_finished": {
            "TourStatus.get_Received",
            "TourStatus.get_Finished",
        }.issubset(set(lifecycle["TourReceived"]["state_references_in_order"])),
        "tour_sent_and_ready_back_use_transactional_direct_nonquery": all(
            lifecycle[name]["mutation_calls_in_order"]
            == [
                "System.Data.Entity.Database.BeginTransaction",
                "DatabaseExtensions.ExecuteNonQuery",
                "System.Data.Entity.DbContextTransaction.Commit",
            ]
            for name in ("TourSent", "backToReadySendStatusTour")
        ),
        "customer_call_add_update_has_19_mutations_without_local_begin": len(
            lifecycle["AddOrUpdateCustomerCallFromDevice"]["mutation_calls_in_order"]
        )
        == 19
        and "System.Data.Entity.Database.BeginTransaction"
        not in lifecycle["AddOrUpdateCustomerCallFromDevice"]["mutation_calls_in_order"],
        "save_tour_is_only_direct_call_update_caller": len(
            runtime["direct_static_callers"][
                "NGT.Business.Domain.CustomerCallDomain.AddOrUpdateCustomerCallFromDevice"
            ]
        )
        == 1
        and "<SaveTourData>"
        in runtime["direct_static_callers"][
            "NGT.Business.Domain.CustomerCallDomain.AddOrUpdateCustomerCallFromDevice"
        ][0]["owner"],
        "29_lifecycle_endpoints_are_selected": len(lifecycle_endpoints) == 29,
        "24_get_and_five_post_lifecycle_endpoints": sum(
            "GET" in row["http_verbs"] for row in lifecycle_endpoints
        )
        == 24
        and sum("POST" in row["http_verbs"] for row in lifecycle_endpoints) == 5,
        "all_lifecycle_endpoints_have_one_ngt_authorization": all(
            row["ngt_authorize_attribute_count"] == 1 for row in lifecycle_endpoints
        ),
        "authorization_shapes_are_25_resource_and_four_roles": sum(
            row["ngt_authorization_shapes"] == ["resource_and_action"]
            for row in lifecycle_endpoints
        )
        == 25
        and sum(
            row["ngt_authorization_shapes"] == ["roles_or_empty_only"]
            for row in lifecycle_endpoints
        )
        == 4,
        "risk_register_valid_65": risks["validation"] == "PASS"
        and risks["summary"]["risk_count"] == 84
        and risks["summary"]["high_count"] == 31,
        "state_risk_extended_without_incident_claim": state_risk is not None
        and "only 455 Tours retain a PreviousStatus" in state_risk["failure_mode"]
        and "a current user incident is not asserted" in state_risk["failure_mode"],
        "get_transport_risk_is_high_and_auth_caveated": get_risk is not None
        and get_risk["severity"] == "HIGH"
        and "24 are declared GET" in get_risk["failure_mode"]
        and "anonymous reachability or a current unauthorized incident is not asserted"
        in get_risk["failure_mode"],
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
        "artifact": "varanegar_ngt_tour_call_checkpoint_20260829",
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
            "tour_count": sql_summary["tour_count"],
            "customer_call_count": sql_summary["customer_call_count"],
            "cross_type_visit_status_count": status_integrity[
                "wrong_base_type_visit_status_count"
            ],
            "previous_status_present_count": tour_aggregate["previous_status_present_count"],
            "duplicate_tour_customer_group_count": duplicates[
                "duplicate_tour_customer_group_count"
            ],
            "lifecycle_method_count": runtime_summary["lifecycle_method_count"],
            "lifecycle_get_endpoint_count": sum(
                "GET" in row["http_verbs"] for row in lifecycle_endpoints
            ),
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
