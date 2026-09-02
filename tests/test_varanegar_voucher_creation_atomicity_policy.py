from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "domains"
    / "voucher_creation_atomicity_and_policy_20260828.json"
)
SCRIPT = ROOT / "scripts" / "sql" / "extract_varanegar_voucher_creation_atomicity_policy.py"


def _load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_voucher_creation_evidence_is_read_only_and_hash_pinned() -> None:
    payload = _load()
    safety = payload["safety"]
    assert safety["updateability"] == "READ_ONLY"
    assert safety["can_update"] == 0
    assert safety["denies_data_writes"] == 1
    assert safety["operational_procedures_executed"] == 0
    assert safety["creator_views_executed"] == 0
    assert safety["assemblies_loaded_or_executed"] == 0
    hashes = payload["deployed_call_and_transaction_contract"]["assembly_hashes"]
    assert len(hashes) == 7
    assert all(row["hash_matches_inventory"] for row in hashes.values())


def test_desktop_voucher_path_binds_exact_modern_procedure_and_transaction() -> None:
    payload = _load()
    contract = payload["deployed_call_and_transaction_contract"]
    assert contract["ui_entrypoint"]["passes_null_data_context"] is True
    assert contract["business_boundary"]["transaction_mode_operand_before_context_ctor"] == 0
    assert contract["data_context_runtime"]["transaction_enum"] == {"Begin": 0, "No": 1}
    assert contract["adapter_binding"]["exact_procedure_literals"] == [
        "dbo.usp_DoExternalVoucher"
    ]
    assert contract["conclusion"]["desktop_null_context_path_has_one_outer_transaction"] is True
    assert contract["conclusion"]["procedure_owns_transaction"] is False
    assert payload["engineering_conclusion"][
        "legacy_do_external_voucher_create_is_active_desktop_path"
    ] is False


def test_modern_sql_procedure_relies_on_outer_transaction() -> None:
    payload = _load()
    procedure = payload["procedure_contracts"]["dbo.usp_DoExternalVoucher"]
    assert procedure["transaction_tokens"] == {
        "begin_transaction": 0,
        "commit": 0,
        "rollback": 0,
        "begin_try": 0,
        "begin_catch": 0,
    }
    signals = procedure["semantic_signals"]
    assert signals["calls_usp_do_pre_voucher"] is True
    assert signals["writes_external_header"] is True
    assert signals["writes_external_lines"] is True
    assert signals["writes_external_relation"] is True
    assert signals["uses_dense_rank_grouping"] is True


def test_confirm_delete_and_transfer_bind_exact_outer_transaction_paths() -> None:
    payload = _load()
    operations = payload["deployed_call_and_transaction_contract"][
        "lifecycle_operations"
    ]
    expected = {
        "confirm_or_unconfirm": "dbo.usp_DoExternalVoucherConfirmed",
        "delete_unconfirmed_batch": "dbo.usp_DoExternalVoucherDelete",
        "transfer_to_general_ledger": "dbo.usp_DoExternalVoucherTransfer",
    }
    assert set(operations) == set(expected)
    for name, procedure in expected.items():
        operation = operations[name]
        assert operation["ui_paths"]
        assert all(path["passes_null_data_context"] for path in operation["ui_paths"])
        assert operation["business_transaction_mode_operand"] == 0
        assert operation["exact_procedure_literals"] == [procedure]
        assert operation["dispose_is_in_finally"] is True
        assert operation["outer_transaction_proven"] is True
        assert operation["procedure_owns_transaction"] is False


def test_lifecycle_procedure_mutation_and_guard_contracts_are_explicit() -> None:
    payload = _load()
    procedures = payload["procedure_contracts"]
    confirm = procedures["dbo.usp_DoExternalVoucherConfirmed"]
    delete = procedures["dbo.usp_DoExternalVoucherDelete"]
    transfer = procedures["dbo.usp_DoExternalVoucherTransfer"]
    for procedure in (confirm, delete, transfer):
        assert procedure["transaction_tokens"]["begin_transaction"] == 0
        assert procedure["transaction_tokens"]["commit"] == 0
        assert procedure["transaction_tokens"]["rollback"] == 0
    assert confirm["semantic_signals"]["updates_external_confirmation"] is True
    assert confirm["semantic_signals"]["checks_concurrent_voucher_after_mutation"] is True
    delete_signals = delete["semantic_signals"]
    assert delete_signals["deletes_pre_voucher"] is True
    assert delete_signals["deletes_external_header"] is True
    assert delete_signals["deletes_external_lines"] is True
    assert delete_signals["deletes_external_relation"] is True
    assert delete_signals["uses_delete_session_context"] is True
    transfer_signals = transfer["semantic_signals"]
    assert transfer_signals["writes_voucher"] is True
    assert transfer_signals["writes_voucher_item"] is True
    assert transfer_signals["writes_voucher_status_history"] is True
    assert transfer_signals["writes_voucher_edit_log"] is True
    assert transfer_signals["writes_set_voucher_no"] is True
    assert transfer_signals["calls_transfer_validation"] is True
    assert transfer_signals["catch_reraises_error"] is True


def test_transfer_validation_has_a_reachable_prevalidation_cleanup_commit() -> None:
    payload = _load()
    signals = payload["procedure_contracts"]["dbo.usp_DoExternalVoucherTransfer"][
        "semantic_signals"
    ]
    assert signals["deletes_set_voucher_no_before_validation"] is True
    assert signals["validation_can_return_without_exception"] is True
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix["transfer validation is side-effect free"]["result"] == "FAIL"


