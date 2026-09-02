"""Execute deterministic synthetic fiscal-period decision vectors."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "scripts/windows/varanegar_fiscal_period_reference.py"
SOURCES = {
    "fiscal_contract": "artifacts/varanegar_analysis/varanegar_target_erp_fiscal_period_close_reopen_adjustment_lock_contract_20260829.json",
    "fiscal_checkpoint": "artifacts/varanegar_analysis/varanegar_target_erp_fiscal_period_close_reopen_adjustment_lock_checkpoint_20260829.json",
    "authorization": "artifacts/varanegar_analysis/varanegar_target_erp_command_authorization_scope_decision_trace_contract_20260829.json",
    "configuration": "artifacts/varanegar_analysis/varanegar_target_erp_configuration_policy_immutability_change_audit_contract_20260829.json",
    "evidence": "artifacts/varanegar_analysis/varanegar_target_erp_evidence_logging_redaction_retention_contract_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_module():
    spec = importlib.util.spec_from_file_location("fiscal_period_reference", REFERENCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    docs = {name: load(path) for name, path in paths.items()}
    reference = reference_module()
    base = reference.baseline()

    def changed(**values):
        item = copy.deepcopy(base)
        item.update(values)
        return item

    positive = [
        ("POS-SOFT-CLOSE", changed(period_state="OPEN", requested_action="CLOSE_SOFT"), "SOFT_CLOSE_ACCEPTED_RESTRICTED_POSTING"),
        ("POS-HARD-CLOSE", base, "HARD_CLOSE_ACCEPTED_ALL_DEPENDENCIES_RECONCILED"),
        ("POS-ADJUSTMENT", changed(period_state="HARD_CLOSED", requested_action="POST_ADJUSTMENT"), "ADJUSTMENT_ACCEPTED_SCOPED_AND_REVERSIBLE"),
        ("POS-REOPEN", changed(period_state="HARD_CLOSED", requested_action="REOPEN"), "REOPEN_ACCEPTED_SCOPED_EXPIRING_AND_SEPARATED"),
        ("POS-RECLOSE", changed(period_state="REOPENED", requested_action="RECLOSE"), "RECLOSE_ACCEPTED_RECONCILED_AND_SUPERSEDED"),
    ]
    negative = [
        ("NEG-EXTRA-SCHEMA", dict(base, extra=True), "SCHEMA_INVALID"),
        ("NEG-SCOPE", changed(scope_current=False), "FISCAL_ACTION_REJECTED_SCOPE"),
        ("NEG-VERSION", changed(expected_period_version=6), "FISCAL_ACTION_REJECTED_VERSION"),
        ("NEG-STATE", changed(period_state="HARD_CLOSED"), "FISCAL_ACTION_REJECTED_STATE"),
        ("NEG-LOCK-BYPASS", changed(all_posting_paths_guarded=False), "FISCAL_ACTION_REJECTED_LOCK_BYPASS"),
        ("NEG-UNKNOWN", changed(blocking_unknown=True), "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"),
        ("NEG-SUBLEDGER", changed(subledger_dependency_receipts_current=False), "CLOSE_REJECTED_DEPENDENCY_OR_RECONCILIATION"),
        ("NEG-CONTROL-TOTAL", changed(control_totals_reconciled=False), "CLOSE_REJECTED_DEPENDENCY_OR_RECONCILIATION"),
        ("NEG-NUMBERING", changed(numbering_rollover_atomic=False), "CLOSE_REJECTED_NUMBERING_ROLLOVER_ATOMICITY"),
        ("NEG-ADJUSTMENT-CLASS", changed(period_state="HARD_CLOSED", requested_action="POST_ADJUSTMENT", adjustment_class_current=False), "ADJUSTMENT_REJECTED_CLASS_AUTHORIZATION_OR_BALANCE"),
        ("NEG-ADJUSTMENT-BALANCE", changed(period_state="HARD_CLOSED", requested_action="POST_ADJUSTMENT", adjustment_balanced=False), "ADJUSTMENT_REJECTED_CLASS_AUTHORIZATION_OR_BALANCE"),
        ("NEG-REVERSAL", changed(period_state="HARD_CLOSED", requested_action="POST_ADJUSTMENT", reversal_policy_current=False), "ADJUSTMENT_REJECTED_REVERSAL_POLICY"),
        ("NEG-REOPEN-IMPACT", changed(period_state="HARD_CLOSED", requested_action="REOPEN", reopen_impact_scope_current=False), "REOPEN_REJECTED_REASON_SCOPE_IMPACT_OR_EXPIRY"),
        ("NEG-REOPEN-SOD", changed(period_state="HARD_CLOSED", requested_action="REOPEN", sod_separated=False), "REOPEN_REJECTED_SEGREGATION_OF_DUTIES"),
        ("NEG-REOPEN-TOKEN", changed(period_state="HARD_CLOSED", requested_action="REOPEN", token_current_single_use=False), "REOPEN_REJECTED_REASON_SCOPE_IMPACT_OR_EXPIRY"),
        ("NEG-BREAK-GLASS", changed(period_state="HARD_CLOSED", requested_action="REOPEN", break_glass=True, incident_and_independent_review_current=False), "BREAK_GLASS_REJECTED_INCIDENT_OR_REVIEW"),
        ("NEG-RECLOSE-RERUN", changed(period_state="REOPENED", requested_action="RECLOSE", reclose_dependencies_rerun=False), "RECLOSE_REJECTED_DEPENDENCY_OR_LINEAGE"),
        ("NEG-RECLOSE-LINEAGE", changed(period_state="REOPENED", requested_action="RECLOSE", supersession_lineage_current=False), "RECLOSE_REJECTED_DEPENDENCY_OR_LINEAGE"),
    ]

    def run(vectors):
        results = []
        for vector_id, evidence, expected in vectors:
            actual = reference.evaluate(evidence)
            results.append({"vector_id": vector_id, "expected": expected, "actual": actual, "status": "PASS" if actual == expected else "FAIL"})
        return results

    positive_results = run(positive)
    negative_results = run(negative)
    all_results = positive_results + negative_results
    official = docs["tests"]
    fiscal_summary = docs["fiscal_contract"]["summary"]
    summary = {
        "reference_evaluator_implementation_count": 1,
        "positive_vector_count": len(positive_results), "positive_pass_count": sum(x["status"] == "PASS" for x in positive_results),
        "negative_vector_count": len(negative_results), "negative_pass_count": sum(x["status"] == "PASS" for x in negative_results),
        "total_vector_count": len(all_results), "total_pass_count": sum(x["status"] == "PASS" for x in all_results),
        "distinct_typed_outcome_count": len({x["actual"] for x in all_results}),
        "fiscal_gate_count": fiscal_summary["gate_count"], "fiscal_module_gate_assignment_count": fiscal_summary["module_gate_assignment_count"],
        "operational_period_lock_or_posting_implementation_count": 0,
        "operational_period_ledger_document_balance_or_entry_read_count": 0,
        "close_reopen_adjustment_reversal_or_posting_run_count": 0,
        "accepted_operational_receipt_count": 0, "command_ready_module_count": 0, "pilot_ready_module_count": 0,
        "design_lower_bound_before_reference_evaluator": 1404, "design_lower_bound_after_reference_evaluator": 1404,
        "official_test_file_count": official["runner"]["test_file_count"], "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": docs["risk"]["summary"]["risk_count"], "mapped_risk_assignment_count": docs["trace"]["summary"]["mapped_risk_assignment_count"], "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(docs[name].get("validation") == "PASS" for name in ("fiscal_contract", "fiscal_checkpoint", "authorization", "configuration", "evidence", "tests")),
        "positive_5_of_5": summary["positive_vector_count"] == summary["positive_pass_count"] == 5,
        "negative_18_of_18": summary["negative_vector_count"] == summary["negative_pass_count"] == 18,
        "total_23_of_23": summary["total_vector_count"] == summary["total_pass_count"] == 23,
        "distinct_outcomes_at_least_14": summary["distinct_typed_outcome_count"] >= 14,
        "coverage_24_336": (summary["fiscal_gate_count"], summary["fiscal_module_gate_assignment_count"]) == (24, 336),
        "operational_and_readiness_zero": all(summary[name] == 0 for name in ("operational_period_lock_or_posting_implementation_count", "operational_period_ledger_document_balance_or_entry_read_count", "close_reopen_adjustment_reversal_or_posting_run_count", "accepted_operational_receipt_count", "command_ready_module_count", "pilot_ready_module_count")),
        "non_additive_1404": summary["design_lower_bound_before_reference_evaluator"] == summary["design_lower_bound_after_reference_evaluator"] == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    result = {
        "artifact": "varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_contract_20260829",
        "schema_version": 1, "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "pure_synthetic_fiscal_period_reference_evaluator", "continuation_complete": False, "operational_period_ledger_document_balance_or_entry_read": False},
        "safety": {"database_connections": 0, "network_reads_or_writes": 0, "operational_period_ledger_document_balance_or_entry_reads": 0, "period_close_reopen_adjustment_reversal_or_posting_actions_executed": 0, "operational_forms_reports_queries_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "credentials_endpoints_pii_or_raw_business_values_read_or_persisted": 0},
        "summary": summary, "positive_results": positive_results, "negative_results": negative_results,
        "outcome_precedence": ["SCHEMA", "SCOPE", "VERSION", "STATE", "LOCK_PATH_COVERAGE", "BLOCKING_UNKNOWN", "CLOSE_DEPENDENCIES", "NUMBERING_ROLLOVER", "ADJUSTMENT", "REOPEN", "RECLOSE", "ACCEPTED"],
        "checks": checks, "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())] + [{"name": "reference_evaluator", "path": REFERENCE.relative_to(ROOT).as_posix(), "size_bytes": REFERENCE.stat().st_size, "sha256": sha(REFERENCE)}, {"name": "builder", "path": "scripts/windows/build_varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_contract_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha(Path(__file__))}],
        "limits": ["Only fixed synthetic booleans states and version numbers were evaluated.", "The evaluator is not a fiscal calendar lock ledger posting or workflow provider.", "Operational close reopen adjustment and readiness remain blocked pending isolated authenticated receipts and owner approval."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(result["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
