"""Build a static baseline-action shortlist for the eight P1 alias handoffs."""
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
    "previous": "artifacts/varanegar_analysis/varanegar_p0_final_evidence_gap_status_checkpoint_20260829.json",
    "core": "artifacts/varanegar_analysis/ui/varanegar_golden_command_cases_20260827.json",
    "orchestrator": "artifacts/varanegar_analysis/ui/varanegar_orchestrator_golden_cases_20260827.json",
    "extension": "artifacts/varanegar_analysis/ui/varanegar_extension_golden_cases_20260827.json",
    "report_base": "artifacts/varanegar_analysis/ui/varanegar_report_target_contracts_golden_cases_20260827.json",
    "master": "artifacts/varanegar_analysis/ui/negin_erp_customer_goods_master_golden_cases_20260827.json",
    "foundation": "artifacts/varanegar_analysis/ui/negin_erp_foundation_context_pricing_golden_cases_20260827.json",
    "bank": "artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_golden_cases_20260827.json",
    "bank_state": "artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_state_machine_contract_20260827.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}
CANDIDATES = {
    "AAP-03": [],
    "AAP-05": [],
    "AAP-11": [("receivables_treasury", "bank_reconciliation.cancel", "CancelSession")],
    "AAP-12": [("receivables_treasury", "bank_reconciliation.confirm", "ConfirmSession")],
    "AAP-13": [("receivables_treasury", "bank_reconciliation.match_instrument", "MatchInstrument")],
    "AAP-15": [("receivables_treasury", "bank_reconciliation.unmatch_instrument", "UnmatchInstrument")],
    "AAP-16": [],
    "AAP-17": [],
}
SEARCH_SCOPE = {
    "AAP-03": ["accounting"],
    "AAP-05": ["accounting"],
    "AAP-11": ["receivables_treasury"],
    "AAP-12": ["receivables_treasury"],
    "AAP-13": ["receivables_treasury"],
    "AAP-15": ["receivables_treasury"],
    "AAP-16": ["receivables_treasury"],
    "AAP-17": ["receivables_treasury"],
}
REQUIRED_FIELDS = [
    "source_packet_and_case_set_hash",
    "searched_baseline_modules",
    "candidate_baseline_action_or_explicit_none",
    "candidate_baseline_case_ids",
    "state_machine_command_capability_evidence",
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

    state_map = {row["command"]: row for row in data["bank_state"]["transition_contracts"]}
    priority_rows = {row["source_packet_id"]: row for row in data["priority"]["handoff_packets"]}
    owner_rows = {row["packet_id"]: row for row in data["owner_matrix"]["action_alias_packets"]}
    p1_ids = sorted(packet_id for packet_id, row in priority_rows.items() if row["priority_rank"] == 1)
    packets = []
    for packet_id in p1_ids:
        priority = priority_rows[packet_id]
        owner = owner_rows[packet_id]
        current_kinds = set(owner["case_kinds"])
        candidate_rows = []
        for candidate_module, candidate_action, state_command in CANDIDATES[packet_id]:
            matching = [row for row in baseline[candidate_module] if action(row) == candidate_action]
            baseline_kinds = {kind(row) for row in matching if kind(row)}
            transition = state_map.get(state_command)
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
                    "state_machine_command": state_command,
                    "state_machine_capability": transition["capability"] if transition else None,
                    "state_machine_mapping_exact": bool(transition and transition["capability"] == candidate_action),
                    "state_transition_from": transition["from"] if transition else None,
                    "state_transition_to": transition["to"] if transition else None,
                    "candidate_status": "REVIEW_REQUIRED_NOT_SEMANTIC_EQUIVALENCE",
                }
            )
        candidate_class = (
            "EXPLICIT_STATE_MACHINE_COMMAND_CAPABILITY_MAPPING_REVIEW"
            if candidate_rows
            else "EXPLICIT_NONE_AFTER_RECONSTRUCTED_BASELINE_SEARCH"
        )
        packets.append(
            {
                "shortlist_id": f"P1S-{len(packets)+1:02d}",
                "source_packet_id": packet_id,
                "module": priority["module"],
                "newer_action_or_surface": priority["newer_action_or_surface"],
                "newer_case_count": priority["case_count"],
                "newer_case_id_set_sha256": priority["case_id_set_sha256"],
                "newer_case_kinds": owner["case_kinds"],
                "searched_baseline_modules": SEARCH_SCOPE[packet_id],
                "searched_baseline_case_count": sum(len(baseline[module]) for module in SEARCH_SCOPE[packet_id]),
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

    all_candidates = [candidate for row in packets for candidate in row["candidate_baseline_actions"]]
    summary = {
        "p1_packet_count": len(packets),
        "p1_case_count": sum(row["newer_case_count"] for row in packets),
        "candidate_bearing_packet_count": sum(bool(row["candidate_baseline_action_count"]) for row in packets),
        "explicit_none_packet_count": sum(not row["candidate_baseline_action_count"] for row in packets),
        "candidate_baseline_action_reference_count": len(all_candidates),
        "candidate_baseline_case_reference_count": sum(row["baseline_case_count"] for row in all_candidates),
        "candidate_case_kind_overlap_reference_count": sum(row["overlapping_case_kind_count"] for row in all_candidates),
        "state_machine_exact_mapping_count": sum(row["state_machine_mapping_exact"] for row in all_candidates),
        "exact_action_string_match_count": sum(row["exact_action_string_match"] for row in all_candidates),
        "searched_baseline_case_reference_count": sum(row["searched_baseline_case_count"] for row in packets),
        "accountable_role_assignment_count": sum(len(row["accountable_role_types"]) for row in packets),
        "required_disposition_field_count": len(REQUIRED_FIELDS),
        "accepted_candidate_action_count": 0,
        "accepted_case_disposition_count": 0,
        "exact_non_duplicated_additive_count": 0,
        "design_lower_bound_before_shortlist": 1404,
        "design_lower_bound_after_shortlist": 1404,
        "executed_case_count": 0,
        "owner_approved_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "risk_count": data["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": data["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "validated_sources_pass": all(data[name].get("validation") == "PASS" for name in data if name != "core"),
        "legacy_core_shape_pinned": data["core"].get("validation") is None and data["core"]["summary"]["case_count"] == 77,
        "p1_partition_8_56": summary["p1_packet_count"] == 8 and summary["p1_case_count"] == 56 and len({row["source_packet_id"] for row in packets}) == 8,
        "candidate_split_4_4": summary["candidate_bearing_packet_count"] == 4 and summary["explicit_none_packet_count"] == 4,
        "four_action_refs_76_cases": summary["candidate_baseline_action_reference_count"] == 4 and summary["candidate_baseline_case_reference_count"] == 76,
        "kind_overlap_24": summary["candidate_case_kind_overlap_reference_count"] == 24,
        "four_explicit_state_mappings_no_string_exact": summary["state_machine_exact_mapping_count"] == 4 and summary["exact_action_string_match_count"] == 0,
        "searched_reference_scope_1008": summary["searched_baseline_case_reference_count"] == 1008,
        "candidate_rows_nonempty_and_review_only": all(row["baseline_case_count"] > 0 and row["candidate_status"] == "REVIEW_REQUIRED_NOT_SEMANTIC_EQUIVALENCE" for row in all_candidates),
        "roles_and_fields": summary["accountable_role_assignment_count"] == 16 and summary["required_disposition_field_count"] == 12,
        "non_additive_1404": summary["accepted_candidate_action_count"] == summary["accepted_case_disposition_count"] == summary["exact_non_duplicated_additive_count"] == 0 and summary["design_lower_bound_before_shortlist"] == summary["design_lower_bound_after_shortlist"] == 1404,
        "execution_readiness_zero": summary["executed_case_count"] == summary["owner_approved_case_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_p1_alias_baseline_candidate_shortlist_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "OFFLINE_P1_BASELINE_CANDIDATE_SHORTLIST", "continuation_complete": False},
        "safety": {"database_connections": 0, "golden_uat_or_operational_execution": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "write_access_created": 0, "raw_business_values_identity_or_credentials_persisted": 0},
        "summary": summary,
        "required_disposition_fields": REQUIRED_FIELDS,
        "p1_candidate_packets": packets,
        "interpretation_rule": "an explicit command-to-capability state-machine mapping and case-kind overlap are shortlist evidence only, never semantic equivalence or acceptance",
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)} for name, path in sorted(paths.items())] + [{"name": "builder", "path": "scripts/windows/build_varanegar_p1_alias_baseline_candidate_shortlist_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha256(Path(__file__))}],
        "limits": ["The shortlist contains no accepted alias or case disposition.", "EXPLICIT_NONE means no candidate in the reconstructed baseline scope, not proof that no historical implementation exists.", "State-machine command-to-capability mapping does not prove precondition, outcome, assertion, or effect parity.", "No case was executed and no readiness state was promoted."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
