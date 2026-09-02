"""Chain the treasury command outcome/retry envelope."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
S={"envelope":"artifacts/varanegar_analysis/varanegar_treasury_command_outcome_envelope_20260829.json","previous":"artifacts/varanegar_analysis/varanegar_24h_continuation_wave01_checkpoint_20260829.json","builder":"scripts/windows/build_varanegar_treasury_command_outcome_envelope_20260829.py","checkpoint_builder":"scripts/windows/build_varanegar_treasury_command_outcome_checkpoint_20260829.py","test":"tests/test_varanegar_treasury_command_outcome_envelope.py","doc":"docs/varanegar_reconstruction/TREASURY_COMMAND_OUTCOME_RETRY_ENVELOPE_20260829_FA.md"}
def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();paths={k:ROOT/v for k,v in S.items()};e=load(paths["envelope"]);prev=load(paths["previous"]);s=e["summary"]
 checks={"sources_pass":e["validation"]==prev["validation"]=="PASS","twelve_commands":s["command_count"]==12,"seven_static_five_design":s["legacy_static_command_count"]==7 and s["target_design_only_command_count"]==5,"four_outcomes":s["target_outcome_code_count"]==4,"runtime_owner_zero":s["runtime_effect_parity_proven_count"]==s["executed_acceptance_case_count"]==s["owner_approved_count"]==0,"risk_trace_stable":s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["new_risk_count"]==0,"safety_zero":set(v for k,v in e["safety"].items() if k!="mode")=={0}};failed=sorted(k for k,v in checks.items() if not v)
 out={"artifact":"varanegar_treasury_command_outcome_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","previous_checkpoint":{"path":S["previous"],"sha256":sha(paths["previous"])},"checks":checks,"failed_checks":failed,"source_manifest":[{"name":k,"path":S[k],"size_bytes":v.stat().st_size,"sha256":sha(v)} for k,v in sorted(paths.items())],"safety":{"commands_forms_queries_or_procedures_executed":0,"assemblies_loaded_or_executed":0,"database_connections":0,"data_mutations":0,"sensitive_values_persisted":0}};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);return 0 if not failed else 1
if __name__=="__main__": raise SystemExit(main())
