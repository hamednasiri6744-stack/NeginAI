import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_golden_uat_crosswalk_feasibility_matrix_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_golden_uat_crosswalk_feasibility_matrix_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"matrix.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_baseline_reconstructed_from_case_ids():
 s=load()["summary"];assert s["reconstructed_baseline_case_count"]==s["reconstructed_baseline_unique_case_id_count"]==511
def test_newer_representation_and_exact_overlap():
 d=load();s=d["summary"];assert s["newer_represented_case_count"]==s["newer_represented_unique_case_id_count"]==302;assert s["exact_case_id_overlap_count"]==64;assert next(x for x in d["case_crosswalk_matrix"] if x["module"]=="pricing_rules")["exact_case_id_overlap_count"]==64
def test_other_modules_have_no_exact_id_overlap():
 assert all(x["exact_case_id_overlap_count"]==0 for x in load()["case_crosswalk_matrix"] if x["module"]!="pricing_rules")
def test_candidate_semantics_are_not_promoted():
 s=load()["summary"];assert s["unmatched_baseline_case_count"]==447;assert s["unmatched_newer_case_count"]==238;assert s["candidate_casefold_action_kind_row_overlap_count"]==30;assert s["accepted_semantic_equivalence_count"]==0
def test_lower_bound_and_readiness_unchanged():
 d=load();s=d["summary"];assert s["exact_non_duplicated_additive_count"]==0;assert s["design_lower_bound_before_crosswalk"]==s["design_lower_bound_after_crosswalk"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
