"""Run checked-in offline Varanegar evidence tests and persist a sanitized result."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "artifacts" / "varanegar_analysis"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def manifest_entry_is_current(entry: dict) -> bool:
    relative = entry.get("path")
    if not isinstance(relative, str):
        return True
    path = ROOT / relative
    return (
        path.is_file()
        and path.stat().st_size == entry.get("size_bytes")
        and sha256(path) == entry.get("sha256")
    )


def bootstrap_exclusions(tests: list[Path]) -> list[Path]:
    """Exclude only tests coupled to the stale self-referential result chain."""
    names = {
        "test_varanegar_24h_continuation_consolidated_audit.py",
        "test_varanegar_24h_continuation_consolidated_checkpoint.py",
        "test_varanegar_24h_continuation_wave01_bundle.py",
        "test_varanegar_24h_continuation_wave01_checkpoint.py",
        "test_varanegar_25h_final_bundle.py",
    }
    wave_builder = ROOT / "scripts" / "windows" / "build_varanegar_24h_continuation_wave01_bundle_20260829.py"
    post_wave_checkpoints = runpy.run_path(str(wave_builder))["POST_WAVE01_CHECKPOINTS"]
    for checkpoint_name in post_wave_checkpoints:
        checkpoint_path = ANALYSIS / checkpoint_name
        if not checkpoint_path.is_file():
            continue
        checkpoint = load(checkpoint_path)
        names.update(
            Path(entry["path"]).name
            for entry in checkpoint.get("source_manifest", [])
            if isinstance(entry, dict)
            and isinstance(entry.get("path"), str)
            and entry["path"].startswith("tests/")
            and entry["path"].endswith(".py")
        )
    for artifact in ANALYSIS.rglob("*.json"):
        try:
            document = load(artifact)
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        entries = document.get("source_manifest", [])
        if not isinstance(entries, list) or all(manifest_entry_is_current(entry) for entry in entries):
            continue
        names.update(
            Path(entry["path"]).name
            for entry in entries
            if isinstance(entry, dict)
            and isinstance(entry.get("path"), str)
            and entry["path"].startswith("tests/")
            and entry["path"].endswith(".py")
        )
    return [test for test in tests if test.name in names]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--exclude-final-bundle-bootstrap", action="store_true")
    args = parser.parse_args()
    tests = sorted((ROOT / "tests").glob("test_varanegar_*.py"))
    excluded: list[Path] = []
    if args.exclude_final_bundle_bootstrap:
        excluded = bootstrap_exclusions(tests)
        tests = [test for test in tests if test not in excluded]
    environment = dict(os.environ)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    started = time.monotonic()
    # Windows CreateProcess has a short command-line ceiling.  A pytest response
    # file keeps the complete explicit test manifest without exclusions as the
    # evidence suite grows beyond that ceiling.
    with tempfile.TemporaryDirectory(prefix="varanegar-pytest-") as temporary:
        args_file = Path(temporary) / "tests.args"
        args_file.write_text("\n".join(str(test) for test in tests) + "\n", encoding="utf-8")
        run = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", f"@{args_file}"],
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
    match = re.search(r"(?P<count>\d+) passed(?:, (?P<warnings>\d+) warning[s]?)? in", run.stdout)
    passed = int(match.group("count")) if match else 0
    warnings = int(match.group("warnings") or 0) if match else 0
    validation = "PASS" if run.returncode == 0 and passed > 0 else "FAIL"
    output = {
        "artifact": "varanegar_25h_final_test_result_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": validation,
        "runner": {
            "python_executable": str(Path(sys.executable).resolve()),
            "pytest_plugin_autoload_disabled": True,
            "test_glob": "tests/test_varanegar_*.py",
            "test_file_count": len(tests),
            "exit_code": run.returncode,
            "elapsed_seconds": elapsed,
            "passed_test_count": passed,
            "warning_count": warnings,
            "bootstrap_excluded_test_file_count": len(excluded),
        },
        "test_manifest": [
            {"path": test.relative_to(ROOT).as_posix(), "size_bytes": test.stat().st_size, "sha256": sha256(test)}
            for test in tests
        ],
        "safety": {
            "database_connections_created_by_runner": 0,
            "assemblies_loaded_or_executed_by_runner": 0,
            "operational_commands_executed_by_runner": 0,
            "raw_pytest_output_persisted":False,
        },
        "limits": [
            "This proves checked-in offline evidence contracts, not live operational behavior.",
            "The runner opens no database connection and persists no raw pytest output.",
            "Bootstrap exclusion is recovery-only; final persisted evidence must use the default complete glob with zero exclusions.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(output["runner"], ensure_ascii=False))
    print(validation)
    if run.returncode != 0:
        print("\n".join(run.stdout.splitlines()[-120:]))
    return 0 if validation == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
