import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_configuration_outcome_checkpoint_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_configuration_outcome_checkpoint_20260829.json"
def test_checkpoint():
 subprocess.run([sys.executable,str(B),"--output",str(A)],cwd=ROOT,check=True);d=json.loads(A.read_text(encoding="utf-8"));assert d["validation"]=="PASS" and all(d["checks"].values())
