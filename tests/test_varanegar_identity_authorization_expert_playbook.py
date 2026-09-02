import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_identity_authorization_expert_playbook_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_identity_authorization_expert_playbook_20260829.json"
def test_playbook(tmp_path):
 output=tmp_path/"identity_authorization_expert_playbook.json";subprocess.run([sys.executable,str(B),"--output",str(output)],cwd=ROOT,check=True);d=json.loads(output.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["playbook_count"],s["minimum_step_count"])==(7,9);assert s["runtime_incidents_diagnosed_count"]==0 and len(d["diagnostic_result_contract"]["allowed"])==4
