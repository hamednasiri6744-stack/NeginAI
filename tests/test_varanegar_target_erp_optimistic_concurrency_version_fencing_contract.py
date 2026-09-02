import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_optimistic_concurrency_version_fencing_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_optimistic_concurrency_version_fencing_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"concurrency.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["target_command_count"])==(14,49);assert(s["concurrency_dimension_count"],s["command_dimension_assignment_count"])==(10,490);assert(s["strategy_candidate_count"],s["command_strategy_candidate_assignment_count"])==(6,294);assert(s["concurrency_receipt_field_count"],s["conflict_receipt_field_count"],s["lease_fencing_receipt_field_count"])==(22,18,20);assert(s["failure_case_count"],s["command_failure_assignment_count"])==(14,686);assert(s["gate_count"],s["command_gate_assignment_count"])==(18,882);assert(s["role_type_count"],s["command_role_assignment_count"],s["typed_outcome_count"])==(6,294,10)
def test_every_command_has_full_coverage():
 d=load();ids={(x["module_id"],x["command_id"]) for x in d["command_dimension_assignments"]};assert len(ids)==49
 for module_id,command_id in ids:
  match=lambda x:x["module_id"]==module_id and x["command_id"]==command_id
  assert len({x["dimension"] for x in d["command_dimension_assignments"] if match(x)})==10;assert len({x["strategy"] for x in d["command_strategy_candidates"] if match(x)})==6;assert len({x["failure_case_id"] for x in d["command_failure_assignments"] if match(x)})==14;assert len({x["gate_id"] for x in d["command_gate_assignments"] if match(x)})==18;assert len({x["role_type"] for x in d["command_role_assignments"] if match(x)})==6
def test_rules_fail_closed():
 r=load()["concurrency_rule"]
 for f in ("idempotency_key_is_concurrency_control","authoritative_update_may_omit_expected_version","client_only_version_check_without_repository_compare_and_swap_allowed","lost_update_last_write_wins_or silent_overwrite_allowed","compare_and_swap_zero_or multiple_match_is_success","write_skew_or phantom_may_break_business_invariant","expired_revoked_wrong_owner_lease_or stale_fencing_token_allowed","deadlock_retry_may_change_command_identity_or idempotency_key","unknown_commit_may_be_retried_before reconciliation","bulk_mixed_version_may_partially_commit_without typed_policy","stale_read_model_is_authoritative_precondition","automatic_conflict_resolution_commit_or readiness"):assert r[f] is False
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("selected_strategy_count","runtime_compare_and_swap_proven_count","runtime_sequence_or_fencing_proven_count","deadlock_or_conflict_test_run_count","unknown_commit_reconciliation_run_count","owner_approved_command_count","command_ready_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_concurrency_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
