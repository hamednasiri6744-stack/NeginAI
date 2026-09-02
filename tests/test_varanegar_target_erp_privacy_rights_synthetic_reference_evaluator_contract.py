import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_privacy_rights_synthetic_reference_evaluator_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_privacy_rights_synthetic_reference_evaluator_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"privacy-reference.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_vectors_pass():s=load()["summary"];assert s["positive_vector_count"]==s["positive_pass_count"]==9;assert s["negative_vector_count"]==s["negative_pass_count"]==21;assert s["total_vector_count"]==s["total_pass_count"]==30 and s["distinct_typed_outcome_count"]>=18
def test_precedence_explicit():assert load()["outcome_precedence"][:5]==["SCHEMA","INVENTORY_SUBJECT_LINKAGE","PURPOSE_BASIS_JURISDICTION","NOTICE","CONSENT_WITHDRAWAL"]
def test_no_operational_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_privacy_consent_rights_or_disposition_implementation_count","operational_person_subject_identifier_or_sensitive_data_read_count","consent_rights_disposition_sharing_or_breach_run_count","accepted_operational_receipt_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_reference_evaluator"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
