import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_identity_authorization_outcome_envelope_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_identity_authorization_outcome_envelope_20260829.json"
def test_contract(tmp_path):
 o=tmp_path/"identity_authorization_outcome.json";subprocess.run([sys.executable,str(B),"--output",str(o)],cwd=ROOT,check=True);d=json.loads(o.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["command_contract_count"],s["existing_reused_uat_case_count"])==(6,184);assert s["mutating_endpoint_without_declared_authorization_count"]==38 and s["scope_consistency_mismatch_count"]==58;assert d["decision_contract"]["deny_precedence"].startswith("explicit deny")
