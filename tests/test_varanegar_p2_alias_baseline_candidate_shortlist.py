import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_p2_alias_baseline_candidate_shortlist_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_p2_alias_baseline_candidate_shortlist_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"s.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_partition_and_candidate_split():s=load()["summary"];assert (s["p2_packet_count"],s["p2_case_count"],s["candidate_bearing_packet_count"],s["explicit_none_packet_count"])==(6,42,5,1)
def test_candidate_references():s=load()["summary"];assert (s["candidate_baseline_action_reference_count"],s["candidate_baseline_case_reference_count"],s["candidate_case_kind_overlap_reference_count"],s["searched_baseline_case_reference_count"])==(7,87,38,652)
def test_normalization_and_review_only():d=load();assert d["category_to_kind_normalization"]=={"happy_path":"success","invariant":"validation","fault_injection":"failure_injection"};assert all(c["candidate_status"]=="REVIEW_REQUIRED_NOT_SEMANTIC_EQUIVALENCE" for p in d["p2_candidate_packets"] for c in p["candidate_baseline_actions"])
def test_nonadditive_safe():d=load();s=d["summary"];assert s["design_lower_bound_before_shortlist"]==s["design_lower_bound_after_shortlist"]==1404;assert s["accepted_candidate_action_count"]==s["accepted_case_disposition_count"]==s["executed_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
