import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_pricing_rule_outcome_envelope_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_pricing_rule_outcome_envelope_20260829.json"
def test_build_and_contract():
 subprocess.run([sys.executable,str(B),"--output",str(A)],cwd=ROOT,check=True);d=json.loads(A.read_text(encoding="utf-8"));s=d["summary"]
 assert d["validation"]=="PASS" and s["command_contract_count"]==7 and s["existing_reused_golden_case_count"]==64
 assert s["linear_max_id_plus_one_literal_count"]==1 and s["replication_unproven_gate_count"]==6
 assert len(d["lifecycle"])==4 and len(d["global_invariants"])==8
 assert {x["runtime_effect_parity"] for x in d["commands"]}=={"UNPROVEN"}
 assert d["publication_contract"]["classification"].startswith("TARGET_DURABLE_EFFECT")
 assert set(v for k,v in d["safety"].items() if k!="mode")=={0}
