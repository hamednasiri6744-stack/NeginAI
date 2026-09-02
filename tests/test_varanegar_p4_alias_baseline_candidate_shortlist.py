import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_p4_alias_baseline_candidate_shortlist_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_p4_alias_baseline_candidate_shortlist_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"s.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_partition_and_candidates():s=load()["summary"];assert (s["p4_packet_count"],s["p4_case_count"],s["candidate_bearing_packet_count"],s["explicit_none_packet_count"])==(3,21,3,0)
def test_reference_counts():s=load()["summary"];assert (s["candidate_baseline_action_reference_count"],s["candidate_baseline_case_reference_count"],s["candidate_case_kind_overlap_reference_count"],s["searched_baseline_case_reference_count"])==(3,14,10,525)
def test_ownership_is_not_parity():s=load()["summary"];assert (s["ownership_evidence_closed_candidate_count"],s["independent_result_parity_applicable_candidate_count"],s["result_parity_proven_candidate_count"])==(3,3,0)
def test_nonadditive_safe():d=load();s=d["summary"];assert s["accepted_candidate_action_count"]==s["accepted_case_disposition_count"]==0;assert s["design_lower_bound_before_shortlist"]==s["design_lower_bound_after_shortlist"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
