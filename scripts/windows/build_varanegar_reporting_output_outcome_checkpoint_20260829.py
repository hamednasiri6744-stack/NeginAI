"""Chain the reporting/output outcome and retry envelope."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "envelope": "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_envelope_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_24h_continuation_gap_refresh_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_reporting_output_outcome_envelope_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_reporting_output_outcome_checkpoint_20260829.py",
    "test": "tests/test_varanegar_reporting_output_outcome_envelope.py",
    "checkpoint_test": "tests/test_varanegar_reporting_output_outcome_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/REPORTING_OUTPUT_OUTCOME_RETRY_ENVELOPE_20260829_FA.md",
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
    data = load(paths["envelope"])
    previous = load(paths["previous"])
    summary = data["summary"]
    checks = {
        "sources_pass": data["validation"] == previous["validation"] == "PASS",
        "eight_surfaces": summary["command_surface_count"] == summary["partial_failure_fixture_count"] == 8,
        "contract_shape": summary["outcome_code_count"] == 5 and summary["common_request_field_count"] == 10 and summary["common_response_field_count"] == 9,
        "legacy_gap": summary["legacy_explicit_command_id_count"] == 0,
        "history_and_delegation": summary["sale_print_event_count"] == 308432 and summary["bank_delegated_command_count"] == 5,
        "runtime_zero": summary["runtime_outcome_parity_proven_count"] == summary["implemented_command_count"] == summary["owner_approved_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343 and summary["new_risk_count"] == 0,
        "safety_zero": set(value for key, value in data["safety"].items() if key != "mode") == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_reporting_output_outcome_checkpoint_20260829",
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
