"""Chain the synthetic fiscal-period reference evaluator."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_target_erp_fiscal_period_close_reopen_adjustment_lock_checkpoint_20260829.json",
    "reference": "scripts/windows/varanegar_fiscal_period_reference.py",
    "builder": "scripts/windows/build_varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_checkpoint_20260829.py",
    "reference_test": "tests/test_varanegar_fiscal_period_reference.py",
    "test": "tests/test_varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_contract.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_FISCAL_PERIOD_SYNTHETIC_REFERENCE_EVALUATOR_20260829_FA.md",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    contract = load(paths["contract"])
    previous = load(paths["previous"])
    summary = contract["summary"]
    checks = {
        "sources_pass": contract["validation"] == previous["validation"] == "PASS",
        "vectors_23_of_23": summary["total_vector_count"] == summary["total_pass_count"] == 23,
        "positive_5_negative_18": summary["positive_pass_count"] == 5 and summary["negative_pass_count"] == 18,
        "coverage_24_336": (summary["fiscal_gate_count"], summary["fiscal_module_gate_assignment_count"]) == (24, 336),
        "operational_and_readiness_zero": all(summary[name] == 0 for name in ("operational_period_lock_or_posting_implementation_count", "operational_period_ledger_document_balance_or_entry_read_count", "close_reopen_adjustment_reversal_or_posting_run_count", "accepted_operational_receipt_count", "command_ready_module_count", "pilot_ready_module_count")),
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343 and summary["design_lower_bound_after_reference_evaluator"] == 1404,
        "safety_zero": set(contract["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    result = {
        "artifact": "varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_checkpoint_20260829",
        "schema_version": 1, "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "previous_checkpoint": {"path": SOURCES["previous"], "sha256": sha(paths["previous"])},
        "checks": checks, "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "safety": {"database_connections": 0, "network_reads_or_writes": 0, "operational_period_ledger_document_balance_or_entry_reads": 0, "period_close_reopen_adjustment_reversal_or_posting_actions_executed": 0, "operational_forms_reports_queries_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "credentials_endpoints_pii_or_raw_business_values_read_or_persisted": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(result["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
