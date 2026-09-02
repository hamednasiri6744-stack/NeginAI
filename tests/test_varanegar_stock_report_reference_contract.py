from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/"artifacts/varanegar_analysis/domains/stock_report_reference_contract_20260829.json"
CHECKPOINT=ROOT/"artifacts/varanegar_analysis/varanegar_stock_report_checkpoint_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_ten_bindings_and_parameter_sets_are_exact():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["exact_method_sql_binding_count"]==10;assert p["summary"]["sql_object_count"]==10;assert p["summary"]["parameter_set_match_count"]==10
 assert all(x["parameter_set_matches_case_insensitive"] for x in p["reference_reports"])
def test_cardex_and_open_commitment_objects_are_not_name_candidates_anymore():
 rows={x["report_method"]:x for x in load()["reference_reports"]}
 assert rows["GetCardexReport"]["sql_object"].casefold()=="inv.usp_sdsn_getcardexreport"
 assert rows["GetOpenOrderList"]["sql_object"].casefold()=="sle.usp_sdsn_getopenorderlist"
 assert rows["GetOpenSaleList"]["sql_object"].casefold()=="sle.usp_sdsn_getopensalelist"
 assert all(x["binding_confidence"]=="CONFIRMED_STATIC_IL_PLUS_READ_ONLY_CATALOG" for x in rows.values())
def test_source_of_truth_and_parity_are_not_overclaimed():
 p=load();assert p["summary"]["result_parity_proven_count"]==0;assert p["confidence"]["result_parity"]=="UNPROVEN";assert p["confidence"]["report_role_and_source_of_truth_classification"]=="STRONG_INFERENCE"
 assert all(x["source_of_truth_classification"].startswith("DERIVED_PROJECTION") for x in p["reference_reports"])
def test_uat_design_is_nonexecuting_and_privacy_safe():
 u=load()["uat_reconciliation_design"];assert u["execution_status"]=="DESIGN_ONLY_NOT_AUTHORIZED";assert "ANONYMIZED" in u["fixture_privacy"]
 safety=load()["safety"];assert set(v for k,v in safety.items() if k!="mode")=={0}
def test_existing_risks_are_reused_without_inflation():
 p=load();assert p["summary"]["risk_count"]==84;assert "R-031" in p["risk_links"]
def test_manifest_is_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
def test_checkpoint_is_chained_and_zero_execution():
 p=json.loads(CHECKPOINT.read_text(encoding="utf-8-sig"));assert p["validation"]=="PASS";prior=ROOT/p["previous_checkpoint"]["path"];assert hashlib.sha256(prior.read_bytes()).hexdigest()==p["previous_checkpoint"]["sha256"];assert set(p["safety"].values())=={0}
