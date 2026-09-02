import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_p0_alias_semantic_evidence_comparator_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_p0_alias_semantic_evidence_comparator_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"comparator.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_candidate_and_pair_counts():
 s=load()["summary"];assert s["candidate_action_comparison_count"]==6;assert s["same_kind_case_pair_count"]==66
def test_pair_kind_distribution():
 s=load()["summary"];assert (s["authorization_pair_count"],s["concurrency_pair_count"],s["failure_injection_pair_count"],s["idempotency_pair_count"],s["reconciliation_pair_count"],s["scope_pair_count"],s["success_pair_count"])==(9,9,20,12,2,8,6)
def test_exactness_is_insufficient():
 s=load()["summary"];assert (s["precondition_exact_pair_count"],s["outcome_exact_pair_count"],s["assertion_list_exact_pair_count"],s["fully_exact_pair_count"])==(0,2,0,0)
def test_review_only_nonadditive():
 d=load();s=d["summary"];assert all(x["current_status"].startswith("REVIEW_REQUIRED") and x["accepted_candidate_count"]==x["accepted_case_pair_count"]==0 and x["counting_effect"]=="ZERO" for x in d["candidate_comparisons"]);assert s["design_lower_bound_before_comparator"]==s["design_lower_bound_after_comparator"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
