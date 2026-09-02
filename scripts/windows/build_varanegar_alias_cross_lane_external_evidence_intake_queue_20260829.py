"""Build the external-evidence intake queue for the 29 open alias routes."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "cross_lane": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_closure_route_matrix_20260829.json",
    "owner_packets": "artifacts/varanegar_analysis/varanegar_action_alias_owner_evidence_packet_matrix_20260829.json",
    "priority": "artifacts/varanegar_analysis/varanegar_action_alias_handoff_priority_matrix_20260829.json",
    "report_gate": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json",
    "terminal_gate": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_contract_20260829.json",
    "gate_matrix": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

COMMON_RECEIPTS = [
    "frozen_case_set_hash_receipt",
    "candidate_or_explicit_none_disposition_receipt",
    "precondition_and_policy_version_receipt",
    "outcome_vocabulary_mapping_receipt",
    "accountable_role_receipt",
    "conflict_and_supersession_receipt",
]

ROUTE_DEFINITIONS = {
    "EXTERNAL_ALIAS_OR_NEW_ACTION_DECISION_REQUIRED": {
        "route_group": "ALIAS_OR_NEW_ACTION_CLASSIFICATION",
        "required_gate_ids": ["CG-06", "CG-01", "CG-02", "CG-03", "CG-04"],
        "required_evidence_receipts": COMMON_RECEIPTS
        + [
            "explicit_alias_new_action_or_reject_decision_receipt",
            "authorization_and_denial_receipt",
            "transaction_or_source_immutability_receipt",
            "success_failure_and_retry_effect_receipt",
        ],
        "acceptance_rule": "accept only an explicit alias, new-action, or rejected mapping decision plus applicable isolated receipts and accountable-role approval",
    },
    "EXTERNAL_SEMANTIC_EQUIVALENCE_DECISION_REQUIRED": {
        "route_group": "SEMANTIC_EQUIVALENCE_ADJUDICATION",
        "required_gate_ids": ["CG-06", "CG-01", "CG-02", "CG-03", "CG-04"],
        "required_evidence_receipts": COMMON_RECEIPTS
        + [
            "candidate_pair_disposition_receipt",
            "assertion_and_effect_family_receipt",
            "failure_stage_and_retry_receipt",
            "transaction_or_source_immutability_receipt",
        ],
        "acceptance_rule": "accept only a pair-level equivalent, partial, distinct, or rejected disposition supported by precondition, outcome, effect, failure-stage and applicable transaction evidence",
    },
    "EXTERNAL_SEMANTIC_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED": {
        "route_group": "REPORT_COMMAND_EFFECT_AND_RESULT_PARITY",
        "required_gate_ids": ["CG-06", "CG-01", "CG-02", "CG-03", "CG-05", "CG-04"],
        "required_evidence_receipts": COMMON_RECEIPTS
        + [
            "command_state_and_effect_receipt",
            "failure_stage_and_per_item_outcome_receipt",
            "frozen_fixture_value_and_rowset_parity_receipt",
            "render_file_and_presentation_integrity_receipt",
        ],
        "acceptance_rule": "accept only when command effects and frozen-fixture result/render parity are independently evidenced and the report and business-control roles approve",
    },
    "EXTERNAL_EXPORT_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED": {
        "route_group": "EXPORT_EFFECT_AND_RESULT_PARITY",
        "required_gate_ids": ["CG-06", "CG-01", "CG-03", "CG-05", "CG-04"],
        "required_evidence_receipts": COMMON_RECEIPTS
        + [
            "frozen_input_and_query_identity_receipt",
            "export_schema_order_format_encoding_receipt",
            "export_file_digest_and_source_immutability_receipt",
            "frozen_fixture_result_parity_receipt",
        ],
        "acceptance_rule": "accept only when frozen inputs, result values, export schema/order/format/encoding, file digest and source immutability are evidenced and approved",
    },
}


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
    cross_lane = documents["cross_lane"]
    owner_by_packet = {
        row["packet_id"]: row for row in documents["owner_packets"]["action_alias_packets"]
    }
    priority_by_packet = {
        row["source_packet_id"]: row for row in documents["priority"]["handoff_packets"]
    }
    known_gate_ids = {
        row["gate_id"] for row in documents["gate_matrix"]["gate_handoff_matrix"]
    }

    queue = []
    for index, route in enumerate(cross_lane["cross_lane_packet_routes"], 1):
        packet_id = route["source_packet_id"]
        owner = owner_by_packet[packet_id]
        priority = priority_by_packet[packet_id]
        definition = ROUTE_DEFINITIONS[route["required_decision_route"]]
        queue.append(
            {
                "intake_id": f"AEI-{index:02d}",
                "cross_lane_status_id": route["cross_lane_status_id"],
                "source_packet_id": packet_id,
                "lane": route["lane"],
                "review_priority_lane": priority["review_priority_lane"],
                "priority_rank": priority["priority_rank"],
                "module": route["module"],
                "newer_action_or_surface": route["newer_action_or_surface"],
                "case_count": route["case_count"],
                "candidate_baseline_action_count": route["candidate_baseline_action_count"],
                "required_decision_route": route["required_decision_route"],
                "route_group": definition["route_group"],
                "required_gate_ids": definition["required_gate_ids"],
                "accountable_role_types": owner["accountable_role_types"],
                "required_evidence_receipts": definition["required_evidence_receipts"],
                "acceptance_rule": definition["acceptance_rule"],
                "intake_status": "OPEN_EXTERNAL_EVIDENCE_REQUIRED",
                "named_owner_assignment_count": 0,
                "received_evidence_receipt_count": 0,
                "accepted_evidence_receipt_count": 0,
                "accepted_route_decision_count": 0,
                "accepted_case_disposition_count": 0,
                "executed_case_count": 0,
                "owner_approved_case_count": 0,
                "counting_effect": "ZERO",
            }
        )

    route_counts = Counter(row["required_decision_route"] for row in queue)
    route_case_counts = Counter()
    receipt_assignments = Counter()
    gate_assignments = Counter()
    for row in queue:
        route_case_counts[row["required_decision_route"]] += row["case_count"]
        receipt_assignments[row["required_decision_route"]] += len(row["required_evidence_receipts"])
        gate_assignments[row["required_decision_route"]] += len(row["required_gate_ids"])

    route_groups = []
    for route_name, definition in ROUTE_DEFINITIONS.items():
        route_groups.append(
            {
                "required_decision_route": route_name,
                "route_group": definition["route_group"],
                "packet_count": route_counts[route_name],
                "case_count": route_case_counts[route_name],
                "required_gate_ids": definition["required_gate_ids"],
                "required_evidence_receipts": definition["required_evidence_receipts"],
                "required_receipt_assignment_count": receipt_assignments[route_name],
                "required_gate_assignment_count": gate_assignments[route_name],
                "accepted_packet_count": 0,
                "accepted_case_disposition_count": 0,
            }
        )

    summary = {
        "queue_item_count": len(queue),
        "covered_case_count": sum(row["case_count"] for row in queue),
        "route_group_count": len(route_groups),
        "alias_or_new_action_packet_count": route_counts["EXTERNAL_ALIAS_OR_NEW_ACTION_DECISION_REQUIRED"],
        "semantic_equivalence_packet_count": route_counts["EXTERNAL_SEMANTIC_EQUIVALENCE_DECISION_REQUIRED"],
        "report_effect_and_result_parity_packet_count": route_counts["EXTERNAL_SEMANTIC_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
        "export_effect_and_result_parity_packet_count": route_counts["EXTERNAL_EXPORT_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
        "alias_or_new_action_case_count": route_case_counts["EXTERNAL_ALIAS_OR_NEW_ACTION_DECISION_REQUIRED"],
        "semantic_equivalence_case_count": route_case_counts["EXTERNAL_SEMANTIC_EQUIVALENCE_DECISION_REQUIRED"],
        "report_effect_and_result_parity_case_count": route_case_counts["EXTERNAL_SEMANTIC_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
        "export_effect_and_result_parity_case_count": route_case_counts["EXTERNAL_EXPORT_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
        "accountable_role_assignment_count": sum(len(row["accountable_role_types"]) for row in queue),
        "required_evidence_receipt_assignment_count": sum(len(row["required_evidence_receipts"]) for row in queue),
        "required_gate_assignment_count": sum(len(row["required_gate_ids"]) for row in queue),
        "named_owner_assignment_count": 0,
        "received_evidence_receipt_count": 0,
        "accepted_evidence_receipt_count": 0,
        "accepted_route_decision_count": 0,
        "accepted_case_disposition_count": 0,
        "executed_case_count": 0,
        "owner_approved_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_intake_queue": 1404,
        "design_lower_bound_after_intake_queue": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }

    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "queue_29_cases_203": (summary["queue_item_count"], summary["covered_case_count"]) == (29, 203),
        "four_route_groups": summary["route_group_count"] == 4,
        "route_packets_9_12_5_3": (
            summary["alias_or_new_action_packet_count"],
            summary["semantic_equivalence_packet_count"],
            summary["report_effect_and_result_parity_packet_count"],
            summary["export_effect_and_result_parity_packet_count"],
        ) == (9, 12, 5, 3),
        "route_cases_63_84_35_21": (
            summary["alias_or_new_action_case_count"],
            summary["semantic_equivalence_case_count"],
            summary["report_effect_and_result_parity_case_count"],
            summary["export_effect_and_result_parity_case_count"],
        ) == (63, 84, 35, 21),
        "packet_join_complete": len(owner_by_packet) == len(priority_by_packet) == len(queue) == 29,
        "roles_58": summary["accountable_role_assignment_count"] == 58,
        "gates_known": all(set(row["required_gate_ids"]) <= known_gate_ids for row in queue),
        "all_intake_open_zero": all(
            row["intake_status"] == "OPEN_EXTERNAL_EVIDENCE_REQUIRED"
            and row["named_owner_assignment_count"] == 0
            and row["received_evidence_receipt_count"] == 0
            and row["accepted_evidence_receipt_count"] == 0
            and row["accepted_route_decision_count"] == 0
            and row["accepted_case_disposition_count"] == 0
            and row["executed_case_count"] == 0
            and row["owner_approved_case_count"] == 0
            and row["counting_effect"] == "ZERO"
            for row in queue
        ),
        "report_routes_use_cg05": all(
            "CG-05" in row["required_gate_ids"]
            for row in queue
            if row["route_group"] in {"REPORT_COMMAND_EFFECT_AND_RESULT_PARITY", "EXPORT_EFFECT_AND_RESULT_PARITY"}
        ),
        "execution_readiness_zero": summary["executed_case_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_intake_queue"]
        == summary["design_lower_bound_after_intake_queue"]
        == 1404,
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)

    output = {
        "artifact": "varanegar_alias_cross_lane_external_evidence_intake_queue_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_EXTERNAL_EVIDENCE_INTAKE_DESIGN",
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
        "route_group_definitions": route_groups,
        "intake_queue": queue,
        "intake_order_rule": "priority_rank ascending, then source packet id; external evidence may be received independently but no route closes until every applicable receipt and role approval is accepted",
        "promotion_rule": "the queue is routing-only and contributes zero readiness or design-count promotion until accepted evidence is independently validated through the referenced gates",
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
                "path": "scripts/windows/build_varanegar_alias_cross_lane_external_evidence_intake_queue_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This queue assigns accountable role types, not named people or accepted ownership.",
            "Receipt definitions are evidence-intake requirements, not authorization to execute legacy or target operations.",
            "No semantic equivalence, result parity, UAT execution, owner acceptance, command readiness or pilot readiness is claimed.",
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
