import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_organization_context_outcome_envelope_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_organization_context_outcome_envelope_20260829.json"
def test_contract():
 subprocess.run([sys.executable,str(B),"--output",str(A)],cwd=ROOT,check=True);d=json.loads(A.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["command_contract_count"],s["existing_reused_case_count"])==(6,64);assert s["null_operation_date_profile_count"]==3 and s["server_command_revalidates_set_operation_date_permission"] is False;assert len(d["context_snapshot_contract"]["typed_date_concepts"])==4
