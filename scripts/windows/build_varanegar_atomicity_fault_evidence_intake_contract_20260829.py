"""Build the CG-02 rollback and partial-failure atomicity evidence intake contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "priority": "artifacts/varanegar_analysis/varanegar_external_evidence_gate_priority_map_20260829.json",
    "readiness": "artifacts/varanegar_analysis/varanegar_platform_readiness_delta_20260829.json",
    "boundary": "artifacts/varanegar_analysis/varanegar_identity_integration_transaction_mutation_boundary_20260829.json",
    "consolidated": "artifacts/varanegar_analysis/varanegar_24h_continuation_consolidated_audit_20260829.json",
    "platform_intake": "artifacts/varanegar_analysis/varanegar_platform_decision_evidence_intake_contract_20260829.json",
    "authorization_intake": "artifacts/varanegar_analysis/varanegar_authorization_runtime_evidence_intake_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_authorization_runtime_evidence_intake_checkpoint_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    cg02 = next(row for row in data["priority"]["priority_map"] if row["gate_id"] == "CG-02")

    fault_categories = [
        {"id": "AT-01", "injection_boundary": "validation_or_authorization_before_transaction", "required_outcome": "REJECTED_WITH_ZERO_EFFECT"},
        {"id": "AT-02", "injection_boundary": "after_first_mutation_before_dependent_mutation", "required_outcome": "ROLLBACK_TO_BEFORE_DIGEST"},
        {"id": "AT-03", "injection_boundary": "after_business_mutation_before_audit_or_outbox", "required_outcome": "ATOMIC_ROLLBACK_OR_COMPLETE_COMMIT"},
        {"id": "AT-04", "injection_boundary": "after_commit_before_client_acknowledgement", "required_outcome": "UNKNOWN_OUTCOME_THEN_IMMUTABLE_READBACK"},
        {"id": "AT-05", "injection_boundary": "external_effect_before_local_commit", "required_outcome": "QUARANTINE_OR_COMPENSATION_REQUIRED"},
        {"id": "AT-06", "injection_boundary": "local_commit_before_external_effect", "required_outcome": "PENDING_OUTBOX_RETRY_WITHOUT_DUPLICATE"},
        {"id": "AT-07", "injection_boundary": "rollback_operation_itself_fails", "required_outcome": "UNKNOWN_OUTCOME_STOP_AND_ESCALATE"},
        {"id": "AT-08", "injection_boundary": "concurrent_same_idempotency_key", "required_outcome": "ONE_DURABLE_OUTCOME"},
        {"id": "AT-09", "injection_boundary": "stale_expected_version", "required_outcome": "CONFLICT_WITH_ZERO_NEW_MUTATION"},
        {"id": "AT-10", "injection_boundary": "retry_after_partial_or_unknown_outcome", "required_outcome": "CONVERGE_TO_ONE_APPROVED_STATE"},
    ]
    required_packet_fields = [
        "module",
        "command_contract_manifest_hash",
        "transaction_owner_reference_hash",
        "declared_mutation_set_reference_hash",
        "fault_injection_plan_hash",
        "injection_point_reference_hash",
        "before_state_digest",
        "after_state_digest",
        "command_outcome_receipt_hash",
        "commit_or_rollback_receipt_hash",
        "unknown_outcome_readback_receipt_hash",
        "idempotency_retry_receipt_hash",
        "quarantine_or_compensation_receipt_hash",
        "external_effect_reference_hash",
        "difference_manifest_hash",
        "technical_owner_approval_reference_hash",
        "business_owner_approval_reference_hash",
    ]
    modules = []
    target_only_modules = {"identity_authorization", "integration_migration"}
    for row in data["readiness"]["modules"]:
        transaction = row["truth_table_dimensions"]["transaction_owner"]
        if transaction["design_or_static_evidence"]:
            evidence_class = "LEGACY_STATIC_OR_TARGET_DESIGN_PRESENT"
        elif row["module"] in target_only_modules:
            evidence_class = "TARGET_DESIGN_PRESENT_LEGACY_STATIC_INCOMPLETE"
        else:
            evidence_class = "MISSING_DESIGN"
        modules.append(
            {
                "module": row["module"],
                "transaction_evidence_class": evidence_class,
                "runtime_atomicity_proven": transaction["runtime_atomicity_proven"],
                "required_fault_category_ids": [item["id"] for item in fault_categories],
                "required_packet_field_count": len(required_packet_fields),
                "current_packet_status": "WAITING_FOR_APPROVED_CG06_AND_FAULT_INJECTION_HARNESS",
                "accepted_packet_count": 0,
                "owner_approved_count": 0,
                "command_ready": False,
                "pilot_ready": False,
            }
        )
    summary = {
        "cg02_priority_rank": cg02["priority_rank"],
        "module_count": len(modules),
        "legacy_static_or_design_present_module_count": sum(
            row["transaction_evidence_class"] == "LEGACY_STATIC_OR_TARGET_DESIGN_PRESENT" for row in modules
        ),
        "target_design_only_legacy_static_incomplete_module_count": sum(
            row["transaction_evidence_class"] == "TARGET_DESIGN_PRESENT_LEGACY_STATIC_INCOMPLETE" for row in modules
        ),
        "runtime_atomicity_proven_module_count": sum(row["runtime_atomicity_proven"] for row in modules),
        "fault_category_count": len(fault_categories),
        "required_packet_field_count": len(required_packet_fields),
        "accepted_module_packet_count": sum(row["accepted_packet_count"] for row in modules),
        "owner_approved_module_count": sum(row["owner_approved_count"] for row in modules),
        "cg06_required_current_decision_slot_count": data["platform_intake"]["cg06_closure_rule"]["required_current_slot_count"],
        "cg06_current_accepted_decision_slot_count": data["platform_intake"]["cg06_closure_rule"]["current_accepted_slot_count"],
        "cg01_runtime_authorization_proven_module_count": data["authorization_intake"]["summary"]["runtime_authorization_proven_module_count"],
        "identity_integration_target_transaction_design_command_count": data["boundary"]["summary"]["command_with_target_transaction_design_count"],
        "identity_integration_complete_legacy_static_proof_count": data["boundary"]["summary"]["command_with_complete_legacy_static_proof_count"],
        "synthetic_acceptance_design_obligation_count": data["consolidated"]["summary"]["synthetic_acceptance_design_obligation_count"],
        "cg02_closed_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "cg02_is_parallel_runtime_foundation": cg02["priority_rank"] == 4
        and cg02["lane"] == "ISOLATED_RUNTIME_FOUNDATION"
        and cg02["parallel_with_gate_ids"] == ["CG-01"],
        "fourteen_unique_modules": len(modules) == len({row["module"] for row in modules}) == 14,
        "evidence_boundary_12_plus_2": summary["legacy_static_or_design_present_module_count"] == 12
        and summary["target_design_only_legacy_static_incomplete_module_count"] == 2,
        "ten_fault_categories": summary["fault_category_count"] == 10
        and len({item["id"] for item in fault_categories}) == 10,
        "packet_schema_17": summary["required_packet_field_count"] == 17,
        "rollback_unknown_external_retry_covered": {item["required_outcome"] for item in fault_categories}
        >= {
            "ROLLBACK_TO_BEFORE_DIGEST",
            "UNKNOWN_OUTCOME_STOP_AND_ESCALATE",
            "PENDING_OUTBOX_RETRY_WITHOUT_DUPLICATE",
            "CONVERGE_TO_ONE_APPROVED_STATE",
        },
        "cg06_open_and_cg01_parallel_unproven": summary["cg06_required_current_decision_slot_count"] == 8
        and summary["cg06_current_accepted_decision_slot_count"] == 0
        and summary["cg01_runtime_authorization_proven_module_count"] == 0,
        "target_only_boundary_honest": summary["identity_integration_target_transaction_design_command_count"] == 12
        and summary["identity_integration_complete_legacy_static_proof_count"] == 0,
        "runtime_acceptance_readiness_zero": summary["runtime_atomicity_proven_module_count"]
        == summary["accepted_module_packet_count"]
        == summary["owner_approved_module_count"]
        == summary["cg02_closed_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_atomicity_fault_evidence_intake_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_FAULT_INJECTION_ATOMICITY_EVIDENCE_INTAKE_DESIGN",
            "gate_id": "CG-02",
            "runtime_execution_requires_cg06_accepted": True,
            "may_execute_in_parallel_with_cg01_after_cg06": True,
            "gate_closed": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "fault_injections_transactions_rollbacks_or_retries_executed": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "credentials_pii_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "fault_categories": fault_categories,
        "packet_schema": {
            "required_fields": required_packet_fields,
            "prohibited_fields": [
                "production_connection_or_endpoint",
                "raw_business_row_or_value",
                "credential_or_identity",
                "unbounded_fault_target",
                "repair_or_replay_command",
            ],
            "acceptance_rule": "Every category runs only in the approved isolated environment and converges to one approved committed, rolled-back or explicitly unknown/quarantined state with immutable before/after/readback receipts and zero unexplained partial effect.",
        },
        "module_intake_map": modules,
        "global_validation_rules": [
            "A caught exception, Boolean return or rollback call does not prove rollback success.",
            "Commit without client acknowledgement is UNKNOWN_OUTCOME until immutable readback.",
            "Database and external systems do not share atomic commit unless independently proven.",
            "Retry after unknown outcome must reconcile before any new mutation or external effect.",
            "Rollback failure stops automation and escalates; it is never silently normalized.",
            "Identity and Integration target design does not become complete legacy/static proof.",
        ],
        "cg02_closure_rule": {
            "required_accepted_module_packet_count": 14,
            "current_accepted_module_packet_count": 0,
            "required_fault_category_count_per_module": 10,
            "status": "OPEN_EXTERNAL_RUNTIME_GATE",
            "rule": "CG-02 closes only after CG-06 acceptance and fourteen owner-approved module packets covering all ten categories with zero unexplained partial effect; CG-01 may run in parallel but is not inferred.",
        },
        "checks": checks,
        "failed_checks": failed,
        "risk_links": ["R-001", "R-005", "R-006", "R-007", "R-008", "R-011", "R-013", "R-023", "R-027", "R-031", "R-034", "R-043", "R-056", "R-059"],
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_atomicity_fault_evidence_intake_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This is a fault-injection design, not an executed rollback or atomicity result.",
            "No production or clone database is connected and no fault target is activated.",
            "CG-02, runtime atomicity, command readiness and pilot readiness remain zero.",
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
