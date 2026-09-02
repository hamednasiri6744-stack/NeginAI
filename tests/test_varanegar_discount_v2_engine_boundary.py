from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "artifacts/varanegar_analysis/domains/discount_v2_engine_runtime_20260829.json"
SQL = ROOT / "artifacts/varanegar_analysis/domains/discount_v2_dynamic_rule_sql_20260829.json"
FAMILIES = ROOT / "artifacts/varanegar_analysis/domains/discount_v2_condition_families_20260829.json"
AUTHORING = ROOT / "artifacts/varanegar_analysis/domains/discount_rule_authoring_boundary_20260829.json"
AUTHORIZATION = ROOT / "artifacts/varanegar_analysis/domains/discount_rule_authorization_boundary_20260829.json"
DOC = ROOT / "docs/varanegar_reconstruction/DISCOUNT_V2_ENGINE_PIPELINE_AND_DYNAMIC_RULE_BOUNDARY_20260829_FA.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_engine_is_hash_pinned_and_statically_bounded() -> None:
    data = _load(ENGINE)
    assert data["validation"] == "PASS"
    assert data["summary"]["engine_assembly_count"] == 3
    assert data["summary"]["managed_type_count"] == 713
    assert data["summary"]["managed_method_count"] == 7156
    assert data["summary"]["selected_method_count"] == 22
    assert data["summary"]["selected_instruction_count"] == 3743
    assert data["safety"]["assembly_loads_or_executions"] == 0


def test_algorithm_pipeline_order_is_proven() -> None:
    assertions = _load(ENGINE)["assertions"]
    assert assertions["public_calculate_delegates_to_sds_do_evc"]
    assert assertions["main_pipeline_contains_validation_usance_price_statute_and_special_value"]
    assert assertions["statute_pipeline_order_is_preserved"]
    assert assertions["fill_pipeline_contains_rule_selection_and_advanced_condition"]


def test_advanced_conditions_are_executable_rule_text() -> None:
    data = _load(ENGINE)
    assert data["summary"]["advanced_condition_helper_count"] == 2
    assert data["summary"]["dynamic_rule_executor_count"] == 2
    assert data["assertions"]["advanced_condition_reads_sqlcondition_and_executes_scalar_sql"]
    assert data["assertions"]["advanced_condition_uses_sp_executesql_with_parameters"]
    assert data["assertions"]["sds_helper_contains_base_to_temp_name_rewrite_literals"]
    assert data["assertions"]["sds_object_rewrite_pairs_are_exact_and_ordered"]
    assert data["summary"]["sds_exact_object_rewrite_pair_count"] == 4
    assert data["assertions"]["apply_summary_delegates_once_to_advanced_condition_helper"]
    assert data["assertions"]["selected_calcdata_constructor_fixes_backoffice_type_one"]
    assert data["assertions"]["advanced_condition_gate_accepts_backoffice_type_one"]
    assert data["assertions"]["sds_helper_captures_and_prefers_injected_context"]
    assert data["summary"]["sds_injected_context_preference_count"] == 1
    assert data["assertions"][
        "sds_advanced_condition_executes_one_dynamic_query_per_enumerated_candidate"
    ]
    assert data["assertions"]["sds_true_branch_reads_and_deletes_item_include_staging"]
    assert data["summary"]["sds_per_candidate_dynamic_query_loop_count"] == 1


def test_read_only_snapshot_profiles_rules_without_persisting_text() -> None:
    data = _load(SQL)
    assert data["validation"] == "PASS"
    assert data["summary"]["primary_rule_count"] == 5098
    assert data["summary"]["primary_nonempty_condition_count"] == 845
    assert data["summary"]["primary_active_nonempty_condition_count"] == 626
    assert data["summary"]["primary_distinct_condition_hash_count"] == 44
    assert data["safety"]["raw_conditions_persisted"] == 0
    assert data["safety"]["row_identifiers_persisted"] == 0
    assert data["safety"]["data_mutations"] == 0


def test_current_condition_corpus_has_no_write_or_external_shape() -> None:
    data = _load(SQL)
    assert data["summary"]["primary_write_dml_shape_count"] == 0
    assert data["summary"]["primary_ddl_or_permission_shape_count"] == 0
    assert data["summary"]["primary_external_or_delay_shape_count"] == 0
    primary = next(row for row in data["sources"] if row["qualified_table"] == "SLE.tblDiscount")
    assert primary["lexical_shape_counts"]["select"] == 844
    assert primary["lexical_shape_counts"]["evc_id_parameter"] == 843
    assert primary["lexical_shape_counts"]["result_parameter"] == 844
    assert primary["lexical_shape_counts"]["temporary_evc_object"] == 793


def test_document_requires_typed_versioned_rule_replacement() -> None:
    text = DOC.read_text(encoding="utf-8-sig")
    for marker in ("AST/DSL", "۴۴ الگو", "sp_executesql", "RuleEvaluationTrace", "Golden Case"):
        assert marker in text


