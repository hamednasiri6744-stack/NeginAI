import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_BOUNDARY = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "ngt_tour_call_state_boundary_20260829.json"
)
RUNTIME_BOUNDARY = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "ngt_tour_call_runtime_boundary_20260829.json"
)
AUTH_ENDPOINTS = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "ngt_authorization_endpoint_coverage_20260828.json"
)
ORDER_BOUNDARY = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "ngt_order_persistence_boundary_20260829.json"
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
    / "varanegar_ngt_tour_call_checkpoint_20260829.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_tour_call_sql_boundary_is_read_only_and_identity_free():
    payload = _load(SQL_BOUNDARY)
    assert payload["artifact"] == "varanegar_ngt_tour_call_state_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_CATALOG_AND_ANONYMOUS_STATE_AGGREGATES",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "business_rows_customer_user_location_comment_configuration_values_or_identifiers_persisted": 0,
        "sql_definitions_persisted": 0,
        "safe_schema_table_column_status_label_and_module_identifiers_persisted": True,
        "source_or_target_state_changed": 0,
    }
    text = SQL_BOUNDARY.read_text(encoding="utf-8")
    assert not re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        text,
    )
    assert '"definition":' not in text


def test_tour_call_catalog_and_state_summary_is_exact():
    assert _load(SQL_BOUNDARY)["summary"] == {
        "target_table_count": 4,
        "catalog_column_count": 162,
        "tour_count": 64561,
        "customer_call_count": 2471250,
        "semantic_status_row_count": 17,
        "tour_status_matrix_row_count": 14,
        "call_visit_order_matrix_row_count": 16,
        "unique_or_primary_index_count": 2,
        "history_or_status_named_table_count": 1,
        "target_trigger_count": 1,
        "target_sql_module_count": 95,
        "tour_month_status_bucket_count": 18,
        "call_month_status_bucket_count": 45,
    }


def test_visit_status_currently_contains_a_cross_type_delivery_state():
    contract = _load(SQL_BOUNDARY)["semantic_status_contract"]
    assert contract["reference_integrity"] == {
        "unresolved_tour_status_count": 0,
        "unresolved_call_status_count": 0,
        "unresolved_visit_status_count": 0,
        "wrong_base_type_tour_status_count": 0,
        "wrong_base_type_call_status_count": 0,
        "wrong_base_type_visit_status_count": 772,
        "removed_tour_status_reference_count": 0,
        "removed_call_status_reference_count": 0,
        "removed_visit_status_reference_count": 0,
    }
    delivery = next(
        row
        for row in contract["semantic_status_rows"]
        if row["base_type_name"] == "DistributionDeliveryStatus"
    )
    assert delivery["base_value_name"] == "تحويل قسمتي"
    assert delivery["visit_status_count"] == 772


def test_tour_current_state_retains_only_sparse_previous_status_and_two_time_reversals():
    contract = _load(SQL_BOUNDARY)["tour_state_contract"]
    aggregate = contract["aggregate"]
    assert aggregate["tour_count"] == 64561
    assert aggregate["active_count"] == 64561
    assert aggregate["removed_count"] == 0
    assert aggregate["started_count"] == 64311
    assert aggregate["ended_count"] == 63849
    assert aggregate["end_before_start_count"] == 2
    assert aggregate["previous_status_present_count"] == 455
    assert aggregate["unresolved_previous_status_count"] == 0
    assert aggregate["status_application_owner_difference_count"] == 0
    assert aggregate["status_data_owner_difference_count"] == 0
    assert aggregate["status_center_difference_count"] == 64561
    by_current = {}
    for row in contract["current_previous_status_matrix"]:
        by_current[row["current_status_name"]] = (
            by_current.get(row["current_status_name"], 0) + row["tour_count"]
        )
    assert by_current == {
        "ارسال شده": 16,
        "انصراف داده": 3419,
        "خاتمه يافته": 49354,
        "در حال دريافت اطلاعات": 78,
        "دريافت شده": 10659,
        "غيرفعال": 1035,
    }


def test_customer_calls_have_current_parent_scope_integrity_and_bounded_time_anomalies():
    aggregate = _load(SQL_BOUNDARY)["customer_call_state_contract"]["aggregate"]
    assert aggregate["call_count"] == 2471250
    assert aggregate["active_count"] == 2471250
    assert aggregate["orphan_tour_count"] == 0
    assert aggregate["active_call_under_removed_tour_count"] == 0
    assert aggregate["tour_scope_mismatch_count"] == 0
    assert aggregate["null_call_date_count"] == 16039
    assert aggregate["started_count"] == aggregate["ended_count"] == 1092628
    assert aggregate["end_before_start_count"] == 0
    assert aggregate["negative_visit_duration_count"] == 3
    assert aggregate["manual_started_count"] == aggregate["manual_ended_count"] == 0


