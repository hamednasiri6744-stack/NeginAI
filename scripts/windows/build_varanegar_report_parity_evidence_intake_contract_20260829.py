"""Build the bounded CG-05 report parity and owner-Golden evidence intake contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "priority": "artifacts/varanegar_analysis/varanegar_external_evidence_gate_priority_map_20260829.json",
    "ledger": "artifacts/varanegar_analysis/varanegar_report_surface_closure_ledger_20260829.json",
    "fixture": "artifacts/varanegar_analysis/varanegar_report_golden_fixture_design_20260829.json",
    "reporting_golden": "artifacts/varanegar_analysis/varanegar_reporting_output_golden_uat_cases_20260829.json",
    "outcome": "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_envelope_20260829.json",
    "readiness": "artifacts/varanegar_analysis/varanegar_reporting_output_readiness_delta_20260829.json",
    "playbook": "artifacts/varanegar_analysis/varanegar_reporting_output_expert_playbook_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_platform_decision_evidence_intake_checkpoint_20260829.json",
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
    cg05 = next(row for row in data["priority"]["priority_map"] if row["gate_id"] == "CG-05")

    packet_schemas = {
        "RESULT_PARITY_PACKET": {
            "required_fields": [
                "surface_id",
                "result_owner_contract_reference_hash",
                "fixture_manifest_hash",
                "legacy_output_digest",
                "target_output_digest",
                "row_key_set_digest",
                "formula_policy_reference_hash",
                "grain_reference_hash",
                "scope_reference_hash",
                "rounding_policy_reference_hash",
                "null_policy_reference_hash",
                "watermark_reference_hash",
                "difference_manifest_hash",
                "owner_approval_reference_hash",
            ],
            "acceptance_rule": "Frozen isolated input; owner-approved formula/grain/scope/rounding/null policy; equal key, aggregate and output digests; zero unexplained difference.",
        },
        "COMMAND_OUTCOME_PACKET": {
            "required_fields": [
                "surface_id",
                "command_contract_reference_hash",
                "synthetic_fixture_manifest_hash",
                "authorization_decision_receipt_hash",
                "outcome_receipt_hash",
                "idempotency_or_retry_receipt_hash",
                "partial_failure_disposition_hash",
                "owner_approval_reference_hash",
            ],
            "acceptance_rule": "Authorization, outcome, retry and partial-failure cases are accepted without fabricating an independent query-result owner.",
        },
        "ROUTING_VIEW_PACKET": {
            "required_fields": [
                "surface_id",
                "routing_or_view_contract_reference_hash",
                "permission_scope_receipt_hash",
                "lifecycle_or_failure_isolation_receipt_hash",
                "downstream_owner_reference_hash",
                "owner_approval_reference_hash",
            ],
            "acceptance_rule": "Routing, permission, lifecycle and downstream ownership pass; the shell/viewer/selector is not promoted as a result owner.",
        },
    }
    rows = []
    for surface in data["ledger"]["surfaces"]:
        if surface["independent_result_parity_applicable"]:
            packet_class = "RESULT_PARITY_PACKET"
        elif surface["command_surface_present"]:
            packet_class = "COMMAND_OUTCOME_PACKET"
        else:
            packet_class = "ROUTING_VIEW_PACKET"
        rows.append(
            {
                "surface_id": surface["contract_id"],
                "ownership_class": surface["ownership_class"],
                "ownership_evidence_status": surface["ownership_evidence_status"],
                "independent_result_parity_applicable": surface["independent_result_parity_applicable"],
                "command_surface_present": surface["command_surface_present"],
                "packet_class": packet_class,
                "required_field_count": len(packet_schemas[packet_class]["required_fields"]),
                "current_packet_status": "UNEXECUTED_NO_OWNER_APPROVAL",
                "accepted_packet_count": 0,
                "result_parity_proven": False,
                "owner_golden_values_present": False,
                "acceptance_rule": packet_schemas[packet_class]["acceptance_rule"],
                "misclassification_guard": "Only RESULT_PARITY_PACKET may close result parity; shell/view/route or command receipts do not prove formula/result parity.",
            }
        )

    class_counts = {
        packet_class: sum(row["packet_class"] == packet_class for row in rows) for packet_class in packet_schemas
    }
    summary = {
        "cg05_priority_rank": cg05["priority_rank"],
        "report_surface_count": len(rows),
        "ownership_evidence_closed_count": sum(
            row["ownership_evidence_status"] == "CLOSED_HASH_PINNED_OR_VALIDATED_CONTRACT" for row in rows
        ),
        "result_parity_packet_surface_count": class_counts["RESULT_PARITY_PACKET"],
        "command_outcome_packet_surface_count": class_counts["COMMAND_OUTCOME_PACKET"],
        "routing_view_packet_surface_count": class_counts["ROUTING_VIEW_PACKET"],
        "command_surface_count": sum(row["command_surface_present"] for row in rows),
        "result_and_command_overlap_surface_count": sum(
            row["independent_result_parity_applicable"] and row["command_surface_present"] for row in rows
        ),
        "report_golden_fixture_design_count": data["fixture"]["summary"]["case_count"],
        "reporting_command_acceptance_design_count": data["reporting_golden"]["summary"]["case_count"],
        "reporting_playbook_count": data["playbook"]["summary"]["playbook_count"],
        "accepted_packet_count": sum(row["accepted_packet_count"] for row in rows),
        "executed_case_count": data["fixture"]["summary"]["executed_case_count"],
        "result_parity_proven_surface_count": data["ledger"]["summary"]["result_parity_proven_count"],
        "owner_approved_surface_count": data["fixture"]["summary"]["owner_approved_surface_count"],
        "runtime_outcome_parity_proven_count": data["outcome"]["summary"]["runtime_outcome_parity_proven_count"],
        "cg05_closed_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(value["validation"] == "PASS" for value in data.values()),
        "cg05_is_bounded_parallel": cg05["priority_rank"] == 2 and cg05["lane"] == "BOUNDED_REPORT_PARITY",
        "twenty_unique_surfaces": len(rows) == len({row["surface_id"] for row in rows}) == 20,
        "ownership_closed_20": summary["ownership_evidence_closed_count"] == 20,
        "packet_partition_11_2_7": summary["result_parity_packet_surface_count"] == 11
        and summary["command_outcome_packet_surface_count"] == 2
        and summary["routing_view_packet_surface_count"] == 7,
        "command_overlap_8_6": summary["command_surface_count"] == 8
        and summary["result_and_command_overlap_surface_count"] == 6,
        "packet_schema_sizes": len(packet_schemas["RESULT_PARITY_PACKET"]["required_fields"]) == 14
        and len(packet_schemas["COMMAND_OUTCOME_PACKET"]["required_fields"]) == 8
        and len(packet_schemas["ROUTING_VIEW_PACKET"]["required_fields"]) == 6,
        "only_result_packet_closes_parity": all(
            row["packet_class"] == "RESULT_PARITY_PACKET" if row["independent_result_parity_applicable"] else row["packet_class"] != "RESULT_PARITY_PACKET"
            for row in rows
        ),
        "design_assets_stable": summary["report_golden_fixture_design_count"] == 88
        and summary["reporting_command_acceptance_design_count"] == 56
        and summary["reporting_playbook_count"] == 6,
        "execution_owner_parity_zero": summary["accepted_packet_count"]
        == summary["executed_case_count"]
        == summary["result_parity_proven_surface_count"]
        == summary["owner_approved_surface_count"]
        == summary["runtime_outcome_parity_proven_count"]
        == summary["cg05_closed_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_report_parity_evidence_intake_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_BOUNDED_REPORT_PARITY_EVIDENCE_INTAKE_DESIGN",
            "gate_id": "CG-05",
            "logical_dependency_on_cg06_acceptance": False,
            "gate_closed": False,
            "continuation_complete": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "reports_queries_exports_prints_or_commands_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "credentials_pii_or_raw_business_values_read_or_persisted": 0,
        },
        "summary": summary,
        "packet_schemas": packet_schemas,
        "surface_intake_map": rows,
        "global_validation_rules": [
            "Frozen fixture, scope and watermark references must identify the same isolated comparison run.",
            "Row-key equality does not replace formula, aggregate, rounding, null and scope parity.",
            "Owner approval must reference the exact immutable difference manifest and expected-value policy.",
            "Any unexplained difference keeps the surface open; a documented approved semantic difference is not silently normalized.",
            "Shell, viewer, selector and orchestrator ownership must not be promoted to query-result ownership.",
            "No digest or receipt may embed raw business values, identities, credentials or endpoints.",
        ],
        "cg05_closure_rule": {
            "required_result_parity_surface_count": 11,
            "current_result_parity_surface_count": 0,
            "required_non_result_surface_packet_count": 9,
            "current_non_result_surface_packet_count": 0,
            "status": "OPEN_EXTERNAL_REPORT_UAT_GATE",
            "rule": "CG-05 closes only when all eleven result owners pass parity and all nine non-result surfaces pass their correct routing/view/command packets with owner approval and zero unexplained difference.",
        },
        "checks": checks,
        "failed_checks": failed,
        "risk_links": ["R-002", "R-004", "R-005", "R-006", "R-007", "R-009", "R-017", "R-021", "R-023", "R-031", "R-034"],
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_report_parity_evidence_intake_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This contract may be prepared in parallel with CG-06; it does not imply a runtime environment exists.",
            "No report, query, export, print or command was executed and no owner value was collected.",
            "All result parity, owner approval and readiness counts remain zero.",
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
