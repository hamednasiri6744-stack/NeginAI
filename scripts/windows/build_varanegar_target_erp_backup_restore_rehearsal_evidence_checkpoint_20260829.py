"""Chain the target ERP backup/restore rehearsal evidence contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "restore": "artifacts/varanegar_analysis/varanegar_target_erp_backup_restore_rehearsal_evidence_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_p3_p4_evidence_freshness_clock_policy_reference_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_target_erp_backup_restore_rehearsal_evidence_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_backup_restore_rehearsal_evidence_checkpoint_20260829.py",
    "test": "tests/test_varanegar_target_erp_backup_restore_rehearsal_evidence_contract.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_backup_restore_rehearsal_evidence_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_BACKUP_RESTORE_REHEARSAL_EVIDENCE_20260829_FA.md",
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
    restore = load(paths["restore"])
    previous = load(paths["previous"])
    summary = restore["summary"]
    checks = {
        "sources_pass": restore["validation"] == previous["validation"] == "PASS",
        "coverage_14_84_168": summary["module_count"] == 14
        and summary["module_asset_obligation_count"] == 84
        and summary["module_scenario_assignment_count"] == 168,
        "gates_and_roles_complete": summary["module_gate_assignment_count"] == 196
        and summary["module_role_assignment_count"] == 70,
        "restore_and_recovery_readiness_zero": summary["backup_set_created_or_read_count"]
        == summary["restore_rehearsal_run_count"]
        == summary["passed_restore_rehearsal_count"]
        == summary["reconciled_restore_count"]
        == summary["recovery_ready_module_count"]
        == 0,
        "command_pilot_zero": summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84
        and summary["mapped_risk_assignment_count"] == 343
        and summary["design_lower_bound_after_restore_contract"] == 1404,
        "safety_zero": set(restore["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_backup_restore_rehearsal_evidence_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "previous_checkpoint": {"path": SOURCES["previous"], "sha256": sha256(paths["previous"])},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {
                "name": name,
                "path": SOURCES[name],
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for name, path in sorted(paths.items())
        ],
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "backup_sets_created_read_or_restored": 0,
            "deployments_jobs_failovers_or_drills_executed": 0,
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

