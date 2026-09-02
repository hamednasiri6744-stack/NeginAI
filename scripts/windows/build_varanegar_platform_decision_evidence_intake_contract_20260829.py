"""Build the provider-neutral CG-06 decision evidence intake contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "priority": "artifacts/varanegar_analysis/varanegar_external_evidence_gate_priority_map_20260829.json",
    "outcome": "artifacts/varanegar_analysis/varanegar_platform_outcome_envelope_20260829.json",
    "readiness": "artifacts/varanegar_analysis/varanegar_platform_readiness_delta_20260829.json",
    "golden": "artifacts/varanegar_analysis/varanegar_platform_golden_uat_cases_20260829.json",
    "playbook": "artifacts/varanegar_analysis/varanegar_platform_expert_playbook_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_external_evidence_gate_priority_checkpoint_20260829.json",
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
    cg06 = next(row for row in data["priority"]["priority_map"] if row["gate_id"] == "CG-06")

    slots = [
        {
            "rank": 1,
            "decision_slot_id": "PD-01",
            "decision": "application_and_service_stack",
            "lane": "ARCHITECTURE",
            "dependency_slot_ids": [],
            "status": "UNSELECTED",
            "decision_selected": False,
            "current_accepted_packet_count": 0,
            "required_specific_evidence": ["supported-runtime reference", "lifecycle/support-policy reference"],
        },
        {
            "rank": 2,
            "decision_slot_id": "PD-02",
            "decision": "database_platform",
            "lane": "ARCHITECTURE",
            "dependency_slot_ids": ["PD-01"],
            "status": "UNSELECTED",
            "decision_selected": False,
            "current_accepted_packet_count": 0,
            "required_specific_evidence": ["database capability reference", "backup/restore compatibility reference"],
        },
        {
            "rank": 3,
            "decision_slot_id": "PD-03",
            "decision": "hosting_and_network_topology",
            "lane": "ARCHITECTURE",
            "dependency_slot_ids": ["PD-01"],
            "status": "UNSELECTED",
            "decision_selected": False,
            "current_accepted_packet_count": 0,
            "required_specific_evidence": ["topology decision reference", "isolation/trust-boundary reference"],
        },
        {
            "rank": 4,
            "decision_slot_id": "PD-04",
            "decision": "accountable_deployment_owner_role",
            "lane": "OWNERSHIP",
            "dependency_slot_ids": [],
            "status": "UNSELECTED",
            "decision_selected": False,
            "current_accepted_packet_count": 0,
            "required_specific_evidence": ["accountability charter reference", "delegation/escalation policy reference"],
        },
        {
            "rank": 5,
            "decision_slot_id": "PD-05",
            "decision": "approved_rpo_policy",
            "lane": "RECOVERY_POLICY",
            "dependency_slot_ids": ["PD-04"],
            "status": "UNSELECTED",
            "decision_selected": False,
            "current_accepted_packet_count": 0,
            "required_specific_evidence": ["approved target reference", "measurement-boundary reference"],
        },
        {
            "rank": 6,
            "decision_slot_id": "PD-06",
            "decision": "approved_rto_policy",
            "lane": "RECOVERY_POLICY",
            "dependency_slot_ids": ["PD-04"],
            "status": "UNSELECTED",
            "decision_selected": False,
            "current_accepted_packet_count": 0,
            "required_specific_evidence": ["approved target reference", "start/stop clock-boundary reference"],
        },
        {
            "rank": 7,
            "decision_slot_id": "PD-07",
            "decision": "isolated_runtime_evidence_environment",
            "lane": "EVIDENCE_ENVIRONMENT",
            "dependency_slot_ids": ["PD-01", "PD-02", "PD-03", "PD-04"],
            "status": "UNSELECTED",
            "decision_selected": False,
            "current_accepted_packet_count": 0,
            "required_specific_evidence": ["non-production isolation attestation", "synthetic-data and credential-boundary attestation"],
        },
        {
            "rank": 8,
            "decision_slot_id": "PD-08",
            "decision": "recovery_drill_and_receipt_policy",
            "lane": "RECOVERY_POLICY",
            "dependency_slot_ids": ["PD-03", "PD-04", "PD-05", "PD-06", "PD-07"],
            "status": "UNSELECTED",
            "decision_selected": False,
            "current_accepted_packet_count": 0,
            "required_specific_evidence": ["approved drill policy reference", "health/reconciliation/external-effect receipt contract reference"],
        },
    ]
    required_packet_fields = [
        "packet_id",
        "decision_slot_id",
        "decision_version",
        "decision_status",
        "scope_reference_hash",
        "selected_option_reference_hash",
        "approval_reference_hash",
        "approval_authority_role_code",
        "effective_window_reference_hash",
        "supersedes_packet_hash",
        "evidence_manifest_hashes",
    ]
    intake_contract = {
        "allowed_decision_statuses": ["PROPOSAL", "APPROVED", "REJECTED", "SUPERSEDED"],
        "accepted_current_classification": "APPROVED_CURRENT",
        "required_packet_fields": required_packet_fields,
        "prohibited_payload_fields": [
            "person_name_or_identity",
            "credential_or_secret",
            "raw_endpoint_or_connection_string",
            "raw_vendor_quote_or_contract",
            "raw_business_value_or_production_sample",
        ],
        "validation_outcomes": [
            "MISSING",
            "PROPOSAL_ONLY",
            "INCOMPLETE_APPROVAL",
            "APPROVED_CURRENT",
            "SUPERSEDED",
            "CONFLICTING_CURRENT_APPROVALS",
            "DEPENDENCY_NOT_APPROVED",
        ],
        "canonical_rules": [
            "PROPOSAL never satisfies an approval slot",
            "APPROVED requires option, approval, authority-role, scope and effective-window references",
            "only one non-superseded APPROVED packet may be current per slot and scope",
            "every dependency slot must be APPROVED_CURRENT before a dependent slot is accepted",
            "a role code proves accountable role classification, not a person's identity or effective authority",
            "approval and policy references are hash-pinned; their raw sensitive contents are not copied here",
            "a selected technology or policy never proves deployment, restore, failover or runtime parity",
        ],
    }
    rank_by_slot = {slot["decision_slot_id"]: slot["rank"] for slot in slots}
    dependencies_ordered = all(
        rank_by_slot[dependency] < slot["rank"] for slot in slots for dependency in slot["dependency_slot_ids"]
    )
    summary = {
        "cg06_priority_rank": cg06["priority_rank"],
        "decision_slot_count": len(slots),
        "decision_lane_count": len({slot["lane"] for slot in slots}),
        "dependent_decision_slot_count": sum(bool(slot["dependency_slot_ids"]) for slot in slots),
        "required_packet_field_count": len(required_packet_fields),
        "validation_outcome_count": len(intake_contract["validation_outcomes"]),
        "selected_decision_slot_count": sum(slot["decision_selected"] for slot in slots),
        "accepted_current_packet_count": sum(slot["current_accepted_packet_count"] for slot in slots),
        "cg06_closed_count": 0,
        "platform_command_contract_count": data["outcome"]["summary"]["command_contract_count"],
        "platform_acceptance_design_count": data["golden"]["summary"]["combined_platform_acceptance_design_count"],
        "platform_playbook_count": data["playbook"]["summary"]["playbook_count"],
        "deployment_file_count": data["outcome"]["summary"]["deployment_file_count"],
        "deployment_external_reference_count": data["outcome"]["summary"]["deployment_external_reference_count"],
        "implemented_command_count": data["outcome"]["summary"]["implemented_command_count"],
        "executed_restore_drill_count": data["outcome"]["summary"]["executed_restore_drill_count"],
        "runtime_external_effect_parity_proven_count": data["outcome"]["summary"]["runtime_external_effect_parity_proven_count"],
        "owner_approved_case_count": data["golden"]["summary"]["owner_approved_case_count"],
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "cg06_is_foundation": cg06["priority_rank"] == 1 and cg06["lane"] == "FOUNDATION_DECISION",
        "eight_unique_ordered_slots": len(slots) == len(rank_by_slot) == 8
        and [slot["rank"] for slot in slots] == list(range(1, 9)),
        "dependencies_precede_consumers": dependencies_ordered,
        "four_lanes": summary["decision_lane_count"] == 4,
        "packet_schema_complete": summary["required_packet_field_count"] == 11
        and len(intake_contract["prohibited_payload_fields"]) == 5,
        "proposal_not_approval": intake_contract["canonical_rules"][0] == "PROPOSAL never satisfies an approval slot",
        "all_decisions_unselected": summary["selected_decision_slot_count"]
        == summary["accepted_current_packet_count"]
        == summary["cg06_closed_count"]
        == data["outcome"]["summary"]["stack_selected_count"]
        == data["outcome"]["summary"]["database_selected_count"]
        == data["outcome"]["summary"]["hosting_selected_count"]
        == data["outcome"]["summary"]["approved_recovery_target_count"]
        == data["outcome"]["summary"]["deployment_owner_selected_count"]
        == 0,
        "design_assets_stable": summary["platform_command_contract_count"] == 6
        and summary["platform_acceptance_design_count"] == 42
        and summary["platform_playbook_count"] == 7,
        "runtime_and_readiness_zero": summary["implemented_command_count"]
        == summary["executed_restore_drill_count"]
        == summary["runtime_external_effect_parity_proven_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_platform_decision_evidence_intake_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_PROVIDER_NEUTRAL_DECISION_EVIDENCE_INTAKE_DESIGN",
            "gate_id": "CG-06",
            "gate_closed": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "platform_deployments_restores_or_drills_executed": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "credentials_pii_endpoints_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "intake_contract": intake_contract,
        "decision_slots": slots,
        "cg06_closure_rule": {
            "required_current_slot_count": 8,
            "current_accepted_slot_count": 0,
            "status": "OPEN_EXTERNAL_DECISION_GATE",
            "rule": "CG-06 closes only when all eight slots classify APPROVED_CURRENT with ordered dependencies and no conflict; closure still does not prove runtime effects.",
        },
        "checks": checks,
        "failed_checks": failed,
        "risk_links": ["R-001", "R-002", "R-005", "R-006", "R-007", "R-008", "R-023", "R-031", "R-034", "R-043"],
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_platform_decision_evidence_intake_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This defines evidence intake; it does not select a provider, stack, database, topology, target or owner.",
            "No proposal, role label or hash reference is treated as effective approval without the complete packet.",
            "CG-06 remains open and all runtime/readiness dimensions remain zero.",
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
