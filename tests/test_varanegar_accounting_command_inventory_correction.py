import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_accounting_command_inventory_correction_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_accounting_command_inventory_correction_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"c.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_inventory_corrected_from_seven_to_six():assert load()["summary"]["prior_candidate_count"]==7 and load()["summary"]["corrected_command_count"]==6
def test_ui_close_removed():assert load()["removed_candidates"]==[{"candidate":"accounting.manual_voucher.cancel","classification":"REJECTED_UI_CLOSE_ONLY","evidence":"InternalCancelCommand has three instructions and only Form.Close","target_erp_effect":"no financial cancel/reversal API"}]
def test_manual_save_now_has_static_transaction_owner():
 x=next(x for x in load()["corrected_truth_table"] if x["command_id"]=="accounting.manual_voucher.save");assert "Transaction.Begin" in x["transaction_owner"] and "Commit" in x["transaction_owner"]
def test_design_present_runtime_zero():assert load()["summary"]["accounting_target_outcome_contract_present"] and load()["summary"]["runtime_effect_parity_proven_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
