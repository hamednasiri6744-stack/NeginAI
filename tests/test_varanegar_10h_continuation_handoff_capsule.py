import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_10h_continuation_handoff_capsule_20260901.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_10h_continuation_handoff_capsule_20260901.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"handoff.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_graph_and_official_suite_fresh():s=load()["summary"];assert s["invalid_json_count"]==s["stale_reference_count"]==s["official_bootstrap_exclusion_count"]==0;assert s["reachable_checkpoint_count"]==s["passing_checkpoint_count"];assert s["official_test_file_count"]>=226 and s["official_passed_test_count"]>=1214
def test_resume_point_is_explicit_and_portable():d=load();assert d["scope"]["portable_project_root"]=="G:/NeginAI";assert d["current_resume_point"]["top_checkpoint"].endswith("varanegar_target_erp_contract_portfolio_invariant_audit_checkpoint_20260901.json");assert "settle_varanegar_analysis_chain_20260831.ps1" in d["current_resume_point"]["full_settle_command"]
def test_latest_end_to_end_family_includes_project_job_costing():
 d=load();f=next(x for x in d["completed_families"] if x["family"]=="end_to_end_erp_cycles_added_last");assert "project job costing progress billing and revenue recognition" in f["capabilities"]
def test_truth_boundaries_remain_honest():d=load();assert d["truth_boundaries"]["runtime_result_parity"]=="NOT_PROVEN" and d["truth_boundaries"]["business_owner_acceptance"]=="NOT_OBSERVED" and d["truth_boundaries"]["provider_selection"]=="NOT_MADE"
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("runtime_result_parity_proven_count","command_ready_module_count","pilot_ready_module_count","database_connection_count","network_read_or_write_count","operational_execution_count","data_mutation_count","assembly_load_or_execution_count","sensitive_value_persisted_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert(s["risk_count"],s["mapped_risk_assignment_count"],s["design_lower_bound"])==(84,343,1404)
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
