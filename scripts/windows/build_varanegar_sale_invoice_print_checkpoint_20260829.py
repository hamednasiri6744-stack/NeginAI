"""Build the offline sale-invoice Crystal template and print-audit checkpoint."""
from __future__ import annotations
import argparse,hashlib,json,re
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES={
 "sql_boundary":"artifacts/varanegar_analysis/domains/sale_invoice_print_audit_boundary_20260829.json",
 "runtime_boundary":"artifacts/varanegar_analysis/domains/sale_invoice_print_runtime_boundary_20260829.json",
 "report_gaps":"artifacts/varanegar_analysis/ui/varanegar_report_evidence_gaps_20260827.json",
 "report_contracts":"artifacts/varanegar_analysis/ui/varanegar_report_target_contracts_golden_cases_20260827.json",
 "sale_cancel":"artifacts/varanegar_analysis/domains/sale_cancellation_boundary_20260829.json",
 "previous_checkpoint":"artifacts/varanegar_analysis/varanegar_sale_accounting_crosswalk_checkpoint_20260829.json",
 "risk_register":"artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
 "traceability":"artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
 "sql_extractor":"scripts/sql/extract_varanegar_sale_invoice_print_audit_boundary.py",
 "runtime_extractor":"scripts/sql/extract_varanegar_sale_invoice_print_runtime_boundary.py",
 "risk_builder":"scripts/windows/build_negin_erp_risk_register.py",
 "rebuild_script":"scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
 "checkpoint_builder":"scripts/windows/build_varanegar_sale_invoice_print_checkpoint_20260829.py",
 "tests":"tests/test_varanegar_sale_invoice_print_boundary.py",
 "domain_doc":"docs/varanegar_reconstruction/SALE_INVOICE_CRYSTAL_TEMPLATE_AND_PRINT_AUDIT_BOUNDARY_20260829_FA.md",
 "knowledge_doc":"docs/VARANEGAR_KNOWLEDGE_FA.md","discovery_log":"docs/varanegar_reconstruction/DISCOVERY_LOG_FA.md","readme":"docs/varanegar_reconstruction/README_FA.md",
}
def _load(n):return json.loads((ROOT/SOURCES[n]).read_text(encoding="utf-8-sig"))
def _sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 missing=[p for p in SOURCES.values() if not (ROOT/p).is_file()]
 if missing:raise AssertionError({"missing_sources":missing})
 sql,runtime,previous,risks,trace=(_load(x) for x in("sql_boundary","runtime_boundary","previous_checkpoint","risk_register","traceability"));static=sql["static_print_sql_contract"];managed=runtime["managed_invoice_print_contract"];r=next(x for x in risks["risks"] if x["id"]=="R-084");raw=(ROOT/SOURCES["sql_boundary"]).read_text(encoding="utf-8");s=sql["summary"];x=sql["sale_print_after_current_terminal_cancel_time"]
 checks={"read_only_redacted":sql["validation"]=="PASS" and sql["safety"]["database_updateability"]=="READ_ONLY" and sql["safety"]["can_update"]==0 and sql["safety"]["report_procedure_view_form_print_or_application_command_executions"]==0 and sql["safety"]["report_sale_customer_user_host_template_name_or_raw_values_persisted"]==0,
 "sql_hash_and_contract":s["selected_sql_module_count"]==2 and all(len(y["definition_sha256"])==64 for y in sql["sql_module_profiles"]) and all(static.values()),
 "template_boundary":sql["report_template_inventory"]["configured_template_count"]==6 and sql["report_template_inventory"]["configured_default_count"]==1 and sql["report_template_inventory"]["scanned_template_file_count"]==88 and sql["report_template_inventory"]["configured_template_deployment_match_count"]==0,
 "runtime_hash_pinned":runtime["validation"]=="PASS" and runtime["summary"]["assembly_count"]==3 and runtime["summary"]["selected_method_count"]==9 and runtime["summary"]["selected_instruction_count"]==1011 and runtime["summary"]["source_hash_mismatch_count"]==0 and runtime["safety"]["assembly_loads_or_executions"]==0,
 "runtime_query_command_boundary":managed["ui_resolves_configured_report_filename"] and managed["single_print_calls_report_then_marks_only_after_printed_completed"] and managed["collection_print_calls_report_then_marks_only_after_printed_completed"] and managed["report_engine_loads_crystal_template_and_sets_parameters"] and managed["report_engine_refresh_applies_current_connection_to_report_tables"] and managed["report_engine_supports_custom_override_when_file_exists"] and managed["print_completion_builds_type2_audit_rows"] and managed["print_completion_uses_context_save_then_commit"] and managed["print_completion_has_no_explicit_rollback"] and not managed["template_embedded_query_identity_and_result_parity_proven"],
 "print_event_history":s["print_event_count"]==816321 and s["printed_document_key_count"]==197586 and s["sale_print_event_count"]==308432 and s["sale_printed_document_count"]==144847 and s["repeated_sale_printed_document_count"]==34840 and s["maximum_sale_prints_per_document"]==26 and s["sale_printed_absent_current_sale_count"]==68,
 "post_cancel_is_caveated":x["print_event_count"]==143 and x["document_count"]==45 and x["after_day_count"]==101 and x["recent_print_event_count"]==2,
 "previous_chain":previous["validation"]=="PASS" and previous["summary"]["risk_count"]==84,
 "risk_caveat":r["severity"]=="CRITICAL" and "does not prove a runtime load failure" in r["failure_mode"] and "must not be called unauthorized" in r["failure_mode"] and "capability only" in r["failure_mode"],
 "register_trace":risks["summary"]["risk_count"]==84 and risks["summary"]["critical_count"]==50 and risks["summary"]["high_count"]==31 and trace["summary"]["unique_risk_count"]==84 and trace["summary"]["mapped_risk_assignment_count"]==343 and trace["summary"]["command_ready_module_count"]==0,
 "no_uuid_secret":re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b",raw)is None and re.search(r"(?i)(password|pwd)\s*[=:]",raw)is None}
 failed=sorted(k for k,v in checks.items() if not v);manifest=[{"name":n,"path":p,"size_bytes":(ROOT/p).stat().st_size,"sha256":_sha(ROOT/p)} for n,p in sorted(SOURCES.items())]
 return {"artifact":"varanegar_sale_invoice_print_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","safety":{"mode":"OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE","database_connections":0,"network_reads_or_writes":0,"live_ui_actions":0,"assemblies_loaded_or_executed":0,"operational_commands_executed":0,"report_template_sale_customer_user_host_error_or_raw_values_read":0},"source_manifest":manifest,"checks":checks,"failed_checks":failed,"summary":{"source_count":len(manifest),"passed_check_count":sum(checks.values()),"failed_check_count":len(failed),"configured_template_count":s["configured_template_count"],"configured_template_deployment_match_count":s["configured_template_deployment_match_count"],"sale_print_event_count":s["sale_print_event_count"],"sale_printed_document_count":s["sale_printed_document_count"],"post_terminal_cancel_sale_print_event_count":s["post_terminal_cancel_sale_print_event_count"],"risk_count":risks["summary"]["risk_count"],"mapped_risk_assignment_count":trace["summary"]["mapped_risk_assignment_count"]}}
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();x=build();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(x["validation"]);print(json.dumps(x["summary"],ensure_ascii=False));return 0 if x["validation"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
