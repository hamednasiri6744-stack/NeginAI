import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_BOUNDARY = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "ngt_order_persistence_boundary_20260829.json"
)
RUNTIME_BOUNDARY = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "ngt_order_runtime_boundary_20260829.json"
)
AUTH_ENDPOINTS = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "ngt_authorization_endpoint_coverage_20260828.json"
)
AUTH_MANUAL = (
    ROOT / "artifacts" / "varanegar_analysis" / "domains"
    / "ngt_authorization_manual_guard_boundary_20260829.json"
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
    / "varanegar_ngt_order_checkpoint_20260829.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ngt_order_sql_boundary_is_read_only_and_identity_free():
    payload = _load(SQL_BOUNDARY)
    assert payload["artifact"] == "varanegar_ngt_order_persistence_boundary"
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "business_rows_customer_user_configuration_values_or_identifiers_persisted": 0,
        "sql_definitions_persisted": 0,
        "safe_schema_table_column_parameter_and_module_identifiers_persisted": True,
        "source_or_target_state_changed": 0,
    }
    text = SQL_BOUNDARY.read_text(encoding="utf-8")
    assert not re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        text,
    )
    assert '"definition":' not in text


def test_ngt_order_catalog_exposes_no_status_history_key_or_crosswalk_unique_key():
    payload = _load(SQL_BOUNDARY)
    assert payload["summary"] == {
        "target_table_count": 7,
        "catalog_column_count": 313,
        "order_header_count": 228284,
        "order_line_count": 1239998,
        "order_status_event_count": 0,
        "unique_or_primary_index_count": 6,
        "related_foreign_key_edge_count": 61,
        "untrusted_related_foreign_key_edge_count": 61,
        "target_trigger_count": 2,
        "state_matrix_group_count": 6,
        "partially_mapped_order_count": 1,
        "split_backoffice_order_count": 7,
        "target_sql_module_count": 69,
        "activity_month_bucket_count": 4,
        "mapping_strategy_count": 4,
    }
    indexes = payload["target_unique_index_contracts"]
    assert all(row["key_columns"] == ["Id"] for row in indexes)
    assert not any(
        row["qualified_table"] == "NGT.CustomerCallOrderStatus" for row in indexes
    )
    assert all(row["is_disabled"] is False for row in payload["related_foreign_key_contracts"])
    assert all(row["is_not_trusted"] is True for row in payload["related_foreign_key_contracts"])


def test_ngt_order_header_has_two_disjoint_current_crosswalk_shapes():
    contract = _load(SQL_BOUNDARY)["header_state_contract"]
    aggregate = contract["aggregate"]
    assert aggregate["active_count"] == 228284
    assert aggregate["removed_count"] == 0
    assert aggregate["canceled_count"] == 273
    assert aggregate["sent_to_console_count"] == 218489
    assert aggregate["sent_without_numeric_order_id_count"] == 218489
    assert aggregate["backoffice_order_id_count"] == 9795
    assert aggregate["unsent_with_numeric_order_id_count"] == 9795
    assert aggregate["backoffice_order_uuid_count"] == 0
    assert aggregate["backoffice_invoice_id_count"] == 9795
    assert aggregate["backoffice_invoice_uuid_count"] == 3593
    duplicates = contract["duplicate_crosswalk_groups"]
    assert duplicates == {
        "duplicate_numeric_backoffice_order_id_group_count": 1125,
        "headers_in_duplicate_numeric_order_id_groups": 3385,
        "maximum_headers_per_numeric_backoffice_order_id": 13,
        "duplicate_numeric_backoffice_invoice_id_group_count": 1125,
        "maximum_headers_per_numeric_backoffice_invoice_id": 13,
        "duplicate_backoffice_invoice_uuid_group_count": 0,
    }


def test_ngt_order_line_crosswalk_is_more_complete_but_not_one_to_one():
    contract = _load(SQL_BOUNDARY)["line_persistence_contract"]
    assert contract["aggregate"] == {
        "line_count": 1239998,
        "active_line_count": 1220840,
        "orphan_line_count": 0,
        "active_line_under_removed_header_count": 0,
        "numeric_backoffice_order_ref_count": 1118244,
        "backoffice_order_uuid_count": 1118244,
        "numeric_ref_without_uuid_count": 0,
        "active_unmapped_line_under_mapped_header_count": 62655,
        "active_mapped_line_under_unmapped_header_count": 1118244,
        "parent_scope_mismatch_count": 0,
    }
    assert contract["parent_mapping_groups"] == {
        "order_with_lines_count": 228284,
        "all_active_lines_mapped_order_count": 212231,
        "partially_mapped_order_count": 1,
        "split_backoffice_order_count": 7,
        "maximum_backoffice_orders_per_ngt_order": 2,
    }
    matrix = {
        (row["has_numeric_header_order_id"], row["active_line_mapping_state"]): row
        for row in contract["header_line_mapping_matrix"]
    }
    assert matrix[(0, "ALL_MAPPED")]["order_count"] == 212231
    assert matrix[(1, "NONE_MAPPED")]["order_count"] == 9795
    assert matrix[(0, "PARTIAL")]["order_count"] == 1


