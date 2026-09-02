"""Build the chained checkpoint for the opening 25-hour gap map."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "gap_map": "artifacts/varanegar_analysis/varanegar_25h_opening_gap_map_20260829.json",
    "prior_bundle": "artifacts/varanegar_analysis/varanegar_15h_final_baseline_bundle_20260829.json",
    "gap_builder": "scripts/windows/build_varanegar_25h_gap_map_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_25h_gap_checkpoint_20260829.py",
    "test": "tests/test_varanegar_25h_opening_gap_map.py",
    "document": "docs/varanegar_reconstruction/VARANEGAR_25H_OPENING_GAP_MAP_20260829_FA.md",
}
def load(path): return json.loads(path.read_text(encoding="utf-8-sig"))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output", required=True, type=Path); args=parser.parse_args()
    paths={name:ROOT/rel for name,rel in SOURCES.items()}; missing=[SOURCES[n] for n,p in paths.items() if not p.is_file()]
    if missing: raise AssertionError({"missing_sources":missing})
    gap,prior=load(paths["gap_map"]),load(paths["prior_bundle"])
    checks={"gap_map_passes":gap["validation"]=="PASS","prior_bundle_passes":prior["validation"]=="PASS","chain_is_drift_free":gap["baseline"]["drift_count"]==0,"priority_is_report_parity":gap["prioritized_gaps"][0]["gap_id"]=="G25-REPORT-IDENTITY-SCOPE-PARITY","risk_baseline_stable":gap["baseline"]["risk_count"]==84 and gap["baseline"]["mapped_risk_assignment_count"]==343,"zero_execution_and_mutation":set(v for k,v in gap["safety"].items() if k!="mode")=={0}}
    failed=sorted(k for k,v in checks.items() if not v)
    payload={"artifact":"varanegar_25h_gap_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","previous_checkpoint":{"path":SOURCES["prior_bundle"],"sha256":sha(paths["prior_bundle"])},"checks":checks,"failed_checks":failed,"source_manifest":[{"name":n,"path":SOURCES[n],"size_bytes":p.stat().st_size,"sha256":sha(p)} for n,p in sorted(paths.items())],"safety":{"database_connections":0,"live_ui_actions":0,"operational_commands_executed":0,"assemblies_loaded_or_executed":0,"data_mutations":0,"sensitive_values_persisted":0},"confidence":"CONFIRMED_OFFLINE_EVIDENCE","limits":["Result parity remains unproven until isolated UAT is explicitly authorized."]}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(args.output.resolve()); print(payload["validation"]); return 0 if not failed else 1
if __name__=="__main__": raise SystemExit(main())
