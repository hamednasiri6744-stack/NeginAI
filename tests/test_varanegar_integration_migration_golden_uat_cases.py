import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_integration_migration_golden_uat_cases_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_integration_migration_golden_uat_cases_20260829.json"
def test_golden(tmp_path):
 o=tmp_path/"integration_migration_golden.json";subprocess.run([sys.executable,str(B),"--output",str(o)],cwd=ROOT,check=True);d=json.loads(o.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["existing_reused_case_count"],s["delta_case_count"],s["combined_integration_acceptance_design_count"])==(34,35,69);assert len({x["case_id"] for x in d["cases"]})==35 and {x["status"] for x in d["cases"]}=={"DESIGNED_NOT_EXECUTED"}
