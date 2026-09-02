import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_monetary_quantity_temporal_semantics_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_monetary_quantity_temporal_semantics_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"semantics.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["semantic_dimension_count"],s["module_dimension_assignment_count"])==(14,14,196);assert(s["arithmetic_temporal_invariant_count"],s["module_invariant_assignment_count"])==(12,168);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["numeric_policy_field_count"],s["calculation_receipt_field_count"],s["conversion_receipt_field_count"],s["temporal_fiscal_receipt_field_count"])==(22,24,20,20);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(16,224);assert(s["gate_count"],s["module_gate_assignment_count"])==(22,308);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(7,98,12)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_semantic_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["semantic_dimension"] for x in d["module_dimension_assignments"] if x["module_id"]==i})==14;assert len({x["invariant_id"] for x in d["module_invariant_assignments"] if x["module_id"]==i})==12;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==16;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==22;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==7
def test_rules_fail_closed():
 r=load()["semantic_rule"]
 for f in ("binary_float_allowed_for_authoritative_amount_rate_or quantity","implicit_precision_scale_rounding_stage_or aggregation_order_allowed","allocation_residual_may_be_dropped_or nondeterministic","exchange_rate_may_be_unversioned_undirected_or timeless","unit_conversion_may_cross_dimensions_or be_unversioned","reversal_may_drop_sign_reference_or original_policy","naive_timestamp_or silent_dst_normalization_allowed","business_document_posting_and system_dates_interchangeable","posting_may_use_closed_unknown_period_or infer_current_date","jalali_or gregorian_display_value_is_authoritative_instant","automatic_semantic_acceptance_posting_or readiness"):assert r[f] is False
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_amount_quantity_rate_date_or_timestamp_read_count","numeric_or_temporal_policy_approved_count","runtime_calculation_conversion_or_temporal_receipt_count","cross_module_semantic_reconciliation_run_count","fiscal_posting_or_business_command_run_count","owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_semantics_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
