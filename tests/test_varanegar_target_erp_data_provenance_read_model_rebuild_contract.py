import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_data_provenance_read_model_rebuild_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_data_provenance_read_model_rebuild_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"provenance.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["data_class_count"],s["module_data_assignment_count"])==(14,12,168);assert(s["authority_class_count"],s["module_authority_assignment_count"])==(8,112);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["provenance_receipt_field_count"],s["rebuild_receipt_field_count"],s["drift_receipt_field_count"],s["retention_disposition_receipt_field_count"])==(24,22,20,18);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(14,196);assert(s["gate_count"],s["module_gate_assignment_count"])==(20,280);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(6,84,10)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_provenance_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["data_class"] for x in d["module_data_assignments"] if x["module_id"]==i})==12;assert len({x["authority_class"] for x in d["module_authority_assignments"] if x["module_id"]==i})==8;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==14;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==20;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==6
def test_rules_fail_closed():
 r=load()["provenance_rule"]
 for f in ("derived_read_model_cache_report_or_export_is_authoritative","rebuild_may_use_unversioned_or unowned_source","direct_projection_repair_without_authoritative_correction_allowed","snapshot_or_delta_gap_overlap_fork_unknown_allows_publication","duplicate_event_or replay_may_create_new_effect","partial_rebuild_or quarantine_unknown_allows_read_switch","same_sources_recipe_versions_may_produce_different_digest","deletion_may_break_financial_retention_or lineage_tombstone","raw_pii_payload_or business_value_may_be_persisted_as_evidence","automatic_rebuild_publication_read_switch_or readiness"):assert r[f] is False
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_dataset_table_row_or_sample_read_count","authoritative_source_connected_count","lineage_receipt_accepted_count","read_model_rebuild_run_count","delta_replay_run_count","drift_check_run_count","disposition_or_deletion_run_count","read_switch_enabled_count","owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_provenance_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
