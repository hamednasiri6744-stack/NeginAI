import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_master_data_golden_uat_cases_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_master_data_golden_uat_cases_20260829.json"
def test_cases():
 subprocess.run([sys.executable,str(B),"--output",str(A)],cwd=ROOT,check=True);d=json.loads(A.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["existing_reused_case_count"],s["delta_case_count"],s["combined_master_data_acceptance_design_count"])==(114,35,149);assert len({x["case_id"] for x in d["cases"]})==35 and s["merge_executed_count"]==0
