"""Checkpoint the P3/P4 Golden/UAT result adjudication and promotion guard."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "adjudication": "artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_checkpoint_20260829.py",
    "test": "tests/test_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard.py",
    "checkpoint_test": "tests/test_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/P3_P4_GOLDEN_UAT_RESULT_ADJUDICATION_PROMOTION_GUARD_20260829_FA.md",
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
    adjudication = load(paths["adjudication"])
    previous = load(paths["previous"])
    summary = adjudication["summary"]
    checks = {
        "sources_pass": adjudication["validation"] == previous["validation"] == "PASS",
        "packets_8_cases_56_outcomes_4": (
            summary["packet_count"],
            summary["covered_golden_case_count"],
            summary["diagnostic_outcome_count"],
        ) == (8, 56, 4),
        "routes_32_case_assignments_224": (
            summary["adjudication_route_count"],
            summary["outcome_case_assignment_count"],
        ) == (32, 224),
        "guards_12_assignments_96": (
            summary["promotion_guard_count"],
            summary["promotion_guard_assignment_count"],
        ) == (12, 96),
        "dimensions_160_receipts_27": (
            summary["parity_dimension_assignment_count"],
            summary["cg05_receipt_assignment_count"],
        ) == (160, 27),
        "only_one_review_eligible_no_current_promotion": summary["review_eligible_outcome_count"] == 1
        and summary["adjudicated_route_count"]
        == summary["cg05_acceptance_review_entered_packet_count"]
        == summary["cg05_closed_packet_count"]
        == summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_adjudication_guard"]
        == summary["design_lower_bound_after_adjudication_guard"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(adjudication["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_checkpoint_20260829",
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
        "safety": {
            "database_connections": 0,
            "operational_or_uat_execution": 0,
            "repairs_replays_or_recaptures": 0,
            "data_mutations": 0,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

