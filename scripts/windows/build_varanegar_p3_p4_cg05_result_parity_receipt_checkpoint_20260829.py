"""Checkpoint the P3/P4 CG-05 result parity receipt matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "matrix": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_p1_p4_external_evidence_activation_sequence_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_p3_p4_cg05_result_parity_receipt_checkpoint_20260829.py",
    "test": "tests/test_varanegar_p3_p4_cg05_result_parity_receipt_matrix.py",
    "checkpoint_test": "tests/test_varanegar_p3_p4_cg05_result_parity_receipt_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/P3_P4_CG05_RESULT_PARITY_RECEIPT_MATRIX_20260829_FA.md",
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
    matrix = load(paths["matrix"])
    previous = load(paths["previous"])
    summary = matrix["summary"]
    checks = {
        "sources_pass": matrix["validation"] == previous["validation"] == "PASS",
        "packets_8_p3_5_p4_3_cases_56": (
            summary["packet_count"],
            summary["p3_packet_count"],
            summary["p4_packet_count"],
            summary["covered_case_count"],
        ) == (8, 5, 3, 56),
        "dimensions_20_assignments_160": (
            summary["required_parity_dimension_count"],
            summary["required_parity_dimension_assignment_count"],
        ) == (20, 160),
        "cg05_slots_27_p3_15_p4_12_multi_5": (
            summary["cg05_receipt_slot_count"],
            summary["p3_cg05_receipt_slot_count"],
            summary["p4_cg05_receipt_slot_count"],
            summary["multi_class_cg05_receipt_slot_count"],
        ) == (27, 15, 12, 5),
        "gap_52_exact_0_result_0_6": (
            summary["candidate_case_pair_count"],
            summary["exact_effect_family_set_pair_count"],
            summary["newer_result_or_content_parity_pair_count"],
            summary["baseline_result_or_content_parity_pair_count"],
        ) == (52, 0, 0, 6),
        "all_open_zero": summary["accepted_parity_dimension_count"]
        == summary["role_accepted_cg05_receipt_count"]
        == summary["result_parity_proven_packet_count"]
        == summary["render_or_export_parity_proven_packet_count"]
        == summary["owner_approved_packet_count"]
        == 0,
        "execution_readiness_zero": summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_cg05_matrix"]
        == summary["design_lower_bound_after_cg05_matrix"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(matrix["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_cg05_result_parity_receipt_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "previous_checkpoint": {"path": SOURCES["previous"], "sha256": sha256(paths["previous"])},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ],
        "safety": {"database_connections": 0, "operational_or_uat_execution": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
