"""Build identity-free role/UAT obligations for bank reconciliation."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


LEGACY_BASE_CAPABILITIES = (
    "bank_reconciliation.view",
    "bank_reconciliation.import_statement",
    "bank_reconciliation.match_instrument",
    "bank_reconciliation.unmatch_instrument",
    "bank_reconciliation.confirm",
    "bank_reconciliation.cancel",
)
CAPABILITIES = LEGACY_BASE_CAPABILITIES + (
    "bank_reconciliation.reverse_confirmed_session",
)
ROLE_TEMPLATES = (
    {
        "role": "bank_reconciliation_viewer",
        "purpose": "scoped read and summary only",
        "allow": ("bank_reconciliation.view",),
    },
    {
        "role": "bank_statement_importer",
        "purpose": "upload, preview and commit an approved statement profile",
        "allow": (
            "bank_reconciliation.view",
            "bank_reconciliation.import_statement",
        ),
    },
    {
        "role": "bank_reconciliation_matcher",
        "purpose": "match and unmatch an unconfirmed scoped session",
        "allow": (
            "bank_reconciliation.view",
            "bank_reconciliation.match_instrument",
            "bank_reconciliation.unmatch_instrument",
        ),
    },
    {
        "role": "bank_reconciliation_confirmer",
        "purpose": "independent confirmation after reconciliation checks",
        "allow": (
            "bank_reconciliation.view",
            "bank_reconciliation.confirm",
        ),
    },
    {
        "role": "bank_reconciliation_supervisor",
        "purpose": "provisional session cancellation subject to owner policy",
        "allow": (
            "bank_reconciliation.view",
            "bank_reconciliation.cancel",
        ),
    },
    {
        "role": "bank_reconciliation_reversal_authorizer",
        "purpose": "independent audited reversal of a confirmed session after owner approval",
        "allow": (
            "bank_reconciliation.view",
            "bank_reconciliation.reverse_confirmed_session",
        ),
    },
)
CONTEXT_VARIATIONS = (
    "account_scope_denied",
    "closed_operation_date",
    "wrong_fiscal_year_or_dc",
    "stale_expected_version",
    "feature_or_entitlement_disabled",
)
STATE_PROFILE_CASES = (
    ("match_requires_unconfirmed", "bank_reconciliation.match_instrument", "CONFIRMED", "DENY"),
    ("unmatch_requires_unconfirmed", "bank_reconciliation.unmatch_instrument", "CONFIRMED", "DENY"),
    ("confirm_from_unconfirmed", "bank_reconciliation.confirm", "IMPORTED_UNCONFIRMED", "ALLOW_IF_ALL_OTHER_GATES_PASS"),
    ("confirm_retry_from_confirmed", "bank_reconciliation.confirm", "CONFIRMED", "RETURN_ORIGINAL_RESULT"),
    ("confirm_inconsistent_markers", "bank_reconciliation.confirm", "INCONSISTENT_LEGACY_MARKERS_QUARANTINED", "DENY"),
    ("cancel_confirmed_without_reversal", "bank_reconciliation.cancel", "CONFIRMED", "DENY"),
    ("unapproved_profile", "bank_reconciliation.import_statement", "PROFILE_UNAPPROVED", "DENY_BEFORE_PARSER"),
    ("changed_profile_after_preview", "bank_reconciliation.import_statement", "PROFILE_VERSION_CHANGED", "DENY_STALE_VERSION"),
    ("raw_sql_provider_or_path", "bank_reconciliation.import_statement", "EXECUTABLE_PROFILE_INPUT", "DENY_BEFORE_PARSER"),
    ("unsupported_or_spoofed_extension", "bank_reconciliation.import_statement", "FORMAT_INVALID", "DENY_BEFORE_PARSER"),
    ("summary_formula_unvalidated", "bank_reconciliation.confirm", "PARITY_NOT_APPROVED", "DENY_PILOT_GATE"),
    ("amount_tolerance_unvalidated", "bank_reconciliation.match_instrument", "PARITY_NOT_APPROVED", "DENY_AUTOMATIC_MATCH"),
    ("reverse_from_confirmed", "bank_reconciliation.reverse_confirmed_session", "CONFIRMED", "ALLOW_IF_OWNER_POLICY_AND_ALL_OTHER_GATES_PASS"),
    ("reverse_from_unconfirmed", "bank_reconciliation.reverse_confirmed_session", "IMPORTED_UNCONFIRMED", "DENY"),
    ("reverse_inconsistent_markers", "bank_reconciliation.reverse_confirmed_session", "INCONSISTENT_LEGACY_MARKERS_QUARANTINED", "DENY"),
)
SOD_RULES = (
    ("importer_cannot_confirm_own_batch", "bank_reconciliation.import_statement", "bank_reconciliation.confirm"),
    ("matcher_cannot_confirm_own_session", "bank_reconciliation.match_instrument", "bank_reconciliation.confirm"),
    ("unmatcher_cannot_confirm_same_session", "bank_reconciliation.unmatch_instrument", "bank_reconciliation.confirm"),
    ("confirmer_cannot_cancel_same_session", "bank_reconciliation.confirm", "bank_reconciliation.cancel"),
    ("importer_cannot_reverse_own_batch", "bank_reconciliation.import_statement", "bank_reconciliation.reverse_confirmed_session"),
    ("matcher_cannot_reverse_same_session", "bank_reconciliation.match_instrument", "bank_reconciliation.reverse_confirmed_session"),
    ("confirmer_cannot_reverse_same_session", "bank_reconciliation.confirm", "bank_reconciliation.reverse_confirmed_session"),
)
NON_INFERENCE_CASES = (
    ("legacy_edit_does_not_grant_confirm", "Edit", "bank_reconciliation.confirm"),
    ("legacy_delete_does_not_grant_cancel", "Delete", "bank_reconciliation.cancel"),
    ("aggregate_allow_count_does_not_identify_actor", "aggregate_effective_allow", "authenticated_actor_allow"),
    ("admin_bypass_count_does_not_define_target_admin", "legacy_admin_bypass", "target_superuser"),
    ("legacy_delete_does_not_grant_reverse", "Delete", "bank_reconciliation.reverse_confirmed_session"),
    ("legacy_confirm_does_not_grant_reverse", "Confirm", "bank_reconciliation.reverse_confirmed_session"),
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _case_id(*parts: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "_", ".".join(parts).casefold())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--permission-catalog", required=True, type=Path)
    parser.add_argument("--matching-boundary", required=True, type=Path)
    parser.add_argument("--profile-state-boundary", required=True, type=Path)
    parser.add_argument("--golden-cases", required=True, type=Path)
    parser.add_argument("--general-role-uat", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    inputs = {
        "permission_catalog": _load(args.permission_catalog),
        "matching_boundary": _load(args.matching_boundary),
        "profile_state_boundary": _load(args.profile_state_boundary),
        "golden_cases": _load(args.golden_cases),
        "general_role_uat": _load(args.general_role_uat),
    }
    for name, payload in inputs.items():
        if payload.get("validation") != "PASS":
            raise ValueError(f"validated {name} artifact is required")
    observed = tuple(
        inputs["permission_catalog"]["target_contract"]["distinct_capabilities_required"]
    )
    if observed != LEGACY_BASE_CAPABILITIES:
        raise ValueError("observed bank-reconciliation base capability set changed")

    cases: list[dict[str, Any]] = []
    for role in ROLE_TEMPLATES:
        allow = set(role["allow"])
        for capability in CAPABILITIES:
            expected = "ALLOW_IF_ALL_CONTEXT_STATE_AND_SCOPE_GATES_PASS" if capability in allow else "DENY"
            cases.append(
                {
                    "case_id": _case_id("assignment", role["role"], capability),
                    "kind": "role_assignment_decision",
                    "synthetic_role": role["role"],
                    "capability": capability,
                    "expected": expected,
                    "assertions": [
                        "deny-first authorization result is stable",
                        "no identity or production assignment is used",
                        "source Varanegar remains untouched",
                    ],
                }
            )
        for capability in sorted(allow - {"bank_reconciliation.view"}):
            for variation in CONTEXT_VARIATIONS:
                cases.append(
                    {
                        "case_id": _case_id("context", role["role"], capability, variation),
                        "kind": "context_negative",
                        "synthetic_role": role["role"],
                        "capability": capability,
                        "variation": variation,
                        "expected": "DENY_WITH_STABLE_REASON_AND_ZERO_MUTATION",
                        "assertions": [
                            "capability allow never bypasses context or data scope",
                            "no aggregate existence is leaked outside scope",
                            "source Varanegar remains untouched",
                        ],
                    }
                )

    for name, capability, fixture_state, expected in STATE_PROFILE_CASES:
        cases.append(
            {
                "case_id": _case_id("state_profile", name),
                "kind": "state_or_profile_gate",
                "capability": capability,
                "fixture_state": fixture_state,
                "expected": expected,
                "assertions": [
                    "server-side state and profile gate is evaluated",
                    "failed gate produces zero accepted mutation",
                    "source Varanegar remains untouched",
                ],
            }
        )
    for name, first, second in SOD_RULES:
        cases.append(
            {
                "case_id": _case_id("sod", name),
                "kind": "segregation_of_duties",
                "capabilities": [first, second],
                "same_aggregate_actor_fixture": True,
                "expected": "DENY_PENDING_OWNER_APPROVED_EXCEPTION_POLICY",
                "process_owner_signoff_required": True,
                "assertions": [
                    "same-aggregate actor history is evaluated",
                    "role names alone do not satisfy SoD",
                    "source Varanegar remains untouched",
                ],
            }
        )
    for name, legacy_signal, forbidden_inference in NON_INFERENCE_CASES:
        cases.append(
            {
                "case_id": _case_id("non_inference", name),
                "kind": "legacy_non_inference",
                "legacy_signal": legacy_signal,
                "forbidden_inference": forbidden_inference,
                "expected": "NO_TARGET_ALLOW_IS_CREATED",
                "assertions": [
                    "aggregate evidence is not expanded into an identity claim",
                    "legacy alias is not treated as a target capability",
                    "source Varanegar remains untouched",
                ],
            }
        )

    ids = [row["case_id"] for row in cases]
    duplicate_ids = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    counts = {
        "role_template_count": len(ROLE_TEMPLATES),
        "capability_count": len(CAPABILITIES),
        "role_assignment_case_count": sum(row["kind"] == "role_assignment_decision" for row in cases),
        "context_negative_case_count": sum(row["kind"] == "context_negative" for row in cases),
        "state_or_profile_case_count": len(STATE_PROFILE_CASES),
        "sod_case_count": len(SOD_RULES),
        "non_inference_case_count": len(NON_INFERENCE_CASES),
        "synthetic_uat_case_count": len(cases),
        "authenticated_uat_execution_count": 0,
        "owner_approved_case_count": 0,
        "production_assignment_count": 0,
        "duplicate_case_id_count": len(duplicate_ids),
    }
    artifact = {
        "artifact": "negin_erp_bank_reconciliation_identity_free_role_uat_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not duplicate_ids else "FAIL",
        "status": "DESIGN_ONLY_NOT_AUTHENTICATED_OR_EXECUTED",
        "safety": {
            "mode": "OFFLINE_SYNTHETIC_IDENTITY_FREE_UAT_DESIGN",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "identity_membership_or_individual_right_values_used": 0,
            "production_assignments_created": 0,
            "synthetic_cases_only": 1,
        },
        "summary": counts,
        "capabilities": list(CAPABILITIES),
        "role_templates": [
            {
                **role,
                "allow": list(role["allow"]),
                "deny": sorted(set(CAPABILITIES) - set(role["allow"])),
                "owner_approval_status": "NOT_APPROVED",
            }
            for role in ROLE_TEMPLATES
        ],
        "authorization_contract": {
            "decision": "capability AND feature entitlement AND fiscal/DC/account scope AND operation date AND state transition AND domain validation",
            "deny_overrides_allow": True,
            "neutral_is_not_allow": True,
            "legacy_edit_implies_confirm": False,
            "legacy_delete_implies_cancel": False,
            "legacy_delete_or_confirm_implies_reverse": False,
            "aggregate_counts_prove_individual_access": False,
            "parent_ui_permission_is_inherited_by_web_command": False,
        },
        "cases": cases,
        "source_evidence": [path.as_posix() for path in (
            args.permission_catalog,
            args.matching_boundary,
            args.profile_state_boundary,
            args.golden_cases,
            args.general_role_uat,
        )],
        "approval_gate": {
            "process_owner": "UNASSIGNED_REQUIRES_BUSINESS_SIGNOFF",
            "security_owner": "UNASSIGNED_REQUIRES_APPROVAL",
            "authenticated_test_accounts_required": True,
            "account_scope_fixtures_required": True,
            "owner_approved_expected_results_required": True,
            "ready_for_authenticated_uat": False,
            "ready_for_production_assignment": False,
        },
        "duplicate_case_ids": duplicate_ids,
        "limits": [
            "Role templates and expected results are proposals, not approved production policy.",
            "No named user, membership, individual legacy right, credential, or real account scope was used.",
            "Cases were generated but not executed against an authenticated seller or ERP UI.",
            "Legacy aggregate counts remain evidence of distribution only, never individual authorization.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], "summary": counts}))
    return 0 if not duplicate_ids else 1


if __name__ == "__main__":
    raise SystemExit(main())
