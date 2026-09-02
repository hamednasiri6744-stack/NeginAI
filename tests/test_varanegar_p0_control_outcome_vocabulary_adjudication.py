import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_p0_control_outcome_vocabulary_adjudication_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_p0_control_outcome_vocabulary_adjudication_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"matrix.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_packet_and_pair_counts():
 s=load()["summary"];assert s["control_kind_packet_count"]==6;assert s["non_failure_case_pair_count"]==46
def test_control_kind_distribution():
 s=load()["summary"];assert (s["authorization_pair_count"],s["concurrency_pair_count"],s["idempotency_pair_count"],s["reconciliation_pair_count"],s["scope_pair_count"],s["success_pair_count"])==(9,9,12,2,8,6)
def test_vocabulary_and_exactness():
 s=load()["summary"];assert (s["global_newer_outcome_vocabulary_count"],s["global_baseline_outcome_vocabulary_count"],s["per_kind_newer_outcome_vocabulary_count"],s["per_kind_baseline_outcome_vocabulary_count"])==(8,23,10,23);assert (s["outcome_label_exact_pair_count"],s["outcome_label_mapping_required_pair_count"],s["assertion_list_exact_pair_count"],s["fully_exact_pair_count"])==(2,44,0,0)
def test_all_waiting_nonadditive():
 d=load();s=d["summary"];assert all(x["current_status"].startswith("WAITING") and x["accepted_pair_count"]==0 and x["counting_effect"]=="ZERO" for x in d["outcome_adjudication_packets"]);assert s["design_lower_bound_before_outcome_adjudication"]==s["design_lower_bound_after_outcome_adjudication"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
