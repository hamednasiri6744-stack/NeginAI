"""Build an unexecuted dependency-ordered restore and reconciliation contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "blueprint": "artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json",
    "restore_evidence": "artifacts/varanegar_analysis/varanegar_target_erp_backup_restore_rehearsal_evidence_contract_20260829.json",
    "restore_checkpoint": "artifacts/varanegar_analysis/varanegar_target_erp_backup_restore_rehearsal_evidence_checkpoint_20260829.json",
    "platform_readiness": "artifacts/varanegar_analysis/varanegar_platform_readiness_delta_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

RESTORE_STAGES = [
    ("RWS-01", "freeze_writes_and_pin_recovery_boundary"),
    ("RWS-02", "validate_backup_manifest_hash_completeness_and_versions"),
    ("RWS-03", "recover_configuration_policy_key_and_external_references"),
    ("RWS-04", "restore_authoritative_transactional_state"),
    ("RWS-05", "restore_object_and_file_evidence_state"),
    ("RWS-06", "restore_audit_outbox_inbox_and_idempotency_state_with_replay_fenced"),
    ("RWS-07", "rebuild_read_models_and_search_from_authoritative_state"),
    ("RWS-08", "reconcile_intra_module_and_dependency_edge_invariants"),
    ("RWS-09", "measure_rpo_rto_and_record_unresolved_differences"),
    ("RWS-10", "independent_review_before_controlled_service_enablement"),
]

RECONCILIATION_DIMENSIONS = [
    "AUTHORITATIVE_REFERENCE_AND_POINTER_SET_HASH",
    "AGGREGATE_COUNT_AND_CANONICAL_CONTENT_HASH",
    "OUTBOX_INBOX_IDEMPOTENCY_AND_WATERMARK_CONVERGENCE",
    "FINANCIAL_AND_OPERATIONAL_INVARIANT_OUTCOME",
]

WAVE_GATES = [
    ("RWG-01", "approved_recovery_policy_and_boundary_pinned"),
    ("RWG-02", "all_predecessor_waves_reconciled_not_merely_started"),
    ("RWG-03", "backup_manifest_complete_current_and_hash_valid"),
    ("RWG-04", "schema_application_configuration_and_policy_versions_compatible"),
    ("RWG-05", "key_secret_and_external_references_recoverable_without_material_persistence"),
    ("RWG-06", "authoritative_store_restore_receipts_accepted"),
    ("RWG-07", "object_file_and_evidence_store_receipts_accepted_or_not_applicable"),
    ("RWG-08", "audit_outbox_inbox_idempotency_restore_and_replay_fence_accepted"),
    ("RWG-09", "read_models_rebuilt_from_authoritative_state"),
    ("RWG-10", "all_dependency_edges_reconciled_with_zero_blocking_unknown"),
    ("RWG-11", "measured_rpo_and_rto_within_approved_targets"),
    ("RWG-12", "abort_cleanup_residue_scan_and_repeatability_accepted"),
    ("RWG-13", "operator_reviewer_and_business_owner_separation_accepted"),
    ("RWG-14", "controlled_enablement_receipt_approved_after_reconciliation"),
]

ROLE_TYPES = [
    "RECOVERY_ORCHESTRATOR_ROLE",
    "RESTORE_OPERATOR_ROLE",
    "MODULE_RECONCILIATION_OWNER_ROLE",
    "INDEPENDENT_RECOVERY_REVIEWER_ROLE",
    "SERVICE_ENABLEMENT_APPROVER_ROLE",
]

RECONCILIATION_RECEIPT_FIELDS = [
    "receipt_id",
    "recovery_policy_version_sha256",
    "rehearsal_id",
    "wave_id",
    "dependency_edge_id",
    "upstream_module_id",
    "downstream_module_id",
    "reconciliation_dimension",
    "fixture_or_boundary_reference_sha256",
    "upstream_result_sha256",
    "downstream_result_sha256",
    "difference_map_sha256",
    "blocking_unknown_count",
    "measured_at",
    "operator_role_receipt_reference",
    "business_owner_role_receipt_reference",
    "independent_reviewer_role_receipt_reference",
    "typed_outcome",
    "supersedes_receipt_sha256",
    "receipt_sha256",
]

TYPED_OUTCOMES = [
    "EDGE_RECONCILED_CURRENT",
    "UPSTREAM_NOT_RECONCILED",
    "DOWNSTREAM_RESTORE_BLOCKED",
    "REFERENCE_OR_POINTER_MISMATCH",
    "AGGREGATE_OR_CONTENT_HASH_MISMATCH",
    "REPLAY_OR_WATERMARK_NOT_CONVERGED",
    "FINANCIAL_OR_OPERATIONAL_INVARIANT_FAILED",
    "BLOCKING_UNKNOWN_PRESENT",
    "RECEIPT_STALE_REVOKED_OR_UNREVIEWED",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_hash(values: list[str]) -> str:
    payload = json.dumps(sorted(values), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def dependency_levels(modules: list[dict]) -> dict[str, int]:
    dependencies = {item["id"]: list(item["depends_on"]) for item in modules}
    if any(dependency not in dependencies for values in dependencies.values() for dependency in values):
        raise ValueError("unknown module dependency")
    levels: dict[str, int] = {}
    visiting: set[str] = set()

    def visit(module_id: str) -> int:
        if module_id in levels:
            return levels[module_id]
        if module_id in visiting:
            raise ValueError("module dependency cycle")
        visiting.add(module_id)
        levels[module_id] = 0 if not dependencies[module_id] else 1 + max(visit(x) for x in dependencies[module_id])
        visiting.remove(module_id)
        return levels[module_id]

    for module_id in sorted(dependencies):
        visit(module_id)
    return levels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    modules = documents["blueprint"]["modules"]
    levels = dependency_levels(modules)
    dependency_edges = []
    for downstream in sorted(modules, key=lambda item: item["id"]):
        for upstream_id in sorted(downstream["depends_on"]):
            dependency_edges.append(
                {
                    "dependency_edge_id": f"RDE-{len(dependency_edges) + 1:03d}",
                    "upstream_module_id": upstream_id,
                    "downstream_module_id": downstream["id"],
                    "upstream_wave_number": levels[upstream_id],
                    "downstream_wave_number": levels[downstream["id"]],
                    "status": "UNRECONCILED_NO_RESTORE_EVIDENCE",
                    "accepted_receipt_count": 0,
                }
            )
    wave_numbers = list(range(max(levels.values()) + 1))
    waves = [
        {
            "wave_id": f"RESTORE-WAVE-{wave_number:02d}",
            "wave_number": wave_number,
            "module_ids": sorted(module_id for module_id, level in levels.items() if level == wave_number),
            "module_id_set_sha256": set_hash([module_id for module_id, level in levels.items() if level == wave_number]),
            "status": "NOT_STARTED_NO_AUTHORIZED_REHEARSAL",
            "restore_run_count": 0,
            "reconciled_module_count": 0,
            "enablement_approved_count": 0,
        }
        for wave_number in wave_numbers
    ]
    module_plans = [
        {
            "module_id": module["id"],
            "restore_wave_number": levels[module["id"]],
            "dependency_module_ids": sorted(module["depends_on"]),
            "dependency_module_id_set_sha256": set_hash(module["depends_on"]),
            "owned_concept_set_sha256": set_hash(module["owns"]),
            "restore_status": "UNEXECUTED",
            "reconciliation_status": "UNRECONCILED_NO_RESTORE_EVIDENCE",
            "service_enablement_status": "BLOCKED",
        }
        for module in sorted(modules, key=lambda item: item["id"])
    ]
    stage_assignments = [
        {
            "module_id": module["id"],
            "stage_id": stage_id,
            "status": "UNEXECUTED",
            "accepted_evidence_count": 0,
        }
        for module in sorted(modules, key=lambda item: item["id"])
        for stage_id, _ in RESTORE_STAGES
    ]
    edge_reconciliation_assignments = [
        {
            "dependency_edge_id": edge["dependency_edge_id"],
            "reconciliation_dimension": dimension,
            "status": "MISSING",
            "accepted_receipt_count": 0,
        }
        for edge in dependency_edges
        for dimension in RECONCILIATION_DIMENSIONS
    ]
    wave_gate_assignments = [
        {
            "wave_id": wave["wave_id"],
            "gate_id": gate_id,
            "status": "UNMET",
            "accepted_evidence_count": 0,
        }
        for wave in waves
        for gate_id, _ in WAVE_GATES
    ]
    wave_role_assignments = [
        {
            "wave_id": wave["wave_id"],
            "role_type": role_type,
            "status": "UNASSIGNED",
            "role_receipt_reference": None,
        }
        for wave in waves
        for role_type in ROLE_TYPES
    ]
    official = documents["tests"]
    summary = {
        "module_count": len(module_plans),
        "module_dependency_edge_count": len(dependency_edges),
        "restore_wave_count": len(waves),
        "restore_stage_count": len(RESTORE_STAGES),
        "module_restore_stage_assignment_count": len(stage_assignments),
        "reconciliation_dimension_count": len(RECONCILIATION_DIMENSIONS),
        "edge_reconciliation_assignment_count": len(edge_reconciliation_assignments),
        "wave_gate_count": len(WAVE_GATES),
        "wave_gate_assignment_count": len(wave_gate_assignments),
        "role_type_count": len(ROLE_TYPES),
        "wave_role_assignment_count": len(wave_role_assignments),
        "reconciliation_receipt_field_count": len(RECONCILIATION_RECEIPT_FIELDS),
        "typed_outcome_count": len(TYPED_OUTCOMES),
        "authorized_restore_wave_count": 0,
        "restore_run_count": 0,
        "reconciled_dependency_edge_count": 0,
        "reconciled_module_count": 0,
        "owner_approved_wave_count": 0,
        "service_enabled_module_count": 0,
        "recovery_ready_module_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_dependency_contract": 1404,
        "design_lower_bound_after_dependency_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(documents[name].get("validation") == "PASS" for name in ("restore_evidence", "restore_checkpoint", "platform_readiness", "tests")),
        "module_dependency_dag_14_38_7": (summary["module_count"], summary["module_dependency_edge_count"], summary["restore_wave_count"]) == (14, 38, 7),
        "every_dependency_is_in_an_earlier_wave": all(edge["upstream_wave_number"] < edge["downstream_wave_number"] for edge in dependency_edges),
        "platform_is_only_wave_zero_module": waves[0]["module_ids"] == ["platform"],
        "stages_10_assignments_140": (summary["restore_stage_count"], summary["module_restore_stage_assignment_count"]) == (10, 140),
        "dimensions_4_assignments_152": (summary["reconciliation_dimension_count"], summary["edge_reconciliation_assignment_count"]) == (4, 152),
        "gates_14_assignments_98": (summary["wave_gate_count"], summary["wave_gate_assignment_count"]) == (14, 98),
        "roles_5_assignments_35_receipt_20_outcomes_9": (summary["role_type_count"], summary["wave_role_assignment_count"], summary["reconciliation_receipt_field_count"], summary["typed_outcome_count"]) == (5, 35, 20, 9),
        "all_stages_edges_gates_roles_unexecuted": all(item["status"] == "UNEXECUTED" for item in stage_assignments) and all(item["status"] == "UNRECONCILED_NO_RESTORE_EVIDENCE" for item in dependency_edges) and all(item["status"] == "UNMET" for item in wave_gate_assignments) and all(item["status"] == "UNASSIGNED" for item in wave_role_assignments),
        "execution_reconciliation_enablement_readiness_zero": summary["authorized_restore_wave_count"] == summary["restore_run_count"] == summary["reconciled_dependency_edge_count"] == summary["reconciled_module_count"] == summary["owner_approved_wave_count"] == summary["service_enabled_module_count"] == summary["recovery_ready_module_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "non_additive_1404": summary["design_lower_bound_before_dependency_contract"] == summary["design_lower_bound_after_dependency_contract"] == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_restore_dependency_wave_reconciliation_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "provider_neutral_static_dependency_order_and_reconciliation_design",
            "continuation_complete": False,
            "restore_rehearsal_authorized_or_executed": False,
            "rpo_rto_stack_storage_or_owner_selected": False,
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
        "risk_links": ["R-019", "R-006", "R-007", "R-022", "R-025", "R-004", "R-023"],
        "restore_stages": [{"stage_id": stage_id, "stage": stage} for stage_id, stage in RESTORE_STAGES],
        "reconciliation_dimensions": RECONCILIATION_DIMENSIONS,
        "wave_gates": [{"gate_id": gate_id, "gate": gate, "failure_effect": "WAVE_BLOCKED"} for gate_id, gate in WAVE_GATES],
        "role_types": ROLE_TYPES,
        "reconciliation_receipt_fields": RECONCILIATION_RECEIPT_FIELDS,
        "typed_outcomes": TYPED_OUTCOMES,
        "restore_waves": waves,
        "module_restore_plans": module_plans,
        "module_dependency_edges": dependency_edges,
        "module_restore_stage_assignments": stage_assignments,
        "edge_reconciliation_assignments": edge_reconciliation_assignments,
        "wave_gate_assignments": wave_gate_assignments,
        "wave_role_assignments": wave_role_assignments,
        "restore_order_rule": {
            "dependency_must_be_reconciled_before_dependent_restore": True,
            "service_start_or_schema_load_is_reconciliation": False,
            "read_model_is_authoritative_restore_source": False,
            "outbox_inbox_replay_allowed_before_idempotency_reconciliation": False,
            "blocking_unknown_or_unreviewed_difference_allows_enablement": False,
            "production_environment_restore_allowed": False,
            "parallel_restore_allowed_only_within_same_wave_and_no_dependency_edge": True,
            "automatic_wave_promotion_or_service_enablement": False,
        },
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [{"name": "builder", "path": "scripts/windows/build_varanegar_target_erp_restore_dependency_wave_reconciliation_contract_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha256(Path(__file__))}],
        "limits": [
            "This computes a restore dependency DAG from the approved design blueprint; it does not prove runtime dependencies or restorability.",
            "No backup restore replay reconciliation failover deployment service enablement or production action was authorized or executed.",
            "Every wave remains blocked until current hash-only receipts and independent approvals satisfy all gates.",
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
