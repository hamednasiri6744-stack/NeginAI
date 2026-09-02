import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_treasury_golden_uat_cases_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_treasury_golden_uat_cases_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"g.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_twelve_commands_have_seven_cases_each():
 d=load();assert d["summary"]["case_count"]==84 and all(sum(x["command_id"]==c["id"] for x in d["cases"])==7 for c in json.loads((ROOT/"artifacts/varanegar_analysis/varanegar_treasury_command_outcome_envelope_20260829.json").read_text(encoding="utf-8-sig"))["commands"])
def test_case_ids_unique():assert len({x["case_id"] for x in load()["cases"]})==84
def test_durable_and_unknown_outcomes_covered():
 outcomes={x["expected_outcome"] for x in load()["cases"]};assert "REJECTED_WITH_DURABLE_EFFECT" in outcomes and "UNKNOWN_REQUIRES_READBACK" in outcomes
def test_all_are_unexecuted_designs():assert set(x["status"] for x in load()["cases"])=={"DESIGNED_NOT_EXECUTED"}
def test_runtime_and_readiness_zero():
 s=load()["summary"];assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
