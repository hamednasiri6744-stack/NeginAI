"""Chain the P3/P4 evidence freshness and clock-policy reference contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "freshness": "artifacts/varanegar_analysis/varanegar_p3_p4_evidence_freshness_clock_policy_reference_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_p3_p4_evidence_invalidation_reopen_propagation_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_p3_p4_evidence_freshness_clock_policy_reference_contract_20260829.py",
    "reference": "scripts/windows/varanegar_evidence_freshness_reference.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_p3_p4_evidence_freshness_clock_policy_reference_checkpoint_20260829.py",
    "test": "tests/test_varanegar_p3_p4_evidence_freshness_clock_policy_reference_contract.py",
    "checkpoint_test": "tests/test_varanegar_p3_p4_evidence_freshness_clock_policy_reference_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/P3_P4_EVIDENCE_FRESHNESS_CLOCK_POLICY_REFERENCE_20260829_FA.md",
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
    freshness = load(paths["freshness"])
    previous = load(paths["previous"])
    summary = freshness["summary"]
    checks = {
        "sources_pass": freshness["validation"] == previous["validation"] == "PASS",
        "synthetic_48_pass": summary["synthetic_evaluation_count"]
        == summary["synthetic_evaluation_pass_count"]
        == 48
        and summary["synthetic_evaluation_fail_count"] == 0,
        "obligations_216": summary["freshness_obligation_count"] == 216,
        "real_acceptance_parity_zero": summary["real_clock_evaluation_count"]
        == summary["current_evidence_count"]
        == summary["accepted_freshness_count"]
        == summary["result_parity_proven_packet_count"]
        == summary["cg05_closed_packet_count"]
        == 0,
        "readiness_zero": summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84
        and summary["mapped_risk_assignment_count"] == 343
        and summary["design_lower_bound_after_freshness_contract"] == 1404,
        "safety_zero": set(freshness["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_evidence_freshness_clock_policy_reference_checkpoint_20260829",
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
            "system_or_external_clock_reads_for_vectors": 0,
            "real_evidence_evaluations": 0,
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

