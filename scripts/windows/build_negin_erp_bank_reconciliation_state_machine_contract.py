"""Build a decision-gated target state machine for bank reconciliation."""

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
    for name in (
        "profile_state", "matching", "confirm_orchestration", "unmatch",
        "discard_cancel", "integrity", "owner_decisions", "role_uat",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    names = (
        "profile_state", "matching", "confirm_orchestration", "unmatch",
        "discard_cancel", "integrity", "owner_decisions", "role_uat",
    )
    inputs = {name: _load(getattr(args, name)) for name in names}
    invalid = sorted(name for name, value in inputs.items() if value.get("validation") != "PASS")

    states = [
        {"state": "OPEN_UNCONFIRMED", "terminal": False, "source_mapping": "both ConfirmerId and ConfirmDate are null"},
        {"state": "CONFIRMED", "terminal": False, "source_mapping": "both ConfirmerId and ConfirmDate are non-null"},
        {"state": "CANCELLED", "terminal": True, "source_mapping": "target-only; not inferred from legacy"},
        {"state": "REVERSED", "terminal": True, "source_mapping": "target-only; not inferred from legacy"},
        {"state": "QUARANTINED", "terminal": False, "source_mapping": "inconsistent markers or integrity violation"},
    ]
    progress = [
        {"value": "NO_ACTIVE_LINKS", "definition": "active link count is zero"},
        {"value": "PARTIALLY_LINKED", "definition": "some but not all owner-approved row dispositions are satisfied"},
        {"value": "READY_FOR_CONFIRM_REVIEW", "definition": "owner-approved reconciliation predicate and parity gates pass"},
        {"value": "AMBIGUOUS_OR_INVALID", "definition": "zero/multiple typed reference or unresolved integrity anomaly"},
    ]
    transitions = [
        {"command": "CommitImportJob", "capability": "bank_reconciliation.import_statement", "from": "NONE", "to": "OPEN_UNCONFIRMED", "decision_gate": None},
        {"command": "MatchInstrument", "capability": "bank_reconciliation.match_instrument", "from": "OPEN_UNCONFIRMED", "to": "OPEN_UNCONFIRMED", "decision_gate": "approved amount and candidate policy"},
        {"command": "UnmatchInstrument", "capability": "bank_reconciliation.unmatch_instrument", "from": "OPEN_UNCONFIRMED", "to": "OPEN_UNCONFIRMED", "decision_gate": None},
        {"command": "ConfirmSession", "capability": "bank_reconciliation.confirm", "from": "OPEN_UNCONFIRMED", "to": "CONFIRMED", "decision_gate": "Summary parity, tolerance and all-link atomicity approved"},
        {"command": "CancelSession", "capability": "bank_reconciliation.cancel", "from": "OPEN_UNCONFIRMED", "to": "CANCELLED", "decision_gate": "BR-DEC-007"},
        {"command": "ReverseConfirmedSession", "capability": "bank_reconciliation.reverse_confirmed_session", "from": "CONFIRMED", "to": "REVERSED", "decision_gate": "BR-DEC-006"},
        {"command": "QuarantineLegacySession", "capability": "migration.integrity.quarantine", "from": "LEGACY_IMPORT", "to": "QUARANTINED", "decision_gate": "integrity review evidence"},
    ]
    invariants = [
        "header lifecycle state and computed matching progress are separate dimensions",
        "match and unmatch never change header lifecycle state",
        "unmatch is allowed only in OPEN_UNCONFIRMED and addresses one link id with expected version",
        "cancel is not unmatch, discard or confirmed-session reversal",
        "reverse is not cancel and requires its own capability and SoD",
        "confirmed sessions cannot be physically deleted or silently unconfirmed",
        "confirm validates every typed link before any mutation and updates all links atomically",
        "a confirmed marker alone does not prove linked instrument integrity",
        "exactly one of legacy confirmer id/date being null always maps to QUARANTINED",
        "zero or multiple typed references map to AMBIGUOUS_OR_INVALID and block confirm",
        "all transitions require feature, fiscal/DC/account scope, operation date, state, expected version and domain guards",
        "all accepted commands require idempotency and one application transaction owner",
        "audit and outbox are atomic with the transition",
        "owner-decision recommendations never activate Cancel or Reverse semantics automatically",
    ]
    acceptance = [
        "open session match changes progress only",
        "open session unmatch named link changes progress only",
        "confirmed session match or unmatch is denied",
        "confirm with one invalid link rolls back markers and every instrument update",
        "confirm with two links updates both and fails regression if only one changes",
        "confirm retry returns original result",
        "cancel open session follows BR-DEC-007 and archives/transitions header and rows atomically",
        "cancel confirmed session is denied",
        "reverse confirmed session follows BR-DEC-006 and resets all linked instruments atomically",
        "reverse by confirmer of the same session is denied by SoD",
        "reverse unconfirmed session is denied",
        "reverse failure after audit or outbox rolls back all changes",
        "inconsistent legacy markers import into quarantine",
        "confirmed/unreconciled or unconfirmed/reconciled integrity mismatch imports into quarantine",
        "quarantined session is visible only through scoped review and accepts no operational command",
        "stale expected version causes zero mutation",
        "closed operation date causes zero mutation",
        "denied account scope leaks no session or aggregate existence",
    ]
    errors: list[str] = []
    if invalid:
        errors.append("invalid inputs: " + ", ".join(invalid))
    owner = inputs["owner_decisions"]
    by_id = {row["decision_id"]: row for row in owner["decisions"]}
    for decision_id in ("BR-DEC-006", "BR-DEC-007"):
        if by_id[decision_id]["decision_status"] != "NOT_APPROVED":
            errors.append(f"{decision_id} changed and requires state-machine review")
    if "bank_reconciliation.reverse_confirmed_session" not in inputs["role_uat"]["capabilities"]:
        errors.append("distinct reversal capability missing")

    payload = {
        "artifact": "negin_erp_bank_reconciliation_decision_gated_target_state_machine_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "STATE_CONTRACT_READY_COMMANDS_NOT_IMPLEMENTED_OR_OWNER_APPROVED",
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
            "lifecycle_state_count": len(states),
            "computed_progress_value_count": len(progress),
            "transition_contract_count": len(transitions),
            "distinct_transition_capability_count": len({row["capability"] for row in transitions}),
            "invariant_count": len(invariants),
            "acceptance_obligation_count": len(acceptance),
            "approved_cancel_or_reverse_decision_count": 0,
            "implemented_transition_count": 0,
            "validation_error_count": len(errors),
        },
        "lifecycle_states": states,
        "computed_matching_progress": progress,
        "transition_contracts": transitions,
        "invariants": invariants,
        "acceptance_obligations": acceptance,
        "decision_gates": {
            decision_id: {
                "status": by_id[decision_id]["decision_status"],
                "recommended_safe_default": by_id[decision_id]["recommended_safe_default"],
                "recommendation_is_approval": False,
            }
            for decision_id in ("BR-DEC-006", "BR-DEC-007")
        },
        "validation_errors": errors,
        "limits": [
            "CANCELLED and REVERSED are target states and are not inferred from legacy markers.",
            "READY_FOR_CONFIRM_REVIEW depends on an owner-approved reconciliation predicate.",
            "No transition implementation, owner approval or authenticated UAT is claimed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(json.dumps({"validation": payload["validation"], "summary": payload["summary"]}, ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