def test_accounting_actions_lack_separate_server_enforced_authorization() -> None:
    payload = _load()
    authorization = payload["deployed_call_and_transaction_contract"][
        "authorization_and_scope_contract"
    ]
    base = authorization["base_toolbar_permission_gate"]
    assert base["permission_call_count"] > 0
    assert base["confirm_unconfirm_or_transfer_in_referenced_fields"] is False
    form = authorization["form_permission_override"]
    assert form["permission_call_count"] == 0
    assert form["hides_new_edit_view"] is True
    assert form["forces_confirm_and_unconfirm_visible"] is True
    assert authorization["custom_command_control_references"] == {
        "buttonSave": ["InitializeComponent"],
        "MenuButtonTransfer": ["CreateCustomToolStripButton"],
    }
    assert authorization["no_action_permission_call_in_form_command_methods"] is True
    assert authorization["conclusion"]["read_grid_is_session_accyear_dc_scoped"] is True
    server = authorization["server_procedure_authorization"]
    assert server["action_procedure_count"] == 4
    assert server["action_procedure_with_authorization_count"] == 0
    assert server["issue_validates_existing_dc_but_not_user_dc_scope"] is True
    assert server["issue_enforces_operation_finality"] is True
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix[
        "issue confirm unconfirm delete and transfer have separate enforceable action permissions"
    ]["result"] == "FAIL"
    assert matrix["issuance date waits for source-system finality"]["result"] == "PASS"


def test_issuance_finality_is_pre_mutation_but_purchase_coverage_is_incomplete() -> None:
    payload = _load()
    assert payload["schema_version"] == 2
    finality = payload["issuance_finality_contract"]
    semantics = finality["deployed_sql_semantics"]
    assert semantics["selected_dc_cross_selected_external_type"] is True
    assert semantics["nonpurchase_uses_min_last_date_by_system_dc_year"] is True
    assert semantics["purchase_uses_min_existing_stockdc_definite_date"] is True
    assert semantics["purchase_query_requires_every_stockdc_row"] is False
    assert semantics["operation_id_5_is_explicitly_exempt"] is True
    assert semantics["missing_finality_date_blocks_nonexempt_issue"] is True
    assert semantics["business_error_returns_result_without_exception"] is True
    assert semantics["finality_failure_is_before_first_persistent_mutation"] is True
    assert finality["operation_date_key_integrity"] == {
        "duplicate_general_operation_key_groups": 0,
        "duplicate_purchase_operation_key_groups": 0,
    }
    summary = finality["summary"]
    assert summary == {
        "configured_system_count": 5,
        "configured_operation_id_5_type_count": 2,
        "operation_id_5_retained_header_count": 0,
        "purchase_partially_covered_active_dc_year_scope_count": 3,
        "purchase_missing_stockdc_operation_row_count": 10,
        "modern_header_scope_count": 382,
        "modern_header_would_fail_current_finality_count": 0,
    }
    coverage = {row["AccYear"]: row for row in finality["purchase_stockdc_operation_row_coverage"]}
    assert coverage[1405]["max_stockdc_per_scope"] == 10
    assert coverage[1405]["max_operation_rows_per_scope"] == 8
    assert coverage[1405]["partially_covered_scope_count"] == 1
    assert coverage[1405]["wholly_missing_scope_count"] == 1
    payroll = next(
        row
        for row in finality["configured_and_retained_system_profiles"]
        if row["system_semantic"] == "payroll"
    )
    assert payroll["configured_type_count"] == 2
    assert payroll["retained_header_count"] == 0
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix["source finality rejection is pre-mutation"]["result"] == "PASS"
    assert matrix[
        "purchase finality covers every stock DC in the selected business DC"
    ]["result"] == "FAIL"
    assert matrix[
        "operation-id-5 finality exemption is covered by retained evidence"
    ]["result"] == "FAIL"


def test_issue_result_protocol_and_action_chaining_are_explicit() -> None:
    payload = _load()
    deployed = payload["deployed_call_and_transaction_contract"]
    ui = deployed["ui_entrypoint"]
    assert ui["save_action_enum"] == {
        "Issue": 1,
        "IssueAndConfirm": 2,
        "IssueAndConfirmAndSend": 3,
    }
    assert [row["call"].rsplit(".", 1)[-1] for row in ui["command_chain"]] == [
        "DoExternalVoucher",
        "DoExternalVoucherConfirmed",
        "DoExternalVoucherTransfer",
    ]
    assert ui["issue_validation_failure_returns_before_confirm"] is True
    assert ui["confirm_validation_failure_returns_before_transfer"] is True
    assert ui["successful_header_ids_are_parsed_only_from_message_type_zero"] is True
    business = deployed["business_boundary"]
    assert business["policy_preflight_occurs_before_issue_transaction"] is True
    assert business["message_type_one_is_validation_error"] is True
    assert business["result_is_set_before_commit_even_for_business_error_rows"] is True
    runtime = deployed["data_context_runtime"]
    assert runtime["exception_path_has_explicit_rollback"] is False
    assert runtime[
        "provider_dispose_disposes_transaction_before_closing_connection"
    ] is True
    signals = payload["procedure_contracts"]["dbo.usp_DoExternalVoucher"][
        "semantic_signals"
    ]
    assert signals["returns_message_type_1_for_business_errors"] is True
    assert signals["returns_message_type_0_for_created_header_ids"] is True
    assert signals["returns_message_type_2_or_3_for_warning_or_information"] is True
    assert signals["message_type_1_result_precedes_persistent_issue_mutation"] is True
    sql = payload["issuance_finality_contract"]["deployed_sql_semantics"]
    assert sql["procedure_parameters"] == [
        "@AccYear",
        "@UserRef",
        "@ExternalVoucherTypeList",
        "@DCList",
        "@ToDate",
    ]
    assert sql["policy_values_are_not_procedure_parameters"] is True
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix[
        "issue confirm and transfer chaining stops on validation failure"
    ]["result"] == "PASS"
    assert matrix[
        "issue message protocol separates errors ids warnings and information"
    ]["result"] == "PASS"
    assert matrix[
        "issuance policy preflight and applied policy share one immutable snapshot"
    ]["result"] == "FAIL"


