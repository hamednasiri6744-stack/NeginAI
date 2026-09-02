import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_reporting_output_traceability_delta_20260829.py";ARTIFACT=ROOT/"artifacts/varanegar_analysis/varanegar_reporting_output_traceability_delta_20260829.json"
def load():return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"t.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_counts():
 s=load()["summary"];assert s["reporting_output_evidence_count"]==5 and s["requirement_contract_delta_count"]==10 and s["module_evidence_link_count"]==30 and s["risk_evidence_link_count"]==40
def test_existing_and_consistent():assert load()["summary"]["unique_linked_risk_count"]==8 and load()["checks"]["module_consistent"]
def test_additive_no_promotion():
 d=load();assert d["policy"]["relationship"]=="ADDITIVE_EVIDENCE_DELTA_ONLY" and d["summary"]["new_risk_count"]==d["summary"]["runtime_readiness_promotions"]==0
def test_sources_current():
 for item in load()["source_manifest"]:
  path=ROOT/item["path"];assert path.stat().st_size==item["size_bytes"] and hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
