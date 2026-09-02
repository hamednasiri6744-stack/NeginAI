"""Reconstruct baseline case IDs and measure safe Golden/UAT crosswalk feasibility."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "readiness": "artifacts/varanegar_analysis/ui/negin_erp_module_readiness_matrix_20260827.json",
    "core": "artifacts/varanegar_analysis/ui/varanegar_golden_command_cases_20260827.json",
    "orchestrator": "artifacts/varanegar_analysis/ui/varanegar_orchestrator_golden_cases_20260827.json",
    "extension": "artifacts/varanegar_analysis/ui/varanegar_extension_golden_cases_20260827.json",
    "report_base": "artifacts/varanegar_analysis/ui/varanegar_report_target_contracts_golden_cases_20260827.json",
    "master": "artifacts/varanegar_analysis/ui/negin_erp_customer_goods_master_golden_cases_20260827.json",
    "foundation": "artifacts/varanegar_analysis/ui/negin_erp_foundation_context_pricing_golden_cases_20260827.json",
    "bank": "artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_golden_cases_20260827.json",
    "pricing": "artifacts/varanegar_analysis/varanegar_pricing_rule_golden_uat_cases_20260829.json",
    "distribution": "artifacts/varanegar_analysis/varanegar_distribution_golden_uat_cases_20260829.json",
    "treasury": "artifacts/varanegar_analysis/varanegar_treasury_golden_uat_cases_20260829.json",
    "accounting": "artifacts/varanegar_analysis/varanegar_accounting_golden_uat_cases_20260829.json",
    "reporting": "artifacts/varanegar_analysis/varanegar_reporting_output_golden_uat_cases_20260829.json",
    "audit": "artifacts/varanegar_analysis/varanegar_golden_uat_design_delta_audit_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_cross_gate_golden_uat_refinement_checkpoint_20260829.json",
}

MODULES = ("pricing_rules", "distribution", "receivables_treasury", "accounting", "reporting_documents")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    raise ValueError(f"unmapped command prefix: {command}")


def action(row: dict) -> str:
    return str(row.get("command") or row.get("surface") or row.get("command_id") or "")


def kind(row: dict) -> str:
    return str(row.get("kind") or row.get("case_kind") or "")


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

    newer_source = {
        "pricing_rules": "pricing",
        "distribution": "distribution",
        "receivables_treasury": "treasury",
        "accounting": "accounting",
        "reporting_documents": "reporting",
    }
    rows = []
    for module in MODULES:
        base_rows = baseline[module]
        newer_delta_rows = data[newer_source[module]]["cases"]
        represented_rows = list(newer_delta_rows)
        if module == "pricing_rules":
            represented_rows = [row for row in data["foundation"]["cases"] if row["target_module"] == "pricing_rules"] + represented_rows
        base_ids = {row["case_id"] for row in base_rows}
        represented_ids = {row["case_id"] for row in represented_rows}
        overlap_ids = base_ids & represented_ids
        unmatched_base = [row for row in base_rows if row["case_id"] not in overlap_ids]
        unmatched_newer = [row for row in represented_rows if row["case_id"] not in overlap_ids]
        base_pairs = Counter((action(row).casefold(), kind(row).casefold()) for row in unmatched_base)
        newer_pairs = Counter((action(row).casefold(), kind(row).casefold()) for row in unmatched_newer)
        candidate_pairs = set(base_pairs) & set(newer_pairs)
        candidate_rows = sum(min(base_pairs[pair], newer_pairs[pair]) for pair in candidate_pairs)
        rows.append(
            {
                "module": module,
                "baseline_design_count": len(base_rows),
                "baseline_unique_case_id_count": len(base_ids),
                "newer_represented_design_count": len(represented_rows),
                "newer_unique_case_id_count": len(represented_ids),
                "exact_case_id_overlap_count": len(overlap_ids),
                "unmatched_baseline_case_count": len(unmatched_base),
                "unmatched_newer_case_count": len(unmatched_newer),
                "candidate_casefold_action_kind_pair_count": len(candidate_pairs),
                "candidate_casefold_action_kind_row_overlap_count": candidate_rows,
                "accepted_semantic_equivalence_count": 0,
                "exact_non_duplicated_additive_count": 0,
                "crosswalk_status": "PARTIAL_EXACT_ID_REUSE_SEMANTIC_ALIAS_MAP_REQUIRED" if overlap_ids else "NO_EXACT_ID_OVERLAP_SEMANTIC_ALIAS_MAP_REQUIRED",
                "newer_source": SOURCES[newer_source[module]],
                "required_evidence": [
                    "versioned old-to-new command/surface alias map",
                    "case-level equivalence disposition using precondition, expected outcome, assertions and effect class",
                    "explicit NEW, REUSE, REPLACEMENT, DEPRECATED or UNRESOLVED state per unmatched case",
                ],
            }
        )
    readiness_counts = {
        row["module"]: row["evidence_counts"]["synthetic_golden_case_count"]
        for row in data["readiness"]["modules"]
    }
    summary = {
        "unresolved_module_count": len(rows),
        "reconstructed_baseline_case_count": sum(row["baseline_design_count"] for row in rows),
        "reconstructed_baseline_unique_case_id_count": sum(row["baseline_unique_case_id_count"] for row in rows),
        "newer_represented_case_count": sum(row["newer_represented_design_count"] for row in rows),
        "newer_represented_unique_case_id_count": sum(row["newer_unique_case_id_count"] for row in rows),
        "exact_case_id_overlap_count": sum(row["exact_case_id_overlap_count"] for row in rows),
        "unmatched_baseline_case_count": sum(row["unmatched_baseline_case_count"] for row in rows),
        "unmatched_newer_case_count": sum(row["unmatched_newer_case_count"] for row in rows),
        "candidate_casefold_action_kind_row_overlap_count": sum(row["candidate_casefold_action_kind_row_overlap_count"] for row in rows),
        "accepted_semantic_equivalence_count": 0,
        "required_crosswalk_packet_count": 15,
        "accepted_crosswalk_packet_count": 0,
        "exact_non_duplicated_additive_count": 0,
        "design_lower_bound_before_crosswalk": data["audit"]["summary"]["current_proven_non_duplicated_design_lower_bound"],
        "design_lower_bound_after_crosswalk": data["audit"]["summary"]["current_proven_non_duplicated_design_lower_bound"],
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
        "five_modules": len(rows) == len({row["module"] for row in rows}) == 5,
        "baseline_counts_reconstruct_readiness": all(row["baseline_design_count"] == readiness_counts[row["module"]] for row in rows),
        "baseline_511_newer_302": summary["reconstructed_baseline_case_count"] == summary["reconstructed_baseline_unique_case_id_count"] == 511
        and summary["newer_represented_case_count"] == summary["newer_represented_unique_case_id_count"] == 302,
        "exact_id_overlap_64_only_pricing": summary["exact_case_id_overlap_count"] == 64
        and next(row for row in rows if row["module"] == "pricing_rules")["exact_case_id_overlap_count"] == 64
        and all(row["exact_case_id_overlap_count"] == 0 for row in rows if row["module"] != "pricing_rules"),
        "unmatched_447_238_candidate_30": summary["unmatched_baseline_case_count"] == 447
        and summary["unmatched_newer_case_count"] == 238
        and summary["candidate_casefold_action_kind_row_overlap_count"] == 30,
        "candidate_not_promoted": summary["accepted_semantic_equivalence_count"] == summary["exact_non_duplicated_additive_count"] == 0,
        "lower_bound_unchanged_1404": summary["design_lower_bound_before_crosswalk"] == summary["design_lower_bound_after_crosswalk"] == 1404,
        "execution_approval_readiness_zero": summary["accepted_crosswalk_packet_count"] == summary["executed_case_count"] == summary["owner_approved_case_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_golden_uat_crosswalk_feasibility_matrix_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "OFFLINE_CASE_ID_AND_CANDIDATE_SEMANTIC_CROSSWALK", "continuation_complete": False},
        "safety": {"database_connections": 0, "golden_uat_or_operational_execution": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "write_access_created": 0, "raw_business_values_identity_or_credentials_persisted": 0},
        "summary": summary,
        "case_crosswalk_matrix": rows,
        "crosswalk_state_contract": ["EXACT_REUSE", "EXACT_NEW", "SEMANTIC_REPLACEMENT", "DEPRECATED", "UNRESOLVED"],
        "required_case_crosswalk_fields": ["baseline_case_id", "newer_case_id", "baseline_action_or_surface", "newer_action_or_surface", "case_kind", "precondition_class", "expected_outcome_class", "effect_or_assertion_class", "equivalence_state", "accountable_disposition_and_expiry"],
        "interpretation_rules": [
            "Exact case-ID overlap proves identity reuse only; it does not prove execution or acceptance.",
            "Casefold action+kind overlap is a review candidate, not semantic equivalence.",
            "Different IDs or action names may be renamed duplicates; unmatched cases are not additive until disposition.",
            "The 64 exact pricing IDs are reused and never counted again.",
            "All 238 unmatched newer cases contribute zero until case-level semantic crosswalk packets are accepted.",
        ],
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)} for name, path in sorted(paths.items())]
        + [{"name": "builder", "path": "scripts/windows/build_varanegar_golden_uat_crosswalk_feasibility_matrix_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha256(Path(__file__))}],
        "limits": ["No semantic equivalence packet is accepted.", "No unmatched case is added to the 1,404 design lower bound.", "No Golden/UAT case was executed and no readiness state was promoted."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