def test_configured_voucher_types_are_not_all_current_capabilities() -> None:
    payload = _load()
    profile = payload["voucher_type_structural_validation_profile"]
    semantics = profile["deployed_validator_semantics"]
    assert semantics["called_by_issue_before_finality_check"] is True
    assert semantics["validates_view_object_and_base_columns"] is True
    assert semantics["validates_conditional_party_columns"] is True
    assert semantics[
        "validates_effective_articles_fields_ledgers_and_comments"
    ] is True
    assert semantics[
        "compiles_predicates_with_dynamic_select_where_one_equals_two"
    ] is True
    assert semantics["predicate_compile_queries_executed_by_extractor"] == 0
    assert semantics["operational_creator_views_executed_by_extractor"] == 0
    assert profile["summary"] == {
        "configured_type_count": 65,
        "structurally_candidate_type_count": 45,
        "structurally_invalid_type_count": 20,
        "invalid_type_with_retained_history_count": 0,
        "invalid_type_with_recent_history_count": 0,
        "invalid_type_with_modern_header_count": 0,
        "predicate_count_not_runtime_compiled": 71,
    }
    years = {row["AccYear"]: row for row in profile["year_profiles"]}
    assert set(years) == {1403, 1404, 1405}
    assert all(row["structurally_invalid_type_count"] == 20 for row in years.values())
    assert years[1405]["violation_reason_counts"] == [
        {
            "reason": "no_effective_article",
            "violation_row_count": 20,
            "affected_type_count": 20,
        },
        {
            "reason": "view_name_missing",
            "violation_row_count": 13,
            "affected_type_count": 13,
        },
    ]
    systems = {row["system_semantic"]: row for row in years[1405]["system_profiles"]}
    assert systems["customer_accounting"]["configured_type_count"] == 14
    assert systems["customer_accounting"]["structurally_invalid_type_count"] == 13
    assert systems["treasury"]["structurally_invalid_type_count"] == 4
    assert systems["inventory_accounting_purchase"]["structurally_invalid_type_count"] == 3
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix[
        "every configured voucher type is an issueable current capability"
    ]["result"] == "FAIL"
    assert matrix[
        "structurally invalid current types are absent from retained operational use"
    ]["result"] == "PASS"
    assert matrix[
        "all configured article predicates compile against creator views"
    ]["result"] == "FAIL"


def test_retained_lifecycle_state_is_terminal_and_one_to_one() -> None:
    payload = _load()
    for scope in ("full_history_lifecycle_state", "three_month_lifecycle_state"):
        state = payload[scope]
        headers = state["header_state"]
        numbers = state["set_voucher_number_state"]
        assert headers["headers"] == headers["confirmed_headers"]
        assert headers["headers"] == headers["exactly_one_active_voucher"]
        assert headers["unconfirmed_headers"] == 0
        assert headers["confirmed_not_transferred"] == 0
        assert headers["delete_eligible_shape"] == 0
        assert headers["multiple_active_vouchers"] == 0
        assert numbers["headers"] == headers["headers"]
        assert numbers["rows"] == headers["headers"]
        assert numbers["missing_header_rows"] == 0
        assert numbers["no_active_voucher_rows"] == 0
        assert numbers["duplicate_header_groups"] == 0


def test_dynamic_rule_sql_and_source_snapshot_boundary_is_explicit() -> None:
    payload = _load()
    profile = payload["dynamic_rule_sql_and_source_snapshot_profile"]
    semantics = profile["deployed_sql_semantics"]
    assert semantics["pre_voucher_builds_one_concatenated_sql_batch"] is True
    assert semantics["pre_voucher_uses_sp_executesql_parameters"] is False
    assert semantics["validator_executes_concatenated_view_and_predicate"] is True
    assert semantics["validator_restricts_view_name_to_quoted_identifier"] is False
    assert semantics["pre_voucher_concatenates_view_name"] is True
    assert semantics["pre_voucher_concatenates_article_fields"] is True
    assert semantics["pre_voucher_concatenates_article_predicate"] is True
    assert semantics["pre_voucher_concatenates_default_where"] is True
    assert semantics["pre_voucher_concatenates_comment_recipe"] is True
    assert semantics["creator_view_read_uses_nolock"] is True
    assert semantics["source_read_is_guaranteed_committed_consistent"] is False
    assert semantics["raw_dynamic_sql_or_config_values_persisted"] is False

    fragments = profile["configured_fragment_profiles"]
    assert {name: row["present_row_count"] for name, row in fragments.items()} == {
        "view_name": 17,
        "type_default_where": 21,
        "type_secondary_where": 14,
        "article_predicate": 129,
        "article_date_field": 159,
        "article_amount_field": 159,
        "article_ledger_fragment": 459,
        "comment_constant": 353,
        "type_default_comment": 61,
        "voucher_type_name": 78,
        "creator_field_name": 597,
    }
    assert {name: row["distinct_value_count"] for name, row in fragments.items()} == {
        "view_name": 17,
        "type_default_where": 21,
        "type_secondary_where": 14,
        "article_predicate": 71,
        "article_date_field": 7,
        "article_amount_field": 20,
        "article_ledger_fragment": 80,
        "comment_constant": 82,
        "type_default_comment": 41,
        "voucher_type_name": 78,
        "creator_field_name": 313,
    }
    suspicious_metrics = (
        "semicolon_value_count",
        "line_comment_token_value_count",
        "block_comment_token_value_count",
        "statement_keyword_value_count",
        "single_quote_value_count",
        "control_character_value_count",
    )
    assert all(row[metric] == 0 for row in fragments.values() for metric in suspicious_metrics)
    assert all(row["raw_values_persisted"] is False for row in fragments.values())
    assert profile["summary"] == {
        "configured_fragment_category_count": 11,
        "current_consumed_fragment_category_count": 10,
        "current_suspicious_token_or_quote_value_count": 0,
        "distinct_article_predicate_count": 71,
        "creator_view_nolock_read_count_in_definition": 1,
        "dynamic_sql_execution_site_count": 2,
        "dynamic_sql_execution_sites_run_by_extractor": 0,
    }
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix[
        "accounting staging source reads are committed and snapshot-consistent"
    ]["result"] == "FAIL"
    assert matrix[
        "voucher rule configuration is not executed as concatenated SQL"
    ]["result"] == "FAIL"
    assert matrix[
        "current configured fragments contain obvious SQL meta tokens"
    ]["result"] == "PASS"


