"""Checkpoint comparison-adapter test vectors and receipt-verification design."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "verification": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint_20260829.py",
    "test": "tests/test_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_COMPARISON_ADAPTER_TEST_VECTOR_RECEIPT_VERIFICATION_20260829_FA.md",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / value for name, value in SOURCES.items()}
    verification = load(paths["verification"])
    previous = load(paths["previous"])
    summary = verification["summary"]
    checks = {
        "sources_pass": verification["validation"] == previous["validation"] == "PASS",
        "vectors_12_16_28_assignments_224": (
            summary["canonical_positive_vector_count"],
            summary["negative_error_vector_count"],
            summary["total_test_vector_count"],
            summary["profile_vector_assignment_count"],
        ) == (12, 16, 28, 224),
        "metadata_16_outcomes_8_states_6_rules_8_steps_10": (
            summary["authenticity_metadata_field_count"],
            summary["verification_outcome_count"],
            summary["key_lifecycle_state_count"],
            summary["rotation_rule_count"],
            summary["verification_step_count"],
        ) == (16, 8, 6, 8, 10),
        "all_runtime_zero": summary["selected_algorithm_profile_count"]
        == summary["registered_verification_key_count"]
        == summary["signed_receipt_count"]
        == summary["verification_run_count"]
        == summary["authentic_receipt_count"]
        == summary["accepted_receipt_count"]
        == summary["result_parity_proven_profile_count"]
        == summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_verification_contract"]
        == summary["design_lower_bound_after_verification_contract"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(verification["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "network_access": 0, "keys_or_signatures_created": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

