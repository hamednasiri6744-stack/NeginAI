import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_platform_outcome_checkpoint_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_platform_outcome_checkpoint_20260829.json"
def test_checkpoint(tmp_path):
 o=tmp_path/"c.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);d=json.loads(o.read_text(encoding="utf-8"));assert d["validation"]=="PASS" and all(d["checks"].values())
def test_checked_in():assert json.loads(A.read_text(encoding="utf-8-sig"))["validation"]=="PASS"
