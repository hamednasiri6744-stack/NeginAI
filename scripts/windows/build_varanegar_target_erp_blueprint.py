"""Build the evidence-backed, stack-neutral target ERP implementation blueprint."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


MODULES: tuple[dict[str, Any], ...] = (
    {"id": "platform", "owns": ["tenant", "command_idempotency", "audit_event", "outbox", "approval", "job"], "commands": ["approve", "reject", "retry_job"], "queries": ["audit_timeline", "command_result", "job_status"], "depends_on": [], "gate": "transaction/outbox/idempotency/failure-injection tests"},
    {"id": "organization_context", "owns": ["company", "fiscal_year", "dc", "sale_office", "stock_dc", "operation_date"], "commands": ["open_or_close_operation_context"], "queries": ["effective_context", "available_contexts"], "depends_on": ["platform"], "gate": "DC=0/1 and fiscal/operation-date semantics signed off"},
    {"id": "identity_authorization", "owns": ["principal", "role", "capability", "role_capability", "data_scope", "decision_trace"], "commands": ["assign_role", "grant_scope"], "queries": ["effective_permissions", "explain_decision"], "depends_on": ["platform", "organization_context"], "gate": "AccessNode and NGT namespaces crosswalked; deny-wins and scope tests"},
    {"id": "configuration", "owns": ["config_definition", "config_value", "config_version", "feature_entitlement", "resolution_trace"], "commands": ["publish_config_version"], "queries": ["effective_config", "config_history"], "depends_on": ["platform", "organization_context"], "gate": "General/Server/DC/Device/App precedence proven"},
    {"id": "master_data", "owns": ["unit", "document_type", "geography", "area", "route", "product", "brand", "package", "barcode", "party", "customer", "supplier", "personnel", "vehicle", "team"], "commands": ["curate_master", "merge_duplicate_candidate"], "queries": ["catalog_search", "party_search", "route_tree"], "depends_on": ["platform", "organization_context", "identity_authorization"], "gate": "repeatable import, PII policy, key/crosswalk/orphan parity"},
    {"id": "pricing_rules", "owns": ["price_list", "contract_price", "discount_rule", "prize_rule", "rule_version", "calculation_trace"], "commands": ["publish_rule_version", "quote_price"], "queries": ["explain_price", "active_rules"], "depends_on": ["master_data", "configuration"], "gate": "Golden parity for priority/order/rounding and safe rule DSL"},
    {"id": "sales", "owns": ["order", "order_line", "sale", "sale_line", "return", "return_line", "conversion_attempt", "sales_state_event"], "commands": ["create_order", "convert_order_to_sale", "cancel_sale", "create_return"], "queries": ["order_view", "sale_view", "return_view"], "depends_on": ["pricing_rules", "master_data", "organization_context", "identity_authorization"], "gate": "state/retry/split/conversion parity plus exact gross-discount-addition-net provenance and zero official return-net residual"},
    {"id": "inventory", "owns": ["stock_policy", "stock_event", "voucher", "voucher_line", "batch_allocation", "reservation", "open_sale_stock_obligation", "exit", "stock_projection"], "commands": ["reserve", "release_reservation", "post_voucher", "issue_exit", "reverse_exit"], "queries": ["stock_goods", "cardex", "stock_obligation_explain", "reservation_reasons", "exit_view"], "depends_on": ["master_data", "organization_context", "platform", "identity_authorization"], "gate": "ledger-minus-operational-obligation projection rebuild and zero unexplained residual"},
    {"id": "distribution", "owns": ["distribution", "distribution_path_code", "distribution_path_mode_decision", "distribution_sale_link", "distribution_state_event", "delivery_attempt", "delivery_evidence", "undelivered_reason", "exit_adjustment_workset"], "commands": ["create_distribution", "issue_exit", "send", "complete", "reverse_status", "remove_exit", "merge_exit"], "queries": ["distribution_work_queue", "distribution_detail", "delivery_timeline"], "depends_on": ["sales", "inventory", "master_data", "configuration", "platform", "identity_authorization"], "gate": "mode-aware integer path preservation, authoritative label crosswalk, allowed-edge contract, proof-of-delivery and 77 Golden command cases"},
    {"id": "receivables_treasury", "owns": ["receipt", "payment_instrument", "allocation", "open_invoice_projection", "received_cheque", "received_cheque_event", "returned_cheque_settlement"], "commands": ["record_receipt", "allocate_payment", "change_received_cheque_status", "undo_received_cheque_status", "settle_returned_cheque"], "queries": ["open_invoices", "received_cheque_work_queue", "received_cheque_timeline"], "depends_on": ["sales", "organization_context", "platform", "identity_authorization"], "gate": "allocation/open-invoice parity; approved history Pay authority; LegalType propagation; 49 cross-customer rows reviewed"},
    {"id": "procurement_payables", "owns": ["purchase_receipt", "supplier_invoice", "supplier_return", "pay", "pay_instrument", "payable_cheque", "payable_cheque_event", "supplier_balance_projection"], "commands": ["record_supplier_invoice", "record_supplier_return", "record_pay", "change_payable_cheque_status", "undo_payable_cheque_status"], "queries": ["supplier_cardex", "supplier_balance", "payable_cheque_work_queue"], "depends_on": ["inventory", "master_data", "platform", "identity_authorization"], "gate": "28-branch supplier cardex parity and 155 used book-item review"},
    {"id": "accounting", "owns": ["prevoucher", "external_voucher", "voucher", "journal_entry", "journal_line", "posting_event", "period_close"], "commands": ["stage_prevoucher", "post_voucher", "reverse_posting", "close_period"], "queries": ["journal", "posting_trace", "trial_balance"], "depends_on": ["organization_context", "platform", "identity_authorization"], "gate": "creator rule, double-entry, current pointer, closing and manual-voucher parity"},
    {"id": "reporting_documents", "owns": ["report_definition", "report_version", "projection_build", "output_job", "document_output_event"], "commands": ["request_export", "request_print", "mark_print_completed", "rebuild_projection"], "queries": ["dashboard", "cardex_reports", "report_job"], "depends_on": ["platform", "identity_authorization"], "gate": "read/preview/export/print permissions and print-completion idempotency"},
    {"id": "integration_migration", "owns": ["source_snapshot", "source_crosswalk", "migration_run", "quarantine_finding", "reconciliation_run", "source_contract_hash"], "commands": ["capture_snapshot", "import_slice", "reconcile", "resolve_quarantine"], "queries": ["migration_status", "reconciliation_dashboard", "drift_report"], "depends_on": ["platform"], "gate": "source remains read-only; repeatable import and explainable zero/accepted differences"},
)


PHASES: tuple[dict[str, Any], ...] = (
    {"id": "P0", "name": "foundation_and_observability", "modules": ["platform", "integration_migration", "organization_context", "identity_authorization", "configuration"], "deliverable": "separate target DB, migrations, audit/outbox/idempotency, read-only source snapshots and reconciliation shell", "estimate_weeks": [2, 3]},
    {"id": "P1", "name": "read_only_master_slice", "modules": ["master_data", "reporting_documents"], "deliverable": "authenticated scoped web review of organization/product/party/route with import parity", "estimate_weeks": [3, 5]},
    {"id": "P2", "name": "pricing_and_sales", "modules": ["pricing_rules", "sales", "accounting"], "deliverable": "rule trace, order/sale read models and synthetic command rehearsal", "estimate_weeks": [4, 6]},
    {"id": "P3", "name": "inventory_and_distribution", "modules": ["inventory", "distribution"], "deliverable": "rebuildable stock/cardex, exit and distribution state machine with failure-tested commands", "estimate_weeks": [6, 9]},
    {"id": "P4", "name": "treasury_returns", "modules": ["receivables_treasury", "sales"], "deliverable": "receipt/allocation/open invoice, sales return and received-cheque workflows", "estimate_weeks": [4, 6]},
    {"id": "P5", "name": "procurement_payables", "modules": ["procurement_payables", "accounting"], "deliverable": "supplier invoice/return/pay/payable-cheque and supplier-cardex parity", "estimate_weeks": [4, 6]},
    {"id": "P6", "name": "pilot_cutover", "modules": ["platform", "reporting_documents", "integration_migration"], "deliverable": "role UAT, performance/security/recovery, delta reconciliation, rollback drill and signed cutover", "estimate_weeks": [4, 6]},
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--forms", required=True, type=Path)
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--state-machines", required=True, type=Path)
    parser.add_argument("--side-effects", required=True, type=Path)
    parser.add_argument("--golden-cases", required=True, type=Path)
    parser.add_argument("--orchestrator-golden-cases", required=True, type=Path)
    parser.add_argument("--extension-golden-cases", required=True, type=Path)
    parser.add_argument("--report-golden-cases", required=True, type=Path)
    parser.add_argument("--master-golden-cases", required=True, type=Path)
    parser.add_argument("--foundation-golden-cases", required=True, type=Path)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--drift", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = _load(args.manifest)
    forms = _load(args.forms)
    authorization = _load(args.authorization)
    states = _load(args.state_machines)
    side_effects = _load(args.side_effects)
    golden = _load(args.golden_cases)
    orchestrator_golden = _load(args.orchestrator_golden_cases)
    extension_golden = _load(args.extension_golden_cases)
    report_golden = _load(args.report_golden_cases)
    master_golden = _load(args.master_golden_cases)
    foundation_golden = _load(args.foundation_golden_cases)
    reports = _load(args.reports)
    drift = _load(args.drift)
    if manifest["validation"] != "PASS" or manifest["domain_count"] != 18:
        raise ValueError("validated 18-domain manifest is required")

    command_envelope = {
        "required": ["command_id", "aggregate_id", "expected_version", "operational_date", "fiscal_year", "dc_ref", "actor_context"],
        "conditional": ["sale_office_ref", "stock_dc_ref", "reason", "approval_id", "evidence_refs"],
        "server_checks": ["authentication", "atomic capability", "data scope", "feature/config version", "operation date", "allowed transition", "domain validation", "idempotency"],
        "result": ["command_id", "aggregate_id", "new_version", "new_state", "audit_event_id", "reconciliation_status"],
    }
    artifact = {
        "artifact": "negin_personal_erp_evidence_backed_blueprint",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "safety": {
            "mode": "OFFLINE_TARGET_DESIGN_FROM_REDACTED_READ_ONLY_EVIDENCE",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_values_persisted": 0,
            "production_stack_or_cutover_authorized": 0,
        },
        "architecture_style": {
            "recommendation": "modular_monolith_first_with_explicit_bounded_contexts",
            "reason": "strong transactional workflows and a small initial team; preserve extraction boundaries so modules can split later",
            "stack_status": "not_selected_by_user",
            "data_policy": "separate target database; Varanegar remains read-only during reconstruction; no browser direct writes",
        },
        "evidence_snapshot": {
            "validated_domain_count": manifest["domain_count"],
            "validated_domain_artifact_bytes": manifest["bundle_totals"]["artifact_bytes"],
            "runtime_form_candidates": forms["summary"]["form_candidate_count"],
            "open_route_authorization_nodes": authorization["summary"]["authorization_node_count"],
            "state_machines": states["summary"]["machine_count"],
            "states": states["summary"]["state_count"],
            "command_traces": side_effects["summary"]["command_trace_count"],
            "mutating_commands_without_explicit_legacy_idempotency_token": side_effects["summary"]["mutation_command_without_explicit_idempotency_parameter_count"],
            "synthetic_golden_cases": golden["summary"]["case_count"] + orchestrator_golden["summary"]["case_count"] + extension_golden["summary"]["case_count"] + report_golden["summary"]["golden_case_count"] + master_golden["summary"]["case_count"] + foundation_golden["summary"]["case_count"],
            "active_route_golden_cases": golden["summary"]["case_count"],
            "high_impact_orchestrator_golden_cases": orchestrator_golden["summary"]["case_count"],
            "material_extension_golden_cases": extension_golden["summary"]["case_count"],
            "report_query_export_print_golden_cases": report_golden["summary"]["golden_case_count"],
            "customer_goods_master_data_golden_cases": master_golden["summary"]["case_count"],
            "supplier_context_pricing_golden_cases": foundation_golden["summary"]["case_count"],
            "report_output_surfaces": reports["summary"]["surface_count"],
            "runtime_baseline_sha256": drift["release_identity"]["overall_semantic_sha256"],
        },
        "module_count": len(MODULES),
        "modules": list(MODULES),
        "command_envelope": command_envelope,
        "query_contract": {
            "rules": ["authorization and data scope applied in the server query", "business/fiscal date explicit", "snapshot/projection version returned", "PII minimized and field-authorized", "drill-down reauthorizes target route"],
            "pagination": "stable cursor over deterministic business sort plus immutable tie-breaker",
            "cache": "cache keys include tenant/context/scope/config/projection version; financial or stock projections expose freshness",
        },
        "cross_module_rules": [
            "A module never writes another module's tables; use an internal command contract or event/outbox.",
            "Cross-module reporting reads versioned projections, not ad-hoc mutable joins exposed to clients.",
            "Money, quantity and dates use explicit domain value objects and source-compatible precision/calendar rules.",
            "State transitions append events and atomically advance expected-version pointers.",
            "Balances and on-hand quantities are rebuildable projections over authoritative ledgers.",
            "Configuration version and authorization decision trace are attached to material commands.",
            "Source identifiers live only in crosswalk/import metadata, not as target aggregate identity.",
        ],
        "phases": list(PHASES),
        "estimated_total_weeks": [21, 33],
        "first_usable_read_only_slice_weeks": [3, 5],
        "definition_of_done": [
            "schema migration and repeatable synthetic/source-snapshot import",
            "authorization plus data-scope denial tests",
            "happy, cancel/reverse, stale-version, retry and failure-injection Golden cases",
            "ledger/projection reconciliation with explained exceptions",
            "PII/secret/log review and immutable audit/outbox",
            "performance, backup/restore and rollback drill",
            "business-owner parity sign-off and authenticated real-device UAT",
        ],
        "not_yet_authorized_or_ready": [
            "writes to operational Varanegar",
            "production cutover or dual-write",
            "automatic repair of legacy anomalies",
            "final technology stack selection",
            "Command-ready or Pilot-ready classification for any domain",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"module_count": artifact["module_count"], "phase_count": len(PHASES), "evidence_snapshot": artifact["evidence_snapshot"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
