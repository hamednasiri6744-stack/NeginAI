from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "matrix": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_external_gate_handoff_acceptance_matrix_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_external_gate_handoff_acceptance_checkpoint_20260829.py",
    "test": "tests/test_varanegar_external_gate_handoff_acceptance_matrix.py",
    "checkpoint_test": "tests/test_varanegar_external_gate_handoff_acceptance_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/EXTERNAL_GATE_HANDOFF_ACCEPTANCE_MATRIX_20260829_FA.md",
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
        "six_open_gates": summary["gate_count"] == summary["open_gate_count"] == 6 and summary["closed_gate_count"] == 0,
        "units_84_current_0": summary["required_acceptance_unit_count"] == 84 and summary["current_accepted_unit_count"] == 0,
        "nine_handoffs_blocked": summary["handoff_edge_count"] == summary["blocked_handoff_edge_count"] == 9
        and summary["accepted_handoff_edge_count"] == 0,
        "execution_approval_readiness_zero": summary["executed_obligation_count"]
        == summary["owner_approved_module_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(matrix["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_external_gate_handoff_acceptance_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "external_gate_execution_or_approval": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
