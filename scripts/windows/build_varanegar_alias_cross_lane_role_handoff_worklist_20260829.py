"""Build role-scoped handoff worklists for the cross-lane evidence queue."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "receipt_matrix": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.json",
    "receipt_checkpoint": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_checkpoint_20260829.json",
    "queue": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_external_evidence_intake_queue_20260829.json",
    "owner_packets": "artifacts/varanegar_analysis/varanegar_action_alias_owner_evidence_packet_matrix_20260829.json",
    "priority": "artifacts/varanegar_analysis/varanegar_action_alias_handoff_priority_matrix_20260829.json",
    "gate_matrix": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json",
    "terminal_gate": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_contract_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

ROLE_DUTIES = {
    "ACCOUNTING_DOMAIN_OWNER_ROLE": ["semantic disposition", "accounting outcome vocabulary", "business-control approval"],
    "ACCOUNTING_APPLICATION_OWNER_ROLE": ["technical effect evidence", "failure and retry receipt", "reproducibility review"],
    "INVENTORY_ACCOUNTING_CROSS_MODULE_OWNER_ROLE": ["cross-module boundary", "reconciliation effect", "supersession conflict review"],
    "TREASURY_DOMAIN_OWNER_ROLE": ["treasury semantic disposition", "state-transition outcome", "business-control approval"],
    "BANK_RECONCILIATION_OWNER_ROLE": ["bank reconciliation state machine", "instrument lifecycle effect", "control approval"],
    "TREASURY_APPLICATION_OWNER_ROLE": ["technical effect evidence", "source immutability", "failure and retry receipt"],
    "INTEGRATION_REPLICATION_OWNER_ROLE": ["replication effect", "crosswalk and retry convergence", "external acknowledgment boundary"],
    "PRICING_POLICY_OWNER_ROLE": ["policy semantics", "precedence and version", "business-rule approval"],
    "PRICING_APPLICATION_OWNER_ROLE": ["compiled condition effect", "concurrency and retry", "technical reproducibility"],
    "REPORT_RESULT_OWNER_ROLE": ["frozen fixture", "value and rowset parity", "result acceptance"],
    "DATA_EXPORT_POLICY_OWNER_ROLE": ["export schema and ordering", "format and encoding", "file/source immutability"],
    "BANK_STATEMENT_OWNER_ROLE": ["statement fixture identity", "import/read result", "statement control approval"],
    "DOCUMENT_PRINT_OWNER_ROLE": ["render and completion", "per-item outcome", "presentation integrity"],
}

OWNER_ROSTER_FIELDS = [
    "role_type",
    "named_owner_reference",
    "delegate_reference",
    "approval_authority_reference",
    "environment_scope",
    "module_or_surface_scope",
    "effective_from",
    "expires_at",
    "policy_version",
    "conflict_of_interest_attestation",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_ids(values: list[str]) -> str:
    payload = "\n".join(sorted(values)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = {name: ROOT / value for name, value in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    queue = documents["queue"]["intake_queue"]
    slots = documents["receipt_matrix"]["receipt_slots"]
    slots_by_intake = defaultdict(list)
    for slot in slots:
        slots_by_intake[slot["intake_id"]].append(slot)

    role_to_intakes = defaultdict(list)
    for intake in queue:
        for role_type in intake["accountable_role_types"]:
            role_to_intakes[role_type].append(intake)

    worklists = []
    for role_type in sorted(role_to_intakes):
        intakes = sorted(role_to_intakes[role_type], key=lambda row: (row["priority_rank"], row["source_packet_id"]))
        receipt_slot_ids = sorted(
            slot["receipt_slot_id"]
            for intake in intakes
            for slot in slots_by_intake[intake["intake_id"]]
        )
        route_distribution = Counter(intake["required_decision_route"] for intake in intakes)
        lane_distribution = Counter(intake["lane"] for intake in intakes)
        worklists.append(
            {
                "role_worklist_id": f"RHW-{len(worklists)+1:02d}",
                "accountable_role_type": role_type,
                "role_duties": ROLE_DUTIES[role_type],
                "required_owner_roster_fields": OWNER_ROSTER_FIELDS,
                "packet_assignment_count": len(intakes),
                "case_assignment_count": sum(intake["case_count"] for intake in intakes),
                "receipt_slot_assignment_count": len(receipt_slot_ids),
                "intake_ids": [intake["intake_id"] for intake in intakes],
                "source_packet_ids": [intake["source_packet_id"] for intake in intakes],
                "receipt_slot_ids": receipt_slot_ids,
                "receipt_slot_id_set_sha256": digest_ids(receipt_slot_ids),
                "route_distribution": dict(sorted(route_distribution.items())),
                "lane_distribution": dict(sorted(lane_distribution.items())),
                "named_owner_assignment_count": 0,
                "delegate_assignment_count": 0,
                "accepted_owner_roster_count": 0,
                "received_receipt_count": 0,
                "role_accepted_receipt_count": 0,
                "accepted_route_decision_count": 0,
                "handoff_status": "UNASSIGNED_NAMED_OWNER",
                "readiness_effect": "ZERO",
            }
        )

    summary = {
        "role_worklist_count": len(worklists),
        "role_packet_assignment_count": sum(row["packet_assignment_count"] for row in worklists),
        "role_case_assignment_count": sum(row["case_assignment_count"] for row in worklists),
        "role_receipt_slot_assignment_count": sum(row["receipt_slot_assignment_count"] for row in worklists),
        "underlying_intake_item_count": len(queue),
        "underlying_case_count": sum(row["case_count"] for row in queue),
        "underlying_receipt_slot_count": len(slots),
        "owner_roster_field_count": len(OWNER_ROSTER_FIELDS),
        "named_owner_assignment_count": 0,
        "delegate_assignment_count": 0,
        "accepted_owner_roster_count": 0,
        "received_receipt_count": 0,
        "role_accepted_receipt_count": 0,
        "accepted_route_decision_count": 0,
        "executed_case_count": 0,
        "owner_approved_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_role_handoff": 1404,
        "design_lower_bound_after_role_handoff": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }

    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "roles_13": summary["role_worklist_count"] == 13 == len(ROLE_DUTIES),
        "role_packet_assignments_58": summary["role_packet_assignment_count"] == 58,
        "role_case_assignments_406": summary["role_case_assignment_count"] == 406,
        "role_receipt_assignments_580": summary["role_receipt_slot_assignment_count"] == 580,
        "underlying_29_203_290": (
            summary["underlying_intake_item_count"],
            summary["underlying_case_count"],
            summary["underlying_receipt_slot_count"],
        ) == (29, 203, 290),
        "ten_owner_roster_fields": summary["owner_roster_field_count"] == 10,
        "two_roles_per_packet": all(
            sum(intake["source_packet_id"] in row["source_packet_ids"] for row in worklists) == 2
            for intake in queue
        ),
        "worklist_hashes_current": all(
            row["receipt_slot_id_set_sha256"] == digest_ids(row["receipt_slot_ids"]) for row in worklists
        ),
        "all_unassigned_zero": all(
            row["handoff_status"] == "UNASSIGNED_NAMED_OWNER"
            and row["named_owner_assignment_count"] == 0
            and row["delegate_assignment_count"] == 0
            and row["accepted_owner_roster_count"] == 0
            and row["received_receipt_count"] == 0
            and row["role_accepted_receipt_count"] == 0
            and row["accepted_route_decision_count"] == 0
            and row["readiness_effect"] == "ZERO"
            for row in worklists
        ),
        "execution_readiness_zero": summary["executed_case_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_role_handoff"]
        == summary["design_lower_bound_after_role_handoff"]
        == 1404,
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)

    output = {
        "artifact": "varanegar_alias_cross_lane_role_handoff_worklist_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_ROLE_SCOPED_EXTERNAL_EVIDENCE_HANDOFF_DESIGN",
            "continuation_complete": False,
            "named_person_assignment_in_scope": False,
        },
        "safety": {
            "database_connections": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "required_owner_roster_fields": OWNER_ROSTER_FIELDS,
        "role_worklists": worklists,
        "assignment_rule": "a role type becomes assigned only through a scoped, versioned, expiring owner-roster record with conflict-of-interest attestation; this artifact does not name people",
        "handoff_rule": "receipt production and review may proceed only after roster acceptance and must preserve independent review, hash pinning, redaction and gate scope",
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
                "path": "scripts/windows/build_varanegar_alias_cross_lane_role_handoff_worklist_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "Role types are work-routing abstractions and are not named owner assignments.",
            "Assignment counts intentionally duplicate packets, cases and receipt slots across the two accountable roles per packet.",
            "No external receipt, owner acceptance, operational execution, semantic closure or readiness is claimed.",
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
