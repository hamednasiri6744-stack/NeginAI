import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_unmatched_golden_case_alias_work_queue_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_unmatched_golden_case_alias_work_queue_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"queue.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_queue_and_module_split():
 s=load()["summary"];assert s["unmatched_newer_work_queue_count"]==208;assert (s["pricing_queue_count"],s["distribution_queue_count"],s["treasury_queue_count"],s["accounting_queue_count"],s["reporting_queue_count"])==(28,4,78,42,56)
def test_gap_split_and_actions():
 s=load()["summary"];assert s["action_alias_required_count"]==203;assert s["action_match_kind_or_multiplicity_gap_count"]==5;assert s["distinct_unmatched_newer_action_count"]==34
def test_all_unresolved_with_packet_fields():
 rows=load()["work_queue"];assert len({x["queue_id"] for x in rows})==208;assert all(x["current_disposition"]=="UNRESOLVED" and not x["accepted_alias_or_semantic_disposition"] and len(x["required_packet_fields"])==10 for x in rows)
def test_non_additive_and_zero_readiness():
 d=load();s=d["summary"];assert s["exact_non_duplicated_additive_count"]==0;assert s["design_lower_bound_before_queue"]==s["design_lower_bound_after_queue"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
