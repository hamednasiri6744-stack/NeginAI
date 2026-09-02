import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_identity_authorization_traceability_delta_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_identity_authorization_traceability_delta_20260829.json"
def test_delta():
 subprocess.run([sys.executable,str(B),"--output",str(A)],cwd=ROOT,check=True);d=json.loads(A.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["identity_authorization_evidence_count"],s["requirement_contract_delta_count"])==(5,10);assert (s["module_evidence_link_count"],s["risk_evidence_link_count"],s["runtime_readiness_promotions"])==(35,45,0)
