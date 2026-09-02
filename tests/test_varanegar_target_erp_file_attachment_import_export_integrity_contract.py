import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_file_attachment_import_export_integrity_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_file_attachment_import_export_integrity_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"file_integrity.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["file_integrity_dimension_count"],s["module_dimension_assignment_count"])==(14,14,196);assert(s["lifecycle_stage_count"],s["module_stage_assignment_count"])==(12,168);assert(s["file_manifest_field_count"],s["scan_receipt_field_count"],s["quarantine_receipt_field_count"],s["disposition_receipt_field_count"])==(22,22,20,20);assert(s["failure_case_count"],s["module_failure_assignment_count"])==(16,224);assert(s["gate_count"],s["module_gate_assignment_count"])==(22,308);assert(s["role_type_count"],s["module_role_assignment_count"],s["typed_outcome_count"])==(7,98,12)
def test_every_module_has_full_coverage():
 d=load();ids={x["module_id"] for x in d["module_file_plans"]};assert len(ids)==14
 for i in ids:
  assert len({x["file_dimension"] for x in d["module_dimension_assignments"] if x["module_id"]==i})==14;assert len({x["stage_id"] for x in d["module_stage_assignments"] if x["module_id"]==i})==12;assert len({x["failure_case_id"] for x in d["module_failure_assignments"] if x["module_id"]==i})==16;assert len({x["gate_id"] for x in d["module_gate_assignments"] if x["module_id"]==i})==22;assert len({x["role_type"] for x in d["module_role_assignments"] if x["module_id"]==i})==7
def test_rules_fail_closed():
 r=load()["file_integrity_rule"]
 for f in ("extension_or declared_media_type_is_trusted_without sniffing","path_traversal_absolute_reserved_symlink_or canonical_collision_allowed","archive_recursion_zip_slip_or compression_bomb_allowed","unbounded_count_size_entry_ratio_parser_or resource_limit_allowed","scanner_error_timeout_unknown_or stale_signature_is_clean","quarantined_file_may_be_previewed_downloaded_exported_or parsed","sanitized_derivative_may_overwrite_or lose_original_lineage","raw_file_body_pii_secret_payment_or payload_may_be_persisted_as evidence","download_or signed_url_may_omit scope_authorization_ttl_or revocation","csv_formula_spreadsheet_active_content_export_injection_allowed","retention_legal_hold_deletion_or tombstone_may_be_bypassed","automatic_file_release_download_export_disposition_or readiness"):assert r[f] is False
def test_no_runtime_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_file_attachment_import_export_or_body_read_count","scanner_parser_storage_or_dlp_provider_selected_count","file_scan_or_parser_run_count","quarantine_release_or_download_run_count","export_or_disposition_run_count","owner_approved_module_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_file_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
