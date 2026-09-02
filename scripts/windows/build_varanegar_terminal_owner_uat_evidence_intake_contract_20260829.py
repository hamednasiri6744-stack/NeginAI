"""Build the terminal CG-04 owner-UAT evidence intake contract."""
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
    "consolidated": "artifacts/varanegar_analysis/varanegar_24h_continuation_consolidated_audit_20260829.json",
    "platform_intake": "artifacts/varanegar_analysis/varanegar_platform_decision_evidence_intake_contract_20260829.json",
    "report_intake": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json",
    "authorization_intake": "artifacts/varanegar_analysis/varanegar_authorization_runtime_evidence_intake_contract_20260829.json",
    "atomicity_intake": "artifacts/varanegar_analysis/varanegar_atomicity_fault_evidence_intake_contract_20260829.json",
    "effect_intake": "artifacts/varanegar_analysis/varanegar_effect_parity_evidence_intake_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_effect_parity_evidence_intake_checkpoint_20260829.json",
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
    cg04 = next(row for row in data["priority"]["priority_map"] if row["gate_id"] == "CG-04")

    acceptance_dimensions = [
        {"id": "UAT-01", "dimension": "all_upstream_gate_packets_accepted"},
        {"id": "UAT-02", "dimension": "module_obligation_manifest_complete"},
        {"id": "UAT-03", "dimension": "immutable_isolated_execution_receipts_complete"},
        {"id": "UAT-04", "dimension": "zero_unexplained_difference"},
        {"id": "UAT-05", "dimension": "risk_and_exception_disposition_complete"},
        {"id": "UAT-06", "dimension": "business_owner_approval"},
        {"id": "UAT-07", "dimension": "security_approval"},
        {"id": "UAT-08", "dimension": "finance_operations_or_platform_control_approval_when_applicable"},
        {"id": "UAT-09", "dimension": "promotion_snapshot_and_rollback_boundary_approved"},
    ]
    required_packet_fields = [
        "module",
        "module_obligation_manifest_hash",
        "cg06_decision_packet_set_hash",
        "cg05_report_packet_set_hash",
        "cg01_authorization_packet_hash",
        "cg02_atomicity_packet_hash",
        "cg03_effect_parity_packet_hash",
        "isolated_run_manifest_hash",
        "executed_obligation_receipt_set_hash",
        "difference_and_exception_manifest_hash",
        "risk_disposition_manifest_hash",
        "business_owner_approval_reference_hash",
        "security_approval_reference_hash",
        "control_owner_approval_reference_hash",
        "promotion_snapshot_reference_hash",
        "rollback_boundary_reference_hash",
    ]
    modules = [
        {
            "module": row["module"],
            "required_acceptance_dimension_ids": [item["id"] for item in acceptance_dimensions],
            "required_packet_field_count": len(required_packet_fields),
            "current_packet_status": "WAITING_FOR_CG06_CG05_CG01_CG02_CG03",
            "executed_obligation_count": 0,
            "accepted_packet_count": 0,
            "owner_approved_count": 0,
            "promotion_approved": False,
            "command_ready": False,
            "pilot_ready": False,
        }
        for row in data["readiness"]["modules"]
    ]
    prerequisites = {
        "CG-06": {
            "required": data["platform_intake"]["cg06_closure_rule"]["required_current_slot_count"],
            "current": data["platform_intake"]["cg06_closure_rule"]["current_accepted_slot_count"],
        },
        "CG-05": {
            "required": data["report_intake"]["summary"]["report_surface_count"],
            "current": data["report_intake"]["summary"]["accepted_packet_count"],
        },
        "CG-01": {
            "required": data["authorization_intake"]["cg01_closure_rule"]["required_accepted_module_packet_count"],
            "current": data["authorization_intake"]["cg01_closure_rule"]["current_accepted_module_packet_count"],
        },
        "CG-02": {
            "required": data["atomicity_intake"]["cg02_closure_rule"]["required_accepted_module_packet_count"],
            "current": data["atomicity_intake"]["cg02_closure_rule"]["current_accepted_module_packet_count"],
        },
        "CG-03": {
            "required": data["effect_intake"]["cg03_closure_rule"]["required_accepted_module_packet_count"],
            "current": data["effect_intake"]["cg03_closure_rule"]["current_accepted_module_packet_count"],
        },
    }
    summary = {
        "cg04_priority_rank": cg04["priority_rank"],
        "module_count": len(modules),
        "acceptance_dimension_count": len(acceptance_dimensions),
        "required_packet_field_count": len(required_packet_fields),
        "synthetic_acceptance_design_obligation_count": data["consolidated"]["summary"]["synthetic_acceptance_design_obligation_count"],
        "executed_obligation_count": data["consolidated"]["summary"]["executed_case_count"],
        "accepted_module_packet_count": sum(row["accepted_packet_count"] for row in modules),
        "owner_approved_module_count": sum(row["owner_approved_count"] for row in modules),
        "promotion_approved_module_count": sum(row["promotion_approved"] for row in modules),
        "upstream_gate_count": len(prerequisites),
        "upstream_required_packet_or_slot_count": sum(row["required"] for row in prerequisites.values()),
        "upstream_current_accepted_packet_or_slot_count": sum(row["current"] for row in prerequisites.values()),
        "unexplained_difference_count": 0,
        "approved_exception_count": 0,
        "cg04_closed_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "cg04_is_terminal": cg04["priority_rank"] == 6
        and cg04["lane"] == "TERMINAL_OWNER_UAT"
        and set(cg04["dependency_gate_ids"]) == {"CG-01", "CG-02", "CG-03", "CG-05", "CG-06"},
        "fourteen_unique_modules": len(modules) == len({row["module"] for row in modules}) == 14,
        "nine_dimensions_sixteen_fields": summary["acceptance_dimension_count"] == 9
        and summary["required_packet_field_count"] == 16,
        "five_upstream_gates": set(prerequisites) == {"CG-01", "CG-02", "CG-03", "CG-05", "CG-06"}
        and summary["upstream_gate_count"] == 5,
        "upstream_required_count_70_current_0": summary["upstream_required_packet_or_slot_count"] == 70
        and summary["upstream_current_accepted_packet_or_slot_count"] == 0,
        "design_1229_execution_zero": summary["synthetic_acceptance_design_obligation_count"] == 1229
        and summary["executed_obligation_count"] == 0,
        "approval_promotion_readiness_zero": summary["accepted_module_packet_count"]
        == summary["owner_approved_module_count"]
        == summary["promotion_approved_module_count"]
        == summary["cg04_closed_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_terminal_owner_uat_evidence_intake_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_TERMINAL_OWNER_UAT_EVIDENCE_INTAKE_DESIGN",
            "gate_id": "CG-04",
            "execution_requires_all_five_upstream_gates_accepted": True,
            "gate_closed": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "uat_cases_commands_reports_or_procedures_executed": 0,
            "owner_or_security_approvals_collected": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "credentials_pii_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "upstream_gate_requirements": prerequisites,
        "acceptance_dimensions": acceptance_dimensions,
        "packet_schema": {
            "required_fields": required_packet_fields,
            "prohibited_fields": [
                "person_name_or_identity",
                "credential_or_endpoint",
                "raw_business_value_or_output",
                "unsigned_or_mutable_approval",
                "readiness_promotion_before_complete_prerequisites",
            ],
            "acceptance_rule": "All five upstream gates are accepted; every in-scope obligation executes in isolation with immutable receipts; unexplained differences are zero; risk exceptions and accountable role approvals are complete; promotion and rollback boundaries reference the exact snapshot.",
        },
        "module_intake_map": modules,
        "global_validation_rules": [
            "A designed obligation, passing offline contract test or hash-pinned artifact is not an executed UAT result.",
            "Approval references the exact immutable run, difference, risk and promotion snapshot; generic approval is invalid.",
            "No module is command-ready or pilot-ready until every required upstream and terminal packet is accepted.",
            "An approved exception is explicit, bounded and owned; it is never counted as zero unexplained difference.",
            "Report owner approval remains in CG-05 and is referenced, not duplicated or inferred in CG-04.",
            "Readiness promotion is atomic at the declared snapshot and retains a rollback boundary.",
        ],
        "cg04_closure_rule": {
            "required_executed_obligation_count": 1229,
            "current_executed_obligation_count": 0,
            "required_accepted_module_packet_count": 14,
            "current_accepted_module_packet_count": 0,
            "required_upstream_gate_count": 5,
            "current_accepted_upstream_gate_count": 0,
            "status": "OPEN_EXTERNAL_OWNER_UAT_GATE",
            "rule": "CG-04 closes only after all five upstream gates, all 1,229 obligation receipts, fourteen terminal packets, zero unexplained difference and exact accountable-role approvals; only then may readiness be reconsidered.",
        },
        "checks": checks,
        "failed_checks": failed,
        "risk_links": ["R-001", "R-002", "R-004", "R-005", "R-006", "R-007", "R-008", "R-009", "R-011", "R-013", "R-017", "R-021", "R-023", "R-027", "R-031", "R-034", "R-043", "R-056", "R-057", "R-058", "R-059", "R-062"],
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_terminal_owner_uat_evidence_intake_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This is a terminal UAT intake design, not UAT execution or owner approval.",
            "All five upstream gates are open and no readiness state is promoted.",
            "No identity, raw value, command, report, procedure, mutation or external effect was used.",
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
