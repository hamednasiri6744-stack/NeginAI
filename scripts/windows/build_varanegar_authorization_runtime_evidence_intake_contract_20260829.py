"""Build the CG-01 authenticated authorization and scope runtime evidence intake contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "priority": "artifacts/varanegar_analysis/varanegar_external_evidence_gate_priority_map_20260829.json",
    "readiness": "artifacts/varanegar_analysis/varanegar_platform_readiness_delta_20260829.json",
    "identity_outcome": "artifacts/varanegar_analysis/varanegar_identity_authorization_outcome_envelope_20260829.json",
    "identity_golden": "artifacts/varanegar_analysis/varanegar_identity_authorization_golden_uat_cases_20260829.json",
    "identity_playbook": "artifacts/varanegar_analysis/varanegar_identity_authorization_expert_playbook_20260829.json",
    "platform_intake": "artifacts/varanegar_analysis/varanegar_platform_decision_evidence_intake_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_checkpoint_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    cg01 = next(row for row in data["priority"]["priority_map"] if row["gate_id"] == "CG-01")

    scenario_categories = [
        {"id": "AUTH-01", "scenario": "authenticated explicit allow within capability and resource scope", "expected": "ALLOW"},
        {"id": "AUTH-02", "scenario": "explicit deny conflicts with direct, group, inherited or admin allow", "expected": "DENY"},
        {"id": "AUTH-03", "scenario": "missing action capability", "expected": "DENY"},
        {"id": "AUTH-04", "scenario": "valid capability but mismatched organization/resource scope", "expected": "DENY"},
        {"id": "AUTH-05", "scenario": "stale session epoch after revoke", "expected": "DENY_AND_SESSION_INVALIDATED"},
        {"id": "AUTH-06", "scenario": "segregation-of-duties conflict", "expected": "DENY_OR_INDEPENDENT_APPROVAL_REQUIRED"},
        {"id": "AUTH-07", "scenario": "break-glass request outside approved window or scope", "expected": "DENY_AND_AUDIT"},
        {"id": "AUTH-08", "scenario": "server-side resource check differs from UI visibility", "expected": "SERVER_DECISION_CONTROLS"},
    ]
    required_packet_fields = [
        "module",
        "scenario_set_manifest_hash",
        "synthetic_principal_reference_hash",
        "role_template_reference_hash",
        "capability_reference_hash",
        "resource_scope_reference_hash",
        "session_epoch_reference_hash",
        "policy_version_reference_hash",
        "expected_decision_manifest_hash",
        "actual_decision_receipt_hash",
        "server_enforcement_receipt_hash",
        "audit_receipt_hash",
        "negative_case_manifest_hash",
        "security_approval_reference_hash",
        "business_owner_approval_reference_hash",
    ]
    modules = []
    for row in data["readiness"]["modules"]:
        authorization = row["truth_table_dimensions"]["authorization"]
        modules.append(
            {
                "module": row["module"],
                "authorization_design_evidence": authorization["design_evidence"],
                "runtime_authorization_proven": authorization["runtime_proven"],
                "required_scenario_category_ids": [item["id"] for item in scenario_categories],
                "required_packet_field_count": len(required_packet_fields),
                "current_packet_status": "WAITING_FOR_APPROVED_CG06_AND_RUNTIME_EXECUTION",
                "accepted_packet_count": 0,
                "owner_approved_count": 0,
                "security_approved_count": 0,
                "command_ready": False,
                "pilot_ready": False,
            }
        )
    summary = {
        "cg01_priority_rank": cg01["priority_rank"],
        "module_count": len(modules),
        "authorization_design_module_count": sum(row["authorization_design_evidence"] for row in modules),
        "runtime_authorization_proven_module_count": sum(row["runtime_authorization_proven"] for row in modules),
        "scenario_category_count": len(scenario_categories),
        "required_packet_field_count": len(required_packet_fields),
        "accepted_module_packet_count": sum(row["accepted_packet_count"] for row in modules),
        "owner_approved_module_count": sum(row["owner_approved_count"] for row in modules),
        "security_approved_module_count": sum(row["security_approved_count"] for row in modules),
        "cg06_required_current_decision_slot_count": data["platform_intake"]["cg06_closure_rule"]["required_current_slot_count"],
        "cg06_current_accepted_decision_slot_count": data["platform_intake"]["cg06_closure_rule"]["current_accepted_slot_count"],
        "identity_existing_role_uat_design_count": data["identity_golden"]["summary"]["existing_reused_case_count"],
        "identity_delta_acceptance_design_count": data["identity_golden"]["summary"]["delta_case_count"],
        "identity_combined_acceptance_design_count": data["identity_golden"]["summary"]["combined_identity_acceptance_design_count"],
        "identity_playbook_count": data["identity_playbook"]["summary"]["playbook_count"],
        "identity_endpoint_without_declaration_count": data["identity_outcome"]["summary"]["endpoint_without_declared_authorization_count"],
        "identity_mutating_endpoint_without_declaration_count": data["identity_outcome"]["summary"]["mutating_endpoint_without_declared_authorization_count"],
        "identity_scope_mismatch_count": data["identity_outcome"]["summary"]["scope_consistency_mismatch_count"],
        "cg01_closed_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "cg01_is_runtime_foundation": cg01["priority_rank"] == 3 and cg01["lane"] == "ISOLATED_RUNTIME_FOUNDATION",
        "fourteen_unique_modules": len(modules) == len({row["module"] for row in modules}) == 14,
        "design_14_runtime_0": summary["authorization_design_module_count"] == 14
        and summary["runtime_authorization_proven_module_count"] == 0,
        "eight_scenario_categories": summary["scenario_category_count"] == 8
        and len({item["id"] for item in scenario_categories}) == 8,
        "packet_schema_15": summary["required_packet_field_count"] == 15,
        "deny_and_server_controls_present": {item["expected"] for item in scenario_categories}
        >= {"DENY", "DENY_AND_SESSION_INVALIDATED", "SERVER_DECISION_CONTROLS"},
        "cg06_dependency_open": summary["cg06_required_current_decision_slot_count"] == 8
        and summary["cg06_current_accepted_decision_slot_count"] == 0,
        "identity_design_and_blockers_stable": summary["identity_existing_role_uat_design_count"] == 184
        and summary["identity_delta_acceptance_design_count"] == 42
        and summary["identity_combined_acceptance_design_count"] == 226
        and summary["identity_playbook_count"] == 7
        and summary["identity_endpoint_without_declaration_count"] == 60
        and summary["identity_mutating_endpoint_without_declaration_count"] == 38
        and summary["identity_scope_mismatch_count"] == 58,
        "acceptance_owner_security_readiness_zero": summary["accepted_module_packet_count"]
        == summary["owner_approved_module_count"]
        == summary["security_approved_module_count"]
        == summary["cg01_closed_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_authorization_runtime_evidence_intake_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_AUTHENTICATED_AUTHORIZATION_RUNTIME_EVIDENCE_INTAKE_DESIGN",
            "gate_id": "CG-01",
            "runtime_execution_requires_cg06_accepted": True,
            "gate_closed": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "authentication_sessions_or_authorization_commands_executed": 0,
            "identity_assignments_grants_revokes_or_repairs_performed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "identity_values_credentials_or_raw_grants_read_or_persisted": 0,
        },
        "summary": summary,
        "scenario_categories": scenario_categories,
        "packet_schema": {
            "required_fields": required_packet_fields,
            "prohibited_fields": [
                "person_name_or_identity",
                "credential_or_token",
                "raw_membership_or_grant_row",
                "raw_business_resource_value",
                "production_endpoint_or_session_identifier",
            ],
            "acceptance_rule": "All eight categories execute with synthetic authenticated principals in the approved isolated environment; server-side decisions match expected deny-first capability/scope/session/SoD policy; owner and security approvals reference the immutable receipts.",
        },
        "module_intake_map": modules,
        "global_validation_rules": [
            "UI visibility or client-side guard never substitutes for a server-side decision receipt.",
            "Count equality never proves principal, role, membership or effective grant identity.",
            "Explicit deny precedes direct, group, inherited and admin allow.",
            "Action capability, organization/resource scope, session epoch and SoD are independently evidenced.",
            "Break-glass requires bounded scope/window, independent approval and immutable audit receipt.",
            "No identity, credential, membership row, permission value or production session id is stored in this artifact.",
        ],
        "cg01_closure_rule": {
            "required_accepted_module_packet_count": 14,
            "current_accepted_module_packet_count": 0,
            "required_scenario_category_count_per_module": 8,
            "status": "OPEN_EXTERNAL_RUNTIME_GATE",
            "rule": "CG-01 closes only after CG-06 acceptance and fourteen owner/security-approved module packets with all eight categories and zero unexplained authorization difference.",
        },
        "checks": checks,
        "failed_checks": failed,
        "risk_links": ["R-001", "R-002", "R-006", "R-007", "R-008", "R-023", "R-031", "R-034", "R-056", "R-057", "R-059", "R-062"],
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_authorization_runtime_evidence_intake_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This is an intake design, not authenticated runtime evidence.",
            "CG-06 is open, so no runtime execution or readiness promotion is claimed.",
            "Existing identity endpoint/scope blockers remain unresolved and are not generalized as incidents in every module.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
