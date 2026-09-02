"""Build a least-privilege evidence and access request pack for next steps."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("readiness", "integrity", "owner_decisions", "uat_runbook", "root_closure"):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    names = ("readiness", "integrity", "owner_decisions", "uat_runbook", "root_closure")
    inputs = {name: _load(getattr(args, name)) for name in names}
    invalid = sorted(name for name, value in inputs.items() if value.get("validation") != "PASS")

    requests = [
        {
            "request_id": "BR-EVID-001",
            "priority": 1,
            "owner_role": "database_snapshot_owner",
            "request": "fresh owner-approved redacted READ_ONLY clone containing representative reconciliation sessions, bills and links across legacy marker shapes",
            "minimum_access": "DBA creates/restores clone; analyst login remains SELECT-only with explicit write deny",
            "forbidden": "production credential or write grant to the analyst",
            "unblocks": ["runtime integrity frequency", "row-result parity", "legacy marker quarantine measurement"],
            "current_status": "MISSING_CURRENT_CLONE_HAS_ZERO_RUNTIME_FIXTURE",
        },
        {
            "request_id": "BR-EVID-002",
            "priority": 1,
            "owner_role": "treasury_integration_owner",
            "request": "redacted approved real profile versions and one safe sample file per actively used parser format",
            "minimum_access": "copy into isolated evidence storage; no executable SQL/provider/path values are activated",
            "forbidden": "unredacted bank details, live shared path or executable profile configuration",
            "unblocks": ["profile value parity", "parser row/diagnostic parity", "BR-DEC-004 evidence"],
            "current_status": "MISSING_PROFILE_TABLES_ZERO",
        },
        {
            "request_id": "BR-EVID-003",
            "priority": 1,
            "owner_role": "finance_process_owner",
            "request": "approved redacted Summary fixtures with inputs and all 11 signed outputs, including both Type spelling variants",
            "minimum_access": "execute read-only comparison on clone or export an approved fixture/result set",
            "forbidden": "procedure mutation, silent alias normalization or production values in project artifacts",
            "unblocks": ["11-formula runtime parity", "BR-DEC-001", "Summary slice exit gate"],
            "current_status": "MISSING_RUNTIME_PARITY_APPROVAL",
        },
        {
            "request_id": "BR-EVID-004",
            "priority": 2,
            "owner_role": "treasury_process_owner",
            "request": "record selections for the seven owner-decision records with rationale and evidence references",
            "minimum_access": "decision review only; no application or database permission required",
            "forbidden": "treating engineering recommendations as approvals",
            "unblocks": ["parser edge policies", "alias policy", "confirm conflict", "cancel and reversal semantics"],
            "current_status": "SEVEN_DECISIONS_NOT_APPROVED",
        },
        {
            "request_id": "BR-EVID-005",
            "priority": 2,
            "owner_role": "identity_and_security_administrator",
            "request": "provision seven non-production UAT principal slots for six proposed roles plus deny baseline",
            "minimum_access": "target UAT environment only; credentials remain in identity provider/secret store",
            "forbidden": "production assignment or storing user identity/credential in project artifacts",
            "unblocks": ["authenticated allow/deny UAT", "SoD UAT", "command authorization gate"],
            "current_status": "ZERO_TEST_ACCOUNTS_PROVISIONED",
        },
        {
            "request_id": "BR-EVID-006",
            "priority": 2,
            "owner_role": "uat_environment_owner",
            "request": "create isolated target fixtures for in/out scope, open/closed date, correct/wrong fiscal/DC, feature on/off, profile states and five lifecycle states",
            "minimum_access": "write only to disposable target UAT database; no source Varanegar/NGT writes",
            "forbidden": "production fixture mutation or copying unredacted business data",
            "unblocks": ["all 100 authenticated UAT cases"],
            "current_status": "MISSING_AUTHENTICATED_UAT_FIXTURES",
        },
        {
            "request_id": "BR-EVID-007",
            "priority": 3,
            "owner_role": "target_test_environment_owner",
            "request": "provide disposable target database, audit/outbox sink and failure-injection controls for parser, confirm and reversal checkpoints",
            "minimum_access": "target test environment only with reset/reseed ownership",
            "forbidden": "failure injection against source or production",
            "unblocks": ["11 marked failure-injection cases", "atomic rollback proof", "retry/idempotency proof"],
            "current_status": "MISSING_TARGET_IMPLEMENTATION_AND_FAILURE_INJECTION",
        },
        {
            "request_id": "BR-EVID-008",
            "priority": 3,
            "owner_role": "varanegar_application_owner",
            "request": "collect allowlisted activation telemetry for the three unresolved roots over the three prescribed sessions",
            "minimum_access": "event metadata only; no identity, business value, file path, SQL or raw exception payload",
            "forbidden": "automated form action, command execution or scope exclusion from static absence",
            "unblocks": ["setup launcher mapping", "list/preview disposition", "SpecialOptionsDistrict disposition"],
            "current_status": "THREE_ROOTS_REQUIRE_RUNTIME_OR_OWNER_EVIDENCE",
        },
        {
            "request_id": "BR-EVID-009",
            "priority": 3,
            "owner_role": "business_scope_owner",
            "request": "sign retain/replace/retire disposition for each unresolved root after telemetry review",
            "minimum_access": "owner decision record only",
            "forbidden": "source deletion or automatic exclusion based only on no static reference",
            "unblocks": ["navigation scope closure", "three-root pilot gate"],
            "current_status": "ZERO_ROOTS_RESOLVED",
        },
    ]
    errors: list[str] = []
    if invalid:
        errors.append("invalid inputs: " + ", ".join(invalid))
    readiness = inputs["readiness"]["summary"]
    expected_zero = {
        "current_clone_runtime_fixture_available_count": readiness["current_clone_runtime_fixture_available_count"],
        "approved_owner_decision_count": readiness["approved_owner_decision_count"],
        "provisioned_uat_test_account_count": readiness["provisioned_uat_test_account_count"],
        "authenticated_uat_execution_count": readiness["authenticated_uat_execution_count"],
        "resolved_root_count": readiness["resolved_root_count"],
        "target_command_execution_count": readiness["target_command_execution_count"],
    }
    if any(expected_zero.values()):
        errors.append("one or more blocker-zero counts changed; refresh request statuses")

    payload = {
        "artifact": "negin_erp_bank_reconciliation_least_privilege_evidence_and_access_request_pack",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "REQUEST_PACK_READY_NO_NEW_ACCESS_OR_EVIDENCE_GRANTED",
        "safety": {
            "mode": "OFFLINE_VALIDATED_ARTIFACT_COMPOSITION",
            "database_connections": 0,
            "identity_provider_or_secret_store_reads": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "access_grants_or_owner_approvals_created": 0,
        },
        "summary": {
            "source_artifact_count": len(inputs),
            "request_count": len(requests),
            "priority_1_request_count": sum(row["priority"] == 1 for row in requests),
            "priority_2_request_count": sum(row["priority"] == 2 for row in requests),
            "priority_3_request_count": sum(row["priority"] == 3 for row in requests),
            "distinct_owner_role_count": len({row["owner_role"] for row in requests}),
            "current_satisfied_request_count": 0,
            "new_access_grant_count": 0,
            "owner_approval_count": 0,
            "validation_error_count": len(errors),
        },
        "requests": requests,
        "recommended_sequence": [
            "BR-EVID-001 and BR-EVID-002",
            "BR-EVID-003 and BR-EVID-004",
            "BR-EVID-005 and BR-EVID-006",
            "BR-EVID-007",
            "BR-EVID-008 and BR-EVID-009",
        ],
        "blocker_zero_snapshot": expected_zero,
        "validation_errors": errors,
        "limits": [
            "This pack requests evidence and least-privilege access; it grants nothing.",
            "DBA, identity, UAT and business owners retain their normal approval boundaries.",
            "No production write access is required for discovery or parity work.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(json.dumps({"validation": payload["validation"], "summary": payload["summary"]}, ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
