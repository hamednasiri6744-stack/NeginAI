import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts/windows"))
from varanegar_evidence_redaction_reference import ALLOWED_FIELDS,validate_evidence
B=ROOT/"scripts/windows/build_varanegar_target_erp_evidence_redaction_synthetic_reference_validator_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_evidence_redaction_synthetic_reference_validator_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"validator.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals_and_all_results_pass():
 s=load()["summary"];assert(s["evidence_channel_count"],s["allowed_field_count"],s["prohibited_field_code_count"],s["negative_mutation_count"])==(10,8,13,14);assert s["positive_execution_count"]==s["positive_pass_count"]==10;assert s["negative_execution_count"]==s["negative_pass_count"]==140;assert s["synthetic_execution_count"]==s["synthetic_pass_count"]==150;assert(s["gate_count"],s["channel_gate_assignment_count"])==(8,80)
def test_positive_and_negative_reference_behavior():
 d=load();assert all(x["status"]=="PASS" and x["accepted"] for x in d["positive_results"]);assert all(x["status"]=="PASS" and not x["accepted"] and x["changed_field_count"]==1 for x in d["negative_results"]);assert set(d["allowed_fields"])==ALLOWED_FIELDS
def test_unknown_nested_and_incomplete_fail_closed():
 assert validate_evidence("SYNTHETIC_CHANNEL",{"unknown":{"nested":True}})=={"accepted":False,"code":"UNKNOWN_OR_NESTED_PAYLOAD"};assert validate_evidence("SYNTHETIC_CHANNEL",{})=={"accepted":False,"code":"ALLOWED_FIELD_SET_INCOMPLETE"}
def test_no_operational_or_readiness_claim():
 d=load();s=d["summary"];assert s["reference_validator_implementation_count"]==1
 for f in ("operational_logging_redaction_implementation_count","real_log_or_runtime_sample_scan_count","accepted_runtime_attestation_count","command_ready_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_reference_validator"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
