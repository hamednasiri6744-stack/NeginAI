"""Build a design-only command idempotency and message convergence contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "blueprint": "artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json",
    "command_ledger": "artifacts/varanegar_analysis/varanegar_command_readiness_ledger_20260829.json",
    "cross_module": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_contract_20260829.json",
    "restore_dependency": "artifacts/varanegar_analysis/varanegar_target_erp_restore_dependency_wave_reconciliation_contract_20260829.json",
    "restore_dependency_checkpoint": "artifacts/varanegar_analysis/varanegar_target_erp_restore_dependency_wave_reconciliation_checkpoint_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

COMMAND_ENVELOPE_FIELDS = [
    "command_id",
    "module_id",
    "command_name",
    "tenant_reference_sha256",
    "organization_context_reference_sha256",
    "fiscal_and_operation_context_reference_sha256",
    "authorization_decision_receipt_sha256",
    "correlation_id",
    "causation_id",
    "idempotency_key_sha256",
    "canonical_request_fingerprint_sha256",
    "business_scope_reference_set_sha256",
    "expected_aggregate_version_set_sha256",
    "command_contract_version_sha256",
    "policy_version_sha256",
    "received_at",
    "deadline_at",
    "attempt_number",
    "retry_reason_code",
    "trace_reference_sha256",
    "payload_persistence_status",
    "envelope_sha256",
]

IDEMPOTENCY_RECEIPT_FIELDS = [
    "receipt_id",
    "idempotency_key_sha256",
    "canonical_request_fingerprint_sha256",
    "command_contract_version_sha256",
    "first_attempt_reference_sha256",
    "current_attempt_number",
    "transaction_boundary_reference_sha256",
    "aggregate_version_before_set_sha256",
    "aggregate_version_after_set_sha256",
    "business_effect_set_sha256",
    "outbox_event_id_set_sha256",
    "typed_outcome",
    "commit_state",
    "reconciliation_state",
    "created_at",
    "expires_at",
    "supersedes_receipt_sha256",
    "owner_review_receipt_reference",
    "independent_review_receipt_reference",
    "receipt_sha256",
]

OUTBOX_RECORD_FIELDS = [
    "event_id",
    "command_receipt_sha256",
    "module_id",
    "aggregate_reference_sha256",
    "aggregate_version",
    "event_type",
    "event_contract_version_sha256",
    "payload_fingerprint_sha256",
    "partition_key_sha256",
    "sequence_number",
    "occurred_at",
    "committed_at",
    "publish_attempt_count",
    "publication_state",
    "last_error_code",
    "record_sha256",
]

INBOX_RECORD_FIELDS = [
    "consumer_id",
    "event_id",
    "event_contract_version_sha256",
    "payload_fingerprint_sha256",
    "partition_key_sha256",
    "sequence_number",
    "first_received_at",
    "attempt_count",
    "processing_state",
    "effect_receipt_sha256",
    "consumer_watermark_reference_sha256",
    "last_error_code",
    "completed_at",
    "record_sha256",
]

FAILURE_STAGES = [
    ("CFS-01", "authorization_completed_before_idempotency_reservation"),
    ("CFS-02", "idempotency_key_reserved_before_transaction_begin"),
    ("CFS-03", "transaction_begun_before_first_business_effect"),
    ("CFS-04", "between_multiple_business_effects"),
    ("CFS-05", "after_business_effect_before_outbox_insert"),
    ("CFS-06", "after_outbox_insert_before_local_commit"),
    ("CFS-07", "commit_returned_unknown_or_connection_lost"),
    ("CFS-08", "after_commit_before_receipt_persisted_or_returned"),
    ("CFS-09", "response_lost_then_same_request_retried"),
    ("CFS-10", "same_key_reused_with_different_request_fingerprint"),
    ("CFS-11", "outbox_publish_failed_or_duplicated"),
    ("CFS-12", "consumer_received_duplicate_before_processing"),
    ("CFS-13", "consumer_effect_committed_before_acknowledgement"),
    ("CFS-14", "recovery_replay_attempted_before_watermark_reconciliation"),
]

CONVERGENCE_DIMENSIONS = [
    "ONE_COMMAND_RECEIPT_PER_KEY_AND_FINGERPRINT",
    "ONE_BUSINESS_EFFECT_SET_PER_ACCEPTED_COMMAND",
    "ONE_OUTBOX_EVENT_ID_PER_DECLARED_EVENT",
    "OUTBOX_COMMITTED_WITH_BUSINESS_EFFECTS",
    "ONE_INBOX_DECISION_PER_CONSUMER_AND_EVENT_ID",
    "CONSUMER_EFFECT_AND_INBOX_STATE_ATOMIC_OR_RECOVERABLE",
    "PARTITION_SEQUENCE_AND_WATERMARK_MONOTONIC",
    "UNKNOWN_OUTCOME_RECONCILED_BEFORE_RETRY_OR_REPLAY",
]

COMMAND_GATES = [
    ("CIG-01", "canonical_request_and_business_scope_fingerprints_versioned"),
    ("CIG-02", "idempotency_key_recipe_and_retention_policy_approved"),
    ("CIG-03", "same_key_same_fingerprint_returns_original_receipt"),
    ("CIG-04", "same_key_different_fingerprint_rejected_as_conflict"),
    ("CIG-05", "business_effects_receipt_and_outbox_share_transaction_owner"),
    ("CIG-06", "unique_business_and_outbox_constraints_declared"),
    ("CIG-07", "commit_unknown_routes_to_reconciliation_not_blind_retry"),
    ("CIG-08", "finite_deadline_and_cancellation_propagation_proven"),
    ("CIG-09", "outbox_publication_retry_is_idempotent"),
    ("CIG-10", "consumer_inbox_identity_unique_and_payload_conflict_rejected"),
    ("CIG-11", "consumer_effect_is_atomic_or_durably_recoverable"),
    ("CIG-12", "partition_order_gap_overlap_and_watermark_policy_proven"),
    ("CIG-13", "recovery_replay_fenced_until_restore_reconciliation"),
    ("CIG-14", "all_failure_stages_exercised_in_isolated_fault_harness"),
    ("CIG-15", "owner_and_independent_reviewer_receipts_current"),
    ("CIG-16", "zero_unresolved_duplicate_partial_or_unknown_outcome"),
]

ROLE_TYPES = [
    "COMMAND_CONTRACT_OWNER_ROLE",
    "TRANSACTION_AND_IDEMPOTENCY_REVIEWER_ROLE",
    "MESSAGING_CONVERGENCE_REVIEWER_ROLE",
    "BUSINESS_EFFECT_OWNER_ROLE",
    "INDEPENDENT_UAT_APPROVER_ROLE",
]

TYPED_OUTCOMES = [
    "COMMITTED_FIRST_ATTEMPT",
    "REPLAY_RETURNED_ORIGINAL_RECEIPT",
    "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT",
    "REJECTED_BEFORE_EFFECT",
    "ROLLED_BACK_NO_EFFECT",
    "COMMIT_UNKNOWN_RECONCILIATION_REQUIRED",
    "COMMITTED_OUTBOX_PUBLICATION_PENDING",
    "CONSUMER_DUPLICATE_NO_NEW_EFFECT",
    "CONSUMER_PROCESSING_RECOVERY_REQUIRED",
    "QUARANTINED_GAP_OVERLAP_OR_WATERMARK_CONFLICT",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_hash(values: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(values), separators=(",", ":")).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    modules = documents["blueprint"]["modules"]
    commands = []
    for module in modules:
        for command_name in module["commands"]:
            commands.append(
                {
                    "target_command_id": f"TCMD-{len(commands) + 1:03d}",
                    "module_id": module["id"],
                    "command_name": command_name,
                    "dependency_module_id_set_sha256": set_hash(module["depends_on"]),
                    "command_envelope_status": "DESIGNED_NOT_IMPLEMENTED",
                    "idempotency_receipt_status": "MISSING",
                    "outbox_inbox_status": "DESIGNED_NOT_IMPLEMENTED",
                    "fault_injection_status": "UNEXECUTED",
                    "runtime_convergence_status": "UNPROVEN",
                    "command_readiness": False,
                }
            )
    failure_assignments = [
        {"target_command_id": command["target_command_id"], "failure_stage_id": stage_id, "status": "UNEXECUTED", "accepted_receipt_count": 0}
        for command in commands
        for stage_id, _ in FAILURE_STAGES
    ]
    convergence_assignments = [
        {"target_command_id": command["target_command_id"], "convergence_dimension": dimension, "status": "UNPROVEN", "accepted_receipt_count": 0}
        for command in commands
        for dimension in CONVERGENCE_DIMENSIONS
    ]
    gate_assignments = [
        {"target_command_id": command["target_command_id"], "gate_id": gate_id, "status": "UNMET", "accepted_evidence_count": 0}
        for command in commands
        for gate_id, _ in COMMAND_GATES
    ]
    role_assignments = [
        {"target_command_id": command["target_command_id"], "role_type": role_type, "status": "UNASSIGNED", "role_receipt_reference": None}
        for command in commands
        for role_type in ROLE_TYPES
    ]
    official = documents["tests"]
    summary = {
        "module_count": len(modules),
        "target_command_count": len(commands),
        "command_envelope_field_count": len(COMMAND_ENVELOPE_FIELDS),
        "idempotency_receipt_field_count": len(IDEMPOTENCY_RECEIPT_FIELDS),
        "outbox_record_field_count": len(OUTBOX_RECORD_FIELDS),
        "inbox_record_field_count": len(INBOX_RECORD_FIELDS),
        "failure_stage_count": len(FAILURE_STAGES),
        "command_failure_stage_assignment_count": len(failure_assignments),
        "convergence_dimension_count": len(CONVERGENCE_DIMENSIONS),
        "command_convergence_assignment_count": len(convergence_assignments),
        "command_gate_count": len(COMMAND_GATES),
        "command_gate_assignment_count": len(gate_assignments),
        "role_type_count": len(ROLE_TYPES),
        "command_role_assignment_count": len(role_assignments),
        "typed_outcome_count": len(TYPED_OUTCOMES),
        "implemented_idempotency_contract_count": 0,
        "fault_injection_run_count": 0,
        "same_key_replay_proven_command_count": 0,
        "outbox_atomicity_proven_command_count": 0,
        "inbox_convergence_proven_command_count": 0,
        "unknown_outcome_reconciled_command_count": 0,
        "owner_approved_command_count": 0,
        "command_ready_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_convergence_contract": 1404,
        "design_lower_bound_after_convergence_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(documents[name].get("validation") == "PASS" for name in ("command_ledger", "cross_module", "restore_dependency", "restore_dependency_checkpoint", "tests")),
        "blueprint_14_modules_49_commands": (summary["module_count"], summary["target_command_count"]) == (14, 49),
        "schema_fields_22_20_16_14": (summary["command_envelope_field_count"], summary["idempotency_receipt_field_count"], summary["outbox_record_field_count"], summary["inbox_record_field_count"]) == (22, 20, 16, 14),
        "failure_stages_14_assignments_686": (summary["failure_stage_count"], summary["command_failure_stage_assignment_count"]) == (14, 686),
        "convergence_8_assignments_392": (summary["convergence_dimension_count"], summary["command_convergence_assignment_count"]) == (8, 392),
        "gates_16_assignments_784": (summary["command_gate_count"], summary["command_gate_assignment_count"]) == (16, 784),
        "roles_5_assignments_245_outcomes_10": (summary["role_type_count"], summary["command_role_assignment_count"], summary["typed_outcome_count"]) == (5, 245, 10),
        "all_failure_convergence_gate_role_states_open": all(item["status"] == "UNEXECUTED" for item in failure_assignments) and all(item["status"] == "UNPROVEN" for item in convergence_assignments) and all(item["status"] == "UNMET" for item in gate_assignments) and all(item["status"] == "UNASSIGNED" for item in role_assignments),
        "implementation_runtime_owner_readiness_zero": summary["implemented_idempotency_contract_count"] == summary["fault_injection_run_count"] == summary["same_key_replay_proven_command_count"] == summary["outbox_atomicity_proven_command_count"] == summary["inbox_convergence_proven_command_count"] == summary["unknown_outcome_reconciled_command_count"] == summary["owner_approved_command_count"] == summary["command_ready_count"] == summary["pilot_ready_module_count"] == 0,
        "non_additive_1404": summary["design_lower_bound_before_convergence_contract"] == summary["design_lower_bound_after_convergence_contract"] == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_command_idempotency_outbox_inbox_convergence_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "provider_neutral_target_command_reliability_design_only",
            "continuation_complete": False,
            "command_or_message_runtime_executed": False,
            "transport_database_queue_or_provider_selected": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "commands_messages_retries_replays_or_faults_executed": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "credentials_endpoints_pii_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "risk_links": ["R-006", "R-007", "R-022", "R-025", "R-004", "R-019", "R-023"],
        "command_envelope_fields": COMMAND_ENVELOPE_FIELDS,
        "idempotency_receipt_fields": IDEMPOTENCY_RECEIPT_FIELDS,
        "outbox_record_fields": OUTBOX_RECORD_FIELDS,
        "inbox_record_fields": INBOX_RECORD_FIELDS,
        "failure_stages": [{"failure_stage_id": stage_id, "failure_stage": stage} for stage_id, stage in FAILURE_STAGES],
        "convergence_dimensions": CONVERGENCE_DIMENSIONS,
        "command_gates": [{"gate_id": gate_id, "gate": gate, "failure_effect": "COMMAND_NOT_READY"} for gate_id, gate in COMMAND_GATES],
        "role_types": ROLE_TYPES,
        "typed_outcomes": TYPED_OUTCOMES,
        "target_commands": commands,
        "command_failure_stage_assignments": failure_assignments,
        "command_convergence_assignments": convergence_assignments,
        "command_gate_assignments": gate_assignments,
        "command_role_assignments": role_assignments,
        "idempotency_and_convergence_rule": {
            "same_key_same_fingerprint_returns_original_receipt": True,
            "same_key_different_fingerprint_is_conflict": True,
            "attempt_number_or_retry_may_change_idempotency_key": False,
            "business_effect_receipt_and_outbox_share_transaction_owner": True,
            "commit_unknown_allows_blind_retry": False,
            "consumer_duplicate_delivery_may_create_new_effect": False,
            "recovery_replay_allowed_before_restore_and_watermark_reconciliation": False,
            "raw_command_payload_or_business_values_may_be_persisted_in_evidence": False,
            "code_or_schema_existence_proves_runtime_convergence": False,
            "automatic_command_or_pilot_readiness": False,
        },
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [{"name": "builder", "path": "scripts/windows/build_varanegar_target_erp_command_idempotency_outbox_inbox_convergence_contract_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha256(Path(__file__))}],
        "limits": [
            "This maps 49 blueprint commands to design obligations; it does not assert implementation or runtime behavior.",
            "No database queue transport command retry replay fault injection or business value was accessed or executed.",
            "Readiness remains zero until isolated fault tests and owner-reviewed receipts prove convergence for each command.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
