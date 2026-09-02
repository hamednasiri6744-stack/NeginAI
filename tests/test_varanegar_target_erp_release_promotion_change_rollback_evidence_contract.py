import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_release_promotion_change_rollback_evidence_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_release_promotion_change_rollback_evidence_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"release.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["promotion_transition_count"],s["module_promotion_assignment_count"])==(14,2,28);assert(s["release_asset_class_count"],s["module_asset_assignment_count"])==(8,112);assert(s["release_step_count"],s["module_step_assignment_count"])==(12,168);assert(s["release_manifest_field_count"],s["change_receipt_field_count"],s["rollback_receipt_field_count"])==(22,20,18);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(12,168);assert(s["gate_count"],s["module_gate_assignment_count"])==(20,280);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(6,84,10)
def test_every_module_has_full_release_coverage():
 d=load();ids={x["module_id"] for x in d["module_release_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["promotion_id"] for x in d["module_promotion_assignments"] if x["module_id"]==i})==2;assert len({x["asset_class"] for x in d["module_asset_assignments"] if x["module_id"]==i})==8;assert len({x["step_id"] for x in d["module_step_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==12;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==20;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==6
def test_release_rules_fail_closed():
 r=load()["release_rule"]
 for f in ("artifact_may_be_rebuilt_between_promotion_environments","uat_acceptance_is_production_approval","application_start_is_success_without_health_slo_and_business_invariants","database_migration_may_run_without_compatibility_and_rollback_boundary","rollback_may_run_when_forward_only_data_would_be_destroyed","secret_or_environment_endpoint_may_be_embedded_in_artifact","blocking_unknown_or_unreviewed_difference_allows_promotion","production_change_operator_may_self_approve","missing_stale_or_invalid_signature_provenance_sbom_allows_promotion","automatic_promotion_rollback_or_readiness"):assert r[f] is False
def test_no_release_deploy_promotion_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("release_manifest_received_count","artifact_digest_verified_count","deployment_or_migration_run_count","promotion_accepted_count","production_change_approved_count","rollback_or_forward_fix_run_count","post_deploy_health_accepted_count","owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_release_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
