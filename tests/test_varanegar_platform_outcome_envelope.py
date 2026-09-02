import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_platform_outcome_envelope_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_platform_outcome_envelope_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"a.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_contract_and_open_decisions():
 d=load();s=d["summary"];assert d["validation"]=="PASS" and s["command_contract_count"]==6 and s["deployment_file_count"]==853 and s["deployment_external_reference_count"]==0;assert s["stack_selected_count"]==s["approved_recovery_target_count"]==s["deployment_owner_selected_count"]==0
def test_no_external_claim():assert all(x["status"]=="TARGET_DESIGN_ONLY_NOT_IMPLEMENTED" and "external" in x["transaction_boundary"] for x in load()["commands"])
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
