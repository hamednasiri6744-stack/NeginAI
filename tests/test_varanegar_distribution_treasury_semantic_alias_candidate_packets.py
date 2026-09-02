import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_distribution_treasury_semantic_alias_candidate_packets_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_distribution_treasury_semantic_alias_candidate_packets_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"packets.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_candidate_split():
 s=load()["summary"];assert (s["candidate_packet_count"],s["distribution_candidate_packet_count"],s["treasury_candidate_packet_count"])==(30,24,6)
def test_action_kind_match_but_not_full_contract():
 s=load()["summary"];assert s["action_casefold_equal_count"]==s["kind_casefold_equal_count"]==30;assert s["expected_outcome_label_exact_equal_count"]==5;assert s["assertion_list_exact_equal_count"]==s["fully_exact_candidate_count"]==0
def test_no_auto_accept():
 rows=load()["candidate_packets"];assert len({x["packet_id"] for x in rows})==30;assert all(x["current_disposition"]=="REVIEW_REQUIRED" and not x["automatic_equivalence_allowed"] and not x["accepted_semantic_equivalence"] for x in rows)
def test_non_additive_and_zero_readiness():
 d=load();s=d["summary"];assert s["exact_non_duplicated_additive_count"]==0;assert s["design_lower_bound_before_alias_review"]==s["design_lower_bound_after_alias_review"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
