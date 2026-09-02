"""Derive the cross-domain final-date management boundary from persisted evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _caption(route: dict) -> str:
    value = route.get("menu_caption") or {}
    return value.get("value", "") if isinstance(value, dict) else ""


def _walk_consumer_rows(value: Any) -> list[dict]:
    found: list[dict] = []
    if isinstance(value, dict):
        name = value.get("consumer_name")
        if isinstance(name, str) and "FinalDateManagement" in name:
            found.append(
                {
                    "consumer_schema": value.get("consumer_schema"),
                    "consumer_name": name,
                    "consumer_type": value.get("consumer_type"),
                    "source_schema": value.get("source_schema"),
                    "source_table": value.get("source_table"),
                }
            )
        for child in value.values():
            found.extend(_walk_consumer_rows(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_consumer_rows(child))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--navigation", required=True, type=Path)
    parser.add_argument("--all-form-calls", required=True, type=Path)
    parser.add_argument("--extension-dependency-graph", required=True, type=Path)
    parser.add_argument("--organization-domain", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    navigation = _load(args.navigation)
    forms = _load(args.all_form_calls)
    graph = _load(args.extension_dependency_graph)
    organization = _load(args.organization_domain)
    errors: list[str] = []
    for name, payload in (("navigation", navigation), ("forms", forms), ("graph", graph)):
        if payload.get("validation") not in (None, "PASS"):
            errors.append(f"{name} source is not PASS")
    if organization.get("domain") != "organization_and_fiscal_year":
        errors.append("unexpected organization domain")
    if organization.get("safety", {}).get("can_update") != 0:
        errors.append("organization domain is not read-only")

    routes = [
        row
        for row in navigation.get("routes", [])
        if row.get("root_menu_id") == 900
        and row.get("form_info_id") is not None
        and "تاریخ قطعی" in _caption(row)
    ]
    route_rows = [
        {
            "menu_id": row.get("menu_id"),
            "static_caption": _caption(row),
            "form_info_id": row.get("form_info_id"),
            "access_node_id": row.get("access_node_id"),
            "runtime_coverage_classification": row.get("route_runtime_coverage_classification"),
            "matched_form_type": row.get("matched_form_type"),
        }
        for row in routes
    ]
    route_rows.sort(key=lambda row: row["menu_id"])

    sales_forms = [
        row for row in forms.get("forms", []) if row.get("type") == "VN.SDS.Sales.UI.FinalDateManagement.FormFinalDateManagement"
    ]
    capabilities = [
        row for row in graph.get("capabilities", []) if str(row.get("capability_hint", "")).startswith("configuration.final_date_")
    ]
    business_contracts = [
        row for row in graph.get("business_contracts", []) if "FinalDateManagement" in str(row.get("type", ""))
    ]
    data_contracts = [
        row for row in graph.get("data_access_contracts", []) if "FinalDateManagement" in str(row.get("type", ""))
    ]
    business_updates = sorted({method for row in business_contracts for method in row.get("contract", {}).get("write_like_methods", [])})
    business_validations = sorted({method for row in business_contracts for method in row.get("contract", {}).get("validation_methods", [])})
    data_updates = sorted({method for row in data_contracts for method in row.get("contract", {}).get("write_like_methods", [])})
    data_validations = sorted({method for row in data_contracts for method in row.get("contract", {}).get("validation_methods", [])})
    consumer_rows = _walk_consumer_rows(organization)
    consumer_rows = sorted(
        {json.dumps(row, sort_keys=True): row for row in consumer_rows}.values(),
        key=lambda row: (str(row["consumer_schema"]), str(row["consumer_name"]), str(row["source_table"])),
    )

    if len(route_rows) != 5:
        errors.append("final-date route count drift")
    if len(sales_forms) != 1:
        errors.append("sales final-date form contract mismatch")
    if len(capabilities) != 3:
        errors.append("extension final-date capability count mismatch")
    if any(row.get("has_direct_ui_data_access_coupling") for row in capabilities):
        errors.append("unexpected direct UI data access coupling")

    classifications = Counter(row["runtime_coverage_classification"] for row in route_rows)
    artifact = {
        "artifact": "varanegar_cross_domain_final_date_management_command_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_REDACTED_STATIC_UI_AND_READ_ONLY_AGGREGATE_DOMAIN_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "application_or_final_date_commands_executed": 0,
            "business_dates_rows_or_values_read_or_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "configured_final_date_route_count": len(route_rows),
            "runtime_matched_route_count": sum(bool(row["matched_form_type"]) for row in route_rows),
            "runtime_unmatched_route_count": sum(not row["matched_form_type"] for row in route_rows),
            "runtime_coverage_classification_counts": dict(sorted(classifications.items())),
            "sales_runtime_form_contract_count": len(sales_forms),
            "extension_final_date_capability_count": len(capabilities),
            "extension_capability_with_business_mediation_count": sum(bool(row.get("has_business_mediation_evidence")) for row in capabilities),
            "extension_capability_with_direct_ui_data_access_count": sum(bool(row.get("has_direct_ui_data_access_coupling")) for row in capabilities),
            "business_update_method_count": len(business_updates),
            "business_validation_method_count": len(business_validations),
            "data_access_update_method_count": len(data_updates),
            "data_access_validation_method_count": len(data_validations),
            "clone_final_date_consumer_edge_count": len(consumer_rows),
            "runtime_effect_parity_proven_count": 0,
            "golden_case_executed_count": 0,
            "validation_error_count": len(errors),
        },
        "target_commands": [
            {"command": "configuration.set_sales_final_date", "scope": ["dc", "fiscal_year"], "legacy_signal": "UpdateDateManagement"},
            {"command": "configuration.set_purchase_final_date", "scope": ["dc", "fiscal_year"], "legacy_signal": "UpdateDateManagementBuy"},
            {"command": "configuration.set_financial_final_date", "scope": ["dc", "fiscal_year"], "legacy_signal": "UpdateDateManagementMali"},
            {"command": "configuration.set_petty_cash_final_date", "scope": ["dc", "fiscal_year"], "legacy_signal": "UpdateDateManagementTankhah"},
        ],
        "command_invariants": [
            "each boundary is independently versioned by DC and fiscal year",
            "a new final date cannot precede the accepted prior boundary without an explicit reopen command",
            "open-date and close-date semantics remain distinct",
            "the command validates affected sales, purchase, treasury, petty-cash and accounting consumers before commit",
            "the accepted change and audit/outbox append are atomic",
            "replay with the same command id produces one accepted version",
            "no operational document is silently rewritten when a boundary changes",
        ],
        "routes": route_rows,
        "sales_form_contract": sales_forms[0] if sales_forms else None,
        "extension_capabilities": capabilities,
        "business_method_contract": {"updates": business_updates, "validations": business_validations},
        "data_access_method_contract": {"updates": data_updates, "validations": data_validations},
        "clone_consumer_edges": consumer_rows,
        "implementation_gate": "owner-approved date semantics, exact SQL effect inventory, synthetic stale/reopen/overlap/failure cases, authenticated UAT and reconciliation on an isolated target",
        "evidence_limits": [
            "Static method and dependency names prove a layered command path, not result parity or transaction ownership.",
            "Three setting forms are present-package but runtime-unmatched in the captured navigation evidence.",
            "No actual final-date value, affected document, identity, validation result or command effect was read or persisted.",
            "No final-date command or validation procedure was executed.",
        ],
        "source_paths": {
            "navigation": args.navigation.as_posix(),
            "all_form_calls": args.all_form_calls.as_posix(),
            "extension_dependency_graph": args.extension_dependency_graph.as_posix(),
            "organization_domain": args.organization_domain.as_posix(),
        },
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
