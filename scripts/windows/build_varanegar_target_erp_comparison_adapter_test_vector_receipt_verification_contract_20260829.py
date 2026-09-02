"""Build synthetic canonical vectors and receipt-verification metadata for the comparison adapter."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "adapter": "artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.json",
    "adapter_checkpoint": "artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_checkpoint_20260829.json",
    "adjudication": "artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.json",
    "fixture": "artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.json",
    "diagnostic": "artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

SYNTHETIC_POSITIVE_VECTOR_SPECS = [
    ("MANIFEST_SCOPE_AND_VERSION", "VNCOMPARE/v1/manifest", {"packet": "SYNTH_PACKET", "schema": "SYNTH_SCHEMA", "version": "SYNTH_V1"}),
    ("CASE_AND_DIMENSION_SET", "VNCOMPARE/v1/set", {"case_set": ["CASE_A", "CASE_B"], "dimension_set": ["DIM_A", "DIM_B"]}),
    ("TYPED_ENVELOPE_KEY_ORDER", "VNCOMPARE/v1/envelope", {"a": {"t": "TOKEN", "v": "A"}, "b": {"t": "TOKEN", "v": "B"}}),
    ("UNICODE_NORMALIZATION_TOKEN", "VNCOMPARE/v1/unicode", {"normalization": "NFC", "token": "SYNTH_UNICODE_TOKEN"}),
    ("TEMPORAL_LOCALE_POLICY_REFERENCE", "VNCOMPARE/v1/temporal", {"calendar": "SYNTH_CAL", "locale": "SYNTH_LOCALE", "timezone": "SYNTH_ZONE"}),
    ("DECIMAL_CURRENCY_POLICY_REFERENCE", "VNCOMPARE/v1/decimal", {"currency": "SYNTH_CUR", "rounding": "SYNTH_ROUND", "scale": "SYNTH_SCALE"}),
    ("NULL_MISSING_EMPTY_ZERO_UNKNOWN_TAGS", "VNCOMPARE/v1/type-tags", {"tags": ["NULL", "MISSING", "EMPTY", "ZERO", "UNKNOWN"]}),
    ("STABLE_KEY_AND_ROW_HASH", "VNCOMPARE/v1/row", {"row_token": "ROW_A", "stable_key_token": "KEY_A"}),
    ("ORDER_INDEPENDENT_SET_HASH", "VNCOMPARE/v1/set-hash", {"member_hash_tokens": ["HASH_A", "HASH_B"]}),
    ("ORDER_SENSITIVE_SEQUENCE_HASH", "VNCOMPARE/v1/order-hash", {"ordered_hash_tokens": ["HASH_A", "HASH_B"]}),
    ("GRAIN_AND_AGGREGATE_VECTOR", "VNCOMPARE/v1/grain-aggregate", {"aggregate_token": "AGG_A", "grain_token": "GRAIN_A"}),
    ("RENDER_FILE_AND_PER_ITEM_VECTOR", "VNCOMPARE/v1/output-effects", {"file_token": "FILE_A", "per_item_token": "ITEMSET_A", "render_token": "RENDER_A"}),
]

AUTHENTICITY_METADATA_FIELDS = [
    "receipt_id",
    "signed_payload_sha256",
    "receipt_schema_version_sha256",
    "canonicalization_profile_sha256",
    "signature_algorithm_profile_reference",
    "verification_key_id",
    "verification_key_version",
    "verification_key_status_reference",
    "signature_sha256",
    "issuer_role_receipt_reference",
    "issued_at",
    "expires_at",
    "previous_receipt_sha256",
    "supersedes_receipt_id",
    "verification_policy_version_sha256",
    "verification_outcome",
]

VERIFICATION_OUTCOMES = [
    "AUTHENTIC_CURRENT",
    "PAYLOAD_HASH_MISMATCH",
    "INVALID_SIGNATURE",
    "UNKNOWN_VERIFICATION_KEY",
    "EXPIRED_VERIFICATION_KEY",
    "REVOKED_VERIFICATION_KEY",
    "SUPERSEDED_RECEIPT",
    "PROFILE_OR_POLICY_MISMATCH",
]

KEY_LIFECYCLE_STATES = ["PROPOSED", "ACTIVE", "RETIRING_VERIFY_ONLY", "REVOKED", "EXPIRED", "DESTROYED_REFERENCE_ONLY"]
ROTATION_RULES = [
    "algorithm_and_key_selection_requires_separate_platform_security_decision",
    "new_key_version_must_be_active_before_signing_cutover",
    "retiring_key_remains_verify_only_for_approved_retention_window",
    "revoked_key_never_signs_and_verification_returns_revoked",
    "expired_key_never_signs_and_verification_returns_expired",
    "historical_receipts_keep_immutable_key_id_and_version_references",
    "rotation_emits_supersession_metadata_not_receipt_overwrite",
    "private_public_and_signature_material_never_enter_analysis_artifacts",
]
VERIFICATION_STEPS = [
    "validate_receipt_schema_and_required_authenticity_metadata",
    "recompute_signed_payload_hash_from_canonical_hash_only_receipt_fields",
    "validate_algorithm_profile_policy_reference",
    "resolve_verification_key_by_id_version_and_status_reference",
    "validate_key_effective_expiry_revocation_and_retiring_boundaries",
    "verify_signature_in_separately_authorized_runtime_boundary",
    "validate_receipt_expiry_previous_hash_and_supersession_chain",
    "validate_adapter_profile_and_canonicalization_policy_hashes",
    "emit_typed_verification_outcome_without_raw_material",
    "route_only_authentic_current_receipt_to_independent_adjudication_review",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(domain_tag: str, value: dict) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((domain_tag + "\0" + canonical).encode("utf-8")).hexdigest()


def negative_status(error_code: str) -> str:
    if error_code in {"SCHEMA_VERSION_UNSUPPORTED", "ADAPTER_PROFILE_VERSION_MISMATCH"}:
        return "UNSUPPORTED_PROFILE_OR_SCHEMA"
    if error_code == "IDEMPOTENCY_CONFLICT":
        return "CONFLICT_OR_SUPERSESSION_BLOCK"
    if error_code == "PARTIAL_OR_UNKNOWN_OUTCOME":
        return "PARTIAL_OR_UNKNOWN_BLOCK"
    return "INVALID_EVIDENCE_RECOLLECTION_REQUIRED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / value for name, value in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    adapter = documents["adapter"]
    positive_vectors = [
        {
            "test_vector_id": f"CTV-P-{index:02d}",
            "vector_class": vector_class,
            "domain_tag": domain_tag,
            "synthetic_canonical_object": value,
            "expected_sha256": canonical_digest(domain_tag, value),
            "expected_acceptance": True,
            "synthetic_only": True,
            "contains_business_value": False,
        }
        for index, (vector_class, domain_tag, value) in enumerate(SYNTHETIC_POSITIVE_VECTOR_SPECS, 1)
    ]
    negative_vectors = [
        {
            "test_vector_id": f"CTV-N-{index:02d}",
            "synthetic_trigger_class": error_code.lower(),
            "expected_error_code": error_code,
            "expected_typed_status": negative_status(error_code),
            "expected_verification_or_adapter_acceptance": False,
            "synthetic_only": True,
            "contains_business_value": False,
        }
        for index, error_code in enumerate(adapter["error_codes"], 1)
    ]
    vector_ids = [vector["test_vector_id"] for vector in positive_vectors + negative_vectors]
    assignments = [
        {
            "adapter_profile_id": profile["adapter_profile_id"],
            "test_vector_ids": vector_ids,
            "positive_vector_count": len(positive_vectors),
            "negative_vector_count": len(negative_vectors),
            "executed_vector_count": 0,
            "passed_vector_count": 0,
            "failed_vector_count": 0,
            "current_status": "DESIGNED_NOT_EXECUTED",
        }
        for profile in adapter["adapter_profiles"]
    ]
    authenticity_contract = {
        "selected_runtime_algorithm_profile": None,
        "algorithm_profile_selection_status": "EXTERNAL_PLATFORM_SECURITY_DECISION_REQUIRED",
        "asymmetric_verification_required": True,
        "signed_payload_is_canonical_hash_only_receipt_envelope": True,
        "private_key_material_persisted": False,
        "public_key_material_persisted": False,
        "signature_bytes_persisted": False,
        "analysis_artifact_contains_only_references_and_hashes": True,
        "verification_required_before_adjudication": True,
        "authentic_receipt_alone_closes_cg05": False,
    }
    summary = {
        "adapter_profile_count": adapter["summary"]["adapter_profile_count"],
        "canonical_positive_vector_count": len(positive_vectors),
        "negative_error_vector_count": len(negative_vectors),
        "total_test_vector_count": len(vector_ids),
        "profile_vector_assignment_count": sum(len(row["test_vector_ids"]) for row in assignments),
        "expected_digest_count": len(positive_vectors),
        "authenticity_metadata_field_count": len(AUTHENTICITY_METADATA_FIELDS),
        "verification_outcome_count": len(VERIFICATION_OUTCOMES),
        "key_lifecycle_state_count": len(KEY_LIFECYCLE_STATES),
        "rotation_rule_count": len(ROTATION_RULES),
        "verification_step_count": len(VERIFICATION_STEPS),
        "selected_algorithm_profile_count": 0,
        "registered_verification_key_count": 0,
        "signed_receipt_count": 0,
        "verification_run_count": 0,
        "authentic_receipt_count": 0,
        "accepted_receipt_count": 0,
        "result_parity_proven_profile_count": 0,
        "executed_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_verification_contract": 1404,
        "design_lower_bound_after_verification_contract": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "profiles_8_vectors_12_16_28_assignments_224": (
            summary["adapter_profile_count"],
            summary["canonical_positive_vector_count"],
            summary["negative_error_vector_count"],
            summary["total_test_vector_count"],
            summary["profile_vector_assignment_count"],
        ) == (8, 12, 16, 28, 224),
        "positive_digests_unique_and_reproducible": len({vector["expected_sha256"] for vector in positive_vectors}) == 12
        and all(vector["expected_sha256"] == canonical_digest(vector["domain_tag"], vector["synthetic_canonical_object"]) for vector in positive_vectors),
        "negative_taxonomy_exact": {vector["expected_error_code"] for vector in negative_vectors} == set(adapter["error_codes"]),
        "metadata_16_outcomes_8_states_6_rules_8_steps_10": (
            summary["authenticity_metadata_field_count"],
            summary["verification_outcome_count"],
            summary["key_lifecycle_state_count"],
            summary["rotation_rule_count"],
            summary["verification_step_count"],
        ) == (16, 8, 6, 8, 10),
        "no_algorithm_key_or_signature_material": authenticity_contract["selected_runtime_algorithm_profile"] is None
        and not authenticity_contract["private_key_material_persisted"]
        and not authenticity_contract["public_key_material_persisted"]
        and not authenticity_contract["signature_bytes_persisted"],
        "all_vectors_synthetic": all(vector["synthetic_only"] and not vector["contains_business_value"] for vector in positive_vectors + negative_vectors),
        "all_runtime_and_readiness_zero": summary["selected_algorithm_profile_count"]
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
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_SYNTHETIC_CANONICAL_VECTOR_AND_RECEIPT_VERIFICATION_DESIGN",
            "continuation_complete": False,
            "runtime_signing_verification_or_key_selection_authorized": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "cryptographic_keys_or_signatures_created_or_loaded": 0,
            "verification_runs": 0,
            "write_access_created": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "adapter_error_codes": adapter["error_codes"],
        "canonical_positive_vectors": positive_vectors,
        "negative_error_vectors": negative_vectors,
        "profile_vector_assignments": assignments,
        "authenticity_metadata_fields": AUTHENTICITY_METADATA_FIELDS,
        "verification_outcomes": VERIFICATION_OUTCOMES,
        "key_lifecycle_states": KEY_LIFECYCLE_STATES,
        "rotation_rules": ROTATION_RULES,
        "verification_steps": VERIFICATION_STEPS,
        "receipt_authenticity_contract": authenticity_contract,
        "prohibited_persistence_categories": [
            "private_key_material",
            "public_key_material",
            "signature_bytes",
            "raw_rows_items_values_or_identifiers",
            "rendered_documents_or_export_files",
            "credentials_connection_strings_tokens_or_endpoints",
        ],
        "verification_rule": "only AUTHENTIC_CURRENT may proceed to independent adjudication; authenticity proves receipt integrity and provenance metadata, not result parity, owner acceptance, CG-05 closure or readiness",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "Canonical positive vectors contain synthetic tokens only; they are not business fixtures or runtime adapter executions.",
            "No algorithm suite is selected and no private key, public key or signature bytes are created, loaded or stored.",
            "No signing, verification, receipt acceptance, parity, UAT or readiness is claimed.",
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

