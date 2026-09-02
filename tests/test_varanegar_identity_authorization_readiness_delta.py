import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_identity_authorization_readiness_delta_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_identity_authorization_readiness_delta_20260829.json"
def test_delta(tmp_path):
 o=tmp_path/"identity_authorization_readiness.json";subprocess.run([sys.executable,str(B),"--output",str(o)],cwd=ROOT,check=True);d=json.loads(o.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["outcome_target_contract_module_count_before"],s["outcome_target_contract_module_count_after"])==(10,11);assert s["runtime_authorization_proven_module_count"]==s["command_ready_module_count"]==0
