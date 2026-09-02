import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_p1_alias_semantic_evidence_comparator_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_p1_alias_semantic_evidence_comparator_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"c.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_four_mappings_and_55_pairs():s=load()["summary"];assert (s["candidate_action_comparison_count"],s["state_machine_exact_mapping_count"],s["same_kind_case_pair_count"])==(4,4,55)
def test_kind_distribution():s=load()["summary"];assert (s["authorization_pair_count"],s["concurrency_pair_count"],s["failure_injection_pair_count"],s["idempotency_pair_count"],s["scope_pair_count"],s["success_pair_count"])==(5,7,19,11,9,4)
def test_no_semantic_exactness_or_acceptance():s=load()["summary"];assert s["precondition_exact_pair_count"]==s["outcome_exact_pair_count"]==s["assertion_list_exact_pair_count"]==s["fully_exact_pair_count"]==s["accepted_candidate_count"]==s["accepted_case_pair_count"]==0
def test_nonadditive_safe_boundary():d=load();s=d["summary"];assert s["design_lower_bound_before_comparator"]==s["design_lower_bound_after_comparator"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
