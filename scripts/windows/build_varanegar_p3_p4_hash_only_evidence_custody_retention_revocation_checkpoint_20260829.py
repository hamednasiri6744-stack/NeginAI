"""Chain the hash-only evidence custody, retention, and revocation contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "custody": "artifacts/varanegar_analysis/varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_p3_p4_capture_to_comparison_evidence_handoff_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_checkpoint_20260829.py",
    "test": "tests/test_varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract.py",
    "checkpoint_test": "tests/test_varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/P3_P4_HASH_ONLY_EVIDENCE_CUSTODY_RETENTION_REVOCATION_20260829_FA.md",
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
    custody = load(paths["custody"])
    previous = load(paths["previous"])
    summary = custody["summary"]
    checks = {
        "sources_pass": custody["validation"] == previous["validation"] == "PASS",
        "requirements_54": summary["custody_requirement_count"] == 54,
        "contract_counts_complete": (
            summary["custody_metadata_field_count"],
            summary["custody_state_count"],
            summary["transition_rule_count"],
            summary["custody_gate_count"],
            summary["custody_gate_assignment_count"],
            summary["custody_role_assignment_count"],
        )
        == (20, 9, 12, 10, 540, 216),
        "custody_acceptance_parity_zero": summary["created_custody_receipt_count"]
        == summary["transferred_custody_receipt_count"]
        == summary["accepted_current_custody_receipt_count"]
        == summary["accepted_evidence_count"]
        == summary["comparison_handoff_ready_count"]
        == summary["result_parity_proven_packet_count"]
        == summary["cg05_closed_packet_count"]
        == 0,
        "readiness_zero": summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84
        and summary["mapped_risk_assignment_count"] == 343
        and summary["design_lower_bound_after_custody_contract"] == 1404,
        "safety_zero": set(custody["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_checkpoint_20260829",
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
            "network_reads_or_writes_to_varanegar_or_erp": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "external_evidence_or_custody_receipts_received": 0,
            "raw_payloads_or_files_persisted": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

