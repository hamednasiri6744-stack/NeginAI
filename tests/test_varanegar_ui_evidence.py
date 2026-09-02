from __future__ import annotations

import importlib.util
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_ui_inventory.ps1"
ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_ui_inventory_20260827.json"
)
BINARY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_binary_inventory_20260827.json"
)
ASSEMBLY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_assembly_contracts_20260827.json"
)
IL_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_targeted_il_contracts_20260827.json"
)
SQL_CONTRACT_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_ui_sql_contracts_20260827.json"
)
SQL_CONTRACT_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_ui_sql_contracts.py"
CAPABILITY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_ui_capability_matrix_20260827.json"
)
FORM_CATALOG_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_form_catalog_20260827.json"
)
WORKFLOW_CATALOG_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_workflow_catalog_20260827.json"
)
REPORT_CATALOG_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_report_catalog_20260827.json"
)
MENU_ROUTE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_menu_route_catalog_20260827.json"
)
MENU_ROUTE_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_menu_route_catalog.py"
MENU_FORM_CROSSWALK_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_menu_form_crosswalk_20260827.json"
)
ROUTE_AUTHORIZATION_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_route_authorization_matrix_20260827.json"
)
ROUTE_AUTHORIZATION_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_route_authorization_matrix.py"
)
DRIFT_BASELINE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_runtime_drift_baseline_20260827.json"
)
DRIFT_BASELINE_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_runtime_drift_baseline.py"
)
ACTIVE_PAGE_CONTRACTS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_active_page_contracts_20260827.json"
)
ACTIVE_PAGE_CONTRACTS_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_active_page_contracts.py"
)
STATE_MACHINE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_state_machine_catalog_20260827.json"
)
STATE_MACHINE_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_state_machine_catalog.py"
)
COMMAND_SIDE_EFFECTS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_command_side_effects_20260827.json"
)
COMMAND_SIDE_EFFECTS_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_command_side_effects.py"
)
GOLDEN_COMMAND_CASES_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_golden_command_cases_20260827.json"
)
GOLDEN_COMMAND_CASES_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_golden_command_cases.py"
)
REPORT_EXECUTION_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_report_execution_contracts_20260827.json"
)
REPORT_EXECUTION_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_report_execution_contracts.py"
)
TARGET_ERP_BLUEPRINT_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_personal_erp_blueprint_20260827.json"
)
TARGET_ERP_BLUEPRINT_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_target_erp_blueprint.py"
)
NIGHT_BUNDLE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_night_evidence_bundle_manifest_20260827.json"
)
NIGHT_BUNDLE_VALIDATOR = (
    ROOT / "scripts" / "windows" / "validate_varanegar_night_evidence_bundle.py"
)
MIGRATION_CONTRACT_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_varanegar_migration_contract_20260827.json"
)
MIGRATION_CONTRACT_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_migration_contract.py"
)
ROLE_SOD_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_role_sod_contract_20260827.json"
)
ROLE_SOD_BUILDER = (
    ROOT / "scripts" / "windows" / "build_negin_erp_sod_role_contract.py"
)
DATA_ENTRY_IL_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_data_entry_il_contracts_20260827.json"
)
DATA_ENTRY_IL_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_data_entry_il_contracts.py"
)
HIGH_IMPACT_CALL_GRAPH_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_high_impact_call_graph_20260827.json"
)
HIGH_IMPACT_CALL_GRAPH_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_high_impact_call_graph.py"
)
ORCHESTRATOR_COMMAND_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_orchestrator_command_contracts_20260827.json"
)
ORCHESTRATOR_COMMAND_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_orchestrator_command_contracts.py"
)
ORCHESTRATOR_GOLDEN_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_orchestrator_golden_cases_20260827.json"
)
ORCHESTRATOR_GOLDEN_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_orchestrator_golden_cases.py"
)
ALL_FORM_CALL_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_all_form_call_contracts_20260827.json"
)
ALL_FORM_CALL_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_all_form_call_contracts.py"
)
FORM_GAP_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_form_evidence_gaps_20260827.json"
)
FORM_GAP_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_form_evidence_gap_catalog.py"
)
PRIORITY_GAP_ROUTE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_priority_gap_routes_20260827.json"
)
PRIORITY_GAP_ROUTE_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_priority_gap_routes.py"
)
PRIORITY_GAP_CALL_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_priority_gap_call_graph_20260827.json"
)
PRIORITY_GAP_CALL_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_priority_gap_call_graph.py"
)
ROOT_ENTRYPOINT_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_root_entrypoints_20260827.json"
)
ROOT_ENTRYPOINT_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_root_entrypoints.py"
)
DEPLOYMENT_ROOT_REFERENCE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_deployment_root_reference_scan_20260827.json"
)
DEPLOYMENT_ROOT_REFERENCE_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_deployment_root_reference_scan.py"
)
UNRESOLVED_ROOT_CLOSURE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_unresolved_root_closure_contract_20260827.json"
)
UNRESOLVED_ROOT_CLOSURE_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_unresolved_root_closure_contract.py"
)
P0_BACKLOG_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_p0_backlog_20260827.json"
)
P0_BACKLOG_BUILDER = (
    ROOT / "scripts" / "windows" / "build_negin_erp_p0_backlog.py"
)
MODULE_READINESS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_module_readiness_matrix_20260827.json"
)
MODULE_READINESS_BUILDER = (
    ROOT / "scripts" / "windows" / "build_negin_erp_module_readiness_matrix.py"
)
RISK_REGISTER_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_risk_register_20260827.json"
)
RISK_REGISTER_BUILDER = (
    ROOT / "scripts" / "windows" / "build_negin_erp_risk_register.py"
)
NAVIGATION_MODULE_MAP_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_navigation_module_map_20260827.json"
)
NAVIGATION_MODULE_MAP_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_navigation_module_map.py"
)
SCOPE_FREEZE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_scope_freeze_catalog_20260827.json"
)
SCOPE_FREEZE_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_scope_freeze_catalog.py"
)
PRESENT_PACKAGE_ROUTE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_present_package_route_types_20260827.json"
)
PRESENT_PACKAGE_ROUTE_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_present_package_route_types.py"
)
EXTENSION_CAPABILITY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_capability_map_20260827.json"
)
EXTENSION_CAPABILITY_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_extension_capability_map.py"
)
EXTENSION_DEPENDENCY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_dependency_graph_20260827.json"
)
EXTENSION_DEPENDENCY_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_extension_dependency_graph.py"
)
EXTENSION_COMMAND_PATH_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_command_paths_20260827.json"
)
EXTENSION_COMMAND_PATH_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_extension_command_paths.py"
)
EXTENSION_TARGET_CONTRACT_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_target_contracts_20260827.json"
)
EXTENSION_TARGET_CONTRACT_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_extension_target_contracts.py"
)
EXTENSION_GOLDEN_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_golden_cases_20260827.json"
)
EXTENSION_GOLDEN_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_extension_golden_cases.py"
)
EXTENSION_SQL_SURFACE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_sql_surface_20260827.json"
)
EXTENSION_SQL_SURFACE_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_extension_sql_surface.py"
)
EXTENSION_DATA_BOUNDARY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_data_boundary_assessment_20260827.json"
)
EXTENSION_DATA_BOUNDARY_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_extension_data_boundary_assessment.py"
)
EXTENSION_GAP_PATH_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_gap_paths_20260827.json"
)
EXTENSION_GAP_PATH_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_extension_gap_paths.py"
)
EXTENSION_SQL_ANCHOR_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_sql_anchor_contracts_20260827.json"
)
EXTENSION_SQL_ANCHOR_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_extension_sql_anchor_contracts.py"
)
EXTENSION_SQL_SEMANTICS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_extension_sql_semantics_20260827.json"
)
EXTENSION_SQL_SEMANTICS_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_extension_sql_semantics.py"
)
POS_RECEIPT_REPLICATION_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_pos_receipt_replication_contract_20260827.json"
)
POS_RECEIPT_REPLICATION_BUILDER = (
    ROOT / "scripts" / "windows" / "build_negin_erp_pos_receipt_replication_contract.py"
)
POS_RECEIPT_TRANSITIVE_GRAPH_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_pos_replication_transitive_graph_20260827.json"
)
POS_RECEIPT_TRANSITIVE_GRAPH_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_pos_replication_transitive_graph.py"
)
REQUIREMENTS_TRACEABILITY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_requirements_traceability_20260827.json"
)
REQUIREMENTS_TRACEABILITY_BUILDER = (
    ROOT / "scripts" / "windows" / "build_negin_erp_requirements_traceability.py"
)
POS_SOURCE_MODEL_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_pos_source_model_20260827.json"
)
POS_SOURCE_MODEL_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_pos_source_model.py"
)
BANK_RECONCILIATION_SOURCE_MODEL_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_source_model_20260827.json"
)
BANK_RECONCILIATION_SOURCE_MODEL_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_bank_reconciliation_source_model.py"
)
PRIORITY_GAP_DECLARED_FIELDS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_priority_gap_declared_fields_20260827.json"
)
PRIORITY_GAP_DECLARED_FIELDS_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_priority_gap_declared_fields.py"
)
BANK_RECONCILIATION_COMMAND_GUARDS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_command_guards_20260827.json"
)
BANK_RECONCILIATION_COMMAND_GUARDS_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_bank_reconciliation_command_guards.py"
)
SPECIAL_OPTIONS_DISTRICT_ASSESSMENT_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_special_options_district_assessment_20260827.json"
)
SPECIAL_OPTIONS_DISTRICT_ASSESSMENT_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_special_options_district_assessment.py"
)
BANK_STATEMENT_IMPORT_BOUNDARY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_statement_import_boundary_20260827.json"
)
BANK_STATEMENT_IMPORT_BOUNDARY_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_bank_statement_import_boundary.py"
)
BANK_STATEMENT_PERSISTENCE_BOUNDARY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_statement_persistence_boundary_20260827.json"
)
BANK_STATEMENT_PERSISTENCE_BOUNDARY_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_bank_statement_persistence_boundary.py"
)
BANK_RECONCILIATION_GOLDEN_CASES_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_golden_cases_20260827.json"
)
BANK_RECONCILIATION_GOLDEN_CASES_BUILDER = (
    ROOT / "scripts" / "windows" / "build_negin_erp_bank_reconciliation_golden_cases.py"
)
BANK_RECONCILIATION_TRANSACTION_BOUNDARY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_transaction_boundary_20260827.json"
)
BANK_RECONCILIATION_TRANSACTION_BOUNDARY_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_bank_reconciliation_transaction_boundary.py"
)
BANK_RECONCILIATION_CARDEX_SQL_BOUNDARY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_cardex_sql_boundary_20260827.json"
)
BANK_RECONCILIATION_CARDEX_SQL_BOUNDARY_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_bank_reconciliation_cardex_sql_boundary.py"
)
BANK_RECONCILIATION_MATCHING_BOUNDARY_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_matching_boundary_20260827.json"
)
BANK_RECONCILIATION_MATCHING_BOUNDARY_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_bank_reconciliation_matching_boundary.py"
)
BANK_RECONCILIATION_SUMMARY_UI_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_summary_ui_boundary_20260827.json"
)
BANK_RECONCILIATION_SUMMARY_UI_EXTRACTOR = (
    ROOT
    / "scripts"
    / "windows"
    / "extract_varanegar_bank_reconciliation_summary_ui_boundary.py"
)
BANK_RECONCILIATION_SUMMARY_SQL_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_summary_sql_semantics_20260827.json"
)
BANK_RECONCILIATION_SUMMARY_SQL_EXTRACTOR = (
    ROOT
    / "scripts"
    / "sql"
    / "extract_varanegar_bank_reconciliation_summary_sql_semantics.py"
)
BANK_STATEMENT_PARSER_ROW_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_statement_parser_row_contract_20260827.json"
)
BANK_STATEMENT_PARSER_ROW_EXTRACTOR = (
    ROOT
    / "scripts"
    / "windows"
    / "extract_varanegar_bank_statement_parser_row_contract.py"
)
BANK_RECONCILIATION_CONFIRM_CARDEX_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_confirm_cardex_semantics_20260827.json"
)
BANK_RECONCILIATION_CONFIRM_CARDEX_EXTRACTOR = (
    ROOT
    / "scripts"
    / "sql"
    / "extract_varanegar_bank_reconciliation_confirm_cardex_semantics.py"
)
BANK_RECONCILIATION_CONFIRM_ORCHESTRATION_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_confirm_orchestration_20260827.json"
)
BANK_RECONCILIATION_CONFIRM_ORCHESTRATION_EXTRACTOR = (
    ROOT
    / "scripts"
    / "windows"
    / "extract_varanegar_bank_reconciliation_confirm_orchestration.py"
)
BANK_RECONCILIATION_DIFFERENTIAL_ACCEPTANCE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_differential_acceptance_20260827.json"
)
BANK_RECONCILIATION_DIFFERENTIAL_ACCEPTANCE_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_reconciliation_differential_acceptance.py"
)
BANK_RECONCILIATION_OWNER_DECISION_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_owner_decision_register_20260827.json"
)
BANK_RECONCILIATION_OWNER_DECISION_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_reconciliation_owner_decision_pack.py"
)
BANK_STATEMENT_PROFILE_TARGET_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_statement_profile_target_contract_20260827.json"
)
BANK_STATEMENT_PROFILE_TARGET_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_statement_profile_target_contract.py"
)
BANK_RECONCILIATION_READ_MODEL_TARGET_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_read_model_contract_20260827.json"
)
BANK_RECONCILIATION_READ_MODEL_TARGET_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_reconciliation_read_model_contract.py"
)
BANK_STATEMENT_STAGING_TARGET_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_statement_staging_target_contract_20260827.json"
)
BANK_STATEMENT_STAGING_TARGET_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_statement_staging_target_contract.py"
)
BANK_RECONCILIATION_STATE_MACHINE_TARGET_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_state_machine_contract_20260827.json"
)
BANK_RECONCILIATION_STATE_MACHINE_TARGET_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_reconciliation_state_machine_contract.py"
)
BANK_RECONCILIATION_COMMAND_ENVELOPE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_command_envelope_20260827.json"
)
BANK_RECONCILIATION_COMMAND_ENVELOPE_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_reconciliation_command_envelope.py"
)
BANK_RECONCILIATION_AUTHENTICATED_UAT_RUNBOOK_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_authenticated_uat_runbook_20260827.json"
)
BANK_RECONCILIATION_AUTHENTICATED_UAT_RUNBOOK_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_reconciliation_authenticated_uat_runbook.py"
)
BANK_RECONCILIATION_EVIDENCE_REQUEST_PACK_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_evidence_request_pack_20260827.json"
)
BANK_RECONCILIATION_EVIDENCE_REQUEST_PACK_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_reconciliation_evidence_request_pack.py"
)
BANK_RECONCILIATION_PROFILE_STATE_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_profile_state_boundary_20260827.json"
)
BANK_RECONCILIATION_PROFILE_STATE_EXTRACTOR = (
    ROOT
    / "scripts"
    / "windows"
    / "extract_varanegar_bank_reconciliation_profile_state_boundary.py"
)
BANK_RECONCILIATION_ROLE_UAT_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_role_uat_20260827.json"
)
BANK_RECONCILIATION_ROLE_UAT_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_reconciliation_role_uat.py"
)
BANK_RECONCILIATION_IMPLEMENTATION_READINESS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_bank_reconciliation_implementation_readiness_20260827.json"
)
BANK_RECONCILIATION_IMPLEMENTATION_READINESS_BUILDER = (
    ROOT
    / "scripts"
    / "windows"
    / "build_negin_erp_bank_reconciliation_implementation_readiness.py"
)
BANK_RECONCILIATION_INTEGRITY_AGGREGATES_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_integrity_aggregates_20260827.json"
)
BANK_RECONCILIATION_INTEGRITY_AGGREGATES_EXTRACTOR = (
    ROOT
    / "scripts"
    / "sql"
    / "extract_varanegar_bank_reconciliation_integrity_aggregates.py"
)
BANK_RECONCILIATION_TYPE_ALIAS_AGGREGATES_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_type_alias_aggregates_20260827.json"
)
BANK_RECONCILIATION_TYPE_ALIAS_AGGREGATES_EXTRACTOR = (
    ROOT
    / "scripts"
    / "sql"
    / "extract_varanegar_bank_reconciliation_type_alias_aggregates.py"
)
BANK_RECONCILIATION_PERMISSION_CATALOG_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_permission_catalog_20260827.json"
)
BANK_RECONCILIATION_PERMISSION_CATALOG_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_bank_reconciliation_permission_catalog.py"
)
BANK_RECONCILIATION_DELETE_SEMANTICS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_delete_semantics_20260827.json"
)
BANK_RECONCILIATION_DELETE_SEMANTICS_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_bank_reconciliation_delete_semantics.py"
)
BANK_RECONCILIATION_UNMATCH_SQL_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_unmatch_sql_semantics_20260827.json"
)
BANK_RECONCILIATION_UNMATCH_SQL_EXTRACTOR = (
    ROOT
    / "scripts"
    / "sql"
    / "extract_varanegar_bank_reconciliation_unmatch_sql_semantics.py"
)
BANK_RECONCILIATION_DISCARD_CANCEL_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_bank_reconciliation_discard_cancel_boundary_20260827.json"
)
BANK_RECONCILIATION_DISCARD_CANCEL_EXTRACTOR = (
    ROOT
    / "scripts"
    / "windows"
    / "extract_varanegar_bank_reconciliation_discard_cancel_boundary.py"
)
STACK_RECOVERY_DECISION_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_stack_recovery_decision_input_20260827.json"
)
STACK_RECOVERY_DECISION_BUILDER = (
    ROOT / "scripts" / "windows" / "build_negin_erp_stack_and_recovery_decision_input.py"
)
UI_CHECKPOINT_ARTIFACT = (
    ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_ui_checkpoint_20260827_0300.json"
)
UI_CHECKPOINT_COMPARISON_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_ui_checkpoint_comparison_20260827_0300.json"
)
UI_CHECKPOINT_COMPARISON_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_ui_checkpoint_comparison.py"
)
END_TO_END_PROCESS_ATLAS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "negin_erp_end_to_end_process_atlas_20260827.json"
)
END_TO_END_PROCESS_ATLAS_BUILDER = (
    ROOT / "scripts" / "windows" / "build_negin_erp_end_to_end_process_atlas.py"
)
REPORT_TARGET_GOLDEN_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_report_target_contracts_golden_cases_20260827.json"
)
REPORT_TARGET_GOLDEN_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_report_target_contracts_and_golden_cases.py"
)
REPORT_DEPENDENCY_GRAPH_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_report_dependency_graph_20260827.json"
)
REPORT_DEPENDENCY_GRAPH_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_report_dependency_graph.py"
)
REPORT_SQL_CANDIDATES_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_report_sql_candidates_20260827.json"
)
REPORT_SQL_CANDIDATES_EXTRACTOR = (
    ROOT / "scripts" / "sql" / "extract_varanegar_report_sql_candidates.py"
)
REPORT_METHOD_PATHS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_report_method_paths_20260827.json"
)
REPORT_METHOD_PATHS_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_report_method_paths.py"
)
REPORT_EVIDENCE_GAPS_ARTIFACT = (
    ROOT
    / "artifacts"
    / "varanegar_analysis"
    / "ui"
    / "varanegar_report_evidence_gaps_20260827.json"
)
REPORT_EVIDENCE_GAPS_BUILDER = (
    ROOT / "scripts" / "windows" / "build_varanegar_report_evidence_gap_register.py"
)
REPORT_SHELL_ENTRYPOINTS_ARTIFACT = (
    ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_report_shell_entrypoints_20260827.json"
)
REPORT_SHELL_ENTRYPOINTS_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_report_shell_entrypoints.py"
)
REPORT_SHELL_CALLER_PATHS_ARTIFACT = (
    ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_report_shell_caller_paths_20260827.json"
)
REPORT_SHELL_CALLER_PATHS_EXTRACTOR = (
    ROOT / "scripts" / "windows" / "extract_varanegar_report_shell_caller_paths.py"
)
REPORT_GENERIC_BINDINGS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_report_generic_bindings_20260827.json"
REPORT_GENERIC_BINDINGS_EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_report_generic_bindings.py"
REPORT_GENERIC_SQL_CANDIDATES_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_report_generic_sql_candidates_20260827.json"
REPORT_GENERIC_SQL_CANDIDATES_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_report_generic_sql_candidates.py"
REPORT_GENERIC_SQL_SEMANTICS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_report_generic_sql_semantics_20260827.json"
REPORT_GENERIC_SQL_SEMANTICS_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_report_generic_sql_semantics.py"
ROLE_UAT_CASES_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "negin_erp_role_uat_cases_20260827.json"
ROLE_UAT_CASES_BUILDER = ROOT / "scripts" / "windows" / "build_negin_erp_role_uat_cases.py"
DATA_ENTRY_FIELD_DICTIONARY_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_data_entry_field_dictionary_20260827.json"
DATA_ENTRY_FIELD_DICTIONARY_BUILDER = ROOT / "scripts" / "windows" / "build_varanegar_data_entry_field_dictionary.py"
DATA_ENTRY_DECLARED_FIELDS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_data_entry_declared_fields_20260827.json"
DATA_ENTRY_DECLARED_FIELDS_EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_data_entry_declared_fields.py"
DATA_ENTRY_BASE_TEMPLATE_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_data_entry_base_template_contracts_20260827.json"
DATA_ENTRY_BASE_TEMPLATE_EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_data_entry_base_template_contracts.py"
DATA_ENTRY_FIELD_TYPES_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_data_entry_field_types_20260827.json"
DATA_ENTRY_FIELD_TYPES_EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_data_entry_field_types.py"
DATA_ENTRY_FIELD_BINDING_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_data_entry_field_binding_candidates_20260827.json"
DATA_ENTRY_FIELD_BINDING_BUILDER = ROOT / "scripts" / "windows" / "build_varanegar_data_entry_field_binding_candidates.py"
DATA_ENTRY_FIELD_SQL_COLUMNS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_data_entry_field_sql_columns_20260827.json"
DATA_ENTRY_FIELD_SQL_COLUMNS_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_data_entry_field_sql_column_candidates.py"
TREASURY_EDIT_COMMAND_PATHS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_treasury_edit_command_paths_20260827.json"
TREASURY_EDIT_COMMAND_PATHS_BUILDER = ROOT / "scripts" / "windows" / "build_varanegar_treasury_edit_command_paths.py"
TREASURY_EDIT_SOURCE_MODEL_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_treasury_edit_source_model_20260827.json"
TREASURY_EDIT_SOURCE_MODEL_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_treasury_edit_source_model.py"
TREASURY_TRIGGER_SEMANTICS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_treasury_trigger_semantics_20260827.json"
TREASURY_TRIGGER_SEMANTICS_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_treasury_trigger_semantics.py"
TREASURY_VIEW_LINEAGE_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_treasury_view_column_lineage_20260827.json"
TREASURY_VIEW_LINEAGE_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_treasury_view_column_lineage.py"
TREASURY_TARGET_CONTRACTS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "negin_erp_treasury_edit_target_contracts_20260827.json"
TREASURY_TARGET_CONTRACTS_BUILDER = ROOT / "scripts" / "windows" / "build_negin_erp_treasury_edit_target_contracts.py"
TREASURY_VALIDATION_CONTRACTS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_treasury_edit_validation_contracts_20260827.json"
TREASURY_VALIDATION_CONTRACTS_BUILDER = ROOT / "scripts" / "windows" / "build_varanegar_treasury_edit_validation_contracts.py"
TREASURY_TRIGGER_TRANSITIVE_GRAPH_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_treasury_trigger_transitive_graph_20260827.json"
TREASURY_TRIGGER_TRANSITIVE_GRAPH_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_treasury_trigger_transitive_graph.py"
TREASURY_WEB_FIELD_CONTRACTS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_treasury_web_field_contract_candidates_20260827.json"
TREASURY_WEB_FIELD_CONTRACTS_BUILDER = ROOT / "scripts" / "windows" / "build_varanegar_treasury_web_field_contract_candidates.py"
TREASURY_UI_LABELS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_treasury_ui_label_candidates_20260827.json"
TREASURY_UI_LABELS_EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_treasury_ui_label_candidates.py"
TREASURY_WEB_SCREENS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "negin_erp_treasury_web_screen_contract_candidates_20260827.json"
TREASURY_WEB_SCREENS_BUILDER = ROOT / "scripts" / "windows" / "build_negin_erp_treasury_web_screen_contract_candidates.py"
ORDER_SALE_COMMANDS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_order_sale_entry_command_contracts_20260827.json"
ORDER_SALE_COMMANDS_BUILDER = ROOT / "scripts" / "windows" / "build_varanegar_order_sale_entry_command_contracts.py"
ORDER_SALE_UI_LABELS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_order_sale_ui_label_candidates_20260827.json"
ORDER_SALE_UI_LABELS_EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_order_sale_ui_label_candidates.py"
ORDER_SALE_FULL_FIELDS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_order_sale_full_field_metadata_20260827.json"
ORDER_SALE_FULL_FIELDS_EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_order_sale_full_field_metadata.py"
ORDER_SALE_LAYOUT_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_order_sale_layout_bindings_20260827.json"
ORDER_SALE_LAYOUT_EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_order_sale_layout_bindings.py"
ORDER_SALE_WEB_SCREENS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "negin_erp_order_sale_web_screen_contract_candidates_20260827.json"
ORDER_SALE_WEB_SCREENS_BUILDER = ROOT / "scripts" / "windows" / "build_negin_erp_order_sale_web_screen_contract_candidates.py"
ORDER_SALE_DEPENDENCY_GRAPH_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_order_sale_command_dependency_graph_20260827.json"
ORDER_SALE_DEPENDENCY_GRAPH_EXTRACTOR = ROOT / "scripts" / "windows" / "extract_varanegar_order_sale_command_dependency_graph.py"
ORDER_SALE_SQL_SEMANTICS_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_order_sale_sql_semantics_20260827.json"
ORDER_SALE_SQL_SEMANTICS_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_order_sale_sql_semantics.py"
ORDER_SALE_SOURCE_MODEL_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_order_sale_mutation_source_model_20260827.json"
ORDER_SALE_SOURCE_MODEL_EXTRACTOR = ROOT / "scripts" / "sql" / "extract_varanegar_order_sale_mutation_source_model.py"
ORDER_SALE_TRIGGER_GRAPH_ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_order_sale_trigger_transitive_graph_20260827.json"
DOCUMENT = ROOT / "docs" / "varanegar_reconstruction" / "UI_RUNTIME_INVENTORY_20260827_FA.md"


def _mapping_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(map(str, value)) | {
            key for child in value.values() for key in _mapping_keys(child)
        }
    if isinstance(value, list):
        return {key for child in value for key in _mapping_keys(child)}
    return set()


def test_ui_extractor_contains_no_mutating_automation_calls() -> None:
    source = EXTRACTOR.read_text(encoding="utf-8")
    forbidden = (
        r"\.Invoke\s*\(",
        r"GetCurrentPattern\s*\(",
        r"\.SetValue\s*\(",
        r"\.SetFocus\s*\(",
        r"SendKeys",
        r"mouse_event",
        r"keybd_event",
        r"ClickInput",
    )
    for pattern in forbidden:
        assert re.search(pattern, source, flags=re.IGNORECASE) is None, pattern
    assert "TreeScope]::Descendants" not in source
    assert "Get-ReadOnlyDescendants" in source
    assert "MaximumElements = 5000" in source


def test_ui_inventory_is_read_only_and_contains_no_raw_bound_values() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert payload["artifact"] == "varanegar_windows_ui_inventory"
    assert payload["source"]["machine_ipv4"] == "192.168.1.184"
    assert payload["source"]["process_name"] == "VN.SDS.Container"
    assert payload["safety"] == {
        "mode": "READ_ONLY_UI_OBSERVATION",
        "invoked_controls": 0,
        "input_events_sent": 0,
        "values_set": 0,
        "win32_messages_sent": 0,
        "screenshots_persisted": 0,
        "raw_data_bound_names_persisted": 0,
        "safe_label_policy": (
            "exact reviewed UTF-8 allowlist; all other names are fingerprint-only"
        ),
    }
    assert payload["summary"]["top_level_window_count"] >= 1
    assert payload["summary"]["observed_control_count"] >= 1
    assert payload["summary"]["win32_child_window_count"] >= 1
    forbidden_keys = {
        "raw_name",
        "raw_text",
        "value",
        "password",
        "username",
        "customer_name",
        "national_code",
        "cheque_number",
    }
    assert forbidden_keys.isdisjoint(_mapping_keys(payload))


def test_persisted_safe_labels_cannot_contain_value_markers() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    labels = [row["safe_label"] for row in payload["safe_named_controls"]]
    assert labels
    for label in labels:
        assert len(label) <= 160
        assert not re.search(r"[0-9۰-۹]", label)
        assert "@" not in label
        assert "\\" not in label
        assert "/" not in label


def test_cheque_tracking_forms_expose_read_only_ui_contract() -> None:
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    rows = payload["win32_window_tree"]
    expected_forms = {
        "پيگيري چکهاي دريافتني",
        "پيگيري چکهاي پرداختني",
    }
    assert expected_forms <= {
        row["safe_title"] for row in rows if row["safe_title"]
    }
    disabled_change_buttons = [
        row
        for row in rows
        if row["safe_title"] == "تغيير وضعيت"
        and row["is_visible"]
        and not row["is_enabled"]
    ]
    assert len(disabled_change_buttons) == 2
    for label in (
        "تاريخ پِيگيرِي:",
        "تعداد انتخابي:",
        "مبلغ:",
        "توضيحات:",
        "تغيير به وضعيت:",
    ):
        assert sum(row["safe_title"] == label for row in rows) == 2


def test_ui_contract_is_linked_and_documents_reproduction_and_open_questions() -> None:
    document = DOCUMENT.read_text(encoding="utf-8")
    readme = (
        ROOT / "docs" / "varanegar_reconstruction" / "README_FA.md"
    ).read_text(encoding="utf-8")
    discovery_log = (
        ROOT / "docs" / "varanegar_reconstruction" / "DISCOVERY_LOG_FA.md"
    ).read_text(encoding="utf-8")
    assert DOCUMENT.name in readme
    assert DOCUMENT.name in discovery_log
    assert "Golden Case" in document
    assert "ابهام‌های باز" in document
    assert "دستور بازتولید" in document
    for forbidden_operation in ("Invoke", "SetValue", "SendKeys"):
        assert forbidden_operation in document


def test_binary_inventory_is_metadata_only_and_has_core_module_layers() -> None:
    payload = json.loads(BINARY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "READ_ONLY_FILE_METADATA",
        "config_files_read": 0,
        "executable_code_invoked": 0,
        "assemblies_loaded": 0,
        "credentials_persisted": 0,
    }
    families = {row["family"]: row for row in payload["families"]}
    for family in (
        "VN.SDS.MainData",
        "VN.SDS.Sales",
        "VN.SDS.Stock",
        "VN.SDS.Treasury",
    ):
        assert {"Business", "DataAccess", "IBusiness", "UI", "UIComponent"} <= set(
            families[family]["layers"]
        )
    assert "Forms" in families["TreasuryOld"]["layers"]
    assert all(len(row["sha256"]) == 64 for row in payload["files"])
    assert not any(row["name"].endswith(".config") for row in payload["files"])


def test_assembly_contracts_are_metadata_only_and_cover_runtime_domains() -> None:
    payload = json.loads(ASSEMBLY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "READ_ONLY_DOTNET_METADATA",
        "assemblies_loaded_or_executed": 0,
        "method_bodies_read": 0,
        "user_strings_read": 0,
        "resources_read": 0,
        "config_files_read": 0,
        "credentials_persisted": 0,
    }
    assert payload["summary"]["selected_file_count"] == payload["summary"][
        "analyzed_file_count"
    ]
    assert payload["summary"]["failed_file_count"] == 0
    assert payload["summary"]["type_count"] > 0
    assemblies = {row["file"]: row for row in payload["assemblies"]}
    assert "TreasuryOld.Forms.dll" in assemblies
    assert "VN.SDS.Stock.UI.dll" in assemblies
    assert "VN.SDS.Sales.UI.dll" in assemblies
    assert assemblies["TreasuryOld.Forms.dll"]["form_candidates"]
    assert assemblies["VN.SDS.Stock.UI.dll"]["business_contract_candidates"]
    all_forms = [
        form
        for assembly in payload["assemblies"]
        for form in assembly["form_candidates"]
    ]
    assert all(form.get("base_type") != "System.Enum" for form in all_forms)
    assert not any(form["type"] in {"FORM_BUTTON", "FormulaTypeEnum"} for form in all_forms)