def test_call_visit_order_matrix_preserves_pending_and_delivery_semantics():
    rows = _load(SQL_BOUNDARY)["customer_call_state_contract"][
        "call_visit_order_state_matrix"
    ]
    keyed = {
        (
            row["call_status_name"],
            row["visit_status_base_type"],
            row["visit_status_name"],
            row["has_active_order"],
        ): row["call_count"]
        for row in rows
    }
    assert keyed[("تاييد شده", "DistributionDeliveryStatus", "تحويل قسمتي", 1)] == 550
    assert keyed[("عدم قطعی", "DistributionDeliveryStatus", "تحويل قسمتي", 1)] == 222
    assert keyed[("در انتظار دريافت", "VisitStatus", "عدم قطعي", 0)] == 1375789
    assert keyed[("در انتظار دريافت", "VisitStatus", "عدم قطعي", 1)] == 2833
    assert keyed[("تاييد شده", "VisitStatus", "قطعی", 0)] == 1


def test_tour_customer_pair_is_not_a_unique_visit_identity():
    duplicate = _load(SQL_BOUNDARY)["customer_call_state_contract"][
        "duplicate_tour_customer_contract"
    ]
    assert duplicate == {
        "duplicate_tour_customer_group_count": 26613,
        "calls_in_duplicate_tour_customer_groups": 57391,
        "maximum_calls_per_tour_customer": 14,
    }


def test_tour_stored_counters_are_candidates_not_declared_invariants():
    contract = _load(SQL_BOUNDARY)["tour_counter_candidate_contract"]
    assert contract["aggregate_candidate_matches"] == {
        "tour_count": 64561,
        "tour_without_call_count": 60,
        "customer_count_matches_call_count": 17926,
        "customer_count_matches_distinct_customer_count": 19493,
        "visit_count_matches_started_call_count": 33745,
        "visit_count_matches_ended_call_count": 33745,
        "order_count_matches_ordered_call_count": 63073,
        "invoice_count_matches_invoiced_call_count": 64136,
        "negative_stored_counter_tour_count": 0,
    }
    assert "candidate equalities only" in contract["interpretation"]


def test_no_complete_named_tour_call_history_surface_is_evidenced():
    payload = _load(SQL_BOUNDARY)
    assert payload["history_or_status_named_table_candidates"] == [
        {
            "schema_name": "NGT",
            "table_name": "CustomerCallOrderStatus",
            "name_signals_history": 0,
            "name_signals_status": 1,
        }
    ]
    assert _load(ORDER_BOUNDARY)["summary"]["order_status_event_count"] == 0
    assert payload["target_trigger_contracts"] == [
        {
            "qualified_table": "NGT.Tours",
            "trigger_name": "Trg_Tours_CheckTourStatusUniqueId",
            "is_disabled": False,
            "is_instead_of_trigger": False,
            "definition_sha256": "477031e6d46853acb3ff4f5f69f0d0ea1fac78c97c12a59443e6b0dcb6756da7",
            "definition_length": 829,
            "uuid_literal_count": 2,
            "rollback_token_count": 1,
            "throw_or_raiserror_token_count": 1,
        }
    ]


def test_tour_call_runtime_is_static_and_all_target_lifecycle_bodies_resolve():
    payload = _load(RUNTIME_BOUNDARY)
    assert payload["artifact"] == "varanegar_ngt_tour_call_runtime_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "STATIC_PE_METADATA_AND_IL_ONLY",
        "assemblies_loaded_or_executed": 0,
        "application_endpoints_or_commands_called": 0,
        "configuration_files_or_values_read": 0,
        "business_rows_or_identifiers_read": 0,
        "non_allowlisted_literals_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    assert payload["summary"] == {
        "assembly_count": 4,
        "method_body_count": 27788,
        "method_body_error_count": 3,
        "signal_named_body_error_count": 0,
        "selected_method_count": 3451,
        "focused_method_count": 217,
        "focused_mutation_method_count": 45,
        "lifecycle_method_count": 20,
        "missing_lifecycle_method_count": 0,
    }
    assert not re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        RUNTIME_BOUNDARY.read_text(encoding="utf-8"),
    )


def test_static_lifecycle_contract_preserves_transition_specific_rules():
    lifecycle = _load(RUNTIME_BOUNDARY)["lifecycle_method_contracts"]
    cancel = lifecycle["CancelTour"]
    assert "TourStatus.get_Canceled" in cancel["state_references_in_order"]
    assert "TourStatus.get_Deactivated" in cancel["state_references_in_order"]
    assert "NGT.DataAccess.Models.TourModel.Tour.set_EndTime" in cancel[
        "state_references_in_order"
    ]
    deactivate = lifecycle["DeactivateTour"]
    assert "NGT.DataAccess.Models.TourModel.Tour.set_PreviousStatusUniqueId" in deactivate[
        "state_references_in_order"
    ]
    assert "TourStatus.get_Deactivated" in deactivate["state_references_in_order"]
    activate = lifecycle["ActivateTour"]
    assert "NGT.DataAccess.Models.TourModel.Tour.get_PreviousStatusUniqueId" in activate[
        "state_references_in_order"
    ]
    received = lifecycle["TourReceived"]
    assert "TourStatus.get_Received" in received["state_references_in_order"]
    assert "TourStatus.get_Finished" in received["state_references_in_order"]
    finish = lifecycle["FinishTour"]
    assert finish["mutation_calls_in_order"] == [
        "DatabaseExtensions.ExecuteNonQuery",
        "TypeSpecRow.SaveChangesAsync",
    ]


