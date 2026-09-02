from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/domains/print_batch_contract_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_render_paths_split_completion_gated_and_render_only():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["render_path_count"]==7;assert p["summary"]["completion_gated_render_path_count"]==4;assert p["summary"]["render_only_path_count"]==3
def test_completion_is_after_render_and_commits_without_local_rollback():
 p=load();g=[x for x in p["render_truth_table"] if x["reads_printed_completed"]];assert all(x["render_offset"]<x["completion_offset"] for x in g);assert p["summary"]["completion_commit_path_count"]==2;assert p["summary"]["completion_local_rollback_path_count"]==0
def test_batch_contract_is_partial_success_not_one_boolean():
 b=load()["batch_orchestration"];assert b["transaction_owner"]=="NONE_IN_SELECTED_UI_ORCHESTRATOR";assert b["rollback"]=="NO_BATCH_ROLLBACK_SIGNAL";assert "PER_OUTPUT" in b["partial_success"];assert "ONE_BOOLEAN" in b["success_message"]
def test_target_has_per_item_idempotency_outbox_and_retry():
 t=load()["target_contract"];assert "request_id" in t["item_idempotency_key"];assert "IMMUTABLE_EVENT" in t["outbox"];assert t["response"].startswith("PER_ITEM");assert t["retry"]=="FAILED_OR_UNCONFIRMED_ITEMS_ONLY"
def test_golden_cases_cover_mixed_and_commit_failure():
 cases={x["id"]:x for x in load()["golden_cases"]};assert len(cases)==5;assert "two successes retained" in cases["PB-G02"]["expected"];assert "rendered_unconfirmed" in cases["PB-G03"]["expected"]
def test_safety_parity_risk_and_manifest():
 p=load();assert set(v for k,v in p["safety"].items() if k!="mode")=={0};assert p["summary"]["result_parity_proven_count"]==0;assert p["summary"]["risk_count"]==84;assert "R-017" in p["risk_links"]
 for row in p["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
