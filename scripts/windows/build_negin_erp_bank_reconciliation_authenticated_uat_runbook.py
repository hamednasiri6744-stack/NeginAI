"""Build an identity-safe authenticated UAT execution runbook."""

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
    parser.add_argument("--role-uat", required=True, type=Path)
    parser.add_argument("--command-envelope", required=True, type=Path)
    parser.add_argument("--state-machine", required=True, type=Path)
    parser.add_argument("--owner-decisions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {
        "role_uat": args.role_uat,
        "command_envelope": args.command_envelope,
        "state_machine": args.state_machine,
        "owner_decisions": args.owner_decisions,
    }
    inputs = {name: _load(path) for name, path in paths.items()}
    invalid = sorted(name for name, value in inputs.items() if value.get("validation") != "PASS")
    role_uat = inputs["role_uat"]
    kind_counts = Counter(row["kind"] for row in role_uat["cases"])

    principal_slots = [
        {"slot": "UAT_VIEWER", "role_template": "bank_reconciliation_viewer"},
        {"slot": "UAT_IMPORTER", "role_template": "bank_statement_importer"},
        {"slot": "UAT_MATCHER", "role_template": "bank_reconciliation_matcher"},
        {"slot": "UAT_CONFIRMER", "role_template": "bank_reconciliation_confirmer"},
        {"slot": "UAT_CANCELLER", "role_template": "bank_reconciliation_supervisor"},
        {"slot": "UAT_REVERSER", "role_template": "bank_reconciliation_reversal_authorizer"},
        {"slot": "UAT_DENY_BASELINE", "role_template": None},
    ]
    fixture_slots = [
        "ACCOUNT_IN_SCOPE", "ACCOUNT_OUT_OF_SCOPE", "OPEN_OPERATION_DATE",
        "CLOSED_OPERATION_DATE", "CORRECT_FISCAL_DC", "WRONG_FISCAL_OR_DC",
        "FEATURE_ENABLED", "FEATURE_DISABLED", "CURRENT_VERSION", "STALE_VERSION",
        "PROFILE_APPROVED", "PROFILE_UNAPPROVED", "SESSION_OPEN", "SESSION_CONFIRMED",
        "SESSION_QUARANTINED",
    ]
    prerequisites = [
        "isolated target UAT environment with no production write path",
        "seven non-production principal slots provisioned by the authorized identity administrator",
        "real identities and credentials remain only in the identity provider or secret store",
        "owner-approved role/capability expectations and SoD exception policy",
        "inside/outside bank-account scope fixtures with synthetic or approved redacted data",
        "open/closed operation-date and correct/wrong fiscal/DC fixtures",
        "feature enabled/disabled and profile approved/unapproved fixtures",
        "all lifecycle states including quarantine and reversal candidate fixtures",
        "server/application version and evidence store available before execution",
    ]
    waves = [
        {"order": 1, "kind": "role_assignment_decision", "case_count": kind_counts["role_assignment_decision"]},
        {"order": 2, "kind": "context_negative", "case_count": kind_counts["context_negative"]},
        {"order": 3, "kind": "state_or_profile_gate", "case_count": kind_counts["state_or_profile_gate"]},
        {"order": 4, "kind": "segregation_of_duties", "case_count": kind_counts["segregation_of_duties"]},
        {"order": 5, "kind": "legacy_non_inference", "case_count": kind_counts["legacy_non_inference"]},
    ]
    evidence_fields = [
        "uat_run_id", "case_id", "principal_slot", "environment_key", "application_version",
        "capability", "fixture_slot", "expected_result", "actual_result", "pass_fail",
        "stable_error_code", "redacted_evidence_reference", "executed_at_utc",
    ]
    forbidden_evidence = [
        "user name, email, personnel id or group-membership dump",
        "credential, token, cookie, connection string or secret reference value",
        "raw SQL, stack trace or unredacted exception payload",
        "bank account number, statement description, amount or business row identifier",
        "screenshot containing identity or business values",
    ]
    stop_conditions = [
        "any unexpected source Varanegar or NGT write path is reachable",
        "scope denial leaks aggregate existence or values",
        "a denied command causes any accepted target mutation",
        "same-session SoD is bypassed without an approved exception",
        "audit/outbox is missing or differs from the committed command result",
        "evidence capture contains a forbidden identity, credential or business value",
    ]
    errors: list[str] = []
    if invalid:
        errors.append("invalid inputs: " + ", ".join(invalid))
    if sum(row["case_count"] for row in waves) != role_uat["summary"]["synthetic_uat_case_count"]:
        errors.append("UAT wave coverage does not equal source cases")
    if {row["role_template"] for row in principal_slots if row["role_template"]} != {
        row["role"] for row in role_uat["role_templates"]
    }:
        errors.append("principal slots do not cover all role templates")

    payload = {
        "artifact": "negin_erp_bank_reconciliation_identity_safe_authenticated_uat_execution_runbook",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "RUNBOOK_READY_TEST_ACCOUNTS_NOT_PROVISIONED_UAT_NOT_EXECUTED",
        "safety": {
            "mode": "OFFLINE_VALIDATED_ARTIFACT_COMPOSITION",
            "database_connections": 0,
            "identity_provider_or_secret_store_reads": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "identity_membership_business_values_or_credentials_persisted": 0,
        },
        "summary": {
            "source_artifact_count": len(inputs),
            "principal_slot_count": len(principal_slots),
            "role_template_count": role_uat["summary"]["role_template_count"],
            "capability_count": role_uat["summary"]["capability_count"],
            "fixture_slot_count": len(fixture_slots),
            "prerequisite_count": len(prerequisites),
            "execution_wave_count": len(waves),
            "covered_uat_case_count": sum(row["case_count"] for row in waves),
            "evidence_field_count": len(evidence_fields),
            "forbidden_evidence_class_count": len(forbidden_evidence),
            "stop_condition_count": len(stop_conditions),
            "provisioned_test_account_count": 0,
            "executed_case_count": 0,
            "passed_case_count": 0,
            "owner_approved_expected_result_count": 0,
            "validation_error_count": len(errors),
        },
        "principal_slots": principal_slots,
        "fixture_slots": fixture_slots,
        "prerequisites": prerequisites,
        "execution_waves": waves,
        "evidence_record_fields": evidence_fields,
        "forbidden_evidence": forbidden_evidence,
        "stop_conditions": stop_conditions,
        "execution_policy": {
            "principal_slot_maps_to_real_test_identity_only_at_execution_time": True,
            "project_artifacts_store_slot_not_identity": True,
            "deny_wave_runs_before_allowing_any_command_wave": True,
            "source_varanegar_and_ngt_remain_read_only": True,
            "failed_stop_condition_blocks_later_waves": True,
            "pilot_requires_all_100_cases_pass_and_owner_signoff": True,
        },
        "validation_errors": errors,
        "limits": [
            "No test account is provisioned by this runbook.",
            "No real identity, role membership, credential or business fixture value is present.",
            "The runbook is ready for authorized execution but all execution and approval counts are zero.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(json.dumps({"validation": payload["validation"], "summary": payload["summary"]}, ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
