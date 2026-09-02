"""Pure synthetic project/job-costing evaluator; no ERP access or mutation."""
from __future__ import annotations
FIELDS={"operation","scope_current","wbs_version_current","funding_budget_current","commitment_balance_current","time_expense_approved","progress_measure_current","billing_terms_current","revenue_policy_current","cost_allocation_current","period_current","expected_version_match","idempotency_current","unknown_commit","project_subledger_gl_reconciled","blocking_unknown"}
BOOL=FIELDS-{"operation"};OPS={"COMMIT","POST_COST","MEASURE","BILL","RECOGNIZE_REVENUE","RECONCILE"}
def evaluate(e):
 if not isinstance(e,dict) or set(e)!=FIELDS:return "SCHEMA_INVALID"
 if e["operation"] not in OPS or any(type(e[x]) is not bool for x in BOOL):return "SCHEMA_INVALID"
 if not e["scope_current"] or not e["wbs_version_current"]:return "PROJECT_REJECTED_SCOPE_OR_WBS_VERSION"
 if not e["expected_version_match"] or not e["idempotency_current"]:return "PROJECT_REJECTED_VERSION_OR_IDEMPOTENCY"
 if e["unknown_commit"]:return "PROJECT_UNKNOWN_RECONCILIATION_REQUIRED"
 if e["blocking_unknown"]:return "MANUAL_REVIEW_REQUIRED_BLOCKING_UNKNOWN"
 op=e["operation"]
 if op=="COMMIT":return "COMMITMENT_ACCEPTED_FUNDED_AND_BALANCED" if e["funding_budget_current"] and e["commitment_balance_current"] else "COMMITMENT_REJECTED_BUDGET_OR_BALANCE"
 if op=="POST_COST":return "PROJECT_COST_ACCEPTED_APPROVED_AND_ALLOCATED" if e["time_expense_approved"] and e["cost_allocation_current"] and e["period_current"] else "PROJECT_COST_REJECTED_APPROVAL_ALLOCATION_OR_PERIOD"
 if op=="MEASURE":return "PROGRESS_ACCEPTED_WBS_AND_EVIDENCE_CURRENT" if e["progress_measure_current"] else "PROGRESS_REJECTED_MEASURE_OR_EVIDENCE"
 if op=="BILL":return "PROJECT_BILLING_ACCEPTED_TERMS_AND_PROGRESS" if e["billing_terms_current"] and e["progress_measure_current"] else "PROJECT_BILLING_REJECTED_TERMS_OR_PROGRESS"
 if op=="RECOGNIZE_REVENUE":return "PROJECT_REVENUE_ACCEPTED_POLICY_PROGRESS_AND_PERIOD" if e["revenue_policy_current"] and e["progress_measure_current"] and e["period_current"] else "PROJECT_REVENUE_REJECTED_POLICY_PROGRESS_OR_PERIOD"
 return "PROJECT_RECONCILIATION_ACCEPTED_COST_REVENUE_BILLING_GL" if e["project_subledger_gl_reconciled"] else "PROJECT_RECONCILIATION_REJECTED_SUBLEDGER_OR_GL"
def baseline():return {"operation":"COMMIT","scope_current":True,"wbs_version_current":True,"funding_budget_current":True,"commitment_balance_current":True,"time_expense_approved":True,"progress_measure_current":True,"billing_terms_current":True,"revenue_policy_current":True,"cost_allocation_current":True,"period_current":True,"expected_version_match":True,"idempotency_current":True,"unknown_commit":False,"project_subledger_gl_reconciled":True,"blocking_unknown":False}
