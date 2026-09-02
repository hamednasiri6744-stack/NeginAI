import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_p1_failure_injection_adjudication_packets_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_p1_failure_injection_adjudication_packets_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"p.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_partition_and_unique_cases():s=load()["summary"];assert (s["source_packet_count"],s["candidate_action_comparison_count"],s["failure_injection_pair_count"],s["newer_unique_failure_case_count"],s["baseline_unique_failure_case_count"])==(4,4,19,5,15)
def test_stage_and_baseline_properties():s=load()["summary"];assert (s["exact_fault_stage_label_pair_count"],s["generic_or_different_to_detailed_stage_pair_count"])==(0,19);assert (s["baseline_retry_or_convergence_explicit_pair_count"],s["baseline_no_partial_effect_explicit_pair_count"],s["audit_or_outbox_sensitive_stage_pair_count"])==(15,16,9)
def test_no_exact_or_acceptance():s=load()["summary"];assert s["outcome_exact_pair_count"]==s["assertion_list_exact_pair_count"]==s["fully_exact_pair_count"]==s["accepted_failure_pair_count"]==0
def test_nonadditive_safe():d=load();s=d["summary"];assert s["design_lower_bound_before_failure_adjudication"]==s["design_lower_bound_after_failure_adjudication"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
