import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_five_case_kind_multiplicity_disposition_packets_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_five_case_kind_multiplicity_disposition_packets_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"packets.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_packet_scope_and_gap_split():
 s=load()["summary"];assert (s["packet_count"],s["distribution_packet_count"],s["treasury_packet_count"])==(5,4,1);assert (s["kind_absent_packet_count"],s["same_kind_multiplicity_packet_count"])==(3,2)
def test_nearest_baseline_references_without_exact_contract_match():
 s=load()["summary"];assert s["nearest_baseline_reference_count"]==13;assert s["exact_expected_outcome_match_count"]==s["exact_assertion_list_match_count"]==0
def test_priority_and_roles_present():
 rows=load()["disposition_packets"];assert [x["priority"] for x in rows]==[1,2,3,4,5];assert all(len(x["accountable_role_types"])==2 and len(x["required_disposition_evidence"])==5 for x in rows)
def test_unresolved_nonadditive_and_zero_readiness():
 d=load();s=d["summary"];assert all(x["current_disposition"]=="UNRESOLVED" and not x["accepted_semantic_disposition"] for x in d["disposition_packets"]);assert s["exact_non_duplicated_additive_count"]==0;assert s["design_lower_bound_before_disposition"]==s["design_lower_bound_after_disposition"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
