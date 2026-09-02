import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "ngt_authorization_runtime_boundary_20260828.json"
)
EFFECTIVE_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "ngt_authorization_effective_boundary_20260828.json"
)
ENDPOINT_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "ngt_authorization_endpoint_coverage_20260828.json"
)
RISK_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_risk_register_20260829.json"
)
TRACE_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_requirements_traceability_20260829.json"
)
MANUAL_GUARD_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "ngt_authorization_manual_guard_boundary_20260829.json"
)
ROLE_SHORT_CIRCUIT_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "ngt_authorization_role_short_circuit_20260829.json"
)
AUTHORIZATION_CHECKPOINT_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "varanegar_authorization_checkpoint_20260829.json"
)
OWNER_SCOPE_RUNTIME_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "ngt_owner_scope_runtime_boundary_20260829.json"
)
OWNER_SCOPE_REPOSITORY_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "ngt_owner_scope_repository_boundary_20260829.json"
)
OWNER_SCOPE_EFFECTIVE_PATH = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "ngt_owner_scope_effective_boundary_20260829.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_static_runtime_artifact_is_complete_and_non_executing():
    payload = _load(RUNTIME_PATH)
    assert payload["artifact"] == "varanegar_ngt_authorization_runtime_boundary"
    assert payload["safety"] == {
        "mode": "READ_ONLY_STATIC_DOTNET_METADATA_AND_BOUNDED_IL",
        "assemblies_loaded_or_executed": 0,
        "config_files_read": 0,
        "resources_read": 0,
        "user_strings_read_or_persisted": 0,
        "credentials_read_or_persisted": 0,
        "database_connections": 0,
    }
    summary = payload["summary"]
    assert summary["target_file_count"] == 8
    assert summary["analyzed_file_count"] == 8
    assert summary["failed_file_count"] == 0
    assert summary["method_bodies_read"] == 678
    assert summary["method_body_error_count"] == 0
    assert len(payload["assemblies"]) == 8
    assert all(len(row["sha256"]) == 64 for row in payload["assemblies"])


def test_deployed_guard_selects_the_three_parameter_grant_one_paths():
    payload = _load(RUNTIME_PATH)
    contract = payload["runtime_guard_contract"]
    assert contract["guard_direct_query_parameter_counts"] == [3]
    assert contract["guard_group_query_parameter_counts"] == [3]
    assert contract["direct_query_grant_equality_constants"] == [1]
    assert contract["direct_query_splits_action_on_comma"] is True
    assert contract["direct_query_normalizes_action_lower_and_trim"] is True
    assert contract["direct_query_uses_exact_action_membership"] is True
    assert contract["direct_query_resource_name_equality_expression_present"] is True
    assert contract["group_query_parameter_count"] == 3
    assert contract["group_query_grant_equality_constants"] == []
    assert contract["group_query_callback_calls_direct_query"] is True
    assert contract["group_query_callback_direct_query_parameter_counts"] == [3]
    assert contract["post_union_veto_grant_equality_constants"] == [-1]
    assert contract["guard_catalog_named_call_count"] == 0
    assert contract["catalog_save_creates_atomic_principal_permissions"] is True
    assert (
        payload["summary"][
            "runtime_guard_group_query_delegates_to_grant_filtered_direct_query"
        ]
        is True
    )


def test_endpoint_attribute_coverage_is_static_complete_and_bounded():
    payload = _load(ENDPOINT_PATH)
    assert payload["artifact"] == "varanegar_ngt_authorization_endpoint_coverage"
    assert payload["safety"] == {
        "mode": "READ_ONLY_STATIC_CUSTOM_ATTRIBUTE_METADATA",
        "assemblies_loaded_or_executed": 0,
        "config_files_read": 0,
        "route_templates_persisted": 0,
        "role_values_persisted": 0,
        "arbitrary_custom_attribute_strings_persisted": 0,
        "credentials_read_or_persisted": 0,
        "database_connections": 0,
        "startup_method_bodies_read": 1,
    }
    assert len(payload["source"]["assemblies"]) == 2
    assert all(
        len(row["sha256"]) == 64 for row in payload["source"]["assemblies"]
    )
    summary = payload["summary"]
    assert summary["custom_attribute_row_count"] == 8068
    assert summary["ngt_authorize_attribute_declaration_count"] == 596
    assert summary["attribute_declared_endpoint_count"] == 784
    assert summary["endpoint_with_ngt_authorize_count"] == 595
    assert summary["endpoint_shape_counts"] == {
        "no_ngt_attribute": 189,
        "resource_and_action": 250,
        "roles_or_empty_only": 345,
    }
    assert summary["custom_attribute_parse_failure_count"] == 0