def test_targeted_il_is_redacted_and_links_received_cheque_load_to_adapter() -> None:
    payload = json.loads(IL_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"]["mode"] == "READ_ONLY_TARGETED_IL"
    assert payload["safety"]["assemblies_loaded_or_executed"] == 0
    assert payload["safety"]["config_files_read"] == 0
    assert payload["safety"]["raw_non_allowlisted_strings_persisted"] == 0
    assert payload["summary"]["method_body_error_count"] == 0
    types = {
        target["type"]: target
        for assembly in payload["assemblies"]
        for target in assembly["target_types"]
    }
    tracking = types["TreasuryOld.Forms.frmRChequeTrackingNew"]
    load_data = next(row for row in tracking["methods"] if row["method"] == "LoadData")
    assert "TreasuryOld.DataLayer.RChequeAdapter.GetRChequeSWhere" in load_data[
        "calls"
    ]
    assert any(
        literal.get("safe_literal", "").startswith("RChequeStatusId in")
        for literal in load_data["string_literals"]
    )
    assert "VN.SDS.Container.MainForm" in types
    assert "VN.SDS.Container.Program" in types
    payable = types["TreasuryOld.Forms.frmPChequeTrackingNew"]
    payable_load = next(row for row in payable["methods"] if row["method"] == "LoadData")
    assert "TreasuryOld.DataLayer.PChequeAdapter.GetPChequeSWhere" in payable_load[
        "calls"
    ]
    assert any(
        literal.get("safe_literal", "").strip().startswith("PChequeStatusId in (1,5)")
        for literal in payable_load["string_literals"]
    )
    stock = types["VN.SDS.Stock.UI.StockGoods.FormStockGoods"]
    stock_load = next(row for row in stock["methods"] if row["method"] == "LoadInitData")
    assert (
        "VN.SDS.Stock.UIComponent.StockGoods.StockGoodsUIHelper.StockGoodsGridServerModeDC"
        in stock_load["calls"]
    )
    distribution = types["VN.SDS.Sales.UI.DistManagement.FormDistManagementList"]
    exit_command = next(
        row for row in distribution["methods"] if row["method"] == "SetExitexportation"
    )
    assert "VN.SDS.Sales.Business.Dist.DistHandler.CreateExitVocherByDist" in exit_command[
        "calls"
    ]
    permissions = types["VN.SDS.Container.Program"]
    fill_permissions = next(
        row for row in permissions["methods"] if row["method"] == "FillUserPermissionS"
    )
    assert (
        "VN.SDS.Setting.Business.AccessNodeInfo.AccessNodeInfoHandler.GetInstance"
        in fill_permissions["calls"]
    )
    serialized = json.dumps(payload, ensure_ascii=False).casefold()
    for forbidden in (
        "password=",
        "pwd=",
        "user id=",
        "data source=",
        "initial catalog=",
        "sk-proj-",
    ):
        assert forbidden not in serialized


def test_ui_sql_contract_extractor_and_artifact_are_read_only() -> None:
    source = SQL_CONTRACT_EXTRACTOR.read_text(encoding="utf-8")
    static_sql = "\n".join(re.findall(r'"""(.*?)"""', source, flags=re.DOTALL))
    for forbidden in (" insert ", " update ", " delete ", " merge ", " execute ", " exec "):
        assert forbidden not in f" {static_sql.casefold()} "

    payload = json.loads(SQL_CONTRACT_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"]["mode"] == "READ_ONLY_CLONE_METADATA"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] == 1
    assert payload["safety"]["application_procedures_executed"] == 0
    assert payload["safety"]["business_rows_read_or_persisted"] == 0
    assert payload["safety"]["raw_definitions_persisted"] == 0
    assert payload["summary"]["missing_required"] == []
    contracts = {row["object"].casefold(): row for row in payload["contracts"]}
    assert contracts["sle.usp_sdsnet_createdist"]["found"] is True
    assert contracts["dbo.dorcheque_addrchequehistory"]["parameters"]
    assert contracts["dbo.dopcheque_addpchequehistory"]["parameters"]
    assert contracts["gnr.vwstockgoods_servermode"]["found"] is True


def test_capability_matrix_separates_commands_context_and_data_partition() -> None:
    payload = json.loads(CAPABILITY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "DERIVED_FROM_READ_ONLY_REDACTED_EVIDENCE",
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "database_queries_executed_by_builder": 0,
        "raw_business_values_persisted": 0,
    }
    assert payload["summary"]["all_evidence_assertions_passed"] is True
    assert payload["summary"]["selection_guard_observed_for_both_cheque_forms"] is True
    capabilities = {row["capability"]: row for row in payload["capabilities"]}
    assert "distribution.issue_exit" in capabilities
    assert "received_cheque.change_status" in capabilities
    assert "payable_cheque.undo" in capabilities
    assert all(row["permission_source"] for row in capabilities.values())
    assert all(row["context_guards"] for row in capabilities.values())
    assert all(row["data_partition"] for row in capabilities.values())


def test_form_catalog_is_metadata_only_and_keeps_classification_limits() -> None:
    payload = json.loads(FORM_CATALOG_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "DERIVED_FROM_DOTNET_METADATA_ONLY",
        "assemblies_loaded_or_executed": 0,
        "method_bodies_read": 0,
        "resources_or_user_strings_read": 0,
        "live_ui_actions": 0,
        "database_queries": 0,
    }
    assert payload["summary"]["form_candidate_count"] >= 400
    assert payload["summary"]["high_confidence_form_count"] >= 350
    assert payload["classification_limits"]
    assert all(row["base_type"] != "System.Enum" for row in payload["forms"])
    types = {row["type"] for row in payload["forms"]}
    assert "VN.SDS.Stock.UI.StockGoods.FormStockGoods" in types
    assert "VN.SDS.Sales.UI.DistManagement.FormDistManagementList" in types
    assert "TreasuryOld.Forms.frmRChequeTrackingNew" in types


def test_workflow_catalog_covers_all_workflow_forms_without_execution() -> None:
    payload = json.loads(WORKFLOW_CATALOG_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "DERIVED_FROM_REDACTED_TARGETED_IL",
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "assemblies_loaded_or_executed": 0,
        "database_queries": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    assert payload["summary"]["workflow_form_count"] == 20
    assert payload["summary"]["analyzed_count"] == 20
    assert payload["summary"]["missing_target_count"] == 0
    assert payload["summary"]["command_method_count"] > 40
    workflows = {row["type"]: row for row in payload["workflows"]}
    guarantee = workflows["TreasuryOld.Forms.frmGuaranteeTracking"]
    assert "DoChangeStatusCheque" in guarantee["command_methods"]
    receipt = workflows[
        "VN.SDS.Treasury.UI.ReceiptManagment.FormReceiptManagmentTracking"
    ]
    assert "ConfirmCommand" in receipt["command_methods"]
    assert "UnConfirmCommand" in receipt["command_methods"]


def test_report_catalog_covers_all_report_forms_without_running_reports() -> None:
    payload = json.loads(REPORT_CATALOG_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "DERIVED_FROM_REDACTED_TARGETED_IL",
        "live_ui_actions": 0,
        "reports_executed": 0,
        "exports_created": 0,
        "assemblies_loaded_or_executed": 0,
        "database_queries": 0,
        "raw_report_rows_persisted": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    assert payload["summary"]["report_form_count"] == 20
    assert payload["summary"]["analyzed_count"] == 20
    assert payload["summary"]["missing_target_count"] == 0
    reports = {row["type"]: row for row in payload["reports"]}
    assert "VN.SDS.MainData.UI.Supplier.FormSupplierCardex" in reports
    assert "VN.SDS.Sales.UI.Customers.FormCustCardex" in reports
    assert "VN.SDS.Stock.UI.VchHealthyCardex.FormVchHealthyCardex" in reports


def test_menu_route_catalog_excludes_users_urls_and_writes() -> None:
    source = MENU_ROUTE_EXTRACTOR.read_text(encoding="utf-8")
    static_sql = "\n".join(re.findall(r'"""(.*?)"""', source, flags=re.DOTALL))
    for forbidden in (" insert ", " update ", " delete ", " merge ", " execute ", " exec "):
        assert forbidden not in f" {static_sql.casefold()} "
    payload = json.loads(MENU_ROUTE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_STATIC_CONFIGURATION",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "user_or_group_right_rows_read": 0,
        "user_identities_persisted": 0,
        "urls_read_or_persisted": 0,
        "operational_business_rows_read": 0,
        "write_statements_executed": 0,
        "credentials_persisted": 0,
    }
    assert payload["summary"]["route_row_count"] > 0
    assert payload["summary"]["route_with_form_count"] > 0
    serialized = json.dumps(payload, ensure_ascii=False).casefold()
    assert '"url"' not in serialized
    assert '"app_user"' not in serialized
    assert '"user_name"' not in serialized


def test_menu_form_crosswalk_resolves_the_four_open_forms() -> None:
    payload = json.loads(MENU_FORM_CROSSWALK_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "DERIVED_FROM_READ_ONLY_REDACTED_EVIDENCE",
        "live_ui_actions": 0,
        "database_queries_executed_by_builder": 0,
        "user_or_group_rights_read": 0,
        "operational_business_rows_read_or_persisted": 0,
    }
    assert payload["summary"]["open_window_count"] == 4
    assert payload["summary"]["open_window_with_unique_route_count"] == 4
    resolved = {
        row["ui_title"]: row["routes"][0]["matched_form_type"]
        for row in payload["open_form_routes"]
    }
    assert resolved["اقلام انبار"] == "VN.SDS.Stock.UI.StockGoods.FormStockGoods"
    assert resolved["مديريت توزيع"] == (
        "VN.SDS.Sales.UI.DistManagement.FormDistManagementList"
    )
    assert resolved["پيگيري چکهاي دريافتني"] == (
        "TreasuryOld.Forms.frmRChequeTracking"
    )
    assert resolved["پيگيري چکهاي پرداختني"] == (
        "TreasuryOld.Forms.frmPChequeTracking"
    )


def test_route_authorization_matrix_is_anonymous_aggregate_and_read_only() -> None:
    source = ROUTE_AUTHORIZATION_EXTRACTOR.read_text(encoding="utf-8")
    static_sql = "\n".join(re.findall(r'"""(.*?)"""', source, flags=re.DOTALL))
    for forbidden in (" insert ", " update ", " delete ", " merge ", " execute ", " exec "):
        assert forbidden not in f" {static_sql.casefold()} "

    payload = json.loads(ROUTE_AUTHORIZATION_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATE_AUTHORIZATION",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "identities_or_group_names_persisted": 0,
        "individual_memberships_or_grants_persisted": 0,
        "business_rows_read_or_persisted": 0,
        "write_statements_executed": 0,
        "live_ui_actions": 0,
    }
    assert payload["summary"]["open_route_count"] == 4
    assert payload["summary"]["authorization_node_count"] == 40
    assert payload["summary"]["command_node_count"] == 36
    nodes = {
        (row["root_access_node_id"], row["access_node_key"].get("value")): row
        for row in payload["nodes"]
    }
    assert nodes[(42, "ChangeStatus")]["rights"]["effective_active_users"]
    assert nodes[(42, "Undo")]["rights"]["effective_active_users"]
    assert nodes[(43, "ChangeStatus")]["rights"]["effective_active_users"]
    assert nodes[(412, "RemoveExitFromDist")]["rights"]["effective_active_users"]
    assert nodes[(412, "issuanceOutput")]["rights"]["effective_active_users"][
        "explicit_deny"
    ] == 3
    serialized = json.dumps(payload, ensure_ascii=False).casefold()
    for forbidden in (
        '"username":',
        '"user_name":',
        '"group_name":',
        '"password":',
        '"token":',
    ):
        assert forbidden not in serialized


def test_runtime_drift_baseline_is_offline_and_componentized() -> None:
    source = DRIFT_BASELINE_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    assert "pymssql" not in source.casefold()

    payload = json.loads(DRIFT_BASELINE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_REDACTED_READ_ONLY_EVIDENCE",
        "database_connections": 0,
        "live_ui_actions": 0,
        "network_reads": 0,
        "application_commands_executed": 0,
        "business_rows_read_or_persisted": 0,
        "credentials_persisted": 0,
    }
    assert payload["comparison"]["status"] == "NO_SEMANTIC_DRIFT"
    assert payload["comparison"]["unchanged_source_count"] == 178
    assert payload["release_identity"]["binary_file_count"] == 62
    assert payload["release_identity"]["sql_contract_count"] == 12
    assert payload["release_identity"]["route_authorization_node_count"] == 40
    assert set(payload["groups"]) == {
        "runtime_package",
        "navigation_surface",
        "behavioral_contracts",
        "deep_command_boundaries",
        "target_verification",
        "authorization_surface",
        "session_surface",
        "reconstruction_bundle",
    }
    assert {name: row["source_count"] for name, row in payload["groups"].items()} == {
        "runtime_package": 3,
        "navigation_surface": 7,
        "behavioral_contracts": 67,
            "deep_command_boundaries": 72,
        "target_verification": 17,
        "authorization_surface": 2,
        "session_surface": 9,
        "reconstruction_bundle": 1,
    }
    assert set(payload["groups"]["target_verification"]["sources"]) == {
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
    }
    assert all(
        len(row["semantic_sha256"]) == 64 for row in payload["groups"].values()
    )
    assert len(payload["release_identity"]["overall_semantic_sha256"]) == 64


def test_active_page_contracts_cover_fields_filters_validators_and_sql() -> None:
    source = ACTIVE_PAGE_CONTRACTS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(ACTIVE_PAGE_CONTRACTS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_REDACTED_READ_ONLY_EVIDENCE",
        "database_connections": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "business_rows_or_bound_values_read_or_persisted": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    assert payload["summary"]["page_count"] == 4
    assert payload["summary"]["missing_type_count"] == 0
    assert payload["summary"]["grid_column_count"] == 45
    assert payload["summary"]["sql_contract_count"] == 12
    assert payload["summary"]["authorization_node_count"] == 40
    pages = {row["page_id"]: row for row in payload["pages"]}
    assert "RChequeHistoryId" in pages["received_cheque_tracking"]["grid_columns"]
    assert "PChequeBookItemId" in pages["payable_cheque_tracking"]["grid_columns"]
    stock_fields = {
        row["field"] for row in pages["stock_goods"]["entity_field_candidates"]
    }
    assert {"GoodsRef", "StockDCRef", "OrderPoint", "OnHandQty"} <= stock_fields
    dist_fields = {
        row["field"]
        for row in pages["distribution_management"]["entity_field_candidates"]
    }
    assert {"DistNo", "DistPath", "TruckRef", "LockedByAppUserForExit"} <= dist_fields
    assert all(row["missing_types"] == [] for row in pages.values())
    assert all(row["validation_methods"] for row in pages.values())


def test_state_machine_catalog_separates_configured_observed_and_current() -> None:
    source = STATE_MACHINE_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(STATE_MACHINE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_AGGREGATE_READ_ONLY_EVIDENCE",
        "database_connections": 0,
        "live_ui_actions": 0,
        "commands_or_transitions_executed": 0,
        "individual_instrument_or_distribution_rows_persisted": 0,
        "identities_or_amounts_persisted": 0,
    }
    assert payload["summary"] == {
        "machine_count": 3,
        "state_count": 22,
        "configured_allowed_transition_count": 26,
        "observed_transition_count": 34,
        "observed_outside_configured_cheque_workflow_count": 0,
    }
    machines = {row["machine_id"]: row for row in payload["state_machines"]}
    received = machines["received_cheque"]
    payable = machines["payable_cheque"]
    distribution = machines["distribution"]
    assert received["observed_outside_allowed"] == []
    assert payable["observed_outside_allowed"] == []
    assert {(row["from"], row["to"]) for row in received["allowed_but_unobserved"]} == {
        (1, 9), (9, 1), (9, 4)
    }
    assert {(row["from"], row["to"]) for row in payable["allowed_but_unobserved"]} == {
        (1, 3), (3, 4), (5, 4)
    }
    assert distribution["allowed_transitions"] is None
    assert distribution["canonical_observed_path"] == [
        {"from": None, "to": 1},
        {"from": 1, "to": 2},
        {"from": 2, "to": 3},
        {"from": 3, "to": 4},
        {"from": 4, "to": 7},
    ]


def test_command_side_effects_are_metadata_only_and_trace_mutations() -> None:
    source = COMMAND_SIDE_EFFECTS_EXTRACTOR.read_text(encoding="utf-8")
    static_sql = "\n".join(re.findall(r'"""(.*?)"""', source, flags=re.DOTALL))
    for forbidden in (" insert ", " update ", " delete ", " merge ", " execute ", " exec "):
        assert forbidden not in f" {static_sql.casefold()} "
    payload = json.loads(COMMAND_SIDE_EFFECTS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_MODULE_DEPENDENCY_INSPECTION",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "application_procedures_executed": 0,
        "write_statements_executed": 0,
        "raw_module_definitions_persisted": 0,
        "business_rows_read_or_persisted": 0,
        "credentials_or_literal_values_persisted": 0,
        "live_ui_actions": 0,
    }
    assert payload["summary"]["command_trace_count"] == 11
    assert payload["summary"]["sql_object_count"] == 12
    assert payload["summary"]["module_dependency_error_count"] == 0
    assert payload["summary"]["mutation_command_count"] == 8
    assert payload["summary"]["mutation_command_without_explicit_idempotency_parameter_count"] == 8
    traces = {row["command"]: row for row in payload["command_traces"]}
    assert "inv.tblvocherhdr" in traces["distribution.issue_exit"]["mutated_references"]
    assert "sle.tblsaledisthistfull" in traces["distribution.remove_exit"]["ledger_and_history_references"]
    assert "dbo.pchequebookitem" in traces["payable_cheque.undo"]["mutated_references"]
    assert traces["inventory.stock_goods.read"]["mutation_statement_evidence_count"] == 0
    sql_objects = {row["object"]: row for row in payload["sql_objects"]}
    assert sql_objects["dbo.DoRCheque_AddRChequeHistory"]["transaction_evidence"] == {
        "begin_transaction_count": 1,
        "commit_count": 1,
        "rollback_count": 1,
        "try_count": 1,
        "catch_count": 1,
    }
    contract_payload = json.loads(SQL_CONTRACT_ARTIFACT.read_text(encoding="utf-8"))
    contract_hashes = {row["object"]: row["definition_sha256"] for row in contract_payload["contracts"]}
    assert all(
        row["definition_sha256"] == contract_hashes[row["object"]]
        for row in payload["sql_objects"]
    )


def test_golden_command_cases_cover_retry_rollback_and_domain_failures() -> None:
    source = GOLDEN_COMMAND_CASES_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(GOLDEN_COMMAND_CASES_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "OFFLINE_SYNTHETIC_TEST_DESIGN",
        "database_connections": 0,
        "live_ui_actions": 0,
        "commands_executed": 0,
        "business_rows_or_values_used": 0,
        "synthetic_cases_only": 1,
    }
    assert payload["summary"]["source_command_trace_count"] == 11
    assert payload["summary"]["mutating_command_count"] == 8
    assert payload["summary"]["case_count"] == 77
    assert payload["summary"]["generic_mutation_case_count"] == 40
    assert len({row["case_id"] for row in payload["cases"]}) == 77
    by_command: dict[str, list[dict]] = {}
    for row in payload["cases"]:
        by_command.setdefault(row["command"], []).append(row)
    side_effects = json.loads(COMMAND_SIDE_EFFECTS_ARTIFACT.read_text(encoding="utf-8"))
    mutating = {
        row["command"] for row in side_effects["command_traces"] if row["mutation_expected"]
    }
    for command in mutating:
        kinds = {row["kind"] for row in by_command[command]}
        assert {"success", "authorization", "scope", "concurrency", "idempotency", "failure_injection"} <= kinds
        case_ids = {row["case_id"] for row in by_command[command]}
        assert f"{command}.duplicate_command_id" in case_ids
        assert f"{command}.fault_after_first_write" in case_ids
    assert any(row["case_id"].endswith("negative_cardex") for row in payload["cases"])
    assert any(row["case_id"].endswith("voucher_dependency") for row in payload["cases"])


def test_report_execution_contract_separates_preview_export_and_stateful_print() -> None:
    source = REPORT_EXECUTION_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(REPORT_EXECUTION_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_REDACTED_TARGETED_IL",
        "database_connections": 0,
        "reports_rendered": 0,
        "prints_or_exports_created": 0,
        "print_completion_commands_executed": 0,
        "live_ui_actions": 0,
        "business_rows_or_values_persisted": 0,
    }
    assert payload["summary"]["surface_count"] == 20
    assert payload["summary"]["transactional_document_output_count"] == 3
    assert payload["summary"]["file_export_surface_count"] == 3
    assert payload["summary"]["report_like_command_form_count"] == 2
    surfaces = {row["type"]: row for row in payload["surfaces"]}
    for name in (
        "VN.SDS.Sales.UI.PrintBatch.FormPrintBatch",
        "VN.SDS.Sales.UI.Sale.FormReportFactor",
        "VN.SDS.Sales.UI.RetSale.FormReportRetSale",
    ):
        row = surfaces[name]
        assert row["classification"] == "transactional_document_output"
        assert row["execution_flags"]["has_print_completion_read"] is True
        assert row["execution_flags"]["has_print_completion_write"] is True
        assert "document.mark_print_completed" in row["recommended_atomic_permissions"]
    for name in (
        "VN.SDS.Treasury.UI.Statement.FormStatement",
        "VN.SDS.Treasury.UI.Statement.FormStatementDataEntry",
    ):
        assert surfaces[name]["classification"] == "report_like_command_form"
        assert surfaces[name]["execution_flags"]["has_save_command"] is True
    export = surfaces["VN.SDS.Stock.UI.VchHealthyCardex.FormVchHealthyCardex"]
    assert export["execution_flags"]["has_export_to_file"] is True
    assert export["execution_flags"]["has_print_completion_write"] is False


def test_target_erp_blueprint_is_evidence_backed_stack_neutral_and_gated() -> None:
    source = TARGET_ERP_BLUEPRINT_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(TARGET_ERP_BLUEPRINT_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "OFFLINE_TARGET_DESIGN_FROM_REDACTED_READ_ONLY_EVIDENCE",
        "database_connections": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_values_persisted": 0,
        "production_stack_or_cutover_authorized": 0,
    }
    assert payload["architecture_style"]["recommendation"] == (
        "modular_monolith_first_with_explicit_bounded_contexts"
    )
    assert payload["architecture_style"]["stack_status"] == "not_selected_by_user"
    assert payload["module_count"] == 14
    assert len(payload["modules"]) == 14
    assert len(payload["phases"]) == 7
    assert payload["estimated_total_weeks"] == [21, 33]
    assert payload["first_usable_read_only_slice_weeks"] == [3, 5]
    assert payload["evidence_snapshot"]["validated_domain_count"] == 18
    assert payload["evidence_snapshot"]["synthetic_golden_cases"] == 877
    assert payload["evidence_snapshot"]["active_route_golden_cases"] == 77
    assert payload["evidence_snapshot"]["high_impact_orchestrator_golden_cases"] == 154
    assert payload["evidence_snapshot"]["material_extension_golden_cases"] == 215
    assert payload["evidence_snapshot"]["report_query_export_print_golden_cases"] == 175
    assert payload["evidence_snapshot"]["customer_goods_master_data_golden_cases"] == 64
    assert payload["evidence_snapshot"]["supplier_context_pricing_golden_cases"] == 192
    assert payload["evidence_snapshot"][
        "mutating_commands_without_explicit_legacy_idempotency_token"
    ] == 8
    assert set(payload["command_envelope"]["required"]) == {
        "command_id",
        "aggregate_id",
        "expected_version",
        "operational_date",
        "fiscal_year",
        "dc_ref",
        "actor_context",
    }
    assert "writes to operational Varanegar" in payload["not_yet_authorized_or_ready"]


def test_night_evidence_bundle_is_complete_offline_and_reproducible() -> None:
    source = NIGHT_BUNDLE_VALIDATOR.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(NIGHT_BUNDLE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_PROJECT_EVIDENCE_VALIDATION",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "application_or_business_commands_executed": 0,
        "source_or_target_business_rows_changed": 0,
    }
    assert payload["counts"] == {
        "validated_domain_count": 18,
        "ui_artifact_count": 178,
        "document_count": 114,
        "builder_or_extractor_count": 145,
        "error_count": 0,
    }
    assert len(payload["bundle_sha256"]) == 64
    assert len(payload["knowledge_indexes"]) == 2
    assert len(payload["artifacts"]) == 178
    assert all(len(row["sha256"]) == 64 for row in payload["artifacts"])
    assert all(row["schema_version"] == 1 for row in payload["artifacts"])


def test_morning_handoff_bootstrap_accepts_only_its_single_stale_count() -> None:
    path = ROOT / "scripts" / "windows" / "build_negin_erp_morning_readiness_handoff.py"
    spec = importlib.util.spec_from_file_location("morning_handoff_builder", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    allowed_error = module.ALLOWED_NIGHT_BUNDLE_BOOTSTRAP_ERRORS[0]
    assert module._night_bundle_is_acceptable({"validation": "PASS", "errors": []})
    assert module._night_bundle_is_acceptable({"validation": "FAIL", "errors": [allowed_error]})
    assert not module._night_bundle_is_acceptable(
        {"validation": "FAIL", "errors": ["missing artifact: ui/example.json"]}
    )
    assert not module._night_bundle_is_acceptable(
        {"validation": "FAIL", "errors": [allowed_error, "another error"]}
    )


def test_migration_contract_preserves_provenance_and_blocks_unknown_differences() -> None:
    source = MIGRATION_CONTRACT_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(MIGRATION_CONTRACT_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "OFFLINE_TARGET_CONTRACT_FROM_AGGREGATE_READ_ONLY_EVIDENCE",
        "database_connections": 0,
        "source_snapshots_captured": 0,
        "source_or_target_rows_read_or_changed": 0,
        "legacy_repairs_executed": 0,
        "cutover_or_dual_write_authorized": 0,
    }
    assert payload["evidence"] == {
        "validated_domain_count": 18,
        "target_module_count": 14,
        "state_machine_count": 3,
        "golden_case_count": 877,
        "active_route_golden_case_count": 77,
        "high_impact_orchestrator_golden_case_count": 154,
        "material_extension_golden_case_count": 215,
        "report_query_export_print_golden_case_count": 175,
        "customer_goods_master_data_golden_case_count": 64,
        "supplier_context_pricing_golden_case_count": 192,
    }
    assert payload["slice_count"] == 12
    assert [row["order"] for row in payload["ordered_slices"]] == list(range(1, 13))
    assert payload["crosswalk_contract"]["mapping_statuses"] == [
        "exact", "derived", "ambiguous", "quarantined", "retired"
    ]
    assert len(payload["quarantine_contract"]["known_aggregate_baseline"]) == 14
    return_amount_baseline = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"].startswith("RETSALE_")
    )
    assert return_amount_baseline["code"] == "RETSALE_GROSS_NET_ADJUSTMENT_NOT_AN_ERROR"
    assert return_amount_baseline["observed_count"] == 696
    assert "never quarantine solely" in return_amount_baseline["disposition"]
    stock_baseline = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"].startswith("STOCK_")
    )
    assert stock_baseline["code"] == "STOCK_CARDEX_ONLY_GAP_EXPLAINED_BY_OPEN_SALE_OBLIGATION"
    assert stock_baseline["observed_count"] == 1594
    assert "unexplained residual is zero" in stock_baseline["disposition"]
    returned_cheque_baseline = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"].startswith("RETURNED_CHEQUE_")
    )
    assert returned_cheque_baseline["code"] == (
        "RETURNED_CHEQUE_CROSS_CUSTOMER_ALLOCATION_NOT_AN_ERROR"
    )
    assert returned_cheque_baseline["observed_count"] == 49
    assert "accepted source semantics" in returned_cheque_baseline["disposition"]
    received_pay_baseline = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "RECEIVED_CHEQUE_MASTER_PAY_PROJECTION_GAP_NOT_AN_ERROR"
    )
    assert received_pay_baseline["observed_count"] == 8
    assert "never synthesize" in received_pay_baseline["disposition"]
    received_legal_baseline = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "RECEIVED_CHEQUE_LEGAL_TYPE_UNSPECIFIED"
    )
    assert received_legal_baseline["observed_count"] == 35
    assert "never impute" in received_legal_baseline["disposition"]
    payable_leaf_baseline = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "PAYABLE_SOURCE_USED_UNLINKED_LEAF"
    )
    assert payable_leaf_baseline["observed_count"] == 155
    assert "never synthesize" in payable_leaf_baseline["disposition"]
    voucher_fork_baseline = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "VOUCHER_CURRENT_POINTER_HISTORY_FORK"
    )
    assert voucher_fork_baseline["observed_count"] == 1094
    assert "never replace pointer" in voucher_fork_baseline["disposition"]
    empty_shell_baseline = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "VOUCHER_DRAFT_EMPTY_NUMBERED_SHELL"
    )
    assert empty_shell_baseline["observed_count"] == 1
    assert "never synthesize lines" in empty_shell_baseline["disposition"]
    ngt_pending = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "NGT_MOBILE_RETURN_PENDING_OR_UNATTEMPTED"
    )
    assert ngt_pending["observed_count"] == 1
    ngt_missing_target = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "NGT_MOBILE_RETURN_HISTORICAL_RESULT_CURRENT_TARGET_MISSING"
    )
    assert ngt_missing_target["observed_count"] == 1
    assert "never recreate" in ngt_missing_target["disposition"]
    supplier_receipt_component = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "SUPPLIER_RECEIPT_PER_INVOICE_ONLY_GROUP_NOT_AN_ERROR"
    )
    assert supplier_receipt_component["observed_count"] == 5
    assert "connected invoice-receipt component" in supplier_receipt_component["disposition"]
    supplier_return_source = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "SUPPLIER_RETURN_OPTIONAL_SOURCE_ITEM_ABSENT_NOT_AN_INVENTORY_ERROR"
    )
    assert supplier_return_source["observed_count"] == 7
    assert "never auto-reassign" in supplier_return_source["disposition"]
    supplier_return_toll = next(
        row
        for row in payload["quarantine_contract"]["known_aggregate_baseline"]
        if row["code"] == "SUPPLIER_RETURN_STALE_EXPLICIT_TOLL_REF_RESOLVED_BY_HEADER_TOLL_CODE"
    )
    assert supplier_return_toll["observed_count"] == 20
    assert "uniquely recoverable" in supplier_return_toll["disposition"]
    assert payload["reconciliation_contract"]["acceptance_rule"].startswith(
        "no blocking_unknown"
    )
    assert "source write-back" in payload["import_run_contract"]["prohibitions"]


