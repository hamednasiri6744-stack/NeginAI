from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "playbook": "artifacts/varanegar_analysis/varanegar_cross_gate_diagnostic_playbook_addendum_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_identity_authorization_gap_triage_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_cross_gate_diagnostic_playbook_addendum_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_cross_gate_diagnostic_playbook_addendum_checkpoint_20260829.py",
    "test": "tests/test_varanegar_cross_gate_diagnostic_playbook_addendum.py",
    "checkpoint_test": "tests/test_varanegar_cross_gate_diagnostic_playbook_addendum_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/CROSS_GATE_DIAGNOSTIC_PLAYBOOK_ADDENDUM_20260829_FA.md",
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
    playbook = load(paths["playbook"])
    previous = load(paths["previous"])
    summary = playbook["summary"]
    checks = {
        "sources_pass": playbook["validation"] == previous["validation"] == "PASS",
        "eight_unique_addenda": summary["addendum_playbook_count"] == 8 and summary["duplicate_playbook_id_count"] == 0,
        "ten_steps_five_classes": summary["minimum_step_count"] >= 10 and summary["diagnostic_result_class_count"] == 5,
        "latest_boundaries_bound": summary["identity_triage_required_unit_count"] == 139
        and summary["pos_static_work_queue_count"] == 5
        and summary["report_formula_policy_obligation_count"] == 123
        and summary["blocked_handoff_edge_count"] == 9,
        "execution_acceptance_readiness_zero": summary["runtime_diagnosis_count"]
        == summary["repair_replay_grant_query_or_command_execution_count"]
        == summary["accepted_evidence_packet_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(playbook["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_cross_gate_diagnostic_playbook_addendum_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "operational_diagnosis_or_repair": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
