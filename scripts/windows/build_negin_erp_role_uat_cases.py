"""Build identity-free synthetic UAT cases for provisional ERP role templates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roles", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    roles = _load(args.roles)
    cases: list[dict[str, Any]] = []

    def add(category: str, role: str | None, subject: str, expected: str, evidence_ref: str) -> None:
        cases.append({
            "case_id": f"RBAC-{len(cases) + 1:03d}",
            "category": category,
            "role_template": role,
            "subject": subject,
            "expected_decision_or_control": expected,
            "evidence_ref": evidence_ref,
            "uses_named_identity_or_current_grant": False,
            "production_assignment_or_approval": False,
            "status": "SYNTHETIC_REQUIRES_OWNER_UAT",
        })

    for role in roles["role_templates"]:
        role_id = role["role"]
        for capability in role["allow"]:
            add("allow", role_id, capability, "ALLOW only inside fresh authenticated context, effective scope, enabled feature and valid domain state", role_id)
        for deny_pattern in role["deny"]:
            add("deny_pattern", role_id, deny_pattern, "DENY overrides group or wildcard allow and emits explanation/audit without leaking data", role_id)
        add("context_invalidation", role_id, "switch fiscal year, DC, stock, office or tenant context", "previous authorization decision and cached rows are invalidated; request is reauthorized", role_id)

    for rule in roles["sod_rules"]:
        add("segregation_of_duties", None, rule["id"], f"BLOCK or require the declared independent approval control: {rule['control']}", rule["id"])
    for index, scenario in enumerate(roles["mandatory_negative_tests"], 1):
        add("mandatory_negative", None, scenario, "DENY or reauthorize exactly as the scenario requires; record safe reason and correlation", f"mandatory_negative_tests[{index}]")
    for index, claim in enumerate(roles["not_inferred_from_aggregate_legacy_evidence"], 1):
        add("non_inference", None, claim, "MUST_REMAIN_UNKNOWN until explicit owner-approved provisioning evidence exists", f"not_inferred[{index}]")

    errors = []
    atomic = set(roles["atomic_capabilities"])
    if any(capability not in atomic for role in roles["role_templates"] for capability in role["allow"]):
        errors.append("role allow contains unknown atomic capability")
    if roles.get("status") != "PROVISIONAL_TEMPLATES_REQUIRE_BUSINESS_OWNER_SIGNOFF":
        errors.append("source role template status changed")
    if any(case["uses_named_identity_or_current_grant"] or case["production_assignment_or_approval"] for case in cases):
        errors.append("identity or production approval leaked into synthetic cases")
    category_counts = Counter(case["category"] for case in cases)
    artifact = {
        "artifact": "negin_erp_identity_free_role_scope_sod_synthetic_uat_cases",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "SYNTHETIC_UAT_DESIGN_REQUIRES_BUSINESS_OWNER_SIGNOFF",
        "safety": {
            "mode": "OFFLINE_CASE_GENERATION_FROM_IDENTITY_FREE_ROLE_TEMPLATES",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "named_identities_current_grants_or_assignments_read_or_persisted": 0,
            "production_role_assignment_or_authorization_granted": 0,
        },
        "summary": {
            "role_template_count": roles["role_template_count"],
            "atomic_capability_count": roles["atomic_capability_count"],
            "allow_assignment_case_count": category_counts["allow"],
            "deny_pattern_case_count": category_counts["deny_pattern"],
            "context_invalidation_case_count": category_counts["context_invalidation"],
            "sod_case_count": category_counts["segregation_of_duties"],
            "mandatory_negative_case_count": category_counts["mandatory_negative"],
            "non_inference_case_count": category_counts["non_inference"],
            "synthetic_uat_case_count": len(cases),
            "owner_approved_case_count": 0,
            "production_assignment_count": 0,
            "validation_error_count": len(errors),
        },
        "cases": cases,
        "approval_gate": {
            "required_before_identity_provisioning": [
                "business owner approves each role purpose and allow list",
                "security owner approves deny precedence, scope dimensions and break-glass policy",
                "financial controller approves material SoD rules",
                "authenticated UAT proves allow, deny, scope, context invalidation and audit readback",
            ],
            "current_gate_status": "BLOCKED_BY_OWNER_SIGNOFF_AND_RUNTIME_UAT",
        },
        "validation_errors": errors,
        "limits": [
            "Cases are generated from provisional templates, not from named users or current production grants.",
            "Passing unit or policy tests cannot replace authenticated role UAT and provisioning readback.",
            "No role, scope, approval or break-glass assignment is created by this artifact.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
