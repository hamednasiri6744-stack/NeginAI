import hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_contract_portfolio_invariant_audit_20260901.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_contract_portfolio_invariant_audit_20260901.json"
SPEC=importlib.util.spec_from_file_location("portfolio_audit",B);MOD=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MOD)
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"portfolio-audit.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_contracts_pass_invariants():s=load()["summary"];assert s["audited_contract_count"]==s["passing_contract_count"]==54 and s["portfolio_finding_count"]==0
def test_identity_freshness_safety_runtime_and_lower_bound_clean():
 s=load()["summary"]
 for k in ("duplicate_artifact_id_count","stale_contract_manifest_count","nonzero_safety_contract_count","nonzero_runtime_or_readiness_contract_count","invalid_lower_bound_contract_count"):assert s[k]==0
def test_each_row_has_no_issue():assert all(x["issue_count"]==0 and not x["issues"] and x["source_count"]>0 for x in load()["audit_rows"])
def test_synthetic_run_counts_are_not_runtime():assert not MOD.zero_key("synthetic_negative_run_count") and not MOD.zero_key("positive_baseline_run_count") and not MOD.zero_key("reference_vector_run_count")
def test_domain_action_and_operational_counts_are_runtime():assert MOD.zero_key("plan_release_issue_report_run_count") and MOD.zero_key("operational_record_read_count") and MOD.zero_key("provider_selected_count") and MOD.zero_key("pilot_ready_module_count")
def test_no_runtime_or_readiness_claim():d=load();s=d["summary"];assert s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0};assert(s["risk_count"],s["mapped_risk_assignment_count"],s["design_lower_bound"])==(84,343,1404)
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