def test_endpoint_declaration_gap_and_startup_global_filter_are_not_overclaimed():
    payload = _load(ENDPOINT_PATH)
    summary = payload["summary"]
    assert summary["endpoint_with_standard_authorize_count"] == 91
    assert summary["endpoint_with_claims_authorize_count"] == 1
    assert summary["endpoint_with_allow_anonymous_count"] == 38
    assert summary["endpoint_with_bypass_authorization_count"] == 0
    assert (
        summary[
            "endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count"
        ]
        == 60
    )
    assert (
        summary[
            "mutating_endpoint_with_no_ngt_standard_claims_or_anonymous_declaration_count"
        ]
        == 38
    )
    startup = payload["startup_global_filter_contract"]
    assert startup == {
        "method": "NGT.WebApi.Startup.ConfigureWebApi",
        "instruction_count": 39,
        "map_http_attribute_routes_call_present": True,
        "global_filter_add_call_count": 2,
        "constructed_filter_like_types": [
            "Anatoli.Common.WebApi.CatchExceptionsAttribute",
            "Anatoli.Common.WebApi.ValidateModelAttribute",
        ],
        "authorization_named_constructor_count": 0,
    }
    assert any(
        "manual authorization checks" in line
        for line in payload["evidence_limits"]
    )


def test_effective_artifact_preserves_clone_read_only_boundary():
    payload = _load(EFFECTIVE_PATH)
    safety = payload["safety"]
    assert safety["target_is_local"] is True
    assert safety["database_name"] == "NeginPakhsh_WebDev"
    assert safety["updateability"] == "READ_ONLY"
    assert safety["can_update"] == 0
    assert safety["denies_data_writes"] == 1
    assert safety["operational_procedures_executed"] == 0
    assert safety["assemblies_loaded_or_executed"] == 0
    assert safety["identity_values_read_or_persisted"] == 0
    assert safety["raw_membership_or_permission_rows_persisted"] == 0


def test_snapshot_direction_and_principal_kind_are_aggregate_only():
    payload = _load(EFFECTIVE_PATH)
    rows = payload["snapshot"]["atomic_direction_distribution_by_principal_kind"]
    assert rows == [
        {
            "principal_kind": "group",
            "grant_value": 0,
            "permission_rows": 2093,
            "principals": 7,
            "permissions": 345,
        },
        {
            "principal_kind": "group",
            "grant_value": 1,
            "permission_rows": 322,
            "principals": 7,
            "permissions": 128,
        },
        {
            "principal_kind": "user",
            "grant_value": 1,
            "permission_rows": 2,
            "principals": 2,
            "permissions": 1,
        },
    ]
    assert payload["summary"]["atomic_zero_rows"] == 2093
    assert payload["summary"]["atomic_one_rows"] == 324


def test_catalog_direct_links_are_materialized_with_same_direction():
    payload = _load(EFFECTIVE_PATH)
    catalog = payload["snapshot"]["catalog_direct_link_materialization"]
    assert catalog == {
        "distinct_direct_link_expansions": 2415,
        "matched_atomic_same_direction": 2415,
        "missing_atomic_same_direction": 0,
        "atomic_opposite_direction": 0,
        "principal_catalog_rows": 2415,
        "catalog_permission_links": 345,
    }
    assert (
        payload["summary"][
            "catalog_direct_link_expansion_fully_matches_atomic_direction"
        ]
        is True
    )


