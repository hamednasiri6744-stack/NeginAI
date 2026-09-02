from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/healthy_cardex_report_contract_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_exact_master_detail_bindings_replace_candidates():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["exact_query_binding_count"]==2;assert p["summary"]["prior_name_candidate_count"]==85;rows={x["role"]:x for x in p["queries"]};assert rows["MASTER"]["sql_object"].casefold()=="ica.usp_vchhealthycardex_getlist";assert rows["DETAIL"]["sql_object"].casefold()=="ica.usp_vchhealthycardexdetails_getlist"
def test_raw_where_is_only_on_dynamic_master():
 rows={x["role"]:x for x in load()["queries"]};assert rows["MASTER"]["raw_where_input"] and rows["MASTER"]["dynamic_sql"];assert not rows["DETAIL"]["raw_where_input"] and not rows["DETAIL"]["dynamic_sql"]
def test_printdoc_is_attempt_before_render_not_success():
 t=load()["print_truth_table"];assert t["selected_id_call_offset"]<t["print_audit_insert_call_offset"]<t["report_render_call_offset"];assert t["observed_linear_order"]==["SELECT_IDS","INSERT_PRINTDOC_ATTEMPT","SHOW_REPORT"];assert "DOES_NOT_PROVE" in t["success_semantics"]
def test_target_splits_preview_export_and_physical_print():
 t=load()["target_contract"];assert "NO_PRINT_AUDIT" in t["preview"];assert "NO_ERP_MUTATION" in t["export"];assert "IDEMPOTENT_COMMAND" in t["physical_print"]
def test_parity_safety_and_risk_are_honest():
 p=load();assert p["summary"]["result_parity_proven_count"]==0;assert p["summary"]["risk_count"]==84;assert "R-017" in p["risk_links"];assert set(v for k,v in p["safety"].items() if k!="mode")=={0}
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
