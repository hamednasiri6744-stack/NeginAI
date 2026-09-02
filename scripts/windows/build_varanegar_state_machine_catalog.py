"""Build cheque and distribution state-machine contracts from safe artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _received(source: dict[str, Any]) -> dict[str, Any]:
    references = source["reference_masters"]
    usage = {row["ID"]: row for row in references["current_status_master"]}
    states = []
    for row in references["legacy_compatible_status_master"]:
        state_id = row["RChequeStatusId"]
        state_usage = usage.get(state_id, {})
        states.append(
            {
                "id": state_id,
                "name": row["RChequeStatusName"],
                "action": row["RchequeStatusAct"],
                "history_usage": state_usage.get("history_usage", 0),
                "current_usage": state_usage.get("current_usage", 0),
                "in_active_tracking_queue": state_id in {1, 2, 4, 8, 9},
            }
        )
    allowed = [
        {
            "transition_id": row["RChequeWorkflowId"],
            "from": row["RChequeStatusId"],
            "to": row["RChequeNextStatusId"],
        }
        for row in references["allowed_workflow"]
    ]
    observed = [
        {
            "from": row["from_status"],
            "to": row["to_status"],
            "events": row["transitions"],
            "workflow_id_present": row["with_transition_id"],
            "workflow_definition_matches": row["transition_definition_matches"],
        }
        for row in source["state_history"]["actual_transition_distribution"]
    ]
    allowed_pairs = {(row["from"], row["to"]) for row in allowed}
    observed_pairs = {(row["from"], row["to"]) for row in observed}
    return {
        "machine_id": "received_cheque",
        "states": states,
        "allowed_transitions": allowed,
        "observed_transitions": observed,
        "allowed_but_unobserved": [
            {"from": start, "to": end}
            for start, end in sorted(allowed_pairs - observed_pairs)
        ],
        "observed_outside_allowed": [
            {"from": start, "to": end}
            for start, end in sorted(observed_pairs - allowed_pairs)
        ],
        "history_integrity": source["state_history"]["chain_and_transition_integrity"],
        "current_pointer_integrity": source["state_history"]["current_event_is_latest"],
        "data_quality": source["data_quality"],
        "command_contract": {
            "change_status": "validate allowed edge + operation date + status context, append immutable event, atomically advance current pointer",
            "undo": "validate current leaf + dependent transfer/settlement/balance, remove or compensate only latest event, atomically restore pointer",
        },
    }


def _payable(source: dict[str, Any]) -> dict[str, Any]:
    references = source["reference_masters"]
    states = [
        {
            "id": row["PChequeStatusId"],
            "name": row["PChequeStatusName"],
            "history_usage": row["history_usage"],
            "current_usage": row["current_usage"],
            "in_active_tracking_queue": row["PChequeStatusId"] in {1, 5},
        }
        for row in references["payable_cheque_statuses"]
    ]
    allowed = [
        {
            "transition_id": row["PChequeWorkflowId"],
            "from": row["from_status"],
            "to": row["to_status"],
            "workflow_code": row["PChequeWorkflowCode"],
            "process_type_id": row["ProcessTypeId"],
        }
        for row in references["payable_cheque_workflow"]
    ]
    observed = [
        {
            "from": row["from_status"],
            "to": row["to_status"],
            "events": row["transitions"],
            "allowed_events": row["allowed_by_workflow"],
        }
        for row in source["payable_cheque_lifecycle"]["actual_transitions"]
    ]
    allowed_pairs = {(row["from"], row["to"]) for row in allowed}
    observed_pairs = {(row["from"], row["to"]) for row in observed}
    return {
        "machine_id": "payable_cheque",
        "states": states,
        "allowed_transitions": allowed,
        "observed_transitions": observed,
        "allowed_but_unobserved": [
            {"from": start, "to": end}
            for start, end in sorted(allowed_pairs - observed_pairs)
        ],
        "observed_outside_allowed": [
            {"from": start, "to": end}
            for start, end in sorted(observed_pairs - allowed_pairs)
        ],
        "history_integrity": source["payable_cheque_lifecycle"]["history_integrity"],
        "data_quality": source["data_quality"],
        "command_contract": {
            "change_status": "validate workflow edge + operation date + cheque leaf/pay/balance constraints, append event and advance pointer atomically",
            "undo": "validate current leaf and book-item/pay relationships, reverse only the latest permitted transition",
        },
    }


def _distribution(source: dict[str, Any]) -> dict[str, Any]:
    current = {
        row["Status"]: row for row in source["distributions"]["status_distribution"]
    }
    states = [
        {
            "id": row["Code"],
            "name": row["Title"],
            "current_usage": current.get(row["Code"], {}).get("distributions", 0),
            "current_with_send_date": current.get(row["Code"], {}).get("has_send_date", 0),
            "current_with_return_date": current.get(row["Code"], {}).get("has_return_date", 0),
        }
        for row in source["reference_masters"]["distribution_statuses"]
    ]
    observed = [
        {
            "from": row["OldStatus"],
            "to": row["Status"],
            "events": row["events"],
            "aggregates": row["distributions"],
        }
        for row in source["status_event_log"]["status_transitions"]
    ]
    return {
        "machine_id": "distribution",
        "states": states,
        "allowed_transitions": None,
        "observed_transitions": observed,
        "canonical_observed_path": [
            {"from": None, "to": 1},
            {"from": 1, "to": 2},
            {"from": 2, "to": 3},
            {"from": 3, "to": 4},
            {"from": 4, "to": 7},
        ],
        "reverse_or_side_paths_observed": [
            row for row in observed
            if (row["from"], row["to"]) not in {
                (None, 1), (1, 2), (2, 3), (3, 4), (4, 7)
            }
        ],
        "event_population": source["status_event_log"]["population"],
        "data_quality": source["data_quality"],
        "command_contract": {
            "create": "append initial state 1 with fiscal/DC/distribution-number identity",
            "issue_exit": "state 1 to 2 with stock exit/cardex transaction and quantity/batch reconciliation",
            "send": "state 2 to 3 after route/team/vehicle/date checks",
            "complete": "state 3 to 4 then 4 to 7 with return/delivery evidence",
            "reverse": "explicit guarded transition with reason, dependency checks and audit; never arbitrary status assignment",
            "tablet_handoff": "state 3 to 5 is a distinct integration path; state 5 can return to 3 or finish at 7",
        },
        "evidence_boundary": (
            "Distribution has an observed event graph but no complete configured allowed-edge table in this evidence. "
            "Observed transitions are not automatically a whitelist."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--received", required=True, type=Path)
    parser.add_argument("--payable", required=True, type=Path)
    parser.add_argument("--distribution", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    machines = [
        _received(_load(args.received)),
        _payable(_load(args.payable)),
        _distribution(_load(args.distribution)),
    ]
    artifact = {
        "artifact": "varanegar_state_machine_catalog",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "sources": {
            "received_cheque_domain": args.received.as_posix(),
            "payable_cheque_domain": args.payable.as_posix(),
            "distribution_domain": args.distribution.as_posix(),
        },
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_AGGREGATE_READ_ONLY_EVIDENCE",
            "database_connections": 0,
            "live_ui_actions": 0,
            "commands_or_transitions_executed": 0,
            "individual_instrument_or_distribution_rows_persisted": 0,
            "identities_or_amounts_persisted": 0,
        },
        "summary": {
            "machine_count": len(machines),
            "state_count": sum(len(row["states"]) for row in machines),
            "configured_allowed_transition_count": sum(
                len(row["allowed_transitions"] or []) for row in machines
            ),
            "observed_transition_count": sum(
                len(row["observed_transitions"]) for row in machines
            ),
            "observed_outside_configured_cheque_workflow_count": sum(
                len(row.get("observed_outside_allowed", [])) for row in machines
            ),
        },
        "erp_state_contract": [
            "Persist an append-only transition event ledger and a versioned current-state pointer.",
            "Use an explicit allowed-edge catalog with per-edge authorization, required fields, guards and side effects.",
            "Treat undo as a guarded compensating/reverse command, not direct current-state editing.",
            "Separate configured-allowed, observed, active-in-form and currently-used transition dimensions.",
            "Preserve source status IDs in a migration crosswalk; use stable namespaced IDs in the target.",
            "Reconcile every material transition against dependent ledgers such as payment allocation, stock cardex and delivery evidence.",
        ],
        "limits": [
            "Transition counts are aggregate clone evidence and contain no individual instrument or distribution row.",
            "An unobserved configured edge may still be valid; an observed distribution edge is not automatically allowed for future use.",
            "Current usage can drift after the source snapshot.",
        ],
        "state_machines": machines,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
