"""Build the target ERP source-snapshot, crosswalk, quarantine contract offline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


SLICE_ORDER: tuple[dict[str, Any], ...] = (
    {"order": 1, "slice": "organization_context", "source_domains": ["organization_and_fiscal_year"], "target_modules": ["organization_context"], "identity": "curated natural code plus immutable target UUID", "reconciliation": ["row_count", "active_by_context", "orphan_fk", "effective_date_coverage"]},
    {"order": 2, "slice": "reference_types", "source_domains": ["units_stock_and_document_types"], "target_modules": ["master_data", "organization_context"], "identity": "versioned explicit type crosswalk; never merge unrelated type namespaces", "reconciliation": ["row_count_by_namespace", "unknown_code", "unused_code_preserved"]},
    {"order": 3, "slice": "geography_routes", "source_domains": ["geography_and_routes"], "target_modules": ["master_data"], "identity": "separate legacy sale-path and NGT visit-path keys with quality status", "reconciliation": ["hierarchy_orphans", "customer_coverage", "legacy_ngt_crosswalk_quality"]},
    {"order": 4, "slice": "product_catalog", "source_domains": ["product_catalog"], "target_modules": ["master_data"], "identity": "target product UUID; barcode/package/brand links remain independently versioned", "reconciliation": ["product_count", "barcode_uniqueness", "package_unit_consistency", "brand_link_cardinality"]},
    {"order": 5, "slice": "parties", "source_domains": ["parties_customers_suppliers_personnel"], "target_modules": ["master_data"], "identity": "party UUID plus typed customer/supplier/personnel roles; duplicate candidates never auto-merge", "reconciliation": ["role_counts", "reference_orphans", "duplicate_candidates", "pii_policy"]},
    {"order": 6, "slice": "authorization_configuration", "source_domains": ["legacy_and_ngt_authorization", "configuration_and_rule_flags"], "target_modules": ["identity_authorization", "configuration"], "identity": "capability and config-definition UUIDs; Legacy AccessNode and NGT namespaces remain distinct", "reconciliation": ["deny_wins_cases", "scope_coverage", "resolution_precedence", "decision_trace"]},
    {"order": 7, "slice": "pricing_rules", "source_domains": ["pricing_discounts_prizes"], "target_modules": ["pricing_rules"], "identity": "immutable version UUID per published rule set", "reconciliation": ["active_rule_count", "priority_order", "rounding_golden_cases", "explain_trace"]},
    {"order": 8, "slice": "sales_returns", "source_domains": ["order_sale_lifecycle", "sales_returns_and_settlement"], "target_modules": ["sales"], "identity": "separate order/sale/return aggregates; source links are crosswalk metadata", "reconciliation": ["header_line_count", "quantity_amount_totals", "state_distribution", "conversion_links", "return_difference_quarantine"]},
    {"order": 9, "slice": "inventory_distribution", "source_domains": ["inventory_reservation_and_exit", "distribution_delivery"], "target_modules": ["inventory", "distribution"], "identity": "ledger-event and distribution UUID; current projection never becomes authoritative identity", "reconciliation": ["ledger_projection_balance", "voucher_line_totals", "reservation_reason", "exit_sale_links", "distribution_state_edges"]},
    {"order": 10, "slice": "receivables", "source_domains": ["collections_payments_open_invoices", "received_cheque_lifecycle"], "target_modules": ["receivables_treasury"], "identity": "receipt/instrument/allocation/cheque UUIDs with independent event histories", "reconciliation": ["allocation_conservation", "open_invoice_balance", "cheque_current_history", "returned_settlement_links"]},
    {"order": 11, "slice": "procurement_payables", "source_domains": ["supplier_purchase_and_payables", "supplier_disbursement_and_payable_cheques", "official_supplier_cardex_contract"], "target_modules": ["procurement_payables"], "identity": "supplier document/pay/instrument UUIDs; official cardex is a reconciliation contract", "reconciliation": ["document_line_totals", "supplier_balance_branches", "cheque_book_usage", "cardex_parity"]},
    {"order": 12, "slice": "accounting", "source_domains": ["general_ledger_staging_and_posting"], "target_modules": ["accounting"], "identity": "voucher UUID plus immutable journal entry/line IDs; preserve source-to-ledger provenance", "reconciliation": ["debit_credit_balance", "creator_rule", "prevoucher_current_pointer", "period_totals", "manual_external_provenance"]},
)


KNOWN_QUARANTINE_BASELINE = (
    {"code": "RETSALE_GROSS_NET_ADJUSTMENT_NOT_AN_ERROR", "observed_count": 696, "disposition": "preserve gross, discount/addition components and official net; never quarantine solely for gross-versus-net difference"},
    {"code": "STOCK_CARDEX_ONLY_GAP_EXPLAINED_BY_OPEN_SALE_OBLIGATION", "observed_count": 1594, "disposition": "accepted_source_semantics; preserve the official cardex-minus-operational-obligation formula; unexplained residual is zero on the clone"},
    {"code": "RECEIVED_CHEQUE_MASTER_PAY_PROJECTION_GAP_NOT_AN_ERROR", "observed_count": 8, "disposition": "accepted source semantics; all eight resolve to approved current-history PayId2; never synthesize or quarantine from TblCheque.PayId alone"},
    {"code": "RECEIVED_CHEQUE_LEGAL_TYPE_UNSPECIFIED", "observed_count": 35, "disposition": "preserve UNKNOWN_SOURCE and Personnel separately; never impute legal route 1 or 2 without authoritative provenance"},
    {"code": "RETURNED_CHEQUE_CROSS_CUSTOMER_ALLOCATION_NOT_AN_ERROR", "observed_count": 49, "disposition": "accepted source semantics; preserve distinct cheque-owner, allocation-customer and invoice-customer roles plus linked accounting provenance; quarantine only missing/inconsistent allocation or over-settlement"},
    {"code": "PAYABLE_SOURCE_USED_UNLINKED_LEAF", "observed_count": 155, "disposition": "accepted source state with UNKNOWN_SOURCE provenance; preserve used-unlinked, require owner review before reuse, and never synthesize a cheque or clear IsUsed automatically"},
    {"code": "VOUCHER_CURRENT_POINTER_HISTORY_FORK", "observed_count": 1094, "disposition": "blocking accounting reconciliation; preserve current pointer projection and every detached trailing event with UNKNOWN_OUTCOME; never replace pointer with MAX or discard history automatically"},
    {"code": "VOUCHER_DRAFT_EMPTY_NUMBERED_SHELL", "observed_count": 1, "disposition": "preserve as non-posted draft with UNKNOWN_SOURCE and source-number provenance; never synthesize lines, post it or silently reuse its source number"},
    {"code": "NGT_MOBILE_RETURN_PENDING_OR_UNATTEMPTED", "observed_count": 1, "disposition": "preserve as non-official mobile integration state; do not infer rejection or create RetOrder/RetSale without an authoritative result"},
    {"code": "NGT_MOBILE_RETURN_HISTORICAL_RESULT_CURRENT_TARGET_MISSING", "observed_count": 1, "disposition": "blocking integration reconciliation; preserve exact TourHistory and copied BackOffice crosswalk provenance; never recreate the missing target automatically"},
    {"code": "SUPPLIER_RECEIPT_PER_INVOICE_ONLY_GROUP_NOT_AN_ERROR", "observed_count": 5, "disposition": "accepted N:M relation semantics; all five reconcile inside the connected invoice-receipt component; never synthesize financial lines or delete receipt goods from per-invoice comparison alone"},
    {"code": "SUPPLIER_RETURN_OPTIONAL_SOURCE_ITEM_ABSENT_NOT_AN_INVENTORY_ERROR", "observed_count": 7, "disposition": "accepted inventory-voucher authority: all seven exactly match their linked type-55 exit; preserve nonzero source price/amount provenance, keep the optional invoice-item absence explicit, and never auto-reassign to a prior invoice or reprice"},
    {"code": "SUPPLIER_RETURN_STALE_EXPLICIT_TOLL_REF_RESOLVED_BY_HEADER_TOLL_CODE", "observed_count": 20, "disposition": "preserve the stale explicit ref as provenance and resolve the effective toll through the deployed same-header TollRef compatibility rule; all twenty are uniquely recoverable and visible, but any missing or ambiguous code match must quarantine"},
    {"code": "DISTRIBUTION_MANUAL_PATH_CODE_WITHOUT_LABEL_MASTER", "observed_count": 26086, "disposition": "accepted source semantics; preserve the exact mode-dependent integer code and provenance; add labels only through an authoritative crosswalk"},
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--state-machines", required=True, type=Path)
    parser.add_argument("--golden-cases", required=True, type=Path)
    parser.add_argument("--orchestrator-golden-cases", required=True, type=Path)
    parser.add_argument("--extension-golden-cases", required=True, type=Path)
    parser.add_argument("--report-golden-cases", required=True, type=Path)
    parser.add_argument("--master-golden-cases", required=True, type=Path)
    parser.add_argument("--foundation-golden-cases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = _load(args.manifest)
    blueprint = _load(args.blueprint)
    states = _load(args.state_machines)
    golden = _load(args.golden_cases)
    orchestrator_golden = _load(args.orchestrator_golden_cases)
    extension_golden = _load(args.extension_golden_cases)
    report_golden = _load(args.report_golden_cases)
    master_golden = _load(args.master_golden_cases)
    foundation_golden = _load(args.foundation_golden_cases)
    if manifest.get("validation") != "PASS" or manifest.get("domain_count") != 18:
        raise ValueError("validated 18-domain manifest is required")
    source_slugs = {row["slug"] for row in manifest["domains"]}
    required_slugs = {slug for item in SLICE_ORDER for slug in item["source_domains"]}
    missing = sorted(required_slugs - source_slugs)
    if missing:
        raise ValueError(f"migration slices reference missing domains: {missing}")

    artifact = {
        "artifact": "negin_erp_varanegar_migration_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "safety": {
            "mode": "OFFLINE_TARGET_CONTRACT_FROM_AGGREGATE_READ_ONLY_EVIDENCE",
            "database_connections": 0,
            "source_snapshots_captured": 0,
            "source_or_target_rows_read_or_changed": 0,
            "legacy_repairs_executed": 0,
            "cutover_or_dual_write_authorized": 0,
        },
        "evidence": {
            "validated_domain_count": manifest["domain_count"],
            "target_module_count": blueprint["module_count"],
            "state_machine_count": states["summary"]["machine_count"],
            "golden_case_count": golden["summary"]["case_count"] + orchestrator_golden["summary"]["case_count"] + extension_golden["summary"]["case_count"] + report_golden["summary"]["golden_case_count"] + master_golden["summary"]["case_count"] + foundation_golden["summary"]["case_count"],
            "active_route_golden_case_count": golden["summary"]["case_count"],
            "high_impact_orchestrator_golden_case_count": orchestrator_golden["summary"]["case_count"],
            "material_extension_golden_case_count": extension_golden["summary"]["case_count"],
            "report_query_export_print_golden_case_count": report_golden["summary"]["golden_case_count"],
            "customer_goods_master_data_golden_case_count": master_golden["summary"]["case_count"],
            "supplier_context_pricing_golden_case_count": foundation_golden["summary"]["case_count"],
        },
        "source_snapshot_contract": {
            "immutability": "append_only_capture; never update a completed source snapshot",
            "required_metadata": [
                "capture_id", "source_system", "source_database_fingerprint",
                "source_contract_semantic_sha256", "query_or_extractor_sha256",
                "capture_started_at", "capture_completed_at", "business_cutoff",
                "consistency_boundary", "table_or_projection", "row_count",
                "ordered_key_range", "aggregate_checksum", "pii_classification",
            ],
            "consistency": "record isolation/snapshot boundary and source clock; reject mixed-boundary ledger slices",
            "incremental_rule": "watermark plus immutable tie-breaker; late-arriving rows are a new delta capture",
            "privacy": "raw restricted PII remains encrypted in access-controlled staging; manifests persist only aggregates and hashes",
        },
        "crosswalk_contract": {
            "key": ["source_system", "source_database_fingerprint", "entity_type", "source_key"],
            "required_fields": ["target_id", "mapping_status", "quality_code", "valid_from", "valid_to", "evidence_ref", "reviewed_by", "mapping_version"],
            "mapping_statuses": ["exact", "derived", "ambiguous", "quarantined", "retired"],
            "rules": [
                "target_id is an immutable target UUID and never reuses the source integer identity",
                "one source key has at most one active exact target mapping per mapping version",
                "many-to-one merges require an approved duplicate-resolution record",
                "ambiguous or quarantined mappings cannot enable target mutation commands",
                "rekeying creates a new version and preserves prior provenance",
            ],
        },
        "quarantine_contract": {
            "required_fields": ["finding_id", "capture_id", "slice", "entity_type", "source_key_hash", "reason_code", "severity", "evidence_ref", "status", "resolution", "approved_by", "resolved_at"],
            "statuses": ["open", "accepted_source_truth", "mapped", "excluded", "corrected_in_target_fixture", "blocked"],
            "rules": [
                "never persist raw cheque, contact, address or amount details in aggregate evidence artifacts",
                "never change Varanegar to resolve a migration finding",
                "automatic exclusion is forbidden for ledger, stock, payment, cheque and journal entities",
                "resolution is append-only and approval/audit linked",
            ],
            "known_aggregate_baseline": list(KNOWN_QUARANTINE_BASELINE),
        },
        "import_run_contract": {
            "states": ["planned", "snapshot_validated", "staged", "validated", "committed", "reconciled", "accepted", "rolled_back", "failed"],
            "atomic_unit": "one ordered migration slice and mapping version in an isolated target import transaction/job",
            "idempotency_key": ["capture_id", "slice", "mapping_version", "importer_version"],
            "resume_rule": "resume only from a durable completed slice checkpoint; partial writes are rolled back or fully compensated",
            "prohibitions": ["direct browser import", "source write-back", "production dual-write", "silent anomaly repair"],
        },
        "slice_count": len(SLICE_ORDER),
        "ordered_slices": list(SLICE_ORDER),
        "reconciliation_contract": {
            "levels": [
                "L0_file_and_schema_hash", "L1_row_and_key_counts",
                "L2_reference_and_state_distribution", "L3_quantity_and_amount_totals",
                "L4_ledger_projection_and_double_entry", "L5_business_golden_cases",
            ],
            "difference_classes": ["zero", "known_accepted", "mapped", "quarantined", "blocking_unknown"],
            "acceptance_rule": "no blocking_unknown; every non-zero difference has evidence, owner, reason and approval",
            "rerun_rule": "same capture/mapping/importer produces identical target hashes and reconciliation result",
        },
        "slice_definition_of_ready": [
            "source contract and semantic hash frozen",
            "target schema migration reviewed",
            "key and crosswalk policy approved",
            "PII classification and access policy applied",
            "synthetic fixtures include ambiguous, orphan, duplicate and retry cases",
            "expected aggregate reconciliation thresholds approved",
            "rollback and rerun demonstrated in isolated target test DB",
        ],
        "pilot_gate": [
            "all prerequisite slices accepted",
            "zero blocking_unknown reconciliation differences",
            "authorization denial and scope tests pass",
            "ledger/projection rebuild and recovery drill pass",
            "authenticated role-based UAT signed",
            "source remains read-only and rollback window is documented",
        ],
        "not_executed_or_authorized": [
            "a source snapshot containing business rows",
            "target schema creation or import",
            "legacy data repair",
            "dual-write, pilot or production cutover",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"slice_count": artifact["slice_count"], "known_quarantine_class_count": len(KNOWN_QUARANTINE_BASELINE), "evidence": artifact["evidence"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
