import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_observability_slo_incident_evidence_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_observability_slo_incident_evidence_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"observability.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["signal_class_count"],s["module_signal_assignment_count"])==(14,12,168);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["sli_receipt_field_count"],s["slo_policy_field_count"],s["alert_receipt_field_count"],s["incident_receipt_field_count"])==(18,18,20,22);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(14,196);assert(s["gate_count"],s["module_gate_assignment_count"])==(20,280);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(6,84,10)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_observability_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["signal_class"] for x in d["module_signal_assignments"] if x["module_id"]==i})==12;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==14;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==20;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==6
def test_rules_fail_closed():
 r=load()["observability_rule"]
 for f in ("process_running_is_success","technical_health_is_business_invariant_success","missing_or_stale_telemetry_is_healthy","sensitive_or_unbounded_labels_logs_traces_allowed","single_window_threshold_replaces_short_and_long_burn_windows","alert_without_owner_route_and_runbook_is_actionable","authorization_denies_or_reconciliation_unknowns_may_be_silently_dropped","process_restart_automatically_closes_incident","severity_or_residual_difference_may_be_lowered_or_waived_without_evidence","automatic_health_incident_closure_or_readiness"):assert r[f] is False
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("telemetry_source_read_or_queried_count","sli_implemented_count","slo_approved_count","alert_route_activated_count","synthetic_alert_or_incident_rehearsal_count","runtime_incident_observed_count","health_or_business_invariant_receipt_accepted_count","incident_closed_count","owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_observability_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
