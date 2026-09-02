"""Checkpoint the P3/P4 result parity mismatch diagnostic playbook."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "playbook": "artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint_20260829.py",
    "test": "tests/test_varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook.py",
    "checkpoint_test": "tests/test_varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/P3_P4_RESULT_PARITY_MISMATCH_DIAGNOSTIC_PLAYBOOK_20260829_FA.md",
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
    playbook = load(paths["playbook"])
    previous = load(paths["previous"])
    summary = playbook["summary"]
    checks = {
        "sources_pass": playbook["validation"] == previous["validation"] == "PASS",
        "playbooks_10_steps_10_assignments_100": (
            summary["diagnostic_playbook_count"],
            summary["minimum_step_count"],
            summary["diagnostic_step_assignment_count"],
        ) == (10, 10, 100),
        "fixture_8_cases_56_assignments_72_504": (
            summary["fixture_contract_count"],
            summary["covered_golden_case_count"],
            summary["playbook_packet_assignment_count"],
            summary["playbook_golden_case_assignment_count"],
        ) == (8, 56, 72, 504),
        "dimension_links_34": summary["parity_dimension_link_count"] == 34,
        "all_not_run_zero": summary["diagnostic_run_count"]
        == summary["match_confirmed_count"]
        == summary["accepted_exception_count"]
        == summary["invalid_evidence_count"]
        == summary["unexplained_block_count"]
        == summary["repair_or_replay_performed_count"]
        == summary["owner_approved_resolution_count"]
        == 0,
        "execution_readiness_zero": summary["result_parity_proven_packet_count"]
        == summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_diagnostic_playbook"]
        == summary["design_lower_bound_after_diagnostic_playbook"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(playbook["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "operational_or_uat_execution": 0, "repairs_or_replays": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