def test_role_sod_contract_is_identity_free_deny_first_and_testable() -> None:
    source = ROLE_SOD_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(ROLE_SOD_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["status"] == "PROVISIONAL_TEMPLATES_REQUIRE_BUSINESS_OWNER_SIGNOFF"
    assert payload["safety"] == {
        "mode": "OFFLINE_IDENTITY_FREE_DERIVATION_FROM_AGGREGATE_AUTHORIZATION_EVIDENCE",
        "database_connections": 0,
        "live_ui_actions": 0,
        "roles_or_grants_changed": 0,
        "user_or_group_identities_persisted": 0,
        "individual_grants_persisted": 0,
    }
    assert payload["evidence"]["observed_capability_count"] == 16
    assert payload["evidence"]["authorization_node_count"] == 40
    assert payload["atomic_capability_count"] == 45
    assert payload["role_template_count"] == 15
    assert payload["sod_rule_count"] == 10
    assert "NOT explicit_deny" in payload["decision_model"]["formula"]
    assert {row["id"] for row in payload["sod_rules"]} == {
        f"SOD-{number:02d}" for number in range(1, 11)
    }
    assert "self-grant and self-approval rejected" in payload["mandatory_negative_tests"]
    serialized = json.dumps(payload, ensure_ascii=False).casefold()
    for forbidden in ('"username":', '"group_name":', '"individual_grants":'):
        assert forbidden not in serialized


def test_all_data_entry_il_contracts_are_hash_matched_and_redacted() -> None:
    source = DATA_ENTRY_IL_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in source
    payload = json.loads(DATA_ENTRY_IL_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "READ_ONLY_PE_METADATA_AND_IL_FROM_RUNTIME_SHARE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "config_or_resource_payloads_read": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["selected_form_count"] == 141
    assert summary["found_form_count"] == 141
    assert summary["missing_form_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert summary["method_body_count"] == 3971
    assert summary["method_body_error_count"] == 1
    assert summary["business_method_body_error_count"] == 0
    assert summary["form_with_write_like_method_count"] == 134
    assert summary["form_with_destructive_or_reversing_method_count"] == 99
    assert summary["form_with_validation_method_count"] == 131
    assert summary["review_priority_counts"] == {"high": 127, "medium": 7, "low": 7}
    assert payload["method_body_errors"] == [
        {
            "type": "VN.SDS.MainData.UI.ServerConfig.FormServerConfig",
            "method": "InitializeComponent",
            "rva": 65240,
            "error_class": "MethodBodyFormatError",
        }
    ]
    assert all(row["found"] for row in payload["forms"])
    for assembly in payload["raw_il"]:
        for target in assembly["target_types"]:
            for method in target["methods"]:
                for literal in method["string_literals"]:
                    if literal["persisted_as"] == "fingerprint_only":
                        assert set(literal) == {"sha256", "length", "persisted_as"}


def test_high_impact_call_graph_reaches_business_and_data_access_without_execution() -> None:
    source = HIGH_IMPACT_CALL_GRAPH_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in source
    payload = json.loads(HIGH_IMPACT_CALL_GRAPH_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "READ_ONLY_PE_METADATA_AND_IL_FROM_RUNTIME_SHARE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "config_or_resource_payloads_read": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    assert payload["summary"] == {
        "selected_form_count": 12,
        "business_assembly_count": 3,
        "business_type_count": 87,
        "business_type_found_count": 87,
        "data_access_assembly_count": 3,
        "data_access_type_count": 43,
        "data_access_type_found_count": 43,
        "form_to_business_edge_count": 140,
        "business_to_data_access_edge_count": 45,
        "business_method_body_count": 1068,
        "data_access_method_body_count": 375,
        "method_body_error_count": 0,
        "source_hash_mismatch_count": 0,
        "business_type_with_transaction_signal_count": 9,
        "business_type_with_persistence_signal_count": 19,
        "selected_form_with_any_transaction_signal_count": 12,
    }
    assert all(row["found"] for row in payload["business_contracts"])
    assert all(row["found"] for row in payload["data_access_contracts"])
    assert all(
        row["has_any_observed_transaction_signal"]
        for row in payload["form_transaction_signals"]
    )
    selected = {row["type"] for row in payload["selected_forms"]}
    assert "VN.SDS.Sales.UI.Order.FormOrderDataEntry" in selected
    assert "VN.SDS.Sales.UI.RetSale.FormRetSaleDataEntry" in selected
    assert "VN.SDS.Stock.UI.SupInvoice.FormSupInvoiceDataEntry" in selected
    assert "VN.SDS.Stock.UI.Vocher.FormVocherDataEntry" in selected


def test_orchestrator_commands_are_method_backed_idempotent_and_failure_tested() -> None:
    source = ORCHESTRATOR_COMMAND_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(ORCHESTRATOR_COMMAND_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_TARGET_COMMAND_DESIGN_FROM_REDACTED_IL_AND_AGGREGATE_EVIDENCE",
        "database_connections": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_values_persisted": 0,
        "production_write_or_cutover_authorized": 0,
    }
    assert payload["command_count"] == 10
    assert payload["evidence"]["evidence_error_count"] == 0
    commands = {row["command"]: row for row in payload["commands"]}
    assert set(commands) == {
        "order.save",
        "order.cancel",
        "order.convert_to_sale",
        "sales_return.save",
        "sales_return.cancel_and_generate_voucher",
        "supplier_invoice.save",
        "supplier_return.save",
        "stock_voucher.save",
        "stock_voucher.confirm_or_unconfirm",
        "stock_voucher.generate_return",
    }
    for row in commands.values():
        assert row["failure_injection_after"]
        assert row["reconciliation"]
        assert "command_id" in row["required_envelope"]
        assert "expected_version" in row["required_envelope"]
        assert "reconciliation_status" in row["required_result"]
    assert "one application command owns the transaction boundary" in payload[
        "shared_execution_rules"
    ]


def test_orchestrator_golden_cases_cover_every_stage_and_forbid_source_execution() -> None:
    source = ORCHESTRATOR_GOLDEN_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(ORCHESTRATOR_GOLDEN_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_SYNTHETIC_TARGET_TEST_DESIGN",
        "database_connections": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_values_used": 0,
        "synthetic_cases_only": 1,
    }
    assert payload["summary"]["source_command_count"] == 10
    assert payload["summary"]["case_count"] == 154
    assert payload["summary"]["common_case_count"] == 70
    assert payload["summary"]["failure_injection_case_count"] == 54
    assert payload["summary"]["domain_specific_case_count"] == 30
    assert payload["summary"]["duplicate_case_id_count"] == 0
    assert len({row["case_id"] for row in payload["cases"]}) == 154
    by_command: dict[str, list[dict]] = {}
    for row in payload["cases"]:
        by_command.setdefault(row["command"], []).append(row)
    assert len(by_command) == 10
    for rows in by_command.values():
        kinds = {row["kind"] for row in rows}
        assert {
            "success",
            "authorization",
            "scope",
            "concurrency",
            "idempotency",
            "context",
            "reconciliation",
            "failure_injection",
        } <= kinds
    assert "operational Varanegar" in payload["execution_policy"]["forbidden_environment"]
    assert "NeginPakhsh_WebDev clone" in payload["execution_policy"]["forbidden_environment"]


def test_all_high_confidence_forms_have_compact_redacted_call_contracts() -> None:
    source = ALL_FORM_CALL_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in source
    payload = json.loads(ALL_FORM_CALL_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "READ_ONLY_COMPACT_PE_METADATA_AND_IL_FROM_RUNTIME_SHARE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "config_or_resource_payloads_read": 0,
        "raw_non_allowlisted_strings_persisted": 0,
        "raw_method_il_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["selected_form_count"] == 442
    assert summary["assembly_count"] == 7
    assert summary["found_form_count"] == 442
    assert summary["missing_form_count"] == 0
    assert summary["method_body_count"] == 10386
    assert summary["method_body_error_count"] == 1
    assert summary["business_method_body_error_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert summary["validation_form_count"] == 358
    assert summary["permission_form_count"] == 122
    assert summary["report_or_output_form_count"] == 112
    assert summary["transaction_signal_form_count"] == 112
    assert summary["first_party_call_count"] == 15997
    assert summary["cross_module_form_count"] == 280
    assert summary["cross_business_module_form_count_excluding_setting"] == 111
    assert len(payload["forms"]) == 442
    assert all(row["found"] and row["contract"] is not None for row in payload["forms"])
    assert "raw_il" not in payload
    assert payload["cross_business_module_family_combinations_excluding_setting"][
        "MainData+Sales"
    ] == 51
    assert payload["cross_business_module_family_combinations_excluding_setting"][
        "MainData+Stock"
    ] == 33


def test_form_gap_catalog_preserves_uncertainty_and_prioritizes_real_gaps() -> None:
    source = FORM_GAP_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(FORM_GAP_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_REDACTED_RUNTIME_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "business_rows_or_values_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["form_candidate_count"] == 445
    assert summary["high_confidence_form_count"] == 442
    assert summary["medium_confidence_candidate_count"] == 3
    assert summary["unmapped_primary_domain_count"] == 66
    assert summary["high_confidence_unmapped_primary_domain_count"] == 63
    assert summary["high_confidence_without_direct_first_party_call_count"] == 22
    assert summary["form_with_any_direct_route_count"] == 157
    assert summary["form_with_visible_direct_route_count"] == 153
    assert summary["unrouted_likely_child_surface_count"] == 179
    assert summary["unrouted_non_child_shape_review_count"] == 109
    assert summary["write_like_without_local_permission_method_count"] == 277
    assert summary["priority_counts"] == {"high": 7, "low": 298, "medium": 140}
    assert summary["surface_classification_counts"] == {
        "business_or_unclassified_surface": 424,
        "framework_or_system_shell": 15,
        "integration_or_compliance_surface": 6,
    }
    high = {row["type"] for row in payload["forms"] if row["priority"] == "high"}
    assert "TreasuryOld.Forms.frmBankReconciliation" in high
    assert "TreasuryOld.Forms.frmReconciliation" in high
    assert "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict" in high
    assert "VN.SDS.Container.MainForm" not in high
    assert "VN.SDS.MainData.UI.Dashboard.PublicDashboard.MainUiDashboard.FormZoomChart" not in high


def test_priority_form_gaps_use_read_only_routes_and_constructor_only_launchers() -> None:
    sql_source = PRIORITY_GAP_ROUTE_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in sql_source
    assert "SELECT f.FormInfoId" in sql_source
    for forbidden in ("INSERT INTO", "UPDATE dbo", "DELETE FROM", "EXEC "):
        assert forbidden not in sql_source.upper()
    routes = json.loads(PRIORITY_GAP_ROUTE_ARTIFACT.read_text(encoding="utf-8"))
    assert routes["safety"]["database_updateability"] == "READ_ONLY"
    assert routes["safety"]["can_update"] == 0
    assert routes["safety"]["denies_data_writes"] == 1
    assert routes["summary"] == {
        "target_class_count": 7,
        "matched_static_row_count": 0,
        "matched_distinct_class_count": 0,
        "row_with_menu_route_count": 0,
        "row_with_container_visible_route_count": 0,
        "row_with_access_node_count": 0,
    }

    il_source = PRIORITY_GAP_CALL_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in il_source
    payload = json.loads(PRIORITY_GAP_CALL_ARTIFACT.read_text(encoding="utf-8"))
    summary = payload["summary"]
    assert summary == {
        "priority_gap_count": 7,
        "parent_form_count": 10,
        "precise_type_reference_edge_count": 50,
        "constructor_launcher_edge_count": 20,
        "resolved_as_child_or_nested_surface_count": 4,
        "root_entrypoint_unresolved_count": 3,
        "static_forminfo_or_menu_match_count": 0,
        "treasury_data_layer_type_count": 18,
        "treasury_data_layer_type_found_count": 18,
        "treasury_data_layer_namespace_assembly_mismatch_count": 1,
        "method_body_error_count": 0,
        "source_hash_mismatch_count": 0,
    }
    launchers = payload["constructor_launcher_edges"]
    assert all(row["called_member"] == "ctor" for row in launchers)
    assert all(row["parent_form"] != row["target_form"] for row in launchers)
    assert {row["type"] for row in payload["resolutions"] if row["status"] == "ROOT_ENTRYPOINT_STILL_UNRESOLVED"} == {
        "TreasuryOld.Forms.frmBankReconciliationList",
        "TreasuryOld.Forms.frmReconciliationSetup",
        "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict",
    }
    mismatches = [
        row for row in payload["treasury_data_layer_contracts"]
        if row["namespace_assembly_mismatch"]
    ]
    assert [(row["type"], row["definition_assembly"]) for row in mismatches] == [
        ("TreasuryOld.DataLayer.PdtReport", "TreasuryOld.Forms.dll")
    ]


def test_unresolved_roots_are_scanned_across_complete_runtime_without_execution() -> None:
    source = ROOT_ENTRYPOINT_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in source
    assert "resource_payloads_read" in source
    payload = json.loads(ROOT_ENTRYPOINT_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["safety"] == {
        "mode": "READ_ONLY_ALL_SELECTED_ASSEMBLY_METADATA_AND_IL",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "resource_payloads_read": 0,
        "config_files_read": 0,
        "raw_non_target_string_literals_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["target_root_count"] == 3
    assert summary["assembly_count"] == 62
    assert summary["core_metadata_baseline_assembly_count"] == 29
    assert summary["type_count"] == 7650
    assert summary["method_body_count"] == 81473
    assert summary["source_hash_mismatch_count"] == 0
    assert summary["target_token_reference_count"] == 191
    assert summary["self_target_token_reference_count"] == 191
    assert summary["external_target_token_reference_count"] == 0
    assert summary["external_constructor_entrypoint_count"] == 0
    assert summary["exact_target_string_reference_count"] == 0
    assert summary["embedded_target_string_reference_count"] == 0
    assert summary["resolved_root_count"] == 0
    assert summary["still_unresolved_root_count"] == 3
    assert summary["known_nonbusiness_method_body_error_count"] == 2
    assert summary["unexpected_method_body_error_count"] == 0
    assert all(
        row["status"] == "ENTRYPOINT_STILL_UNRESOLVED_AFTER_ALL_ASSEMBLY_IL_SCAN"
        for row in payload["resolutions"]
    )


def test_unresolved_roots_have_no_external_exact_reference_in_complete_deployment() -> None:
    source = DEPLOYMENT_ROOT_REFERENCE_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in source
    assert "subprocess" not in source
    assert "_connect(" not in source
    payload = json.loads(DEPLOYMENT_ROOT_REFERENCE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_DEPLOYMENT_ALLOWLISTED_EXACT_BYTE_SIGNATURE_SCAN",
        "files_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "raw_file_payloads_or_surrounding_strings_persisted": 0,
        "credentials_or_connection_string_values_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["target_root_count"] == 3
    assert summary["selected_file_count"] == 853
    assert summary["selected_file_read_count"] == 853
    assert summary["selected_file_read_error_count"] == 0
    assert summary["bytes_scanned"] == 598558431
    assert summary["external_occurrence_count"] == 0
    assert summary["target_with_external_occurrence_count"] == 0
    assert summary["validation_error_count"] == 0
    assert all(
        row["deployment_reference_status"] == "NO_EXTERNAL_DEPLOYMENT_REFERENCE_OBSERVED"
        for row in payload["target_resolutions"]
    )
    observed_files = {
        (row["relative_path"], row["classification"])
        for row in payload["allowlisted_occurrences"]
    }
    assert observed_files == {
        ("TreasuryOld.Forms.dll", "TARGET_DEFINING_ASSEMBLY"),
        ("TreasuryOld.Forms.dll.disable", "DISABLED_COPY_OF_TARGET_ASSEMBLY"),
        ("VN.SDS.MainData.UI.dll", "TARGET_DEFINING_ASSEMBLY"),
        ("VN.SDS.MainData.UI.dll.disable", "DISABLED_COPY_OF_TARGET_ASSEMBLY"),
    }


def test_unresolved_root_closure_contract_stops_repeated_scans_without_inferring_deletion() -> None:
    source = UNRESOLVED_ROOT_CLOSURE_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(UNRESOLVED_ROOT_CLOSURE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["status"] == "STATIC_SCAN_EXHAUSTED_RUNTIME_OR_OWNER_EVIDENCE_REQUIRED"
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVED_FROM_VALIDATED_READ_ONLY_ARTIFACTS",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "application_or_business_commands_executed": 0,
        "identity_or_business_values_used": 0,
        "source_or_target_changes": 0,
    }
    assert payload["summary"] == {
        "root_count": 3,
        "real_logic_unresolved_launcher_count": 1,
        "template_or_preview_candidate_count": 1,
        "placeholder_or_dynamic_candidate_count": 1,
        "resolved_by_static_evidence_count": 0,
        "automatic_scope_exclusion_count": 0,
        "runtime_or_owner_evidence_required_count": 3,
        "additional_identical_static_scan_recommended_count": 0,
        "validation_error_count": 0,
    }
    roots = {row["root_type"]: row for row in payload["root_contracts"]}
    setup = roots["TreasuryOld.Forms.frmReconciliationSetup"]
    assert setup["classification"] == "REAL_BANK_STATEMENT_IMPORT_AND_SESSION_SETUP_LOGIC_WITH_UNRESOLVED_LAUNCHER"
    assert setup["provisional_target_disposition"] == "KEEP_IMPORT_WORKFLOW_IN_SCOPE_BUT_ROUTE_MAPPING_PROVISIONAL"
    misleading = roots["TreasuryOld.Forms.frmBankReconciliationList"]
    assert misleading["provisional_target_disposition"] == "DO_NOT_CREATE_RECONCILIATION_QUEUE_ROUTE"
    special = roots[
        "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict"
    ]
    assert special["provisional_target_disposition"] == "NO_TARGET_SCHEMA_COMMAND_OR_ROUTE_INFERENCE"
    assert all(row["automatic_deletion_or_scope_exclusion_authorized"] is False for row in roots.values())
    assert all(row["additional_identical_static_scan_recommended"] is False for row in roots.values())
    telemetry = payload["runtime_telemetry_contract"]
    assert telemetry["minimum_sessions"] == 3
    assert telemetry["source_write_or_command_execution_required"] is False
    assert "user_identity_or_group_membership" in telemetry["forbidden_fields"]
    assert "business_row_or_field_value" in telemetry["forbidden_fields"]
    decision = payload["decision_policy"]
    assert decision["absence_of_static_reference_proves_unused"] is False
    assert decision["empty_or_template_shape_authorizes_deletion"] is False
    assert decision["scope_exclusion_requires_named_owner_signoff"] is True


def test_p0_backlog_is_dependency_valid_evidence_backed_and_non_executing() -> None:
    source = P0_BACKLOG_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(P0_BACKLOG_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_TARGET_BACKLOG_DESIGN_FROM_REDACTED_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "files_outside_output_changed": 0,
        "source_or_target_commands_executed": 0,
        "environments_accounts_or_roles_created": 0,
        "production_write_pilot_or_cutover_authorized": 0,
    }
    assert payload["summary"] == {
        "item_count": 26,
        "workstream_count": 13,
        "ready_for_refinement_count": 21,
        "needs_user_decision_count": 2,
        "needs_business_owner_evidence_count": 1,
        "blocked_by_dependency_count": 2,
        "dependency_edge_count": 51,
        "validation_error_count": 0,
    }
    assert payload["evidence"]["target_module_count"] == 14
    assert payload["evidence"]["migration_slice_count"] == 12
    assert payload["evidence"]["atomic_capability_count"] == 45
    assert payload["evidence"]["synthetic_golden_case_count"] == 877
    assert payload["evidence"]["material_extension_golden_case_count"] == 215
    assert payload["evidence"]["report_query_export_print_golden_case_count"] == 175
    assert payload["evidence"]["customer_goods_master_data_golden_case_count"] == 64
    assert payload["evidence"]["supplier_context_pricing_golden_case_count"] == 192
    assert payload["evidence"]["unresolved_root_entrypoint_count"] == 3
    items = {row["id"]: row for row in payload["items"]}
    assert set(items) == {f"P0-{number:03d}" for number in range(1, 27)}
    assert items["P0-001"]["status"] == "NEEDS_USER_DECISION"
    assert items["P0-025"]["status"] == "NEEDS_BUSINESS_OWNER_EVIDENCE"
    assert items["P0-026"]["status"] == "BLOCKED_BY_DEPENDENCIES"
    assert all(
        dependency in items
        for row in items.values()
        for dependency in row["depends_on"]
    )
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "direct operational Varanegar write" in serialized
    assert "technology_stack\": \"not_selected_by_user" in serialized


def test_module_readiness_matrix_preserves_zero_runtime_readiness_and_open_gaps() -> None:
    source = MODULE_READINESS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(MODULE_READINESS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_MODULE_READINESS_DERIVATION_FROM_AGGREGATE_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_identity_grants_persisted": 0,
        "implementation_pilot_or_cutover_authorized": 0,
    }
    summary = payload["summary"]
    assert summary["module_count"] == 14
    assert summary["module_with_substantial_multi_source_evidence_count"] == 9
    assert summary["p0_ready_for_refinement_count"] == 5
    assert summary["p1_read_only_ready_for_refinement_count"] == 2
    assert summary["later_phase_design_only_count"] == 7
    assert summary["command_ready_module_count"] == 0
    assert summary["pilot_ready_module_count"] == 0
    assert summary["production_ready_module_count"] == 0
    assert summary["mapped_validated_domain_count"] == 18
    assert summary["unique_form_candidate_count"] == 445
    assert summary["unique_form_candidate_with_primary_domain_count"] == 379
    assert summary["unmapped_form_candidate_count"] == 66
    assert summary["unique_workflow_surface_count"] == 20
    assert summary["unique_report_surface_count"] == 20
    assert summary["mapped_synthetic_golden_case_count"] == 970
    traceability = json.loads(REQUIREMENTS_TRACEABILITY_ARTIFACT.read_text(encoding="utf-8"))
    bank_reconciliation = json.loads(
        BANK_RECONCILIATION_GOLDEN_CASES_ARTIFACT.read_text(encoding="utf-8")
    )
    assert (
        traceability["summary"]["mapped_golden_case_count"]
        + bank_reconciliation["summary"]["case_count"]
        == summary["mapped_synthetic_golden_case_count"]
    )
    assert summary["high_priority_form_gap_count"] == 7
    assert summary["unresolved_root_entrypoint_count"] == 3
    modules = {row["module"]: row for row in payload["modules"]}
    assert len(modules) == 14
    assert all(not row["command_ready"] for row in modules.values())
    assert modules["sales"]["evidence_counts"]["synthetic_golden_case_count"] == 97
    assert modules["inventory"]["evidence_counts"]["synthetic_golden_case_count"] == 79
    assert modules["receivables_treasury"]["evidence_counts"]["unresolved_root_entrypoint_count"] == 2
    assert modules["receivables_treasury"]["evidence_counts"]["synthetic_golden_case_count"] == 162
    assert modules["receivables_treasury"]["evidence_counts"]["target_command_with_golden_cases_count"] == 12
    assert modules["configuration"]["evidence_counts"]["unresolved_root_entrypoint_count"] == 1
    assert modules["reporting_documents"]["evidence_counts"]["report_surface_count"] == 20
    assert modules["reporting_documents"]["evidence_counts"]["synthetic_golden_case_count"] == 175
    assert modules["master_data"]["evidence_counts"]["synthetic_golden_case_count"] == 114
    assert modules["organization_context"]["evidence_counts"]["synthetic_golden_case_count"] == 64
    assert modules["pricing_rules"]["evidence_counts"]["synthetic_golden_case_count"] == 82
    assert modules["platform"]["evidence_counts"]["synthetic_golden_case_count"] == 0
    assert modules["configuration"]["evidence_counts"]["synthetic_golden_case_count"] == 36


def test_risk_register_covers_every_module_and_requires_evidence_to_close() -> None:
    source = RISK_REGISTER_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(RISK_REGISTER_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_RISK_DERIVATION_FROM_AGGREGATE_AND_REDACTED_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_identity_grants_persisted": 0,
        "risk_acceptance_or_production_authorization_granted": 0,
    }
    assert payload["summary"] == {
        "risk_count": 56,
        "critical_count": 31,
        "high_count": 22,
        "medium_count": 3,
        "open_count": 56,
        "covered_module_count": 14,
        "risk_with_exit_criteria_count": 56,
        "validation_error_count": 0,
    }
    risks = {row["id"]: row for row in payload["risks"]}
    assert set(risks) == {f"R-{number:03d}" for number in range(1, 57)}
    assert all(row["status"] == "OPEN" for row in risks.values())
    assert all(row["controls"] and row["exit_criteria"] for row in risks.values())
    assert risks["R-001"]["severity"] == "CRITICAL"
    assert "integration_migration" in risks["R-001"]["modules"]
    assert risks["R-012"]["severity"] == "CRITICAL"
    assert risks["R-012"]["evidence_strength"] == "CONFIRMED_READ_ONLY_CLONE_RECONCILIATION_AND_STATIC_SQL_EVIDENCE"
    assert risks["R-013"]["severity"] == "CRITICAL"
    assert risks["R-013"]["evidence_strength"] == "CONFIRMED_READ_ONLY_CLONE_SQL_IL_AND_AGGREGATE_EVIDENCE"
    assert "AmountNut" in risks["R-013"]["failure_mode"]
    assert risks["R-014"]["severity"] == "CRITICAL"
    assert risks["R-014"]["evidence_strength"] == (
        "CONFIRMED_READ_ONLY_CLONE_SQL_IL_AND_AGGREGATE_EVIDENCE"
    )
    assert "cheque owner" in risks["R-014"]["failure_mode"]
    assert risks["R-015"]["severity"] == "HIGH"
    assert risks["R-015"]["evidence_strength"] == (
        "CONFIRMED_READ_ONLY_CLONE_AND_DEPLOYED_SQL_WITH_HISTORICAL_REASON_UNPROVEN"
    )
    assert "SOURCE_USED_UNLINKED" in " ".join(risks["R-015"]["controls"])
    assert risks["R-016"]["evidence_strength"] == "STATIC_ABSENCE_ONLY_NOT_PROOF"
    assert risks["R-025"]["severity"] == "CRITICAL"
    assert risks["R-027"]["severity"] == "CRITICAL"
    assert risks["R-028"]["severity"] == "HIGH"
    assert risks["R-029"]["severity"] == "HIGH"
    assert risks["R-030"]["evidence_strength"] == "CONFIRMED_CLONE_LIMIT_NOT_OPERATIONAL_USAGE"
    assert risks["R-031"]["evidence_strength"] == "CONFIRMED_STATIC_EVIDENCE_LIMIT"
    assert risks["R-031"]["severity"] == "HIGH"
    assert risks["R-032"]["severity"] == "CRITICAL"
    assert risks["R-032"]["evidence_strength"] == "CONFIRMED_STATIC_UI_AND_CLONE_CATALOG_EVIDENCE"
    assert risks["R-033"]["severity"] == "CRITICAL"
    assert risks["R-033"]["evidence_strength"] == "CONFIRMED_STATIC_UI_IL_AND_CLONE_CATALOG_EVIDENCE"
    assert risks["R-034"]["severity"] == "CRITICAL"
    assert risks["R-034"]["evidence_strength"] == "CONFIRMED_STATIC_UI_IL_AND_CLONE_CATALOG_EVIDENCE"
    assert risks["R-035"]["severity"] == "CRITICAL"
    assert risks["R-035"]["evidence_strength"] == "CONFIRMED_STATIC_UI_IL_AND_CLONE_CATALOG_EVIDENCE"
    assert risks["R-036"]["severity"] == "CRITICAL"
    assert risks["R-036"]["evidence_strength"] == "CONFIRMED_STATIC_UI_CALLS_WITH_NAME_ONLY_CLONE_SQL_CANDIDATES"
    assert risks["R-037"]["severity"] == "HIGH"
    assert risks["R-037"]["evidence_strength"] == "CONFIRMED_STATIC_UI_IL_WITH_DESIGNED_UNEXECUTED_GOLDEN_AND_LABEL_GAPS"
    assert risks["R-038"]["severity"] == "HIGH"
    assert risks["R-038"]["evidence_strength"] == "CONFIRMED_STATIC_UI_IL_WITH_DESIGNED_UNEXECUTED_GOLDEN_CASES"
    assert risks["R-039"]["severity"] == "HIGH"
    assert risks["R-039"]["evidence_strength"] == "CONFIRMED_STATIC_UI_IL_AND_DOMAIN_EVIDENCE_WITH_DESIGNED_UNEXECUTED_GOLDEN_CASES"
    assert risks["R-040"]["severity"] == "HIGH"
    assert risks["R-040"]["evidence_strength"] == "CONFIRMED_STATIC_UI_IL_AND_DOMAIN_EVIDENCE_WITH_DESIGNED_UNEXECUTED_GOLDEN_CASES"
    assert risks["R-041"]["severity"] == "CRITICAL"
    assert risks["R-041"]["evidence_strength"] == "CONFIRMED_LAYERED_STATIC_COMMAND_PATH_AND_READ_ONLY_CLONE_DIAGNOSTIC_WITH_UNPROVEN_TARGET_RUNTIME_PARITY"
    assert risks["R-042"]["severity"] == "CRITICAL"
    assert risks["R-042"]["evidence_strength"] == (
        "CONFIRMED_READ_ONLY_CLONE_AND_DEPLOYED_SQL_PATH_WITH_RUNTIME_FREQUENCY_UNPROVEN"
    )
    assert "TblCheque.PayId" in risks["R-042"]["failure_mode"]
    assert risks["R-043"]["severity"] == "CRITICAL"
    assert risks["R-043"]["evidence_strength"] == (
        "CONFIRMED_READ_ONLY_CLONE_AND_DEPLOYED_SQL_WITH_HISTORICAL_CAUSATION_UNPROVEN"
    )
    assert "MAX(history)" in risks["R-043"]["failure_mode"]
    assert risks["R-044"]["severity"] == "HIGH"
    assert risks["R-044"]["evidence_strength"] == (
        "CONFIRMED_READ_ONLY_CLONE_AND_DEPLOYED_SQL_WITH_HISTORICAL_CAUSATION_UNPROVEN"
    )
    assert "synthesizes balancing lines" in risks["R-044"]["failure_mode"]
    assert risks["R-045"]["severity"] == "CRITICAL"
    assert "TourHistory" in " ".join(risks["R-045"]["controls"])
    assert risks["R-046"]["severity"] == "CRITICAL"
    assert risks["R-046"]["evidence_strength"] == (
        "CONFIRMED_READ_ONLY_CLONE_AGGREGATES_DEPLOYED_SQL_AND_STATIC_DESKTOP_IL_WITH_NO_MUTATION_EXECUTED"
    )
    assert "inner-joins" in risks["R-046"]["failure_mode"]
    assert risks["R-047"]["severity"] == "CRITICAL"
    assert risks["R-047"]["evidence_strength"] == (
        "CONFIRMED_HASH_PINNED_DESKTOP_IL_READ_ONLY_SQL_AND_FULL_CLONE_AGGREGATES_WITH_NO_MUTATION_EXECUTED"
    )
    assert "FiscalYear.ExternalVoucherIssueMode" in risks["R-047"]["failure_mode"]
    assert risks["R-048"]["severity"] == "HIGH"
    assert risks["R-048"]["evidence_strength"] == (
        "CONFIRMED_HASH_PINNED_DESKTOP_IL_AND_STATIC_SQL_WITH_CLEAN_READ_ONLY_SNAPSHOT"
    )
    assert "SetVoucherNo" in risks["R-048"]["failure_mode"]
    assert risks["R-049"]["severity"] == "CRITICAL"
    assert risks["R-049"]["evidence_strength"] == (
        "CONFIRMED_HASH_PINNED_UI_BASE_TEMPLATE_AND_BUSINESS_IL_PLUS_STATIC_SQL_ABSENCE_WITH_SCREEN_ACCESS_CAVEAT"
    )
    assert "distinct action authorization" in risks["R-049"]["failure_mode"]
    assert risks["R-050"]["severity"] == "CRITICAL"
    assert risks["R-050"]["evidence_strength"] == (
        "CONFIRMED_DEPLOYED_SQL_AND_READ_ONLY_COVERAGE_WITH_NO_MODERN_PURCHASE_RUNTIME_EXAMPLE"
    )
    assert "MIN(DefeniteDate)" in risks["R-050"]["failure_mode"]
    assert risks["R-051"]["severity"] == "HIGH"
    assert risks["R-051"]["evidence_strength"] == (
        "CONFIRMED_DEPLOYED_VALIDATOR_SQL_AND_READ_ONLY_CATALOG_WITH_PREDICATE_RUNTIME_UNEXECUTED"
    )
    assert "45 of 65" in risks["R-051"]["failure_mode"]
    assert risks["R-052"]["severity"] == "CRITICAL"
    assert risks["R-052"]["evidence_strength"] == (
        "CONFIRMED_HASH_PINNED_PROVIDER_IL_DEPLOYED_SQL_AND_READ_ONLY_DEPENDENCY_GRAPH_WITH_NO_RUNTIME_DIRTY_READ_INCIDENT_TEST"
    )
    assert "WITH(NOLOCK)" in risks["R-052"]["failure_mode"]
    assert risks["R-053"]["severity"] == "CRITICAL"
    assert risks["R-053"]["evidence_strength"] == (
        "CONFIRMED_DEPLOYED_DYNAMIC_SQL_DESIGN_WITH_CURRENT_SNAPSHOT_TOKEN_SCAN_CLEAN"
    )
    assert "zero obvious" in risks["R-053"]["failure_mode"]
    assert risks["R-054"]["severity"] == "CRITICAL"
    assert risks["R-054"]["evidence_strength"] == (
        "CONFIRMED_STATIC_SQL_AND_FULL_HASH_PINNED_PACKAGE_ABSENCE_WITH_ADMIN_AUTHORITY_AND_RUNTIME_FREQUENCY_UNPROVEN"
    )
    assert "four dynamic execution sites" in risks["R-054"]["failure_mode"]
    assert "VoucherCreatorId and ArticleCaption" in risks["R-054"]["failure_mode"]
    assert risks["R-055"]["severity"] == "HIGH"
    assert risks["R-055"]["evidence_strength"] == (
        "CONFIRMED_HASH_PINNED_REPLICATION_IL_STATIC_SQL_AND_READ_ONLY_CLONE_AGGREGATES_WITH_PRODUCTION_DELIVERY_UNPROVEN"
    )
    assert "durable binary outbox" in risks["R-055"]["failure_mode"]
    assert "content checksum" in risks["R-055"]["failure_mode"]
    assert risks["R-056"]["severity"] == "CRITICAL"
    assert risks["R-056"]["evidence_strength"] == (
        "CONFIRMED_HASH_PINNED_REPLICATION_AND_FLUENTFTP_IL_WITH_ACTIVE_PRODUCTION_TRANSPORT_MODE_UNPROVEN"
    )
    assert "EncryptionMode" in risks["R-056"]["failure_mode"]
    assert "active production mode" in risks["R-056"]["failure_mode"]
    assert payload["source_checkpoint"]["voucher_creation_active_creator_count"] == 11
    assert payload["source_checkpoint"]["voucher_creation_desktop_outer_transaction_proven"] is True
    assert payload["source_checkpoint"]["voucher_creation_server_owned_transaction"] is False
    assert payload["source_checkpoint"]["voucher_creation_current_policy_fully_explains_history"] is False
    assert payload["source_checkpoint"]["voucher_creation_1405_multi_source_header_count"] == 366
    assert payload["source_checkpoint"]["voucher_creator_configured_rule_count"] == 149
    assert payload["source_checkpoint"]["voucher_creator_historically_observed_rule_count"] == 101
    assert payload["source_checkpoint"]["voucher_creator_historically_unobserved_rule_count"] == 48
    assert payload["source_checkpoint"]["voucher_historical_staging_line_count"] == 2370569
    assert payload["source_checkpoint"]["voucher_historical_actual_external_line_count"] == 1287874
    assert payload["source_checkpoint"]["voucher_historical_current_grain_expected_line_count"] == 1424039
    assert payload["source_checkpoint"]["voucher_historical_legacy_equivalent_expected_line_count"] == 1287874
    assert payload["source_checkpoint"]["voucher_historical_collapsed_staging_line_count"] == 1082695
    assert payload["source_checkpoint"]["voucher_historical_all_creators_match_current_grain"] is False
    assert payload["source_checkpoint"]["voucher_lifecycle_all_outer_transactions_proven"] is True
    assert payload["source_checkpoint"]["voucher_transfer_deletes_number_crosswalk_before_validation"] is True
    assert payload["source_checkpoint"]["voucher_transfer_validation_can_return_without_exception"] is True
    assert payload["source_checkpoint"]["voucher_lifecycle_full_header_count"] == 197518
    assert payload["source_checkpoint"]["voucher_lifecycle_full_multiple_active_voucher_count"] == 0
    assert payload["source_checkpoint"]["voucher_lifecycle_full_number_crosswalk_orphan_count"] == 0
    assert payload["source_checkpoint"]["voucher_read_grid_session_accyear_dc_scoped"] is True
    assert payload["source_checkpoint"]["voucher_form_command_method_permission_call_count"] == 0
    assert payload["source_checkpoint"]["voucher_action_procedure_authorization_count"] == 0
    assert payload["source_checkpoint"]["voucher_issue_operation_finality_enforced"] is True
    assert payload["source_checkpoint"]["voucher_issue_finality_failure_is_pre_mutation"] is True
    assert payload["source_checkpoint"]["voucher_purchase_finality_requires_every_stockdc_row"] is False
    assert payload["source_checkpoint"]["voucher_purchase_partially_covered_active_dc_year_scope_count"] == 3
    assert payload["source_checkpoint"]["voucher_purchase_missing_stockdc_operation_row_count"] == 10
    assert payload["source_checkpoint"]["voucher_operation_id_5_configured_type_count"] == 2
    assert payload["source_checkpoint"]["voucher_operation_id_5_retained_header_count"] == 0
    assert payload["source_checkpoint"]["voucher_modern_header_current_finality_failure_count"] == 0
    assert payload["source_checkpoint"]["voucher_issue_policy_preflight_before_transaction"] is True
    assert payload["source_checkpoint"]["voucher_issue_policy_values_are_procedure_parameters"] is False
    assert payload["source_checkpoint"]["voucher_issue_validation_failure_stops_confirmation"] is True
    assert payload["source_checkpoint"]["voucher_confirm_validation_failure_stops_transfer"] is True
    assert payload["source_checkpoint"]["voucher_success_ids_only_from_message_type_zero"] is True
    assert payload["source_checkpoint"]["voucher_configured_type_count"] == 65
    assert payload["source_checkpoint"]["voucher_structurally_candidate_type_count"] == 45
    assert payload["source_checkpoint"]["voucher_structurally_invalid_type_count"] == 20
    assert payload["source_checkpoint"]["voucher_invalid_type_with_retained_history_count"] == 0
    assert payload["source_checkpoint"]["voucher_uncompiled_predicate_count"] == 71
    assert payload["source_checkpoint"]["voucher_creator_view_queries_executed_for_validation"] == 0
    assert payload["source_checkpoint"]["voucher_creator_view_nolock_read_count"] == 1
    assert payload["source_checkpoint"]["voucher_dynamic_sql_execution_site_count"] == 2
    assert payload["source_checkpoint"]["voucher_dynamic_sql_sites_executed_by_extractor"] == 0
    assert payload["source_checkpoint"]["voucher_current_suspicious_fragment_count"] == 0
    assert payload["source_checkpoint"]["voucher_distinct_dynamic_predicate_count"] == 71
    assert payload["source_checkpoint"]["voucher_provider_explicit_isolation_level"] is False
    assert payload["source_checkpoint"]["voucher_clone_read_committed_snapshot_enabled"] is True
    assert payload["source_checkpoint"]["voucher_clone_snapshot_isolation_state"] == "ON"
    assert payload["source_checkpoint"]["voucher_recent_source_base_table_count"] == 54
    assert payload["source_checkpoint"]["voucher_recent_source_rowversion_table_count"] == 6
    assert payload["source_checkpoint"]["voucher_recent_source_temporal_table_count"] == 0
    assert payload["source_checkpoint"]["voucher_recent_source_change_tracked_table_count"] == 0
    assert payload["source_checkpoint"]["voucher_rule_target_form_type_count"] == 0
    assert payload["source_checkpoint"]["voucher_rule_named_save_is_validation_failure"] is True
    assert payload["source_checkpoint"]["voucher_rule_template_transfer_procedure_count"] == 2
    assert payload["source_checkpoint"]["voucher_rule_template_transfer_transaction_count"] == 0
    assert payload["source_checkpoint"]["voucher_rule_template_transfer_try_catch_count"] == 0
    assert payload["source_checkpoint"]["voucher_rule_template_transfer_authorization_count"] == 0
    assert payload["source_checkpoint"]["voucher_rule_template_transfer_version_audit_count"] == 0
    assert payload["source_checkpoint"]["voucher_rule_template_transfer_analyzer_execute_count"] == 0
    assert payload["source_checkpoint"]["voucher_rule_enabled_replication_trigger_count"] == 6
    assert payload["source_checkpoint"]["rule_replication_hash_pinned_binary_count"] == 4
    assert payload["source_checkpoint"]["rule_replication_outbound_binary_outbox_proven"] is True
    assert payload["source_checkpoint"]["rule_replication_receive_transaction_proven"] is True
    assert payload["source_checkpoint"]["rule_replication_clone_downstream_success_proven"] is False
    assert payload["source_checkpoint"]["rule_replication_ftp_explicit_transport_encryption_proven"] is False
    assert payload["source_checkpoint"]["rule_replication_package_content_authentication_proven"] is False
    assert payload["source_checkpoint"]["supplier_return_three_month_new_path_header_count"] == 50
    assert payload["source_checkpoint"]["supplier_return_three_month_legacy_path_header_count"] == 0
    assert payload["source_checkpoint"][
        "supplier_return_three_month_optional_source_item_absent_goods_group_count"
    ] == 5
    assert payload["source_checkpoint"]["supplier_return_three_month_stale_explicit_toll_ref_row_count"] == 0
    assert payload["source_checkpoint"]["supplier_invoice_item_duplicate_header_goods_group_count"] == 0
    assert payload["source_checkpoint"]["supplier_invoice_item_unique_header_goods_index_count"] == 1
    assert all("source acknowledgement" not in control for control in risks["R-027"]["controls"])
    assert payload["source_checkpoint"]["known_anomaly_class_count"] == 14
    assert payload["source_checkpoint"]["stock_cardex_only_gap_count"] == 1594
    assert payload["source_checkpoint"]["stock_official_formula_residual_count"] == 0
    assert payload["source_checkpoint"][
        "returned_cheque_cross_customer_previous_anomaly_interpretation_valid"
    ] is False
    assert payload["source_checkpoint"][
        "returned_cheque_cross_customer_exact_allocation_match_count"
    ] == 49
    assert payload["source_checkpoint"][
        "returned_cheque_cross_customer_unexplained_row_count"
    ] == 0
    assert payload["source_checkpoint"][
        "returned_cheque_cross_customer_over_settled_pair_count"
    ] == 0
    assert payload["source_checkpoint"]["received_cheque_master_pay_projection_gap_count"] == 8
    assert payload["source_checkpoint"][
        "received_cheque_master_pay_projection_gap_with_valid_approved_history_count"
    ] == 8
    assert payload["source_checkpoint"]["received_cheque_unspecified_legal_type_count"] == 35
    assert payload["source_checkpoint"]["received_cheque_bulk_confirmation_forwards_legal_type"] is False
    assert payload["source_checkpoint"]["payable_source_used_unlinked_leaf_count"] == 155
    assert payload["source_checkpoint"][
        "payable_source_used_unlinked_previous_orphan_interpretation_valid"
    ] is False
    assert payload["source_checkpoint"][
        "payable_source_used_unlinked_historical_reason_recoverable"
    ] is False
    assert payload["source_checkpoint"]["voucher_current_pointer_history_fork_count"] == 1094
    assert payload["source_checkpoint"]["voucher_detached_trailing_event_count"] == 14946
    assert payload["source_checkpoint"][
        "voucher_status_change_failure_has_explicit_rollback"
    ] is False
    assert payload["source_checkpoint"]["empty_numbered_draft_voucher_shell_count"] == 1
    assert payload["source_checkpoint"]["empty_numbered_draft_voucher_ledger_debit_effect"] == "0"
    assert payload["source_checkpoint"]["empty_numbered_draft_voucher_safe_to_synthesize_lines"] is False
    assert payload["source_checkpoint"]["ngt_mobile_return_without_current_official_return_count"] == 2
    assert payload["source_checkpoint"]["ngt_mobile_return_historical_result_missing_target_count"] == 1
    assert payload["source_checkpoint"]["ngt_mobile_return_without_historical_result_count"] == 1
    assert payload["source_checkpoint"]["supplier_return_sourced_goods_group_count"] == 115
    assert payload["source_checkpoint"]["supplier_return_unmatched_source_goods_group_count"] == 7
    assert payload["source_checkpoint"]["supplier_return_matched_over_return_goods_group_count"] == 0
    assert payload["source_checkpoint"]["supplier_return_validator_update_path_call"] is False
    assert payload["source_checkpoint"]["supplier_return_validator_insert_captures_return_code"] is False
    assert payload["source_checkpoint"]["supplier_return_validator_has_unmatched_goods_check"] is False
    assert payload["source_checkpoint"]["supplier_return_desktop_validator_before_commit"] is True
    assert payload["source_checkpoint"]["supplier_return_desktop_nonempty_message_blocks_commit"] is True
    assert payload["source_checkpoint"]["supplier_return_stale_explicit_toll_ref_count"] == 20
    assert payload["source_checkpoint"]["supplier_return_stale_toll_ref_affected_new_path_header_count"] == 0
    assert payload["source_checkpoint"]["supplier_return_stale_toll_ref_unique_compatibility_resolution_count"] == 20
    assert payload["source_checkpoint"]["supplier_return_toll_compatibility_unresolved_count"] == 0
    assert payload["source_checkpoint"]["supplier_return_toll_compatibility_ambiguous_count"] == 0
    assert payload["source_checkpoint"]["supplier_return_optional_source_item_absent_exact_type55_exit_count"] == 7
    assert payload["source_checkpoint"]["supplier_return_optional_source_item_absent_nonzero_price_count"] == 7
    assert payload["source_checkpoint"]["supplier_return_item_grid_inventory_voucher_authority"] is True
    assert payload["source_checkpoint"]["supplier_return_rights_forwards_dc_or_accyear_scope"] is False
    assert payload["source_checkpoint"]["supplier_return_required_goods_check_is_current_aggregate_scoped"] is False
    assert payload["source_checkpoint"]["supplier_return_current_zero_or_null_goods_item_count"] == 0
    assert payload["source_checkpoint"]["final_date_incident_finding_count"] == 11
    assert payload["source_checkpoint"]["mutating_command_without_explicit_idempotency_count"] == 8
    assert payload["source_checkpoint"]["unresolved_root_count"] == 3
    assert payload["source_checkpoint"]["report_surface_count"] == 20
    assert payload["source_checkpoint"]["pos_replication_dependency_count"] == 66
    assert payload["source_checkpoint"]["pos_replication_lexical_operation_count"] == 17
    assert payload["source_checkpoint"]["pos_transitive_graph_node_count"] == 500
    assert payload["source_checkpoint"]["pos_transitive_graph_trigger_count"] == 362
    assert payload["source_checkpoint"]["pos_transitive_graph_truncated"] is True
    assert payload["source_checkpoint"]["pos_source_untrusted_fk_count"] == 61
    assert payload["source_checkpoint"]["pos_source_version_signal_table_count"] == 0
    assert payload["source_checkpoint"]["report_target_golden_case_count"] == 175
    assert payload["source_checkpoint"]["report_result_parity_proven_contract_count"] == 0
    assert payload["source_checkpoint"]["report_l3_static_evidence_count"] == 9
    assert payload["source_checkpoint"]["report_result_parity_gap_count"] == 20
    assert payload["source_checkpoint"]["generic_report_selected_sql_module_count"] == 5
    assert payload["source_checkpoint"]["generic_report_described_result_column_count"] == 0
    assert payload["source_checkpoint"]["treasury_edit_mutation_command_method_count"] == 3
    assert payload["source_checkpoint"]["treasury_edit_direct_execute_non_query_method_count"] == 3
    assert payload["source_checkpoint"]["treasury_source_writable_view_count"] == 2
    assert payload["source_checkpoint"]["treasury_source_enabled_trigger_count"] == 29
    assert payload["source_checkpoint"]["treasury_trigger_dependency_count"] == 133
    assert payload["source_checkpoint"]["treasury_trigger_lexical_operation_count"] == 20
    assert payload["source_checkpoint"]["treasury_trigger_effect_parity_proven_count"] == 0
    assert payload["source_checkpoint"]["treasury_view_visible_column_count"] == 97
    assert payload["source_checkpoint"]["treasury_view_visible_column_with_source_lineage_count"] == 89
    assert payload["source_checkpoint"]["treasury_view_runtime_effect_proven_count"] == 0
    assert payload["source_checkpoint"]["treasury_view_direct_metadata_gap_with_parsed_candidate_count"] == 8
    assert payload["source_checkpoint"]["treasury_target_command_contract_count"] == 3
    assert payload["source_checkpoint"]["treasury_unexecuted_acceptance_obligation_count"] == 51
    assert payload["source_checkpoint"]["treasury_owner_approved_contract_count"] == 0
    assert payload["source_checkpoint"]["treasury_validation_rule_signal_count"] == 14
    assert payload["source_checkpoint"]["treasury_validation_exact_branch_proven_count"] == 0
    assert payload["source_checkpoint"]["treasury_transitive_node_count"] == 376
    assert payload["source_checkpoint"]["treasury_transitive_resolved_write_target_count"] == 42
    assert payload["source_checkpoint"]["treasury_transitive_graph_truncated"] is False
    assert payload["source_checkpoint"]["treasury_transitive_effect_parity_proven_count"] == 0
    assert payload["source_checkpoint"]["treasury_web_declared_field_count"] == 68
    assert payload["source_checkpoint"]["treasury_web_field_with_source_candidate_count"] == 17
    assert payload["source_checkpoint"]["treasury_web_field_source_conflict_count"] == 1
    assert payload["source_checkpoint"]["treasury_web_runtime_binding_proven_count"] == 0
    assert payload["source_checkpoint"]["order_sale_selected_method_count"] == 18
    assert payload["source_checkpoint"]["order_sale_rule_signal_count"] == 13
    assert payload["source_checkpoint"]["order_sale_business_dependency_edge_count"] == 86
    assert payload["source_checkpoint"]["order_sale_sql_anchor_count"] == 7
    assert payload["source_checkpoint"]["order_sale_sql_durable_mutation_target_count"] == 9
    assert payload["source_checkpoint"]["order_sale_source_enabled_trigger_count"] == 73
    assert payload["source_checkpoint"]["order_sale_trigger_node_count"] == 500
    assert payload["source_checkpoint"]["order_sale_trigger_graph_truncated"] is True
    assert payload["source_checkpoint"]["order_sale_trigger_resolved_write_target_count"] == 35
    assert payload["source_checkpoint"]["order_sale_web_input_candidate_count"] == 140
    assert payload["source_checkpoint"]["order_sale_linked_synthetic_golden_case_count"] == 48
    assert payload["source_checkpoint"]["order_sale_runtime_effect_or_golden_proven_count"] == 0


def test_navigation_module_map_covers_full_tree_without_claiming_effective_rights() -> None:
    source = NAVIGATION_MODULE_MAP_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(NAVIGATION_MODULE_MAP_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_NAVIGATION_DERIVATION_FROM_REDACTED_STATIC_ROUTE_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "user_or_group_rights_read": 0,
        "business_rows_or_values_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["route_count"] == 836
    assert summary["root_section_count"] == 31
    assert summary["configured_form_route_count"] == 399
    assert summary["runtime_matched_form_count"] == 160
    assert summary["runtime_matched_form_with_primary_domain_count"] == 126
    assert summary["container_visible_config_count"] == 241
    assert summary["route_with_access_node_count"] == 399
    assert summary["action_menu_count"] == 3
    assert summary["modal_route_count"] == 17
    assert summary["maximum_hierarchy_depth"] == 4
    assert summary["orphan_parent_count"] == 0
    assert summary["cycle_menu_count"] == 0
    assert summary["validation_error_count"] == 0
    assert payload["route_runtime_coverage_classification_counts"] == {
        "CONFIGURED_LEAF_EXTERNAL_OR_ABSENT_PACKAGE_HINT": 104,
        "CONFIGURED_LEAF_NULL_OR_PLACEHOLDER_TARGET": 37,
        "CONFIGURED_LEAF_PRESENT_PACKAGE_TYPE_UNMATCHED": 34,
        "CONFIGURED_LEAF_REDACTED_TARGET_NEEDS_REVIEW": 3,
        "CONFIGURED_NAVIGATION_OR_SELECTOR_SHELL": 61,
        "NAVIGATION_ONLY_NO_FORM_CONFIG": 437,
        "RUNTIME_FORM_MATCHED": 160,
    }
    assert len(payload["root_sections"]) == 31
    assert len(payload["routes"]) == 836
    assert all("not final" in limit.casefold() or "not the effective" in limit.casefold() or "does not authorize" in limit.casefold() or "can reflect" in limit.casefold() for limit in payload["limits"])


def test_scope_freeze_catalog_prioritizes_without_auto_retiring_routes() -> None:
    source = SCOPE_FREEZE_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(SCOPE_FREEZE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_SCOPE_REVIEW_FROM_REDACTED_STATIC_NAVIGATION_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "user_or_group_rights_read": 0,
        "routes_enabled_disabled_or_changed": 0,
        "raw_redacted_target_values_recovered_or_persisted": 0,
    }
    assert payload["summary"] == {
        "candidate_count": 239,
        "shell_candidate_count": 61,
        "leaf_candidate_count": 178,
        "priority_counts": {"high": 76, "low": 58, "medium": 105},
        "container_visible_candidate_count": 85,
        "candidate_with_access_node_count": 239,
        "candidate_with_material_signal_count": 128,
        "auto_retired_count": 0,
        "validation_error_count": 0,
    }
    assert payload["classification_counts"] == {
        "CONFIGURED_LEAF_EXTERNAL_OR_ABSENT_PACKAGE_HINT": 104,
        "CONFIGURED_LEAF_NULL_OR_PLACEHOLDER_TARGET": 37,
        "CONFIGURED_LEAF_PRESENT_PACKAGE_TYPE_UNMATCHED": 34,
        "CONFIGURED_LEAF_REDACTED_TARGET_NEEDS_REVIEW": 3,
        "CONFIGURED_NAVIGATION_OR_SELECTOR_SHELL": 61,
    }
    assert len(payload["candidates"]) == 239
    assert all(
        row["scope_disposition"] == "REVIEW_REQUIRED_NEVER_AUTO_RETIRED"
        for row in payload["candidates"]
    )
    high_classes = Counter(
        row["classification"] for row in payload["candidates"] if row["priority"] == "high"
    )
    assert high_classes == {
        "CONFIGURED_LEAF_EXTERNAL_OR_ABSENT_PACKAGE_HINT": 40,
        "CONFIGURED_LEAF_PRESENT_PACKAGE_TYPE_UNMATCHED": 33,
        "CONFIGURED_LEAF_REDACTED_TARGET_NEEDS_REVIEW": 3,
    }


def test_present_package_route_types_extend_core_catalog_without_execution() -> None:
    source = PRESENT_PACKAGE_ROUTE_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in source
    payload = json.loads(PRESENT_PACKAGE_ROUTE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_COMPLETE_PACKAGE_TYPEDEF_AND_TARGETED_IL_RESOLUTION",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "config_or_resource_payloads_read": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    assert payload["summary"] == {
        "candidate_count": 34,
        "package_file_count": 62,
        "package_typedef_count": 7650,
        "resolution_status_counts": {
            "RESOLVED_UNIQUE_TYPEDEF": 33,
            "UNRESOLVED_IN_PRESENT_PACKAGE_TYPEDEFS": 1,
        },
        "distinct_matched_type_count": 32,
        "target_assembly_count": 5,
        "target_method_body_count": 607,
        "target_with_write_like_method_count": 26,
        "target_with_permission_method_count": 13,
        "target_method_body_error_count": 0,
        "source_hash_mismatch_count": 0,
        "metadata_failure_count": 0,
        "auto_implemented_or_retired_count": 0,
        "validation_error_count": 0,
    }
    resolved_assemblies = Counter(
        matched["assembly"]
        for row in payload["routes"]
        for matched in row["matched_types"]
    )
    assert resolved_assemblies == {
        "VN.SDS.POSSystem.UI.dll": 13,
        "VN.SDS.Tablet.UI.dll": 9,
        "VN.SDS.Setting.UI.dll": 8,
        "VN.SDS.Report.Interface.dll": 2,
        "VNMembers.dll": 1,
    }
    unresolved = [row for row in payload["routes"] if row["resolution_status"].startswith("UNRESOLVED")]
    assert len(unresolved) == 1
    assert unresolved[0]["menu_id"] == 20037
    assert all(
        row["scope_disposition"] == "REVIEW_REQUIRED_NEVER_AUTO_IMPLEMENTED_OR_RETIRED"
        for row in payload["routes"]
    )


def test_extension_capability_map_keeps_hints_separate_from_scope_decisions() -> None:
    source = EXTENSION_CAPABILITY_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(EXTENSION_CAPABILITY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_CAPABILITY_DERIVATION_FROM_REDACTED_TARGETED_IL_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "routes_permissions_or_configuration_changed": 0,
        "business_rows_or_identity_grants_persisted": 0,
    }
    assert payload["summary"] == {
        "capability_count": 32,
        "route_association_count": 33,
        "family_counts": {"POS": 13, "Report": 1, "Setting": 8, "Tablet": 9, "VNMembers": 1},
        "capability_with_write_like_method_count": 26,
        "capability_with_destructive_or_reversing_method_count": 13,
        "capability_with_validation_method_count": 20,
        "capability_with_local_permission_method_count": 13,
        "write_like_method_count": 103,
        "destructive_or_reversing_method_count": 18,
        "validation_method_count": 78,
        "permission_method_count": 25,
        "external_contract_call_count": 1828,
        "unresolved_route_count": 1,
        "auto_scope_decision_count": 0,
        "validation_error_count": 0,
    }
    capabilities = {row["capability_hint"]: row for row in payload["capabilities"]}
    assert len(capabilities) == 32
    assert capabilities["pos.linear_discount"]["target_module_hints_not_final_ownership"] == ["sales", "pricing_rules"]
    assert "distribution" in capabilities["tablet.visit_plan"]["target_module_hints_not_final_ownership"]
    assert capabilities["authorization.stock_accounting_access"]["evidence"]["permission_method_count"] == 12
    assert payload["unresolved_routes"][0]["menu_id"] == 20037
    assert all(row["mandatory_gates"] for row in payload["capabilities"])


def test_extension_dependency_graph_detects_direct_data_access_without_execution() -> None:
    source = EXTENSION_DEPENDENCY_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in source
    payload = json.loads(EXTENSION_DEPENDENCY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_COMPLETE_PACKAGE_METADATA_AND_TARGETED_IL_DEPENDENCY_TRACE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "config_or_resource_payloads_read": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    assert payload["summary"] == {
        "capability_count": 32,
        "first_party_ui_edge_count": 1402,
        "ui_to_business_edge_count": 149,
        "business_target_type_count": 73,
        "business_target_method_body_count": 292,
        "direct_ui_to_data_access_edge_count": 42,
        "capability_with_direct_ui_data_access_count": 13,
        "business_to_data_access_edge_count": 184,
        "data_access_target_type_count": 58,
        "data_access_target_method_body_count": 807,
        "capability_with_business_mediation_count": 31,
        "unresolved_first_party_like_call_type_count": 0,
        "targeted_method_body_error_count": 0,
        "source_hash_mismatch_count": 0,
        "metadata_failure_count": 0,
        "validation_error_count": 0,
    }
    capabilities = {row["capability_hint"]: row for row in payload["capabilities"]}
    direct = {name for name, row in capabilities.items() if row["has_direct_ui_data_access_coupling"]}
    assert len(direct) == 13
    assert "pos.charge_device" in direct
    assert "configuration.general" in direct
    assert "party.contact_selector" in direct
    assert not capabilities["party.contact_selector"]["has_business_mediation_evidence"]
    assert all(row["found"] for row in payload["business_contracts"])
    assert all(row["found"] for row in payload["data_access_contracts"])


def test_material_extension_command_paths_are_method_backed_and_non_executing() -> None:
    source = EXTENSION_COMMAND_PATH_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in source
    payload = json.loads(EXTENSION_COMMAND_PATH_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_TARGETED_METHOD_LEVEL_IL_PATH_TRACE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "config_or_resource_payloads_read": 0,
        "string_literals_persisted": 0,
    }
    assert payload["summary"] == {
        "selected_capability_count": 12,
        "selected_ui_type_count": 12,
        "selected_ui_method_body_count": 265,
        "ui_path_method_count": 216,
        "ui_command_candidate_method_count": 55,
        "ui_guard_candidate_method_count": 49,
        "ui_query_event_context_method_count": 112,
        "ui_path_business_edge_occurrence_count": 173,
        "ui_path_unique_business_edge_count": 90,
        "ui_path_direct_data_access_edge_occurrence_count": 42,
        "ui_path_unique_direct_data_access_edge_count": 26,
        "reachable_business_type_count": 42,
        "called_business_member_count": 89,
        "resolved_business_method_body_count": 89,
        "interface_or_unresolved_business_body_count": 0,
        "business_method_data_access_edge_occurrence_count": 120,
        "business_method_unique_data_access_edge_count": 105,
        "ui_transaction_signal_count": 0,
        "business_transaction_signal_count": 0,
        "targeted_method_body_error_count": 0,
        "source_hash_mismatch_count": 0,
        "validation_error_count": 0,
    }
    capabilities = {row["capability_hint"]: row for row in payload["capability_paths"]}
    assert len(capabilities) == 12
    assert capabilities["authorization.stock_accounting_access"]["path_method_count"] == 31
    assert capabilities["pos.charge_device"]["path_method_count"] == 24
    assert any(
        method["direct_data_access_edge_count"]
        for method in capabilities["pos.charge_device"]["methods"]
    )
    assert all(row["resolved_method_body_count"] == row["called_member_count"] for row in payload["business_paths"])


def test_extension_target_contracts_separate_commands_from_read_only_queries() -> None:
    source = EXTENSION_TARGET_CONTRACT_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "LoadLibrary" not in source
    payload = json.loads(EXTENSION_TARGET_CONTRACT_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_TARGET_CONTRACT_DESIGN_FROM_REDACTED_METHOD_PATH_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
        "credentials_or_secrets_read_or_persisted": 0,
    }
    assert payload["summary"] == {
        "source_capability_count": 12,
        "target_command_count": 11,
        "target_query_count": 2,
        "command_source_candidate_method_count": 55,
        "command_with_ui_command_candidate_count": 10,
        "command_with_deep_execute_non_query_evidence_count": 1,
        "command_with_direct_data_access_source_count": 5,
        "query_with_ui_command_candidate_count": 0,
        "query_with_coexisting_target_command_count": 1,
        "source_transaction_signal_count": 0,
        "deep_transaction_call_count": 7,
        "validation_error_count": 0,
    }
    commands = {row["command"]: row for row in payload["commands"]}
    queries = {row["query"]: row for row in payload["queries"]}
    assert len(commands) == 11
    assert len(queries) == 2
    assert set(queries) == {"pos.read_scoped_safes", "pos.read_scoped_sessions"}
    assert sum(bool(row["source_evidence"]["source_command_candidate_methods"]) for row in commands.values()) == 10
    assert all(not row["source_evidence"]["source_command_candidate_methods"] for row in queries.values())
    assert any(call.endswith("ExecuteNonQuery") for call in commands["pos.replicate_session_sales_receipts"]["deep_gap_evidence"]["mutation_or_transaction_calls"])
    assert "secret-reference validation" in commands["configuration.publish_web_service_version"]["failure_stages"]
    assert commands["configuration.publish_general_version"]["owner"] == "configuration"
    assert commands["configuration.publish_web_service_version"]["owner"] == "configuration"
    assert all("command_id" in row["required_envelope"] for row in commands.values())


def test_extension_golden_cases_cover_failures_and_never_target_legacy() -> None:
    source = EXTENSION_GOLDEN_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(EXTENSION_GOLDEN_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_SYNTHETIC_TARGET_TEST_DESIGN",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_or_queries_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
    }
    assert payload["summary"] == {
        "command_surface_count": 11,
        "query_surface_count": 2,
        "case_count": 215,
        "category_counts": {
            "authorization": 13,
            "concurrency": 11,
            "fault_injection": 44,
            "freshness": 2,
            "happy_path": 13,
            "idempotency": 22,
            "invariant": 46,
            "pagination": 2,
            "privacy": 2,
            "read_only": 2,
            "reconciliation": 45,
            "scope": 13,
        },
        "legacy_execution_allowed_count": 0,
        "validation_error_count": 0,
    }
    assert all(not case["legacy_execution_allowed"] for case in payload["cases"])
    query_cases = [case for case in payload["cases"] if case["surface"].startswith("pos.read_")]
    assert len(query_cases) == 14
    assert sum(case["category"] == "read_only" for case in query_cases) == 2


def test_extension_sql_surface_is_clone_catalog_only_and_redacted() -> None:
    source = EXTENSION_SQL_SURFACE_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    assert "m.definition" in source
    payload = json.loads(EXTENSION_SQL_SURFACE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["scope"]["database"] == "NeginPakhsh_WebDev"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_METADATA_ONLY",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_definitions_persisted": 0,
        "credentials_or_secrets_persisted": 0,
        "identity_grants_read_or_persisted": 0,
        "procedures_functions_or_triggers_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    assert payload["summary"] == {
        "capability_count": 12,
        "capability_with_candidate_count": 12,
        "capability_without_candidate_count": 0,
        "candidate_object_count": 132,
        "candidate_table_count": 28,
        "candidate_module_count": 104,
        "column_metadata_count": 826,
        "foreign_key_metadata_count": 64,
        "trigger_metadata_count": 40,
        "module_dependency_count": 475,
        "validation_error_count": 0,
    }
    assert all("definition" not in row for row in payload["objects"])
    coverage = {row["capability"]: row for row in payload["capability_coverage"]}
    assert not {name for name, row in coverage.items() if not row["candidate_count"]}
    objects = {(row["schema_name"], row["object_name"]): row for row in payload["objects"]}
    assert objects[("GNR", "tblGeneralConfig")]["row_count_metadata"] == 177
    assert objects[("GNR", "tblGeneralConfig_History")]["row_count_metadata"] == 8782


def test_extension_data_boundary_assessment_forbids_ui_transaction_ownership() -> None:
    source = EXTENSION_DATA_BOUNDARY_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(EXTENSION_DATA_BOUNDARY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["summary"] == {
        "capability_count": 12,
        "target_command_count": 11,
        "target_query_count": 2,
        "capability_with_direct_ui_data_access_count": 6,
        "direct_ui_data_access_method_count": 16,
        "direct_ui_data_access_unique_edge_count": 26,
        "legacy_boundary_classification_counts": {
            "LEGACY_UI_DIRECT_READ_CONTEXT_COUPLING": 2,
            "LEGACY_UI_OWNS_DATA_CONTEXT_WITHOUT_OBSERVED_COMMIT": 2,
            "LEGACY_UI_OWNS_EXPLICIT_COMMIT": 2,
            "NO_DIRECT_UI_DATA_ACCESS_IN_SELECTED_PATHS": 6,
        },
        "capability_with_clone_catalog_candidate_count": 12,
        "capability_without_clone_catalog_candidate_count": 0,
        "clone_catalog_candidate_count": 132,
        "clone_catalog_table_candidate_count": 28,
        "clone_catalog_module_candidate_count": 104,
        "validation_error_count": 0,
    }
    assessments = {row["capability"]: row for row in payload["assessments"]}
    assert assessments["configuration.general"]["legacy_boundary_classification"] == "LEGACY_UI_OWNS_EXPLICIT_COMMIT"
    assert assessments["configuration.accounting_article_template"]["legacy_boundary_classification"] == "LEGACY_UI_OWNS_EXPLICIT_COMMIT"
    assert assessments["pos.charge_device"]["legacy_boundary_classification"] == "LEGACY_UI_DIRECT_READ_CONTEXT_COUPLING"
    assert all("no DataContext" in row["target_boundary"]["ui"] for row in assessments.values())


def test_extension_gap_paths_recover_deep_command_and_child_form_evidence() -> None:
    source = EXTENSION_GAP_PATH_EXTRACTOR.read_text(encoding="utf-8")
    assert "LoadLibrary" not in source
    payload = json.loads(EXTENSION_GAP_PATH_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_TARGETED_PE_METADATA_AND_IL_GAP_TRACE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "config_or_resource_payloads_read": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    assert payload["summary"] == {
        "capability_gap_count": 3,
        "assembly_count": 7,
        "related_type_count": 16,
        "method_body_count": 55,
        "call_count": 454,
        "string_literal_count": 130,
        "allowlisted_business_literal_count": 18,
        "allowlisted_ui_literal_count": 12,
        "fingerprint_only_literal_count": 100,
        "missing_file_count": 0,
        "source_hash_mismatch_count": 0,
        "metadata_failure_count": 0,
        "method_body_error_count": 0,
        "validation_error_count": 0,
    }
    paths = {row["capability"]: row for row in payload["capability_paths"]}
    assert any("dbo.POSLineDiscount" in value for value in paths["pos.linear_discount"]["allowlisted_business_literals"])
    assert any(value.strip() == "usp_ReplicateSalesReceipt" for value in paths["pos.session"]["allowlisted_business_literals"])
    types = {row["type"]: row for row in payload["type_contracts"]}
    assert "VN.SDS.Tablet.UI.DealersDayPaths.FormEditDealerDayPath" in types
    assert any(method["method"] == "SaveCommand" for method in types["VN.SDS.Tablet.UI.DealersDayPaths.FormEditDealerDayPath"]["methods"])


def test_extension_sql_anchor_contracts_separate_proven_links_from_candidates() -> None:
    source = EXTENSION_SQL_ANCHOR_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(EXTENSION_SQL_ANCHOR_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_SELECTION_FROM_REDACTED_IL_AND_READ_ONLY_CLONE_CATALOG_METADATA",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "procedures_functions_or_triggers_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
        "module_definitions_or_credentials_persisted": 0,
    }
    assert payload["summary"] == {
        "capability_count": 12,
        "anchor_count": 48,
        "anchor_type_counts": {
            "SQL_STORED_PROCEDURE": 30,
            "USER_TABLE": 17,
            "VIEW": 1,
        },
        "table_column_count": 266,
        "module_parameter_count": 150,
        "foreign_key_count": 51,
        "trigger_count": 32,
        "dependency_count": 207,
        "runtime_execution_proven_anchor_count": 2,
        "candidate_only_anchor_count": 46,
        "validation_error_count": 0,
    }
    anchors = {
        anchor["object"]: anchor
        for contract in payload["contracts"]
        for anchor in contract["anchors"]
    }
    proven = {name for name, row in anchors.items() if row["runtime_execution_proven"]}
    assert proven == {"dbo.POSLineDiscount", "dbo.usp_ReplicateSalesReceipt"}
    assert all(contract["target_gates"] for contract in payload["contracts"])


def test_extension_sql_semantics_persist_footprints_not_definitions() -> None:
    source = EXTENSION_SQL_SEMANTICS_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    payload = json.loads(EXTENSION_SQL_SEMANTICS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_MODULE_DEFINITION_IN_MEMORY_REDACTED_SEMANTIC_PARSE",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_definitions_persisted": 0,
        "string_literals_persisted": 0,
        "credentials_or_secrets_persisted": 0,
        "procedures_functions_or_triggers_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    assert payload["summary"] == {
        "module_count": 8,
        "found_module_count": 8,
        "parameter_count": 42,
        "dependency_count": 114,
        "lexical_operation_count": 31,
        "resolved_mutation_target_count": 11,
        "module_with_explicit_transaction_envelope_count": 5,
        "module_with_explicit_error_handler_count": 1,
        "module_with_dynamic_sql_signal_count": 0,
        "definition_persisted_count": 0,
        "missing_module_count": 0,
        "validation_error_count": 0,
    }
    assert all("definition" not in row for row in payload["modules"])
    modules = {row["object"]: row for row in payload["modules"]}
    replication = modules["dbo.usp_ReplicateSalesReceipt"]
    assert replication["dependency_count"] == 66
    assert replication["lexical_operation_count"] == 17
    assert replication["has_explicit_transaction_envelope"]
    assert replication["has_explicit_error_handler"]
    assert {"Acc.tblPayments", "dbo.PSession", "inv.tblVocherHdr"} <= set(replication["resolved_mutation_targets"])


def test_pos_receipt_replication_contract_is_resumable_reconciled_and_no_writeback() -> None:
    source = POS_RECEIPT_REPLICATION_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(POS_RECEIPT_REPLICATION_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_TARGET_DESIGN_FROM_REDACTED_STATIC_AND_CLONE_METADATA_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
        "operational_varanegar_acknowledgements_or_writes": 0,
        "pilot_cutover_or_dual_write_authorized": 0,
    }
    assert payload["evidence"]["legacy_dependency_count"] == 66
    assert payload["evidence"]["legacy_lexical_operation_count"] == 17
    assert payload["evidence"]["target_golden_case_count"] == 20
    assert len(payload["batch_states"]) == 9
    assert len(payload["allowed_transitions"]) == 10
    assert len(payload["item_states"]) == 8
    assert len(payload["target_effect_boundaries"]) == 6
    assert len(payload["reconciliation_checks"]) == 9
    assert all(row["blocking"] for row in payload["reconciliation_checks"])
    assert payload["quarantine_contract"]["auto_accept_or_auto_fix_allowed"] is False
    assert any("never writes acknowledgement" in rule for rule in payload["execution_contract"])
    assert payload["readiness"].startswith("TARGET_DESIGN_ONLY")


def test_pos_receipt_transitive_graph_is_bounded_redacted_and_read_only() -> None:
    source = POS_RECEIPT_TRANSITIVE_GRAPH_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    assert "EXEC dbo.usp_ReplicateSalesReceipt" not in source
    payload = json.loads(POS_RECEIPT_TRANSITIVE_GRAPH_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_AND_IN_MEMORY_REDACTED_DEFINITION_GRAPH",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_definitions_or_string_literals_persisted": 0,
        "credentials_or_identity_grants_persisted": 0,
        "procedures_functions_views_or_triggers_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    summary = payload["summary"]
    assert summary["node_count"] == 500
    assert summary["edge_count"] == 1039
    assert summary["trigger_node_count"] == 362
    assert summary["resolved_write_target_count"] == 48
    assert summary["graph_truncated_at_safety_cap"] is True
    assert summary["unexpanded_frontier_count"] == 160
    assert summary["definition_persisted_count"] == 0
    assert payload["warnings"]
    assert all("definition" not in row for row in payload["nodes"])


def test_erp_traceability_maps_all_modules_cases_risks_and_p0_items() -> None:
    source = REQUIREMENTS_TRACEABILITY_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(REQUIREMENTS_TRACEABILITY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_REDACTED_PERSISTED_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
        "implementation_or_production_readiness_inferred": 0,
    }
    assert payload["summary"] == {
        "module_count": 14,
        "traced_module_count": 14,
        "design_only_evidence_gap_module_count": 0,
        "mapped_golden_case_count": 877,
        "mapped_risk_assignment_count": 221,
        "unique_risk_count": 56,
        "mapped_p0_item_count": 26,
        "mapped_three_month_activity_block_count": 14,
        "module_with_direct_three_month_activity_evidence_count": 9,
        "module_with_critical_risk_count": 13,
        "command_ready_module_count": 0,
        "validation_error_count": 0,
    }
    assert payload["unmapped"] == {
        "golden_case_ids": [],
        "p0_item_ids": [],
        "activity_domains": [],
    }
    modules = {row["module"]: row for row in payload["modules"]}
    assert modules["sales"]["golden_case_count"] == 97
    assert modules["inventory"]["risk_severity_counts"]["CRITICAL"] == 17
    assert modules["platform"]["direct_p0_item_count"] == 14
    assert modules["sales"]["three_month_activity_evidence_count"] == 2
    assert modules["reporting_documents"]["golden_case_count"] == 175
    assert modules["master_data"]["golden_case_count"] == 114
    assert modules["organization_context"]["golden_case_count"] == 64
    assert modules["inventory"]["golden_case_count"] == 79
    assert modules["pricing_rules"]["golden_case_count"] == 82


def test_pos_source_model_preserves_catalog_not_business_rows_or_definitions() -> None:
    source = POS_SOURCE_MODEL_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    payload = json.loads(POS_SOURCE_MODEL_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_AND_AGGREGATE_ROW_COUNTS",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_or_trigger_definitions_persisted": 0,
        "procedures_or_triggers_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    summary = payload["summary"]
    assert summary["found_table_count"] == 13
    assert summary["column_count"] == 309
    assert summary["foreign_key_constraint_count"] == 89
    assert summary["foreign_key_not_trusted_count"] == 61
    assert summary["in_scope_foreign_key_constraint_count"] == 10
    assert summary["in_scope_foreign_key_not_trusted_count"] == 7
    assert summary["trigger_count"] == 51
    assert summary["table_with_source_version_signal_count"] == 0
    assert summary["row_count_snapshot_total"] == 30
    assert payload["missing_tables"] == []
    assert all("definition" not in trigger for table in payload["tables"] for trigger in table["triggers"])


def test_bank_reconciliation_source_model_is_read_only_and_keeps_matching_polymorphic() -> None:
    source = BANK_RECONCILIATION_SOURCE_MODEL_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    payload = json.loads(BANK_RECONCILIATION_SOURCE_MODEL_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_AND_AGGREGATE_ROW_COUNTS",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_or_trigger_definitions_persisted": 0,
        "procedures_or_triggers_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    summary = payload["summary"]
    assert summary["requested_table_count"] == 15
    assert summary["found_table_count"] == 15
    assert summary["missing_table_count"] == 0
    assert summary["matching_instrument_column_count"] >= 6
    assert summary["validation_error_count"] == 0
    assert payload["missing_tables"] == []
    assert payload["target_contract"]["matching_cardinality"] == "one bank statement row to zero or more typed reconciliation links"
    assert payload["target_contract"]["direct_table_crud_allowed"] is False
    assert payload["target_contract"]["provisional_command_names"] == ["bank_reconciliation.cancel"]
    assert payload["target_contract"]["cancel_legacy_parity_status"] == "UNPROVEN_NO_DISTINCT_LEGACY_COMMAND_OBSERVED"
    assert "bank_reconciliation.reverse_confirmed_session" in payload["target_contract"]["additional_required_command_boundaries"]
    tables = {row["object"]: row for row in payload["tables"]}
    assert {
        "BankBillFormatTypeId",
        "BankId",
        "BankAccountTypeId",
        "StartRow",
        "Seperator",
        "IsArabic",
        "SQLStatement",
        "SchemaFile",
        "HDR",
        "BankBillFormatId",
    } == {row["name"] for row in tables["dbo.BankBillFormat"]["columns"]}
    assert {row["name"] for row in tables["dbo.BankBillFormatItem"]["columns"]} == {
        "BankBillFormatId",
        "ReconciliationColumnId",
        "StartColumn",
        "EndColumn",
        "BankBillFormatItemId",
    }
    assert {row["name"] for row in tables["dbo.BankBillFormatType"]["columns"]} == {
        "FormatExtension",
        "BankBillFormatTypeId",
    }
    assert {row["name"] for row in tables["dbo.ReconciliationColumn"]["columns"]} == {
        "ReconciliationColumnName",
        "ReconciliationColumnId",
    }
    assert all(
        tables[name]["row_count_snapshot"] == 0
        for name in (
            "dbo.BankBillFormat",
            "dbo.BankBillFormatItem",
            "dbo.BankBillFormatType",
            "dbo.ReconciliationColumn",
        )
    )
    assert all("definition" not in trigger for table in payload["tables"] for trigger in table["triggers"])


def test_priority_gap_declared_fields_are_offline_metadata_only() -> None:
    source = PRIORITY_GAP_DECLARED_FIELDS_EXTRACTOR.read_text(encoding="utf-8")
    assert "dnfile" in source
    assert "_connect(" not in source
    payload = json.loads(PRIORITY_GAP_DECLARED_FIELDS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_TARGETED_TYPE_AND_FIELD_METADATA_PARSE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "field_values_string_literals_resources_or_config_payloads_read_or_persisted": 0,
        "runtime_binding_requiredness_or_visibility_inferred": 0,
    }
    summary = payload["summary"]
    assert summary["selected_priority_form_count"] == 7
    assert summary["resolved_form_type_count"] == 7
    assert summary["missing_form_type_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert summary["validation_error_count"] == 0
    assert summary["declared_control_field_count"] > 0
    assert summary["form_with_declared_control_field_count"] == 6
    assert summary["form_without_declared_control_field_count"] == 1
    assert summary["inherited_base_field_count"] > 0
    special = next(
        row for row in payload["forms"]
        if row["form_type"] == "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict"
    )
    assert special["entrypoint_status"] == "ROOT_ENTRYPOINT_STILL_UNRESOLVED"
    assert special["declared_control_field_count"] == 0
    assert special["inherited_base_field_count"] > 0
    assert any(
        row["base_type"] == "Application.BaseTemaplateV2.UIBase.FormBaseV2SimpleDataEntry"
        and row["declared_field_count"] > 0
        for row in special["base_type_chain"]
    )


def test_bank_reconciliation_command_guards_preserve_permission_date_and_transaction_gates() -> None:
    source = BANK_RECONCILIATION_COMMAND_GUARDS_EXTRACTOR.read_text(encoding="utf-8")
    assert "dnfile" in source
    assert "_connect(" not in source
    payload = json.loads(BANK_RECONCILIATION_COMMAND_GUARDS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_TARGETED_IL_METHOD_CONTRACT_PARSE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "business_row_values_read_or_persisted": 0,
        "string_literal_or_config_payload_values_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["target_form_type_count"] == 4
    assert summary["found_form_type_count"] == 4
    assert summary["selected_method_contract_count"] == 10
    assert summary["missing_selected_method_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert summary["method_body_error_count"] == 0
    assert summary["validation_error_count"] == 0
    methods = {
        (row["form_type"], row["method"]): row for row in payload["method_contracts"]
    }
    list_permission = methods[("TreasuryOld.Forms.frmBankReconciliationList", "SetFormPermission")]
    assert {
        "TransferList.get_AddNew",
        "TransferList.get_Edit",
        "TransferList.get_Delete",
        "TreasuryOld.DataLayer.OprDate.get_IsClosed",
    }.issubset(list_permission["business_calls"])
    setup_permission = methods[("TreasuryOld.Forms.frmReconciliationSetup", "SetFormPermission")]
    assert {"ReconciliationSetup.get_Edit", "ReconciliationSetup.get_Delete"}.issubset(
        setup_permission["business_calls"]
    )
    validation = methods[("TreasuryOld.Forms.frmReconciliationSetup", "DataIsValid")]
    assert {
        "TreasuryOld.Forms.frmReconciliationSetup.cmbBankAccountName",
        "TreasuryOld.Forms.frmReconciliationSetup.txtBankDate",
        "TreasuryOld.Forms.frmReconciliationSetup.txtBankFile",
    }.issubset(validation["referenced_fields"])
    detail_delete = methods[("TreasuryOld.Forms.frmReconciliation", "btnDelete_Click")]
    assert {
        "TreasuryOld.DataLayer.Transaction.Start",
        "TreasuryOld.DataLayer.Transaction.Commit",
        "TreasuryOld.DataLayer.Transaction.RollBack",
    }.issubset(detail_delete["business_calls"])
    assert payload["target_contract"]["direct_table_crud_allowed"] is False
    assert payload["target_contract"]["permission_alias_copy_allowed"] is False


def test_special_options_district_assessment_does_not_promote_an_empty_unrouted_shell() -> None:
    source = SPECIAL_OPTIONS_DISTRICT_ASSESSMENT_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    payload = json.loads(SPECIAL_OPTIONS_DISTRICT_ASSESSMENT_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_CATALOG_AND_OFFLINE_METADATA_CORRELATION",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_or_trigger_definitions_persisted": 0,
        "assemblies_loaded_or_executed": 0,
        "procedures_or_triggers_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    summary = payload["summary"]
    assert summary["form_method_count"] == 3
    assert summary["form_business_method_count"] == 0
    assert summary["direct_declared_field_count"] == 0
    assert summary["inherited_base_field_count"] == 88
    assert summary["static_route_count"] == 0
    assert summary["external_launcher_or_reference_count"] == 0
    assert summary["validation_error_count"] == 0
    assert summary["clone_catalog_candidate_count"] >= 0
    assert payload["assessment"]["classification"] == "PLACEHOLDER_OR_DYNAMIC_FEATURE_CANDIDATE_UNRESOLVED"
    assert payload["assessment"]["deletion_or_scope_exclusion_authorized"] is False
    assert payload["assessment"]["target_schema_or_command_inference_allowed"] is False


def test_bank_statement_import_boundary_quarantines_legacy_file_and_query_execution() -> None:
    source = BANK_STATEMENT_IMPORT_BOUNDARY_EXTRACTOR.read_text(encoding="utf-8")
    assert "dnfile" in source
    assert "_connect(" not in source
    payload = json.loads(BANK_STATEMENT_IMPORT_BOUNDARY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_TARGETED_IL_IMPORT_AND_FILE_SIDE_EFFECT_PARSE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "files_created_deleted_or_opened": 0,
        "office_processes_started_or_killed": 0,
        "string_literal_or_config_payload_values_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["selected_method_contract_count"] == 6
    assert summary["missing_selected_method_count"] == 0
    assert summary["ole_db_import_method_count"] == 3
    assert summary["file_write_or_delete_method_count"] == 2
    assert summary["office_automation_method_count"] == 1
    assert summary["process_kill_method_count"] == 1
    assert summary["source_hash_mismatch_count"] == 0
    assert summary["method_body_error_count"] == 0
    assert summary["validation_error_count"] == 0
    methods = {row["method"]: row for row in payload["methods"]}
    for name in ("getDataFromDBF", "getDataFromTXT", "getDataFromXLS"):
        assert {
            "System.Data.OleDb.OleDbConnection..ctor",
            "System.Data.OleDb.OleDbCommand..ctor",
            "System.Data.Common.DbDataAdapter.Fill",
        }.issubset(methods[name]["calls"])
    assert "System.IO.File.CreateText" in methods["WriteSchemaFile"]["calls"]
    assert "System.Diagnostics.Process.Kill" in methods["SaveAsExcel"]["calls"]
    accept = methods["btnAccept_Click"]
    assert {
        "TreasuryOld.Forms.frmReconciliationSetup.SQLStatement",
        "TreasuryOld.Forms.frmReconciliationSetup.SchemaFile",
        "TreasuryOld.Forms.frmReconciliationSetup.HDR",
        "TreasuryOld.Forms.frmReconciliationSetup.FormatExtension",
    }.issubset(accept["referenced_fields"])
    target = payload["target_contract"]
    assert target["arbitrary_provider_or_query_execution_allowed"] is False
    assert target["desktop_office_automation_allowed"] is False
    assert target["arbitrary_process_kill_allowed"] is False
    assert target["direct_import_to_accounting_ledger_allowed"] is False


def test_bank_statement_persistence_boundary_keeps_header_and_rows_atomic() -> None:
    source = BANK_STATEMENT_PERSISTENCE_BOUNDARY_EXTRACTOR.read_text(encoding="utf-8")
    assert "sys.sql_modules" not in source
    payload = json.loads(BANK_STATEMENT_PERSISTENCE_BOUNDARY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["denies_data_writes"] is True
    assert payload["safety"]["raw_sql_module_definitions_or_connection_strings_persisted"] == 0
    assert payload["safety"]["application_or_sql_commands_executed"] == 0
    assert payload["summary"] == {
        "selected_method_contract_count": 10,
        "bank_bill_crud_fingerprint_count": 7,
        "bank_bill_crud_verb_counts": {"DELETE": 1, "INSERT": 1, "SELECT": 4, "UPDATE": 1},
        "allowlisted_hook_name_count": 3,
        "clone_present_hook_count": 1,
        "clone_absent_optional_hook_count": 2,
        "source_hash_mismatch_count": 0,
        "method_body_error_count": 0,
        "validation_error_count": 0,
    }
    assert payload["persistence_chain"] == [
        "frmReconciliationSetup.SaveData",
        "Reconcile.Update",
        "Reconcile.UpdateDetailTables",
        "BankBillS.Update",
        "BankBill.Update",
        "BankBillAdapter.Update",
        "dbo.BankBill CRUD command",
    ]
    assert {row["object"] for row in payload["clone_catalog_hooks"]} == {
        "dbo.DoBankBill_DeleteReconcileItem"
    }
    assert payload["clone_absent_optional_hooks"] == ["AfterBankBill", "BeforeBankBill"]
    target = payload["target_contract"]
    assert target["header_and_imported_statement_rows_commit_atomically"] is True
    assert target["parser_staging_commits_directly_to_ledger"] is False
    assert target["repository_level_commit_allowed"] is False
    assert target["optional_runtime_procedure_discovery_allowed"] is False


def test_bank_reconciliation_golden_cases_cover_target_commands_without_source_execution() -> None:
    source = BANK_RECONCILIATION_GOLDEN_CASES_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(BANK_RECONCILIATION_GOLDEN_CASES_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_SYNTHETIC_TARGET_TEST_DESIGN",
        "database_connections": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_values_used": 0,
        "synthetic_cases_only": 1,
    }
    assert payload["summary"] == {
        "source_command_count": 5,
        "case_count": 93,
        "common_case_count": 40,
        "failure_injection_case_count": 15,
        "domain_specific_case_count": 30,
        "post_commit_parity_case_count": 8,
        "duplicate_case_id_count": 0,
    }
    assert {row["command"] for row in payload["cases"]} == {
        "bank_reconciliation.import_statement",
        "bank_reconciliation.match_instrument",
        "bank_reconciliation.unmatch_instrument",
        "bank_reconciliation.confirm",
        "bank_reconciliation.cancel",
    }
    assert all("source Varanegar untouched" in row["assertions"] for row in payload["cases"])
    assert any(
        row["command"] == "bank_reconciliation.import_statement"
        and row["variation"] == "parser_timeout_or_fault"
        for row in payload["cases"]
    )
    assert any(
        row["command"] == "bank_reconciliation.confirm"
        and row["variation"] == "bank_cardex_reconciliation_mismatch"
        for row in payload["cases"]
    )
    provisional_cancel = payload["provisional_command_contracts"]["bank_reconciliation.cancel"]
    assert provisional_cancel["legacy_parity_status"] == "UNPROVEN_NO_DISTINCT_LEGACY_COMMAND_OBSERVED"
    assert provisional_cancel["process_owner_signoff_required"] is True
    assert "bank_reconciliation.discard_imported_statement" in provisional_cancel["must_not_conflate_with"]
    assert "NeginPakhsh_WebDev clone" in payload["execution_policy"]["forbidden_environment"]


def test_bank_reconciliation_transaction_boundary_rejects_static_legacy_transaction_state_for_web() -> None:
    source = BANK_RECONCILIATION_TRANSACTION_BOUNDARY_EXTRACTOR.read_text(encoding="utf-8")
    assert "dnfile" in source
    assert "_connect(" not in source
    payload = json.loads(BANK_RECONCILIATION_TRANSACTION_BOUNDARY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_TARGETED_IL_AND_FIELD_ATTRIBUTE_TRANSACTION_PARSE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
        "string_literal_or_connection_string_values_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["selected_method_contract_count"] == 6
    assert summary["static_transaction_field_count"] == 4
    assert summary["thread_static_transaction_field_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert summary["method_body_error_count"] == 0
    assert summary["validation_error_count"] == 0
    legacy = payload["legacy_transaction_semantics"]
    assert legacy["outer_confirm_scope"] == "TreasuryOld.Forms.frmReconciliation.DoAccept"
    assert legacy["start_opens_physical_transaction_only_when_level_zero"] is True
    assert legacy["commit_physically_commits_only_when_level_one"] is True
    assert legacy["rollback_resets_level_to_zero_and_rolls_back_physical_transaction"] is True
    assert legacy["nested_data_layer_calls_share_static_transaction_state"] is True
    target = payload["target_contract"]
    assert target["static_connection_transaction_or_nesting_counter_allowed"] is False
    assert target["single_application_service_transaction_owner_required"] is True
    assert target["repository_level_commit_allowed"] is False


def test_bank_reconciliation_cardex_sql_boundary_is_catalog_only_and_typed() -> None:
    source = BANK_RECONCILIATION_CARDEX_SQL_BOUNDARY_EXTRACTOR.read_text(encoding="utf-8")
    assert "sys.sql_expression_dependencies" in source
    assert "sys.sql_modules" not in source
    assert "EXEC " not in source.upper()
    payload = json.loads(BANK_RECONCILIATION_CARDEX_SQL_BOUNDARY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["denies_data_writes"] is True
    assert payload["safety"]["module_definitions_read_or_persisted"] == 0
    assert payload["safety"]["business_rows_or_values_read_or_persisted"] == 0
    assert payload["safety"]["procedures_functions_triggers_or_application_commands_executed"] == 0
    assert payload["il_boundary"]["allowlisted_command_names"] == [
        "DoReconcile_UpdateBankAccountCardex"
    ]
    assert payload["il_boundary"]["target_parameter_name_observed"] is True
    assert payload["summary"] == {
        "allowlisted_il_command_count": 1,
        "catalog_object_count": 1,
        "catalog_parameter_count": 2,
        "catalog_dependency_count": 9,
        "source_hash_mismatch_count": 0,
        "validation_error_count": 0,
    }
    assert [(row["name"], row["data_type"], row["is_output"]) for row in payload["catalog_parameters"]] == [
        ("@ReconcileId", "int", False),
        ("@ErrorNo", "tinyint", True),
    ]
    dependencies = {row["referenced_object"] for row in payload["catalog_dependencies"]}
    assert {
        "dbo.BankBill",
        "dbo.PCheque",
        "dbo.PWithdraw",
        "dbo.RBankDraft",
        "dbo.RCashDraft",
        "dbo.RCheque",
        "dbo.ReconcileItem",
        "dbo.Transfer",
    }.issubset(dependencies)
    target = payload["target_contract"]
    assert target["direct_web_execution_of_legacy_procedure_allowed"] is False
    assert target["repository_accepts_typed_reconcile_id_only"] is True
    assert target["dependency_effects_require_post_commit_parity_checks"] is True


def test_bank_reconciliation_matching_boundary_is_typed_explicit_and_event_safe() -> None:
    source = BANK_RECONCILIATION_MATCHING_BOUNDARY_EXTRACTOR.read_text(encoding="utf-8")
    assert "sys.sql_expression_dependencies" in source
    assert "sys.sql_modules" not in source
    payload = json.loads(
        BANK_RECONCILIATION_MATCHING_BOUNDARY_ARTIFACT.read_text(encoding="utf-8")
    )
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_ALLOWLISTED_IL_AND_SQL_SYSTEM_CATALOG_METADATA",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": True,
        "assemblies_loaded_or_executed": 0,
        "forms_or_application_commands_executed": 0,
        "procedures_hooks_or_triggers_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
        "sql_module_definitions_persisted": 0,
        "unknown_string_literal_values_persisted": 0,
    }
    assert payload["summary"] == {
        "selected_method_contract_count": 15,
        "typed_reference_mapping_count": 6,
        "matching_event_count": 2,
        "matching_amount_column_count": 4,
        "empty_grid_delete_handler_count": 2,
        "allowlisted_hook_name_count": 2,
        "clone_present_hook_count": 0,
        "catalog_object_count": 5,
        "catalog_view_column_count": 27,
        "catalog_dependency_count": 11,
        "summary_parameter_count": 14,
        "summary_dependency_count": 6,
        "source_hash_mismatch_count": 0,
        "method_body_error_count": 0,
        "validation_error_count": 0,
    }
    assert {
        row["type_discriminator"]: row["typed_reference_property"]
        for row in payload["matching_dispatch"]["typed_reference_mappings"]
    } == {
        "PCHEQUE": "PChequeId",
        "PWITHDRAW": "PWithdrawId",
        "RBANKDRAFT": "RBankDraftId",
        "RCASHDRAFT": "RCashDraftId",
        "RCHEQUE": "RChequeId",
        "TRANSFER": "TransferId",
    }
    for event in payload["matching_event_contracts"]:
        assert event["amount_columns"] == [
            "Credit",
            "Debit",
            "VocherCredit",
            "VocherDebit",
        ]
        assert event["exact_decimal_equality_signal_observed"] is True
        assert event["absolute_difference_signal_observed"] is True
        assert event["confirmation_prompt_call_observed"] is True
        assert event["immediate_link_persistence_call_observed"] is True
        assert event["refresh_after_match_calls_observed"] is True
    persistence = payload["persistence_contract"]
    assert persistence["legacy_ui_event_calls_link_update_immediately"] is True
    assert persistence["reconcile_item_update_owns_nested_static_transaction"] is True
    assert persistence["optional_hook_names_observed_in_il"] == [
        "AfterReconcileItem",
        "BeforeReconcileItem",
    ]
    assert persistence["optional_hooks_present_in_clone"] == []
    assert persistence["empty_grid_delete_handlers"] == [
        "vGrid_DeletingRecords",
        "vGrid_RecordsDeleted",
    ]
    summary = payload["summary_boundary"]
    assert summary["legacy_command"] == "dbo.DoReconcile_GetSummary"
    assert [(row["name"], row["data_type"], row["is_output"]) for row in summary["catalog_parameters"]] == [
        ("@ReconcileId", "int", False),
        ("@VocherDate", "varchar", False),
        ("@BankAccountId", "int", False),
        ("@RemainingLastReconcile", "money", True),
        ("@RemainingThisPeriod", "money", True),
        ("@RemainingBill", "money", True),
        ("@RemainingCardex", "money", True),
        ("@BillDebitOpenItems", "money", True),
        ("@BillCreditOpenItems", "money", True),
        ("@CardexDebitOpenItems", "money", True),
        ("@CardexCreditOpenItems", "money", True),
        ("@RealRemainingBill", "money", True),
        ("@RealRemainingCardex", "money", True),
        ("@Reconcile", "money", True),
    ]
    assert summary["input_scope"] == ["ReconcileId", "VocherDate", "BankAccountId"]
    assert summary["output_metric_names_are_catalog_confirmed"] is True
    assert summary["output_formula_semantics_confirmed"] is False
    assert summary["module_definition_read_or_persisted"] is False
    assert {
        row["referenced_object"] for row in summary["catalog_dependencies"]
    } == {
        "BankAccount",
        "BankAccountCardex",
        "BankBill",
        "FreeBankAccountCardex",
        "FreeBankBill",
        "Reconcile",
    }
    target = payload["target_contract"]
    assert target["direct_grid_event_persistence_allowed"] is False
    assert target["explicit_user_command_required"] is True
    assert target["exactly_one_typed_source_reference_required"] is True
    assert target["single_application_service_transaction_owner_required"] is True
    assert target["repository_level_commit_allowed"] is False
    assert target["idempotency_and_optimistic_version_required"] is True
    assert target["optional_runtime_hook_discovery_allowed"] is False
    assert target["unmatch_is_separate_command"] is True
    assert target["summary_query_returns_named_money_metrics_without_exposing_legacy_procedure"] is True
    assert target["summary_formula_parity_requires_fixture_or_owner_validation"] is True


def test_bank_reconciliation_profile_and_state_boundary_rejects_implicit_web_semantics() -> None:
    source = BANK_RECONCILIATION_PROFILE_STATE_EXTRACTOR.read_text(encoding="utf-8")
    assert "sys.sql_expression_dependencies" in source
    assert "sys.sql_modules" not in source
    payload = json.loads(BANK_RECONCILIATION_PROFILE_STATE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_STATIC_IL_EXISTING_SOURCE_MODEL_AND_SQL_SYSTEM_CATALOG",
        "assemblies_loaded_or_executed": 0,
        "forms_or_application_commands_executed": 0,
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": True,
        "database_connections": 1,
        "business_rows_or_values_read_or_persisted": 0,
        "raw_sql_or_profile_values_persisted": 0,
        "unknown_string_literal_values_persisted": 0,
    }
    assert payload["summary"] == {
        "selected_method_contract_count": 10,
        "observed_runtime_profile_field_count": 4,
        "format_dispatch_key_count": 3,
        "profile_table_count": 4,
        "profile_table_row_count_snapshot": 0,
        "profile_projection_column_count": 46,
        "profile_projection_dependency_count": 7,
        "state_marker_column_count": 3,
        "explicit_legacy_state_column_count": 0,
        "confirmed_marker_count": 2,
        "source_hash_mismatch_count": 0,
        "method_body_error_count": 0,
        "validation_error_count": 0,
    }
    profile = payload["profile_boundary"]
    assert profile["observed_runtime_profile_fields"] == [
        "FormatExtension",
        "HDR",
        "SQLStatement",
        "SchemaFile",
    ]
    assert profile["format_dispatch_keys"] == ["dbf", "txt", "xls"]
    assert profile["inline_bank_account_profile_projection"]["raw_sql_text_persisted"] is False
    assert profile["clone_profile_projection_object"]["name"] == "BankAccount2"
    assert {
        row["name"] for row in profile["clone_profile_projection_columns"]
    }.issuperset(
        {
            "FormatExtension",
            "FormatFileName",
            "BankBillFormatId",
            "BankBillFormatTypeId",
            "SQLStatement",
            "SchemaFile",
            "HDR",
        }
    )
    assert {row["referenced_object"] for row in profile["clone_profile_projection_dependencies"]}.issuperset(
        {"BankAccount", "BankBillFormat", "BankBillFormatType"}
    )
    assert profile["profile_tables_have_version_or_effective_date_column"] is False
    assert profile["profile_tables_have_active_or_approval_column"] is False
    assert profile["start_row_separator_and_arabic_form_getter_observed"] is False
    assert profile["profile_values_available_in_clone_snapshot"] is False
    legacy = payload["legacy_state_boundary"]
    assert legacy["storage_has_explicit_state_or_status_column"] is False
    assert legacy["confirm_command_dispatch"]["command_key"] == "Ok"
    assert any(call.endswith("DoAccept") for call in legacy["confirm_command_dispatch"]["allowlisted_target_calls"])
    assert legacy["confirm_sets_confirmer_id"] is True
    assert legacy["confirm_sets_confirm_date"] is True
    assert legacy["confirm_sets_amount_to_decimal_zero"] is True
    assert legacy["confirm_updates_bank_account_cardex"] is True
    assert legacy["detail_form_has_own_permission_method"] is False
    assert legacy["detail_form_has_operation_date_guard_call"] is False
    root = payload["misleading_named_root_boundary"]
    assert root["list_applying_filter_instruction_count"] == 1
    assert root["list_applying_filter_calls"] == []
    assert root["permission_alias_calls"] == [
        "TransferList.get_AddNew",
        "TransferList.get_Delete",
        "TransferList.get_Edit",
    ]
    assert root["core_reconcile_query_or_row_load_observed"] is False
    assert root["direct_target_route_or_command_inference_allowed"] is False
    assert root["deletion_or_scope_exclusion_authorized"] is False
    target = payload["target_contract"]
    assert target["profile_is_versioned_approved_and_immutable_after_use"] is True
    assert target["raw_sql_provider_or_path_configuration_allowed"] is False
    assert target["parser_kind_is_typed_enum_not_extension_string"] is True
    assert target["legacy_amount_zero_is_not_a_computed_reconciliation_result"] is True
    assert target["cancelled_or_reversed_state_inferred_from_legacy"] is False
    assert target["authorization_must_be_enforced_server_side_not_inherited_from_parent_ui"] is True


def test_bank_reconciliation_role_uat_is_identity_free_and_not_claimed_executed() -> None:
    source = BANK_RECONCILIATION_ROLE_UAT_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "app_user_id" not in source.casefold()
    payload = json.loads(BANK_RECONCILIATION_ROLE_UAT_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["status"] == "DESIGN_ONLY_NOT_AUTHENTICATED_OR_EXECUTED"
    assert payload["safety"] == {
        "mode": "OFFLINE_SYNTHETIC_IDENTITY_FREE_UAT_DESIGN",
        "database_connections": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "identity_membership_or_individual_right_values_used": 0,
        "production_assignments_created": 0,
        "synthetic_cases_only": 1,
    }
    assert payload["summary"] == {
        "role_template_count": 6,
        "capability_count": 7,
        "role_assignment_case_count": 42,
        "context_negative_case_count": 30,
        "state_or_profile_case_count": 15,
        "sod_case_count": 7,
        "non_inference_case_count": 6,
        "synthetic_uat_case_count": 100,
        "authenticated_uat_execution_count": 0,
        "owner_approved_case_count": 0,
        "production_assignment_count": 0,
        "duplicate_case_id_count": 0,
    }
    assert payload["capabilities"] == [
        "bank_reconciliation.view",
        "bank_reconciliation.import_statement",
        "bank_reconciliation.match_instrument",
        "bank_reconciliation.unmatch_instrument",
        "bank_reconciliation.confirm",
        "bank_reconciliation.cancel",
        "bank_reconciliation.reverse_confirmed_session",
    ]
    roles = {row["role"]: row for row in payload["role_templates"]}
    assert roles["bank_statement_importer"]["allow"] == [
        "bank_reconciliation.view",
        "bank_reconciliation.import_statement",
    ]
    assert roles["bank_reconciliation_confirmer"]["allow"] == [
        "bank_reconciliation.view",
        "bank_reconciliation.confirm",
    ]
    assert roles["bank_reconciliation_reversal_authorizer"]["allow"] == [
        "bank_reconciliation.view",
        "bank_reconciliation.reverse_confirmed_session",
    ]
    assert all(row["owner_approval_status"] == "NOT_APPROVED" for row in roles.values())
    auth = payload["authorization_contract"]
    assert auth["deny_overrides_allow"] is True
    assert auth["neutral_is_not_allow"] is True
    assert auth["legacy_edit_implies_confirm"] is False
    assert auth["legacy_delete_implies_cancel"] is False
    assert auth["legacy_delete_or_confirm_implies_reverse"] is False
    assert auth["aggregate_counts_prove_individual_access"] is False
    assert auth["parent_ui_permission_is_inherited_by_web_command"] is False
    assert all("source Varanegar remains untouched" in row["assertions"] for row in payload["cases"])
    assert payload["approval_gate"]["authenticated_test_accounts_required"] is True
    assert payload["approval_gate"]["ready_for_authenticated_uat"] is False
    assert payload["approval_gate"]["ready_for_production_assignment"] is False


def test_bank_reconciliation_summary_ui_maps_all_signed_outputs_without_formula_claim() -> None:
    source = BANK_RECONCILIATION_SUMMARY_UI_EXTRACTOR.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "ExecuteNonQuery" not in source
    payload = json.loads(BANK_RECONCILIATION_SUMMARY_UI_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "ALLOWLISTED_STATIC_IL_ONLY",
        "assembly_loaded_or_executed": 0,
        "form_invoked": 0,
        "database_connections": 0,
        "stored_procedures_executed": 0,
        "business_row_values_read": 0,
        "string_literal_values_persisted": 0,
    }
    assert payload["summary"] == {
        "selected_method_count": 1,
        "instruction_count": 394,
        "summary_input_count": 3,
        "summary_output_count": 11,
        "output_to_label_mapping_count": 11,
        "negative_comparison_count": 11,
        "absolute_value_multiply_count": 11,
        "red_color_assignment_count": 11,
        "dark_blue_color_assignment_count": 11,
        "text_assignment_count": 22,
        "foreground_color_assignment_count": 22,
        "assembly_hash_mismatch_count": 0,
        "string_literal_value_persisted_count": 0,
        "database_connection_count": 0,
        "validation_error_count": 0,
    }
    assert [row["output_metric"] for row in payload["output_to_ui_mappings"]] == [
        "RemainingLastReconcile",
        "RemainingThisPeriod",
        "RemainingBill",
        "RemainingCardex",
        "BillDebitOpenItems",
        "BillCreditOpenItems",
        "CardexDebitOpenItems",
        "CardexCreditOpenItems",
        "RealRemainingBill",
        "RealRemainingCardex",
        "Reconcile",
    ]
    presentation = payload["presentation_semantics"]
    assert presentation["negative_values_multiplied_by_decimal_minus_one_before_text"] is True
    assert presentation["negative_values_have_parenthesis_tokens_around_absolute_value"] is True
    assert presentation["presentation_does_not_update_reconcile_or_other_domain_entity"] is True
    target = payload["target_contract"]
    assert target["summary_api_returns_signed_decimal_metrics"] is True
    assert target["accessible_text_must_not_rely_on_color_alone"] is True
    assert target["summary_formula_semantics_confirmed"] is False
    assert target["runtime_row_result_parity_required_before_command_pilot"] is True


def test_bank_reconciliation_summary_sql_semantics_are_redacted_exact_and_nonexecuting() -> None:
    source = BANK_RECONCILIATION_SUMMARY_SQL_EXTRACTOR.read_text(encoding="utf-8")
    assert "cursor.execute(OBJECT_NAME" not in source
    assert "procedures_executed" in source
    payload = json.loads(BANK_RECONCILIATION_SUMMARY_SQL_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_DEFINITION_IN_MEMORY_REDACTED_FORMULA_PARSE",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_definitions_persisted": 0,
        "non_allowlisted_string_literals_persisted": 0,
        "procedures_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    assert payload["summary"] == {
        "catalog_object_count": 1,
        "parameter_count": 14,
        "dependency_count": 6,
        "output_metric_count": 11,
        "formula_pattern_count": 13,
        "matched_formula_pattern_count": 13,
        "cardex_type_predicate_count": 6,
        "type_literal_alias_risk_count": 2,
        "lexical_mutation_keyword_count": 0,
        "definition_length": 3070,
        "definition_persisted_count": 0,
        "allowlisted_domain_literal_value_count": 6,
        "business_row_value_read_count": 0,
        "procedure_execution_count": 0,
        "validation_error_count": 0,
    }
    assert all(payload["formula_pattern_checks"].values())
    assert [row["metric"] for row in payload["formulas"]] == [
        "RemainingLastReconcile",
        "RemainingThisPeriod",
        "RemainingBill",
        "RemainingCardex",
        "BillDebitOpenItems",
        "BillCreditOpenItems",
        "CardexDebitOpenItems",
        "CardexCreditOpenItems",
        "RealRemainingBill",
        "RealRemainingCardex",
        "Reconcile",
    ]
    assert payload["cardex_type_status_predicates"] == [
        {"type": "RCHEQUE", "required_status_id": 3},
        {"type": "RBANKDARFT", "required_status_id": 1},
        {"type": "PCHEQUE", "required_status_id": 3},
        {"type": "TRANSFER", "required_status_id": None},
        {"type": "PWITHDRAW", "required_status_id": None},
        {"type": "RCASHDRAF", "required_status_id": None},
    ]
    assert payload["type_literal_alias_risks"] == [
        {
            "summary_literal": "RBANKDARFT",
            "matching_discriminator": "RBANKDRAFT",
            "status_id": 1,
        },
        {
            "summary_literal": "RCASHDRAF",
            "matching_discriminator": "RCASHDRAFT",
            "status_id": None,
        },
    ]
    target = payload["target_contract"]
    assert target["static_formula_semantics_confirmed_from_clone_definition"] is True
    assert target["misspelled_type_literals_are_silently_corrected"] is False
    assert target["runtime_row_result_parity_confirmed"] is False
    assert target["command_pilot_allowed"] is False


def test_bank_statement_parser_row_contract_exposes_unsafe_profile_dedup_and_partial_commit() -> None:
    source = BANK_STATEMENT_PARSER_ROW_EXTRACTOR.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "OleDbConnection(" not in source
    payload = json.loads(BANK_STATEMENT_PARSER_ROW_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "ALLOWLISTED_STATIC_IL_AND_VALIDATED_ARTIFACT_COMPOSITION",
        "assemblies_loaded_or_executed": 0,
        "forms_or_office_automation_invoked": 0,
        "files_opened_by_legacy_parser": 0,
        "database_connections": 0,
        "source_or_target_commands_executed": 0,
        "business_row_values_read": 0,
        "string_literal_values_persisted": 0,
    }
    assert payload["summary"] == {
        "selected_method_count": 4,
        "selected_instruction_count": 409,
        "format_dispatch_count": 4,
        "parser_count": 3,
        "canonical_input_column_count": 6,
        "row_to_entity_mapping_count": 6,
        "profile_sqlstatement_executing_parser_count": 2,
        "hardcoded_query_parser_count": 1,
        "parser_consuming_hdr_argument_count": 0,
        "forms_assembly_startrow_separator_isarabic_getter_call_count": 0,
        "legacy_duplicate_lookup_call_count": 2,
        "per_row_bankbill_update_call_site_count": 1,
        "assembly_hash_mismatch_count": 0,
        "string_literal_values_persisted_count": 0,
        "database_connection_count": 0,
        "validation_error_count": 0,
    }
    parsers = {row["method"]: row for row in payload["parser_contracts"]}
    assert parsers["getDataFromDBF"]["query_mode"] == "PROFILE_SQLSTATEMENT_EXECUTED"
    assert parsers["getDataFromTXT"]["query_mode"] == "PROFILE_SQLSTATEMENT_EXECUTED"
    assert parsers["getDataFromXLS"]["query_mode"] == "HARDCODED_SHEET1_QUERY"
    assert all(row["hdr_argument_read_count"] == 0 for row in parsers.values())
    assert [row["input_column"] for row in payload["canonical_row_mapping"]] == [
        "Date",
        "Comment",
        "Debit",
        "Credit",
        "No1",
        "BaLance",
    ]
    assert payload["amount_branch"]["both_nonzero_behavior"] == "Credit is ignored because Debit branch wins"
    duplicate = payload["duplicate_contract"]
    assert duplicate["uses_string_concatenated_predicate"] is True
    assert duplicate["scoped_by_reconcile_id"] is False
    assert duplicate["scoped_by_bank_account_id"] is False
    assert duplicate["safe_or_complete_idempotency_key"] is False
    atomicity = payload["legacy_atomicity_contract"]
    assert atomicity["single_transaction_wraps_header_and_all_rows"] is False
    assert atomicity["parser_exception_can_leave_committed_header"] is True
    assert atomicity["later_row_failure_can_leave_prior_rows_committed"] is True
    target = payload["target_contract"]
    assert target["raw_profile_sql_statement_execution_allowed"] is False
    assert target["header_and_all_rows_commit_in_one_target_transaction"] is True
    assert target["parse_or_validation_failure_commits_nothing"] is True


def test_bank_reconciliation_confirm_cardex_exposes_one_link_early_return_defect() -> None:
    source = BANK_RECONCILIATION_CONFIRM_CARDEX_EXTRACTOR.read_text(encoding="utf-8")
    assert "cursor.execute(OBJECT_NAME" not in source
    payload = json.loads(
        BANK_RECONCILIATION_CONFIRM_CARDEX_ARTIFACT.read_text(encoding="utf-8")
    )
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_DEFINITION_IN_MEMORY_REDACTED_MUTATION_PARSE",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_definitions_persisted": 0,
        "string_literals_persisted": 0,
        "procedures_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    assert payload["summary"] == {
        "catalog_object_count": 1,
        "parameter_count": 2,
        "dependency_count": 9,
        "typed_update_branch_count": 6,
        "cursor_count": 1,
        "fetch_next_count": 2,
        "return_count": 12,
        "unordered_cursor_count": 1,
        "explicit_transaction_statement_count": 0,
        "maximum_typed_link_updates_per_execution": 1,
        "definition_length": 2442,
        "definition_persisted_count": 0,
        "business_row_value_read_count": 0,
        "procedure_execution_count": 0,
        "validation_error_count": 0,
    }
    assert [row["zero_row_error_code"] for row in payload["mutation_contracts"]] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert all(row["returns_after_zero_row"] for row in payload["mutation_contracts"])
    assert all(row["returns_after_success"] for row in payload["mutation_contracts"])
    defect = payload["early_return_defect"]
    assert defect["fetch_next_reached_after_any_typed_branch"] is False
    assert defect["maximum_typed_link_updates_per_execution"] == 1
    assert defect["which_link_is_processed_is_deterministic_when_multiple_links_exist"] is False
    target = payload["target_contract"]
    assert target["copy_cursor_or_early_return_behavior"] is False
    assert target["update_every_link_or_roll_back_everything"] is True
    assert target["legacy_result_parity_does_not_mean_reproducing_the_one_link_defect"] is True


def test_bank_reconciliation_confirm_orchestration_commits_markers_after_one_link_success() -> None:
    source = BANK_RECONCILIATION_CONFIRM_ORCHESTRATION_EXTRACTOR.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(
        BANK_RECONCILIATION_CONFIRM_ORCHESTRATION_ARTIFACT.read_text(encoding="utf-8")
    )
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "ALLOWLISTED_STATIC_IL_AND_VALIDATED_REDACTED_SEMANTICS",
        "assemblies_loaded_or_executed": 0,
        "forms_invoked": 0,
        "database_connections": 0,
        "source_or_target_commands_executed": 0,
        "business_row_values_read": 0,
        "non_allowlisted_string_literal_values_persisted": 0,
    }
    assert payload["summary"] == {
        "selected_method_count": 2,
        "selected_instruction_count": 129,
        "command_key_count": 4,
        "confirm_ordered_stage_count": 6,
        "confirm_commit_call_count": 1,
        "confirm_rollback_call_count": 2,
        "confirm_permission_or_operation_date_call_count": 0,
        "legacy_maximum_instrument_updates_before_success_commit": 1,
        "assembly_hash_mismatch_count": 0,
        "string_literal_values_persisted_count": 4,
        "non_allowlisted_string_literal_values_persisted_count": 0,
        "database_connection_count": 0,
        "validation_error_count": 0,
    }
    assert payload["command_dispatch"]["confirm_key"] == "Ok"
    assert payload["command_dispatch"]["closes_form_only_after_doaccept_true"] is True
    assert payload["confirm_success_path"] == [
        "Transaction.Start",
        "Reconcile.Amount=Decimal.Zero",
        "Reconcile.ConfirmerId=current AppUserId",
        "Reconcile.ConfirmDate=DateTime.Now",
        "Reconcile.Update",
        "ReconcileAdapter.UpdateBankAccountCardex(ReconcileId, out ErrorNo)",
        "if ErrorNo==0 Transaction.Commit and return true",
    ]
    auth = payload["authorization_boundary"]
    assert auth["detail_doaccept_permission_call_observed"] is False
    assert auth["detail_doaccept_operation_date_guard_call_observed"] is False
    combined = payload["combined_legacy_defect"]
    assert combined["outer_doaccept_commits_on_that_zero_error"] is True
    assert combined["confirmed_session_can_have_remaining_instruments_not_marked_reconciled"] is True
    assert combined["legacy_amount_zero_is_not_summary_result"] is True
    target = payload["target_contract"]
    assert target["all_links_are_validated_before_any_mutation"] is True
    assert target["any_missing_conflicting_or_failed_link_rolls_back_session_markers"] is True
    assert target["one_link_legacy_defect_is_a_regression_test_not_target_behavior"] is True


def test_bank_reconciliation_differential_acceptance_is_complete_unexecuted_and_separate_from_goldens() -> None:
    source = BANK_RECONCILIATION_DIFFERENTIAL_ACCEPTANCE_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(
        BANK_RECONCILIATION_DIFFERENTIAL_ACCEPTANCE_ARTIFACT.read_text(encoding="utf-8")
    )
    assert payload["validation"] == "PASS"
    assert payload["status"] == "DESIGN_ONLY_NOT_EXECUTED_OR_OWNER_APPROVED"
    assert payload["safety"] == {
        "mode": "OFFLINE_SYNTHETIC_DIFFERENTIAL_ACCEPTANCE_DESIGN",
        "database_connections": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_row_or_identity_values_used": 0,
        "synthetic_cases_only": 1,
    }
    assert payload["summary"] == {
        "source_artifact_count": 8,
        "summary_case_count": 38,
        "parser_case_count": 24,
        "confirm_case_count": 54,
        "differential_acceptance_case_count": 116,
        "legacy_redacted_fixture_case_count": 41,
        "owner_decision_case_count": 12,
        "failure_injection_case_count": 11,
        "authenticated_uat_case_count": 5,
        "executed_case_count": 0,
        "owner_approved_case_count": 0,
        "duplicate_case_id_count": 0,
        "validation_error_count": 0,
    }
    assert len(payload["cases"]) == 116
    assert len({row["case_id"] for row in payload["cases"]}) == 116
    assert all(row["execution_status"] == "NOT_EXECUTED" for row in payload["cases"])
    assert all(row["source_varanegar_mutation_allowed"] is False for row in payload["cases"])
    policy = payload["execution_policy"]
    assert policy["source_varanegar_is_read_only"] is True
    assert policy["these_cases_are_not_added_to_the_970_module_golden_mapping"] is True
    by_id = {row["case_id"]: row for row in payload["cases"]}
    assert by_id["confirm.regression.legacy_one_link_early_return"]["fixture"]["typed_link_count"] == 2
    assert by_id["parser.atomicity.mid_batch_failure"]["failure_injection_required"] is True
    assert by_id["summary.alias_risk.rbankdarft"]["owner_decision_required"] is True
    assert by_id["confirm.unmatch_reversal.unmatch_confirmed"]["expected"] == "deny unmatch and require owner-approved reversal"
    assert by_id["confirm.unmatch_reversal.reversal_authorization_denied"]["authenticated_uat_required"] is True
    assert by_id["confirm.unmatch_reversal.reversal_audit_failure"]["failure_injection_required"] is True
    assert by_id["confirm.discard_cancel.cancel_empty_header"]["owner_decision_required"] is True


def test_bank_reconciliation_owner_decisions_cover_every_flagged_case_without_inferred_approval() -> None:
    source = BANK_RECONCILIATION_OWNER_DECISION_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(BANK_RECONCILIATION_OWNER_DECISION_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["status"] == "DECISION_INPUT_READY_NOT_OWNER_APPROVED"
    assert payload["safety"] == {
        "mode": "OFFLINE_VALIDATED_ACCEPTANCE_OBLIGATION_COMPOSITION",
        "database_connections": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_identity_values_read": 0,
        "owner_approvals_inferred": 0,
    }
    assert payload["summary"] == {
        "owner_decision_case_count": 12,
        "decision_register_count": 7,
        "mapped_case_count": 12,
        "recommended_safe_default_count": 7,
        "decision_with_partial_clone_evidence_count": 1,
        "approved_decision_count": 0,
        "unapproved_decision_count": 7,
        "database_connection_count": 0,
        "source_or_target_command_execution_count": 0,
        "validation_error_count": 0,
    }
    decisions = payload["decisions"]
    assert len(decisions) == 7
    assert len({case_id for row in decisions for case_id in row["case_ids"]}) == 12
    assert all(row["decision_status"] == "NOT_APPROVED" for row in decisions)
    assert all(row["selected_option_id"] is None for row in decisions)
    assert all(row["recommended_safe_default"] in {option["option_id"] for option in row["options"]} for row in decisions)
    alias_decision = next(row for row in decisions if row["decision_id"] == "BR-DEC-001")
    assert alias_decision["available_evidence"]["matching_literal_total_count"] == 146576
    assert alias_decision["available_evidence"]["short_literal_catalog_consumer_count"] == 2
    assert alias_decision["available_evidence"]["canonical_literal_catalog_consumer_count"] == 25
    assert alias_decision["available_evidence"]["alias_family_with_short_summary_outlier_count"] == 2
    assert alias_decision["available_evidence"]["owner_approval_inferred"] is False
    assert alias_decision["available_evidence"]["runtime_result_parity_proven"] is False
    assert payload["execution_rule"]["recommendation_is_not_approval"] is True
    assert payload["execution_rule"]["command_slice_remains_blocked_until_its_required_decisions_are_approved"] is True


def test_bank_statement_profile_target_contract_is_versioned_typed_and_not_implemented() -> None:
    source = BANK_STATEMENT_PROFILE_TARGET_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(BANK_STATEMENT_PROFILE_TARGET_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["status"] == "SCHEMA_AND_COMMAND_CONTRACT_READY_NOT_IMPLEMENTED_OR_OWNER_APPROVED"
    assert payload["safety"] == {
        "mode": "OFFLINE_VALIDATED_ARTIFACT_COMPOSITION",
        "database_connections": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_identity_values_read": 0,
        "owner_approvals_inferred": 0,
    }
    assert payload["summary"] == {
        "source_artifact_count": 3,
        "entity_count": 3,
        "field_count": 29,
        "invariant_count": 12,
        "command_contract_count": 4,
        "distinct_profile_capability_count": 2,
        "acceptance_obligation_count": 12,
        "approved_owner_decision_count": 0,
        "implementation_execution_count": 0,
        "validation_error_count": 0,
    }
    facts = payload["source_facts"]
    assert facts["legacy_profile_row_count_snapshot"] == 0
    assert facts["dormant_option_decision_status"] == "NOT_APPROVED"
    assert set(facts["canonical_columns"]) == {"Date", "Comment", "Debit", "Credit", "No1", "BaLance"}
    field_names = {field[0] for entity in payload["entities"] for field in entity["fields"]}
    assert not {"sql_statement", "provider", "connection_string", "file_path"} & field_names
    assert "raw SQL, provider names, connection strings, executable expressions and filesystem paths have no schema field" in payload["invariants"]


def test_bank_reconciliation_read_model_contract_preserves_signed_summary_and_scope() -> None:
    source = BANK_RECONCILIATION_READ_MODEL_TARGET_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(BANK_RECONCILIATION_READ_MODEL_TARGET_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["status"] == "READ_MODEL_CONTRACT_READY_NOT_IMPLEMENTED_OR_RUNTIME_PARITY_APPROVED"
    assert payload["summary"] == {
        "source_artifact_count": 5,
        "projection_count": 4,
        "projection_field_count": 44,
        "query_contract_count": 5,
        "summary_metric_count": 11,
        "typed_source_mapping_count": 6,
        "acceptance_obligation_count": 16,
        "runtime_parity_approved_count": 0,
        "query_implementation_execution_count": 0,
        "validation_error_count": 0,
    }
    assert len(payload["summary_formula_contracts"]) == 11
    assert len(payload["summary_presentation_mappings"]) == 11
    assert payload["alias_decision_gate"] == {
        "decision_id": "BR-DEC-001",
        "status": "NOT_APPROVED",
        "silent_normalization_allowed": False,
    }
    assert all("bank_account_id" in row["required_scope"] for row in payload["query_contracts"])
    assert payload["authorization_contract"]["deny_overrides_allow"] is True


def test_bank_statement_staging_contract_is_isolated_atomic_and_unimplemented() -> None:
    source = BANK_STATEMENT_STAGING_TARGET_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(BANK_STATEMENT_STAGING_TARGET_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["status"] == "STAGING_CONTRACT_READY_NOT_IMPLEMENTED_OR_OWNER_APPROVED"
    assert payload["summary"] == {
        "source_artifact_count": 5,
        "entity_count": 4,
        "field_count": 40,
        "state_count": 8,
        "pipeline_stage_count": 8,
        "invariant_count": 14,
        "command_contract_count": 6,
        "acceptance_obligation_count": 16,
        "approved_parser_owner_decision_count": 0,
        "implementation_execution_count": 0,
        "validation_error_count": 0,
    }
    assert payload["source_facts"]["legacy_profile_sql_executing_parser_count"] == 2
    assert payload["source_facts"]["legacy_parser_consuming_hdr_count"] == 0
    assert set(payload["source_facts"]["parser_decision_statuses"].values()) == {"NOT_APPROVED"}
    assert "no reconciliation session header is created before successful explicit commit" in payload["invariants"]
    assert "mid-commit failure rolls back header, rows, audit and outbox" in payload["acceptance_obligations"]


def test_bank_reconciliation_state_machine_separates_lifecycle_from_match_progress() -> None:
    source = BANK_RECONCILIATION_STATE_MACHINE_TARGET_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(BANK_RECONCILIATION_STATE_MACHINE_TARGET_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["status"] == "STATE_CONTRACT_READY_COMMANDS_NOT_IMPLEMENTED_OR_OWNER_APPROVED"
    assert payload["summary"] == {
        "source_artifact_count": 8,
        "lifecycle_state_count": 5,
        "computed_progress_value_count": 4,
        "transition_contract_count": 7,
        "distinct_transition_capability_count": 7,
        "invariant_count": 14,
        "acceptance_obligation_count": 18,
        "approved_cancel_or_reverse_decision_count": 0,
        "implemented_transition_count": 0,
        "validation_error_count": 0,
    }
    states = {row["state"] for row in payload["lifecycle_states"]}
    assert states == {"OPEN_UNCONFIRMED", "CONFIRMED", "CANCELLED", "REVERSED", "QUARANTINED"}
    transitions = {row["command"]: row for row in payload["transition_contracts"]}
    assert transitions["MatchInstrument"]["from"] == transitions["MatchInstrument"]["to"] == "OPEN_UNCONFIRMED"
    assert transitions["ReverseConfirmedSession"]["capability"] == "bank_reconciliation.reverse_confirmed_session"
    assert payload["decision_gates"]["BR-DEC-006"]["status"] == "NOT_APPROVED"
    assert payload["decision_gates"]["BR-DEC-007"]["recommendation_is_approval"] is False


def test_bank_reconciliation_command_envelope_is_atomic_stable_and_blocked() -> None:
    source = BANK_RECONCILIATION_COMMAND_ENVELOPE_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(BANK_RECONCILIATION_COMMAND_ENVELOPE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["status"] == "COMMAND_ENVELOPE_READY_COMMANDS_BLOCKED_NOT_IMPLEMENTED"
    assert payload["summary"] == {
        "source_artifact_count": 6,
        "command_contract_count": 5,
        "distinct_capability_count": 5,
        "common_request_field_count": 10,
        "common_guard_stage_count": 10,
        "common_response_field_count": 9,
        "stable_error_code_count": 11,
        "invariant_count": 12,
        "implemented_command_count": 0,
        "executed_acceptance_case_count": 0,
        "validation_error_count": 0,
    }
    assert payload["common_guard_order"][0] == "authenticate actor"
    assert payload["common_guard_order"][-1] == "commit once and return a stable result envelope"
    commands = {row["command"]: row for row in payload["command_contracts"]}
    assert commands["UnmatchInstrument"]["specific_request_fields"] == ["link_id"]
    assert commands["ReverseConfirmedSession"]["capability"] == "bank_reconciliation.reverse_confirmed_session"
    assert payload["implementation_gate"]["all_five_commands_allowed_now"] is False
    assert payload["implementation_gate"]["source_varanegar_remains_read_only"] is True


def test_bank_reconciliation_authenticated_uat_runbook_uses_slots_not_identities() -> None:
    source = BANK_RECONCILIATION_AUTHENTICATED_UAT_RUNBOOK_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(
        BANK_RECONCILIATION_AUTHENTICATED_UAT_RUNBOOK_ARTIFACT.read_text(encoding="utf-8")
    )
    assert payload["validation"] == "PASS"
    assert payload["status"] == "RUNBOOK_READY_TEST_ACCOUNTS_NOT_PROVISIONED_UAT_NOT_EXECUTED"
    assert payload["summary"] == {
        "source_artifact_count": 4,
        "principal_slot_count": 7,
        "role_template_count": 6,
        "capability_count": 7,
        "fixture_slot_count": 15,
        "prerequisite_count": 9,
        "execution_wave_count": 5,
        "covered_uat_case_count": 100,
        "evidence_field_count": 13,
        "forbidden_evidence_class_count": 5,
        "stop_condition_count": 6,
        "provisioned_test_account_count": 0,
        "executed_case_count": 0,
        "passed_case_count": 0,
        "owner_approved_expected_result_count": 0,
        "validation_error_count": 0,
    }
    assert sum(row["case_count"] for row in payload["execution_waves"]) == 100
    assert all("slot" in row and "role_template" in row for row in payload["principal_slots"])
    assert payload["execution_policy"]["project_artifacts_store_slot_not_identity"] is True
    assert payload["execution_policy"]["source_varanegar_and_ngt_remain_read_only"] is True


def test_bank_reconciliation_evidence_request_pack_is_least_privilege_and_grants_nothing() -> None:
    source = BANK_RECONCILIATION_EVIDENCE_REQUEST_PACK_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(BANK_RECONCILIATION_EVIDENCE_REQUEST_PACK_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["status"] == "REQUEST_PACK_READY_NO_NEW_ACCESS_OR_EVIDENCE_GRANTED"
    assert payload["summary"] == {
        "source_artifact_count": 5,
        "request_count": 9,
        "priority_1_request_count": 3,
        "priority_2_request_count": 3,
        "priority_3_request_count": 3,
        "distinct_owner_role_count": 9,
        "current_satisfied_request_count": 0,
        "new_access_grant_count": 0,
        "owner_approval_count": 0,
        "validation_error_count": 0,
    }
    requests = {row["request_id"]: row for row in payload["requests"]}
    assert requests["BR-EVID-001"]["minimum_access"].endswith("explicit write deny")
    assert "production credential" in requests["BR-EVID-001"]["forbidden"]
    assert requests["BR-EVID-006"]["minimum_access"].startswith("write only to disposable target UAT database")
    assert payload["safety"]["access_grants_or_owner_approvals_created"] == 0
    assert set(payload["blocker_zero_snapshot"].values()) == {0}


def test_bank_reconciliation_unmatch_deletes_all_bill_links_without_instrument_reset() -> None:
    source = BANK_RECONCILIATION_UNMATCH_SQL_EXTRACTOR.read_text(encoding="utf-8")
    assert "cursor.execute(OBJECT_NAME" not in source
    payload = json.loads(BANK_RECONCILIATION_UNMATCH_SQL_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_DEFINITION_IN_MEMORY_REDACTED_DELETE_PARSE",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_definitions_persisted": 0,
        "string_literals_persisted": 0,
        "procedures_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    assert payload["summary"] == {
        "catalog_object_count": 1,
        "parameter_count": 2,
        "dependency_count": 1,
        "delete_statement_count": 1,
        "instrument_update_statement_count": 0,
        "bank_bill_scope_column_count": 1,
        "link_id_scope_column_count": 0,
        "reconcile_or_account_scope_column_count": 0,
        "explicit_transaction_statement_count": 0,
        "definition_length": 269,
        "definition_persisted_count": 0,
        "business_row_value_read_count": 0,
        "procedure_execution_count": 0,
        "validation_error_count": 0,
    }
    delete = payload["delete_contract"]
    assert delete["deletes_one_specific_reconcile_item_by_link_id"] is False
    assert delete["deletes_all_reconcile_items_for_bank_bill"] is True
    assert payload["missing_side_effects"]["instrument_is_reconciled_reset"] is False
    risk = payload["confirmed_state_risk"]
    assert risk["link_delete_can_leave_instrument_is_reconciled_true"] is True
    assert risk["reverse_confirmed_session_is_equivalent_to_this_delete"] is False
    target = payload["target_contract"]
    assert target["unmatch_allowed_state"] == "IMPORTED_UNCONFIRMED"
    assert target["unmatch_uses_link_id_and_expected_version"] is True
    assert target["confirmed_session_uses_separate_owner_approved_reversal"] is True


def test_bank_reconciliation_discard_removes_rows_but_not_session_header() -> None:
    source = BANK_RECONCILIATION_DISCARD_CANCEL_EXTRACTOR.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(
        BANK_RECONCILIATION_DISCARD_CANCEL_ARTIFACT.read_text(encoding="utf-8")
    )
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "ALLOWLISTED_STATIC_IL_AND_VALIDATED_ARTIFACT_COMPOSITION",
        "assemblies_loaded_or_executed": 0,
        "forms_invoked": 0,
        "database_connections": 0,
        "source_or_target_commands_executed": 0,
        "business_row_values_read": 0,
        "string_literal_values_persisted": 0,
    }
    assert payload["summary"] == {
        "selected_method_count": 2,
        "selected_instruction_count": 90,
        "discard_link_check_call_count": 1,
        "discard_bank_bill_collection_delete_call_count": 1,
        "discard_reconcile_header_mutation_call_count": 0,
        "discard_permission_date_or_confirm_state_call_count": 0,
        "save_header_update_call_count": 1,
        "assembly_hash_mismatch_count": 0,
        "string_literal_value_persisted_count": 0,
        "database_connection_count": 0,
        "validation_error_count": 0,
    }
    discard = payload["discard_contract"]
    assert discard["active_link_count_greater_than_zero_blocks_discard"] is True
    assert discard["deletes_and_updates_bank_bill_collection"] is True
    assert discard["deletes_or_cancels_reconcile_header"] is False
    orphan = payload["orphan_header_risk"]
    assert orphan["parser_failure_can_follow_committed_header"] is True
    assert orphan["empty_reconcile_header_can_remain_after_failure_or_discard"] is True
    assert orphan["distinct_legacy_cancel_session_command_observed"] is False
    target = payload["target_contract"]
    assert target["discard_imported_statement_and_cancel_session_are_same_command"] is False
    assert target["unconfirmed_cancel_transitions_or_archives_header_and_rows_atomically"] is True
    assert target["confirmed_session_physical_delete_allowed"] is False


def test_bank_reconciliation_implementation_readiness_separates_static_knowledge_from_execution() -> None:
    source = BANK_RECONCILIATION_IMPLEMENTATION_READINESS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    assert "pyodbc" not in source.casefold()
    payload = json.loads(
        BANK_RECONCILIATION_IMPLEMENTATION_READINESS_ARTIFACT.read_text(encoding="utf-8")
    )
    assert payload["validation"] == "PASS"
    assert payload["status"] == "DESIGN_READY_FOR_FIRST_THREE_READ_SIDE_SLICES_NOT_READY_FOR_COMMAND_PILOT"
    assert payload["safety"] == {
        "mode": "OFFLINE_VALIDATED_ARTIFACT_COMPOSITION",
        "database_connections": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_row_values_read": 0,
        "identity_or_membership_values_read": 0,
    }
    assert payload["summary"] == {
        "input_artifact_count": 30,
        "validated_input_artifact_count": 30,
        "readiness_dimension_count": 9,
        "static_method_contract_count": 58,
        "source_contract_table_count": 15,
        "typed_match_reference_mapping_count": 6,
        "summary_parameter_count": 14,
        "summary_output_to_ui_mapping_count": 11,
        "summary_static_formula_metric_count": 11,
        "summary_type_literal_alias_risk_count": 2,
        "clone_type_alias_pair_with_observed_count_difference_count": 1,
        "clone_alias_summary_literal_total_count": 0,
        "clone_alias_matching_literal_total_count": 146576,
        "clone_short_literal_catalog_consumer_count": 2,
        "clone_canonical_literal_catalog_consumer_count": 25,
        "clone_alias_family_with_short_summary_outlier_count": 2,
        "parser_canonical_input_column_count": 6,
        "legacy_profile_sqlstatement_executing_parser_count": 2,
        "legacy_parser_consuming_hdr_argument_count": 0,
        "legacy_confirm_maximum_typed_link_updates_per_execution": 1,
        "legacy_confirm_unordered_cursor_count": 1,
        "legacy_confirm_permission_or_operation_date_call_count": 0,
        "differential_acceptance_case_count": 116,
        "executed_differential_acceptance_case_count": 0,
        "owner_decision_register_count": 7,
        "approved_owner_decision_count": 0,
        "profile_target_entity_count": 3,
        "profile_target_command_contract_count": 4,
        "read_model_target_projection_count": 4,
        "read_model_target_query_contract_count": 5,
        "staging_target_entity_count": 4,
        "staging_target_pipeline_stage_count": 8,
        "state_machine_target_state_count": 5,
        "state_machine_target_transition_count": 7,
        "command_envelope_target_command_count": 5,
        "command_envelope_stable_error_count": 11,
        "authenticated_uat_runbook_case_count": 100,
        "provisioned_uat_test_account_count": 0,
        "legacy_unmatch_link_id_scope_column_count": 0,
        "legacy_unmatch_instrument_update_statement_count": 0,
        "legacy_discard_reconcile_header_mutation_call_count": 0,
        "current_clone_runtime_fixture_available_count": 0,
        "synthetic_golden_case_count": 93,
        "identity_free_uat_case_count": 100,
        "real_profile_row_snapshot_count": 0,
        "authenticated_uat_execution_count": 0,
        "owner_approved_case_count": 0,
        "resolved_root_count": 0,
        "target_command_execution_count": 0,
        "implementation_slice_count": 6,
        "currently_allowed_implementation_slice_count": 3,
        "hard_pilot_gate_count": 8,
        "validation_error_count": 0,
    }
    decision = payload["readiness_decision"]
    assert decision["start_target_schema_and_read_only_profile_catalog"] is True
    assert decision["start_isolated_parser_staging"] is True
    assert decision["start_session_read_model_summary_candidate"] is True
    assert decision["start_match_unmatch_confirm_commands"] is False
    assert decision["start_pilot"] is False
    assert decision["start_production"] is False
    assert [row["allowed_now"] for row in payload["ordered_implementation_slices"]] == [
        True,
        True,
        True,
        False,
        False,
        False,
    ]
    assert len(payload["hard_pilot_gates"]) == 8
    assert len(payload["definition_of_done"]) == 8
    assert all(row["validation"] == "PASS" for row in payload["source_evidence"])


def test_bank_reconciliation_integrity_snapshot_is_aggregate_only_and_not_runtime_parity() -> None:
    source = BANK_RECONCILIATION_INTEGRITY_AGGREGATES_EXTRACTOR.read_text(encoding="utf-8")
    assert "SELECT TOP" not in source.upper()
    payload = json.loads(
        BANK_RECONCILIATION_INTEGRITY_AGGREGATES_ARTIFACT.read_text(encoding="utf-8")
    )
    assert payload["validation"] == "PASS"
    assert payload["status"] == "NO_RUNTIME_PARITY_FIXTURE_IN_CURRENT_CLONE"
    assert payload["safety"] == {
        "mode": "READ_ONLY_PRIVACY_SAFE_COUNT_AND_SUM_AGGREGATES",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "row_identifiers_dates_amounts_comments_files_or_user_values_persisted": 0,
        "aggregate_counts_only": 1,
        "procedures_or_application_commands_executed": 0,
        "live_ui_actions": 0,
    }
    assert payload["summary"] == {
        "counted_table_count": 7,
        "session_count": 0,
        "bank_bill_count": 0,
        "reconcile_item_count": 0,
        "profile_row_count": 0,
        "typed_instrument_family_count": 6,
        "bank_bill_with_multiple_links_count": 0,
        "confirmed_session_with_multiple_links_count": 0,
        "partial_marker_count": 0,
        "confirmed_session_instrument_not_reconciled_count": 0,
        "unconfirmed_session_instrument_reconciled_count": 0,
        "runtime_fixture_available_count": 0,
        "row_identifier_or_business_value_persisted_count": 0,
        "source_command_execution_count": 0,
        "validation_error_count": 0,
    }
    assert payload["interpretation"]["zero_current_counts_prove_no_production_issue"] is False
    assert payload["interpretation"]["current_clone_can_measure_legacy_defect_frequency"] is False
    assert payload["interpretation"]["fresh_owner_approved_redacted_snapshot_required_for_parity"] is True


def test_bank_reconciliation_type_alias_snapshot_is_aggregate_only_and_blocks_silent_normalization() -> None:
    source = BANK_RECONCILIATION_TYPE_ALIAS_AGGREGATES_EXTRACTOR.read_text(encoding="utf-8")
    assert "SELECT TOP" not in source.upper()
    assert "COUNT_BIG(*)" in source
    payload = json.loads(
        BANK_RECONCILIATION_TYPE_ALIAS_AGGREGATES_ARTIFACT.read_text(encoding="utf-8")
    )
    assert payload["validation"] == "PASS"
    assert payload["safety"]["mode"] == "READ_ONLY_PRE_ALLOWLISTED_LITERAL_COUNTS_AND_CATALOG_CONSUMERS"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["procedures_or_application_commands_executed"] == 0
    assert payload["summary"] == {
        "bank_account_cardex_row_count": 192106,
        "alias_pair_literal_row_count": 146576,
        "known_summary_or_matching_literal_row_count": 192083,
        "other_type_row_count": 23,
        "summary_predicate_eligible_row_count": 45454,
        "canonical_alias_alternative_eligible_row_count": 146576,
        "status_excluded_known_literal_row_count": 53,
        "summary_predicate_eligible_share_basis_points": 2366,
        "canonical_alias_alternative_share_basis_points": 7630,
        "short_literal_catalog_consumer_count": 2,
        "canonical_literal_catalog_consumer_count": 25,
        "catalog_consumer_with_both_literals_count": 0,
        "alias_family_with_short_summary_outlier_count": 2,
        "alias_pair_count": 2,
        "pair_with_observed_count_difference_count": 1,
        "summary_literal_total_count": 0,
        "matching_literal_total_count": 146576,
        "row_identifier_or_business_value_persisted_count": 0,
        "source_command_execution_count": 0,
        "validation_error_count": 0,
    }
    aliases = {row["summary_literal"]: row for row in payload["alias_aggregates"]}
    assert aliases["RCASHDRAF"]["summary_literal_count"] == 0
    assert aliases["RCASHDRAF"]["matching_literal_count"] == 146576
    assert payload["interpretation"]["observed_counts_make_silent_normalization_safe"] is False
    assert payload["interpretation"]["owner_decision_and_redacted_summary_parity_fixture_still_required"] is True
    predicates = {row["summary_literal"]: row for row in payload["summary_predicate_aggregates"]}
    assert predicates["PCHEQUE"]["predicate_eligible_row_count"] == 3637
    assert predicates["RCHEQUE"]["status_excluded_row_count"] == 53
    consumers = {
        (row["alias_family"], row["object_name"]): row
        for row in payload["catalog_literal_consumers"]
    }
    for family in ("RCASH_DRAFT", "RBANK_DRAFT"):
        assert consumers[(family, "DoReconcile_GetSummary")]["uses_short_summary_literal"] == 1
        assert consumers[(family, "DoReconcile_GetSummary")]["uses_canonical_literal"] == 0
    assert payload["interpretation"]["short_literal_isolated_to_summary_in_clone_catalog"] is True


def test_bank_reconciliation_permission_aliases_are_coarse_and_identity_free() -> None:
    source = BANK_RECONCILIATION_PERMISSION_CATALOG_EXTRACTOR.read_text(encoding="utf-8")
    assert "aggregate_effective_active_user_counts" in source
    assert '"app_user_id"' not in source
    assert '"user_group_id"' not in source
    payload = json.loads(BANK_RECONCILIATION_PERMISSION_CATALOG_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["denies_data_writes"] is True
    assert payload["safety"]["user_group_or_membership_identity_values_persisted"] == 0
    assert payload["safety"]["identities_processed_transiently_for_aggregate_effective_counts"] == 1
    assert payload["safety"]["individual_right_rows_persisted"] == 0
    assert payload["summary"] == {
        "observed_il_alias_count": 2,
        "catalog_alias_root_count": 2,
        "catalog_child_node_count": 7,
        "aggregate_assignment_bucket_count": 36,
        "effective_node_count": 9,
        "active_user_count_per_node": 141,
        "admin_bypass_count_per_node": 7,
        "effective_allow_count_min": 18,
        "effective_allow_count_max": 27,
        "direct_allow_assignment_count": 63,
        "group_allow_assignment_count": 22,
        "deny_assignment_count": 0,
        "validation_error_count": 0,
    }
    aliases = {row["legacy_alias"]: row for row in payload["alias_contracts"]}
    assert aliases["TransferList"]["child_keys"] == ["AddNew", "Delete", "Edit", "View"]
    assert aliases["ReconciliationSetup"]["child_keys"] == ["Delete", "Edit", "View"]
    assert all(row["parent_access_node_key"] == "OtherOperation" for row in aliases.values())
    assert all(row["has_dedicated_confirm_child"] is False for row in aliases.values())
    effective = payload["effective_permission_contract"]
    assert effective["deny_overrides_allow"] is True
    assert effective["neutral_is_not_allow"] is True
    assert effective["current_user_or_role_effective_permission_computed"] is False
    assert effective["aggregate_active_user_effective_counts_computed"] is True
    counts = {row["access_node_id"]: row for row in payload["aggregate_effective_active_user_counts"]}
    assert {row["active_user_count"] for row in counts.values()} == {141}
    assert {row["admin_bypass_count"] for row in counts.values()} == {7}
    assert {row["effective_allow_count"] for row in counts.values()} == {18, 27}
    assert {row["explicit_deny_count"] for row in counts.values()} == {0}
    target = payload["target_contract"]
    assert target["legacy_aliases_are_target_capability_names"] is False
    assert target["legacy_edit_implies_confirm"] is False
    assert "bank_reconciliation.confirm" in target["distinct_capabilities_required"]


def test_bank_reconciliation_delete_surfaces_do_not_imply_session_cancel() -> None:
    source = BANK_RECONCILIATION_DELETE_SEMANTICS_EXTRACTOR.read_text(encoding="utf-8")
    assert "sys.sql_modules" not in source
    payload = json.loads(BANK_RECONCILIATION_DELETE_SEMANTICS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["denies_data_writes"] is True
    assert payload["safety"]["module_definitions_or_business_rows_read_or_persisted"] == 0
    assert payload["summary"] == {
        "legacy_delete_surface_count": 2,
        "unmatch_procedure_count": 1,
        "unmatch_parameter_count": 2,
        "unmatch_dependency_count": 1,
        "session_cancel_legacy_command_observed_count": 0,
        "validation_error_count": 0,
    }
    surfaces = {row["form_type"]: row for row in payload["legacy_delete_surfaces"]}
    assert surfaces["TreasuryOld.Forms.frmReconciliation"]["semantic_classification"] == "UNMATCH_ONE_RECONCILIATION_LINK"
    assert surfaces["TreasuryOld.Forms.frmReconciliation"]["explicit_ui_transaction_observed"] is True
    setup = surfaces["TreasuryOld.Forms.frmReconciliationSetup"]
    assert setup["semantic_classification"] == "DISCARD_IMPORTED_BANK_STATEMENT_ROWS_AFTER_LINK_CHECK"
    assert setup["reconcile_header_mutation_call_observed"] is False
    procedure = payload["unmatch_procedure"]
    assert [(row["name"], row["data_type"], row["is_output"]) for row in procedure["parameters"]] == [
        ("@BankBillId", "int", False),
        ("@ErrorNo", "tinyint", True),
    ]
    assert {row["referenced_object"] for row in procedure["dependencies"]} == {"dbo.ReconcileItem"}
    target = payload["target_contract"]
    assert target["cancel_session_legacy_parity_status"] == "UNPROVEN_NO_DISTINCT_LEGACY_COMMAND_OBSERVED"
    assert target["golden_cancel_name_is_provisional_until_process_owner_signoff"] is True
    assert target["confirmed_session_requires_explicit_reversal_not_delete"] is True


def test_stack_recovery_input_is_evidence_backed_but_not_approved() -> None:
    source = STACK_RECOVERY_DECISION_BUILDER.read_text(encoding="utf-8")
    assert ".env" not in source
    assert "_connect(" not in source
    payload = json.loads(STACK_RECOVERY_DECISION_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["decision_status"] == "NEEDS_USER_DECISION_NOT_AN_APPROVED_ADR"
    assert payload["safety"] == {
        "mode": "OFFLINE_LOCAL_REPOSITORY_METADATA_AND_REDACTED_EVIDENCE",
        "environment_or_secret_files_read": 0,
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "production_stack_or_recovery_target_approved": 0,
    }
    assert payload["recommended_direction"]["status"] == "PROPOSAL_PENDING_USER_APPROVAL"
    assert payload["recommended_direction"]["architecture"] == "modular monolith first"
    assert "user decision" in payload["recommended_direction"]["database"]
    assert len(payload["user_decisions_required"]) == 6
    assert len(payload["recovery_target_options"]) == 3
    recommended = [row for row in payload["recovery_target_options"] if row["recommended"]]
    assert len(recommended) == 1
    assert recommended[0]["id"] == "B_STANDARD_BUSINESS"
    assert payload["evidence_checkpoint"]["needs_user_decision_backlog_ids"] == ["P0-001", "P0-021"]
    assert payload["evidence_checkpoint"]["estimated_total_weeks"] == [21, 33]
    assert payload["evidence_checkpoint"]["first_usable_read_only_slice_weeks"] == [3, 5]


def test_ui_checkpoint_has_no_semantic_drift_and_comparison_is_offline() -> None:
    source = UI_CHECKPOINT_COMPARISON_BUILDER.read_text(encoding="utf-8")
    assert "AutomationElement" not in source
    assert "_connect(" not in source
    checkpoint = json.loads(UI_CHECKPOINT_ARTIFACT.read_text(encoding="utf-8"))
    assert checkpoint["artifact"] == "varanegar_windows_ui_inventory"
    assert checkpoint["source"]["machine_ipv4"] == "192.168.1.184"
    payload = json.loads(UI_CHECKPOINT_COMPARISON_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["comparison_status"] == "NO_SEMANTIC_UI_DRIFT"
    assert payload["safety"] == {
        "mode": "OFFLINE_COMPARISON_OF_PERSISTED_READ_ONLY_UI_INVENTORIES",
        "live_ui_actions": 0,
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "business_values_or_control_text_added": 0,
    }
    assert payload["summary"]["compared_section_count"] == 6
    assert payload["summary"]["changed_section_count"] == 0
    assert payload["summary"]["baseline_observed_control_count"] == 76
    assert payload["summary"]["current_observed_control_count"] == 76


def test_ui_checkpoint_method_transition_is_explicit_not_release_drift() -> None:
    path = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_ui_checkpoint_comparison_20260827_0740.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["comparison_status"] == "OBSERVATION_METHOD_CHANGED"
    assert payload["summary"]["observation_method_changed"] is True
    assert payload["inputs"]["baseline_ui_automation_traversal"] == "LEGACY_DESCENDANTS"
    assert payload["inputs"]["current_ui_automation_traversal"] == "BOUNDED_BREADTH_FIRST_CHILDREN"
    assert payload["summary"]["changed_sections"] == [
        "source",
        "summary",
        "windows",
        "safe_named_controls",
    ]


def test_end_to_end_process_atlas_covers_workflows_reports_and_state_machines() -> None:
    source = END_TO_END_PROCESS_ATLAS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(END_TO_END_PROCESS_ATLAS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_REDACTED_PERSISTED_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
        "implementation_or_release_readiness_inferred": 0,
    }
    assert payload["summary"] == {
        "process_count": 10,
        "unique_workflow_surface_count": 20,
        "workflow_assignment_count": 20,
        "unique_report_surface_count": 20,
        "report_assignment_count": 36,
        "state_machine_count": 3,
        "state_machine_assignment_count": 3,
        "unique_golden_case_count": 877,
        "golden_case_assignment_count": 877,
        "unassigned_golden_case_count": 0,
        "process_with_target_golden_cases_count": 10,
        "process_with_critical_risk_count": 9,
        "implementation_ready_process_count": 0,
        "pilot_ready_process_count": 0,
        "production_ready_process_count": 0,
        "validation_error_count": 0,
    }
    assert all(len(owners) == 1 for owners in payload["coverage"]["workflow_assignments"].values())
    assert all(len(owners) >= 1 for owners in payload["coverage"]["report_assignments"].values())
    assert all(len(owners) == 1 for owners in payload["coverage"]["state_machine_assignments"].values())
    assert all(len(owners) == 1 for owners in payload["coverage"]["golden_case_assignments"].values())
    processes = {row["process_id"]: row for row in payload["processes"]}
    assert processes["P04_INVENTORY_TO_DELIVERY"]["state_machines"][0]["machine_id"] == "distribution"
    assert processes["P09_POS_SESSION_REPLICATION"]["target_golden_case_count"] == 70
    assert processes["P01_FOUNDATION_GOVERNANCE"]["target_golden_case_count"] == 119
    assert processes["P02_MASTER_AND_PRICING"]["target_golden_case_count"] == 196
    assert all(
        sum(row["target_golden_case_source_counts"].values())
        == row["target_golden_case_count"]
        for row in processes.values()
    )
    assert all(not row["implementation_ready"] for row in processes.values())


def test_report_target_contracts_split_reads_exports_prints_and_statement_writes() -> None:
    source = REPORT_TARGET_GOLDEN_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(REPORT_TARGET_GOLDEN_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_TARGET_DESIGN_FROM_REDACTED_STATIC_REPORT_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
        "legacy_report_or_print_execution_allowed": 0,
        "result_parity_uat_or_release_readiness_inferred": 0,
    }
    assert payload["summary"] == {
        "report_contract_count": 20,
        "query_surface_count": 20,
        "export_surface_count": 3,
        "print_completion_command_count": 3,
        "statement_command_count": 2,
        "golden_case_count": 175,
        "golden_case_category_counts": {
            "authorization": 28,
            "concurrency": 2,
            "export": 3,
            "fault_injection": 8,
            "filter_boundary": 16,
            "freshness": 20,
            "happy_path": 25,
            "idempotency": 8,
            "pagination": 20,
            "privacy": 20,
            "read_only": 5,
            "scope": 20,
        },
        "legacy_execution_allowed_count": 0,
        "result_parity_proven_contract_count": 0,
        "validation_error_count": 0,
    }
    assert all(contract["query_contract"]["read_only"] for contract in payload["contracts"])
    assert all(not contract["print_contract"]["preview_or_export_may_mark_completed"] for contract in payload["contracts"])
    assert all(not case["legacy_execution_allowed"] for case in payload["golden_cases"])
    print_contracts = [row for row in payload["contracts"] if row["print_contract"]["mark_print_completed_command"]]
    assert len(print_contracts) == 3
    assert all(row["print_contract"]["mark_command_requires_idempotency_and_expected_version"] for row in print_contracts)


def test_report_dependency_graph_is_static_complete_and_keeps_result_parity_open() -> None:
    source = REPORT_DEPENDENCY_GRAPH_EXTRACTOR.read_text(encoding="utf-8")
    assert "dnfile" in source
    payload = json.loads(REPORT_DEPENDENCY_GRAPH_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_COMPLETE_PACKAGE_METADATA_AND_TARGETED_IL_DEPENDENCY_TRACE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "config_or_resource_payloads_read": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    assert payload["summary"] == {
        "report_surface_count": 20,
        "first_party_ui_edge_count": 674,
        "ui_to_business_edge_count": 76,
        "business_target_type_count": 25,
        "business_target_method_body_count": 377,
        "direct_ui_to_data_access_edge_count": 13,
        "business_to_data_access_edge_count": 239,
        "data_access_target_type_count": 27,
        "data_access_target_method_body_count": 400,
        "report_with_business_to_data_access_path_count": 13,
        "report_with_direct_ui_to_data_access_path_count": 2,
        "report_with_any_direct_ui_to_data_access_coupling_count": 4,
        "report_without_one_hop_data_access_path_count": 5,
        "unresolved_first_party_like_call_type_count": 0,
        "targeted_method_body_error_count": 0,
        "source_hash_mismatch_count": 0,
        "metadata_failure_count": 0,
        "runtime_execution_or_result_parity_proven_count": 0,
        "validation_error_count": 0,
    }
    no_path = {row["report_type"] for row in payload["reports"] if row["static_query_path_status"] == "NO_DATA_ACCESS_PATH_IN_ONE_HOP_BUSINESS_TRACE"}
    assert no_path == {
        "VN.SDS.MainData.UI.Dashboard.PublicDashboard.FormMainDashboard",
        "VN.SDS.MainData.UI.Dashboard.PublicDashboard.MainUiDashboard.FormZoomChart",
        "VN.SDS.Sales.UI.PrintInvoice.FormPrintInvoice",
        "VN.SDS.Stock.UI.StockGoods.Reports.FormSelectGoodsType",
        "VN.SDS.Stock.UI.StockGoods.Reports.FormSelectMainReport",
    }
    assert all(not row["runtime_execution_or_result_parity_proven"] for row in payload["reports"])


def test_report_sql_candidates_are_catalog_only_and_never_execution_proof() -> None:
    source = REPORT_SQL_CANDIDATES_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    payload = json.loads(REPORT_SQL_CANDIDATES_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_METADATA_AND_DEFINITION_FINGERPRINTS_ONLY",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": 1,
        "business_row_values_read_or_persisted": 0,
        "module_definitions_or_string_literals_persisted": 0,
        "credentials_identity_grants_or_secrets_persisted": 0,
        "procedures_functions_views_or_triggers_executed": 0,
        "application_or_live_ui_actions": 0,
    }
    assert payload["summary"] == {
        "report_surface_count": 20,
        "data_access_search_term_count": 40,
        "term_with_candidate_count": 22,
        "term_without_candidate_count": 18,
        "term_truncated_at_cap_count": 10,
        "unique_candidate_object_count": 518,
        "candidate_table_count": 112,
        "candidate_module_count": 406,
        "report_with_candidate_count": 11,
        "report_without_candidate_count": 9,
        "definition_persisted_count": 0,
        "runtime_execution_or_result_parity_proven_count": 0,
        "validation_error_count": 0,
    }
    assert all(row["link_status"] != "EXECUTION_PROVEN" for row in payload["reports"])
    assert all("definition" not in row for row in payload["objects"])
    exact = {row["object"] for row in payload["objects"] if row["match_strength"] == "EXACT_NORMALIZED_NAME"}
    assert {"dbo.AccYear", "dbo.Customer", "dbo.Goods", "dbo.ProductionOrderItem", "dbo.ServerConfig", "dbo.Supplier"} <= exact


def test_report_method_paths_are_static_scoped_and_split_mutating_commands() -> None:
    source = REPORT_METHOD_PATHS_EXTRACTOR.read_text(encoding="utf-8")
    assert "dnfile" in source
    assert "subprocess" not in source
    payload = json.loads(REPORT_METHOD_PATHS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_COMPLETE_PACKAGE_TARGETED_METHOD_BODY_PARSE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_or_reports_executed": 0,
        "config_or_resource_payloads_read": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    assert payload["summary"] == {
        "report_surface_count": 20,
        "ui_type_count": 20,
        "ui_method_to_business_or_data_edge_count": 125,
        "called_business_type_count": 25,
        "scoped_business_method_to_data_edge_count": 62,
        "called_data_access_type_count": 16,
        "terminal_data_access_method_count": 47,
        "terminal_method_with_execution_signal_count": 26,
        "terminal_method_with_mutation_signal_count": 1,
        "direct_ui_to_data_access_terminal_edge_count": 23,
        "safe_static_literal_count": 21,
        "fingerprint_only_literal_count": 55,
        "unresolved_called_business_method_count": 0,
        "unresolved_called_data_method_count": 0,
        "targeted_method_body_error_count": 0,
        "source_hash_mismatch_count": 0,
        "metadata_failure_count": 0,
        "runtime_execution_or_result_parity_proven_count": 0,
        "validation_error_count": 0,
    }
    mutating = [row for row in payload["terminal_data_access_methods"] if row["mutation_calls"]]
    assert [(row["data_access_type"], row["method"]) for row in mutating] == [
        ("Thunderstruck.DataContext", "Commit")
    ]
    assert all(not row["runtime_execution_or_result_parity_proven"] for row in payload["reports"])


def test_report_gap_register_never_promotes_static_evidence_to_readiness() -> None:
    source = REPORT_EVIDENCE_GAPS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(REPORT_EVIDENCE_GAPS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_CROSSWALK_OF_REDACTED_STATIC_REPORT_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "legacy_reports_queries_or_commands_executed": 0,
        "business_rows_or_values_read_or_persisted": 0,
        "implementation_pilot_or_result_parity_inferred": 0,
    }
    summary = payload["summary"]
    assert summary["report_surface_count"] == 20
    assert summary["evidence_level_counts"] == {
        "L0_REPORT_SHELL_OR_UNRESOLVED_PATH": 7,
        "L1_TERMINAL_METHOD_PATH_ONLY": 3,
        "L2_TERMINAL_METHOD_EXECUTION_SIGNAL": 1,
        "L3_METHOD_EXECUTION_SIGNAL_PLUS_NAME_CANDIDATES": 9,
    }
    assert summary["report_with_terminal_method_path_count"] == 13
    assert summary["report_with_execution_signal_count"] == 10
    assert summary["report_with_sql_candidate_count"] == 11
    assert summary["report_with_direct_ui_data_access_count"] == 4
    assert summary["report_with_mutation_boundary_count"] == 2
    assert summary["result_parity_proven_count"] == 0
    assert summary["implementation_ready_count"] == 0
    assert summary["pilot_ready_count"] == 0
    assert all("RESULT_PARITY_MISSING" in row["gap_codes"] for row in payload["reports"])
    assert all(not row["implementation_ready"] and not row["pilot_ready"] for row in payload["reports"])


def test_report_shell_entrypoints_scan_complete_package_without_execution() -> None:
    source = REPORT_SHELL_ENTRYPOINTS_EXTRACTOR.read_text(encoding="utf-8")
    assert "dnfile" in source and "read_method_body_from_bytes" in source
    payload = json.loads(REPORT_SHELL_ENTRYPOINTS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_COMPLETE_PACKAGE_METADATA_AND_IL_ENTRYPOINT_SCAN",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_or_reports_executed": 0,
        "resource_payloads_or_config_files_read": 0,
        "raw_non_target_string_literals_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["target_report_shell_count"] == 7
    assert summary["assembly_count"] == 62
    assert summary["type_count"] == 7650
    assert summary["method_body_count"] == 81473
    assert summary["external_token_reference_count"] == 10
    assert summary["external_constructor_reference_count"] == 9
    assert summary["target_with_entrypoint_evidence_count"] == 4
    assert summary["target_without_entrypoint_evidence_count"] == 3
    assert summary["unexpected_method_body_error_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert summary["runtime_execution_or_result_parity_proven_count"] == 0
    resolved = {row["target_type"] for row in payload["resolutions"] if row["entrypoint_status"] == "CALLER_OR_DYNAMIC_ENTRYPOINT_FOUND"}
    assert "VN.SDS.MainData.UI.Dashboard.PublicDashboard.MainUiDashboard.FormZoomChart" in resolved
    assert "VN.SDS.Stock.UI.StockGoods.Reports.FormSelectMainReport" in resolved


def test_report_shell_caller_paths_preserve_generic_dispatch_gap() -> None:
    source = REPORT_SHELL_CALLER_PATHS_EXTRACTOR.read_text(encoding="utf-8")
    assert "_analyze_assembly" in source
    payload = json.loads(REPORT_SHELL_CALLER_PATHS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_COMPLETE_PACKAGE_TARGETED_CALLER_BUSINESS_DATAACCESS_IL_PARSE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_or_reports_executed": 0,
        "config_or_resource_payloads_read": 0,
        "raw_non_allowlisted_strings_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["report_shell_count"] == 7
    assert summary["discovered_caller_type_count"] == 8
    assert summary["caller_to_business_or_data_edge_count"] == 6
    assert summary["called_business_type_count"] == 5
    assert summary["scoped_business_to_data_edge_count"] == 0
    assert summary["terminal_data_access_method_count"] == 0
    assert summary["report_shell_with_data_access_path_count"] == 0
    assert summary["targeted_method_body_error_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert summary["runtime_execution_or_result_parity_proven_count"] == 0


def test_report_generic_bindings_capture_filters_without_claiming_sql_identity() -> None:
    source = REPORT_GENERIC_BINDINGS_EXTRACTOR.read_text(encoding="utf-8")
    assert "_analyze_assembly" in source
    payload = json.loads(REPORT_GENERIC_BINDINGS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    summary = payload["summary"]
    assert summary["report_shell_count"] == 7
    assert summary["caller_type_count"] == 8
    assert summary["caller_with_generic_query_binding_count"] == 2
    assert summary["unique_entity_helper_type_count"] == 5
    assert summary["unique_filter_member_count"] == 17
    assert summary["runtime_execution_sql_identity_or_result_parity_proven_count"] == 0
    filters = {item for row in payload["caller_contracts"] for item in row["filter_members"]}
    assert {"AccYear", "Date1", "Date2", "StockDCRef", "MounthId"} <= filters


def test_generic_report_sql_candidates_are_read_only_name_hints() -> None:
    source = REPORT_GENERIC_SQL_CANDIDATES_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    payload = json.loads(REPORT_GENERIC_SQL_CANDIDATES_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    summary = payload["summary"]
    assert summary["generic_binding_search_term_count"] == 32
    assert summary["unique_candidate_object_count"] == 201
    assert summary["report_shell_with_candidate_count"] == 4
    assert summary["definition_persisted_count"] == 0
    assert summary["sql_identity_execution_or_result_parity_proven_count"] == 0
    unique = {row["candidate_objects"][0] for row in payload["term_coverage"] if row["candidate_count"] == 1}
    assert {"GNR.uspReviewOrderPoints", "GNR.SaleAmountPerInterval", "GNR.TopDealerSales", "dbo.USP_SDSNET_SaleDashboard_GetList", "inv.UspRptCardexBatchNo6004"} == unique


def test_generic_report_sql_semantics_do_not_misclassify_temp_mutation_as_durable_write() -> None:
    source = REPORT_GENERIC_SQL_SEMANTICS_EXTRACTOR.read_text(encoding="utf-8")
    assert "dm_exec_describe_first_result_set_for_object" in source
    payload = json.loads(REPORT_GENERIC_SQL_SEMANTICS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    summary = payload["summary"]
    assert summary["selected_module_count"] == 5
    assert summary["stored_procedure_count"] == 5
    assert summary["parameter_count"] == 32
    assert summary["dependency_count"] == 32
    assert summary["module_with_mutation_token_count"] == 4
    assert summary["module_with_catalog_resolved_durable_mutation_target_count"] == 0
    assert summary["catalog_resolved_durable_mutation_target_count"] == 0
    assert summary["definition_persisted_count"] == 0
    assert summary["execution_or_result_parity_proven_count"] == 0
    assert all(not row["durable_mutation_targets"] for row in payload["modules"])


def test_role_uat_cases_are_identity_free_and_require_owner_signoff() -> None:
    source = ROLE_UAT_CASES_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(ROLE_UAT_CASES_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_CASE_GENERATION_FROM_IDENTITY_FREE_ROLE_TEMPLATES",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "named_identities_current_grants_or_assignments_read_or_persisted": 0,
        "production_role_assignment_or_authorization_granted": 0,
    }
    assert payload["summary"] == {
        "role_template_count": 15,
        "atomic_capability_count": 45,
        "allow_assignment_case_count": 75,
        "deny_pattern_case_count": 71,
        "context_invalidation_case_count": 15,
        "sod_case_count": 10,
        "mandatory_negative_case_count": 9,
        "non_inference_case_count": 4,
        "synthetic_uat_case_count": 184,
        "owner_approved_case_count": 0,
        "production_assignment_count": 0,
        "validation_error_count": 0,
    }
    assert all(not row["uses_named_identity_or_current_grant"] for row in payload["cases"])
    assert all(not row["production_assignment_or_approval"] for row in payload["cases"])
    assert payload["approval_gate"]["current_gate_status"] == "BLOCKED_BY_OWNER_SIGNOFF_AND_RUNTIME_UAT"


def test_data_entry_field_dictionary_keeps_field_binding_and_requiredness_unproven() -> None:
    source = DATA_ENTRY_FIELD_DICTIONARY_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(DATA_ENTRY_FIELD_DICTIONARY_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_REDACTED_TARGETED_IL",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "application_commands_executed": 0,
        "raw_non_allowlisted_strings_persisted": 0,
        "label_to_field_pairings_inferred": 0,
    }
    summary = payload["summary"]
    assert summary["selected_data_entry_form_count"] == 141
    assert summary["form_with_field_candidate_count"] == 93
    assert summary["form_without_field_candidate_count"] == 48
    assert summary["field_candidate_count"] == 581
    assert summary["unique_field_name_count"] == 350
    assert summary["safe_unpaired_ui_label_count"] == 1594
    assert summary["proven_required_or_nullable_field_count"] == 0
    assert summary["proven_data_binding_field_count"] == 0
    assert all(row["label_to_field_pairing_status"] == "NOT_INFERRED_FROM_LITERAL_ORDER" for row in payload["forms"])
    assert all(field["required_or_nullable_semantics"] == "UNPROVEN" for row in payload["forms"] for field in row["fields"])


def test_declared_field_metadata_expands_candidates_without_runtime_type_claims() -> None:
    source = DATA_ENTRY_DECLARED_FIELDS_EXTRACTOR.read_text(encoding="utf-8")
    assert "dnfile" in source
    payload = json.loads(DATA_ENTRY_DECLARED_FIELDS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_TARGETED_TYPE_AND_FIELD_METADATA_PARSE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "field_values_string_literals_resources_or_config_payloads_read_or_persisted": 0,
        "runtime_type_binding_or_requiredness_inferred": 0,
    }
    summary = payload["summary"]
    assert summary["selected_data_entry_form_count"] == 141
    assert summary["resolved_form_type_count"] == 141
    assert summary["form_with_declared_control_field_count"] == 95
    assert summary["form_without_declared_control_field_count"] == 46
    assert summary["declared_control_field_count"] == 813
    assert summary["unique_declared_field_name_count"] == 490
    assert summary["usage_enriched_field_count"] == 581
    assert summary["declared_only_field_count"] == 232
    assert summary["runtime_control_type_proven_count"] == 0
    assert summary["required_or_nullable_proven_count"] == 0
    assert summary["data_binding_proven_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert all(field["runtime_control_type"] == "UNPROVEN" for row in payload["forms"] for field in row["fields"])


def test_base_template_contracts_reclassify_local_field_gaps_without_runtime_claims() -> None:
    source = DATA_ENTRY_BASE_TEMPLATE_EXTRACTOR.read_text(encoding="utf-8")
    assert "_analyze_assembly" in source
    payload = json.loads(DATA_ENTRY_BASE_TEMPLATE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_HASH_VERIFIED_TARGETED_BASE_TEMPLATE_METADATA_AND_IL_PARSE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "field_values_resources_or_config_payloads_read_or_persisted": 0,
        "raw_string_literals_persisted": 0,
        "runtime_behavior_or_binding_inferred": 0,
    }
    summary = payload["summary"]
    assert summary["local_field_gap_form_count"] == 46
    assert summary["unique_base_template_count"] == 6
    assert summary["resolved_base_template_count"] == 6
    assert summary["base_template_declared_control_field_count"] == 43
    assert summary["base_template_method_body_count"] == 263
    assert summary["base_template_signaled_method_count"] == 104
    assert summary["form_reclassified_as_base_template_driven_count"] == 46
    assert summary["truly_fieldless_form_proven_count"] == 0
    assert summary["runtime_behavior_or_binding_proven_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert all(row["local_form_field_gap_interpretation"] == "BEHAVIOR_AND_CONTROLS_ARE_BASE_TEMPLATE_DRIVEN_NOT_FIELDLESS" for row in payload["base_templates"])


def test_field_signature_types_resolve_without_claiming_runtime_binding() -> None:
    source = DATA_ENTRY_FIELD_TYPES_EXTRACTOR.read_text(encoding="utf-8")
    assert "dnfile" in source and "_compressed" in source
    payload = json.loads(DATA_ENTRY_FIELD_TYPES_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_HASH_VERIFIED_FIELD_SIGNATURE_AND_TYPEDEF_TYPEREF_METADATA_PARSE",
        "assemblies_loaded_or_executed": 0,
        "database_connections": 0,
        "network_writes": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "field_values_string_literals_resources_or_config_payloads_read_or_persisted": 0,
        "runtime_instance_behavior_visibility_binding_or_requiredness_inferred": 0,
    }
    summary = payload["summary"]
    assert summary["selected_data_entry_form_count"] == 141
    assert summary["declared_field_candidate_count"] == 813
    assert summary["resolved_clr_field_type_count"] == 813
    assert summary["unresolved_clr_field_type_count"] == 0
    assert summary["unique_resolved_clr_type_count"] == 53
    assert summary["prefix_kind_match_count"] == 592
    assert summary["prefix_kind_mismatch_or_unclassified_count"] == 221
    assert summary["runtime_behavior_visibility_binding_or_requiredness_proven_count"] == 0
    assert summary["source_hash_mismatch_count"] == 0
    assert not payload["decode_failures"]
    top = {row["clr_field_type"]: row["field_count"] for row in payload["top_resolved_clr_types"]}
    assert top["System.Windows.Forms.Label"] == 171
    assert top["DevExpress.XtraEditors.TextEdit"] == 69


def test_field_binding_candidates_keep_method_cooccurrence_non_authoritative() -> None:
    source = DATA_ENTRY_FIELD_BINDING_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(DATA_ENTRY_FIELD_BINDING_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_METHOD_LEVEL_COOCCURRENCE_FROM_REDACTED_IL_AND_FIELD_TYPES",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "application_commands_executed": 0,
        "field_values_string_literals_or_business_rows_read_or_persisted": 0,
        "runtime_bindings_source_columns_or_query_parameters_inferred_as_proven": 0,
    }
    summary = payload["summary"]
    assert summary["selected_data_entry_form_count"] == 141
    assert summary["field_candidate_count"] == 813
    assert summary["field_with_strong_name_candidate_count"] == 78
    assert summary["field_with_singleton_method_candidate_count"] == 31
    assert summary["field_with_ambiguous_cooccurrence_count"] == 173
    assert summary["field_without_property_candidate_count"] == 531
    assert summary["unique_strong_name_property_call_count"] == 100
    assert summary["runtime_binding_proven_count"] == 0
    assert summary["source_column_or_query_parameter_proven_count"] == 0
    assert all(not field["runtime_binding_proven"] for row in payload["forms"] for field in row["fields"])


def test_field_sql_column_candidates_preserve_name_match_boundary() -> None:
    source = DATA_ENTRY_FIELD_SQL_COLUMNS_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    payload = json.loads(DATA_ENTRY_FIELD_SQL_COLUMNS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_COLUMN_KEY_AND_TYPE_METADATA_ONLY",
        "database_updateability": "READ_ONLY",
        "can_update": 0,
        "denies_data_writes": True,
        "business_row_values_module_definitions_or_string_literals_read_or_persisted": 0,
        "credentials_identities_grants_or_secrets_persisted": 0,
        "procedures_functions_views_triggers_or_application_commands_executed": 0,
        "live_ui_actions": 0,
        "runtime_binding_or_source_column_inferred_as_proven": 0,
    }
    summary = payload["summary"]
    assert summary["strong_static_field_count"] == 78
    assert summary["unique_property_call_count"] == 100
    assert summary["property_call_with_column_candidate_count"] == 85
    assert summary["property_call_without_column_candidate_count"] == 15
    assert summary["property_call_with_exact_entity_object_candidate_count"] == 28
    assert summary["field_with_column_candidate_count"] == 70
    assert summary["field_with_stronger_entity_object_candidate_count"] == 56
    assert summary["unique_candidate_column_count"] == 1331
    assert summary["property_candidate_truncated_at_cap_count"] == 17
    assert summary["runtime_binding_or_source_column_proven_count"] == 0
    assert all(not row["runtime_binding_or_source_column_proven"] for row in payload["fields"])
    exact_links = {
        (row["form_type"], row["field_name"], prop["property_name"], candidate["object"], candidate["column"])
        for row in payload["fields"]
        for prop in row["property_candidates"]
        for candidate in prop["candidate_column_details"]
        if candidate["match_strength"] == "ENTITY_OBJECT_EXACT_AND_COLUMN_EXACT"
    }
    assert len(exact_links) == 21
    assert (
        "TreasuryOld.Forms.frmRCashDraftEdit",
        "txtRCashDraftNo",
        "NotInsertDuplicateRCashDraftNo",
        "dbo.TRServerConfig",
        "NotInsertDuplicateRCashDraftNo",
    ) in exact_links


def test_treasury_edit_paths_expose_direct_ui_transaction_boundary() -> None:
    source = TREASURY_EDIT_COMMAND_PATHS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(TREASURY_EDIT_COMMAND_PATHS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["mode"] == "OFFLINE_DERIVATION_FROM_HASHED_REDACTED_DATA_ENTRY_IL"
    assert payload["safety"]["application_or_business_commands_executed"] == 0
    summary = payload["summary"]
    assert summary["target_form_count"] == 3
    assert summary["resolved_target_form_count"] == 3
    assert summary["target_method_body_count"] == 73
    assert summary["mutation_command_method_count"] == 3
    assert summary["validation_with_transaction_method_count"] == 1
    assert summary["method_with_direct_execute_non_query_count"] == 3
    assert summary["method_with_adapter_preupdate_count"] == 2
    assert summary["method_with_entity_update_count"] == 1
    assert summary["unique_entity_property_setter_count"] == 24
    assert summary["unique_referenced_form_field_count"] == 29
    assert summary["runtime_execution_success_idempotency_or_result_parity_proven_count"] == 0
    commands = [method for row in payload["contracts"] for method in row["selected_methods"] if method["classification"] == "MUTATION_COMMAND_STATIC_PATH"]
    assert {method["method"] for method in commands} == {"BtnOk_Click", "btnOk_Click"}
    assert all(method["transaction_signals"] for method in commands)


def test_treasury_source_model_keeps_writable_views_distinct_from_tables() -> None:
    source = TREASURY_EDIT_SOURCE_MODEL_EXTRACTOR.read_text(encoding="utf-8")
    assert "_assert_safe_target" in source
    payload = json.loads(TREASURY_EDIT_SOURCE_MODEL_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] is True
    summary = payload["summary"]
    assert summary["target_object_count"] == 8
    assert summary["resolved_object_count"] == 8
    assert summary["table_count"] == 6
    assert summary["column_count"] == 235
    assert summary["primary_key_column_count"] == 6
    assert summary["foreign_key_edge_observation_count"] == 75
    assert summary["trigger_count"] == 29
    assert summary["enabled_trigger_count"] == 29
    assert summary["referencing_module_observation_count"] == 804
    assert summary["business_row_values_or_module_definitions_persisted_count"] == 0
    objects = {row["object"]: row for row in payload["objects"]}
    assert objects["dbo.RCheque"]["object_type_desc"] == "VIEW"
    assert objects["dbo.RCashDraft"]["object_type_desc"] == "VIEW"
    assert objects["Acc.TblCheque"]["object_type_desc"] == "USER_TABLE"
    assert objects["Acc.TblBankOrders"]["object_type_desc"] == "USER_TABLE"
    for name in ("dbo.RCheque", "dbo.RCashDraft"):
        assert len(objects[name]["triggers"]) == 1
        assert objects[name]["triggers"][0]["is_instead_of"] is True
        assert set(objects[name]["triggers"][0]["events"]) == {"INSERT", "UPDATE", "DELETE"}


def test_treasury_trigger_semantics_resolve_two_view_bridges_without_execution() -> None:
    source = TREASURY_TRIGGER_SEMANTICS_EXTRACTOR.read_text(encoding="utf-8")
    assert "_module_contract" in source and "_assert_safe_target" in source
    payload = json.loads(TREASURY_TRIGGER_SEMANTICS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] is True
    assert payload["safety"]["module_definitions_or_string_literals_persisted"] == 0
    assert payload["safety"]["triggers_procedures_functions_views_or_application_commands_executed"] == 0
    summary = payload["summary"]
    assert summary["expected_trigger_count"] == 29
    assert summary["resolved_trigger_count"] == 29
    assert summary["instead_of_trigger_count"] == 2
    assert summary["disabled_trigger_count"] == 0
    assert summary["dependency_count"] == 133
    assert summary["lexical_operation_count"] == 20
    assert summary["lexical_operation_counts"] == {"DELETE_FROM": 2, "INSERT_INTO": 5, "UPDATE": 13}
    assert summary["resolved_mutation_target_count"] == 3
    assert summary["definition_persisted_count"] == 0
    assert summary["runtime_trigger_execution_or_effect_parity_proven_count"] == 0
    bridges = {row["parent_object"]: row for row in payload["triggers"] if row["is_instead_of"]}
    assert bridges["dbo.RCheque"]["resolved_mutation_targets"] == ["Acc.TblCheque"]
    assert bridges["dbo.RCashDraft"]["resolved_mutation_targets"] == ["Acc.TblBankOrders"]
    assert set(bridges["dbo.RCheque"]["lexical_operation_counts"]) == {"INSERT_INTO", "UPDATE", "DELETE_FROM"}


def test_treasury_writable_view_lineage_maps_visible_columns_without_running_views() -> None:
    source = TREASURY_VIEW_LINEAGE_EXTRACTOR.read_text(encoding="utf-8")
    assert "dm_exec_describe_first_result_set" in source
    payload = json.loads(TREASURY_VIEW_LINEAGE_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] is True
    assert payload["safety"]["business_row_values_or_string_literals_read_or_persisted"] == 0
    assert payload["safety"]["view_definitions_read_in_memory_count"] == 2
    assert payload["safety"]["view_definitions_persisted"] == 0
    assert payload["safety"]["procedures_functions_views_triggers_or_application_commands_executed"] == 0
    summary = payload["summary"]
    assert summary["target_view_count"] == 2
    assert summary["resolved_view_count"] == 2
    assert summary["view_column_count"] == 97
    assert summary["lineage_edge_count"] == 133
    assert summary["visible_described_result_column_count"] == 97
    assert summary["visible_described_result_column_with_source_lineage_count"] == 89
    assert summary["hidden_browse_lineage_column_count"] == 15
    assert summary["visible_column_without_direct_source_lineage_count"] == 8
    assert summary["parsed_select_candidate_count"] == 97
    assert summary["parsed_select_candidate_with_source_identifier_count"] == 97
    assert summary["definition_parse_error_count"] == 0
    assert summary["definition_persisted_count"] == 0
    assert summary["direct_metadata_gap_with_parsed_identifier_candidate_count"] == 8
    assert summary["runtime_read_write_or_trigger_effect_proven_count"] == 0
    views = {row["view"]: row for row in payload["views"]}
    cheque = {row["name"]: row for row in views["dbo.RCheque"]["described_result_columns"] if not row["is_hidden"]}
    draft = {row["name"]: row for row in views["dbo.RCashDraft"]["described_result_columns"] if not row["is_hidden"]}
    assert (cheque["RChequeAmount"]["source_object"], cheque["RChequeAmount"]["source_column"]) == ("Acc.TblCheque", "ChqAmount")
    assert (cheque["SayadNo"]["source_object"], cheque["SayadNo"]["source_column"]) == ("Acc.TblCheque", "SayadNo")
    assert (draft["RCashDraftAmount"]["source_object"], draft["RCashDraftAmount"]["source_column"]) == ("Acc.TblBankOrders", "Amount")
    assert (draft["BankAccountId"]["source_object"], draft["BankAccountId"]["source_column"]) == ("Acc.TblBankOrders", "DepBranchRef")
    parsed_cheque = {row["output_column"]: row for row in views["dbo.RCheque"]["parsed_select_lineage_candidates"]}
    parsed_draft = {row["output_column"]: row for row in views["dbo.RCashDraft"]["parsed_select_lineage_candidates"]}
    assert parsed_cheque["RChequeNo"]["source_identifier_candidates"][0]["source_column"] == "ChqNo"
    assert parsed_draft["RCashDraftNo"]["source_identifier_candidates"][0]["source_column"] == "OrderNo"


def test_treasury_target_contracts_keep_acceptance_obligations_unexecuted() -> None:
    source = TREASURY_TARGET_CONTRACTS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(TREASURY_TARGET_CONTRACTS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_TARGET_CONTRACT_DERIVATION_FROM_REDACTED_STATIC_EVIDENCE",
        "database_connections": 0,
        "network_reads_or_writes": 0,
        "live_ui_actions": 0,
        "source_or_target_commands_executed": 0,
        "business_rows_values_identities_or_grants_read_or_persisted": 0,
        "owner_approval_implementation_or_production_readiness_inferred": 0,
    }
    assert payload["summary"] == {
        "target_command_contract_count": 3,
        "acceptance_obligation_count": 51,
        "obligation_per_command_count": 17,
        "owner_approved_contract_count": 0,
        "implemented_contract_count": 0,
        "executed_acceptance_obligation_count": 0,
        "runtime_effect_or_result_parity_proven_count": 0,
        "validation_error_count": 0,
    }
    assert all(row["source_write_policy"] == "VARANEGAR_AND_CLONE_READ_ONLY_NO_WRITE_BACK" for row in payload["contracts"])
    assert all(not row["owner_approved"] and not row["implementation_ready"] for row in payload["contracts"])
    assert all(row["status"] == "UNEXECUTED_ACCEPTANCE_OBLIGATION" for row in payload["acceptance_obligations"])
    assert all(not row["legacy_or_clone_command_executed"] for row in payload["acceptance_obligations"])


def test_treasury_validation_contracts_separate_rule_signals_from_branch_proof() -> None:
    source = TREASURY_VALIDATION_CONTRACTS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(TREASURY_VALIDATION_CONTRACTS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["mode"] == "OFFLINE_DERIVATION_FROM_HASHED_REDACTED_DATA_ENTRY_IL"
    assert payload["safety"]["application_or_business_commands_executed"] == 0
    summary = payload["summary"]
    assert summary["target_form_count"] == 3
    assert summary["resolved_target_form_count"] == 3
    assert summary["selected_validation_or_command_method_count"] == 7
    assert summary["selected_instruction_count"] == 2461
    assert summary["unique_referenced_form_field_count"] == 29
    assert summary["unique_rule_signal_count"] == 14
    assert summary["method_with_transaction_signal_count"] == 4
    assert summary["method_with_direct_sql_mutation_signal_count"] == 3
    assert summary["exact_branch_condition_message_and_effect_proven_count"] == 0
    methods = {(row["form_type"], method["method"]): method for row in payload["contracts"] for method in row["methods"]}
    assert "CUSTOMER_REQUIRED_CONFIGURATION" in methods[("TreasuryOld.Forms.frmChequeEdit", "CheckRules")]["rule_signals"]
    assert "DUPLICATE_INSTRUMENT_NUMBER_CONFIGURATION" in methods[("TreasuryOld.Forms.frmRCashDraftEdit", "IsDataValid")]["rule_signals"]
    assert "ARRIVAL_DATE_INTERVAL_CONFIGURATION" in methods[("TreasuryOld.Forms.frmRCashDraftEdit", "txtRCashDraftDate_Leave")]["rule_signals"]
    assert "SAFE_OR_BANK_BALANCE_GUARD" in methods[("TreasuryOld.Forms.frmRCashDraftEdit", "ValidateRCashDraftAmount")]["rule_signals"]
    assert all(not method["exact_branch_condition_message_and_effect_proven"] for method in methods.values())


def test_treasury_trigger_transitive_graph_keeps_blast_radius_static_and_bounded() -> None:
    source = TREASURY_TRIGGER_TRANSITIVE_GRAPH_EXTRACTOR.read_text(encoding="utf-8")
    assert "MAX_DEPTH = 3" in source and "MAX_NODES = 500" in source
    payload = json.loads(TREASURY_TRIGGER_TRANSITIVE_GRAPH_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["denies_data_writes"] is True
    assert payload["safety"]["module_definitions_or_string_literals_persisted"] == 0
    assert payload["safety"]["procedures_functions_views_or_triggers_executed"] == 0
    summary = payload["summary"]
    assert summary["root_trigger_count"] == 29
    assert summary["maximum_depth"] == 3
    assert summary["node_count"] == 376
    assert summary["edge_count"] == 755
    assert summary["trigger_node_count"] == 270
    assert summary["table_node_count"] == 81
    assert summary["lexical_operation_count"] == 235
    assert summary["resolved_write_target_count"] == 42
    assert summary["root_with_resolved_write_target_count"] == 23
    assert summary["maximum_root_reachable_node_count"] == 121
    assert summary["maximum_root_resolved_write_target_count"] == 12
    assert summary["unresolved_dependency_count"] == 160
    assert summary["graph_truncated_at_safety_cap"] is False
    assert summary["runtime_execution_or_effect_parity_proven_count"] == 0
    impacts = {row["root_trigger"]: row for row in payload["root_impacts"]}
    assert impacts["dbo.Trg_RCheque_TblCheque"]["reachable_node_count"] == 121
    assert impacts["dbo.Trg_RCheque_TblCheque"]["resolved_write_target_count"] == 10
    assert impacts["dbo.Trg_RCashDraft_tblBankOrders"]["reachable_node_count"] == 93
    assert impacts["dbo.Trg_RCashDraft_tblBankOrders"]["resolved_write_target_count"] == 11
    assert all(row["reachability_status"] == "BOUNDED_STATIC_GRAPH_NOT_RUNTIME_BRANCH_PROOF" for row in payload["root_impacts"])


def test_treasury_web_field_contracts_preserve_setting_source_conflict() -> None:
    source = TREASURY_WEB_FIELD_CONTRACTS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(TREASURY_WEB_FIELD_CONTRACTS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["mode"] == "OFFLINE_MERGE_OF_REDACTED_PERSISTED_FIELD_LINEAGE_AND_RULE_EVIDENCE"
    assert payload["safety"]["assemblies_or_application_commands_executed"] == 0
    summary = payload["summary"]
    assert summary["target_form_count"] == 3
    assert summary["resolved_target_form_count"] == 3
    assert summary["declared_field_count"] == 68
    assert summary["field_status_counts"] == {
        "DECLARED_CONTROL_NO_FIELD_CONTRACT_CANDIDATE": 42,
        "STATIC_PROPERTY_AND_UNDERLYING_COLUMN_CANDIDATE": 16,
        "STATIC_PROPERTY_ONLY_CANDIDATE": 2,
        "STATIC_PROPERTY_WITH_CONFLICTING_UNDERLYING_COLUMN_CANDIDATES": 1,
        "VALIDATION_OR_COMMAND_FIELD_WITHOUT_PROPERTY_CANDIDATE": 7,
    }
    assert summary["field_with_strong_property_candidate_count"] == 19
    assert summary["field_with_underlying_source_column_candidate_count"] == 17
    assert summary["field_with_conflicting_underlying_source_candidates_count"] == 1
    assert summary["field_with_validation_or_command_method_use_count"] == 24
    assert summary["unique_underlying_source_column_candidate_count"] == 18
    assert summary["runtime_binding_requiredness_effective_rule_or_write_mapping_proven_count"] == 0
    fields = {(row["form_type"], field["field_name"]): field for row in payload["forms"] for field in row["fields"]}
    conflict = fields[("TreasuryOld.Forms.frmRCashDraftEdit", "txtRCashDraftNo")]
    assert conflict["multiple_underlying_source_candidate_conflict"] is True
    assert {(row["source_object"], row["source_column"]) for row in conflict["source_column_candidates"]} == {
        ("acc.TblBankOrders", "OrderNo"), ("dbo.TRServerConfig", "NotInsertDuplicateRCashDraftNo")
    }
    assert all(not field["runtime_binding_requiredness_effective_rule_or_write_mapping_proven"] for field in fields.values())


def test_treasury_ui_labels_are_static_allowlisted_candidates_only() -> None:
    source = TREASURY_UI_LABELS_EXTRACTOR.read_text(encoding="utf-8")
    assert "read_method_body_from_bytes" in source
    assert "InvokePattern" not in source
    assert "SendKeys" not in source
    payload = json.loads(TREASURY_UI_LABELS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["mode"] == "READ_ONLY_STATIC_INITIALIZE_COMPONENT_IL_PARSE"
    assert payload["safety"]["assemblies_loaded_or_executed"] == 0
    assert payload["safety"]["business_rows_or_field_values_read_or_persisted"] == 0
    summary = payload["summary"]
    assert summary["target_form_count"] == 3
    assert summary["resolved_initializer_count"] == 3
    assert summary["static_ui_assignment_candidate_count"] == 40
    assert summary["declared_control_label_candidate_count"] == 37
    assert summary["form_or_unresolved_target_candidate_count"] == 3
    assert summary["unique_declared_control_with_label_candidate_count"] == 37
    assert summary["ambiguous_declared_control_count"] == 0
    assert summary["runtime_visibility_or_effective_text_proven_count"] == 0
    titles = {
        row["form_type"]: [
            item["ui_text"]
            for item in row["assignments"]
            if item["target_kind"] == "FORM_OR_UNRESOLVED_TARGET"
        ]
        for row in payload["forms"]
    }
    assert titles["TreasuryOld.Forms.frmCashEdit"] == ["فرم ویرایش مبلغ نقد"]
    assert titles["TreasuryOld.Forms.frmChequeEdit"] == ["فرم اصلاح مشخصات چک"]
    assert titles["TreasuryOld.Forms.frmRCashDraftEdit"] == ["فرم اصلاح مشخصات واریز"]


def test_treasury_web_screen_candidates_keep_owner_and_runtime_gates_open() -> None:
    source = TREASURY_WEB_SCREENS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(TREASURY_WEB_SCREENS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["mode"] == "OFFLINE_READ_ONLY_EVIDENCE_COMPOSITION"
    assert payload["safety"]["legacy_or_clone_writes"] == 0
    summary = payload["summary"]
    assert summary["screen_candidate_count"] == 3
    assert summary["target_command_count"] == 3
    assert summary["input_control_candidate_count"] == 27
    assert summary["input_with_direct_static_caption_candidate_count"] == 2
    assert summary["command_control_candidate_count"] == 6
    assert summary["unpaired_static_label_candidate_count"] == 31
    assert summary["unique_rule_signal_count"] == 14
    assert summary["acceptance_obligation_count"] == 51
    assert summary["owner_approved_screen_count"] == 0
    assert summary["implementation_ready_screen_count"] == 0
    assert summary["runtime_golden_proven_screen_count"] == 0
    assert all(row["promotion_status"] == "NOT_IMPLEMENTATION_READY" for row in payload["screens"])
    assert all(not row["owner_approved"] and not row["runtime_golden_proven"] for row in payload["screens"])


def test_order_sale_entry_contracts_separate_ui_commit_and_handler_boundaries() -> None:
    source = ORDER_SALE_COMMANDS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(ORDER_SALE_COMMANDS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["mode"] == "OFFLINE_DERIVATION_FROM_HASHED_REDACTED_DATA_ENTRY_IL"
    assert payload["safety"]["application_or_business_commands_executed"] == 0
    summary = payload["summary"]
    assert summary["target_form_count"] == 3
    assert summary["resolved_target_form_count"] == 3
    assert summary["selected_method_count"] == 18
    assert summary["selected_instruction_count"] == 1754
    assert summary["unique_referenced_form_field_count"] == 29
    assert summary["unique_business_action_call_count"] == 11
    assert summary["unique_first_party_business_call_count"] == 25
    assert summary["unique_first_party_data_access_call_count"] == 0
    assert summary["unique_configuration_getter_count"] == 10
    assert summary["unique_rule_signal_count"] == 13
    assert summary["form_with_permission_override_count"] == 2
    assert summary["method_with_data_context_commit_count"] == 2
    assert summary["method_with_direct_sql_execution_count"] == 0
    assert summary["runtime_success_or_effect_parity_proven_count"] == 0
    contracts = {row["form_type"]: row for row in payload["contracts"]}
    assert contracts["VN.SDS.Sales.UI.Order.FormOrderDataEntry"]["target_command_candidate"] == "order.save"
    assert contracts["VN.SDS.Sales.UI.Sale.FormSaleDataEntry"]["target_command_candidate"] == "order.convert_to_sale"
    assert contracts["VN.SDS.Sales.UI.RetSale.FormRetSaleDataEntry"]["target_command_candidate"] == "sales_return.save"
    assert contracts["VN.SDS.Sales.UI.Sale.FormSaleDataEntry"]["permission_override_present"] is False
    assert all(not row["owner_approved"] and not row["runtime_success_or_effect_parity_proven"] for row in contracts.values())


def test_order_sale_static_labels_full_fields_and_layout_pairing_are_bounded() -> None:
    for source_path in (
        ORDER_SALE_UI_LABELS_EXTRACTOR,
        ORDER_SALE_FULL_FIELDS_EXTRACTOR,
        ORDER_SALE_LAYOUT_EXTRACTOR,
    ):
        source = source_path.read_text(encoding="utf-8")
        assert "InvokePattern" not in source and "SendKeys" not in source
    labels = json.loads(ORDER_SALE_UI_LABELS_ARTIFACT.read_text(encoding="utf-8"))
    assert labels["validation"] == "PASS"
    assert labels["summary"] == {
        "target_form_count": 3,
        "resolved_initializer_count": 3,
        "declared_control_field_count": 43,
        "static_ui_assignment_candidate_count": 144,
        "declared_control_label_candidate_count": 8,
        "unregistered_form_field_label_candidate_count": 126,
        "likely_form_title_candidate_count": 3,
        "form_or_unresolved_target_candidate_count": 10,
        "unique_form_field_with_label_candidate_count": 134,
        "ambiguous_declared_control_count": 0,
        "rejected_literal_count": 16,
        "runtime_visibility_or_effective_text_proven_count": 0,
        "validation_error_count": 0,
    }
    fields = json.loads(ORDER_SALE_FULL_FIELDS_ARTIFACT.read_text(encoding="utf-8"))
    assert fields["validation"] == "PASS"
    assert fields["summary"]["declared_field_count"] == 423
    assert fields["summary"]["resolved_field_type_count"] == 423
    assert fields["summary"]["unresolved_field_type_count"] == 0
    assert fields["summary"]["ui_component_candidate_count"] == 342
    assert fields["summary"]["web_input_candidate_count"] == 140
    assert fields["summary"]["ui_component_with_static_text_candidate_count"] == 133
    assert fields["summary"]["runtime_behavior_binding_requiredness_or_value_proven_count"] == 0
    layout = json.loads(ORDER_SALE_LAYOUT_ARTIFACT.read_text(encoding="utf-8"))
    assert layout["validation"] == "PASS"
    assert layout["summary"]["layout_binding_candidate_count"] == 140
    assert layout["summary"]["web_input_layout_binding_candidate_count"] == 122
    assert layout["summary"]["web_input_binding_with_static_label_candidate_count"] == 113
    assert layout["summary"]["control_with_multiple_layout_binding_candidate_count"] == 0
    assert layout["summary"]["rejected_set_control_shape_count"] == 0
    assert layout["summary"]["runtime_layout_visibility_effective_label_or_binding_proven_count"] == 0


def test_order_sale_web_screens_link_existing_synthetic_golden_cases_without_readiness_claim() -> None:
    source = ORDER_SALE_WEB_SCREENS_BUILDER.read_text(encoding="utf-8")
    assert "_connect(" not in source
    payload = json.loads(ORDER_SALE_WEB_SCREENS_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["legacy_or_clone_writes"] == 0
    summary = payload["summary"]
    assert summary["screen_candidate_count"] == 3
    assert summary["target_command_count"] == 3
    assert summary["input_control_candidate_count"] == 140
    assert summary["input_with_static_layout_label_candidate_count"] == 113
    assert summary["input_without_static_layout_label_candidate_count"] == 27
    assert summary["command_control_candidate_count"] == 13
    assert summary["unique_rule_signal_count"] == 13
    assert summary["linked_synthetic_golden_case_count"] == 48
    assert summary["owner_approved_screen_count"] == 0
    assert summary["implementation_ready_screen_count"] == 0
    assert summary["runtime_golden_executed_screen_count"] == 0
    assert all(row["synthetic_golden_case_count"] == 16 for row in payload["screens"])
    assert all(not row["owner_approved"] and not row["implementation_ready"] and not row["runtime_golden_executed"] for row in payload["screens"])


def test_order_sale_business_dataaccess_and_sql_semantics_remain_static() -> None:
    graph_source = ORDER_SALE_DEPENDENCY_GRAPH_EXTRACTOR.read_text(encoding="utf-8")
    assert "_analyze_assembly" in graph_source and "application_or_business_commands_executed" in graph_source
    graph = json.loads(ORDER_SALE_DEPENDENCY_GRAPH_ARTIFACT.read_text(encoding="utf-8"))
    assert graph["validation"] == "PASS"
    assert graph["summary"]["root_form_count"] == 3
    assert graph["summary"]["root_form_method_to_business_edge_count"] == 30
    assert graph["summary"]["business_depth_limit"] == 2
    assert graph["summary"]["selected_business_method_node_count"] == 53
    assert graph["summary"]["business_dependency_edge_count"] == 86
    assert graph["summary"]["selected_data_access_method_node_count"] == 28
    assert graph["summary"]["safe_sql_object_anchor_count"] == 7
    assert graph["summary"]["source_hash_mismatch_count"] == 0
    assert graph["summary"]["unresolved_selected_member_count"] == 0
    sql_source = ORDER_SALE_SQL_SEMANTICS_EXTRACTOR.read_text(encoding="utf-8")
    assert "procedures_functions_views_or_triggers_executed" in sql_source
    sql = json.loads(ORDER_SALE_SQL_SEMANTICS_ARTIFACT.read_text(encoding="utf-8"))
    assert sql["validation"] == "PASS"
    assert sql["safety"]["database_updateability"] == "READ_ONLY"
    assert sql["safety"]["can_update"] == 0
    assert sql["safety"]["denies_data_writes"] == 1
    assert sql["summary"]["selected_anchor_count"] == 7
    assert sql["summary"]["resolved_module_count"] == 7
    assert sql["summary"]["parameter_count"] == 95
    assert sql["summary"]["dependency_count"] == 114
    assert sql["summary"]["module_with_mutation_token_count"] == 2
    assert sql["summary"]["catalog_resolved_durable_mutation_target_count"] == 9
    assert sql["summary"]["result_shape_metadata_failure_count"] == 7
    assert sql["summary"]["execution_result_or_effect_parity_proven_count"] == 0


def test_order_sale_mutation_targets_and_trigger_blast_radius_are_explicitly_incomplete() -> None:
    source = ORDER_SALE_SOURCE_MODEL_EXTRACTOR.read_text(encoding="utf-8")
    assert "UPDATE " not in source and "DELETE FROM" not in source and "INSERT INTO" not in source
    model = json.loads(ORDER_SALE_SOURCE_MODEL_ARTIFACT.read_text(encoding="utf-8"))
    assert model["validation"] == "PASS"
    assert model["safety"]["database_updateability"] == "READ_ONLY"
    assert model["summary"]["target_object_count"] == 9
    assert model["summary"]["resolved_object_count"] == 9
    assert model["summary"]["column_count"] == 265
    assert model["summary"]["foreign_key_edge_observation_count"] == 115
    assert model["summary"]["enabled_trigger_count"] == 73
    assert model["summary"]["referencing_module_observation_count"] == 2088
    trigger = json.loads(ORDER_SALE_TRIGGER_GRAPH_ARTIFACT.read_text(encoding="utf-8"))
    assert trigger["validation"] == "PASS"
    summary = trigger["summary"]
    assert summary["root_trigger_count"] == 73
    assert summary["maximum_depth"] == 3
    assert summary["node_count"] == 500
    assert summary["edge_count"] == 1013
    assert summary["trigger_node_count"] == 384
    assert summary["table_node_count"] == 90
    assert summary["lexical_operation_count"] == 315
    assert summary["resolved_write_target_count"] == 35
    assert summary["maximum_root_reachable_node_count"] == 175
    assert summary["maximum_root_resolved_write_target_count"] == 21
    assert summary["unresolved_dependency_count"] == 207
    assert summary["graph_truncated_at_safety_cap"] is True
    assert summary["unexpanded_frontier_count"] == 184
    assert summary["runtime_execution_or_effect_parity_proven_count"] == 0


def test_stock_voucher_command_contract_keeps_transitions_separate() -> None:
    path = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_stock_voucher_command_contract_20260827.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["business_commands_executed"] == 0
    assert payload["summary"]["selected_method_count"] == 9
    assert payload["summary"]["selected_instruction_count"] == 1122
    assert payload["summary"]["referenced_form_field_count"] == 20
    assert payload["summary"]["rule_signal_count"] == 8
    assert payload["summary"]["handler_transaction_signal_count"] == 1
    assert payload["target_command_candidates"] == [
        "stock_voucher.save",
        "stock_voucher.confirm_or_unconfirm",
        "stock_voucher.generate_return",
    ]
    assert payload["owner_approved"] is False
    assert payload["runtime_effect_parity_proven"] is False


def test_distribution_to_exit_sql_and_trigger_blast_radius_are_bounded() -> None:
    base = ROOT / "artifacts" / "varanegar_analysis" / "ui"
    anchors = json.loads((base / "varanegar_distribution_sql_anchor_contracts_20260827.json").read_text(encoding="utf-8"))
    assert anchors["validation"] == "PASS"
    assert anchors["summary"]["selected_command_count"] == 4
    assert anchors["summary"]["sql_object_anchor_count"] == 5
    assert anchors["summary"]["explicit_idempotency_parameter_observed_count"] == 0
    sql = json.loads((base / "varanegar_distribution_sql_semantics_20260827.json").read_text(encoding="utf-8"))
    assert sql["validation"] == "PASS"
    assert sql["safety"]["database_updateability"] == "READ_ONLY"
    assert sql["summary"]["selected_anchor_count"] == 5
    assert sql["summary"]["parameter_count"] == 49
    assert sql["summary"]["dependency_count"] == 65
    assert sql["summary"]["module_with_mutation_token_count"] == 5
    assert sql["summary"]["catalog_resolved_durable_mutation_target_count"] == 16
    model = json.loads((base / "varanegar_distribution_mutation_source_model_20260827.json").read_text(encoding="utf-8"))
    assert model["validation"] == "PASS"
    assert model["summary"]["target_object_count"] == 16
    assert model["summary"]["column_count"] == 316
    assert model["summary"]["foreign_key_edge_observation_count"] == 105
    assert model["summary"]["enabled_trigger_count"] == 87
    graph = json.loads((base / "varanegar_distribution_trigger_transitive_graph_20260827.json").read_text(encoding="utf-8"))
    assert graph["validation"] == "PASS"
    assert graph["summary"]["node_count"] == 500
    assert graph["summary"]["edge_count"] == 1215
    assert graph["summary"]["trigger_node_count"] == 369
    assert graph["summary"]["resolved_write_target_count"] == 38
    assert graph["summary"]["unresolved_dependency_count"] == 232
    assert graph["summary"]["graph_truncated_at_safety_cap"] is True
    assert graph["summary"]["runtime_execution_or_effect_parity_proven_count"] == 0


def test_supplier_invoice_contract_preserves_trigger_guard_as_evidence_not_action() -> None:
    base = ROOT / "artifacts" / "varanegar_analysis" / "ui"
    contract = json.loads((base / "varanegar_supplier_invoice_command_contract_20260827.json").read_text(encoding="utf-8"))
    assert contract["validation"] == "PASS"
    assert contract["safety"]["business_or_sql_commands_executed"] == 0
    assert contract["summary"]["target_form_count"] == 2
    assert contract["summary"]["selected_method_count"] == 19
    assert contract["summary"]["selected_instruction_count"] == 1155
    assert contract["summary"]["static_sql_literal_count"] == 7
    assert contract["summary"]["trigger_enable_disable_literal_count"] == 2
    assert contract["summary"]["method_with_data_context_commit_count"] == 3
    assert all(row["runtime_executed"] is False for row in contract["static_sql_literals"])
    anchors = json.loads((base / "varanegar_supplier_invoice_sql_anchor_contracts_20260827.json").read_text(encoding="utf-8"))
    assert anchors["validation"] == "PASS"
    assert anchors["summary"]["resolved_durable_mutation_target_count"] == 1
    assert anchors["summary"]["resolved_trigger_name_count"] == 1
    assert anchors["modules"][0]["durable_mutation_targets"] == ["ica.tblSupInvInvoiceRelation"]
    model = json.loads((base / "varanegar_supplier_invoice_relation_source_model_20260827.json").read_text(encoding="utf-8"))
    assert model["validation"] == "PASS"
    assert model["summary"]["column_count"] == 5
    assert model["summary"]["foreign_key_edge_observation_count"] == 1
    assert model["summary"]["enabled_trigger_count"] == 4
    graph = json.loads((base / "varanegar_supplier_invoice_relation_trigger_transitive_graph_20260827.json").read_text(encoding="utf-8"))
    assert graph["validation"] == "PASS"
    assert graph["summary"]["root_trigger_count"] == 4
    assert graph["summary"]["node_count"] == 215
    assert graph["summary"]["edge_count"] == 343
    assert graph["summary"]["trigger_node_count"] == 143
    assert graph["summary"]["resolved_write_target_count"] == 29
    assert graph["summary"]["graph_truncated_at_safety_cap"] is False
    assert graph["summary"]["runtime_execution_or_effect_parity_proven_count"] == 0


def test_stock_supplier_screen_candidates_keep_static_layout_separate_from_readiness() -> None:
    base = ROOT / "artifacts" / "varanegar_analysis" / "ui"
    labels = json.loads((base / "varanegar_stock_supplier_ui_label_candidates_20260827.json").read_text(encoding="utf-8"))
    assert labels["validation"] == "PASS"
    assert labels["summary"]["target_form_count"] == 3
    assert labels["summary"]["unique_form_field_with_label_candidate_count"] == 77
    fields = json.loads((base / "varanegar_stock_supplier_full_field_metadata_20260827.json").read_text(encoding="utf-8"))
    assert fields["validation"] == "PASS"
    assert fields["summary"]["declared_field_count"] == 288
    assert fields["summary"]["unresolved_field_type_count"] == 0
    assert fields["summary"]["web_input_candidate_count"] == 94
    layout = json.loads((base / "varanegar_stock_supplier_layout_bindings_20260827.json").read_text(encoding="utf-8"))
    assert layout["validation"] == "PASS"
    assert layout["summary"]["layout_binding_candidate_count"] == 67
    assert layout["summary"]["web_input_binding_with_static_label_candidate_count"] == 59
    screens = json.loads((base / "negin_erp_stock_supplier_web_screen_contract_candidates_20260827.json").read_text(encoding="utf-8"))
    assert screens["validation"] == "PASS"
    assert screens["safety"]["legacy_or_clone_writes"] == 0
    assert screens["summary"]["screen_candidate_count"] == 3
    assert screens["summary"]["input_control_candidate_count"] == 94
    assert screens["summary"]["input_with_static_layout_label_candidate_count"] == 59
    assert screens["summary"]["input_without_static_layout_label_candidate_count"] == 35
    assert screens["summary"]["linked_synthetic_golden_case_count"] == 77
    assert screens["summary"]["owner_approved_screen_count"] == 0
    assert screens["summary"]["implementation_ready_screen_count"] == 0
    assert screens["summary"]["runtime_golden_executed_screen_count"] == 0


def test_accounting_voucher_entrypoints_separate_generated_stock_and_manual_boundaries() -> None:
    base = ROOT / "artifacts" / "varanegar_analysis" / "ui"
    contracts = json.loads((base / "varanegar_accounting_voucher_entrypoint_contracts_20260827.json").read_text(encoding="utf-8"))
    assert contracts["validation"] == "PASS"
    assert contracts["safety"]["application_or_business_commands_executed"] == 0
    assert contracts["summary"]["target_form_count"] == 3
    assert contracts["summary"]["method_body_count"] == 71
    assert contracts["summary"]["write_like_method_count"] == 21
    assert contracts["summary"]["target_command_candidate_count"] == 7
    assert contracts["summary"]["unique_rule_signal_count"] == 8
    assert contracts["summary"]["owner_approved_contract_count"] == 0
    sql = json.loads((base / "varanegar_accounting_voucher_sql_candidates_20260827.json").read_text(encoding="utf-8"))
    assert sql["validation"] == "PASS"
    assert sql["safety"]["database_updateability"] == "READ_ONLY"
    assert sql["safety"]["can_update"] == 0
    assert sql["summary"]["candidate_object_count"] == 128
    assert sql["summary"]["total_parameter_count"] == 190
    assert sql["summary"]["total_dependency_count"] == 581
    assert sql["summary"]["exact_static_ui_or_handler_binding_count"] == 0
    assert sql["summary"]["runtime_execution_or_result_parity_proven_count"] == 0


def test_customer_goods_screen_candidates_expose_labels_and_unexecuted_golden_contracts() -> None:
    base = ROOT / "artifacts" / "varanegar_analysis" / "ui"
    commands = json.loads((base / "varanegar_customer_goods_command_contracts_20260827.json").read_text(encoding="utf-8"))
    assert commands["validation"] == "PASS"
    assert commands["summary"]["selected_method_count"] == 21
    assert commands["summary"]["selected_instruction_count"] == 2119
    assert commands["summary"]["unique_rule_signal_count"] == 10
    assert commands["summary"]["method_with_data_context_commit_count"] == 4
    customer = json.loads((base / "varanegar_customer_full_field_metadata_20260827.json").read_text(encoding="utf-8"))
    goods = json.loads((base / "varanegar_goods_full_field_metadata_20260827.json").read_text(encoding="utf-8"))
    assert customer["summary"]["declared_field_count"] == 263
    assert customer["summary"]["web_input_candidate_count"] == 69
    assert goods["summary"]["declared_field_count"] == 178
    assert goods["summary"]["web_input_candidate_count"] == 61
    customer_layout = json.loads((base / "varanegar_customer_layout_bindings_20260827.json").read_text(encoding="utf-8"))
    goods_layout = json.loads((base / "varanegar_goods_layout_bindings_20260827.json").read_text(encoding="utf-8"))
    assert customer_layout["summary"]["web_input_binding_with_static_label_candidate_count"] == 21
    assert goods_layout["summary"]["web_input_binding_with_static_label_candidate_count"] == 47
    screens = json.loads((base / "negin_erp_customer_goods_web_screen_contract_candidates_20260827.json").read_text(encoding="utf-8"))
    golden = json.loads((base / "negin_erp_customer_goods_master_golden_cases_20260827.json").read_text(encoding="utf-8"))
    assert golden["validation"] == "PASS"
    assert golden["summary"]["source_command_count"] == 4
    assert golden["summary"]["case_count"] == 64
    assert golden["summary"]["failure_injection_case_count"] == 12
    assert golden["safety"]["source_or_target_commands_executed"] == 0
    assert screens["validation"] == "PASS"
    assert screens["summary"]["screen_candidate_count"] == 2
    assert screens["summary"]["input_control_candidate_count"] == 130
    assert screens["summary"]["input_with_static_layout_label_candidate_count"] == 68
    assert screens["summary"]["input_without_any_static_text_candidate_count"] == 62
    assert screens["summary"]["command_control_candidate_count"] == 16
    assert screens["summary"]["linked_synthetic_golden_case_count"] == 64
    assert screens["summary"]["screen_with_missing_golden_contract_count"] == 0
    assert screens["summary"]["implementation_ready_screen_count"] == 0
    assert all(screen["golden_contract_gap"] is None for screen in screens["screens"])
    assert all(len(screen["linked_synthetic_golden_case_ids"]) == 32 for screen in screens["screens"])
    assert all(not screen["runtime_golden_executed"] for screen in screens["screens"])


def test_supplier_master_preserves_payment_accounting_contact_and_cardex_gates() -> None:
    base = ROOT / "artifacts" / "varanegar_analysis" / "ui"
    command = json.loads((base / "varanegar_supplier_master_command_contract_20260827.json").read_text(encoding="utf-8"))
    fields = json.loads((base / "varanegar_supplier_full_field_metadata_20260827.json").read_text(encoding="utf-8"))
    layout = json.loads((base / "varanegar_supplier_layout_bindings_20260827.json").read_text(encoding="utf-8"))
    screen = json.loads((base / "negin_erp_supplier_master_web_screen_contract_candidate_20260827.json").read_text(encoding="utf-8"))
    golden = json.loads((base / "negin_erp_foundation_context_pricing_golden_cases_20260827.json").read_text(encoding="utf-8"))
    assert golden["validation"] == "PASS"
    assert golden["summary"]["source_command_count"] == 12
    assert golden["summary"]["case_count"] == 192
    assert golden["summary"]["failure_injection_case_count"] == 35
    assert golden["summary"]["target_module_case_counts"] == {
        "inventory": 32,
        "master_data": 32,
        "organization_context": 64,
        "pricing_rules": 64,
    }
    assert golden["safety"]["source_or_target_commands_executed"] == 0
    assert command["validation"] == "PASS"
    assert command["summary"]["selected_method_count"] == 19
    assert command["summary"]["selected_instruction_count"] == 628
    assert command["summary"]["unique_rule_signal_count"] == 9
    assert command["summary"]["method_with_data_context_commit_count"] == 1
    assert "SUPPLIER_PAYMENT_USAGE_DELETE_GUARD" in command["contract"]["rule_signals"]
    assert "SUPPLIER_ACCOUNTING_GROUP_RELATION" in command["contract"]["rule_signals"]
    assert fields["summary"]["declared_field_count"] == 41
    assert fields["summary"]["unresolved_field_type_count"] == 0
    assert fields["summary"]["web_input_candidate_count"] == 12
    assert layout["summary"]["layout_binding_candidate_count"] == 14
    assert layout["summary"]["unique_bound_control_count"] == 13
    assert screen["validation"] == "PASS"
    assert screen["summary"]["input_control_candidate_count"] == 12
    assert screen["summary"]["input_with_static_layout_label_candidate_count"] == 12
    assert screen["summary"]["linked_synthetic_golden_case_count"] == 32
    assert screen["summary"]["screen_with_missing_golden_contract_count"] == 0
    assert screen["summary"]["implementation_ready_screen_count"] == 0
    assert screen["screen"]["golden_contract_gap"] is None
    assert not screen["screen"]["runtime_golden_executed"]


def test_identity_access_navigation_gap_is_identity_free_and_does_not_infer_runtime_grants() -> None:
    path = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_identity_access_navigation_gap_contract_20260827.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_REDACTED_STATIC_NAVIGATION_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "application_commands_executed": 0,
        "user_group_identity_or_grant_rows_read_or_persisted": 0,
        "credentials_or_secrets_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["identity_access_route_candidate_count"] == 16
    assert summary["runtime_matched_form_count"] == 0
    assert summary["route_with_form_info_count"] == 10
    assert summary["route_with_access_node_count"] == 10
    assert summary["effective_user_or_group_grant_proven_count"] == 0
    assert summary["runtime_form_behavior_proven_count"] == 0
    assert all(not row["effective_user_or_group_grant_proven"] for row in payload["routes"])
    assert all(not row["runtime_form_behavior_proven"] for row in payload["routes"])
    assert payload["target_contract"]["first_allowed_slice"].startswith("read_only")


def test_system_configuration_navigation_requires_versioned_effective_precedence() -> None:
    path = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_system_configuration_navigation_contract_20260827.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_JOIN_OF_REDACTED_STATIC_NAVIGATION_AND_READ_ONLY_AGGREGATE_CONFIGURATION_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "application_or_configuration_commands_executed": 0,
        "configuration_or_history_values_read_or_persisted": 0,
        "credentials_urls_paths_hosts_or_device_owners_persisted": 0,
    }
    summary = payload["summary"]
    assert summary["settings_root_route_count"] == 50
    assert summary["configured_form_route_count"] == 15
    assert summary["runtime_matched_configured_route_count"] == 4
    assert summary["runtime_unmatched_configured_route_count"] == 11
    assert summary["configuration_table_count"] == 14
    assert summary["general_config_key_count"] == 177
    assert summary["server_config_key_count"] == 334
    assert summary["history_only_key_count"] == 40
    assert summary["reviewed_cross_module_rule_key_count"] == 22
    assert summary["runtime_effective_value_or_precedence_proven_count"] == 0
    assert summary["runtime_mutation_effect_proven_count"] == 0
    assert payload["target_contract"]["first_allowed_slice"].startswith("read_only")
    assert all(not row["runtime_effective_value_or_precedence_proven"] for row in payload["configured_routes"])


def test_final_date_management_is_four_versioned_commands_not_one_setting_edit() -> None:
    path = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_final_date_management_boundary_20260827.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "OFFLINE_DERIVATION_FROM_REDACTED_STATIC_UI_AND_READ_ONLY_AGGREGATE_DOMAIN_EVIDENCE",
        "database_connections": 0,
        "network_reads": 0,
        "live_ui_actions": 0,
        "application_or_final_date_commands_executed": 0,
        "business_dates_rows_or_values_read_or_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["configured_final_date_route_count"] == 5
    assert summary["runtime_matched_route_count"] == 2
    assert summary["runtime_unmatched_route_count"] == 3
    assert summary["sales_runtime_form_contract_count"] == 1
    assert summary["extension_final_date_capability_count"] == 3
    assert summary["extension_capability_with_business_mediation_count"] == 3
    assert summary["extension_capability_with_direct_ui_data_access_count"] == 0
    assert summary["business_update_method_count"] == 4
    assert summary["data_access_update_method_count"] == 4
    assert summary["runtime_effect_parity_proven_count"] == 0
    assert summary["golden_case_executed_count"] == 0
    assert [row["command"] for row in payload["target_commands"]] == [
        "configuration.set_sales_final_date",
        "configuration.set_purchase_final_date",
        "configuration.set_financial_final_date",
        "configuration.set_petty_cash_final_date",
    ]


def test_final_date_incident_contract_captures_first_create_and_reopen_risks() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_final_date_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_DEFINITIONS_AND_NONEXECUTING_IL_PARSE",
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "raw_log_scripts_persisted": 0,
        "business_date_values_persisted": 0,
        "configuration_values_persisted": 0,
        "identities_or_individual_grants_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["finding_count"] == 11
    assert summary["finding_severity_counts"] == {
        "CRITICAL": 3,
        "HIGH": 7,
        "MEDIUM": 1,
    }
    assert summary["operation_date_consumer_count"] == 256
    assert summary["three_month_logged_operation_count"] == 160
    assert summary["command_execution_count"] == 0
    findings = {row["finding_id"]: row for row in payload["incident_findings"]}
    assert set(findings) == {f"FD-{number:03d}" for number in range(1, 12)}
    assert findings["FD-001"]["severity"] == "CRITICAL"
    assert len(findings["FD-001"]["evidence"]) == 6
    assert findings["FD-006"]["severity"] == "CRITICAL"
    assert findings["FD-007"]["severity"] == "CRITICAL"
    latest = {
        row["SysRef"]: row
        for row in payload["population_without_business_date_values"][
            "latest_fiscal_year_coverage_without_year_value"
        ]
    }
    assert latest[5]["row_present_count"] == 0
    assert latest[7]["row_present_count"] == 0
    impacts = payload["reopen_impact_aggregates"]
    assert impacts["financial_reopen_opening_statement_blast_radius"][
        "statement_type_1005_rows"
    ] == 0
    distribution = {
        row["Status"]: row["row_count"]
        for row in impacts["sales_reopen_distribution_branch_blast_radius"]
    }
    assert distribution == {4: 12, 7: 23382}
    assert impacts["distribution_backup_and_trigger_state"][
        "disabled_trigger_count"
    ] == 0
    activity = payload["three_month_activity_without_raw_scripts"][
        "aggregate_without_raw_scripts"
    ]
    assert activity == {
        "row_count": 160,
        "update_scripts": 160,
        "insert_scripts": 0,
        "delete_scripts": 0,
    }
    il_summary = payload["il_contract"]["summary"]
    assert il_summary["target_type_count"] == 6
    assert il_summary["found_type_count"] == 6
    assert il_summary["adapter_sql_template_count"] == 8
    assert il_summary["parameterized_adapter_template_count"] == 0


def test_stock_reconciliation_uses_official_obligation_formula_without_repair() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_stock_reconciliation_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["safety"] == {
        "database_name": "NeginPakhsh_WebDev",
        "updateability": "READ_ONLY",
        "can_select": 1,
        "can_update": 0,
        "database_commands_executed": 0,
        "stored_procedures_executed": 0,
        "application_or_ui_commands_executed": 0,
        "assemblies_loaded_or_executed": 0,
        "operational_rows_changed": 0,
        "raw_goods_vouchers_users_hosts_or_config_values_persisted": 0,
        "mode": "READ_ONLY_CATALOG_AND_ANONYMOUS_AGGREGATES",
    }
    assert payload["summary"] == {
        "cardex_only_mismatch_count": 1594,
        "official_formula_mismatch_count": 0,
        "finding_count": 5,
        "critical_finding_count": 2,
        "high_finding_count": 3,
        "target_module_count": 7,
    }
    official = payload["official_legacy_formula_reconciliation"]
    assert official["overview"]["compared_keys"] == 33314
    assert official["overview"]["exact"] == 33314
    assert official["overview"]["mismatch"] == 0
    assert official["overview"]["obligation_keys"] == 1594
    assert official["overview"]["absolute_obligation"] == "104470"
    assert official["component_aggregates"] == [
        {
            "component": "sale_without_exit",
            "component_keys": 1594,
            "stock_centers": 4,
            "signed_quantity": "104470",
            "absolute_quantity": "104470",
        }
    ]
    assert payload["healthy_cardex_vs_for_check_view_parity"]["mismatch"] == 0
    assert {row["finding_id"] for row in payload["findings"]} == {
        f"STK-{number:03d}" for number in range(1, 6)
    }
    activity = payload["three_month_sale_exit_activity"]
    assert activity["window_months"] == 3
    assert sum(
        row["sale_headers"]
        for row in activity["current_stock_obligation_aging"]
    ) == 821
    assert all(not row["is_disabled"] for row in payload["trigger_state"])


def test_distribution_path_is_manual_code_not_orphan_master_fk() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_distribution_path_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_DEFINITIONS_AND_NONEXECUTING_IL_PARSE",
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "identities_or_raw_party_rows_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["distribution_count"] == 26086
    assert summary["distinct_path_code_count"] == 7
    assert summary["legacy_path_master_row_count"] == 0
    assert summary["formal_dist_path_fk_count"] == 0
    assert summary["previous_orphan_fk_interpretation_valid"] is False
    assert summary["current_runtime_path_mode"] == "MANUAL_INTEGER_CODE"
    assert summary["recent_distribution_count"] == 3379
    assert summary["create_dist_references_legacy_master"] is False
    assert summary["database_or_application_commands_executed"] == 0
    assert payload["configuration_contract"][
        "all_groups_select_manual_entry_branch"
    ] is True
    assert payload["semantic_correction"]["wrong_model"].endswith(
        "GNR.tblDistPath.ID"
    )
    assert {row["finding_id"] for row in payload["incident_findings"]} == {
        f"DP-{number:03d}" for number in range(1, 7)
    }
    assert payload["incident_findings"][0]["severity"] == "CRITICAL"
    assert len(payload["il_contract"]["verified_branch_contracts"]) == 4
    assert [row["path_code"] for row in payload["schema_and_population"]["path_code_profile"]] == [
        1,
        2,
        3,
        4,
        5,
        11,
        12,
    ]


def test_sales_return_total_is_official_net_not_gross_amount() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_sales_return_amount_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_DEFINITIONS_AND_NONEXECUTING_IL_PARSE",
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "live_ui_actions": 0,
        "assemblies_loaded_or_executed": 0,
        "identities_or_raw_business_rows_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["return_count"] == 14091
    assert summary["previous_gross_comparison_difference_count"] == 731
    assert summary["previous_active_difference_count"] == 696
    assert summary["previous_mismatch_interpretation_valid"] is False
    assert summary["official_stored_net_difference_count"] == 0
    assert summary["official_calculated_net_difference_count"] == 0
    assert summary["item_formula_difference_count"] == 0
    assert summary["discount_rollup_difference_count"] == 0
    assert summary["addition_rollup_difference_count"] == 0
    assert summary["maximum_official_net_delta"] == "0"
    assert summary["official_header_total_basis"] == "SUM(SLE.tblRetSaleItm.AmountNut)"
    assert summary["official_item_net_formula"] == "Amount - Discount + AddAmount"
    assert summary["sql_formula_verified"] is True
    assert summary["sql_header_net_verified"] is True
    assert summary["recalculation_header_net_verified"] is True
    assert {row["finding_id"] for row in payload["incident_findings"]} == {
        f"RA-{number:03d}" for number in range(1, 7)
    }
    assert payload["incident_findings"][0]["severity"] == "CRITICAL"
    assert len(payload["il_contract"]["verified_branch_contracts"]) == 4
    assert all(
        row["stored_net_differences"] == 0
        and row["calculated_net_differences"] == 0
        for row in payload["amount_reconciliation"]["by_cancel_state"]
    )
    assert all(
        row["stored_net_differences"] == 0
        and row["calculated_net_differences"] == 0
        for row in payload["recent_three_month_activity"][
            "monthly_cancel_state_aggregates"
        ]
    )


def test_returned_cheque_cross_customer_rows_follow_original_allocation() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_returned_cheque_cross_customer_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_DEFINITIONS_AND_EXISTING_NONEXECUTING_IL_EVIDENCE",
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "identities_or_raw_business_rows_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["cross_customer_rows"] == 49
    assert summary["cross_customer_cheques"] == 17
    assert summary["exact_original_allocation_matches"] == 49
    assert summary["unexplained_rows"] == 0
    assert summary["allocation_pairs"] == 31
    assert summary["over_settled_pairs"] == 0
    assert summary["previous_anomaly_interpretation_valid"] is False
    assert summary["official_authority_key"] == (
        "RetChequeRef + SaleRef + allocation CustRef"
    )
    assert all(payload["verified_sql_contracts"].values())
    profile = payload["aggregate_contract"]["relationship_profile"]
    assert profile["sale_matches_payment_customer"] == 48
    assert profile["sale_matches_cheque_customer"] == 0
    pairs = payload["aggregate_contract"][
        "cheque_sale_customer_pair_reconciliation"
    ]
    assert pairs["pairs_without_exact_allocation"] == 0
    assert pairs["over_settled_pairs"] == 0
    assert {row["finding_id"] for row in payload["incident_findings"]} == {
        f"RCX-{number:03d}" for number in range(1, 6)
    }
    assert payload["incident_findings"][0]["severity"] == "CRITICAL"
    assert payload["ui_contract"]["form_type"] == (
        "TreasuryOld.Forms.frmSettlementByCustomer"
    )


def test_received_cheque_approved_pay_authority_and_legal_type_gap() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_received_cheque_projection_and_legal_type_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_AND_DEFINITION_ANALYSIS",
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "identities_or_raw_business_rows_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["current_status7_cheques"] == 12635
    assert summary["master_pay_projection_missing_rows"] == 8
    assert summary["valid_approved_history_pay_links_for_all_missing_master_rows"] == 8
    assert summary["history_pay_orphans"] == 0
    assert summary["conflicting_pay_links"] == 0
    assert summary["previous_missing_pay_link_interpretation_valid"] is False
    assert summary["current_status9_unspecified_legal_type_rows"] == 35
    assert summary["current_status9_explicit_legal_department_rows"] == 18
    assert summary["legal_type_null_is_safe_to_impute"] is False
    assert summary["bulk_confirmation_forwards_legal_type"] is False
    assert {row["finding_id"] for row in payload["incident_findings"]} == {
        f"RCL-{number:03d}" for number in range(1, 6)
    }


def test_payable_cheque_leaf_used_unlinked_is_preserved_without_invented_provenance() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_payable_cheque_leaf_usage_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_AND_DEFINITION_ANALYSIS",
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "identities_or_raw_business_rows_persisted": 0,
        "cheque_numbers_or_comments_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["leaf_count"] == 5687
    assert summary["used_leaf_count"] == 4827
    assert summary["current_cheque_link_count"] == 4672
    assert summary["source_used_unlinked_count"] == 155
    assert summary["affected_book_count"] == 23
    assert summary["linked_transfer_family_count"] == 0
    assert summary["manual_context_present_count"] == 0
    assert summary["previous_orphan_interpretation_valid"] is False
    assert summary["safe_to_clear_or_synthesize"] is False
    assert summary["historical_reason_recoverable"] is False
    assert all(payload["verified_contracts"].values())
    assert {row["finding_id"] for row in payload["incident_findings"]} == {
        f"PCL-{number:03d}" for number in range(1, 5)
    }


def test_voucher_status_pointer_fork_is_not_silently_repaired() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_voucher_status_pointer_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_AND_DEFINITION_ANALYSIS",
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "identities_comments_or_raw_business_rows_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["voucher_count"] == 205944
    assert summary["history_event_count"] == 322576
    assert summary["invalid_current_pointer_count"] == 0
    assert summary["current_pointer_not_maximum_count"] == 1094
    assert summary["detached_trailing_event_count"] == 14946
    assert summary["pointer_at_first_event_count"] == 1090
    assert summary["fork_with_different_status_count"] == 1091
    assert summary["maximum_trailing_events_per_voucher"] == 244
    assert summary["trailing_event_with_comment_count"] == 0
    assert summary["safe_to_replace_pointer_with_maximum"] is False
    assert summary["safe_to_discard_trailing_history"] is False
    assert summary["legacy_change_status_failure_has_explicit_rollback"] is False
    assert summary["historical_outcome_recoverable"] is False
    assert all(payload["verified_contracts"].values())
    assert {row["finding_id"] for row in payload["incident_findings"]} == {
        f"VSP-{number:03d}" for number in range(1, 5)
    }


def test_empty_voucher_header_is_kept_as_non_posted_numbered_draft_shell() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_empty_voucher_shell_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    assert payload["safety"] == {
        "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_AND_DEFINITION_ANALYSIS",
        "database_updateability": "READ_ONLY",
        "can_select": 1,
        "can_view_definition": 1,
        "can_update": 0,
        "denies_data_writes": 1,
        "stored_procedure_or_application_command_executions": 0,
        "identities_numbers_comments_or_raw_rows_persisted": 0,
        "source_or_target_state_changed": 0,
    }
    summary = payload["summary"]
    assert summary["active_header_without_line_count"] == 1
    assert summary["draft_shell_count"] == 1
    assert summary["numbered_shell_count"] == 1
    assert summary["external_link_count"] == 0
    assert summary["any_item_count"] == 0
    assert summary["deleted_item_count"] == 0
    assert summary["ledger_debit_effect"] == "0"
    assert summary["ledger_credit_effect"] == "0"
    assert summary["previous_active_journal_corruption_interpretation_valid"] is False
    assert summary["safe_to_synthesize_lines"] is False
    assert summary["safe_to_reuse_source_number"] is False
    assert summary["historical_reason_recoverable"] is False
    assert all(payload["verified_contracts"].values())
    assert {row["finding_id"] for row in payload["incident_findings"]} == {
        f"EVS-{number:03d}" for number in range(1, 5)
    }


def test_ngt_return_crosswalk_separates_pending_from_historical_missing_target() -> None:
    path = (
        ROOT
        / "artifacts"
        / "varanegar_analysis"
        / "ui"
        / "varanegar_ngt_return_crosswalk_diagnostic_contract_20260827.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    assert payload["safety"]["database_updateability"] == "READ_ONLY"
    assert payload["safety"]["can_update"] == 0
    assert payload["safety"]["stored_procedure_or_application_command_executions"] == 0
    summary = payload["summary"]
    assert summary["active_mobile_return_header_count"] == 2
    assert summary["active_mobile_return_line_count"] == 2
    assert summary["exact_current_order_crosswalk_count"] == 0
    assert summary["exact_current_official_return_crosswalk_count"] == 0
    assert summary["without_current_official_return_count"] == 2
    assert summary["historical_return_order_result_line_count"] == 1
    assert summary["historical_result_missing_current_order_count"] == 1
    assert summary["without_historical_return_order_result_line_count"] == 1
    assert summary["header_line_return_net_mismatch_count"] == 0
    replicate = next(
        row
        for row in payload["sql_module_contracts"]
        if row["qualified_name"] == "dbo.NGT_DoReplicateTour"
    )
    assert replicate["calls_ngt_replicate_tour"] is True
    assert replicate["writes_line_order_crosswalk_from_final_result"] is True
    assert replicate["commits_replication_before_ngt_return_crosswalk_writeback"] is True
    assert "FRU.CustomerCallReturns.Id" in payload["dual_mobile_model_contract"]["sle_reverse_link_target"]


def test_supplier_receipt_reconciliation_uses_relation_components() -> None:
    path = ROOT / "artifacts" / "varanegar_analysis" / "ui" / "varanegar_supplier_receipt_component_diagnostic_contract_20260827.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    summary = payload["summary"]
    assert summary["relation_count"] == 3689
    assert summary["relation_component_count"] == 3425
    assert summary["component_with_multiple_invoices_count"] == 1
    assert summary["naive_per_invoice_receipt_only_goods_group_count"] == 5
    assert summary["naive_receipt_only_explained_by_other_invoice_in_component_count"] == 5
    assert summary["component_scope_receipt_only_goods_group_count"] == 0
    assert summary["component_scope_invoice_only_goods_group_count"] == 0
    assert summary["component_scope_quantity_mismatch_goods_group_count"] == 0
    assert summary["component_scope_exact_goods_group_count"] == 30096
    assert summary["supplier_return_missing_direct_source_goods_group_count"] == 7
    assert summary["supplier_return_missing_source_goods_found_in_component_invoice_count"] == 0
    assert payload["supplier_return_missing_direct_source_profile"]["return_headers"] == 3
    assert payload["supplier_return_missing_direct_source_profile"]["goods_seen_on_prior_same_scope_supplier_invoice"] == 7
    assert payload["supplier_return_missing_direct_source_profile"]["nonzero_price_goods_groups"] == 7
    assert payload["supplier_return_missing_direct_source_profile"]["new_path_nonzero_price_goods_groups"] == 5
    assert payload["supplier_return_missing_direct_source_profile"]["legacy_path_nonzero_price_goods_groups"] == 2
    assert payload["supplier_return_missing_direct_source_profile"]["nonzero_total_amount_goods_groups"] == 7
    assert payload["supplier_return_missing_direct_source_profile"]["exact_linked_type55_inventory_exit_goods_groups"] == 7
    assert payload["official_apply_contract"]["compares_aggregate_goods_quantities"] is True
    profile = payload["supplier_return_validator_data_profile"]
    assert profile["sourced_return_goods_group_count"] == 115
    assert profile["return_document_goods_group_count"] == 156
    assert profile["unmatched_return_document_goods_group_count"] == 7
    assert profile["unmatched_return_goods_group_count"] == 7
    assert profile["matched_over_return_goods_group_count"] == 0
    contract = payload["supplier_return_validation_contract"]
    assert contract["sup_invoice_ref_is_optional_in_before_save_required_field_check"] is True
    assert contract["validator_quantity_check_uses_inner_join_on_goods"] is True
    assert contract["validator_aggregates_all_return_headers_sharing_source_invoice"] is True
    assert contract["validator_scopes_return_items_to_current_return_header"] is False
    assert contract["validator_has_explicit_unmatched_return_goods_check"] is False
    assert contract["insert_branch_calls_validator"] is True
    assert contract["update_branch_calls_validator"] is False
    assert contract["insert_branch_captures_validator_return_code"] is False
    assert contract["insert_branch_raises_after_validator_call"] is False
    assert contract["save_has_explicit_transaction_and_catch_rollback"] is True
    assert contract["update_branch_uses_hdrid_for_new_item_tolls"] is True
    assert contract["update_branch_assigns_hdrid"] is False
    assert contract["update_branch_retargets_existing_item_toll_header_ref"] is False
    assert contract["compatibility_view_resolves_item_toll_by_same_header_and_toll_code"] is True
    assert contract["compatibility_view_uses_stored_explicit_item_toll_header_ref"] is False
    price_path = contract["price_provenance_contract"]
    assert price_path["sdsnet_save_copies_staged_price_and_amount"] is True
    assert price_path["official_import_maps_unit_price_to_price"] is True
    assert price_path["official_import_calculates_amount_from_qty_times_unit_price"] is True
    assert price_path["legacy_insert_accepts_and_persists_price_parameter"] is True
    assert price_path["legacy_update_accepts_and_persists_price_parameter"] is True
    assert price_path["current_row_creation_path_marker_available"] is False
    scope = contract["access_operation_date_and_required_goods_contract"]
    assert [scope["insert_access_node_id"], scope["update_access_node_id"], scope["delete_access_node_id"]] == [826001, 826002, 826003]
    assert scope["uses_access_node_authorizer"] is True
    assert scope["forwards_accyear_or_dcref_to_access_node_authorizer"] is False
    assert scope["purchase_final_date_sysref"] == 5
    assert scope["final_date_lookup_filters_accyear"] is True
    assert scope["final_date_lookup_filters_dcref"] is False
    assert scope["before_save_required_goods_check_reads_global_persisted_item_table"] is True
    assert scope["before_save_required_goods_check_scoped_to_current_parent_or_temp_items"] is False
    assert payload["supplier_return_required_goods_guard_profile"] == {
        "zero_or_null_goods_item_count": 0,
        "affected_return_header_count": 0,
    }
    assert payload["supplier_invoice_item_uniqueness_profile"] == {
        "duplicate_header_goods_group_count": 0,
        "unique_header_goods_index_count": 1,
    }
    desktop = payload["desktop_save_boundary"]
    assert desktop["binary_inventory_sha256_match"] is True
    assert desktop["method_instruction_count"] == 124
    assert desktop["calls_buffered_row_save_before_return_validator"] is True
    assert desktop["calls_return_validator_before_data_context_commit"] is True
    assert desktop["nonempty_validator_message_builds_validation_failure_before_commit"] is True
    assert desktop["nonempty_validator_message_has_dispose_before_commit"] is True
    assert desktop["empty_message_branch_targets_commit_block"] is True
    layered = desktop["layered_binding"]
    assert layered["business_calls_data_access_adapter"] is True
    assert layered["data_access_calls_data_context_execute"] is True
    assert layered["data_access_exact_sql_module_literal_observed"] is True
    assert layered["data_access_exact_sql_module_literal"] == "SLE.usp_CheckRetSupInvoice"
    assert [row["instruction_count"] for row in layered["methods"]] == [6, 17]
    selection = desktop["source_selection_contract"]
    assert selection["fill_item_grid_instruction_count"] == 359
    assert selection["source_invoice_change_instruction_count"] == 148
    assert selection["inventory_voucher_change_instruction_count"] == 46
    assert selection["grid_validation_instruction_count"] == 53
    assert selection["item_grid_loads_through_inventory_voucher_ref"] is True
    assert selection["source_invoice_change_fetches_invoice_items"] is True
    assert selection["matched_goods_copy_source_invoice_price_to_grid"] is True
    assert selection["unmatched_goods_set_grid_price_to_zero"] is True
    assert selection["inventory_voucher_change_clears_source_invoice_selection"] is True
    assert selection["grid_numeric_validation_columns"] == ["Amount", "Price"]
    assert selection["grid_price_or_amount_validation_calls_numeric_only_helper"] is True
    correction = payload["supplier_return_semantic_correction"]
    assert correction["source_item_absent_goods_group_count"] == 7
    assert correction["exact_type55_inventory_exit_goods_group_count"] == 7
    assert correction["migration_state"] == "OPTIONAL_SOURCE_ITEM_ABSENT_NOT_AN_INVENTORY_ERROR"
    tolls = payload["supplier_return_toll_integrity_profile"]
    assert tolls["item_toll_row_count"] == 4601
    assert tolls["affected_return_header_count"] == 1
    assert tolls["affected_new_path_return_header_count"] == 0
    assert tolls["correct_scope_missing_header_toll_row_count"] == 20
    assert tolls["referenced_toll_row_missing_globally_count"] == 20
    assert tolls["stale_explicit_ref_resolved_by_same_header_toll_code_count"] == 20
    assert tolls["unresolved_by_explicit_ref_or_same_header_toll_code_count"] == 0
    assert tolls["ambiguous_same_header_toll_code_match_count"] == 0
    assert tolls["omitted_from_deployed_compatibility_view_count"] == 0
    assert tolls["deployed_validator_missed_missing_toll_row_count"] == 20
    recent = payload["three_month_supplier_return_profile"]
    assert recent["window"] == "1405/03/01..1405/05/31"
    assert recent["return_header_count"] == 50
    assert recent["new_path_header_count"] == 50
    assert recent["legacy_path_header_count"] == 0
    assert recent["optional_source_invoice_present_header_count"] == 1
    assert recent["return_item_count"] == 393
    assert recent["optional_source_item_absent_goods_group_count"] == 5
    assert recent["stale_explicit_toll_ref_row_count"] == 0


def test_operational_context_keeps_year_dc_stock_and_accounting_semantics_separate() -> None:
    base = ROOT / "artifacts" / "varanegar_analysis" / "ui"
    command = json.loads((base / "varanegar_operational_context_command_contracts_20260827.json").read_text(encoding="utf-8"))
    main_fields = json.loads((base / "varanegar_operational_context_main_full_fields_20260827.json").read_text(encoding="utf-8"))
    stock_fields = json.loads((base / "varanegar_stock_accounting_context_full_fields_20260827.json").read_text(encoding="utf-8"))
    screen = json.loads((base / "negin_erp_operational_context_web_screen_contract_candidates_20260827.json").read_text(encoding="utf-8"))
    assert command["validation"] == "PASS"
    assert command["summary"]["target_form_count"] == 3
    assert command["summary"]["selected_method_count"] == 41
    assert command["summary"]["selected_instruction_count"] == 1105
    assert command["summary"]["unique_rule_signal_count"] == 9
    assert command["summary"]["method_with_data_context_commit_count"] == 2
    assert "OPERATIONAL_YEAR_SEPARATE_FROM_FISCAL_YEAR" in command["rule_signals"]
    assert "STOCK_TYPE_FIVE_FLAG_ENCODING" in command["rule_signals"]
    assert "STOCK_ACCOUNTING_CONTEXT_HAS_PRICE_GUARD" in command["rule_signals"]
    assert main_fields["summary"]["declared_field_count"] == 69
    assert main_fields["summary"]["web_input_candidate_count"] == 23
    assert stock_fields["summary"]["declared_field_count"] == 14
    assert stock_fields["summary"]["web_input_candidate_count"] == 3
    assert screen["validation"] == "PASS"
    assert screen["summary"]["screen_candidate_count"] == 3
    assert screen["summary"]["input_control_candidate_count"] == 26
    assert screen["summary"]["input_with_static_layout_label_candidate_count"] == 17
    assert screen["summary"]["linked_synthetic_golden_case_count"] == 96
    assert screen["summary"]["screen_with_missing_golden_contract_count"] == 0
    assert screen["summary"]["implementation_ready_screen_count"] == 0
    assert all(row["golden_contract_gap"] is None for row in screen["screens"])
    assert all(not row["runtime_golden_executed"] for row in screen["screens"])


def test_pricing_rules_preserve_context_precedence_version_and_explain_gates() -> None:
    base = ROOT / "artifacts" / "varanegar_analysis" / "ui"
    command = json.loads((base / "varanegar_pricing_rule_command_contracts_20260827.json").read_text(encoding="utf-8"))
    fields = json.loads((base / "varanegar_pricing_rule_full_fields_20260827.json").read_text(encoding="utf-8"))
    layout = json.loads((base / "varanegar_pricing_rule_layout_20260827.json").read_text(encoding="utf-8"))
    screen = json.loads((base / "negin_erp_pricing_rule_web_screen_contract_candidates_20260827.json").read_text(encoding="utf-8"))
    assert command["validation"] == "PASS"
    assert command["summary"]["target_form_count"] == 2
    assert command["summary"]["selected_method_count"] == 56
    assert command["summary"]["selected_instruction_count"] == 13433
    assert command["summary"]["unique_rule_signal_count"] == 14
    assert command["summary"]["method_with_data_context_commit_count"] == 2
    assert "CPRICE_PRIORITY_ORDER" in command["rule_signals"]
    assert "DISCOUNT_CONDITION_DSL" in command["rule_signals"]
    assert "DISCOUNT_PRIZE_AND_PACKAGE" in command["rule_signals"]
    assert fields["summary"]["declared_field_count"] == 236
    assert fields["summary"]["unresolved_field_type_count"] == 0
    assert fields["summary"]["web_input_candidate_count"] == 40
    assert layout["summary"]["layout_binding_candidate_count"] == 45
    assert screen["validation"] == "PASS"
    assert screen["summary"]["screen_candidate_count"] == 2
    assert screen["summary"]["input_control_candidate_count"] == 40
    assert screen["summary"]["input_with_static_layout_label_candidate_count"] == 32
    assert screen["summary"]["linked_synthetic_golden_case_count"] == 64
    assert screen["summary"]["screen_with_missing_golden_contract_count"] == 0
    assert screen["summary"]["implementation_ready_screen_count"] == 0
    assert all(row["golden_contract_gap"] is None for row in screen["screens"])
    assert all(not row["runtime_golden_executed"] for row in screen["screens"])
