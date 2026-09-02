from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "priority_map": "artifacts/varanegar_analysis/varanegar_external_evidence_gate_priority_map_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_identity_integration_transaction_mutation_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_external_evidence_gate_priority_map_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_external_evidence_gate_priority_checkpoint_20260829.py",
    "test": "tests/test_varanegar_external_evidence_gate_priority_map.py",
    "checkpoint_test": "tests/test_varanegar_external_evidence_gate_priority_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/EXTERNAL_EVIDENCE_GATE_PRIORITY_MAP_20260829_FA.md",
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
    priority_map = load(paths["priority_map"])
    previous = load(paths["previous"])
    summary = priority_map["summary"]
    rows = priority_map["priority_map"]
    checks = {
        "sources_pass": priority_map["validation"] == previous["validation"] == "PASS",
        "six_ranked": summary["gate_count"] == 6 and [row["priority_rank"] for row in rows] == list(range(1, 7)),
        "foundation_first_uat_last": rows[0]["gate_id"] == "CG-06" and rows[-1]["gate_id"] == "CG-04",
        "runtime_owner_zero": summary["runtime_authorization_proven_module_count"]
        == summary["runtime_atomicity_proven_module_count"]
        == summary["runtime_effect_parity_proven_module_count"]
        == summary["owner_approved_case_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(priority_map["safety"].values()) == {0, False},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_external_evidence_gate_priority_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "operational_actions": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
