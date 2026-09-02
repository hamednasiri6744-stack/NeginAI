"""Build the offline sale-accounting issuance/crosswalk checkpoint."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
 "boundary":"artifacts/varanegar_analysis/domains/sale_accounting_crosswalk_boundary_20260829.json",
 "general_ledger":"artifacts/varanegar_analysis/domains/general_ledger_staging_and_posting_20260826.json",
 "accounting_policy":"artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json",
 "sale_snapshot":"artifacts/varanegar_analysis/domains/sale_voucher_snapshot_boundary_20260829.json",
 "previous_checkpoint":"artifacts/varanegar_analysis/varanegar_sale_voucher_snapshot_checkpoint_20260829.json",
 "risk_register":"artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
 "traceability":"artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
 "extractor":"scripts/sql/extract_varanegar_sale_accounting_crosswalk_boundary.py",
 "risk_builder":"scripts/windows/build_negin_erp_risk_register.py",
 "rebuild_script":"scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
 "checkpoint_builder":"scripts/windows/build_varanegar_sale_accounting_crosswalk_checkpoint_20260829.py",
 "tests":"tests/test_varanegar_sale_accounting_crosswalk_boundary.py",
 "domain_doc":"docs/varanegar_reconstruction/SALE_ACCOUNTING_ISSUANCE_WATERMARK_AND_CROSSWALK_BOUNDARY_20260829_FA.md",
 "knowledge_doc":"docs/VARANEGAR_KNOWLEDGE_FA.md",
 "discovery_log":"docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
 "readme":"docs/varanegar_reconstruction/README_FA.md",
}

def _load(name): return json.loads((ROOT/SOURCES[name]).read_text(encoding="utf-8-sig"))
def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    missing=[p for p in SOURCES.values() if not (ROOT/p).is_file()]
    if missing: raise AssertionError({"missing_sources":missing})
    boundary,previous,risks,trace=(_load(x) for x in ("boundary","previous_checkpoint","risk_register","traceability"))
    static=boundary["static_sale_accounting_contract"]
    r083=next(x for x in risks["risks"] if x["id"]=="R-083")
    raw=(ROOT/SOURCES["boundary"]).read_text(encoding="utf-8")
    active=next(x for x in boundary["sale_state_accounting_shapes"] if (x["Status"],x["CancelFlag"],x["has_sale_no"])==(1,0,1))
    months={x["business_month"]:x for x in boundary["active_final_accounting_coverage_by_business_month"]}
    q={(x["has_snapshot"],x["has_accounting_source"]):x for x in boundary["active_final_snapshot_accounting_quadrants"]}
    chain=boundary["sale_batch_journal_chain"]
    checks={
      "read_only_redacted":boundary["validation"]=="PASS" and boundary["safety"]["database_updateability"]=="READ_ONLY" and boundary["safety"]["can_update"]==0 and boundary["safety"]["stored_procedure_view_form_or_application_command_executions"]==0 and boundary["safety"]["sale_snapshot_accounting_customer_user_host_or_raw_values_persisted"]==0,
      "hash_coverage":boundary["summary"]["selected_sql_module_count"]==3 and all(len(x["definition_sha256"])==64 for x in boundary["sql_module_profiles"]),
      "static_contract":all(static.values()),
      "source_integrity":boundary["summary"]["sale_accounting_source_count"]==202636 and boundary["summary"]["sale_accounting_line_count"]==625839 and boundary["summary"]["sale_accounting_source_without_current_sale_count"]==0 and boundary["summary"]["sale_accounting_source_with_multiple_batch_count"]==0 and boundary["summary"]["unbalanced_sale_accounting_source_count"]==0,
      "journal_chain":chain["batch_count"]==101649 and chain["missing_batch_link_count"]==0 and chain["link_without_journal_count"]==0 and chain["link_with_multiple_journal_count"]==0 and chain["link_with_one_active_journal_count"]==202636,
      "issuance_watermark":active["without_accounting_source_count"]==10123 and months["1405/03"]["without_accounting_source_count"]==0 and months["1405/04"]["without_accounting_source_count"]==0 and months["1405/05"]["without_accounting_source_count"]==10122 and months["1403/01"]["without_accounting_source_count"]==1,
      "independent_state_dimensions":q[(0,0)]["sale_count"]==480 and q[(0,1)]["sale_count"]==9008 and q[(1,0)]["sale_count"]==9643 and q[(1,1)]["sale_count"]==193628 and boundary["summary"]["snapshot_without_accounting_source_count"]==72555 and boundary["summary"]["cancelled_sale_accounting_source_count"]==0,
      "historical_policy_and_amount_caveat":next(x for x in boundary["sale_batch_source_grouping"] if x["source_shape"]=="MULTI_SOURCE")["batch_count"]==370 and active["debit_differs_sale_amount_count"]==175042,
      "previous_chain":previous["validation"]=="PASS" and previous["summary"]["risk_count"]==84,
      "r083_caveated":r083["severity"]=="CRITICAL" and "must not be called an incident" in r083["failure_mode"] and "does not prove historical non-issuance" in r083["failure_mode"] and "must not be called an accounting mismatch" in r083["failure_mode"],
      "register_trace":risks["summary"]["risk_count"]==84 and risks["summary"]["critical_count"]==50 and risks["summary"]["high_count"]==31 and trace["summary"]["unique_risk_count"]==84 and trace["summary"]["mapped_risk_assignment_count"]==343 and trace["summary"]["command_ready_module_count"]==0,
      "no_uuid_secret":re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",raw) is None and re.search(r"(?i)(password|pwd)\s*[=:]",raw) is None,
    }
    failed=sorted(k for k,v in checks.items() if not v)
    manifest=[{"name":n,"path":p,"size_bytes":(ROOT/p).stat().st_size,"sha256":_sha(ROOT/p)} for n,p in sorted(SOURCES.items())]
    return {"artifact":"varanegar_sale_accounting_crosswalk_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL",
            "safety":{"mode":"OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE","database_connections":0,"network_reads_or_writes":0,"live_ui_actions":0,"assemblies_loaded_or_executed":0,"operational_commands_executed":0,"sale_snapshot_accounting_customer_user_host_error_or_raw_values_read":0},
            "source_manifest":manifest,"checks":checks,"failed_checks":failed,
            "summary":{"source_count":len(manifest),"passed_check_count":sum(checks.values()),"failed_check_count":len(failed),"sale_accounting_source_count":boundary["summary"]["sale_accounting_source_count"],"sale_accounting_line_count":boundary["summary"]["sale_accounting_line_count"],"active_final_without_accounting_source_count":active["without_accounting_source_count"],"open_month_without_accounting_source_count":months["1405/05"]["without_accounting_source_count"],"historical_without_accounting_source_count":months["1403/01"]["without_accounting_source_count"],"risk_count":risks["summary"]["risk_count"],"mapped_risk_assignment_count":trace["summary"]["mapped_risk_assignment_count"]}}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();x=build();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(x["validation"]);print(json.dumps(x["summary"],ensure_ascii=False));return 0 if x["validation"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
