import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_capacity_timeout_backpressure_degradation_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_capacity_timeout_backpressure_degradation_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"capacity.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["capacity_dimension_count"],s["module_dimension_assignment_count"])==(14,12,168);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["capacity_policy_field_count"],s["timeout_retry_budget_receipt_field_count"],s["overload_receipt_field_count"],s["degradation_receipt_field_count"])==(22,20,22,20);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(16,224);assert(s["gate_count"],s["module_gate_assignment_count"])==(20,280);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(6,84,12)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_capacity_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["capacity_dimension"] for x in d["module_dimension_assignments"] if x["module_id"]==i})==12;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==16;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==20;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==6
def test_rules_fail_closed():
 r=load()["capacity_rule"]
 for f in ("unbounded_inflight_queue_batch_payload_or resource_pool_allowed","child_timeout_may_exceed_parent_or ignore_cancellation","retry_without_idempotency_or after_unknown_commit_allowed","retry_without_attempt_elapsed_budget_backoff_jitter_or cap_allowed","queue_overflow_may_silently_drop_reorder_or hide_effect","rate_limit_may_leak_scope_or starve_tenant","dependency_may_exhaust_shared_pool_without bulkhead","degraded_mode_may_bypass_authorization_or business_invariant","stale_read_may_be_presented_as authoritative_current_state","recovery_may_enable_before drain_replay_reconciliation","synthetic_load_may_target_operational_environment","automatic_capacity_acceptance_degradation_recovery_or readiness"):assert r[f] is False
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_traffic_metric_queue_resource_or_dependency_read_count","capacity_policy_approved_count","synthetic_or_operational_load_test_run_count","fault_or_overload_rehearsal_run_count","degradation_mode_activated_count","recovery_reconciliation_run_count","owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_capacity_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
