"""Apply the reporting/output outcome-contract design delta to command readiness."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "base": "artifacts/varanegar_analysis/varanegar_distribution_command_readiness_delta_20260829.json",
    "envelope": "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_envelope_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_checkpoint_20260829.json",
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
    data = {name: load(path) for name, path in paths.items()}
    modules = copy.deepcopy(data["base"]["modules"])
    reporting = next(x for x in modules if x["module"] == "reporting_documents")
    before = reporting["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"]
    reporting["mapped_validated_evidence"].append({"key": "reporting_output_outcome", "path": SOURCES["envelope"], "validation": data["envelope"]["validation"]})
    reporting["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"] = True
    reporting["legacy_open_blockers"].append("eight-surface reporting outcome/retry envelope is designed, but print/export/import runtime parity and owner approval remain unproven")
    summary = {
        "module_count": len(modules),
        "changed_module_count": 1,
        "outcome_target_contract_module_count_before": sum(x["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"] for x in data["base"]["modules"]),
        "outcome_target_contract_module_count_after": sum(x["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"] for x in modules),
        "reporting_command_surface_count": data["envelope"]["summary"]["command_surface_count"],
        "runtime_retry_idempotency_proven_module_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(x["validation"] == "PASS" for x in data.values()),
        "fourteen_modules": len(modules) == 14,
        "reporting_false_to_true": before is False and reporting["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"] is True,
        "six_to_seven": summary["outcome_target_contract_module_count_before"] == 6 and summary["outcome_target_contract_module_count_after"] == 7,
        "eight_surfaces": summary["reporting_command_surface_count"] == 8,
        "one_changed": sum(a["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"] != b["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"] for a, b in zip(data["base"]["modules"], modules)) == 1,
        "runtime_zero": summary["runtime_retry_idempotency_proven_module_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": data["risk"]["summary"]["risk_count"] == 84 and data["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_reporting_output_readiness_delta_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_DESIGN_DELTA", "database_connections": 0, "commands_forms_reports_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
        "summary": summary,
        "modules": modules,
        "promotion_boundary": {"changed": "reporting_documents outcome/retry target contract design only", "unchanged": ["runtime authorization", "runtime atomicity", "runtime effect parity", "runtime retry/idempotency", "owner approval", "command readiness", "pilot readiness"]},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "confidence": {"design_delta": "HIGH", "runtime_readiness": "NOT_PROVEN"},
        "limits": ["Design coverage is not implementation readiness.", "No print, export, import or command was executed.", "Owner-approved result and completion policies remain external gates."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
