from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/return_report_template_boundary_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_return_report_is_external_template_owned_not_sql_candidate_bound():
 p=load();assert p["validation"]=="PASS";assert p["corrected_classification"]["current"]=="EXTERNAL_TEMPLATE_OWNED_QUERY_AND_FORMULA";assert p["summary"]["prior_name_candidate_count"]==24;assert p["summary"]["bound_report_query_count"]==0
def test_path_engine_and_context_calls_are_hash_pinned():
 p=load();assert p["scope"]["assembly_sha256"]=="be1feb2307bef7c676ea0a58b1aa00ef1ab895a562c376698fc33827ebd2c280";assert p["summary"]["passing_method_contract_count"]==4;assert all(x["all_required_calls_present"] for x in p["method_evidence"].values())
def test_parity_and_post_print_order_are_not_overclaimed():
 p=load();assert p["summary"]["result_parity_proven_count"]==0;assert p["runtime_contract"]["post_print_audit_call_order"]=="UNPROVEN_FROM_CALL_SET_ONLY";assert p["target_contract"]["implementation_ready"] is False
def test_safety_and_existing_risks():
 p=load();assert set(v for k,v in p["safety"].items() if k!="mode")=={0};assert p["summary"]["risk_count"]==84;assert "R-084" in p["risk_links"]
def test_manifest_current():
 for row in load()["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
