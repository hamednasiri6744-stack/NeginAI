"""Build the CG-03 mutation, result and external-effect parity evidence intake contract."""
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
    "atomicity_intake": "artifacts/varanegar_analysis/varanegar_atomicity_fault_evidence_intake_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_atomicity_fault_evidence_intake_checkpoint_20260829.json",
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
    cg03 = next(row for row in data["priority"]["priority_map"] if row["gate_id"] == "CG-03")

    parity_categories = [
        {"id": "EP-01", "effect_layer": "declared_primary_database_mutation_set", "required_evidence": "BEFORE_AFTER_MUTATION_DIGEST"},
        {"id": "EP-02", "effect_layer": "audit_and_decision_history", "required_evidence": "IMMUTABLE_AUDIT_RECEIPT"},
        {"id": "EP-03", "effect_layer": "outbox_message_or_job_intent", "required_evidence": "DURABLE_OUTBOX_OR_JOB_RECEIPT"},
        {"id": "EP-04", "effect_layer": "external_system_or_file_transport", "required_evidence": "EXTERNAL_EFFECT_OR_QUARANTINE_RECEIPT"},
        {"id": "EP-05", "effect_layer": "typed_command_result_and_outcome", "required_evidence": "RESULT_CONTRACT_RECEIPT"},
        {"id": "EP-06", "effect_layer": "immutable_readback_and_current_state", "required_evidence": "READBACK_RECONCILIATION_DIGEST"},
        {"id": "EP-07", "effect_layer": "duplicate_and_retry", "required_evidence": "ONE_DURABLE_EFFECT_RECEIPT"},
        {"id": "EP-08", "effect_layer": "compensation_reversal_or_rollback_command", "required_evidence": "APPEND_ONLY_COMPENSATION_RECEIPT"},
        {"id": "EP-09", "effect_layer": "crosswalk_identity_and_provenance", "required_evidence": "VERSIONED_CROSSWALK_PROVENANCE_DIGEST"},
        {"id": "EP-10", "effect_layer": "reconciliation_difference_and_quarantine", "required_evidence": "ZERO_UNEXPLAINED_DIFFERENCE_OR_QUARANTINE"},
    ]
    required_packet_fields = [
        "module",
        "command_contract_manifest_hash",
        "declared_mutation_set_reference_hash",
        "declared_result_contract_reference_hash",
        "declared_external_effect_reference_hash",
        "synthetic_fixture_manifest_hash",
        "before_state_digest",
        "database_after_state_digest",
        "typed_result_receipt_hash",
        "audit_receipt_hash",
        "outbox_or_job_receipt_hash",
        "external_effect_or_quarantine_receipt_hash",
        "immutable_readback_digest",
        "duplicate_retry_receipt_hash",
        "compensation_or_reversal_receipt_hash",
        "crosswalk_provenance_digest",
        "reconciliation_difference_manifest_hash",
        "technical_owner_approval_reference_hash",
        "business_owner_approval_reference_hash",
    ]
    target_only_modules = {"identity_authorization", "integration_migration"}
    modules = []
    for row in data["readiness"]["modules"]:
        mutation = row["truth_table_dimensions"]["mutation_set"]
        if mutation["static_evidence"]:
            evidence_class = "LEGACY_STATIC_OR_TARGET_MUTATION_EVIDENCE_PRESENT"
        elif row["module"] in target_only_modules:
            evidence_class = "TARGET_MUTATION_EFFECT_DESIGN_PRESENT_LEGACY_STATIC_INCOMPLETE"
        else:
            evidence_class = "MISSING_MUTATION_DESIGN"
        modules.append(
            {
                "module": row["module"],
                "mutation_effect_evidence_class": evidence_class,
                "runtime_effect_parity_proven": mutation["runtime_effect_parity_proven"],
                "required_parity_category_ids": [item["id"] for item in parity_categories],
                "required_packet_field_count": len(required_packet_fields),
                "current_packet_status": "WAITING_FOR_APPROVED_CG06_AND_ACCEPTED_CG02",
                "accepted_packet_count": 0,
                "owner_approved_count": 0,
                "command_ready": False,
                "pilot_ready": False,
            }
        )
    summary = {
        "cg03_priority_rank": cg03["priority_rank"],
        "module_count": len(modules),
        "legacy_static_or_target_mutation_evidence_module_count": sum(
            row["mutation_effect_evidence_class"] == "LEGACY_STATIC_OR_TARGET_MUTATION_EVIDENCE_PRESENT" for row in modules
        ),
        "target_design_only_legacy_static_incomplete_module_count": sum(
            row["mutation_effect_evidence_class"] == "TARGET_MUTATION_EFFECT_DESIGN_PRESENT_LEGACY_STATIC_INCOMPLETE" for row in modules
        ),
        "runtime_effect_parity_proven_module_count": sum(row["runtime_effect_parity_proven"] for row in modules),
        "parity_category_count": len(parity_categories),
        "required_packet_field_count": len(required_packet_fields),
        "accepted_module_packet_count": sum(row["accepted_packet_count"] for row in modules),
        "owner_approved_module_count": sum(row["owner_approved_count"] for row in modules),
        "cg06_current_accepted_decision_slot_count": data["platform_intake"]["summary"]["accepted_current_packet_count"],
        "cg02_required_accepted_module_packet_count": data["atomicity_intake"]["cg02_closure_rule"]["required_accepted_module_packet_count"],
        "cg02_current_accepted_module_packet_count": data["atomicity_intake"]["cg02_closure_rule"]["current_accepted_module_packet_count"],
        "identity_integration_target_mutation_effect_design_command_count": data["boundary"]["summary"]["command_with_target_mutation_effect_design_count"],
        "identity_integration_complete_legacy_static_proof_count": data["boundary"]["summary"]["command_with_complete_legacy_static_proof_count"],
        "synthetic_acceptance_design_obligation_count": data["consolidated"]["summary"]["synthetic_acceptance_design_obligation_count"],
        "cg03_closed_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "cg03_follows_cg02": cg03["priority_rank"] == 5
        and cg03["lane"] == "ISOLATED_EFFECT_PARITY"
        and cg03["dependency_gate_ids"] == ["CG-06", "CG-02"],
        "fourteen_unique_modules": len(modules) == len({row["module"] for row in modules}) == 14,
        "evidence_boundary_12_plus_2": summary["legacy_static_or_target_mutation_evidence_module_count"] == 12
        and summary["target_design_only_legacy_static_incomplete_module_count"] == 2,
        "ten_parity_categories": summary["parity_category_count"] == 10
        and len({item["id"] for item in parity_categories}) == 10,
        "packet_schema_19": summary["required_packet_field_count"] == 19,
        "database_result_external_readback_retry_compensation_covered": {item["required_evidence"] for item in parity_categories}
        >= {
            "BEFORE_AFTER_MUTATION_DIGEST",
            "RESULT_CONTRACT_RECEIPT",
            "EXTERNAL_EFFECT_OR_QUARANTINE_RECEIPT",
            "READBACK_RECONCILIATION_DIGEST",
            "ONE_DURABLE_EFFECT_RECEIPT",
            "APPEND_ONLY_COMPENSATION_RECEIPT",
        },
        "dependencies_open": summary["cg06_current_accepted_decision_slot_count"] == 0
        and summary["cg02_required_accepted_module_packet_count"] == 14
        and summary["cg02_current_accepted_module_packet_count"] == 0,
        "target_only_boundary_honest": summary["identity_integration_target_mutation_effect_design_command_count"] == 12
        and summary["identity_integration_complete_legacy_static_proof_count"] == 0,
        "runtime_acceptance_readiness_zero": summary["runtime_effect_parity_proven_module_count"]
        == summary["accepted_module_packet_count"]
        == summary["owner_approved_module_count"]
        == summary["cg03_closed_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_effect_parity_evidence_intake_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_MUTATION_RESULT_EXTERNAL_EFFECT_PARITY_EVIDENCE_INTAKE_DESIGN",
            "gate_id": "CG-03",
            "runtime_execution_requires_cg06_and_cg02_accepted": True,
            "gate_closed": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "commands_mutations_retries_compensations_or_external_effects_executed": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "credentials_pii_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "parity_categories": parity_categories,
        "packet_schema": {
            "required_fields": required_packet_fields,
            "prohibited_fields": [
                "raw_business_row_or_value",
                "production_connection_or_endpoint",
                "credential_or_identity",
                "unbounded_replay_or_compensation_command",
                "effect_assumption_without_receipt",
            ],
            "acceptance_rule": "After accepted atomicity evidence, every declared database/result/audit/outbox/external/readback/retry/compensation/crosswalk effect reconciles on frozen synthetic inputs with immutable receipts and zero unexplained difference.",
        },
        "module_intake_map": modules,
        "global_validation_rules": [
            "Commit, audit or outbox presence alone never proves an external effect.",
            "Result success without immutable readback never proves the mutation set.",
            "Retry must reconcile the prior outcome before producing a new effect.",
            "Compensation is an append-only command and does not erase original history or provenance.",
            "Crosswalk identity, current-state identity and historical receipt identity remain separate.",
            "Any unmatched effect is quarantined; it is not silently normalized or attributed.",
        ],
        "cg03_closure_rule": {
            "required_accepted_module_packet_count": 14,
            "current_accepted_module_packet_count": 0,
            "required_parity_category_count_per_module": 10,
            "status": "OPEN_EXTERNAL_RUNTIME_GATE",
            "rule": "CG-03 closes only after CG-06 and CG-02 acceptance plus fourteen owner-approved module packets covering all ten effect layers with zero unexplained difference.",
        },
        "checks": checks,
        "failed_checks": failed,
        "risk_links": ["R-001", "R-002", "R-004", "R-005", "R-006", "R-007", "R-008", "R-011", "R-013", "R-017", "R-021", "R-023", "R-027", "R-031", "R-034", "R-043", "R-056", "R-059"],
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_effect_parity_evidence_intake_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This is an effect-parity design, not executed mutation, result or external-effect evidence.",
            "CG-06 and CG-02 are open; no CG-03 execution or promotion is claimed.",
            "No retry, compensation, crosswalk write, message, file or external call was performed.",
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
