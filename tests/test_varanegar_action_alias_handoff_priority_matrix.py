import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_action_alias_handoff_priority_matrix_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_action_alias_handoff_priority_matrix_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"matrix.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_complete_partition():
 d=load();s=d["summary"];assert s["handoff_packet_count"]==29;assert s["covered_case_count"]==203;assert len({x["source_packet_id"] for x in d["handoff_packets"]})==29
def test_priority_lane_split():
 s=load()["summary"];assert (s["p0_packet_count"],s["p0_case_count"],s["p1_packet_count"],s["p1_case_count"],s["p2_packet_count"],s["p2_case_count"],s["p3_packet_count"],s["p3_case_count"],s["p4_packet_count"],s["p4_case_count"])==(7,49,8,56,6,42,5,35,3,21)
def test_roles_and_required_fields():
 d=load();assert d["summary"]["accountable_role_assignment_count"]==58;assert all(len(x["accountable_role_types"])==2 and len(x["required_handoff_fields"])==9 for x in d["handoff_packets"])
def test_no_acceptance_or_promotion():
 d=load();s=d["summary"];assert all(x["current_status"].startswith("WAITING") and x["named_owner_assignment_count"]==x["accepted_handoff_count"]==x["accepted_case_disposition_count"]==0 and x["counting_effect"]=="ZERO" for x in d["handoff_packets"]);assert s["design_lower_bound_before_priority_handoff"]==s["design_lower_bound_after_priority_handoff"]==1404;assert s["exact_non_duplicated_additive_count"]==s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
