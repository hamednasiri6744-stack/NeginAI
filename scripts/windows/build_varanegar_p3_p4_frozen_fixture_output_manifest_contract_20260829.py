"""Build frozen-fixture and output-manifest contracts for the eight P3/P4 packets."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "cg05": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.json",
    "cg05_checkpoint": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_checkpoint_20260829.json",
    "reporting_golden": "artifacts/varanegar_analysis/varanegar_reporting_output_golden_uat_cases_20260829.json",
    "report_fixture_design": "artifacts/varanegar_analysis/varanegar_report_golden_fixture_design_20260829.json",
    "formula_policy": "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_matrix_20260829.json",
    "report_gate": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json",
    "outcome_envelope": "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_envelope_20260829.json",
    "playbook": "artifacts/varanegar_analysis/varanegar_reporting_output_expert_playbook_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

FIXTURE_MANIFEST_FIELDS = [
    "fixture_manifest_id",
    "cg05_packet_id",
    "golden_case_set_sha256",
    "golden_case_id_reference",
    "collection_environment_class",
    "dataset_snapshot_reference",
    "dataset_snapshot_sha256",
    "query_template_projection_version_sha256",
    "parameter_schema_sha256",
    "policy_and_configuration_version_reference",
    "as_of_cutoff_and_source_watermark_reference",
    "authorization_scope_reference",
    "locale_timezone_calendar_reference",
    "currency_unit_rate_reference",
    "redaction_attestation",
    "captured_at",
]

OUTPUT_MANIFEST_FIELDS = [
    "output_manifest_id",
    "fixture_manifest_id",
    "capture_side",
    "output_kind",
    "row_or_item_count_category",
    "stable_key_set_sha256",
    "canonical_rowset_or_itemset_sha256",
    "grain_schema_sha256",
    "stable_ordering_sha256",
    "aggregate_vector_sha256",
    "formula_and_projection_version_sha256",
    "render_or_file_content_sha256",
    "mime_format_encoding_locale_reference",
    "page_sheet_file_structure_sha256",
    "per_item_outcome_set_sha256",
    "produced_at",
]

COMPARISON_MANIFEST_FIELDS = [
    "comparison_manifest_id",
    "legacy_output_manifest_id",
    "target_output_manifest_id",
    "parity_dimension_disposition_map_sha256",
    "stable_key_set_difference_sha256",
    "row_or_item_count_difference_category",
    "canonical_value_difference_sha256",
    "formula_and_aggregate_difference_sha256",
    "ordering_and_pagination_difference_sha256",
    "render_or_file_difference_sha256",
    "per_item_outcome_difference_sha256",
    "explained_difference_reference",
    "accepted_exception_reference",
    "accountable_role_receipt_reference",
    "comparison_status",
    "compared_at",
]

ACQUISITION_STEPS = [
    "accept_scoped_owner_rosters_and_separation_of_duties",
    "freeze_case_set_dataset_snapshot_policy_and_query_versions",
    "obtain_separate_authorization_for_isolated_legacy_and_target_capture",
    "capture_redacted_hash_only_output_manifests_for_both_sides",
    "build_dimension_level_comparison_manifest_without_raw_values",
    "adjudicate_differences_exceptions_conflicts_and_supersession",
    "accept_cg05_receipts_and_owner_decision_or_keep_packet_open",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_ids(values: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / value for name, value in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}

    cases_by_command = {}
    for case in documents["reporting_golden"]["cases"]:
        cases_by_command.setdefault(case["command"], []).append(case)
    contracts = []
    for index, packet in enumerate(documents["cg05"]["cg05_packets"], 1):
        cases = sorted(cases_by_command[packet["newer_action_or_surface"]], key=lambda case: case["case_id"])
        case_ids = [case["case_id"] for case in cases]
        case_kinds = Counter(case["case_kind"] for case in cases)
        contracts.append(
            {
                "fixture_contract_id": f"P34-FOM-{index:02d}",
                "cg05_packet_id": packet["cg05_packet_id"],
                "lane": packet["lane"],
                "source_packet_id": packet["source_packet_id"],
                "command_or_surface": packet["newer_action_or_surface"],
                "output_kind": "REPORT_COMMAND_RENDER_OR_DOCUMENT" if packet["lane"] == "P3" else "EXPORT_FILE",
                "golden_case_count": len(cases),
                "golden_case_ids": case_ids,
                "golden_case_id_set_sha256": digest_ids(case_ids),
                "golden_case_kind_distribution": dict(sorted(case_kinds.items())),
                "required_parity_dimension_ids": packet["required_parity_dimension_ids"],
                "cg05_receipt_slot_ids": packet["cg05_receipt_slot_ids"],
                "accountable_role_types": packet["accountable_role_types"],
                "required_fixture_manifest_fields": FIXTURE_MANIFEST_FIELDS,
                "required_output_manifest_fields": OUTPUT_MANIFEST_FIELDS,
                "required_comparison_manifest_fields": COMPARISON_MANIFEST_FIELDS,
                "required_capture_sides": ["LEGACY_REFERENCE", "TARGET_CANDIDATE"],
                "required_acquisition_steps": ACQUISITION_STEPS,
                "accepted_owner_roster_count": 0,
                "captured_fixture_manifest_count": 0,
                "captured_output_manifest_count": 0,
                "captured_comparison_manifest_count": 0,
                "accepted_parity_dimension_count": 0,
                "accepted_cg05_receipt_count": 0,
                "result_parity_proven": False,
                "owner_approved": False,
                "current_status": "DESIGNED_NOT_CAPTURED_SEPARATE_AUTHORIZATION_REQUIRED",
                "operational_execution_authorized": False,
                "readiness_effect": "ZERO",
            }
        )

    golden_summary = documents["reporting_golden"]["summary"]
    summary = {
        "fixture_contract_count": len(contracts),
        "p3_fixture_contract_count": sum(contract["lane"] == "P3" for contract in contracts),
        "p4_fixture_contract_count": sum(contract["lane"] == "P4" for contract in contracts),
        "covered_golden_case_count": sum(contract["golden_case_count"] for contract in contracts),
        "case_count_per_contract": len(contracts[0]["golden_case_ids"]),
        "fixture_manifest_field_count": len(FIXTURE_MANIFEST_FIELDS),
        "output_manifest_field_count": len(OUTPUT_MANIFEST_FIELDS),
        "comparison_manifest_field_count": len(COMPARISON_MANIFEST_FIELDS),
        "manifest_field_assignment_count": len(contracts)
        * (len(FIXTURE_MANIFEST_FIELDS) + 2 * len(OUTPUT_MANIFEST_FIELDS) + len(COMPARISON_MANIFEST_FIELDS)),
        "required_capture_side_count": len(contracts) * 2,
        "acquisition_step_count": len(ACQUISITION_STEPS),
        "acquisition_step_assignment_count": len(contracts) * len(ACQUISITION_STEPS),
        "required_parity_dimension_assignment_count": sum(len(contract["required_parity_dimension_ids"]) for contract in contracts),
        "cg05_receipt_slot_assignment_count": sum(len(contract["cg05_receipt_slot_ids"]) for contract in contracts),
        "accepted_owner_roster_count": 0,
        "captured_fixture_manifest_count": 0,
        "captured_output_manifest_count": 0,
        "captured_comparison_manifest_count": 0,
        "accepted_parity_dimension_count": 0,
        "accepted_cg05_receipt_count": 0,
        "result_parity_proven_contract_count": 0,
        "owner_approved_contract_count": 0,
        "executed_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_fixture_contract": 1404,
        "design_lower_bound_after_fixture_contract": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }

    expected_case_kinds = {"authorization": 1, "failure_injection": 2, "idempotency": 1, "partial_failure": 1, "success": 1, "versioning": 1}
    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "contracts_8_p3_5_p4_3_cases_56_seven_each": (
            summary["fixture_contract_count"],
            summary["p3_fixture_contract_count"],
            summary["p4_fixture_contract_count"],
            summary["covered_golden_case_count"],
            summary["case_count_per_contract"],
        ) == (8, 5, 3, 56, 7),
        "exact_action_mapping": set(cases_by_command) == {contract["command_or_surface"] for contract in contracts},
        "case_kind_distribution_per_contract": all(contract["golden_case_kind_distribution"] == expected_case_kinds for contract in contracts),
        "manifest_fields_16_16_16_assignments_512": (
            summary["fixture_manifest_field_count"],
            summary["output_manifest_field_count"],
            summary["comparison_manifest_field_count"],
            summary["manifest_field_assignment_count"],
        ) == (16, 16, 16, 512),
        "capture_sides_16_steps_7_assignments_56": (
            summary["required_capture_side_count"],
            summary["acquisition_step_count"],
            summary["acquisition_step_assignment_count"],
        ) == (16, 7, 56),
        "dimensions_160_receipts_27": (
            summary["required_parity_dimension_assignment_count"],
            summary["cg05_receipt_slot_assignment_count"],
        ) == (160, 27),
        "case_hashes_unique": len({contract["golden_case_id_set_sha256"] for contract in contracts}) == 8,
        "all_designed_not_captured": all(
            contract["accepted_owner_roster_count"] == 0
            and contract["captured_fixture_manifest_count"] == 0
            and contract["captured_output_manifest_count"] == 0
            and contract["captured_comparison_manifest_count"] == 0
            and contract["accepted_parity_dimension_count"] == 0
            and contract["accepted_cg05_receipt_count"] == 0
            and contract["result_parity_proven"] is False
            and contract["owner_approved"] is False
            and contract["current_status"] == "DESIGNED_NOT_CAPTURED_SEPARATE_AUTHORIZATION_REQUIRED"
            and contract["operational_execution_authorized"] is False
            and contract["readiness_effect"] == "ZERO"
            for contract in contracts
        ),
        "execution_readiness_zero": summary["captured_fixture_manifest_count"]
        == summary["captured_output_manifest_count"]
        == summary["captured_comparison_manifest_count"]
        == summary["result_parity_proven_contract_count"]
        == summary["owner_approved_contract_count"]
        == summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "source_golden_boundary_honest": golden_summary["case_count"] == 56 and golden_summary["executed_case_count"] == 0,
        "non_additive_1404": summary["design_lower_bound_before_fixture_contract"]
        == summary["design_lower_bound_after_fixture_contract"]
        == 1404,
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)

    output = {
        "artifact": "varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_FROZEN_FIXTURE_AND_HASH_ONLY_OUTPUT_MANIFEST_DESIGN",
            "continuation_complete": False,
            "capture_or_execution_authorized": False,
        },
        "safety": {
            "database_connections": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "fixture_manifest_fields": FIXTURE_MANIFEST_FIELDS,
        "output_manifest_fields": OUTPUT_MANIFEST_FIELDS,
        "comparison_manifest_fields": COMPARISON_MANIFEST_FIELDS,
        "acquisition_steps": ACQUISITION_STEPS,
        "fixture_contracts": contracts,
        "capture_rule": "this contract does not authorize capture; any legacy or target capture requires separate isolated authorization and may persist only references, hashes, categorical differences and redaction attestations",
        "comparison_rule": "compare stable key sets and grain before aggregates, then formula/value/order/render/file/per-item dimensions; equal totals or file existence cannot close parity",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "Field names define an intake schema; no fixture values, output values, files, identities or credentials are stored.",
            "The 512 field assignments refine existing 56 Golden/UAT cases and do not increase the design lower bound.",
            "No capture, execution, comparison result, parity, owner approval or readiness is claimed.",
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
