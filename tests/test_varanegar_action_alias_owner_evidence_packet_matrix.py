import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_action_alias_owner_evidence_packet_matrix_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_action_alias_owner_evidence_packet_matrix_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"matrix.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_packet_and_case_counts():
 s=load()["summary"];assert s["action_alias_packet_count"]==29;assert s["covered_unmatched_case_count"]==203
def test_module_split():
 s=load()["summary"];assert (s["pricing_packet_count"],s["pricing_case_count"],s["treasury_packet_count"],s["treasury_case_count"],s["accounting_packet_count"],s["accounting_case_count"],s["reporting_packet_count"],s["reporting_case_count"])==(4,28,11,77,6,42,8,56)
def test_each_action_packet_has_seven_cases_two_roles_ten_fields():
 rows=load()["action_alias_packets"];assert len({x["packet_id"] for x in rows})==29;assert all(x["case_count"]==7 and len(x["accountable_role_types"])==2 and len(x["required_packet_fields"])==10 for x in rows)
def test_all_waiting_nonadditive():
 d=load();s=d["summary"];assert all(x["current_status"].startswith("WAITING") and x["accepted_packet_count"]==x["accepted_case_disposition_count"]==0 and x["counting_effect"]=="ZERO" for x in d["action_alias_packets"]);assert s["design_lower_bound_before_alias_packets"]==s["design_lower_bound_after_alias_packets"]==1404;assert s["exact_non_duplicated_additive_count"]==s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
