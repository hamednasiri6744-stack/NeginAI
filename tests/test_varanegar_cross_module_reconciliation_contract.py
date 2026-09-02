import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_cross_module_reconciliation_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"x.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_three_modules_and_twenty_two_commands():
 s=load()["summary"];assert s["module_count"]==3 and s["source_command_count"]==22
def test_edges_invariants_and_schema():
 s=load()["summary"];assert s["edge_type_count"]==7 and s["invariant_count"]==10 and s["schema_section_count"]==10
def test_amount_equality_and_max_history_are_rejected():
 d=load();payment=next(x for x in d["cross_module_edges"] if x["edge"]=="ngt_payment_to_backoffice_receipt");assert "amount equality" in payment["prohibited_inference"]
 assert any("MAX(id)" in x["rule"] for x in d["reconciliation_invariants"])
def test_quarantine_covers_pointer_shell_and_unknown():
 q=load()["target_reconciliation_receipt_schema"]["quarantine"];assert {"UNKNOWN_COMMAND_OUTCOME","POINTER_HISTORY_FORK","NUMBERED_EMPTY_SHELL"}<=set(q)
def test_aggregate_facts_pinned():
 s=load()["summary"];assert s["payment_receipt_linked_count"]==274 and s["payment_receipt_amount_scope_differs_count"]==270 and s["voucher_pointer_not_maximum_count"]==1094 and s["numbered_empty_shell_count"]==1
def test_runtime_zero():assert load()["summary"]["runtime_reconciliation_executed_count"]==load()["summary"]["owner_approved_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
