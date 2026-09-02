"""Build the offline sales-return issue/cancel checkpoint."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
 "sql_boundary":"artifacts/varanegar_analysis/domains/return_issue_cancel_boundary_20260829.json",
 "runtime_boundary":"artifacts/varanegar_analysis/domains/return_issue_cancel_runtime_boundary_20260829.json",
 "return_domain":"artifacts/varanegar_analysis/domains/sales_returns_and_settlement_20260826.json",
 "return_amount":"artifacts/varanegar_analysis/ui/varanegar_sales_return_amount_diagnostic_contract_20260827.json",
 "previous_checkpoint":"artifacts/varanegar_analysis/varanegar_sale_cancellation_checkpoint_20260829.json",
 "risk_register":"artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
 "traceability":"artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
 "sql_extractor":"scripts/sql/extract_varanegar_return_issue_cancel_boundary.py",
 "runtime_extractor":"scripts/sql/extract_varanegar_return_issue_cancel_runtime_boundary.py",
 "risk_builder":"scripts/windows/build_negin_erp_risk_register.py",
 "rebuild_script":"scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
 "checkpoint_builder":"scripts/windows/build_varanegar_return_issue_cancel_checkpoint_20260829.py",
 "tests":"tests/test_varanegar_return_issue_cancel_boundary.py",
 "domain_doc":"docs/varanegar_reconstruction/SALES_RETURN_ISSUE_CANCEL_VOUCHER_AND_CREDIT_BOUNDARY_20260829_FA.md",
 "knowledge_doc":"docs/VARANEGAR_KNOWLEDGE_FA.md",
 "discovery_log":"docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md",
 "readme":"docs/varanegar_reconstruction/README_FA.md",
}

def _load(name): return json.loads((ROOT/SOURCES[name]).read_text(encoding="utf-8-sig"))
def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    missing=[p for p in SOURCES.values() if not (ROOT/p).is_file()]
    if missing: raise AssertionError({"missing_sources":missing})
    sql,runtime,previous,risks,trace=(_load(x) for x in ("sql_boundary","runtime_boundary","previous_checkpoint","risk_register","traceability"))
    static,managed=sql["static_issue_cancel_contract"],runtime["managed_return_contract"]
    r081=next(x for x in risks["risks"] if x["id"]=="R-081")
    raw=(ROOT/SOURCES["sql_boundary"]).read_text(encoding="utf-8")
    checks={
      "sql_read_only_redacted":sql["validation"]=="PASS" and sql["safety"]["database_updateability"]=="READ_ONLY" and sql["safety"]["can_update"]==0 and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"]==0 and sql["safety"]["return_sale_voucher_payment_customer_user_host_or_raw_values_persisted"]==0,
      "sql_hash_coverage":sql["summary"]["selected_sql_module_count"]==9 and all(len(x["definition_sha256"])==64 for x in sql["sql_module_profiles"]),
      "sql_issue_cancel_contract":all(static.values()),
      "current_projection":sql["summary"]["active_return_count"]==13913 and sql["summary"]["cancelled_return_count"]==178 and sql["summary"]["active_return_with_type10_voucher_count"]==13913 and sql["summary"]["cancelled_return_with_type10_voucher_count"]==0 and sql["summary"]["cancelled_return_with_payment_count"]==0,
      "flag_is_history_not_existence":next(x for x in sql["current_return_state"]["by_cancel_flag"] if x["CancelFlag"]==1)["voucher_flag_one_count"]==178,
      "audit_has_no_absence":sql["summary"]["retained_return_delete_log_count"]==0 and sql["summary"]["logged_return_absent_count"]==0 and sql["summary"]["direct_physical_return_delete_candidate_count"]==3,
      "runtime_hash_pinned":runtime["validation"]=="PASS" and runtime["summary"]["assembly_count"]==3 and runtime["summary"]["selected_method_count"]==5 and runtime["summary"]["selected_instruction_count"]==404 and runtime["summary"]["source_hash_mismatch_count"]==0 and runtime["safety"]["assembly_loads_or_executions"]==0,
      "runtime_route":managed["ui_cancel_calls_business_without_explicit_context_commit_or_rollback"] and managed["business_cancel_is_thin_adapter_delegate"] and managed["business_generate_is_thin_adapter_delegate"] and managed["adapter_cancel_uses_named_save_or_cancel_procedures"] and managed["adapter_generate_uses_named_generator"] and managed["adapter_cancel_context_query_or_execute"] and managed["adapter_cancel_has_explicit_commit"] and not managed["adapter_cancel_has_explicit_rollback"] and managed["adapter_generate_queries_named_generator_without_explicit_context_commit_or_rollback"] and not managed["managed_to_sql_physical_transaction_enlistment_proven"],
      "previous_chain":previous["validation"]=="PASS" and previous["summary"]["risk_count"]==84,
      "r081_caveated":r081["severity"]=="CRITICAL" and "Current state is clean and must not be called an incident" in r081["failure_mode"] and "are capability only" in r081["failure_mode"],
      "register_trace":risks["summary"]["risk_count"]==84 and risks["summary"]["critical_count"]==50 and risks["summary"]["high_count"]==31 and trace["summary"]["unique_risk_count"]==84 and trace["summary"]["mapped_risk_assignment_count"]==343 and trace["summary"]["command_ready_module_count"]==0,
      "no_uuid_secret":re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",raw) is None and re.search(r"(?i)(password|pwd)\s*[=:]",raw) is None,
    }
    failed=sorted(k for k,v in checks.items() if not v)
    manifest=[{"name":n,"path":p,"size_bytes":(ROOT/p).stat().st_size,"sha256":_sha(ROOT/p)} for n,p in sorted(SOURCES.items())]
    return {"artifact":"varanegar_return_issue_cancel_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL",
            "safety":{"mode":"OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE","database_connections":0,"network_reads_or_writes":0,"live_ui_actions":0,"assemblies_loaded_or_executed":0,"operational_commands_executed":0,"return_sale_voucher_payment_customer_user_host_error_or_raw_values_read":0},
            "source_manifest":manifest,"checks":checks,"failed_checks":failed,
            "summary":{"source_count":len(manifest),"passed_check_count":sum(checks.values()),"failed_check_count":len(failed),"selected_sql_module_count":sql["summary"]["selected_sql_module_count"],"selected_runtime_method_count":runtime["summary"]["selected_method_count"],"active_return_count":sql["summary"]["active_return_count"],"cancelled_return_count":sql["summary"]["cancelled_return_count"],"active_return_with_type10_voucher_count":sql["summary"]["active_return_with_type10_voucher_count"],"cancelled_return_with_type10_voucher_count":sql["summary"]["cancelled_return_with_type10_voucher_count"],"cancelled_return_with_payment_count":sql["summary"]["cancelled_return_with_payment_count"],"risk_count":risks["summary"]["risk_count"],"mapped_risk_assignment_count":trace["summary"]["mapped_risk_assignment_count"]}}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();x=build();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(x["validation"]);print(json.dumps(x["summary"],ensure_ascii=False));return 0 if x["validation"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
