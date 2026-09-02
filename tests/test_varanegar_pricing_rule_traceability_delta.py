import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_pricing_rule_traceability_delta_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_pricing_rule_traceability_delta_20260829.json"
def test_trace_delta():
 subprocess.run([sys.executable,str(B),"--output",str(A)],cwd=ROOT,check=True);d=json.loads(A.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["pricing_rule_evidence_count"],s["requirement_contract_delta_count"],s["module_evidence_link_count"],s["risk_evidence_link_count"])==(5,10,30,40);assert s["new_risk_count"]==s["runtime_readiness_promotions"]==0
