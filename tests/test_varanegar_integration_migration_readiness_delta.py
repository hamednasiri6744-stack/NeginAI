import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_integration_migration_readiness_delta_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_integration_migration_readiness_delta_20260829.json"
def test_readiness(tmp_path):
 o=tmp_path/"integration_migration_readiness.json";subprocess.run([sys.executable,str(B),"--output",str(o)],cwd=ROOT,check=True);d=json.loads(o.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["outcome_target_contract_module_count_before"],s["outcome_target_contract_module_count_after"])==(8,9);assert s["changed_module_count"]==1 and s["command_ready_module_count"]==0
