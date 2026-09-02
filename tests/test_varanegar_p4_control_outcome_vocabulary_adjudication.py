import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_p4_control_outcome_vocabulary_adjudication_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_p4_control_outcome_vocabulary_adjudication_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"o.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_partition():s=load()["summary"];assert (s["control_kind_packet_count"],s["non_failure_case_pair_count"],s["authorization_pair_count"],s["idempotency_pair_count"],s["success_pair_count"])==(3,8,3,2,3)
def test_vocab():s=load()["summary"];assert (s["global_newer_outcome_vocabulary_count"],s["global_baseline_outcome_vocabulary_count"],s["per_kind_newer_outcome_vocabulary_count"],s["per_kind_baseline_outcome_vocabulary_count"])==(3,1,3,3);assert (s["generic_rejected_no_effect_pair_count"],s["generic_committed_original_once_pair_count"])==(3,2)
def test_exactness_zero():s=load()["summary"];assert (s["outcome_label_exact_pair_count"],s["outcome_label_mapping_required_pair_count"],s["assertion_list_exact_pair_count"],s["fully_exact_pair_count"])==(0,8,0,0)
def test_nonadditive_safe():d=load();s=d["summary"];assert s["accepted_outcome_pair_count"]==s["result_parity_proven_packet_count"]==0;assert s["design_lower_bound_before_outcome_adjudication"]==s["design_lower_bound_after_outcome_adjudication"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
