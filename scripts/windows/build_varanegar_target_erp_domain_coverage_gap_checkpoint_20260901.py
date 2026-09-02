"""Chain the target-ERP domain coverage and gap register."""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
S={"register":"artifacts/varanegar_analysis/varanegar_target_erp_domain_coverage_gap_register_20260901.json","previous":"artifacts/varanegar_analysis/varanegar_target_erp_project_job_costing_synthetic_reference_evaluator_checkpoint_20260901.json","builder":"scripts/windows/build_varanegar_target_erp_domain_coverage_gap_register_20260901.py","checkpoint_builder":"scripts/windows/build_varanegar_target_erp_domain_coverage_gap_checkpoint_20260901.py","test":"tests/test_varanegar_target_erp_domain_coverage_gap_register.py","checkpoint_test":"tests/test_varanegar_target_erp_domain_coverage_gap_checkpoint.py","doc":"docs/varanegar_reconstruction/TARGET_ERP_DOMAIN_COVERAGE_GAP_REGISTER_20260901_FA.md"}
def load(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();paths={k:ROOT/v for k,v in S.items()};c=load(paths["register"]);prev=load(paths["previous"]);s=c["summary"]
 checks={"sources_pass":c["validation"]==prev["validation"]=="PASS","contract_inventory_pass":s["target_erp_contract_artifact_count"]==s["passing_contract_artifact_count"] and s["target_erp_contract_artifact_count"]>=54,"gap_priorities_0_4_2":(s["p0_gap_count"],s["p1_gap_count"],s["p2_gap_count"])==(0,4,2),"runtime_and_readiness_zero":s["operational_contract_receipt_count"]==s["command_ready_module_count"]==s["pilot_ready_module_count"]==0,"baseline_stable":(s["risk_count"],s["mapped_risk_assignment_count"],s["design_lower_bound"])==(84,343,1404),"safety_zero":set(c["safety"].values())=={0}};failed=sorted(k for k,v in checks.items() if not v)
 out={"artifact":"varanegar_target_erp_domain_coverage_gap_checkpoint_20260901","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","previous_checkpoint":{"path":S["previous"],"sha256":sha(paths["previous"])},"checks":checks,"failed_checks":failed,"source_manifest":[{"name":k,"path":S[k],"size_bytes":v.stat().st_size,"sha256":sha(v)} for k,v in sorted(paths.items())],"safety":{"database_connections":0,"network_reads_or_writes":0,"operational_records_or_business_values_read":0,"operational_forms_reports_queries_or_procedures_executed":0,"assemblies_loaded_or_executed":0,"data_mutations":0,"credentials_pii_or_raw_business_values_persisted":0}}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);return 0 if not failed else 1
if __name__=="__main__":raise SystemExit(main())
