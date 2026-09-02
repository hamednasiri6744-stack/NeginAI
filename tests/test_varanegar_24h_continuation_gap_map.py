import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_24h_continuation_gap_map_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_24h_continuation_gap_map_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"g.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_priority_and_classes():
 x=load();assert x["summary"]=={"gap_count":5,"static_or_design_advanceable_count":4,"external_authority_required_count":1,"selected_gap_id":"G24-ACCOUNTING-OUTCOME-LINEAGE","new_risk_count":0};assert [g["rank"] for g in x["prioritized_gaps"]]==[1,2,3,4,5]
def test_accounting_selection_is_evidence_backed():
 g=load()["prioritized_gaps"][0];assert g["domain"]=="accounting" and g["current_evidence"]["entrypoint_candidates"]==7 and g["current_evidence"]["empty_numbered_shells"]==1
def test_uat_is_external_gate():assert load()["prioritized_gaps"][-1]["class"]=="EXTERNAL_AUTHORITY_REQUIRED"
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