def test_ngt_order_quantity_children_have_current_parent_and_scope_integrity():
    rows = _load(SQL_BOUNDARY)["quantity_detail_contracts"]
    assert [row["row_count"] for row in rows] == [1290047, 32642]
    for row in rows:
        assert row["orphan_line_count"] == 0
        assert row["active_detail_under_removed_line_count"] == 0
        assert row["parent_scope_mismatch_count"] == 0


def test_ngt_crosswalk_strategies_overlap_in_the_three_month_update_window():
    timeline = _load(SQL_BOUNDARY)["crosswalk_mapping_strategy_timeline"]
    all_time = {row["mapping_strategy"]: row for row in timeline["all_time"]}
    assert all_time["ALL_ACTIVE_LINES_ONLY"]["order_count"] == 212231
    assert all_time["HEADER_NUMERIC_ONLY"]["order_count"] == 9795
    assert all_time["NO_NUMERIC_CROSSWALK"]["order_count"] == 6257
    assert all_time["PARTIAL_ACTIVE_LINES_ONLY"]["order_count"] == 1
    window = timeline["window_month_buckets"]
    for month in ("2026-06", "2026-07", "2026-08"):
        strategies = {row["mapping_strategy"] for row in window if row["month_bucket"] == month}
        assert "ALL_ACTIVE_LINES_ONLY" in strategies
        assert "HEADER_NUMERIC_ONLY" in strategies


def test_ngt_replication_procedure_is_fingerprinted_not_executed():
    payload = _load(SQL_BOUNDARY)
    procedure = payload["replication_procedure_contract"]
    assert procedure["qualified_name"] == "dbo.NGT_DoReplicateTour"
    assert [row["parameter_name"] for row in procedure["parameters"]] == [
        "@TourId",
        "@DataOwnerCenterId",
        "@AppUserUniqueId",
        "@PreviewOrderMode",
        "@OrderGuid",
    ]
    assert procedure["result_set_contract"] == [
        {
            "column_ordinal": 0,
            "column_name": None,
            "system_type_name": None,
            "is_nullable": None,
            "error_number": 229,
        }
    ]
    profile = next(
        row
        for row in payload["target_sql_module_profiles"]
        if row["qualified_name"] == "dbo.NGT_DoReplicateTour"
    )
    assert profile["definition_length"] == 61020
    assert profile["begin_transaction_token_count"] == 1
    assert profile["commit_token_count"] == 0
    assert profile["rollback_token_count"] == 1
    assert profile["throw_or_raiserror_token_count"] == 4
    assert "ngt.customercallorders" in {
        value.casefold() for value in profile["safe_sql_object_references"]
    }


def test_ngt_order_runtime_orchestration_is_static_and_multi_stage():
    payload = _load(RUNTIME_BOUNDARY)
    assert payload["artifact"] == "varanegar_ngt_order_runtime_boundary"
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
        "selected_method_count": 1859,
        "runtime_selection_method_count": 158,
        "mutation_method_count": 78,
        "explicit_transaction_method_count": 17,
        "key_runtime_method_count": 360,
    }
    contract = payload["key_orchestration_contract"]
    assert contract["save_tour_data"] == {
        "instruction_count": 8960,
        "begin_transaction_call_count": 1,
        "commit_call_count": 1,
        "rollback_call_count": 2,
        "replicate_tour_call_count": 4,
        "safe_sql_object_references": [
            "NGT.NGT_TourValidation",
            "dbo.USP_NGT_SaveRecomendationResult",
        ],
    }
    assert contract["replicate_tour"]["instruction_count"] == 15532
    assert contract["replicate_tour"]["new_replicate_tour_call_count"] == 1
    assert contract["replicate_tour"]["replicate_to_backoffice_call_count"] == 2
    assert contract["new_replicate_tour"]["safe_sql_object_references"] == [
        "dbo.NGT_DoReplicateTour"
    ]
    assert len(contract["save_tour_data_callers"]) == 4
    assert len(contract["replicate_tour_callers"]) == 6


