"""Build target command contracts for four high-impact Varanegar orchestrators."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


COMMANDS: tuple[dict[str, Any], ...] = (
    {
        "command": "order.save",
        "source_form": "VN.SDS.Sales.UI.Order.FormOrderDataEntry",
        "evidence": [
            ["VN.SDS.Sales.Business.Order.OrderHandler", "SaveCommandCustom"],
            ["VN.SDS.Sales.Business.Order.OrderHandler", "AfterSaveOrder"],
            ["VN.SDS.Sales.Business.Order.OrderValidator", "OrderValidation"],
            ["VN.SDS.Sales.Business.Order.OrderValidator", "DuplicateOrderItems"],
        ],
        "target_owner": "sales",
        "depends_on": ["organization_context", "identity_authorization", "master_data", "pricing_rules", "inventory", "platform"],
        "invariants": ["operation context open", "customer/dealer/goods active and scoped", "order number unique", "item/detail quantities agree", "credit/min-max/stock/batch/rule checks pass", "order version advances once"],
        "failure_injection_after": ["number reservation", "header stage", "item stage", "batch stage", "pricing/EVC calculation", "outbox append"],
        "reconciliation": ["header_line_totals", "item_detail_quantities", "pricing_trace", "batch_links", "audit_outbox"],
    },
    {
        "command": "order.cancel",
        "source_form": "VN.SDS.Sales.UI.Order.FormOrderDataEntry",
        "evidence": [
            ["VN.SDS.Sales.Business.Order.OrderHandler", "CancelOrder"],
            ["VN.SDS.Sales.Business.Order.OrderValidator", "BeCanceled"],
            ["VN.SDS.Sales.Business.Order.OrderHandler", "CheckConcurrencyStatusWithSelect"],
        ],
        "target_owner": "sales",
        "depends_on": ["inventory", "pricing_rules", "platform", "identity_authorization"],
        "invariants": ["expected version matches", "downstream conversion/status permits cancel", "cancel event and current pointer agree", "dependent reservations/rule artifacts are reconciled"],
        "failure_injection_after": ["cancel event append", "dependent release request", "current pointer advance", "outbox append"],
        "reconciliation": ["order_state_history", "conversion_links", "reservation_reasons", "pricing_or_evc_links"],
    },
    {
        "command": "order.convert_to_sale",
        "source_form": "VN.SDS.Sales.UI.Order.FormOrderDataEntry",
        "evidence": [
            ["VN.SDS.Sales.Business.Order.OrderHandler", "CreateSaleByOrder"],
            ["VN.SDS.Sales.Business.Order.OrderHandler", "CreateSaleItemDetailBySale"],
            ["VN.SDS.Sales.Business.Order.OrderHandler", "OrderToSaleValidation"],
        ],
        "target_owner": "sales",
        "depends_on": ["pricing_rules", "inventory", "accounting", "platform"],
        "invariants": ["one successful conversion result per command_id", "source order and target sale provenance immutable", "line/detail quantities and calculated amounts agree", "retry returns the original sale identity"],
        "failure_injection_after": ["sale identity allocation", "sale header stage", "sale item stage", "detail stage", "order conversion pointer", "outbox append"],
        "reconciliation": ["order_sale_crosswalk", "header_line_totals", "price_discount_prize_trace", "conversion_attempt_status"],
    },
    {
        "command": "sales_return.save",
        "source_form": "VN.SDS.Sales.UI.RetSale.FormRetSaleDataEntry",
        "evidence": [
            ["VN.SDS.Sales.Business.RetSale.RetSaleHandler", "SaveCommand"],
            ["VN.SDS.Sales.Business.RetSale.RetSaleHandler", "AfterSaveRetSale"],
            ["VN.SDS.Sales.Business.RetSale.RetSaleValidator", "RetSaleValidation"],
            ["VN.SDS.Sales.Business.RetSale.RetSaleHandler", "CreateRetSaleEVCs"],
        ],
        "target_owner": "sales",
        "depends_on": ["pricing_rules", "inventory", "distribution", "receivables_treasury", "platform"],
        "invariants": ["source sale is returnable", "remaining return quantity is not exceeded", "return cause/health/batch/date valid", "item and detail quantities agree", "settlement/discount/EVC effects reconcile"],
        "failure_injection_after": ["return header stage", "item stage", "detail/batch stage", "discount/EVC calculation", "settlement request", "outbox append"],
        "reconciliation": ["sale_return_crosswalk", "remaining_quantities", "return_difference_quarantine", "pricing_evc_trace", "settlement_links"],
    },
    {
        "command": "sales_return.cancel_and_generate_voucher",
        "source_form": "VN.SDS.Sales.UI.RetSale.FormRetSaleDataEntry",
        "evidence": [
            ["VN.SDS.Sales.Business.RetSale.RetSaleHandler", "CancelRetSaleAndGenerateCancelRetSaleVocher"],
            ["VN.SDS.Sales.Business.RetSale.RetSaleHandler", "GenerateRetSaleVocher"],
            ["VN.SDS.Sales.Business.RetSale.RetSaleValidator", "EbtalValidation"],
        ],
        "target_owner": "sales",
        "depends_on": ["inventory", "accounting", "receivables_treasury", "platform"],
        "invariants": ["cancel transition allowed", "one compensating voucher request per return version", "return/voucher provenance bidirectional", "financial and stock projections reconcile"],
        "failure_injection_after": ["cancel event", "voucher request", "settlement compensation request", "current pointer advance", "outbox append"],
        "reconciliation": ["return_state_history", "voucher_provenance", "stock_projection", "customer_balance_projection"],
    },
    {
        "command": "supplier_invoice.save",
        "source_form": "VN.SDS.Stock.UI.SupInvoice.FormSupInvoiceDataEntry",
        "evidence": [
            ["VN.SDS.Stock.Business.SupInvoice.SupInvoiceHdrHandler", "CheckSupInvoice"],
            ["VN.SDS.Stock.Business.SupInvoice.SupInvoiceHdrHandler", "IsSupInvoiceNoDuplicate"],
            ["VN.SDS.Stock.Business.SupInvoice.SupInvoiceHdrValidator", "SupInvInvoiceItemsValidation"],
            ["VN.SDS.Stock.Business.SupInvoice.SupInvoiceHdrValidator", "UnitQtyRemainingValidation"],
        ],
        "target_owner": "procurement_payables",
        "depends_on": ["master_data", "inventory", "organization_context", "platform"],
        "invariants": ["supplier/goods relation valid", "invoice number unique in approved scope", "quantity/price/percent/toll constraints pass", "ICA/voucher relation provenance retained", "supplier balance projection reconciles"],
        "failure_injection_after": ["number reservation", "header stage", "item stage", "toll stage", "inventory-document link", "outbox append"],
        "reconciliation": ["header_line_toll_totals", "supplier_goods_links", "ica_voucher_relations", "supplier_balance_projection"],
    },
    {
        "command": "supplier_return.save",
        "source_form": "VN.SDS.Stock.UI.RetSupInvoice.FormRetSupInvoiceDataEntry",
        "evidence": [
            ["VN.SDS.Stock.Business.RetSupInvoice.RetSupInvoiceHdrHandler", "CheckRetSupInvoice"],
            ["VN.SDS.Stock.Business.RetSupInvoice.RetSupInvoiceHdrHandler", "IsRetInvoiceNoDuplicate"],
            ["VN.SDS.Stock.Business.RetSupInvoice.RetSupInvoiceHdrValidator", "InvVocherRefValidation"],
            ["VN.SDS.Stock.Business.RetSupInvoice.RetSupInvoiceHdrValidator", "SupInvoiceRefValidation"],
        ],
        "target_owner": "procurement_payables",
        "depends_on": ["inventory", "master_data", "platform"],
        "invariants": ["source supplier invoice and inventory voucher valid", "return number unique", "remaining quantity not exceeded", "price/prize/percent constraints pass", "supplier and stock projections reconcile"],
        "failure_injection_after": ["return header stage", "item stage", "toll stage", "inventory compensation request", "outbox append"],
        "reconciliation": ["supplier_invoice_return_links", "remaining_quantities", "inventory_voucher_links", "supplier_cardex"],
    },
    {
        "command": "stock_voucher.save",
        "source_form": "VN.SDS.Stock.UI.Vocher.FormVocherDataEntry",
        "evidence": [
            ["VN.SDS.Stock.Business.Vocher.VocherHdrHandler", "BeforeSave"],
            ["VN.SDS.Stock.Business.Vocher.VocherHdrHandler", "CheckOnHandQty"],
            ["VN.SDS.Stock.Business.Vocher.VocherHdrValidator", "ValidationInVocherItem"],
        ],
        "target_owner": "inventory",
        "depends_on": ["master_data", "organization_context", "platform"],
        "invariants": ["voucher type/context/date valid", "goods/stock/health/batch valid", "header/item/detail quantities agree", "negative/on-hand policy enforced", "ledger event append is idempotent"],
        "failure_injection_after": ["voucher identity allocation", "header stage", "item stage", "batch/detail stage", "ledger event append", "projection/outbox stage"],
        "reconciliation": ["header_item_detail_totals", "ledger_event_count", "stock_projection_rebuild", "batch_provenance"],
    },
    {
        "command": "stock_voucher.confirm_or_unconfirm",
        "source_form": "VN.SDS.Stock.UI.Vocher.FormVocherDataEntry",
        "evidence": [
            ["VN.SDS.Stock.Business.Vocher.VocherHdrHandler", "UpdateVocherConfirmUnonfirm"],
            ["VN.SDS.Stock.Business.Vocher.VocherHdrHandler", "ConfirmValidation"],
            ["VN.SDS.Stock.Business.Vocher.VocherHdrHandler", "CheckCardexQty"],
        ],
        "target_owner": "inventory",
        "depends_on": ["accounting", "organization_context", "platform", "identity_authorization"],
        "invariants": ["expected voucher version/state matches", "operation/close date permits transition", "cardex quantity validation passes", "confirmation event and projection version advance once"],
        "failure_injection_after": ["transition validation", "state event append", "ledger projection request", "accounting request", "outbox append"],
        "reconciliation": ["voucher_state_history", "cardex_projection", "posting_provenance", "confirmation_audit"],
    },
    {
        "command": "stock_voucher.generate_return",
        "source_form": "VN.SDS.Stock.UI.Vocher.FormVocherDataEntry",
        "evidence": [
            ["VN.SDS.Stock.Business.Vocher.VocherHdrHandler", "GenerateRetVocher"],
            ["VN.SDS.Stock.Business.Vocher.VocherHdrHandler", "ValidRetVocher"],
            ["VN.SDS.Stock.Business.Vocher.VocherHdrHandler", "MergeValidation"],
        ],
        "target_owner": "inventory",
        "depends_on": ["platform", "identity_authorization"],
        "invariants": ["source voucher returnable", "one return voucher per command/source version", "source/return provenance immutable", "net ledger and projection reconcile"],
        "failure_injection_after": ["return identity allocation", "return header stage", "return lines stage", "source link stage", "ledger/outbox append"],
        "reconciliation": ["source_return_crosswalk", "net_quantities", "ledger_projection", "audit_outbox"],
    },
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--call-graph", required=True, type=Path)
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--migration-contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    graph = _load(args.call_graph)
    data_entry = _load(args.data_entry_il)
    migration = _load(args.migration_contract)
    methods_by_type = {
        row["type"]: {method["method"] for method in raw["methods"]}
        for layer in ("business", "data_access")
        for assembly in graph["raw_il"][layer]
        for raw in assembly["target_types"]
        for row in [{"type": raw["type"]}]
    }
    # The comprehension above intentionally indexes only parsed Business/DataAccess
    # types. UI evidence is checked separately through the selected form set.
    selected_forms = {row["type"] for row in graph["selected_forms"]}
    evidence_errors = []
    for contract in COMMANDS:
        if contract["source_form"] not in selected_forms:
            evidence_errors.append(f"source form not selected: {contract['source_form']}")
        for type_name, method in contract["evidence"]:
            if method not in methods_by_type.get(type_name, set()):
                evidence_errors.append(f"missing method evidence: {type_name}.{method}")

    artifact = {
        "artifact": "varanegar_high_impact_orchestrator_target_command_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not evidence_errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_TARGET_COMMAND_DESIGN_FROM_REDACTED_IL_AND_AGGREGATE_EVIDENCE",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_values_persisted": 0,
            "production_write_or_cutover_authorized": 0,
        },
        "evidence": {
            "selected_high_impact_form_count": graph["summary"]["selected_form_count"],
            "business_type_count": graph["summary"]["business_type_count"],
            "data_access_type_count": graph["summary"]["data_access_type_count"],
            "data_entry_form_count": data_entry["summary"]["selected_form_count"],
            "migration_slice_count": migration["slice_count"],
            "evidence_error_count": len(evidence_errors),
        },
        "command_count": len(COMMANDS),
        "commands": [
            {
                **row,
                "required_envelope": ["command_id", "aggregate_id", "expected_version", "operational_date", "fiscal_year", "dc_ref", "actor_context"],
                "required_result": ["command_id", "aggregate_id", "new_version", "new_state", "audit_event_id", "reconciliation_status"],
            }
            for row in COMMANDS
        ],
        "shared_execution_rules": [
            "one application command owns the transaction boundary",
            "nested domain handlers do not independently commit target state",
            "cross-module effects use transactional outbox and idempotent consumers",
            "all number allocation is concurrency-safe and retry returns the original result",
            "failure at every declared stage leaves no partial accepted business outcome",
            "current pointers and projections are rebuildable from immutable events/ledgers",
        ],
        "evidence_errors": evidence_errors,
        "limits": [
            "Contracts are target design gates, not proof that legacy end-to-end transactions are atomic.",
            "Static calls can miss inheritance, reflection, ORM hooks and runtime configuration branches.",
            "No command has been executed against Varanegar or a target database.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], "command_count": artifact["command_count"], "evidence": artifact["evidence"]}, ensure_ascii=False))
    return 0 if not evidence_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
