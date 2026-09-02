from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/party_cardex_reference_contract_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_exact_bindings_replace_name_candidates():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["exact_method_binding_count"]==6;assert p["summary"]["resolved_sql_object_count"]==5;assert sum(x["prior_name_candidate_count"] for x in p["reports"])==455
def test_three_report_scopes_are_distinct():
 rows={x["contract_id"]:x for x in load()["reports"]};assert rows["RPT-05"]["party"]=="SUPPLIER";assert rows["RPT-07"]["party"]=="CUSTOMER_CURRENCY";assert rows["RPT-08"]["party"]=="CUSTOMER_BASE"
def test_centralized_branch_is_not_silent_local_fallback():
 p=load();r=next(x for x in p["reports"] if x["contract_id"]=="RPT-08");assert "FARARU_REMOTE_REQUEST" in r["centralization"];case=next(x for x in p["golden_cases"] if x["id"]=="PC-G02");assert "no silent local substitution" in case["expected"]
def test_currency_and_formula_claims_are_honest():
 p=load();assert p["reconciliation_contract"]["formula_status"].startswith("UNPROVEN");assert p["summary"]["result_parity_proven_count"]==0;assert p["summary"]["owner_golden_value_count"]==0
def test_target_is_projection_not_ledger_crud():
 p=load();assert all("DERIVED_" in x["projection"] for x in p["reports"]);assert "do not patch ledger facts" in p["diagnostic_playbook"]["steps"][-1]
def test_risk_and_safety_remain_stable():
 p=load();assert p["summary"]["risk_count"]==84;assert not p["risk_decision"]["new_risk_created"];assert set(v for k,v in p["safety"].items() if k!="mode")=={0}
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
