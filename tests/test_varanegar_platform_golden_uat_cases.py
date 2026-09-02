import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_platform_golden_uat_cases_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_platform_golden_uat_cases_20260829.json"
def test_rebuild(tmp_path):o=tmp_path/"a.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text())["validation"]=="PASS"
def test_cases():d=json.loads(A.read_text(encoding="utf-8-sig"));assert len(d["cases"])==42 and {x["status"] for x in d["cases"]}=={"DESIGNED_NOT_EXECUTED"}
