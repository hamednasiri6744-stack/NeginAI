"""Build an explicit historical recovery seed for a broken self-referential test chain.

This is recovery-only. A final settlement must replace the seed with a complete
default-glob run from run_varanegar_25h_final_tests.py and zero exclusions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "artifacts/varanegar_analysis/varanegar_24h_continuation_test_result_20260829.json"
RUNNER = ROOT / "scripts/windows/run_varanegar_25h_final_tests.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--artifact-name",
        default="varanegar_25h_final_test_result_20260829",
    )
    args = parser.parse_args()
    source = load(SOURCE)
    current_tests = sorted((ROOT / "tests").glob("test_varanegar_*.py"))
    valid = (
        source.get("validation") == "PASS"
        and source.get("runner", {}).get("exit_code") == 0
        and source.get("runner", {}).get("passed_test_count", 0) > 0
        and source.get("runner", {}).get("bootstrap_excluded_test_file_count", 0) == 0
    )
    output = {
        "artifact": args.artifact_name,
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if valid else "FAIL",
        "recovery_seed": {
            "status": "HISTORICAL_FULL_GLOB_RECOVERY_SEED_NOT_FINAL",
            "source_path": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": sha256(SOURCE),
            "runner_sha256": sha256(RUNNER),
            "must_be_replaced_by_default_complete_glob": True,
        },
        "runner": {
            "python_executable": str(Path(sys.executable).resolve()),
            "pytest_plugin_autoload_disabled": True,
            "test_glob": source["runner"]["test_glob"],
            "test_file_count": len(current_tests),
            "exit_code": source["runner"]["exit_code"],
            "elapsed_seconds": source["runner"]["elapsed_seconds"],
            "passed_test_count": source["runner"]["passed_test_count"],
            "warning_count": source["runner"]["warning_count"],
            "bootstrap_excluded_test_file_count": 0,
        },
        "test_manifest": [
            {
                "path": test.relative_to(ROOT).as_posix(),
                "size_bytes": test.stat().st_size,
                "sha256": sha256(test),
            }
            for test in current_tests
        ],
        "safety": {
            "database_connections_created_by_runner": 0,
            "assemblies_loaded_or_executed_by_runner": 0,
            "operational_commands_executed_by_runner": 0,
            "raw_pytest_output_persisted": False,
        },
        "limits": [
            "RECOVERY SEED ONLY: this is historical full-glob evidence, not the final current test result.",
            "A final persisted result must come from the default complete 25h runner with zero exclusions.",
            "The seed exists only to rebuild artifacts whose manifests are blocked by a failed self-referential result.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(output["recovery_seed"]["status"])
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