def test_negative_one_veto_is_dormant_in_current_snapshot():
    payload = _load(EFFECTIVE_PATH)
    assert payload["snapshot"]["direction_value_window"] == {
        "atomic_negative_one": 0,
        "atomic_outside_zero_one": 0,
        "catalog_negative_one": 0,
        "catalog_outside_zero_one": 0,
    }
    assert payload["summary"]["runtime_post_union_negative_one_veto_present"] is True
    assert payload["summary"]["snapshot_negative_one_row_count"] == 0
    assert payload["summary"]["legacy_to_ngt_crosswalk_proven"] is False
    assert payload["summary"]["runtime_endpoint_coverage_proven"] is False


def test_resource_action_contracts_are_compared_after_runtime_normalization():
    payload = _load(EFFECTIVE_PATH)
    coverage = payload["snapshot"]["endpoint_permission_contract_coverage"]
    assert coverage["declared_endpoint_resource_action_count"] == 251
    assert coverage["unique_normalized_resource_action_count"] == 128
    assert coverage["permission_row_match_count_distribution"] == {
        "0": 3,
        "1": 100,
        "2": 12,
        "3": 7,
        "5": 3,
        "8": 1,
        "9": 1,
        "15": 1,
    }
    assert coverage["absent_contract_count"] == 3
    assert coverage["multirow_contract_count"] == 25
    assert coverage["resource_action_absent_from_all_application_owners"] == [
        {"resource": "AreaLayer", "action": "View"},
        {"resource": "Tours", "action": "ConfirmTourReceived"},
        {"resource": "Tours", "action": "Viewpreview"},
    ]
    assert (
        payload["summary"][
            "resource_action_contract_absent_from_all_application_owners_count"
        ]
        == 3
    )


def test_declaration_gaps_follow_async_bodies_without_inventing_enforcement():
    payload = _load(MANUAL_GUARD_PATH)
    assert payload["artifact"] == "varanegar_ngt_authorization_manual_guard_boundary"
    assert payload["safety"] == {
        "mode": "READ_ONLY_STATIC_ENDPOINT_AND_ASYNC_IL",
        "assemblies_loaded_or_executed": 0,
        "config_files_read": 0,
        "user_strings_read_or_persisted": 0,
        "route_templates_read_or_persisted": 0,
        "role_or_identity_values_read_or_persisted": 0,
        "credentials_read_or_persisted": 0,
        "database_connections": 0,
    }
    assert payload["summary"] == {
        "selected_declaration_gap_endpoint_count": 60,
        "async_state_machine_followed_count": 43,
        "body_error_count": 0,
        "endpoint_with_manual_authorization_decision_candidate_count": 0,
        "endpoint_with_authorization_data_only_candidate_count": 6,
        "endpoint_with_identity_context_only_candidate_count": 3,
        "endpoint_without_named_authorization_decision_data_or_identity_signal_count": 51,
        "endpoint_without_named_manual_authorization_decision_signal_count": 60,
        "mutating_endpoint_without_named_manual_authorization_decision_signal_count": 38,
    }
    assert len(payload["endpoints"]) == 60
    assert all(
        not row["manual_authorization_decision_candidate"]
        for row in payload["endpoints"]
    )
    assert any("does not exclude" in line for line in payload["evidence_limits"])


