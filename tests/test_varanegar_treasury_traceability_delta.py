import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_treasury_traceability_delta_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_treasury_traceability_delta_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"t.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_counts():
 s=load()["summary"];assert s["treasury_evidence_count"]==4 and s["requirement_contract_delta_count"]==7 and s["module_evidence_link_count"]==14 and s["risk_evidence_link_count"]==25
def test_existing_risks_only():assert load()["summary"]["unique_linked_risk_count"]==9 and load()["checks"]["module_consistent"]
def test_additive_without_promotion():
 d=load();assert d["policy"]["relationship"]=="ADDITIVE_EVIDENCE_DELTA_ONLY" and d["summary"]["new_risk_count"]==d["summary"]["runtime_readiness_promotions"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
