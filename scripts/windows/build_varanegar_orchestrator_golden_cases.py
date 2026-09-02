"""Generate synthetic Golden cases for high-impact target ERP orchestrators."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SPECIFIC_CASES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "order.save": (
        ("duplicate_item", "validation", "duplicate goods/item is rejected without a partial order"),
        ("credit_exceeded", "validation", "customer/dealer credit failure leaves no accepted order"),
        ("batch_dates_missing", "validation", "required production/expiry dates block save"),
    ),
    "order.cancel": (
        ("downstream_conversion_blocks_cancel", "workflow", "sale/conversion dependency prevents invalid cancel"),
        ("reservation_release_rejected", "reconciliation", "cancel remains unaccepted until reservation outcome reconciles"),
        ("current_pointer_conflict", "concurrency", "concurrent state advance rejects cancel"),
    ),
    "order.convert_to_sale": (
        ("source_not_ready", "workflow", "conversion validation rejects the source state"),
        ("calculation_mismatch", "reconciliation", "sale is not accepted with pricing/discount/prize mismatch"),
        ("concurrent_conversion", "concurrency", "only one sale identity is returned for competing conversion commands"),
    ),
    "sales_return.save": (
        ("return_exceeds_remaining", "validation", "remaining return quantity cannot become negative"),
        ("source_sale_not_returnable", "workflow", "non-returnable sale produces no return aggregate"),
        ("batch_or_health_mismatch", "validation", "item/detail batch and health mismatch blocks save"),
    ),
    "sales_return.cancel_and_generate_voucher": (
        ("voucher_dependency_failure", "failure_injection", "cancel is not accepted without a durable voucher outcome"),
        ("settlement_compensation_failure", "failure_injection", "financial compensation failure is visible and recoverable"),
        ("duplicate_cancel", "idempotency", "retry returns the original cancel/voucher outcome"),
    ),
    "supplier_invoice.save": (
        ("duplicate_supplier_invoice_no", "validation", "duplicate scoped number is rejected"),
        ("missing_or_lower_priority_toll", "validation", "toll coverage/priority violation blocks invoice"),
        ("remaining_quantity_exceeded", "validation", "linked inventory quantity cannot be over-consumed"),
    ),
    "supplier_return.save": (
        ("return_exceeds_supplier_invoice", "validation", "supplier return cannot exceed remaining quantity"),
        ("invalid_inventory_voucher", "validation", "invalid source inventory voucher blocks return"),
        ("inactive_supplier", "validation", "inactive supplier blocks new return save"),
    ),
    "stock_voucher.save": (
        ("negative_stock_policy", "validation", "disallowed negative/on-hand result blocks ledger append"),
        ("batch_health_mismatch", "validation", "batch/health/stock context mismatch blocks save"),
        ("header_item_detail_mismatch", "reconciliation", "quantity mismatch leaves no accepted voucher"),
    ),
    "stock_voucher.confirm_or_unconfirm": (
        ("closed_operation_date", "context", "closed date blocks transition"),
        ("cardex_quantity_mismatch", "reconciliation", "confirmation remains unaccepted until cardex matches"),
        ("posting_dependency_failure", "failure_injection", "posting failure is retryable without duplicate state event"),
    ),
    "stock_voucher.generate_return": (
        ("source_not_returnable", "workflow", "invalid source voucher produces no return"),
        ("duplicate_return_request", "idempotency", "retry returns the original return voucher identity"),
        ("net_quantity_mismatch", "reconciliation", "return is not accepted until net ledger quantity reconciles"),
    ),
}


def _case_id(command: str, suffix: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "_", f"{command}.{suffix}".casefold())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commands", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    command_artifact = json.loads(args.commands.read_text(encoding="utf-8-sig"))
    if command_artifact.get("validation") != "PASS":
        raise ValueError("validated orchestrator command contracts are required")
    commands = {row["command"]: row for row in command_artifact["commands"]}
    missing_specific = sorted(set(commands) - set(SPECIFIC_CASES))
    if missing_specific:
        raise ValueError(f"missing specific cases for: {missing_specific}")

    cases: list[dict[str, Any]] = []
    for command, contract in commands.items():
        common = (
            ("success", "success", "authorized valid command commits once and reconciles"),
            ("authorization_denied", "authorization", "no state, audit command result, or outbox business event is committed"),
            ("scope_denied", "scope", "out-of-scope aggregate is not disclosed or changed"),
            ("stale_expected_version", "concurrency", "stale command is rejected with current version metadata only"),
            ("duplicate_command_id", "idempotency", "same payload returns the original result; different payload is rejected"),
            ("operation_context_closed", "context", "closed fiscal/DC/date context blocks mutation"),
            ("blocking_reconciliation_difference", "reconciliation", "command outcome is not accepted while blocking_unknown remains"),
        )
        for suffix, kind, expected in common:
            cases.append(
                {
                    "case_id": _case_id(command, suffix),
                    "command": command,
                    "kind": kind,
                    "fixture": "synthetic_minimum_valid_fixture_with_single_declared_variation",
                    "variation": suffix,
                    "expected": expected,
                    "assertions": ["target transaction boundary respected", "audit decision recorded", "source Varanegar untouched"],
                }
            )
        for stage in contract["failure_injection_after"]:
            suffix = "fault_after_" + re.sub(r"[^a-z0-9]+", "_", stage.casefold()).strip("_")
            cases.append(
                {
                    "case_id": _case_id(command, suffix),
                    "command": command,
                    "kind": "failure_injection",
                    "fixture": "synthetic_valid_command_with_deterministic_fault",
                    "variation": f"inject fault after {stage}",
                    "expected": "no partial accepted business outcome; retry with same command_id converges to one result",
                    "assertions": ["no duplicate aggregate/event/outbox", "reconciliation is zero or explicitly pending/recoverable", "source Varanegar untouched"],
                }
            )
        for suffix, kind, expected in SPECIFIC_CASES[command]:
            cases.append(
                {
                    "case_id": _case_id(command, suffix),
                    "command": command,
                    "kind": kind,
                    "fixture": "synthetic_domain_boundary_fixture",
                    "variation": suffix,
                    "expected": expected,
                    "assertions": ["declared invariants preserved", "audit reason code is stable", "source Varanegar untouched"],
                }
            )

    duplicate_ids = [case_id for case_id in {row["case_id"] for row in cases} if sum(x["case_id"] == case_id for x in cases) > 1]
    kind_counts: dict[str, int] = {}
    for row in cases:
        kind_counts[row["kind"]] = kind_counts.get(row["kind"], 0) + 1
    artifact = {
        "artifact": "negin_erp_high_impact_orchestrator_synthetic_golden_cases",
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
            "common_case_count": len(commands) * 7,
            "failure_injection_case_count": sum(len(row["failure_injection_after"]) for row in commands.values()),
            "domain_specific_case_count": sum(len(rows) for rows in SPECIFIC_CASES.values()),
            "duplicate_case_id_count": len(duplicate_ids),
            "kind_counts": dict(sorted(kind_counts.items())),
        },
        "execution_policy": {
            "allowed_environment": "isolated target test database with synthetic fixtures only",
            "forbidden_environment": ["operational Varanegar", "NeginPakhsh_WebDev clone", "target production database"],
            "source_mode": "Varanegar remains untouched and disconnected during execution",
        },
        "cases": cases,
        "duplicate_case_ids": duplicate_ids,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], "summary": artifact["summary"]}, ensure_ascii=False))
    return 0 if not duplicate_ids else 1


if __name__ == "__main__":
    raise SystemExit(main())
