import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_command_readiness_delta_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_command_readiness_delta_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"d.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_only_accounting_changes():assert load()["delta"]=={"module":"accounting","dimension":"outcome_retry_idempotency.target_contract","before":False,"after":True,"basis":"artifacts/varanegar_analysis/varanegar_accounting_command_inventory_correction_20260829.json","runtime_readiness_effect":"NONE"}
def test_design_coverage_moves_three_to_four():assert load()["summary"]["outcome_target_contract_module_count_before"]==3 and load()["summary"]["outcome_target_contract_module_count_after"]==4
def test_runtime_and_readiness_remain_zero():
 s=load()["summary"];assert s["runtime_retry_idempotency_proven_module_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0
def test_accounting_evidence_mapped():
 a=next(x for x in load()["modules"] if x["module"]=="accounting");assert a["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"] and any(x["key"]=="accounting_correction" for x in a["mapped_validated_evidence"])
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
