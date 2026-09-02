"""Chain the first non-final continuation wave bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "bundle": "artifacts/varanegar_analysis/varanegar_24h_continuation_wave01_bundle_20260829.json",
    "test_result": "artifacts/varanegar_analysis/varanegar_24h_continuation_test_result_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_continuation_traceability_delta_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_24h_continuation_wave01_bundle_20260829.py",
    "runner": "scripts/windows/run_varanegar_24h_continuation_tests.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_24h_continuation_wave01_checkpoint_20260829.py",
    "test": "tests/test_varanegar_24h_continuation_wave01_bundle.py",
    "doc": "docs/varanegar_reconstruction/VARANEGAR_24H_CONTINUATION_WAVE01_20260829_FA.md",
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
    bundle = load(paths["bundle"])
    test_result = load(paths["test_result"])
    previous = load(paths["previous"])
    baseline = bundle["baseline"]
    checks = {
        "sources_pass": bundle["validation"] == test_result["validation"] == previous["validation"] == "PASS",
        "explicitly_non_final": bundle["scope"]["continuation_complete"] is False,
        "all_prior_checkpoints_current": baseline["checkpoint_count"] == baseline["passing_checkpoint_count"]
        and baseline["checkpoint_count"] >= 63
        and baseline["stale_checkpoint_manifest_count"] == 0,
        "full_glob_selected": test_result["runner"]["test_glob"] == "tests/test_varanegar_*.py",
        "base_counts_stable": baseline["risk_count"] == 84 and baseline["mapped_risk_assignment_count"] == 343,
        "runtime_gates_zero": baseline["command_ready_module_count"] == baseline["pilot_ready_module_count"] == 0
        and baseline["accounting_golden_executed_count"] == baseline["report_result_parity_proven_count"] == 0,
        "safety_zero": set(bundle["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_24h_continuation_wave01_checkpoint_20260829",
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
            "commands_forms_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "data_mutations": 0,
            "sensitive_values_persisted": 0,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
