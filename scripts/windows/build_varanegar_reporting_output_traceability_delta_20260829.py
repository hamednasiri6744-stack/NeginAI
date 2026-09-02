"""Map reporting/output continuation evidence to existing modules, requirements and risks."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCES={"gap":"artifacts/varanegar_analysis/varanegar_24h_continuation_gap_refresh_20260829.json","envelope":"artifacts/varanegar_analysis/varanegar_reporting_output_outcome_envelope_20260829.json","readiness":"artifacts/varanegar_analysis/varanegar_reporting_output_readiness_delta_20260829.json","golden":"artifacts/varanegar_analysis/varanegar_reporting_output_golden_uat_cases_20260829.json","playbook":"artifacts/varanegar_analysis/varanegar_reporting_output_expert_playbook_20260829.json","risk":"artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json","trace":"artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json","previous":"artifacts/varanegar_analysis/varanegar_reporting_output_expert_playbook_checkpoint_20260829.json"}
MODULES=["reporting_documents","sales","inventory","receivables_treasury","platform","integration_migration"]
RISKS=["R-002","R-005","R-006","R-007","R-017","R-023","R-036","R-059"]
MAPPINGS=[
 {"id":"RO-E24-01","source":"gap","modules":MODULES,"requirements":["reporting.output.gap_selection","reporting.runtime_owner_gate_separation"],"risks":RISKS},
 {"id":"RO-E24-02","source":"envelope","modules":MODULES,"requirements":["reporting.output.typed_outcome_receipt","reporting.render_completion_state_separation","reporting.batch_per_item_outcome"],"risks":RISKS},
 {"id":"RO-E24-03","source":"readiness","modules":MODULES,"requirements":["reporting.output.design_readiness_delta"],"risks":RISKS},
 {"id":"RO-E24-04","source":"golden","modules":MODULES,"requirements":["reporting.output.synthetic_acceptance_56","reporting.output.retry_idempotency_fault_matrix"],"risks":RISKS},
 {"id":"RO-E24-05","source":"playbook","modules":MODULES,"requirements":["reporting.output.incident_playbook","reporting.reprint_replay_separate_authority"],"risks":RISKS},
]
def load(path:Path):return json.loads(path.read_text(encoding="utf-8-sig"))
def sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path);args=parser.parse_args();paths={name:ROOT/rel for name,rel in SOURCES.items()};data={name:load(path) for name,path in paths.items()};known={x["id"] for x in data["risk"]["risks"]};module_risks={x["module"]:{r["id"] for r in x["risks"]} for x in data["trace"]["modules"]};reqs=sorted({r for m in MAPPINGS for r in m["requirements"]});linked=sorted({r for m in MAPPINGS for r in m["risks"]})
 summary={"reporting_output_evidence_count":len(MAPPINGS),"requirement_contract_delta_count":len(reqs),"module_evidence_link_count":sum(len(x["modules"]) for x in MAPPINGS),"risk_evidence_link_count":sum(len(x["risks"]) for x in MAPPINGS),"unique_linked_risk_count":len(linked),"base_risk_count":84,"base_mapped_risk_assignment_count":343,"new_risk_count":0,"runtime_readiness_promotions":0}
 checks={"sources_pass":all(x["validation"]=="PASS" for x in data.values()),"five_evidence":summary["reporting_output_evidence_count"]==5,"ten_requirements":summary["requirement_contract_delta_count"]==10,"link_counts":summary["module_evidence_link_count"]==30 and summary["risk_evidence_link_count"]==40,"eight_existing":summary["unique_linked_risk_count"]==8 and set(linked)<=known,"module_consistent":all(any(risk in module_risks[module] for module in mapping["modules"]) for mapping in MAPPINGS for risk in mapping["risks"]),"base_stable":data["risk"]["summary"]["risk_count"]==84 and data["trace"]["summary"]["mapped_risk_assignment_count"]==343,"runtime_zero":data["envelope"]["summary"]["runtime_outcome_parity_proven_count"]==data["golden"]["summary"]["executed_case_count"]==data["playbook"]["summary"]["runtime_incidents_diagnosed_count"]==0}
 failed=sorted(name for name,passed in checks.items() if not passed);out={"artifact":"varanegar_reporting_output_traceability_delta_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","safety":{"mode":"OFFLINE_EVIDENCE_SYNTHESIS","database_connections":0,"commands_forms_reports_or_procedures_executed":0,"assemblies_loaded_or_executed":0,"data_mutations":0,"sensitive_values_persisted":0},"summary":summary,"policy":{"relationship":"ADDITIVE_EVIDENCE_DELTA_ONLY","base_registers_unchanged":True,"no_risk_closure_or_runtime_promotion":True},"mappings":MAPPINGS,"requirements":reqs,"linked_existing_risks":linked,"checks":checks,"failed_checks":failed,"source_manifest":[{"name":name,"path":SOURCES[name],"size_bytes":path.stat().st_size,"sha256":sha(path)} for name,path in sorted(paths.items())],"confidence":{"design_trace":"HIGH","runtime_effect_parity":"UNPROVEN"},"limits":["Risk links do not close risks.","The 84-risk and 343-assignment base registers remain unchanged.","No runtime output or incident diagnosis is claimed."]}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(args.output.resolve());print(out["validation"]);print(json.dumps(summary,ensure_ascii=False));return 0 if not failed else 1
if __name__=="__main__":raise SystemExit(main())
