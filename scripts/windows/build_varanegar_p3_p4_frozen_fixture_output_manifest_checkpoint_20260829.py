"""Checkpoint the P3/P4 frozen-fixture and output-manifest contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint_20260829.py",
    "test": "tests/test_varanegar_p3_p4_frozen_fixture_output_manifest_contract.py",
    "checkpoint_test": "tests/test_varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/P3_P4_FROZEN_FIXTURE_OUTPUT_MANIFEST_CONTRACT_20260829_FA.md",
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
    contract = load(paths["contract"])
    previous = load(paths["previous"])
    summary = contract["summary"]
    checks = {
        "sources_pass": contract["validation"] == previous["validation"] == "PASS",
        "contracts_8_p3_5_p4_3_cases_56": (
            summary["fixture_contract_count"],
            summary["p3_fixture_contract_count"],
            summary["p4_fixture_contract_count"],
            summary["covered_golden_case_count"],
        ) == (8, 5, 3, 56),
        "manifest_fields_16_16_16_assignments_512": (
            summary["fixture_manifest_field_count"],
            summary["output_manifest_field_count"],
            summary["comparison_manifest_field_count"],
            summary["manifest_field_assignment_count"],
        ) == (16, 16, 16, 512),
        "capture_16_steps_56_dimensions_160_receipts_27": (
            summary["required_capture_side_count"],
            summary["acquisition_step_assignment_count"],
            summary["required_parity_dimension_assignment_count"],
            summary["cg05_receipt_slot_assignment_count"],
        ) == (16, 56, 160, 27),
        "all_not_captured_zero": summary["accepted_owner_roster_count"]
        == summary["captured_fixture_manifest_count"]
        == summary["captured_output_manifest_count"]
        == summary["captured_comparison_manifest_count"]
        == summary["accepted_parity_dimension_count"]
        == summary["accepted_cg05_receipt_count"]
        == 0,
        "execution_readiness_zero": summary["result_parity_proven_contract_count"]
        == summary["owner_approved_contract_count"]
        == summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_fixture_contract"]
        == summary["design_lower_bound_after_fixture_contract"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(contract["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint_20260829",
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
