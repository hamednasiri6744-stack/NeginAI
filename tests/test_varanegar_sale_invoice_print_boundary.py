import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SQL=ROOT/"artifacts/varanegar_analysis/domains/sale_invoice_print_audit_boundary_20260829.json"
RUNTIME=ROOT/"artifacts/varanegar_analysis/domains/sale_invoice_print_runtime_boundary_20260829.json"
RISKS=ROOT/"artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json"
TRACE=ROOT/"artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json"
CHECKPOINT=ROOT/"artifacts/varanegar_analysis/varanegar_sale_invoice_print_checkpoint_20260829.json"

def _load(path):return json.loads(path.read_text(encoding="utf-8-sig"))

def test_sql_and_deployment_evidence_is_read_only_redacted_and_hash_pinned():
 p=_load(SQL);assert p["validation"]=="PASS"
 assert p["safety"]["database_updateability"]=="READ_ONLY" and p["safety"]["can_update"]==0
 assert p["safety"]["report_procedure_view_form_print_or_application_command_executions"]==0
 assert p["safety"]["assemblies_loaded_or_executed"]==0
 assert p["safety"]["report_sale_customer_user_host_template_name_or_raw_values_persisted"]==0
 assert len(p["sql_module_profiles"])==2 and all(len(x["definition_sha256"])==64 for x in p["sql_module_profiles"])
 raw=SQL.read_text(encoding="utf-8");assert re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b",raw) is None
 assert re.search(r"(?i)(password|pwd)\s*[=:]",raw) is None

def test_configured_template_content_is_outside_scanned_deployment_boundary():
 p=_load(SQL)["report_template_inventory"]
 assert p["configured_template_count"]==6 and p["configured_default_count"]==1
 assert p["configured_distinct_filename_hash_count"]==6
 assert p["scanned_template_file_count"]==88
 assert p["configured_template_deployment_match_count"]==0
 assert p["scanned_file_names_or_paths_persisted"]==0
 assert all(x["extension"]==".rpt" and not x["matched_in_scanned_deployment_roots"] and not x["raw_name_persisted"] for x in p["configured_templates"])

def test_runtime_loads_crystal_and_separates_successful_print_from_audit_command():
 p=_load(RUNTIME);assert p["validation"]=="PASS"
 assert p["summary"]=={"assembly_count":3,"selected_method_count":9,"selected_instruction_count":1011,"source_hash_mismatch_count":0,"method_or_coverage_error_count":0}
 assert all(x["inventory_sha256_match"] for x in p["source"])
 c=p["managed_invoice_print_contract"]
 assert c["ui_resolves_configured_report_filename"]
 assert c["single_print_calls_report_then_marks_only_after_printed_completed"]
 assert c["collection_print_calls_report_then_marks_only_after_printed_completed"]
 assert c["report_engine_loads_crystal_template_and_sets_parameters"]
 assert c["report_engine_refresh_applies_current_connection_to_report_tables"]
 assert c["report_engine_supports_custom_override_when_file_exists"]
 assert c["print_completion_builds_type2_audit_rows"] and c["print_completion_uses_context_save_then_commit"]
 assert c["print_completion_has_no_explicit_rollback"]
 assert not c["template_embedded_query_identity_and_result_parity_proven"]

def test_print_audit_is_event_history_not_unique_document_state():
 s=_load(SQL)["summary"]
 assert s["print_event_count"]==816321 and s["printed_document_key_count"]==197586
 assert s["repeated_printed_document_key_count"]==55792 and s["maximum_prints_per_document"]==88
 assert s["sale_print_event_count"]==308432 and s["sale_printed_document_count"]==144847
 assert s["repeated_sale_printed_document_count"]==34840 and s["maximum_sale_prints_per_document"]==26
 assert s["sale_printed_absent_current_sale_count"]==68

def test_post_cancel_print_ordering_is_measured_without_incident_attribution():
 p=_load(SQL);x=p["sale_print_after_current_terminal_cancel_time"]
 assert x["print_event_count"]==143 and x["document_count"]==45
 assert x["within_five_minutes_count"]==5 and x["after_five_minutes_within_day_count"]==37
 assert x["after_day_count"]==101 and x["recent_print_event_count"]==2
 assert any("archive copy" in y for y in p["evidence_limits"])

def test_legacy_sql_anomalies_are_capability_only_and_not_active_attribution():
 p=_load(SQL);assert all(p["static_print_sql_contract"].values())
 assert p["exact_alternate_procedure_literal_hit_count"]==0
 assert any("capability only" in x for x in p["evidence_limits"])

def test_r084_and_checkpoint_are_current_and_caveated():
 risks,trace,checkpoint=_load(RISKS),_load(TRACE),_load(CHECKPOINT)
 assert risks["summary"]["risk_count"]==84 and risks["summary"]["critical_count"]==50
 assert risks["summary"]["high_count"]==31 and risks["summary"]["open_count"]==84
 r=next(x for x in risks["risks"] if x["id"]=="R-084");assert r["severity"]=="CRITICAL"
 assert "does not prove a runtime load failure" in r["failure_mode"]
 assert "must not be called unauthorized" in r["failure_mode"]
 assert "capability only" in r["failure_mode"]
 assert trace["summary"]["unique_risk_count"]==84 and trace["summary"]["mapped_risk_assignment_count"]==343
 assert trace["summary"]["command_ready_module_count"]==0
 assert checkpoint["validation"]=="PASS" and checkpoint["failed_checks"]==[]
 assert checkpoint["summary"]["risk_count"]==84 and checkpoint["summary"]["mapped_risk_assignment_count"]==343
