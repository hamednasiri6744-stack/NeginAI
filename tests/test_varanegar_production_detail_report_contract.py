from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/production_detail_report_contract_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_generic_inheritance_chain_closes_zero_candidate_gap():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["prior_sql_candidate_count"]==0;assert p["query_contract"]["sql_object"].casefold()=="dbo.usp_sdsnet_batchno_getlist";assert p["query_contract"]["binding_chain"]["view_extends_entity"]
def test_signature_and_modes():
 p=load();assert p["summary"]["parameter_count"]==18 and p["summary"]["dependency_count"]==18;assert p["summary"]["generic_read_mode_count"]==2;assert p["query_contract"]["mode_discriminator"].startswith("FETCH_REASON_VALUE_MAPPING_UNPROVEN")
def test_unknown_fetch_reason_fails_closed():
 assert any(x["condition"]=="unknown FetchReason" and "never default" in x["outcome"] for x in load()["truth_table"])
def test_quantities_and_dates_remain_distinct():
 p=load();assert set(p["query_contract"]["reported_measures"])=={"OnHandQty","DamagedQty","AllOnHandQty","AllDamagedQty"};assert p["query_contract"]["reported_dates"]==["ProDate","ExpDate"];assert any("preserve null" in x["outcome"] for x in p["truth_table"])
def test_export_is_external_and_non_mutating():
 p=load();assert p["summary"]["file_export_path_count"]==1;assert not p["target_contract"]["erp_mutation_allowed"];assert set(v for k,v in p["safety"].items() if k!="mode")=={0}
def test_parity_risk_and_golden_cases():
 p=load();assert p["summary"]["result_parity_proven_count"]==0;assert p["summary"]["risk_count"]==84;assert not p["risk_decision"]["new_risk_created"];assert len(p["golden_cases"])==6
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
