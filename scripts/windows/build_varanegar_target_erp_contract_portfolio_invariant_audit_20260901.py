"""Audit portfolio-wide invariants across every target-ERP contract artifact."""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];AN=ROOT/"artifacts/varanegar_analysis"
S={"coverage":"artifacts/varanegar_analysis/varanegar_target_erp_domain_coverage_gap_register_20260901.json","previous":"artifacts/varanegar_analysis/varanegar_target_erp_domain_coverage_gap_checkpoint_20260901.json","official_tests":"artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json","risk":"artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json","trace":"artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"}
ZERO_HINTS=("operational_","accepted_operational","command_ready","pilot_ready","provider_selected","actions_executed")
SYNTHETIC_HINTS=("synthetic","positive","negative","baseline","reference","vector")
def load(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def zero_key(name):return any(h in name for h in ZERO_HINTS) or ((name.endswith("_run_count") or name.endswith("_read_count")) and not any(h in name for h in SYNTHETIC_HINTS))
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();paths={k:ROOT/v for k,v in S.items()};d={k:load(v) for k,v in paths.items()};contracts=[]
 for row in d["coverage"]["completed_contract_inventory"]:contracts.append(ROOT/row["artifact"])
 findings=[];rows=[];ids=[]
 for path in contracts:
  q=load(path);artifact=q.get("artifact");ids.append(artifact);summary=q.get("summary",{});safety=q.get("safety",{});bad_zero={k:v for k,v in summary.items() if isinstance(v,int) and zero_key(k) and v!=0};stale=[]
  for x in q.get("source_manifest",[]):
   t=ROOT/x.get("path","")
   if not t.is_file():stale.append({"path":x.get("path"),"reason":"missing"});continue
   if x.get("size_bytes") is not None and x["size_bytes"]!=t.stat().st_size:stale.append({"path":x["path"],"reason":"size"})
   if x.get("sha256") and x["sha256"]!=sha(t):stale.append({"path":x["path"],"reason":"sha256"})
  lower={k:v for k,v in summary.items() if "design_lower_bound" in k}
  issues=[]
  if q.get("validation")!="PASS":issues.append("validation")
  if q.get("failed_checks"):issues.append("failed_checks")
  if not artifact:issues.append("artifact_id")
  if not q.get("scope",{}).get("mode"):issues.append("scope_mode")
  if not safety or set(safety.values())!={0}:issues.append("safety_zero")
  if bad_zero:issues.append("runtime_or_readiness_zero")
  if stale:issues.append("manifest_freshness")
  if lower and set(lower.values())!={1404}:issues.append("design_lower_bound")
  if not q.get("limits"):issues.append("limits")
  rows.append({"artifact":path.relative_to(ROOT).as_posix(),"artifact_id":artifact,"source_count":len(q.get("source_manifest",[])),"zero_counter_count":len([k for k in summary if zero_key(k)]),"lower_bound_field_count":len(lower),"issue_count":len(issues),"issues":issues})
  findings.extend({"artifact":path.relative_to(ROOT).as_posix(),"issue":x} for x in issues)
 duplicates=sorted({x for x in ids if ids.count(x)>1});official=d["official_tests"];summary={"audited_contract_count":len(contracts),"passing_contract_count":sum(not x["issues"] for x in rows),"portfolio_finding_count":len(findings),"duplicate_artifact_id_count":len(duplicates),"stale_contract_manifest_count":sum("manifest_freshness" in x["issues"] for x in rows),"nonzero_safety_contract_count":sum("safety_zero" in x["issues"] for x in rows),"nonzero_runtime_or_readiness_contract_count":sum("runtime_or_readiness_zero" in x["issues"] for x in rows),"invalid_lower_bound_contract_count":sum("design_lower_bound" in x["issues"] for x in rows),"official_test_file_count":official["runner"]["test_file_count"],"official_passed_test_count":official["runner"]["passed_test_count"],"risk_count":d["risk"]["summary"]["risk_count"],"mapped_risk_assignment_count":d["trace"]["summary"]["mapped_risk_assignment_count"],"design_lower_bound":1404,"command_ready_module_count":0,"pilot_ready_module_count":0}
 checks={"sources_pass":all(d[k].get("validation")=="PASS" for k in ("coverage","previous","official_tests")),"portfolio_count_matches_coverage":summary["audited_contract_count"]==d["coverage"]["summary"]["target_erp_contract_artifact_count"]==54,"all_contract_invariants_pass":summary["passing_contract_count"]==summary["audited_contract_count"] and summary["portfolio_finding_count"]==0,"artifact_ids_unique":summary["duplicate_artifact_id_count"]==0,"fresh_safety_runtime_lower_bound":all(summary[k]==0 for k in ("stale_contract_manifest_count","nonzero_safety_contract_count","nonzero_runtime_or_readiness_contract_count","invalid_lower_bound_contract_count")),"official_tests_pass_no_exclusion":official["validation"]=="PASS" and official["runner"]["bootstrap_excluded_test_file_count"]==0,"baseline_stable":(summary["risk_count"],summary["mapped_risk_assignment_count"],summary["design_lower_bound"])==(84,343,1404),"readiness_zero":summary["command_ready_module_count"]==summary["pilot_ready_module_count"]==0};failed=sorted(k for k,v in checks.items() if not v)
 manifest=[{"name":k,"path":S[k],"size_bytes":v.stat().st_size,"sha256":sha(v)} for k,v in sorted(paths.items())]+[{"name":f"audited_contract_{i:03d}","path":x.relative_to(ROOT).as_posix(),"size_bytes":x.stat().st_size,"sha256":sha(x)} for i,x in enumerate(contracts,1)]+[{"name":"builder","path":"scripts/windows/build_varanegar_target_erp_contract_portfolio_invariant_audit_20260901.py","size_bytes":Path(__file__).stat().st_size,"sha256":sha(Path(__file__))}]
 out={"artifact":"varanegar_target_erp_contract_portfolio_invariant_audit_20260901","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","scope":{"mode":"TARGET_ERP_CONTRACT_PORTFOLIO_STATIC_INVARIANT_AUDIT","runtime_execution":False,"provider_selection":False},"summary":summary,"audit_rows":rows,"portfolio_findings":findings,"duplicate_artifact_ids":duplicates,"invariants":["validation PASS and failed_checks empty","artifact id present and unique","scope mode and limits present","all safety counters zero","operational provider execution receipt command and pilot counters zero","every source manifest hash and size current","every declared design lower bound remains 1404"],"safety":{"database_connections":0,"network_reads_or_writes":0,"operational_records_or_business_values_read":0,"operational_forms_reports_queries_or_procedures_executed":0,"assemblies_loaded_or_executed":0,"data_mutations":0,"credentials_pii_or_raw_business_values_persisted":0},"checks":checks,"failed_checks":failed,"source_manifest":manifest,"limits":["This is a static portfolio audit, not runtime conformance.","Zero findings means the declared design invariants are internally current; it does not prove business correctness.","Operational UAT owner acceptance provider suitability and regulatory certification remain external evidence gates."]}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(summary,ensure_ascii=False));return 0 if not failed else 1
if __name__=="__main__":raise SystemExit(main())
