import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_domain_coverage_gap_register_20260901.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_domain_coverage_gap_register_20260901.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"coverage.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_contract_inventory_is_complete_and_passing():s=load()["summary"];assert s["target_erp_contract_artifact_count"]==s["passing_contract_artifact_count"]>=54
def test_gap_priorities_and_packages_are_explicit():d=load();s=d["summary"];assert(s["remaining_gap_count"],s["p0_gap_count"],s["p1_gap_count"],s["p2_gap_count"])==(6,0,4,2);assert all(x["minimum_package"] and x["dependencies"] and x["runtime_status"]=="NOT_PROVEN" for x in d["remaining_domain_gaps"])
def test_p0_is_closed():assert not [x for x in load()["remaining_domain_gaps"] if x["priority"]=="P0"]
def test_no_runtime_or_readiness_claim():d=load();s=d["summary"];assert s["operational_contract_receipt_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0;assert set(d["safety"].values())=={0};assert(s["risk_count"],s["mapped_risk_assignment_count"],s["design_lower_bound"])==(84,343,1404)
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
