"""Build a design-only transaction-owner, saga, and compensation contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "blueprint": "artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json",
    "cross_module": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_contract_20260829.json",
    "command_convergence": "artifacts/varanegar_analysis/varanegar_target_erp_command_idempotency_outbox_inbox_convergence_contract_20260829.json",
    "command_convergence_checkpoint": "artifacts/varanegar_analysis/varanegar_target_erp_command_idempotency_outbox_inbox_convergence_checkpoint_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

TRANSACTION_PATTERNS = [
    "LOCAL_ATOMIC_SINGLE_MODULE",
    "LOCAL_ATOMIC_WITH_TRANSACTIONAL_OUTBOX",
    "DURABLE_SAGA_WITH_IDEMPOTENT_COMPENSATION",
    "MANUAL_QUARANTINED_RECOVERY_FOR_NONCOMPENSABLE_EFFECT",
]

TRANSACTION_BOUNDARY_FIELDS = [
    "target_command_id",
    "transaction_contract_version_sha256",
    "selected_pattern",
    "transaction_owner_module_id",
    "connection_or_unit_of_work_scope_reference_sha256",
    "aggregate_owner_set_sha256",
    "mutation_set_sha256",
    "precondition_set_sha256",
    "invariant_set_sha256",
    "outbox_event_set_sha256",
    "non_transactional_effect_set_sha256",
    "commit_point_reference_sha256",
    "rollback_policy_reference_sha256",
    "commit_unknown_reconciliation_reference_sha256",
    "timeout_and_cancellation_policy_sha256",
    "owner_role_receipt_reference",
    "independent_review_receipt_reference",
    "boundary_sha256",
]

SAGA_STEP_RECEIPT_FIELDS = [
    "saga_id",
    "target_command_id",
    "step_id",
    "step_contract_version_sha256",
    "causation_receipt_sha256",
    "idempotency_key_sha256",
    "participant_module_id",
    "expected_aggregate_version_set_sha256",
    "effect_set_sha256",
    "outbox_event_set_sha256",
    "step_started_at",
    "step_completed_at",
    "typed_outcome",
    "commit_state",
    "compensation_required",
    "compensation_receipt_sha256",
    "unresolved_invariant_count",
    "operator_role_receipt_reference",
    "reviewer_role_receipt_reference",
    "step_receipt_sha256",
]

COMPENSATION_RECEIPT_FIELDS = [
    "compensation_id",
    "saga_id",
    "forward_step_receipt_sha256",
    "compensation_contract_version_sha256",
    "idempotency_key_sha256",
    "participant_module_id",
    "precondition_set_sha256",
    "compensating_effect_set_sha256",
    "non_reversible_effect_set_sha256",
    "attempt_number",
    "started_at",
    "completed_at",
    "typed_outcome",
    "residual_difference_set_sha256",
    "blocking_unknown_count",
    "business_owner_receipt_reference",
    "independent_review_receipt_reference",
    "receipt_sha256",
]

FAILURE_STAGES = [
    ("TFS-01", "before_local_transaction_begin"),
    ("TFS-02", "after_begin_before_first_mutation"),
    ("TFS-03", "between_local_mutations"),
    ("TFS-04", "after_local_mutations_before_outbox"),
    ("TFS-05", "after_outbox_before_local_commit"),
    ("TFS-06", "local_commit_unknown"),
    ("TFS-07", "after_local_commit_before_saga_step_receipt"),
    ("TFS-08", "between_saga_participants"),
    ("TFS-09", "participant_succeeded_parent_orchestrator_failed"),
    ("TFS-10", "compensation_started_then_interrupted"),
    ("TFS-11", "compensation_completed_response_lost_and_retried"),
    ("TFS-12", "noncompensable_effect_failed_or_outcome_unknown"),
]

GATES = [
    ("TSG-01", "one_named_transaction_owner_per_local_mutation_set"),
    ("TSG-02", "aggregate_and_table_write_ownership_declared"),
    ("TSG-03", "no_cross_module_direct_table_writer"),
    ("TSG-04", "transaction_pattern_selected_and_versioned"),
    ("TSG-05", "local_invariants_checked_before_commit"),
    ("TSG-06", "outbox_insert_shares_local_transaction_owner"),
    ("TSG-07", "nontransactional_effect_occurs_only_after_durable_commit_receipt"),
    ("TSG-08", "commit_unknown_reconciled_before_retry_or_compensation"),
    ("TSG-09", "parent_success_requires_all_mandatory_participant_receipts"),
    ("TSG-10", "compensation_is_idempotent_versioned_and_audited"),
    ("TSG-11", "noncompensable_effect_has_manual_quarantine_and_owner"),
    ("TSG-12", "finite_deadline_cancellation_and_fencing_proven"),
    ("TSG-13", "all_failure_stages_exercised_in_isolated_fault_harness"),
    ("TSG-14", "retry_cannot_duplicate_forward_or_compensating_effect"),
    ("TSG-15", "zero_residual_blocking_unknown_or_partial_invariant"),
    ("TSG-16", "business_owner_and_independent_review_receipts_current"),
]

ROLE_TYPES = [
    "TRANSACTION_CONTRACT_OWNER_ROLE",
    "MODULE_AGGREGATE_OWNER_ROLE",
    "SAGA_ORCHESTRATOR_OWNER_ROLE",
    "COMPENSATION_POLICY_OWNER_ROLE",
    "BUSINESS_INVARIANT_OWNER_ROLE",
    "INDEPENDENT_TRANSACTION_REVIEWER_ROLE",
]

TYPED_OUTCOMES = [
    "LOCAL_COMMIT_COMPLETE",
    "LOCAL_ROLLBACK_COMPLETE_NO_EFFECT",
    "LOCAL_COMMIT_UNKNOWN_RECONCILIATION_REQUIRED",
    "SAGA_COMPLETED_ALL_INVARIANTS_RECONCILED",
    "SAGA_FORWARD_PROGRESS_PENDING",
    "SAGA_COMPENSATION_REQUIRED",
    "COMPENSATION_COMPLETED_RESIDUAL_ZERO",
    "COMPENSATION_FAILED_OR_OUTCOME_UNKNOWN",
    "NONCOMPENSABLE_EFFECT_QUARANTINED",
    "BLOCKING_PARTIAL_INVARIANT_UNRESOLVED",
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
    coordination_assignments = []
    for module in modules:
        for command_name in module["commands"]:
            command_id = f"TCMD-{len(commands) + 1:03d}"
            commands.append(
                {
                    "target_command_id": command_id,
                    "module_id": module["id"],
                    "command_name": command_name,
                    "dependency_module_ids": sorted(module["depends_on"]),
                    "dependency_module_id_set_sha256": set_hash(module["depends_on"]),
                    "selected_transaction_pattern": None,
                    "transaction_owner_status": "UNASSIGNED",
                    "saga_or_compensation_status": "OWNER_DECISION_REQUIRED",
                    "fault_injection_status": "UNEXECUTED",
                    "runtime_atomicity_status": "UNPROVEN",
                    "command_readiness": False,
                }
            )
            coordination_assignments.extend(
                {
                    "target_command_id": command_id,
                    "participant_module_id": dependency,
                    "coordination_pattern_status": "UNSELECTED_OWNER_DECISION_REQUIRED",
                    "accepted_participant_receipt_count": 0,
                }
                for dependency in sorted(module["depends_on"])
            )
    pattern_assignments = [
        {"target_command_id": command["target_command_id"], "transaction_pattern": pattern, "selection_status": "CANDIDATE_NOT_SELECTED"}
        for command in commands
        for pattern in TRANSACTION_PATTERNS
    ]
    failure_assignments = [
        {"target_command_id": command["target_command_id"], "failure_stage_id": stage_id, "status": "UNEXECUTED", "accepted_receipt_count": 0}
        for command in commands
        for stage_id, _ in FAILURE_STAGES
    ]
    gate_assignments = [
        {"target_command_id": command["target_command_id"], "gate_id": gate_id, "status": "UNMET", "accepted_evidence_count": 0}
        for command in commands
        for gate_id, _ in GATES
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
        "module_dependency_edge_count": sum(len(module["depends_on"]) for module in modules),
        "command_dependency_coordination_assignment_count": len(coordination_assignments),
        "transaction_pattern_count": len(TRANSACTION_PATTERNS),
        "command_pattern_candidate_assignment_count": len(pattern_assignments),
        "transaction_boundary_field_count": len(TRANSACTION_BOUNDARY_FIELDS),
        "saga_step_receipt_field_count": len(SAGA_STEP_RECEIPT_FIELDS),
        "compensation_receipt_field_count": len(COMPENSATION_RECEIPT_FIELDS),
        "failure_stage_count": len(FAILURE_STAGES),
        "command_failure_stage_assignment_count": len(failure_assignments),
        "gate_count": len(GATES),
        "command_gate_assignment_count": len(gate_assignments),
        "role_type_count": len(ROLE_TYPES),
        "command_role_assignment_count": len(role_assignments),
        "typed_outcome_count": len(TYPED_OUTCOMES),
        "selected_transaction_pattern_count": 0,
        "named_transaction_owner_count": 0,
        "fault_injection_run_count": 0,
        "runtime_atomicity_proven_command_count": 0,
        "saga_completed_command_count": 0,
        "compensation_executed_or_accepted_count": 0,
        "owner_approved_command_count": 0,
        "command_ready_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_transaction_contract": 1404,
        "design_lower_bound_after_transaction_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(documents[name].get("validation") == "PASS" for name in ("cross_module", "command_convergence", "command_convergence_checkpoint", "tests")),
        "blueprint_14_modules_49_commands_38_edges": (summary["module_count"], summary["target_command_count"], summary["module_dependency_edge_count"]) == (14, 49, 38),
        "coordination_assignments_159": summary["command_dependency_coordination_assignment_count"] == 159,
        "patterns_4_assignments_196": (summary["transaction_pattern_count"], summary["command_pattern_candidate_assignment_count"]) == (4, 196),
        "schema_fields_18_20_18": (summary["transaction_boundary_field_count"], summary["saga_step_receipt_field_count"], summary["compensation_receipt_field_count"]) == (18, 20, 18),
        "failure_12_assignments_588": (summary["failure_stage_count"], summary["command_failure_stage_assignment_count"]) == (12, 588),
        "gates_16_assignments_784": (summary["gate_count"], summary["command_gate_assignment_count"]) == (16, 784),
        "roles_6_assignments_294_outcomes_10": (summary["role_type_count"], summary["command_role_assignment_count"], summary["typed_outcome_count"]) == (6, 294, 10),
        "all_candidates_owners_failures_gates_roles_open": all(item["selection_status"] == "CANDIDATE_NOT_SELECTED" for item in pattern_assignments) and all(item["transaction_owner_status"] == "UNASSIGNED" for item in commands) and all(item["status"] == "UNEXECUTED" for item in failure_assignments) and all(item["status"] == "UNMET" for item in gate_assignments) and all(item["status"] == "UNASSIGNED" for item in role_assignments),
        "selection_runtime_compensation_readiness_zero": summary["selected_transaction_pattern_count"] == summary["named_transaction_owner_count"] == summary["fault_injection_run_count"] == summary["runtime_atomicity_proven_command_count"] == summary["saga_completed_command_count"] == summary["compensation_executed_or_accepted_count"] == summary["owner_approved_command_count"] == summary["command_ready_count"] == summary["pilot_ready_module_count"] == 0,
        "non_additive_1404": summary["design_lower_bound_before_transaction_contract"] == summary["design_lower_bound_after_transaction_contract"] == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_transaction_owner_saga_compensation_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "provider_neutral_transaction_owner_and_saga_design_only", "continuation_complete": False, "transaction_saga_or_compensation_executed": False, "stack_or_transport_selected": False},
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "commands_transactions_sagas_compensations_or_faults_executed": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "credentials_endpoints_pii_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "risk_links": ["R-007", "R-006", "R-022", "R-025", "R-004"],
        "transaction_patterns": TRANSACTION_PATTERNS,
        "transaction_boundary_fields": TRANSACTION_BOUNDARY_FIELDS,
        "saga_step_receipt_fields": SAGA_STEP_RECEIPT_FIELDS,
        "compensation_receipt_fields": COMPENSATION_RECEIPT_FIELDS,
        "failure_stages": [{"failure_stage_id": stage_id, "failure_stage": stage} for stage_id, stage in FAILURE_STAGES],
        "gates": [{"gate_id": gate_id, "gate": gate, "failure_effect": "COMMAND_AND_SAGA_NOT_READY"} for gate_id, gate in GATES],
        "role_types": ROLE_TYPES,
        "typed_outcomes": TYPED_OUTCOMES,
        "target_command_transaction_contracts": commands,
        "command_dependency_coordination_assignments": coordination_assignments,
        "command_pattern_candidate_assignments": pattern_assignments,
        "command_failure_stage_assignments": failure_assignments,
        "command_gate_assignments": gate_assignments,
        "command_role_assignments": role_assignments,
        "transaction_and_saga_rule": {
            "distributed_transaction_is_default": False,
            "cross_module_direct_table_write_allowed": False,
            "child_or_participant_success_is_parent_success": False,
            "external_effect_allowed_before_durable_local_commit_receipt": False,
            "commit_unknown_allows_retry_or_compensation_without_reconciliation": False,
            "compensation_is_database_rollback": False,
            "compensation_must_be_idempotent_versioned_and_audited": True,
            "noncompensable_unknown_effect_requires_manual_quarantine": True,
            "residual_blocking_unknown_allows_success_or_readiness": False,
            "automatic_pattern_selection_or_readiness": False,
        },
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)} for name, path in sorted(paths.items())] + [{"name": "builder", "path": "scripts/windows/build_varanegar_target_erp_transaction_owner_saga_compensation_contract_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha256(Path(__file__))}],
        "limits": [
            "All four transaction patterns remain candidates; this artifact does not select an implementation pattern for any command.",
            "No database transaction command message saga compensation fault injection or business value was accessed or executed.",
            "Runtime atomicity and readiness remain zero until isolated failure evidence is accepted for each command and participant.",
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
