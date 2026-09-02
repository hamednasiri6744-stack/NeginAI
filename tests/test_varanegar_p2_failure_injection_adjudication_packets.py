import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_p2_failure_injection_adjudication_packets_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_p2_failure_injection_adjudication_packets_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"f.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_partition_unique_and_stages():s=load()["summary"];assert (s["source_packet_count"],s["candidate_action_comparison_count"],s["failure_injection_pair_count"],s["newer_unique_failure_case_count"],s["baseline_unique_failure_case_count"])==(5,6,15,5,11);assert (s["exact_fault_stage_label_pair_count"],s["different_or_normalized_stage_pair_count"])==(2,13)
def test_baseline_failure_properties():s=load()["summary"];assert (s["baseline_retry_or_convergence_explicit_pair_count"],s["baseline_no_partial_effect_explicit_pair_count"],s["baseline_audit_or_outbox_sensitive_pair_count"])==(10,10,13)
def test_semantic_acceptance_zero():s=load()["summary"];assert s["outcome_exact_pair_count"]==s["assertion_list_exact_pair_count"]==s["fully_exact_pair_count"]==s["accepted_failure_pair_count"]==0
def test_nonadditive_safe():d=load();s=d["summary"];assert s["design_lower_bound_before_failure_adjudication"]==s["design_lower_bound_after_failure_adjudication"]==1404;assert s["executed_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
