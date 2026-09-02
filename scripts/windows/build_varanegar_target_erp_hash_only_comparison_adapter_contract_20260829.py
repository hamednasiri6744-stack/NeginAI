"""Build the target ERP hash-only comparison adapter contract for P3/P4 outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "adjudication": "artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.json",
    "adjudication_checkpoint": "artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_checkpoint_20260829.json",
    "fixture_contract": "artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.json",
    "diagnostic_playbook": "artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.json",
    "cg05": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.json",
    "formula_policy": "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_matrix_20260829.json",
    "receipt_validation": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.json",
    "target_blueprint": "artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

INPUT_ENVELOPE_FIELDS = [
    "comparison_request_id",
    "idempotency_key",
    "adapter_profile_id",
    "adapter_profile_version_sha256",
    "fixture_contract_id",
    "fixture_manifest_reference",
    "fixture_manifest_sha256",
    "legacy_output_manifest_reference",
    "legacy_output_manifest_sha256",
    "target_output_manifest_reference",
    "target_output_manifest_sha256",
    "golden_case_id_set_sha256",
    "requested_parity_dimension_id_set_sha256",
    "canonicalization_policy_version_sha256",
    "scope_policy_version_sha256",
    "locale_timezone_calendar_policy_version_sha256",
    "requested_at",
    "requesting_role_receipt_reference",
]

OUTPUT_RECEIPT_FIELDS = [
    "comparison_receipt_id",
    "comparison_request_id",
    "idempotency_key",
    "adapter_profile_id",
    "adapter_profile_version_sha256",
    "input_envelope_sha256",
    "canonicalization_policy_version_sha256",
    "legacy_canonical_manifest_sha256",
    "target_canonical_manifest_sha256",
    "parity_dimension_disposition_map_sha256",
    "matched_dimension_count",
    "different_dimension_count",
    "invalid_or_unknown_dimension_count",
    "typed_status",
    "error_code_set_sha256",
    "adjudication_route_reference",
    "produced_at",
    "receipt_sha256",
]

CANONICALIZATION_STAGES = [
    "validate_manifest_schema_hashes_versions_and_packet_scope",
    "validate_exact_case_set_dimension_set_and_capture_sides",
    "normalize_envelope_keys_and_type_tags_with_versioned_profile",
    "normalize_unicode_text_for_hashing_without_persisting_text",
    "normalize_temporal_locale_calendar_and_timezone_references",
    "normalize_decimal_scale_rounding_currency_unit_and_rate_references",
    "preserve_null_missing_empty_zero_and_unknown_as_distinct_type_tags",
    "derive_domain_separated_stable_key_and_row_or_item_hashes",
    "derive_order_independent_set_hash_and_separate_order_hash",
    "derive_grain_aggregate_render_file_and_per_item_hash_vectors",
    "compare_each_requested_dimension_and_apply_typed_error_taxonomy",
    "emit_hash_only_dimension_dispositions_and_receipt",
]

ERROR_CODES = [
    "MANIFEST_MISSING",
    "MANIFEST_HASH_MISMATCH",
    "SCHEMA_VERSION_UNSUPPORTED",
    "ADAPTER_PROFILE_VERSION_MISMATCH",
    "FIXTURE_OR_CASE_SET_MISMATCH",
    "CAPTURE_SIDE_MISSING_OR_DUPLICATED",
    "DIMENSION_SET_MISMATCH",
    "SCOPE_POLICY_VERSION_MISMATCH",
    "LOCALE_TIMEZONE_CALENDAR_AMBIGUOUS",
    "DECIMAL_ROUNDING_CURRENCY_POLICY_AMBIGUOUS",
    "STABLE_KEY_MISSING_OR_DUPLICATED",
    "GRAIN_OR_CARDINALITY_MISMATCH",
    "CANONICAL_SERIALIZATION_FAILURE",
    "PARTIAL_OR_UNKNOWN_OUTCOME",
    "IDEMPOTENCY_CONFLICT",
    "RAW_PAYLOAD_PERSISTENCE_ATTEMPT",
]

TYPED_STATUSES = [
    "MATCH_CANDIDATE_AWAITING_ADJUDICATION",
    "DIFFERENCE_REQUIRES_DIAGNOSTIC_PLAYBOOK",
    "INVALID_EVIDENCE_RECOLLECTION_REQUIRED",
    "UNSUPPORTED_PROFILE_OR_SCHEMA",
    "CONFLICT_OR_SUPERSESSION_BLOCK",
    "PARTIAL_OR_UNKNOWN_BLOCK",
]

PROHIBITED_PERSISTENCE_CATEGORIES = [
    "raw_rows_or_items",
    "raw_business_values_or_aggregates",
    "raw_stable_keys_or_entity_identifiers",
    "customer_or_counterparty_identity",
    "rendered_documents_or_export_files",
    "report_parameters_or_filter_values",
    "credentials_connection_strings_or_tokens",
    "raw_rule_formula_or_sql_text",
    "network_or_database_endpoints",
    "unredacted_exception_or_operator_notes",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / value for name, value in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    fixtures = documents["fixture_contract"]["fixture_contracts"]
    adjudication_by_fixture = {
        route["fixture_contract_id"]: route for route in documents["adjudication"]["packet_adjudication_routes"]
    }
    profiles = []
    for index, fixture in enumerate(fixtures, 1):
        adjudication = adjudication_by_fixture[fixture["fixture_contract_id"]]
        profiles.append(
            {
                "adapter_profile_id": f"P34-HCA-{index:02d}",
                "adapter_profile_version": "1.0.0-DESIGN",
                "fixture_contract_id": fixture["fixture_contract_id"],
                "cg05_packet_id": fixture["cg05_packet_id"],
                "lane": fixture["lane"],
                "command_or_surface": fixture["command_or_surface"],
                "output_kind": fixture["output_kind"],
                "golden_case_count": fixture["golden_case_count"],
                "golden_case_id_set_sha256": fixture["golden_case_id_set_sha256"],
                "required_parity_dimension_ids": fixture["required_parity_dimension_ids"],
                "cg05_receipt_slot_ids": fixture["cg05_receipt_slot_ids"],
                "promotion_guard_ids": adjudication["promotion_guard_ids"],
                "input_envelope_fields": INPUT_ENVELOPE_FIELDS,
                "output_receipt_fields": OUTPUT_RECEIPT_FIELDS,
                "canonicalization_stage_ids": [f"CS-{stage:02d}" for stage in range(1, len(CANONICALIZATION_STAGES) + 1)],
                "raw_payload_persistence_allowed": False,
                "implementation_count": 0,
                "adapter_request_count": 0,
                "comparison_run_count": 0,
                "emitted_receipt_count": 0,
                "accepted_receipt_count": 0,
                "result_parity_proven": False,
                "current_status": "DESIGNED_NOT_IMPLEMENTED_OR_RUN",
                "readiness_effect": "ZERO",
            }
        )

    summary = {
        "adapter_profile_count": len(profiles),
        "p3_profile_count": sum(profile["lane"] == "P3" for profile in profiles),
        "p4_profile_count": sum(profile["lane"] == "P4" for profile in profiles),
        "covered_golden_case_count": sum(profile["golden_case_count"] for profile in profiles),
        "input_envelope_field_count": len(INPUT_ENVELOPE_FIELDS),
        "output_receipt_field_count": len(OUTPUT_RECEIPT_FIELDS),
        "canonicalization_stage_count": len(CANONICALIZATION_STAGES),
        "error_code_count": len(ERROR_CODES),
        "typed_status_count": len(TYPED_STATUSES),
        "profile_schema_field_assignment_count": len(profiles) * (len(INPUT_ENVELOPE_FIELDS) + len(OUTPUT_RECEIPT_FIELDS)),
        "canonicalization_stage_assignment_count": len(profiles) * len(CANONICALIZATION_STAGES),
        "parity_dimension_assignment_count": sum(len(profile["required_parity_dimension_ids"]) for profile in profiles),
        "cg05_receipt_assignment_count": sum(len(profile["cg05_receipt_slot_ids"]) for profile in profiles),
        "promotion_guard_assignment_count": sum(len(profile["promotion_guard_ids"]) for profile in profiles),
        "adapter_implementation_count": 0,
        "adapter_request_count": 0,
        "canonicalization_run_count": 0,
        "comparison_run_count": 0,
        "emitted_receipt_count": 0,
        "accepted_receipt_count": 0,
        "result_parity_proven_profile_count": 0,
        "executed_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_adapter_contract": 1404,
        "design_lower_bound_after_adapter_contract": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    digest_contract = {
        "hash_algorithm": "SHA-256",
        "profile_version_hash_required": True,
        "domain_separation_required": True,
        "typed_scalar_serialization_required": True,
        "floating_point_serialization_allowed": False,
        "decimal_values_canonicalized_by_versioned_scale_and_rounding_policy": True,
        "null_missing_empty_zero_unknown_distinct": True,
        "set_hash_and_order_hash_separate": True,
        "raw_value_persistence_allowed": False,
    }
    idempotency_contract = {
        "key_components": [
            "adapter_profile_version_sha256",
            "fixture_manifest_sha256",
            "legacy_output_manifest_sha256",
            "target_output_manifest_sha256",
            "requested_parity_dimension_id_set_sha256",
        ],
        "same_key_same_inputs": "RETURN_ORIGINAL_RECEIPT_HASH",
        "same_key_different_inputs": "REJECT_IDEMPOTENCY_CONFLICT",
        "retry_after_unknown": "READ_RECEIPT_BY_KEY_BEFORE_RETRY",
        "receipt_immutability": "APPEND_SUPERSEDING_RECEIPT_NEVER_OVERWRITE",
    }
    checks = {
        "sources_pass": all(
            document.get("validation") == "PASS"
            for name, document in documents.items()
            if name != "target_blueprint"
        )
        and documents["target_blueprint"]["module_count"] == 14,
        "profiles_8_p3_5_p4_3_cases_56": (
            summary["adapter_profile_count"], summary["p3_profile_count"], summary["p4_profile_count"], summary["covered_golden_case_count"]
        ) == (8, 5, 3, 56),
        "schemas_18_18_stages_12_errors_16_statuses_6": (
            summary["input_envelope_field_count"],
            summary["output_receipt_field_count"],
            summary["canonicalization_stage_count"],
            summary["error_code_count"],
            summary["typed_status_count"],
        ) == (18, 18, 12, 16, 6),
        "schema_assignments_288_stage_assignments_96": (
            summary["profile_schema_field_assignment_count"], summary["canonicalization_stage_assignment_count"]
        ) == (288, 96),
        "dimensions_160_receipts_27_guards_96": (
            summary["parity_dimension_assignment_count"],
            summary["cg05_receipt_assignment_count"],
            summary["promotion_guard_assignment_count"],
        ) == (160, 27, 96),
        "digest_contract_hash_only": digest_contract["hash_algorithm"] == "SHA-256"
        and digest_contract["domain_separation_required"]
        and not digest_contract["floating_point_serialization_allowed"]
        and not digest_contract["raw_value_persistence_allowed"],
        "idempotency_five_components_and_conflict_rejection": len(idempotency_contract["key_components"]) == 5
        and idempotency_contract["same_key_same_inputs"] == "RETURN_ORIGINAL_RECEIPT_HASH"
        and idempotency_contract["same_key_different_inputs"] == "REJECT_IDEMPOTENCY_CONFLICT",
        "raw_persistence_denied": len(PROHIBITED_PERSISTENCE_CATEGORIES) == 10
        and all(not profile["raw_payload_persistence_allowed"] for profile in profiles),
        "all_not_implemented_or_run": all(
            profile["implementation_count"]
            == profile["adapter_request_count"]
            == profile["comparison_run_count"]
            == profile["emitted_receipt_count"]
            == profile["accepted_receipt_count"]
            == 0
            and profile["result_parity_proven"] is False
            and profile["current_status"] == "DESIGNED_NOT_IMPLEMENTED_OR_RUN"
            and profile["readiness_effect"] == "ZERO"
            for profile in profiles
        ),
        "execution_readiness_zero": summary["adapter_implementation_count"]
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
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_target_erp_hash_only_comparison_adapter_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_TARGET_ERP_HASH_ONLY_COMPARISON_ADAPTER_DESIGN",
            "continuation_complete": False,
            "implementation_capture_or_execution_authorized": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "adapter_implementations_or_runs": 0,
            "write_access_created": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "input_envelope_fields": INPUT_ENVELOPE_FIELDS,
        "canonicalization_stages": CANONICALIZATION_STAGES,
        "output_receipt_fields": OUTPUT_RECEIPT_FIELDS,
        "error_codes": ERROR_CODES,
        "typed_statuses": TYPED_STATUSES,
        "digest_contract": digest_contract,
        "idempotency_contract": idempotency_contract,
        "allowed_persistence_categories": [
            "versioned_profile_and_policy_references",
            "manifest_references_and_sha256_digests",
            "case_dimension_and_error_code_set_digests",
            "categorical_counts_and_typed_status",
            "adjudication_and_receipt_references",
            "timestamps_expiry_conflict_and_supersession_references",
        ],
        "prohibited_persistence_categories": PROHIBITED_PERSISTENCE_CATEGORIES,
        "adapter_profiles": profiles,
        "comparison_rule": "validate identity and grain before values or aggregates; compare every requested dimension; equal totals, row counts, render completion or file existence never imply parity",
        "receipt_rule": "emit only references, hashes, typed counts, categorical dispositions and immutable receipt hashes; never persist raw source or target payloads",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This is an adapter contract, not an adapter implementation or runtime comparison result.",
            "No fixture, report, row, item, rendered document, export file, parameter value or identity is stored.",
            "No request, canonicalization run, comparison, receipt acceptance, parity or readiness is claimed.",
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
