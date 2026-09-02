import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_p0_final_evidence_gap_status_matrix_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_p0_final_evidence_gap_status_matrix_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"matrix.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_p0_packet_case_and_module_counts():
 s=load()["summary"];assert (s["p0_status_packet_count"],s["p0_case_count"],s["accounting_packet_count"],s["accounting_case_count"],s["treasury_packet_count"],s["treasury_case_count"])==(7,49,4,28,3,21)
def test_packetization_complete_but_disposition_open():
 s=load()["summary"];assert s["analysis_packetization_complete_count"]==7;assert s["semantic_disposition_closed_packet_count"]==0;assert (s["external_alias_or_new_action_decision_packet_count"],s["external_semantic_equivalence_decision_packet_count"])==(4,3)
def test_pair_and_exactness_summary():
 s=load()["summary"];assert (s["same_kind_case_pair_count"],s["failure_injection_pair_count"],s["control_pair_count"])==(66,20,46);assert (s["outcome_exact_pair_count"],s["assertion_list_exact_pair_count"],s["fully_exact_pair_count"],s["exact_effect_family_set_pair_count"],s["zero_effect_family_overlap_pair_count"])==(2,0,0,0,1)
def test_all_unresolved_nonadditive():
 d=load();s=d["summary"];assert all(x["semantic_disposition_status"].startswith("UNRESOLVED") and x["accepted_alias_or_new_action_decision_count"]==x["accepted_case_disposition_count"]==0 and x["counting_effect"]=="ZERO" for x in d["p0_status_packets"]);assert s["design_lower_bound_before_p0_status"]==s["design_lower_bound_after_p0_status"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
