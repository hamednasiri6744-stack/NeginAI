"""Chain the target ERP restore dependency-wave reconciliation contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_target_erp_restore_dependency_wave_reconciliation_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_target_erp_backup_restore_rehearsal_evidence_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_target_erp_restore_dependency_wave_reconciliation_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_restore_dependency_wave_reconciliation_checkpoint_20260829.py",
    "test": "tests/test_varanegar_target_erp_restore_dependency_wave_reconciliation_contract.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_restore_dependency_wave_reconciliation_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_RESTORE_DEPENDENCY_WAVE_RECONCILIATION_20260829_FA.md",
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
        "dag_14_38_7": (summary["module_count"], summary["module_dependency_edge_count"], summary["restore_wave_count"]) == (14, 38, 7),
        "coverage_140_152_98_35": (summary["module_restore_stage_assignment_count"], summary["edge_reconciliation_assignment_count"], summary["wave_gate_assignment_count"], summary["wave_role_assignment_count"]) == (140, 152, 98, 35),
        "all_operational_counts_zero": summary["authorized_restore_wave_count"] == summary["restore_run_count"] == summary["reconciled_dependency_edge_count"] == summary["reconciled_module_count"] == summary["owner_approved_wave_count"] == summary["service_enabled_module_count"] == summary["recovery_ready_module_count"] == 0,
        "command_pilot_zero": summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343 and summary["design_lower_bound_after_dependency_contract"] == 1404,
        "safety_zero": set(contract["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_restore_dependency_wave_reconciliation_checkpoint_20260829",
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
            "backup_sets_created_read_or_restored": 0,
            "deployments_jobs_failovers_replays_or_drills_executed": 0,
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
