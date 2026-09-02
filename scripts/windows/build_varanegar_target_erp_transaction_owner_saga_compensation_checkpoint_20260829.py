"""Chain the target transaction-owner, saga, and compensation contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_target_erp_transaction_owner_saga_compensation_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_target_erp_command_idempotency_outbox_inbox_convergence_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_target_erp_transaction_owner_saga_compensation_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_transaction_owner_saga_compensation_checkpoint_20260829.py",
    "test": "tests/test_varanegar_target_erp_transaction_owner_saga_compensation_contract.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_transaction_owner_saga_compensation_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_TRANSACTION_OWNER_SAGA_COMPENSATION_20260829_FA.md",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    contract = load(paths["contract"]); previous = load(paths["previous"]); summary = contract["summary"]
    checks = {
        "sources_pass": contract["validation"] == previous["validation"] == "PASS",
        "coverage_14_49_38_159": (summary["module_count"], summary["target_command_count"], summary["module_dependency_edge_count"], summary["command_dependency_coordination_assignment_count"]) == (14, 49, 38, 159),
        "assignment_coverage_196_588_784_294": (summary["command_pattern_candidate_assignment_count"], summary["command_failure_stage_assignment_count"], summary["command_gate_assignment_count"], summary["command_role_assignment_count"]) == (196, 588, 784, 294),
        "selection_runtime_and_readiness_zero": summary["selected_transaction_pattern_count"] == summary["named_transaction_owner_count"] == summary["fault_injection_run_count"] == summary["runtime_atomicity_proven_command_count"] == summary["saga_completed_command_count"] == summary["compensation_executed_or_accepted_count"] == summary["command_ready_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343 and summary["design_lower_bound_after_transaction_contract"] == 1404,
        "safety_zero": set(contract["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_transaction_owner_saga_compensation_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "previous_checkpoint": {"path": SOURCES["previous"], "sha256": sha256(paths["previous"])},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)} for name, path in sorted(paths.items())],
        "safety": {"database_connections": 0, "network_reads_or_writes": 0, "commands_transactions_sagas_compensations_or_faults_executed": 0, "operational_forms_reports_queries_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "credentials_endpoints_pii_or_raw_business_values_read_or_persisted": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve()); print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
