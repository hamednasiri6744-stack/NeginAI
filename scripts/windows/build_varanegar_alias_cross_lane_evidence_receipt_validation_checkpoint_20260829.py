"""Checkpoint the cross-lane evidence-receipt validation matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "matrix": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_external_evidence_intake_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_alias_cross_lane_evidence_receipt_validation_checkpoint_20260829.py",
    "test": "tests/test_varanegar_alias_cross_lane_evidence_receipt_validation_matrix.py",
    "checkpoint_test": "tests/test_varanegar_alias_cross_lane_evidence_receipt_validation_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/ALIAS_CROSS_LANE_EVIDENCE_RECEIPT_VALIDATION_MATRIX_20260829_FA.md",
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
        "queue_29_slots_290": (summary["intake_item_count"], summary["receipt_slot_count"]) == (29, 290),
        "route_slots_90_120_50_30": (
            summary["alias_or_new_action_receipt_slot_count"],
            summary["semantic_equivalence_receipt_slot_count"],
            summary["report_effect_and_result_receipt_slot_count"],
            summary["export_effect_and_result_receipt_slot_count"],
        ) == (90, 120, 50, 30),
        "metadata_and_rejection_14": summary["required_metadata_field_count"] == summary["rejection_code_count"] == 14,
        "multi_class_14_cg05_slots_27": (
            summary["multi_class_receipt_slot_count"],
            summary["cg05_scoped_receipt_slot_count"],
        ) == (14, 27),
        "receipt_states_zero": summary["received_receipt_count"]
        == summary["hash_validated_receipt_count"]
        == summary["content_validated_receipt_count"]
        == summary["role_accepted_receipt_count"]
        == summary["accepted_route_decision_count"]
        == 0,
        "execution_readiness_zero": summary["executed_case_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_receipt_matrix"]
        == summary["design_lower_bound_after_receipt_matrix"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(matrix["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_alias_cross_lane_evidence_receipt_validation_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "previous_checkpoint": {"path": SOURCES["previous"], "sha256": sha256(paths["previous"])},
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
