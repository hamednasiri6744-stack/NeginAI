import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_p4_failure_injection_adjudication_packets_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_p4_failure_injection_adjudication_packets_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"f.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_packet_pair_partition():s=load()["summary"];assert (s["source_packet_count"],s["candidate_action_comparison_count"],s["candidate_without_failure_pair_count"],s["failure_injection_pair_count"])==(2,2,1,6);assert (s["newer_unique_failure_case_count"],s["baseline_unique_failure_case_count"])==(6,2)
def test_stage_gap():s=load()["summary"];assert (s["exact_fault_stage_label_pair_count"],s["different_or_normalized_stage_pair_count"])==(0,6)
def test_export_failure_properties():s=load()["summary"];assert s["baseline_retry_or_recovery_explicit_pair_count"]==s["baseline_partial_file_quarantine_explicit_pair_count"]==s["baseline_source_immutability_explicit_pair_count"]==s["baseline_file_or_artifact_sensitive_pair_count"]==6
def test_nonadditive_safe():d=load();s=d["summary"];assert s["outcome_exact_pair_count"]==s["assertion_list_exact_pair_count"]==s["fully_exact_pair_count"]==s["accepted_failure_pair_count"]==s["result_parity_proven_packet_count"]==0;assert s["design_lower_bound_before_failure_adjudication"]==s["design_lower_bound_after_failure_adjudication"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
