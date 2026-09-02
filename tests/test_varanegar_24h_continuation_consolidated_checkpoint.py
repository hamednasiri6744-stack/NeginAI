import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_24h_continuation_consolidated_checkpoint_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_24h_continuation_consolidated_checkpoint_20260829.json"
def test_checkpoint(tmp_path):o=tmp_path/"c.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);d=json.loads(o.read_text());assert d["validation"]=="PASS" and all(d["checks"].values())
def test_checked_in():assert json.loads(A.read_text(encoding="utf-8-sig"))["validation"]=="PASS"
