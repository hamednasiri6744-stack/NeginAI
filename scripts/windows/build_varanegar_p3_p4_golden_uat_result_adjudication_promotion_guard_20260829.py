"""Build P3/P4 Golden/UAT result adjudication routes and explicit promotion guards."""
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
    "diagnostic_playbook": "artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.json",
    "diagnostic_checkpoint": "artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint_20260829.json",
    "cg05": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.json",
    "receipt_validation": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.json",
    "report_gate": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json",
    "terminal_uat": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_contract_20260829.json",
    "external_handoff": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

PROMOTION_GUARD_NAMES = [
    "current_hash_pinned_fixture_output_and_comparison_manifests",
    "exact_packet_case_set_and_case_kind_coverage",
    "separately_authorized_legacy_and_target_capture_sides",
    "stable_key_grain_cardinality_and_inclusion_disposition",
    "all_required_parity_dimensions_individually_accepted",
    "all_applicable_cg05_receipts_role_accepted_current",
    "zero_unexplained_difference_and_unknown_outcome",
    "versioned_exception_policy_and_risk_acceptance_when_applicable",
    "independent_accountable_owner_review_and_separation_of_duties",
    "current_versions_expiry_conflict_and_supersession_validation",
    "isolated_golden_uat_execution_and_cg04_acceptance",
    "separate_command_and_pilot_readiness_decision",
]

