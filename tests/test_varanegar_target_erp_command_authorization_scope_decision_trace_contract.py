import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/"scripts/windows/build_varanegar_target_erp_command_authorization_scope_decision_trace_contract_20260829.py"
ARTIFACT=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_command_authorization_scope_decision_trace_contract_20260829.json"
def load(): return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
    out=tmp_path/"authorization.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
    s=load()["summary"];assert(s["module_count"],s["target_command_count"])==(14,49);assert(s["authorization_dimension_count"],s["command_dimension_assignment_count"])==(12,588);assert(s["negative_case_count"],s["command_negative_case_assignment_count"])==(14,686);assert(s["decision_trace_field_count"],s["gate_count"],s["command_gate_assignment_count"])==(22,16,784);assert(s["role_type_count"],s["command_role_assignment_count"],s["typed_outcome_count"])==(5,245,10)
def test_every_command_is_fully_covered():
    d=load();ids={x["target_command_id"] for x in d["target_command_authorization_contracts"]};assert len(ids)==49
    for i in ids:
        assert len({x["authorization_dimension"] for x in d["command_dimension_assignments"] if x["target_command_id"]==i})==12
        assert len({x["negative_case_id"] for x in d["command_negative_case_assignments"] if x["target_command_id"]==i})==14
        assert len({x["gate_id"] for x in d["command_gate_assignments"] if x["target_command_id"]==i})==16
        assert len({x["role_type"] for x in d["command_role_assignments"] if x["target_command_id"]==i})==5
def test_authorization_rules_fail_closed():
    r=load()["authorization_rule"];assert r["default_allow"] is False;assert r["explicit_deny_wins"] is True;assert r["ambient_admin_or_role_name_bypass_allowed"] is False;assert r["client_ui_or_route_visibility_is_authorization"] is False;assert r["server_service_only_check_without_repository_scope_is_sufficient"] is False;assert r["bulk_mixed_scope_partial_success_allowed"] is False;assert r["self_approval_allowed"] is False;assert r["decision_trace_may_persist_identity_pii_token_or_business_value"] is False;assert r["legacy_aggregate_right_or_code_existence_creates_target_grant"] is False
def test_no_runtime_authorization_or_readiness_claim():
    d=load();s=d["summary"]
    for f in ("implemented_server_authorization_count","authenticated_isolated_uat_run_count","accepted_allow_trace_count","accepted_deny_trace_count","repository_scope_proven_command_count","route_to_repository_coverage_proven_command_count","owner_approved_command_count","runtime_authorization_proven_command_count","command_ready_count","pilot_ready_module_count"):assert s[f]==0
    assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_authorization_contract"]==1404
def test_source_manifest_current():
    for x in load()["source_manifest"]:
        p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"];assert hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
