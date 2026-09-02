"""Build synthetic Golden cases for supplier, operational context, and pricing."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


COMMON = (
    ("success", "success", "authorized valid command commits exactly one target outcome"),
    ("authorization_denied", "authorization", "denied actor changes no aggregate, relation, audit result, or outbox business event"),
    ("scope_denied", "scope", "out-of-scope aggregate is neither disclosed nor changed"),
    ("missing_command_id", "validation", "command without idempotency identity is rejected before mutation"),
    ("duplicate_same_payload", "idempotency", "same command id and payload returns the original durable result"),
    ("duplicate_conflicting_payload", "idempotency", "same command id with a different fingerprint is rejected"),
    ("stale_expected_version", "concurrency", "stale command is rejected without overwriting current state"),
    ("operation_context_closed", "context", "closed or invalid operating context blocks mutation"),
    ("fault_after_aggregate_stage", "failure_injection", "fault before commit leaves no accepted partial aggregate or relation set"),
    ("fault_after_commit_before_response", "failure_injection", "retry converges to the one committed outcome without duplication"),
    ("blocking_reconciliation_difference", "reconciliation", "outcome remains unaccepted while a blocking difference is unresolved"),
)


SPECIFIC: dict[str, tuple[tuple[str, str, str], ...]] = {
    "master_data.supplier.save": (
        ("duplicate_code_or_national_identity", "validation", "duplicate supplier identity is rejected or quarantined"),
        ("invalid_contact_or_dl_relation", "validation", "invalid contact/DL relation blocks the aggregate"),
        ("invalid_accounting_group", "validation", "invalid accounting group blocks activation"),
        ("after_save_or_cardex_fault", "failure_injection", "supplier, after-save effects and cardex provenance converge atomically"),
        ("attachment_policy_violation", "validation", "attachment policy failure leaves no partial supplier"),
    ),
    "master_data.supplier.delete": (
        ("aggregate_not_found", "validation", "unknown delete has a stable rejected or idempotent-not-found result"),
        ("in_use_by_payment", "workflow", "payment usage guard blocks physical removal"),
        ("in_use_by_document_or_cardex", "workflow", "document/cardex provenance blocks physical removal"),
        ("contact_and_accounting_retention", "validation", "delete cannot orphan contact/DL/accounting relations"),
        ("fault_after_usage_guard", "failure_injection", "usage guard and accepted transition cannot diverge"),
    ),
    "organization_context.operational_year.save": (
        ("overlapping_year_window", "validation", "overlapping operational year range is rejected"),
        ("invalid_start_end_dates", "validation", "end before start is rejected"),
        ("fiscal_year_identity_substitution", "validation", "fiscal and operational year identities cannot be substituted"),
        ("duplicate_year_code", "validation", "duplicate scoped operational-year code is rejected"),
        ("fault_after_context_publish", "failure_injection", "published context and audit/outbox converge atomically"),
    ),
    "organization_context.operational_year.delete": (
        ("aggregate_not_found", "validation", "unknown year delete is stable"),
        ("current_or_open_year", "workflow", "current/open operational year cannot be physically deleted"),
        ("in_use_by_business_documents", "workflow", "used operational year preserves document provenance"),
        ("fiscal_context_dependency", "validation", "fiscal-context dependency blocks invalid removal"),
        ("fault_after_in_use_guard", "failure_injection", "guard and accepted inactive transition cannot diverge"),
    ),
    "organization_context.stock_dc.save": (
        ("invalid_dc_sale_office_stock_combination", "validation", "invalid context combination is rejected"),
        ("stock_type_flag_encoding_mismatch", "validation", "ambiguous sequential/bit-flag type encoding is rejected"),
        ("invalid_ship_type", "validation", "unknown ship type blocks save"),
        ("duplicate_dc_sale_office_relation", "validation", "duplicate scoped relation is rejected"),
        ("fault_after_relation_stage", "failure_injection", "stock/DC and office relations commit atomically"),
    ),
    "organization_context.stock_dc.delete": (
        ("aggregate_not_found", "validation", "unknown stock/DC delete is stable"),
        ("in_use_by_stock_or_ledger", "workflow", "stock/cardex/ledger usage blocks physical deletion"),
        ("in_use_by_sale_office", "workflow", "active office relation blocks invalid removal"),
        ("active_operational_context", "context", "active context must be retired by an approved transition"),
        ("fault_after_in_use_guard", "failure_injection", "guard and relation cleanup cannot diverge"),
    ),
    "inventory.stock_accounting_context.save": (
        ("invalid_stock_dc", "validation", "unknown or incompatible stock/DC blocks save"),
        ("invalid_price_method", "validation", "unsupported price method is rejected"),
        ("stock_has_price_guard", "workflow", "existing priced stock requires the declared guarded transition"),
        ("duplicate_lookup_membership", "validation", "duplicate stock-accounting membership is rejected"),
        ("fault_after_lookup_update", "failure_injection", "context and lookup membership converge atomically"),
    ),
    "inventory.stock_accounting_context.delete": (
        ("aggregate_not_found", "validation", "unknown context delete is stable"),
        ("stock_has_price_or_cardex", "workflow", "price/cardex usage blocks physical removal"),
        ("in_use_by_accounting_document", "workflow", "accounting provenance blocks invalid removal"),
        ("lookup_membership_cleanup_guard", "validation", "delete cannot leave stale membership"),
        ("fault_after_usage_guard", "failure_injection", "guard and membership transition cannot diverge"),
    ),
    "pricing_rules.contextual_price.save": (
        ("overlap_without_deterministic_priority", "validation", "ambiguous overlapping scope is rejected"),
        ("invalid_customer_geography_dc_scope", "validation", "invalid qualification scope blocks publish"),
        ("currency_batch_package_unit_mismatch", "validation", "incompatible price dimensions block publish"),
        ("invalid_effective_window_or_close_state", "validation", "invalid effective/close window is rejected"),
        ("fault_after_priority_version_stage", "failure_injection", "rule version and priority publish atomically"),
    ),
    "pricing_rules.contextual_price.delete": (
        ("aggregate_not_found", "validation", "unknown rule delete is stable"),
        ("used_by_order_or_sale", "workflow", "used price version cannot be physically deleted"),
        ("close_instead_of_delete", "workflow", "published price is closed/versioned rather than erased"),
        ("history_and_explain_retention", "reconciliation", "historical explain trace remains reproducible"),
        ("fault_after_close_guard", "failure_injection", "close/history and current pointer cannot diverge"),
    ),
    "pricing_rules.discount_rule.save": (
        ("invalid_condition_or_group_operator", "validation", "invalid condition DSL is rejected"),
        ("invalid_customer_goods_order_scope", "validation", "invalid scope relation blocks publish"),
        ("invalid_prize_or_package", "validation", "invalid prize/package relation blocks publish"),
        ("overlap_priority_effective_state", "validation", "ambiguous effective overlap is rejected"),
        ("prevent_sale_capability_required", "authorization", "prevent-sale behavior requires explicit capability"),
    ),
    "pricing_rules.discount_rule.delete": (
        ("aggregate_not_found", "validation", "unknown rule delete is stable"),
        ("active_rule_requires_close", "workflow", "active rule must be closed/inactivated, not erased"),
        ("used_by_sale_calculation", "workflow", "used discount/prize version preserves provenance"),
        ("condition_arrangement_history_retention", "reconciliation", "historical qualification remains reproducible"),
        ("fault_after_close_guard", "failure_injection", "close/history and active pointer cannot diverge"),
    ),
}


def _case(command: str, module: str, suffix: str, kind: str, expected: str, fixture: str) -> dict[str, Any]:
    return {"case_id": f"{command}.{suffix}", "command": command, "target_module": module, "kind": kind, "fixture": fixture, "variation": suffix, "expected": expected, "assertions": ["target transaction boundary respected", "stable audit/validation reason recorded", "source Varanegar and read-only clone untouched"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplier-contract", required=True, type=Path)
    parser.add_argument("--operational-context-contracts", required=True, type=Path)
    parser.add_argument("--pricing-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    supplier = json.loads(args.supplier_contract.read_text(encoding="utf-8-sig"))
    context = json.loads(args.operational_context_contracts.read_text(encoding="utf-8-sig"))
    pricing = json.loads(args.pricing_contracts.read_text(encoding="utf-8-sig"))
    if any(row.get("validation") != "PASS" for row in (supplier, context, pricing)):
        raise ValueError("validated source command contracts are required")
    command_modules = {
        supplier["contract"]["target_command_candidate"]: "master_data",
        supplier["contract"]["secondary_delete_command_candidate"]: "master_data",
    }
    for row in context["contracts"]:
        module = "organization_context" if row["target_command_candidate"].startswith("organization_context.") else "inventory"
        command_modules[row["target_command_candidate"]] = module
        command_modules[row["secondary_delete_command_candidate"]] = module
    for row in pricing["contracts"]:
        command_modules[row["target_command_candidate"]] = "pricing_rules"
        command_modules[row["secondary_delete_command_candidate"]] = "pricing_rules"
    if set(command_modules) != set(SPECIFIC):
        raise ValueError(f"unexpected command set: {sorted(set(command_modules) ^ set(SPECIFIC))}")
    cases = []
    for command, module in command_modules.items():
        for suffix, kind, expected in COMMON:
            cases.append(_case(command, module, suffix, kind, expected, "synthetic_minimum_valid_foundation_fixture_with_one_variation"))
        for suffix, kind, expected in SPECIFIC[command]:
            cases.append(_case(command, module, suffix, kind, expected, "synthetic_supplier_context_or_pricing_boundary_fixture"))
    duplicate_ids = sorted(case_id for case_id, count in Counter(row["case_id"] for row in cases).items() if count > 1)
    kinds = Counter(row["kind"] for row in cases)
    modules = Counter(row["target_module"] for row in cases)
    artifact = {
        "artifact": "negin_erp_supplier_operational_context_and_pricing_synthetic_golden_cases",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not duplicate_ids else "FAIL",
        "safety": {"mode": "OFFLINE_SYNTHETIC_TARGET_TEST_DESIGN", "database_connections": 0, "live_ui_actions": 0, "source_or_target_commands_executed": 0, "business_rows_or_values_used": 0, "synthetic_cases_only": 1},
        "summary": {"source_command_count": len(command_modules), "case_count": len(cases), "common_case_count": len(command_modules) * len(COMMON), "domain_specific_case_count": sum(len(rows) for rows in SPECIFIC.values()), "failure_injection_case_count": kinds["failure_injection"], "duplicate_case_id_count": len(duplicate_ids), "target_module_case_counts": dict(sorted(modules.items())), "kind_counts": dict(sorted(kinds.items()))},
        "execution_policy": {"allowed_environment": "isolated target test database with synthetic fixtures only", "forbidden_environment": ["operational Varanegar", "NeginPakhsh_WebDev clone", "target production database"], "source_mode": "Varanegar remains untouched and disconnected during execution"},
        "cases": cases,
        "duplicate_case_ids": duplicate_ids,
        "limits": ["Designed cases are not runtime proof.", "Owner-approved scope, values, precedence, retention, and isolated execution remain required."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
