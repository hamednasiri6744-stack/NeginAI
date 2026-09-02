import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_master_data_readiness_delta_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_master_data_readiness_delta_20260829.json"
def test_delta():
 subprocess.run([sys.executable,str(B),"--output",str(A)],cwd=ROOT,check=True);d=json.loads(A.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["outcome_target_contract_module_count_before"],s["outcome_target_contract_module_count_after"])==(12,13);assert s["runtime_master_effect_parity_proven_module_count"]==s["command_ready_module_count"]==0