def test_provider_isolation_and_creator_source_version_limits_are_explicit() -> None:
    payload = _load()
    profile = payload["transaction_isolation_and_source_version_profile"]
    provider = profile["deployed_provider_boundary"]
    assert provider["assembly"] == "Application.DataAccess.dll"
    assert len(provider["assembly_sha256"]) == 64
    assert provider["hash_matches_inventory"] is True
    assert provider["method"] == "Thunderstruck.Provider.DefaultProvider.Open"
    assert provider["begin_transaction_call_count"] == 1
    assert provider["begin_transaction_calls"][0]["parameter_count"] == 0
    assert provider["begin_transaction_calls"][0][
        "preceded_only_by_connection_receiver"
    ] is True
    assert provider["all_begin_transaction_calls_are_parameterless"] is True
    assert provider["explicit_isolation_level_argument_present"] is False
    assert provider["isolation_text_marker_count_in_binary"] == 0
    assert provider["assembly_loaded_or_executed"] is False

    assert profile["clone_database_options"] == {
        "is_read_only": True,
        "is_read_committed_snapshot_on": True,
        "snapshot_isolation_state_desc": "ON",
    }
    all_active = profile["creator_dependency_version_profiles"][
        "all_active_creators"
    ]
    recent = profile["creator_dependency_version_profiles"][
        "recent_active_creators"
    ]
    assert all_active == {
        "creator_count": 11,
        "maximum_resolved_dependency_depth": 6,
        "base_table_count": 72,
        "view_count": 32,
        "function_count": 0,
        "base_table_with_rowversion_count": 7,
        "base_table_with_version_named_column_count": 38,
        "temporal_base_table_count": 0,
        "change_tracked_base_table_count": 0,
        "unresolved_dependency_edge_count": 0,
        "external_dependency_edge_count": 0,
    }
    assert recent == {
        "creator_count": 4,
        "maximum_resolved_dependency_depth": 6,
        "base_table_count": 54,
        "view_count": 19,
        "function_count": 0,
        "base_table_with_rowversion_count": 6,
        "base_table_with_version_named_column_count": 30,
        "temporal_base_table_count": 0,
        "change_tracked_base_table_count": 0,
        "unresolved_dependency_edge_count": 0,
        "external_dependency_edge_count": 0,
    }
    assert profile["summary"] == {
        "recent_active_creator_count": 4,
        "recent_source_base_table_count": 54,
        "recent_source_base_table_with_rowversion_count": 6,
        "recent_source_temporal_base_table_count": 0,
        "recent_source_change_tracked_base_table_count": 0,
        "provider_explicit_isolation_level": False,
        "operational_creator_views_executed_by_extractor": 0,
    }
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix[
        "desktop issue transaction chooses an explicit isolation level"
    ]["result"] == "FAIL"
    assert matrix[
        "clone database supports committed row-versioned reads"
    ]["result"] == "PASS"
    assert matrix[
        "recent creator sources have portable durable version coverage"
    ]["result"] == "FAIL"


