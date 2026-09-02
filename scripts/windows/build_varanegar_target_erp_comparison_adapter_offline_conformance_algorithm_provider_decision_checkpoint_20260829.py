"""Chain the offline adapter conformance and crypto-provider decision record."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "conformance": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_checkpoint_20260829.py",
    "test": "tests/test_varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_COMPARISON_ADAPTER_OFFLINE_CONFORMANCE_ALGORITHM_PROVIDER_DECISION_20260829_FA.md",
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
    conformance = load(paths["conformance"])
    previous = load(paths["previous"])
    summary = conformance["summary"]
    checks = {
        "sources_pass": conformance["validation"] == previous["validation"] == "PASS",
        "digest_96_pass": summary["offline_digest_evaluation_count"]
        == summary["offline_digest_pass_count"]
        == 96
        and summary["offline_digest_fail_count"] == 0,
        "taxonomy_128_pass": summary["negative_taxonomy_lint_count"]
        == summary["negative_taxonomy_lint_pass_count"]
        == 128,
        "decision_still_open": conformance["decision_status"] == "NEEDS_PLATFORM_SECURITY_OWNER_DECISION"
        and summary["selected_algorithm_count"] == summary["selected_provider_count"] == 0,
        "no_key_signature_or_runtime": summary["key_material_created_or_loaded_count"]
        == summary["signature_created_or_loaded_count"]
        == summary["cryptographic_verification_run_count"]
        == summary["operational_adapter_run_count"]
        == 0,
        "parity_and_readiness_zero": summary["accepted_receipt_count"]
        == summary["result_parity_proven_profile_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84
        and summary["mapped_risk_assignment_count"] == 343
        and summary["design_lower_bound_after_conformance_contract"] == 1404,
        "safety_zero": set(conformance["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_checkpoint_20260829",
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
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "key_material_or_signatures_created_or_loaded": 0,
            "operational_adapter_or_crypto_runs": 0,
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