OUTCOME_RULES = [
    {
        "diagnostic_outcome": "MATCH_CONFIRMED_BY_ACCEPTED_HASH_ONLY_EVIDENCE",
        "required_evidence": [
            "current_fixture_output_and_comparison_manifest_hashes",
            "accepted_stable_key_grain_and_dimension_dispositions",
            "zero_difference_or_canonical_equivalence_receipt",
            "role_accepted_current_cg05_receipts",
            "independent_owner_review_receipt",
            "no_expiry_conflict_or_supersession",
        ],
        "adjudication_state": "ELIGIBLE_FOR_CG05_ACCEPTANCE_REVIEW_ONLY",
        "cg05_effect": "REVIEW_REQUIRED_NO_AUTOMATIC_CLOSURE",
        "can_enter_cg05_acceptance_review": True,
        "automatic_cg05_closure": False,
        "automatic_readiness_promotion": False,
    },
    {
        "diagnostic_outcome": "EXPLAINED_OWNER_APPROVED_VERSIONED_EXCEPTION",
        "required_evidence": [
            "current_difference_manifest_hash",
            "versioned_exception_reference_and_scope",
            "accountable_owner_approval_receipt",
            "independent_risk_acceptance_receipt",
            "effective_and_expiry_boundaries",
            "conflict_and_supersession_validation",
            "rollback_or_containment_boundary_reference",
        ],
        "adjudication_state": "DOCUMENTED_EXCEPTION_NOT_RESULT_PARITY",
        "cg05_effect": "KEEP_OPEN_REQUIRES_SEPARATE_RISK_ACCEPTANCE",
        "can_enter_cg05_acceptance_review": False,
        "automatic_cg05_closure": False,
        "automatic_readiness_promotion": False,
    },
    {
        "diagnostic_outcome": "INVALID_OR_STALE_EVIDENCE_RECOLLECTION_REQUIRED",
        "required_evidence": [
            "rejection_code_and_failed_manifest_boundary",
            "stale_or_invalid_reference_hash",
            "separate_recollection_authorization",
            "superseding_evidence_receipt_reference",
        ],
        "adjudication_state": "RECOLLECTION_REQUIRED_NO_DECISION",
        "cg05_effect": "KEEP_OPEN_RECOLLECT_CURRENT_EVIDENCE",
        "can_enter_cg05_acceptance_review": False,
        "automatic_cg05_closure": False,
        "automatic_readiness_promotion": False,
    },
    {
        "diagnostic_outcome": "UNEXPLAINED_DIFFERENCE_BLOCKS_CG05",
        "required_evidence": [
            "first_unexplained_dimension_reference",
            "difference_manifest_hash",
            "affected_case_and_packet_set_hash",
            "accountable_role_block_receipt",
            "containment_and_no_promotion_attestation",
        ],
        "adjudication_state": "UNEXPLAINED_DIFFERENCE_HARD_BLOCK",
        "cg05_effect": "HARD_BLOCK_CG05",
        "can_enter_cg05_acceptance_review": False,
        "automatic_cg05_closure": False,
        "automatic_readiness_promotion": False,
    },
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
    playbooks = documents["diagnostic_playbook"]["diagnostic_playbooks"]
    diagnostic_outcomes = documents["diagnostic_playbook"]["diagnostic_outcomes"]

    guards = [
        {
            "guard_id": f"PG-{index:02d}",
            "guard": name,
            "currently_satisfied": False,
            "accepted_evidence_count": 0,
            "failure_effect": "STOP_NO_PROMOTION",
        }
        for index, name in enumerate(PROMOTION_GUARD_NAMES, 1)
    ]
    guard_ids = [guard["guard_id"] for guard in guards]
    playbooks_by_fixture = {
        fixture["fixture_contract_id"]: [
            playbook["diagnostic_playbook_id"]
            for playbook in playbooks
            if fixture["fixture_contract_id"] in playbook["applicable_fixture_contract_ids"]
        ]
        for fixture in fixtures
    }

    packet_routes = []
    adjudication_routes = []
    for fixture in fixtures:
        packet_routes.append(
            {
                "fixture_contract_id": fixture["fixture_contract_id"],
                "cg05_packet_id": fixture["cg05_packet_id"],
                "lane": fixture["lane"],
                "command_or_surface": fixture["command_or_surface"],
                "golden_case_count": fixture["golden_case_count"],
                "golden_case_ids": fixture["golden_case_ids"],
                "golden_case_id_set_sha256": fixture["golden_case_id_set_sha256"],
                "diagnostic_playbook_ids": playbooks_by_fixture[fixture["fixture_contract_id"]],
                "required_parity_dimension_ids": fixture["required_parity_dimension_ids"],
                "cg05_receipt_slot_ids": fixture["cg05_receipt_slot_ids"],
                "accountable_role_types": fixture["accountable_role_types"],
                "promotion_guard_ids": guard_ids,
                "allowed_diagnostic_outcomes": diagnostic_outcomes,
                "current_outcome": None,
                "accepted_evidence_count": 0,
                "satisfied_promotion_guard_count": 0,
                "cg05_acceptance_review_entered": False,
                "cg05_closed": False,
                "owner_approved": False,
                "current_status": "WAITING_FOR_AUTHORIZED_CAPTURE_AND_ACCEPTED_EVIDENCE",
                "readiness_effect": "ZERO",
            }
        )
        for outcome in OUTCOME_RULES:
            adjudication_routes.append(
                {
                    "adjudication_route_id": f"P34-ADJ-{len(adjudication_routes) + 1:03d}",
                    "fixture_contract_id": fixture["fixture_contract_id"],
                    "cg05_packet_id": fixture["cg05_packet_id"],
                    "diagnostic_outcome": outcome["diagnostic_outcome"],
                    "golden_case_count": fixture["golden_case_count"],
                    "required_evidence": outcome["required_evidence"],
                    "target_adjudication_state": outcome["adjudication_state"],
                    "cg05_effect": outcome["cg05_effect"],
                    "can_enter_cg05_acceptance_review": outcome["can_enter_cg05_acceptance_review"],
                    "current_evidence_count": 0,
                    "currently_eligible": False,
                    "adjudicated": False,
                    "readiness_effect": "ZERO",
                }
            )

    summary = {
        "packet_count": len(packet_routes),
        "p3_packet_count": sum(route["lane"] == "P3" for route in packet_routes),
        "p4_packet_count": sum(route["lane"] == "P4" for route in packet_routes),
        "covered_golden_case_count": sum(route["golden_case_count"] for route in packet_routes),
        "diagnostic_outcome_count": len(OUTCOME_RULES),
        "adjudication_route_count": len(adjudication_routes),
        "outcome_case_assignment_count": sum(route["golden_case_count"] for route in adjudication_routes),
        "diagnostic_playbook_link_count": sum(len(route["diagnostic_playbook_ids"]) for route in packet_routes),
        "promotion_guard_count": len(guards),
        "promotion_guard_assignment_count": len(packet_routes) * len(guards),
        "outcome_evidence_requirement_assignment_count": sum(len(rule["required_evidence"]) for rule in OUTCOME_RULES),
        "parity_dimension_assignment_count": sum(len(route["required_parity_dimension_ids"]) for route in packet_routes),
        "cg05_receipt_assignment_count": sum(len(route["cg05_receipt_slot_ids"]) for route in packet_routes),
        "review_eligible_outcome_count": sum(rule["can_enter_cg05_acceptance_review"] for rule in OUTCOME_RULES),
        "non_promoting_outcome_count": sum(not rule["can_enter_cg05_acceptance_review"] for rule in OUTCOME_RULES),
        "adjudicated_route_count": 0,
        "accepted_match_route_count": 0,
        "accepted_exception_route_count": 0,
        "recollection_route_count": 0,
        "unexplained_block_route_count": 0,
        "cg05_acceptance_review_entered_packet_count": 0,
        "cg05_closed_packet_count": 0,
        "owner_approved_packet_count": 0,
        "executed_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_adjudication_guard": 1404,
        "design_lower_bound_after_adjudication_guard": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "packets_8_p3_5_p4_3_cases_56": (
            summary["packet_count"],
            summary["p3_packet_count"],
            summary["p4_packet_count"],
            summary["covered_golden_case_count"],
        ) == (8, 5, 3, 56),
        "outcomes_4_routes_32_case_assignments_224": (
            summary["diagnostic_outcome_count"],
            summary["adjudication_route_count"],
            summary["outcome_case_assignment_count"],
        ) == (4, 32, 224),
        "playbook_links_72": summary["diagnostic_playbook_link_count"] == 72,
        "guards_12_assignments_96": (
            summary["promotion_guard_count"],
            summary["promotion_guard_assignment_count"],
        ) == (12, 96),
        "dimensions_160_receipts_27": (
            summary["parity_dimension_assignment_count"],
            summary["cg05_receipt_assignment_count"],
        ) == (160, 27),
        "only_match_enters_review_no_auto_promotion": summary["review_eligible_outcome_count"] == 1
        and summary["non_promoting_outcome_count"] == 3
        and all(not rule["automatic_cg05_closure"] and not rule["automatic_readiness_promotion"] for rule in OUTCOME_RULES),
        "route_crosswalk_complete": all(len(route["diagnostic_playbook_ids"]) in {9, 10} for route in packet_routes)
        and {route["diagnostic_outcome"] for route in adjudication_routes} == set(diagnostic_outcomes),
        "all_current_counts_zero": summary["adjudicated_route_count"]
        == summary["accepted_match_route_count"]
        == summary["accepted_exception_route_count"]
        == summary["recollection_route_count"]
        == summary["unexplained_block_route_count"]
        == summary["cg05_acceptance_review_entered_packet_count"]
        == summary["cg05_closed_packet_count"]
        == summary["owner_approved_packet_count"]
        == summary["executed_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "all_routes_unadjudicated": all(
            route["current_outcome"] is None
            and route["accepted_evidence_count"] == 0
            and route["satisfied_promotion_guard_count"] == 0
            and route["cg05_acceptance_review_entered"] is False
            and route["cg05_closed"] is False
            and route["owner_approved"] is False
            and route["readiness_effect"] == "ZERO"
            for route in packet_routes
        ),
        "non_additive_1404": summary["design_lower_bound_before_adjudication_guard"]
        == summary["design_lower_bound_after_adjudication_guard"]
        == 1404,
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_GOLDEN_UAT_RESULT_ADJUDICATION_AND_PROMOTION_GUARD_DESIGN",
            "continuation_complete": False,
            "capture_diagnostic_uat_or_promotion_authorized": False,
        },
        "safety": {
            "database_connections": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "repairs_replays_or_recaptures": 0,
            "write_access_created": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "promotion_guards": guards,
        "outcome_adjudication_rules": OUTCOME_RULES,
        "packet_adjudication_routes": packet_routes,
        "adjudication_routes": adjudication_routes,
        "decision_rule": "a hash-evidence match may enter independent CG-05 acceptance review only after all packet guards are satisfied; no diagnostic outcome closes CG-05 or promotes readiness automatically",
        "exception_rule": "an explained owner-approved versioned exception is not result parity and requires separate scoped risk acceptance, expiry and rollback containment while CG-05 remains open",
        "stop_rule": "invalid, stale, conflicted, superseded or unexplained evidence stops adjudication; do not recollect, repair, replay, execute or promote without separate authorization",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "The 32 routes and 224 case assignments are decision cross-links to the existing eight packets and 56 cases, not new executed cases.",
            "A match classification is only eligible for acceptance review; it is not accepted parity, UAT, owner approval or readiness.",
            "No capture, diagnostic run, adjudication, exception acceptance, CG-05 closure or promotion is claimed.",
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

