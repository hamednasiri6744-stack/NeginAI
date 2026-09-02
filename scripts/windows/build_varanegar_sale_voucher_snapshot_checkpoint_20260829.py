"""Build the offline sale-voucher snapshot and reverse-conversion checkpoint."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
 "sql_boundary":"artifacts/varanegar_analysis/domains/sale_voucher_snapshot_boundary_20260829.json",
 "runtime_boundary":"artifacts/varanegar_analysis/domains/sale_voucher_snapshot_runtime_boundary_20260829.json",
 "sale_domain":"artifacts/varanegar_analysis/domains/order_sale_lifecycle_20260826.json",
 "previous_checkpoint":"artifacts/varanegar_analysis/varanegar_return_issue_cancel_checkpoint_20260829.json",
 "risk_register":"artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
 "traceability":"artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
 "sql_extractor":"scripts/sql/extract_varanegar_sale_voucher_snapshot_boundary.py",
 "runtime_extractor":"scripts/sql/extract_varanegar_sale_voucher_snapshot_runtime_boundary.py",
 "risk_builder":"scripts/windows/build_negin_erp_risk_register.py",
 "rebuild_script":"scripts/windows/rebuild_negin_erp_risk_and_traceability.ps1",
 "checkpoint_builder":"scripts/windows/build_varanegar_sale_voucher_snapshot_checkpoint_20260829.py",
 "tests":"tests/test_varanegar_sale_voucher_snapshot_boundary.py",
 "domain_doc":"docs/varanegar_reconstruction/SALE_VOUCHER_SNAPSHOT_AND_REVERSE_CONVERSION_BOUNDARY_20260829_FA.md",
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
    static,managed=sql["static_snapshot_contract"],runtime["managed_snapshot_conversion_contract"]
    r082=next(x for x in risks["risks"] if x["id"]=="R-082")
    raw=(ROOT/SOURCES["sql_boundary"]).read_text(encoding="utf-8")
    integrity=sql["current_sale_voucher_state"]["snapshot_integrity"]
    coverage=sql["generic_snapshot_log_lifecycle"]["logged_id_coverage"]
    checks={
      "sql_read_only_redacted":sql["validation"]=="PASS" and sql["safety"]["database_updateability"]=="READ_ONLY" and sql["safety"]["can_update"]==0 and sql["safety"]["stored_procedure_trigger_form_or_application_command_executions"]==0 and sql["safety"]["sale_order_snapshot_customer_user_host_or_raw_values_persisted"]==0,
      "sql_hash_coverage":sql["summary"]["selected_sql_module_count"]==6 and all(len(x["definition_sha256"])==64 for x in sql["sql_module_profiles"]),
      "snapshot_static_contract":all(static.values()),
      "current_snapshot_reconciliation":sql["summary"]["sale_with_voucher_number_count"]==266183 and sql["summary"]["sale_with_snapshot_count"]==266183 and sql["summary"]["voucher_number_or_snapshot_mismatch_count"]==0 and integrity["orphan_snapshot_count"]==0 and integrity["duplicate_sale_snapshot_group_count"]==0 and integrity["orphan_snapshot_item_count"]==0,
      "stage_difference_is_measured":sql["summary"]["cancelled_sale_with_snapshot_count"]==60698 and sql["summary"]["snapshot_amount_diff_count"]==11750 and sql["summary"]["recent_snapshot_amount_diff_count"]==1537,
      "audit_absence_is_historical":coverage["absent_count"]==18 and coverage["recent_absent_count"]==0 and sql["summary"]["retained_snapshot_delete_count"]==0 and sql["summary"]["direct_snapshot_delete_candidate_count"]==1,
      "runtime_hash_pinned":runtime["validation"]=="PASS" and runtime["summary"]["assembly_count"]==3 and runtime["summary"]["selected_method_count"]==4 and runtime["summary"]["selected_instruction_count"]==243 and runtime["summary"]["source_hash_mismatch_count"]==0 and runtime["safety"]["assembly_loads_or_executions"]==0,
      "runtime_route":managed["ui_calls_business_without_explicit_context_commit_or_rollback"] and managed["business_constructs_context_validates_then_calls_adapter"] and not managed["business_has_explicit_commit"] and not managed["business_has_explicit_rollback"] and managed["adapter_uses_named_conversion_procedure"] and managed["adapter_queries_or_executes"] and managed["adapter_has_explicit_context"] and not managed["adapter_has_explicit_commit"] and not managed["adapter_has_explicit_rollback"] and not managed["managed_to_sql_physical_transaction_enlistment_proven"],
      "previous_chain":previous["validation"]=="PASS" and previous["summary"]["risk_count"]==84,
      "r082_caveated":r082["severity"]=="CRITICAL" and "must not be called corruption" in r082["failure_mode"] and "capability only" in r082["failure_mode"],
      "register_trace":risks["summary"]["risk_count"]==84 and risks["summary"]["critical_count"]==50 and risks["summary"]["high_count"]==31 and trace["summary"]["unique_risk_count"]==84 and trace["summary"]["mapped_risk_assignment_count"]==343 and trace["summary"]["command_ready_module_count"]==0,
      "no_uuid_secret":re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",raw) is None and re.search(r"(?i)(password|pwd)\s*[=:]",raw) is None,
    }
    failed=sorted(k for k,v in checks.items() if not v)
    manifest=[{"name":n,"path":p,"size_bytes":(ROOT/p).stat().st_size,"sha256":_sha(ROOT/p)} for n,p in sorted(SOURCES.items())]
    return {"artifact":"varanegar_sale_voucher_snapshot_checkpoint_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL",
            "safety":{"mode":"OFFLINE_FROM_REDACTED_HASH_PINNED_EVIDENCE","database_connections":0,"network_reads_or_writes":0,"live_ui_actions":0,"assemblies_loaded_or_executed":0,"operational_commands_executed":0,"sale_order_snapshot_customer_user_host_error_or_raw_values_read":0},
            "source_manifest":manifest,"checks":checks,"failed_checks":failed,
            "summary":{"source_count":len(manifest),"passed_check_count":sum(checks.values()),"failed_check_count":len(failed),"selected_sql_module_count":sql["summary"]["selected_sql_module_count"],"selected_runtime_method_count":runtime["summary"]["selected_method_count"],"sale_with_snapshot_count":sql["summary"]["sale_with_snapshot_count"],"cancelled_sale_with_snapshot_count":sql["summary"]["cancelled_sale_with_snapshot_count"],"snapshot_amount_diff_count":sql["summary"]["snapshot_amount_diff_count"],"recent_snapshot_amount_diff_count":sql["summary"]["recent_snapshot_amount_diff_count"],"risk_count":risks["summary"]["risk_count"],"mapped_risk_assignment_count":trace["summary"]["mapped_risk_assignment_count"]}}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();x=build();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(x["validation"]);print(json.dumps(x["summary"],ensure_ascii=False));return 0 if x["validation"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
