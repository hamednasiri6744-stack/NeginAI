"""Build read-only evidence-collection activation packets for the seven P0 routes."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "queue": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_external_evidence_intake_queue_20260829.json",
    "receipt_matrix": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.json",
    "role_handoff": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_role_handoff_worklist_20260829.json",
    "cross_lane": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_closure_route_matrix_20260829.json",
    "p0_final": "artifacts/varanegar_analysis/varanegar_p0_final_evidence_gap_status_matrix_20260829.json",
    "gate_matrix": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_role_handoff_checkpoint_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

ACTIVATION_PREREQUISITES = [
    "two_scoped_owner_roster_records_accepted",
    "case_set_hash_and_candidate_disposition_pinned",
    "policy_version_and_expiry_pinned",
    "ten_receipt_slots_role_accepted",
    "applicable_gate_scope_validated",
    "conflict_and_supersession_cleared",
    "route_decision_independently_accepted",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = {name: ROOT / value for name, value in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    p0_queue = sorted(
        (row for row in documents["queue"]["intake_queue"] if row["lane"] == "P0"),
        key=lambda row: row["source_packet_id"],
    )
    slots_by_intake = {}
    for intake in p0_queue:
        slots_by_intake[intake["intake_id"]] = sorted(
            (
                slot
                for slot in documents["receipt_matrix"]["receipt_slots"]
                if slot["intake_id"] == intake["intake_id"]
            ),
            key=lambda slot: slot["receipt_slot_id"],
        )
    cross_lane_by_id = {
        row["cross_lane_status_id"]: row for row in documents["cross_lane"]["cross_lane_packet_routes"]
    }

    packets = []
    for index, intake in enumerate(p0_queue, 1):
        route = cross_lane_by_id[intake["cross_lane_status_id"]]
        receipt_slots = slots_by_intake[intake["intake_id"]]
        packets.append(
            {
                "activation_packet_id": f"P0-ECA-{index:02d}",
                "intake_id": intake["intake_id"],
                "cross_lane_status_id": intake["cross_lane_status_id"],
                "source_packet_id": intake["source_packet_id"],
                "module": intake["module"],
                "newer_action_or_surface": intake["newer_action_or_surface"],
                "required_decision_route": intake["required_decision_route"],
                "case_count": intake["case_count"],
                "candidate_baseline_action_count": intake["candidate_baseline_action_count"],
                "same_kind_case_pair_count": route["same_kind_case_pair_count"],
                "failure_injection_pair_count": route["failure_injection_pair_count"],
                "control_pair_count": route["control_pair_count"],
                "accountable_role_types": intake["accountable_role_types"],
                "required_gate_ids": intake["required_gate_ids"],
                "receipt_slot_ids": [slot["receipt_slot_id"] for slot in receipt_slots],
                "required_activation_prerequisites": ACTIVATION_PREREQUISITES,
                "missing_named_owner_assignment_count": len(intake["accountable_role_types"]),
                "missing_role_accepted_receipt_count": len(receipt_slots),
                "open_gate_count": len(intake["required_gate_ids"]),
                "accepted_prerequisite_count": 0,
                "accepted_route_decision_count": 0,
                "evidence_collection_activation_status": "NOT_ACTIVATED_EXTERNAL_EVIDENCE_MISSING",
                "operational_execution_authorized": False,
                "executed_case_count": 0,
                "owner_approved_case_count": 0,
                "readiness_effect": "ZERO",
            }
        )

    routes = Counter(packet["required_decision_route"] for packet in packets)
    distinct_roles = sorted({role for packet in packets for role in packet["accountable_role_types"]})
    p0_summary = documents["p0_final"]["summary"]
    summary = {
        "activation_packet_count": len(packets),
        "covered_case_count": sum(packet["case_count"] for packet in packets),
        "candidate_bearing_packet_count": sum(packet["candidate_baseline_action_count"] > 0 for packet in packets),
        "explicit_none_packet_count": sum(packet["candidate_baseline_action_count"] == 0 for packet in packets),
        "alias_or_new_action_packet_count": routes["EXTERNAL_ALIAS_OR_NEW_ACTION_DECISION_REQUIRED"],
        "semantic_equivalence_packet_count": routes["EXTERNAL_SEMANTIC_EQUIVALENCE_DECISION_REQUIRED"],
        "same_kind_case_pair_count": sum(packet["same_kind_case_pair_count"] for packet in packets),
        "failure_injection_pair_count": sum(packet["failure_injection_pair_count"] for packet in packets),
        "control_pair_count": sum(packet["control_pair_count"] for packet in packets),
        "outcome_exact_pair_count": p0_summary["outcome_exact_pair_count"],
        "fully_exact_pair_count": p0_summary["fully_exact_pair_count"],
        "exact_effect_family_set_pair_count": p0_summary["exact_effect_family_set_pair_count"],
        "receipt_slot_count": sum(len(packet["receipt_slot_ids"]) for packet in packets),
        "accountable_role_assignment_count": sum(len(packet["accountable_role_types"]) for packet in packets),
        "distinct_accountable_role_type_count": len(distinct_roles),
        "gate_assignment_count": sum(len(packet["required_gate_ids"]) for packet in packets),
        "activation_prerequisite_assignment_count": len(packets) * len(ACTIVATION_PREREQUISITES),
        "named_owner_assignment_count": 0,
        "role_accepted_receipt_count": 0,
        "accepted_prerequisite_count": 0,
        "activated_packet_count": 0,
        "accepted_route_decision_count": 0,
        "executed_case_count": 0,
        "owner_approved_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_p0_activation": 1404,
        "design_lower_bound_after_p0_activation": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }

    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "p0_7_cases_49": (summary["activation_packet_count"], summary["covered_case_count"]) == (7, 49),
        "candidate_3_none_4": (summary["candidate_bearing_packet_count"], summary["explicit_none_packet_count"]) == (3, 4),
        "routes_4_3": (summary["alias_or_new_action_packet_count"], summary["semantic_equivalence_packet_count"]) == (4, 3),
        "pairs_66_20_46": (
            summary["same_kind_case_pair_count"],
            summary["failure_injection_pair_count"],
            summary["control_pair_count"],
        ) == (66, 20, 46),
        "exactness_2_0_0": (
            summary["outcome_exact_pair_count"],
            summary["fully_exact_pair_count"],
            summary["exact_effect_family_set_pair_count"],
        ) == (2, 0, 0),
        "slots_70_roles_14_distinct_7_gates_35": (
            summary["receipt_slot_count"],
            summary["accountable_role_assignment_count"],
            summary["distinct_accountable_role_type_count"],
            summary["gate_assignment_count"],
        ) == (70, 14, 7, 35),
        "ten_receipts_per_packet": all(len(packet["receipt_slot_ids"]) == 10 for packet in packets),
        "five_gates_per_packet": all(len(packet["required_gate_ids"]) == 5 for packet in packets),
        "all_not_activated_zero": all(
            packet["evidence_collection_activation_status"] == "NOT_ACTIVATED_EXTERNAL_EVIDENCE_MISSING"
            and packet["missing_named_owner_assignment_count"] == 2
            and packet["missing_role_accepted_receipt_count"] == 10
            and packet["open_gate_count"] == 5
            and packet["accepted_prerequisite_count"] == 0
            and packet["accepted_route_decision_count"] == 0
            and packet["operational_execution_authorized"] is False
            and packet["executed_case_count"] == 0
            and packet["owner_approved_case_count"] == 0
            and packet["readiness_effect"] == "ZERO"
            for packet in packets
        ),
        "execution_readiness_zero": summary["activated_packet_count"]
        == summary["accepted_route_decision_count"]
        == summary["executed_case_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_p0_activation"]
        == summary["design_lower_bound_after_p0_activation"]
        == 1404,
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)

    output = {
        "artifact": "varanegar_p0_external_evidence_collection_activation_packets_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_P0_EXTERNAL_EVIDENCE_COLLECTION_ACTIVATION_DESIGN",
            "continuation_complete": False,
            "operational_execution_in_scope": False,
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
        "distinct_accountable_role_types": distinct_roles,
        "activation_prerequisites": ACTIVATION_PREREQUISITES,
        "activation_packets": packets,
        "activation_rule": "evidence collection may be activated only after scoped owner rosters are accepted; no operational command, form, report or procedure execution is authorized by this packet",
        "closure_rule": "all ten receipt slots, five gate scopes, conflict/supersession checks and independent route decision must be accepted before any P0 semantic closure is considered",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_p0_external_evidence_collection_activation_packets_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "Activation means permission to collect externally supplied, redacted evidence; it does not authorize operational execution.",
            "Two exact outcome labels do not prove full semantic or effect equivalence.",
            "All named owners, receipts, route decisions, executions, owner approvals and readiness promotions remain absent.",
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
