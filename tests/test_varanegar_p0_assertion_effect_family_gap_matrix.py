import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BUILDER=ROOT/"scripts/windows/build_varanegar_p0_assertion_effect_family_gap_matrix_20260829.py";ART=ROOT/"artifacts/varanegar_analysis/varanegar_p0_assertion_effect_family_gap_matrix_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 out=tmp_path/"matrix.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_pair_family_and_overlap_counts():
 s=load()["summary"];assert (s["candidate_case_pair_count"],s["effect_family_count"])==(66,12);assert (s["exact_family_set_pair_count"],s["nonempty_family_overlap_pair_count"],s["zero_family_overlap_pair_count"])==(0,65,1)
def test_asymmetric_family_assignments():
 s=load()["summary"];assert (s["newer_only_family_assignment_count"],s["baseline_only_family_assignment_count"])==(294,125)
def test_material_family_gaps():
 s=load()["summary"];assert (s["newer_audit_pair_count"],s["baseline_audit_pair_count"],s["newer_outbox_pair_count"],s["baseline_outbox_pair_count"])==(66,50,66,14);assert (s["newer_source_immutability_pair_count"],s["baseline_source_immutability_pair_count"],s["newer_transaction_atomicity_pair_count"],s["baseline_transaction_atomicity_pair_count"])==(0,53,6,29)
def test_no_acceptance_or_promotion():
 d=load();s=d["summary"];assert s["accepted_family_mapping_count"]==s["accepted_case_pair_count"]==0;assert s["design_lower_bound_before_effect_family_matrix"]==s["design_lower_bound_after_effect_family_matrix"]==1404;assert s["executed_case_count"]==s["owner_approved_case_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0}
