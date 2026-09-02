"""Build a provider-neutral, unexecuted backup/restore rehearsal evidence contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "blueprint": "artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json",
    "platform_intake": "artifacts/varanegar_analysis/varanegar_platform_decision_evidence_intake_contract_20260829.json",
    "platform_outcome": "artifacts/varanegar_analysis/varanegar_platform_outcome_envelope_20260829.json",
    "platform_golden": "artifacts/varanegar_analysis/varanegar_platform_golden_uat_cases_20260829.json",
    "platform_readiness": "artifacts/varanegar_analysis/varanegar_platform_readiness_delta_20260829.json",
    "platform_readiness_checkpoint": "artifacts/varanegar_analysis/varanegar_platform_readiness_checkpoint_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

RECOVERY_ASSET_CLASSES = [
    "PRIMARY_TRANSACTIONAL_STORE",
    "OBJECT_OR_FILE_EVIDENCE_STORE",
    "CONFIGURATION_AND_POLICY_PACKAGE_STORE",
    "AUDIT_OUTBOX_INBOX_AND_IDEMPOTENCY_STORE",
    "READ_MODEL_SEARCH_INDEX_AND_REBUILD_INPUT",
    "KEY_SECRET_AND_EXTERNAL_SERVICE_REFERENCE_CONFIGURATION",
]

REHEARSAL_SCENARIOS = [
    ("BRS-01", "isolated_full_restore_from_declared_backup_set"),
    ("BRS-02", "point_in_time_restore_to_declared_recovery_boundary"),
    ("BRS-03", "corrupt_or_incomplete_backup_detected_before_use"),
    ("BRS-04", "missing_backup_segment_or_object_detected"),
    ("BRS-05", "schema_or_application_version_drift_blocks_unsafe_restore"),
    ("BRS-06", "key_or_secret_reference_unavailable_fails_closed"),
    ("BRS-07", "outbox_inbox_idempotency_and_replay_reconciliation"),
    ("BRS-08", "read_model_and_search_index_rebuild_from_authoritative_state"),
    ("BRS-09", "cross_module_pointer_ledger_and_projection_reconciliation"),
    ("BRS-10", "rpo_boundary_breach_detected_and_reported"),
    ("BRS-11", "rto_boundary_breach_detected_and_reported"),
    ("BRS-12", "restore_abort_cleanup_and_repeat_without_hidden_residue"),
]

RECOVERY_OBJECTIVE_FIELDS = [
    "module_id",
    "recovery_policy_version_sha256",
    "authoritative_asset_class_set_sha256",
    "dependency_module_id_set_sha256",
    "rpo_target_duration_seconds",
    "rto_target_duration_seconds",
    "maximum_data_loss_boundary_reference",
    "maximum_service_unavailability_boundary_reference",
    "backup_frequency_policy_reference",
    "retention_policy_reference",
    "encryption_and_key_reference_policy",
    "restore_environment_class",
    "reconciliation_contract_reference",
    "rehearsal_frequency_policy_reference",
    "recovery_owner_role_receipt_reference",
    "independent_reviewer_role_receipt_reference",
    "last_accepted_rehearsal_receipt_reference",
    "objective_status",
]

REHEARSAL_EVIDENCE_FIELDS = [
    "rehearsal_id",
    "module_id",
    "scenario_id",
    "isolated_environment_reference",
    "backup_set_reference",
    "backup_manifest_sha256",
    "source_snapshot_boundary_reference",
    "restore_start_at",
    "restore_end_at",
    "measured_rpo_seconds",
    "measured_rto_seconds",
    "restored_asset_class_set_sha256",
    "schema_and_application_version_sha256",
    "reconciliation_result_map_sha256",
    "unresolved_difference_count",
    "cleanup_attestation_sha256",
    "operator_role_receipt_reference",
    "independent_reviewer_role_receipt_reference",
    "typed_outcome",
    "rehearsal_receipt_sha256",
]

RECOVERY_GATES = [
    ("BRG-01", "stack_database_hosting_and_storage_decisions_accepted"),
    ("BRG-02", "module_authoritative_assets_and_dependencies_declared"),
    ("BRG-03", "rpo_and_rto_targets_owner_approved"),
    ("BRG-04", "backup_manifest_hash_and_completeness_validated"),
    ("BRG-05", "restore_environment_isolated_non_production_and_disposable"),
    ("BRG-06", "restore_operator_and_independent_reviewer_separated"),
    ("BRG-07", "schema_application_and_policy_versions_pinned"),
    ("BRG-08", "key_secret_and_external_reference_recovery_tested_without_material_persistence"),
    ("BRG-09", "outbox_inbox_idempotency_and_replay_reconciled"),
    ("BRG-10", "cross_module_financial_and_operational_invariants_reconciled"),
    ("BRG-11", "measured_rpo_and_rto_within_approved_targets"),
    ("BRG-12", "unresolved_difference_count_zero_or_separately_rejected"),
    ("BRG-13", "abort_cleanup_repeatability_and_residue_scan_accepted"),
    ("BRG-14", "owner_and_independent_review_receipts_current"),
]

RECOVERY_ROLE_TYPES = [
    "RECOVERY_POLICY_OWNER_ROLE",
    "BACKUP_OPERATOR_ROLE",
    "RESTORE_REHEARSAL_OPERATOR_ROLE",
    "INDEPENDENT_RECOVERY_REVIEWER_ROLE",
    "BUSINESS_RECONCILIATION_OWNER_ROLE",
]

TYPED_OUTCOMES = [
    "RESTORE_RECONCILED_WITHIN_RPO_RTO",
    "RESTORE_COMPLETED_RECONCILIATION_FAILED",
    "RPO_TARGET_BREACHED",
    "RTO_TARGET_BREACHED",
    "BACKUP_INVALID_OR_INCOMPLETE",
    "VERSION_OR_POLICY_MISMATCH",
    "DEPENDENCY_OR_KEY_REFERENCE_UNAVAILABLE",
    "ABORTED_CLEANUP_OR_REPEATABILITY_UNPROVEN",
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
    blueprint = documents["blueprint"]
    official = documents["tests"]
    module_contracts = []
    asset_obligations = []
    scenario_assignments = []
    gate_assignments = []
    role_assignments = []
    for module in blueprint["modules"]:
        module_id = module["id"]
        module_contracts.append(
            {
                "module_id": module_id,
                "dependency_module_id_set_sha256": set_hash(module["depends_on"]),
                "owned_concept_set_sha256": set_hash(module["owns"]),
                "recovery_objective_fields": RECOVERY_OBJECTIVE_FIELDS,
                "rpo_target_status": "UNAPPROVED",
                "rto_target_status": "UNAPPROVED",
                "recovery_owner_status": "UNASSIGNED",
                "last_accepted_rehearsal_receipt_reference": None,
                "recovery_readiness": "NOT_READY_NO_ACCEPTED_RESTORE_REHEARSAL",
            }
        )
        asset_obligations.extend(
            {
                "module_id": module_id,
                "asset_class": asset_class,
                "applicability_status": "OWNER_DECISION_REQUIRED",
                "backup_manifest_received_count": 0,
                "restored_and_reconciled_count": 0,
            }
            for asset_class in RECOVERY_ASSET_CLASSES
        )
        scenario_assignments.extend(
            {
                "module_id": module_id,
                "scenario_id": scenario_id,
                "status": "UNEXECUTED",
                "execution_count": 0,
                "accepted_receipt_count": 0,
            }
            for scenario_id, _ in REHEARSAL_SCENARIOS
        )
        gate_assignments.extend(
            {
                "module_id": module_id,
                "gate_id": gate_id,
                "status": "UNMET",
                "accepted_evidence_count": 0,
            }
            for gate_id, _ in RECOVERY_GATES
        )
        role_assignments.extend(
            {
                "module_id": module_id,
                "role_type": role,
                "status": "UNASSIGNED",
                "role_receipt_reference": None,
            }
            for role in RECOVERY_ROLE_TYPES
        )

    summary = {
        "module_count": len(module_contracts),
        "recovery_asset_class_count": len(RECOVERY_ASSET_CLASSES),
        "module_asset_obligation_count": len(asset_obligations),
        "rehearsal_scenario_count": len(REHEARSAL_SCENARIOS),
        "module_scenario_assignment_count": len(scenario_assignments),
        "recovery_objective_field_count": len(RECOVERY_OBJECTIVE_FIELDS),
        "rehearsal_evidence_field_count": len(REHEARSAL_EVIDENCE_FIELDS),
        "recovery_gate_count": len(RECOVERY_GATES),
        "module_gate_assignment_count": len(gate_assignments),
        "recovery_role_type_count": len(RECOVERY_ROLE_TYPES),
        "module_role_assignment_count": len(role_assignments),
        "typed_outcome_count": len(TYPED_OUTCOMES),
        "approved_rpo_target_count": 0,
        "approved_rto_target_count": 0,
        "backup_set_created_or_read_count": 0,
        "restore_rehearsal_run_count": 0,
        "passed_restore_rehearsal_count": 0,
        "reconciled_restore_count": 0,
        "owner_approved_module_count": 0,
        "recovery_ready_module_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_restore_contract": 1404,
        "design_lower_bound_after_restore_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(
            documents[name].get("validation") == "PASS"
            for name in ("platform_intake", "platform_outcome", "platform_golden", "platform_readiness", "platform_readiness_checkpoint", "tests")
        ),
        "blueprint_14_modules": blueprint["module_count"] == summary["module_count"] == 14,
        "assets_6_obligations_84": summary["recovery_asset_class_count"] == 6
        and summary["module_asset_obligation_count"] == 84,
        "scenarios_12_assignments_168": summary["rehearsal_scenario_count"] == 12
        and summary["module_scenario_assignment_count"] == 168,
        "fields_18_20": (summary["recovery_objective_field_count"], summary["rehearsal_evidence_field_count"])
        == (18, 20),
        "gates_14_assignments_196": summary["recovery_gate_count"] == 14
        and summary["module_gate_assignment_count"] == 196,
        "roles_5_assignments_70_outcomes_8": (
            summary["recovery_role_type_count"],
            summary["module_role_assignment_count"],
            summary["typed_outcome_count"],
        )
        == (5, 70, 8),
        "all_targets_unapproved_scenarios_unexecuted": all(
            item["rpo_target_status"] == item["rto_target_status"] == "UNAPPROVED"
            for item in module_contracts
        )
        and all(item["status"] == "UNEXECUTED" for item in scenario_assignments),
        "backup_restore_recovery_readiness_zero": summary["approved_rpo_target_count"]
        == summary["approved_rto_target_count"]
        == summary["backup_set_created_or_read_count"]
        == summary["restore_rehearsal_run_count"]
        == summary["passed_restore_rehearsal_count"]
        == summary["reconciled_restore_count"]
        == summary["owner_approved_module_count"]
        == summary["recovery_ready_module_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_restore_contract"]
        == summary["design_lower_bound_after_restore_contract"]
        == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_backup_restore_rehearsal_evidence_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "provider_neutral_design_only_restore_rehearsal_evidence",
            "continuation_complete": False,
            "stack_database_hosting_or_recovery_targets_selected": False,
            "backup_restore_or_drill_authorized": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "backup_sets_created_read_or_restored": 0,
            "deployments_jobs_failovers_or_drills_executed": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "credentials_endpoints_pii_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "risk_links": ["R-019", "R-004", "R-006", "R-007", "R-022", "R-023", "R-025"],
        "recovery_asset_classes": RECOVERY_ASSET_CLASSES,
        "rehearsal_scenarios": [
            {"scenario_id": scenario_id, "scenario": scenario}
            for scenario_id, scenario in REHEARSAL_SCENARIOS
        ],
        "recovery_objective_fields": RECOVERY_OBJECTIVE_FIELDS,
        "rehearsal_evidence_fields": REHEARSAL_EVIDENCE_FIELDS,
        "recovery_gates": [
            {"gate_id": gate_id, "gate": gate, "failure_effect": "RECOVERY_NOT_READY"}
            for gate_id, gate in RECOVERY_GATES
        ],
        "recovery_role_types": RECOVERY_ROLE_TYPES,
        "typed_outcomes": TYPED_OUTCOMES,
        "module_recovery_contracts": module_contracts,
        "module_asset_obligations": asset_obligations,
        "module_scenario_assignments": scenario_assignments,
        "module_gate_assignments": gate_assignments,
        "module_role_assignments": role_assignments,
        "rehearsal_rule": {
            "production_restore_allowed": False,
            "service_started_is_restore_success": False,
            "schema_load_is_restore_success": False,
            "cross_module_reconciliation_required": True,
            "rpo_rto_measured_not_assumed": True,
            "unresolved_difference_blocks_acceptance": True,
            "backup_presence_proves_restorability": False,
            "restore_rehearsal_must_be_isolated_disposable_and_repeatable": True,
        },
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {
                "name": name,
                "path": SOURCES[name],
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_target_erp_backup_restore_rehearsal_evidence_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This is a provider-neutral evidence contract and does not select a stack database host storage key provider RPO RTO or owner.",
            "No backup set endpoint credential key business data deployment restore failover or drill was accessed or executed.",
            "Recovery readiness remains zero until an isolated restore is measured reconciled independently reviewed and owner accepted.",
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

