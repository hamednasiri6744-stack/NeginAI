import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_treasury_command_readiness_delta_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_treasury_command_readiness_delta_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"r.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_only_treasury_changed():assert load()["delta"]["module"]=="receivables_treasury" and load()["summary"]["changed_module_count"]==1
def test_design_count_moves_four_to_five():
 s=load()["summary"];assert s["outcome_target_contract_module_count_before"]==4 and s["outcome_target_contract_module_count_after"]==5
def test_runtime_readiness_stays_zero():
 s=load()["summary"];assert s["runtime_retry_idempotency_proven_module_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
