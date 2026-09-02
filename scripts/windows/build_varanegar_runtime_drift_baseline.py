"""Build a reproducible Varanegar runtime/schema/authorization drift baseline.

This is an offline builder: it reads only already-redacted evidence artifacts.
It does not connect to the application, database, network share, or live UI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


SOURCE_GROUPS: dict[str, tuple[str, ...]] = {
    "runtime_package": ("binary_inventory", "assembly_contracts", "targeted_il"),
    "navigation_surface": (
        "menu_routes",
        "menu_form_crosswalk",
        "form_catalog",
        "priority_gap_routes",
        "navigation_module_map",
        "scope_freeze_catalog",
        "present_package_route_types",
    ),
    "behavioral_contracts": (
        "capability_matrix",
        "workflow_catalog",
        "report_catalog",
        "ui_sql_contracts",
        "active_page_contracts",
        "state_machine_catalog",
        "command_side_effects",
        "report_execution_contracts",
        "data_entry_il_contracts",
        "high_impact_call_graph",
        "orchestrator_command_contracts",
        "all_form_call_contracts",
        "form_evidence_gaps",
        "priority_gap_call_graph",
        "root_entrypoints",
        "deployment_root_references",
        "priority_gap_declared_fields",
        "bank_reconciliation_source_model",
        "bank_reconciliation_command_guards",
        "bank_reconciliation_permission_catalog",
        "bank_reconciliation_delete_semantics",
        "bank_reconciliation_unmatch_semantics",
        "bank_reconciliation_discard_cancel_boundary",
        "bank_reconciliation_integrity_aggregates",
        "bank_reconciliation_type_alias_aggregates",
        "special_options_district_assessment",
        "bank_statement_import_boundary",
        "bank_statement_parser_row_contract",
        "bank_statement_persistence_boundary",
        "bank_reconciliation_transaction_boundary",
        "bank_reconciliation_cardex_sql_boundary",
        "bank_reconciliation_confirm_cardex_semantics",
        "bank_reconciliation_confirm_orchestration",
        "bank_reconciliation_matching_boundary",
        "bank_reconciliation_summary_ui_boundary",
        "bank_reconciliation_summary_sql_semantics",
        "bank_reconciliation_profile_state_boundary",
        "bank_reconciliation_role_uat",
        "bank_reconciliation_root_closure",
        "extension_capability_map",
        "extension_dependency_graph",
        "extension_command_paths",
        "extension_target_contracts",
        "extension_sql_surface",
        "extension_data_boundary_assessment",
        "extension_gap_paths",
        "extension_sql_anchor_contracts",
        "extension_sql_semantics",
        "pos_receipt_replication_contract",
        "pos_receipt_transitive_graph",
        "pos_source_model",
        "report_dependency_graph",
        "report_sql_candidates",
        "report_method_paths",
        "report_evidence_gaps",
        "report_shell_entrypoints",
        "report_shell_caller_paths",
        "report_generic_bindings",
        "report_generic_sql_candidates",
        "report_generic_sql_semantics",
        "role_uat_cases",
        "data_entry_field_dictionary",
        "data_entry_declared_fields",
        "data_entry_base_template_contracts",
        "data_entry_field_types",
        "data_entry_field_binding_candidates",
        "system_configuration_navigation_contract",
    ),
    "deep_command_boundaries": (
        "treasury_command_paths", "treasury_source_model", "treasury_trigger_semantics",
        "treasury_view_lineage", "treasury_target_contracts", "treasury_validation_contracts",
        "treasury_trigger_transitive_graph", "treasury_web_fields", "treasury_ui_labels",
        "treasury_web_screens", "order_sale_commands", "order_sale_labels",
        "order_sale_fields", "order_sale_layout", "order_sale_web_screens",
        "order_sale_dependency_graph", "order_sale_sql_semantics", "order_sale_source_model",
        "order_sale_trigger_graph", "stock_voucher_commands", "distribution_sql_anchors",
        "distribution_sql_semantics", "distribution_source_model", "distribution_trigger_graph",
        "supplier_invoice_commands", "supplier_invoice_sql_anchors",
        "supplier_invoice_source_model", "supplier_invoice_trigger_graph",
        "stock_supplier_ui_labels", "stock_supplier_fields", "stock_supplier_layout",
        "stock_supplier_web_screens",
        "accounting_voucher_entrypoints", "accounting_voucher_sql_candidates",
        "customer_goods_commands", "customer_ui_labels", "customer_fields",
        "customer_layout", "goods_ui_labels", "goods_fields", "goods_layout",
        "customer_goods_web_screens",
        "supplier_master_commands", "supplier_ui_labels", "supplier_fields",
        "supplier_layout", "supplier_master_web_screen",
        "operational_context_commands", "operational_context_main_labels",
        "operational_context_main_fields", "operational_context_main_layout",
        "stock_accounting_context_labels", "stock_accounting_context_fields",
        "stock_accounting_context_layout", "operational_context_web_screens",
        "pricing_rule_commands", "pricing_rule_labels", "pricing_rule_fields",
        "pricing_rule_layout", "pricing_rule_web_screens",
        "final_date_management_boundary", "final_date_diagnostic_contract",
        "stock_reconciliation_diagnostic_contract", "distribution_path_diagnostic_contract",
        "sales_return_amount_diagnostic_contract", "returned_cheque_cross_customer_diagnostic_contract",
        "received_cheque_projection_and_legal_type_diagnostic_contract",
        "payable_cheque_leaf_usage_diagnostic_contract",
        "voucher_status_pointer_diagnostic_contract",
        "empty_voucher_shell_diagnostic_contract",
        "ngt_return_crosswalk_diagnostic_contract",
        "supplier_receipt_component_diagnostic_contract",
    ),
    "target_verification": (
        "golden_command_cases",
        "orchestrator_golden_cases",
        "extension_golden_cases",
        "report_target_contracts_golden_cases",
        "customer_goods_master_golden",
        "foundation_context_pricing_golden_cases",
        "bank_reconciliation_golden_cases",
        "bank_reconciliation_differential_acceptance",
        "bank_reconciliation_implementation_readiness",
        "bank_reconciliation_owner_decisions",
        "bank_statement_profile_target_contract",
        "bank_reconciliation_read_model_target_contract",
        "bank_statement_staging_target_contract",
        "bank_reconciliation_state_machine_target_contract",
        "bank_reconciliation_command_envelope_target_contract",
        "bank_reconciliation_authenticated_uat_runbook",
        "bank_reconciliation_evidence_request_pack",
    ),
    "authorization_surface": ("route_authorization", "identity_access_navigation_gaps"),
    "session_surface": (
        "ui_inventory", "ui_checkpoint_0300", "ui_checkpoint_comparison_0300",
        "ui_checkpoint_0545", "ui_checkpoint_comparison_0545",
        "ui_checkpoint_0740", "ui_checkpoint_comparison_0740",
        "ui_checkpoint_0900", "ui_checkpoint_comparison_0900",
    ),
    "reconstruction_bundle": ("manifest",),
}


SOURCE_FILES: dict[str, str] = {
    "binary_inventory": "ui/varanegar_binary_inventory_20260827.json",
    "assembly_contracts": "ui/varanegar_assembly_contracts_20260827.json",
    "targeted_il": "ui/varanegar_targeted_il_contracts_20260827.json",
    "menu_routes": "ui/varanegar_menu_route_catalog_20260827.json",
    "menu_form_crosswalk": "ui/varanegar_menu_form_crosswalk_20260827.json",
    "form_catalog": "ui/varanegar_form_catalog_20260827.json",
    "capability_matrix": "ui/varanegar_ui_capability_matrix_20260827.json",
    "workflow_catalog": "ui/varanegar_workflow_catalog_20260827.json",
    "report_catalog": "ui/varanegar_report_catalog_20260827.json",
    "ui_sql_contracts": "ui/varanegar_ui_sql_contracts_20260827.json",
    "route_authorization": "ui/varanegar_route_authorization_matrix_20260827.json",
    "identity_access_navigation_gaps": "ui/varanegar_identity_access_navigation_gap_contract_20260827.json",
    "active_page_contracts": "ui/varanegar_active_page_contracts_20260827.json",
    "state_machine_catalog": "ui/varanegar_state_machine_catalog_20260827.json",
    "command_side_effects": "ui/varanegar_command_side_effects_20260827.json",
    "golden_command_cases": "ui/varanegar_golden_command_cases_20260827.json",
    "orchestrator_golden_cases": "ui/varanegar_orchestrator_golden_cases_20260827.json",
    "report_execution_contracts": "ui/varanegar_report_execution_contracts_20260827.json",
    "data_entry_il_contracts": "ui/varanegar_data_entry_il_contracts_20260827.json",
    "high_impact_call_graph": "ui/varanegar_high_impact_call_graph_20260827.json",
    "orchestrator_command_contracts": "ui/varanegar_orchestrator_command_contracts_20260827.json",
    "all_form_call_contracts": "ui/varanegar_all_form_call_contracts_20260827.json",
    "form_evidence_gaps": "ui/varanegar_form_evidence_gaps_20260827.json",
    "priority_gap_routes": "ui/varanegar_priority_gap_routes_20260827.json",
    "navigation_module_map": "ui/varanegar_navigation_module_map_20260827.json",
    "scope_freeze_catalog": "ui/varanegar_scope_freeze_catalog_20260827.json",
    "present_package_route_types": "ui/varanegar_present_package_route_types_20260827.json",
    "priority_gap_call_graph": "ui/varanegar_priority_gap_call_graph_20260827.json",
    "root_entrypoints": "ui/varanegar_root_entrypoints_20260827.json",
    "deployment_root_references": "ui/varanegar_deployment_root_reference_scan_20260827.json",
    "priority_gap_declared_fields": "ui/varanegar_priority_gap_declared_fields_20260827.json",
    "bank_reconciliation_source_model": "ui/varanegar_bank_reconciliation_source_model_20260827.json",
    "bank_reconciliation_command_guards": "ui/varanegar_bank_reconciliation_command_guards_20260827.json",
    "bank_reconciliation_permission_catalog": "ui/varanegar_bank_reconciliation_permission_catalog_20260827.json",
    "bank_reconciliation_delete_semantics": "ui/varanegar_bank_reconciliation_delete_semantics_20260827.json",
    "bank_reconciliation_unmatch_semantics": "ui/varanegar_bank_reconciliation_unmatch_sql_semantics_20260827.json",
    "bank_reconciliation_discard_cancel_boundary": "ui/varanegar_bank_reconciliation_discard_cancel_boundary_20260827.json",
    "bank_reconciliation_integrity_aggregates": "ui/varanegar_bank_reconciliation_integrity_aggregates_20260827.json",
    "bank_reconciliation_type_alias_aggregates": "ui/varanegar_bank_reconciliation_type_alias_aggregates_20260827.json",
    "special_options_district_assessment": "ui/varanegar_special_options_district_assessment_20260827.json",
    "bank_statement_import_boundary": "ui/varanegar_bank_statement_import_boundary_20260827.json",
    "bank_statement_parser_row_contract": "ui/varanegar_bank_statement_parser_row_contract_20260827.json",
    "bank_statement_persistence_boundary": "ui/varanegar_bank_statement_persistence_boundary_20260827.json",
    "bank_reconciliation_transaction_boundary": "ui/varanegar_bank_reconciliation_transaction_boundary_20260827.json",
    "bank_reconciliation_cardex_sql_boundary": "ui/varanegar_bank_reconciliation_cardex_sql_boundary_20260827.json",
    "bank_reconciliation_confirm_cardex_semantics": "ui/varanegar_bank_reconciliation_confirm_cardex_semantics_20260827.json",
    "bank_reconciliation_confirm_orchestration": "ui/varanegar_bank_reconciliation_confirm_orchestration_20260827.json",
    "bank_reconciliation_matching_boundary": "ui/varanegar_bank_reconciliation_matching_boundary_20260827.json",
    "bank_reconciliation_summary_ui_boundary": "ui/varanegar_bank_reconciliation_summary_ui_boundary_20260827.json",
    "bank_reconciliation_summary_sql_semantics": "ui/varanegar_bank_reconciliation_summary_sql_semantics_20260827.json",
    "bank_reconciliation_profile_state_boundary": "ui/varanegar_bank_reconciliation_profile_state_boundary_20260827.json",
    "bank_reconciliation_role_uat": "ui/negin_erp_bank_reconciliation_role_uat_20260827.json",
    "bank_reconciliation_root_closure": "ui/varanegar_unresolved_root_closure_contract_20260827.json",
    "extension_capability_map": "ui/varanegar_extension_capability_map_20260827.json",
    "extension_dependency_graph": "ui/varanegar_extension_dependency_graph_20260827.json",
    "extension_command_paths": "ui/varanegar_extension_command_paths_20260827.json",
    "extension_target_contracts": "ui/varanegar_extension_target_contracts_20260827.json",
    "extension_golden_cases": "ui/varanegar_extension_golden_cases_20260827.json",
    "foundation_context_pricing_golden_cases": "ui/negin_erp_foundation_context_pricing_golden_cases_20260827.json",
    "bank_reconciliation_golden_cases": "ui/negin_erp_bank_reconciliation_golden_cases_20260827.json",
    "bank_reconciliation_differential_acceptance": "ui/negin_erp_bank_reconciliation_differential_acceptance_20260827.json",
    "bank_reconciliation_implementation_readiness": "ui/negin_erp_bank_reconciliation_implementation_readiness_20260827.json",
    "bank_reconciliation_owner_decisions": "ui/negin_erp_bank_reconciliation_owner_decision_register_20260827.json",
    "bank_statement_profile_target_contract": "ui/negin_erp_bank_statement_profile_target_contract_20260827.json",
    "bank_reconciliation_read_model_target_contract": "ui/negin_erp_bank_reconciliation_read_model_contract_20260827.json",
    "bank_statement_staging_target_contract": "ui/negin_erp_bank_statement_staging_target_contract_20260827.json",
    "bank_reconciliation_state_machine_target_contract": "ui/negin_erp_bank_reconciliation_state_machine_contract_20260827.json",
    "bank_reconciliation_command_envelope_target_contract": "ui/negin_erp_bank_reconciliation_command_envelope_20260827.json",
    "bank_reconciliation_authenticated_uat_runbook": "ui/negin_erp_bank_reconciliation_authenticated_uat_runbook_20260827.json",
    "bank_reconciliation_evidence_request_pack": "ui/negin_erp_bank_reconciliation_evidence_request_pack_20260827.json",
    "extension_sql_surface": "ui/varanegar_extension_sql_surface_20260827.json",
    "extension_data_boundary_assessment": "ui/varanegar_extension_data_boundary_assessment_20260827.json",
    "extension_gap_paths": "ui/varanegar_extension_gap_paths_20260827.json",
    "extension_sql_anchor_contracts": "ui/varanegar_extension_sql_anchor_contracts_20260827.json",
    "extension_sql_semantics": "ui/varanegar_extension_sql_semantics_20260827.json",
    "pos_receipt_replication_contract": "ui/negin_erp_pos_receipt_replication_contract_20260827.json",
    "pos_receipt_transitive_graph": "ui/varanegar_pos_replication_transitive_graph_20260827.json",
    "pos_source_model": "ui/varanegar_pos_source_model_20260827.json",
    "report_target_contracts_golden_cases": "ui/varanegar_report_target_contracts_golden_cases_20260827.json",
    "report_dependency_graph": "ui/varanegar_report_dependency_graph_20260827.json",
    "report_sql_candidates": "ui/varanegar_report_sql_candidates_20260827.json",
    "report_method_paths": "ui/varanegar_report_method_paths_20260827.json",
    "report_evidence_gaps": "ui/varanegar_report_evidence_gaps_20260827.json",
    "report_shell_entrypoints": "ui/varanegar_report_shell_entrypoints_20260827.json",
    "report_shell_caller_paths": "ui/varanegar_report_shell_caller_paths_20260827.json",
    "report_generic_bindings": "ui/varanegar_report_generic_bindings_20260827.json",
    "report_generic_sql_candidates": "ui/varanegar_report_generic_sql_candidates_20260827.json",
    "report_generic_sql_semantics": "ui/varanegar_report_generic_sql_semantics_20260827.json",
    "role_uat_cases": "ui/negin_erp_role_uat_cases_20260827.json",
    "data_entry_field_dictionary": "ui/varanegar_data_entry_field_dictionary_20260827.json",
    "data_entry_declared_fields": "ui/varanegar_data_entry_declared_fields_20260827.json",
    "data_entry_base_template_contracts": "ui/varanegar_data_entry_base_template_contracts_20260827.json",
    "data_entry_field_types": "ui/varanegar_data_entry_field_types_20260827.json",
    "data_entry_field_binding_candidates": "ui/varanegar_data_entry_field_binding_candidates_20260827.json",
    "system_configuration_navigation_contract": "ui/varanegar_system_configuration_navigation_contract_20260827.json",
    "treasury_command_paths": "ui/varanegar_treasury_edit_command_paths_20260827.json",
    "treasury_source_model": "ui/varanegar_treasury_edit_source_model_20260827.json",
    "treasury_trigger_semantics": "ui/varanegar_treasury_trigger_semantics_20260827.json",
    "treasury_view_lineage": "ui/varanegar_treasury_view_column_lineage_20260827.json",
    "treasury_target_contracts": "ui/negin_erp_treasury_edit_target_contracts_20260827.json",
    "treasury_validation_contracts": "ui/varanegar_treasury_edit_validation_contracts_20260827.json",
    "treasury_trigger_transitive_graph": "ui/varanegar_treasury_trigger_transitive_graph_20260827.json",
    "treasury_web_fields": "ui/varanegar_treasury_web_field_contract_candidates_20260827.json",
    "treasury_ui_labels": "ui/varanegar_treasury_ui_label_candidates_20260827.json",
    "treasury_web_screens": "ui/negin_erp_treasury_web_screen_contract_candidates_20260827.json",
    "order_sale_commands": "ui/varanegar_order_sale_entry_command_contracts_20260827.json",
    "order_sale_labels": "ui/varanegar_order_sale_ui_label_candidates_20260827.json",
    "order_sale_fields": "ui/varanegar_order_sale_full_field_metadata_20260827.json",
    "order_sale_layout": "ui/varanegar_order_sale_layout_bindings_20260827.json",
    "order_sale_web_screens": "ui/negin_erp_order_sale_web_screen_contract_candidates_20260827.json",
    "order_sale_dependency_graph": "ui/varanegar_order_sale_command_dependency_graph_20260827.json",
    "order_sale_sql_semantics": "ui/varanegar_order_sale_sql_semantics_20260827.json",
    "order_sale_source_model": "ui/varanegar_order_sale_mutation_source_model_20260827.json",
    "order_sale_trigger_graph": "ui/varanegar_order_sale_trigger_transitive_graph_20260827.json",
    "stock_voucher_commands": "ui/varanegar_stock_voucher_command_contract_20260827.json",
    "distribution_sql_anchors": "ui/varanegar_distribution_sql_anchor_contracts_20260827.json",
    "distribution_sql_semantics": "ui/varanegar_distribution_sql_semantics_20260827.json",
    "distribution_source_model": "ui/varanegar_distribution_mutation_source_model_20260827.json",
    "distribution_trigger_graph": "ui/varanegar_distribution_trigger_transitive_graph_20260827.json",
    "supplier_invoice_commands": "ui/varanegar_supplier_invoice_command_contract_20260827.json",
    "supplier_invoice_sql_anchors": "ui/varanegar_supplier_invoice_sql_anchor_contracts_20260827.json",
    "supplier_invoice_source_model": "ui/varanegar_supplier_invoice_relation_source_model_20260827.json",
    "supplier_invoice_trigger_graph": "ui/varanegar_supplier_invoice_relation_trigger_transitive_graph_20260827.json",
    "stock_supplier_ui_labels": "ui/varanegar_stock_supplier_ui_label_candidates_20260827.json",
    "stock_supplier_fields": "ui/varanegar_stock_supplier_full_field_metadata_20260827.json",
    "stock_supplier_layout": "ui/varanegar_stock_supplier_layout_bindings_20260827.json",
    "stock_supplier_web_screens": "ui/negin_erp_stock_supplier_web_screen_contract_candidates_20260827.json",
    "accounting_voucher_entrypoints": "ui/varanegar_accounting_voucher_entrypoint_contracts_20260827.json",
    "accounting_voucher_sql_candidates": "ui/varanegar_accounting_voucher_sql_candidates_20260827.json",
    "customer_goods_commands": "ui/varanegar_customer_goods_command_contracts_20260827.json",
    "customer_ui_labels": "ui/varanegar_customer_ui_label_candidates_20260827.json",
    "customer_fields": "ui/varanegar_customer_full_field_metadata_20260827.json",
    "customer_layout": "ui/varanegar_customer_layout_bindings_20260827.json",
    "goods_ui_labels": "ui/varanegar_goods_ui_label_candidates_20260827.json",
    "goods_fields": "ui/varanegar_goods_full_field_metadata_20260827.json",
    "goods_layout": "ui/varanegar_goods_layout_bindings_20260827.json",
    "customer_goods_web_screens": "ui/negin_erp_customer_goods_web_screen_contract_candidates_20260827.json",
    "customer_goods_master_golden": "ui/negin_erp_customer_goods_master_golden_cases_20260827.json",
    "supplier_master_commands": "ui/varanegar_supplier_master_command_contract_20260827.json",
    "supplier_ui_labels": "ui/varanegar_supplier_ui_label_candidates_20260827.json",
    "supplier_fields": "ui/varanegar_supplier_full_field_metadata_20260827.json",
    "supplier_layout": "ui/varanegar_supplier_layout_bindings_20260827.json",
    "supplier_master_web_screen": "ui/negin_erp_supplier_master_web_screen_contract_candidate_20260827.json",
    "operational_context_commands": "ui/varanegar_operational_context_command_contracts_20260827.json",
    "operational_context_main_labels": "ui/varanegar_operational_context_main_ui_labels_20260827.json",
    "operational_context_main_fields": "ui/varanegar_operational_context_main_full_fields_20260827.json",
    "operational_context_main_layout": "ui/varanegar_operational_context_main_layout_20260827.json",
    "stock_accounting_context_labels": "ui/varanegar_stock_accounting_context_ui_labels_20260827.json",
    "stock_accounting_context_fields": "ui/varanegar_stock_accounting_context_full_fields_20260827.json",
    "stock_accounting_context_layout": "ui/varanegar_stock_accounting_context_layout_20260827.json",
    "operational_context_web_screens": "ui/negin_erp_operational_context_web_screen_contract_candidates_20260827.json",
    "pricing_rule_commands": "ui/varanegar_pricing_rule_command_contracts_20260827.json",
    "pricing_rule_labels": "ui/varanegar_pricing_rule_ui_labels_20260827.json",
    "pricing_rule_fields": "ui/varanegar_pricing_rule_full_fields_20260827.json",
    "pricing_rule_layout": "ui/varanegar_pricing_rule_layout_20260827.json",
    "pricing_rule_web_screens": "ui/negin_erp_pricing_rule_web_screen_contract_candidates_20260827.json",
    "final_date_management_boundary": "ui/varanegar_final_date_management_boundary_20260827.json",
    "final_date_diagnostic_contract": "ui/varanegar_final_date_diagnostic_contract_20260827.json",
    "stock_reconciliation_diagnostic_contract": "ui/varanegar_stock_reconciliation_diagnostic_contract_20260827.json",
    "distribution_path_diagnostic_contract": "ui/varanegar_distribution_path_diagnostic_contract_20260827.json",
    "sales_return_amount_diagnostic_contract": "ui/varanegar_sales_return_amount_diagnostic_contract_20260827.json",
    "returned_cheque_cross_customer_diagnostic_contract": "ui/varanegar_returned_cheque_cross_customer_diagnostic_contract_20260827.json",
    "received_cheque_projection_and_legal_type_diagnostic_contract": "ui/varanegar_received_cheque_projection_and_legal_type_diagnostic_contract_20260827.json",
    "payable_cheque_leaf_usage_diagnostic_contract": "ui/varanegar_payable_cheque_leaf_usage_diagnostic_contract_20260827.json",
    "voucher_status_pointer_diagnostic_contract": "ui/varanegar_voucher_status_pointer_diagnostic_contract_20260827.json",
    "empty_voucher_shell_diagnostic_contract": "ui/varanegar_empty_voucher_shell_diagnostic_contract_20260827.json",
    "ngt_return_crosswalk_diagnostic_contract": "ui/varanegar_ngt_return_crosswalk_diagnostic_contract_20260827.json",
    "supplier_receipt_component_diagnostic_contract": "ui/varanegar_supplier_receipt_component_diagnostic_contract_20260827.json",
    "ui_inventory": "ui/varanegar_ui_inventory_20260827.json",
    "ui_checkpoint_0300": "ui/varanegar_ui_checkpoint_20260827_0300.json",
    "ui_checkpoint_comparison_0300": "ui/varanegar_ui_checkpoint_comparison_20260827_0300.json",
    "ui_checkpoint_0545": "ui/varanegar_ui_checkpoint_20260827_0545.json",
    "ui_checkpoint_comparison_0545": "ui/varanegar_ui_checkpoint_comparison_20260827_0545.json",
    "ui_checkpoint_0740": "ui/varanegar_ui_checkpoint_20260827_0740.json",
    "ui_checkpoint_comparison_0740": "ui/varanegar_ui_checkpoint_comparison_20260827_0740.json",
    "ui_checkpoint_0900": "ui/varanegar_ui_checkpoint_20260827_0900.json",
    "ui_checkpoint_comparison_0900": "ui/varanegar_ui_checkpoint_comparison_20260827_0900.json",
    "manifest": "manifest_20260826.json",
}


VOLATILE_KEYS = {
    "generated_at",
    "captured_at",
    "server_clock",
    "validated_at",
    "validation_time",
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _stable(item)
            for key, item in sorted(value.items())
            if key not in VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _semantic_hash(payload: Any) -> str:
    canonical = json.dumps(
        _stable(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256_bytes(canonical)


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    if isinstance(summary, dict):
        return summary
    return {
        "status": payload.get("status"),
        "domain_count": payload.get("domain_count"),
        "artifact_count": payload.get("artifact_count"),
    }


def _comparison(current: dict[str, Any], previous_path: Path | None) -> dict[str, Any]:
    if previous_path is None:
        return {
            "status": "BASELINE_ESTABLISHED",
            "previous_baseline": None,
            "changed_sources": [],
            "new_sources": [],
            "missing_sources": [],
            "unchanged_source_count": 0,
        }
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    previous_sources = previous.get("sources", {})
    current_sources = current["sources"]
    changed = sorted(
        name
        for name in current_sources.keys() & previous_sources.keys()
        if current_sources[name]["semantic_sha256"]
        != previous_sources[name]["semantic_sha256"]
    )
    new = sorted(current_sources.keys() - previous_sources.keys())
    missing = sorted(previous_sources.keys() - current_sources.keys())
    unchanged = len(current_sources.keys() & previous_sources.keys()) - len(changed)
    return {
        "status": "DRIFT_DETECTED" if changed or new or missing else "NO_SEMANTIC_DRIFT",
        "previous_baseline": previous_path.as_posix(),
        "changed_sources": changed,
        "new_sources": new,
        "missing_sources": missing,
        "unchanged_source_count": unchanged,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()

    sources: dict[str, Any] = {}
    payloads: dict[str, dict[str, Any]] = {}
    for name, relative in SOURCE_FILES.items():
        path = args.artifact_root / relative
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8-sig"))
        payloads[name] = payload
        sources[name] = {
            "path": path.as_posix(),
            "artifact": payload.get("artifact", payload.get("bundle", name)),
            "schema_version": payload.get("schema_version"),
            "file_bytes": len(raw),
            "file_sha256": _sha256_bytes(raw),
            "semantic_sha256": _semantic_hash(payload),
            "summary": _summary(payload),
        }

    groups = {}
    for group_name, names in SOURCE_GROUPS.items():
        group_values = {
            name: sources[name]["semantic_sha256"] for name in sorted(names)
        }
        groups[group_name] = {
            "source_count": len(names),
            "semantic_sha256": _semantic_hash(group_values),
            "sources": list(names),
        }

    binary_payload = payloads["binary_inventory"]
    versions: dict[str, int] = {}
    for row in binary_payload["files"]:
        version = str(row.get("file_version") or "unknown")
        versions[version] = versions.get(version, 0) + 1
    sql_payload = payloads["ui_sql_contracts"]
    authority_payload = payloads["route_authorization"]
    baseline = {
        "artifact": "varanegar_runtime_drift_baseline",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_REDACTED_READ_ONLY_EVIDENCE",
            "database_connections": 0,
            "live_ui_actions": 0,
            "network_reads": 0,
            "application_commands_executed": 0,
            "business_rows_read_or_persisted": 0,
            "credentials_persisted": 0,
        },
        "release_identity": {
            "binary_file_count": len(binary_payload["files"]),
            "binary_version_distribution": dict(sorted(versions.items())),
            "binary_package_semantic_sha256": groups["runtime_package"]["semantic_sha256"],
            "sql_contract_count": len(sql_payload["contracts"]),
            "sql_contract_semantic_sha256": sources["ui_sql_contracts"]["semantic_sha256"],
            "route_authorization_node_count": authority_payload["summary"]["authorization_node_count"],
            "overall_semantic_sha256": _semantic_hash(
                {name: row["semantic_sha256"] for name, row in sorted(groups.items())}
            ),
        },
        "drift_policy": {
            "runtime_package": "Any DLL hash/version/type/IL contract change requires targeted UI and call-graph re-extraction.",
            "navigation_surface": "Any menu/form/access-node change requires route and form crosswalk regeneration.",
            "behavioral_contracts": "Any workflow/report/capability/SQL hash change invalidates affected ERP parity claims until reviewed.",
            "target_verification": "Golden-case drift requires target test-plan review; cases are synthetic contracts and are never executed against Varanegar.",
            "authorization_surface": "Any node/right aggregate change requires capability and segregation-of-duties review; aggregate drift is not identity evidence.",
            "session_surface": "UI surface drift may be selection/session state; verify against package and route drift before classifying a release change.",
            "reconstruction_bundle": "Manifest drift must be accompanied by regenerated evidence and passing tests.",
        },
        "sources": sources,
        "groups": groups,
    }
    baseline["comparison"] = _comparison(baseline, args.previous)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps({"release_identity": baseline["release_identity"], "comparison": baseline["comparison"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