def test_rule_configuration_write_authority_and_template_transfer_are_bounded() -> None:
    payload = _load()
    profile = payload["rule_configuration_write_authority_profile"]
    sql = profile["sql_write_surface"]
    assert sql["target_table_count"] == 5
    assert sql["lexical_mutation_module_count"] == 8
    assert sql["lexical_table_module_pair_count"] == 11
    assert sql["raw_definitions_persisted"] is False
    assert sql["operational_modules_executed"] == 0
    assert {name: row["row_count"] for name, row in sql["tables"].items()} == {
        "VoucherCreator": 17,
        "VoucherCreatorField": 597,
        "ExternalVoucherType": 65,
        "Article": 159,
        "ArticleComment": 353,
    }
    assert sql["tables"]["Article"]["enabled_trigger_count"] == 3
    assert sql["tables"]["ArticleComment"]["enabled_trigger_count"] == 3

    app = profile["deployed_application_surface"]
    assert app["inventory_file_count"] == 62
    assert app["hash_mismatch_count"] == 0
    assert app["parsed_managed_assembly_count"] == 62
    assert app["managed_parse_error_or_nonmanaged_count"] == 0
    assert app["target_named_type_count"] == 11
    assert app["target_named_form_type_count"] == 0
    assert app["external_voucher_type_save_call_site_count"] == 0
    assert app["direct_target_sql_literal_site_count"] == 0
    assert app["template_procedure_literal_site_count"] == 0
    assert app["binary_voucher_mapping_literal_site_count"] == 0
    assert app["binary_voucher_mapping_literal_sites"] == []
    assert app["handler_save_command"] == {
        "instruction_count": 8,
        "branch_instruction_count": 0,
        "validation_failure_constructor_count": 1,
        "validation_result_constructor_count": 1,
        "data_adapter_or_transaction_call_count": 0,
        "string_literal_count": 2,
        "raw_localized_validation_values_persisted": False,
    }
    assert app["entity_data_procedure_literals"] == [
        "dbo.USP_SDSNET_ExternalVoucherType_GetList"
    ]
    assert app["assemblies_loaded_or_executed"] == 0

    procedures = profile["template_transfer_procedure_contracts"]
    assert set(procedures) == {
        "dbo.VoucherTemplateTransfer",
        "dbo.VoucherTemplateArticleTransfer",
    }
    parent = procedures["dbo.VoucherTemplateTransfer"]
    child = procedures["dbo.VoucherTemplateArticleTransfer"]
    assert parent["parameter_count"] == child["parameter_count"] == 0
    assert parent["dynamic_exec_site_count"] == 4
    assert child["dynamic_exec_site_count"] == 1
    assert parent["drops_and_creates_creator_views"] is True
    assert parent["target_table_mutations"] == [
        "ExternalVoucherType",
        "VoucherCreator",
        "VoucherCreatorField",
    ]
    assert child["target_table_mutations"] == ["Article", "ArticleComment"]
    assert parent["calls_article_transfer"] is True
    assert child["catalog_callers"] == [
        {
            "caller_name": "[dbo].[VoucherTemplateTransfer]",
            "caller_type": "SQL_STORED_PROCEDURE",
        }
    ]
    assert all(row["uses_cursor"] is True for row in procedures.values())
    assert all(row["owns_explicit_transaction"] is False for row in procedures.values())
    assert all(row["has_try_catch"] is False for row in procedures.values())
    assert all(row["has_explicit_rollback"] is False for row in procedures.values())
    assert all(row["references_authorization_signal"] is False for row in procedures.values())
    assert all(
        row["references_version_or_publish_audit_signal"] is False
        for row in procedures.values()
    )
    assert all(row["analyzer_login_has_execute"] is False for row in procedures.values())
    assert all(row["definition_persisted"] is False for row in procedures.values())
    assert profile["summary"] == {
        "application_target_form_type_count": 0,
        "application_save_call_site_count": 0,
        "application_direct_target_sql_literal_site_count": 0,
        "application_template_procedure_literal_site_count": 0,
        "application_binary_voucher_mapping_literal_site_count": 0,
        "handler_save_is_unconditional_validation_failure": True,
        "sql_lexical_mutation_module_count": 8,
        "sql_enabled_target_trigger_count": 6,
        "configuration_write_authority_attributed_to_deployed_form": False,
        "template_transfer_procedure_count": 2,
        "template_transfer_procedure_with_transaction_count": 0,
        "template_transfer_procedure_with_try_catch_count": 0,
        "template_transfer_procedure_with_authorization_signal_count": 0,
        "template_transfer_procedure_with_version_audit_signal_count": 0,
        "analyzer_login_executable_template_procedure_count": 0,
    }
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix[
        "voucher-rule write authority is attributable to a deployed form and permission"
    ]["result"] == "FAIL"
    assert matrix[
        "voucher-template rule transfer is atomic versioned and audited"
    ]["result"] == "FAIL"
    assert matrix[
        "read-only analyzer can execute voucher-template transfer"
    ]["result"] == "PASS"


