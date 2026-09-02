import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_p2_alias_semantic_evidence_comparator_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_p2_alias_semantic_evidence_comparator_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"c.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_candidates_pairs_and_distribution():s=load()["summary"];assert (s["candidate_action_comparison_count"],s["zero_pair_candidate_comparison_count"],s["same_kind_case_pair_count"])==(7,1,73);assert (s["authorization_pair_count"],s["concurrency_pair_count"],s["failure_injection_pair_count"],s["idempotency_pair_count"],s["scope_pair_count"],s["success_pair_count"],s["validation_pair_count"])==(7,11,15,10,2,6,22)
def test_exactness_not_equivalence():s=load()["summary"];assert (s["precondition_exact_pair_count"],s["outcome_exact_pair_count"],s["assertion_list_exact_pair_count"],s["fully_exact_pair_count"])==(0,2,0,0)
def test_normalization_is_explicit():d=load();assert d["normalization"]["category"]["fault_injection"]=="failure_injection";assert d["normalization"]["legacy_expected_list"]=="assertion_list_only_not_outcome_label"
def test_nonadditive_safe():d=load();s=d["summary"];assert s["accepted_candidate_count"]==s["accepted_case_pair_count"]==0;assert s["design_lower_bound_before_comparator"]==s["design_lower_bound_after_comparator"]==1404;assert s["executed_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
