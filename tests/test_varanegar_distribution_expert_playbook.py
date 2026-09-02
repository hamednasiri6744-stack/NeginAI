import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_distribution_expert_playbook_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_distribution_expert_playbook_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"p.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_five_with_eight_steps():assert len(load()["playbooks"])==5 and all(len(x["steps"])==8 for x in load()["playbooks"])
def test_four_way_only():assert load()["diagnostic_result_contract"]["allowed"]==["NATURAL_BEHAVIOR","DATA_DEBT","BUG","UNPROVEN"]
def test_counts_pinned():
 s=load()["summary"];assert s["distribution_command_count"]==4 and s["golden_case_count"]==28 and s["logged_exit_absent_count"]==8 and s["historically_absent_distribution_count"]==6
def test_no_diagnosis_repair():
 s=load()["summary"];assert s["runtime_incidents_diagnosed_count"]==s["repairs_performed_count"]==s["owner_approved_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
