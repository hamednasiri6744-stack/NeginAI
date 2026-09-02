from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/stock_report_selector_contract_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_selectors_do_not_own_queries_or_result_sets():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["selector_count"]==2;assert p["summary"]["query_owner_count"]==0;assert p["summary"]["independent_result_set_count"]==0
def test_classification_is_corrected_to_routing_parity():
 c=load()["classification_correction"];assert c["corrected"]=="SELECTOR_AND_ROUTE_CONTRACTS_NO_INDEPENDENT_RESULT_SET";assert c["independent_result_parity_applicable_count"]==0;assert c["routing_parity_required_count"]==2
def test_rpt16_is_modal_typed_choice():
 s=next(x for x in load()["selectors"] if x["contract_id"]=="RPT-16");assert s["corrected_classification"]=="MODAL_PARAMETER_SELECTOR";assert not s["query_owned"];assert any(x["surface"]=="RPT-16" and x["condition"]=="cancel" and "no query" in x["outcome"] for x in load()["truth_table"])
def test_rpt17_routes_to_existing_downstream_contracts():
 p=load();s=next(x for x in p["selectors"] if x["contract_id"]=="RPT-17");assert s["downstream_contracts"]==["RPT-14","RPT-15"];assert set(p["target_contract"]["downstream_result_contracts"])=={"RPT-14","RPT-15"}
def test_unknown_route_fails_closed_and_multi_route_is_partial():
 t=load()["truth_table"];assert any(x["condition"]=="unknown enum or missing localized resource" and "never default" in x["outcome"] for x in t);assert "PER_ROUTE" in load()["target_contract"]["multi_route_outcome"]
def test_safety_risk_and_golden_cases():
 p=load();assert p["summary"]["risk_count"]==84;assert not p["risk_decision"]["new_risk_created"];assert len(p["golden_cases"])==6;assert set(v for k,v in p["safety"].items() if k!="mode")=={0}
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
