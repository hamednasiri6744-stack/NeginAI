import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_distribution_command_outcome_envelope_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_distribution_command_outcome_envelope_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"d.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_four_commands_unique():assert len(load()["commands"])==len({x["id"] for x in load()["commands"]})==4
def test_all_idempotency_and_transaction_gaps_preserved():
 s=load()["summary"];assert s["command_without_explicit_idempotency_count"]==s["command_with_unproven_physical_transaction_owner_count"]==4
def test_merge_owner_explicitly_unproven():assert next(x for x in load()["commands"] if x["command"]=="distribution.merge_or_adjust_exit")["transaction_owner"].startswith("UNPROVEN")
def test_durable_and_unknown_outcomes_present():
 x=load()["target_outcome_retry_envelope"]["outcome_codes"];assert "REJECTED_WITH_DURABLE_EFFECT" in x and "UNKNOWN_REQUIRES_READBACK" in x
def test_lifecycle_counts_pinned():
 s=load()["summary"];assert s["cancelled_exit_without_type60_delete_count"]==0 and s["logged_exit_absent_count"]==8 and s["historically_absent_distribution_count"]==6
def test_runtime_zero():
 s=load()["summary"];assert s["runtime_effect_parity_proven_count"]==s["executed_acceptance_case_count"]==s["owner_approved_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
