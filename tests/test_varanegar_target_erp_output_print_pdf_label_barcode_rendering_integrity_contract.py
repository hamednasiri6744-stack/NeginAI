import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_output_print_pdf_label_barcode_rendering_integrity_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_output_print_pdf_label_barcode_rendering_integrity_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"output.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["output_integrity_dimension_count"],s["module_dimension_assignment_count"])==(14,14,196);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["output_policy_field_count"],s["render_manifest_field_count"],s["print_receipt_field_count"],s["barcode_verification_field_count"])==(24,24,22,20);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(18,252);assert(s["gate_count"],s["module_gate_assignment_count"])==(24,336);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(7,98,14)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_output_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["dimension"] for x in d["module_dimension_assignments"] if x["module_id"]==i})==14;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==18;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==24;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==7
def test_rules_fail_closed():assert set(load()["output_integrity_rule"].values())=={False}
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_template_data_snapshot_document_output_barcode_or_print_receipt_read_count","renderer_pdf_barcode_printer_or_signing_provider_selected_count","render_print_scan_sign_download_or_delivery_run_count","accepted_operational_receipt_count","owner_golden_output_approved_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_output_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
