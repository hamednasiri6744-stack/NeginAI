"""Refresh the active continuation gap ranking after six command-contract modules."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "readiness": "artifacts/varanegar_analysis/varanegar_distribution_command_readiness_delta_20260829.json",
    "reports": "artifacts/varanegar_analysis/varanegar_report_surface_closure_ledger_20260829.json",
    "report_golden": "artifacts/varanegar_analysis/varanegar_report_golden_fixture_design_20260829.json",
    "print_batch": "artifacts/varanegar_analysis/domains/print_batch_contract_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_traceability_delta_checkpoint_20260829.json",
}
GAPS = [
    {"rank": 1, "gap_id": "G24-REPORTING-OUTCOME-RETRY", "domain": "reporting_documents", "class": "STATIC_AND_DESIGN_ADVANCEABLE", "reason": "eight command-bearing output surfaces have partial-failure fixtures but the module-level outcome/retry target contract is absent", "next_artifact": "report output command/outcome/retry envelope", "risk_links": ["R-002", "R-005", "R-007", "R-017", "R-023", "R-059"]},
    {"rank": 2, "gap_id": "G24-PRICING-OUTCOME-IDEMPOTENCY", "domain": "pricing_rules", "class": "STATIC_AND_DESIGN_ADVANCEABLE", "reason": "rule authoring and allocation evidence exists while effective precedence and collision-safe command outcomes remain open", "next_artifact": "pricing rule command/outcome and allocation contract", "risk_links": ["R-005", "R-006", "R-024"]},
    {"rank": 3, "gap_id": "G24-CONFIGURATION-CHANGE-OUTCOME", "domain": "configuration", "class": "DESIGN_ADVANCEABLE_OWNER_BLOCKED", "reason": "effective precedence is evidenced but material-setting change approval and typed outcomes are not contracted", "next_artifact": "versioned configuration change receipt design", "risk_links": ["R-005", "R-020", "R-023"]},
    {"rank": 4, "gap_id": "G24-MASTER-DATA-QUARANTINE-COMMANDS", "domain": "master_data", "class": "DESIGN_ADVANCEABLE_OWNER_BLOCKED", "reason": "duplicate and sentinel evidence requires quarantine/merge outcomes without automatic identity collapse", "next_artifact": "master-data quarantine and merge command boundary", "risk_links": ["R-006", "R-008", "R-019"]},
    {"rank": 5, "gap_id": "G24-IDENTITY-GRANT-OWNER-GATE", "domain": "identity_authorization", "class": "EXTERNAL_AUTHORITY_REQUIRED", "reason": "aggregate legacy rights cannot identify real target role assignments or authorize grants", "next_artifact": "owner-approved identity and grant policy", "risk_links": ["R-001", "R-003", "R-023"]},
    {"rank": 6, "gap_id": "G24-INTEGRATION-RUNTIME-GATE", "domain": "integration_migration", "class": "EXTERNAL_AUTHORITY_REQUIRED", "reason": "source snapshot/import, dual-write and cutover remain unauthorized runtime work", "next_artifact": "isolated migration rehearsal evidence", "risk_links": ["R-006", "R-007", "R-023"]},
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / rel for name, rel in SOURCES.items()}
    data = {name: load(path) for name, path in paths.items()}
    readiness_modules = data["readiness"]["modules"]
    reporting = next(x for x in readiness_modules if x["module"] == "reporting_documents")
    partial_cases = [x for x in data["report_golden"]["cases"] if x["case_id"].endswith(".command_partial_failure")]
    summary = {
        "gap_count": len(GAPS),
        "static_or_design_advanceable_count": 4,
        "external_authority_required_count": 2,
        "outcome_target_contract_module_count": data["readiness"]["summary"]["outcome_target_contract_module_count_after"],
        "report_command_surface_count": data["reports"]["summary"]["command_surface_count"],
        "report_partial_failure_case_count": len(partial_cases),
        "print_render_path_count": data["print_batch"]["summary"]["render_path_count"],
        "print_completion_gated_path_count": data["print_batch"]["summary"]["completion_gated_render_path_count"],
        "selected_gap_id": GAPS[0]["gap_id"],
        "runtime_readiness_promotions": 0,
        "risk_count": 84,
        "mapped_risk_assignment_count": 343,
        "new_risk_count": 0,
    }
    known_risks = {x["id"] for x in data["risk"]["risks"]}
    checks = {
        "sources_pass": all(x["validation"] == "PASS" for x in data.values()),
        "six_ranked": len(GAPS) == 6 and [x["rank"] for x in GAPS] == list(range(1, 7)),
        "six_contract_modules": summary["outcome_target_contract_module_count"] == 6,
        "reporting_contract_open": reporting["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"] is False,
        "eight_command_surfaces_and_cases": summary["report_command_surface_count"] == summary["report_partial_failure_case_count"] == 8,
        "print_paths_pinned": summary["print_render_path_count"] == 7 and summary["print_completion_gated_path_count"] == 4,
        "selected_reporting": summary["selected_gap_id"] == "G24-REPORTING-OUTCOME-RETRY",
        "risk_links_existing": all(risk in known_risks for gap in GAPS for risk in gap["risk_links"]),
        "base_stable": data["risk"]["summary"]["risk_count"] == 84 and data["trace"]["summary"]["mapped_risk_assignment_count"] == 343,
        "runtime_zero": summary["runtime_readiness_promotions"] == summary["new_risk_count"] == 0,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    out = {
        "artifact": "varanegar_24h_continuation_gap_refresh_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "safety": {"mode": "OFFLINE_FROM_PERSISTED_HASHED_EVIDENCE", "database_connections": 0, "commands_forms_reports_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "sensitive_values_persisted": 0},
        "summary": summary,
        "prioritized_gaps": GAPS,
        "selection_boundary": {"selected": "reporting_documents outcome/retry design", "not_selected": "report result-parity execution or owner-approved Golden values", "reason": "the command-output contract can advance offline while runtime parity remains an external gate"},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())],
        "confidence": {"ranking": "HIGH_WITHIN_CURRENT_EVIDENCE", "runtime_parity": "NOT_PROVEN"},
        "limits": ["Ranking is evidence-work priority, not operational business urgency.", "No output command, report or import was executed.", "Owner and runtime gates remain external."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(out["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
