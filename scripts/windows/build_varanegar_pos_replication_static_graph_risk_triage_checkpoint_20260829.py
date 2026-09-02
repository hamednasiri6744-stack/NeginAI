from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "triage": "artifacts/varanegar_analysis/varanegar_pos_replication_static_graph_risk_triage_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_pos_replication_static_graph_risk_triage_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_pos_replication_static_graph_risk_triage_checkpoint_20260829.py",
    "test": "tests/test_varanegar_pos_replication_static_graph_risk_triage.py",
    "checkpoint_test": "tests/test_varanegar_pos_replication_static_graph_risk_triage_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/POS_REPLICATION_STATIC_GRAPH_RISK_TRIAGE_20260829_FA.md",
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
    triage = load(paths["triage"])
    previous = load(paths["previous"])
    summary = triage["summary"]
    checks = {
        "sources_pass": triage["validation"] == previous["validation"] == "PASS",
        "cap_and_boundary_honest": summary["graph_truncated_at_safety_cap"] is True
        and summary["opaque_unexpanded_queue_count"] == 160
        and summary["depth_boundary_callable_module_count"] == 151,
        "unresolved_refined": summary["unresolved_dependency_count"] == 179
        and summary["sql_pseudotable_reference_count"] == 168
        and summary["actionable_unresolved_name_or_type_count"] == 11,
        "cycles_preserved": summary["cyclic_component_count"] == 11 and summary["cyclic_node_count"] == 68,
        "runtime_readiness_zero": summary["runtime_atomicity_proven_command_count"]
        == summary["runtime_effect_parity_proven_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(triage["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_pos_replication_static_graph_risk_triage_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "sql_or_command_execution": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
