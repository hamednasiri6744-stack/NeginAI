from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/dashboard_shell_contract_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_shells_do_not_own_queries_or_independent_parity():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["shell_count"]==2;assert p["summary"]["query_owner_count"]==0;assert p["summary"]["shell_independent_result_parity_applicable_count"]==0
def test_dashboard_host_owns_five_widget_composition_not_formulas():
 p=load();assert p["summary"]["widget_count"]==5;assert len({x["widget_id"] for x in p["widget_contracts"]})==5;assert all(x["result_parity"]=="PER_WIDGET_UNPROVEN" for x in p["widget_contracts"]);assert "does_not_own" in p["classification_correction"]["RPT-03"]
def test_permission_refresh_and_failure_are_per_widget():
 t=load()["truth_table"];assert any(x["condition"]=="widget permission denied" and "query not dispatched" in x["outcome"] for x in t);assert any(x["condition"]=="one widget refresh fails" and "other widgets retain" in x["outcome"] for x in t);assert "PER_WIDGET" in load()["target_contract"]["refresh"]
def test_zoom_is_pure_view_state():
 p=load();assert p["classification_correction"]["RPT-04"]["corrected"]=="CONTROL_ZOOM_AND_DRAG_DROP_SHELL";assert "PURE_VIEW_STATE" in p["target_contract"]["zoom"];assert any(x["surface"]=="RPT-04" and "scope and watermark unchanged" in x["outcome"] for x in p["truth_table"])
def test_no_cross_widget_atomicity_claim():assert load()["target_contract"]["snapshot_semantics"].startswith("NO_CROSS_WIDGET_ATOMICITY")
def test_safety_risk_and_golden_cases():
 p=load();assert p["summary"]["risk_count"]==84;assert not p["risk_decision"]["new_risk_created"];assert len(p["golden_cases"])==6;assert set(v for k,v in p["safety"].items() if k!="mode")=={0}
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
