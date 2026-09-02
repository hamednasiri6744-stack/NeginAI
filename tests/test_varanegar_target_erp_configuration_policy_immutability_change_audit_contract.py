import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_configuration_policy_immutability_change_audit_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_configuration_policy_immutability_change_audit_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"configuration.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["configuration_scope_count"],s["module_scope_assignment_count"])==(14,10,140);assert(s["policy_type_count"],s["module_policy_assignment_count"])==(12,168);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["snapshot_field_count"],s["change_receipt_field_count"],s["evaluation_receipt_field_count"],s["emergency_override_receipt_field_count"])==(22,24,20,20);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(14,196);assert(s["gate_count"],s["module_gate_assignment_count"])==(20,280);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(7,98,10)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_configuration_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["scope_type"] for x in d["module_scope_assignments"] if x["module_id"]==i})==10;assert len({x["policy_type"] for x in d["module_policy_assignments"] if x["module_id"]==i})==12;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==14;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==20;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==7
def test_rules_fail_closed():
 r=load()["configuration_rule"]
 for f in ("in_place_mutation_or_version_history_deletion_allowed","effective_time_may_precede_independent_approval","ambiguous_precedence_or_implicit_fallback_allowed","unknown_key_or_invalid_type_may_be_ignored","secret_endpoint_credential_or_sensitive_value_may_be_embedded","uat_configuration_acceptance_is_production_approval","feature_flag_may_bypass_authorization_sod_or_business_invariant","emergency_override_may_be_unbounded_unapproved_or unreconciled","stale_cache_or partial_fleet_activation_is_healthy","rollback_deletes_history_instead_of_activating_a_version","automatic_production_change_override_or_readiness"):assert r[f] is False
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_configuration_or_secret_read_count","immutable_snapshot_received_count","change_or_rollback_executed_count","runtime_evaluation_receipt_count","emergency_override_activated_count","cache_or_fleet_version_observed_count","production_change_approved_count","owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_configuration_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
