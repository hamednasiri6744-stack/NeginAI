import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_project_job_costing_revenue_billing_contract_20260901.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_project_job_costing_revenue_billing_contract_20260901.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"project.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():s=load()["summary"];assert(s["module_count"],s["project_dimension_count"],s["module_dimension_assignment_count"],s["module_stage_assignment_count"])==(14,12,168,140);assert(s["module_failure_assignment_count"],s["module_gate_assignment_count"],s["module_role_assignment_count"])==(224,280,112)
def test_rules_fail_closed():assert set(load()["project_rule"].values())=={False}
def test_no_runtime_or_readiness_claim():d=load();s=d["summary"];assert set(d["safety"].values())=={0};assert s["accepted_operational_receipt_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert(s["risk_count"],s["mapped_risk_assignment_count"],s["design_lower_bound_after_project_contract"])==(84,343,1404)
def test_source_manifest_current():
 for x in load()["source_manifest"]:p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
