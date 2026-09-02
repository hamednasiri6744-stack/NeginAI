import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_p1_alias_baseline_candidate_shortlist_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_p1_alias_baseline_candidate_shortlist_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"shortlist.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_p1_partition_and_candidate_split():
 s=load()["summary"];assert (s["p1_packet_count"],s["p1_case_count"],s["candidate_bearing_packet_count"],s["explicit_none_packet_count"])==(8,56,4,4)
def test_candidate_reference_counts():
 s=load()["summary"];assert (s["candidate_baseline_action_reference_count"],s["candidate_baseline_case_reference_count"],s["candidate_case_kind_overlap_reference_count"])==(4,76,24)
def test_state_machine_mapping_is_explicit_but_not_acceptance():
 d=load();s=d["summary"];assert s["state_machine_exact_mapping_count"]==4;assert s["exact_action_string_match_count"]==0;assert all(c["state_machine_mapping_exact"] and c["candidate_status"]=="REVIEW_REQUIRED_NOT_SEMANTIC_EQUIVALENCE" for p in d["p1_candidate_packets"] for c in p["candidate_baseline_actions"])
def test_nonadditive_and_safe():
 d=load();s=d["summary"];assert all(p["accepted_candidate_action_count"]==p["accepted_case_disposition_count"]==0 and p["counting_effect"]=="ZERO" for p in d["p1_candidate_packets"]);assert s["design_lower_bound_before_shortlist"]==s["design_lower_bound_after_shortlist"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
