from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/production_order_report_contract_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_exact_query_and_signature():
 p=load();assert p["validation"]=="PASS";assert p["query_contract"]["sql_object"].casefold()=="dbo.usp_sdsnet_productionorderreport";assert p["summary"]["parameter_count"]==8;assert p["summary"]["prior_name_candidate_count"]==4
def test_source_and_target_stock_are_distinct():
 q=load()["query_contract"];names=[x["parameter_name"] for x in q["parameters"]];assert "@StockDcRef" in names and "@TStockDCRef" in names;assert any("independently" in x["outcome"] for x in load()["truth_table"] if x["condition"]=="target stock DC supplied")
def test_missing_legacy_auth_scope_is_not_overclaimed():
 q=load()["query_contract"];assert not q["explicit_accyear_parameter"] and not q["explicit_user_parameter"];assert q["authorization_and_fiscal_scope_status"].startswith("NOT_PROVEN")
def test_export_and_report_are_non_mutating():
 p=load();assert not p["target_contract"]["erp_mutation_allowed"];assert any(x["condition"]=="export requested" and "zero ERP mutation" in x["outcome"] for x in p["truth_table"]);assert set(v for k,v in p["safety"].items() if k!="mode")=={0}
def test_parity_risk_and_golden_cases():
 p=load();assert p["summary"]["result_parity_proven_count"]==0;assert p["summary"]["risk_count"]==84;assert not p["risk_decision"]["new_risk_created"];assert len(p["golden_cases"])==6
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
