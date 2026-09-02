"""Build target Command/Query contracts for material Varanegar extension surfaces.

This builder is offline. It consumes the redacted method-path artifact and never
loads assemblies, connects to SQL Server, or invokes the live application.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


COMMAND_DESIGNS: tuple[dict[str, Any], ...] = (
    {
        "command": "authorization.publish_stock_accounting_scope_matrix",
        "capability": "authorization.stock_accounting_access",
        "owner": "identity_authorization",
        "aggregate": "stock_accounting_scope_policy",
        "invariants": [
            "actor has policy-publish permission in the same organization context",
            "subject kind and subject identity are explicit and active",
            "every requested scope belongs to the actor's delegable scope",
            "deny by default; no implicit grant is inferred from menu visibility",
            "policy version advances once and preserves a complete before/after audit diff",
        ],
        "failure_stages": ["scope validation", "policy version append", "effective projection rebuild", "audit/outbox append"],
        "reconciliation": ["requested_vs_effective_scopes", "orphan_subjects", "policy_version_chain", "audit_outbox"],
    },
    {
        "command": "configuration.save_accounting_article_template_version",
        "capability": "configuration.accounting_article_template",
        "owner": "accounting",
        "aggregate": "accounting_article_template",
        "invariants": [
            "template identity and accounting context are explicit",
            "debit and credit rules are structurally valid and balanced where required",
            "published historical versions remain immutable",
            "deletion is a separately authorized retirement transition, never physical loss of used history",
        ],
        "failure_stages": ["template validation", "version append", "current pointer advance", "audit/outbox append"],
        "reconciliation": ["template_version_chain", "debit_credit_rule_shape", "consumer_references", "audit_outbox"],
    },
    {
        "command": "configuration.publish_general_version",
        "capability": "configuration.general",
        "owner": "configuration",
        "aggregate": "general_configuration",
        "invariants": [
            "configuration keys are allowlisted and typed",
            "effective date and organization context are explicit",
            "secrets are never accepted through this command",
            "published versions are immutable and rollback creates a new version",
        ],
        "failure_stages": ["schema validation", "version append", "effective pointer advance", "cache invalidation event"],
        "reconciliation": ["effective_configuration_hash", "version_chain", "consumer_acknowledgements", "audit_outbox"],
    },
    {
        "command": "configuration.publish_web_service_version",
        "capability": "configuration.web_service",
        "owner": "configuration",
        "aggregate": "web_service_configuration",
        "invariants": [
            "endpoint scheme and destination are allowlisted",
            "secret values are referenced by vault handle and never returned or logged",
            "activation requires an explicit authorized actor and expected version",
            "connectivity test is non-mutating and is not proof of provider business success",
        ],
        "failure_stages": ["endpoint policy validation", "secret-reference validation", "version append", "activation event"],
        "reconciliation": ["active_version_pointer", "secret_reference_health", "consumer_acknowledgements", "audit_outbox"],
    },
    {
        "command": "pos.save_charge_device",
        "capability": "pos.charge_device",
        "owner": "receivables_treasury",
        "aggregate": "pos_charge_device",
        "invariants": [
            "device identity is unique within organization and cashier context",
            "receiver safe and settlement destination are active and scoped",
            "device reassignment uses expected version and is fully audited",
            "retirement is rejected while an open session or unsettled transaction references the device",
        ],
        "failure_stages": ["device uniqueness check", "scope validation", "aggregate append", "integration/outbox append"],
        "reconciliation": ["device_cashier_safe_crosswalk", "open_session_references", "provider_device_identity", "audit_outbox"],
    },
    {
        "command": "pos.save_instalment_method_version",
        "capability": "pos.instalment_method",
        "owner": "receivables_treasury",
        "aggregate": "instalment_method",
        "invariants": [
            "term count, interval, rounding and amount rules are internally consistent",
            "effective dates do not overlap for the same method/context",
            "contracts already using a version retain that immutable version",
            "retirement does not rewrite prior receivable schedules",
        ],
        "failure_stages": ["rule validation", "version append", "effective pointer advance", "audit/outbox append"],
        "reconciliation": ["effective_interval_overlap", "schedule_calculation_samples", "referenced_versions", "audit_outbox"],
    },
    {
        "command": "pos.replicate_session_sales_receipts",
        "capability": "pos.session",
        "owner": "sales",
        "aggregate": "pos_receipt_replication_batch",
        "invariants": [
            "source session and receipt set are explicit, scoped and frozen by a source watermark",
            "every receipt has a stable source identity/version and exactly one target crosswalk",
            "retry cannot duplicate sale, receipt or settlement effects",
            "partial per-receipt failure is quarantined and never silently acknowledged",
            "target-local batch acknowledgement follows durable apply and successful reconciliation; no Varanegar write-back is allowed",
        ],
        "failure_stages": ["batch identity reservation", "receipt apply", "source-target crosswalk append", "outbox/ack append"],
        "reconciliation": ["source_target_receipt_count", "amount_currency_totals", "receipt_crosswalk_uniqueness", "duplicate_effect_detection", "failed_receipt_quarantine"],
    },
    {
        "command": "pricing.publish_linear_discount_version",
        "capability": "pos.linear_discount",
        "owner": "pricing_rules",
        "aggregate": "linear_discount_rule",
        "invariants": [
            "goods/customer/context/effective-period scope is explicit",
            "threshold bands are ordered, non-overlapping and deterministic",
            "percentage and amount bounds pass the approved policy",
            "a sale keeps the exact rule version and calculation trace used at pricing time",
        ],
        "failure_stages": ["band validation", "conflict detection", "version append", "effective index/outbox append"],
        "reconciliation": ["band_gap_overlap", "golden_price_calculations", "effective_rule_index", "audit_outbox"],
    },
    {
        "command": "party.save_pos_subscriber",
        "capability": "pos.subscriber",
        "owner": "master_data",
        "aggregate": "pos_subscriber",
        "invariants": [
            "subscriber identity and normalized contact keys satisfy duplicate policy",
            "personal fields are minimized, scoped and audited",
            "merge or retirement is explicit and preserves transaction provenance",
            "retry with the same command_id returns the original subscriber identity",
        ],
        "failure_stages": ["duplicate check", "PII policy validation", "aggregate append", "search index/outbox append"],
        "reconciliation": ["duplicate_candidates", "identity_crosswalk", "transaction_references", "audit_outbox"],
    },
    {
        "command": "distribution.publish_dealer_day_path_version",
        "capability": "tablet.dealer_day_path",
        "owner": "distribution",
        "aggregate": "dealer_day_path",
        "invariants": [
            "dealer, workday and route context are active and scoped",
            "a dealer/day assignment has no conflicting active version",
            "published history is immutable and edit creates a new version",
            "delete is a separately authorized retirement transition",
        ],
        "failure_stages": ["assignment validation", "conflict detection", "version append", "mobile-sync outbox append"],
        "reconciliation": ["dealer_day_conflicts", "route_version_chain", "mobile_sync_acknowledgements", "audit_outbox"],
    },
    {
        "command": "distribution.publish_visit_template_version",
        "capability": "tablet.visit_template",
        "owner": "distribution",
        "aggregate": "visit_template",
        "invariants": [
            "template steps and required fields form a valid ordered workflow",
            "region/context references are active and scoped",
            "published templates are immutable and offline clients retain version provenance",
            "Excel import is staged, validated and reviewed before publication",
        ],
        "failure_stages": ["schema/import validation", "reference validation", "version append", "mobile-sync outbox append"],
        "reconciliation": ["step_order_and_required_fields", "region_scope", "client_version_adoption", "audit_outbox"],
    },
)


QUERY_DESIGNS: tuple[dict[str, Any], ...] = (
    {
        "query": "pos.read_scoped_safes",
        "capability": "pos.safe",
        "owner": "receivables_treasury",
        "projection": "pos_safe_directory",
        "rules": [
            "read only and scoped by actor, organization and operational context",
            "returns stable identifiers and status; sensitive balance fields require a separate capability",
            "pagination/filter semantics are deterministic and every access is auditable",
        ],
    },
    {
        "query": "pos.read_scoped_sessions",
        "capability": "pos.session",
        "owner": "receivables_treasury",
        "projection": "pos_session_summary",
        "rules": [
            "read only and scoped by actor, organization, safe and operational date",
            "session state is a projection; receipt replication uses a separate evidenced command",
            "money totals expose currency, cutoff and reconciliation status",
        ],
    },
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _evidence_for(row: dict[str, Any]) -> dict[str, Any]:
    methods = row["methods"]
    command_methods = sorted(
        {method["ui_method"] for method in methods if "command_candidate" in method["role"]}
    )
    guard_methods = sorted(
        {method["ui_method"] for method in methods if "guard_candidate" in method["role"]}
    )
    business_edges = sorted(
        {
            (edge["target_type"], edge["called_member"])
            for method in methods
            for edge in method["edges"]
            if edge["target_layer"].startswith("business")
        }
    )
    direct_data_access_edges = sorted(
        {
            (edge["target_type"], edge["called_member"])
            for method in methods
            for edge in method["edges"]
            if edge["target_layer"] == "data_access"
        }
    )
    return {
        "source_ui_type": row["ui_type"],
        "source_ui_assembly": row["ui_assembly"],
        "source_command_candidate_methods": command_methods,
        "source_guard_candidate_methods": guard_methods,
        "source_business_calls": [
            {"target_type": target, "called_member": member}
            for target, member in business_edges
        ],
        "source_direct_data_access_calls": [
            {"target_type": target, "called_member": member}
            for target, member in direct_data_access_edges
        ],
        "source_transaction_signal_count": sum(
            len(method["transaction_signals"]) for method in methods
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-paths", required=True, type=Path)
    parser.add_argument("--gap-paths", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = _load(args.command_paths)
    gap_source = _load(args.gap_paths)
    by_capability = {row["capability_hint"]: row for row in source["capability_paths"]}
    gap_by_capability = {row["capability"]: row for row in gap_source["capability_paths"]}
    gap_types_by_capability: dict[str, list[dict[str, Any]]] = {}
    for capability in gap_by_capability:
        gap_types_by_capability[capability] = [
            row for row in gap_source["type_contracts"] if row["capability"] == capability
        ]
    errors: list[str] = []
    commands = []
    for design in COMMAND_DESIGNS:
        source_row = by_capability.get(design["capability"])
        if source_row is None:
            errors.append(f"missing source capability: {design['capability']}")
            continue
        evidence = _evidence_for(source_row)
        gap = gap_by_capability.get(design["capability"])
        gap_types = gap_types_by_capability.get(design["capability"], [])
        deep_mutation_calls = sorted(
            {
                call
                for row in gap_types
                for method in row["methods"]
                for call in method["calls"]
                if call.endswith(("ExecuteNonQuery", "Transaction.Start", "Transaction.Commit", "Transaction.RollBack"))
            }
        )
        deep_method_evidence = sorted(
            {
                f"{row['type']}.{method['method']}"
                for row in gap_types
                for method in row["methods"]
                if method["method"] in {"Send", "SaveCommand", "GenerateLinearDiscountId", "LinearDiscountIsUsed"}
            }
        )
        deep_evidence = {
            "related_type_count": 0 if gap is None else gap["type_count"],
            "method_evidence": deep_method_evidence,
            "mutation_or_transaction_calls": deep_mutation_calls,
            "allowlisted_business_literals": [] if gap is None else gap["allowlisted_business_literals"],
        }
        has_deep_pos_session_command = (
            design["capability"] == "pos.session"
            and any(call.endswith("ExecuteNonQuery") for call in deep_mutation_calls)
            and any(literal.strip().casefold() == "usp_replicatesalesreceipt" for literal in deep_evidence["allowlisted_business_literals"])
        )
        if not evidence["source_command_candidate_methods"] and not has_deep_pos_session_command:
            errors.append(f"command lacks command-candidate evidence: {design['command']}")
        commands.append(
            {
                **design,
                "required_envelope": [
                    "command_id",
                    "correlation_id",
                    "aggregate_id",
                    "expected_version",
                    "actor_context",
                    "organization_context",
                    "operational_date",
                ],
                "required_result": [
                    "command_id",
                    "aggregate_id",
                    "new_version",
                    "audit_event_id",
                    "reconciliation_status",
                ],
                "transaction_owner": "one target application service owns aggregate append, current pointer and outbox atomically",
                "idempotency": "same command_id and payload returns the original result; different payload with the same command_id is rejected",
                "source_evidence": evidence,
                "deep_gap_evidence": deep_evidence,
                "readiness": "TARGET_DESIGN_ONLY_NOT_COMMAND_OR_PILOT_READY",
            }
        )

    queries = []
    for design in QUERY_DESIGNS:
        source_row = by_capability.get(design["capability"])
        if source_row is None:
            errors.append(f"missing source capability: {design['capability']}")
            continue
        evidence = _evidence_for(source_row)
        queries.append(
            {
                **design,
                "required_context": ["actor_context", "organization_context", "operational_date", "page_token", "page_size"],
                "mutation_policy": "NO_MUTATION; query handler cannot call command services or write data",
                "source_evidence": evidence,
                "coexisting_command_policy": "A read projection may coexist with an independently authorized command; the query handler itself remains mutation-free.",
                "readiness": "TARGET_DESIGN_ONLY_NOT_UAT_OR_PRODUCTION_READY",
            }
        )

    artifact = {
        "artifact": "negin_erp_material_extension_target_command_query_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_TARGET_CONTRACT_DESIGN_FROM_REDACTED_METHOD_PATH_EVIDENCE",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "credentials_or_secrets_read_or_persisted": 0,
        },
        "summary": {
            "source_capability_count": len(by_capability),
            "target_command_count": len(commands),
            "target_query_count": len(queries),
            "command_source_candidate_method_count": sum(len(row["source_evidence"]["source_command_candidate_methods"]) for row in commands),
            "command_with_ui_command_candidate_count": sum(bool(row["source_evidence"]["source_command_candidate_methods"]) for row in commands),
            "command_with_deep_execute_non_query_evidence_count": sum(any(call.endswith("ExecuteNonQuery") for call in row["deep_gap_evidence"]["mutation_or_transaction_calls"]) for row in commands),
            "command_with_direct_data_access_source_count": sum(bool(row["source_evidence"]["source_direct_data_access_calls"]) for row in commands),
            "query_with_ui_command_candidate_count": sum(bool(row["source_evidence"]["source_command_candidate_methods"]) for row in queries),
            "query_with_coexisting_target_command_count": sum(row["capability"] in {command["capability"] for command in commands} for row in queries),
            "source_transaction_signal_count": sum(row["source_evidence"]["source_transaction_signal_count"] for row in commands + queries),
            "deep_transaction_call_count": sum(len(row["deep_gap_evidence"]["mutation_or_transaction_calls"]) for row in commands),
            "validation_error_count": len(errors),
        },
        "commands": commands,
        "queries": queries,
        "shared_execution_rules": [
            "Varanegar remains read-only; these are target ERP contracts, not legacy commands.",
            "authorization is checked inside the application service before mutation and is rechecked for delegated scope.",
            "one application service owns aggregate append, current-pointer update and transactional outbox atomically.",
            "cross-module effects are idempotent consumers; no distributed dual write is accepted.",
            "history is immutable; edit, retirement and rollback append versions or transitions.",
            "every declared failure stage requires retry, duplicate-delivery and reconciliation tests.",
        ],
        "evidence_errors": errors,
        "limits": [
            "Method roles and static calls identify evidence-backed surfaces but do not prove runtime execution order.",
            "No explicit transaction signal in selected UI/business bodies does not prove that deeper legacy code lacks a transaction.",
            "Fields, authorization scope and owner mapping require role UAT and business-owner acceptance before implementation freeze.",
            "No command or query was executed against Varanegar, the clone, or a target database.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
