import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_concurrency_synthetic_reference_evaluator_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_concurrency_synthetic_reference_evaluator_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"concurrency_reference.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_vectors_pass():
 s=load()["summary"];assert(s["positive_vector_count"],s["positive_pass_count"])==(3,3);assert(s["negative_vector_count"],s["negative_pass_count"])==(13,13);assert(s["total_vector_count"],s["total_pass_count"])==(16,16)
def test_precedence_and_outcomes_present():
 d=load();assert d["outcome_precedence"][0]=="SCHEMA" and d["outcome_precedence"][-1]=="COMMIT";assert "RECONCILIATION_REQUIRED_UNKNOWN_COMMIT" in {x["actual"] for x in d["negative_results"]}
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"];assert s["reference_evaluator_implementation_count"]==1
 for f in ("operational_concurrency_implementation_count","runtime_version_lock_lease_or_fencing_read_count","command_conflict_retry_or_reconciliation_run_count","accepted_operational_receipt_count","command_ready_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_reference_evaluator"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
