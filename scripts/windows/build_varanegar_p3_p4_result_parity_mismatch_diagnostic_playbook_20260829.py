"""Build diagnostic playbooks for P3/P4 result, render and export parity mismatches."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "fixture_contract": "artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.json",
    "fixture_checkpoint": "artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint_20260829.json",
    "cg05": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.json",
    "reporting_playbook": "artifacts/varanegar_analysis/varanegar_reporting_output_expert_playbook_20260829.json",
    "reporting_golden": "artifacts/varanegar_analysis/varanegar_reporting_output_golden_uat_cases_20260829.json",
    "formula_policy": "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_matrix_20260829.json",
    "report_gate": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

COMMON_STEPS = [
    "validate_current_fixture_output_comparison_manifest_hashes",
    "classify_the_first_failed_boundary_without_replaying_or_repairing",
    "pin_the_failed_parity_dimension_and_receipt_slot",
    "verify_fixture_dataset_query_policy_watermark_and_scope_versions",
    "compare_stable_key_sets_grain_and_cardinality_before_totals",
    "compare_canonical_values_formulas_rounding_ordering_and_aggregates",
    "compare_render_file_structure_digest_and_per_item_outcomes_when_applicable",
    "check_expiry_redaction_conflict_supersession_and_exception_references",
    "request_independent_accountable_role_review_and_record_hash_only_evidence",
    "record_match_explained_exception_invalid_evidence_or_unexplained_block_without_promotion",
]

SCENARIOS = [
    ("FIXTURE_OR_VERSION_IDENTITY_MISMATCH", ["P3", "P4"], ["FP-14", "RP-20"]),
    ("STABLE_KEY_SET_OR_INCLUSION_MISMATCH", ["P3", "P4"], ["FP-01", "FP-04", "FP-13"]),
    ("GRAIN_CARDINALITY_OR_MASTER_DETAIL_MISMATCH", ["P3", "P4"], ["FP-01", "FP-09", "FP-13"]),
    ("FORMULA_SIGN_ROUNDING_CURRENCY_OR_CARRY_MISMATCH", ["P3", "P4"], ["FP-05", "FP-06", "FP-07", "FP-08", "FP-10", "FP-14"]),
    ("ORDERING_PAGINATION_SUBTOTAL_OR_TOTAL_MISMATCH", ["P3", "P4"], ["FP-09", "RP-17"]),
    ("REPORT_RENDER_PRESENTATION_OR_COMPLETION_MISMATCH", ["P3"], ["FP-12", "RP-17", "RP-20"]),
    ("EXPORT_SCHEMA_FORMAT_ENCODING_OR_LOCALE_MISMATCH", ["P4"], ["FP-09", "FP-12", "FP-14", "RP-18", "RP-19"]),
    ("FILE_DIGEST_ATOMIC_PUBLISH_OR_SOURCE_IMMUTABILITY_MISMATCH", ["P3", "P4"], ["RP-19", "RP-20"]),
    ("PER_ITEM_PARTIAL_UNKNOWN_OR_COMPLETION_OUTCOME_MISMATCH", ["P3", "P4"], ["RP-15", "RP-16", "RP-19"]),
    ("UNEXPLAINED_DIFFERENCE_EXCEPTION_CONFLICT_OR_SUPERSESSION", ["P3", "P4"], ["FP-02", "FP-03", "FP-11", "FP-14", "RP-20"]),
]

DIAGNOSTIC_OUTCOMES = [
    "MATCH_CONFIRMED_BY_ACCEPTED_HASH_ONLY_EVIDENCE",
    "EXPLAINED_OWNER_APPROVED_VERSIONED_EXCEPTION",
    "INVALID_OR_STALE_EVIDENCE_RECOLLECTION_REQUIRED",
    "UNEXPLAINED_DIFFERENCE_BLOCKS_CG05",
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
    fixture_contracts = documents["fixture_contract"]["fixture_contracts"]
    known_dimension_ids = {dimension["id"] for dimension in documents["cg05"]["parity_dimensions"]}

    playbooks = []
    for index, (scenario, lanes, dimension_ids) in enumerate(SCENARIOS, 1):
        applicable = [contract for contract in fixture_contracts if contract["lane"] in lanes]
        playbooks.append(
            {
                "diagnostic_playbook_id": f"P34-RPD-{index:02d}",
                "scenario": scenario,
                "applicable_lanes": lanes,
                "applicable_fixture_contract_ids": [contract["fixture_contract_id"] for contract in applicable],
                "applicable_packet_count": len(applicable),
                "applicable_golden_case_count": sum(contract["golden_case_count"] for contract in applicable),
                "required_parity_dimension_ids": dimension_ids,
                "steps": COMMON_STEPS,
                "allowed_diagnostic_outcomes": DIAGNOSTIC_OUTCOMES,
                "current_diagnostic_run_count": 0,
                "match_confirmed_count": 0,
                "accepted_exception_count": 0,
                "invalid_evidence_count": 0,
                "unexplained_block_count": 0,
                "repair_or_replay_performed_count": 0,
                "owner_approved_resolution_count": 0,
                "current_status": "DESIGNED_NOT_RUN_NO_CAPTURE_AUTHORIZATION",
                "readiness_effect": "ZERO",
            }
        )

    summary = {
        "diagnostic_playbook_count": len(playbooks),
        "minimum_step_count": min(len(playbook["steps"]) for playbook in playbooks),
        "diagnostic_step_assignment_count": sum(len(playbook["steps"]) for playbook in playbooks),
        "diagnostic_outcome_count": len(DIAGNOSTIC_OUTCOMES),
        "fixture_contract_count": len(fixture_contracts),
        "covered_golden_case_count": documents["fixture_contract"]["summary"]["covered_golden_case_count"],
        "playbook_packet_assignment_count": sum(playbook["applicable_packet_count"] for playbook in playbooks),
        "playbook_golden_case_assignment_count": sum(playbook["applicable_golden_case_count"] for playbook in playbooks),
        "parity_dimension_link_count": sum(len(playbook["required_parity_dimension_ids"]) for playbook in playbooks),
        "diagnostic_run_count": 0,
        "match_confirmed_count": 0,
        "accepted_exception_count": 0,
        "invalid_evidence_count": 0,
        "unexplained_block_count": 0,
        "repair_or_replay_performed_count": 0,
        "owner_approved_resolution_count": 0,
        "result_parity_proven_packet_count": 0,
        "executed_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_diagnostic_playbook": 1404,
        "design_lower_bound_after_diagnostic_playbook": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }

    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "playbooks_10_steps_10_assignments_100": (
            summary["diagnostic_playbook_count"],
            summary["minimum_step_count"],
            summary["diagnostic_step_assignment_count"],
        ) == (10, 10, 100),
        "outcomes_4_fixture_8_cases_56": (
            summary["diagnostic_outcome_count"],
            summary["fixture_contract_count"],
            summary["covered_golden_case_count"],
        ) == (4, 8, 56),
        "packet_assignments_72_case_assignments_504": (
            summary["playbook_packet_assignment_count"],
            summary["playbook_golden_case_assignment_count"],
        ) == (72, 504),
        "dimension_links_34_known": summary["parity_dimension_link_count"] == 34
        and all(set(playbook["required_parity_dimension_ids"]) <= known_dimension_ids for playbook in playbooks),
        "lane_specific_render_5_export_3": (
            next(playbook["applicable_packet_count"] for playbook in playbooks if playbook["scenario"] == "REPORT_RENDER_PRESENTATION_OR_COMPLETION_MISMATCH"),
            next(playbook["applicable_packet_count"] for playbook in playbooks if playbook["scenario"] == "EXPORT_SCHEMA_FORMAT_ENCODING_OR_LOCALE_MISMATCH"),
        ) == (5, 3),
        "all_designed_not_run_zero": all(
            playbook["current_diagnostic_run_count"] == 0
            and playbook["match_confirmed_count"] == 0
            and playbook["accepted_exception_count"] == 0
            and playbook["invalid_evidence_count"] == 0
            and playbook["unexplained_block_count"] == 0
            and playbook["repair_or_replay_performed_count"] == 0
            and playbook["owner_approved_resolution_count"] == 0
            and playbook["current_status"] == "DESIGNED_NOT_RUN_NO_CAPTURE_AUTHORIZATION"
            and playbook["readiness_effect"] == "ZERO"
            for playbook in playbooks
        ),
        "execution_readiness_zero": summary["diagnostic_run_count"]
        == summary["repair_or_replay_performed_count"]
        == summary["owner_approved_resolution_count"]
        == summary["result_parity_proven_packet_count"]
        == summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_diagnostic_playbook"]
        == summary["design_lower_bound_after_diagnostic_playbook"]
        == 1404,
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_HASH_ONLY_RESULT_PARITY_MISMATCH_DIAGNOSTIC_DESIGN",
            "continuation_complete": False,
            "diagnostic_run_or_repair_authorized": False,
        },
        "safety": {
            "database_connections": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "repairs_or_replays_performed": 0,
            "write_access_created": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "diagnostic_outcomes": DIAGNOSTIC_OUTCOMES,
        "diagnostic_playbooks": playbooks,
        "stop_rule": "stop at the first unvalidated manifest, hash, version, scope, redaction, conflict or unexplained-difference boundary; do not repair, replay, recapture or promote automatically",
        "resolution_rule": "only accepted hash-only evidence and independent role review may classify a match or versioned exception; all other outcomes keep CG-05 open",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "Playbooks diagnose only supplied hash-only manifests; they do not authorize capture, report/export execution, repair or replay.",
            "The 504 case assignments are diagnostic cross-links to the same 56 Golden/UAT cases, not new cases.",
            "No diagnostic run, parity result, owner-approved resolution or readiness promotion is claimed.",
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
