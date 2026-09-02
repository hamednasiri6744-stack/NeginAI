import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_platform_readiness_delta_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_platform_readiness_delta_20260829.json"
def test_rebuild(tmp_path):o=tmp_path/"a.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text())["validation"]=="PASS"
def test_coverage():s=json.loads(A.read_text(encoding="utf-8-sig"))["summary"];assert (s["outcome_target_contract_module_count_before"],s["outcome_target_contract_module_count_after"])==(13,14) and s["command_ready_module_count"]==0
