import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_identity_integration_transaction_mutation_boundary_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_identity_integration_transaction_mutation_boundary_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"a.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text())["validation"]=="PASS"
def test_target_not_runtime():s=load()["summary"];assert s["command_count"]==s["command_with_target_transaction_design_count"]==s["command_with_target_mutation_effect_design_count"]==12 and s["command_with_complete_legacy_static_proof_count"]==s["runtime_effect_parity_proven_command_count"]==0
def test_safety():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
