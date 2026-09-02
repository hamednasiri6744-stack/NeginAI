"""Chain the P3/P4 evidence invalidation propagation matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "propagation": "artifacts/varanegar_analysis/varanegar_p3_p4_evidence_invalidation_reopen_propagation_matrix_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_p3_p4_evidence_invalidation_reopen_propagation_matrix_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_p3_p4_evidence_invalidation_reopen_propagation_checkpoint_20260829.py",
    "test": "tests/test_varanegar_p3_p4_evidence_invalidation_reopen_propagation_matrix.py",
    "checkpoint_test": "tests/test_varanegar_p3_p4_evidence_invalidation_reopen_propagation_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/P3_P4_EVIDENCE_INVALIDATION_REOPEN_PROPAGATION_20260829_FA.md",
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
    propagation = load(paths["propagation"])
    previous = load(paths["previous"])
    summary = propagation["summary"]
    checks = {
        "sources_pass": propagation["validation"] == previous["validation"] == "PASS",
        "causes_assignments_complete": summary["invalidation_cause_count"] == 12
        and summary["cause_requirement_assignment_count"] == 648,
        "dependency_edges_complete": summary["total_dependency_edge_count"] == 285
        and summary["pair_promotion_guard_edge_count"] == 96,
        "events_and_reacceptance_zero": summary["observed_invalidation_event_count"]
        == summary["invalidated_custody_requirement_count"]
        == summary["reaccepted_evidence_count"]
        == 0,
        "parity_and_readiness_zero": summary["result_parity_proven_packet_count"]
        == summary["cg05_closed_packet_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84
        and summary["mapped_risk_assignment_count"] == 343
        and summary["design_lower_bound_after_invalidation_matrix"] == 1404,
        "safety_zero": set(propagation["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_evidence_invalidation_reopen_propagation_checkpoint_20260829",
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
            "invalidation_or_reopen_events_triggered": 0,
            "external_evidence_received": 0,
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

