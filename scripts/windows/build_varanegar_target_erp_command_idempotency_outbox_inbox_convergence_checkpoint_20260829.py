"""Chain the target command idempotency and message convergence contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_target_erp_command_idempotency_outbox_inbox_convergence_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_target_erp_restore_dependency_wave_reconciliation_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_target_erp_command_idempotency_outbox_inbox_convergence_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_command_idempotency_outbox_inbox_convergence_checkpoint_20260829.py",
    "test": "tests/test_varanegar_target_erp_command_idempotency_outbox_inbox_convergence_contract.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_command_idempotency_outbox_inbox_convergence_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_COMMAND_IDEMPOTENCY_OUTBOX_INBOX_CONVERGENCE_20260829_FA.md",
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
    contract = load(paths["contract"])
    previous = load(paths["previous"])
    summary = contract["summary"]
    checks = {
        "sources_pass": contract["validation"] == previous["validation"] == "PASS",
        "coverage_14_modules_49_commands": summary["module_count"] == 14 and summary["target_command_count"] == 49,
        "assignment_coverage_686_392_784_245": (summary["command_failure_stage_assignment_count"], summary["command_convergence_assignment_count"], summary["command_gate_assignment_count"], summary["command_role_assignment_count"]) == (686, 392, 784, 245),
        "implementation_runtime_and_readiness_zero": summary["implemented_idempotency_contract_count"] == summary["fault_injection_run_count"] == summary["same_key_replay_proven_command_count"] == summary["outbox_atomicity_proven_command_count"] == summary["inbox_convergence_proven_command_count"] == summary["unknown_outcome_reconciled_command_count"] == summary["command_ready_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343 and summary["design_lower_bound_after_convergence_contract"] == 1404,
        "safety_zero": set(contract["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_command_idempotency_outbox_inbox_convergence_checkpoint_20260829",
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
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "commands_messages_retries_replays_or_faults_executed": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "credentials_endpoints_pii_or_raw_business_values_read_or_persisted": 0,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
