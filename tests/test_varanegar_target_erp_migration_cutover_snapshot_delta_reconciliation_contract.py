import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_migration_cutover_snapshot_delta_reconciliation_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_migration_cutover_snapshot_delta_reconciliation_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"cutover.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["cutover_phase_count"],s["module_phase_assignment_count"])==(14,12,168);assert(s["reconciliation_dimension_count"],s["module_reconciliation_assignment_count"])==(12,168);assert(s["snapshot_manifest_field_count"],s["delta_batch_receipt_field_count"],s["cutover_decision_field_count"])==(22,20,18);assert(s["gate_count"],s["module_gate_assignment_count"])==(18,252);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(6,84,10)
def test_every_module_has_full_phase_dimension_gate_and_role_coverage():
 d=load();ids={x["module_id"] for x in d["module_cutover_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["phase_id"] for x in d["module_phase_assignments"] if x["module_id"]==i})==12
  assert len({x["reconciliation_dimension"] for x in d["module_reconciliation_assignments"] if x["module_id"]==i})==12
  assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==18
  assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==6
def test_cutover_rules_fail_closed():
 r=load()["cutover_rule"]
 for f in ("stale_clone_may_be_labeled_live_source","snapshot_without_authorized_watermark_is_current","delta_gap_overlap_or_out_of_order_may_be_applied","same_delta_replay_may_create_new_effect","blocking_unknown_may_be_waived_for_schedule","operator_may_self_approve_reconciliation_or_cutover","target_writes_may_enable_before_source_fence_and_final_receipts","raw_source_target_values_may_be_persisted_in_evidence","rollback_or_reentry_may_be_assumed","automatic_cutover_or_readiness"):assert r[f] is False
def test_no_snapshot_delta_cutover_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("authorized_snapshot_capture_count","snapshot_captured_or_read_count","delta_batch_captured_or_applied_count","module_reconciliation_run_count","blocking_unknown_zero_proven_module_count","owner_approved_module_count","cutover_accepted_module_count","target_write_enabled_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_cutover_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
