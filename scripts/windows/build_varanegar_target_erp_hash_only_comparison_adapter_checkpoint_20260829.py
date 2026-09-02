"""Checkpoint the target ERP hash-only comparison adapter contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "adapter": "artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_target_erp_hash_only_comparison_adapter_checkpoint_20260829.py",
    "test": "tests/test_varanegar_target_erp_hash_only_comparison_adapter_contract.py",
    "checkpoint_test": "tests/test_varanegar_target_erp_hash_only_comparison_adapter_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TARGET_ERP_HASH_ONLY_COMPARISON_ADAPTER_CONTRACT_20260829_FA.md",
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
    adapter = load(paths["adapter"])
    previous = load(paths["previous"])
    summary = adapter["summary"]
    checks = {
        "sources_pass": adapter["validation"] == previous["validation"] == "PASS",
        "profiles_8_cases_56": (summary["adapter_profile_count"], summary["covered_golden_case_count"]) == (8, 56),
        "schemas_18_18_stages_12_errors_16_statuses_6": (
            summary["input_envelope_field_count"],
            summary["output_receipt_field_count"],
            summary["canonicalization_stage_count"],
            summary["error_code_count"],
            summary["typed_status_count"],
        ) == (18, 18, 12, 16, 6),
        "dimensions_160_receipts_27_guards_96": (
            summary["parity_dimension_assignment_count"],
            summary["cg05_receipt_assignment_count"],
            summary["promotion_guard_assignment_count"],
        ) == (160, 27, 96),
        "all_runtime_and_readiness_zero": summary["adapter_implementation_count"]
        == summary["adapter_request_count"]
        == summary["canonicalization_run_count"]
        == summary["comparison_run_count"]
        == summary["emitted_receipt_count"]
        == summary["accepted_receipt_count"]
        == summary["result_parity_proven_profile_count"]
        == summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_adapter_contract"]
        == summary["design_lower_bound_after_adapter_contract"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(adapter["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_hash_only_comparison_adapter_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "network_access": 0, "adapter_or_uat_execution": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

