import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_p0_failure_injection_adjudication_packets_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_p0_failure_injection_adjudication_packets_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"packets.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_packet_candidate_pair_counts():
 s=load()["summary"];assert (s["source_packet_count"],s["candidate_action_comparison_count"],s["failure_injection_pair_count"])==(3,6,20)
def test_stage_and_unique_case_counts():
 s=load()["summary"];assert (s["newer_unique_failure_case_count"],s["baseline_unique_failure_case_count"],s["exact_fault_stage_label_pair_count"],s["generic_to_detailed_stage_pair_count"])==(3,20,2,18)
def test_baseline_failure_properties():
 s=load()["summary"];assert (s["baseline_retry_or_convergence_explicit_pair_count"],s["baseline_no_partial_effect_explicit_pair_count"],s["audit_or_outbox_sensitive_stage_pair_count"])==(15,15,7)
def test_no_semantic_acceptance_or_promotion():
 d=load();s=d["summary"];assert s["outcome_exact_pair_count"]==s["assertion_list_exact_pair_count"]==s["fully_exact_pair_count"]==s["accepted_failure_pair_count"]==0;assert s["design_lower_bound_before_failure_adjudication"]==s["design_lower_bound_after_failure_adjudication"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
