"""Build a design-only fiscal period close/reopen/adjustment locking contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "blueprint": "artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json",
    "accounting": "artifacts/varanegar_analysis/varanegar_accounting_expert_playbook_contract_20260829.json",
    "organization": "artifacts/varanegar_analysis/varanegar_organization_context_expert_playbook_20260829.json",
    "semantics": "artifacts/varanegar_analysis/varanegar_target_erp_monetary_quantity_temporal_semantics_contract_20260829.json",
    "numbering": "artifacts/varanegar_analysis/varanegar_target_erp_document_numbering_series_void_rollover_contract_20260829.json",
    "authorization": "artifacts/varanegar_analysis/varanegar_target_erp_command_authorization_scope_decision_trace_contract_20260829.json",
    "configuration": "artifacts/varanegar_analysis/varanegar_target_erp_configuration_policy_immutability_change_audit_contract_20260829.json",
    "evidence": "artifacts/varanegar_analysis/varanegar_target_erp_evidence_logging_redaction_retention_contract_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

DIMENSIONS = [
    "TENANT_ORGANIZATION_LEDGER_FISCAL_CALENDAR_SCOPE",
    "PERIOD_STATE_MACHINE_AND_EFFECTIVE_BOUNDARIES",
    "SOFT_CLOSE_HARD_CLOSE_AND_PERMANENT_SEAL",
    "POSTING_DATE_OPERATION_DATE_AND_DOCUMENT_DATE_LOCK",
    "SUBLEDGER_TO_GENERAL_LEDGER_CLOSE_SEQUENCE",
    "INVENTORY_COSTING_NEGATIVE_STOCK_AND_VALUATION_CLOSE",
    "RECEIVABLE_PAYABLE_SETTLEMENT_AND_CUTOFF",
    "CASH_BANK_RECONCILIATION_AND_UNCLEARED_ITEMS",
    "TAX_WITHHOLDING_FISCALIZATION_AND_DECLARATION_LOCK",
    "PAYROLL_ASSET_DEPRECIATION_ACCRUAL_AND_FX_REVALUATION",
    "ADJUSTING_REVERSING_AND_POST_CLOSE_ENTRY_CLASS",
    "REOPEN_REASON_SCOPE_EXPIRY_AND_BREAK_GLASS_GOVERNANCE",
    "DEPENDENCY_RECONCILIATION_TRIAL_BALANCE_AND_CONTROL_TOTALS",
    "IMMUTABLE_CLOSE_EVIDENCE_RETENTION_AND_SUPERSESSION_LINEAGE",
]

STAGES = [
    ("FPC-01", "fiscal calendar scope and period boundaries frozen"),
    ("FPC-02", "open items and subledger cutoffs inventoried"),
    ("FPC-03", "inventory cost tax payroll asset accrual and fx prerequisites evaluated"),
    ("FPC-04", "bank settlement intercompany and control totals reconciled"),
    ("FPC-05", "soft close posting classes and exceptions activated"),
    ("FPC-06", "trial balance subledger and document completeness approved"),
    ("FPC-07", "hard close lock and numbering rollover atomically evidenced"),
    ("FPC-08", "late adjustment class authorization and reversal policy frozen"),
    ("FPC-09", "reopen request reason scope expiry and impact assessed"),
    ("FPC-10", "independent reopen approval and least-scope token issued"),
    ("FPC-11", "reclose rerun reconciliation and supersession completed"),
    ("FPC-12", "retention revocation incident and owner acceptance closed"),
]

POLICY_FIELDS = [
    "fiscal_lock_policy_id", "tenant_scope_sha256", "organization_scope_sha256", "ledger_scope_sha256",
    "fiscal_calendar_version", "period_id", "period_start", "period_end", "timezone_policy_sha256",
    "allowed_document_date_rule", "allowed_operation_date_rule", "allowed_posting_date_rule",
    "soft_close_policy_sha256", "hard_close_policy_sha256", "adjustment_class_policy_sha256",
    "reopen_policy_sha256", "subledger_sequence_sha256", "dependency_matrix_sha256",
    "numbering_rollover_policy_sha256", "owner_role_receipt_reference",
    "independent_approval_receipt_reference", "effective_from", "policy_sha256", "status",
]

CLOSE_RECEIPT_FIELDS = [
    "close_receipt_id", "period_id", "scope_reference_sha256", "policy_sha256", "expected_period_version",
    "closing_period_version", "close_level", "posting_class_set_sha256", "subledger_status_set_sha256",
    "inventory_cost_status_sha256", "bank_reconciliation_status_sha256", "tax_payroll_asset_status_sha256",
    "trial_balance_sha256", "control_total_set_sha256", "open_exception_set_sha256",
    "numbering_rollover_receipt_sha256", "operator_role_receipt_reference",
    "independent_review_receipt_reference", "typed_outcome", "closed_at", "evidence_set_sha256",
    "close_receipt_sha256",
]

REOPEN_RECEIPT_FIELDS = [
    "reopen_receipt_id", "period_id", "scope_reference_sha256", "closed_period_version",
    "reopen_reason_code", "affected_module_set_sha256", "affected_document_class_set_sha256",
    "impact_assessment_sha256", "requested_by_role_receipt_reference", "approved_by_role_receipt_reference",
    "segregation_of_duties_receipt_sha256", "break_glass_incident_reference", "authorization_token_sha256",
    "token_expires_at", "maximum_entry_count", "maximum_amount_policy_sha256", "reopened_at",
    "reclose_due_at", "typed_outcome", "redaction_attestation_sha256", "evidence_set_sha256",
    "reopen_receipt_sha256",
]

ADJUSTMENT_RECEIPT_FIELDS = [
    "adjustment_receipt_id", "period_id", "reopen_receipt_sha256", "adjustment_class",
    "document_reference_sha256", "original_document_reference_sha256", "posting_date", "operation_date",
    "reversal_due_date", "scope_reference_sha256", "currency_and_scale_policy_sha256",
    "debit_total_hash_sha256", "credit_total_hash_sha256", "control_total_set_sha256",
    "idempotency_key_sha256", "expected_period_version", "authorization_decision_sha256",
    "operator_role_receipt_reference", "independent_review_receipt_reference", "typed_outcome",
    "observed_at", "adjustment_receipt_sha256",
]

FAILURES = [
    ("FPF-01", "tenant organization ledger calendar or period scope omitted"),
    ("FPF-02", "posting date operation date or document date bypasses locked boundary"),
    ("FPF-03", "period state changed outside monotonic state machine or expected version"),
    ("FPF-04", "hard close accepted before required subledger sequence"),
    ("FPF-05", "inventory cost negative stock or valuation exception unresolved"),
    ("FPF-06", "receivable payable settlement cutoff or open item unresolved"),
    ("FPF-07", "bank cash reconciliation or uncleared item silently ignored"),
    ("FPF-08", "tax payroll asset accrual or fx dependency missing stale or revoked"),
    ("FPF-09", "trial balance control totals or document counts do not reconcile"),
    ("FPF-10", "close and numbering rollover are non-atomic or lineage missing"),
    ("FPF-11", "late entry posted without explicit adjustment class and reversal rule"),
    ("FPF-12", "reopen has no reason impact assessment expiry or affected scope"),
    ("FPF-13", "requester approver operator or reviewer violates segregation of duties"),
    ("FPF-14", "reopen token is reusable unbounded transferable or not revoked"),
    ("FPF-15", "reclose omits dependency rerun reconciliation or supersession lineage"),
    ("FPF-16", "old close receipt overwritten deleted or treated as current after reopen"),
    ("FPF-17", "closed period changed through import integration batch or direct storage path"),
    ("FPF-18", "close reopen adjustment or exception evidence missing stale or unretained"),
]

GATES = [
    ("FPG-01", "tenant organization ledger calendar and period scope complete"),
    ("FPG-02", "period boundary timezone and date semantics current"),
    ("FPG-03", "period state transition and expected version accepted"),
    ("FPG-04", "soft hard permanent close levels and posting classes explicit"),
    ("FPG-05", "all command import batch integration and direct paths share lock guard"),
    ("FPG-06", "subledger close dependency order current"),
    ("FPG-07", "inventory costing valuation and negative stock exceptions reconciled"),
    ("FPG-08", "receivable payable settlement and cutoff reconciled"),
    ("FPG-09", "cash bank reconciliation and uncleared exceptions accepted"),
    ("FPG-10", "tax withholding fiscalization and declaration lock current"),
    ("FPG-11", "payroll asset depreciation accrual and fx dependencies accepted"),
    ("FPG-12", "trial balance control totals and document counts reconcile"),
    ("FPG-13", "numbering rollover and close state are atomic and linked"),
    ("FPG-14", "adjusting and reversing entry classes are explicit"),
    ("FPG-15", "late posting authorization amount and count limits current"),
    ("FPG-16", "reopen reason impact scope and expiry complete"),
    ("FPG-17", "reopen requester approver operator reviewer separated"),
    ("FPG-18", "least-scope single-use reopen token current"),
    ("FPG-19", "break glass requires incident and independent review"),
    ("FPG-20", "reclose reruns every affected dependency"),
    ("FPG-21", "old and new close receipts linked by immutable supersession"),
    ("FPG-22", "isolated boundary concurrency retry and unknown tests accepted"),
    ("FPG-23", "redaction retention revocation and incident evidence current"),
    ("FPG-24", "no blocking unknown unresolved difference or owner exception"),
]

ROLES = [
    "FISCAL_CALENDAR_POLICY_OWNER_ROLE", "SUBLEDGER_CLOSE_OWNER_ROLE", "GENERAL_LEDGER_CLOSE_OPERATOR_ROLE",
    "FISCAL_REOPEN_REQUESTER_ROLE", "FISCAL_REOPEN_APPROVER_ROLE", "ADJUSTMENT_ENTRY_OPERATOR_ROLE",
    "INDEPENDENT_FISCAL_CLOSE_REVIEWER_ROLE",
]

OUTCOMES = [
    "SOFT_CLOSE_ACCEPTED_RESTRICTED_POSTING", "HARD_CLOSE_ACCEPTED_ALL_DEPENDENCIES_RECONCILED",
    "CLOSE_REJECTED_SCOPE_STATE_OR_VERSION", "CLOSE_REJECTED_DEPENDENCY_OR_RECONCILIATION",
    "POSTING_REJECTED_PERIOD_LOCK", "ADJUSTMENT_ACCEPTED_SCOPED_AND_REVERSIBLE",
    "ADJUSTMENT_REJECTED_CLASS_AUTHORIZATION_OR_BALANCE", "REOPEN_ACCEPTED_SCOPED_EXPIRING_AND_SEPARATED",
    "REOPEN_REJECTED_REASON_SCOPE_IMPACT_OR_EXPIRY", "REOPEN_REJECTED_SEGREGATION_OF_DUTIES",
    "BREAK_GLASS_REJECTED_INCIDENT_OR_REVIEW", "RECLOSE_ACCEPTED_RECONCILED_AND_SUPERSEDED",
    "RECLOSE_REJECTED_DEPENDENCY_OR_LINEAGE", "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    docs = {name: load(path) for name, path in paths.items()}
    modules = docs["blueprint"]["modules"]
    plans = [{"module_id": m["id"], "fiscal_period_lock_status": "DESIGN_ONLY", "approval_status": "MISSING", "readiness": "BLOCKED"} for m in modules]
    dimensions = [{"module_id": m["id"], "dimension": item, "status": "UNPROVEN", "accepted_receipt_count": 0} for m in modules for item in DIMENSIONS]
    stages = [{"module_id": m["id"], "stage_id": stage_id, "status": "UNEXECUTED", "accepted_receipt_count": 0} for m in modules for stage_id, _ in STAGES]
    failures = [{"module_id": m["id"], "failure_case_id": failure_id, "status": "UNEXECUTED", "accepted_result_count": 0} for m in modules for failure_id, _ in FAILURES]
    gates = [{"module_id": m["id"], "gate_id": gate_id, "status": "UNMET", "accepted_evidence_count": 0} for m in modules for gate_id, _ in GATES]
    roles = [{"module_id": m["id"], "role_type": role, "status": "UNASSIGNED"} for m in modules for role in ROLES]
    official = docs["tests"]
    summary = {
        "module_count": len(modules), "fiscal_period_dimension_count": len(DIMENSIONS),
        "module_dimension_assignment_count": len(dimensions), "lifecycle_stage_count": len(STAGES),
        "module_stage_assignment_count": len(stages), "fiscal_lock_policy_field_count": len(POLICY_FIELDS),
        "close_receipt_field_count": len(CLOSE_RECEIPT_FIELDS), "reopen_receipt_field_count": len(REOPEN_RECEIPT_FIELDS),
        "adjustment_receipt_field_count": len(ADJUSTMENT_RECEIPT_FIELDS), "failure_case_count": len(FAILURES),
        "module_failure_assignment_count": len(failures), "gate_count": len(GATES),
        "module_gate_assignment_count": len(gates), "role_type_count": len(ROLES),
        "module_role_assignment_count": len(roles), "typed_outcome_count": len(OUTCOMES),
        "operational_period_ledger_document_balance_or_entry_read_count": 0,
        "fiscal_policy_approved_count": 0, "period_close_or_reopen_run_count": 0,
        "adjusting_reversing_or_late_posting_run_count": 0, "reconciliation_or_rollover_run_count": 0,
        "accepted_operational_receipt_count": 0, "owner_approved_module_count": 0,
        "command_ready_module_count": 0, "pilot_ready_module_count": 0,
        "design_lower_bound_before_fiscal_period_contract": 1404,
        "design_lower_bound_after_fiscal_period_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": docs["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": docs["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(docs[name].get("validation") == "PASS" for name in ("accounting", "organization", "semantics", "numbering", "authorization", "configuration", "evidence", "tests")),
        "modules_14_dimensions_14_assignments_196": (summary["module_count"], summary["fiscal_period_dimension_count"], summary["module_dimension_assignment_count"]) == (14, 14, 196),
        "stages_12_assignments_168": (summary["lifecycle_stage_count"], summary["module_stage_assignment_count"]) == (12, 168),
        "fields_24_22_22_22": (summary["fiscal_lock_policy_field_count"], summary["close_receipt_field_count"], summary["reopen_receipt_field_count"], summary["adjustment_receipt_field_count"]) == (24, 22, 22, 22),
        "failures_18_assignments_252": (summary["failure_case_count"], summary["module_failure_assignment_count"]) == (18, 252),
        "gates_24_assignments_336": (summary["gate_count"], summary["module_gate_assignment_count"]) == (24, 336),
        "roles_7_assignments_98_outcomes_14": (summary["role_type_count"], summary["module_role_assignment_count"], summary["typed_outcome_count"]) == (7, 98, 14),
        "all_obligations_open": all(x["status"] == "UNPROVEN" for x in dimensions) and all(x["status"] == "UNEXECUTED" for x in stages + failures) and all(x["status"] == "UNMET" for x in gates) and all(x["status"] == "UNASSIGNED" for x in roles),
        "runtime_and_readiness_zero": all(summary[name] == 0 for name in ("operational_period_ledger_document_balance_or_entry_read_count", "fiscal_policy_approved_count", "period_close_or_reopen_run_count", "adjusting_reversing_or_late_posting_run_count", "reconciliation_or_rollover_run_count", "accepted_operational_receipt_count", "owner_approved_module_count", "command_ready_module_count", "pilot_ready_module_count")),
        "non_additive_1404": summary["design_lower_bound_before_fiscal_period_contract"] == summary["design_lower_bound_after_fiscal_period_contract"] == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    result = {
        "artifact": "varanegar_target_erp_fiscal_period_close_reopen_adjustment_lock_contract_20260829",
        "schema_version": 1, "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {"mode": "fiscal_period_close_reopen_adjustment_lock_design_only", "continuation_complete": False, "operational_period_ledger_document_balance_or_entry_read": False, "fiscal_calendar_lock_or_posting_provider_selected": False},
        "safety": {"database_connections": 0, "network_reads_or_writes": 0, "operational_period_ledger_document_balance_or_entry_reads": 0, "period_close_reopen_adjustment_reversal_or_posting_actions_executed": 0, "operational_forms_reports_queries_or_procedures_executed": 0, "assemblies_loaded_or_executed": 0, "data_mutations": 0, "credentials_endpoints_pii_or_raw_business_values_read_or_persisted": 0},
        "summary": summary, "risk_links": ["R-001", "R-004", "R-006", "R-007", "R-012", "R-019", "R-022", "R-025"],
        "fiscal_period_dimensions": DIMENSIONS, "lifecycle_stages": [{"stage_id": i, "stage": text} for i, text in STAGES],
        "fiscal_lock_policy_fields": POLICY_FIELDS, "close_receipt_fields": CLOSE_RECEIPT_FIELDS,
        "reopen_receipt_fields": REOPEN_RECEIPT_FIELDS, "adjustment_receipt_fields": ADJUSTMENT_RECEIPT_FIELDS,
        "failure_cases": [{"failure_case_id": i, "failure_case": text} for i, text in FAILURES],
        "gates": [{"gate_id": i, "gate": text, "failure_effect": "PERIOD_CLOSE_REOPEN_OR_POSTING_BLOCKED"} for i, text in GATES],
        "role_types": ROLES, "typed_outcomes": OUTCOMES, "module_fiscal_period_plans": plans,
        "module_dimension_assignments": dimensions, "module_stage_assignments": stages,
        "module_failure_assignments": failures, "module_gate_assignments": gates, "module_role_assignments": roles,
        "fiscal_period_rule": {
            "posting_path_may_bypass_period_lock": False, "document_date_alone_may_authorize_posting": False,
            "hard_close_may_precede_subledger_and_control_reconciliation": False,
            "unresolved_inventory_tax_bank_payroll_asset_accrual_or_fx_dependency_may_be_ignored": False,
            "late_posting_without_adjustment_class_and_reversal_rule_allowed": False,
            "reopen_without_reason_scope_impact_expiry_and_independent_approval_allowed": False,
            "reopen_requester_may_self_approve_operate_and_review": False,
            "reopen_token_may_be_reused_transferred_or_unbounded": False,
            "reclose_may_skip_affected_dependency_rerun": False,
            "prior_close_receipt_may_be_overwritten_or_deleted": False,
            "automatic_period_close_reopen_adjustment_or_readiness": False,
        },
        "checks": checks, "failed_checks": failed,
        "source_manifest": [{"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha(path)} for name, path in sorted(paths.items())] + [{"name": "builder", "path": "scripts/windows/build_varanegar_target_erp_fiscal_period_close_reopen_adjustment_lock_contract_20260829.py", "size_bytes": Path(__file__).stat().st_size, "sha256": sha(Path(__file__))}],
        "limits": ["This is design evidence only; no operational fiscal period ledger document balance or entry was read.", "No calendar lock posting database or external provider is selected.", "Close reopen adjustment and readiness remain blocked pending scoped policy isolated tests reconciliation approvals and retained receipts."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(result["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
