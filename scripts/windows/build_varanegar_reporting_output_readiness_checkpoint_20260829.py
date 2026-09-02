"""Chain the reporting/output command-readiness design delta."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "delta": "artifacts/varanegar_analysis/varanegar_reporting_output_readiness_delta_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_reporting_output_readiness_delta_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_reporting_output_readiness_checkpoint_20260829.py",
    "test": "tests/test_varanegar_reporting_output_readiness_delta.py",
    "checkpoint_test": "tests/test_varanegar_reporting_output_readiness_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/REPORTING_OUTPUT_READINESS_DELTA_20260829_FA.md",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / rel for name, rel in SOURCES.items()}
    data = load(paths["delta"])
    previous = load(paths["previous"])
    summary = data["summary"]
    checks = {
        "sources_pass": data["validation"] == previous["validation"] == "PASS",
        "fourteen_one_changed": summary["module_count"] == 14 and summary["changed_module_count"] == 1,
        "six_to_seven": summary["outcome_target_contract_module_count_before"] == 6 and summary["outcome_target_contract_module_count_after"] == 7,
        "eight_surfaces": summary["reporting_command_surface_count"] == 8,
        "runtime_zero": summary["runtime_retry_idempotency_proven_module_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343 and summary["new_risk_count"] == 0,
        "safety_zero": set(value for key, value in data["safety"].items() if key != "mode") == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_reporting_output_readiness_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "previous_checkpoint": {"path": SOURCES["previous"], "sha256": sha(paths["previous"])},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "safety": {"commands_forms_queries_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "database_connections": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
