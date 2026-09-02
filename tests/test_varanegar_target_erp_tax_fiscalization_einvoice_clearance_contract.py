import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_tax_fiscalization_einvoice_clearance_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_tax_fiscalization_einvoice_clearance_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"tax.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["tax_fiscalization_dimension_count"],s["module_dimension_assignment_count"])==(14,14,196);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["tax_fiscalization_policy_field_count"],s["fiscal_document_manifest_field_count"],s["submission_receipt_field_count"],s["correction_receipt_field_count"])==(24,24,22,22);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(18,252);assert(s["gate_count"],s["module_gate_assignment_count"])==(24,336);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(8,112,15)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_tax_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["dimension"] for x in d["module_dimension_assignments"] if x["module_id"]==i})==14;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==18;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==24;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==8
def test_rules_fail_closed():assert set(load()["tax_fiscalization_rule"].values())=={False}
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_taxpayer_identifier_document_tax_value_payload_certificate_or_provider_receipt_read_count","jurisdiction_tax_regime_clearance_or_signing_provider_selected_count","fiscalize_sign_submit_retry_correct_cancel_or_reconcile_run_count","accepted_operational_receipt_count","tax_or_legal_owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_tax_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
