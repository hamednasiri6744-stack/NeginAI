import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_integration_migration_outcome_envelope_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_integration_migration_outcome_envelope_20260829.json"
def test_contract(tmp_path):
 o=tmp_path/"integration_migration_outcome.json";subprocess.run([sys.executable,str(B),"--output",str(o)],cwd=ROOT,check=True);d=json.loads(o.read_text(encoding="utf-8"));s=d["summary"];assert d["validation"]=="PASS" and (s["command_contract_count"],s["existing_reused_case_count"],s["migration_slice_count"])==(6,34,12);assert s["rule_transport_unproven_gate_count"]==6 and len(d["global_invariants"])==9 and {x["runtime_effect_parity"] for x in d["commands"]}=={"UNPROVEN"}
