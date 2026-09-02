import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_evidence_logging_redaction_retention_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_evidence_logging_redaction_retention_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"redaction.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_totals():
 s=load()["summary"];assert(s["module_count"],s["target_command_count"],s["evidence_channel_count"])==(14,49,10);assert(s["prohibited_data_class_count"],s["channel_prohibited_class_assignment_count"],s["allowed_evidence_class_count"])==(14,140,8);assert s["command_channel_assignment_count"]==490;assert(s["redaction_attestation_field_count"],s["retention_field_count"])==(20,16);assert(s["negative_vector_count"],s["channel_negative_vector_assignment_count"])==(14,140);assert(s["gate_count"],s["channel_gate_assignment_count"])==(16,160);assert(s["role_type_count"],s["channel_role_assignment_count"],s["typed_outcome_count"])==(5,50,10)
def test_every_channel_has_prohibited_negative_gate_and_role_coverage():
 d=load();channels=set(d["evidence_channels"])
 for c in channels:
  assert len({x["prohibited_data_class"] for x in d["channel_prohibited_class_assignments"] if x["evidence_channel"]==c})==14
  assert len({x["negative_vector_id"] for x in d["channel_negative_vector_assignments"] if x["evidence_channel"]==c})==14
  assert len({x["gate_id"] for x in d["channel_gate_assignments"] if x["evidence_channel"]==c})==16
  assert len({x["role_type"] for x in d["channel_role_assignments"] if x["evidence_channel"]==c})==5
def test_rules_fail_closed():
 r=load()["redaction_and_retention_rule"]
 for f in ("unknown_field_or_nested_payload_default_allowed","raw_payload_exception_stack_file_backup_message_or_export_body_persistence_allowed","hash_without_domain_separation_allowed","opaque_reference_may_equal_business_identifier","sensitive_or_unbounded_metric_label_allowed","retention_expiry_automatically_extends","revoked_or_superseded_evidence_remains_acceptable","disposition_may_remove_lineage_tombstone","scanner_or_schema_failure_allows_evidence_emission","automatic_evidence_or_readiness_acceptance"):assert r[f] is False
def test_no_runtime_scan_retention_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("implemented_channel_count","runtime_sample_scan_count","accepted_redaction_attestation_count","retention_policy_approved_channel_count","disposition_proven_channel_count","incident_closed_count","owner_approved_channel_count","command_ready_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_redaction_contract"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