def test_rule_replication_shape_and_stale_template_schema_are_separated() -> None:
    payload = _load()
    profile = payload["rule_replication_trigger_profile"]
    triggers = profile["trigger_contracts"]
    assert len(triggers) == 6
    assert all(row["is_disabled"] is False for row in triggers)
    assert all(row["is_instead_of_trigger"] is False for row in triggers)
    assert all(row["uses_replication_mode_guard"] is True for row in triggers)
    assert all(row["calls_local_insert_to_log"] is True for row in triggers)
    assert all(row["insert_to_log_output_argument_count"] == 1 for row in triggers)
    assert all(
        row["insert_to_log_output_variable_reused_after_call"] is False
        for row in triggers
    )
    assert all(row["uses_per_row_cursor"] is True for row in triggers)
    assert all(row["has_try_catch"] is False for row in triggers)
    assert all(row["sets_xact_abort"] is False for row in triggers)
    assert all(row["external_dependency_edge_count"] == 0 for row in triggers)
    assert all(row["definition_persisted"] is False for row in triggers)

    coverage = profile["replication_insert_column_coverage"]
    assert coverage["Article"]["table_column_count"] == 16
    assert coverage["Article"]["replication_insert_column_count"] == 16
    assert coverage["Article"]["omitted_columns"] == []
    assert coverage["Article"]["all_nonidentity_columns_replicated"] is True
    assert coverage["ArticleComment"]["table_column_count"] == 5
    assert coverage["ArticleComment"]["replication_insert_column_count"] == 5
    assert coverage["ArticleComment"]["omitted_columns"] == []
    assert coverage["ArticleComment"]["all_nonidentity_columns_replicated"] is True

    template = profile["template_article_transfer_schema_compatibility"]
    assert template["current_article_column_count"] == 16
    assert template["template_insert_column_count"] == 11
    assert template["template_insert_unknown_columns"] == [
        "VoucherCreatorId",
        "ArticleCaption",
    ]
    assert template["current_nonidentity_columns_omitted_by_template"] == [
        "ShowDateRange",
        "FromAccYear",
        "ToAccYear",
        "SeventhLedger",
        "ArticleTemplateId",
        "ArticleComment",
    ]
    assert template["current_required_columns_omitted_by_template"] == []
    assert template["dynamic_insert_schema_compatible"] is False
    assert template["definition_persisted"] is False

    writer = profile["local_log_writer_contract"]
    assert writer["writes_local_gnr_tbl_log"] is True
    assert writer["stores_generated_sql_script"] is True
    assert writer["uses_ident_current_for_output_id"] is True
    assert writer["uses_scope_identity_for_output_id"] is False
    assert writer["parameter_count"] == 6
    assert writer["output_parameter_count"] == 1
    assert writer["output_parameter_type_names"] == ["int"]
    assert writer["owns_explicit_transaction"] is False
    assert writer["log_column_count"] == 11
    assert writer["has_host_name_column"] is True
    assert writer["has_application_name_column"] is True
    assert writer["has_sql_user_name_column"] is True
    assert writer["has_spid_column"] is True
    assert writer["has_rule_or_policy_version_column"] is False
    assert writer["has_approval_column"] is False
    assert writer["runtime_context_defaults_present"] is True
    assert writer["definition_persisted"] is False

    activity = {
        (row["OperationTable"], row["OperationType"]): (
            row["retained_log_rows"],
            row["three_month_log_rows"],
        )
        for row in profile["aggregate_log_activity"]
    }
    assert activity == {
        ("dbo.Article", "DELETE"): (158, 0),
        ("dbo.Article", "INSERT"): (159, 0),
        ("dbo.Article", "UPDATE"): (15, 4),
        ("dbo.ArticleComment", "DELETE"): (397, 0),
        ("dbo.ArticleComment", "INSERT"): (401, 0),
        ("dbo.ArticleComment", "UPDATE"): (2, 0),
    }
    assert profile["summary"] == {
        "enabled_trigger_count": 6,
        "trigger_with_replication_mode_guard_count": 6,
        "trigger_calling_local_insert_to_log_count": 6,
        "trigger_capturing_insert_to_log_output_count": 6,
        "trigger_reusing_insert_to_log_output_after_call_count": 0,
        "rule_trigger_control_flow_depends_on_returned_log_id": False,
        "trigger_with_external_dependency_count": 0,
        "article_replication_omitted_column_count": 0,
        "article_replication_omitted_required_column_count": 0,
        "retained_rule_replication_log_count": 1132,
        "three_month_rule_replication_log_count": 4,
        "template_article_insert_unknown_column_count": 2,
        "template_article_insert_omitted_current_column_count": 6,
        "template_article_dynamic_insert_schema_compatible": False,
        "operational_triggers_or_replication_scripts_executed": 0,
        "raw_replication_script_values_persisted": False,
    }


def test_insert_to_log_ident_current_impact_is_scoped_by_actual_consumers() -> None:
    boundary = _load()["rule_replication_trigger_profile"][
        "insert_to_log_global_output_boundary"
    ]
    assert boundary["dependency_module_counts"] == {
        "SQL_STORED_PROCEDURE": 11,
        "SQL_TRIGGER": 1142,
    }
    assert boundary["trigger_footprint"] == {
        "trigger_count": 1142,
        "parent_table_count": 376,
        "parent_schema_count": 6,
        "enabled_count": 1142,
        "not_for_replication_count": 0,
        "cursor_signal_count": 1140,
        "try_catch_count": 0,
        "xact_abort_count": 3,
    }
    assert boundary["trigger_event_counts"] == {
        "DELETE": 378,
        "INSERT": 384,
        "UPDATE": 384,
    }
    assert boundary["trigger_schema_footprint"] == [
        {
            "parent_schema": "Acc",
            "trigger_count": 53,
            "parent_table_count": 17,
            "cursor_signal_count": 53,
            "try_catch_count": 0,
            "xact_abort_count": 0,
            "not_for_replication_count": 0,
        },
        {
            "parent_schema": "dbo",
            "trigger_count": 426,
            "parent_table_count": 140,
            "cursor_signal_count": 426,
            "try_catch_count": 0,
            "xact_abort_count": 3,
            "not_for_replication_count": 0,
        },
        {
            "parent_schema": "GNR",
            "trigger_count": 321,
            "parent_table_count": 107,
            "cursor_signal_count": 319,
            "try_catch_count": 0,
            "xact_abort_count": 0,
            "not_for_replication_count": 0,
        },
        {
            "parent_schema": "ICA",
            "trigger_count": 15,
            "parent_table_count": 5,
            "cursor_signal_count": 15,
            "try_catch_count": 0,
            "xact_abort_count": 0,
            "not_for_replication_count": 0,
        },
        {
            "parent_schema": "inv",
            "trigger_count": 45,
            "parent_table_count": 15,
            "cursor_signal_count": 45,
            "try_catch_count": 0,
            "xact_abort_count": 0,
            "not_for_replication_count": 0,
        },
        {
            "parent_schema": "SLE",
            "trigger_count": 282,
            "parent_table_count": 92,
            "cursor_signal_count": 282,
            "try_catch_count": 0,
            "xact_abort_count": 0,
            "not_for_replication_count": 0,
        },
    ]
    assert boundary["trigger_event_shapes"] == [
        {
            "has_insert": 0,
            "has_update": 0,
            "has_delete": 1,
            "trigger_count": 376,
            "cursor_signal_count": 376,
        },
        {
            "has_insert": 0,
            "has_update": 1,
            "has_delete": 0,
            "trigger_count": 382,
            "cursor_signal_count": 382,
        },
        {
            "has_insert": 1,
            "has_update": 0,
            "has_delete": 0,
            "trigger_count": 382,
            "cursor_signal_count": 382,
        },
        {
            "has_insert": 1,
            "has_update": 1,
            "has_delete": 1,
            "trigger_count": 2,
            "cursor_signal_count": 0,
        },
    ]
    assert sum(row["trigger_count"] for row in boundary["trigger_schema_footprint"]) == (
        boundary["trigger_footprint"]["trigger_count"]
    )
    assert sum(
        row["parent_table_count"] for row in boundary["trigger_schema_footprint"]
    ) == boundary["trigger_footprint"]["parent_table_count"]
    assert sum(row["trigger_count"] for row in boundary["trigger_event_shapes"]) == (
        boundary["trigger_footprint"]["trigger_count"]
    )
    assert sum(
        row["cursor_signal_count"] for row in boundary["trigger_event_shapes"]
    ) == boundary["trigger_footprint"]["cursor_signal_count"]
    assert sum(
        row["trigger_count"]
        * (row["has_insert"] + row["has_update"] + row["has_delete"])
        for row in boundary["trigger_event_shapes"]
    ) == sum(boundary["trigger_event_counts"].values())
    assert boundary["binary_mapping_trigger_count"] == 2
    assert boundary["binary_mapping_trigger_using_returned_ident_current_count"] == 2
    assert all(
        row["captures_insert_to_log_output"] is True
        and row["persists_returned_log_id_in_mapping_table"] is True
        and row["definition_persisted"] is False
        for row in boundary["binary_voucher_mapping_trigger_contracts"]
    )
    assert boundary["binary_mapping_table_with_unique_index_count"] == 0
    assert boundary["binary_mapping_table_with_foreign_key_count"] == 0
    assert boundary["binary_mapping_table_dependency_module_count"] == 4
    assert boundary["binary_mapping_table_reader_module_count"] == 0
    assert boundary["retained_binary_voucher_mapping_rows"] == {
        "vocherHdrInserttolog": 0,
        "vocheritmInserttolog": 0,
    }
    assert boundary["concurrent_wrong_log_mapping_observed_in_snapshot"] is False
    assert boundary["definition_values_persisted"] is False


