"""Build synthetic Golden contracts for customer and goods master-data commands.

This generator is deliberately offline.  It consumes only the already-redacted
static command contract and never imports or executes a Varanegar assembly.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


COMMON_CASES: tuple[tuple[str, str, str], ...] = (
    ("success", "success", "authorized valid command commits exactly one target outcome"),
    ("authorization_denied", "authorization", "denied actor changes no aggregate, relation, audit result, or outbox business event"),
    ("scope_denied", "scope", "out-of-scope aggregate is neither disclosed nor changed"),
    ("missing_command_id", "validation", "command without an idempotency identity is rejected before mutation"),
    ("duplicate_same_payload", "idempotency", "same command id and payload returns the original durable result"),
    ("duplicate_conflicting_payload", "idempotency", "same command id with a different fingerprint is rejected"),
    ("stale_expected_version", "concurrency", "stale command is rejected without overwriting the current aggregate"),
    ("operation_context_closed", "context", "closed or invalid operating context blocks mutation"),
    ("fault_after_aggregate_stage", "failure_injection", "fault before commit leaves no accepted partial aggregate or relation set"),
    ("fault_after_commit_before_response", "failure_injection", "retry converges to the one committed outcome without duplication"),
    ("blocking_reconciliation_difference", "reconciliation", "outcome remains unaccepted while a blocking difference is unresolved"),
)


SPECIFIC_CASES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "master_data.customer.save": (
        ("duplicate_business_key", "validation", "duplicate customer business key is rejected or explicitly quarantined"),
        ("invalid_parent_or_dl_crosswalk", "validation", "invalid parent or accounting-detail crosswalk blocks save"),
        ("headquarters_permission_required", "authorization", "head-office-only attributes require the declared capability and scope"),
        ("credit_account_relation_invalid", "validation", "invalid credit/account relation leaves no partial child collection"),
        ("fault_after_child_relation_stage", "failure_injection", "customer and account relations commit atomically or not at all"),
    ),
    "master_data.customer.delete": (
        ("aggregate_not_found", "validation", "unknown customer delete is a stable rejected or idempotent-not-found result"),
        ("in_use_by_sales_or_ledger", "workflow", "referenced customer cannot be physically removed"),
        ("inactive_instead_of_delete_policy", "workflow", "retention policy preserves provenance through an explicit inactive transition"),
        ("child_relation_cleanup_guard", "validation", "delete cannot orphan customer accounts, groups, routes, or addresses"),
        ("fault_after_delete_guard", "failure_injection", "guard evaluation and accepted state transition cannot diverge"),
    ),
    "master_data.goods.save": (
        ("duplicate_barcode", "validation", "duplicate barcode is rejected or quarantined under an explicit policy"),
        ("invalid_supplier_relation", "validation", "invalid supplier-product relation blocks the aggregate"),
        ("package_or_batch_package_inconsistent", "validation", "package and batch-package quantities remain internally consistent"),
        ("invalid_group_crosswalk", "validation", "unknown or ambiguous goods group crosswalk blocks activation"),
        ("fault_after_child_relation_stage", "failure_injection", "goods and barcode/supplier/package relations commit atomically or not at all"),
    ),
    "master_data.goods.delete": (
        ("aggregate_not_found", "validation", "unknown goods delete is a stable rejected or idempotent-not-found result"),
        ("in_use_by_stock_or_document", "workflow", "goods referenced by stock or documents cannot be physically removed"),
        ("replication_delete_guard", "workflow", "replicated goods require the explicit legacy-compatible delete guard"),
        ("child_relation_cleanup_guard", "validation", "delete cannot orphan barcode, supplier, package, batch, or DC relations"),
        ("fault_after_delete_guard", "failure_injection", "guard evaluation and accepted state transition cannot diverge"),
    ),
}


def _case(command: str, suffix: str, kind: str, expected: str, fixture: str) -> dict[str, Any]:
    return {
        "case_id": f"{command}.{suffix}",
        "command": command,
        "target_module": "master_data",
        "kind": kind,
        "fixture": fixture,
        "variation": suffix,
        "expected": expected,
        "assertions": [
            "target transaction boundary respected",
            "stable authorization, validation, and audit reason recorded",
            "source Varanegar and read-only clone untouched",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.command_contracts.read_text(encoding="utf-8-sig"))
    if source.get("validation") != "PASS":
        raise ValueError("validated customer/goods command contracts are required")
    commands = []
    for contract in source["contracts"]:
        commands.extend((contract["target_command_candidate"], contract["secondary_delete_command_candidate"]))
    if set(commands) != set(SPECIFIC_CASES):
        raise ValueError(f"unexpected command set: {sorted(commands)}")

    cases: list[dict[str, Any]] = []
    for command in commands:
        for suffix, kind, expected in COMMON_CASES:
            cases.append(_case(command, suffix, kind, expected, "synthetic_minimum_valid_master_fixture_with_one_declared_variation"))
        for suffix, kind, expected in SPECIFIC_CASES[command]:
            cases.append(_case(command, suffix, kind, expected, "synthetic_customer_or_goods_relation_boundary_fixture"))

    duplicate_ids = sorted(case_id for case_id, count in Counter(row["case_id"] for row in cases).items() if count > 1)
    kind_counts = Counter(row["kind"] for row in cases)
    artifact = {
        "artifact": "negin_erp_customer_goods_master_data_synthetic_golden_cases",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not duplicate_ids else "FAIL",
        "safety": {
            "mode": "OFFLINE_SYNTHETIC_TARGET_TEST_DESIGN",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_values_used": 0,
            "synthetic_cases_only": 1,
        },
        "summary": {
            "source_command_count": len(commands),
            "case_count": len(cases),
            "common_case_count": len(commands) * len(COMMON_CASES),
            "domain_specific_case_count": sum(len(rows) for rows in SPECIFIC_CASES.values()),
            "failure_injection_case_count": kind_counts["failure_injection"],
            "duplicate_case_id_count": len(duplicate_ids),
            "kind_counts": dict(sorted(kind_counts.items())),
        },
        "execution_policy": {
            "allowed_environment": "isolated target test database with synthetic fixtures only",
            "forbidden_environment": ["operational Varanegar", "NeginPakhsh_WebDev clone", "target production database"],
            "source_mode": "Varanegar remains untouched and disconnected during execution",
        },
        "source_rule_signals": source["rule_signals"],
        "cases": cases,
        "duplicate_case_ids": duplicate_ids,
        "limits": [
            "These are target design contracts, not evidence that the legacy or future target command has executed successfully.",
            "Runtime requiredness, branch values, permissions, relation cardinality, error text, and side effects still require owner review and isolated execution.",
            "Physical delete versus inactivation/retention remains an owner-approved target policy decision.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
