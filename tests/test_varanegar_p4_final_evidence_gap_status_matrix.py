import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_p4_final_evidence_gap_status_matrix_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_p4_final_evidence_gap_status_matrix_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"g.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_partition_and_route():s=load()["summary"];assert (s["p4_status_packet_count"],s["p4_case_count"],s["candidate_bearing_packet_count"],s["read_model_candidate_packet_count"],s["export_file_candidate_packet_count"],s["external_export_effect_and_result_parity_decision_packet_count"])==(3,21,3,1,2,3)
def test_pair_and_semantic_status():s=load()["summary"];assert (s["same_kind_case_pair_count"],s["failure_injection_pair_count"],s["control_pair_count"])==(14,6,8);assert s["outcome_exact_pair_count"]==s["assertion_list_exact_pair_count"]==s["fully_exact_pair_count"]==s["exact_effect_family_set_pair_count"]==0
def test_packetization_not_disposition_or_parity():s=load()["summary"];assert s["analysis_packetization_complete_count"]==3;assert s["semantic_disposition_closed_packet_count"]==s["result_parity_proven_packet_count"]==s["accepted_case_disposition_count"]==0
def test_nonadditive_safe():d=load();s=d["summary"];assert s["design_lower_bound_before_p4_status"]==s["design_lower_bound_after_p4_status"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