def test_admin_role_short_circuit_is_exact_and_identity_free():
    payload = _load(ROLE_SHORT_CIRCUIT_PATH)
    assert payload["artifact"] == "varanegar_ngt_authorization_role_short_circuit"
    assert payload["safety"] == {
        "mode": "READ_ONLY_STATIC_TARGETED_AUTHORIZATION_IL",
        "assemblies_loaded_or_executed": 0,
        "config_files_read": 0,
        "allowlisted_code_role_literals_read_or_persisted": 1,
        "arbitrary_user_strings_read_or_persisted": 0,
        "runtime_role_or_identity_values_read_or_persisted": 0,
        "credentials_read_or_persisted": 0,
        "database_connections": 0,
    }
    assert payload["summary"] == {
        "target_method_count": 4,
        "target_method_body_error_count": 0,
        "admin_role_short_circuits_base_authorization": True,
        "non_admin_delegates_to_base_authorization": True,
        "base_web_permission_precedes_standard_authentication_and_roles": True,
        "explicit_endpoint_bypass_declaration_count": 0,
    }
    contract = payload["contract"]
    assert contract["admin_role_literal"] == "admin"
    assert contract["derived_role_lookup_call_count"] == 2
    assert contract["admin_predicate_is_case_insensitive_exact_equality"] is True
    assert contract["admin_true_branch_precedes_base_authorization"] is True
    assert contract["non_admin_path_calls_base_authorization"] is True
    assert contract["base_checks_current_or_peer_attribute_bypass"] is True
    assert contract["base_web_permission_check_precedes_standard_authorize"] is True
    assert contract["base_handles_web_permission_failure_as_unauthorized"] is True
    assert contract["roles_or_empty_only_endpoint_count"] == 345
    assert contract["roles_only_endpoint_with_roles_contract_count"] == 344


def test_admin_short_circuit_has_current_aggregate_assignments_without_identities():
    payload = _load(EFFECTIVE_PATH)
    assert payload["snapshot"]["admin_role_population_without_identities"] == {
        "admin_role_rows": 1,
        "admin_assignment_rows": 3,
        "admin_subjects": 3,
    }
    assert payload["summary"]["admin_role_short_circuits_base_authorization"] is True
    assert payload["summary"]["admin_role_current_assignment_subject_count"] == 3


def test_effective_artifact_contains_no_identity_or_secret_fields():
    payload = _load(EFFECTIVE_PATH)
    forbidden = {
        "username",
        "name",
        "fullname",
        "email",
        "phone",
        "password",
        "passwordhash",
        "token",
        "apikey",
        "principalid",
        "userid",
        "usergroupid",
        "permissionid",
    }

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = key.casefold().replace("_", "")
                assert normalized not in forbidden
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)


def test_owner_scope_runtime_fallback_and_guard_split_are_static_and_explicit():
    payload = _load(OWNER_SCOPE_RUNTIME_PATH)
    assert payload["validation"] == "PASS"
    assert payload["safety"]["assemblies_loaded_or_executed"] == 0
    assert payload["safety"]["runtime_identity_or_header_values_read_or_persisted"] == 0
    assert payload["safety"]["non_scope_literals_persisted"] == 0
    summary = payload["summary"]
    assert summary["analyzed_assembly_count"] == 3
    assert summary["method_body_count"] == 12695
    assert summary["method_body_error_count"] == 1
    assert summary["scope_named_method_body_error_count"] == 0
    assert summary["selected_scope_method_count"] == 1473
    assert summary["scope_consumer_method_count"] == 298
    assert summary["scope_consumer_declaring_type_count"] == 261
    assert summary["header_fallback_chain_is_center_to_data_owner_to_owner"] is True
    assert summary["authorization_domain_one_parameter_constructor_repeats_one_key_three_times"] is True
    assert summary["web_permission_guard_reads_owner_key_but_not_data_owner_headers"] is True
    contract = payload["contract"]
    assert contract["allowlisted_owner_header_literals"] == [
        "DataOwnerCenterKey",
        "DataOwnerKey",
        "OwnerKey",
    ]
    assert contract["controller_owner_info_materializes_all_three_headers_and_current_user"] is True
    assert contract["model_validation_owner_info_materializes_all_three_headers_without_user"] is True
    assert payload["non_scope_named_body_errors"] == [
        {
            "file": "NGT.WebApi.dll",
            "owner": "NGT.WebApi.Handler.AutoMapper.ConfigDefaultAutoMapperHelper",
            "method": "ConfigModelToViewModel",
            "parameter_count": 0,
            "error_class": "MethodBodyFormatError",
            "scope_named_method_or_type": False,
        }
    ]


