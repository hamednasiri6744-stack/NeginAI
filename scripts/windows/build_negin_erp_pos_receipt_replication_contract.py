"""Build a target batch/state/reconciliation contract for POS receipt ingestion."""

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
    parser.add_argument("--sql-semantics", required=True, type=Path)
    parser.add_argument("--target-contracts", required=True, type=Path)
    parser.add_argument("--golden-cases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    sql = _load(args.sql_semantics)
    target = _load(args.target_contracts)
    golden = _load(args.golden_cases)
    errors: list[str] = []
    for name, payload in (("SQL semantics", sql), ("target contracts", target), ("Golden cases", golden)):
        if payload.get("validation") != "PASS":
            errors.append(f"source is not PASS: {name}")

    legacy = next((row for row in sql["modules"] if row["object"] == "dbo.usp_ReplicateSalesReceipt"), None)
    command = next((row for row in target["commands"] if row["command"] == "pos.replicate_session_sales_receipts"), None)
    cases = [row for row in golden["cases"] if row["surface"] == "pos.replicate_session_sales_receipts"]
    if legacy is None:
        errors.append("legacy replication semantic footprint missing")
    if command is None:
        errors.append("target receipt replication command missing")
    if len(cases) != 20:
        errors.append(f"expected 20 receipt replication Golden cases, got {len(cases)}")

    batch_states = (
        {"state": "RECEIVED", "terminal": False, "meaning": "target-local immutable batch envelope and source watermark accepted"},
        {"state": "VALIDATING", "terminal": False, "meaning": "scope, identity, duplicate and structural validation in progress"},
        {"state": "READY_TO_APPLY", "terminal": False, "meaning": "every eligible receipt has a deterministic apply plan"},
        {"state": "APPLYING", "terminal": False, "meaning": "per-receipt commands execute with durable receipts/outbox"},
        {"state": "RECONCILING", "terminal": False, "meaning": "counts, amounts, crosswalks and ledger/projection effects are compared"},
        {"state": "ACCEPTED", "terminal": True, "meaning": "all eligible receipts reconcile and target-local acknowledgement is durable"},
        {"state": "PARTIALLY_QUARANTINED", "terminal": True, "meaning": "accepted items reconcile and rejected items have owner/reason/evidence"},
        {"state": "BLOCKING_UNKNOWN", "terminal": True, "meaning": "outcome cannot be proven; no acceptance or source write-back is allowed"},
        {"state": "REJECTED", "terminal": True, "meaning": "batch failed before any accepted receipt effect"},
    )
    transitions = (
        ("RECEIVED", "VALIDATING", "begin_validation"),
        ("VALIDATING", "READY_TO_APPLY", "all_eligible_items_planned"),
        ("VALIDATING", "REJECTED", "batch_envelope_or_scope_invalid"),
        ("READY_TO_APPLY", "APPLYING", "begin_apply"),
        ("APPLYING", "RECONCILING", "all_item_attempts_terminal_or_recoverable"),
        ("APPLYING", "BLOCKING_UNKNOWN", "commit_or_response_outcome_unknown"),
        ("RECONCILING", "ACCEPTED", "zero_difference_and_zero_quarantine"),
        ("RECONCILING", "PARTIALLY_QUARANTINED", "accepted_items_reconcile_and_all_other_items_quarantined"),
        ("RECONCILING", "BLOCKING_UNKNOWN", "unexplained_difference"),
        ("BLOCKING_UNKNOWN", "RECONCILING", "operator_supplies_fresh_read_only_evidence_and_retries_reconciliation"),
    )
    item_states = (
        "STAGED",
        "VALIDATED",
        "DUPLICATE_ALREADY_APPLIED",
        "APPLYING",
        "APPLIED",
        "RECONCILED",
        "QUARANTINED",
        "UNKNOWN",
    )
    target_effects = (
        {"effect": "sales_order_or_sale", "legacy_hints": ["POrder", "POrderXBO", "tblsalehdr", "tblSaleItm"], "target_owner": "sales", "rule": "one immutable source receipt crosswalk to the created order/sale version"},
        {"effect": "sales_return", "legacy_hints": ["PRetSaleXBO", "tblRetSaleHdr", "tblRetSaleItm"], "target_owner": "sales", "rule": "return provenance and remaining quantities reconcile before acceptance"},
        {"effect": "payment_and_allocation", "legacy_hints": ["Acc.tblPayments", "tblPayWithPaymentRelation", "PPayment"], "target_owner": "receivables_treasury", "rule": "payment instrument and allocation ledger are authoritative; no inferred reassignment"},
        {"effect": "inventory_voucher", "legacy_hints": ["inv.tblVocherHdr", "usp_DBApi_CreateInvVocher"], "target_owner": "inventory", "rule": "stock ledger append and projection version are linked to receipt provenance"},
        {"effect": "credit", "legacy_hints": ["PCredit"], "target_owner": "receivables_treasury", "rule": "credit consume/reversal is versioned and idempotent"},
        {"effect": "session_projection", "legacy_hints": ["PSession", "BaseChargeDevice"], "target_owner": "receivables_treasury", "rule": "session status is a rebuildable projection and cannot acknowledge unreconciled items"},
    )
    reconciliation = (
        {"check": "receipt_count", "grain": "batch and receipt_type", "blocking": True},
        {"check": "gross_discount_net_amount_by_currency", "grain": "batch, currency and receipt_type", "blocking": True},
        {"check": "source_target_crosswalk_uniqueness", "grain": "source_system, session_id, receipt_id, source_version", "blocking": True},
        {"check": "created_sale_return_payment_voucher_counts", "grain": "batch and target effect", "blocking": True},
        {"check": "payment_allocation_and_credit_balance", "grain": "receipt and customer/party", "blocking": True},
        {"check": "inventory_ledger_projection", "grain": "receipt, stock, goods, batch and health", "blocking": True},
        {"check": "duplicate_effect_count", "grain": "source identity and target aggregate", "blocking": True},
        {"check": "outbox_inbox_delivery", "grain": "command_id and consumer", "blocking": True},
        {"check": "quarantine_completeness", "grain": "every non-accepted receipt", "blocking": True},
    )
    artifact = {
        "artifact": "negin_erp_pos_receipt_replication_batch_state_and_reconciliation_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_TARGET_DESIGN_FROM_REDACTED_STATIC_AND_CLONE_METADATA_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "operational_varanegar_acknowledgements_or_writes": 0,
            "pilot_cutover_or_dual_write_authorized": 0,
        },
        "evidence": {
            "legacy_object": None if legacy is None else legacy["object"],
            "legacy_dependency_count": 0 if legacy is None else legacy["dependency_count"],
            "legacy_lexical_operation_count": 0 if legacy is None else legacy["lexical_operation_count"],
            "legacy_resolved_mutation_targets": [] if legacy is None else legacy["resolved_mutation_targets"],
            "legacy_explicit_transaction": False if legacy is None else legacy["has_explicit_transaction_envelope"],
            "legacy_explicit_error_handler": False if legacy is None else legacy["has_explicit_error_handler"],
            "target_command": None if command is None else command["command"],
            "target_golden_case_count": len(cases),
        },
        "command_envelope": {
            "required": ["command_id", "correlation_id", "source_system", "source_session_id", "source_watermark", "source_contract_hash", "actor_context", "organization_context", "operational_date"],
            "per_receipt_identity": ["source_receipt_id", "source_receipt_version", "receipt_type", "payload_hash"],
            "idempotency_key": ["source_system", "source_session_id", "source_receipt_id", "source_receipt_version"],
            "payload_mismatch_rule": "same idempotency key with a different payload_hash is rejected and audited",
        },
        "batch_states": list(batch_states),
        "allowed_transitions": [
            {"from": source, "to": target_state, "event": event}
            for source, target_state, event in transitions
        ],
        "item_states": list(item_states),
        "target_effect_boundaries": list(target_effects),
        "execution_contract": [
            "ingest creates target-local immutable staging; it never writes acknowledgement or status to Varanegar",
            "each receipt is an independently idempotent application command with a durable result receipt",
            "one local aggregate transaction includes event/current pointer/outbox; cross-module effects use idempotent inbox consumers",
            "a batch can be accepted only after every eligible item is reconciled and every other item is explicitly quarantined",
            "unknown commit outcome stays BLOCKING_UNKNOWN until fresh read-only evidence proves convergence",
            "operator retry resumes from durable item receipts and never replays already-applied effects",
        ],
        "reconciliation_checks": list(reconciliation),
        "quarantine_contract": {
            "required": ["case_id", "batch_id", "source_receipt_identity", "failure_stage", "reason_code", "evidence_refs", "owner_role", "status", "created_at"],
            "statuses": ["OPEN", "EXPLAINED", "RETRYABLE", "REJECTED", "RESOLVED"],
            "auto_accept_or_auto_fix_allowed": False,
        },
        "acceptance_gate": [
            "all 20 synthetic command cases are executable in the isolated target harness",
            "fault injection at batch, receipt, crosswalk and outbox stages produces one result or explicit quarantine",
            "parallel duplicate delivery creates no duplicate order, return, payment, voucher, credit or session effect",
            "all nine reconciliation checks have zero unexplained blocking difference",
            "role/scope UAT, performance budget, restore drill and business-owner expected values are approved",
        ],
        "readiness": "TARGET_DESIGN_ONLY_NOT_IMPLEMENTED_NOT_UAT_NOT_PILOT_NOT_PRODUCTION_READY",
        "validation_errors": errors,
        "limits": [
            "The legacy footprint is static clone evidence and does not prove every runtime branch or operational freshness.",
            "Resolved mutation targets omit masked dynamic literals, nested trigger effects and unresolved aliases.",
            "Target states and boundaries are design controls that still require owner-approved field/value semantics and executable tests.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({
        "validation": artifact["validation"],
        "batch_state_count": len(batch_states),
        "transition_count": len(transitions),
        "item_state_count": len(item_states),
        "effect_boundary_count": len(target_effects),
        "reconciliation_check_count": len(reconciliation),
        "golden_case_count": len(cases),
        "validation_error_count": len(errors),
    }, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
