import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_accounting_command_outcome_truth_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_accounting_command_outcome_truth_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"a.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_seven_truth_rows_and_confidence_split():
 s=load()["summary"];assert (s["command_candidate_count"],s["exact_external_procedure_command_count"],s["route_ambiguous_stock_command_count"],s["candidate_only_manual_command_count"])==(7,4,1,2)
def test_transfer_error_does_not_imply_rollback():
 x=next(x for x in load()["truth_table"] if x["command_id"]=="accounting.external_voucher.transfer");assert "committed" in x["outcome_contract"] and "never infer rollback" in x["retry_contract"]
def test_manual_paths_remain_candidates():assert all(x["confidence"]=="LOW_CANDIDATE_ONLY" for x in load()["truth_table"] if "manual_voucher" in x["command_id"])
def test_no_false_runtime_or_owner_claim():assert not any(x["runtime_effect_parity_proven"] or x["owner_approved"] for x in load()["truth_table"])
def test_lineage_counts_pinned():assert load()["lineage_diagnostic"]["current_pointer_not_maximum_count"]==1094 and load()["lineage_diagnostic"]["detached_trailing_event_count"]==14946
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
