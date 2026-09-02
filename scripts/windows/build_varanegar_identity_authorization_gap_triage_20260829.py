"""Build an offline triage of NGT authorization declaration and scope gaps."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "endpoint": "artifacts/varanegar_analysis/domains/ngt_authorization_endpoint_coverage_20260828.json",
    "manual": "artifacts/varanegar_analysis/domains/ngt_authorization_manual_guard_boundary_20260829.json",
    "owner": "artifacts/varanegar_analysis/domains/ngt_owner_scope_effective_boundary_20260829.json",
    "effective": "artifacts/varanegar_analysis/domains/ngt_authorization_effective_boundary_20260828.json",
    "short_circuit": "artifacts/varanegar_analysis/domains/ngt_authorization_role_short_circuit_20260829.json",
    "navigation": "artifacts/varanegar_analysis/ui/varanegar_identity_access_navigation_gap_contract_20260827.json",
    "role_uat": "artifacts/varanegar_analysis/ui/negin_erp_role_uat_cases_20260827.json",
    "intake": "artifacts/varanegar_analysis/varanegar_authorization_runtime_evidence_intake_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_checkpoint_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signal_class(row: dict) -> str:
    if row["manual_authorization_decision_candidate"]:
        return "NAMED_AUTHORIZATION_DECISION"
    if row["authorization_data_only_candidate"]:
        return "AUTHORIZATION_DATA_ONLY_NOT_ENFORCEMENT"
    if row["identity_context_only_candidate"]:
        return "IDENTITY_CONTEXT_ONLY_NOT_ENFORCEMENT"
    return "NO_NAMED_DECISION_DATA_OR_IDENTITY_SIGNAL"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    rows = data["manual"]["endpoints"]
    mutating_verbs = {"POST", "PUT", "PATCH", "DELETE"}
    mutating = [row for row in rows if set(row["http_verbs"]) & mutating_verbs]
    read_side = [row for row in rows if not set(row["http_verbs"]) & mutating_verbs]
    verb_counts = Counter(verb for row in rows for verb in row["http_verbs"])
    all_signal_counts = Counter(signal_class(row) for row in rows)
    mutating_signal_counts = Counter(signal_class(row) for row in mutating)
    read_signal_counts = Counter(signal_class(row) for row in read_side)
    scope = data["owner"]["user_group_scope_consistency"]

    lanes = [
        {
            "priority": 1,
            "id": "IA-GAP-01",
            "lane": "MUTATING_ENDPOINT_DECLARATION_AND_DENY_BEFORE_HANDLER",
            "required_unit_count": len(mutating),
            "current_accepted_unit_count": 0,
            "required_evidence": "explicit protected declaration or approved anonymous/removal disposition plus unauthenticated, unauthorized, wrong-scope and revoked-session deny-before-handler receipts",
        },
        {
            "priority": 2,
            "id": "IA-GAP-02",
            "lane": "MEMBERSHIP_USER_SCOPE_MISMATCH_DISPOSITION",
            "required_unit_count": scope["membership_user_scope_mismatch"],
            "current_accepted_unit_count": 0,
            "required_evidence": "owner-approved repair/quarantine/retire disposition with pre/post hierarchy digest and zero silent cross-scope grant",
        },
        {
            "priority": 3,
            "id": "IA-GAP-03",
            "lane": "READ_ENDPOINT_DECLARATION_AND_NO_EXISTENCE_LEAK",
            "required_unit_count": len(read_side),
            "current_accepted_unit_count": 0,
            "required_evidence": "explicit declaration/disposition and deny/no-resource-existence-leak receipt under missing capability and wrong scope",
        },
        {
            "priority": 4,
            "id": "IA-GAP-04",
            "lane": "RESOURCE_ACTION_CONFIGURATION_DISPOSITION",
            "required_unit_count": data["effective"]["summary"]["resource_action_contract_absent_from_all_application_owners_count"],
            "current_accepted_unit_count": 0,
            "required_evidence": "versioned owner-approved mapping or deliberate fail-closed removal for every absent normalized Resource/Action declaration",
        },
        {
            "priority": 5,
            "id": "IA-GAP-05",
            "lane": "ADMIN_SHORT_CIRCUIT_POLICY",
            "required_unit_count": 1,
            "current_accepted_unit_count": 0,
            "required_evidence": "security-owner decision for deny precedence, scope, audit and break-glass behavior when the admin role would bypass base authorization",
        },
        {
            "priority": 6,
            "id": "IA-GAP-06",
            "lane": "OWNER_FILTERED_PERMISSION_REPOSITORY",
            "required_unit_count": 1,
            "current_accepted_unit_count": 0,
            "required_evidence": "static implementation and isolated negative tests proving every permission lookup is application-owner/resource-scope filtered",
        },
        {
            "priority": 7,
            "id": "IA-GAP-07",
            "lane": "IDENTITY_ACCESS_ROUTE_DISPOSITION",
            "required_unit_count": data["navigation"]["summary"]["identity_access_route_candidate_count"],
            "current_accepted_unit_count": 0,
            "required_evidence": "route-to-capability and owner-scope mapping or explicit retirement for each navigation candidate; UI visibility is not enforcement",
        },
    ]
    summary = {
        "attribute_declared_endpoint_count": data["endpoint"]["summary"]["attribute_declared_endpoint_count"],
        "declaration_gap_endpoint_count": len(rows),
        "mutating_declaration_gap_endpoint_count": len(mutating),
        "read_declaration_gap_endpoint_count": len(read_side),
        "gap_http_verb_counts": dict(sorted(verb_counts.items())),
        "async_state_machine_followed_count": sum(row["async_state_machine_followed"] for row in rows),
        "mutating_async_state_machine_followed_count": sum(row["async_state_machine_followed"] for row in mutating),
        "read_async_state_machine_followed_count": sum(row["async_state_machine_followed"] for row in read_side),
        "named_manual_authorization_decision_candidate_count": all_signal_counts["NAMED_AUTHORIZATION_DECISION"],
        "authorization_data_only_candidate_count": all_signal_counts["AUTHORIZATION_DATA_ONLY_NOT_ENFORCEMENT"],
        "identity_context_only_candidate_count": all_signal_counts["IDENTITY_CONTEXT_ONLY_NOT_ENFORCEMENT"],
        "no_named_decision_data_or_identity_signal_count": all_signal_counts["NO_NAMED_DECISION_DATA_OR_IDENTITY_SIGNAL"],
        "mutating_signal_class_counts": dict(sorted(mutating_signal_counts.items())),
        "read_signal_class_counts": dict(sorted(read_signal_counts.items())),
        "scope_consistency_mismatch_count": data["owner"]["summary"]["scope_consistency_mismatch_count"],
        "membership_user_scope_mismatch_count": scope["membership_user_scope_mismatch"],
        "other_scope_mismatch_count": sum(value for key, value in scope.items() if key != "membership_user_scope_mismatch"),
        "orphan_membership_user_count": data["owner"]["owner_hierarchy_integrity"]["orphan_membership_user"],
        "cross_type_owner_key_collision_count": data["owner"]["summary"]["cross_type_owner_key_collision_count"],
        "resource_action_contract_absent_count": data["effective"]["summary"]["resource_action_contract_absent_from_all_application_owners_count"],
        "admin_role_short_circuit_present": data["short_circuit"]["summary"]["admin_role_short_circuits_base_authorization"],
        "admin_role_current_assignment_subject_count": data["effective"]["summary"]["admin_role_current_assignment_subject_count"],
        "authorization_repository_owner_filtered": data["owner"]["summary"]["authorization_permission_repository_path_is_owner_filtered"],
        "identity_access_route_candidate_count": data["navigation"]["summary"]["identity_access_route_candidate_count"],
        "runtime_matched_identity_form_count": data["navigation"]["summary"]["runtime_matched_form_count"],
        "synthetic_role_uat_case_count": data["role_uat"]["summary"]["synthetic_uat_case_count"],
        "owner_approved_role_uat_case_count": data["role_uat"]["summary"]["owner_approved_case_count"],
        "triage_lane_count": len(lanes),
        "triage_required_unit_count": sum(row["required_unit_count"] for row in lanes),
        "triage_current_accepted_unit_count": 0,
        "runtime_authorization_proven_module_count": data["intake"]["summary"]["runtime_authorization_proven_module_count"],
        "security_approved_module_count": data["intake"]["summary"]["security_approved_module_count"],
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value.get("validation", "PASS") == "PASS" for value in data.values()),
        "gap_60_split_38_22": summary["declaration_gap_endpoint_count"] == 60
        and summary["mutating_declaration_gap_endpoint_count"] == 38
        and summary["read_declaration_gap_endpoint_count"] == 22,
        "verbs_31_6_1_22": summary["gap_http_verb_counts"] == {"DELETE": 1, "GET": 22, "POST": 31, "PUT": 6},
        "manual_signals_0_6_3_51": summary["named_manual_authorization_decision_candidate_count"] == 0
        and summary["authorization_data_only_candidate_count"] == 6
        and summary["identity_context_only_candidate_count"] == 3
        and summary["no_named_decision_data_or_identity_signal_count"] == 51,
        "async_43_split_32_11": summary["async_state_machine_followed_count"] == 43
        and summary["mutating_async_state_machine_followed_count"] == 32
        and summary["read_async_state_machine_followed_count"] == 11,
        "scope_58_one_class": summary["scope_consistency_mismatch_count"]
        == summary["membership_user_scope_mismatch_count"]
        == 58
        and summary["other_scope_mismatch_count"] == 0,
        "structural_boundaries_preserved": summary["resource_action_contract_absent_count"] == 3
        and summary["admin_role_short_circuit_present"] is True
        and summary["authorization_repository_owner_filtered"] is False,
        "seven_lanes_139_units": summary["triage_lane_count"] == 7 and summary["triage_required_unit_count"] == 139,
        "role_uat_design_184_approval_zero": summary["synthetic_role_uat_case_count"] == 184
        and summary["owner_approved_role_uat_case_count"] == 0,
        "runtime_security_readiness_zero": summary["triage_current_accepted_unit_count"]
        == summary["runtime_authorization_proven_module_count"]
        == summary["security_approved_module_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_identity_authorization_gap_triage_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_HASH_PINNED_AUTHORIZATION_METADATA_AND_STATIC_IL_TRIAGE",
            "gate_id": "CG-01",
            "anonymous_reachability_or_incident_claimed": False,
            "cg01_closed": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "endpoints_forms_commands_or_identity_operations_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "credentials_person_identity_or_raw_permission_values_persisted": 0,
            "data_mutations": 0,
            "write_access_created": 0,
        },
        "summary": summary,
        "triage_lanes": lanes,
        "classification_rules": [
            "Absence of an endpoint declaration is a verification gap, not proof of anonymous reachability or a production incident.",
            "Reading permission catalog data is not an authorization decision and reading current-user identity is not resource-scope enforcement.",
            "Mutating POST, PUT and DELETE gaps require deny-before-handler evidence; a UI guard is insufficient.",
            "Read gaps must deny without leaking resource or aggregate existence.",
            "All 58 scope mismatches are membership-user scope mismatches in the persisted snapshot; they are not generalized to every scope dimension.",
            "Admin short-circuit presence does not prove misuse, but deny precedence, resource scope and audit behavior remain unproven.",
            "Three missing Resource/Action mappings are classified as fail-closed availability/configuration gaps, not grants.",
        ],
        "required_endpoint_disposition_states": [
            "PROTECTED_BY_EXPLICIT_DECLARATION_AND_RUNTIME_DENY_RECEIPTS",
            "EXPLICIT_ANONYMOUS_WITH_OWNER_AND_SECURITY_APPROVAL",
            "REMOVED_OR_UNROUTABLE_WITH_STATIC_AND_RUNTIME_RECEIPTS",
            "REJECTED_INCOMPLETE_OR_UNVERIFIED",
        ],
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_identity_authorization_gap_triage_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This triage classifies persisted metadata and static IL signals; it does not authenticate, call endpoints or modify identity data.",
            "Obfuscated/delegated host or middleware authorization is not excluded and requires isolated runtime evidence.",
            "No endpoint, scope mismatch, role case or route is accepted by this artifact.",
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
