"""Build an offline synthetic conformance record and an open crypto-provider decision record."""
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
    "vectors": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.json",
    "vectors_checkpoint": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_checkpoint_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

STANDARDS_REFERENCES = [
    {
        "reference_id": "NIST_FIPS_186_5",
        "title": "Digital Signature Standard (DSS)",
        "url": "https://csrc.nist.gov/pubs/fips/186-5/final",
        "decision_use": "classical signature candidate standards baseline",
    },
    {
        "reference_id": "NIST_SP_800_57_PT1_R5",
        "title": "Recommendation for Key Management: Part 1 - General",
        "url": "https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final",
        "decision_use": "key lifecycle and protection criteria",
    },
    {
        "reference_id": "RFC_8032",
        "title": "Edwards-Curve Digital Signature Algorithm (EdDSA)",
        "url": "https://www.rfc-editor.org/info/rfc8032/",
        "decision_use": "Ed25519 interoperability candidate reference",
    },
    {
        "reference_id": "RFC_8017",
        "title": "PKCS #1: RSA Cryptography Specifications Version 2.2",
        "url": "https://www.rfc-editor.org/info/rfc8017/",
        "decision_use": "RSASSA-PSS interoperability candidate reference",
    },
    {
        "reference_id": "NIST_CSWP_39_UPD1",
        "title": "Considerations for Achieving Crypto Agility: Strategies and Practices",
        "url": "https://csrc.nist.gov/pubs/cswp/39/upd1/considerations-for-achieving-crypto-agility/final",
        "decision_use": "algorithm transition and crypto-agility criteria",
    },
    {
        "reference_id": "NIST_FIPS_204",
        "title": "Module-Lattice-Based Digital Signature Standard",
        "url": "https://csrc.nist.gov/pubs/fips/204/final",
        "decision_use": "post-quantum migration candidate reference",
    },
]

ALGORITHM_CANDIDATES = [
    {
        "candidate_id": "RSA_PSS_SHA256_CANDIDATE",
        "family": "RSA",
        "standards_references": ["NIST_FIPS_186_5", "RFC_8017"],
        "selection_status": "CANDIDATE_NOT_SELECTED",
        "decision_note": "Interoperability candidate; parameter profile and provider support require owner approval.",
    },
    {
        "candidate_id": "ECDSA_P256_SHA256_CANDIDATE",
        "family": "ECDSA",
        "standards_references": ["NIST_FIPS_186_5"],
        "selection_status": "CANDIDATE_NOT_SELECTED",
        "decision_note": "Classical elliptic-curve candidate; implementation and deterministic-signing policy remain open.",
    },
    {
        "candidate_id": "ED25519_CANDIDATE",
        "family": "EdDSA",
        "standards_references": ["NIST_FIPS_186_5", "RFC_8032"],
        "selection_status": "CANDIDATE_NOT_SELECTED",
        "decision_note": "Compact-signature candidate; runtime and provider interoperability remain open.",
    },
    {
        "candidate_id": "ML_DSA_MIGRATION_CANDIDATE",
        "family": "post_quantum",
        "standards_references": ["NIST_FIPS_204", "NIST_CSWP_39_UPD1"],
        "selection_status": "CANDIDATE_NOT_SELECTED",
        "decision_note": "Migration/agility candidate only; no deployment or hybrid-composition decision is implied.",
    },
]

PROVIDER_PATTERNS = [
    {
        "candidate_id": "MANAGED_KMS_NON_EXPORTABLE_PATTERN",
        "pattern": "managed_key_management_service",
        "selection_status": "CANDIDATE_NOT_SELECTED",
        "private_key_export_required": False,
    },
    {
        "candidate_id": "HSM_BACKED_PATTERN",
        "pattern": "dedicated_or_managed_hardware_security_module",
        "selection_status": "CANDIDATE_NOT_SELECTED",
        "private_key_export_required": False,
    },
    {
        "candidate_id": "PLATFORM_NATIVE_KEYSTORE_PATTERN",
        "pattern": "operating_platform_native_keystore",
        "selection_status": "CANDIDATE_NOT_SELECTED",
        "private_key_export_required": False,
    },
    {
        "candidate_id": "EXTERNAL_SIGNING_SERVICE_PATTERN",
        "pattern": "separately_operated_signing_service",
        "selection_status": "CANDIDATE_NOT_SELECTED",
        "private_key_export_required": False,
    },
]

