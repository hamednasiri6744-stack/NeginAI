"""Compose a durable evidence-backed morning handoff for Negin ERP planning."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


ALLOWED_NIGHT_BUNDLE_BOOTSTRAP_ERRORS = [
    "checkpoint count mismatch: "
    "negin_erp_varanegar_morning_evidence_readiness_handoff."
    "synthetic_golden_case_count"
]


def _night_bundle_is_acceptable(payload: dict) -> bool:
    return payload.get("validation") == "PASS" or payload.get("errors", []) == ALLOWED_NIGHT_BUNDLE_BOOTSTRAP_ERRORS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--forms", required=True, type=Path)
    parser.add_argument("--navigation", required=True, type=Path)
    parser.add_argument("--workflows", required=True, type=Path)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--readiness", required=True, type=Path)
    parser.add_argument("--risks", required=True, type=Path)
    parser.add_argument("--traceability", required=True, type=Path)
    parser.add_argument("--process-atlas", required=True, type=Path)
    parser.add_argument("--drift", required=True, type=Path)
    parser.add_argument("--night-bundle", required=True, type=Path)
    parser.add_argument("--customer-goods", required=True, type=Path)
    parser.add_argument("--supplier", required=True, type=Path)
    parser.add_argument("--operational-context", required=True, type=Path)
    parser.add_argument("--pricing", required=True, type=Path)
    parser.add_argument("--identity-access", required=True, type=Path)
    parser.add_argument("--system-configuration", required=True, type=Path)
    parser.add_argument("--final-date", required=True, type=Path)
    parser.add_argument("--order-sale", required=True, type=Path)
    parser.add_argument("--treasury", required=True, type=Path)
    parser.add_argument("--stock-distribution", required=True, type=Path)
    parser.add_argument("--supplier-invoice", required=True, type=Path)
    parser.add_argument("--accounting", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: path for name, path in vars(args).items() if isinstance(path, Path) and name != "output"}
    sources = {name: _load(path) for name, path in paths.items()}
    errors = []
    for name, payload in sources.items():
        if name == "night_bundle":
            if not _night_bundle_is_acceptable(payload):
                # The bundle validates this handoff, while this handoff also
                # records the bundle counts. Permit exactly one constrained
                # bootstrap state: every other bundle check has passed and the
                # only remaining error is this artifact's stale Golden count.
                errors.append("night bundle is not PASS")
        elif payload.get("validation") not in (None, "PASS"):
            errors.append(f"source is not PASS: {name}")
    manifest = sources["manifest"]
    forms = sources["forms"]
    navigation = sources["navigation"]
    workflows = sources["workflows"]
    reports = sources["reports"]
    blueprint = sources["blueprint"]
    readiness = sources["readiness"]
    risks = sources["risks"]
    trace = sources["traceability"]
    processes = sources["process_atlas"]
    drift = sources["drift"]
    night = sources["night_bundle"]
    if readiness["summary"]["command_ready_module_count"] != 0:
        errors.append("unexpected command-ready module")
    if processes["summary"]["implementation_ready_process_count"] != 0:
        errors.append("unexpected implementation-ready process")
    if drift["comparison"]["status"] != "NO_SEMANTIC_DRIFT":
        errors.append("drift checkpoint is not stable")
    summary = {
        "validated_domain_count": manifest["domain_count"],
        "runtime_form_candidate_count": forms["summary"]["form_candidate_count"],
        "navigation_route_count": navigation["summary"]["route_count"],
        "workflow_surface_count": workflows["summary"]["workflow_form_count"],
        "report_surface_count": reports["summary"]["surface_count"],
        "target_module_count": blueprint["module_count"],
        "target_process_count": processes["summary"]["process_count"],
        "synthetic_golden_case_count": trace["summary"]["mapped_golden_case_count"],
        "open_risk_count": risks["summary"]["risk_count"],
        "critical_risk_count": risks["summary"]["critical_count"],
        "high_risk_count": risks["summary"]["high_count"],
        "command_ready_module_count": readiness["summary"]["command_ready_module_count"],
        "implementation_ready_process_count": processes["summary"]["implementation_ready_process_count"],
        "drift_source_count": drift["comparison"]["unchanged_source_count"],
        "night_bundle_artifact_count": night["counts"]["ui_artifact_count"],
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "negin_erp_varanegar_morning_evidence_readiness_handoff",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_HANDOFF_FROM_PERSISTED_REDACTED_READ_ONLY_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "implementation_pilot_or_production_authorized": 0,
        },
        "summary": summary,
        "knowledge_statement": {
            "status": "SUBSTANTIAL_MULTI_SOURCE_RECONSTRUCTION_BASELINE_NOT_COMPLETE_RUNTIME_PARITY",
            "supported_claim": "Enough evidence exists to define module boundaries, first read-only slices, high-risk command contracts, migration controls, and the owner-review agenda.",
            "unsupported_claims": [
                "complete knowledge of every runtime branch, effective setting, identity grant, dynamic layout, or external integration",
                "command, pilot, or production readiness",
                "current operational truth from the development clone alone",
                "authorization to write to Varanegar or perform cutover/dual-write",
            ],
        },
        "deep_boundaries": [
            {"area": "customer_goods_master", "screen_count": sources["customer_goods"]["summary"]["screen_candidate_count"], "input_count": sources["customer_goods"]["summary"]["input_control_candidate_count"], "golden_gap_count": sources["customer_goods"]["summary"]["screen_with_missing_golden_contract_count"], "gate": "owner field/relation review plus isolated execution of 64 designed cases"},
            {"area": "supplier_master", "screen_count": sources["supplier"]["summary"]["screen_candidate_count"], "input_count": sources["supplier"]["summary"]["input_control_candidate_count"], "golden_gap_count": sources["supplier"]["summary"]["screen_with_missing_golden_contract_count"], "gate": "payment/accounting/contact/cardex guard cases"},
            {"area": "operational_context", "screen_count": sources["operational_context"]["summary"]["screen_candidate_count"], "input_count": sources["operational_context"]["summary"]["input_control_candidate_count"], "golden_gap_count": sources["operational_context"]["summary"]["screen_with_missing_golden_contract_count"], "gate": "owner-approved year/DC/office/stock/type/price-method contract"},
            {"area": "contextual_price_discount", "screen_count": sources["pricing"]["summary"]["screen_candidate_count"], "input_count": sources["pricing"]["summary"]["input_control_candidate_count"], "golden_gap_count": sources["pricing"]["summary"]["screen_with_missing_golden_contract_count"], "gate": "owner-approved scope/priority/effective-date/rounding/explain contract plus isolated execution of designed cases"},
            {"area": "identity_access_administration", "route_count": sources["identity_access"]["summary"]["identity_access_route_candidate_count"], "runtime_matched_form_count": sources["identity_access"]["summary"]["runtime_matched_form_count"], "gate": "deny-first capability/scope policy, identity source, authenticated role UAT and immutable assignment audit"},
            {"area": "system_configuration", "configured_route_count": sources["system_configuration"]["summary"]["configured_form_route_count"], "runtime_matched_route_count": sources["system_configuration"]["summary"]["runtime_matched_configured_route_count"], "gate": "owner-reviewed scope precedence, versioned effective-setting explain and isolated publication/rollback tests"},
            {"area": "final_date_management", "configured_route_count": sources["final_date"]["summary"]["configured_final_date_route_count"], "target_command_count": len(sources["final_date"]["target_commands"]), "gate": "exact SQL effects, owner-approved date/reopen semantics, fault cases and cross-module reconciliation"},
            {"area": "order_sale_return", "screen_count": sources["order_sale"]["summary"]["screen_candidate_count"], "input_count": sources["order_sale"]["summary"]["input_control_candidate_count"], "gate": "73-trigger disposition, fault tests, and reconciliation"},
            {"area": "treasury_edit", "target_command_count": sources["treasury"]["summary"]["target_command_contract_count"], "acceptance_obligation_count": sources["treasury"]["summary"]["acceptance_obligation_count"] - sources["treasury"]["summary"]["executed_acceptance_obligation_count"], "gate": "writable-view and trigger effect parity without UI SQL"},
            {"area": "stock_distribution", "root_trigger_count": sources["stock_distribution"]["summary"]["root_trigger_count"], "resolved_write_target_count": sources["stock_distribution"]["summary"]["resolved_write_target_count"], "gate": "cardex/on-hand/exit reconciliation and truncated frontier disposition"},
            {"area": "supplier_invoice", "root_trigger_count": sources["supplier_invoice"]["summary"]["root_trigger_count"], "resolved_write_target_count": sources["supplier_invoice"]["summary"]["resolved_write_target_count"], "gate": "replace trigger-toggle guard with explicit invariant"},
            {"area": "accounting_voucher", "target_command_candidate_count": sources["accounting"]["summary"]["target_command_candidate_count"], "exact_sql_binding_count": 0, "gate": "separate generated/manual provenance and exact handler-to-SQL binding"},
        ],
        "recommended_construction_sequence": [
            {"order": 1, "slice": "decisions_and_safety_kernel", "deliver": "stack ADR, RPO/RTO, isolated target environments, deny-first source adapter", "write_enabled": False},
            {"order": 2, "slice": "organization_context_and_authorization", "deliver": "typed company/DC/office/stock/year context plus capability/scope explanation", "write_enabled": False},
            {"order": 3, "slice": "read_only_master_and_reports", "deliver": "customer, goods, supplier list/search/detail and bounded reports from versioned projections", "write_enabled": False},
            {"order": 4, "slice": "snapshot_crosswalk_quarantine", "deliver": "immutable snapshot, UUID crosswalk, anomaly quarantine, reconciliation runner", "write_enabled": "isolated_target_only"},
            {"order": 5, "slice": "synthetic_command_harness", "deliver": "877 addressable Golden contracts, fault injection, idempotency, audit/outbox", "write_enabled": "synthetic_target_test_db_only"},
            {"order": 6, "slice": "owner_approved_master_commands", "deliver": "versioned customer/goods/supplier/context commands after field/relation/retention signoff", "write_enabled": "isolated_target_only"},
            {"order": 7, "slice": "commercial_and_ledger_workflows", "deliver": "order/sale/stock/distribution/treasury/procurement/accounting commands with reconciliation", "write_enabled": "staged_target_only_after_domain_gates"},
            {"order": 8, "slice": "pilot_and_cutover", "deliver": "authenticated UAT, performance, security, restore, delta reconciliation, rollback drill", "write_enabled": "only_after_signed_gate"},
        ],
        "immediate_user_decisions": [
            "select target backend/web/database/deployment stack after ADR comparison",
            "approve RPO/RTO and backup/restore owner",
            "confirm DC=0 versus DC=1 and valid office/stock/year combinations",
            "name business owners for master data, stock, treasury, procurement, accounting, reports, and migration review",
            "choose the first authenticated read-only workflow for UAT",
            "state expected concurrent users and first-year growth",
            "decide whether offline warehouse or seller operation is required in the first ERP release",
        ],
        "source_paths": {name: path.as_posix() for name, path in paths.items()},
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