def test_clone_has_no_partial_external_voucher_state_or_balance_gap() -> None:
    payload = _load()
    for profile_name in ("full_history_integrity", "three_month_integrity"):
        profile = payload[profile_name]
        assert profile["pre_voucher_state"]["unlinked_lines"] == 0
        assert profile["pre_voucher_state"]["not_marked_lines"] == 0
        assert all(value == 0 for value in profile["orphan_and_partial_state"].values())
        balance = profile["header_line_balance"]
        assert balance["no_line_headers"] == 0
        assert balance["unbalanced_line_headers"] == 0
        assert balance["header_line_amount_mismatch"] == 0
        assert balance["max_line_imbalance"] == "0"


def test_mutable_current_issue_mode_does_not_explain_1405_history() -> None:
    payload = _load()
    drift = payload["historical_grouping_policy_drift"]
    assert drift["current_policy_fully_explains_history"] is False
    assert drift["current_mode_one_but_historical_multi_source_years"] == [1405]
    year_1405 = next(row for row in drift["by_accounting_year"] if row["AccYear"] == 1405)
    assert year_1405["current_issue_mode"] == 1
    assert year_1405["headers"] == 382
    assert year_1405["multi_source_headers"] == 366
    recent = drift["three_month_window"]
    assert recent["headers"] == 204
    assert recent["multi_source_headers"] == 196
    assert recent["source_groups"] == 27177
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix["historical issuance grouping is reproducible"]["result"] == "FAIL"


def test_three_month_creator_parity_and_daily_historical_shape_are_exact() -> None:
    payload = _load()
    parity = payload["three_month_creator_posting_parity"]
    assert parity["observed_creator_count"] == 4
    assert parity["zero_activity_creator_count"] == 7
    assert parity["three_layer_creator_parity"] is True
    observed = [row for row in parity["creator_rows"] if row["pre_voucher_lines"]]
    assert {row["VoucherCreatorId"] for row in observed} == {25, 28, 29, 31}
    assert sum(row["pre_voucher_lines"] for row in observed) == 109428
    assert sum(row["source_groups"] for row in observed) == 27177
    assert sum(row["pre_voucher_headers"] for row in observed) == 204
    assert all(
        row["pre_voucher_lines"] == row["external_lines"] == row["journal_lines"]
        for row in observed
    )
    assert all(
        row["pre_voucher_debit"]
        == row["pre_voucher_credit"]
        == row["external_debit"]
        == row["external_credit"]
        == row["journal_debit"]
        == row["journal_credit"]
        for row in observed
    )
    shape = parity["header_grouping_shape"]
    assert shape["headers"] == shape["one_date_headers"] == 204
    assert shape["multi_date_headers"] == 0
    assert shape["one_external_type_headers"] == 204
    assert shape["one_dc_headers"] == 204
    assert shape["one_sale_office_headers"] == 204
    assert shape["multi_source_headers"] == 196


def test_full_history_creator_financial_parity_allows_proven_line_consolidation() -> None:
    payload = _load()
    parity = payload["full_history_creator_posting_parity"]
    assert parity["observed_creator_count"] == 11
    assert parity["zero_activity_creator_count"] == 0
    assert parity["staging_to_external_line_count_parity"] is False
    assert parity["external_to_journal_line_count_parity"] is True
    assert parity["three_layer_header_count_parity"] is True
    assert parity["three_layer_amount_parity"] is True
    assert parity["persisted_financial_and_header_parity"] is True
    assert sum(row["pre_voucher_lines"] for row in parity["creator_rows"]) == 2370569
    assert sum(row["external_lines"] for row in parity["creator_rows"]) == 1287874
    assert sum(row["staging_to_external_line_delta"] for row in parity["creator_rows"]) == 1082695


