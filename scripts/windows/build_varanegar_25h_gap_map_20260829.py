"""Build the drift-safe opening gap map for the 25-hour Varanegar pass."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "prior_bundle": "artifacts/varanegar_analysis/varanegar_15h_final_baseline_bundle_20260829.json",
    "report_gaps": "artifacts/varanegar_analysis/ui/varanegar_report_evidence_gaps_20260827.json",
    "report_contracts": "artifacts/varanegar_analysis/ui/varanegar_report_target_contracts_golden_cases_20260827.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    paths = {name: ROOT / rel for name, rel in SOURCES.items()}
    missing = [rel for name, rel in SOURCES.items() if not paths[name].is_file()]
    if missing:
        raise AssertionError({"missing_sources": missing})
    prior, gaps, contracts, risks, trace = (load(paths[name]) for name in SOURCES)
    drift = []
    for row in prior["manifest"]:
        path = ROOT / row["path"]
        actual = sha256(path) if path.is_file() else None
        if actual != row["sha256"]:
            drift.append({"path": row["path"], "expected_sha256": row["sha256"], "actual_sha256": actual})
    report_summary = gaps["summary"]
    contract_summary = contracts["summary"]
    priorities = [
        {
            "rank": 1,
            "gap_id": "G25-REPORT-IDENTITY-SCOPE-PARITY",
            "domain": "reports_and_reference_outputs",
            "why_now": "All 20 report surfaces lack result parity and exact SQL/parameter/effective-scope proof despite 20 target contracts and 175 offline golden cases.",
            "evidence": {
                "report_surface_count": report_summary["report_surface_count"],
                "result_parity_proven_count": report_summary["result_parity_proven_count"],
                "sql_identity_parameter_unproven_count": report_summary["gap_code_counts"]["SQL_IDENTITY_AND_PARAMETER_BINDING_UNPROVEN"],
                "effective_scope_unproven_count": report_summary["gap_code_counts"]["EFFECTIVE_SCOPE_SEMANTICS_UNPROVEN"],
                "offline_golden_case_count": contract_summary["golden_case_count"],
            },
            "closure_gate": "Bind exact query/procedure, parameters, filters, OperationDate/DC/FiscalYear/User scope and formulas; then reconcile a privacy-safe frozen snapshot in isolated UAT.",
            "confidence": "CONFIRMED_GAP",
            "risk_links": ["R-002", "R-023", "R-031"],
            "target_erp_effect": "report_source_of_truth_contract_and_reconciliation_gate",
        },
        {
            "rank": 2,
            "gap_id": "G25-COMMAND-TRUTH-TABLE-REMAINDER",
            "domain": "commands",
            "why_now": "The prior baseline intentionally keeps every module command-not-ready; remaining command paths need complete UI-to-side-effect truth tables.",
            "evidence": {"command_ready_module_count": prior["baseline"]["command_ready_module_count"]},
            "closure_gate": "For each prioritized command prove authorization, transaction owner, SQL/trigger mutations, side effects, outcome and retry semantics.",
            "confidence": "CONFIRMED_GAP",
            "risk_links": ["R-005", "R-007", "R-033", "R-034", "R-036"],
            "target_erp_effect": "deny_first_command_schema_and_unit_of_work_contract",
        },
        {
            "rank": 3,
            "gap_id": "G25-GOLDEN-CASE-RUNTIME-PARITY",
            "domain": "golden_cases",
            "why_now": "Offline cases define expectations but legacy runtime parity has deliberately not been claimed.",
            "evidence": {"report_golden_case_count": contract_summary["golden_case_count"], "legacy_execution_allowed_count": contract_summary["legacy_execution_allowed_count"]},
            "closure_gate": "Design anonymized fixtures and rollback-safe isolated UAT; do not run any operational scenario without explicit permission.",
            "confidence": "CONFIRMED_GAP",
            "risk_links": ["R-023", "R-026", "R-031"],
            "target_erp_effect": "acceptance_gate_and_migration_quarantine",
        },
    ]
    checks = {
        "prior_bundle_passes": prior["validation"] == "PASS",
        "prior_manifest_has_no_drift": len(drift) == 0 and len(prior["manifest"]) == 45,
        "prior_checkpoint_baseline_is_36_of_36": prior["baseline"]["checkpoint_count_20260829"] == 36 and prior["baseline"]["passing_checkpoint_count_20260829"] == 36,
        "report_gap_is_material_and_not_reextracted": report_summary["result_parity_proven_count"] == 0 and report_summary["report_surface_count"] == 20,
        "existing_golden_cases_are_reused": contract_summary["golden_case_count"] == 175,
        "risk_register_not_inflated": risks["summary"]["risk_count"] == 84,
        "traceability_baseline_is_stable": trace["summary"]["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "artifact": "varanegar_25h_opening_gap_map_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_EXISTING_ARTIFACT_CROSSWALK", "database_connections": 0, "live_ui_actions": 0, "operational_commands_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
        "baseline": {"manifest_entry_count": len(prior["manifest"]), "drift_count": len(drift), "risk_count": risks["summary"]["risk_count"], "mapped_risk_assignment_count": trace["summary"]["mapped_risk_assignment_count"], "command_ready_module_count": prior["baseline"]["command_ready_module_count"]},
        "prioritized_gaps": priorities,
        "checks": checks,
        "failed_checks": failed,
        "drift": drift,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)} for name, path in sorted(paths.items())],
        "limits": ["This gap map prioritizes existing evidence; it does not prove report result parity or operational behavior.", "Runtime parity remains gated on privacy-safe isolated UAT and explicit permission."]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(payload["validation"])
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
