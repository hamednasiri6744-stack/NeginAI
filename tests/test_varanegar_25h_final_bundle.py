import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AN=ROOT/"artifacts/varanegar_analysis";B=AN/"varanegar_25h_final_baseline_bundle_20260829.json";T=AN/"varanegar_25h_final_test_result_20260829.json";BUILDER=ROOT/"scripts/windows/build_varanegar_25h_final_bundle_20260829.py"
def load():return json.loads(B.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"b.json";subprocess.run([sys.executable,str(BUILDER),"--test-result",str(T),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_gates_pass():assert load()["failed_checks"]==[] and all(load()["checks"].values())
def test_baseline_truthful():
 x=load()["baseline"];assert x["checkpoint_count"]==53 and x["risk_count"]==84 and x["mapped_risk_assignment_count"]==343 and x["command_ready_module_count"]==0 and x["report_result_parity_proven_count"]==0 and x["executed_golden_case_count"]==0 and x["expert_playbook_count"]==10
def test_requirement_audit_has_eight_items():assert len(load()["requirement_audit"])==8
def test_external_gates_explicit():assert len(load()["remaining_external_evidence_gates"])==4
def test_manifest_current():
 for x in load()["manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(load()["safety"].values())=={0}
