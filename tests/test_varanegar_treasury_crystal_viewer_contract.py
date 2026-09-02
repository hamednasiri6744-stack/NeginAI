from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/treasury_crystal_viewer_contract_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_viewers_accept_external_documents_and_do_not_own_queries():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["viewer_count"]==2;assert p["summary"]["independent_query_owner_count"]==0;assert p["classification_correction"]["corrected"]=="CALLER_SUPPLIED_CRYSTAL_DOCUMENT_VIEWERS"
def test_viewer_rebind_is_not_template_identity():
 p=load();assert p["classification_correction"]["sql_candidate_resolution"].startswith("NOT_APPLICABLE_AT_VIEWER");assert p["parity_design"]["status"]=="VIEWER_BOUNDARY_PROVEN_TEMPLATE_PARITY_UNPROVEN";assert p["summary"]["template_query_formula_result_parity_proven_count"]==0
def test_multi_viewer_permissions_need_backend_enforcement():
 v=next(x for x in load()["viewers"] if x["contract_id"]=="RPT-02");assert "PRINT_AND_EXPORT" in v["viewer_permissions"];assert "SPOOLER_AUTHORIZATION_UNPROVEN" in v["print_export"];t=load()["truth_table"];assert any(x["condition"]=="print permission denied" and "trusted backend" in x["outcome"] for x in t)
def test_multi_document_partial_failure_and_close():
 p=load();assert "PER_DOCUMENT" in p["target_contract"]["multi_document"];assert p["summary"]["document_close_lifecycle_count"]==1;assert any(x["condition"]=="form closes" and "no business-state mutation" in x["outcome"] for x in p["truth_table"])
def test_connection_credentials_are_not_persisted():
 p=load();assert "NEVER_CLIENT_CREDENTIAL_REBIND" in p["target_contract"]["connection"];assert p["safety"]["credentials_connection_strings_business_values_or_identities_persisted"]==0
def test_risk_golden_cases_and_zero_execution():
 p=load();assert p["summary"]["risk_count"]==84;assert not p["risk_decision"]["new_risk_created"];assert len(p["golden_cases"])==6;assert set(v for k,v in p["safety"].items() if k!="mode")=={0}
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
