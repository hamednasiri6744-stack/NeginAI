"""Build a uniform target command envelope for bank reconciliation."""

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
    for name in ("state_machine", "role_uat", "differential", "owner_decisions", "confirm", "unmatch"):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    names = ("state_machine", "role_uat", "differential", "owner_decisions", "confirm", "unmatch")
    inputs = {name: _load(getattr(args, name)) for name in names}
    invalid = sorted(name for name, value in inputs.items() if value.get("validation") != "PASS")

    common_request = [
        "command_id", "idempotency_key", "aggregate_id", "expected_version",
        "fiscal_year_id", "dc_id", "bank_account_id", "operation_date",
        "reason_code", "correlation_id",
    ]
    common_guard_order = [
        "authenticate actor",
        "authorize exact capability with deny-first semantics",
        "validate feature entitlement",
        "validate fiscal year, DC and bank-account scope without existence leakage",
        "validate operation date",
        "load aggregate and compare expected version",
        "validate idempotency key and payload hash",
        "validate lifecycle transition and domain invariants",
        "perform all mutations, audit and outbox in one application transaction",
        "commit once and return a stable result envelope",
    ]
    commands = [
        {
            "command": "MatchInstrument",
            "capability": "bank_reconciliation.match_instrument",
            "allowed_state": "OPEN_UNCONFIRMED",
            "specific_request_fields": ["statement_row_id", "instrument_type", "instrument_id", "candidate_snapshot_hash"],
            "decision_gates": ["owner-approved amount/tolerance policy"],
            "mutation_set": ["one typed link", "aggregate version", "audit", "outbox"],
        },
        {
            "command": "UnmatchInstrument",
            "capability": "bank_reconciliation.unmatch_instrument",
            "allowed_state": "OPEN_UNCONFIRMED",
            "specific_request_fields": ["link_id"],
            "decision_gates": [],
            "mutation_set": ["one named link", "aggregate version", "audit", "outbox"],
        },
        {
            "command": "ConfirmSession",
            "capability": "bank_reconciliation.confirm",
            "allowed_state": "OPEN_UNCONFIRMED",
            "specific_request_fields": ["as_of_date", "reconciliation_snapshot_hash"],
            "decision_gates": ["Summary parity", "owner-approved tolerance", "all-link integrity"],
            "mutation_set": ["session markers/state", "every linked instrument", "aggregate version", "audit", "outbox"],
        },
        {
            "command": "CancelSession",
            "capability": "bank_reconciliation.cancel",
            "allowed_state": "OPEN_UNCONFIRMED",
            "specific_request_fields": ["cancel_policy_version"],
            "decision_gates": ["BR-DEC-007"],
            "mutation_set": ["session state/archive", "statement rows", "aggregate version", "audit", "outbox"],
        },
        {
            "command": "ReverseConfirmedSession",
            "capability": "bank_reconciliation.reverse_confirmed_session",
            "allowed_state": "CONFIRMED",
            "specific_request_fields": ["reversal_policy_version", "confirmation_version"],
            "decision_gates": ["BR-DEC-006", "authenticated SoD"],
            "mutation_set": ["session state", "every linked instrument", "aggregate version", "audit", "outbox"],
        },
    ]
    response = [
        "command_id", "result_code", "aggregate_id", "aggregate_version", "lifecycle_state",
        "matching_progress", "summary_version", "committed_at", "correlation_id",
    ]
    errors = [
        ["AUTHENTICATION_REQUIRED", 401, False],
        ["CAPABILITY_DENIED", 403, False],
        ["SCOPE_DENIED", 404, False],
        ["FEATURE_DISABLED", 403, False],
        ["OPERATION_DATE_CLOSED", 409, False],
        ["STALE_VERSION", 409, True],
        ["IDEMPOTENCY_PAYLOAD_CONFLICT", 409, False],
        ["INVALID_STATE_TRANSITION", 409, False],
        ["DOMAIN_VALIDATION_FAILED", 422, False],
        ["INTEGRITY_QUARANTINED", 409, False],
        ["DEPENDENCY_OR_COMMIT_FAILED", 503, True],
    ]
    invariants = [
        "client-supplied role, permission, fiscal scope or state is never trusted",
        "scope denial does not reveal whether the aggregate exists",
        "idempotency uniqueness is scoped by actor/tenant, command kind and key",
        "same idempotency key with a different payload is a conflict",
        "expected version is checked inside the transaction before mutation",
        "repository helpers cannot commit independently",
        "audit and outbox share the business transaction",
        "no success is returned before physical commit",
        "ambiguous response retry returns the committed original result",
        "every linked instrument is prevalidated before confirm or reverse mutation",
        "one failed link rolls back the session, all instruments, audit and outbox",
        "legacy procedure names, raw SQL and data-access error numbers are not public API contracts",
    ]
    errors_validation: list[str] = []
    if invalid:
        errors_validation.append("invalid inputs: " + ", ".join(invalid))
    known_caps = set(inputs["role_uat"]["capabilities"])
    missing_caps = sorted({row["capability"] for row in commands} - known_caps)
    if missing_caps:
        errors_validation.append("missing capabilities: " + ", ".join(missing_caps))
    if inputs["differential"]["summary"]["executed_case_count"] != 0:
        errors_validation.append("execution state changed and requires command-envelope review")

    payload = {
        "artifact": "negin_erp_bank_reconciliation_uniform_atomic_command_envelope_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors_validation else "FAIL",
        "status": "COMMAND_ENVELOPE_READY_COMMANDS_BLOCKED_NOT_IMPLEMENTED",
        "safety": {
            "mode": "OFFLINE_VALIDATED_ARTIFACT_COMPOSITION",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_identity_values_read": 0,
            "owner_approvals_inferred": 0,
        },
        "summary": {
            "source_artifact_count": len(inputs),
            "command_contract_count": len(commands),
            "distinct_capability_count": len({row["capability"] for row in commands}),
            "common_request_field_count": len(common_request),
            "common_guard_stage_count": len(common_guard_order),
            "common_response_field_count": len(response),
            "stable_error_code_count": len(errors),
            "invariant_count": len(invariants),
            "implemented_command_count": 0,
            "executed_acceptance_case_count": inputs["differential"]["summary"]["executed_case_count"],
            "validation_error_count": len(errors_validation),
        },
        "common_request_fields": common_request,
        "common_guard_order": common_guard_order,
        "command_contracts": commands,
        "common_response_fields": response,
        "stable_error_contracts": [
            {"code": row[0], "http_status": row[1], "retryable": row[2]}
            for row in errors
        ],
        "invariants": invariants,
        "implementation_gate": {
            "all_five_commands_allowed_now": False,
            "match_unmatch_confirm_cancel_reverse_are_not_legacy_aliases": True,
            "owner_decisions_authenticated_uat_failure_injection_and_runtime_parity_required": True,
            "source_varanegar_remains_read_only": True,
        },
        "validation_errors": errors_validation,
        "limits": [
            "This is an API/application-service contract, not an implementation.",
            "Stable target errors do not expose raw legacy error numbers or exception payloads.",
            "All command execution and owner approval counts remain zero.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(json.dumps({"validation": payload["validation"], "summary": payload["summary"]}, ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
