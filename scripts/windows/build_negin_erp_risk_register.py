"""Build a durable, evidence-backed risk register for Negin ERP reconstruction."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _risk(
    risk_id: str,
    title: str,
    severity: str,
    category: str,
    modules: list[str],
    failure_mode: str,
    controls: list[str],
    exit_criteria: list[str],
    evidence_refs: list[str],
    phase_gate: str,
    owner: str,
    evidence_strength: str = "CONFIRMED_AGGREGATE_OR_STATIC_EVIDENCE",
) -> dict[str, Any]:
    return {
        "id": risk_id,
        "title": title,
        "severity": severity,
        "category": category,
        "modules": modules,
        "evidence_strength": evidence_strength,
        "failure_mode": failure_mode,
        "controls": controls,
        "exit_criteria": exit_criteria,
        "phase_gate": phase_gate,
        "accountable_role_template_or_team": owner,
        "evidence_refs": evidence_refs,
        "status": "OPEN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--migration", required=True, type=Path)
    parser.add_argument("--roles", required=True, type=Path)
    parser.add_argument("--side-effects", required=True, type=Path)
    parser.add_argument("--gaps", required=True, type=Path)
    parser.add_argument("--roots", required=True, type=Path)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--drift", required=True, type=Path)
    parser.add_argument("--backlog", required=True, type=Path)
    parser.add_argument("--extension-semantics", required=True, type=Path)
    parser.add_argument("--extension-gap-paths", required=True, type=Path)
    parser.add_argument("--pos-transitive-graph", required=True, type=Path)
    parser.add_argument("--pos-source-model", required=True, type=Path)
    parser.add_argument("--report-target-contracts", required=True, type=Path)
    parser.add_argument("--report-evidence-gaps", required=True, type=Path)
    parser.add_argument("--report-generic-semantics", required=True, type=Path)
    parser.add_argument("--treasury-command-paths", required=True, type=Path)
    parser.add_argument("--treasury-source-model", required=True, type=Path)
    parser.add_argument("--treasury-trigger-semantics", required=True, type=Path)
    parser.add_argument("--treasury-view-lineage", required=True, type=Path)
    parser.add_argument("--treasury-target-contracts", required=True, type=Path)
    parser.add_argument("--treasury-validation-contracts", required=True, type=Path)
    parser.add_argument("--treasury-trigger-transitive-graph", required=True, type=Path)
    parser.add_argument("--treasury-web-field-contracts", required=True, type=Path)
    parser.add_argument("--order-sale-command-contracts", required=True, type=Path)
    parser.add_argument("--order-sale-dependency-graph", required=True, type=Path)
    parser.add_argument("--order-sale-sql-semantics", required=True, type=Path)
    parser.add_argument("--order-sale-source-model", required=True, type=Path)
    parser.add_argument("--order-sale-trigger-transitive-graph", required=True, type=Path)
    parser.add_argument("--order-sale-web-screens", required=True, type=Path)
    parser.add_argument("--stock-voucher-command-contract", required=True, type=Path)
    parser.add_argument("--distribution-sql-semantics", required=True, type=Path)
    parser.add_argument("--distribution-source-model", required=True, type=Path)
    parser.add_argument("--distribution-trigger-transitive-graph", required=True, type=Path)
    parser.add_argument("--supplier-invoice-command-contract", required=True, type=Path)
    parser.add_argument("--supplier-invoice-source-model", required=True, type=Path)
    parser.add_argument("--supplier-invoice-trigger-transitive-graph", required=True, type=Path)
    parser.add_argument("--accounting-voucher-entrypoints", required=True, type=Path)
    parser.add_argument("--accounting-voucher-sql-candidates", required=True, type=Path)
    parser.add_argument("--customer-goods-command-contracts", required=True, type=Path)
    parser.add_argument("--customer-goods-web-screens", required=True, type=Path)
    parser.add_argument("--supplier-master-command-contract", required=True, type=Path)
    parser.add_argument("--supplier-master-web-screen", required=True, type=Path)
    parser.add_argument("--operational-context-command-contracts", required=True, type=Path)
    parser.add_argument("--operational-context-web-screens", required=True, type=Path)
    parser.add_argument("--pricing-rule-command-contracts", required=True, type=Path)
    parser.add_argument("--pricing-rule-web-screens", required=True, type=Path)
    parser.add_argument("--final-date-boundary", required=True, type=Path)
    parser.add_argument("--final-date-diagnostic", required=True, type=Path)
    parser.add_argument("--stock-reconciliation-diagnostic", required=True, type=Path)
    parser.add_argument("--distribution-path-diagnostic", required=True, type=Path)
    parser.add_argument("--sales-return-amount-diagnostic", required=True, type=Path)
    parser.add_argument("--returned-cheque-cross-customer-diagnostic", required=True, type=Path)
    parser.add_argument("--received-cheque-projection-legal-diagnostic", required=True, type=Path)
    parser.add_argument("--payable-cheque-leaf-usage-diagnostic", required=True, type=Path)
    parser.add_argument("--voucher-status-pointer-diagnostic", required=True, type=Path)
    parser.add_argument("--empty-voucher-shell-diagnostic", required=True, type=Path)
    parser.add_argument("--ngt-return-crosswalk-diagnostic", required=True, type=Path)
    parser.add_argument("--supplier-receipt-component-diagnostic", required=True, type=Path)
    parser.add_argument(
        "--voucher-creation-policy",
        type=Path,
        default=Path(
            "artifacts/varanegar_analysis/domains/"
            "voucher_creation_atomicity_and_policy_20260828.json"
        ),
    )
    parser.add_argument(
        "--rule-replication-transport",
        type=Path,
        default=Path(
            "artifacts/varanegar_analysis/domains/"
            "rule_replication_transport_boundary_20260828.json"
        ),
    )
    parser.add_argument("--ngt-authorization-effective", type=Path)
    parser.add_argument("--ngt-owner-scope-effective", type=Path)
    parser.add_argument("--ngt-operation-date-boundary", type=Path)
    parser.add_argument("--configuration-precedence-boundary", type=Path)
    parser.add_argument("--ngt-configuration-runtime-boundary", type=Path)
    parser.add_argument("--ngt-order-persistence-boundary", type=Path)
    parser.add_argument("--ngt-order-runtime-boundary", type=Path)
    parser.add_argument("--ngt-tour-call-state-boundary", type=Path)
    parser.add_argument("--ngt-tour-call-runtime-boundary", type=Path)
    parser.add_argument("--ngt-tour-call-authorization-endpoints", type=Path)
    parser.add_argument("--ngt-payment-settlement-boundary", type=Path)
    parser.add_argument("--ngt-payment-runtime-boundary", type=Path)
    parser.add_argument("--ngt-payment-replication-boundary", type=Path)
    parser.add_argument("--ngt-payment-replication-runtime-boundary", type=Path)
    parser.add_argument("--ngt-replication-compensation-boundary", type=Path)
    parser.add_argument("--ngt-replication-compensation-runtime-boundary", type=Path)
    parser.add_argument("--ngt-return-replication-boundary", type=Path)
    parser.add_argument("--ngt-return-runtime-boundary", type=Path)
    parser.add_argument("--ngt-sale-replication-boundary", type=Path)
    parser.add_argument("--ngt-sale-replication-runtime-boundary", type=Path)
    parser.add_argument("--ngt-order-history-boundary", type=Path)
    parser.add_argument("--ngt-order-history-runtime-boundary", type=Path)
    parser.add_argument("--ngt-order-deletion-boundary", type=Path)
    parser.add_argument("--ngt-order-delete-log-boundary", type=Path)
    parser.add_argument("--supplier-cost-apply-boundary", type=Path)
    parser.add_argument("--supplier-cost-apply-runtime-boundary", type=Path)
    parser.add_argument("--supplier-unapply-delete-boundary", type=Path)
    parser.add_argument("--supplier-unapply-delete-runtime-boundary", type=Path)
    parser.add_argument("--payable-cheque-undo-boundary", type=Path)
    parser.add_argument("--payable-cheque-undo-runtime-boundary", type=Path)
    parser.add_argument("--received-cheque-undo-boundary", type=Path)
    parser.add_argument("--received-cheque-undo-runtime-boundary", type=Path)
    parser.add_argument("--received-cheque-delete-boundary", type=Path)
    parser.add_argument("--received-cheque-delete-runtime-boundary", type=Path)
    parser.add_argument("--stock-voucher-state-boundary", type=Path)
    parser.add_argument("--stock-voucher-state-runtime-boundary", type=Path)
    parser.add_argument("--stock-projection-validation-boundary", type=Path)
    parser.add_argument("--distribution-exit-lifecycle-boundary", type=Path)
    parser.add_argument("--distribution-exit-runtime-boundary", type=Path)
    parser.add_argument("--sale-conversion-state-boundary", type=Path)
    parser.add_argument("--sale-conversion-runtime-boundary", type=Path)
    parser.add_argument("--order-sale-policy-flag-sql", type=Path)
    parser.add_argument("--order-sale-policy-flag-runtime", type=Path)
    parser.add_argument("--order-sale-policy-gate-runtime", type=Path)
    parser.add_argument("--order-sale-policy-config-snapshot", type=Path)
    parser.add_argument("--order-sale-operation-date-sql", type=Path)
    parser.add_argument("--order-sale-operation-date-runtime", type=Path)
    parser.add_argument("--order-sale-authorization-sql", type=Path)
    parser.add_argument("--order-sale-authorization-runtime", type=Path)
    parser.add_argument("--datacontext-transaction-runtime", type=Path)
    parser.add_argument("--order-sale-evc-sql-boundary", type=Path)
    parser.add_argument("--order-sale-evc-runtime-boundary", type=Path)
    parser.add_argument("--discount-v2-query-contracts", type=Path)
    parser.add_argument("--discount-v2-dataset-sql", type=Path)
    parser.add_argument("--discount-v2-engine-runtime", type=Path)
    parser.add_argument("--discount-v2-dynamic-rule-sql", type=Path)
    parser.add_argument("--discount-v2-condition-families", type=Path)
    parser.add_argument("--discount-rule-authoring-boundary", type=Path)
    parser.add_argument("--discount-rule-authorization-boundary", type=Path)
    parser.add_argument("--sale-cancellation-boundary", type=Path)
    parser.add_argument("--sale-cancellation-runtime-boundary", type=Path)
    parser.add_argument("--return-issue-cancel-boundary", type=Path)
    parser.add_argument("--return-issue-cancel-runtime-boundary", type=Path)
    parser.add_argument("--sale-voucher-snapshot-boundary", type=Path)
    parser.add_argument("--sale-voucher-snapshot-runtime-boundary", type=Path)
    parser.add_argument("--sale-accounting-crosswalk-boundary", type=Path)
    parser.add_argument("--sale-invoice-print-boundary", type=Path)
    parser.add_argument("--sale-invoice-print-runtime-boundary", type=Path)
    parser.add_argument("--idempotency-guard-boundary", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    matrix = _load(args.matrix)
    migration = _load(args.migration)
    roles = _load(args.roles)
    side_effects = _load(args.side_effects)
    gaps = _load(args.gaps)
    roots = _load(args.roots)
    reports = _load(args.reports)
    drift = _load(args.drift)
    backlog = _load(args.backlog)
    extension_semantics = _load(args.extension_semantics)
    extension_gaps = _load(args.extension_gap_paths)
    pos_graph = _load(args.pos_transitive_graph)
    pos_source = _load(args.pos_source_model)
    report_target = _load(args.report_target_contracts)
    report_gaps = _load(args.report_evidence_gaps)
    report_generic = _load(args.report_generic_semantics)
    treasury_paths = _load(args.treasury_command_paths)
    treasury_source = _load(args.treasury_source_model)
    treasury_triggers = _load(args.treasury_trigger_semantics)
    treasury_lineage = _load(args.treasury_view_lineage)
    treasury_target = _load(args.treasury_target_contracts)
    treasury_validation = _load(args.treasury_validation_contracts)
    treasury_transitive = _load(args.treasury_trigger_transitive_graph)
    treasury_fields = _load(args.treasury_web_field_contracts)
    order_sale_commands = _load(args.order_sale_command_contracts)
    order_sale_dependencies = _load(args.order_sale_dependency_graph)
    order_sale_sql = _load(args.order_sale_sql_semantics)
    order_sale_source = _load(args.order_sale_source_model)
    order_sale_triggers = _load(args.order_sale_trigger_transitive_graph)
    order_sale_screens = _load(args.order_sale_web_screens)
    stock_voucher_contract = _load(args.stock_voucher_command_contract)
    distribution_sql = _load(args.distribution_sql_semantics)
    distribution_source = _load(args.distribution_source_model)
    distribution_triggers = _load(args.distribution_trigger_transitive_graph)
    supplier_invoice_contract = _load(args.supplier_invoice_command_contract)
    supplier_invoice_source = _load(args.supplier_invoice_source_model)
    supplier_invoice_triggers = _load(args.supplier_invoice_trigger_transitive_graph)
    accounting_voucher_entrypoints = _load(args.accounting_voucher_entrypoints)
    accounting_voucher_sql = _load(args.accounting_voucher_sql_candidates)
    customer_goods_commands = _load(args.customer_goods_command_contracts)
    customer_goods_screens = _load(args.customer_goods_web_screens)
    supplier_master_command = _load(args.supplier_master_command_contract)
    supplier_master_screen = _load(args.supplier_master_web_screen)
    operational_context_commands = _load(args.operational_context_command_contracts)
    operational_context_screens = _load(args.operational_context_web_screens)
    pricing_rule_commands = _load(args.pricing_rule_command_contracts)
    pricing_rule_screens = _load(args.pricing_rule_web_screens)
    final_date_boundary = _load(args.final_date_boundary)
    final_date_diagnostic = _load(args.final_date_diagnostic)
    stock_reconciliation = _load(args.stock_reconciliation_diagnostic)
    distribution_path = _load(args.distribution_path_diagnostic)
    sales_return_amount = _load(args.sales_return_amount_diagnostic)
    returned_cheque_cross_customer = _load(args.returned_cheque_cross_customer_diagnostic)
    received_cheque_projection_legal = _load(args.received_cheque_projection_legal_diagnostic)
    payable_cheque_leaf_usage = _load(args.payable_cheque_leaf_usage_diagnostic)
    voucher_status_pointer = _load(args.voucher_status_pointer_diagnostic)
    empty_voucher_shell = _load(args.empty_voucher_shell_diagnostic)
    ngt_return_crosswalk = _load(args.ngt_return_crosswalk_diagnostic)
    supplier_receipt_component = _load(args.supplier_receipt_component_diagnostic)
    voucher_creation_policy = _load(args.voucher_creation_policy)
    rule_replication_transport = _load(args.rule_replication_transport)
    idempotency_guard_boundary = (
        _load(args.idempotency_guard_boundary)
        if args.idempotency_guard_boundary
        else None
    )
    ngt_authorization_effective = (
        _load(args.ngt_authorization_effective)
        if args.ngt_authorization_effective
        else None
    )
    ngt_owner_scope_effective = (
        _load(args.ngt_owner_scope_effective)
        if args.ngt_owner_scope_effective
        else None
    )
    ngt_operation_date_boundary = (
        _load(args.ngt_operation_date_boundary)
        if args.ngt_operation_date_boundary
        else None
    )
    configuration_precedence_boundary = (
        _load(args.configuration_precedence_boundary)
        if args.configuration_precedence_boundary
        else None
    )
    ngt_configuration_runtime_boundary = (
        _load(args.ngt_configuration_runtime_boundary)
        if args.ngt_configuration_runtime_boundary
        else None
    )
    ngt_order_persistence_boundary = (
        _load(args.ngt_order_persistence_boundary)
        if args.ngt_order_persistence_boundary
        else None
    )
    ngt_order_runtime_boundary = (
        _load(args.ngt_order_runtime_boundary)
        if args.ngt_order_runtime_boundary
        else None
    )
    ngt_tour_call_state_boundary = (
        _load(args.ngt_tour_call_state_boundary)
        if args.ngt_tour_call_state_boundary
        else None
    )
    ngt_tour_call_runtime_boundary = (
        _load(args.ngt_tour_call_runtime_boundary)
        if args.ngt_tour_call_runtime_boundary
        else None
    )
    ngt_tour_call_authorization_endpoints = (
        _load(args.ngt_tour_call_authorization_endpoints)
        if args.ngt_tour_call_authorization_endpoints
        else None
    )
    ngt_payment_settlement_boundary = (
        _load(args.ngt_payment_settlement_boundary)
        if args.ngt_payment_settlement_boundary
        else None
    )
    ngt_payment_runtime_boundary = (
        _load(args.ngt_payment_runtime_boundary)
        if args.ngt_payment_runtime_boundary
        else None
    )
    ngt_payment_replication_boundary = (
        _load(args.ngt_payment_replication_boundary)
        if args.ngt_payment_replication_boundary
        else None
    )
    ngt_payment_replication_runtime_boundary = (
        _load(args.ngt_payment_replication_runtime_boundary)
        if args.ngt_payment_replication_runtime_boundary
        else None
    )
    ngt_replication_compensation_boundary = (
        _load(args.ngt_replication_compensation_boundary)
        if args.ngt_replication_compensation_boundary
        else None
    )
    ngt_replication_compensation_runtime_boundary = (
        _load(args.ngt_replication_compensation_runtime_boundary)
        if args.ngt_replication_compensation_runtime_boundary
        else None
    )
    ngt_return_replication_boundary = (
        _load(args.ngt_return_replication_boundary)
        if args.ngt_return_replication_boundary
        else None
    )
    ngt_return_runtime_boundary = (
        _load(args.ngt_return_runtime_boundary)
        if args.ngt_return_runtime_boundary
        else None
    )
    ngt_sale_replication_boundary = (
        _load(args.ngt_sale_replication_boundary)
        if args.ngt_sale_replication_boundary
        else None
    )
    ngt_sale_replication_runtime_boundary = (
        _load(args.ngt_sale_replication_runtime_boundary)
        if args.ngt_sale_replication_runtime_boundary
        else None
    )
    ngt_order_history_boundary = (
        _load(args.ngt_order_history_boundary) if args.ngt_order_history_boundary else None
    )
    ngt_order_history_runtime_boundary = (
        _load(args.ngt_order_history_runtime_boundary)
        if args.ngt_order_history_runtime_boundary
        else None
    )
    ngt_order_deletion_boundary = (
        _load(args.ngt_order_deletion_boundary) if args.ngt_order_deletion_boundary else None
    )
    ngt_order_delete_log_boundary = (
        _load(args.ngt_order_delete_log_boundary)
        if args.ngt_order_delete_log_boundary
        else None
    )
    supplier_cost_apply_boundary = (
        _load(args.supplier_cost_apply_boundary)
        if args.supplier_cost_apply_boundary
        else None
    )
    supplier_cost_apply_runtime_boundary = (
        _load(args.supplier_cost_apply_runtime_boundary)
        if args.supplier_cost_apply_runtime_boundary
        else None
    )
    supplier_unapply_delete_boundary = (
        _load(args.supplier_unapply_delete_boundary)
        if args.supplier_unapply_delete_boundary
        else None
    )
    supplier_unapply_delete_runtime_boundary = (
        _load(args.supplier_unapply_delete_runtime_boundary)
        if args.supplier_unapply_delete_runtime_boundary
        else None
    )
    payable_cheque_undo_boundary = (
        _load(args.payable_cheque_undo_boundary)
        if args.payable_cheque_undo_boundary
        else None
    )
    payable_cheque_undo_runtime_boundary = (
        _load(args.payable_cheque_undo_runtime_boundary)
        if args.payable_cheque_undo_runtime_boundary
        else None
    )
    received_cheque_undo_boundary = (
        _load(args.received_cheque_undo_boundary)
        if args.received_cheque_undo_boundary
        else None
    )
    received_cheque_undo_runtime_boundary = (
        _load(args.received_cheque_undo_runtime_boundary)
        if args.received_cheque_undo_runtime_boundary
        else None
    )
    received_cheque_delete_boundary = (
        _load(args.received_cheque_delete_boundary)
        if args.received_cheque_delete_boundary
        else None
    )
    received_cheque_delete_runtime_boundary = (
        _load(args.received_cheque_delete_runtime_boundary)
        if args.received_cheque_delete_runtime_boundary
        else None
    )
    stock_voucher_state_boundary = (
        _load(args.stock_voucher_state_boundary)
        if args.stock_voucher_state_boundary
        else None
    )
    stock_voucher_state_runtime_boundary = (
        _load(args.stock_voucher_state_runtime_boundary)
        if args.stock_voucher_state_runtime_boundary
        else None
    )
    stock_projection_validation_boundary = (
        _load(args.stock_projection_validation_boundary)
        if args.stock_projection_validation_boundary
        else None
    )
    distribution_exit_lifecycle_boundary = (
        _load(args.distribution_exit_lifecycle_boundary)
        if args.distribution_exit_lifecycle_boundary
        else None
    )
    distribution_exit_runtime_boundary = (
        _load(args.distribution_exit_runtime_boundary)
        if args.distribution_exit_runtime_boundary
        else None
    )
    sale_conversion_state_boundary = (
        _load(args.sale_conversion_state_boundary)
        if args.sale_conversion_state_boundary
        else None
    )
    sale_conversion_runtime_boundary = (
        _load(args.sale_conversion_runtime_boundary)
        if args.sale_conversion_runtime_boundary
        else None
    )
    order_sale_policy_flag_sql = (
        _load(args.order_sale_policy_flag_sql)
        if args.order_sale_policy_flag_sql
        else None
    )
    order_sale_policy_flag_runtime = (
        _load(args.order_sale_policy_flag_runtime)
        if args.order_sale_policy_flag_runtime
        else None
    )
    order_sale_policy_gate_runtime = (
        _load(args.order_sale_policy_gate_runtime)
        if args.order_sale_policy_gate_runtime
        else None
    )
    order_sale_policy_config_snapshot = (
        _load(args.order_sale_policy_config_snapshot)
        if args.order_sale_policy_config_snapshot
        else None
    )
    order_sale_operation_date_sql = (
        _load(args.order_sale_operation_date_sql)
        if args.order_sale_operation_date_sql
        else None
    )
    order_sale_operation_date_runtime = (
        _load(args.order_sale_operation_date_runtime)
        if args.order_sale_operation_date_runtime
        else None
    )
    order_sale_authorization_sql = (
        _load(args.order_sale_authorization_sql)
        if args.order_sale_authorization_sql
        else None
    )
    order_sale_authorization_runtime = (
        _load(args.order_sale_authorization_runtime)
        if args.order_sale_authorization_runtime
        else None
    )
    datacontext_transaction_runtime = (
        _load(args.datacontext_transaction_runtime)
        if args.datacontext_transaction_runtime
        else None
    )
    order_sale_evc_sql_boundary = (
        _load(args.order_sale_evc_sql_boundary)
        if args.order_sale_evc_sql_boundary
        else None
    )
    order_sale_evc_runtime_boundary = (
        _load(args.order_sale_evc_runtime_boundary)
        if args.order_sale_evc_runtime_boundary
        else None
    )
    discount_v2_query_contracts = (
        _load(args.discount_v2_query_contracts)
        if args.discount_v2_query_contracts
        else None
    )
    discount_v2_dataset_sql = (
        _load(args.discount_v2_dataset_sql)
        if args.discount_v2_dataset_sql
        else None
    )
    discount_v2_engine_runtime = (
        _load(args.discount_v2_engine_runtime)
        if args.discount_v2_engine_runtime
        else None
    )
    discount_v2_dynamic_rule_sql = (
        _load(args.discount_v2_dynamic_rule_sql)
        if args.discount_v2_dynamic_rule_sql
        else None
    )
    discount_v2_condition_families = (
        _load(args.discount_v2_condition_families)
        if args.discount_v2_condition_families
        else None
    )
    discount_rule_authoring_boundary = (
        _load(args.discount_rule_authoring_boundary)
        if args.discount_rule_authoring_boundary
        else None
    )
    discount_rule_authorization_boundary = (
        _load(args.discount_rule_authorization_boundary)
        if args.discount_rule_authorization_boundary
        else None
    )
    sale_cancellation_boundary = (
        _load(args.sale_cancellation_boundary)
        if args.sale_cancellation_boundary
        else None
    )
    sale_cancellation_runtime_boundary = (
        _load(args.sale_cancellation_runtime_boundary)
        if args.sale_cancellation_runtime_boundary
        else None
    )
    return_issue_cancel_boundary = (
        _load(args.return_issue_cancel_boundary)
        if args.return_issue_cancel_boundary
        else None
    )
    return_issue_cancel_runtime_boundary = (
        _load(args.return_issue_cancel_runtime_boundary)
        if args.return_issue_cancel_runtime_boundary
        else None
    )
    sale_voucher_snapshot_boundary = (
        _load(args.sale_voucher_snapshot_boundary)
        if args.sale_voucher_snapshot_boundary
        else None
    )
    sale_voucher_snapshot_runtime_boundary = (
        _load(args.sale_voucher_snapshot_runtime_boundary)
        if args.sale_voucher_snapshot_runtime_boundary
        else None
    )
    sale_accounting_crosswalk_boundary = (
        _load(args.sale_accounting_crosswalk_boundary)
        if args.sale_accounting_crosswalk_boundary
        else None
    )
    sale_invoice_print_boundary = (
        _load(args.sale_invoice_print_boundary)
        if args.sale_invoice_print_boundary
        else None
    )
    sale_invoice_print_runtime_boundary = (
        _load(args.sale_invoice_print_runtime_boundary)
        if args.sale_invoice_print_runtime_boundary
        else None
    )
    if ngt_owner_scope_effective is not None and ngt_authorization_effective is None:
        raise ValueError("NGT owner scope evidence requires NGT authorization evidence")
    if ngt_operation_date_boundary is not None and ngt_owner_scope_effective is None:
        raise ValueError("NGT operation-date evidence requires NGT owner-scope evidence")
    if (configuration_precedence_boundary is None) != (ngt_configuration_runtime_boundary is None):
        raise ValueError("configuration precedence and NGT runtime evidence must be supplied together")
    if configuration_precedence_boundary is not None and ngt_operation_date_boundary is None:
        raise ValueError("configuration evidence requires the preceding NGT evidence chain")
    if (ngt_order_persistence_boundary is None) != (ngt_order_runtime_boundary is None):
        raise ValueError("NGT order persistence and runtime evidence must be supplied together")
    if ngt_order_persistence_boundary is not None and configuration_precedence_boundary is None:
        raise ValueError("NGT order evidence requires the preceding configuration evidence chain")
    tour_call_evidence_count = sum(
        value is not None
        for value in (
            ngt_tour_call_state_boundary,
            ngt_tour_call_runtime_boundary,
            ngt_tour_call_authorization_endpoints,
        )
    )
    if tour_call_evidence_count not in (0, 3):
        raise ValueError("NGT tour/call state, runtime and authorization evidence must be supplied together")
    if ngt_tour_call_state_boundary is not None and ngt_order_persistence_boundary is None:
        raise ValueError("NGT tour/call evidence requires the preceding order evidence chain")
    if (ngt_payment_settlement_boundary is None) != (ngt_payment_runtime_boundary is None):
        raise ValueError("NGT payment settlement and runtime evidence must be supplied together")
    if ngt_payment_settlement_boundary is not None and ngt_tour_call_state_boundary is None:
        raise ValueError("NGT payment evidence requires the preceding tour/call evidence chain")
    if (ngt_payment_replication_boundary is None) != (
        ngt_payment_replication_runtime_boundary is None
    ):
        raise ValueError("NGT payment replication SQL and runtime evidence must be supplied together")
    if ngt_payment_replication_boundary is not None and ngt_payment_settlement_boundary is None:
        raise ValueError("NGT payment replication evidence requires the preceding payment evidence chain")
    if (ngt_replication_compensation_boundary is None) != (
        ngt_replication_compensation_runtime_boundary is None
    ):
        raise ValueError("NGT compensation SQL and runtime evidence must be supplied together")
    if ngt_replication_compensation_boundary is not None and ngt_payment_replication_boundary is None:
        raise ValueError("NGT compensation evidence requires the preceding payment replication evidence chain")
    if (ngt_return_replication_boundary is None) != (ngt_return_runtime_boundary is None):
        raise ValueError("NGT return SQL and runtime evidence must be supplied together")
    if ngt_return_replication_boundary is not None and ngt_replication_compensation_boundary is None:
        raise ValueError("NGT return evidence requires the preceding compensation evidence chain")
    if (ngt_sale_replication_boundary is None) != (
        ngt_sale_replication_runtime_boundary is None
    ):
        raise ValueError("NGT sale SQL and runtime evidence must be supplied together")
    if ngt_sale_replication_boundary is not None and ngt_return_replication_boundary is None:
        raise ValueError("NGT sale evidence requires the preceding return evidence chain")
    if (ngt_order_history_boundary is None) != (ngt_order_history_runtime_boundary is None):
        raise ValueError("NGT order-history SQL and runtime evidence must be supplied together")
    if ngt_order_history_boundary is not None and ngt_sale_replication_boundary is None:
        raise ValueError("NGT order-history evidence requires the preceding sale evidence chain")
    if ngt_order_deletion_boundary is not None and ngt_order_history_boundary is None:
        raise ValueError("NGT order-deletion evidence requires order-history evidence")
    if ngt_order_delete_log_boundary is not None and ngt_order_deletion_boundary is None:
        raise ValueError("NGT order delete-log evidence requires order-deletion evidence")
    if (supplier_cost_apply_boundary is None) != (
        supplier_cost_apply_runtime_boundary is None
    ):
        raise ValueError("supplier cost SQL and runtime evidence must be supplied together")
    if supplier_cost_apply_boundary is not None and ngt_order_delete_log_boundary is None:
        raise ValueError("supplier cost evidence requires the preceding evidence chain")
    if (supplier_unapply_delete_boundary is None) != (
        supplier_unapply_delete_runtime_boundary is None
    ):
        raise ValueError("supplier unlink/delete SQL and runtime evidence must be supplied together")
    if supplier_unapply_delete_boundary is not None and supplier_cost_apply_boundary is None:
        raise ValueError("supplier unlink/delete evidence requires supplier cost evidence")
    if (payable_cheque_undo_boundary is None) != (
        payable_cheque_undo_runtime_boundary is None
    ):
        raise ValueError("payable-cheque undo SQL and runtime evidence must be supplied together")
    if payable_cheque_undo_boundary is not None and supplier_unapply_delete_boundary is None:
        raise ValueError("payable-cheque undo evidence requires the preceding supplier evidence chain")
    if (received_cheque_undo_boundary is None) != (
        received_cheque_undo_runtime_boundary is None
    ):
        raise ValueError("received-cheque undo SQL and runtime evidence must be supplied together")
    if received_cheque_undo_boundary is not None and payable_cheque_undo_boundary is None:
        raise ValueError("received-cheque undo evidence requires payable-cheque undo evidence")
    if (received_cheque_delete_boundary is None) != (
        received_cheque_delete_runtime_boundary is None
    ):
        raise ValueError("received-cheque delete SQL and runtime evidence must be supplied together")
    if received_cheque_delete_boundary is not None and received_cheque_undo_boundary is None:
        raise ValueError("received-cheque delete evidence requires received-cheque undo evidence")
    if (stock_voucher_state_boundary is None) != (
        stock_voucher_state_runtime_boundary is None
    ):
        raise ValueError("stock-voucher state SQL and runtime evidence must be supplied together")
    if stock_voucher_state_boundary is not None and received_cheque_delete_boundary is None:
        raise ValueError("stock-voucher state evidence requires the preceding evidence chain")
    if stock_projection_validation_boundary is not None and stock_voucher_state_boundary is None:
        raise ValueError("stock projection validation evidence requires stock-voucher state evidence")
    if (distribution_exit_lifecycle_boundary is None) != (
        distribution_exit_runtime_boundary is None
    ):
        raise ValueError("distribution-exit SQL and runtime evidence must be supplied together")
    if distribution_exit_lifecycle_boundary is not None and stock_projection_validation_boundary is None:
        raise ValueError("distribution-exit evidence requires the preceding stock projection evidence chain")
    if (sale_conversion_state_boundary is None) != (sale_conversion_runtime_boundary is None):
        raise ValueError("sale-conversion SQL and runtime evidence must be supplied together")
    if (order_sale_policy_flag_sql is None) != (order_sale_policy_flag_runtime is None):
        raise ValueError("order-sale policy-flag SQL and runtime evidence must be supplied together")
    if order_sale_policy_flag_sql is not None and sale_conversion_state_boundary is None:
        raise ValueError("order-sale policy-flag evidence requires sale-conversion evidence")
    if (order_sale_policy_gate_runtime is None) != (order_sale_policy_config_snapshot is None):
        raise ValueError("order-sale policy gate and current config evidence must be supplied together")
    if order_sale_policy_gate_runtime is not None and order_sale_policy_flag_sql is None:
        raise ValueError("order-sale policy gate evidence requires policy-flag evidence")
    if (order_sale_operation_date_sql is None) != (order_sale_operation_date_runtime is None):
        raise ValueError("order-sale operation-date SQL and runtime evidence must be supplied together")
    if order_sale_operation_date_sql is not None and order_sale_policy_gate_runtime is None:
        raise ValueError("order-sale operation-date evidence requires policy-gate evidence")
    if (order_sale_authorization_sql is None) != (order_sale_authorization_runtime is None):
        raise ValueError("order-sale authorization SQL and runtime evidence must be supplied together")
    if order_sale_authorization_sql is not None and order_sale_operation_date_sql is None:
        raise ValueError("order-sale authorization evidence requires operation-date evidence")
    if datacontext_transaction_runtime is not None and order_sale_authorization_sql is None:
        raise ValueError("DataContext transaction evidence requires order-sale authorization evidence")
    if (order_sale_evc_sql_boundary is None) != (order_sale_evc_runtime_boundary is None):
        raise ValueError("order-sale EVC SQL and runtime evidence must be supplied together")
    if order_sale_evc_sql_boundary is not None and datacontext_transaction_runtime is None:
        raise ValueError("order-sale EVC evidence requires DataContext transaction evidence")
    if (discount_v2_query_contracts is None) != (discount_v2_dataset_sql is None):
        raise ValueError("Discount V2 query and dataset evidence must be supplied together")
    if discount_v2_query_contracts is not None and order_sale_evc_sql_boundary is None:
        raise ValueError("Discount V2 dataset evidence requires order-sale EVC evidence")
    if (discount_v2_engine_runtime is None) != (discount_v2_dynamic_rule_sql is None):
        raise ValueError("Discount V2 engine and dynamic-rule SQL evidence must be supplied together")
    if discount_v2_engine_runtime is not None and discount_v2_query_contracts is None:
        raise ValueError("Discount V2 engine evidence requires query and dataset evidence")
    if discount_v2_condition_families is not None and discount_v2_engine_runtime is None:
        raise ValueError("Discount V2 condition-family evidence requires engine evidence")
    if discount_rule_authoring_boundary is not None and discount_v2_condition_families is None:
        raise ValueError("Discount rule authoring evidence requires condition-family evidence")
    if discount_rule_authorization_boundary is not None and discount_rule_authoring_boundary is None:
        raise ValueError("Discount rule authorization evidence requires authoring evidence")
    if sale_conversion_state_boundary is not None and distribution_exit_lifecycle_boundary is None:
        raise ValueError("sale-conversion evidence requires the preceding distribution-exit evidence chain")
    if (sale_cancellation_boundary is None) != (sale_cancellation_runtime_boundary is None):
        raise ValueError("sale-cancellation SQL and runtime evidence must be supplied together")
    if sale_cancellation_boundary is not None and sale_conversion_state_boundary is None:
        raise ValueError("sale-cancellation evidence requires the preceding sale-conversion evidence chain")
    if (return_issue_cancel_boundary is None) != (return_issue_cancel_runtime_boundary is None):
        raise ValueError("return issue/cancel SQL and runtime evidence must be supplied together")
    if return_issue_cancel_boundary is not None and sale_cancellation_boundary is None:
        raise ValueError("return issue/cancel evidence requires the preceding sale-cancellation evidence chain")
    if (sale_voucher_snapshot_boundary is None) != (sale_voucher_snapshot_runtime_boundary is None):
        raise ValueError("sale-voucher snapshot SQL and runtime evidence must be supplied together")
    if sale_voucher_snapshot_boundary is not None and return_issue_cancel_boundary is None:
        raise ValueError("sale-voucher snapshot evidence requires the preceding return issue/cancel evidence chain")
    if sale_accounting_crosswalk_boundary is not None and sale_voucher_snapshot_boundary is None:
        raise ValueError("sale-accounting crosswalk evidence requires the preceding sale-voucher snapshot evidence chain")
    if (sale_invoice_print_boundary is None) != (sale_invoice_print_runtime_boundary is None):
        raise ValueError("sale invoice print SQL/deployment and runtime evidence must be supplied together")
    if sale_invoice_print_boundary is not None and sale_accounting_crosswalk_boundary is None:
        raise ValueError("sale invoice print evidence requires the preceding sale-accounting crosswalk evidence chain")
    E = {name: value.as_posix() for name, value in vars(args).items() if isinstance(value, Path) and name != "output"}
    tour_lifecycle_endpoint_names = {
        "ActivateDistTour", "ActivateHotSaleTour", "ActivatePreSaleTour", "ActivateVanSaleTour",
        "CancelTour", "ConfirmDistTour", "ConfirmDistTourPayments", "ConfirmDistTourReceived",
        "ConfirmHotSaleTourPayments", "ConfirmHotSaleTourReceived",
        "ConfirmPreSaleTourPayments", "ConfirmPreSaleTourReceived", "ConfirmTourReceived",
        "ConfirmVanSaleTourPayments", "DeactivateDistTour", "DeactivateHotSaleTour",
        "DeactivatePreSaleTour", "DeactivateVanSaleTour", "ReplicateDistTour",
        "ReplicateHotSaleTour", "ReplicatePreSaleTour", "ReplicateVanSaleTour",
        "TourReceived", "TourSent", "WithdrawDistTourPayments", "WithdrawHotSaleTourPayments",
        "WithdrawPreSaleTourPayments", "WithdrawVanSaleTourPayments",
        "backToReadySendStatusTour",
    }
    tour_lifecycle_endpoints = (
        [
            row
            for row in ngt_tour_call_authorization_endpoints["endpoints"]
            if row["controller"] == "NGT.WebApi.Controllers.V2.TourController"
            and row["method"] in tour_lifecycle_endpoint_names
        ]
        if ngt_tour_call_authorization_endpoints is not None
        else []
    )

    risks = [
        _risk("R-001", "accidental write to operational Varanegar", "CRITICAL", "safety", ["integration_migration", "platform"], "analysis, migration or test code mutates operational source or triggers a business command", ["read-only credential and database updateability assertion", "deny-datawriter", "environment allowlist and command runner denylist"], ["automated negative test proves all source adapters reject updateable or operational targets", "no operational write credential exists in target runtime"], [E["migration"], E["backlog"]], "P0", "security_administrator"),
        _risk("R-002", "runtime or schema drift invalidates parity evidence", "HIGH", "evidence", ["integration_migration", "reporting_documents"], "DLL, menu, SQL or authorization changes after extraction while old contracts remain trusted", ["semantic drift baseline by source group", "fresh extraction before release gate"], ["comparison artifact is NO_SEMANTIC_DRIFT or every changed source is reviewed and dependent tests regenerated"], [E["drift"]], "P1_AND_EVERY_RELEASE", "migration_reviewer"),
        _risk("R-003", "legacy aggregate rights converted into real grants", "CRITICAL", "authorization", ["identity_authorization"], "anonymous or aggregate legacy rights are assigned to identities without owner review", ["identity-free role templates", "deny-first policy", "explicit provisioning approval"], ["identity source selected", "each production assignment is read back and owner-approved", "mandatory deny tests pass"], [E["roles"]], "P0", "security_administrator"),
        _risk("R-004", "PII, credentials or business values leak into artifacts/logs", "CRITICAL", "privacy_security", ["platform", "reporting_documents", "integration_migration"], "raw values, secrets, identities or connection strings are persisted in evidence, logs or browser", ["fingerprint-only redaction", "server-side secret store", "aggregate-only authorization evidence", "log allowlist"], ["secret/PII scanners pass", "browser bundle and evidence manifest contain no forbidden keys", "retention policy approved"], [E["backlog"], E["matrix"]], "P0_AND_EVERY_RELEASE", "security_administrator"),
        _risk("R-005", "CRUD replication bypasses domain invariants", "CRITICAL", "architecture", ["sales", "inventory", "distribution", "receivables_treasury", "procurement_payables", "accounting"], "target writes tables directly and omits orchestration, history, ledger or reversal rules", ["application command ownership", "forbidden dependency tests", "ledger/projection reconciliation"], ["all material writes are reachable only through named commands", "Golden and fault-injection cases pass", "no UI or integration direct table writer"], [E["side_effects"], E["matrix"]], "P2_TO_P5", "delivery_team"),
        _risk(
            "R-006",
            "retry creates duplicate business outcome",
            "CRITICAL",
            "reliability",
            ["platform", "sales", "inventory", "distribution", "receivables_treasury", "procurement_payables", "accounting", "configuration", "integration_migration"],
            "network/process retry repeats number allocation, voucher, history, ledger or outbox effect; the clone has no unique FileName/CenterId outbox-watermark constraint, and its receive receipt has only an identity PK plus non-unique site/range/file indexes: the trigger rejects decreasing watermarks but permits equality, does not require the next contiguous range, and scalarizes inserted. Local receive enumerates directory files and FTP receive consumes server listing without a proven explicit Sort/OrderBy step; combined with the non-gapless receipt guard, deterministic range order before execution is not proven. Service Start/Run call a named ControlLock, but its inspected graph has no Mutex, Monitor or database call and only a File.Exists signal; the send watermark read/update concatenate queries and ReplicationSend.CenterId is not unique. Timer initialization sets Interval, subscribes Elapsed and enables the timer, but has no explicit AutoReset/SynchronizingObject setter; Run contains Thread.Sleep, only sets Timer.Enabled=true, and its graph has no Mutex, Monitor, Interlocked, Semaphore or ReaderWriterLock. The package executor also feeds CommandTimeout constants 0, 600 and 30000 while the general connector uses 600; a finite positive deadline and cancellation propagation on every package path are not proven. Six rule triggers capture but do not reuse InsertToLog's IDENT_CURRENT output, so direct rule-watermark corruption is not asserted; however two binary voucher triggers persist that returned LogId into mapping tables with no index, unique constraint or foreign key. Both mapping tables are empty, their four SQL dependencies are insert/delete triggers, and no SELECT/JOIN reader or direct literal in the 62 catalogued application assemblies was found; no retained wrong mapping or active downstream-consumer incident is asserted, and dynamic/external consumption remains unknown. Therefore neither cross-process per-center sender serialization nor periodic Run single-flight is proven. The empty transport snapshot cannot demonstrate an actual out-of-order, sender-race, overlapping-tick or long-running package incident",
            ["command_id receipt", "payload fingerprint", "unique business constraints", "idempotent consumers", "unique center+package+version replication inbox/outbox identity", "set-based receipt validation and explicit contiguous-range policy", "parse and sort by typed center/range metadata before execution", "quarantine gaps and out-of-order packages before any script or command", "database-backed per-center lease or application lock with fencing token"],
            ["same-key replay returns original result", "crash-after-commit tests converge", "duplicate aggregate/event/outbox count is zero", "equal replication replay is rejected or returns the original receipt", "concurrent and multi-row receipt tests preserve a unique contiguous center watermark", "shuffled local and FTP listings converge to deterministic range order", "missing and overlapping ranges fail before package execution", "two concurrent sender instances cannot allocate overlapping ranges or regress the fenced center watermark", "a timer callback lasting longer than its interval cannot overlap another receive/send cycle", "every package execution path has a finite positive deadline, propagates cancellation and quarantines timeout without advancing receipt", "concurrent binary voucher log writes persist each source voucher against the exact inserted LogId under a unique foreign-keyed mapping"],
            [
                E["side_effects"],
                E["backlog"],
                E["rule_replication_transport"],
                *(
                    [E["idempotency_guard_boundary"]]
                    if idempotency_guard_boundary is not None
                    else []
                ),
            ],
            "P0_BEFORE_ANY_COMMAND",
            "delivery_team",
        ),
        _risk(
            "R-007",
            "partial multi-aggregate commit",
            "CRITICAL",
            "transactionality",
            ["platform", "sales", "inventory", "distribution", "receivables_treasury", "procurement_payables", "accounting", "configuration", "integration_migration"],
            "one part of sale/return/stock/distribution/settlement succeeds while dependent ledger or history fails. In the hash-pinned replication connector, Execute closes and rethrows and Commit failure also throws, but RollBackTransaction has an exception handler with no throw/rethrow. Receiver error paths call this rollback method, so a rollback failure is not proven observable and can leave transaction outcome unknown even though ordinary executor false/exception paths correctly attempt rollback before receipt. Both receivers also perform filesystem cleanup after recording the receipt but before database Commit: Local copies then deletes files, while FTP deletes local files and the remote package before Commit. Filesystem/FTP and SQL do not share an atomic commit, and automatic retry from a preserved input after Commit failure is not proven. On executor false, the standard Local wrapper supplies a false flag, then Rollback precedes five File.Delete calls and addDefectiveCenter while the caller discards the returned outcome; FTP Rollback precedes three local File.Delete calls and no remote DeleteFile in the immediate block. Exact path roles and later remote preservation were not proven, so durable quarantine and retry parity are not assumed. After the primary local receive commit, ResetReplicationSendTable runs a separate two-command transaction and returns true/false, but its caller immediately pops the result; the exact obfuscated SQL effect and a runtime failure were not proven. No runtime Commit failure or rejected package was observed",
            ["single transaction owner", "outbox after local commit", "failure injection at every stage", "unknown reconciliation status", "rollback failure propagation and durable incident receipt", "connection quarantine after failed rollback", "defer destructive input acknowledgement until durable database commit", "recoverable inbox state machine with immutable package copy", "durable rejected-package quarantine with payload hash, reason and attempt", "propagate and persist every post-commit maintenance result"],
            ["all declared failure stages roll back or become explicitly recoverable", "no accepted result with incomplete invariant", "forced rollback failure is surfaced and leaves no reusable connection or success receipt", "unknown commit/rollback outcome is quarantined until reconciliation", "forced commit failure leaves an immutable input available for automatic retry", "remote/local package deletion occurs only after durable applied receipt commit", "executor rejection preserves one immutable quarantined payload and produces the same retry decision in local and FTP modes", "forced post-receive reset failure changes the orchestration result and creates a retryable incident receipt"],
            [E["side_effects"], E["matrix"], E["rule_replication_transport"]],
            "P2_TO_P5",
            "financial_controller",
        ),
        _risk("R-008", "snapshot, ledger and current pointer are conflated", "CRITICAL", "data_model", ["accounting", "inventory", "receivables_treasury", "procurement_payables"], "mutable current state overwrites event/history or historical snapshots are treated as authoritative current balance", ["separate immutable ledger/history and rebuildable projection", "version/current pointer provenance"], ["projection rebuild matches ledger", "historical version queries and reversal tests pass", "current pointer never deletes history"], [E["matrix"], E["migration"]], "P2_TO_P5", "financial_controller"),
        _risk("R-009", "business date replaced by migration or created timestamp", "HIGH", "temporal", ["organization_context", "sales", "inventory", "accounting", "integration_migration"], "operational reports, fiscal allocation or aging use import time instead of business date", ["typed business/effective/posted/import timestamps", "snapshot window provenance"], ["date semantics documented per entity", "three-month reconciliation uses business date", "timezone and Persian-date boundary tests pass"], [E["migration"], E["matrix"]], "P0_TO_P2", "migration_reviewer"),
        _risk("R-010", "automatic merge of barcode, party or route crosswalk", "HIGH", "migration", ["master_data", "integration_migration"], "duplicate/sentinel barcode, contact indicators or incompatible legacy/NGT paths are silently merged", ["versioned crosswalk statuses", "quarantine", "no auto-merge from weak indicators"], ["all ambiguous mappings have owner/evidence", "sentinels and placeholders remain quarantined", "merge reversal audit is tested"], [E["migration"], E["matrix"]], "P1", "master_data_steward"),
        _risk("R-011", "mode-dependent distribution path codes are mistaken for orphan master IDs", "CRITICAL", "data_quality", ["distribution", "master_data", "configuration", "integration_migration"], "the target joins 26,086 valid integer path/run codes to GNR.tblDistPath.ID, invents corruption, rejects history or assigns a default geographic route", ["preserve exact integer code and source mode", "separate optional authoritative label crosswalk", "no inferred master ID or default route", "mode-aware validation and aggregate reconciliation"], ["all 26,086 codes retain exact value and provenance", "manual-code configuration branch is covered by tests", "every label is authoritative or explicitly unresolved", "no master-ID join is used as an orphan test"], [E["distribution_path_diagnostic"], E["migration"], E["matrix"]], "P1_AND_P3", "distribution_planner", "CONFIRMED_READ_ONLY_CLONE_SCHEMA_SQL_IL_AND_AGGREGATE_EVIDENCE"),
        _risk("R-012", "cardex-only rebuild discards operational stock obligations", "CRITICAL", "data_quality", ["inventory", "sales", "distribution", "accounting", "integration_migration"], "the target treats plain cardex as on-hand truth and ignores 1,594 open-sale stock-obligation keys, overstating operational stock by 104,470 units on the clone", ["versioned transcription of the official legacy formula", "separate immutable cardex ledger, open-sale obligation and operational projection", "component-level explain output", "quarantine only the residual after the complete formula"], ["all 33,314 clone keys reconcile under the complete formula", "approved snapshot reproduces zero or explicitly explained residual", "open-sale obligation and exit transitions rebuild deterministically", "source remains untouched"], [E["stock_reconciliation_diagnostic"], E["migration"], E["matrix"]], "P3", "financial_controller", "CONFIRMED_READ_ONLY_CLONE_RECONCILIATION_AND_STATIC_SQL_EVIDENCE"),
        _risk("R-013", "gross sales-return amount is substituted for official net", "CRITICAL", "financial_integrity", ["sales", "inventory", "receivables_treasury", "accounting", "integration_migration"], "the target treats 731 valid gross-to-net adjustments, including 696 active returns, as corruption or credits/reverses customers using gross Amount instead of official AmountNut", ["preserve gross, discount/addition components and net provenance", "named Amount-Discount+AddAmount money policy", "header SUM(AmountNut) invariant", "separate tax/charge and return-credit-stock reconciliation", "never quarantine gross-versus-net difference alone"], ["all 14,091 clone returns retain exact components and reconcile with zero official-net residual", "item formula and component rollups are command and persistence invariants", "gross-to-net bridge is explainable", "return, credit, stock, retry and reversal Golden cases pass"], [E["sales_return_amount_diagnostic"], E["migration"], E["matrix"]], "P2_AND_P4", "financial_controller", "CONFIRMED_READ_ONLY_CLONE_SQL_IL_AND_AGGREGATE_EVIDENCE"),
        _risk("R-014", "cross-party returned-cheque allocation semantics are flattened", "CRITICAL", "financial_integrity", ["receivables_treasury", "accounting", "integration_migration"], "the target forces cheque owner, allocation customer and invoice customer into one party field, reassigning 49 valid cross-party settlements or losing their linked accounting legs", ["distinct cheque-owner and allocation-customer roles", "immutable cheque+sale+customer allocation key", "preserve linked accounting-leg provenance", "quarantine only missing/inconsistent allocation or over-settlement", "never repair from ManualCustRef"], ["all 49 clone rows match their exact original allocation", "unexplained and over-settled pair counts are zero", "invoice, allocation, cheque and customer balances reconcile before/after", "cross-party, parent-customer, partial, retry and rollback Golden cases pass"], [E["returned_cheque_cross_customer_diagnostic"], E["migration"], E["matrix"]], "P4", "financial_controller", "CONFIRMED_READ_ONLY_CLONE_SQL_IL_AND_AGGREGATE_EVIDENCE"),
        _risk("R-015", "payable cheque leaf usage state loses provenance or is silently repaired", "HIGH", "financial_integrity", ["procurement_payables", "accounting", "integration_migration"], "155 supported source-used-unlinked leaves are cleared, synthesized into payable cheques, or mislabeled as proven manual intent despite absent actor/time provenance", ["typed SOURCE_USED_UNLINKED state", "UNKNOWN_SOURCE provenance", "owner review before reuse", "single cheque-event/projection/leaf transaction", "supplier cardex and leaf-state reconciliation"], ["4827 used leaves reconcile as 4672 linked plus 155 source-used-unlinked", "no synthetic cheque or automatic clear occurs", "all future manual leaf transitions record actor, time and reason", "retry/fault/undo tests preserve one leaf outcome", "treasury owner approves reuse policy"], [E["payable_cheque_leaf_usage_diagnostic"], E["migration"], E["matrix"]], "P5", "financial_controller", "CONFIRMED_READ_ONLY_CLONE_AND_DEPLOYED_SQL_WITH_HISTORICAL_REASON_UNPROVEN"),
        _risk("R-016", "unresolved legacy forms are removed as dead code", "HIGH", "functional_parity", ["receivables_treasury", "configuration"], "bank reconciliation list/setup or special district options disappear despite dynamic/external usage", ["retain unresolved status", "business-owner disposition", "runtime/configuration evidence where available"], ["retain/replace/retire decision exists for all three roots", "retained behavior has acceptance tests"], [E["gaps"], E["roots"]], "P0_BEFORE_SCOPE_FREEZE", "migration_reviewer", "STATIC_ABSENCE_ONLY_NOT_PROOF"),
        _risk("R-017", "stateful print is implemented as a pure read", "HIGH", "reporting", ["reporting_documents", "sales"], "print-completed/status/history side effects are omitted or executed on preview/export", ["separate preview/export/print-completed commands", "idempotency and audit", "state-machine guard"], ["preview/export mutate nothing", "print-completed retry is idempotent", "document status/history reconcile"], [E["reports"], E["report_target_contracts"]], "P1_TO_P2", "report_exporter"),
        _risk("R-018", "configuration precedence changes business behavior", "HIGH", "configuration", ["configuration", "pricing_rules", "sales", "inventory"], "global/DC/office/user/effective-date flags resolve differently from Varanegar", ["typed versioned settings", "effective-value explanation", "four-eyes material publish"], ["precedence matrix approved", "boundary-date and missing-setting tests pass", "every rule decision records effective setting version"], [E["matrix"], E["roles"]], "P0_TO_P2", "configuration_publisher"),
        _risk("R-019", "backup exists but restore is unproven", "CRITICAL", "operations", ["platform"], "database loss cannot be recovered within business tolerance", ["encrypted backup", "isolated restore drills", "checksum and application smoke test"], ["user approves RPO/RTO", "fresh restore drill passes and is timestamped", "runbook owner is named"], [E["backlog"]], "P0_AND_P6", "delivery_team", "TARGET_OPERATIONAL_REQUIREMENT"),
        _risk("R-020", "technology choice is assumed and creates rework", "MEDIUM", "planning", ["platform", "reporting_documents"], "backend/web/database/deployment choices are embedded before user decision", ["P0-001 signed ADR", "stack-neutral contracts until decision"], ["ADR records selected stack, support owner and rejected alternatives", "backlog is re-estimated"], [E["backlog"]], "P0_START", "user_decision"),
        _risk("R-021", "large read models cause operational performance failure", "HIGH", "performance", ["master_data", "sales", "inventory", "reporting_documents"], "customer/product/order/cardex/report queries scan unbounded history or block writes", ["prepared projections", "pagination and bounded filters", "query budgets and load tests"], ["representative volume p95 targets are user-approved and met", "no report requires operational-table lock escalation"], [E["matrix"], E["report_target_contracts"]], "P1_TO_P6", "delivery_team", "INFERRED_FROM_VOLUME_AND_REPORT_SURFACES"),
        _risk("R-022", "module coupling is recreated as distributed transactions", "HIGH", "architecture", ["master_data", "sales", "inventory", "distribution", "accounting"], "cross-module Legacy calls become synchronous service mesh or shared-table ownership", ["modular monolith first", "single owner per table", "outbox for post-commit propagation"], ["forbidden-dependency tests pass", "no cross-module table writer", "failure isolation is tested"], [E["matrix"], E["backlog"]], "P0_TO_P3", "delivery_team"),
        _risk("R-023", "clone evidence is treated as live operational truth", "HIGH", "evidence", ["integration_migration", "reporting_documents"], "NeginPakhsh_WebDev snapshot lag or divergence is ignored during migration/cutover decisions", ["snapshot timestamp/watermark", "runtime package hash", "delta reconciliation from authorized source"], ["source freshness is measured and accepted", "cutover uses authorized current snapshot and delta plan", "stale clone is never labeled live"], [E["drift"], E["migration"]], "P0_AND_P6", "migration_reviewer"),
        _risk("R-024", "current UI session is generalized to all roles and workflows", "MEDIUM", "evidence", ["identity_authorization", "reporting_documents"], "four open forms or current disabled buttons are assumed to represent all users/configurations", ["menu/form catalog", "aggregate authorization matrix", "role UAT", "session evidence separated from package evidence"], ["role/context test matrix covers allowed and denied paths", "session-only observations are labeled"], [E["matrix"], E["drift"]], "P1_TO_P6", "security_administrator"),
        _risk("R-025", "unknown reconciliation is accepted to meet schedule", "CRITICAL", "governance", ["integration_migration", "accounting", "inventory", "receivables_treasury", "procurement_payables"], "blocking_unknown is waived without evidence, owner, reason and approval", ["machine acceptance gate", "separate migration operator/reviewer", "immutable approval audit"], ["blocking_unknown count is zero", "every explained difference has signed evidence", "self-approval negative test passes"], [E["migration"], E["roles"]], "P1_TO_P6", "migration_reviewer"),
        _risk("R-026", "release claim is made from code existence alone", "MEDIUM", "quality", ["platform", "reporting_documents", "integration_migration"], "tests or files exist but authenticated user workflow, restore, performance and reconciliation were not proven", ["fresh evidence manifest", "authenticated UAT", "restore/performance/security gates"], ["all Definition of Done gates have current readback evidence", "pilot and production flags remain false until signed"], [E["matrix"], E["backlog"]], "EVERY_RELEASE", "migration_reviewer"),
        _risk("R-027", "POS receipt replication is ported as one opaque multi-domain command", "CRITICAL", "transactionality", ["sales", "receivables_treasury", "inventory", "accounting", "integration_migration"], "a retry or partial failure across the observed 66 dependencies and 17 mutation candidates duplicates or loses order, payment, voucher, credit or crosswalk effects", ["source-watermarked replication batch", "per-receipt command_id and immutable source-target crosswalk", "single local transaction plus outbox", "per-item quarantine and count/amount/effect reconciliation", "target-local acceptance state only; no Varanegar acknowledgement or write-back"], ["same batch/receipt replay creates zero duplicates", "fault injection at every stage converges or quarantines explicitly", "source-target receipt counts, currencies, amounts and ledger effects reconcile", "no blocking_unknown receipt becomes target-accepted", "source Varanegar remains unchanged"], [E["extension_semantics"], E["pos_transitive_graph"]], "P0_BEFORE_POS_COMMAND_AND_P4", "financial_controller"),
        _risk("R-028", "legacy MAX(Id)+1 identifier allocation is copied into pricing rules", "HIGH", "concurrency", ["pricing_rules", "sales", "platform"], "concurrent linear-discount creation allocates the same identifier or overwrites a rule", ["database identity/sequence or UUID", "unique constraint", "optimistic concurrency and idempotency key", "parallel creation test"], ["target code contains no MAX(Id)+1 allocator", "parallel writers produce unique stable identities", "duplicate-key retry returns one original result", "pricing rule version/crosswalk remains deterministic"], [E["extension_gap_paths"]], "P0_BEFORE_PRICING_COMMAND", "delivery_team"),
        _risk("R-029", "POS snapshot has no durable source version and relies on untrusted relationships", "HIGH", "migration_integrity", ["sales", "inventory", "receivables_treasury", "integration_migration"], "PSessionId-only extraction replays changed data or silently loses orphan order, payment, return or credit relationships because no rowversion signal exists and seven of ten in-scope foreign keys are not trusted", ["immutable snapshot id and extraction watermark", "payload hash per source record and receipt", "missing-parent and duplicate-key quarantine", "count and amount control totals", "immutable source-target crosswalk"], ["repeat extraction of one snapshot produces identical hashes", "changed payload under the same source key is rejected as conflict", "all missing parents are explained or blocking", "source/target counts and amounts reconcile"], [E["pos_source_model"]], "P0_BEFORE_POS_IMPORT", "migration_reviewer"),
        _risk("R-030", "empty POS clone data is generalized to operational behavior", "HIGH", "evidence", ["sales", "reporting_documents", "integration_migration"], "the clone's twelve empty POS tables are treated as proof of no usage, low volume or valid production distributions", ["label clone schema evidence separately from operational data evidence", "authorized aggregate-only operational snapshot before sizing or UAT", "freshness and coverage checks"], ["current authorized source window has aggregate counts and control totals", "performance fixtures reflect accepted operational percentiles", "no zero-row clone table is labeled unused without independent evidence"], [E["pos_source_model"]], "P0_BEFORE_POS_SCOPE_OR_SIZING", "migration_reviewer", "CONFIRMED_CLONE_LIMIT_NOT_OPERATIONAL_USAGE"),
        _risk("R-031", "static or name-matched report evidence is treated as result parity", "HIGH", "functional_parity", ["reporting_documents", "sales", "inventory", "receivables_treasury", "integration_migration"], "a method signal, unique SQL name candidate or parameter/dependency footprint is implemented as the authoritative report although effective scope, exact SQL binding, result shape and owner-approved values are unproven", ["exact query identity and parameter binding", "frozen source snapshot with provenance", "owner-approved Golden inputs and aggregate outputs", "scope, paging, date, null and rounding parity tests", "query and command boundaries kept separate"], ["all twenty report contracts have approved Golden values", "row counts, totals, filters, scope and business dates reconcile on the accepted snapshot", "result parity is recorded per report and no name candidate alone grants readiness"], [E["report_evidence_gaps"], E["report_generic_semantics"], E["report_target_contracts"]], "P1_BEFORE_REPORT_IMPLEMENTATION_OR_PILOT", "migration_reviewer", "CONFIRMED_STATIC_EVIDENCE_LIMIT"),
        _risk("R-032", "writable treasury views and trigger side effects are flattened into CRUD tables", "CRITICAL", "financial_integrity", ["receivables_treasury", "accounting", "integration_migration"], "RCheque or RCashDraft is migrated as an independent table and the INSTEAD OF bridge, underlying accounting row, receipt amount, log, audit, replication or guard effect is omitted or duplicated", ["explicit aggregate and table ownership", "command-owned transaction with outbox", "view-trigger effect inventory", "source-target crosswalk", "fault injection and financial reconciliation", "no UI direct SQL"], ["every legacy trigger effect is retained, replaced or explicitly retired with owner approval", "cash/cheque/draft, receipt, log and accounting effects reconcile on Golden snapshots", "retry and crash tests produce one business outcome", "target UI has no SQL or transaction ownership"], [E["treasury_command_paths"], E["treasury_source_model"], E["treasury_trigger_semantics"], E["treasury_view_lineage"], E["treasury_target_contracts"], E["treasury_validation_contracts"], E["treasury_trigger_transitive_graph"], E["treasury_web_field_contracts"], E["side_effects"]], "P0_BEFORE_TREASURY_COMMAND_AND_P4", "financial_controller", "CONFIRMED_STATIC_UI_AND_CLONE_CATALOG_EVIDENCE"),
        _risk("R-033", "order-to-sale orchestration and trigger cascade are flattened into screen CRUD", "CRITICAL", "transactionality", ["sales", "inventory", "receivables_treasury", "accounting", "integration_migration"], "the web port saves order, sale conversion or return header/lines directly and omits or duplicates credit, stock, reservation, price, prize, batch, payment, history or accounting effects observed across layered handlers, procedures and the bounded trigger graph", ["one named idempotent versioned command per workflow", "explicit transaction owner and post-commit outbox", "retain-replace-retire inventory for every trigger and SQL effect", "source-target crosswalk and control-total reconciliation", "fault injection across number/header/item/batch/pricing/trigger/outbox stages", "source Varanegar remains read-only"], ["all 73 root triggers and truncated frontier have reviewed dispositions before command enablement", "order, conversion, return, stock, credit, price, prize, payment and history effects reconcile on approved Golden snapshots", "all 48 linked synthetic Golden cases execute on the isolated target harness", "same command replay and injected faults converge to one accepted outcome", "no web UI or integration owns direct table writes"], [E["order_sale_command_contracts"], E["order_sale_dependency_graph"], E["order_sale_sql_semantics"], E["order_sale_source_model"], E["order_sale_trigger_transitive_graph"], E["order_sale_web_screens"], E["side_effects"]], "P0_BEFORE_ORDER_SALE_RETURN_COMMANDS_AND_P2", "financial_controller", "CONFIRMED_STATIC_UI_IL_AND_CLONE_CATALOG_EVIDENCE"),
        _risk("R-034", "stock voucher transitions and distribution-to-exit cascade are flattened into CRUD", "CRITICAL", "transactionality", ["inventory", "distribution", "sales", "accounting", "integration_migration"], "the web port treats stock draft, confirm/unconfirm, return and distribution exit issue/merge/remove as direct row edits and omits or duplicates cardex, on-hand, history, voucher, sale and exit effects", ["separate idempotent versioned commands for draft, confirm/unconfirm, return and exit transitions", "single application transaction owner plus outbox", "retain-replace-retire disposition for every SQL and trigger effect", "cardex/on-hand/source-return and distribution-exit reconciliation", "fault injection at every declared transition"], ["all 87 root triggers and truncated frontier have reviewed dispositions", "all 16 direct mutation targets and 38 bounded transitive write targets are owned or explicitly retired", "stock draft/confirm/unconfirm/return and distribution create/issue/merge/remove Golden cases pass", "same command replay creates one accepted outcome", "no web UI or integration directly writes legacy-shaped tables"], [E["stock_voucher_command_contract"], E["distribution_sql_semantics"], E["distribution_source_model"], E["distribution_trigger_transitive_graph"], E["side_effects"]], "P0_BEFORE_STOCK_OR_DISTRIBUTION_COMMANDS_AND_P3", "financial_controller", "CONFIRMED_STATIC_UI_IL_AND_CLONE_CATALOG_EVIDENCE"),
        _risk("R-035", "supplier invoice relation guard is bypassed by copied trigger toggling", "CRITICAL", "financial_integrity", ["procurement_payables", "inventory", "accounting", "integration_migration"], "the target copies legacy enable/disable-trigger and inline-delete behavior around supplier-invoice to stock-voucher relations, bypassing invariants or leaving the guard disabled after a fault", ["never disable target constraints or triggers to perform a business command", "explicit supplier-invoice/stock-voucher aggregate invariant", "versioned idempotent save/delete/return commands", "privileged compensating workflow with reason and immutable audit", "fault injection and supplier/stock/accounting reconciliation"], ["all four root triggers and 29 bounded transitive write targets have retain-replace-retire disposition", "save/delete/return failures cannot leave a guard disabled", "supplier invoice, voucher relation, stock, toll and supplier balance Golden cases reconcile", "no application role has ALTER TRIGGER permission", "same delete or return command replay produces one accepted outcome"], [E["supplier_invoice_command_contract"], E["supplier_invoice_source_model"], E["supplier_invoice_trigger_transitive_graph"], E["side_effects"]], "P0_BEFORE_SUPPLIER_INVOICE_COMMANDS_AND_P5", "financial_controller", "CONFIRMED_STATIC_UI_IL_AND_CLONE_CATALOG_EVIDENCE"),
        _risk("R-036", "generated accounting vouchers are flattened into manual ledger CRUD", "CRITICAL", "financial_integrity", ["accounting", "sales", "inventory", "procurement_payables", "receivables_treasury", "integration_migration"], "the target writes accounting rows manually and loses or duplicates source-document provenance, generation rule version, fiscal/date/DC scope and generate/confirm/delete/transfer transitions", ["separate generated and manual voucher command boundaries", "immutable source-document and rule-version provenance", "idempotent versioned generate/confirm/delete/transfer commands", "posting outbox and ledger reconciliation", "configuration-effective-value explanation and segregation of duties"], ["exact handler-to-SQL bindings replace name-only candidates", "source document, voucher header/items and ledger balance reconcile on approved Golden snapshots", "retry and every injected fault converge to one accepted posting outcome", "manual voucher role cannot impersonate automated generation", "delete/transfer preserve immutable audit and reversal provenance"], [E["accounting_voucher_entrypoints"], E["accounting_voucher_sql_candidates"], E["side_effects"], E["roles"]], "P0_BEFORE_ACCOUNTING_COMMANDS_AND_P5", "financial_controller", "CONFIRMED_STATIC_UI_CALLS_WITH_NAME_ONLY_CLONE_SQL_CANDIDATES"),
        _risk("R-037", "customer and goods masters are flattened or made writable before child and permission contracts", "HIGH", "functional_parity", ["master_data", "sales", "inventory", "pricing_rules", "integration_migration"], "the first web slice exposes save/delete from incomplete static labels or unexecuted Golden contracts, drops customer parent/DL/status scope or flattens goods barcode, supplier, package, batch and DC relations", ["read-only list/detail first", "owner-reviewed field/layout/lookup contract", "structured child relation ownership", "deny-first permission and headquarters scope", "versioned idempotent save with separate guarded delete/merge", "crosswalk and dependency reconciliation"], ["all 130 input semantics and 62 missing-label candidates are dispositioned", "all 64 customer and goods save/delete/duplicate/in-use/replication Golden cases execute", "effective permissions and configuration cases pass", "barcode/supplier/package/batch/DC counts and crosswalks reconcile", "no write screen is enabled from static metadata alone"], [E["customer_goods_command_contracts"], E["customer_goods_web_screens"], E["migration"], E["roles"]], "P1_BEFORE_MASTER_DATA_WRITE_SCREEN", "master_data_steward", "CONFIRMED_STATIC_UI_IL_WITH_DESIGNED_UNEXECUTED_GOLDEN_AND_LABEL_GAPS"),
        _risk("R-038", "supplier master is collapsed into party CRUD and bypasses payment, accounting, contact or cardex guards", "HIGH", "functional_parity", ["master_data", "procurement_payables", "accounting", "integration_migration"], "supplier save/delete is implemented as shared party fields and loses IsUsedInPay, accounting group, contact/DL, status, attachment, after-save or supplier-cardex dependencies", ["separate supplier role/aggregate boundary", "read-only list/detail first", "owner-reviewed field/lookup/relation contract", "deny-first permission and payment-usage delete guard", "versioned idempotent save and retained/inactivated delete policy", "supplier-cardex and accounting reconciliation"], ["all 12 web input and 9 static rule signals are dispositioned", "supplier save/delete authorization, duplicate, in-use, retry and fault Golden cases execute", "payment and accounting group dependencies reconcile", "contact/DL and cardex provenance are preserved", "no write is enabled from static IL or labels alone"], [E["supplier_master_command_contract"], E["supplier_master_web_screen"], E["migration"], E["roles"]], "P1_BEFORE_SUPPLIER_MASTER_WRITE_SCREEN", "master_data_steward", "CONFIRMED_STATIC_UI_IL_WITH_DESIGNED_UNEXECUTED_GOLDEN_CASES"),
        _risk("R-039", "operational year, fiscal year, DC, sale office, stock and stock-accounting context are collapsed", "HIGH", "context_integrity", ["organization_context", "configuration", "inventory", "accounting", "integration_migration"], "the target models one branch/year/warehouse field, conflates operational and fiscal year, or copies incompatible sequential and bit-flag stock-type encodings, causing wrong scope, price method, posting or stock behavior", ["typed versioned operational context", "separate operational and fiscal year identities", "explicit DC-sale-office-stock compatibility table", "reviewed stock-type crosswalk and five-flag contract", "versioned stock-accounting price method", "closed/in-use context guards and reconciliation"], ["all 26 screen inputs and 9 static rule signals are dispositioned", "DC=0/1 and valid office/stock combinations are owner-approved", "stock-type encoding and GNR.HasStockType behavior reconcile", "operational/fiscal boundary and closed-year Golden cases pass", "stock accounting price method and cardex/posting outputs reconcile"], [E["operational_context_command_contracts"], E["operational_context_web_screens"], E["migration"], E["matrix"]], "P0_BEFORE_CONTEXT_OR_STOCK_CONFIGURATION_WRITE", "configuration_publisher", "CONFIRMED_STATIC_UI_IL_AND_DOMAIN_EVIDENCE_WITH_DESIGNED_UNEXECUTED_GOLDEN_CASES"),
        _risk("R-040", "contextual price and discount precedence are flattened into mutable nullable rule rows", "HIGH", "pricing_integrity", ["pricing_rules", "sales", "configuration", "accounting", "integration_migration"], "the target loses version/effective window, priority, qualification, close/history, condition/arrangement, prize/package or explain semantics and silently selects a different price or discount", ["immutable versioned rule publication", "explicit scope relation tables", "deterministic priority and overlap policy", "effective-date and close/inactive transitions", "calculation/rounding and explain trace", "idempotent copy/save/close/delete commands"], ["all 40 inputs and 14 static rule signals are dispositioned", "qualification and priority outcomes reconcile on owner-approved snapshots", "overlap, boundary-date, rounding, currency, batch and package Golden cases pass", "copy/close/delete/retry/fault tests preserve history", "every applied price/discount/prize returns a stable explain trace"], [E["pricing_rule_command_contracts"], E["pricing_rule_web_screens"], E["migration"], E["matrix"]], "P0_BEFORE_PRICING_WRITE_AND_P2", "configuration_publisher", "CONFIRMED_STATIC_UI_IL_AND_DOMAIN_EVIDENCE_WITH_DESIGNED_UNEXECUTED_GOLDEN_CASES"),
        _risk("R-041", "sales, purchase, financial and petty-cash final dates are flattened into one mutable setting", "CRITICAL", "temporal_financial_integrity", ["organization_context", "configuration", "sales", "inventory", "receivables_treasury", "procurement_payables", "accounting", "integration_migration"], "the target stores one close date or edits it directly, conflating four independently validated DC/fiscal-year boundaries, open versus final dates, and reopen behavior; clone evidence also shows missing mandatory first-create fields, unscoped financial reopen deletion and cross-year distribution rewrites", ["four explicit versioned idempotent final-date commands", "DC and fiscal-year scope", "separate open/final/reopen semantics", "pre-commit affected-consumer and blast-radius validation", "atomic accepted version plus immutable audit/outbox", "no silent operational-document rewrite", "fiscal-year-scoped reopen", "cross-module date-boundary reconciliation"], ["all eleven FD findings have explicit retain-replace-retire disposition", "first-create succeeds atomically with mandatory actor provenance", "no reopen effect escapes the selected DC and fiscal year", "stale, overlap, backwards-date, reopen, retry and fault-injection cases pass", "sales, purchase, treasury, petty-cash, inventory and accounting boundary outcomes reconcile", "authenticated owner UAT approves each of four commands", "source Varanegar remains read-only"], [E["final_date_boundary"], E["final_date_diagnostic"], E["migration"], E["matrix"]], "P0_BEFORE_FINAL_DATE_CLOSE_OR_REOPEN_COMMAND", "financial_controller", "CONFIRMED_LAYERED_STATIC_COMMAND_PATH_AND_READ_ONLY_CLONE_DIAGNOSTIC_WITH_UNPROVEN_TARGET_RUNTIME_PARITY"),
        _risk("R-042", "received-cheque approval loses Pay or legal-routing event semantics", "CRITICAL", "financial_integrity", ["receivables_treasury", "accounting", "integration_migration"], "the target treats TblCheque.PayId as the approved authority or repeats the deployed confirmation omission that stores LegalType on a draft parent but not on the immutable history event", ["separate draft Pay selection from approved history PayRef", "typed PERSONNEL/LEGAL_DEPARTMENT/UNKNOWN_SOURCE legal route", "single transaction for parent, event, accounting and projection", "never impute legal route from PersonnelId", "source-version contract and parent-versus-history reconciliation"], ["all eight master gaps resolve through approved history without synthetic links", "35 unknown legal routes remain explicitly unknown", "type 1/2 command tests persist the selected route in history", "retry/fault/undo tests preserve one complete event and accounting outcome", "no parent/history LegalType drift on approved target commands"], [E["received_cheque_projection_legal_diagnostic"], E["migration"], E["matrix"]], "P4", "financial_controller", "CONFIRMED_READ_ONLY_CLONE_AND_DEPLOYED_SQL_PATH_WITH_RUNTIME_FREQUENCY_UNPROVEN"),
        _risk("R-043", "voucher status event branch diverges from the deployed current pointer", "CRITICAL", "financial_integrity", ["accounting", "integration_migration", "platform"], "the target silently selects MAX(history), discards 14946 detached events, or repeats a status-change failure path whose CATCH does not explicitly roll back event/pointer work", ["typed CURRENT_POINTER_HISTORY_FORK quarantine", "preserve deployed current projection plus UNKNOWN_OUTCOME branch", "single idempotent event-pointer-numbering transaction", "compare-and-swap expected current event", "transaction-count and rollback guard in every catch"], ["all 1094 forks have accountant-approved disposition", "no pointer is replaced by MAX and no trailing event is discarded automatically", "failure between event insert and pointer update rolls back fully with transaction count zero", "numbering and status read models reconcile on approved snapshots", "retry produces one accepted event and pointer"], [E["voucher_status_pointer_diagnostic"], E["migration"], E["matrix"]], "P5", "financial_controller", "CONFIRMED_READ_ONLY_CLONE_AND_DEPLOYED_SQL_WITH_HISTORICAL_CAUSATION_UNPROVEN"),
        _risk("R-044", "an empty numbered draft voucher is treated as posted or silently repaired", "HIGH", "financial_integrity", ["accounting", "integration_migration"], "the target treats IsDeleted=0 as posted, synthesizes balancing lines for the one empty draft shell, or silently reuses its assigned source number", ["explicit DRAFT_EMPTY_NUMBERED_SHELL state", "ledger requires at least two balanced lines", "posted-number assignment only after validation", "preserve source number as provenance", "accountant disposition before reuse"], ["the shell remains outside ledger debit/credit and posting reports", "no synthetic line is created", "source-number policy is owner-approved", "empty/unbalanced/retry/fault cases cannot receive a posted target number", "draft abandonment and number release are audited commands"], [E["empty_voucher_shell_diagnostic"], E["migration"], E["matrix"]], "P5", "financial_controller", "CONFIRMED_READ_ONLY_CLONE_AND_DEPLOYED_SQL_WITH_HISTORICAL_CAUSATION_UNPROVEN"),
        _risk("R-045", "NGT mobile return replication result is lost or duplicated across the BackOffice crosswalk boundary", "CRITICAL", "integration_financial_integrity", ["sales", "inventory", "distribution", "integration_migration"], "the target flattens two different unresolved states, recreates the return whose TourHistory result exists but current target is missing, or commits an official return before durable idempotent crosswalk writeback", ["separate PENDING_OR_UNATTEMPTED from HISTORICAL_RESULT_CURRENT_TARGET_MISSING", "preserve NGT UUID, FRU integer identity, TourHistory result and BackOffice refs independently", "atomic result receipt/outbox and idempotent crosswalk writeback", "two-way reconciliation before retry", "no automatic official document reconstruction"], ["the one historical-result/missing-target row has owner-approved disposition", "the one no-result row remains non-official until an authoritative command result exists", "commit-before-writeback fault injection converges to one result and one crosswalk", "NGT/FRU/SLE identity joins are typed and non-ambiguous", "quantity/net and inventory/credit consequences reconcile before promotion"], [E["ngt_return_crosswalk_diagnostic"], E["migration"], E["matrix"]], "P2_AND_P6", "migration_reviewer", "CONFIRMED_READ_ONLY_CLONE_TOUR_HISTORY_AND_DEPLOYED_SQL_WITH_HISTORICAL_TARGET_DISAPPEARANCE_CAUSE_UNPROVEN"),
        _risk("R-046", "supplier-return source and toll validation differs by command path", "CRITICAL", "financial_integrity", ["procurement_payables", "inventory", "accounting", "integration_migration"], "the target trusts or copies a validator that inner-joins return goods to optional source-invoice goods and ignores unmatched goods, misclassifies seven inventory-voucher-authoritative items as corruption, or drops twenty stale explicit toll refs that the deployed compatibility view uniquely resolves by same-header TollRef; the desktop path blocks a non-empty message before commit, while the SDSNET SQL save omits validation on UPDATE and on INSERT neither captures the validator return code nor raises its output before commit", ["validate the full union of source and return goods before any write", "treat the linked type-55 inventory voucher as item/quantity authority and the supplier invoice as optional source/pricing provenance", "preserve nonzero historical price/amount without repricing from a prior invoice", "preserve explicit toll ref provenance and resolve only through unique same-header TollRef compatibility", "one versioned atomic return command with blocking domain errors", "validate INSERT and UPDATE under the same invariant", "reconcile type-55 stock exit, supplier balance, tolls and accounting effects"], ["all seven source-item-absent groups exactly match their type-55 exit and retain nonzero price/amount provenance", "all twenty stale toll refs resolve uniquely with zero omitted or ambiguous compatibility rows", "unmatched, over-quantity, prize-quantity and full-return amount cases fail before persistence", "INSERT and UPDATE execute identical blocking validation", "validator return/error propagation and rollback are proven by fault injection", "desktop and SDSNET parity differences have explicit retain/replace/retire disposition", "return header/items, type-55 voucher, supplier balance and accounting voucher reconcile after retry and reversal"], [E["supplier_receipt_component_diagnostic"], E["migration"], E["matrix"]], "P3_AND_P5", "financial_controller", "CONFIRMED_READ_ONLY_CLONE_AGGREGATES_DEPLOYED_SQL_AND_STATIC_DESKTOP_IL_WITH_NO_MUTATION_EXECUTED"),
        _risk("R-047", "mutable voucher-issuance policy cannot explain persisted accounting batches", "CRITICAL", "financial_integrity", ["accounting", "configuration", "integration_migration", "platform"], "the target replays or migrates historical source groups using the current FiscalYear.ExternalVoucherIssueMode and silently splits or merges official accounting batches; in the clone year 1405 is currently mode 1 (one source per batch), yet 366 of 382 persisted headers contain multiple source groups and the three-month window has 27,177 source groups in only 204 headers. The deployed desktop path is atomic only because its Business DataContext supplies the transaction; dbo.usp_DoExternalVoucher owns no transaction for a direct or nonstandard caller. Retained line cardinality also matches a legacy-equivalent net grouping grain exactly at 1,287,874 lines, while replay under the current ReferenceNo/debit-side grain yields 1,424,039 lines", ["immutable effective-dated voucher-issuance policy versions", "persist issue mode, DC grouping, headquarters grouping, sale-office grouping, fiscal mapping, line-grouping grain and creator-rule version on every batch", "server-owned transaction covering PreVoucher, ExternalVoucherHeader, ExternalVoucher and relation writes", "idempotent issuance command receipt plus exact semantic unique constraints", "preserve historical batch/source/line lineage without replay under current settings", "owner-approved golden cases for all eleven active creators and all historically unobserved rule branches"], ["all 382 year-1405 headers and 46,519 source groups retain their original grouping provenance", "the three-month 204 headers and 27,177 source groups reconcile without reconstruction from current mode 1", "all 1,287,874 retained ExternalVoucher lines retain their legacy-equivalent grouping provenance and are not regenerated as 1,424,039 current-grain lines", "policy change creates a new immutable version and never changes historical explain output", "desktop, API and integration callers use the same server-owned transaction", "fault injection after every staging/header/line/relation phase rolls back fully", "parallel retry converges to one batch and all eleven creator Golden cases plus 48 unobserved rule-branch cases reconcile debit, credit, dimensions and source lineage"], [E["voucher_creation_policy"], E["migration"], E["matrix"]], "P5_BEFORE_ACCOUNTING_ISSUANCE", "financial_controller", "CONFIRMED_HASH_PINNED_DESKTOP_IL_READ_ONLY_SQL_AND_FULL_CLONE_AGGREGATES_WITH_NO_MUTATION_EXECUTED"),
        _risk("R-048", "accounting transfer validation can commit pre-validation cleanup", "HIGH", "transactionality", ["accounting", "platform"], "the deployed transfer procedure deletes selected stale SetVoucherNo rows before calling its business validator; validation failures are returned as ordinary result rows and RETURN rather than raised exceptions, so the standard Business path can commit that cleanup even though transfer was rejected. The clone currently has zero orphan or duplicate SetVoucherNo rows, making this a reachable code-path risk rather than an observed retained inconsistency", ["make ValidateAccountingTransfer a read-only query", "move all numbering cleanup after validation PASS and inside the transfer command", "treat business validation failure and exception as explicit non-committing outcomes", "server-owned transaction and idempotency receipt", "row-version and semantic uniqueness guard for one active voucher and one number crosswalk per batch"], ["validation-failure tests leave every table byte-for-byte unchanged including stale number-crosswalk fixtures", "fault injection after each Voucher, VoucherItem, status, edit-log and number write rolls back fully", "two parallel transfers converge to one active Voucher and one SetVoucherNo row", "full-clone parity retains 197,518 one-to-one header/voucher/number mappings and the three-month 204 mappings reconcile"], [E["voucher_creation_policy"], E["matrix"]], "P5_BEFORE_ACCOUNTING_TRANSFER", "financial_controller", "CONFIRMED_HASH_PINNED_DESKTOP_IL_AND_STATIC_SQL_WITH_CLEAN_READ_ONLY_SNAPSHOT"),
        _risk("R-049", "accounting issuance approval and transfer lack server-enforced action authorization", "CRITICAL", "authorization", ["accounting", "identity_authorization", "platform"], "a principal who can reach FormExternalVoucher may be able to issue, confirm, unconfirm or transfer accounting batches without distinct action authorization or resource-scope enforcement: the base toolbar permission gate covers new/edit/delete/print/export, the form forces confirm/unconfirm visible, custom save and transfer controls have no permission references, all command methods have zero HasPersmission calls, and all four operational procedures have zero access/action authorization references. The issue procedure validates only that DCs and the user exist and that source finality is closed; lifecycle procedures accept header IDs, and delete accepts no user parameter", ["server-side authorization for issue, confirm, unconfirm, delete and transfer as separate actions", "deny-first fiscal-year, DC, external-voucher-type and header resource scope", "segregation-of-duties policy preventing unauthorized self-approval or self-posting", "derive actor from authenticated command context rather than accepting an arbitrary existing user id", "immutable authorization decision audit with policy version and scoped resource set", "UI visibility only as presentation, never as the security boundary"], ["view-only principal is denied every mutation by the server", "issuer-only principal cannot confirm or transfer unless explicitly granted", "forged cross-DC, cross-year, cross-type and unscoped header identifiers are denied even through direct API calls", "delete records the authenticated actor and reason", "positive and negative role-matrix tests cover all five actions and resource scopes", "screen access cannot substitute for command authorization in architecture tests"], [E["voucher_creation_policy"], E["roles"], E["matrix"]], "P0_AND_P5_BEFORE_ANY_ACCOUNTING_COMMAND", "security_administrator", "CONFIRMED_HASH_PINNED_UI_BASE_TEMPLATE_AND_BUSINESS_IL_PLUS_STATIC_SQL_ABSENCE_WITH_SCREEN_ACCESS_CAVEAT"),
        _risk("R-050", "accounting issuance finality can ignore missing purchase stock-DC operation rows", "CRITICAL", "temporal_financial_integrity", ["accounting", "inventory", "procurement_payables", "configuration"], "the deployed issue procedure computes purchase finality as MIN(DefeniteDate) over existing ICA operation-date rows joined to StockDC, without proving that every applicable StockDC has a row. In each active-DC scope for years 1403-1405 the stocked DC is partially covered; the current 1405 shape has ten StockDCs but only eight operation rows, so two missing rows are invisible to MIN. The procedure also exempts OperationId 5; two payroll types are configured but have zero retained headers, so the intended exemption has no historical parity evidence", ["fail-closed finality decision for every selected external type and DC", "explicit applicable StockDC set with complete-row anti-join before MIN", "versioned source-system finality policy including approved exemptions", "store the evaluated stock-DC set, dates and policy version on the issuance decision", "owner-approved payroll exemption and negative cases", "no persistent write before finality PASS"], ["a purchase issue is denied when any applicable StockDC lacks its year operation row", "mixed finalized and missing StockDC fixtures cannot pass through MIN", "all selected type-by-DC combinations produce explicit explainable decisions", "the two OperationId-5 configured types have owner-approved exempt and non-exempt Golden cases", "finality rejection remains mutation-free and retry-safe", "inventory/purchase/accounting boundaries reconcile after finality PASS"], [E["voucher_creation_policy"], E["final_date_boundary"], E["final_date_diagnostic"], E["matrix"]], "P0_AND_P5_BEFORE_ACCOUNTING_ISSUANCE", "financial_controller", "CONFIRMED_DEPLOYED_SQL_AND_READ_ONLY_COVERAGE_WITH_NO_MODERN_PURCHASE_RUNTIME_EXAMPLE"),
        _risk("R-051", "dormant invalid voucher-type configuration is exposed as an active ERP capability", "HIGH", "configuration_integrity", ["accounting", "configuration", "integration_migration"], "the target treats every ExternalVoucherType row as an issueable capability. The deployed year-1405 validator classifies only 45 of 65 configured types as structural candidates; 20 fail because they have no effective Article and 13 of those also have no creator view. None of the 20 has retained, recent or modern-header activity, so they are dormant or incomplete rather than proven active behavior. Seventy-one distinct predicates remain runtime-uncompiled because creator views were deliberately not executed", ["explicit CONFIGURED_DORMANT, STRUCTURALLY_VALID, OBSERVED and OWNER_APPROVED capability states", "fail-closed activation gate using the full deployed structural contract", "isolated non-operational predicate compilation harness", "owner disposition for every dormant type without automatic deletion", "versioned type, creator, article and comment configuration", "UI lists only approved capabilities while preserving source provenance"], ["all 45 structural candidates pass view, field, ledger, article, comment and predicate checks in the isolated harness", "all 20 invalid configured types have owner-approved dormant, repair or retire disposition", "the 13 missing-view and seven additional no-article types cannot be selected for target issuance", "zero invalid type is silently activated from table presence", "all 71 predicate branches compile and have typed Golden cases before activation", "historical migration preserves dormant configuration provenance without creating commands"], [E["voucher_creation_policy"], E["migration"], E["matrix"]], "P5_BEFORE_ACCOUNTING_CAPABILITY_ACTIVATION", "configuration_publisher", "CONFIRMED_DEPLOYED_VALIDATOR_SQL_AND_READ_ONLY_CATALOG_WITH_PREDICATE_RUNTIME_UNEXECUTED"),
        _risk("R-052", "dirty or inconsistent creator-view state becomes persistent financial staging", "CRITICAL", "financial_snapshot_integrity", ["accounting", "sales", "inventory", "procurement_payables", "receivables_treasury", "platform"], "dbo.usp_DoPreVoucher reads each configured creator view AS vw WITH(NOLOCK) and persists the result to PreVoucher inside the outer issue transaction. The provider uses the parameterless BeginTransaction overload. Although the read-only clone has READ_COMMITTED_SNAPSHOT and SNAPSHOT isolation enabled, NOLOCK bypasses committed-read protection. The four recent creators recursively depend on 54 base tables; only six expose rowversion and none is temporal or change-tracked, so no portable cross-table watermark exists. No dirty-read incident was asserted because creator views and concurrent writes were deliberately not executed", ["remove NOLOCK from financial source reads", "explicit committed snapshot or repeatable source-version boundary", "capture source watermark and rule/policy version with the issuance decision", "idempotent source-reference uniqueness", "post-stage source-count and amount reconciliation before posting", "concurrent writer and rollback fault-injection harness on isolated fixtures"], ["uncommitted source rows never create persistent staging", "row movement or rollback cannot produce missing or duplicate financial effects", "same source watermark and rule version reproduce the same staged count and amount", "concurrent issue attempts converge to one source-reference outcome", "failure before confirmation leaves no staged/header/journal residue", "all active creator Golden cases reconcile source, staging, external voucher and journal"], [E["voucher_creation_policy"], E["matrix"]], "P0_AND_P5_BEFORE_ACCOUNTING_ISSUANCE", "financial_controller", "CONFIRMED_HASH_PINNED_PROVIDER_IL_DEPLOYED_SQL_AND_READ_ONLY_DEPENDENCY_GRAPH_WITH_NO_RUNTIME_DIRTY_READ_INCIDENT_TEST"),
        _risk("R-053", "trusted voucher-rule configuration is executed as concatenated SQL", "CRITICAL", "configuration_code_execution", ["accounting", "configuration", "identity_authorization", "platform"], "dbo.usp_DoPreVoucher concatenates creator view, field, predicate, ledger and comment configuration into one executable SQL batch, while dbo.usp_DoExternalVoucherTypeValidation dynamically executes the configured view and predicate shape. The current aggregate scan of eleven fragment categories found zero obvious separator, comment, statement-keyword, quote or control-character values, but clean current values do not make executable configuration safe. Configuration write authority was not attributed, so this is a confirmed design boundary rather than a claim of a current exploit", ["replace executable SQL fragments with a typed versioned voucher-rule DSL", "allowlisted schema-bound creator projections", "strict identifier mapping and parameterized scalar values", "four-eyes publish for financially material rule versions", "immutable compiled-rule hash and source snapshot provenance", "deny direct production edits and audit every publish"], ["target issuance contains no concatenated executable configuration", "malformed and adversarial rule fixtures fail closed before any persistent write", "every approved rule compiles from typed nodes to a reviewed deterministic plan", "publisher and approver separation plus audit readback is enforced", "all 71 observed predicate shapes have owner-approved typed Golden cases", "rule rollback selects a prior immutable version without editing history"], [E["voucher_creation_policy"], E["roles"], E["matrix"]], "P0_AND_P5_BEFORE_RULE_PUBLISHING", "security_administrator", "CONFIRMED_DEPLOYED_DYNAMIC_SQL_DESIGN_WITH_CURRENT_SNAPSHOT_TOKEN_SCAN_CLEAN"),
        _risk("R-054", "legacy voucher-template transfer can partially publish executable accounting rules", "CRITICAL", "configuration_publish_atomicity", ["accounting", "configuration", "identity_authorization", "platform", "integration_migration"], "two no-parameter SQL procedures form a legacy template-transfer chain. The parent has four dynamic execution sites, drops and recreates creator views, inserts ExternalVoucherType, VoucherCreator and VoucherCreatorField, then calls a child with one dynamic execution site that inserts Article and ArticleComment. The child is no longer schema-compatible: its Article INSERT names VoucherCreatorId and ArticleCaption, which do not exist in the current 16-column table, and omits six current optional columns. It therefore fails when that dynamic statement is reached, after the parent can already have changed views and three rule tables. Neither procedure owns a transaction, TRY/CATCH, rollback, authorization check or version/publish audit signal; six enabled Article/ArticleComment triggers enlarge the side-effect boundary. The complete 62-assembly scan found no target-named form, caller or procedure literal, the named application SaveCommand is an unconditional validation failure, and the analyzer login cannot execute either procedure. Therefore administrative authority and frequency remain unknown; this is not attributed to an ordinary application user", ["replace template transfer with a server-owned versioned publish command", "stage and validate the complete creator/view/type/article/comment graph before activation", "single atomic swap or immutable version pointer after full validation", "publisher/approver separation and server authorization", "dry-run diff with hashes, dependency compilation and Golden financial effects", "idempotency key, rollback to prior immutable version and outbox/audit for propagation", "explicit disposition of six replication triggers"], ["failure at every view/type/creator/field/article/comment stage leaves the prior active rule version unchanged", "partial template data is never visible to issuance", "the current template column contract fails preflight before any parent mutation", "same template replay returns the original publish result", "all 71 predicate shapes compile and reconcile before activation", "direct SQL execution without approved publisher role is denied and audited", "replication-trigger effects are reconciled or replaced by an explicit outbox", "no deployed UI or integration path can bypass the publish command"], [E["voucher_creation_policy"], E["roles"], E["migration"], E["matrix"]], "P0_AND_P5_BEFORE_RULE_MIGRATION_OR_PUBLISH", "configuration_publisher", "CONFIRMED_STATIC_SQL_AND_FULL_HASH_PINNED_PACKAGE_ABSENCE_WITH_ADMIN_AUTHORITY_AND_RUNTIME_FREQUENCY_UNPROVEN"),
        _risk(
            "R-055",
            "replication watermark is mistaken for approved immutable accounting-rule provenance",
            "HIGH",
            "configuration_provenance",
            ["accounting", "configuration", "platform", "integration_migration"],
            "Article and ArticleComment triggers serialize row changes as executable SQL. The separate hash-pinned replication service has a durable binary outbox and applies each received script plus LastExecLog inside a transaction, so transport loss is not asserted. However the source log and receive receipt carry runtime actor/application and numeric ranges only: neither has an immutable rule/policy version, approval identity, content checksum or business-effect reconciliation. Service Run returns from Receive before looking up and dynamically executing a configured post-receive script, without one outer database transaction. The declared usp_ReplicationAfterReciveAll wrapper has no transaction or TRY/CATCH and calls transactional log sorting plus a non-transactional dynamic DBCC identity hook. The clone has zero configured identity targets, so no current identity mutation is asserted; the exact active configuration mapping, production configuration parity and effective service principal authority were deliberately not proven. Four Article updates occurred in the selected three-month window, while the clone retains zero ReplicationFile, ReplicationSend, tblLogRcv or tblLogSnd rows. A deployed clear procedure deletes receive receipts using LastExecLog/MAX and named service cleanup runs before receive/send, although the obfuscated helper-to-procedure binding is not proven; three separate center-provisioning procedures can also delete the main log. Therefore retained rows are not accepted as complete immutable history, and this snapshot cannot prove which approved rule version, if any, was applied downstream or whether any configured post-receive maintenance completed",
            ["publish immutable approved rule versions rather than arbitrary row SQL", "content-addressed outbox and inbox with manifest hash", "publisher and approver identities bound to the rule version", "idempotent apply-by-version command", "target-side compilation and financial-effect validation before activation", "source-target version and effect reconciliation independent of transport watermark", "separate idempotent post-receive maintenance receipt with retry and reconciliation", "least-privilege service identity with readback-tested effective permissions", "append-only externally anchored audit for rule publish and apply receipts"],
            ["every rule mutation has immutable version, publisher, approver and content hash", "transport receipt binds center, version and manifest checksum", "same version replay is a no-op with the original receipt", "tampered, out-of-order or unapproved payload is quarantined before activation", "all receiving centers reconcile active rule version and Golden financial effects", "LastExecLog alone is never accepted as publish approval or business parity", "failure after package receipt but before maintenance completion remains visible and retryable", "service principal can execute only the typed inbox and maintenance commands required by the target design", "retention or center provisioning cannot erase the authoritative rule-application audit"],
            [E["voucher_creation_policy"], E["rule_replication_transport"], E["roles"], E["matrix"]],
            "P0_AND_P5_BEFORE_RULE_REPLICATION_OR_MIGRATION",
            "configuration_publisher",
            "CONFIRMED_HASH_PINNED_REPLICATION_IL_STATIC_SQL_AND_READ_ONLY_CLONE_AGGREGATES_WITH_PRODUCTION_DELIVERY_UNPROVEN",
        ),
        _risk(
            "R-056",
            "executable replication packages can traverse an unauthenticated plaintext FTP branch",
            "CRITICAL",
            "integration_security",
            ["accounting", "configuration", "identity_authorization", "platform", "integration_migration"],
            "the replication receiver executes SQL carried in password-protected ZIP packages. Its named executor constructs SqlCommand, sets CommandText and calls ExecuteNonQuery; it does not call the named record validator, and both local and FTP outer paths reach an executor call before their later record-validation call, so a universal typed pre-execution allowlist is not proven. Site/DC and center lookups occur before unzip, but both helpers accept a string, concatenate it and call ExecuteScalar; query parameterization and the exact filename-to-lookup character-validation flow are not proven. A lookup is not cryptographic center binding. In the deployed hash-pinned FTP branch, VN.Replication constructs the default FluentFTP 32.4.3 client and sets credentials but never sets EncryptionMode, SslProtocols or certificate validation; the library default leaves encryption mode at enum None=0. The named package creation/extraction and send/receive flows contain zero content-hash, HMAC or signature calls. File-share transport is also supported and the active production mode/configuration was deliberately not read, so use of FTP at a specific center is not asserted. If the FTP branch is enabled, transport confidentiality and cryptographic sender/content authenticity are not evidenced before executable text SQL reaches the transactional receiver",
            ["replace arbitrary SQL packages with typed signed versioned domain payloads", "mutual TLS or a modern authenticated secure transport with strict certificate validation", "detached signature over canonical manifest and payload using a rotated asymmetric signing key", "verify signer, center, rule version, hash, expiry and replay nonce before unzip or SQL staging", "strict typed parsing plus parameterized site/center lookup", "least-privilege inbox executor with no arbitrary SQL capability", "tamper-evident audit and source-target reconciliation", "quarantine legacy FTP/file packages during migration"],
            ["plaintext FTP mode is disabled and cannot be re-enabled by configuration drift", "valid certificate chain and hostname are enforced in integration tests", "unsigned, altered, replayed, expired and wrong-center packages fail before database transaction or script execution", "malformed center/DC filename tokens fail before any lookup and lookup queries are parameterized", "receiver accepts only allowlisted typed operations, never arbitrary SQL text", "package signer and rule approver are independently attributable", "secret rotation and compromise drill complete without accepting old or forged packages", "all centers prove secure transport and content-authentication posture by readback"],
            [E["rule_replication_transport"], E["voucher_creation_policy"], E["roles"], E["matrix"]],
            "P0_BEFORE_ANY_REPLICATION_OR_RULE_MIGRATION",
            "security_administrator",
            "CONFIRMED_HASH_PINNED_REPLICATION_AND_FLUENTFTP_IL_WITH_ACTIVE_PRODUCTION_TRANSPORT_MODE_UNPROVEN",
        ),
    ]

    if ngt_authorization_effective is not None:
        risks.append(
            _risk(
                "R-057",
                "web command route authorization coverage is not mechanically complete",
                "CRITICAL",
                "authorization",
                ["identity_authorization", "platform", "integration_migration"],
                "the target copies implicit or mixed authorization conventions instead of requiring a policy for every route. In the deployed NGT metadata boundary, 784 HTTP/Route-attributed actions were counted; 60 have no NGT, standard, claims or anonymous declaration after local and direct shared-base inheritance, and 38 of those use a mutating HTTP verb. Startup.ConfigureWebApi registers attribute routes and constructs only validation and exception global filters, with no authorization-named constructor. Static analysis followed 43 async state machines and read direct/MoveNext bodies for all 60 gaps with zero body errors; none contains a named authorization-decision signal. Six only touch authorization/permission data and three only consume current-user identity context, neither of which is treated as enforcement. Obfuscated or delegated checks, host policy and external middleware were not excluded, so anonymous reachability and a production incident are not asserted. Separately, three normalized Resource/Action declarations have no permission row in any current ApplicationOwner, creating a fail-closed availability/configuration mismatch rather than an access grant",
                [
                    "generated route manifest with an explicit policy or reviewed anonymous disposition for every endpoint",
                    "server middleware that fails closed when a route policy is absent",
                    "separate typed permissions for every mutation and data scope",
                    "build-time Route-to-Permission registry validation in ApplicationOwner scope",
                    "manual/async guard inventory and retirement into centralized policy",
                    "immutable authorization decision audit with policy version",
                ],
                [
                    "all 784 attributed actions and every convention-only public action have one owner-approved policy disposition",
                    "all 60 declaration gaps are proven protected, explicitly anonymous, or removed",
                    "all 38 mutating declaration gaps fail unauthenticated and unauthorized integration tests before handler entry",
                    "the three permission-catalog mismatches are corrected or retired with owner approval",
                    "adding a route without policy fails CI and deployment",
                    "host, middleware, controller, method and manual checks produce one deterministic deny-first decision",
                ],
                [
                    E["ngt_authorization_effective"],
                    E["roles"],
                    E["matrix"],
                ],
                "P0_BEFORE_ANY_WEB_COMMAND",
                "security_administrator",
                "CONFIRMED_HASH_PINNED_STATIC_ATTRIBUTE_IL_AND_READ_ONLY_CLONE_CROSSCHECK_WITH_RUNTIME_REACHABILITY_UNPROVEN",
            )
        )

    if ngt_owner_scope_effective is not None:
        risks.append(
            _risk(
                "R-059",
                "functional permission scope relies on grant consistency instead of the owner-filtered repository path",
                "CRITICAL",
                "authorization_scope",
                ["identity_authorization", "platform", "integration_migration"],
                "the target assumes that passing ApplicationOwner/DataOwner/DataOwnerCenter into an authorization domain guarantees tenant filtering. Static deployed IL proves the web permission guard reads only OwnerKey and invokes a one-parameter AuthorizationDomain constructor that repeats the same key into all three owner positions. Direct and group permission methods call GetQuery, while the common repository GetQuery returns the raw DbSet; the distinct GetQueryByOwner path is the one that composes ApplicationOwnerId, DataOwnerId, DataOwnerCenterId and removed-data predicates. The selected authorization repositories do not override GetQuery. The current read-only clone is internally safer than the structure: all 324 effective Grant=1 rows have the same Application as their Principal and active group expansions have zero cross-Application permission mismatch. Therefore no current cross-tenant effective grant or incident is asserted. However one future/misconfigured cross-Application grant would be evaluated without OwnerKey filtering. Separately, 58 of 59 membership rows match group scope but differ from user scope, one membership references no current NGT.Users row, one DataOwner has a same-key default DataOwnerCenter, and both current centers are IsActive=0/IsRemoved=0 while referenced by all 786 users, eight groups and 59 memberships; flattening these semantics would deny valid work or broaden group scope",
                [
                    "central deny-first authorization service that evaluates principal, application owner, data owner, center and operation together",
                    "database constraints or validated command invariants preventing cross-Application principal-permission links",
                    "explicit group-scope semantics separate from user default scope",
                    "typed owner context with mandatory hierarchy validation and no ambiguous parent-key fallback",
                    "owner-filtered query API as the only authorization repository surface",
                    "immutable decision audit containing policy version and non-sensitive scope references",
                ],
                [
                    "a deliberately cross-Application grant is rejected at write time and denied at request time",
                    "all direct and group permission queries mechanically include the authenticated ApplicationOwner scope",
                    "altered DataOwner/DataOwnerCenter headers cannot change readable or writable scope without an explicit principal grant",
                    "the 58 group-scope memberships have owner-approved behavior and cross-center positive/negative tests",
                    "the orphan membership is removed or explicitly reconciled",
                    "default-center fallback and IsActive/IsRemoved semantics are owner-approved and covered by migration/read-model tests",
                    "current and migrated permission/application consistency reconciles to zero unexplained mismatch",
                ],
                [
                    E["ngt_owner_scope_effective"],
                    E["ngt_authorization_effective"],
                    E["roles"],
                    E["matrix"],
                ],
                "P0_BEFORE_IDENTITY_PROVISIONING_OR_WEB_COMMAND",
                "security_administrator",
                "CONFIRMED_HASH_PINNED_STATIC_OWNER_AND_REPOSITORY_IL_PLUS_IDENTITY_FREE_READ_ONLY_CLONE_AGGREGATES_WITH_NO_CURRENT_CROSS_APPLICATION_GRANT",
            )
        )
    if ngt_authorization_effective is not None:
        risks.append(
            _risk(
                "R-058",
                "ambient admin role bypasses resource/action and standard role authorization",
                "CRITICAL",
                "authorization",
                ["identity_authorization", "platform"],
                "the target silently copies the deployed NGT superuser shortcut. Static IL proves the derived authorization attribute performs a case-insensitive exact comparison to the code role literal admin and returns true before calling base authorization; base authorization is where Web Resource/Action permission, unauthorized handling, authentication and standard role checks occur. The current clone has one admin role row, three assignment rows and three distinct assigned subjects in aggregate. No identity was persisted and inappropriate use or an incident is not asserted, but a persistent role assignment can bypass every endpoint-specific permission handled by this attribute",
                [
                    "explicit versioned superuser policy separate from ordinary roles",
                    "just-in-time break-glass activation with MFA, dual approval, expiry and reason",
                    "no permanent ambient bypass in ordinary request authorization",
                    "resource/action and data-scope evaluation retained for administrators unless an audited emergency policy explicitly overrides it",
                    "immutable high-signal admin decision and command audit",
                    "segregation-of-duties and periodic assignment recertification",
                ],
                [
                    "all three current aggregate assignments have owner-approved identity-level disposition outside redacted evidence",
                    "ordinary admin-role membership cannot bypass Resource/Action or data scope in target integration tests",
                    "break-glass activation expires automatically and every use records approver, reason, policy version and affected resource",
                    "sensitive financial, authorization and configuration commands require explicit step-up and SoD tests even for administrators",
                    "role removal and emergency revocation take effect within an owner-approved bound",
                ],
                [
                    E["ngt_authorization_effective"],
                    E["roles"],
                    E["matrix"],
                ],
                "P0_BEFORE_IDENTITY_PROVISIONING_OR_WEB_COMMAND",
                "security_administrator",
                "CONFIRMED_HASH_PINNED_STATIC_BRANCH_AND_ALLOWLISTED_ROLE_LITERAL_PLUS_IDENTITY_FREE_CLONE_AGGREGATES",
            )
        )

    if ngt_operation_date_boundary is not None:
        risks.append(
            _risk(
                "R-060",
                "customer-call replication date selector drifts across business and SQL implementations",
                "HIGH",
                "temporal_configuration_integrity",
                ["configuration", "sales", "distribution", "accounting", "integration_migration"],
                "the target flattens CustomerCallReturn.OperationDate, the selected replication document date and GNR.tblOprDate into one field or ports only one of two deployed selection implementations. Static Business IL exposes four selector values. Its OperationDate branch copies the NGT return event timestamp, ActiveDate uses a back-office retrieved active date, ServerDate uses formatted server now, and CallDate has no explicit override branch. Static deployed dbo.NGT_DoReplicateTour instead maps CallDate to call activity date, OperationDate to call activity date with tour-date fallback, ServerDate to server today, and ActiveDate to the open sales GNR.tblOprDate selected with SysRef=1, IsClosed=0 and OprDate after LastDate or LastDate null. Exact equivalence is therefore not proved for OperationDate or ActiveDate. Its selector CASE expressions have no evidenced ELSE, while the IL falls through for missing or unknown values. The current clone is safer than the structure: the one active AppSettings row is a valid non-removed CallDate/«تاريخ درخواست» value; both current NGT return rows have non-sentinel OperationDate on the same calendar day as CreatedDate, FRU has zero rows and the current NGT-to-FRU bridge count is zero. No current wrong-date or accounting incident is asserted. SaveTourData rejects .NET DateTime default and AddDistributionTour assigns captured server now, but the table independently defaults omitted OperationDate to 1900 without an OperationDate check constraint or table trigger",
                [
                    "one server-owned typed replication-date policy shared by every application and SQL path",
                    "separate event timestamp, selected document date, open-system date and created/import timestamps",
                    "fail-closed handling for missing, removed or unknown selector values",
                    "versioned effective configuration with source explanation on every replicated document",
                    "database constraint rejecting sentinel/default event dates outside an explicit migration quarantine",
                    "single Persian/Gregorian conversion and timezone policy with no client-controlled fiscal allocation",
                ],
                [
                    "all four selector values produce identical approved dates across Business IL replacement and SQL replacement Golden cases",
                    "OperationDate and ActiveDate differences are resolved by owner-approved semantics rather than name matching",
                    "null, removed and unknown selector fixtures fail before any return/order/accounting write",
                    "every replicated result records selector version, source kind, source timestamp and final document date",
                    "omitted or 1900 OperationDate is rejected or quarantined at persistence even when application validation is bypassed",
                    "CallDate current-state reconciliation proves the same selected date across both paths on authorized fixtures",
                    "fiscal-year and closed-date boundary tests pass for call, tour, server and open-operation dates",
                ],
                [
                    E["ngt_operation_date_boundary"],
                    E["final_date_diagnostic"],
                    E["ngt_return_crosswalk_diagnostic"],
                    E["matrix"],
                ],
                "P0_BEFORE_RETURN_OR_ORDER_REPLICATION_REWRITE",
                "configuration_publisher",
                "CONFIRMED_HASH_PINNED_STATIC_NGT_IL_DEPLOYED_SQL_READ_ONLY_SCHEMA_AND_ANONYMOUS_AGGREGATES_WITH_NO_CURRENT_WRONG_DATE_INCIDENT",
            )
        )

    if configuration_precedence_boundary is not None:
        risks.append(
            _risk(
                "R-061",
                "effective configuration differs between live business composition and replication views",
                "HIGH",
                "configuration_replication_integrity",
                ["configuration", "sales", "distribution", "platform", "integration_migration"],
                "the target ports a configuration table or one legacy read path instead of one typed effective-setting policy. Static Business IL shows user/device resolution uses owner-aware DeviceSetting and DeviceUser queries, filters removed rows, joins by user, then composes App, General, Tracking, PreSale, HotSale, Distribution, TaskPriority, Report, Print, BackOffice and Inquiry lists. AppSetting is separately retrieved by one fixed singleton identifier. For MandatoryCustomerVisit, the Business composer reads DeviceSettings in General configuration and does not read the AppSettings column, while the SQL transport views do the reverse: the App view emits it and the Device view omits it. All 17 active DeviceSettings currently differ from the one active AppSettings value for that field, including two nullable device values. Back-office live retrieval carries DataOwnerCenterKey to the sync adapter and dbo.NGT_GetBackOfficeSettings reads the DC-effective GNR.SdsNet_serverConfig, but FRU.NGT_TourBackOfficeSettingModel pivots global tblServerConfig instead. Of twelve mapped back-office fields, one output is statically omitted, five additional declared outputs are currently absent because the global source produces NULL/absence, and seven DC-to-delivery comparisons are semantically unequal; the procedure exposes 36 output names while the replication UNPIVOT exposes 30, with six procedure-only outputs after accounting for the known DCName rename. The raw NGT device transport view also emits 2,184 key/value rows for 23 removed-only profiles and 51 active DeviceOrderTypes rows still reference removed profiles, although no current DeviceUser references a removed profile and runtime GetQueryByOwner/explicit predicates filter removed settings. Therefore a current end-user incident or delivery of a removed profile is not asserted, but copying any single path would encode contradictory behavior",
                [
                    "one server-owned typed effective-configuration resolver shared by API, synchronization and migration",
                    "explicit scope lattice for global, application, owner, center, device profile and user assignment",
                    "versioned source-to-output name map with null, missing and removed-state semantics",
                    "no raw configuration view exposed as an effective policy surface",
                    "referential lifecycle policy for profile retirement and dependent order/print/task/user rows",
                    "effective-setting explain output containing source layer, version and fallback decision",
                ],
                [
                    "MandatoryCustomerVisit and every other overlapping setting have owner-approved precedence and identical results across live and replication Golden cases",
                    "all 36 live back-office outputs are mapped, intentionally retired or delivered with the same center-effective value",
                    "missing global values cannot silently remove center-effective settings from synchronization",
                    "null, removed, unknown profile and no-assignment cases fail closed or use an explicitly approved default",
                    "retiring a profile has deterministic cascade/retain behavior for DeviceOrderTypes, print, task and user assignments",
                    "current 17-profile and two-center fixtures reconcile with zero unexplained effective-setting differences",
                    "every synchronized setting records its source scope and policy version",
                ],
                [
                    E["configuration_precedence_boundary"],
                    E["ngt_configuration_runtime_boundary"],
                    E["ngt_owner_scope_effective"],
                    E["matrix"],
                ],
                "P0_BEFORE_CONFIGURATION_OR_DEVICE_SYNC_REWRITE",
                "configuration_publisher",
                "CONFIRMED_HASH_PINNED_STATIC_IL_DEPLOYED_SQL_AND_READ_ONLY_ANONYMOUS_PARITY_AGGREGATES_WITH_NO_ASSERTED_END_USER_INCIDENT",
            )
        )

    if ngt_order_persistence_boundary is not None:
        order_risk = next(row for row in risks if row["id"] == "R-033")
        order_risk["failure_mode"] += (
            ". The deployed NGT order boundary adds a second non-flattenable orchestration: four WebApi bodies call TourDomain.SaveTourData; its async body has 8,960 IL instructions, owns an explicit transaction and can call ReplicateTour four times. ReplicateTour has 15,532 instructions, calls NewReplicateTour and ReplicateToBackOffice, and the SQL adapter reaches the 61,020-character dbo.NGT_DoReplicateTour procedure. The separate UpdateTour path calls CustomerCallOrderDomain.UpdateFromNGT; that body sets removed state and issues five SaveChangesAsync calls with no BeginTransaction call in either inspected body. An ambient or delegated transaction outside those bodies was not excluded, so a current partial-write incident is not asserted. Current anonymous crosswalk aggregates also prove parallel grains rather than one FK: 212,231 NGT orders are fully mapped only through active lines, 9,795 are mapped only through a numeric header id with zero active mapped lines, one is partially line-mapped, seven split across two back-office orders, and 1,125 numeric back-office order ids are shared by multiple NGT headers (3,385 headers; maximum 13). All 61 related foreign-key edges are enabled but not trusted, while current orphan and owner-scope mismatch counts are zero. The empty CustomerCallOrderStatus table and lack of a key/index there do not provide observed immutable transition history"
        )
        order_risk["controls"].extend(
            [
                "versioned many-to-many NGT header/line to back-office order and invoice crosswalk",
                "one explicit transaction owner across save, SQL replication, local state update and post-commit effects",
                "immutable order state events independent of mutable header flags and an optional empty legacy status table",
            ]
        )
        order_risk["exit_criteria"].extend(
            [
                "all four SaveTourData entry paths and four direct replication paths converge on one versioned command contract",
                "header-only, line-only, partial, split and many-to-one crosswalk Golden cases reconcile without collapsing cardinality",
                "faults after each of the five UpdateFromNGT persistence stages leave no partial accepted order state",
                "every accepted order transition emits one immutable event and replay returns the original crosswalk result",
            ]
        )
        order_risk["evidence_refs"].extend(
            [
                E["ngt_order_persistence_boundary"],
                E["ngt_order_runtime_boundary"],
            ]
        )
        order_risk["evidence_strength"] = (
            "CONFIRMED_STATIC_UI_AND_SERVER_IL_DEPLOYED_SQL_READ_ONLY_CATALOG_AND_ANONYMOUS_CROSSWALK_EVIDENCE"
        )

    if ngt_tour_call_state_boundary is not None:
        state_risk = next(row for row in risks if row["id"] == "R-008")
        state_risk["failure_mode"] += (
            ". The deployed NGT tour/customer-call lifecycle is also not a single mutable status column. "
            "Static IL resolves separate Cancel, Deactivate, Activate, Receive, Send, Close and Finish paths: "
            "Deactivate records PreviousStatus before setting Deactivated; Activate restores PreviousStatus; "
            "TourReceived can select Received or Finished; FinishTour performs a direct non-query plus SaveChanges; "
            "and TourSent/backToReadySendStatusTour each wrap a formatted direct non-query in a local transaction. "
            "The current clone has 64,561 Tours and 2,471,250 CustomerCalls but only 455 Tours retain a PreviousStatus, "
            "and the only NGT table whose name signals Tour/CustomerCall status history is the currently empty "
            "CustomerCallOrderStatus table. Therefore PreviousStatus is a narrow reactivation aid, not a complete event log. "
            "The generic BaseValues reference also permits 772 current VisitStatus references to the semantic type "
            "DistributionDeliveryStatus (partial delivery), while all TourStatus and CallStatus references use their expected "
            "types. This can be intentional legacy union behavior, so a current user incident is not asserted; flattening it "
            "would nevertheless erase the distinction between visit outcome and delivery outcome. Two Tours currently have "
            "EndTime before StartTime and three CustomerCalls have a negative VisitDuration, without raw row identities retained"
        )
        state_risk["controls"].extend(
            [
                "typed separate tour, visit, call and delivery state machines with explicit cross-domain transitions",
                "immutable transition event containing previous state, next state, actor, command, reason and policy version",
                "reactivation state stored independently from the immutable lifecycle history",
                "temporal invariants and quarantine for negative duration or end-before-start legacy rows",
            ]
        )
        state_risk["exit_criteria"].extend(
            [
                "Cancel, Deactivate, Activate, Receive, Send, Close, Finish and rollback Golden cases reproduce approved guards and effects",
                "the 772 delivery-status-in-visit-field cases migrate to an owner-approved typed representation without semantic loss",
                "event replay rebuilds current Tour and CustomerCall state, approvals and reactivation state exactly",
                "the two Tour time reversals and three negative call durations are reconciled or quarantined before command enablement",
            ]
        )
        state_risk["evidence_refs"].extend(
            [
                E["ngt_tour_call_state_boundary"],
                E["ngt_tour_call_runtime_boundary"],
            ]
        )
        state_risk["evidence_strength"] = (
            "CONFIRMED_STATIC_DEPLOYED_IL_READ_ONLY_CLONE_TYPED_STATUS_AND_ANONYMOUS_STATE_AGGREGATES_WITHOUT_CURRENT_USER_INCIDENT_CLAIM"
        )

        risks.append(
            _risk(
                "R-062",
                "state-changing NGT tour operations are exposed through HTTP GET",
                "HIGH",
                "web_command_transport",
                ["platform", "sales", "distribution", "identity_authorization", "integration_migration"],
                "the target preserves legacy HTTP transport semantics for Tour lifecycle commands. Among 29 hash-pinned TourController endpoints mapped to activation, deactivation, cancellation, receive, send, payment withdrawal/confirmation and replication operations, 24 are declared GET and only five POST. All 29 have one NGT authorization declaration (25 Resource/Action and four roles-or-empty), so anonymous reachability or a current unauthorized incident is not asserted. However authentication does not make GET a safe mutation verb: browser prefetch, link scanners, intermediary retry/cache behavior, CSRF-style navigation and accidental replay can invoke or repeat a state transition outside an explicit command submission contract",
                [
                    "POST-only or stronger unsafe-method command endpoints with anti-forgery/origin policy where browser credentials are used",
                    "idempotency key and immutable command receipt for every lifecycle transition and replication request",
                    "disable caching and reject GET/HEAD for all state-changing routes",
                    "resource/action authorization, owner scope and expected-version checks inside the command handler",
                    "UI confirmation for irreversible or financially material transitions",
                ],
                [
                    "all 24 legacy mutating GET routes return method-not-allowed or are absent in the target",
                    "GET, HEAD, prefetch and crawler fixtures produce zero state or audit changes",
                    "same idempotency-key replay returns the original transition receipt without a second effect",
                    "cross-origin and unauthorized lifecycle submissions fail before state lookup or mutation",
                    "all 29 transition commands retain positive and negative Resource/Action, role and owner-scope tests",
                ],
                [
                    E["ngt_tour_call_authorization_endpoints"],
                    E["ngt_tour_call_runtime_boundary"],
                    E["ngt_tour_call_state_boundary"],
                ],
                "P0_BEFORE_TOUR_OR_CUSTOMER_CALL_WEB_COMMANDS",
                "security_administrator",
                "CONFIRMED_HASH_PINNED_ENDPOINT_METADATA_STATIC_IL_AND_READ_ONLY_STATE_AGGREGATES_WITH_AUTHORIZATION_PRESENT_AND_NO_CURRENT_INCIDENT_ASSERTED",
            )
        )

    if ngt_payment_settlement_boundary is not None:
        transaction_risk = next(row for row in risks if row["id"] == "R-007")
        transaction_risk["failure_mode"] += (
            ". The deployed NGT UpdateTour path sequentially calls "
            "CustomerCallPaymentDomain.SaveTourPaymentChanges, "
            "StockLevelDomain.SaveTourStockLevelChanges and "
            "CustomerCallOrderDomain.UpdateFromNGT. The inspected UpdateTour async body has no "
            "local BeginTransaction, Commit or Rollback call, while SaveTourPaymentChanges owns "
            "and commits its own explicit transaction with rollback on its caught failure path. "
            "A later stock or order failure can therefore occur after the payment child transaction "
            "has committed unless an unobserved ambient coordinator exists. No current partial-tour "
            "incident or ambient-transaction absence outside the inspected bodies is asserted"
        )
        transaction_risk["controls"].extend(
            [
                "one explicit UpdateTour transaction or durable saga owner across payment, stock and order children",
                "child commands return durable receipts but never independently publish overall tour success",
                "compensation and reconciliation state for payment-committed/stock-or-order-failed outcomes",
            ]
        )
        transaction_risk["exit_criteria"].extend(
            [
                "fault injection after payment commit and before each stock/order persistence stage leaves one recoverable non-success outcome",
                "UpdateTour retry cannot duplicate payment, allocation, stock or order effects",
                "the accepted tour result is published only after all child invariants and durable receipts reconcile",
            ]
        )
        transaction_risk["evidence_refs"].extend(
            [
                E["ngt_payment_runtime_boundary"],
                E["ngt_payment_settlement_boundary"],
                E["ngt_order_runtime_boundary"],
            ]
        )
        transaction_risk["evidence_strength"] = (
            "CONFIRMED_HASH_PINNED_STATIC_MULTI_CHILD_IL_AND_READ_ONLY_ANONYMOUS_PAYMENT_AGGREGATES_WITH_NO_CURRENT_PARTIAL_INCIDENT_ASSERTED"
        )

        configuration_risk = next(row for row in risks if row["id"] == "R-061")
        configuration_risk["failure_mode"] += (
            ". Payment eligibility has the same lifecycle ambiguity: the clone has 404 "
            "PaymentTypeOrders but only 15 active, while all 2,521 DealerPaymentTypes bridge rows "
            "are active and 482 point to removed payment terms. The deployed "
            "GetDealerCustomerPaymentTypes method joins dealer, order-payment, payment-type and "
            "customer-payment sources but has no explicit IsRemoved or IsEnabled metadata reference "
            "in its inspected body. Repository-level filtering or a current end-user exposure was not "
            "proven, so this is a fail-closed eligibility requirement rather than an asserted incident"
        )
        configuration_risk["controls"].extend(
            [
                "versioned payment-term eligibility resolver that filters retired and disabled terms at one boundary",
                "bridge-retirement policy preventing active dealer mappings from silently retaining obsolete terms",
            ]
        )
        configuration_risk["exit_criteria"].extend(
            [
                "all 482 active mappings to removed terms are retired, remapped or explicitly grandfathered with an effective date",
                "dealer/customer payment-term queries cannot return removed or disabled terms unless an approved historical-read mode is explicit",
            ]
        )
        configuration_risk["evidence_refs"].extend(
            [E["ngt_payment_settlement_boundary"], E["ngt_payment_runtime_boundary"]]
        )

        risks.append(
            _risk(
                "R-063",
                "NGT payment header and allocation detail can diverge without a durable invariant",
                "CRITICAL",
                "financial_integrity",
                ["sales", "distribution", "receivables_treasury", "integration_migration"],
                "the target treats CustomerCallPayments.Amount and the sum of active CustomerCallPaymentDetails.PaidAmount as independently editable values or assumes current equality. The read-only clone has 3,523 active payment headers and 3,917 active details: 3,466 headers reconcile to one-cent tolerance, while 57 are underallocated and none are overallocated. Fourteen of the 57 have no detail and 43 have a partial detail sum. The mismatch spans 24 POS, seven cash, 21 cheque and five receipt headers. Static deployed IL shows SaveTourPaymentChanges opens its own transaction, soft-removes existing cash payments for the tour, maps the incoming payment list, accumulates both header Amount and updated existing-detail PaidAmount, then bulk-merges and commits. Current accepted mismatches prove that equality is not a universal durable persistence invariant on every path. All 24 in-scope foreign keys are enabled but not trusted, the five payment/configuration tables have no non-primary unique business key and no trigger, and one current allocation detail points to an order belonging to another CustomerCall; that single relation stays within the same Tour and Customer and may be intentional, so it is not labelled corruption. BackOffice crosswalk identity is strong for 274 linked headers, but only four NGT header amounts equal the linked Receipt amount while 270 differ, proving that receipt identity and amount aggregation grain must remain separate",
                [
                    "fixed-precision payment and allocation money types with one named rounding policy",
                    "server-owned invariant declaring whether header amount must equal allocated amount, with explicit unallocated balance when partial allocation is legal",
                    "immutable payment and allocation command receipt with idempotency key and expected aggregate version",
                    "typed allocation target separating current NGT order, old BackOffice sale and cross-call same-customer allocation",
                    "versioned many-to-one NGT payment to BackOffice receipt crosswalk without amount-equality assumption",
                    "trusted foreign keys and business uniqueness constraints introduced only after reconciliation",
                ],
                [
                    "all 57 current underallocations are reconciled, explicitly represented as unallocated balance or quarantined with no silent repair",
                    "header/detail equality or allowed-partial rules are enforced atomically for cash, POS, cheque and receipt Golden cases",
                    "retry and concurrent update tests create one payment outcome and one allocation set under a fixed aggregate version",
                    "old-invoice, current-order and same-tour/same-customer cross-call allocation fixtures preserve their approved target semantics",
                    "all 274 receipt crosswalks retain identity parity while the 270 different aggregation amounts remain explainable rather than forced equal",
                    "foreign keys become trusted and approved business-key duplicate groups remain zero after migration",
                ],
                [
                    E["ngt_payment_settlement_boundary"],
                    E["ngt_payment_runtime_boundary"],
                    E["ngt_tour_call_state_boundary"],
                    E["ngt_order_persistence_boundary"],
                ],
                "P0_BEFORE_NGT_PAYMENT_OR_SETTLEMENT_WRITE",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_PAYMENT_IL_READ_ONLY_CLONE_CATALOG_AND_ANONYMOUS_RECONCILIATION_WITHOUT_RAW_FINANCIAL_ROWS",
            )
        )

    if ngt_payment_replication_boundary is not None:
        transaction_risk = next(row for row in risks if row["id"] == "R-007")
        transaction_risk["failure_mode"] += (
            ". The deployed payment replication boundary adds a concrete split-writeback case. "
            "dbo.NGT_CreateReceipt_ForDistInfo creates Receipt plus cash, cheque/history and bank-order "
            "instruments, while dbo.NGT_CreateSettlement_Merge creates settlement allocations; neither "
            "helper owns a local transaction and both are called inside dbo.NGT_ReplicateTour's explicit "
            "transaction. That SQL transaction also writes TourHistory Type=10. The outer "
            "dbo.NGT_DoReplicateTour later updates only CustomerCallPayments.BackOfficeReceiptNo. Static "
            "deployed IL then shows TourDomain.ReplicateTour processing NewReplicateTour results and "
            "setting BackOfficeReceiptUniqueId, BackOfficeReceiptRef and BackOfficeReceiptNo, with Commit "
            "events both before and after those setter expressions in linear IL. Branch-complete runtime "
            "reachability is not asserted without fault injection, but current read-only state contains "
            "70 active payments with multiple Type=10 histories and only the receipt number populated, "
            "which is an observed partial crosswalk state"
        )
        transaction_risk["controls"].extend(
            [
                "durable receipt-created/payment-crosswalk-pending state with outbox delivery between SQL and NGT writeback",
                "one reconciliation owner that resolves TourHistory Type=10 to Receipt before any replication retry",
                "accepted payment replication requires UUID, numeric ref and receipt number parity, not number-only writeback",
            ]
        )
        transaction_risk["exit_criteria"].extend(
            [
                "fault after BackOffice receipt commit but before each NGT crosswalk field write leaves a recoverable pending state and no duplicate receipt",
                "all 70 current number-only payment crosswalks are reconciled or quarantined with immutable evidence",
                "the three payment crosswalk fields and current-pointer state become visible atomically to readers",
            ]
        )
        transaction_risk["evidence_refs"].extend(
            [
                E["ngt_payment_replication_boundary"],
                E["ngt_payment_replication_runtime_boundary"],
            ]
        )
        transaction_risk["evidence_strength"] = (
            "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_PARTIAL_CROSSWALK_STATE_AND_NO_COMMAND_EXECUTION"
        )

        risks.append(
            _risk(
                "R-064",
                "NGT receipt replication can repeat history or target creation without an idempotent current crosswalk",
                "CRITICAL",
                "replication_idempotency",
                ["sales", "distribution", "receivables_treasury", "integration_migration"],
                "the target retries mobile payment replication using TourHistory as if it were a unique current crosswalk. Type=10 has 447 rows for 344 active payments. Seventy payments have multiple histories totalling 173 rows and all 70 retain only BackOfficeReceiptNo while UUID and numeric ref are absent. There are 72 exact duplicate target groups, two payments reference multiple distinct target UUIDs, nine history rows across four payments no longer resolve to a current Receipt, and the maximum is six histories for one payment. By contrast, all 274 one-history payments have an exact current UUID/ref/no crosswalk. The only unique EntityUniqueId index on TourHistory is filtered to Type=1, not Type=10; Type=10 has no FK or trigger. Static SQL confirms several receipt branches insert Type=10 without a universal not-exists guard, while another branch has such a guard. Receipt creation writes Receipt, RCash/RCashDetail, TblCheque/tblChqHist and TblBankOrders and settlement creation can write multiple Settlement rows. Static IL shows the main ReplicateTour path sets all three payment crosswalk fields after NewReplicateTour result processing, but this is a separate writeback phase. These facts establish a retry/idempotency gap; they do not prove that every duplicate history created a duplicate financial instrument",
                [
                    "stable idempotency key and payload hash per source payment replication command",
                    "separate append-only replication-attempt history from a unique current payment-to-receipt crosswalk",
                    "receipt and settlement creators first reconcile by source payment key before insert",
                    "outbox/inbox or saga state linking BackOffice commit to NGT crosswalk publication",
                    "quarantine for missing or multi-target histories with no automatic destructive repair",
                    "database uniqueness on the approved current-crosswalk key after reconciliation",
                ],
                [
                    "all 70 multi-history number-only payments and all nine missing-target histories are dispositioned with evidence",
                    "the two multi-target payments resolve to one approved current target while all historical attempts remain auditable",
                    "same-key same-payload retry returns the original Receipt and Settlement result with zero new financial or Type=10 effect",
                    "same-key different-payload retry is rejected before mutation",
                    "fault injection before and after Receipt, instrument, Settlement, TourHistory and NGT crosswalk commits converges to one current result",
                    "concurrent duplicate delivery produces one current crosswalk and one financial effect set",
                ],
                [
                    E["ngt_payment_replication_boundary"],
                    E["ngt_payment_replication_runtime_boundary"],
                    E["ngt_payment_settlement_boundary"],
                    E["ngt_order_runtime_boundary"],
                ],
                "P0_BEFORE_NGT_PAYMENT_REPLICATION_OR_RETRY",
                "delivery_team",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_READ_ONLY_CLONE_CROSSWALK_AGGREGATES_WITHOUT_RAW_FINANCIAL_ROWS",
            )
        )

    if ngt_replication_compensation_boundary is not None:
        risks.append(
            _risk(
                "R-065",
                "NGT rollback cannot compensate current receipt dependency shapes",
                "CRITICAL",
                "replication_compensation",
                ["sales", "distribution", "receivables_treasury", "integration_migration"],
                "the target treats the deployed RollBackTour path as a complete compensating transaction after BackOffice replication. Static Business IL proves RollBackTour assigns request type 20, calls RetrieveInfo once and immediately discards its Boolean result with the pop opcode, so the adapter's false result after catch-Rollback is not propagated as a checkable success/failure signal. Both deployed VnLite and VnSds adapters select ReplicateResult.EntityUniqueId values, stage an EntityUniqueId temp table, execute dbo.NGT_RollBackTour and own one Commit plus catch Rollback branch. The active procedure has no local transaction and deletes TourHistory after attempting BackOffice cleanup, but it does not mention RCashDetail or tblChqHist. Its tblPayments delete is driven only by TourHistory Type=11, while current TourHistory contains only Types 1, 2, 8 and 10. The similarly named dbo.USP_NGT_UndoReplicateTour has an unconditional RETURN before its mutation block and all 21 profiled mutations, including cash-detail and cheque-history cleanup, are commented. Current anonymous aggregates show 342 distinct existing Type=10 receipt targets; all 342 have at least one enabled NO_ACTION dependency candidate through cash detail, cheque history or settlement payment links. The adapters execute only schema/temp staging and the active rollback call in request-type 20 before Commit. This proves the deployed compensation design is structurally incomplete for the current receipt shape and its failure result can be made invisible at the Business boundary; it does not prove which rollback attempts occurred or their operational frequency",
                [
                    "one versioned compensator that deletes or reverses settlement payments, cheque history and cash detail before instruments and Receipt",
                    "compensation plan generated from the same immutable replication attempt manifest and entity ids",
                    "durable saga state distinguishing compensation requested, running, blocked, completed and manually quarantined",
                    "foreign-key-aware dependency traversal with explicit reversible actions instead of blind physical delete",
                    "no TourHistory deletion until every dependent financial action is reconciled and the NGT crosswalk state is atomically updated",
                    "typed compensation result propagated to every caller plus an operator-visible blocked queue with exact non-sensitive reason codes",
                ],
                [
                    "controlled fault injection after every receipt, instrument, settlement, history and crosswalk step converges to one valid pre-command or committed state",
                    "all current receipt dependency shapes—cash, cheque and bank order—pass compensation tests with trusted foreign keys enabled",
                    "same compensation key is idempotent and concurrent compensation cannot double-reverse or delete a newer financial state",
                    "a failed compensation retains TourHistory and current-pointer evidence, returns an explicit failure to its caller and creates a durable blocked state",
                    "the dead dbo.USP_NGT_UndoReplicateTour entry point is removed or explicitly quarantined and cannot be mistaken for an operational control",
                    "the 342 current dependency-bearing receipt targets are classified by reversible, retained or manual-remediation policy before migration",
                ],
                [
                    E["ngt_replication_compensation_boundary"],
                    E["ngt_replication_compensation_runtime_boundary"],
                    E["ngt_payment_replication_boundary"],
                    E["ngt_payment_replication_runtime_boundary"],
                ],
                "P0_BEFORE_NGT_REPLICATION_COMPENSATION_OR_RETRY",
                "delivery_team",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_REFERENTIAL_DEPENDENCY_AGGREGATES_AND_NO_COMMAND_EXECUTION",
            )
        )

    if ngt_return_replication_boundary is not None:
        risks.append(
            _risk(
                "R-066",
                "NGT return replication commit and crosswalk write-back are not atomic or uniquely guarded",
                "CRITICAL",
                "return_replication_idempotency",
                ["sales", "distribution", "inventory", "integration_migration"],
                "the target retries or migrates NGT mobile returns as though BackOffice creation and NGT crosswalk persistence were one atomic operation. Read-only SQL fingerprints prove dbo.NGT_DoReplicateTour commits its NGT_ReplicateTour call before the ReturnOrder crosswalk write-back. Static IL independently shows TourDomain.ReplicateTour calls NewReplicateTour before its first managed transaction and before six line-level BackOfficeReturn Order/Invoice setters plus two call-level return-order collection setters; managed Commit signals exist on both sides of those setters. No enabled unfiltered unique index protects TourHistory EntityUniqueId for return Types 2/12, and no unique index protects the return-line BackOffice crosswalk columns. Current anonymous state contains two active mobile return lines: one has no return history, while one has an exact historical Type=2 result and write-back but its current RetOrder target is missing; neither has a current RetOrder target. This proves a durable failure/reconciliation window and an ambiguous retry boundary, not that a duplicate return currently exists or which historical failure caused the missing target",
                [
                    "one immutable ReturnReplicationAttempt with a caller-supplied idempotency key and canonical payload hash",
                    "one versioned current crosswalk plus append-only historical result receipt for each mobile return line",
                    "database-enforced uniqueness for accepted attempt identity and the current source-to-target crosswalk",
                    "transactional outbox or recoverable saga linking BackOffice return creation to NGT crosswalk publication",
                    "retry policy that returns the prior result for the same key/payload and rejects key reuse with different payload",
                    "quarantine and reconciliation for historical-result/current-target-missing and no-history states before migration",
                ],
                [
                    "fault injection after BackOffice RetOrder/RetSale creation and before every crosswalk/history write converges to one target",
                    "concurrent identical return submissions create one accepted attempt, one current crosswalk and one inventory/credit effect",
                    "same-key same-payload retry returns the original result while same-key different-payload retry is rejected before mutation",
                    "the current historical-result/missing-target line is dispositioned with evidence and is never recreated automatically",
                    "the no-history line is classified as pending, rejected or unattempted by authoritative evidence before any command",
                    "reconciliation detects committed targets whose NGT write-back is absent and repairs only the crosswalk, not the business document",
                ],
                [
                    E["ngt_return_replication_boundary"],
                    E["ngt_return_runtime_boundary"],
                    E["ngt_return_crosswalk_diagnostic"],
                    E["ngt_replication_compensation_boundary"],
                ],
                "P0_BEFORE_NGT_RETURN_REPLICATION_RETRY_OR_MIGRATION",
                "delivery_team",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_RETURN_STATE_AND_NO_COMMAND_EXECUTION",
            )
        )
        risks.append(
            _risk(
                "R-067",
                "NGT return update can persist a partial header-line-detail graph",
                "HIGH",
                "return_ingest_atomicity",
                ["sales", "distribution", "integration_migration"],
                "the target treats UpdateFromNGT as one atomic aggregate update. Static IL proves CustomerCallReturnDomain.UpdateFromNGT writes removed state across existing line/detail records, merges line/detail state, updates the header canceled flag, and performs three SaveChanges calls with zero local Begin/Commit/Rollback signals. Its single observed CustomerCallDomain.UpdateFromNGT caller adds one further SaveChanges and also has zero transaction signals. This establishes multiple durable boundaries across a logical return graph; it does not prove that a partial update incident occurred or that an ambient provider transaction never exists outside the visible methods",
                [
                    "one aggregate transaction for return header, lines, quantity details and tombstones",
                    "optimistic concurrency token checked once for the aggregate version rather than per SaveChanges phase",
                    "idempotent device-sync command with immutable request identity and payload hash",
                    "validation and quantity/unit normalization completed before the first durable mutation",
                    "transactional outbox emitted in the same commit as the new aggregate version",
                    "partial-state detector and quarantine reason codes for interrupted legacy imports",
                ],
                [
                    "fault injection before and after each legacy-equivalent SaveChanges point leaves either the prior or complete next aggregate",
                    "removed lines and quantity details cannot become visible without their matching header/version transition",
                    "retry of an interrupted device sync converges without duplicate line/detail rows or lost tombstones",
                    "concurrent edits produce an explicit version conflict rather than last-writer-wins partial merge",
                    "outbox and audit contain exactly one accepted aggregate version for every successful sync",
                    "controlled fixtures cover add, update, remove, cancel and mixed line/detail replacement paths",
                ],
                [
                    E["ngt_return_runtime_boundary"],
                    E["ngt_return_replication_boundary"],
                    E["ngt_return_crosswalk_diagnostic"],
                ],
                "P0_BEFORE_NGT_RETURN_DEVICE_SYNC_COMMAND",
                "delivery_team",
                "CONFIRMED_STATIC_IL_MULTI_SAVE_BOUNDARY_WITHOUT_RUNTIME_FAULT_INJECTION",
            )
        )

    if ngt_sale_replication_boundary is not None:
        risks.append(
            _risk(
                "R-068",
                "NGT sale replication history is duplicated without an atomic uniquely guarded crosswalk",
                "CRITICAL",
                "sale_replication_idempotency",
                ["sales", "inventory", "distribution", "integration_migration"],
                "the target treats a Type=8 TourHistory row as a unique sale-replication attempt/current crosswalk. Read-only aggregates prove 3,731 Type=8 histories for 3,593 NGT order entities: 138 entities have exactly two history rows, and every duplicate pair has the same BackOffice UUID, Ref, No and timestamp. All 3,593 current NGT order header UUID/Ref values agree with their history target and all 3,593 Sale targets currently resolve; multi-target and missing-target counts are zero. Static IL separately proves TourDomain.ReplicateTour calls NewReplicateTour before its first managed transaction and before three BackOfficeInvoice UUID/Id/No setters, with Commit signals both before and after those setters. No enabled unfiltered unique index protects Type=8 TourHistory entity identity or the NGT order invoice crosswalk. This proves duplicate ledger facts and a structural retry/write-back race window; it does not prove duplicate Sale, stock or accounting effects, nor identify the SQL branch that inserted each duplicate row",
                [
                    "immutable SaleReplicationAttempt keyed by source order, command id and canonical payload hash",
                    "append-only attempt history separated from one database-unique current order-to-sale crosswalk",
                    "transactional outbox or recoverable saga linking Sale commit, stock/accounting effects and NGT write-back",
                    "same-key retry returns the prior Sale result while different-payload reuse is rejected before mutation",
                    "reconciliation compares order header, attempt history, Sale target, inventory voucher and accounting receipt",
                    "migration collapse policy that preserves both duplicate legacy history facts but selects one evidenced current target",
                ],
                [
                    "all 138 duplicate-history entities migrate with two historical facts and exactly one current Sale crosswalk",
                    "fault injection after Sale creation and before each history/header write converges to one Sale and one effect set",
                    "concurrent identical sale replication produces one accepted attempt, one Sale, one stock effect and one accounting effect",
                    "same-key same-payload and different-payload retry behavior passes deterministic tests",
                    "reconciliation detects and quarantines any future multi-target or missing-target state before command retry",
                    "all 3,593 current mappings pass UUID/Ref/header/target parity after repeatable import",
                ],
                [
                    E["ngt_sale_replication_boundary"],
                    E["ngt_sale_replication_runtime_boundary"],
                    E["ngt_order_persistence_boundary"],
                    E["ngt_replication_compensation_boundary"],
                ],
                "P0_BEFORE_NGT_SALE_REPLICATION_RETRY_OR_MIGRATION",
                "delivery_team",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_TYPE8_CROSSWALK_AGGREGATES",
            )
        )

    if ngt_order_history_boundary is not None:
        risks.append(
            _risk(
                "R-069",
                "NGT order history retains crosswalks to missing BackOffice order targets",
                "CRITICAL",
                "order_replication_reconciliation",
                ["sales", "distribution", "inventory", "integration_migration"],
                "the target recreates or trusts an order solely from a Type=1 TourHistory/current NGT line crosswalk. Read-only aggregates prove 1,118,244 Type=1 line histories; 1,112,711 resolve by both UUID and Ref to the same current SLE order, while 5,533 resolve by neither key. Those 5,533 surviving NGT line crosswalks map to 1,024 distinct missing target pairs across 1,022 parent mobile orders. All affected lines and parents are active, uncanceled and not converted through a Type=8 sale history; 1,021 parents have every Type=1 target missing and one parent has a mixed 15-resolved/1-missing line set. Retained generic replication logs contain exactly one canonical SLE.tblOrderHdr DELETE for each of the 1,024 missing target refs, and every delete follows the last Type=1 history: 298 on the same day, 534 within 1-7 days and 192 within 8-30 days. This proves target deletion after replication, while static IL separately shows NewReplicateTour precedes the managed transaction and order-line write-back. It does not identify the calling procedure, business reason or operator intent and it does not authorize recreation",
                [
                    "durable OrderReplicationAttempt and one versioned current line/order crosswalk with target existence status",
                    "reconciliation that resolves UUID and Ref independently and quarantines neither-match or conflict states",
                    "target tombstone/archive registry so deletion or relocation cannot look like never-attempted replication",
                    "transactional outbox or saga linking BackOffice order creation to all line crosswalk publications",
                    "parent-level completeness policy preventing partial promotion when any active line target is unresolved",
                    "operator workflow for retain, relink, void or owner-approved recreate decisions with evidence",
                ],
                [
                    "all 1,022 affected parent orders and 1,024 missing target pairs receive an evidenced disposition",
                    "the mixed 15-resolved/1-missing parent remains quarantined until one consistent parent target policy is approved",
                    "all 634 recent missing-target lines are reconciled against delete/archive/rollback telemetry without automatic recreation",
                    "fault injection before and after order creation/history/line write-back converges to one target and complete parent mapping",
                    "concurrent retry cannot create a second target or publish a partial line crosswalk",
                    "repeatable import preserves historical crosswalk facts and reports zero silently unresolved command-ready parents",
                ],
                [
                    E["ngt_order_history_boundary"],
                    E["ngt_order_history_runtime_boundary"],
                    E["ngt_order_delete_log_boundary"],
                    E["ngt_order_persistence_boundary"],
                    E["ngt_sale_replication_boundary"],
                ],
                "P0_BEFORE_NGT_ORDER_REPLICATION_RETRY_RECREATE_OR_MIGRATION",
                "delivery_team",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_TYPE1_TARGET_RECONCILIATION_AGGREGATES",
            )
        )

    if ngt_order_deletion_boundary is not None:
        risks.append(
            _risk(
                "R-070",
                "BackOffice order deletion has no durable NGT-aware target tombstone",
                "HIGH",
                "order_target_deletion_observability",
                ["sales", "distribution", "inventory", "integration_migration"],
                "the target treats a missing SLE order as equivalent to an unattempted NGT replication or treats the generic replication log as a durable NGT-aware tombstone. Static read-only catalog analysis finds 404 SQL modules referencing SLE.tblOrderHdr and four executable static procedures that directly delete the order header. Only NGT_RollBackTour also references TourHistory; the other three direct delete procedures reference neither TourHistory, NGT order lines nor BackOfficeOrder UUID/Ref/No crosswalks. Three active DELETE triggers exist; none reconciles NGT, while the replication trigger records target table, operation, numeric target id and time in GNR.tblLog. That log exactly matches all 1,024 currently missing Type=1 target refs and places every deletion after the last history. Every matched session has an item-delete then visit-delete then order-header-delete tail; this excludes the normal successful NGT_RollBackTour visit-item-header-history sequence and the no-visit UndoUserExtraInfo sequence. It matches usp_sdsnet_Order_Delete and the order tail of usp_sdsnet_ConfirmFreeInvoice, but zero preceding SaleHeader DELETE signals leave procedure attribution unresolved. Anonymous metadata spans 23 applications, 25 hosts and 466 sessions. This proves deletion and a domain-aware tombstone/reconciliation gap, but does not attribute any current missing target to a particular procedure, business reason or operator action",
                [
                    "append-only OrderTargetTombstone keyed by target UUID/ref with source command, reason and actor class",
                    "one deletion orchestrator that reconciles NGT current crosswalk and history before target removal",
                    "outbox event for target deleted, archived or relocated committed with the disposition record",
                    "deny-by-default delete policy when an active NGT mapping exists unless an approved disposition is supplied",
                    "reconciliation that distinguishes never-created, deleted, archived, relocated and inaccessible targets",
                    "retention and audit policy independent of generic replication transport logs",
                ],
                [
                    "every supported order-delete entry point produces one immutable target disposition and one outbox event",
                    "deleting a mapped order cannot leave its NGT crosswalk looking command-ready or never-attempted",
                    "fault injection around child cleanup, header delete, tombstone and outbox commit converges deterministically",
                    "the 5,533 legacy missing-target histories are classified without fabricating a deletion cause",
                    "generic replication-log loss or replay cannot erase or duplicate target disposition state",
                    "temporal/audit retention tests prove who/why/when evidence survives the operational retention window",
                ],
                [
                    E["ngt_order_deletion_boundary"],
                    E["ngt_order_delete_log_boundary"],
                    E["ngt_order_history_boundary"],
                    E["ngt_replication_compensation_boundary"],
                ],
                "P0_BEFORE_ORDER_DELETE_RECREATE_OR_CROSSWALK_REPAIR",
                "delivery_team",
                "CONFIRMED_HASH_PINNED_READ_ONLY_STATIC_DELETE_AND_TOMBSTONE_COVERAGE_WITHOUT_CAUSAL_ATTRIBUTION",
            )
        )
    if supplier_cost_apply_boundary is not None:
        risks.append(
            _risk(
                "R-071",
                "supplier invoice reapply can publish applied status before inventory cost rebuild completes",
                "CRITICAL",
                "supplier_cost_atomicity",
                ["procurement_payables", "inventory", "accounting", "integration_migration"],
                "the target copies supplier-cost apply/reapply as independent destructive price rebuild and status writes. Five core SQL modules contain no local explicit transaction. The ordinary apply deletes then reinserts inv.tblVocherItmPrice; fast apply deletes, reinserts and then marks the invoice applied. More critically, reapply first marks selected invoice headers Status=1 with ConfirmDate and only afterwards loops into fast apply. A direct SLE.usp_CheckSupInvoice caller also has no explicit local transaction, while other catalogued callers vary and some own an outer transaction. Hash-pinned static IL confirms the managed StartReApplySupInvoice route reaches the reapply procedure through DataContext.Query with no selected-path BeginTransaction or Commit signal; the separate ApplySupInvoice business route does expose a DataContext.Commit after its adapter call in linear IL. Current read-only parity is clean: all 3,285 applied invoices cover 29,078 related voucher items with price rows and all 141 unapplied invoices cover 1,354 items with none. This proves a structural failure window, not a current partial-apply incident. Ninety-five orphan price rows exist without a voucher-item foreign key, but their cause is not attributed to supplier apply",
                [
                    "immutable SupplierCostApplicationAttempt with command id, payload hash and source invoice version",
                    "single transaction owner for validation, cost-price rebuild, applied status, confirm timestamp and outbox",
                    "explicit Pending/Applying/Applied/Failed state machine with no pre-marking as Applied",
                    "versioned cost layer or append-only cost audit instead of unaudited destructive replacement",
                    "per-component concurrency lock and same-key retry semantics",
                    "foreign-key or explicit tombstone/reconciliation policy for voucher-item price ownership",
                ],
                [
                    "fault injection before and after price delete, rebuild, status update, audit and outbox leaves either the prior complete state or one complete next state",
                    "Applied is true if and only if every governed voucher item has the expected versioned price outcome",
                    "concurrent reapply accepts one attempt and cannot expose a transient applied-without-price projection",
                    "same-key replay returns the original result and different-payload reuse is rejected",
                    "all current 3,285 applied/29,078 priced and 141 unapplied/1,354 unpriced snapshot invariants reconcile after repeatable import",
                    "all 95 orphan price rows receive an evidenced disposition without fabricating a supplier-apply cause",
                    "every direct and outer caller has one tested transaction-ownership contract",
                ],
                [
                    E["supplier_cost_apply_boundary"],
                    E["supplier_cost_apply_runtime_boundary"],
                    E["supplier_receipt_component_diagnostic"],
                    E["migration"],
                ],
                "P0_BEFORE_SUPPLIER_COST_APPLY_REAPPLY_OR_MIGRATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_STATUS_PRICE_PARITY",
            )
        )
    if supplier_unapply_delete_boundary is not None:
        risks.append(
            _risk(
                "R-072",
                "supplier invoice unlink and delete erase cost provenance through path-dependent reversal",
                "HIGH",
                "supplier_cost_reversal_and_deletion",
                ["procurement_payables", "inventory", "accounting", "integration_migration"],
                "the target copies supplier invoice unlink/delete as generic row deletion or in-place price reset. Eight selected SQL modules expose three transaction owners and several distinct semantics. ICA.uspLinkUnlinkSupInvoiceInv owns no local transaction: its unlink branch validates purchase final dates, then marks the whole invoice Status=0 and clears ConfirmDate before zeroing Price and UnitPrice for items of the selected inventory voucher. The branch also contains application-name-specific rollback behavior. Other paths delete relations, item/toll rows or the header; the direct UspSupInvoiceHdrOperation→UspSupInvoiceHdrDelete→UspSupInvoiceHdrDeleteItemsAndTolls chain has no local explicit transaction, while SDSNET and voucher-removal paths do. Hash-pinned IL shows the managed Unlink route performs a generic relation SaveCommand, calls operation code 3 twice through the adapter and then commits in linear order, but exact generic table mutation and branch-specific physical transaction reachability remain unproven. This granularity mismatch matters because 17 unapplied and 192 applied invoices have multiple receipt relations. Retained generic relation logs contain 3,902 inserts and 213 deletes, including 15 deletes in June-August 2026; last-event state exactly projects 3,689 current and 203 absent relation ids, proving an active lifecycle but not the business reason or corresponding cost transition. Header and price tables are non-temporal with no CDC/change tracking or audit trigger. Current snapshot parity remains clean and the 83 globally zero-price rows are not attributed to unlink. Two settlements reference applied invoices and 27 returns reference 12 source invoices across both statuses; direct delete SQL does not itself prove those dependency policies are enforced",
                [
                    "append-only SupplierCostReversalAttempt keyed by invoice, governed receipt component, command id and prior cost version",
                    "one explicit application transaction for relation transition, cost reversal, invoice state, dependency checks, audit and outbox",
                    "component-grain N:M reversal policy that cannot mark an invoice Unapplied while only part of its governed receipts remain priced",
                    "immutable before/after cost-layer provenance instead of zeroing or deleting the only current price record",
                    "uniform dependency guard for settlements, purchase returns, closed dates and consumed downstream cost across desktop and SDSNET paths",
                    "soft-delete or tombstone policy for invoice and relation identities with deterministic restore/relink semantics",
                ],
                [
                    "fault injection before and after relation removal, status transition, each cost reversal, audit and outbox yields one complete prior or next state",
                    "all 17 unapplied and 192 applied multi-receipt invoices pass component-grain unlink/relink Golden cases",
                    "same-key retry and concurrent unlink/relink cannot duplicate, lose or partially publish a relation or cost version",
                    "settled, returned, closed-period and consumed-cost delete/unlink cases are consistently rejected or use an approved compensating workflow",
                    "all 213 retained relation deletes receive a migration-safe lifecycle disposition without fabricating business reason or actor intent",
                    "the clean 3,285/29,078 applied and 141/1,354 unapplied status-price invariants remain exact after repeatable import and reversal tests",
                    "the 83 zero-price rows are provenance-classified without attributing them to unlink from aggregate evidence",
                ],
                [
                    E["supplier_unapply_delete_boundary"],
                    E["supplier_unapply_delete_runtime_boundary"],
                    E["supplier_cost_apply_boundary"],
                    E["supplier_receipt_component_diagnostic"],
                ],
                "P0_BEFORE_SUPPLIER_UNAPPLY_DELETE_RELINK_OR_MIGRATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_RELATION_LIFECYCLE_AND_STATUS_PRICE_PARITY",
            )
        )
    if payable_cheque_undo_boundary is not None:
        risks.append(
            _risk(
                "R-073",
                "payable-cheque undo physically deletes the last financial state event",
                "HIGH",
                "payable_cheque_audit_and_reversal",
                ["procurement_payables", "receivables_treasury", "accounting", "integration_migration"],
                "the target implements payable-cheque undo by deleting the last state event or treats the retained replication log as a complete event ledger. Static SQL proves DoPCheque_DeleteLastPChequeHistory checks voucher dependency before opening a transaction, then deletes PChequeHistory, updates the cheque current pointer, recomputes cheque-leaf usage and commits with TRY/CATCH rollback; it appends no compensating event. The outer SDSNET change-status procedure can call both AddHistory and DeleteLastHistory inside its own transaction. Retained anonymous logs contain 1,668 distinct history DELETE events; 1,537 have the exact static undo tail History DELETE→PCheque UPDATE→PChequeBookItem UPDATE, including 78 in June-August 2026. Another 117 have a cheque-delete signal and 14 have a partial update tail, so not every history delete is attributed to undo. Hash-pinned IL independently shows the legacy form checks CanDoUndo, starts a transaction, calls the adapter delete, may call CreateApprovePChequeHistory on a branch, then refreshes and commits; the adapter itself starts a nested transaction around ExecuteNonQuery. The newer tracking form UndoStatus is a one-instruction stub, but runtime form selection is not proven. Current 4,672 cheques and 13,108 histories have exact parent/current-max pointer parity and all observed transitions are valid. However 402 history IDs were inserted and later became absent with no retained DELETE event in one March 2024 batch; they are not attributed to undo or trigger bypass. All three operational tables are non-temporal without CDC/change tracking. Therefore the current projection is clean while the authoritative audit trail is destructive and incomplete",
                [
                    "append-only PayableChequeStateEvent with a compensating Reversed event referencing the superseded event instead of deleting it",
                    "versioned current-state projection rebuilt only from immutable events with optimistic concurrency",
                    "one transaction for event append, current pointer, leaf availability, supplier ledger effect, voucher dependency audit and outbox",
                    "idempotent undo command keyed by cheque and expected current event version",
                    "explicit source tombstone state for legacy destructive undo and unexplained history disappearance without fabricated status payload",
                    "uniform permission and dependency policy across legacy, new tracking and SDSNET routes",
                ],
                [
                    "undo creates one compensating event and never deletes an existing destination state event",
                    "fault injection after event, pointer, leaf, ledger and outbox boundaries converges to one complete projection",
                    "concurrent same-version undo accepts one command and stale versions fail deterministically",
                    "all 1,537 exact-tail legacy deletes and 78 recent cases are imported as evidenced destructive-undo tombstones without invented status, actor or reason",
                    "the 117 cheque-delete tails, 14 partial tails and 402 March-2024 no-delete-log rows receive separate dispositions",
                    "all 4,672 cheque pointers remain same-parent/max-event and the 4,827 used-leaf partition remains 4,672 linked plus 155 SOURCE_USED_UNLINKED",
                    "valid forward, undo, certified, voucher-blocked and supplier-ledger Golden cases pass for every supported UI/API route",
                ],
                [
                    E["payable_cheque_undo_boundary"],
                    E["payable_cheque_undo_runtime_boundary"],
                    E["payable_cheque_leaf_usage_diagnostic"],
                    E["migration"],
                ],
                "P0_BEFORE_PAYABLE_CHEQUE_UNDO_STATUS_MIGRATION_OR_WRITE_UI",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_HISTORY_DELETE_TAIL_RECONCILIATION",
            )
        )
    if received_cheque_undo_boundary is not None:
        risks.append(
            _risk(
                "R-074",
                "received-cheque undo deletes one or two state events and relies on trigger-owned projection repair",
                "HIGH",
                "received_cheque_audit_and_reversal",
                ["receivables_treasury", "sales", "accounting", "integration_migration"],
                "the target copies received-cheque undo as row deletion or assumes one deleted history row per command. Static SQL proves DoRCheque_DeleteLastRChequeHistory validates through BeforeRChequeHistory before opening its transaction, deletes the current Acc.tblChqHist row and, specifically when PreviousStatRef=8 and the deleted current status is 1, deletes the preceding status-8 row too. It appends no compensating event. Active delete and insert triggers own the IsLast projection by reactivating the previous row after delete and deactivating it on append. The desktop forms do not call the direct DeleteLast adapter: both hash-pinned legacy and new DoUndo methods start a managed transaction, check CanDoUndo, call RChequeAdapter.DeleteCessionToOther, refresh and commit with rollback signal. That adapter opens another transaction around ExecuteNonQuery; the SQL wrapper itself starts a transaction, calls DeleteLast and commits but has no explicit rollback token. Retained anonymous logs contain 14,711 history DELETE events. Exact adjacent tails identify 1,502 undo-command candidates; 22 are conditional double-delete heads, so 1,524 deleted rows are attributed to those candidates. In June-August 2026 there are 471 command candidates and 475 attributed deleted rows. Another 12 recent deletes and the larger historical delete population are not attributed to undo. Current 23,822 cheques and 106,131 histories have exactly one IsLast row, max-ID and chain parity with zero mismatch. Another 252 inserted history IDs are absent without retained DELETE events across a March-2024 historical interval and are not attributed to undo, migration or trigger bypass. Both operational tables are non-temporal without CDC/change tracking. Therefore the current projection is clean while source audit history is destructive, trigger-dependent and variable-cardinality",
                [
                    "append-only ReceivedChequeStateEvent with a compensating Reversed event referencing every superseded source event",
                    "versioned current projection derived from immutable events rather than trigger repair after physical deletion",
                    "one transaction for event append, current projection, cession cleanup, returned-cheque allocation effects, accounting dependency audit and outbox",
                    "idempotent undo keyed by cheque and expected current event version with explicit one-event versus transient-status-collapse semantics",
                    "migration tombstones for legacy destructive undo and unexplained disappearance without fabricated status, actor or reason",
                    "uniform command and authorization policy across legacy form, new form, wrapper procedure and SDSNET bulk route",
                ],
                [
                    "undo creates compensating events and never deletes destination history",
                    "single and status-8-collapse undo Golden cases preserve the intended final state with complete provenance",
                    "fault injection around event, projection, cession cleanup, allocation, accounting audit and outbox yields one complete state",
                    "concurrent same-version undo accepts one command and stale or repeated versions fail deterministically",
                    "all 1,502 exact-tail command candidates, 22 double-delete heads and 471 recent commands receive source-safe dispositions without invented payload",
                    "the 252 no-delete-log gaps and all non-undo delete shapes remain separately quarantined",
                    "all 23,822 current cheques retain exactly one max-ID IsLast event and zero broken PreviousHistRef/PreviousStatRef chains after repeatable import",
                ],
                [
                    E["received_cheque_undo_boundary"],
                    E["received_cheque_undo_runtime_boundary"],
                    E["received_cheque_projection_legal_diagnostic"],
                    E["migration"],
                ],
                "P0_BEFORE_RECEIVED_CHEQUE_UNDO_STATUS_MIGRATION_OR_WRITE_UI",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_VARIABLE_CARDINALITY_DELETE_TAIL_RECONCILIATION",
            )
        )
    if received_cheque_delete_boundary is not None:
        risks.append(
            _risk(
                "R-075",
                "received-cheque and receipt deletion have distinct destructive entry points and tombstone scopes",
                "HIGH",
                "received_cheque_and_receipt_deletion",
                ["receivables_treasury", "sales", "accounting", "integration_migration"],
                "the target models every received-cheque disappearance as the same delete command, attributes adjacent table logs to one procedure, or relies on current rows as a complete deletion audit. Static SQL finds seven direct Acc.TblCheque delete candidates with heterogeneous ownership: Acc.uspCHQDelete validates and owns an atomic history-before-master transaction; dbo.usp_sdsnet_Receipt_Save owns a transaction/savepoint and contains a full history→master→receipt cleanup branch; the INSTEAD OF view trigger dbo.Trg_RCheque_TblCheque deletes the master without directly deleting history or receipt; four other direct candidates have different local-transaction and cleanup signals. The master has NO_ACTION dependencies from history, payments, settlement and transfer/reconciliation tables, while receipt deletion also has a mixed NO_ACTION/CASCADE graph and TblCheque deletion cascades tblRChequeLog. Retained anonymous logs contain 31 master DELETE events, including 11 in June-August 2026. All 31 logged IDs are currently absent with zero insert-only-absent or deleted-but-present mismatch, and every master delete has at least one same-session history-delete lookback. Twenty-three masters and twenty-three history deletes occur in 19 receipt-delete batches, structurally matching the full receipt-save branch but not proving its invocation; seven other masters have a receipt-update tail and one recent master has an isolated tail. Of 2,351 retained receipt deletes, only those 19 batches include master cleanup; 238 receipt deletes and five master-cleanup batches are recent. Hash-pinned IL shows the legacy tracking form confirms, marks a DataRow deleted and calls RCheque.Update in linear order without an explicit transaction signal in that method, while the new form's selected DeleteRCheque contains confirmation but no dataset delete/update signal. Runtime form selection and dataset-to-trigger reachability remain unresolved. Therefore DeleteCheque, DeleteReceipt and cleanup/tombstone semantics must stay separate, and procedure, user and business-reason attribution must not be fabricated from adjacency alone",
                [
                    "separate idempotent DeleteReceivedCheque and DeleteReceipt commands with explicit expected version, reason and authorization",
                    "append immutable cheque and receipt tombstones before projection removal, preserving source evidence without inventing actor or reason",
                    "one declared transaction owner for history, cheque, receipt/cash cleanup, dependency checks, accounting effects and outbox",
                    "explicit dependency policy for NO_ACTION links and explicit audit policy for CASCADE children such as tblRChequeLog",
                    "route-parity contract across legacy dataset update, view trigger, direct procedure, SDSNET save and integration rollback paths",
                    "migration classification that preserves receipt-delete batches, receipt-update tails and isolated tails as distinct evidence states",
                ],
                [
                    "DeleteReceivedCheque and DeleteReceipt Golden cases produce different command/event types and deterministic projection scopes",
                    "all 31 retained master tombstones reconcile to absent source rows, with the 23 receipt-delete-tail, seven receipt-update-tail and one isolated-tail cases kept distinct",
                    "the 19 receipt-delete batches preserve their 23-master/23-history cardinality without assigning an unproven procedure, actor or reason",
                    "fault injection at history, master, receipt, cash, accounting and outbox boundaries yields one complete transaction or a replayable failed attempt",
                    "NO_ACTION dependency conflicts fail before mutation and CASCADE-audit children are exported before deletion",
                    "legacy/new/direct/SDSNET route tests share one policy and runtime form selection is explicit rather than inferred",
                    "repeat import of 2,351 receipt tombstones and 31 cheque tombstones is idempotent and never converts adjacency into fabricated business attribution",
                ],
                [
                    E["received_cheque_delete_boundary"],
                    E["received_cheque_delete_runtime_boundary"],
                    E["received_cheque_undo_boundary"],
                    E["migration"],
                ],
                "P0_BEFORE_RECEIVED_CHEQUE_OR_RECEIPT_DELETE_MIGRATION_OR_WRITE_UI",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_MASTER_RECEIPT_DELETE_TAIL_RECONCILIATION",
            )
        )
    if stock_voucher_state_boundary is not None:
        risks.append(
            _risk(
                "R-076",
                "stock-voucher confirmation has route-dependent validation, transaction and projection semantics",
                "CRITICAL",
                "stock_voucher_state_and_projection",
                ["inventory", "distribution", "sales", "accounting", "integration_migration"],
                "the target treats stock-voucher confirmation, unconfirmation and deletion as uniform row updates, or assumes that every managed route reaches one procedure under one physical transaction. Static SQL proves that dbo.USP_SDSNET_ConfirmVocher validates before starting its per-voucher transaction/savepoint, updates the confirmation header, and—only when there is no ambient transaction—contains a commit before inv.AfterInvVocherHdr. dbo.usp_sdsnet_Vocher_Save can wrap confirmation in an outer transaction, so the structural commit window must not be asserted for that route. Unconfirm validates first, then owns one transaction/savepoint that clears confirmation, may delete linked type-15 detail/item/header rows, invokes the after hook and commits with rollback handling. Active header and item triggers own StockGoods projection; they have replication-mode bypass, SET XACT_ABORT OFF and special voucher-type skips. Audit triggers retain full-row I/U/D lifecycle events but suppress one confirmed voucher-date-only update shape. Hash-pinned managed IL exposes two materially different families: thin business methods delegate to named-procedure adapters that execute and commit, while MainConfirmVocher has validator/writer overloads and a writer that uses dynamic header SQL routes before DataContext.Commit without calling those adapters. Runtime caller/overload selection and physical transaction enlistment across dynamic SQL, adapters and outer save remain unproven. The retained audit contains 75,569 confirmation transitions, 13,021 unconfirm transitions and 27,450 deletes; June-August 2026 contains 8,822, 1,771 and 3,200 respectively. Every retained delete is either after an unconfirm (10,458) or never confirmed (16,992), with zero direct confirmed delete without unconfirm. Current state has 96,495 confirmed and seven unconfirmed of 96,502 vouchers, while 15 historical insert-only absent IDs remain. A cardex-only comparison has 1,594 differences totaling 104,470 units, but the official legacy formula classifies exactly those values as open-sale stock obligations and has zero residual; they are not current stock mismatches. These clean aggregates do not prove route safety, runtime branch selection, physical transaction ownership or absence of a future partial outcome",
                [
                    "one versioned ConfirmStockVoucher and UnconfirmStockVoucher state machine with an explicit expected state and idempotency key",
                    "one declared physical transaction owner spanning validation, header state, linked type-15 cleanup, stock projection, accounting and outbox",
                    "replace trigger-only projection with an explicit deterministic projector while preserving documented special-type policy",
                    "deny or quarantine replication bypass unless a fenced replay protocol and post-run reconciliation prove convergence",
                    "route-parity tests for named-procedure adapters, dynamic MainConfirmVocher writers and outer Vocher_Save orchestration",
                    "append-only domain events and tombstones that preserve source lifecycle evidence without inventing actor, reason or route",
                    "official legacy-formula reconciliation as a release gate, preserving the 1,594 open-sale obligation keys separately from true residual mismatch",
                ],
                [
                    "all 96,502 current vouchers import with exactly 96,495 confirmed and seven unconfirmed states and no fabricated transition history",
                    "all 75,569 confirm, 13,021 unconfirm and 27,450 delete transitions replay deterministically; the 15 historical lifecycle gaps remain explicitly quarantined",
                    "every one of the 27,450 retained deletes remains classified as 10,458 after-unconfirm or 16,992 never-confirmed and no direct-confirmed-delete is introduced",
                    "fault injection before and after validation, header mutation, linked cleanup, projection, accounting and outbox yields one atomic outcome or a replayable failed attempt",
                    "named adapter, dynamic writer and outer-save Golden cases converge to identical policy while making their actual runtime route and physical transaction owner observable",
                    "replication-mode and special-voucher-type tests either produce the intended stock delta exactly once or fail before state advancement",
                    "official healthy, damaged and reserved cardex checks have approved explanations and zero unexplained residual before inventory write release",
                ],
                [
                    E["stock_voucher_state_boundary"],
                    E["stock_voucher_state_runtime_boundary"],
                    E["stock_reconciliation_diagnostic"],
                    E["stock_voucher_command_contract"],
                    E["migration"],
                ],
                "P0_BEFORE_STOCK_VOUCHER_CONFIRM_UNCONFIRM_DELETE_MIGRATION_OR_WRITE_UI",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_VOUCHER_LIFECYCLE_RECONCILIATION_AND_EXPLICIT_RUNTIME_LIMITS",
            )
        )
    if stock_projection_validation_boundary is not None:
        risks.append(
            _risk(
                "R-077",
                "post-voucher inventory validation can be advisory and outside the direct confirmation commit boundary",
                "CRITICAL",
                "stock_projection_validation_and_failure_semantics",
                ["inventory", "distribution", "sales", "accounting", "integration_migration"],
                "the target preserves Legacy message-return behavior or assumes that every post-voucher validation failure aborts the state transition. Hash-pinned static SQL proves that the direct no-ambient dbo.USP_SDSNET_ConfirmVocher route contains its first commit before invoking inv.AfterInvVocherHdr. It appends the output message to MsgErr and continues cursor processing without an abort guard. Unconfirm invokes the same After procedure before its commit, but likewise appends the output and then commits without testing the message. AfterInvVocherHdr has no local transaction, RAISERROR or THROW; it performs a type-20 batch IsDisabled update before validation, uses nine NOLOCK reads, calls four validation modules, skips the common on-hand/cardex checks for types 12 and 13, and runs cardex checks only for confirmed state. The confirmation After cursor also excludes the generated-type-15 mode. Header/item projection triggers can RAISERROR/ROLLBACK, while the StockGoods negative guard is set-based but has both session-context and replication bypass capabilities. The 50-row cardex-effect rule snapshot covers 30 voucher types with positive, negative, zero, healthy, damaged and reserved effects. Current aggregate evidence is clean: 67,161 StockGoods rows have zero negative components, StockGoodsDetail is empty, and official legacy-formula reconciliation has zero residual after preserving 1,594 open-sale obligation keys. Therefore no current validation failure or bypass incident is asserted, but message-only validation, route exemptions and a post-commit check must not be copied as a correctness boundary",
                [
                    "turn invariant validation into a typed precondition inside the same declared physical transaction as voucher state, projection, accounting and outbox",
                    "make every failed postcondition abort and expose a machine-readable error; never treat appended display text as transaction control",
                    "separate type-20 batch-state mutation from validation and ensure it is atomic with the accepted voucher transition",
                    "version the 50-row cardex-effect matrix and explicit type-12, type-13 and generated-type-15 exception policies",
                    "deny session-context and replication bypass by default; require a fenced maintenance command, actor, reason and mandatory reconciliation",
                    "route-parity and fault-injection tests across direct confirm, outer save, dynamic writer, unconfirm and generated voucher paths",
                ],
                [
                    "a forced failure from each of the four After validators leaves voucher state, type-20 batch state, StockGoods, accounting and outbox unchanged on every route",
                    "direct no-ambient, outer-save, adapter, dynamic-writer and unconfirm cases share one observable transaction owner and typed failure result",
                    "generated-type-15 and types 12/13 have owner-approved explicit invariants rather than silent omission from common checks",
                    "session-context and replication bypass tests require authorization, are audit-visible and end with zero official-formula residual",
                    "the 50 cardex-effect rows import as a versioned unique rule set for 30 voucher types and Golden deltas cover positive, negative, zero, healthy, damaged and reserved effects",
                    "the 67,161-row projection preserves zero negative component rows and the 1,594 open-sale obligations remain separate from true mismatch after repeatable migration",
                ],
                [
                    E["stock_projection_validation_boundary"],
                    E["stock_voucher_state_boundary"],
                    E["stock_voucher_state_runtime_boundary"],
                    E["stock_reconciliation_diagnostic"],
                    E["stock_voucher_command_contract"],
                    E["migration"],
                ],
                "P0_BEFORE_STOCK_VALIDATION_PROJECTION_OR_BYPASS_IMPLEMENTATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_WITH_READ_ONLY_RULE_MATRIX_AND_CURRENT_PROJECTION_RECONCILIATION",
            )
        )
    if distribution_exit_lifecycle_boundary is not None:
        risks.append(
            _risk(
                "R-078",
                "distribution exit issue and cancellation have caller-dependent atomicity and distinct physical-delete routes",
                "CRITICAL",
                "distribution_exit_lifecycle_and_transaction_ownership",
                ["distribution", "inventory", "sales", "accounting", "integration_migration"],
                "the target treats issue, merge, cancellation and physical deletion as one uniform command or assumes that a UI DataContext proves one shared database transaction. Hash-pinned SQL shows that dbo.usp_CreateExitVocherByDist validates and then writes exit, sale linkage, type-60 voucher graph and history before post-write cardex checking, with no local transaction or savepoint. inv.Usp_RemoveExitFromDist validates, deletes the voucher graph, unlinks sales, soft-cancels the exit, writes history and resets distribution state; it has no local BEGIN/COMMIT, although its catch can roll back an ambient transaction. Hash-pinned IL proves the ordinary issue UI constructs a DataContext, calls create and then commits; the ordinary removal UI validates before constructing a DataContext, then calls remove and commits. The business methods instantiate thin adapters, and the adapters query their procedures without a local Commit, so physical enlistment between the UI context and nested adapter-created contexts is not proven. MergeGoodsExitData delegates to an adapter Execute route with no explicit UI or adapter commit in the selected IL. Three SQL modules separately contain direct physical tblExit deletion, and only USP_VSA_ChangeDistStatus has a local transaction. Current aggregate evidence is clean and must not be misread as an incident: 33,945 exits comprise 24,035 active and 9,910 cancelled rows; every active exit has exactly one type-60 voucher, every cancellation has a type-60 delete event and no lingering sale link, and all 1,442 recent cancellations were paired within five seconds. General audit has 33,953 logged exit identities but eight historical identities absent from the live table, all dated March 28-30 2024 before the currently inspected delete trigger; there is no retained DELETE operation row and no recent absent exit. Distribution history has zero chain breaks and six corresponding historical absent distributions. Thus no current partial issue, cancellation, or unauthorized delete incident is asserted; the risk is copying caller-dependent transaction ownership, merge ambiguity, and soft-cancel/physical-delete divergence into the web ERP",
                [
                    "define typed IssueDistributionExit, CancelDistributionExit and exceptional PhysicalDeleteExit commands with separate authorization and invariants",
                    "place exit, sale linkage, type-60 voucher, voucher items, stock projection, accounting, history and outbox under one explicit transaction owner",
                    "run all stock/cardex preconditions before durable state advancement and make postconditions abort with typed errors",
                    "make soft cancellation the default; fence physical deletion behind explicit recovery policy, actor, reason and immutable audit",
                    "make merge ownership explicit and prohibit adapter-created untracked transaction contexts",
                    "preserve versioned distribution-status transitions and reconcile current exits, vouchers, sales and history after every replay or repair",
                ],
                [
                    "fault injection at each create and cancel write leaves either the complete accepted outcome or no state change across every caller",
                    "UI, API, batch, replication and recovery callers expose the same observable physical transaction id and command id",
                    "merge has a declared owner, finite failure result and deterministic replay behavior with no uncommitted or partial exit state",
                    "24,035 active exits retain a one-to-one type-60 voucher and sale linkage; 9,910 cancellations retain no live voucher or sale link and preserve complete history",
                    "physical deletion requires separately approved permission, cannot bypass immutable audit, and has Golden cases for all three legacy candidate shapes",
                    "the eight pre-trigger historical absences and six distribution histories are quarantined without fabricating attribution; no new unexplained absence appears after migration",
                ],
                [
                    E["distribution_exit_lifecycle_boundary"],
                    E["distribution_exit_runtime_boundary"],
                    E["distribution_path_diagnostic"],
                    E["distribution_sql_semantics"],
                    E["distribution_source_model"],
                    E["distribution_trigger_transitive_graph"],
                    E["stock_projection_validation_boundary"],
                    E["migration"],
                ],
                "P0_BEFORE_DISTRIBUTION_EXIT_ISSUE_CANCEL_MERGE_OR_DELETE_IMPLEMENTATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_CURRENT_AND_HISTORICAL_EXIT_RECONCILIATION",
            )
        )
    if sale_conversion_state_boundary is not None:
        risks.append(
            _risk(
                "R-079",
                "order-to-sale conversion has rollback-mode branching, nested commit signals and trigger-owned projections",
                "CRITICAL",
                "sale_conversion_atomicity_state_projection_and_deletion",
                ["sales", "inventory", "distribution", "receivables_treasury", "accounting", "integration_migration"],
                "the target treats order conversion as a simple one-row Order-to-Invoice insert, copies the legacy WithOutRollback switch, exposes legacy chkNot* inputs as ordinary API booleans, or assumes nested DataContext Commit calls prove one transaction. Hash-pinned SQL shows that SLE.usp_sdsnet_CreateSaleByOrder has local transaction/try/catch/commit/rollback control plus a WithOutRollback branch; it calls the transaction-free core SLE.usp_CreateSaleByOrder before updating the selected SaleHdrRef and also mutates conversion timing, payment, batch, reserved-prize and sale-item-detail state, with dynamic SQL capability. The policy inputs are not equivalent booleans: chkNotStock=1 removes short items from the temporary conversion set and continues only when an item remains; contract-price, conditional user-price and maximum-limit checks have distinct skip branches; both customer-credit flags or both dealer-credit flags must be 1 to bypass their validator, otherwise caller values are overwritten from DC configuration; IgnoreValidateExpDate is declared but has no current wrapper use. Static UI IL proves the bulk form reads stock, customer/dealer credit and maximum-limit controls while forcing both price flags to zero; the ordinary Sale save forces both price flags to zero and reads only its stock field. The bulk-form controls are driven by three-state server configuration, not an observed identity permission decision: five credit/limit settings use 0=locked bypass, 1=user-selectable default enforcement and 2=locked enforcement, while stock uses 0=user-selectable strict, 1=locked partial conversion and 2=locked strict. The selected method named ApplySetadPermission only derives Select-button enablement from SiteType and DCRef. The current anonymous two-DC snapshot has stock=2 in both profiles; one profile has all five credit/limit values=2 and the other has five NULLs. Entity getters return non-nullable CLI Int32 while SQL reloads customer/dealer values without NULL coalescing, so the UI materialization of those NULLs is unproven and the SQL validator condition can evaluate UNKNOWN when both reloaded values are NULL. Hash-pinned operation-date evidence adds a separate temporal boundary: both bulk conversion routes copy the session sale operation date into CreateSaleDate; the desktop gate can require the SetOprDate form under the named VN.SDS.Sales/SetOprDate permission and otherwise auto-selects the second FetchReason=2 output, proven to be OprDate rather than LastDate. The server core reuses that date for price, contract-price, date-open, EVC and customer-limit decisions. For ordinary order types it rejects a closed sale period or CreateSaleDate less than or equal to LastDate, but skips this date-open check for types 1007/1008; the selected date-open procedure has no explicit missing-boundary rejection and can therefore fail open through SQL NULL logic. Hash-pinned authorization evidence finds no named permission/access call in the exact conversion form or seven selected conversion methods. The separate order-type rights helper covers View/New/Edit/Delete/Cancel/Confirm/Unconfirm and its ten UI callsites are confined to order-list forms, not the conversion form. The wrapper has only a conditional customer-sale-area scope gate; both its global AreaAccess key and the client general AreaAccess setting are disabled in the clone, and the core accepts UserRef without a named action-authorization dependency. This does not disprove outer menu/base-form authorization, but it does block treating page access or legacy list rights as server conversion authority. These modes therefore encode privileged policy, partial-conversion intent, temporal finality, action/resource authorization and NULL/missing-boundary resolution, not portable request fields. Header triggers separately own SaleHdrDetail insertion, payment deletion on cancellation, and StockGoods mutation; the replication delete trigger is active and bypassable. Hash-pinned IL also proves the Sale form delegates without a context, SaleHandler creates a DataContext, calls CreateSaleByOrder and commits without an explicit RollBack signal, while OrderAdapter creates another DataContext, executes the named orchestrator and commits. A second OrderHandler overload directly queries the legacy core without a local Commit. Which overload and policy mode executes on every branch, and whether business/adapter contexts share one physical transaction, are not proven. Current evidence must be interpreted by state semantics: 275,995 sales include 214,973 active and 61,022 cancelled; 18,009 orders have multiple attempts but none has multiple active sales, selected-pointer dangling and reverse mismatch are zero. Of 26,624 raw Header/latest-Detail status differences, 26,618 are the expected cancellation projection shape (Status 0 detail versus preserved Header status), leaving six active mismatches and three cancelled unexpected terminal details, all non-recent. Conversion timing is not a complete attempt ledger: 9,809 sale-bearing orders lack timing and nine timing-bearing orders lack a sale. General audit records 640 physical deletes, including 112 recent, and all 640 IDs are absent; 18 additional absent IDs have no retained delete, all non-recent. The only catalogued direct SaleHdr delete candidate is the transactional free-invoice confirmation procedure, but capability and timing do not prove attribution. Therefore no current duplicate-active-sale, unauthorized conversion incident or recent state-projection exception is asserted; the risk is copying mode-dependent rollback, caller-selectable validation modes, temporal/missing-row fail-open behavior, absent command authorization, NULL/default ambiguity, nested ownership ambiguity, trigger side effects and incomplete attempt/delete evidence into the web ERP",
                [
                    "implement ConvertOrderToSale as one idempotent command with a single injected transaction owner and explicit typed rollback policy",
                    "remove caller-selectable WithOutRollback behavior from public/API inputs; model approved partial/recovery flows as separate fenced commands",
                    "do not expose chkNot* booleans in the public command; resolve versioned stock, price, customer/dealer credit and maximum-limit policy server-side from actor, scope and order type",
                    "model stock-shortage partial conversion as a separately authorized command with an explicit selected/rejected item outcome, never as validation bypass",
                    "define one typed three-state policy enum per rule, validate every DC configuration and fail closed on NULL or unknown values before command dispatch",
                    "resolve operation date server-side from an explicit scoped boundary; require exactly one current sale-period row and fail closed on missing, ambiguous, closed or non-forward dates",
                    "treat SetOprDate as a distinct privileged temporal action, preserve the 1007/1008 exception only with owner approval, and never trust a client-supplied session date as final authority",
                    "enforce distinct server-side ConvertOrderToSale, ConvertOrderToSalePartially, OverrideCredit and SetSaleOperationDate actions; derive actor from the authenticated principal and deny by DC, office, order type, customer area, order and stock scope",
                    "do not treat form access, order-list View/Edit/Confirm rights or the conditionally disabled legacy AreaAccess gate as conversion authorization",
                    "include sale header/items, selected-order pointer, timing attempt, payments, batches, reserved prizes, stock projection, detail events, accounting and outbox in one atomic boundary",
                    "replace trigger-owned state with explicit versioned SaleStateEvent and projection handlers tested in the same unit of work",
                    "retain every conversion attempt and physical-delete tombstone with command id, expected version, actor, reason and immutable audit",
                    "reconcile Header/latest Detail by semantic terminal-state mapping so expected cancel Status=0 is not reported as corruption",
                ],
                [
                    "fault injection at every legacy mutation point yields one complete conversion or zero state change across UI, API, batch and replication callers",
                    "all callers expose one physical transaction id; nested adapter Commit cannot independently publish a partial conversion",
                    "ordinary conversion callers cannot supply policy-bypass values; privileged partial conversion and credit override require separate permission, reason, policy version and immutable audit",
                    "Golden cases prove contract-price, user-price, customer/dealer credit, maximum-limit and stock-shortage behavior including both partial-item and all-items-rejected outcomes",
                    "both current anonymous DC profiles migrate with an explicit owner-approved mapping; the five NULL values are resolved or quarantined and cannot silently become bypass",
                    "operation-date Golden cases cover closed, equal, before, after, missing and duplicate boundaries plus the approved disposition of order types 1007/1008",
                    "direct API negative tests deny principals with page/list rights but without conversion action, plus cross-DC, cross-office, cross-area, unscoped-customer and partial-conversion escalation attempts",
                    "same-key retry returns the original Sale attempt and never creates more than one active selected sale per order",
                    "all 18,009 multi-attempt orders preserve history while selected-pointer dangling, reverse mismatch and multiple-active counts remain zero",
                    "the six active and three cancelled historical projection exceptions are explained or quarantined, and no new exception appears in a replayed migration",
                    "conversion-attempt ledger covers the 9,809 sale-without-timing and nine timing-without-sale historical gaps without fabricating missing outcomes",
                    "640 retained physical deletes and 18 no-delete absences migrate as tombstones with the 112 recent deletes auditable; no deletion is attributed to a procedure without direct evidence",
                ],
                [
                    E["sale_conversion_state_boundary"],
                    E["sale_conversion_runtime_boundary"],
                    *(
                        [E["order_sale_policy_flag_sql"], E["order_sale_policy_flag_runtime"]]
                        if order_sale_policy_flag_sql is not None
                        else []
                    ),
                    *(
                        [E["order_sale_policy_gate_runtime"], E["order_sale_policy_config_snapshot"]]
                        if order_sale_policy_gate_runtime is not None
                        else []
                    ),
                    *(
                        [E["order_sale_operation_date_sql"], E["order_sale_operation_date_runtime"]]
                        if order_sale_operation_date_sql is not None
                        else []
                    ),
                    *(
                        [E["order_sale_authorization_sql"], E["order_sale_authorization_runtime"]]
                        if order_sale_authorization_sql is not None
                        else []
                    ),
                    *(
                        [E["datacontext_transaction_runtime"]]
                        if datacontext_transaction_runtime is not None
                        else []
                    ),
                    *(
                        [E["order_sale_evc_sql_boundary"], E["order_sale_evc_runtime_boundary"]]
                        if order_sale_evc_sql_boundary is not None
                        else []
                    ),
                    *(
                        [E["discount_v2_query_contracts"], E["discount_v2_dataset_sql"]]
                        if discount_v2_query_contracts is not None
                        else []
                    ),
                    *(
                        [E["discount_v2_engine_runtime"], E["discount_v2_dynamic_rule_sql"]]
                        if discount_v2_engine_runtime is not None
                        else []
                    ),
                    *(
                        [E["discount_v2_condition_families"]]
                        if discount_v2_condition_families is not None
                        else []
                    ),
                    *(
                        [E["discount_rule_authoring_boundary"]]
                        if discount_rule_authoring_boundary is not None
                        else []
                    ),
                    *(
                        [E["discount_rule_authorization_boundary"]]
                        if discount_rule_authorization_boundary is not None
                        else []
                    ),
                    E["order_sale_command_contracts"],
                    E["order_sale_dependency_graph"],
                    E["order_sale_sql_semantics"],
                    E["order_sale_source_model"],
                    E["order_sale_trigger_transitive_graph"],
                    E["stock_projection_validation_boundary"],
                    E["migration"],
                ],
                "P0_BEFORE_ORDER_TO_SALE_CONVERSION_CANCEL_OR_DELETE_IMPLEMENTATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_SALE_STATE_ATTEMPT_AND_DELETE_RECONCILIATION",
            )
        )
    if sale_cancellation_boundary is not None:
        risks.append(
            _risk(
                "R-080",
                "sale cancellation spans payment deletion, order state, stock projection and retained exit links",
                "CRITICAL",
                "sale_cancellation_atomicity_and_cross_domain_projection",
                ["sales", "inventory", "distribution", "receivables_treasury", "accounting", "integration_migration"],
                "the target models cancellation as a Boolean update or assumes the desktop UI, business handler and adapter share one managed transaction. Hash-pinned SQL shows dbo.usp_sdsnet_Sale_Cancel owns a local transaction with try/catch/commit/rollback and directly mutates sale, order, payment and detail state; enabled SaleHdr triggers additionally delete direct sale payments, write terminal detail and update stock projection. The procedure has no direct Exit/Distribution dependency. Hash-pinned IL shows FormSaleList constructs a cancellation-reason form then calls SaleHandler without an explicit DataContext; SaleHandler is a thin delegate; SaleAdapter constructs a DataContext and executes the named procedure but has no explicit Commit or RollBack signal. The SQL-local transaction is therefore the proven owner, while physical enlistment with the managed context remains unproven. Current aggregate state has 61,022 cancelled sales and zero retained direct payments. Status 3 contains 34,401 cancellations and every one retains both ExitRef and DistRef to an active exit; 34,630 cancelled sales remain selected by an order and 34,397 of those orders are active. This is a state shape, not asserted corruption: the cancellation procedure does not directly own exit/distribution cleanup, so migration must preserve or explicitly replace this cross-command contract. Terminal detail has 61,019 expected Status 0/3 outcomes and three historical exceptions, with no recent exception. No live failure or unauthorized cancellation is asserted; the risk is losing atomic payment cleanup, order selection semantics, stock reversal, reason capture and retained distribution/exit relationships when the web command is redesigned",
                [
                    "implement CancelSale as an idempotent version-checked command with one explicit SQL transaction owner",
                    "include payment removal, order state/selection, sale terminal event, stock projection, accounting, reason and outbox in the declared unit of work",
                    "model cancellation states by semantic transition rather than a naked CancelFlag or numeric Header/Detail equality",
                    "define whether linked active exits/distributions are retained, separately cancelled or compensated; never unlink them implicitly",
                    "preserve cancellation reason, actor, operation date, command id and immutable before/after audit",
                    "replace trigger-only effects with explicit handlers or prove equivalent transactional trigger behavior",
                ],
                [
                    "fault injection at each procedure and projection mutation leaves either the complete cancellation or the original sale",
                    "retry returns the prior cancellation and cannot duplicate reversal, payment deletion, stock movement or accounting effects",
                    "all 61,022 cancelled sales retain zero direct payments and a valid terminal event under the versioned state mapping",
                    "the 34,401 status-3 exit/distribution links and 34,630 selected-order links migrate under an approved invariant with no fabricated cleanup",
                    "the three historical terminal exceptions are quarantined and no recent or replay-generated exception appears",
                    "UI, API, batch and recovery callers expose the same transaction, authorization, operation-date and reason requirements",
                ],
                [
                    E["sale_cancellation_boundary"],
                    E["sale_cancellation_runtime_boundary"],
                    E["sale_conversion_state_boundary"],
                    E["sale_conversion_runtime_boundary"],
                    E["order_sale_command_contracts"],
                    E["order_sale_trigger_transitive_graph"],
                    E["distribution_exit_lifecycle_boundary"],
                    E["stock_projection_validation_boundary"],
                    E["migration"],
                ],
                "P0_BEFORE_SALE_CANCELLATION_OR_REVERSAL_IMPLEMENTATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_CANCELLATION_LINK_AND_TERMINAL_STATE_RECONCILIATION",
            )
        )
    if return_issue_cancel_boundary is not None:
        risks.append(
            _risk(
                "R-081",
                "sales-return issue and cancellation combine stock entry, credit cleanup and layered transaction owners",
                "CRITICAL",
                "sales_return_issue_cancel_stock_credit_atomicity",
                ["sales", "inventory", "distribution", "receivables_treasury", "accounting", "integration_migration"],
                "the target treats a sales return as one header flag, infers current voucher existence from VocherFlag, or splits stock entry and return credit across independently committed calls. Hash-pinned SQL shows dbo.usp_Sdsnet_RetSale_Save is a transaction/savepoint orchestrator that reaches issue, cancel-voucher and cancel-header routes and can delete payment and voucher state. dbo.USP_SDSNET_GenerateRetSaleVocher also owns transaction/savepoint control, inserts type-10 voucher header/items/details, updates VocherFlag and can create return-credit payment; some packaging, batch and completeness validations occur after voucher inserts. SLE.usp_AfterSaveRetSale has no local transaction yet can roll back. Cancellation is also layered: dbo.USP_SDSNET_GenerateCancelRetSaleVocher has a local transaction, mutates the voucher graph with both delete and insert operations and invokes stock checking, while SLE.USP_SDSNET_CancelRetSaleHdr separately updates CancelFlag and removes pay-with-payment relationships. Hash-pinned IL proves the UI delegates cancellation without a context, Business methods are thin delegates, the issue Adapter queries the named generator without explicit context construction or Commit/RollBack, and the cancellation Adapter creates a context, reaches both named cancellation procedures and commits without explicit RollBack. Physical enlistment across managed and SQL-local transactions is not proven. Current state is clean and must not be called an incident: all 13,913 active returns have exactly one confirmed type-10 voucher; all 178 cancelled returns have no current type-10 voucher or payment, although all retain VocherFlag=1, proving the flag is historical state rather than current projection existence. Two cancellations are in the three-month business-date window. General audit covers all 14,091 current return identities with no delete or absence; three direct physical-delete modules are capability only and are not attributed to any event. The risk is reproducing layered commit ownership, post-write validation, destructive compensation and ambiguous flag semantics in the web ERP",
                [
                    "implement idempotent version-checked IssueSalesReturn and CancelSalesReturn commands under one injected transaction owner",
                    "include return header/items, type-10 voucher, stock projection, credit/payment pairs, accounting, audit and outbox in the same atomic boundary",
                    "move amount, quantity, packaging, batch, stock and completeness preconditions before the first durable write",
                    "replace VocherFlag with an explicit Draft/Issued/Cancelled state machine and derive current voucher existence from the projection relation",
                    "represent cancellation with immutable compensating events; retain physical deletes only as internal transactional cleanup with tombstones",
                    "make retry return the prior outcome without duplicating voucher, stock, credit, payment or accounting effects",
                ],
                [
                    "fault injection at every save, voucher, payment, stock-check and cancel step yields one complete outcome or no state change",
                    "all callers expose one physical transaction id and prove that nested SQL transactions cannot independently publish partial state",
                    "13,913 active returns retain one confirmed type-10 voucher and 178 cancellations retain no live voucher or payment after migration replay",
                    "VocherFlag=1 on cancelled returns is migrated as issuance history, never treated as proof of a live voucher",
                    "same-key issue/cancel retries produce no duplicate voucher, payment, stock movement, accounting entry or compensation",
                    "the three direct-delete capabilities require separate recovery authorization and immutable audit; no historical deletion is fabricated",
                ],
                [
                    E["return_issue_cancel_boundary"], E["return_issue_cancel_runtime_boundary"],
                    E["sales_return_amount_diagnostic"], E["distribution_source_model"],
                    E["distribution_trigger_transitive_graph"], E["stock_projection_validation_boundary"],
                    E["sale_cancellation_boundary"], E["migration"],
                ],
                "P0_BEFORE_SALES_RETURN_ISSUE_CANCEL_STOCK_OR_CREDIT_IMPLEMENTATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_RETURN_VOUCHER_PAYMENT_AND_AUDIT_RECONCILIATION",
            )
        )
    if sale_voucher_snapshot_boundary is not None:
        risks.append(
            _risk(
                "R-082",
                "sale voucher snapshots have distinct lifecycle, retained cancellation history and a multi-aggregate reverse command",
                "CRITICAL",
                "sale_voucher_snapshot_version_and_reverse_atomicity",
                ["sales", "inventory", "distribution", "receivables_treasury", "accounting", "integration_migration"],
                "the target treats tblSaleVocherHdr/Itm as a mutable mirror of the current sale, deletes it implicitly on cancellation, assumes its amount must always equal the current sale amount, or implements reverse conversion as a status update. Hash-pinned SQL shows SLE.usp_FillSaleVocher inserts the snapshot header and several item/detail graphs without a local transaction and is reached from the transaction/savepoint order-to-sale orchestrator. dbo.usp_sdsnet_ConvertSaleToVocher is a separate local-transaction Try/Catch Commit/RollBack reverse route that coordinates sale, snapshot, payment, return, numbering and distribution-discount state. SLE.usp_RollbackDisSaleSaleVocher deletes and rebuilds discount subgraphs without a local transaction, while sale cancellation does not directly delete the snapshot header. Hash-pinned IL proves UI delegation, then a Business-created context that validates before calling the Adapter, and an Adapter-created context that queries the named conversion procedure; none of the selected managed methods has explicit Commit/RollBack and physical enlistment with the SQL-local transaction is not proven. Current number and graph reconciliation is clean: all 266,183 sales with voucher numbers have exactly one snapshot, with no number mismatch, duplicate, orphan header or orphan item; 60,698 cancelled sales intentionally retain snapshots. The 11,750 active final sales whose current amount differs from the captured snapshot, including 1,537 in the three-month window, occur only in one valid state shape and must not be called corruption without a version/stage rule. General audit has 18 historical absent identities, no retained delete event and no recent absence. The one direct-delete module is capability only and is not attributed to any event. The risk is losing historical version semantics or partially reversing payment, numbering, discount, return and sale state in the web ERP",
                [
                    "model SaleSnapshot as an immutable version with captured stage, source version and timestamp rather than a mutable Sale copy",
                    "keep order-to-sale, snapshot graph, payment, stock, audit and outbox under one injected transaction owner",
                    "implement idempotent version-checked ReverseSaleVoucher with explicit compensating events for numbering, payment, discounts and returns",
                    "separate sale cancellation, snapshot retention and reverse conversion as distinct authorized commands",
                    "define the approved current-versus-snapshot amount rule before classifying or migrating the 11,750 differences",
                    "restrict FreeInvoice deletion and replication bypass with tombstones, recovery authorization and immutable audit",
                ],
                [
                    "every voucher-numbered sale has exactly one snapshot and every snapshot item has a valid header after migration and replay",
                    "fault injection at each snapshot, payment, numbering, discount and return mutation leaves either the complete reverse outcome or the original state",
                    "same-key issue or reverse retries cannot duplicate snapshots, payments, numbers, stock, discounts, returns or outbox events",
                    "all 60,698 cancelled retained snapshots preserve their approved historical meaning and are never reactivated as current sales",
                    "the 11,750 amount differences are classified by an approved stage/version rule; no corruption label is inferred from inequality alone",
                    "the 18 historical absent identities and direct-delete capability remain quarantined without fabricated attribution",
                ],
                [
                    E["sale_voucher_snapshot_boundary"], E["sale_voucher_snapshot_runtime_boundary"],
                    E["sale_conversion_state_boundary"], E["sale_cancellation_boundary"],
                    E["return_issue_cancel_boundary"], E["migration"],
                ],
                "P0_BEFORE_SALE_SNAPSHOT_OR_REVERSE_CONVERSION_IMPLEMENTATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_AND_IL_WITH_READ_ONLY_ANONYMOUS_SNAPSHOT_NUMBER_AMOUNT_AND_AUDIT_RECONCILIATION",
            )
        )
    if sale_accounting_crosswalk_boundary is not None:
        risks.append(
            _risk(
                "R-083",
                "sale finality, sale snapshot capture and accounting issuance are independent watermark-driven states",
                "CRITICAL",
                "sale_accounting_issuance_watermark_and_lineage",
                ["sales", "receivables_treasury", "accounting", "integration_migration"],
                "the target posts every finalized sale synchronously, treats absence of current PreVoucher rows as a data-loss incident or proof of historical non-issuance, requires tblSaleVocherHdr as the accounting source, or validates accounting by comparing total debit directly with Sale.TotalAmount. Read-only reconciliation shows 202,636 active finalized sales map to 625,839 balanced sale-creator lines, 101,649 external batches and exactly one active journal per source link, with no orphan, duplicate-source-batch or unbalanced group. Another 10,123 active finalized sales have no accounting source: 10,122 are the entire open 1405/05 cohort while 1405/03 and 1405/04 are fully issued; this watermark-shaped current month must not be called an incident, and the one 1403/01 outlier needs separate accountant disposition. The hash-pinned creator view reads non-cancelled numbered SaleHdr/SaleItm rows with NOLOCK, ignores the sale snapshot, and excludes cancelled state. Consequently zero current cancelled-sale sources does not prove historical non-issuance or explain any earlier reversal/deletion. Snapshot and accounting are independent: among active final sales 9,008 have accounting without a snapshot, 9,643 have a snapshot without accounting, 480 have neither and 193,628 have both; 72,555 snapshots lack current accounting sources, including 60,698 cancelled snapshots. Historical grouping also differs from current policy: 370 multi-source batches contain 101,357 source assignments and one batch reaches 1,131 sources. Finally 175,042 balanced accounting sources have total debit different from Sale.TotalAmount because the creator can include receivable, revenue, tax, discount and cost lines; these must not be called an accounting mismatch without rule-level parity. Both staging procedures lack a local transaction and rely on the previously proven managed owner. The risk is collapsing independent states, advancing or skipping the issuance watermark, recreating historical grouping from current policy, or losing reversal lineage in the web ERP",
                [
                    "model Finalized, SnapshotCaptured, AccountingEligible, AccountingIssued, Posted and Reversed as separate versioned states",
                    "persist an accounting-run watermark, committed source snapshot, creator rule version, grouping policy version and run id",
                    "classify an unissued sale as Pending while it is inside the open watermark and as Exception only after a closed-run reconciliation",
                    "preserve Sale to Draft to Batch to Journal crosswalk and explicit reversal events without requiring a sale-snapshot foreign key",
                    "validate financial parity with approved creator line golden cases rather than direct debit-to-sale-total equality",
                    "remove NOLOCK from financial source selection and keep the whole issuance run under one server-side transaction owner",
                ],
                [
                    "closed watermark replay issues each eligible sale once and leaves open-month sales pending without false alerts",
                    "all 202,636 current sources remain balanced and resolve through one batch link to one active journal after migration",
                    "the 10,122 open-month rows and one historical outlier remain separately classified with owner-approved disposition",
                    "all four snapshot/accounting quadrants migrate without synthesizing missing snapshots or accounting history",
                    "historical multi-source batches preserve their recorded grouping policy and are never regrouped from current configuration",
                    "golden rule tests explain debit, credit and dimensions for source lines; the 175,042 non-equalities are not failed by a false total invariant",
                ],
                [
                    E["sale_accounting_crosswalk_boundary"], E["sale_voucher_snapshot_boundary"],
                    E["accounting_voucher_entrypoints"], E["voucher_creation_policy"],
                ],
                "P0_BEFORE_SALE_ACCOUNTING_ISSUANCE_OR_REVERSAL_IMPLEMENTATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_WITH_READ_ONLY_ANONYMOUS_SALE_SNAPSHOT_STAGE_BATCH_JOURNAL_AND_WATERMARK_RECONCILIATION",
            )
        )
    if sale_invoice_print_boundary is not None:
        risks.append(
            _risk(
                "R-084",
                "invoice output depends on external Crystal templates while physical-print audit is a separate mutable command",
                "CRITICAL",
                "invoice_template_parity_print_receipt_and_void_reprint",
                ["identity_authorization", "sales", "distribution", "reporting_documents", "integration_migration"],
                "the target rebuilds invoice output from UI fields or guessed SQL candidates, treats preview as equivalent to successful physical print, makes the print-audit row unique per sale, or reprints cancelled sales without an explicit VOID/archive policy. Hash-pinned IL proves FormReportFactor resolves a configured ReportFile filename, then Crystal ReportDocument loads the external template, sets parameters, applies the current application database connection to report and subreport tables and supports a CustomReps override. Exact embedded query, formulas, layout and result parity are therefore template-owned, not DataAccess-owned. Six configured invoice templates exist with one default, but none of their hashed filenames matched the 88 .rpt/.mrt files in the three scanned deployed roots; this does not prove a runtime load failure because another current directory, cache or distribution source may exist, but it blocks implementation parity. Only after the engine reports PrintedCompleted does UI call the Business audit route. The route creates DocType=2 rows in one context, SaveCommands them and commits without explicit RollBack in the selected method. Current audit is intentionally event-shaped: 308,432 sale print events cover 144,847 sales, 34,840 sales were printed more than once and one reached 26 prints; 68 audited sale identities are absent currently and are not attributed to deletion. There are also 143 print events on 45 currently cancelled sales after their terminal detail timestamp, including two recent; these must not be called unauthorized because archival or approved VOID reprint intent is unknown, but the target needs explicit policy and watermark. A sibling dynamic list procedure reuses DistNo1 as both range bounds, and an alternate direct insert procedure has a hard-coded old KindPrint=0 scope and no local transaction. The alternate procedure has no SQL dependency and no exact deployed binary literal, so it is capability only, not an active path. The risk is shipping legally or financially different invoice output, recording preview/failure as print, losing repeat-attempt audit, or allowing unmarked cancelled output",
                [
                    "obtain every effective Crystal template and extract its table, command, formula, parameter and subreport contract by hash",
                    "version and sign templates; persist template hash, data watermark, parameter hash and output hash on each print job",
                    "keep PreviewInvoice pure and authorize MarkInvoicePrinted only from a trusted spooler success receipt",
                    "model PrintJob attempts idempotently while retaining legitimate repeated prints and their outcomes",
                    "require separate permission and visible VOID/archive watermark for any print of a cancelled sale",
                    "remove or deny the dormant hard-coded procedure and repair the distribution upper-bound selection with regression tests",
                ],
                [
                    "owner-approved Golden PDF and source-data snapshots pass for all six configured templates and each CustomReps override",
                    "preview, export, render failure and spool failure create no successful print audit event",
                    "same print-job retry creates one success event while a separately authorized reprint creates a new linked attempt",
                    "all current 308,432 sale print events migrate as event history without a false unique-sale constraint",
                    "cancelled-sale reprint is denied by default and approved VOID/archive output always includes policy decision and watermark",
                    "multi-distribution range tests honor both bounds and no deployed caller can reach hard-coded legacy scope",
                ],
                [
                    E["sale_invoice_print_boundary"], E["sale_invoice_print_runtime_boundary"],
                    E["report_target_contracts"], E["report_evidence_gaps"], E["sale_cancellation_boundary"],
                ],
                "P0_BEFORE_INVOICE_REPORT_OR_PRINT_AUDIT_IMPLEMENTATION",
                "financial_controller",
                "CONFIRMED_HASH_PINNED_STATIC_SQL_IL_AND_DEPLOYMENT_WITH_READ_ONLY_ANONYMOUS_TEMPLATE_AND_PRINT_EVENT_RECONCILIATION",
            )
        )
    risks.sort(key=lambda row: row["id"])
    module_ids = {row["module"] for row in matrix["modules"]}
    role_ids = {row["role"] for row in roles["role_templates"]}
    allowed_owners = role_ids | {"delivery_team", "user_decision"}
    ids = [row["id"] for row in risks]
    errors = []
    expected_last_risk = (
        84
        if sale_invoice_print_boundary is not None
        else 83
        if sale_accounting_crosswalk_boundary is not None
        else 82
        if sale_voucher_snapshot_boundary is not None
        else 81
        if return_issue_cancel_boundary is not None
        else 80
        if sale_cancellation_boundary is not None
        else 79
        if sale_conversion_state_boundary is not None
        else 78
        if distribution_exit_lifecycle_boundary is not None
        else 77
        if stock_projection_validation_boundary is not None
        else 76
        if stock_voucher_state_boundary is not None
        else 75
        if received_cheque_delete_boundary is not None
        else 74
        if received_cheque_undo_boundary is not None
        else 73
        if payable_cheque_undo_boundary is not None
        else 72
        if supplier_unapply_delete_boundary is not None
        else 71
        if supplier_cost_apply_boundary is not None
        else 70
        if ngt_order_deletion_boundary is not None
        else 69
        if ngt_order_history_boundary is not None
        else 68
        if ngt_sale_replication_boundary is not None
        else 67
        if ngt_return_replication_boundary is not None
        else 65
        if ngt_replication_compensation_boundary is not None
        else 64
        if ngt_payment_replication_boundary is not None
        else 63
        if ngt_payment_settlement_boundary is not None
        else 62
        if ngt_tour_call_state_boundary is not None
        else 61
        if configuration_precedence_boundary is not None
        else 60
        if ngt_operation_date_boundary is not None
        else 59
        if ngt_owner_scope_effective is not None
        else 58
        if ngt_authorization_effective is not None
        else 56
    )
    if ids != [f"R-{number:03d}" for number in range(1, expected_last_risk + 1)]:
        errors.append("risk id sequence mismatch")
    if ngt_tour_call_state_boundary is not None:
        if len(tour_lifecycle_endpoints) != 29:
            errors.append("NGT tour lifecycle endpoint selection count mismatch")
        if sum("GET" in row["http_verbs"] for row in tour_lifecycle_endpoints) != 24:
            errors.append("NGT tour lifecycle GET endpoint count mismatch")
        if sum("POST" in row["http_verbs"] for row in tour_lifecycle_endpoints) != 5:
            errors.append("NGT tour lifecycle POST endpoint count mismatch")
        if any(row["ngt_authorize_attribute_count"] != 1 for row in tour_lifecycle_endpoints):
            errors.append("NGT tour lifecycle authorization declaration mismatch")
    if datacontext_transaction_runtime is not None:
        r079 = next(row for row in risks if row["id"] == "R-079")
        r079["failure_mode"] = r079["failure_mode"].replace(
            "Which overload and policy mode executes on every branch, and whether business/adapter contexts share one physical transaction, are not proven.",
            "The package-wide DataContext analysis resolves the selected physical ownership: default contexts are non-transactional and independently connected; the adapter overload uses Transaction.Begin, while Discount V2 EVC preparation uses a separate Transaction.No context whose Commit is a no-op before V2 calls the transactional adapter overload. Reflection or code outside the inventoried package remains unproven.",
        ).replace(
            "nested ownership ambiguity",
            "the proven split EVC-preparation/conversion transaction boundary",
        )
    if order_sale_evc_sql_boundary is not None:
        r079 = next(row for row in risks if row["id"] == "R-079")
        r079["failure_mode"] += (
            " The Discount V2 boundary further proves a two-calculation fallback: the helper flag defaults to zero and has no typed setter after construction across 59 managed assemblies, so the SQL wrapper normally rebuilds legacy EVC staging on the conversion connection. The managed sharp-payment-usance writer also targets #SaleSaleItemPaymentUsance while runtime creation and every SQL consumer use #SaleItemPaymentUsance; no SQL or managed CREATE literal for the doubled name was found. BackgroundWorker cancellation is checked before the selected per-order conversion call and has no DbCommand.Cancel/CancellationToken path, so stopping a batch is an inter-order StopAfterCurrent boundary rather than rollback of prior commits. This is structural reachability evidence, not a claim that the empty-current-clone branch failed historically."
        )
        r004 = next(row for row in risks if row["id"] == "R-004")
        r004["failure_mode"] += (
            " The Discount V2 desktop capability adds an unpermissioned toolbar checkbox that serializes full CalcData to JSON, compresses it with GZip and writes an OrderNo/OprDate-named .zip file beside the deployment tree; no named encryption call exists. Enabling that checkbox is not observational: it executes legacy SLE.usp_DoEVC against the same staging before managed promotion. The current clone has the feature key disabled and the inspected share has no TestDataDiscountV2 directory, so current leakage or outcome divergence is not asserted."
        )
        r004["controls"].append(
            "replace desktop full-CalcData export with a permissioned server-side diagnostic bundle that redacts identities and commercial values, encrypts at rest, uses isolated storage, TTL cleanup and immutable access audit"
        )
        r004["exit_criteria"].append(
            "negative tests deny ordinary order-to-sale users diagnostic export; approved bundles contain no raw customer/order identifiers or unrestricted pricing rules and expire under the retention policy"
        )
        for evidence in (E["order_sale_evc_runtime_boundary"], E["order_sale_evc_sql_boundary"]):
            if evidence not in r004["evidence_refs"]:
                r004["evidence_refs"].append(evidence)
    if discount_v2_query_contracts is not None:
        r079 = next(row for row in risks if row["id"] == "R-079")
        r079["failure_mode"] += (
            " Discount V2 also reads 42 static query templates over 41 persistent objects and three EVC temp tables. Twenty-seven templates have String.Format slots. The selected order path makes 35 direct DataContext reads under Transaction.No; clone RCSI gives statement snapshots, not one calculation-wide snapshot, so concurrent Price/Discount/Stock/Order changes can produce a mixed-version CalcData. No historical divergence is asserted."
        )
    if discount_v2_engine_runtime is not None:
        r079 = next(row for row in risks if row["id"] == "R-079")
        r079["failure_mode"] += (
            " The actual Discount V2 algorithm resides in three separately hash-pinned assemblies with 713 managed types and 7,156 methods. Selected IL proves the validation, payment-usance, price, statute, special-value, item/header application, periodic-discount and prize pipeline. Both advanced-condition helpers read TypeSpecRow.SqlCondition, escape it into a string and execute it through sp_executesql with @EvcId/@Result. Both selected load paths construct the SDS helper immediately before CalcData, so its legacy-to-temp object rewrite is the injected order-to-sale implementation rather than an unused assembly capability. Four exact rewrites are ordered with broad sle.tblEvc before sle.tblEvcItem and sle.tblEvcItemStatutes, shadowing the later lowercase-specific mappings. The current corpus has zero base-name reference, 793 already-temporary rules and 52 EvcItemFull rules, so this is a future compatibility trap rather than a current incident. The selected one-argument CalcData constructor hard-codes BackOfficeType=1 and the application-summary gate accepts that exact value before validation. ApplyDiscountCriteria delegates once to the helper, but the SDS helper enumerates candidate rules and performs one dynamic GetValue per candidate; a true result can add an AllRawEntity read and Execute cleanup on item-include staging. The helper captures and prefers the injected EVC DataContext, which the separate transaction proof classifies as non-transactional; its per-candidate statements therefore share a connection but not one calculation-wide transaction snapshot. This is an active structural N+1 and mixed-version boundary; candidate count and latency per real order remain unmeasured. The read-only clone has 845 nonempty conditions, 626 active, but only 44 distinct hashes; the current lexical snapshot has zero write-DML, DDL/permission or external/delay primitive matches. Clean current text does not remove the executable-rule trust boundary or prove future published rules safe."
        )
        r079["controls"].extend(
            [
                "replace executable SqlCondition text with an allowlisted typed rule AST/DSL compiled only to parameterized predicates",
                "publish immutable commercial-rule versions with separate publisher/approver identities, compiled hash and rollback by version pointer",
                "capture one calculation-wide Price/Stock/Order/Rule snapshot and an explainable RuleEvaluationTrace",
                "separate CurrentBasketPredicate from bounded HistoricalRuleUsagePredicate with explicit query budgets and temporal scope",
                "compile and batch candidate predicates so rule evaluation has a finite per-order query budget rather than one database round trip per candidate",
                "bind typed rule fields to physical projections through a reviewed compiler map; forbid runtime table-name String.Replace compatibility rewrites",
            ]
        )
        r079["exit_criteria"].extend(
            [
                "all 44 observed advanced-condition hash families have owner-approved typed Golden cases and no target runtime path accepts raw SQL",
                "adversarial rule text, unknown fields/operators and unapproved versions fail closed before any sale or EVC mutation",
                "same calculation snapshot and rule version reproduce the same discounts, additions, prizes, payment usance and rejection trace",
                "historical-usage predicates cannot issue arbitrary SQL, exceed their declared lookback/query budget or read outside the calculation snapshot",
                "load tests publish candidate count, query count and p95/p99 calculation latency; a configured hard ceiling fails closed before sale mutation",
                "Golden compiler tests map every approved current and legacy EVC field deterministically; prefix-overlap names cannot shadow a more specific mapping",
            ]
        )
    if discount_v2_condition_families is not None:
        r079 = next(row for row in risks if row["id"] == "R-079")
        r079["failure_mode"] += (
            " Sanitized family analysis groups the 845 conditions into 44 structures over four persistent objects, one EVC temp object and 23 catalog-backed column candidates. Of 626 currently active-flag rules only 57 across 16 families are currently date-effective; 267 rules across 36 families merely overlap the selected historical date window. DeactivationLog contains 1,313 unique one-way transitions to inactive and no activation transition; one currently active advanced rule has an older deactivation row, proving reactivation history is incomplete. Only two families across three rules have retained effects in that window: 471 discount rows on 38 sales, 0.1568% of 300,361 applied-rule rows. Both query EvcItemFull through EXISTS; the larger shape references ID and the smaller references ID plus BrandName. Its two used rules remain active, while the one used brand-sensitive rule was deactivated inside the window; literal values remain deliberately unpersisted. This prioritizes parity cases but does not prove the other 42 families were never evaluated, are obsolete or may be deleted; no current duplicate-active-sale or recent state-projection exception is asserted."
        )
    if discount_rule_authoring_boundary is not None:
        r079 = next(row for row in risks if row["id"] == "R-079")
        r079["failure_mode"] += (
            " Static authoring-path IL shows the discount form opens a dedicated condition dialog and copies its accepted FilterCondition into SqlCondition; CopyNew is the second selected setter. The visual filter is compiled to a dataset where clause, then the dialog creates an EVC temp context and delegates to ValidateUserBuiltCondition. That path reaches DiscountConditionAdapter.ExecuteBuiltCondition, which performs four DataContext.Execute calls backed by four sp_executesql-shaped literals before acceptance. The UI save then runs business validation/save and commits, while the business save delegates twice to the generic TypeSpecRow.SaveCommand path. Expanded analysis proves FormDiscount inherits FormBaseWithListDataEntry. Base initialization invokes permission application, which calls UserSessionInfo.HasPersmission and sets toolbar Enabled state; New/Edit/Delete/Save click handlers require Visible and Enabled before dispatch. The selected list-base method uses allowlisted keys New/Edit/Delete/Print, directly matching the three mutating child nodes but not referencing View or a separate Save key. HasPersmission/HasPermission search the in-memory UserPermissionS snapshot by ClassName+AccessNodeKey or AccessNodeId and return cached HasAccess with zero database round trip in the two selected lookups. No discount-specific authoring/validation/save method and none of the four internal command methods rechecks session permission. The proven boundary is therefore UI-command gating over a session snapshot, not service-layer authorization; consumption of the configured View child, a distinct Save capability, and admin-bypass/deny-precedence materialization into HasAccess are not proven by these lookup bodies. Execution-based validation is not an allowlisted DSL security boundary."
        )
        r079["controls"].extend(
            [
                "separate rule author, reviewer and publisher permissions explicitly at the API boundary; never infer publish authority from screen visibility or generic form state",
                "validate rule syntax and cost through the typed compiler without executing author-supplied SQL, and audit every draft, review, publish, rollback and deactivation transition",
            ]
        )
        r079["exit_criteria"].extend(
            [
                "authorization tests prove draft, review, publish, rollback and deactivate are distinct permissions and direct API calls cannot bypass menu or UI state",
                "rule validation performs zero dynamic SQL execution and rejects unknown fields, unbounded historical scans and unsupported operators before persistence",
            ]
        )
    if discount_rule_authorization_boundary is not None:
        r079 = next(row for row in risks if row["id"] == "R-079")
        r079["failure_mode"] += (
            " The exact FormDiscount route resolves to legacy AccessNode 404 / DiscountRules with four visible child capabilities: View, New, Edit and Delete. Anonymous read-only-clone aggregation sees 141 active users, seven admin bypasses, 15 effective allows on the root and each child, 126 neutral/no-allow on the root and zero explicit deny on the five selected nodes. Equal counts do not prove identical principals because identities and assignments were deliberately not retained. No separate Review or Publish node exists in the subtree, so the legacy route does not establish four-eyes publication; combined with immediate Save/Commit, authoring and publication are structurally coupled. Configured menu nodes also do not prove every command path enforces them."
        )
        r079["controls"].append(
            "map legacy View/New/Edit/Delete only as migration inputs; introduce independently enforced Draft/Review/Publish/Deactivate/Rollback capabilities and deny-by-default authorization decision traces"
        )
        r079["exit_criteria"].append(
            "a reviewer who cannot author can approve, an author cannot self-publish, and direct API tests prove every rule transition enforces its distinct capability with deny-wins semantics"
        )
    uncovered = module_ids - {module for row in risks for module in row["modules"]}
    if uncovered:
        errors.append("uncovered modules: " + ",".join(sorted(uncovered)))
    bad_modules = {module for row in risks for module in row["modules"]} - module_ids
    if bad_modules:
        errors.append("unknown modules: " + ",".join(sorted(bad_modules)))
    bad_owners = {row["accountable_role_template_or_team"] for row in risks} - allowed_owners
    if bad_owners:
        errors.append("unknown owners: " + ",".join(sorted(bad_owners)))
    if any(not row["controls"] or not row["exit_criteria"] or not row["evidence_refs"] for row in risks):
        errors.append("risk missing control, exit criterion or evidence")

    artifact = {
        "artifact": "negin_personal_erp_evidence_backed_risk_register",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_RISK_DERIVATION_FROM_AGGREGATE_AND_REDACTED_EVIDENCE",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_identity_grants_persisted": 0,
            "risk_acceptance_or_production_authorization_granted": 0,
        },
        "summary": {
            "risk_count": len(risks),
            "critical_count": sum(row["severity"] == "CRITICAL" for row in risks),
            "high_count": sum(row["severity"] == "HIGH" for row in risks),
            "medium_count": sum(row["severity"] == "MEDIUM" for row in risks),
            "open_count": sum(row["status"] == "OPEN" for row in risks),
            "covered_module_count": len({module for row in risks for module in row["modules"]}),
            "risk_with_exit_criteria_count": sum(bool(row["exit_criteria"]) for row in risks),
            "validation_error_count": len(errors),
        },
        "policy": {
            "severity_is_not_probability": "severity describes potential impact; likelihood was not fabricated from static evidence",
            "closure_rule": "a risk closes only with fresh evidence satisfying every exit criterion and accountable readback",
            "acceptance_rule": "risk acceptance is a separate user/business decision and is not granted by this artifact",
        },
        "risks": risks,
        "validation_errors": errors,
        "source_checkpoint": {
            "module_count": matrix["summary"]["module_count"],
            "known_anomaly_class_count": len(migration["quarantine_contract"]["known_aggregate_baseline"]),
            "mutating_command_without_explicit_idempotency_count": side_effects["summary"]["mutation_command_without_explicit_idempotency_parameter_count"],
            "selected_high_impact_command_without_explicit_idempotency_parameter_count": (
                idempotency_guard_boundary["summary"][
                    "selected_command_count"
                ]
                - idempotency_guard_boundary["summary"][
                    "selected_command_with_explicit_idempotency_parameter_count"
                ]
                if idempotency_guard_boundary is not None
                else None
            ),
            "selected_idempotency_storage_guard_current_duplicate_group_count": (
                idempotency_guard_boundary["summary"][
                    "current_guarded_duplicate_group_count"
                ]
                if idempotency_guard_boundary is not None
                else None
            ),
            "high_priority_form_gap_count": gaps["summary"]["priority_counts"]["high"],
            "unresolved_root_count": roots["summary"]["still_unresolved_root_count"],
            "report_surface_count": reports["summary"]["surface_count"],
            "runtime_semantic_sha256": drift["release_identity"]["overall_semantic_sha256"],
            "p0_backlog_item_count": backlog["summary"]["item_count"],
            "pos_replication_dependency_count": next(row["dependency_count"] for row in extension_semantics["modules"] if row["object"] == "dbo.usp_ReplicateSalesReceipt"),
            "pos_replication_lexical_operation_count": next(row["lexical_operation_count"] for row in extension_semantics["modules"] if row["object"] == "dbo.usp_ReplicateSalesReceipt"),
            "extension_gap_related_type_count": extension_gaps["summary"]["related_type_count"],
            "pos_transitive_graph_node_count": pos_graph["summary"]["node_count"],
            "pos_transitive_graph_trigger_count": pos_graph["summary"]["trigger_node_count"],
            "pos_transitive_graph_truncated": pos_graph["summary"]["graph_truncated_at_safety_cap"],
            "pos_source_table_count": pos_source["summary"]["found_table_count"],
            "pos_source_untrusted_fk_count": pos_source["summary"]["foreign_key_not_trusted_count"],
            "pos_source_version_signal_table_count": pos_source["summary"]["table_with_source_version_signal_count"],
            "pos_source_row_count_snapshot_total": pos_source["summary"]["row_count_snapshot_total"],
            "report_target_golden_case_count": report_target["summary"]["golden_case_count"],
            "report_result_parity_proven_contract_count": report_target["summary"]["result_parity_proven_contract_count"],
            "report_l3_static_evidence_count": report_gaps["summary"]["evidence_level_counts"]["L3_METHOD_EXECUTION_SIGNAL_PLUS_NAME_CANDIDATES"],
            "report_result_parity_gap_count": report_gaps["summary"]["gap_code_counts"]["RESULT_PARITY_MISSING"],
            "generic_report_selected_sql_module_count": report_generic["summary"]["selected_module_count"],
            "generic_report_described_result_column_count": report_generic["summary"]["described_result_column_count"],
            "treasury_edit_mutation_command_method_count": treasury_paths["summary"]["mutation_command_method_count"],
            "treasury_edit_direct_execute_non_query_method_count": treasury_paths["summary"]["method_with_direct_execute_non_query_count"],
            "treasury_source_writable_view_count": sum(row["object_type"] == "V" for row in treasury_source["objects"]),
            "treasury_source_enabled_trigger_count": treasury_source["summary"]["enabled_trigger_count"],
            "treasury_trigger_dependency_count": treasury_triggers["summary"]["dependency_count"],
            "treasury_trigger_lexical_operation_count": treasury_triggers["summary"]["lexical_operation_count"],
            "treasury_trigger_effect_parity_proven_count": treasury_triggers["summary"]["runtime_trigger_execution_or_effect_parity_proven_count"],
            "treasury_view_visible_column_count": treasury_lineage["summary"]["visible_described_result_column_count"],
            "treasury_view_visible_column_with_source_lineage_count": treasury_lineage["summary"]["visible_described_result_column_with_source_lineage_count"],
            "treasury_view_runtime_effect_proven_count": treasury_lineage["summary"]["runtime_read_write_or_trigger_effect_proven_count"],
            "treasury_view_direct_metadata_gap_with_parsed_candidate_count": treasury_lineage["summary"]["direct_metadata_gap_with_parsed_identifier_candidate_count"],
            "treasury_target_command_contract_count": treasury_target["summary"]["target_command_contract_count"],
            "treasury_unexecuted_acceptance_obligation_count": treasury_target["summary"]["acceptance_obligation_count"],
            "treasury_owner_approved_contract_count": treasury_target["summary"]["owner_approved_contract_count"],
            "treasury_validation_rule_signal_count": treasury_validation["summary"]["unique_rule_signal_count"],
            "treasury_validation_exact_branch_proven_count": treasury_validation["summary"]["exact_branch_condition_message_and_effect_proven_count"],
            "treasury_transitive_node_count": treasury_transitive["summary"]["node_count"],
            "treasury_transitive_resolved_write_target_count": treasury_transitive["summary"]["resolved_write_target_count"],
            "treasury_transitive_graph_truncated": treasury_transitive["summary"]["graph_truncated_at_safety_cap"],
            "treasury_transitive_effect_parity_proven_count": treasury_transitive["summary"]["runtime_execution_or_effect_parity_proven_count"],
            "treasury_web_declared_field_count": treasury_fields["summary"]["declared_field_count"],
            "treasury_web_field_with_source_candidate_count": treasury_fields["summary"]["field_with_underlying_source_column_candidate_count"],
            "treasury_web_field_source_conflict_count": treasury_fields["summary"]["field_with_conflicting_underlying_source_candidates_count"],
            "treasury_web_runtime_binding_proven_count": treasury_fields["summary"]["runtime_binding_requiredness_effective_rule_or_write_mapping_proven_count"],
            "order_sale_selected_method_count": order_sale_commands["summary"]["selected_method_count"],
            "order_sale_rule_signal_count": order_sale_commands["summary"]["unique_rule_signal_count"],
            "order_sale_business_dependency_edge_count": order_sale_dependencies["summary"]["business_dependency_edge_count"],
            "order_sale_sql_anchor_count": order_sale_sql["summary"]["selected_anchor_count"],
            "order_sale_sql_durable_mutation_target_count": order_sale_sql["summary"]["catalog_resolved_durable_mutation_target_count"],
            "order_sale_source_enabled_trigger_count": order_sale_source["summary"]["enabled_trigger_count"],
            "order_sale_trigger_node_count": order_sale_triggers["summary"]["node_count"],
            "order_sale_trigger_graph_truncated": order_sale_triggers["summary"]["graph_truncated_at_safety_cap"],
            "order_sale_trigger_resolved_write_target_count": order_sale_triggers["summary"]["resolved_write_target_count"],
            "order_sale_web_input_candidate_count": order_sale_screens["summary"]["input_control_candidate_count"],
            "order_sale_linked_synthetic_golden_case_count": order_sale_screens["summary"]["linked_synthetic_golden_case_count"],
            "order_sale_runtime_effect_or_golden_proven_count": 0,
            "stock_voucher_rule_signal_count": stock_voucher_contract["summary"]["rule_signal_count"],
            "stock_voucher_runtime_effect_parity_proven_count": stock_voucher_contract["summary"]["runtime_effect_parity_proven_count"],
            "distribution_sql_durable_mutation_target_count": distribution_sql["summary"]["catalog_resolved_durable_mutation_target_count"],
            "distribution_source_enabled_trigger_count": distribution_source["summary"]["enabled_trigger_count"],
            "distribution_trigger_node_count": distribution_triggers["summary"]["node_count"],
            "distribution_trigger_resolved_write_target_count": distribution_triggers["summary"]["resolved_write_target_count"],
            "distribution_trigger_graph_truncated": distribution_triggers["summary"]["graph_truncated_at_safety_cap"],
            "distribution_runtime_effect_parity_proven_count": distribution_triggers["summary"]["runtime_execution_or_effect_parity_proven_count"],
            "supplier_invoice_rule_signal_count": supplier_invoice_contract["summary"]["unique_rule_signal_count"],
            "supplier_invoice_trigger_toggle_literal_count": supplier_invoice_contract["summary"]["trigger_enable_disable_literal_count"],
            "supplier_invoice_relation_enabled_trigger_count": supplier_invoice_source["summary"]["enabled_trigger_count"],
            "supplier_invoice_trigger_node_count": supplier_invoice_triggers["summary"]["node_count"],
            "supplier_invoice_trigger_resolved_write_target_count": supplier_invoice_triggers["summary"]["resolved_write_target_count"],
            "supplier_invoice_trigger_graph_truncated": supplier_invoice_triggers["summary"]["graph_truncated_at_safety_cap"],
            "supplier_invoice_runtime_effect_parity_proven_count": supplier_invoice_triggers["summary"]["runtime_execution_or_effect_parity_proven_count"],
            "accounting_voucher_target_command_candidate_count": accounting_voucher_entrypoints["summary"]["target_command_candidate_count"],
            "accounting_voucher_rule_signal_count": accounting_voucher_entrypoints["summary"]["unique_rule_signal_count"],
            "accounting_voucher_sql_name_candidate_count": accounting_voucher_sql["summary"]["candidate_object_count"],
            "accounting_voucher_exact_sql_binding_count": accounting_voucher_sql["summary"]["exact_static_ui_or_handler_binding_count"],
            "accounting_voucher_runtime_effect_parity_proven_count": accounting_voucher_sql["summary"]["runtime_execution_or_result_parity_proven_count"],
            "customer_goods_input_candidate_count": customer_goods_screens["summary"]["input_control_candidate_count"],
            "customer_goods_input_without_static_text_count": customer_goods_screens["summary"]["input_without_any_static_text_candidate_count"],
            "customer_goods_screen_missing_golden_count": customer_goods_screens["summary"]["screen_with_missing_golden_contract_count"],
            "customer_goods_rule_signal_count": customer_goods_commands["summary"]["unique_rule_signal_count"],
            "customer_goods_implementation_ready_count": customer_goods_screens["summary"]["implementation_ready_screen_count"],
            "supplier_master_input_candidate_count": supplier_master_screen["summary"]["input_control_candidate_count"],
            "supplier_master_rule_signal_count": supplier_master_command["summary"]["unique_rule_signal_count"],
            "supplier_master_screen_missing_golden_count": supplier_master_screen["summary"]["screen_with_missing_golden_contract_count"],
            "supplier_master_implementation_ready_count": supplier_master_screen["summary"]["implementation_ready_screen_count"],
            "operational_context_input_candidate_count": operational_context_screens["summary"]["input_control_candidate_count"],
            "operational_context_rule_signal_count": operational_context_commands["summary"]["unique_rule_signal_count"],
            "operational_context_screen_missing_golden_count": operational_context_screens["summary"]["screen_with_missing_golden_contract_count"],
            "operational_context_implementation_ready_count": operational_context_screens["summary"]["implementation_ready_screen_count"],
            "pricing_rule_input_candidate_count": pricing_rule_screens["summary"]["input_control_candidate_count"],
            "pricing_rule_signal_count": pricing_rule_commands["summary"]["unique_rule_signal_count"],
            "pricing_rule_screen_missing_golden_count": pricing_rule_screens["summary"]["screen_with_missing_golden_contract_count"],
            "pricing_rule_implementation_ready_count": pricing_rule_screens["summary"]["implementation_ready_screen_count"],
            "final_date_configured_route_count": final_date_boundary["summary"]["configured_final_date_route_count"],
            "final_date_runtime_matched_route_count": final_date_boundary["summary"]["runtime_matched_route_count"],
            "final_date_runtime_unmatched_route_count": final_date_boundary["summary"]["runtime_unmatched_route_count"],
            "final_date_business_update_method_count": final_date_boundary["summary"]["business_update_method_count"],
            "final_date_runtime_effect_parity_proven_count": final_date_boundary["summary"]["runtime_effect_parity_proven_count"],
            "final_date_incident_finding_count": final_date_diagnostic["summary"]["finding_count"],
            "final_date_incident_critical_count": final_date_diagnostic["summary"]["finding_severity_counts"]["CRITICAL"],
            "stock_cardex_only_gap_count": stock_reconciliation["summary"]["cardex_only_mismatch_count"],
            "stock_official_formula_residual_count": stock_reconciliation["summary"]["official_formula_mismatch_count"],
            "distribution_path_previous_orphan_fk_interpretation_valid": distribution_path["summary"]["previous_orphan_fk_interpretation_valid"],
            "distribution_manual_path_code_row_count": distribution_path["summary"]["distribution_count"],
            "distribution_path_formal_fk_count": distribution_path["summary"]["formal_dist_path_fk_count"],
            "sales_return_previous_gross_mismatch_interpretation_valid": sales_return_amount["summary"]["previous_mismatch_interpretation_valid"],
            "sales_return_previous_active_gross_difference_count": sales_return_amount["summary"]["previous_active_difference_count"],
            "sales_return_official_net_difference_count": sales_return_amount["summary"]["official_stored_net_difference_count"],
            "sales_return_item_formula_difference_count": sales_return_amount["summary"]["item_formula_difference_count"],
            "returned_cheque_cross_customer_previous_anomaly_interpretation_valid": returned_cheque_cross_customer["summary"]["previous_anomaly_interpretation_valid"],
            "returned_cheque_cross_customer_exact_allocation_match_count": returned_cheque_cross_customer["summary"]["exact_original_allocation_matches"],
            "returned_cheque_cross_customer_unexplained_row_count": returned_cheque_cross_customer["summary"]["unexplained_rows"],
            "returned_cheque_cross_customer_over_settled_pair_count": returned_cheque_cross_customer["summary"]["over_settled_pairs"],
            "received_cheque_master_pay_projection_gap_count": received_cheque_projection_legal["summary"]["master_pay_projection_missing_rows"],
            "received_cheque_master_pay_projection_gap_with_valid_approved_history_count": received_cheque_projection_legal["summary"]["valid_approved_history_pay_links_for_all_missing_master_rows"],
            "received_cheque_unspecified_legal_type_count": received_cheque_projection_legal["summary"]["current_status9_unspecified_legal_type_rows"],
            "received_cheque_bulk_confirmation_forwards_legal_type": received_cheque_projection_legal["summary"]["bulk_confirmation_forwards_legal_type"],
            "payable_source_used_unlinked_leaf_count": payable_cheque_leaf_usage["summary"]["source_used_unlinked_count"],
            "payable_source_used_unlinked_previous_orphan_interpretation_valid": payable_cheque_leaf_usage["summary"]["previous_orphan_interpretation_valid"],
            "payable_source_used_unlinked_historical_reason_recoverable": payable_cheque_leaf_usage["summary"]["historical_reason_recoverable"],
            "voucher_current_pointer_history_fork_count": voucher_status_pointer["summary"]["current_pointer_not_maximum_count"],
            "voucher_detached_trailing_event_count": voucher_status_pointer["summary"]["detached_trailing_event_count"],
            "voucher_status_change_failure_has_explicit_rollback": voucher_status_pointer["summary"]["legacy_change_status_failure_has_explicit_rollback"],
            "empty_numbered_draft_voucher_shell_count": empty_voucher_shell["summary"]["numbered_shell_count"],
            "empty_numbered_draft_voucher_ledger_debit_effect": empty_voucher_shell["summary"]["ledger_debit_effect"],
            "empty_numbered_draft_voucher_safe_to_synthesize_lines": empty_voucher_shell["summary"]["safe_to_synthesize_lines"],
            "ngt_mobile_return_without_current_official_return_count": ngt_return_crosswalk["summary"]["without_current_official_return_count"],
            "ngt_mobile_return_historical_result_missing_target_count": ngt_return_crosswalk["summary"]["historical_result_missing_current_order_count"],
            "ngt_mobile_return_without_historical_result_count": ngt_return_crosswalk["summary"]["without_historical_return_order_result_line_count"],
            "supplier_return_sourced_goods_group_count": supplier_receipt_component["supplier_return_validator_data_profile"]["sourced_return_goods_group_count"],
            "supplier_return_unmatched_source_goods_group_count": supplier_receipt_component["supplier_return_validator_data_profile"]["unmatched_return_goods_group_count"],
            "supplier_return_matched_over_return_goods_group_count": supplier_receipt_component["supplier_return_validator_data_profile"]["matched_over_return_goods_group_count"],
            "supplier_return_validator_update_path_call": supplier_receipt_component["supplier_return_validation_contract"]["update_branch_calls_validator"],
            "supplier_return_validator_insert_captures_return_code": supplier_receipt_component["supplier_return_validation_contract"]["insert_branch_captures_validator_return_code"],
            "supplier_return_validator_has_unmatched_goods_check": supplier_receipt_component["supplier_return_validation_contract"]["validator_has_explicit_unmatched_return_goods_check"],
            "supplier_return_desktop_validator_before_commit": supplier_receipt_component["desktop_save_boundary"]["calls_return_validator_before_data_context_commit"],
            "supplier_return_desktop_nonempty_message_blocks_commit": supplier_receipt_component["desktop_save_boundary"]["nonempty_validator_message_builds_validation_failure_before_commit"],
            "supplier_return_stale_explicit_toll_ref_count": supplier_receipt_component["supplier_return_toll_integrity_profile"]["correct_scope_missing_header_toll_row_count"],
            "supplier_return_stale_toll_ref_affected_new_path_header_count": supplier_receipt_component["supplier_return_toll_integrity_profile"]["affected_new_path_return_header_count"],
            "supplier_return_stale_toll_ref_unique_compatibility_resolution_count": supplier_receipt_component["supplier_return_toll_integrity_profile"]["stale_explicit_ref_resolved_by_same_header_toll_code_count"],
            "supplier_return_toll_compatibility_unresolved_count": supplier_receipt_component["supplier_return_toll_integrity_profile"]["unresolved_by_explicit_ref_or_same_header_toll_code_count"],
            "supplier_return_toll_compatibility_ambiguous_count": supplier_receipt_component["supplier_return_toll_integrity_profile"]["ambiguous_same_header_toll_code_match_count"],
            "supplier_return_optional_source_item_absent_exact_type55_exit_count": supplier_receipt_component["supplier_return_missing_direct_source_profile"]["exact_linked_type55_inventory_exit_goods_groups"],
            "supplier_return_optional_source_item_absent_nonzero_price_count": supplier_receipt_component["supplier_return_missing_direct_source_profile"]["nonzero_price_goods_groups"],
            "supplier_return_item_grid_inventory_voucher_authority": supplier_receipt_component["desktop_save_boundary"]["source_selection_contract"]["item_grid_loads_through_inventory_voucher_ref"],
            "supplier_return_rights_forwards_dc_or_accyear_scope": supplier_receipt_component["supplier_return_validation_contract"]["access_operation_date_and_required_goods_contract"]["forwards_accyear_or_dcref_to_access_node_authorizer"],
            "supplier_return_required_goods_check_is_current_aggregate_scoped": supplier_receipt_component["supplier_return_validation_contract"]["access_operation_date_and_required_goods_contract"]["before_save_required_goods_check_scoped_to_current_parent_or_temp_items"],
            "supplier_return_current_zero_or_null_goods_item_count": supplier_receipt_component["supplier_return_required_goods_guard_profile"]["zero_or_null_goods_item_count"],
            "supplier_return_three_month_new_path_header_count": supplier_receipt_component["three_month_supplier_return_profile"]["new_path_header_count"],
            "supplier_return_three_month_legacy_path_header_count": supplier_receipt_component["three_month_supplier_return_profile"]["legacy_path_header_count"],
            "supplier_return_three_month_optional_source_item_absent_goods_group_count": supplier_receipt_component["three_month_supplier_return_profile"]["optional_source_item_absent_goods_group_count"],
            "supplier_return_three_month_stale_explicit_toll_ref_row_count": supplier_receipt_component["three_month_supplier_return_profile"]["stale_explicit_toll_ref_row_count"],
            "supplier_invoice_item_duplicate_header_goods_group_count": supplier_receipt_component["supplier_invoice_item_uniqueness_profile"]["duplicate_header_goods_group_count"],
            "supplier_invoice_item_unique_header_goods_index_count": supplier_receipt_component["supplier_invoice_item_uniqueness_profile"]["unique_header_goods_index_count"],
            "voucher_creation_active_creator_count": len(voucher_creation_policy["active_creator_rule_profiles"]),
            "voucher_creation_desktop_outer_transaction_proven": voucher_creation_policy["deployed_call_and_transaction_contract"]["conclusion"]["desktop_null_context_path_has_one_outer_transaction"],
            "voucher_creation_server_owned_transaction": voucher_creation_policy["deployed_call_and_transaction_contract"]["conclusion"]["procedure_owns_transaction"],
            "voucher_creation_current_policy_fully_explains_history": voucher_creation_policy["historical_grouping_policy_drift"]["current_policy_fully_explains_history"],
            "voucher_creation_1405_multi_source_header_count": next(row["multi_source_headers"] for row in voucher_creation_policy["historical_grouping_policy_drift"]["by_accounting_year"] if row["AccYear"] == 1405),
            "voucher_creation_three_month_header_count": voucher_creation_policy["historical_grouping_policy_drift"]["three_month_window"]["headers"],
            "voucher_creation_three_month_source_group_count": voucher_creation_policy["historical_grouping_policy_drift"]["three_month_window"]["source_groups"],
            "voucher_creator_configured_rule_count": voucher_creation_policy[
                "active_creator_rule_coverage"
            ]["configured_rule_count"],
            "voucher_creator_historically_observed_rule_count": voucher_creation_policy[
                "active_creator_rule_coverage"
            ]["historically_observed_rule_count"],
            "voucher_creator_historically_unobserved_rule_count": voucher_creation_policy[
                "active_creator_rule_coverage"
            ]["historically_unobserved_rule_count"],
            "voucher_historical_staging_line_count": voucher_creation_policy[
                "historical_external_line_grain_profile"
            ]["source_lines"],
            "voucher_historical_actual_external_line_count": voucher_creation_policy[
                "historical_external_line_grain_profile"
            ]["actual_external_lines"],
            "voucher_historical_current_grain_expected_line_count": voucher_creation_policy[
                "historical_external_line_grain_profile"
            ]["current_deployed_expected_lines"],
            "voucher_historical_legacy_equivalent_expected_line_count": voucher_creation_policy[
                "historical_external_line_grain_profile"
            ]["legacy_equivalent_expected_lines"],
            "voucher_historical_collapsed_staging_line_count": voucher_creation_policy[
                "historical_external_line_grain_profile"
            ]["legacy_equivalent_collapsed_lines"],
            "voucher_historical_all_creators_match_current_grain": voucher_creation_policy[
                "historical_external_line_grain_profile"
            ]["all_creators_match_current_deployed_grain"],
            "voucher_lifecycle_all_outer_transactions_proven": all(
                row["outer_transaction_proven"]
                for row in voucher_creation_policy[
                    "deployed_call_and_transaction_contract"
                ]["lifecycle_operations"].values()
            ),
            "voucher_transfer_deletes_number_crosswalk_before_validation": voucher_creation_policy[
                "procedure_contracts"
            ]["dbo.usp_DoExternalVoucherTransfer"]["semantic_signals"][
                "deletes_set_voucher_no_before_validation"
            ],
            "voucher_transfer_validation_can_return_without_exception": voucher_creation_policy[
                "procedure_contracts"
            ]["dbo.usp_DoExternalVoucherTransfer"]["semantic_signals"][
                "validation_can_return_without_exception"
            ],
            "voucher_lifecycle_full_header_count": voucher_creation_policy[
                "full_history_lifecycle_state"
            ]["header_state"]["headers"],
            "voucher_lifecycle_full_multiple_active_voucher_count": voucher_creation_policy[
                "full_history_lifecycle_state"
            ]["header_state"]["multiple_active_vouchers"],
            "voucher_lifecycle_full_number_crosswalk_orphan_count": voucher_creation_policy[
                "full_history_lifecycle_state"
            ]["set_voucher_number_state"]["no_active_voucher_rows"],
            "voucher_read_grid_session_accyear_dc_scoped": voucher_creation_policy[
                "deployed_call_and_transaction_contract"
            ]["authorization_and_scope_contract"]["conclusion"][
                "read_grid_is_session_accyear_dc_scoped"
            ],
            "voucher_form_command_method_permission_call_count": sum(
                row["permission_call_count"]
                for row in voucher_creation_policy[
                    "deployed_call_and_transaction_contract"
                ]["authorization_and_scope_contract"][
                    "command_method_permission_calls"
                ].values()
            ),
            "voucher_action_procedure_authorization_count": voucher_creation_policy[
                "deployed_call_and_transaction_contract"
            ]["authorization_and_scope_contract"]["server_procedure_authorization"][
                "action_procedure_with_authorization_count"
            ],
            "voucher_issue_operation_finality_enforced": voucher_creation_policy[
                "deployed_call_and_transaction_contract"
            ]["authorization_and_scope_contract"]["server_procedure_authorization"][
                "issue_enforces_operation_finality"
            ],
            "voucher_issue_finality_failure_is_pre_mutation": voucher_creation_policy[
                "issuance_finality_contract"
            ]["deployed_sql_semantics"][
                "finality_failure_is_before_first_persistent_mutation"
            ],
            "voucher_purchase_finality_requires_every_stockdc_row": voucher_creation_policy[
                "issuance_finality_contract"
            ]["deployed_sql_semantics"][
                "purchase_query_requires_every_stockdc_row"
            ],
            "voucher_purchase_partially_covered_active_dc_year_scope_count": voucher_creation_policy[
                "issuance_finality_contract"
            ]["summary"][
                "purchase_partially_covered_active_dc_year_scope_count"
            ],
            "voucher_purchase_missing_stockdc_operation_row_count": voucher_creation_policy[
                "issuance_finality_contract"
            ]["summary"]["purchase_missing_stockdc_operation_row_count"],
            "voucher_operation_id_5_configured_type_count": voucher_creation_policy[
                "issuance_finality_contract"
            ]["summary"]["configured_operation_id_5_type_count"],
            "voucher_operation_id_5_retained_header_count": voucher_creation_policy[
                "issuance_finality_contract"
            ]["summary"]["operation_id_5_retained_header_count"],
            "voucher_modern_header_current_finality_failure_count": voucher_creation_policy[
                "issuance_finality_contract"
            ]["summary"]["modern_header_would_fail_current_finality_count"],
            "voucher_issue_policy_preflight_before_transaction": voucher_creation_policy[
                "deployed_call_and_transaction_contract"
            ]["business_boundary"][
                "policy_preflight_occurs_before_issue_transaction"
            ],
            "voucher_issue_policy_values_are_procedure_parameters": not voucher_creation_policy[
                "issuance_finality_contract"
            ]["deployed_sql_semantics"][
                "policy_values_are_not_procedure_parameters"
            ],
            "voucher_issue_validation_failure_stops_confirmation": voucher_creation_policy[
                "deployed_call_and_transaction_contract"
            ]["ui_entrypoint"][
                "issue_validation_failure_returns_before_confirm"
            ],
            "voucher_confirm_validation_failure_stops_transfer": voucher_creation_policy[
                "deployed_call_and_transaction_contract"
            ]["ui_entrypoint"][
                "confirm_validation_failure_returns_before_transfer"
            ],
            "voucher_success_ids_only_from_message_type_zero": voucher_creation_policy[
                "deployed_call_and_transaction_contract"
            ]["ui_entrypoint"][
                "successful_header_ids_are_parsed_only_from_message_type_zero"
            ],
            "voucher_configured_type_count": voucher_creation_policy[
                "voucher_type_structural_validation_profile"
            ]["summary"]["configured_type_count"],
            "voucher_structurally_candidate_type_count": voucher_creation_policy[
                "voucher_type_structural_validation_profile"
            ]["summary"]["structurally_candidate_type_count"],
            "voucher_structurally_invalid_type_count": voucher_creation_policy[
                "voucher_type_structural_validation_profile"
            ]["summary"]["structurally_invalid_type_count"],
            "voucher_invalid_type_with_retained_history_count": voucher_creation_policy[
                "voucher_type_structural_validation_profile"
            ]["summary"]["invalid_type_with_retained_history_count"],
            "voucher_uncompiled_predicate_count": voucher_creation_policy[
                "voucher_type_structural_validation_profile"
            ]["summary"]["predicate_count_not_runtime_compiled"],
            "voucher_creator_view_queries_executed_for_validation": voucher_creation_policy[
                "voucher_type_structural_validation_profile"
            ]["deployed_validator_semantics"][
                "operational_creator_views_executed_by_extractor"
            ],
            "voucher_creator_view_nolock_read_count": voucher_creation_policy[
                "dynamic_rule_sql_and_source_snapshot_profile"
            ]["summary"]["creator_view_nolock_read_count_in_definition"],
            "voucher_dynamic_sql_execution_site_count": voucher_creation_policy[
                "dynamic_rule_sql_and_source_snapshot_profile"
            ]["summary"]["dynamic_sql_execution_site_count"],
            "voucher_dynamic_sql_sites_executed_by_extractor": voucher_creation_policy[
                "dynamic_rule_sql_and_source_snapshot_profile"
            ]["summary"]["dynamic_sql_execution_sites_run_by_extractor"],
            "voucher_current_suspicious_fragment_count": voucher_creation_policy[
                "dynamic_rule_sql_and_source_snapshot_profile"
            ]["summary"]["current_suspicious_token_or_quote_value_count"],
            "voucher_distinct_dynamic_predicate_count": voucher_creation_policy[
                "dynamic_rule_sql_and_source_snapshot_profile"
            ]["summary"]["distinct_article_predicate_count"],
            "voucher_provider_explicit_isolation_level": voucher_creation_policy[
                "transaction_isolation_and_source_version_profile"
            ]["summary"]["provider_explicit_isolation_level"],
            "voucher_clone_read_committed_snapshot_enabled": voucher_creation_policy[
                "transaction_isolation_and_source_version_profile"
            ]["clone_database_options"]["is_read_committed_snapshot_on"],
            "voucher_clone_snapshot_isolation_state": voucher_creation_policy[
                "transaction_isolation_and_source_version_profile"
            ]["clone_database_options"]["snapshot_isolation_state_desc"],
            "voucher_recent_source_base_table_count": voucher_creation_policy[
                "transaction_isolation_and_source_version_profile"
            ]["summary"]["recent_source_base_table_count"],
            "voucher_recent_source_rowversion_table_count": voucher_creation_policy[
                "transaction_isolation_and_source_version_profile"
            ]["summary"]["recent_source_base_table_with_rowversion_count"],
            "voucher_recent_source_temporal_table_count": voucher_creation_policy[
                "transaction_isolation_and_source_version_profile"
            ]["summary"]["recent_source_temporal_base_table_count"],
            "voucher_recent_source_change_tracked_table_count": voucher_creation_policy[
                "transaction_isolation_and_source_version_profile"
            ]["summary"]["recent_source_change_tracked_base_table_count"],
            "voucher_rule_target_form_type_count": voucher_creation_policy[
                "rule_configuration_write_authority_profile"
            ]["summary"]["application_target_form_type_count"],
            "voucher_rule_named_save_is_validation_failure": voucher_creation_policy[
                "rule_configuration_write_authority_profile"
            ]["summary"]["handler_save_is_unconditional_validation_failure"],
            "voucher_rule_template_transfer_procedure_count": voucher_creation_policy[
                "rule_configuration_write_authority_profile"
            ]["summary"]["template_transfer_procedure_count"],
            "voucher_rule_template_transfer_transaction_count": voucher_creation_policy[
                "rule_configuration_write_authority_profile"
            ]["summary"]["template_transfer_procedure_with_transaction_count"],
            "voucher_rule_template_transfer_try_catch_count": voucher_creation_policy[
                "rule_configuration_write_authority_profile"
            ]["summary"]["template_transfer_procedure_with_try_catch_count"],
            "voucher_rule_template_transfer_authorization_count": voucher_creation_policy[
                "rule_configuration_write_authority_profile"
            ]["summary"]["template_transfer_procedure_with_authorization_signal_count"],
            "voucher_rule_template_transfer_version_audit_count": voucher_creation_policy[
                "rule_configuration_write_authority_profile"
            ]["summary"]["template_transfer_procedure_with_version_audit_signal_count"],
            "voucher_rule_template_transfer_analyzer_execute_count": voucher_creation_policy[
                "rule_configuration_write_authority_profile"
            ]["summary"]["analyzer_login_executable_template_procedure_count"],
            "voucher_rule_enabled_replication_trigger_count": voucher_creation_policy[
                "rule_configuration_write_authority_profile"
            ]["summary"]["sql_enabled_target_trigger_count"],
            "rule_replication_hash_pinned_binary_count": rule_replication_transport[
                "summary"
            ]["hash_pinned_binary_count"],
            "rule_replication_outbound_binary_outbox_proven": rule_replication_transport[
                "summary"
            ]["outbound_binary_outbox_proven"],
            "rule_replication_receive_transaction_proven": rule_replication_transport[
                "summary"
            ]["receive_script_and_receipt_transaction_proven"],
            "rule_replication_clone_downstream_success_proven": rule_replication_transport[
                "summary"
            ]["clone_downstream_success_proven"],
            "rule_replication_ftp_explicit_transport_encryption_proven": rule_replication_transport[
                "summary"
            ]["ftp_branch_explicit_transport_encryption_proven"],
            "rule_replication_package_content_authentication_proven": rule_replication_transport[
                "summary"
            ]["replication_package_content_authentication_proven"],
            **(
                {
                    "ngt_attribute_declared_endpoint_count": ngt_authorization_effective[
                        "summary"
                    ]["attribute_declared_endpoint_count"],
                    "ngt_endpoint_without_authorization_declaration_count": ngt_authorization_effective[
                        "summary"
                    ][
                        "endpoint_without_ngt_standard_claims_or_anonymous_declaration_count"
                    ],
                    "ngt_mutating_endpoint_without_authorization_declaration_count": ngt_authorization_effective[
                        "summary"
                    ][
                        "mutating_endpoint_without_ngt_standard_claims_or_anonymous_declaration_count"
                    ],
                    "ngt_resource_action_catalog_gap_count": ngt_authorization_effective[
                        "summary"
                    ][
                        "resource_action_contract_absent_from_all_application_owners_count"
                    ],
                    "ngt_endpoint_without_named_manual_authorization_decision_signal_count": ngt_authorization_effective[
                        "summary"
                    ][
                        "endpoint_without_named_manual_authorization_decision_signal_count"
                    ],
                    "ngt_mutating_endpoint_without_named_manual_authorization_decision_signal_count": ngt_authorization_effective[
                        "summary"
                    ][
                        "mutating_endpoint_without_named_manual_authorization_decision_signal_count"
                    ],
                    "ngt_admin_role_short_circuits_base_authorization": ngt_authorization_effective[
                        "summary"
                    ]["admin_role_short_circuits_base_authorization"],
                    "ngt_admin_role_current_assignment_subject_count": ngt_authorization_effective[
                        "summary"
                    ]["admin_role_current_assignment_subject_count"],
                }
                if ngt_authorization_effective is not None
                else {}
            ),
            **(
                {
                    "ngt_order_header_count": ngt_order_persistence_boundary[
                        "summary"
                    ]["order_header_count"],
                    "ngt_order_line_count": ngt_order_persistence_boundary[
                        "summary"
                    ]["order_line_count"],
                    "ngt_order_status_event_count": ngt_order_persistence_boundary[
                        "summary"
                    ]["order_status_event_count"],
                    "ngt_order_untrusted_related_fk_count": ngt_order_persistence_boundary[
                        "summary"
                    ]["untrusted_related_foreign_key_edge_count"],
                    "ngt_order_partial_line_crosswalk_count": ngt_order_persistence_boundary[
                        "summary"
                    ]["partially_mapped_order_count"],
                    "ngt_order_split_backoffice_crosswalk_count": ngt_order_persistence_boundary[
                        "summary"
                    ]["split_backoffice_order_count"],
                    "ngt_order_runtime_save_tour_instruction_count": ngt_order_runtime_boundary[
                        "key_orchestration_contract"
                    ]["save_tour_data"]["instruction_count"],
                    "ngt_order_runtime_replicate_tour_instruction_count": ngt_order_runtime_boundary[
                        "key_orchestration_contract"
                    ]["replicate_tour"]["instruction_count"],
                    "ngt_order_update_from_ngt_save_changes_count": ngt_order_runtime_boundary[
                        "key_orchestration_contract"
                    ]["update_order_from_ngt"]["save_changes_call_count"],
                }
                if ngt_order_persistence_boundary is not None
                else {}
            ),
            **(
                {
                    "ngt_tour_count": ngt_tour_call_state_boundary["summary"]["tour_count"],
                    "ngt_customer_call_count": ngt_tour_call_state_boundary["summary"]["customer_call_count"],
                    "ngt_wrong_base_type_visit_status_count": ngt_tour_call_state_boundary[
                        "semantic_status_contract"
                    ]["reference_integrity"]["wrong_base_type_visit_status_count"],
                    "ngt_tour_previous_status_present_count": ngt_tour_call_state_boundary[
                        "tour_state_contract"
                    ]["aggregate"]["previous_status_present_count"],
                    "ngt_tour_end_before_start_count": ngt_tour_call_state_boundary[
                        "tour_state_contract"
                    ]["aggregate"]["end_before_start_count"],
                    "ngt_customer_call_negative_visit_duration_count": ngt_tour_call_state_boundary[
                        "customer_call_state_contract"
                    ]["aggregate"]["negative_visit_duration_count"],
                    "ngt_tour_call_runtime_lifecycle_method_count": ngt_tour_call_runtime_boundary[
                        "summary"
                    ]["lifecycle_method_count"],
                    "ngt_tour_lifecycle_endpoint_count": len(tour_lifecycle_endpoints),
                    "ngt_tour_lifecycle_get_endpoint_count": sum(
                        "GET" in row["http_verbs"] for row in tour_lifecycle_endpoints
                    ),
                    "ngt_tour_lifecycle_post_endpoint_count": sum(
                        "POST" in row["http_verbs"] for row in tour_lifecycle_endpoints
                    ),
                }
                if ngt_tour_call_state_boundary is not None
                else {}
            ),
            **(
                {
                    "ngt_payment_header_count": ngt_payment_settlement_boundary["summary"][
                        "payment_header_count"
                    ],
                    "ngt_payment_detail_count": ngt_payment_settlement_boundary["summary"][
                        "payment_detail_count"
                    ],
                    "ngt_payment_allocation_mismatch_count": ngt_payment_settlement_boundary[
                        "summary"
                    ]["allocation_mismatch_count"],
                    "ngt_payment_underallocated_count": ngt_payment_settlement_boundary["summary"][
                        "underallocated_count"
                    ],
                    "ngt_payment_receipt_linked_count": ngt_payment_settlement_boundary["summary"][
                        "receipt_linked_count"
                    ],
                    "ngt_payment_receipt_amount_scope_differs_count": ngt_payment_settlement_boundary[
                        "summary"
                    ]["receipt_amount_scope_differs_count"],
                    "ngt_payment_runtime_core_method_count": ngt_payment_runtime_boundary["summary"][
                        "core_method_count"
                    ],
                    "ngt_payment_save_explicit_transaction": ngt_payment_runtime_boundary[
                        "payment_save_transaction_and_allocation_contract"
                    ]["explicit_begin_transaction"],
                }
                if ngt_payment_settlement_boundary is not None
                else {}
            ),
            **(
                {
                    "ngt_payment_type_10_history_count": ngt_payment_replication_boundary[
                        "summary"
                    ]["payment_type_10_history_count"],
                    "ngt_payment_type_10_distinct_entity_count": ngt_payment_replication_boundary[
                        "tour_history_contract"
                    ]["payment_type_10_crosswalk"]["distinct_entity_count"],
                    "ngt_payment_type_10_duplicate_entity_group_count": ngt_payment_replication_boundary[
                        "tour_history_contract"
                    ]["type_10_duplicate_entity_groups"]["duplicate_entity_group_count"],
                    "ngt_payment_type_10_exact_duplicate_group_count": ngt_payment_replication_boundary[
                        "tour_history_contract"
                    ]["type_10_exact_duplicate_groups"]["exact_duplicate_group_count"],
                    "ngt_payment_replication_runtime_crosswalk_setter_count": ngt_payment_replication_runtime_boundary[
                        "replicate_tour_crosswalk_writeback_contract"
                    ]["payment_crosswalk_setter_event_count"],
                }
                if ngt_payment_replication_boundary is not None
                else {}
            ),
            **(
                {
                    "configuration_delivery_static_omission_count": configuration_precedence_boundary[
                        "summary"
                    ]["configuration_delivery_static_omission_count"],
                    "configuration_delivery_current_absence_count": configuration_precedence_boundary[
                        "summary"
                    ]["configuration_delivery_current_absence_count"],
                    "configuration_delivery_semantic_mismatch_count": configuration_precedence_boundary[
                        "summary"
                    ]["configuration_delivery_semantic_mismatch_count"],
                    "configuration_app_device_same_name_mismatch_count": configuration_precedence_boundary[
                        "summary"
                    ]["app_device_same_name_current_mismatch_count"],
                    "configuration_active_child_to_removed_device_setting_reference_count": configuration_precedence_boundary[
                        "summary"
                    ]["active_child_to_removed_device_setting_reference_count"],
                    "ngt_configuration_runtime_selection_method_count": ngt_configuration_runtime_boundary[
                        "summary"
                    ]["runtime_selection_method_count"],
                    "ngt_configuration_runtime_selection_with_removed_signal_count": ngt_configuration_runtime_boundary[
                        "summary"
                    ]["runtime_selection_method_with_is_removed_signal_count"],
                }
                if configuration_precedence_boundary is not None
                else {}
            ),
            **(
                {
                    "supplier_cost_core_apply_module_count": supplier_cost_apply_boundary[
                        "summary"
                    ]["core_apply_module_count"],
                    "supplier_cost_core_local_transaction_count": supplier_cost_apply_boundary[
                        "summary"
                    ]["core_module_with_local_transaction_count"],
                    "supplier_cost_applied_invoice_count": supplier_cost_apply_boundary[
                        "summary"
                    ]["applied_invoice_count"],
                    "supplier_cost_applied_related_item_count": supplier_cost_apply_boundary[
                        "summary"
                    ]["applied_related_item_count"],
                    "supplier_cost_applied_item_without_price_count": supplier_cost_apply_boundary[
                        "summary"
                    ]["applied_item_without_price_count"],
                    "supplier_cost_unapplied_item_with_price_count": supplier_cost_apply_boundary[
                        "summary"
                    ]["unapplied_item_with_price_count"],
                    "supplier_cost_orphan_price_row_count": supplier_cost_apply_boundary[
                        "summary"
                    ]["orphan_price_row_count"],
                    "supplier_cost_runtime_selected_method_count": supplier_cost_apply_runtime_boundary[
                        "summary"
                    ]["selected_method_count"],
                    "supplier_cost_reapply_selected_path_has_commit": supplier_cost_apply_runtime_boundary[
                        "managed_apply_reapply_contract"
                    ]["reapply_selected_path_has_data_context_commit_signal"],
                }
                if supplier_cost_apply_boundary is not None
                else {}
            ),
            **(
                {
                    "supplier_unapply_selected_sql_module_count": supplier_unapply_delete_boundary[
                        "summary"
                    ]["selected_sql_module_count"],
                    "supplier_unapply_sql_local_transaction_count": supplier_unapply_delete_boundary[
                        "summary"
                    ]["selected_module_with_local_transaction_count"],
                    "supplier_unapply_multi_receipt_invoice_count": supplier_unapply_delete_boundary[
                        "summary"
                    ]["unapplied_multi_receipt_invoice_count"],
                    "supplier_unapply_retained_relation_delete_count": supplier_unapply_delete_boundary[
                        "summary"
                    ]["retained_relation_delete_event_count"],
                    "supplier_unapply_recent_relation_delete_count": supplier_unapply_delete_boundary[
                        "summary"
                    ]["recent_relation_delete_event_count"],
                    "supplier_unapply_runtime_selected_method_count": supplier_unapply_delete_runtime_boundary[
                        "summary"
                    ]["selected_method_count"],
                    "supplier_unapply_runtime_operation_code_three": supplier_unapply_delete_runtime_boundary[
                        "managed_unlink_delete_contract"
                    ]["unlink_operation_code_three_precedes_operation_call"],
                }
                if supplier_unapply_delete_boundary is not None
                else {}
            ),
            **(
                {
                    "payable_cheque_undo_selected_sql_module_count": payable_cheque_undo_boundary[
                        "summary"
                    ]["selected_sql_module_count"],
                    "payable_cheque_undo_current_history_count": payable_cheque_undo_boundary[
                        "summary"
                    ]["current_history_count"],
                    "payable_cheque_undo_retained_history_delete_count": payable_cheque_undo_boundary[
                        "summary"
                    ]["retained_history_delete_event_count"],
                    "payable_cheque_undo_exact_tail_count": payable_cheque_undo_boundary[
                        "summary"
                    ]["exact_undo_tail_history_delete_count"],
                    "payable_cheque_undo_recent_exact_tail_count": payable_cheque_undo_boundary[
                        "summary"
                    ]["recent_exact_undo_tail_count"],
                    "payable_cheque_undo_no_delete_log_absent_count": payable_cheque_undo_boundary[
                        "summary"
                    ]["insert_logged_absent_without_delete_count"],
                    "payable_cheque_undo_runtime_selected_method_count": payable_cheque_undo_runtime_boundary[
                        "summary"
                    ]["selected_method_count"],
                }
                if payable_cheque_undo_boundary is not None
                else {}
            ),
            **(
                {
                    "received_cheque_undo_selected_sql_module_count": received_cheque_undo_boundary[
                        "summary"
                    ]["selected_sql_module_count"],
                    "received_cheque_undo_current_history_count": received_cheque_undo_boundary[
                        "summary"
                    ]["current_history_count"],
                    "received_cheque_undo_retained_history_delete_count": received_cheque_undo_boundary[
                        "summary"
                    ]["retained_history_delete_event_count"],
                    "received_cheque_undo_command_tail_count": received_cheque_undo_boundary[
                        "summary"
                    ]["undo_command_tail_count"],
                    "received_cheque_undo_double_delete_command_count": received_cheque_undo_boundary[
                        "summary"
                    ]["conditional_double_delete_command_count"],
                    "received_cheque_undo_recent_command_tail_count": received_cheque_undo_boundary[
                        "summary"
                    ]["recent_undo_command_tail_count"],
                    "received_cheque_undo_no_delete_log_absent_count": received_cheque_undo_boundary[
                        "summary"
                    ]["insert_logged_absent_without_delete_count"],
                    "received_cheque_undo_runtime_selected_method_count": received_cheque_undo_runtime_boundary[
                        "summary"
                    ]["selected_method_count"],
                }
                if received_cheque_undo_boundary is not None
                else {}
            ),
            **(
                {
                    "received_cheque_delete_selected_sql_module_count": received_cheque_delete_boundary[
                        "summary"
                    ]["selected_sql_module_count"],
                    "received_cheque_direct_master_delete_candidate_count": received_cheque_delete_boundary[
                        "summary"
                    ]["direct_master_delete_candidate_count"],
                    "received_cheque_retained_master_delete_count": received_cheque_delete_boundary[
                        "summary"
                    ]["retained_master_delete_event_count"],
                    "received_cheque_recent_master_delete_count": received_cheque_delete_boundary[
                        "summary"
                    ]["recent_master_delete_event_count"],
                    "received_cheque_receipt_delete_batch_count": received_cheque_delete_boundary[
                        "summary"
                    ]["receipt_delete_batch_count"],
                    "received_cheque_receipt_delete_tail_master_count": received_cheque_delete_boundary[
                        "summary"
                    ]["receipt_delete_tail_master_count"],
                    "received_cheque_receipt_update_tail_master_count": received_cheque_delete_boundary[
                        "summary"
                    ]["receipt_update_tail_master_count"],
                    "received_cheque_isolated_delete_tail_count": received_cheque_delete_boundary[
                        "summary"
                    ]["isolated_tail_master_count"],
                    "received_cheque_delete_runtime_selected_method_count": received_cheque_delete_runtime_boundary[
                        "summary"
                    ]["selected_method_count"],
                }
                if received_cheque_delete_boundary is not None
                else {}
            ),
            **(
                {
                    "stock_voucher_selected_sql_module_count": stock_voucher_state_boundary[
                        "summary"
                    ]["selected_sql_module_count"],
                    "stock_voucher_current_count": stock_voucher_state_boundary["summary"][
                        "current_voucher_count"
                    ],
                    "stock_voucher_current_confirmed_count": stock_voucher_state_boundary[
                        "summary"
                    ]["current_confirmed_voucher_count"],
                    "stock_voucher_retained_confirm_transition_count": stock_voucher_state_boundary[
                        "summary"
                    ]["retained_confirm_transition_count"],
                    "stock_voucher_retained_unconfirm_transition_count": stock_voucher_state_boundary[
                        "summary"
                    ]["retained_unconfirm_transition_count"],
                    "stock_voucher_retained_delete_count": stock_voucher_state_boundary["summary"][
                        "retained_delete_count"
                    ],
                    "stock_voucher_direct_confirmed_delete_without_unconfirm_count": stock_voucher_state_boundary[
                        "summary"
                    ]["direct_confirmed_delete_without_unconfirm_count"],
                    "stock_voucher_runtime_selected_method_count": stock_voucher_state_runtime_boundary[
                        "summary"
                    ]["selected_method_count"],
                }
                if stock_voucher_state_boundary is not None
                else {}
            ),
            **(
                {
                    "stock_projection_validation_selected_sql_module_count": stock_projection_validation_boundary[
                        "summary"
                    ]["selected_sql_module_count"],
                    "stock_cardex_effect_rule_count": stock_projection_validation_boundary[
                        "summary"
                    ]["cardex_effect_row_count"],
                    "stock_cardex_effect_voucher_type_count": stock_projection_validation_boundary[
                        "summary"
                    ]["cardex_effect_voucher_type_count"],
                    "stock_projection_row_count": stock_projection_validation_boundary["summary"][
                        "stock_projection_row_count"
                    ],
                    "stock_projection_negative_component_count": stock_projection_validation_boundary[
                        "summary"
                    ]["stock_projection_negative_component_count"],
                }
                if stock_projection_validation_boundary is not None
                else {}
            ),
            **(
                {
                    "distribution_exit_selected_sql_module_count": distribution_exit_lifecycle_boundary[
                        "summary"
                    ]["selected_sql_module_count"],
                    "distribution_exit_current_count": distribution_exit_lifecycle_boundary[
                        "summary"
                    ]["current_exit_count"],
                    "distribution_exit_current_active_count": distribution_exit_lifecycle_boundary[
                        "summary"
                    ]["current_active_exit_count"],
                    "distribution_exit_current_cancelled_count": distribution_exit_lifecycle_boundary[
                        "summary"
                    ]["current_cancelled_exit_count"],
                    "distribution_exit_recent_cancelled_count": distribution_exit_lifecycle_boundary[
                        "summary"
                    ]["recent_cancelled_exit_count"],
                    "distribution_exit_historical_absent_count": distribution_exit_lifecycle_boundary[
                        "summary"
                    ]["logged_exit_absent_count"],
                    "distribution_exit_direct_physical_delete_candidate_count": distribution_exit_lifecycle_boundary[
                        "summary"
                    ]["direct_physical_exit_delete_candidate_count"],
                    "distribution_exit_runtime_selected_method_count": distribution_exit_runtime_boundary[
                        "summary"
                    ]["selected_method_count"],
                }
                if distribution_exit_lifecycle_boundary is not None
                else {}
            ),
            **(
                {
                    "sale_conversion_selected_sql_module_count": sale_conversion_state_boundary[
                        "summary"
                    ]["selected_sql_module_count"],
                    "sale_conversion_current_sale_count": sale_conversion_state_boundary[
                        "summary"
                    ]["current_sale_count"],
                    "sale_conversion_current_active_sale_count": sale_conversion_state_boundary[
                        "summary"
                    ]["current_active_sale_count"],
                    "sale_conversion_current_cancelled_sale_count": sale_conversion_state_boundary[
                        "summary"
                    ]["current_cancelled_sale_count"],
                    "sale_conversion_active_projection_mismatch_count": sale_conversion_state_boundary[
                        "summary"
                    ]["active_latest_detail_status_mismatch_count"],
                    "sale_conversion_retained_delete_count": sale_conversion_state_boundary[
                        "summary"
                    ]["retained_sale_delete_log_count"],
                    "sale_conversion_runtime_selected_method_count": sale_conversion_runtime_boundary[
                        "summary"
                    ]["selected_method_count"],
                }
                if sale_conversion_state_boundary is not None
                else {}
            ),
            **(
                {
                    "order_sale_policy_selected_sql_command_count": order_sale_policy_flag_sql[
                        "summary"
                    ]["selected_command_count"],
                    "order_sale_policy_declared_only_wrapper_flag_count": order_sale_policy_flag_sql[
                        "summary"
                    ]["wrapper_declared_but_not_used_after_declaration_count"],
                    "order_sale_policy_runtime_matched_method_count": order_sale_policy_flag_runtime[
                        "summary"
                    ]["matched_method_count"],
                    "order_sale_policy_runtime_flag_reference_count": order_sale_policy_flag_runtime[
                        "summary"
                    ]["flag_with_runtime_member_reference_count"],
                }
                if order_sale_policy_flag_sql is not None
                else {}
            ),
            **(
                {
                    "order_sale_policy_gate_configured_control_count": order_sale_policy_gate_runtime[
                        "summary"
                    ]["policy_control_count"],
                    "order_sale_policy_gate_permission_decision_call_count": len(
                        order_sale_policy_gate_runtime["selected_permission_method_contract"][
                            "named_permission_decision_calls"
                        ]
                    ),
                    "order_sale_policy_current_dc_config_count": order_sale_policy_config_snapshot[
                        "summary"
                    ]["dc_count"],
                    "order_sale_policy_current_null_cell_count": order_sale_policy_config_snapshot[
                        "summary"
                    ]["null_policy_cell_count"],
                }
                if order_sale_policy_gate_runtime is not None
                else {}
            ),
            **(
                {
                    "order_sale_operation_date_sql_module_count": order_sale_operation_date_sql[
                        "summary"
                    ]["selected_sql_module_count"],
                    "order_sale_operation_date_current_sale_boundary_count": order_sale_operation_date_sql[
                        "summary"
                    ]["sale_boundary_row_count"],
                    "order_sale_operation_date_configured_special_type_count": order_sale_operation_date_sql[
                        "summary"
                    ]["configured_special_order_type_count"],
                    "order_sale_operation_date_current_special_order_count": order_sale_operation_date_sql[
                        "summary"
                    ]["current_special_order_count"],
                    "order_sale_operation_date_runtime_method_count": order_sale_operation_date_runtime[
                        "summary"
                    ]["selected_method_count"],
                    "order_sale_operation_date_automatic_flow_count": len(
                        order_sale_operation_date_runtime["contract"]["automatic_date_flows"]
                    ),
                }
                if order_sale_operation_date_sql is not None
                else {}
            ),
            **(
                {
                    "order_sale_authorization_sql_module_count": order_sale_authorization_sql[
                        "summary"
                    ]["selected_sql_module_count"],
                    "order_sale_authorization_form_permission_call_count": order_sale_authorization_runtime[
                        "summary"
                    ]["order_to_sale_form_permission_call_count"],
                    "order_sale_authorization_order_type_ui_callsite_count": order_sale_authorization_runtime[
                        "summary"
                    ]["order_type_permission_ui_callsite_count"],
                    "order_sale_authorization_current_global_area_gate_count": order_sale_authorization_sql[
                        "summary"
                    ]["global_area_access_enabled_key_count"],
                }
                if order_sale_authorization_sql is not None
                else {}
            ),
            **(
                {
                    "datacontext_managed_assembly_scan_count": datacontext_transaction_runtime[
                        "summary"
                    ]["managed_inventory_assembly_scan_count"],
                    "datacontext_custom_factory_setter_callsite_count": datacontext_transaction_runtime[
                        "summary"
                    ]["custom_provider_or_connection_factory_setter_callsite_count"],
                    "datacontext_order_sale_split_transaction": not datacontext_transaction_runtime[
                        "contract"
                    ]["discount_v2_preparation_and_sale_conversion_share_physical_transaction"],
                }
                if datacontext_transaction_runtime is not None
                else {}
            ),
            **(
                {
                    "order_sale_evc_managed_assembly_scan_count": order_sale_evc_runtime_boundary[
                        "summary"
                    ]["managed_inventory_assembly_scan_count"],
                    "order_sale_evc_calc_flag_setter_callsite_count": order_sale_evc_runtime_boundary[
                        "summary"
                    ]["calc_for_discount_v2_setter_callsite_count"],
                    "order_sale_evc_double_temp_sql_module_count": order_sale_evc_sql_boundary[
                        "summary"
                    ]["double_temp_name_module_count"],
                    "order_sale_evc_double_temp_create_literal_count": len(
                        order_sale_evc_runtime_boundary["inventory_temp_table_literal_scan"][
                            "double_temp_create_literal_files"
                        ]
                    ),
                }
                if order_sale_evc_sql_boundary is not None
                else {}
            ),
            **(
                {
                    "discount_v2_query_template_count": discount_v2_query_contracts["summary"][
                        "query_template_count"
                    ],
                    "discount_v2_formatted_template_count": discount_v2_query_contracts["summary"][
                        "formatted_template_count"
                    ],
                    "discount_v2_persistent_dependency_count": discount_v2_dataset_sql["summary"][
                        "persistent_reference_count"
                    ],
                    "discount_v2_resolved_dependency_count": discount_v2_dataset_sql["summary"][
                        "resolved_reference_count"
                    ],
                    "discount_v2_clone_rcsi_enabled": bool(
                        discount_v2_dataset_sql["database_isolation"]["is_read_committed_snapshot_on"]
                    ),
                }
                if discount_v2_query_contracts is not None
                else {}
            ),
            **(
                {
                    "discount_v2_engine_assembly_count": discount_v2_engine_runtime["summary"][
                        "engine_assembly_count"
                    ],
                    "discount_v2_engine_managed_method_count": discount_v2_engine_runtime["summary"][
                        "managed_method_count"
                    ],
                    "discount_v2_engine_selected_method_count": discount_v2_engine_runtime["summary"][
                        "selected_method_count"
                    ],
                    "discount_v2_per_candidate_dynamic_query_loop_count": discount_v2_engine_runtime["summary"][
                        "sds_per_candidate_dynamic_query_loop_count"
                    ],
                    "discount_v2_advanced_condition_count": discount_v2_dynamic_rule_sql["summary"][
                        "primary_nonempty_condition_count"
                    ],
                    "discount_v2_distinct_condition_hash_count": discount_v2_dynamic_rule_sql["summary"][
                        "primary_distinct_condition_hash_count"
                    ],
                    "discount_v2_condition_write_shape_count": discount_v2_dynamic_rule_sql["summary"][
                        "primary_write_dml_shape_count"
                    ],
                    **(
                        {
                            "discount_v2_condition_family_count": discount_v2_condition_families["summary"][
                                "condition_family_count"
                            ],
                            "discount_v2_three_month_used_condition_family_count": discount_v2_condition_families["summary"][
                                "three_month_used_condition_family_count"
                            ],
                            "discount_v2_three_month_advanced_applied_row_count": discount_v2_condition_families["summary"][
                                "three_month_advanced_condition_applied_row_count"
                            ],
                            "discount_v2_current_effective_advanced_rule_count": discount_v2_condition_families["summary"][
                                "current_effective_rule_instance_count"
                            ],
                            "discount_v2_current_effective_condition_family_count": discount_v2_condition_families["summary"][
                                "current_effective_condition_family_count"
                            ],
                            **(
                                {
                                    "discount_rule_authoring_selected_method_count": discount_rule_authoring_boundary["summary"]["selected_method_count"],
                                    "discount_rule_authoring_dynamic_validation_execute_count": discount_rule_authoring_boundary["summary"]["validation_adapter_dynamic_execute_count"],
                                    "discount_rule_authoring_method_local_authorization_reference_count": discount_rule_authoring_boundary["summary"]["method_local_authorization_reference_count"],
                                    "discount_rule_authoring_discount_specific_authorization_reference_count": discount_rule_authoring_boundary["summary"]["discount_specific_method_local_authorization_reference_count"],
                                    "discount_rule_authoring_internal_command_permission_recheck_count": discount_rule_authoring_boundary["summary"]["internal_command_permission_recheck_count"],
                                    **(
                                        {
                                            "discount_rule_authorization_node_count": discount_rule_authorization_boundary["summary"]["authorization_node_count"],
                                            "discount_rule_authorization_command_node_count": discount_rule_authorization_boundary["summary"]["command_node_count"],
                                            "discount_rule_authorization_root_effective_allow_count": discount_rule_authorization_boundary["summary"]["root_effective_allow_count"],
                                        }
                                        if discount_rule_authorization_boundary is not None
                                        else {}
                                    ),
                                }
                                if discount_rule_authoring_boundary is not None
                                else {}
                            ),
                        }
                        if discount_v2_condition_families is not None
                        else {}
                    ),
                }
                if discount_v2_engine_runtime is not None
                else {}
            ),
            **(
                {
                    "ngt_operation_date_current_selector": ngt_operation_date_boundary[
                        "contract"
                    ]["current_date_selector_code_enum_name"],
                    "ngt_operation_date_current_sentinel_count": ngt_operation_date_boundary[
                        "summary"
                    ]["ngt_sentinel_operation_date_count"],
                    "ngt_operation_date_sql_consumer_count": ngt_operation_date_boundary[
                        "summary"
                    ]["sql_consumer_count"],
                    "ngt_operation_date_sql_global_boundary_consumer_count": ngt_operation_date_boundary[
                        "summary"
                    ]["sql_consumer_references_global_tbl_opr_date_count"],
                }
                if ngt_operation_date_boundary is not None
                else {}
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
