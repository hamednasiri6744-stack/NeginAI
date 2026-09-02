import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; B=ROOT/"scripts/windows/build_varanegar_expert_incident_playbook_20260829.py"; A=ROOT/"artifacts/varanegar_analysis/varanegar_expert_incident_playbook_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"x.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_ten_required_incidents():
 x=load();assert x["summary"]["playbook_count"]==10;assert {p["playbook_id"] for p in x["playbooks"]}=={f"PB-{i:02}" for i in range(1,11)}
def test_each_has_evidence_steps_decision_and_stop():
 assert all(len(x["evidence_to_collect"])>=3 and len(x["diagnostic_steps"])>=6 and set(x["decision_rule"])=={"NATURAL_BEHAVIOR","DATA_DEBT","BUG","UNPROVEN"} and x["stop_conditions"] for x in load()["playbooks"])
def test_risks_are_existing_not_inflated():
 x=load();assert x["summary"]["risk_count"]==84 and x["summary"]["new_risk_count"]==0 and all(p["risk_links"] for p in x["playbooks"])
def test_target_erp_effect_present():assert all(len(x["erp_target_effect"])==3 for x in load()["playbooks"])
def test_sources_hashed():assert all(len(x["sha256"])==64 for x in load()["source_manifest"])
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
