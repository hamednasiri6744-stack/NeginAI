import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_environment_isolation_write_fence_execution_token_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_environment_isolation_write_fence_execution_token_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"environment.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["target_command_count"],s["environment_count"],s["command_environment_assignment_count"])==(14,49,4,196);assert(s["fence_control_count"],s["environment_fence_assignment_count"])==(14,56);assert(s["negative_case_count"],s["command_negative_case_assignment_count"])==(12,588);assert(s["execution_token_field_count"],s["gate_count"],s["command_gate_assignment_count"])==(20,18,882);assert(s["role_type_count"],s["command_role_assignment_count"],s["typed_outcome_count"])==(6,294,10)
def test_every_command_and_environment_has_full_coverage():
 d=load();ids={x["target_command_id"] for x in d["target_commands"]};envs={x["environment_id"] for x in d["environments"]}
 for i in ids:
  assert {x["environment_id"] for x in d["command_environment_assignments"] if x["target_command_id"]==i}==envs;assert len({x["negative_case_id"] for x in d["command_negative_case_assignments"] if x["target_command_id"]==i})==12;assert len({x["gate_id"] for x in d["command_gate_assignments"] if x["target_command_id"]==i})==18;assert len({x["role_type"] for x in d["command_role_assignments"] if x["target_command_id"]==i})==6
 for e in envs:assert len({x["fence_control"] for x in d["environment_fence_assignments"] if x["environment_id"]==e})==14
def test_rules_fail_closed():
 r=load()["environment_and_token_rule"]
 for f in ("legacy_operational_write_or_command_allowed","legacy_reference_read_without_explicit_read_only_transport_allowed","environment_may_be_inferred_from_hostname_path_or_connection_string","sandbox_or_uat_token_may_be_replayed_in_production","expired_revoked_used_or_superseded_token_allowed","break_glass_or_admin_bypasses_independent_approval","uat_success_automatically_promotes_production","production_command_allowed_without_separate_change_and_rollback_receipt","secret_endpoint_or_raw_business_value_may_be_persisted_in_token_or_evidence","automatic_execution_authorization_or_readiness"):assert r[f] is False
def test_no_token_connection_command_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("issued_execution_token_count","legacy_operational_connection_or_command_count","target_sandbox_command_run_count","target_uat_command_run_count","target_production_command_run_count","accepted_runtime_fence_attestation_count","owner_approved_command_count","command_ready_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_environment_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
