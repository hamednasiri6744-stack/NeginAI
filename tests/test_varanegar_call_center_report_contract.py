from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/call_center_report_contract_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_zero_candidate_gap_is_closed_by_exact_binding():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["prior_sql_candidate_count"]==0;assert p["query_contract"]["sql_object"].casefold()=="dbo.usp_callcenter_productcustomer_report"
def test_signature_and_type_boundary_are_exact():
 p=load();assert [x["parameter_name"] for x in p["query_contract"]["parameters"]]==["@AccYear","@DCRef","@UserRef","@Type"];assert p["summary"]["type_discriminator_reference_count"]>0;assert p["query_contract"]["mode_to_type_value_mapping"].startswith("UNPROVEN")
def test_customer_and_product_modes_do_not_share_grain():
 p=load();assert len(p["target_contract"]["separate_response_schemas"])==2;assert p["reconciliation"]["split_first"].startswith("RECONCILE_EACH_TYPE_BRANCH");assert any("never union" in x["outcome"] for x in p["truth_table"])
def test_unknown_type_and_scope_deny_before_query():
 t=load()["truth_table"];assert any(x["condition"]=="unknown legacy Type value" and "never default" in x["outcome"] for x in t);assert any(x["condition"]=="actor outside DC/user scope" and "deny before query" in x["outcome"] for x in t)
def test_privacy_parity_risk_and_safety():
 p=load();assert "MINIMIZE" in p["target_contract"]["privacy"];assert p["summary"]["result_parity_proven_count"]==0;assert p["summary"]["risk_count"]==84;assert not p["risk_decision"]["new_risk_created"];assert set(v for k,v in p["safety"].items() if k!="mode")=={0}
def test_six_golden_cases():assert len(load()["golden_cases"])==6
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
