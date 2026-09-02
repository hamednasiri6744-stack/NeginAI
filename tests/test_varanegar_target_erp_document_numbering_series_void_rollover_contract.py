import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_document_numbering_series_void_rollover_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_document_numbering_series_void_rollover_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"numbering.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["numbering_dimension_count"],s["module_dimension_assignment_count"])==(14,12,168);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["series_policy_field_count"],s["allocation_receipt_field_count"],s["void_receipt_field_count"],s["rollover_receipt_field_count"])==(22,22,18,20);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(16,224);assert(s["gate_count"],s["module_gate_assignment_count"])==(20,280);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(6,84,12)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_numbering_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["numbering_dimension"] for x in d["module_dimension_assignments"] if x["module_id"]==i})==12;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==16;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==20;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==6
def test_rules_fail_closed():
 r=load()["numbering_rule"]
 for f in ("human_document_number_is_database_surrogate_identity","global_series_without tenant_organization_fiscal_document_scope_allowed","series_format_prefix_or version_may_change_in_place","preview_draft_or print_may_allocate_before approved_stage","gap_may_be_hidden_deleted_or reused_without void_receipt","expired_abandoned_or voided_number_may_be_reused","concurrent_allocation_without atomic_sequence_and fencing_allowed","unknown_commit_retry_may_allocate_second_number","offline_range_may_overlap_leak_scope_expire_or remain_unreconciled","backdated_document_may_allocate_closed_or expired_series","cancel_reversal_or amendment_may_remove_original_number_reference","automatic_number_override_rollover_or readiness"):assert r[f] is False
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_document_number_series_gap_or_identifier_read_count","series_policy_approved_count","number_reservation_or_commit_run_count","void_or_gap_receipt_accepted_count","offline_range_or_rollover_run_count","numbering_reconciliation_run_count","owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_numbering_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
