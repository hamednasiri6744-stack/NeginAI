"""Build executable-design Golden cases for the reconstructed ERP commands."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


COMMAND_SPECIFICS: dict[str, list[dict[str, Any]]] = {
    "distribution.create_or_update": [
        {"suffix": "valid_create", "kind": "success", "variation": "valid route/team/vehicle/date and nonempty SaleS", "outcome": "COMMITTED", "assertions": ["one distribution identity", "unique number per AccYear/DC", "sale links and distribution history agree"]},
        {"suffix": "empty_sales", "kind": "validation", "variation": "SaleS empty", "outcome": "VALIDATION_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "vehicle_capacity", "kind": "validation", "variation": "weight/volume/amount outside vehicle policy", "outcome": "VALIDATION_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "closed_operation_date", "kind": "context", "variation": "sales operation date closed", "outcome": "CONTEXT_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "number_race", "kind": "concurrency", "variation": "two creates request next number concurrently", "outcome": "ONE_UNIQUE_NUMBER_PER_COMMAND", "assertions": ["no duplicate AccYear/DC/DistNo", "both commands deterministic or one safely retries"]},
    ],
    "distribution.issue_exit": [
        {"suffix": "valid_exit", "kind": "success", "variation": "status 1, stock/batch available, valid date and lock", "outcome": "COMMITTED", "assertions": ["distribution reaches state 2", "sale ExitRef points to active exit", "voucher item/detail equals sale quantity by goods/batch", "cardex remains nonnegative"]},
        {"suffix": "negative_cardex", "kind": "reconciliation", "variation": "exit would make cardex negative", "outcome": "VALIDATION_REJECTED", "assertions": ["zero durable exit/voucher writes"]},
        {"suffix": "batch_mismatch", "kind": "reconciliation", "variation": "sale quantity differs from voucher detail batch sum", "outcome": "VALIDATION_REJECTED", "assertions": ["zero durable partial voucher"]},
        {"suffix": "wrong_status", "kind": "workflow", "variation": "distribution current state is not exit-eligible", "outcome": "WORKFLOW_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "lock_conflict", "kind": "concurrency", "variation": "exit lock belongs to another actor/session", "outcome": "LOCK_CONFLICT", "assertions": ["zero writes", "lock owner not overwritten"]},
    ],
    "distribution.merge_or_adjust_exit": [
        {"suffix": "valid_merge", "kind": "success", "variation": "goods/batch/stock adjustment balances distribution", "outcome": "COMMITTED", "assertions": ["RD rows match accepted quantities", "no duplicate goods/batch line"]},
        {"suffix": "unknown_goods", "kind": "validation", "variation": "goods outside distribution sales", "outcome": "VALIDATION_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "quantity_overflow", "kind": "validation", "variation": "accepted quantity exceeds eligible total", "outcome": "VALIDATION_REJECTED", "assertions": ["zero writes"]},
    ],
    "distribution.remove_exit": [
        {"suffix": "valid_reverse", "kind": "success", "variation": "reason present, date/status/dependencies reversible", "outcome": "COMMITTED", "assertions": ["exit canceled", "sale ExitRef cleared", "distribution returns to state 1", "related voucher/RD effect reversed", "full history contains reason and actor"]},
        {"suffix": "missing_reason", "kind": "validation", "variation": "remove reason empty", "outcome": "VALIDATION_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "closed_last_date", "kind": "context", "variation": "exit date crosses last closed date", "outcome": "CONTEXT_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "dependent_posting", "kind": "validation", "variation": "dependent voucher/posting cannot be reversed", "outcome": "DEPENDENCY_REJECTED", "assertions": ["zero durable partial reversal"]},
        {"suffix": "partial_exit_set", "kind": "reconciliation", "variation": "multiple exits exist and only subset is eligible", "outcome": "DETERMINISTIC_SCOPE_REQUIRED", "assertions": ["unselected exit untouched", "result state reflects remaining active exits"]},
    ],
    "received_cheque.change_status": [
        {"suffix": "allowed_edge", "kind": "success", "variation": "configured edge with valid operation date and context", "outcome": "COMMITTED", "assertions": ["one new history event", "current pointer equals new event", "previous pointer chain intact"]},
        {"suffix": "invalid_edge", "kind": "workflow", "variation": "edge absent from configured workflow", "outcome": "WORKFLOW_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "older_operation_date", "kind": "validation", "variation": "operation date before cheque/last history date", "outcome": "VALIDATION_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "missing_status_context", "kind": "validation", "variation": "required bank/safe/unpaid/legal context absent for destination state", "outcome": "VALIDATION_REJECTED", "assertions": ["zero writes"]},
    ],
    "received_cheque.undo": [
        {"suffix": "latest_leaf", "kind": "success", "variation": "latest event has no blocking transfer/settlement/balance dependency", "outcome": "COMMITTED", "assertions": ["only latest transition reversed", "current pointer restored", "history chain remains valid"]},
        {"suffix": "not_latest", "kind": "concurrency", "variation": "expected history is no longer current", "outcome": "STALE_VERSION", "assertions": ["zero writes"]},
        {"suffix": "transfer_dependency", "kind": "validation", "variation": "current cheque participates in blocking transfer/cession", "outcome": "DEPENDENCY_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "balance_dependency", "kind": "validation", "variation": "undo would violate account/safe balance", "outcome": "DEPENDENCY_REJECTED", "assertions": ["zero writes"]},
    ],
    "payable_cheque.change_status": [
        {"suffix": "allowed_edge", "kind": "success", "variation": "configured edge and valid cheque-book/pay context", "outcome": "COMMITTED", "assertions": ["one new history event", "current pointer and book item agree"]},
        {"suffix": "invalid_edge", "kind": "workflow", "variation": "edge absent from configured workflow", "outcome": "WORKFLOW_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "book_item_conflict", "kind": "validation", "variation": "book item already linked incompatibly", "outcome": "DEPENDENCY_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "invalid_pay_balance", "kind": "validation", "variation": "pay or balance constraints fail", "outcome": "DEPENDENCY_REJECTED", "assertions": ["zero writes"]},
    ],
    "payable_cheque.undo": [
        {"suffix": "latest_leaf", "kind": "success", "variation": "latest event and book/pay/voucher dependencies reversible", "outcome": "COMMITTED", "assertions": ["current pointer restored", "book item state restored", "history chain valid"]},
        {"suffix": "not_latest", "kind": "concurrency", "variation": "expected history is no longer current", "outcome": "STALE_VERSION", "assertions": ["zero writes"]},
        {"suffix": "voucher_dependency", "kind": "validation", "variation": "voucher check blocks undo", "outcome": "DEPENDENCY_REJECTED", "assertions": ["zero writes"]},
        {"suffix": "other_cheque_on_book_item", "kind": "validation", "variation": "book item leaf belongs to another/latest cheque", "outcome": "DEPENDENCY_REJECTED", "assertions": ["zero writes"]},
    ],
}


GENERIC_MUTATION_CASES = (
    {"suffix": "auth_denied", "kind": "authorization", "variation": "actor lacks atomic command capability", "outcome": "AUTH_DENIED", "assertions": ["zero writes", "denial audit without sensitive values"]},
    {"suffix": "scope_denied", "kind": "scope", "variation": "aggregate outside actor DC/sale-office/stock scope", "outcome": "SCOPE_DENIED", "assertions": ["zero writes"]},
    {"suffix": "stale_version", "kind": "concurrency", "variation": "expected_version/current history differs", "outcome": "STALE_VERSION", "assertions": ["zero writes", "current state returned"]},
    {"suffix": "duplicate_command_id", "kind": "idempotency", "variation": "same command_id retried after committed response loss", "outcome": "REPLAY_PRIOR_RESULT", "assertions": ["one logical write set", "same deterministic result"]},
    {"suffix": "fault_after_first_write", "kind": "failure_injection", "variation": "fault injected after first durable statement before command completion", "outcome": "ROLLED_BACK", "assertions": ["no partial aggregate/history/ledger writes", "retry remains safe"]},
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--side-effects", required=True, type=Path)
    parser.add_argument("--state-machines", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    side_effects = _load(args.side_effects)
    states = _load(args.state_machines)
    traces = {row["command"]: row for row in side_effects["command_traces"]}
    mutation_commands = sorted(
        command for command, row in traces.items() if row["mutation_expected"]
    )
    if set(COMMAND_SPECIFICS) != set(mutation_commands):
        raise ValueError("Golden command specification does not cover every mutating trace exactly")

    cases: list[dict[str, Any]] = []
    for command in mutation_commands:
        trace = traces[command]
        for template in (*GENERIC_MUTATION_CASES, *COMMAND_SPECIFICS[command]):
            cases.append(
                {
                    "case_id": f"{command}.{template['suffix']}",
                    "command": command,
                    "kind": template["kind"],
                    "synthetic_variation": template["variation"],
                    "expected_outcome": template["outcome"],
                    "assertions": template["assertions"],
                    "expected_mutation_scope": trace["mutated_references"],
                    "expected_ledger_or_history_scope": trace["ledger_and_history_references"],
                    "source_sql_objects": trace["sql_objects"],
                }
            )

    read_cases = [
        {
            "case_id": "inventory.stock_goods.read.scope_and_no_side_effect",
            "command": "inventory.stock_goods.read",
            "kind": "read_contract",
            "synthetic_variation": "two StockDC scopes with same GoodsRef",
            "expected_outcome": "SCOPED_READ",
            "assertions": ["only authorized AccYear/DC/StockDC rows", "zero writes", "snapshot quantities labeled as projection"],
            "expected_mutation_scope": [],
            "expected_ledger_or_history_scope": [],
            "source_sql_objects": traces["inventory.stock_goods.read"]["sql_objects"],
        },
        {
            "case_id": "received_cheque.validate_transition.side_effect_free",
            "command": "received_cheque.validate_transition",
            "kind": "read_contract",
            "synthetic_variation": "allowed and disallowed received-cheque edges",
            "expected_outcome": "DETERMINISTIC_VALIDATION",
            "assertions": ["matches configured edge catalog", "zero writes"],
            "expected_mutation_scope": [],
            "expected_ledger_or_history_scope": traces["received_cheque.validate_transition"]["ledger_and_history_references"],
            "source_sql_objects": traces["received_cheque.validate_transition"]["sql_objects"],
        },
        {
            "case_id": "payable_cheque.validate_transition.side_effect_free",
            "command": "payable_cheque.validate_transition",
            "kind": "read_contract",
            "synthetic_variation": "allowed and disallowed payable-cheque edges",
            "expected_outcome": "DETERMINISTIC_VALIDATION",
            "assertions": ["matches configured edge catalog", "zero writes"],
            "expected_mutation_scope": [],
            "expected_ledger_or_history_scope": traces["payable_cheque.validate_transition"]["ledger_and_history_references"],
            "source_sql_objects": traces["payable_cheque.validate_transition"]["sql_objects"],
        },
    ]
    cases.extend(read_cases)
    kind_counts: dict[str, int] = {}
    for case in cases:
        kind_counts[case["kind"]] = kind_counts.get(case["kind"], 0) + 1
    artifact = {
        "artifact": "varanegar_target_erp_golden_command_cases",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "sources": {
            "command_side_effects": args.side_effects.as_posix(),
            "state_machine_catalog": args.state_machines.as_posix(),
        },
        "safety": {
            "mode": "OFFLINE_SYNTHETIC_TEST_DESIGN",
            "database_connections": 0,
            "live_ui_actions": 0,
            "commands_executed": 0,
            "business_rows_or_values_used": 0,
            "synthetic_cases_only": 1,
        },
        "summary": {
            "source_command_trace_count": len(traces),
            "mutating_command_count": len(mutation_commands),
            "case_count": len(cases),
            "generic_mutation_case_count": len(mutation_commands) * len(GENERIC_MUTATION_CASES),
            "command_specific_case_count": sum(len(rows) for rows in COMMAND_SPECIFICS.values()),
            "read_or_validation_case_count": len(read_cases),
            "kind_counts": dict(sorted(kind_counts.items())),
            "state_machine_count": states["summary"]["machine_count"],
        },
        "execution_gate": [
            "These are target-ERP test contracts, not tests executed against Varanegar.",
            "Run only against an isolated target test database seeded with synthetic fixtures.",
            "Never run failure injection or mutation cases against the Varanegar clone or production runtime.",
            "A command is pilot-ready only after all success, denial, stale-version, retry, rollback and reconciliation cases pass.",
        ],
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