def test_owner_scope_repository_separates_raw_and_owner_filtered_query_paths():
    payload = _load(OWNER_SCOPE_REPOSITORY_PATH)
    assert payload["validation"] == "PASS"
    assert payload["safety"]["assemblies_loaded_or_executed"] == 0
    assert payload["safety"]["string_literal_values_persisted"] == 0
    summary = payload["summary"]
    assert summary["analyzed_assembly_count"] == 2
    assert summary["target_type_count"] == 70
    assert summary["target_method_count"] == 695
    assert summary["target_method_body_error_count"] == 0
    assert summary["authorization_repositories_inherit_owner_aware_base_count"] == 3
    assert summary["base_get_query_returns_raw_dbset"] is True
    assert summary["get_query_by_owner_applies_calc_extra_predict"] is True
    assert summary["authorization_repository_get_query_override_count"] == 0
    assert summary["authorization_permission_queries_call_raw_get_query"] is True
    assert summary["authorization_permission_query_uses_owner_filtered_repository_path"] is False
    calc = payload["contract"]["calc_extra_predict_scope_contract"]
    assert {
        "Anatoli.Common.DataAccess.Models.BaseModel.get_ApplicationOwnerId",
        "Anatoli.Common.DataAccess.Models.BaseModel.get_DataOwnerId",
        "Anatoli.Common.DataAccess.Models.BaseModel.get_DataOwnerCenterId",
    }.issubset(set(calc["scope_metadata_tokens"]))


def test_owner_scope_clone_crosscheck_is_aggregate_only_and_caveated():
    payload = _load(OWNER_SCOPE_EFFECTIVE_PATH)
    assert payload["validation"] == "PASS"
    assert payload["safety"]["updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] == 1
    assert payload["safety"]["operational_procedures_executed"] == 0
    assert payload["safety"]["write_statements_executed"] == 0
    assert payload["safety"]["owner_or_principal_identifiers_persisted"] == 0
    summary = payload["summary"]
    assert {
        "applications": 1,
        "application_owners": 1,
        "data_owners": 1,
        "data_owner_centers": 2,
        "principals": 807,
        "users": 786,
        "user_groups": 8,
        "user_group_memberships": 59,
        "permissions": 369,
        "principal_permissions": 2417,
        "hierarchy_orphan_count": 1,
        "scope_consistency_mismatch_count": 58,
        "cross_application_grant_one_row_count": 0,
        "active_group_expansion_application_mismatch_count": 0,
        "data_owner_to_center_fallback_resolves_default_center_count": 1,
    }.items() <= summary.items()
    assert summary["header_fallback_same_key_resolves_valid_full_hierarchy"] is False
    assert summary["authorization_permission_repository_path_is_owner_filtered"] is False
    assert summary["current_snapshot_cross_application_effective_grant_detected"] is False
    assert payload["permission_application_scope"]["grant_one_rows_with_complete_application_chain"] == 324
    assert payload["user_group_scope_consistency"]["membership_group_scope_mismatch"] == 0
    assert payload["user_group_scope_consistency"]["membership_user_scope_mismatch"] == 58
    assert payload["data_owner_center_status_distribution"] == [
        {
            "IsActive": False,
            "IsRemoved": False,
            "centers": 2,
            "referencing_users": 786,
            "referencing_groups": 8,
            "referencing_memberships": 59,
        }
    ]
    assert payload["interpretation"]["incident_claimed"] is False


def test_owner_scope_artifact_contains_no_identifiers_or_secrets():
    payload = _load(OWNER_SCOPE_EFFECTIVE_PATH)
    forbidden = {
        "username",
        "fullname",
        "email",
        "phone",
        "password",
        "passwordhash",
        "token",
        "apikey",
        "principalid",
        "userid",
        "usergroupid",
        "permissionid",
    }

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                assert key.casefold().replace("_", "") not in forbidden
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)