def test_ngt_update_path_has_five_persistence_stages_without_local_transaction_claim():
    contract = _load(RUNTIME_BOUNDARY)["key_orchestration_contract"]
    assert contract["update_tour"] == {
        "calls_update_from_ngt": True,
        "begin_transaction_call_count": 0,
    }
    assert contract["update_order_from_ngt"] == {
        "instruction_count": 2407,
        "save_changes_call_count": 5,
        "begin_transaction_call_count": 0,
        "sets_removed_state": True,
    }
    writer = contract["order_status_writer"]
    assert writer["direct_static_caller_count"] == 1
    assert writer["direct_static_callers"][0]["owner"] == (
        "NGT.WebApi.Controllers.V2.CustomerCallController+"
        "<AddToCustomerCallOrderStatus>d__18"
    )
    assert writer["begin_transaction_call_count"] == 1
    assert writer["commit_call_count"] == 1


def test_order_save_authorization_gap_is_contextualized_without_reachability_claim():
    endpoints = _load(AUTH_ENDPOINTS)["endpoints"]
    endpoint = next(
        row
        for row in endpoints
        if row["controller"] == "NGT.WebApi.Controllers.V2.OrderController"
        and row["method"] == "RequestSaveTourData"
    )
    assert endpoint["http_verbs"] == ["POST"]
    assert endpoint["ngt_authorize_attribute_count"] == 0
    assert endpoint["standard_authorize_declared_or_inherited"] is False
    assert endpoint["claims_authorize_declared_or_inherited"] is False
    assert endpoint["allow_anonymous_declared_or_inherited"] is False
    manual = next(
        row
        for row in _load(AUTH_MANUAL)["endpoints"]
        if row["controller"] == "NGT.WebApi.Controllers.V2.OrderController"
        and row["method"] == "RequestSaveTourData"
    )
    assert manual["manual_authorization_decision_candidate"] is False
    assert manual["identity_context_only_candidate"] is True


def test_existing_critical_order_risk_absorbs_new_ngt_evidence_without_new_count():
    risks = _load(RISK)
    assert risks["validation"] == "PASS"
    assert risks["summary"]["risk_count"] == 84
    risk = next(row for row in risks["risks"] if row["id"] == "R-033")
    assert risk["severity"] == "CRITICAL"
    assert "212,231 NGT orders are fully mapped only through active lines" in risk["failure_mode"]
    assert "a current partial-write incident is not asserted" in risk["failure_mode"]
    assert risk["evidence_refs"][-2].endswith(
        "artifacts/varanegar_analysis/domains/ngt_order_persistence_boundary_20260829.json"
    )
    assert risk["evidence_refs"][-1].endswith(
        "artifacts/varanegar_analysis/domains/ngt_order_runtime_boundary_20260829.json"
    )
    trace = _load(TRACE)
    assert trace["validation"] == "PASS"
    assert trace["summary"]["unique_risk_count"] == 84
    assert trace["summary"]["mapped_risk_assignment_count"] == 343
    assert trace["summary"]["command_ready_module_count"] == 0


def test_ngt_order_checkpoint_is_hash_pinned_offline_and_complete():
    checkpoint = _load(CHECKPOINT)
    assert checkpoint["artifact"] == "varanegar_ngt_order_checkpoint_20260829"
    assert checkpoint["validation"] == "PASS"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["summary"] == {
        "source_count": 18,
        "passed_check_count": 37,
        "failed_check_count": 0,
        "order_header_count": 228284,
        "order_line_count": 1239998,
        "line_only_mapped_order_count": 212231,
        "header_only_mapped_order_count": 9795,
        "partially_mapped_order_count": 1,
        "split_backoffice_order_count": 7,
        "runtime_mutation_method_count": 78,
        "risk_count": 84,
        "critical_risk_count": 50,
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
    manifest = {row["name"]: row for row in checkpoint["source_manifest"]}
    assert set(manifest) == {
        "authorization_endpoints",
        "authorization_manual_guards",
        "checkpoint_builder",
        "discovery_log",
        "knowledge_doc",
        "order_doc",
        "order_tests",
        "prior_order_lifecycle",
        "rebuild_script",
        "reconstruction_readme",
        "risk_builder",
        "risk_register",
        "runtime_boundary",
        "runtime_extractor",
        "sql_boundary",
        "sql_extractor",
        "trace_builder",
        "traceability",
    }
