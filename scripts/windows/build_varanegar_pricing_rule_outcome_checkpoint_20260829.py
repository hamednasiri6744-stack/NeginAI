"""Checkpoint the Pricing Rules outcome contract."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
S={"envelope":"artifacts/varanegar_analysis/varanegar_pricing_rule_outcome_envelope_20260829.json","previous":"artifacts/varanegar_analysis/varanegar_reporting_output_traceability_delta_checkpoint_20260829.json","builder":"scripts/windows/build_varanegar_pricing_rule_outcome_envelope_20260829.py","checkpoint_builder":"scripts/windows/build_varanegar_pricing_rule_outcome_checkpoint_20260829.py","test":"tests/test_varanegar_pricing_rule_outcome_envelope.py","checkpoint_test":"tests/test_varanegar_pricing_rule_outcome_checkpoint.py","doc":"docs/varanegar_reconstruction/PRICING_RULE_OUTCOME_RETRY_AND_PUBLICATION_CONTRACT_20260829_FA.md"}
def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();paths={k:ROOT/v for k,v in S.items()};d=load(paths["envelope"]);prev=load(paths["previous"]);s=d["summary"]
 checks={"sources_pass":d["validation"]==prev["validation"]=="PASS","seven_commands":s["command_contract_count"]==7,"reused_64":s["existing_reused_golden_case_count"]==64,"allocator":s["linear_max_id_plus_one_literal_count"]==1,"replication":s["replication_unproven_gate_count"]==6,"runtime_zero":s["runtime_effect_parity_proven_count"]==s["implemented_command_count"]==s["owner_approved_count"]==0,"base_stable":s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343,"safety_zero":set(v for k,v in d["safety"].items() if k!="mode")=={0}}
 failed=sorted(k for k,v in checks.items() if not v);out={"artifact":"varanegar_pricing_rule_outcome_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","previous_checkpoint":{"path":S["previous"],"sha256":sha(paths["previous"])},"checks":checks,"failed_checks":failed,"source_manifest":[{"name":k,"path":S[k],"size_bytes":v.stat().st_size,"sha256":sha(v)} for k,v in sorted(paths.items())],"safety":{"commands_forms_queries_or_procedures_executed":0,"assemblies_loaded_or_executed":0,"database_connections":0,"data_mutations":0,"sensitive_values_persisted":0}}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);return 0 if not failed else 1
if __name__=="__main__": raise SystemExit(main())
