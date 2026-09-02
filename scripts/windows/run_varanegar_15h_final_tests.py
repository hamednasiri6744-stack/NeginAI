"""Run the bounded Varanegar evidence suite and persist a sanitized result."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    tests = sorted((ROOT / "tests").glob("test_varanegar_*.py"))
    command = [sys.executable, "-m", "pytest", "-q", *map(str, tests)]
    environment = dict(os.environ)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = round(time.monotonic() - started, 3)
    match = re.search(r"(?P<count>\d+) passed(?:, (?P<warnings>\d+) warning[s]?)? in", completed.stdout)
    passed = int(match.group("count")) if match else 0
    warnings = int(match.group("warnings") or 0) if match else 0
    validation = "PASS" if completed.returncode == 0 and passed > 0 else "FAIL"
    artifact = {
        "artifact": "varanegar_15h_final_test_result_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": validation,
        "runner": {
            "python_executable": str(Path(sys.executable).resolve()),
            "pytest_plugin_autoload_disabled": True,
            "test_glob": "tests/test_varanegar_*.py",
            "test_file_count": len(tests),
            "exit_code": completed.returncode,
            "elapsed_seconds": elapsed,
            "passed_test_count": passed,
            "warning_count": warnings,
        },
        "test_manifest": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in tests
        ],
        "safety": {
            "database_connections_created_by_runner": 0,
            "assemblies_loaded_or_executed_by_runner": 0,
            "operational_commands_executed_by_runner": 0,
            "raw_pytest_output_persisted": False,
        },
        "limits": [
            "This result proves the checked-in evidence contracts, not live operational behavior.",
            "The test runner itself opens no database connection; individual tests are expected to be offline artifact checks.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["runner"], ensure_ascii=False))
    print(validation)
    return 0 if validation == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
