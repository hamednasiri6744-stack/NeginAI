"""Build a design-only evidence/logging redaction and retention contract."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCES={
 "blueprint":"artifacts/varanegar_analysis/ui/negin_personal_erp_blueprint_20260827.json",
 "authorization":"artifacts/varanegar_analysis/varanegar_target_erp_command_authorization_scope_decision_trace_contract_20260829.json",
 "authorization_checkpoint":"artifacts/varanegar_analysis/varanegar_target_erp_command_authorization_scope_decision_trace_checkpoint_20260829.json",
 "capture_redaction":"artifacts/varanegar_analysis/varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829.json",
 "custody":"artifacts/varanegar_analysis/varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract_20260829.json",
 "tests":"artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
 "risk":"artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
 "trace":"artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}
EVIDENCE_CHANNELS=[
 "COMMAND_AUDIT_AND_OUTCOME_RECEIPT","AUTHORIZATION_DECISION_TRACE","TRANSACTION_SAGA_AND_COMPENSATION_RECEIPT",
 "IDEMPOTENCY_OUTBOX_AND_INBOX_METADATA","ERROR_INCIDENT_AND_SUPPORT_DIAGNOSTIC","REPORT_EXPORT_PRINT_AND_FILE_METADATA",
 "RECOVERY_BACKUP_AND_RESTORE_EVIDENCE","MIGRATION_IMPORT_AND_RECONCILIATION_EVIDENCE","SECURITY_ACCESS_AND_POLICY_CHANGE_AUDIT",
 "OBSERVABILITY_METRIC_TRACE_AND_HEALTH_SIGNAL",
]
PROHIBITED_DATA_CLASSES=[
 "CREDENTIAL_SECRET_OR_CONNECTION_STRING","AUTH_TOKEN_SESSION_COOKIE_OR_API_KEY","IDENTITY_PII_OR_CONTACT_DETAIL",
 "CUSTOMER_SUPPLIER_EMPLOYEE_OR_DRIVER_RAW_IDENTIFIER","PRICE_DISCOUNT_COST_AMOUNT_OR_COMMERCIAL_TERM_RAW_VALUE",
 "BANK_CARD_CHEQUE_ACCOUNT_OR_PAYMENT_INSTRUMENT_RAW_VALUE","ROW_ITEM_ENTITY_OR_DOCUMENT_PAYLOAD",
 "REQUEST_RESPONSE_FORM_OR_REPORT_BODY","SQL_PROCEDURE_RULE_SCRIPT_OR_EXECUTABLE_CONFIGURATION_TEXT",
 "FILE_SCREENSHOT_DOCUMENT_TEMPLATE_OR_BINARY_CONTENT","ENDPOINT_HOST_PATH_SHARE_OR_NETWORK_LOCATION",
 "PRIVATE_PUBLIC_KEY_SIGNATURE_OR_CRYPTOGRAPHIC_MATERIAL","UNSANITIZED_STACK_TRACE_EXCEPTION_ARGUMENT_OR_MEMORY_DUMP",
 "BACKUP_DATABASE_LOG_QUEUE_MESSAGE_OR_EXPORT_RAW_CONTENT",
]
ALLOWED_EVIDENCE_CLASSES=[
 "DOMAIN_SEPARATED_SHA256","OPAQUE_NON_REVERSIBLE_REFERENCE","AGGREGATE_COUNT","ENUMERATED_STATUS_OR_REASON_CODE",
 "VERSION_POLICY_OR_SCHEMA_HASH","TIME_BOUNDARY_WITHOUT_BUSINESS_VALUE","ROLE_TYPE_WITHOUT_IDENTITY","BOOLEAN_GATE_OR_ATTESTATION",
]
REDACTION_ATTESTATION_FIELDS=[
 "attestation_id","evidence_channel","producer_component_reference_sha256","policy_version_sha256","schema_version_sha256",
 "input_class_set_sha256","prohibited_class_scan_result_sha256","allowed_field_set_sha256","redaction_rule_set_sha256",
 "domain_separation_context_sha256","output_manifest_sha256","output_byte_count","output_record_count","scan_started_at",
 "scan_completed_at","typed_outcome","producer_role_receipt_reference","independent_reviewer_receipt_reference",
 "supersedes_attestation_sha256","attestation_sha256",
]
RETENTION_FIELDS=[
 "retention_policy_version_sha256","evidence_channel","classification","valid_from","expires_at","maximum_retention_duration_seconds",
 "legal_hold_reference_sha256","revocation_reference_sha256","supersession_reference_sha256","disposition_due_at",
 "disposition_status","hash_only_tombstone_sha256","lineage_reference_set_sha256","owner_role_receipt_reference",
 "independent_review_receipt_reference","retention_record_sha256",
]
NEGATIVE_VECTORS=[
 ("RLN-01","credential_or_connection_string_key_detected"),("RLN-02","token_cookie_or_authorization_header_detected"),
 ("RLN-03","identity_pii_or_contact_field_detected"),("RLN-04","customer_supplier_or_employee_identifier_detected"),
 ("RLN-05","commercial_amount_price_discount_or_cost_detected"),("RLN-06","bank_cheque_card_or_payment_value_detected"),
 ("RLN-07","row_item_document_or_request_body_detected"),("RLN-08","sql_rule_script_or_executable_text_detected"),
 ("RLN-09","file_screenshot_template_or_binary_content_detected"),("RLN-10","endpoint_host_path_share_or_network_location_detected"),
 ("RLN-11","key_signature_or_crypto_material_detected"),("RLN-12","unsanitized_exception_stack_argument_or_dump_detected"),
 ("RLN-13","backup_database_log_queue_or_export_content_detected"),("RLN-14","unknown_unclassified_field_or_nested_payload_detected"),
]
GATES=[
 ("RLG-01","channel_schema_and_allowed_field_allowlist_versioned"),("RLG-02","default_deny_for_unknown_field_or_nested_payload"),
 ("RLG-03","all_prohibited_data_class_scanners_pass"),("RLG-04","hashes_are_domain_separated_and_non_reversible"),
 ("RLG-05","opaque_references_are_not_raw_business_identifiers"),("RLG-06","exception_and_stack_trace_sanitizer_passes"),
 ("RLG-07","structured_logging_prevents_string_concatenation_of_payloads"),("RLG-08","metric_labels_have_bounded_non_sensitive_cardinality"),
 ("RLG-09","trace_baggage_headers_and_context_are_allowlisted"),("RLG-10","export_file_backup_and_message_body_capture_disabled"),
 ("RLG-11","retention_expiry_revocation_supersession_and_disposition_enforced"),("RLG-12","hash_only_tombstone_preserves_lineage_without_payload"),
 ("RLG-13","producer_and_independent_reviewer_are_separated"),("RLG-14","negative_vectors_pass_in_build_and_release_pipeline"),
 ("RLG-15","runtime_sample_scan_and_incident_route_accepted"),("RLG-16","security_privacy_and_business_owner_receipts_current"),
]
ROLE_TYPES=["EVIDENCE_SCHEMA_OWNER_ROLE","SECURITY_REDACTION_REVIEWER_ROLE","PRIVACY_RETENTION_OWNER_ROLE","BUSINESS_DATA_OWNER_ROLE","INDEPENDENT_RELEASE_APPROVER_ROLE"]
TYPED_OUTCOMES=["ALLOWLISTED_HASH_ONLY_EVIDENCE_ACCEPTED","PROHIBITED_CLASS_DETECTED_REJECTED","UNKNOWN_FIELD_OR_NESTED_PAYLOAD_REJECTED","UNSANITIZED_EXCEPTION_REJECTED","UNBOUNDED_OR_SENSITIVE_METRIC_LABEL_REJECTED","RETENTION_OR_EXPIRY_POLICY_MISMATCH","REVOKED_OR_SUPERSEDED_EVIDENCE_REJECTED","DISPOSITION_OR_TOMBSTONE_UNPROVEN","REVIEW_OR_SOD_RECEIPT_MISSING","POLICY_SCHEMA_OR_SCANNER_VERSION_MISMATCH"]
def load(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args();paths={k:ROOT/v for k,v in SOURCES.items()};d={k:load(v) for k,v in paths.items()};modules=d["blueprint"]["modules"]
 commands=[]
 for m in modules:
  for name in m["commands"]:commands.append({"target_command_id":f"TCMD-{len(commands)+1:03d}","module_id":m["id"],"command_name":name,"evidence_logging_policy_status":"DESIGNED_NOT_IMPLEMENTED","runtime_redaction_status":"UNPROVEN","command_readiness":False})
 channel_data=[{"evidence_channel":c,"prohibited_data_class":x,"policy":"DENY_PERSIST_FAIL_CLOSED","runtime_scan_status":"UNPROVEN"} for c in EVIDENCE_CHANNELS for x in PROHIBITED_DATA_CLASSES]
 command_channels=[{"target_command_id":x["target_command_id"],"evidence_channel":c,"status":"DESIGNED_NOT_IMPLEMENTED","accepted_attestation_count":0} for x in commands for c in EVIDENCE_CHANNELS]
 negatives=[{"evidence_channel":c,"negative_vector_id":i,"status":"UNEXECUTED","accepted_result_count":0} for c in EVIDENCE_CHANNELS for i,_ in NEGATIVE_VECTORS]
 gates=[{"evidence_channel":c,"gate_id":i,"status":"UNMET","accepted_evidence_count":0} for c in EVIDENCE_CHANNELS for i,_ in GATES]
 roles=[{"evidence_channel":c,"role_type":r,"status":"UNASSIGNED","role_receipt_reference":None} for c in EVIDENCE_CHANNELS for r in ROLE_TYPES]
 o=d["tests"];s={"module_count":len(modules),"target_command_count":len(commands),"evidence_channel_count":len(EVIDENCE_CHANNELS),"prohibited_data_class_count":len(PROHIBITED_DATA_CLASSES),"channel_prohibited_class_assignment_count":len(channel_data),"allowed_evidence_class_count":len(ALLOWED_EVIDENCE_CLASSES),"command_channel_assignment_count":len(command_channels),"redaction_attestation_field_count":len(REDACTION_ATTESTATION_FIELDS),"retention_field_count":len(RETENTION_FIELDS),"negative_vector_count":len(NEGATIVE_VECTORS),"channel_negative_vector_assignment_count":len(negatives),"gate_count":len(GATES),"channel_gate_assignment_count":len(gates),"role_type_count":len(ROLE_TYPES),"channel_role_assignment_count":len(roles),"typed_outcome_count":len(TYPED_OUTCOMES),"implemented_channel_count":0,"runtime_sample_scan_count":0,"accepted_redaction_attestation_count":0,"retention_policy_approved_channel_count":0,"disposition_proven_channel_count":0,"incident_closed_count":0,"owner_approved_channel_count":0,"command_ready_count":0,"pilot_ready_module_count":0,"design_lower_bound_before_redaction_contract":1404,"design_lower_bound_after_redaction_contract":1404,"official_test_file_count":o["runner"]["test_file_count"],"official_passed_test_count":o["runner"]["passed_test_count"],"risk_count":d["risk"]["summary"]["risk_count"],"mapped_risk_assignment_count":d["trace"]["summary"]["mapped_risk_assignment_count"],"new_risk_count":0}
 checks={"sources_pass":all(d[k].get("validation")=="PASS" for k in ("authorization","authorization_checkpoint","capture_redaction","custody","tests")),"coverage_14_modules_49_commands_10_channels":(s["module_count"],s["target_command_count"],s["evidence_channel_count"])==(14,49,10),"prohibited_14_assignments_140_allowed_8":(s["prohibited_data_class_count"],s["channel_prohibited_class_assignment_count"],s["allowed_evidence_class_count"])==(14,140,8),"command_channel_assignments_490":s["command_channel_assignment_count"]==490,"fields_20_16":(s["redaction_attestation_field_count"],s["retention_field_count"])==(20,16),"negative_14_assignments_140":(s["negative_vector_count"],s["channel_negative_vector_assignment_count"])==(14,140),"gates_16_assignments_160":(s["gate_count"],s["channel_gate_assignment_count"])==(16,160),"roles_5_assignments_50_outcomes_10":(s["role_type_count"],s["channel_role_assignment_count"],s["typed_outcome_count"])==(5,50,10),"all_runtime_negative_gate_role_states_open":all(x["runtime_scan_status"]=="UNPROVEN" for x in channel_data) and all(x["status"]=="UNEXECUTED" for x in negatives) and all(x["status"]=="UNMET" for x in gates) and all(x["status"]=="UNASSIGNED" for x in roles),"implementation_scan_attestation_retention_readiness_zero":s["implemented_channel_count"]==s["runtime_sample_scan_count"]==s["accepted_redaction_attestation_count"]==s["retention_policy_approved_channel_count"]==s["disposition_proven_channel_count"]==s["incident_closed_count"]==s["owner_approved_channel_count"]==s["command_ready_count"]==s["pilot_ready_module_count"]==0,"non_additive_1404":s["design_lower_bound_before_redaction_contract"]==s["design_lower_bound_after_redaction_contract"]==1404,"official_tests_pass":o["validation"]=="PASS" and o["runner"]["bootstrap_excluded_test_file_count"]==0,"base_stable":s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343};failed=sorted(k for k,v in checks.items() if not v)
 out={"artifact":"varanegar_target_erp_evidence_logging_redaction_retention_contract_20260829","schema_version":1,"generated_at":datetime.now().astimezone().isoformat(),"validation":"PASS" if not failed else "FAIL","scope":{"mode":"target_evidence_logging_redaction_retention_design_only","continuation_complete":False,"logging_scanner_or_retention_runtime_executed":False,"provider_or_storage_selected":False},"safety":{"database_connections":0,"network_reads_or_writes":0,"logs_traces_backups_messages_exports_or_runtime_samples_read":0,"scanners_disposition_or_incident_actions_executed":0,"operational_forms_reports_queries_or_procedures_executed":0,"assemblies_loaded_or_executed":0,"data_mutations":0,"credentials_tokens_identity_pii_or_raw_business_values_read_or_persisted":0},"summary":s,"risk_links":["R-004","R-001","R-003","R-019","R-023","R-025"],"evidence_channels":EVIDENCE_CHANNELS,"prohibited_data_classes":PROHIBITED_DATA_CLASSES,"allowed_evidence_classes":ALLOWED_EVIDENCE_CLASSES,"redaction_attestation_fields":REDACTION_ATTESTATION_FIELDS,"retention_fields":RETENTION_FIELDS,"negative_vectors":[{"negative_vector_id":i,"negative_vector":v} for i,v in NEGATIVE_VECTORS],"gates":[{"gate_id":i,"gate":v,"failure_effect":"EVIDENCE_REJECTED_AND_RELEASE_BLOCKED"} for i,v in GATES],"role_types":ROLE_TYPES,"typed_outcomes":TYPED_OUTCOMES,"target_command_evidence_contracts":commands,"channel_prohibited_class_assignments":channel_data,"command_channel_assignments":command_channels,"channel_negative_vector_assignments":negatives,"channel_gate_assignments":gates,"channel_role_assignments":roles,"redaction_and_retention_rule":{"unknown_field_or_nested_payload_default_allowed":False,"raw_payload_exception_stack_file_backup_message_or_export_body_persistence_allowed":False,"hash_without_domain_separation_allowed":False,"opaque_reference_may_equal_business_identifier":False,"sensitive_or_unbounded_metric_label_allowed":False,"retention_expiry_automatically_extends":False,"revoked_or_superseded_evidence_remains_acceptable":False,"disposition_may_remove_lineage_tombstone":False,"scanner_or_schema_failure_allows_evidence_emission":False,"automatic_evidence_or_readiness_acceptance":False},"checks":checks,"failed_checks":failed,"source_manifest":[{"name":k,"path":SOURCES[k],"size_bytes":v.stat().st_size,"sha256":sha(v)} for k,v in sorted(paths.items())]+[{"name":"builder","path":"scripts/windows/build_varanegar_target_erp_evidence_logging_redaction_retention_contract_20260829.py","size_bytes":Path(__file__).stat().st_size,"sha256":sha(Path(__file__))}],"limits":["This is a data-minimization and evidence-schema design contract, not a runtime scanner or logging implementation.","No log trace backup message export file database identity secret PII or business value was read or persisted.","Every channel remains blocked until negative scans retention disposition and independent review receipts are accepted."]}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(a.output.resolve());print(out["validation"]);print(json.dumps(s,ensure_ascii=False));return 0 if not failed else 1
if __name__=="__main__":raise SystemExit(main())
