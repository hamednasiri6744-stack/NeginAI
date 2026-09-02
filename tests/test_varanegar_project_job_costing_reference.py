import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_project_job_costing_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_all_positive_operations():
 expected={"COMMIT":"COMMITMENT_ACCEPTED_FUNDED_AND_BALANCED","POST_COST":"PROJECT_COST_ACCEPTED_APPROVED_AND_ALLOCATED","MEASURE":"PROGRESS_ACCEPTED_WBS_AND_EVIDENCE_CURRENT","BILL":"PROJECT_BILLING_ACCEPTED_TERMS_AND_PROGRESS","RECOGNIZE_REVENUE":"PROJECT_REVENUE_ACCEPTED_POLICY_PROGRESS_AND_PERIOD","RECONCILE":"PROJECT_RECONCILIATION_ACCEPTED_COST_REVENUE_BILLING_GL"}
 for op,out in expected.items():assert M.evaluate(dict(M.baseline(),operation=op))==out
def test_global_precedence():assert M.evaluate(dict(M.baseline(),scope_current=False))=="PROJECT_REJECTED_SCOPE_OR_WBS_VERSION";assert M.evaluate(dict(M.baseline(),unknown_commit=True))=="PROJECT_UNKNOWN_RECONCILIATION_REQUIRED"
def test_cost_and_billing_fail_closed():assert M.evaluate(dict(M.baseline(),operation="POST_COST",time_expense_approved=False))=="PROJECT_COST_REJECTED_APPROVAL_ALLOCATION_OR_PERIOD";assert M.evaluate(dict(M.baseline(),operation="BILL",billing_terms_current=False))=="PROJECT_BILLING_REJECTED_TERMS_OR_PROGRESS"
def test_revenue_and_reconciliation_fail_closed():assert M.evaluate(dict(M.baseline(),operation="RECOGNIZE_REVENUE",revenue_policy_current=False))=="PROJECT_REVENUE_REJECTED_POLICY_PROGRESS_OR_PERIOD";assert M.evaluate(dict(M.baseline(),operation="RECONCILE",project_subledger_gl_reconciled=False))=="PROJECT_RECONCILIATION_REJECTED_SUBLEDGER_OR_GL"
def test_schema_exact():e=copy.deepcopy(M.baseline());e["extra"]=True;assert M.evaluate(e)=="SCHEMA_INVALID"