def test_direct_nonquery_and_multi_stage_call_paths_keep_transaction_caveats():
    lifecycle = _load(RUNTIME_BOUNDARY)["lifecycle_method_contracts"]
    expected_direct = [
        "System.Data.Entity.Database.BeginTransaction",
        "DatabaseExtensions.ExecuteNonQuery",
        "System.Data.Entity.DbContextTransaction.Commit",
    ]
    assert lifecycle["TourSent"]["mutation_calls_in_order"] == expected_direct
    assert lifecycle["backToReadySendStatusTour"]["mutation_calls_in_order"] == expected_direct
    call_update = lifecycle["AddOrUpdateCustomerCallFromDevice"]
    assert len(call_update["mutation_calls_in_order"]) == 19
    assert "System.Data.Entity.Database.BeginTransaction" not in call_update[
        "mutation_calls_in_order"
    ]
    assert _load(RUNTIME_BOUNDARY)["direct_static_callers"][
        "NGT.Business.Domain.CustomerCallDomain.AddOrUpdateCustomerCallFromDevice"
    ] == [
        {
            "file": "NGT.Business.dll",
            "owner": "NGT.Business.Domain.TourDomain+<SaveTourData>d__24",
            "method": "MoveNext",
            "parameter_count": 0,
        }
    ]


def test_24_of_29_authorized_tour_lifecycle_mutations_use_get():
    names = {
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
    rows = [
        row
        for row in _load(AUTH_ENDPOINTS)["endpoints"]
        if row["controller"] == "NGT.WebApi.Controllers.V2.TourController"
        and row["method"] in names
    ]
    assert len(rows) == 29
    assert sum("GET" in row["http_verbs"] for row in rows) == 24
    assert sum("POST" in row["http_verbs"] for row in rows) == 5
    assert all(row["ngt_authorize_attribute_count"] == 1 for row in rows)
    assert sum(row["ngt_authorization_shapes"] == ["resource_and_action"] for row in rows) == 25
    assert sum(row["ngt_authorization_shapes"] == ["roles_or_empty_only"] for row in rows) == 4


def test_tour_call_evidence_extends_state_risk_and_adds_get_transport_risk():
    risks = _load(RISK)
    assert risks["validation"] == "PASS"
    assert risks["summary"]["risk_count"] == 84
    assert risks["summary"]["critical_count"] == 50
    assert risks["summary"]["high_count"] == 31
    state_risk = next(row for row in risks["risks"] if row["id"] == "R-008")
    assert "only 455 Tours retain a PreviousStatus" in state_risk["failure_mode"]
    assert "a current user incident is not asserted" in state_risk["failure_mode"]
    get_risk = next(row for row in risks["risks"] if row["id"] == "R-062")
    assert get_risk["severity"] == "HIGH"
    assert "24 are declared GET" in get_risk["failure_mode"]
    assert "anonymous reachability or a current unauthorized incident is not asserted" in get_risk[
        "failure_mode"
    ]
    trace = _load(TRACE)
    assert trace["validation"] == "PASS"
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_tour_call_checkpoint_is_hash_pinned_offline_and_complete():
    checkpoint = _load(CHECKPOINT)
    assert checkpoint["artifact"] == "varanegar_ngt_tour_call_checkpoint_20260829"
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"] == {
        "source_count": 17,
        "passed_check_count": 40,
        "failed_check_count": 0,
        "tour_count": 64561,
        "customer_call_count": 2471250,
        "cross_type_visit_status_count": 772,
        "previous_status_present_count": 455,
        "duplicate_tour_customer_group_count": 26613,
        "lifecycle_method_count": 20,
        "lifecycle_get_endpoint_count": 24,
        "risk_count": 84,
        "high_risk_count": 31,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert all(checkpoint["checks"].values())
    assert checkpoint["safety"] == {
        "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "operational_commands_executed": 0,
        "configuration_values_business_rows_or_identifiers_read": 0,
    }
    assert {row["name"] for row in checkpoint["source_manifest"]} == {
        "authorization_endpoints",
        "checkpoint_builder",
        "discovery_log",
        "knowledge_doc",
        "order_boundary",
        "rebuild_script",
        "reconstruction_readme",
        "risk_builder",
        "risk_register",
        "runtime_boundary",
        "runtime_extractor",
        "sql_boundary",
        "sql_extractor",
        "tour_call_doc",
        "tour_call_tests",
        "trace_builder",
        "traceability",
    }
