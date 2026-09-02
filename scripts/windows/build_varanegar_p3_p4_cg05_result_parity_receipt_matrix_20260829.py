"""Build the CG-05 result/render/export parity receipt matrix for P3 and P4."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "sequence": "artifacts/varanegar_analysis/varanegar_p1_p4_external_evidence_activation_sequence_matrix_20260829.json",
    "sequence_checkpoint": "artifacts/varanegar_analysis/varanegar_p1_p4_external_evidence_activation_sequence_checkpoint_20260829.json",
    "receipt_matrix": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.json",
    "formula_policy": "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_matrix_20260829.json",
    "report_gate": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json",
    "p3_effect": "artifacts/varanegar_analysis/varanegar_p3_assertion_effect_family_gap_matrix_20260829.json",
    "p4_effect": "artifacts/varanegar_analysis/varanegar_p4_assertion_effect_family_gap_matrix_20260829.json",
    "p3_final": "artifacts/varanegar_analysis/varanegar_p3_final_evidence_gap_status_matrix_20260829.json",
    "p4_final": "artifacts/varanegar_analysis/varanegar_p4_final_evidence_gap_status_matrix_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

OUTPUT_DIMENSIONS = [
    {"id": "RP-15", "dimension": "command_effect_and_result_parity_are_independently_proven"},
    {"id": "RP-16", "dimension": "per_item_completion_partial_and_unknown_outcome_disposition"},
    {"id": "RP-17", "dimension": "render_pagination_layout_font_and_presentation_integrity"},
    {"id": "RP-18", "dimension": "export_schema_column_order_format_encoding_and_locale"},
    {"id": "RP-19", "dimension": "file_digest_quarantine_atomic_publish_and_source_immutability"},
    {"id": "RP-20", "dimension": "owner_fixture_acceptance_conflict_and_supersession"},
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

    policy_dimensions = documents["formula_policy"]["policy_dimensions"]
    dimensions = policy_dimensions + OUTPUT_DIMENSIONS
    dimension_ids = [dimension["id"] for dimension in dimensions]
    sequence_rows = [
        row for row in documents["sequence"]["packet_sequence"] if row["lane"] in {"P3", "P4"}
    ]
    cg05_slots_by_intake = {}
    for row in sequence_rows:
        cg05_slots_by_intake[row["intake_id"]] = sorted(
            (
                slot
                for slot in documents["receipt_matrix"]["receipt_slots"]
                if slot["intake_id"] == row["intake_id"] and "CG-05" in slot["applicable_gate_ids"]
            ),
            key=lambda slot: slot["receipt_slot_id"],
        )

    packets = []
    for index, row in enumerate(sequence_rows, 1):
        cg05_slots = cg05_slots_by_intake[row["intake_id"]]
        packets.append(
            {
                "cg05_packet_id": f"CG05-P34-{index:02d}",
                "lane": row["lane"],
                "source_packet_id": row["source_packet_id"],
                "intake_id": row["intake_id"],
                "module": row["module"],
                "newer_action_or_surface": row["newer_action_or_surface"],
                "case_count": row["case_count"],
                "required_decision_route": row["required_decision_route"],
                "accountable_role_types": row["accountable_role_types"],
                "required_parity_dimension_ids": dimension_ids,
                "cg05_receipt_slot_ids": [slot["receipt_slot_id"] for slot in cg05_slots],
                "cg05_receipt_types": [slot["receipt_type"] for slot in cg05_slots],
                "multi_class_cg05_receipt_slot_count": sum(len(slot["receipt_classes"]) > 1 for slot in cg05_slots),
                "required_parity_dimension_count": len(dimension_ids),
                "accepted_parity_dimension_count": 0,
                "explicit_not_applicable_dimension_count": 0,
                "unexplained_difference_count": 0,
                "accepted_exception_count": 0,
                "role_accepted_cg05_receipt_count": 0,
                "result_parity_proven": False,
                "render_or_export_parity_proven": False,
                "owner_approved": False,
                "current_status": "OPEN_CG05_RECEIPTS_AND_DIMENSION_DISPOSITIONS_REQUIRED",
                "readiness_effect": "ZERO",
            }
        )

    p3 = documents["p3_effect"]["summary"]
    p4 = documents["p4_effect"]["summary"]
    summary = {
        "packet_count": len(packets),
        "p3_packet_count": sum(packet["lane"] == "P3" for packet in packets),
        "p4_packet_count": sum(packet["lane"] == "P4" for packet in packets),
        "covered_case_count": sum(packet["case_count"] for packet in packets),
        "policy_dimension_count": len(policy_dimensions),
        "output_specific_dimension_count": len(OUTPUT_DIMENSIONS),
        "required_parity_dimension_count": len(dimensions),
        "required_parity_dimension_assignment_count": len(packets) * len(dimensions),
        "cg05_receipt_slot_count": sum(len(packet["cg05_receipt_slot_ids"]) for packet in packets),
        "p3_cg05_receipt_slot_count": sum(len(packet["cg05_receipt_slot_ids"]) for packet in packets if packet["lane"] == "P3"),
        "p4_cg05_receipt_slot_count": sum(len(packet["cg05_receipt_slot_ids"]) for packet in packets if packet["lane"] == "P4"),
        "multi_class_cg05_receipt_slot_count": sum(packet["multi_class_cg05_receipt_slot_count"] for packet in packets),
        "candidate_case_pair_count": p3["candidate_case_pair_count"] + p4["candidate_case_pair_count"],
        "exact_effect_family_set_pair_count": p3["exact_family_set_pair_count"] + p4["exact_family_set_pair_count"],
        "newer_file_or_artifact_receipt_pair_count": p3["newer_file_or_artifact_receipt_pair_count"] + p4["newer_file_or_artifact_receipt_pair_count"],
        "baseline_file_or_artifact_receipt_pair_count": p3["baseline_file_or_artifact_receipt_pair_count"] + p4["baseline_file_or_artifact_receipt_pair_count"],
        "newer_render_or_export_completion_pair_count": p3["newer_render_or_print_completion_pair_count"] + p4["newer_render_or_export_completion_pair_count"],
        "baseline_render_or_export_completion_pair_count": p3["baseline_render_or_print_completion_pair_count"] + p4["baseline_render_or_export_completion_pair_count"],
        "newer_per_item_partial_outcome_pair_count": p3["newer_per_item_partial_outcome_pair_count"] + p4["newer_per_item_partial_outcome_pair_count"],
        "baseline_per_item_partial_outcome_pair_count": p3["baseline_per_item_partial_outcome_pair_count"] + p4["baseline_per_item_partial_outcome_pair_count"],
        "newer_result_or_content_parity_pair_count": p3["newer_result_or_content_parity_pair_count"] + p4["newer_result_or_content_parity_pair_count"],
        "baseline_result_or_content_parity_pair_count": p3["baseline_result_or_content_parity_pair_count"] + p4["baseline_result_or_content_parity_pair_count"],
        "accepted_parity_dimension_count": 0,
        "explicit_not_applicable_dimension_count": 0,
        "role_accepted_cg05_receipt_count": 0,
        "result_parity_proven_packet_count": 0,
        "render_or_export_parity_proven_packet_count": 0,
        "owner_approved_packet_count": 0,
        "executed_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_cg05_matrix": 1404,
        "design_lower_bound_after_cg05_matrix": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }

    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "packets_8_p3_5_p4_3_cases_56": (
            summary["packet_count"],
            summary["p3_packet_count"],
            summary["p4_packet_count"],
            summary["covered_case_count"],
        ) == (8, 5, 3, 56),
        "dimensions_14_plus_6_equals_20_assignments_160": (
            summary["policy_dimension_count"],
            summary["output_specific_dimension_count"],
            summary["required_parity_dimension_count"],
            summary["required_parity_dimension_assignment_count"],
        ) == (14, 6, 20, 160),
        "cg05_slots_27_p3_15_p4_12_multi_5": (
            summary["cg05_receipt_slot_count"],
            summary["p3_cg05_receipt_slot_count"],
            summary["p4_cg05_receipt_slot_count"],
            summary["multi_class_cg05_receipt_slot_count"],
        ) == (27, 15, 12, 5),
        "per_packet_cg05_slot_count": all(
            len(packet["cg05_receipt_slot_ids"]) == (3 if packet["lane"] == "P3" else 4)
            for packet in packets
        ),
        "candidate_pairs_52_effect_exact_0": (
            summary["candidate_case_pair_count"],
            summary["exact_effect_family_set_pair_count"],
        ) == (52, 0),
        "file_new_52_base_18": (
            summary["newer_file_or_artifact_receipt_pair_count"],
            summary["baseline_file_or_artifact_receipt_pair_count"],
        ) == (52, 18),
        "render_new_52_base_2": (
            summary["newer_render_or_export_completion_pair_count"],
            summary["baseline_render_or_export_completion_pair_count"],
        ) == (52, 2),
        "per_item_new_52_base_0": (
            summary["newer_per_item_partial_outcome_pair_count"],
            summary["baseline_per_item_partial_outcome_pair_count"],
        ) == (52, 0),
        "result_parity_new_0_base_6": (
            summary["newer_result_or_content_parity_pair_count"],
            summary["baseline_result_or_content_parity_pair_count"],
        ) == (0, 6),
        "all_open_zero": all(
            packet["accepted_parity_dimension_count"] == 0
            and packet["role_accepted_cg05_receipt_count"] == 0
            and packet["result_parity_proven"] is False
            and packet["render_or_export_parity_proven"] is False
            and packet["owner_approved"] is False
            and packet["current_status"] == "OPEN_CG05_RECEIPTS_AND_DIMENSION_DISPOSITIONS_REQUIRED"
            and packet["readiness_effect"] == "ZERO"
            for packet in packets
        ),
        "execution_readiness_zero": summary["result_parity_proven_packet_count"]
        == summary["render_or_export_parity_proven_packet_count"]
        == summary["owner_approved_packet_count"]
        == summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_cg05_matrix"]
        == summary["design_lower_bound_after_cg05_matrix"]
        == 1404,
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)

    output = {
        "artifact": "varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_P3_P4_CG05_RESULT_RENDER_EXPORT_PARITY_DESIGN",
            "continuation_complete": False,
            "runtime_result_parity_observed": False,
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
        "parity_dimensions": dimensions,
        "cg05_packets": packets,
        "dimension_disposition_rule": "every dimension requires accepted evidence or an explicit owner-approved not-applicable disposition; missing, defaulted or inferred dimensions remain open",
        "cg05_closure_rule": "CG-05 closes per packet only after all applicable dimensions and all CG-05 receipt slots are accepted with zero unexplained differences or approved, versioned exceptions",
        "misclassification_guard": "command effect, print completion, export creation and file existence are not substitutes for frozen-fixture value, rowset, formula, render or file-content parity",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "The 160 dimension assignments are non-additive refinements, not new Golden/UAT cases.",
            "No frozen business values, report outputs, export files or owner identities are persisted.",
            "No result parity, render/export parity, execution, owner approval or readiness is claimed.",
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
