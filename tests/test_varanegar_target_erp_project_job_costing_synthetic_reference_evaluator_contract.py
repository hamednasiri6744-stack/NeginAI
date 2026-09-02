import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_project_job_costing_synthetic_reference_evaluator_contract_20260901.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_project_job_costing_synthetic_reference_evaluator_contract_20260901.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"project-ref.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_vectors_pass():s=load()["summary"];assert s["positive_vector_count"]==s["positive_pass_count"]==6;assert s["negative_vector_count"]==s["negative_pass_count"]==18;assert s["total_vector_count"]==s["total_pass_count"]==24
def test_no_operational_claim():d=load();s=d["summary"];assert set(d["safety"].values())=={0};assert s["accepted_operational_receipt_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0
def test_source_manifest_current():
 for x in load()["source_manifest"]:p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
