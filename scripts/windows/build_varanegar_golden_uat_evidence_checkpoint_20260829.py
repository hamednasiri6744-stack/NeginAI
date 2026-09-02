"""Build chained checkpoint for Golden/UAT evidence classification."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
S={"ledger":"artifacts/varanegar_analysis/varanegar_golden_uat_evidence_ledger_20260829.json","previous":"artifacts/varanegar_analysis/varanegar_command_readiness_checkpoint_20260829.json","builder":"scripts/windows/build_varanegar_golden_uat_evidence_ledger_20260829.py","checkpoint_builder":"scripts/windows/build_varanegar_golden_uat_evidence_checkpoint_20260829.py","test":"tests/test_varanegar_golden_uat_evidence_ledger.py","doc":"docs/varanegar_reconstruction/GOLDEN_UAT_EVIDENCE_LEDGER_20260829_FA.md"}
def load(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();paths={k:ROOT/v for k,v in S.items()};d={k:load(paths[k]) for k in ("ledger","previous")};s=d["ledger"]["summary"]
 checks={"sources_pass":d["ledger"]["validation"]==d["previous"]["validation"]=="PASS","scope_pinned":s["synthetic_command_case_count"]==77 and s["command_module_count"]==14 and s["report_surface_count"]==20,"runtime_zero":s["executed_case_count"]==s["result_parity_proven_count"]==s["owner_approved_golden_count"]==0,"readiness_zero":s["uat_ready_track_count"]==s["pilot_ready_track_count"]==0,"risk_stable":s["risk_count"]==84,"zero_execution":set(v for k,v in d["ledger"]["safety"].items() if k!="mode")=={0}};failed=sorted(k for k,v in checks.items() if not v)
 out={"artifact":"varanegar_golden_uat_evidence_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","previous_checkpoint":{"path":S["previous"],"sha256":sha(paths["previous"])},"checks":checks,"failed_checks":failed,"source_manifest":[{"name":k,"path":S[k],"size_bytes":v.stat().st_size,"sha256":sha(v)} for k,v in sorted(paths.items())],"safety":{"commands_forms_queries_or_procedures_executed":0,"assemblies_loaded_or_executed":0,"database_connections":0,"data_mutations":0,"sensitive_values_persisted":0}}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);return 0 if not failed else 1
if __name__=="__main__":raise SystemExit(main())
