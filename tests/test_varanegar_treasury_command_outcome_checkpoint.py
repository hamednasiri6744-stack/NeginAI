import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_treasury_command_outcome_checkpoint_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_treasury_command_outcome_checkpoint_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"c.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_checkpoint_passes():assert load()["validation"]=="PASS" and not load()["failed_checks"]
def test_counts_pinned():assert load()["checks"]["twelve_commands"] and load()["checks"]["seven_static_five_design"] and load()["checks"]["four_outcomes"]
def test_runtime_owner_zero():assert load()["checks"]["runtime_owner_zero"]
def test_previous_hash():
 x=load()["previous_checkpoint"];assert hashlib.sha256((ROOT/x["path"]).read_bytes()).hexdigest()==x["sha256"]
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(load()["safety"].values())=={0}
