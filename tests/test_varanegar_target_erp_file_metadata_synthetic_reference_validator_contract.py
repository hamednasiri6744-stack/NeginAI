import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_file_metadata_synthetic_reference_validator_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_file_metadata_synthetic_reference_validator_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"file_reference.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_vectors_pass():s=load()["summary"];assert(s["positive_vector_count"],s["positive_pass_count"])==(5,5);assert(s["negative_vector_count"],s["negative_pass_count"])==(14,14);assert(s["total_vector_count"],s["total_pass_count"])==(19,19)
def test_precedence_and_outcomes_present():d=load();assert d["outcome_precedence"][0]=="SCHEMA" and d["outcome_precedence"][-1]=="ACCEPTED";assert "QUARANTINED_ACCESS_BLOCKED" in {x["actual"] for x in d["positive_results"]}
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"];assert s["reference_validator_implementation_count"]==1
 for f in ("operational_file_scanner_or_parser_implementation_count","operational_file_body_or_archive_read_count","scan_quarantine_download_export_or_disposition_run_count","accepted_operational_receipt_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_reference_validator"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
