"""Build a unified handoff and acceptance matrix for all six external gates."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "priority": "artifacts/varanegar_analysis/varanegar_external_evidence_gate_priority_map_20260829.json",
    "cg06": "artifacts/varanegar_analysis/varanegar_platform_decision_evidence_intake_contract_20260829.json",
    "cg05": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json",
    "cg01": "artifacts/varanegar_analysis/varanegar_authorization_runtime_evidence_intake_contract_20260829.json",
    "cg02": "artifacts/varanegar_analysis/varanegar_atomicity_fault_evidence_intake_contract_20260829.json",
    "cg03": "artifacts/varanegar_analysis/varanegar_effect_parity_evidence_intake_contract_20260829.json",
    "cg04": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_checkpoint_20260829.json",
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
    priority = {row["gate_id"]: row for row in data["priority"]["priority_map"]}

    rows = [
        {
            "gate_id": "CG-06",
            "contract_source": "cg06",
            "required_acceptance_unit_count": data["cg06"]["cg06_closure_rule"]["required_current_slot_count"],
            "current_accepted_unit_count": data["cg06"]["cg06_closure_rule"]["current_accepted_slot_count"],
            "unit_type": "PLATFORM_DECISION_SLOT",
            "accountable_role_types": ["PLATFORM_ACCOUNTABLE_ROLE", "SECURITY_NETWORK_CONTROL_ROLE", "RECOVERY_CONTROL_ROLE"],
            "downstream_gate_ids": ["CG-01", "CG-02", "CG-03", "CG-04"],
            "handoff_payload": "accepted immutable eight-slot decision packet set",
        },
        {
            "gate_id": "CG-05",
            "contract_source": "cg05",
            "required_acceptance_unit_count": data["cg05"]["summary"]["report_surface_count"],
            "current_accepted_unit_count": data["cg05"]["summary"]["accepted_packet_count"],
            "unit_type": "REPORT_SURFACE_PACKET",
            "accountable_role_types": ["REPORT_RESULT_OWNER_ROLE", "BUSINESS_CONTROL_OWNER_ROLE"],
            "downstream_gate_ids": ["CG-04"],
            "handoff_payload": "accepted twenty-surface report packet set with owner dispositions",
        },
        {
            "gate_id": "CG-01",
            "contract_source": "cg01",
            "required_acceptance_unit_count": data["cg01"]["cg01_closure_rule"]["required_accepted_module_packet_count"],
            "current_accepted_unit_count": data["cg01"]["cg01_closure_rule"]["current_accepted_module_packet_count"],
            "unit_type": "AUTHORIZATION_MODULE_PACKET",
            "accountable_role_types": ["SECURITY_AUTHORIZATION_OWNER_ROLE", "MODULE_BUSINESS_OWNER_ROLE"],
            "downstream_gate_ids": ["CG-04"],
            "handoff_payload": "accepted fourteen-module authorization packet set",
        },
        {
            "gate_id": "CG-02",
            "contract_source": "cg02",
            "required_acceptance_unit_count": data["cg02"]["cg02_closure_rule"]["required_accepted_module_packet_count"],
            "current_accepted_unit_count": data["cg02"]["cg02_closure_rule"]["current_accepted_module_packet_count"],
            "unit_type": "ATOMICITY_MODULE_PACKET",
            "accountable_role_types": ["TRANSACTION_CONTROL_OWNER_ROLE", "MODULE_TECHNICAL_OWNER_ROLE"],
            "downstream_gate_ids": ["CG-03", "CG-04"],
            "handoff_payload": "accepted fourteen-module atomicity and fault packet set",
        },
        {
            "gate_id": "CG-03",
            "contract_source": "cg03",
            "required_acceptance_unit_count": data["cg03"]["cg03_closure_rule"]["required_accepted_module_packet_count"],
            "current_accepted_unit_count": data["cg03"]["cg03_closure_rule"]["current_accepted_module_packet_count"],
            "unit_type": "EFFECT_PARITY_MODULE_PACKET",
            "accountable_role_types": ["EFFECT_RECONCILIATION_OWNER_ROLE", "MODULE_BUSINESS_OWNER_ROLE"],
            "downstream_gate_ids": ["CG-04"],
            "handoff_payload": "accepted fourteen-module mutation/result/effect packet set",
        },
        {
            "gate_id": "CG-04",
            "contract_source": "cg04",
            "required_acceptance_unit_count": data["cg04"]["cg04_closure_rule"]["required_accepted_module_packet_count"],
            "current_accepted_unit_count": data["cg04"]["cg04_closure_rule"]["current_accepted_module_packet_count"],
            "unit_type": "TERMINAL_OWNER_UAT_MODULE_PACKET",
            "accountable_role_types": ["BUSINESS_OWNER_ROLE", "SECURITY_APPROVER_ROLE", "CONTROL_OWNER_ROLE", "PLATFORM_PROMOTION_OWNER_ROLE"],
            "downstream_gate_ids": [],
            "handoff_payload": "terminal fourteen-module UAT packet set bound to the exact promotion snapshot",
        },
    ]
    for row in rows:
        gate = priority[row["gate_id"]]
        row.update(
            {
                "priority_rank": gate["priority_rank"],
                "dependency_gate_ids": gate["dependency_gate_ids"],
                "lane": gate["lane"],
                "external_gate_status": gate["status"],
                "current_handoff_status": "WAITING_FOR_ACCEPTED_CURRENT_UNITS",
                "readiness_effect_before_gate_closure": "NONE",
            }
        )

    edges = [
        {
            "from_gate_id": dependency,
            "to_gate_id": row["gate_id"],
            "handoff_state": "BLOCKED_SOURCE_GATE_OPEN",
            "acceptance_rule": "The consumer may reference only the exact hash-pinned ACCEPTED_CURRENT source packet set; proposal, partial acceptance or stale evidence is rejected.",
        }
        for row in rows
        for dependency in row["dependency_gate_ids"]
    ]
    rejection_codes = [
        "MISSING_REQUIRED_FIELD",
        "UNPINNED_OR_MUTABLE_REFERENCE",
        "STALE_OR_SUPERSEDED_EVIDENCE",
        "DEPENDENCY_GATE_NOT_ACCEPTED",
        "ACCOUNTABLE_ROLE_APPROVAL_MISSING",
        "UNEXPLAINED_DIFFERENCE_PRESENT",
        "PROHIBITED_RAW_OR_IDENTITY_PAYLOAD",
        "PREMATURE_READINESS_PROMOTION_ATTEMPT",
    ]
    summary = {
        "gate_count": len(rows),
        "handoff_edge_count": len(edges),
        "required_acceptance_unit_count": sum(row["required_acceptance_unit_count"] for row in rows),
        "current_accepted_unit_count": sum(row["current_accepted_unit_count"] for row in rows),
        "open_gate_count": sum(row["current_accepted_unit_count"] < row["required_acceptance_unit_count"] for row in rows),
        "closed_gate_count": 0,
        "accepted_handoff_edge_count": 0,
        "blocked_handoff_edge_count": len(edges),
        "accountable_role_type_assignment_count": sum(len(row["accountable_role_types"]) for row in rows),
        "rejection_code_count": len(rejection_codes),
        "executed_obligation_count": data["cg04"]["summary"]["executed_obligation_count"],
        "owner_approved_module_count": data["cg04"]["summary"]["owner_approved_module_count"],
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "six_gates_ranked": [row["priority_rank"] for row in rows] == [1, 2, 3, 4, 5, 6],
        "required_units_84_current_0": summary["required_acceptance_unit_count"] == 84
        and summary["current_accepted_unit_count"] == 0,
        "nine_edges_all_blocked": summary["handoff_edge_count"] == summary["blocked_handoff_edge_count"] == 9
        and summary["accepted_handoff_edge_count"] == 0,
        "dependency_edges_exact": {(edge["from_gate_id"], edge["to_gate_id"]) for edge in edges}
        == {
            ("CG-06", "CG-01"),
            ("CG-06", "CG-02"),
            ("CG-06", "CG-03"),
            ("CG-02", "CG-03"),
            ("CG-01", "CG-04"),
            ("CG-02", "CG-04"),
            ("CG-03", "CG-04"),
            ("CG-05", "CG-04"),
            ("CG-06", "CG-04"),
        },
        "all_gates_open_no_promotion": summary["open_gate_count"] == 6
        and summary["closed_gate_count"] == 0
        and all(row["readiness_effect_before_gate_closure"] == "NONE" for row in rows),
        "role_only_no_person_identity": all(
            role.endswith("_ROLE") and "PERSON" not in role
            for row in rows
            for role in row["accountable_role_types"]
        ),
        "terminal_execution_approval_readiness_zero": summary["executed_obligation_count"]
        == summary["owner_approved_module_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_external_gate_handoff_acceptance_matrix_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_EXTERNAL_GATE_HANDOFF_ACCEPTANCE_DESIGN",
            "all_external_gates_open": True,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "operational_forms_reports_procedures_or_commands_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "credentials_pii_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "gate_handoff_matrix": rows,
        "dependency_handoff_edges": edges,
        "handoff_state_machine": {
            "states": ["WAITING_DEPENDENCY", "SUBMITTED", "REJECTED", "ACCEPTED_CURRENT", "SUPERSEDED"],
            "acceptance_invariants": [
                "Only hash-pinned evidence that satisfies the source gate contract may become ACCEPTED_CURRENT.",
                "A newer accepted packet supersedes the prior packet; consumers must rebind to the new exact hash.",
                "A gate remains open until every required unit is ACCEPTED_CURRENT and its closure rule passes.",
                "Acceptance is assigned to accountable role types; no personal identity is stored in this artifact.",
                "No handoff or gate closure alone implies command-ready or pilot-ready status.",
            ],
            "rejection_codes": rejection_codes,
        },
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_external_gate_handoff_acceptance_matrix_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This matrix coordinates evidence handoff; it does not collect or approve external evidence.",
            "All six gates and all nine dependency handoffs remain open or blocked.",
            "No runtime, UAT, owner approval or readiness state is inferred from offline artifacts.",
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
