import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_distribution_golden_uat_cases_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_distribution_golden_uat_cases_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"g.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_four_by_seven():assert load()["summary"]["command_count"]==4 and load()["summary"]["case_count"]==28
def test_unique_ids():assert len({x["case_id"] for x in load()["cases"]})==28
def test_durable_and_unknown():
 x={c["expected_outcome"] for c in load()["cases"]};assert any("DURABLE_EFFECT" in y for y in x) and "UNKNOWN_REQUIRES_READBACK" in x
def test_unexecuted():assert set(x["status"] for x in load()["cases"])=={"DESIGNED_NOT_EXECUTED"}
def test_runtime_zero():
 s=load()["summary"];assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