def test_route_authorization_gap_is_a_caveated_critical_target_risk():
    payload = _load(RISK_PATH)
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "risk_count": 84,
        "critical_count": 50,
        "high_count": 31,
        "medium_count": 3,
        "open_count": 84,
        "covered_module_count": 14,
        "risk_with_exit_criteria_count": 84,
        "validation_error_count": 0,
    }
    risk = next(row for row in payload["risks"] if row["id"] == "R-057")
    assert risk["severity"] == "CRITICAL"
    assert risk["modules"] == [
        "identity_authorization",
        "platform",
        "integration_migration",
    ]
    assert "60 have no NGT" in risk["failure_mode"]
    assert "anonymous reachability" in risk["failure_mode"]
    assert risk["phase_gate"] == "P0_BEFORE_ANY_WEB_COMMAND"
    assert risk["status"] == "OPEN"
    checkpoint = payload["source_checkpoint"]
    assert checkpoint["ngt_attribute_declared_endpoint_count"] == 784
    assert checkpoint["ngt_endpoint_without_authorization_declaration_count"] == 60
    assert (
        checkpoint["ngt_mutating_endpoint_without_authorization_declaration_count"]
        == 38
    )
    assert checkpoint["ngt_admin_role_short_circuits_base_authorization"] is True
    assert checkpoint["ngt_admin_role_current_assignment_subject_count"] == 3
    admin_risk = next(row for row in payload["risks"] if row["id"] == "R-058")
    assert admin_risk["severity"] == "CRITICAL"
    assert admin_risk["modules"] == ["identity_authorization", "platform"]
    assert "returns true before calling base authorization" in admin_risk["failure_mode"]
    assert "inappropriate use or an incident is not asserted" in admin_risk["failure_mode"]
    assert admin_risk["phase_gate"] == (
        "P0_BEFORE_IDENTITY_PROVISIONING_OR_WEB_COMMAND"
    )
    owner_scope_risk = next(row for row in payload["risks"] if row["id"] == "R-059")
    assert owner_scope_risk["severity"] == "CRITICAL"
    assert owner_scope_risk["modules"] == [
        "identity_authorization",
        "platform",
        "integration_migration",
    ]
    assert "all 324 effective Grant=1 rows" in owner_scope_risk["failure_mode"]
    assert "no current cross-tenant effective grant or incident is asserted" in owner_scope_risk["failure_mode"]
    assert owner_scope_risk["phase_gate"] == (
        "P0_BEFORE_IDENTITY_PROVISIONING_OR_WEB_COMMAND"
    )
    assert checkpoint["ngt_resource_action_catalog_gap_count"] == 3
    assert (
        checkpoint[
            "ngt_endpoint_without_named_manual_authorization_decision_signal_count"
        ]
        == 60
    )
    assert (
        checkpoint[
            "ngt_mutating_endpoint_without_named_manual_authorization_decision_signal_count"
        ]
        == 38
    )


def test_new_authorization_risk_is_traced_without_claiming_command_readiness():
    payload = _load(TRACE_PATH)
    assert payload["validation"] == "PASS"
    summary = payload["summary"]
    assert summary["unique_risk_count"] == 84
    assert summary["mapped_risk_assignment_count"] == 343
    assert summary["module_count"] == 14
    assert summary["traced_module_count"] == 14
    assert summary["command_ready_module_count"] == 0
    assert summary["validation_error_count"] == 0


def test_authorization_checkpoint_hashes_all_sources_and_passes_every_gate():
    payload = _load(AUTHORIZATION_CHECKPOINT_PATH)
    assert payload["artifact"] == "varanegar_authorization_checkpoint_20260829"
    assert payload["validation"] == "PASS"
    assert payload["failed_checks"] == []
    assert payload["safety"] == {
        "mode": "OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "operational_commands_executed": 0,
        "business_rows_or_identity_values_read": 0,
    }
    assert all(payload["checks"].values())
    assert payload["summary"] == {
        "source_count": 28,
        "passed_check_count": 71,
        "failed_check_count": 0,
        "authorization_endpoint_count": 784,
        "authorization_declaration_gap_count": 60,
        "mutating_authorization_declaration_gap_count": 38,
        "admin_assignment_subject_aggregate_count": 3,
        "owner_scope_membership_user_mismatch_count": 58,
        "cross_application_effective_grant_count": 0,
        "risk_count": 84,
        "critical_risk_count": 50,
        "mapped_risk_assignment_count": 343,
        "command_ready_module_count": 0,
    }
    assert len(payload["source_manifest"]) == 28
    for row in payload["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
