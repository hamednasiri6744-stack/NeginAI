import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_approval_synthetic_reference_evaluator_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_approval_synthetic_reference_evaluator_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"approval-reference.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_vectors_pass():s=load()["summary"];assert s["positive_vector_count"]==s["positive_pass_count"]==6;assert s["negative_vector_count"]==s["negative_pass_count"]==23;assert s["total_vector_count"]==s["total_pass_count"]==29 and s["distinct_typed_outcome_count"]>=14
def test_precedence_explicit():assert load()["outcome_precedence"][:4]==["SCHEMA","REQUEST_POLICY_THRESHOLD","QUALIFICATION_SOD_CONFLICT","DELEGATION_SCOPE_ACCEPTANCE_EXPIRY_REVOCATION"]
def test_no_operational_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_approval_workflow_or_token_implementation_count","operational_user_role_request_decision_delegation_or_effect_read_count","approve_delegate_escalate_breakglass_or_execute_run_count","accepted_operational_receipt_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_reference_evaluator"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
