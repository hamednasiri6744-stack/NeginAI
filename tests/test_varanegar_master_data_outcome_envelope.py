import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_master_data_outcome_envelope_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_master_data_outcome_envelope_20260829.json"
def test_contract():
 subprocess.run([sys.executable,str(B),"--output",str(A)],cwd=ROOT,check=True);d=json.loads(A.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["command_contract_count"],s["existing_reused_case_count"])==(10,114);assert (s["customer_goods_reused_case_count"],s["supplier_reused_case_count"],s["subscriber_reused_case_count"])==(64,32,18);assert s["automatic_merge_count"]==0 and len(d["identity_crosswalk_contract"]["negative_rules"])==5
