from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "matrix": "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_matrix_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_pos_replication_static_graph_risk_triage_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_report_formula_grain_policy_matrix_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_report_formula_grain_policy_checkpoint_20260829.py",
    "test": "tests/test_varanegar_report_formula_grain_policy_matrix.py",
    "checkpoint_test": "tests/test_varanegar_report_formula_grain_policy_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/REPORT_FORMULA_GRAIN_POLICY_MATRIX_20260829_FA.md",
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
        "eleven_result_owners": summary["result_owner_surface_count"] == 11,
        "partition_8_2_1": summary["query_bound_result_owner_count"] == 8
        and summary["external_template_result_owner_count"] == 2
        and summary["typed_bank_summary_result_owner_count"] == 1,
        "dimensions_obligations_fields": summary["policy_dimension_count"] == 14
        and summary["surface_policy_obligation_count"] == 123
        and summary["required_packet_field_count"] == 20,
        "fifty_design_zero_execution": summary["designed_golden_fixture_count"] == 50
        and summary["executed_golden_fixture_count"] == 0,
        "approval_parity_readiness_zero": summary["accepted_formula_packet_count"]
        == summary["owner_approved_formula_surface_count"]
        == summary["result_parity_proven_surface_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(matrix["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_report_formula_grain_policy_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "report_or_query_execution": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
