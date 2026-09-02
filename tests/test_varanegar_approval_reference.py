import copy,importlib.util
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/windows/varanegar_approval_reference.py";S=importlib.util.spec_from_file_location("ref",P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_approve_and_reject():assert M.evaluate(M.baseline())=="APPROVAL_GRANTED_QUORUM_SEQUENCE_AND_SOD_MET";assert M.evaluate(dict(M.baseline(),action="REJECT"))=="APPROVAL_REJECTED_REASON_AND_LINEAGE_RETAINED"
def test_delegation_expiry_and_revocation_fail_closed():assert M.evaluate(dict(M.baseline(),action="DELEGATE",delegation_used=True,delegation_expiry_current=False))=="DELEGATION_REJECTED_SCOPE_LIMIT_EXPIRY_REVOCATION_OR_QUALIFICATION";assert M.evaluate(dict(M.baseline(),action="DELEGATE",delegation_used=True,delegation_not_revoked=False))=="DELEGATION_REJECTED_SCOPE_LIMIT_EXPIRY_REVOCATION_OR_QUALIFICATION"
def test_timeout_never_auto_decides():assert M.evaluate(dict(M.baseline(),action="ESCALATE",timeout_reached=True,auto_decision_attempted=True))=="ESCALATION_REJECTED_AUTO_DECISION"
def test_breakglass_and_execution_fail_closed():assert M.evaluate(dict(M.baseline(),action="BREAK_GLASS",break_glass=True,incident_current=False))=="BREAK_GLASS_REJECTED_JUSTIFICATION_SCOPE_LIMIT_OR_REVIEW";assert M.evaluate(dict(M.baseline(),action="EXECUTE",token_current_single_use_scoped_fenced=False))=="EXECUTION_REJECTED_TOKEN_EFFECT_OR_RECONCILIATION"
def test_sod_and_quorum():assert M.evaluate(dict(M.baseline(),sod_separated=False))=="APPROVAL_REJECTED_QUALIFICATION_SOD_OR_CONFLICT";assert M.evaluate(dict(M.baseline(),quorum_met=False))=="APPROVAL_REJECTED_QUORUM_OR_SEQUENCE"
def test_schema_exact():e=copy.deepcopy(M.baseline());e["extra"]=True;assert M.evaluate(e)=="SCHEMA_INVALID"
