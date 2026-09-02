"""Build downstream invalidation and gate-reopen propagation for P3/P4 evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "custody": "artifacts/varanegar_analysis/varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract_20260829.json",
    "custody_checkpoint": "artifacts/varanegar_analysis/varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_checkpoint_20260829.json",
    "handoff": "artifacts/varanegar_analysis/varanegar_p3_p4_capture_to_comparison_evidence_handoff_matrix_20260829.json",
    "cg05": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.json",
    "adapter": "artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.json",
    "adjudication": "artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.json",
    "capture": "artifacts/varanegar_analysis/varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

INVALIDATION_CAUSES = [
    ("INV-01", "capture_authorization_expired"),
    ("INV-02", "capture_authorization_revoked"),
    ("INV-03", "redaction_attestation_rejected_or_expired"),
    ("INV-04", "custody_receipt_expired"),
    ("INV-05", "custody_receipt_revoked"),
    ("INV-06", "custody_receipt_superseded"),
    ("INV-07", "custody_hash_chain_broken"),
    ("INV-08", "manifest_hash_or_case_set_drift"),
    ("INV-09", "scope_redaction_or_canonicalization_policy_drift"),
    ("INV-10", "adapter_profile_or_schema_version_drift"),
    ("INV-11", "receipt_authenticity_or_verification_invalid"),
    ("INV-12", "new_unexplained_result_difference"),
]

REOPEN_ACTIONS = [
    ("RPA-01", "mark_custody_requirement_not_current"),
    ("RPA-02", "reopen_capture_to_comparison_handoff_gates"),
    ("RPA-03", "cancel_or_quarantine_pending_adapter_request"),
    ("RPA-04", "invalidate_dependent_comparison_or_cg05_receipt"),
    ("RPA-05", "reopen_dependent_promotion_guards"),
    ("RPA-06", "require_new_authorized_capture_or_recollection"),
    ("RPA-07", "require_independent_diagnostic_and_readjudication"),
    ("RPA-08", "block_cg05_uat_command_and_pilot_readiness"),
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    custody = documents["custody"]
    handoff = documents["handoff"]
    cg05 = documents["cg05"]
    adjudication = documents["adjudication"]
    official = documents["tests"]

    pairs = {pair["capture_pair_id"]: pair for pair in handoff["capture_pairs"]}
    profile_by_packet = {
        profile["cg05_packet_id"]: profile["adapter_profile_id"]
        for profile in documents["adapter"]["adapter_profiles"]
    }
    route_by_packet = {
        route["cg05_packet_id"]: route
        for route in adjudication["packet_adjudication_routes"]
    }

    requirement_pair_edges = []
    requirement_profile_edges = []
    requirement_receipt_slot_edges = []
    cause_assignments = []
    for requirement in custody["custody_requirements"]:
        requirement_id = requirement["custody_requirement_id"]
        pair_id = requirement["capture_pair_id"]
        packet_id = pairs[pair_id]["cg05_packet_id"]
        requirement_pair_edges.append(
            {
                "custody_requirement_id": requirement_id,
                "capture_pair_id": pair_id,
                "invalidation_effect": "REOPEN_PAIR_HANDOFF_GATES",
            }
        )
        requirement_profile_edges.append(
            {
                "custody_requirement_id": requirement_id,
                "adapter_profile_id": profile_by_packet[packet_id],
                "invalidation_effect": "CANCEL_OR_QUARANTINE_PROFILE_REQUEST",
            }
        )
        requirement_receipt_slot_edges.append(
            {
                "custody_requirement_id": requirement_id,
                "cg05_receipt_slot_id": requirement["cg05_receipt_slot_id"],
                "invalidation_effect": "MARK_RECEIPT_SLOT_NOT_CURRENT",
            }
        )
        cause_assignments.extend(
            {
                "invalidation_cause_id": cause_id,
                "custody_requirement_id": requirement_id,
                "current_status": "NO_EVENT_OBSERVED",
                "observed_event_count": 0,
            }
            for cause_id, _ in INVALIDATION_CAUSES
        )

    pair_promotion_guard_edges = []
    for pair_id, pair in sorted(pairs.items()):
        route = route_by_packet[pair["cg05_packet_id"]]
        pair_promotion_guard_edges.extend(
            {
                "capture_pair_id": pair_id,
                "promotion_guard_id": guard_id,
                "invalidation_effect": "REOPEN_GUARD_AND_CLEAR_SATISFACTION",
            }
            for guard_id in route["promotion_guard_ids"]
        )

    receipt_slot_packet_edges = [
        {
            "cg05_receipt_slot_id": slot_id,
            "cg05_packet_id": packet["cg05_packet_id"],
            "invalidation_effect": "REOPEN_PACKET_CG05_ACCEPTANCE",
        }
        for packet in cg05["cg05_packets"]
        for slot_id in packet["cg05_receipt_slot_ids"]
    ]
    total_edges = (
        len(requirement_pair_edges)
        + len(requirement_profile_edges)
        + len(requirement_receipt_slot_edges)
        + len(pair_promotion_guard_edges)
        + len(receipt_slot_packet_edges)
    )
    summary = {
        "packet_count": len(cg05["cg05_packets"]),
        "custody_requirement_count": len(custody["custody_requirements"]),
        "invalidation_cause_count": len(INVALIDATION_CAUSES),
        "cause_requirement_assignment_count": len(cause_assignments),
        "requirement_pair_edge_count": len(requirement_pair_edges),
        "requirement_profile_edge_count": len(requirement_profile_edges),
        "requirement_receipt_slot_edge_count": len(requirement_receipt_slot_edges),
        "pair_promotion_guard_edge_count": len(pair_promotion_guard_edges),
        "receipt_slot_packet_edge_count": len(receipt_slot_packet_edges),
        "total_dependency_edge_count": total_edges,
        "reopen_action_count": len(REOPEN_ACTIONS),
        "observed_invalidation_event_count": 0,
        "invalidated_custody_requirement_count": 0,
        "reopened_handoff_pair_count": 0,
        "invalidated_adapter_profile_count": 0,
        "reopened_cg05_receipt_slot_count": 0,
        "reopened_promotion_guard_count": 0,
        "reaccepted_evidence_count": 0,
        "result_parity_proven_packet_count": 0,
        "cg05_closed_packet_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_invalidation_matrix": 1404,
        "design_lower_bound_after_invalidation_matrix": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(
            documents[name].get("validation") == "PASS"
            for name in ("custody", "custody_checkpoint", "handoff", "cg05", "adapter", "adjudication", "capture", "tests")
        ),
        "packets_8_requirements_54_causes_12_assignments_648": (
            summary["packet_count"],
            summary["custody_requirement_count"],
            summary["invalidation_cause_count"],
            summary["cause_requirement_assignment_count"],
        )
        == (8, 54, 12, 648),
        "requirement_edges_54_54_54": (
            summary["requirement_pair_edge_count"],
            summary["requirement_profile_edge_count"],
            summary["requirement_receipt_slot_edge_count"],
        )
        == (54, 54, 54),
        "guard_and_packet_edges_96_27_total_285": (
            summary["pair_promotion_guard_edge_count"],
            summary["receipt_slot_packet_edge_count"],
            summary["total_dependency_edge_count"],
        )
        == (96, 27, 285),
        "one_pair_profile_slot_per_requirement": len({edge["custody_requirement_id"] for edge in requirement_pair_edges})
        == len({edge["custody_requirement_id"] for edge in requirement_profile_edges})
        == len({edge["custody_requirement_id"] for edge in requirement_receipt_slot_edges})
        == 54,
        "all_events_zero_and_reopen_actions_8": all(item["current_status"] == "NO_EVENT_OBSERVED" for item in cause_assignments)
        and summary["reopen_action_count"] == 8,
        "invalidation_reacceptance_parity_readiness_zero": summary["observed_invalidation_event_count"]
        == summary["invalidated_custody_requirement_count"]
        == summary["reopened_handoff_pair_count"]
        == summary["invalidated_adapter_profile_count"]
        == summary["reopened_cg05_receipt_slot_count"]
        == summary["reopened_promotion_guard_count"]
        == summary["reaccepted_evidence_count"]
        == summary["result_parity_proven_packet_count"]
        == summary["cg05_closed_packet_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_invalidation_matrix"]
        == summary["design_lower_bound_after_invalidation_matrix"]
        == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_evidence_invalidation_reopen_propagation_matrix_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "design_only_invalidation_dependency_and_reopen_propagation",
            "continuation_complete": False,
            "invalidation_event_observed_or_triggered": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes_to_varanegar_or_erp": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "invalidation_or_reopen_events_triggered": 0,
            "external_evidence_received": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "invalidation_causes": [
            {
                "cause_id": cause_id,
                "cause": cause,
                "effect": "INVALIDATE_AND_REOPEN_DEPENDENT_GATES",
            }
            for cause_id, cause in INVALIDATION_CAUSES
        ],
        "reopen_actions": [
            {
                "action_id": action_id,
                "action": action,
                "automatic_reacceptance_allowed": False,
            }
            for action_id, action in REOPEN_ACTIONS
        ],
        "cause_requirement_assignments": cause_assignments,
        "requirement_pair_edges": requirement_pair_edges,
        "requirement_profile_edges": requirement_profile_edges,
        "requirement_receipt_slot_edges": requirement_receipt_slot_edges,
        "pair_promotion_guard_edges": pair_promotion_guard_edges,
        "receipt_slot_packet_edges": receipt_slot_packet_edges,
        "propagation_rule": {
            "fail_closed_on_any_invalidation_cause": True,
            "automatic_reacceptance_allowed": False,
            "automatic_recapture_replay_or_repair_allowed": False,
            "invalidation_clears_result_parity_and_cg05_closure": True,
            "new_independent_evidence_and_adjudication_required": True,
            "readiness_remains_blocked_until_full_revalidation": True,
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
                "path": "scripts/windows/build_varanegar_p3_p4_evidence_invalidation_reopen_propagation_matrix_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This is a dependency and fail-closed propagation design; no invalidation event was observed or emitted.",
            "No evidence was reaccepted and no recapture replay repair comparison or adjudication occurred.",
            "The graph does not establish result parity CG-05 closure UAT or readiness.",
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

