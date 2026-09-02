"""Build the Discount V2 input-dataset and query-consistency checkpoint."""

from __future__ import annotations

import argparse, hashlib, json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "runtime": "artifacts/varanegar_analysis/domains/discount_v2_query_contracts_20260829.json",
    "sql": "artifacts/varanegar_analysis/domains/discount_v2_dataset_sql_20260829.json",
    "previous_checkpoint": "artifacts/varanegar_analysis/varanegar_order_sale_evc_checkpoint_20260829.json",
    "risk_register": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "traceability": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
    "runtime_extractor": "scripts/windows/extract_varanegar_discount_v2_query_contracts.py",
    "sql_extractor": "scripts/sql/extract_varanegar_discount_v2_dataset_sql.py",
    "risk_builder": "scripts/windows/build_negin_erp_risk_register.py",
    "rebuild_script": "scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
    "checkpoint_builder": "scripts/windows/build_varanegar_discount_v2_query_checkpoint_20260829.py",
    "tests": "tests/test_varanegar_discount_v2_query_boundary.py",
    "domain_doc": "docs/varanegar_reconstruction/DISCOUNT_V2_INPUT_DATASET_AND_QUERY_CONTRACT_20260829_FA.md",
    "knowledge_doc": "docs/VARANEGAR_KNOWLEDGE_FA.md",
    "discovery_log": "docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
    "readme": "docs/varanegar_reconstruction/README_FA.md",
}

def _load(name): return json.loads((ROOT/SOURCES[name]).read_text(encoding="utf-8-sig"))
def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    missing=[p for p in SOURCES.values() if not (ROOT/p).is_file()]
    if missing: raise AssertionError({"missing_sources":missing})
    runtime,sql,previous,risks,trace=(_load(x) for x in ("runtime","sql","previous_checkpoint","risk_register","traceability"))
    r079=next(row for row in risks["risks"] if row["id"]=="R-079")
    checks={
        "static_query_contract_passes": runtime["validation"]=="PASS" and runtime["summary"]["query_template_count"]==42 and runtime["source"]["inventory_sha256_match"] and runtime["safety"]["assembly_loads_or_executions"]==0,
        "query_categories_and_dependencies_are_complete": runtime["summary"]["reference_or_rule_template_count"]==17 and runtime["summary"]["order_request_template_count"]==10 and runtime["summary"]["other_template_count"]==15 and runtime["summary"]["unique_table_reference_count"]==44,
        "formatted_read_only_contract_is_bounded": runtime["summary"]["formatted_template_count"]==27 and runtime["summary"]["format_placeholder_slot_count"]==31 and runtime["summary"]["write_or_exec_template_count"]==0 and runtime["safety"]["raw_sql_or_business_values_persisted"]==0,
        "read_only_catalog_resolution_passes": sql["validation"]=="PASS" and sql["summary"]["persistent_reference_count"]==41 and sql["summary"]["resolved_reference_count"]==41 and sql["safety"]["data_mutations"]==0,
        "statement_snapshot_boundary_is_explicit": sql["assertions"]["clone_uses_rcsi_and_allows_snapshot_isolation"] and sql["database_isolation"]["is_read_committed_snapshot_on"] is True,
        "r079_integrates_query_evidence_without_inflation": (ROOT/SOURCES["runtime"]).as_posix() in r079["evidence_refs"] and (ROOT/SOURCES["sql"]).as_posix() in r079["evidence_refs"] and "mixed-version CalcData" in r079["failure_mode"] and risks["summary"]["risk_count"]==84,
        "metrics_and_chain_pass": previous["validation"]=="PASS" and risks["source_checkpoint"]["discount_v2_query_template_count"]==42 and risks["source_checkpoint"]["discount_v2_resolved_dependency_count"]==41 and trace["summary"]["mapped_risk_assignment_count"]==343 and trace["summary"]["command_ready_module_count"]==0,
    }
    failed=sorted(k for k,v in checks.items() if not v)
    manifest=[{"name":n,"path":p,"size_bytes":(ROOT/p).stat().st_size,"sha256":_sha(ROOT/p)} for n,p in sorted(SOURCES.items())]
    return {"artifact":"varanegar_discount_v2_query_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","safety":{"mode":"OFFLINE_FROM_STATIC_AND_READ_ONLY_CATALOG_EVIDENCE","database_connections":0,"network_reads_or_writes":0,"assemblies_loaded_or_executed":0,"operational_commands_executed":0},"source_manifest":manifest,"checks":checks,"failed_checks":failed,"summary":{"source_count":len(manifest),"passed_check_count":sum(checks.values()),"failed_check_count":len(failed),"query_template_count":runtime["summary"]["query_template_count"],"persistent_dependency_count":sql["summary"]["persistent_reference_count"],"risk_count":risks["summary"]["risk_count"],"mapped_risk_assignment_count":trace["summary"]["mapped_risk_assignment_count"]}}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();x=build();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(x["validation"]);print(json.dumps(x["summary"],ensure_ascii=False));return 0 if x["validation"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
