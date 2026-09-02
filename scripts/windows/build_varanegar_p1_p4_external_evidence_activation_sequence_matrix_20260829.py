"""Build the read-only external-evidence activation sequence for lanes P1-P4."""
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
    "p0_activation": "artifacts/varanegar_analysis/varanegar_p0_external_evidence_collection_activation_packets_20260829.json",
    "p0_checkpoint": "artifacts/varanegar_analysis/varanegar_p0_external_evidence_collection_activation_checkpoint_20260829.json",
    "gate_matrix": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

LANE_DEFINITIONS = {
    "P1": {
        "sequence_rank": 1,
        "lane_name": "FINANCIAL_STATE_TRANSITION",
        "sequencing_rationale": "financial state changes and cancellation/matching transitions precede policy and presentation lanes",
        "dependency_lane_ids": ["P0"],
    },
    "P2": {
        "sequence_rank": 2,
        "lane_name": "POLICY_AND_INTEGRATION_INPUT",
        "sequencing_rationale": "versioned pricing policy and replication inputs follow irreversible/state-transition evidence",
        "dependency_lane_ids": ["P0", "P1"],
    },
    "P3": {
        "sequence_rank": 3,
        "lane_name": "STATEFUL_REPORT_COMMAND",
        "sequencing_rationale": "report commands require command-effect receipts plus the independent CG-05 result/render parity lane",
        "dependency_lane_ids": ["P0", "P1", "P2"],
    },
    "P4": {
        "sequence_rank": 4,
        "lane_name": "READ_ONLY_EXPORT",
        "sequencing_rationale": "exports may collect evidence in parallel but cannot close before CG-05 value/file parity and source-immutability receipts",
        "dependency_lane_ids": ["P3"],
    },
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

    queue = [row for row in documents["queue"]["intake_queue"] if row["lane"] in LANE_DEFINITIONS]
    queue.sort(key=lambda row: (LANE_DEFINITIONS[row["lane"]]["sequence_rank"], row["source_packet_id"]))
    slots_by_intake = Counter(
        slot["intake_id"]
        for slot in documents["receipt_matrix"]["receipt_slots"]
        if slot["lane"] in LANE_DEFINITIONS
    )
    cross_by_id = {
        row["cross_lane_status_id"]: row for row in documents["cross_lane"]["cross_lane_packet_routes"]
    }

    packet_sequence = []
    for index, intake in enumerate(queue, 1):
        route = cross_by_id[intake["cross_lane_status_id"]]
        lane_definition = LANE_DEFINITIONS[intake["lane"]]
        packet_sequence.append(
            {
                "sequence_item_id": f"P1P4-EAS-{index:02d}",
                "lane": intake["lane"],
                "sequence_rank": lane_definition["sequence_rank"],
                "source_packet_id": intake["source_packet_id"],
                "intake_id": intake["intake_id"],
                "cross_lane_status_id": intake["cross_lane_status_id"],
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
                "receipt_slot_count": slots_by_intake[intake["intake_id"]],
                "requires_cg05_result_parity": "CG-05" in intake["required_gate_ids"],
                "required_activation_prerequisites": ACTIVATION_PREREQUISITES,
                "missing_named_owner_assignment_count": len(intake["accountable_role_types"]),
                "missing_role_accepted_receipt_count": slots_by_intake[intake["intake_id"]],
                "open_gate_count": len(intake["required_gate_ids"]),
                "accepted_prerequisite_count": 0,
                "activated_for_evidence_collection": False,
                "operational_execution_authorized": False,
                "accepted_route_decision_count": 0,
                "executed_case_count": 0,
                "owner_approved_case_count": 0,
                "readiness_effect": "ZERO",
            }
        )

    lane_sequence = []
    for lane, definition in LANE_DEFINITIONS.items():
        rows = [row for row in packet_sequence if row["lane"] == lane]
        routes = Counter(row["required_decision_route"] for row in rows)
        lane_sequence.append(
            {
                "lane": lane,
                **definition,
                "packet_count": len(rows),
                "case_count": sum(row["case_count"] for row in rows),
                "candidate_bearing_packet_count": sum(row["candidate_baseline_action_count"] > 0 for row in rows),
                "explicit_none_packet_count": sum(row["candidate_baseline_action_count"] == 0 for row in rows),
                "alias_or_new_action_packet_count": routes["EXTERNAL_ALIAS_OR_NEW_ACTION_DECISION_REQUIRED"],
                "semantic_equivalence_packet_count": routes["EXTERNAL_SEMANTIC_EQUIVALENCE_DECISION_REQUIRED"],
                "report_effect_and_result_packet_count": routes["EXTERNAL_SEMANTIC_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
                "export_effect_and_result_packet_count": routes["EXTERNAL_EXPORT_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
                "same_kind_case_pair_count": sum(row["same_kind_case_pair_count"] for row in rows),
                "failure_injection_pair_count": sum(row["failure_injection_pair_count"] for row in rows),
                "control_pair_count": sum(row["control_pair_count"] for row in rows),
                "receipt_slot_count": sum(row["receipt_slot_count"] for row in rows),
                "accountable_role_assignment_count": sum(len(row["accountable_role_types"]) for row in rows),
                "gate_assignment_count": sum(len(row["required_gate_ids"]) for row in rows),
                "cg05_packet_count": sum(row["requires_cg05_result_parity"] for row in rows),
                "activated_packet_count": 0,
                "accepted_route_decision_count": 0,
            }
        )
    lane_sequence.sort(key=lambda row: row["sequence_rank"])

    route_counts = Counter(row["required_decision_route"] for row in packet_sequence)
    distinct_roles = sorted({role for row in packet_sequence for role in row["accountable_role_types"]})
    summary = {
        "lane_count": len(lane_sequence),
        "sequence_item_count": len(packet_sequence),
        "covered_case_count": sum(row["case_count"] for row in packet_sequence),
        "candidate_bearing_packet_count": sum(row["candidate_baseline_action_count"] > 0 for row in packet_sequence),
        "explicit_none_packet_count": sum(row["candidate_baseline_action_count"] == 0 for row in packet_sequence),
        "alias_or_new_action_packet_count": route_counts["EXTERNAL_ALIAS_OR_NEW_ACTION_DECISION_REQUIRED"],
        "semantic_equivalence_packet_count": route_counts["EXTERNAL_SEMANTIC_EQUIVALENCE_DECISION_REQUIRED"],
        "report_effect_and_result_packet_count": route_counts["EXTERNAL_SEMANTIC_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
        "export_effect_and_result_packet_count": route_counts["EXTERNAL_EXPORT_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
        "same_kind_case_pair_count": sum(row["same_kind_case_pair_count"] for row in packet_sequence),
        "failure_injection_pair_count": sum(row["failure_injection_pair_count"] for row in packet_sequence),
        "control_pair_count": sum(row["control_pair_count"] for row in packet_sequence),
        "outcome_exact_pair_count": documents["cross_lane"]["summary"]["outcome_exact_pair_count"]
        - documents["p0_activation"]["summary"]["outcome_exact_pair_count"],
        "fully_exact_pair_count": 0,
        "exact_effect_family_set_pair_count": 0,
        "receipt_slot_count": sum(row["receipt_slot_count"] for row in packet_sequence),
        "accountable_role_assignment_count": sum(len(row["accountable_role_types"]) for row in packet_sequence),
        "distinct_accountable_role_type_count": len(distinct_roles),
        "gate_assignment_count": sum(len(row["required_gate_ids"]) for row in packet_sequence),
        "cg05_result_parity_packet_count": sum(row["requires_cg05_result_parity"] for row in packet_sequence),
        "activation_prerequisite_assignment_count": len(packet_sequence) * len(ACTIVATION_PREREQUISITES),
        "named_owner_assignment_count": 0,
        "role_accepted_receipt_count": 0,
        "accepted_prerequisite_count": 0,
        "activated_packet_count": 0,
        "accepted_route_decision_count": 0,
        "executed_case_count": 0,
        "owner_approved_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_p1_p4_sequence": 1404,
        "design_lower_bound_after_p1_p4_sequence": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }

    lane_tuple = [
        (row["packet_count"], row["case_count"], row["receipt_slot_count"], row["accountable_role_assignment_count"], row["gate_assignment_count"])
        for row in lane_sequence
    ]
    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "lanes_4_packets_22_cases_154": (summary["lane_count"], summary["sequence_item_count"], summary["covered_case_count"]) == (4, 22, 154),
        "candidate_17_none_5": (summary["candidate_bearing_packet_count"], summary["explicit_none_packet_count"]) == (17, 5),
        "routes_5_9_5_3": (
            summary["alias_or_new_action_packet_count"],
            summary["semantic_equivalence_packet_count"],
            summary["report_effect_and_result_packet_count"],
            summary["export_effect_and_result_packet_count"],
        ) == (5, 9, 5, 3),
        "pairs_180_58_122": (
            summary["same_kind_case_pair_count"],
            summary["failure_injection_pair_count"],
            summary["control_pair_count"],
        ) == (180, 58, 122),
        "exactness_2_0_0": (
            summary["outcome_exact_pair_count"],
            summary["fully_exact_pair_count"],
            summary["exact_effect_family_set_pair_count"],
        ) == (2, 0, 0),
        "slots_roles_gates_220_44_115": (
            summary["receipt_slot_count"],
            summary["accountable_role_assignment_count"],
            summary["gate_assignment_count"],
        ) == (220, 44, 115),
        "distinct_roles_12_cg05_packets_8": (
            summary["distinct_accountable_role_type_count"],
            summary["cg05_result_parity_packet_count"],
        ) == (12, 8),
        "lane_partition": lane_tuple == [(8, 56, 80, 16, 40), (6, 42, 60, 12, 30), (5, 35, 50, 10, 30), (3, 21, 30, 6, 15)],
        "ten_receipts_each": all(row["receipt_slot_count"] == 10 for row in packet_sequence),
        "cg05_only_p3_p4": all(row["requires_cg05_result_parity"] == (row["lane"] in {"P3", "P4"}) for row in packet_sequence),
        "all_not_activated_zero": all(
            row["missing_named_owner_assignment_count"] == 2
            and row["missing_role_accepted_receipt_count"] == 10
            and row["accepted_prerequisite_count"] == 0
            and row["activated_for_evidence_collection"] is False
            and row["operational_execution_authorized"] is False
            and row["accepted_route_decision_count"] == 0
            and row["executed_case_count"] == 0
            and row["owner_approved_case_count"] == 0
            and row["readiness_effect"] == "ZERO"
            for row in packet_sequence
        ),
        "execution_readiness_zero": summary["activated_packet_count"]
        == summary["accepted_route_decision_count"]
        == summary["executed_case_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_p1_p4_sequence"]
        == summary["design_lower_bound_after_p1_p4_sequence"]
        == 1404,
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)

    output = {
        "artifact": "varanegar_p1_p4_external_evidence_activation_sequence_matrix_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_P1_P4_EXTERNAL_EVIDENCE_ACTIVATION_SEQUENCE_DESIGN",
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
        "lane_sequence": lane_sequence,
        "packet_sequence": packet_sequence,
        "sequencing_rule": "sequence ranks express risk-first review order; redacted evidence collection may run in parallel after roster and gate prerequisites, but closure cannot bypass dependency lanes or applicable gate acceptance",
        "p3_p4_result_parity_rule": "all eight P3/P4 packets require CG-05 in addition to effect/file receipts; command success or export creation cannot substitute for frozen-fixture value/render parity",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_p1_p4_external_evidence_activation_sequence_matrix_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "Sequence ordering does not authorize evidence collection or operational execution by itself.",
            "P4 export evidence may be collected in parallel, but CG-05 result parity remains mandatory for closure.",
            "No named owner, accepted receipt, activated packet, route decision, execution or readiness promotion exists.",
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
