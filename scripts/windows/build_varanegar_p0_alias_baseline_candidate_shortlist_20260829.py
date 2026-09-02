"""Build a static baseline-action shortlist for the seven P0 alias handoffs."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "priority": "artifacts/varanegar_analysis/varanegar_action_alias_handoff_priority_matrix_20260829.json",
    "owner_matrix": "artifacts/varanegar_analysis/varanegar_action_alias_owner_evidence_packet_matrix_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_action_alias_handoff_priority_checkpoint_20260829.json",
    "core": "artifacts/varanegar_analysis/ui/varanegar_golden_command_cases_20260827.json",
    "orchestrator": "artifacts/varanegar_analysis/ui/varanegar_orchestrator_golden_cases_20260827.json",
    "extension": "artifacts/varanegar_analysis/ui/varanegar_extension_golden_cases_20260827.json",
    "report_base": "artifacts/varanegar_analysis/ui/varanegar_report_target_contracts_golden_cases_20260827.json",
    "master": "artifacts/varanegar_analysis/ui/negin_erp_customer_goods_master_golden_cases_20260827.json",
    "foundation": "artifacts/varanegar_analysis/ui/negin_erp_foundation_context_pricing_golden_cases_20260827.json",
    "bank": "artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_golden_cases_20260827.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}
CANDIDATES = {
    "AAP-01": [],
    "AAP-02": [],
    "AAP-04": [],
    "AAP-06": [("inventory", "stock_voucher.confirm_or_unconfirm")],
    "AAP-14": [
        ("receivables_treasury", "bank_reconciliation.cancel"),
        ("receivables_treasury", "bank_reconciliation.confirm"),
        ("receivables_treasury", "bank_reconciliation.unmatch_instrument"),
    ],
    "AAP-18": [
        ("receivables_treasury", "received_cheque.change_status"),
        ("receivables_treasury", "received_cheque.undo"),
    ],
    "AAP-20": [],
}
SEARCH_SCOPE = {
    "AAP-01": ["accounting"],
    "AAP-02": ["accounting"],
    "AAP-04": ["accounting"],
    "AAP-06": ["accounting", "inventory"],
    "AAP-14": ["receivables_treasury"],
    "AAP-18": ["receivables_treasury"],
    "AAP-20": ["receivables_treasury"],
}
REQUIRED_FIELDS = [
    "source_packet_and_case_set_hash",
    "searched_baseline_modules",
    "candidate_baseline_action_or_explicit_none",
    "candidate_baseline_case_ids",
    "case_kind_overlap",
    "precondition_equivalence_disposition",
    "outcome_vocabulary_mapping",
    "assertion_and_effect_mapping",
    "versioned_alias_or_new_action_disposition",
    "accountable_role_receipts",
    "policy_version_expiry_and_supersession",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def action(row: dict) -> str:
    return str(row.get("command") or row.get("surface") or row.get("command_id") or "")


def kind(row: dict) -> str:
    return str(row.get("kind") or row.get("case_kind") or "")


def command_module(command: str) -> str:
    if command.startswith("master_data."):
        return "master_data"
    if command.startswith(("order.", "sales_return.")):
        return "sales"
    if command.startswith("distribution."):
        return "distribution"
    if command.startswith("received_cheque."):
        return "receivables_treasury"
    if command.startswith(("payable_cheque.", "supplier_")):
        return "procurement_payables"
    if command.startswith(("stock_voucher.", "inventory.")):
        return "inventory"
    raise ValueError(f"unmapped baseline command prefix: {command}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}

    baseline: dict[str, list[dict]] = defaultdict(list)
    for source in ("core", "orchestrator", "master"):
        for row in data[source]["cases"]:
            baseline[command_module(row["command"])].append(row)
    for row in data["extension"]["cases"]:
        baseline[row["target_module"]].append(row)
    for row in data["report_base"]["golden_cases"]:
        baseline[row["target_module"]].append(row)
    for row in data["foundation"]["cases"]:
        baseline[row["target_module"]].append(row)
    baseline["receivables_treasury"].extend(data["bank"]["cases"])

    priority_rows = {row["source_packet_id"]: row for row in data["priority"]["handoff_packets"]}
    owner_rows = {row["packet_id"]: row for row in data["owner_matrix"]["action_alias_packets"]}
    p0_ids = sorted(packet_id for packet_id, row in priority_rows.items() if row["priority_rank"] == 0)
    packets = []
    for packet_id in p0_ids:
        priority = priority_rows[packet_id]
        owner = owner_rows[packet_id]
        current_kinds = set(owner["case_kinds"])
        candidate_rows = []
        for candidate_module, candidate_action in CANDIDATES[packet_id]:
            matching = [row for row in baseline[candidate_module] if action(row) == candidate_action]
            baseline_kinds = {kind(row) for row in matching if kind(row)}
            candidate_rows.append(
                {
                    "baseline_module": candidate_module,
                    "baseline_action": candidate_action,
                    "baseline_case_count": len(matching),
                    "baseline_case_ids": sorted(row["case_id"] for row in matching),
                    "baseline_case_kinds": sorted(baseline_kinds),
                    "overlapping_case_kinds": sorted(current_kinds & baseline_kinds),
                    "overlapping_case_kind_count": len(current_kinds & baseline_kinds),
                    "exact_action_string_match": candidate_action.casefold() == priority["newer_action_or_surface"].casefold(),
                    "candidate_status": "REVIEW_REQUIRED_NOT_SEMANTIC_EQUIVALENCE",
                }
            )
        if not candidate_rows:
            candidate_class = "EXPLICIT_NONE_AFTER_RECONSTRUCTED_BASELINE_SEARCH"
        elif any(row["exact_action_string_match"] for row in candidate_rows):
            candidate_class = "EXACT_ACTION_CROSS_MODULE_SCOPE_MISMATCH_REVIEW"
        else:
            candidate_class = "LIFECYCLE_ACTION_FAMILY_REVIEW"
        search_case_count = sum(len(baseline[module]) for module in SEARCH_SCOPE[packet_id])
        packets.append(
            {
                "shortlist_id": f"P0S-{len(packets)+1:02d}",
                "source_packet_id": packet_id,
                "module": priority["module"],
                "newer_action_or_surface": priority["newer_action_or_surface"],
                "newer_case_count": priority["case_count"],
                "newer_case_id_set_sha256": priority["case_id_set_sha256"],
                "newer_case_kinds": owner["case_kinds"],
                "searched_baseline_modules": SEARCH_SCOPE[packet_id],
                "searched_baseline_case_count": search_case_count,
                "candidate_class": candidate_class,
                "candidate_baseline_action_count": len(candidate_rows),
                "candidate_baseline_actions": candidate_rows,
                "accountable_role_types": priority["accountable_role_types"],
                "required_disposition_fields": REQUIRED_FIELDS,
                "current_status": "WAITING_FOR_EVIDENCE_BACKED_CANDIDATE_DISPOSITION",
                "accepted_candidate_action_count": 0,
                "accepted_case_disposition_count": 0,
                "counting_effect": "ZERO",
            }
        )

    summary = {
        "p0_packet_count": len(packets),
        "p0_case_count": sum(row["newer_case_count"] for row in packets),
        "candidate_bearing_packet_count": sum(bool(row["candidate_baseline_action_count"]) for row in packets),
        "explicit_none_packet_count": sum(not row["candidate_baseline_action_count"] for row in packets),
        "candidate_baseline_action_reference_count": sum(row["candidate_baseline_action_count"] for row in packets),
        "candidate_baseline_case_reference_count": sum(candidate["baseline_case_count"] for row in packets for candidate in row["candidate_baseline_actions"]),
        "candidate_case_kind_overlap_reference_count": sum(candidate["overlapping_case_kind_count"] for row in packets for candidate in row["candidate_baseline_actions"]),
        "exact_action_cross_module_candidate_count": sum(candidate["exact_action_string_match"] for row in packets for candidate in row["candidate_baseline_actions"]),
        "lifecycle_family_candidate_packet_count": sum(row["candidate_class"] == "LIFECYCLE_ACTION_FAMILY_REVIEW" for row in packets),
        "accountable_role_assignment_count": sum(len(row["accountable_role_types"]) for row in packets),
        "required_disposition_field_count": len(REQUIRED_FIELDS),
        "accepted_candidate_action_count": 0,
        "accepted_case_disposition_count": 0,
        "exact_non_duplicated_additive_count": 0,
        "design_lower_bound_before_shortlist": data["priority"]["summary"]["design_lower_bound_after_priority_handoff"],
        "design_lower_bound_after_shortlist": data["priority"]["summary"]["design_lower_bound_after_priority_handoff"],
        "executed_case_count": 0,
        "owner_approved_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    all_candidates = [candidate for row in packets for candidate in row["candidate_baseline_actions"]]
    checks = {
        "validated_sources_pass": all(data[name].get("validation") == "PASS" for name in data if name not in {"core"}),
        "legacy_core_shape_pinned": data["core"].get("validation") is None and data["core"]["summary"]["case_count"] == 77,
        "p0_partition_7_49": summary["p0_packet_count"] == 7 and summary["p0_case_count"] == 49 and len({row["source_packet_id"] for row in packets}) == 7,
        "candidate_split_3_4": summary["candidate_bearing_packet_count"] == 3 and summary["explicit_none_packet_count"] == 4,
        "six_action_refs_92_cases": summary["candidate_baseline_action_reference_count"] == 6 and summary["candidate_baseline_case_reference_count"] == 92,
        "kind_overlap_37": summary["candidate_case_kind_overlap_reference_count"] == 37,
        "one_exact_cross_module_two_lifecycle": summary["exact_action_cross_module_candidate_count"] == 1 and summary["lifecycle_family_candidate_packet_count"] == 2,
        "candidate_rows_nonempty_and_review_only": all(candidate["baseline_case_count"] > 0 and candidate["candidate_status"] == "REVIEW_REQUIRED_NOT_SEMANTIC_EQUIVALENCE" for candidate in all_candidates),
        "roles_and_fields": summary["accountable_role_assignment_count"] == 14 and summary["required_disposition_field_count"] == 11,
        "non_additive_1404": summary["accepted_candidate_action_count"] == summary["accepted_case_disposition_count"] == summary["exact_non_duplicated_additive_count"] == 0 and summary["design_lower_bound_before_shortlist"] == summary["design_lower_bound_after_shortlist"] == 1404,
        "execution_readiness_zero": summary["executed_case_count"] == summary["owner_approved_case_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_p0_alias_baseline_candidate_shortlist_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "OFFLINE_P0_BASELINE_CANDIDATE_SHORTLIST", "continuation_complete": False},
        "safety": {"database_connections": 0, "golden_uat_or_operational_execution": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "write_access_created": 0, "raw_business_values_identity_or_credentials_persisted": 0},
        "summary": summary,
        "required_disposition_fields": REQUIRED_FIELDS,
        "p0_candidate_packets": packets,
        "interpretation_rule": "exact action, action-family similarity, and case-kind overlap are shortlist evidence only and never semantic equivalence or acceptance",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)} for name, path in sorted(paths.items())] + [{"name": "builder", "path": "scripts/windows/build_varanegar_p0_alias_baseline_candidate_shortlist_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha256(Path(__file__))}],
        "limits": ["The shortlist contains no accepted alias or case disposition.", "EXPLICIT_NONE means no candidate in the reconstructed baseline scope, not proof that no historical implementation exists.", "No case was executed and no readiness state was promoted."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
