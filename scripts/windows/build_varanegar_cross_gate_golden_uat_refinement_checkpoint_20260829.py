from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "matrix": "artifacts/varanegar_analysis/varanegar_cross_gate_golden_uat_refinement_matrix_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_golden_uat_design_delta_audit_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_cross_gate_golden_uat_refinement_matrix_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_cross_gate_golden_uat_refinement_checkpoint_20260829.py",
    "test": "tests/test_varanegar_cross_gate_golden_uat_refinement_matrix.py",
    "checkpoint_test": "tests/test_varanegar_cross_gate_golden_uat_refinement_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/CROSS_GATE_GOLDEN_UAT_REFINEMENT_MATRIX_20260829_FA.md",
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
    matrix = load(paths["matrix"])
    previous = load(paths["previous"])
    summary = matrix["summary"]
    checks = {
        "sources_pass": matrix["validation"] == previous["validation"] == "PASS",
        "thirty_two_oracles": summary["refinement_template_count"] == summary["failure_oracle_count"] == 32,
        "lane_split": (summary["identity_refinement_template_count"], summary["pos_refinement_template_count"], summary["report_refinement_template_count"], summary["handoff_refinement_template_count"]) == (8, 8, 10, 6),
        "non_additive_1404": summary["additive_design_obligation_count"] == 0 and summary["design_lower_bound_before_refinement"] == summary["design_lower_bound_after_refinement"] == 1404,
        "receipt_slots_unaccepted": summary["required_refinement_receipt_slot_count"] == 160 and summary["accepted_refinement_receipt_slot_count"] == 0,
        "execution_acceptance_readiness_zero": summary["executed_refinement_case_count"] == summary["owner_accepted_refinement_case_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(matrix["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_cross_gate_golden_uat_refinement_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "golden_or_uat_execution": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
