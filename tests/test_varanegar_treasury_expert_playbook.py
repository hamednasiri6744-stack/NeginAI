import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_treasury_expert_playbook_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_treasury_expert_playbook_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"p.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_six_playbooks_have_seven_steps():assert len(load()["playbooks"])==6 and all(len(x["steps"])==7 for x in load()["playbooks"])
def test_four_way_diagnosis_only():assert load()["diagnostic_result_contract"]["allowed"]==["NATURAL_BEHAVIOR","DATA_DEBT","BUG","UNPROVEN"]
def test_critical_aggregate_facts_pinned():
 s=load()["summary"];assert s["underallocated_clone_count"]==57 and s["receipt_delete_batch_count"]==19
def test_no_diagnosis_or_repair_claim():
 s=load()["summary"];assert s["runtime_incidents_diagnosed_count"]==s["repairs_performed_count"]==s["owner_approved_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
