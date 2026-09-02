import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_reporting_output_expert_playbook_20260829.py";ARTIFACT=ROOT/"artifacts/varanegar_analysis/varanegar_reporting_output_expert_playbook_20260829.json"
def load():return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 output=tmp_path/"p.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(output)],check=True);assert json.loads(output.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_six_with_nine_steps():assert len(load()["playbooks"])==6 and all(len(x["steps"])==9 for x in load()["playbooks"])
def test_four_way_only():assert load()["diagnostic_result_contract"]["allowed"]==["NATURAL_BEHAVIOR","DATA_DEBT","BUG","UNPROVEN"]
def test_counts_and_rules():
 d=load();assert d["summary"]["command_surface_count"]==8 and d["summary"]["golden_case_count"]==56;assert d["checks"]["completion_and_watermark_rules"]
def test_runtime_zero():
 s=load()["summary"];assert s["runtime_incidents_diagnosed_count"]==s["repairs_or_replays_performed_count"]==s["owner_approved_count"]==0
def test_sources_current():
 for item in load()["source_manifest"]:
  path=ROOT/item["path"];assert path.stat().st_size==item["size_bytes"] and hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"]
def test_safety_zero():assert set(value for key,value in load()["safety"].items() if key!="mode")=={0}
