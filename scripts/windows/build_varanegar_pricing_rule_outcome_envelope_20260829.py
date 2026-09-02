"""Build the Pricing Rules command outcome, retry, allocation and publication contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "commands": "artifacts/varanegar_analysis/ui/varanegar_pricing_rule_command_contracts_20260827.json",
    "authoring": "artifacts/varanegar_analysis/domains/discount_rule_authoring_boundary_20260829.json",
    "authorization": "artifacts/varanegar_analysis/domains/discount_rule_authorization_boundary_20260829.json",
    "engine": "artifacts/varanegar_analysis/domains/discount_v2_engine_runtime_20260829.json",
    "dynamic_sql": "artifacts/varanegar_analysis/domains/discount_v2_dynamic_rule_sql_20260829.json",
    "families": "artifacts/varanegar_analysis/domains/discount_v2_condition_families_20260829.json",
    "linear": "artifacts/varanegar_analysis/ui/varanegar_extension_gap_paths_20260827.json",
    "linear_target": "artifacts/varanegar_analysis/ui/varanegar_extension_target_contracts_20260827.json",
    "replication": "artifacts/varanegar_analysis/domains/rule_replication_transport_boundary_20260828.json",
    "legacy_counts": "artifacts/varanegar_analysis/domains/pricing_discounts_prizes_20260826.json",
    "golden": "artifacts/varanegar_analysis/ui/negin_erp_foundation_context_pricing_golden_cases_20260827.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_reporting_output_traceability_delta_checkpoint_20260829.json",
}
REQUEST = ["command_id", "payload_hash", "correlation_id", "actor_scope", "rule_family", "aggregate_id", "expected_version", "intent", "effective_window", "context_scope", "condition_ast_hash", "priority_tuple"]
RESPONSE = ["outcome_code", "command_id", "aggregate_id", "rule_version", "compile_receipt", "allocation_receipt", "audit_event_id", "outbox_event_id", "publication_state", "retryable", "reconciliation_status"]
OUTCOMES = ["REJECTED_NO_EFFECT", "VALIDATED_NO_MUTATION", "COMMITTED_DRAFT", "COMMITTED_PUBLISHED", "COMMITTED_CLOSED", "UNKNOWN_REQUIRES_READBACK"]
COMMANDS = [
    {"command": "pricing_rules.contextual_price.save", "aggregate": "contextual_price_rule", "intent": "CREATE_OR_APPEND_DRAFT", "legacy_anchor": "FormCPrice.SaveCommand", "transaction_owner": "target pricing application service", "special_rule": "append a version; never overwrite a calculation-proven version"},
    {"command": "pricing_rules.contextual_price.delete_or_close", "aggregate": "contextual_price_rule", "intent": "CLOSE_VERSION", "legacy_anchor": "FormCPrice.DeleteCommand", "transaction_owner": "target pricing application service", "special_rule": "used or published rules close; physical erase is forbidden"},
    {"command": "pricing_rules.contextual_price.change_priority", "aggregate": "contextual_price_rule", "intent": "APPEND_PRIORITY_VERSION", "legacy_anchor": "FormCPrice.ChangePriorityOnGrid/SetPriority", "transaction_owner": "target pricing application service", "special_rule": "precedence is a deterministic tuple with a stable tie breaker"},
    {"command": "pricing_rules.discount_rule.save", "aggregate": "discount_rule", "intent": "CREATE_OR_APPEND_DRAFT", "legacy_anchor": "FormDiscount.SaveCommand", "transaction_owner": "target pricing application service", "special_rule": "COPY_AS_DRAFT receives a new immutable identity and is never implicitly published"},
    {"command": "pricing_rules.discount_rule.delete_or_close", "aggregate": "discount_rule", "intent": "CLOSE_VERSION", "legacy_anchor": "FormDiscount.DeleteCommand", "transaction_owner": "target pricing application service", "special_rule": "prevent-sale capability and calculation provenance survive closure"},
    {"command": "pricing_rules.discount_rule.validate_or_compile_condition", "aggregate": "discount_rule_draft", "intent": "VALIDATE_ONLY", "legacy_anchor": "GenerateDiscountCondition/btnCondition_Click", "transaction_owner": "none; side-effect-free application query", "special_rule": "accept only a versioned allowlisted AST/DSL; stored executable SQL is forbidden"},
    {"command": "pricing_rules.linear_discount.allocate_and_save", "aggregate": "linear_discount_rule", "intent": "ALLOCATE_AND_APPEND_VERSION", "legacy_anchor": "LinearDiscountHandler.GenerateLinearDiscountID -> LinearDiscountAdapter.GenerateLinearDiscountId", "transaction_owner": "one target application service owns atomic allocation, append, audit and outbox", "special_rule": "Sequence/Identity/UUID or another atomic allocator plus a unique constraint; never MAX(Id)+1"},
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / rel for name, rel in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    validated = ["commands", "authoring", "authorization", "engine", "dynamic_sql", "families", "linear", "linear_target", "golden", "risk", "trace", "previous"]
    linear_literals = next(x for x in data["linear"]["capability_paths"] if x["capability"] == "pos.linear_discount")["allowlisted_business_literals"]
    replication = data["replication"]["summary"]
    contracts = []
    for command in COMMANDS:
        contracts.append({
            **command,
            "request_fields": REQUEST,
            "response_fields": RESPONSE,
            "allowed_outcomes": OUTCOMES,
            "authorization": "application service rechecks author, publisher and scoped capability deny-first; UI toolbar state is not authority",
            "idempotency": "same CommandId plus PayloadHash returns the original receipt; a conflicting hash is rejected",
            "optimistic_concurrency": "ExpectedVersion mismatch rejects before durable effect",
            "audit_outbox": "aggregate append or close, immutable audit and outbox are atomic",
            "retry_rule": "read CommandId, aggregate version, audit and outbox receipts before retry; UNKNOWN is quarantined",
            "runtime_effect_parity": "UNPROVEN",
            "status": "TARGET_DESIGN_ONLY_NOT_IMPLEMENTED",
        })
    publication = {
        "name": "pricing_rules.publish_version_and_replicate",
        "classification": "TARGET_DURABLE_EFFECT_NOT_PROVEN_AS_A_DISTINCT_LEGACY_UI_COMMAND",
        "preconditions": ["draft compiled against an approved DSL/schema version", "publisher capability rechecked", "overlap and deterministic precedence accepted", "ExpectedVersion current"],
        "atomic_local_effects": ["published immutable version", "current effective index", "audit event", "outbox event"],
        "asynchronous_transport": ["signed/authenticated package", "stable package and center scope identity", "ordered idempotent receipt", "bounded deadline", "quarantine on unknown or rejected outcome"],
        "retry_rule": "never rerun local publication after commit; retry transport from the outbox identity after receipt read-back",
    }
    summary = {
        "command_contract_count": len(contracts),
        "existing_reused_golden_case_count": data["golden"]["summary"]["target_module_case_counts"]["pricing_rules"],
        "request_field_count": len(REQUEST),
        "response_field_count": len(RESPONSE),
        "outcome_code_count": len(OUTCOMES),
        "legacy_selected_method_count": data["commands"]["summary"]["selected_method_count"],
        "legacy_commit_owner_method_count": data["commands"]["summary"]["method_with_data_context_commit_count"],
        "stored_condition_setter_method_count": data["authoring"]["summary"]["selected_sql_condition_setter_method_count"],
        "validation_dynamic_execute_count": data["authoring"]["summary"]["validation_adapter_dynamic_execute_count"],
        "effective_allow_user_count": data["authorization"]["summary"]["root_effective_allow_count"],
        "active_user_count": data["authorization"]["summary"]["active_user_count"],
        "advanced_condition_family_count": data["families"]["summary"]["condition_family_count"],
        "current_effective_condition_family_count": data["families"]["summary"]["current_effective_condition_family_count"],
        "linear_max_id_plus_one_literal_count": sum("MAX(ISNULL(Id" in value for value in linear_literals),
        "replication_unproven_gate_count": sum(not replication[key] for key in ["replication_package_content_authentication_proven", "replication_receipt_idempotency_proven", "received_package_ordering_and_gap_check_proven", "package_center_scope_preexecution_validation_proven", "rejected_package_quarantine_and_retry_safety_proven", "rollback_failure_observability_proven"]),
        "runtime_effect_parity_proven_count": 0,
        "implemented_command_count": 0,
        "owner_approved_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
    }
    checks = {
        "validated_sources_pass": all(data[name]["validation"] == "PASS" for name in validated),
        "legacy_sources_structurally_present": data["replication"].get("artifact") is not None and data["legacy_counts"].get("domain") == "pricing_discounts_and_prizes",
        "seven_commands": len(contracts) == 7 and len({x["command"] for x in contracts}) == 7,
        "envelope_complete": len(REQUEST) == 12 and len(RESPONSE) == 11 and len(OUTCOMES) == 6,
        "four_existing_commands_reused": summary["existing_reused_golden_case_count"] == 64,
        "authoring_gaps_pinned": summary["stored_condition_setter_method_count"] == 2 and summary["validation_dynamic_execute_count"] == 4,
        "authorization_snapshot_not_service_authority": summary["effective_allow_user_count"] == 15 and summary["active_user_count"] == 141,
        "linear_allocator_gap_pinned": summary["linear_max_id_plus_one_literal_count"] == 1,
        "replication_gaps_pinned": summary["replication_unproven_gate_count"] == 6,
        "dsl_and_atomic_allocator_required": "AST/DSL" in contracts[5]["special_rule"] and "never MAX(Id)+1" in contracts[6]["special_rule"],
        "publication_is_not_false_legacy_command": publication["classification"].startswith("TARGET_DURABLE_EFFECT"),
        "runtime_zero": summary["runtime_effect_parity_proven_count"] == summary["implemented_command_count"] == summary["owner_approved_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": data["risk"]["summary"]["risk_count"] == 84 and data["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_pricing_rule_outcome_envelope_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_STATIC_AND_CONTRACT_SYNTHESIS", "database_connections": 0, "commands_forms_reports_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_or_raw_rule_text_persisted": 0},
        "summary": summary,
        "lifecycle": ["DRAFT", "VALIDATED", "PUBLISHED", "CLOSED"],
        "global_invariants": ["rules are immutable versions", "stored executable SQL is forbidden", "validation is side-effect-free", "priority uses a deterministic tuple and stable tie breaker", "published or used rules close and retain explain provenance", "audit and outbox commit atomically with the aggregate", "replication is asynchronous, authenticated, ordered and idempotent", "unknown outcomes require read-back and quarantine before retry"],
        "commands": contracts,
        "publication_contract": publication,
        "legacy_input_classification": {"replication": "LEGACY_STATIC_INPUT_WITHOUT_VALIDATION_GATE", "pricing_counts": "LEGACY_STATIC_INPUT_WITHOUT_VALIDATION_GATE"},
        "checks": checks,
        "failed_checks": failed,
        "risk_links": ["R-002", "R-005", "R-006", "R-007", "R-008", "R-023", "R-028", "R-034", "R-036", "R-043"],
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "confidence": {"static_command_and_rule_boundaries": "HIGH", "target_contract_design": "HIGH", "runtime_effect_parity": "UNPROVEN"},
        "limits": ["No rule, form, query, stored procedure or replication package was executed.", "Legacy aggregate counts are historical evidence, not production-current certification.", "No raw rule text, principal identity or business value is persisted."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