def test_rule_authoring_and_execution_validation_path_is_static_and_bounded() -> None:
    data = _load(AUTHORING)
    assert data["validation"] == "PASS"
    assert data["summary"]["source_assembly_count"] == 5
    assert data["summary"]["selected_method_count"] == 32
    assert data["summary"]["selected_instruction_count"] == 2183
    assert data["summary"]["selected_sql_condition_setter_method_count"] == 2
    assert data["summary"]["validation_adapter_dynamic_execute_count"] == 4
    assert data["summary"]["method_local_authorization_reference_count"] == 12
    assert data["summary"]["discount_specific_method_local_authorization_reference_count"] == 0
    assert data["summary"]["internal_command_permission_recheck_count"] == 0
    assert data["summary"]["session_permission_lookup_method_count"] == 2
    assert data["summary"]["session_permission_lookup_database_call_count"] == 0
    assert data["summary"]["base_permission_allowlisted_keys"] == ["Delete", "Edit", "New", "Print"]
    assert data["summary"]["assertion_pass_count"] == 19
    assert data["safety"]["assemblies_loaded_or_executed"] == 0
    assert data["safety"]["dynamic_conditions_executed"] == 0
    assert all(data["assertions"].values())
    assert not data["authorization_interpretation"]["outer_menu_or_base_form_authorization_disproven"]
    assert data["authorization_interpretation"]["base_form_toolbar_permission_gate_proven"]
    assert not data["authorization_interpretation"]["internal_command_permission_recheck_proven"]
    assert data["authorization_interpretation"]["permission_lookup_source"] == "IN_MEMORY_USER_PERMISSION_SNAPSHOT"
    assert not data["authorization_interpretation"]["admin_bypass_computed_inside_selected_lookup_proven"]
    assert not data["authorization_interpretation"]["configured_view_child_consumed_by_selected_list_base_permission_method_proven"]
    assert not data["authorization_interpretation"]["separate_save_permission_key_in_selected_list_base_proven"]
    assert not data["security_interpretation"]["runtime_validation_is_equivalent_to_allowlisted_dsl"]


def test_rule_route_has_crud_capabilities_but_no_review_publish_split() -> None:
    data = _load(AUTHORIZATION)
    assert data["validation"] == "PASS"
    assert data["summary"]["root_access_node_id"] == 404
    assert data["summary"]["authorization_node_count"] == 5
    assert data["summary"]["command_node_count"] == 4
    assert data["summary"]["visible_command_node_count"] == 4
    assert data["summary"]["active_user_count"] == 141
    assert data["summary"]["admin_bypass_count"] == 7
    assert data["summary"]["root_effective_allow_count"] == 15
    assert data["summary"]["root_neutral_no_allow_count"] == 126
    assert data["summary"]["command_effective_allow_counts"] == {
        "Delete": 15, "Edit": 15, "New": 15, "View": 15,
    }
    assert set(data["summary"]["command_explicit_deny_counts"].values()) == {0}
    assert data["interpretation"]["separate_view_new_edit_delete_nodes_proven"]
    assert not data["interpretation"]["separate_review_or_publish_node_proven"]
    assert not data["interpretation"]["same_effective_allow_count_proves_same_principals"]
    assert data["safety"]["identities_or_group_names_persisted"] == 0
    assert data["safety"]["write_statements_executed"] == 0


def test_condition_families_are_sanitized_and_usage_prioritized() -> None:
    data = _load(FAMILIES)
    assert data["validation"] == "PASS"
    assert data["summary"]["condition_family_count"] == 44
    assert data["summary"]["three_month_used_condition_family_count"] == 2
    assert data["summary"]["current_effective_rule_instance_count"] == 57
    assert data["summary"]["current_effective_condition_family_count"] == 16
    assert data["summary"]["business_window_date_overlap_rule_instance_count"] == 267
    assert data["summary"]["business_window_date_overlap_condition_family_count"] == 36
    assert data["summary"]["advanced_deactivated_before_window_rule_count"] == 218
    assert data["summary"]["advanced_deactivated_inside_window_rule_count"] == 2
    assert data["summary"]["advanced_current_active_with_deactivation_log_count"] == 1
    assert data["assertions"]["deactivation_log_is_one_way_and_one_row_per_rule"]
    assert data["summary"]["three_month_used_advanced_rule_count"] == 3
    assert data["summary"]["three_month_advanced_condition_applied_row_count"] == 471
    assert data["summary"]["three_month_advanced_condition_distinct_sale_count"] == 38
    assert data["summary"]["three_month_advanced_applied_row_share_percent"] == 0.1568
    assert data["summary"]["column_candidate_count"] == 23
    assert data["summary"]["from_join_object_reference_count"] == 6
    used = [row for row in data["families"] if row["three_month_applied_row_count"] > 0]
    assert len(used) == 2
    assert all(row["structure"]["from_join_object_refs"] == ["evcitemfull"] for row in used)
    assert {tuple(row["structure"]["column_candidates"]) for row in used} == {
        ("id",),
        ("brandname", "id"),
    }
    by_length = {row["condition_length"]: row for row in used}
    assert by_length[199]["three_month_used_current_active_rule_instance_count"] == 2
    assert by_length[214]["three_month_used_deactivated_inside_window_rule_instance_count"] == 1
    object_profiles = {
        row["name"]: row for row in data["vocabulary"]["from_join_object_profiles"]
    }
    assert object_profiles["#tbltempevc"]["rule_instance_count"] == 793
    assert object_profiles["#tbltempevc"]["condition_family_count"] == 9
    assert object_profiles["#tbltempevc"]["current_effective_rule_instance_count"] == 41
    assert object_profiles["#tbltempevc"]["three_month_applied_row_count"] == 0
    assert object_profiles["evcitemfull"]["rule_instance_count"] == 52
    assert object_profiles["evcitemfull"]["condition_family_count"] == 35
    assert object_profiles["evcitemfull"]["current_effective_rule_instance_count"] == 16
    assert object_profiles["evcitemfull"]["three_month_applied_row_count"] == 471
    assert data["safety"]["raw_conditions_persisted"] == 0
    assert data["safety"]["rule_identifiers_persisted"] == 0
