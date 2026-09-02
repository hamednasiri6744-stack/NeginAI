import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_monetary_temporal_synthetic_reference_evaluator_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_monetary_temporal_synthetic_reference_evaluator_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"numeric_reference.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_vectors_pass():
 s=load()["summary"];assert(s["positive_vector_count"],s["positive_pass_count"])==(20,20);assert(s["negative_vector_count"],s["negative_pass_count"])==(14,14);assert(s["total_vector_count"],s["total_pass_count"])==(34,34)
def test_vector_families_present():
 s=load()["summary"];assert(s["rounding_vector_count"],s["allocation_vector_count"],s["conversion_vector_count"],s["reversal_vector_count"],s["temporal_positive_vector_count"])==(6,4,4,3,3)
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"];assert s["reference_evaluator_implementation_count"]==1
 for f in ("operational_numeric_or_temporal_implementation_count","operational_value_read_count","calculation_conversion_posting_or command_run_count","accepted_operational_receipt_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_reference_evaluator"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
