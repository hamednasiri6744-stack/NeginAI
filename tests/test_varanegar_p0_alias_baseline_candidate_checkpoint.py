import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_p0_alias_baseline_candidate_checkpoint_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_p0_alias_baseline_candidate_checkpoint_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"checkpoint.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_manifest_current():
 d=load();assert d["validation"]=="PASS"
 for row in d["source_manifest"]:
  p=ROOT/row["path"];assert p.stat().st_size==row["size_bytes"];assert hashlib.sha256(p.read_bytes()).hexdigest()==row["sha256"]
