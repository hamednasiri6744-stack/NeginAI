import hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_p4_failure_injection_adjudication_checkpoint_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_p4_failure_injection_adjudication_checkpoint_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"f.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_manifest_current():
 d=load();assert d["validation"]=="PASS"
 for x in d["source_manifest"]:
  p=R/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