DECISION_CRITERIA = [
    "approved_standard_and_compliance_fit",
    "runtime_library_interoperability",
    "provider_algorithm_and_parameter_support",
    "non_exportable_private_key_enforcement",
    "verify_only_access_to_retired_public_key_versions",
    "rotation_and_supersession_atomicity",
    "revocation_propagation_and_fail_closed_behavior",
    "immutable_audit_and_receipt_linkage",
    "iam_least_privilege_and_segregation_of_duties",
    "latency_availability_and_retry_semantics",
    "offline_verification_and_long_term_evidence",
    "backup_recovery_and_provider_exit_strategy",
    "post_quantum_transition_and_crypto_agility",
    "regional_residency_procurement_and_vendor_constraints",
]

DECISION_GATES = [
    "platform_owner_approval",
    "security_owner_approval",
    "compliance_and_legal_profile_confirmation",
    "threat_model_review",
    "deployment_environment_and_trust_boundary_confirmation",
    "provider_capability_and_non_exportability_evidence",
    "synthetic_performance_and_failure_benchmark",
    "rotation_revocation_and_disaster_recovery_drill_plan",
    "crypto_agility_and_post_quantum_migration_plan",
    "isolated_uat_and_rollback_plan",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_digest(vector: dict) -> str:
    canonical = json.dumps(
        vector["synthetic_canonical_object"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256((vector["domain_tag"] + "\0" + canonical).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    adapter = documents["adapter"]
    vectors = documents["vectors"]
    official = documents["tests"]

    positive_by_id = {vector["test_vector_id"]: vector for vector in vectors["canonical_positive_vectors"]}
    negative_by_id = {vector["test_vector_id"]: vector for vector in vectors["negative_error_vectors"]}
    digest_results = []
    taxonomy_results = []
    for assignment in vectors["profile_vector_assignments"]:
        profile_id = assignment["adapter_profile_id"]
        for vector_id in assignment["test_vector_ids"]:
            if vector_id in positive_by_id:
                vector = positive_by_id[vector_id]
                observed = canonical_digest(vector)
                digest_results.append(
                    {
                        "adapter_profile_id": profile_id,
                        "test_vector_id": vector_id,
                        "evaluation_scope": "OFFLINE_SYNTHETIC_REFERENCE_HASH_ONLY",
                        "expected_sha256": vector["expected_sha256"],
                        "observed_sha256": observed,
                        "validation": "PASS" if observed == vector["expected_sha256"] else "FAIL",
                        "operational_adapter_execution": False,
                        "result_parity_claimed": False,
                    }
                )
            else:
                vector = negative_by_id[vector_id]
                taxonomy_results.append(
                    {
                        "adapter_profile_id": profile_id,
                        "test_vector_id": vector_id,
                        "expected_error_code": vector["expected_error_code"],
                        "expected_typed_status": vector["expected_typed_status"],
                        "validation": "PASS"
                        if vector["expected_error_code"] in vectors["adapter_error_codes"]
                        else "FAIL",
                        "lint_scope": "STATIC_ERROR_TAXONOMY_MEMBERSHIP_ONLY",
                        "runtime_error_injected": False,
                        "operational_adapter_execution": False,
                    }
                )

    candidates = ALGORITHM_CANDIDATES + PROVIDER_PATTERNS
    criterion_assignments = [
        {
            "candidate_id": candidate["candidate_id"],
            "criterion_id": criterion,
            "assessment_status": "REQUIRES_OWNER_EVIDENCE",
            "evidence_received_count": 0,
        }
        for candidate in candidates
        for criterion in DECISION_CRITERIA
    ]
    summary = {
        "adapter_profile_count": len(adapter["adapter_profiles"]),
        "positive_vector_count": len(positive_by_id),
        "negative_vector_count": len(negative_by_id),
        "offline_digest_evaluation_count": len(digest_results),
        "offline_digest_pass_count": sum(item["validation"] == "PASS" for item in digest_results),
        "offline_digest_fail_count": sum(item["validation"] != "PASS" for item in digest_results),
        "negative_taxonomy_lint_count": len(taxonomy_results),
        "negative_taxonomy_lint_pass_count": sum(item["validation"] == "PASS" for item in taxonomy_results),
        "standards_reference_count": len(STANDARDS_REFERENCES),
        "algorithm_candidate_count": len(ALGORITHM_CANDIDATES),
        "provider_pattern_count": len(PROVIDER_PATTERNS),
        "decision_criterion_count": len(DECISION_CRITERIA),
        "candidate_criterion_assignment_count": len(criterion_assignments),
        "decision_gate_count": len(DECISION_GATES),
        "selected_algorithm_count": 0,
        "selected_provider_count": 0,
        "key_material_created_or_loaded_count": 0,
        "signature_created_or_loaded_count": 0,
        "signing_run_count": 0,
        "cryptographic_verification_run_count": 0,
        "operational_adapter_run_count": 0,
        "accepted_receipt_count": 0,
        "result_parity_proven_profile_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_conformance_contract": 1404,
        "design_lower_bound_after_conformance_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(
            documents[name].get("validation") == "PASS"
            for name in ("adapter", "adapter_checkpoint", "vectors", "vectors_checkpoint", "tests")
        ),
        "profiles_8_vectors_12_16": summary["adapter_profile_count"] == 8
        and summary["positive_vector_count"] == 12
        and summary["negative_vector_count"] == 16,
        "digest_evaluations_96_all_pass": summary["offline_digest_evaluation_count"]
        == summary["offline_digest_pass_count"]
        == 96
        and summary["offline_digest_fail_count"] == 0,
        "taxonomy_lints_128_all_pass": summary["negative_taxonomy_lint_count"]
        == summary["negative_taxonomy_lint_pass_count"]
        == 128,
        "decision_matrix_4_4_14_112_10": (
            summary["algorithm_candidate_count"],
            summary["provider_pattern_count"],
            summary["decision_criterion_count"],
            summary["candidate_criterion_assignment_count"],
            summary["decision_gate_count"],
        )
        == (4, 4, 14, 112, 10),
        "algorithm_and_provider_unselected": summary["selected_algorithm_count"]
        == summary["selected_provider_count"]
        == 0,
        "no_key_signature_or_crypto_runtime": summary["key_material_created_or_loaded_count"]
        == summary["signature_created_or_loaded_count"]
        == summary["signing_run_count"]
        == summary["cryptographic_verification_run_count"]
        == 0,
        "operational_parity_and_readiness_zero": summary["operational_adapter_run_count"]
        == summary["accepted_receipt_count"]
        == summary["result_parity_proven_profile_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_conformance_contract"]
        == summary["design_lower_bound_after_conformance_contract"]
        == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "offline_synthetic_reference_hash_conformance_and_open_decision_record",
            "continuation_complete": False,
            "operational_adapter_signing_verification_or_key_access_authorized": False,
            "standards_reviewed_at": "2026-08-31",
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes_to_varanegar_or_erp": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "key_material_created_or_loaded": 0,
            "signature_bytes_created_or_loaded": 0,
            "operational_adapter_or_crypto_runs": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "canonical_positive_vectors": vectors["canonical_positive_vectors"],
        "adapter_error_codes": vectors["adapter_error_codes"],
        "offline_digest_conformance_results": digest_results,
        "negative_taxonomy_lint_results": taxonomy_results,
        "conformance_interpretation": {
            "what_pass_proves": "the checked-in synthetic canonical objects reproduce their checked-in domain-separated SHA-256 digests and negative vectors reference declared error codes",
            "what_pass_does_not_prove": [
                "target ERP adapter implementation correctness",
                "legacy or target output result parity",
                "cryptographic signature authenticity",
                "provider availability security or performance",
                "CG-05 closure UAT command readiness or pilot readiness",
            ],
        },
        "decision_status": "NEEDS_PLATFORM_SECURITY_OWNER_DECISION",
        "standards_references": STANDARDS_REFERENCES,
        "algorithm_candidates": ALGORITHM_CANDIDATES,
        "provider_patterns": PROVIDER_PATTERNS,
        "decision_criteria": DECISION_CRITERIA,
        "candidate_criterion_assignments": criterion_assignments,
        "decision_gates": [
            {"gate_id": gate, "status": "OPEN", "accepted_evidence_count": 0}
            for gate in DECISION_GATES
        ],
        "selection_rule": {
            "automatic_selection_allowed": False,
            "all_decision_gates_must_close": True,
            "security_and_platform_owner_approval_required": True,
            "selected_profile_must_be_versioned_and_receipted": True,
            "provider_private_key_export_allowed": False,
            "crypto_agility_transition_plan_required": True,
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
                "path": "scripts/windows/build_varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "The positive run is a local reference-hash calculation over synthetic tokens, not an operational adapter run.",
            "Negative vectors are taxonomy lints; no runtime fault was injected.",
            "Candidate algorithms and provider patterns are not recommendations or selections.",
            "No key material, signature bytes, business values, credentials, PII, database access, network access to Varanegar, or assembly execution occurred.",
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

