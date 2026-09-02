import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_treasury_golden_uat_checkpoint_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_treasury_golden_uat_checkpoint_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"c.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_pass():assert load()["validation"]=="PASS" and not load()["failed_checks"]
def test_counts():assert load()["checks"]["twelve_commands"] and load()["checks"]["eighty_four_cases"]
def test_runtime_zero():assert load()["checks"]["runtime_owner_zero"] and load()["checks"]["readiness_zero"]
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(load()["safety"].values())=={0}
