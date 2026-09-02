import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_master_data_identity_dedup_merge_supersession_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_master_data_identity_dedup_merge_supersession_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"master_data.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["master_entity_class_count"],s["module_entity_assignment_count"])==(14,12,168);assert(s["identity_dimension_count"],s["module_dimension_assignment_count"])==(14,196);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["identity_receipt_field_count"],s["merge_receipt_field_count"],s["supersession_receipt_field_count"],s["cross_reference_receipt_field_count"])==(22,24,20,20);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(16,224);assert(s["gate_count"],s["module_gate_assignment_count"])==(22,308);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(7,98,12)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_master_data_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["entity_class"] for x in d["module_entity_assignments"] if x["module_id"]==i})==12;assert len({x["identity_dimension"] for x in d["module_dimension_assignments"] if x["module_id"]==i})==14;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==16;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==22;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==7
def test_rules_fail_closed():
 r=load()["master_data_rule"]
 for f in ("global_uniqueness_without_scope_allowed","destructive_normalization_or identity_reuse_allowed","fuzzy_score_or single_attribute_may_auto_merge","merge_may_omit_survivor_loser_field_resolution_or unmerge_plan","merge_may_rewrite_immutable_transaction_history_or audit","supersession_is_deletion_or identity_reuse","inactive_archived_deleted_and superseded_states_interchangeable","alias_redirect_cycle_fork_or ambiguous_cross_reference_allowed","cross_scope_merge_or self_approval_allowed","raw_identifier_pii_or source_payload_may_be_persisted_as evidence","automatic_merge_supersession_propagation_or readiness"):assert r[f] is False
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_identifier_code_name_pii_or_master_record_read_count","identity_or_duplicate_receipt_accepted_count","merge_unmerge_or_supersession_run_count","cross_reference_propagation_run_count","downstream_reconciliation_run_count","owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_master_data_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
