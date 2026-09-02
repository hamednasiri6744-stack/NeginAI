"""Chain the synthetic negative reference-codec contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "codec_contract": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_contract_20260829.py",
    "codec": "scripts/windows/varanegar_comparison_adapter_reference_codec.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_checkpoint_20260829.py",
    "test": "tests/test_varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_contract.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_COMPARISON_ADAPTER_SYNTHETIC_NEGATIVE_REFERENCE_CODEC_20260829_FA.md",
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
    contract = load(paths["codec_contract"])
    previous = load(paths["previous"])
    summary = contract["summary"]
    checks = {
        "sources_pass": contract["validation"] == previous["validation"] == "PASS",
        "positive_8_pass": summary["positive_baseline_run_count"] == summary["positive_baseline_pass_count"] == 8,
        "negative_128_pass": summary["synthetic_negative_run_count"]
        == summary["synthetic_negative_pass_count"]
        == 128
        and summary["synthetic_negative_fail_count"] == 0,
        "reference_not_operational": summary["reference_codec_implementation_count"] == 1
        and summary["operational_adapter_implementation_count"]
        == summary["operational_adapter_run_count"]
        == 0,
        "parity_and_readiness_zero": summary["accepted_receipt_count"]
        == summary["result_parity_proven_profile_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84
        and summary["mapped_risk_assignment_count"] == 343
        and summary["design_lower_bound_after_reference_codec"] == 1404,
        "safety_zero": set(contract["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_checkpoint_20260829",
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
            "legacy_or_target_business_values_captured": 0,
            "operational_adapter_runs": 0,
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

