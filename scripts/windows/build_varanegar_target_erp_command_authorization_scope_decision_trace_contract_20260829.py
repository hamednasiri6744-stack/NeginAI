"""Build a design-only command authorization, scope, and decision-trace contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "blueprint": "artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json",
    "command_ledger": "artifacts/varanegar_analysis/varanegar_command_readiness_ledger_20260829.json",
    "identity_outcome": "artifacts/varanegar_analysis/varanegar_identity_authorization_outcome_envelope_20260829.json",
    "identity_readiness": "artifacts/varanegar_analysis/varanegar_identity_authorization_readiness_delta_20260829.json",
    "identity_gap": "artifacts/varanegar_analysis/varanegar_identity_authorization_gap_triage_20260829.json",
    "role_sod": "artifacts/varanegar_analysis/ui/negin_erp_role_sod_contract_20260827.json",
    "route_matrix": "artifacts/varanegar_analysis/ui/varanegar_route_authorization_matrix_20260827.json",
    "transaction_checkpoint": "artifacts/varanegar_analysis/varanegar_target_erp_transaction_owner_saga_compensation_checkpoint_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

AUTHORIZATION_DIMENSIONS = [
    "AUTHENTICATED_PRINCIPAL_AND_SESSION",
    "TENANT_BOUNDARY",
    "COMPANY_AND_ORGANIZATION_CONTEXT",
    "FISCAL_YEAR_AND_OPERATION_DATE_CONTEXT",
    "DC_SALE_OFFICE_STOCK_AND_CENTER_SCOPE",
    "ACTION_AND_CAPABILITY_GRANT",
    "RESOURCE_OWNER_AND_ROW_SCOPE",
    "AGGREGATE_STATUS_AND_TRANSITION_SCOPE",
    "AMOUNT_RISK_OR_APPROVAL_THRESHOLD",
    "SEPARATION_OF_DUTIES_AND_SELF_APPROVAL",
    "POLICY_VERSION_FRESHNESS_AND_DENY_WINS",
    "SERVER_SIDE_DECISION_AND_REPOSITORY_ENFORCEMENT",
]

NEGATIVE_CASES = [
    ("ANC-01", "unauthenticated_or_invalid_session"),
    ("ANC-02", "tenant_reference_mismatch"),
    ("ANC-03", "company_or_organization_context_out_of_scope"),
    ("ANC-04", "fiscal_year_closed_or_operation_date_forbidden"),
    ("ANC-05", "dc_sale_office_stock_or_center_scope_missing"),
    ("ANC-06", "action_or_capability_grant_missing"),
    ("ANC-07", "resource_owner_or_row_scope_mismatch"),
    ("ANC-08", "aggregate_status_or_transition_not_allowed"),
    ("ANC-09", "amount_risk_or_approval_threshold_exceeded"),
    ("ANC-10", "self_approval_or_sod_conflict"),
    ("ANC-11", "ambient_admin_or_role_name_bypass_attempt"),
    ("ANC-12", "stale_revoked_or_policy_version_mismatched_decision"),
    ("ANC-13", "client_only_route_or_hidden_control_bypass_attempt"),
    ("ANC-14", "bulk_request_contains_mixed_authorized_and_unauthorized_resources"),
]

DECISION_TRACE_FIELDS = [
    "decision_id",
    "target_command_id",
    "principal_reference_sha256",
    "session_or_token_reference_sha256",
    "tenant_reference_sha256",
    "organization_context_reference_sha256",
    "fiscal_and_operation_context_reference_sha256",
    "resource_scope_reference_set_sha256",
    "action_capability_reference_sha256",
    "aggregate_state_reference_sha256",
    "approval_threshold_policy_reference_sha256",
    "applicable_grant_set_sha256",
    "applicable_deny_set_sha256",
    "sod_evaluation_reference_sha256",
    "policy_bundle_version_sha256",
    "policy_effective_from",
    "policy_expires_at",
    "decision_at",
    "typed_outcome",
    "reason_code_set_sha256",
    "independent_review_receipt_reference",
    "decision_trace_sha256",
]

GATES = [
    ("AUG-01", "server_authentication_and_session_validation_proven"),
    ("AUG-02", "tenant_and_organization_context_scope_enforced"),
    ("AUG-03", "fiscal_operation_date_and_location_scope_enforced"),
    ("AUG-04", "action_capability_mapping_explicit_and_versioned"),
    ("AUG-05", "resource_owner_and_row_scope_enforced_in_repository"),
    ("AUG-06", "aggregate_state_transition_scope_enforced"),
    ("AUG-07", "amount_risk_and_approval_threshold_enforced"),
    ("AUG-08", "deny_wins_over_allow_and_inherited_grants"),
    ("AUG-09", "ambient_admin_role_has_no_implicit_bypass"),
    ("AUG-10", "sod_and_self_approval_negative_rules_enforced"),
    ("AUG-11", "bulk_mixed_scope_request_fails_atomically"),
    ("AUG-12", "route_ui_api_service_and_repository_coverage_complete"),
    ("AUG-13", "decision_trace_contains_no_identity_or_business_value"),
    ("AUG-14", "policy_freshness_revocation_and_version_checks_pass"),
    ("AUG-15", "all_negative_cases_executed_in_authenticated_isolated_uat"),
    ("AUG-16", "business_owner_security_and_independent_receipts_current"),
]

ROLE_TYPES = [
    "AUTHORIZATION_POLICY_OWNER_ROLE",
    "RESOURCE_SCOPE_OWNER_ROLE",
    "SEPARATION_OF_DUTIES_REVIEWER_ROLE",
    "SECURITY_REVIEWER_ROLE",
    "INDEPENDENT_UAT_APPROVER_ROLE",
]

TYPED_OUTCOMES = [
    "ALLOW_CURRENT_ALL_SCOPES_SATISFIED",
    "DENY_UNAUTHENTICATED_OR_INVALID_SESSION",
    "DENY_TENANT_OR_ORGANIZATION_SCOPE",
    "DENY_FISCAL_OPERATION_OR_LOCATION_SCOPE",
    "DENY_ACTION_CAPABILITY_OR_RESOURCE_SCOPE",
    "DENY_STATE_THRESHOLD_OR_APPROVAL_POLICY",
    "DENY_SOD_OR_SELF_APPROVAL_CONFLICT",
    "DENY_EXPLICIT_POLICY_OR_ADMIN_BYPASS_ATTEMPT",
    "DENY_STALE_REVOKED_OR_VERSION_MISMATCHED_POLICY",
    "DENY_TRACE_INCOMPLETE_OR_ENFORCEMENT_PATH_UNPROVEN",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_hash(values: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(values), separators=(",", ":")).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True, type=Path); args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}; documents = {name: load(path) for name, path in paths.items()}
    modules = documents["blueprint"]["modules"]
    commands = []
    for module in modules:
        for command_name in module["commands"]:
            commands.append({
                "target_command_id": f"TCMD-{len(commands) + 1:03d}",
                "module_id": module["id"],
                "command_name": command_name,
                "owned_concept_set_sha256": set_hash(module["owns"]),
                "authorization_policy_status": "DESIGNED_NOT_IMPLEMENTED",
                "runtime_authorization_status": "UNPROVEN",
                "decision_trace_status": "MISSING",
                "owner_approval_status": "MISSING",
                "command_readiness": False,
            })
    dimension_assignments = [{"target_command_id": command["target_command_id"], "authorization_dimension": dimension, "status": "UNPROVEN", "accepted_decision_trace_count": 0} for command in commands for dimension in AUTHORIZATION_DIMENSIONS]
    negative_assignments = [{"target_command_id": command["target_command_id"], "negative_case_id": case_id, "status": "UNEXECUTED", "accepted_decision_trace_count": 0} for command in commands for case_id, _ in NEGATIVE_CASES]
    gate_assignments = [{"target_command_id": command["target_command_id"], "gate_id": gate_id, "status": "UNMET", "accepted_evidence_count": 0} for command in commands for gate_id, _ in GATES]
    role_assignments = [{"target_command_id": command["target_command_id"], "role_type": role_type, "status": "UNASSIGNED", "role_receipt_reference": None} for command in commands for role_type in ROLE_TYPES]
    official = documents["tests"]
    summary = {
        "module_count": len(modules), "target_command_count": len(commands),
        "authorization_dimension_count": len(AUTHORIZATION_DIMENSIONS), "command_dimension_assignment_count": len(dimension_assignments),
        "negative_case_count": len(NEGATIVE_CASES), "command_negative_case_assignment_count": len(negative_assignments),
        "decision_trace_field_count": len(DECISION_TRACE_FIELDS), "gate_count": len(GATES), "command_gate_assignment_count": len(gate_assignments),
        "role_type_count": len(ROLE_TYPES), "command_role_assignment_count": len(role_assignments), "typed_outcome_count": len(TYPED_OUTCOMES),
        "implemented_server_authorization_count": 0, "authenticated_isolated_uat_run_count": 0, "accepted_allow_trace_count": 0,
        "accepted_deny_trace_count": 0, "repository_scope_proven_command_count": 0, "route_to_repository_coverage_proven_command_count": 0,
        "owner_approved_command_count": 0, "runtime_authorization_proven_command_count": 0, "command_ready_count": 0, "pilot_ready_module_count": 0,
        "design_lower_bound_before_authorization_contract": 1404, "design_lower_bound_after_authorization_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"], "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"], "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"], "new_risk_count": 0,
    }
    checks = {
        "current_sources_pass": all(documents[name].get("validation") == "PASS" for name in ("command_ledger", "identity_outcome", "identity_readiness", "identity_gap", "transaction_checkpoint", "tests")),
        "historical_contract_identity_pinned": documents["role_sod"].get("artifact") == "negin_erp_identity_free_role_and_sod_contract" and documents["role_sod"].get("schema_version") == 1 and documents["route_matrix"].get("artifact") == "varanegar_open_route_anonymous_authorization_matrix" and documents["route_matrix"].get("schema_version") == 1,
        "blueprint_14_modules_49_commands": (summary["module_count"], summary["target_command_count"]) == (14, 49),
        "dimensions_12_assignments_588": (summary["authorization_dimension_count"], summary["command_dimension_assignment_count"]) == (12, 588),
        "negative_14_assignments_686": (summary["negative_case_count"], summary["command_negative_case_assignment_count"]) == (14, 686),
        "decision_fields_22_gates_16_assignments_784": (summary["decision_trace_field_count"], summary["gate_count"], summary["command_gate_assignment_count"]) == (22, 16, 784),
        "roles_5_assignments_245_outcomes_10": (summary["role_type_count"], summary["command_role_assignment_count"], summary["typed_outcome_count"]) == (5, 245, 10),
        "all_dimensions_negative_gates_roles_open": all(x["status"] == "UNPROVEN" for x in dimension_assignments) and all(x["status"] == "UNEXECUTED" for x in negative_assignments) and all(x["status"] == "UNMET" for x in gate_assignments) and all(x["status"] == "UNASSIGNED" for x in role_assignments),
        "implementation_uat_trace_runtime_readiness_zero": summary["implemented_server_authorization_count"] == summary["authenticated_isolated_uat_run_count"] == summary["accepted_allow_trace_count"] == summary["accepted_deny_trace_count"] == summary["repository_scope_proven_command_count"] == summary["route_to_repository_coverage_proven_command_count"] == summary["owner_approved_command_count"] == summary["runtime_authorization_proven_command_count"] == summary["command_ready_count"] == summary["pilot_ready_module_count"] == 0,
        "non_additive_1404": summary["design_lower_bound_before_authorization_contract"] == summary["design_lower_bound_after_authorization_contract"] == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_command_authorization_scope_decision_trace_contract_20260829", "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(), "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "target_command_authorization_scope_and_trace_design_only", "continuation_complete": False, "authentication_or_command_executed": False, "identity_provider_or_policy_engine_selected": False},
        "safety": {"database_connections": 0, "network_reads_or_writes": 0, "authentication_sessions_commands_or_authorization_uat_executed": 0, "operational_forms_reports_queries_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "credentials_tokens_identity_pii_or_raw_business_values_read_or_persisted": 0},
        "summary": summary, "risk_links": ["R-003", "R-057", "R-058", "R-059", "R-004", "R-001", "R-025"],
        "authorization_dimensions": AUTHORIZATION_DIMENSIONS,
        "negative_cases": [{"negative_case_id": case_id, "negative_case": case} for case_id, case in NEGATIVE_CASES],
        "decision_trace_fields": DECISION_TRACE_FIELDS,
        "gates": [{"gate_id": gate_id, "gate": gate, "failure_effect": "COMMAND_AUTHORIZATION_NOT_READY"} for gate_id, gate in GATES],
        "role_types": ROLE_TYPES, "typed_outcomes": TYPED_OUTCOMES,
        "target_command_authorization_contracts": commands, "command_dimension_assignments": dimension_assignments,
        "command_negative_case_assignments": negative_assignments, "command_gate_assignments": gate_assignments, "command_role_assignments": role_assignments,
        "authorization_rule": {
            "default_allow": False, "explicit_deny_wins": True, "ambient_admin_or_role_name_bypass_allowed": False,
            "client_ui_or_route_visibility_is_authorization": False, "server_service_only_check_without_repository_scope_is_sufficient": False,
            "bulk_mixed_scope_partial_success_allowed": False, "self_approval_allowed": False,
            "stale_revoked_or_version_mismatched_policy_allows_command": False,
            "decision_trace_may_persist_identity_pii_token_or_business_value": False,
            "legacy_aggregate_right_or_code_existence_creates_target_grant": False,
            "automatic_authorization_or_command_readiness": False,
        },
        "checks": checks, "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)} for name, path in sorted(paths.items())] + [{"name": "builder", "path": "scripts/windows/build_varanegar_target_erp_command_authorization_scope_decision_trace_contract_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha256(Path(__file__))}],
        "limits": [
            "This is a target authorization design contract and does not infer grants from legacy aggregate rights route presence or role names.",
            "No identity token session credential command route repository database or business value was accessed or executed.",
            "Runtime authorization and readiness remain zero until authenticated isolated negative and positive UAT receipts are accepted per command.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve()); print(output["validation"]); print(json.dumps(summary, ensure_ascii=False)); return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