def test_retained_line_cardinality_matches_legacy_equivalent_not_current_grain() -> None:
    payload = _load()
    grain = payload["historical_external_line_grain_profile"]
    assert grain["source_lines"] == 2370569
    assert grain["actual_external_lines"] == 1287874
    assert grain["legacy_equivalent_expected_lines"] == 1287874
    assert grain["current_deployed_expected_lines"] == 1424039
    assert grain["legacy_equivalent_collapsed_lines"] == 1082695
    assert grain["legacy_equivalent_consolidated_groups"] == 9624
    assert grain["max_source_lines_per_legacy_equivalent_group"] == 6257
    assert grain["creator_count_matching_legacy_equivalent_grain"] == 11
    assert grain["creator_count_matching_current_deployed_grain"] == 8
    assert grain["all_creators_match_legacy_equivalent_grain"] is True
    assert grain["all_creators_match_current_deployed_grain"] is False
    matrix = {row["requirement_or_risk"]: row for row in payload["verification_matrix"]}
    assert matrix["current deployed external-line grouping reproduces retained history"]["result"] == "FAIL"


def test_all_eleven_active_creator_views_satisfy_structural_contract() -> None:
    payload = _load()
    creators = payload["active_creator_rule_profiles"]
    assert len(creators) == 11
    assert sum(row["articles"] for row in creators) == 149
    assert all(all(row["required_output_contract"].values()) for row in creators)
    assert all(row["articles"] == row["debit_articles"] + row["credit_articles"] for row in creators)
    assert all(len(row["view_definition_sha256"]) == 64 for row in creators)


def test_all_149_creator_rules_have_redacted_reproducible_source_shapes() -> None:
    payload = _load()
    rules = [
        rule
        for creator in payload["active_creator_rule_profiles"]
        for rule in creator["rule_contracts"]
    ]
    assert len(rules) == 149
    assert len({rule["rule_sha256"] for rule in rules}) == 149
    assert all(rule["sources"]["amount"]["kind"] == "VIEW_FIELD" for rule in rules)
    assert all(rule["sources"]["date"]["kind"] == "VIEW_FIELD" for rule in rules)
    assert all(rule["sources"]["sixth"]["kind"] == "VIEW_FIELD" for rule in rules)
    assert sum(rule["sources"]["sl"]["kind"] == "STATIC_LITERAL_OR_EXPRESSION" for rule in rules) == 128
    assert sum(rule["sources"]["sl"]["kind"] == "VIEW_FIELD" for rule in rules) == 21
    assert sum(rule["sources"]["dl"]["kind"] == "VIEW_FIELD" for rule in rules) == 92
    assert sum(rule["sources"]["fifth"]["kind"] == "VIEW_FIELD" for rule in rules) == 11
    assert sum(rule["sources"]["seventh"]["kind"] == "VIEW_FIELD" for rule in rules) == 20
    assert all(rule["comment_recipe"]["component_count"] > 0 for rule in rules)
    assert all(rule["raw_account_codes_predicates_and_comments_persisted"] is False for rule in rules)
    assert all(
        set(rule["predicates"]) == {
            "article",
            "external_type_default",
            "external_type_secondary",
        }
        for rule in rules
    )
    assert sum(rule["retained_history_coverage"]["historical_lines"] > 0 for rule in rules) == 101
    assert sum(rule["retained_history_coverage"]["historical_lines"] == 0 for rule in rules) == 48
    assert sum(rule["retained_history_coverage"]["recent_lines"] > 0 for rule in rules) == 31


def test_creator_rule_coverage_keeps_unobserved_branches_as_golden_obligations() -> None:
    payload = _load()
    coverage = payload["active_creator_rule_coverage"]
    assert coverage == {
        "configured_rule_count": 149,
        "historically_observed_rule_count": 101,
        "historically_unobserved_rule_count": 48,
        "recently_observed_rule_count": 31,
        "recently_unobserved_rule_count": 118,
        "all_active_creators_observed_in_retained_history": True,
        "interpretation": coverage["interpretation"],
    }
    profiles = payload["active_creator_rule_profiles"]
    assert sum(len(row["historically_unobserved_rule_ordinals"]) for row in profiles) == 48
    assert sum(len(row["recently_unobserved_rule_ordinals"]) for row in profiles) == 118
    assert all(
        set(row["historically_unobserved_rule_ordinals"])
        <= set(row["recently_unobserved_rule_ordinals"])
        for row in profiles
    )


def test_prevoucher_exact_signature_has_unique_enforcement_and_no_duplicates() -> None:
    payload = _load()
    contract = payload["pre_voucher_idempotency"]
    unique = next(
        row
        for row in contract["indexes"].values()
        if row["is_unique"]
        and row["key_columns"][:3] == ["VoucherCreatorId", "ReferenceId", "ArticleId"]
    )
    assert unique["is_disabled"] is False
    assert unique["is_hypothetical"] is False
    assert unique["key_columns"][-1] == "PreVoucherItemComment"
    assert contract["exact_unique_signature_duplicate_profile"] == {
        "duplicate_groups": 0,
        "duplicate_rows": 0,
    }
    coarse = contract["procedure_anti_join_grain_profile"]
    assert coarse["groups"] == 949212
    assert coarse["multi_fiscal_groups"] == 0
    assert coarse["multi_external_type_groups"] == 0
    assert coarse["multi_creator_groups"] == 0


def test_extractor_contains_no_operational_exec_call() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "cursor.callproc" not in source
    assert "EXEC dbo.usp_DoExternalVoucher" not in source
    assert "EXEC dbo.usp_DoPreVoucher" not in source
    assert '"read-only clone aggregates and static deployed IL"' in source
