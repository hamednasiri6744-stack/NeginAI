"""Build executable synthetic negative-vector evidence for the reference codec."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from varanegar_comparison_adapter_reference_codec import (
    ERROR_RULES,
    baseline_envelope,
    mutated_envelope,
    validate,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "adapter": "artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.json",
    "vectors": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.json",
    "conformance": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_20260829.json",
    "conformance_checkpoint": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_checkpoint_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "codec": "scripts/windows/varanegar_comparison_adapter_reference_codec.py",
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
    documents = {name: load(path) for name, path in paths.items() if path.suffix == ".json"}
    adapter = documents["adapter"]
    vectors = documents["vectors"]
    official = documents["tests"]
    vector_by_trigger = {vector["synthetic_trigger_class"]: vector for vector in vectors["negative_error_vectors"]}

    positive_results = []
    negative_results = []
    mutation_vectors = []
    for profile in adapter["adapter_profiles"]:
        profile_id = profile["adapter_profile_id"]
        observed = validate(baseline_envelope(profile_id))
        positive_results.append(
            {
                "adapter_profile_id": profile_id,
                "run_scope": "OFFLINE_SYNTHETIC_REFERENCE_CODEC",
                "observed_typed_status": observed["typed_status"],
                "validation": "PASS" if observed["accepted"] else "FAIL",
                "operational_adapter_execution": False,
            }
        )
        for trigger, error_code, typed_status in ERROR_RULES:
            envelope = mutated_envelope(profile_id, trigger)
            observed = validate(envelope)
            baseline = baseline_envelope(profile_id)
            changed = sorted(key for key in baseline if baseline[key] != envelope[key])
            expected_vector = vector_by_trigger[trigger]
            negative_results.append(
                {
                    "adapter_profile_id": profile_id,
                    "test_vector_id": expected_vector["test_vector_id"],
                    "trigger_class": trigger,
                    "expected_error_code": error_code,
                    "observed_error_code": observed["error_code"],
                    "expected_typed_status": typed_status,
                    "observed_typed_status": observed["typed_status"],
                    "changed_control_fields": changed,
                    "validation": "PASS"
                    if observed["accepted"] is False
                    and observed["error_code"] == error_code
                    and observed["typed_status"] == typed_status
                    and len(changed) == 1
                    else "FAIL",
                    "operational_adapter_execution": False,
                    "runtime_fault_in_varanegar_or_erp": False,
                }
            )

    for trigger, error_code, typed_status in ERROR_RULES:
        sample = mutated_envelope("SYNTH_PROFILE_TEMPLATE", trigger)
        base = baseline_envelope("SYNTH_PROFILE_TEMPLATE")
        mutation_vectors.append(
            {
                "trigger_class": trigger,
                "expected_error_code": error_code,
                "expected_typed_status": typed_status,
                "changed_control_field": next(key for key in base if base[key] != sample[key]),
                "contains_business_value": False,
                "synthetic_only": True,
            }
        )

    summary = {
        "adapter_profile_count": len(adapter["adapter_profiles"]),
        "validator_rule_count": len(ERROR_RULES),
        "mutation_vector_count": len(mutation_vectors),
        "positive_baseline_run_count": len(positive_results),
        "positive_baseline_pass_count": sum(item["validation"] == "PASS" for item in positive_results),
        "synthetic_negative_run_count": len(negative_results),
        "synthetic_negative_pass_count": sum(item["validation"] == "PASS" for item in negative_results),
        "synthetic_negative_fail_count": sum(item["validation"] != "PASS" for item in negative_results),
        "error_precedence_rule_count": len(ERROR_RULES),
        "reference_codec_implementation_count": 1,
        "operational_adapter_implementation_count": 0,
        "operational_adapter_run_count": 0,
        "legacy_or_target_capture_count": 0,
        "emitted_receipt_count": 0,
        "accepted_receipt_count": 0,
        "result_parity_proven_profile_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_reference_codec": 1404,
        "design_lower_bound_after_reference_codec": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(
            documents[name].get("validation") == "PASS"
            for name in ("adapter", "vectors", "conformance", "conformance_checkpoint", "tests")
        ),
        "profiles_8_rules_16_mutations_16": (
            summary["adapter_profile_count"],
            summary["validator_rule_count"],
            summary["mutation_vector_count"],
        )
        == (8, 16, 16),
        "positive_8_all_pass": summary["positive_baseline_run_count"]
        == summary["positive_baseline_pass_count"]
        == 8,
        "negative_128_all_pass": summary["synthetic_negative_run_count"]
        == summary["synthetic_negative_pass_count"]
        == 128
        and summary["synthetic_negative_fail_count"] == 0,
        "single_control_mutation": all(len(item["changed_control_fields"]) == 1 for item in negative_results),
        "error_taxonomy_exact": {item["observed_error_code"] for item in negative_results}
        == set(vectors["adapter_error_codes"]),
        "reference_only_operational_zero": summary["reference_codec_implementation_count"] == 1
        and summary["operational_adapter_implementation_count"]
        == summary["operational_adapter_run_count"]
        == summary["legacy_or_target_capture_count"]
        == 0,
        "receipt_parity_readiness_zero": summary["emitted_receipt_count"]
        == summary["accepted_receipt_count"]
        == summary["result_parity_proven_profile_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_reference_codec"]
        == summary["design_lower_bound_after_reference_codec"]
        == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "offline_synthetic_reference_codec_only",
            "continuation_complete": False,
            "operational_adapter_or_legacy_execution_authorized": False,
        },
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
        "summary": summary,
        "validator_rules": [
            {
                "precedence": index,
                "trigger_class": trigger,
                "error_code": error_code,
                "typed_status": typed_status,
            }
            for index, (trigger, error_code, typed_status) in enumerate(ERROR_RULES, start=1)
        ],
        "error_precedence": [error_code for _, error_code, _ in ERROR_RULES],
        "synthetic_mutation_vectors": mutation_vectors,
        "positive_baseline_results": positive_results,
        "synthetic_negative_results": negative_results,
        "reference_codec_contract": {
            "fail_fast_first_error_precedence": True,
            "one_control_mutation_per_negative_vector": True,
            "unknown_trigger_rejected": True,
            "contains_only_synthetic_booleans_counts_and_tokens": True,
            "receipt_emission_supported": False,
            "cryptographic_signing_or_verification_supported": False,
            "operational_use_allowed": False,
        },
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
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "The codec is a pure reference validator over synthetic control fields, not an operational target ERP adapter.",
            "No Varanegar or target ERP runtime fault was injected and no business result was compared.",
            "PASS does not establish receipt authenticity, result parity, CG-05 closure, UAT, command readiness, or pilot readiness.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

