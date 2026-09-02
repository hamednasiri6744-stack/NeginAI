import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_configuration_outcome_envelope_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_configuration_outcome_envelope_20260829.json"
def test_contract():
 subprocess.run([sys.executable,str(B),"--output",str(A)],cwd=ROOT,check=True);d=json.loads(A.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["command_contract_count"],s["existing_reused_case_count"])==(5,54);assert s["top_one_without_order_resolver_count"]==14 and s["runtime_effective_value_or_precedence_proven_count"]==0 and len(d["resolution_contract"]["required_trace"])==5
