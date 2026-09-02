from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"artifacts/varanegar_analysis/varanegar_command_readiness_ledger_20260829.json"
def load():return json.loads(ART.read_text(encoding="utf-8-sig"))
def test_fourteen_modules_and_command_evidence_are_traced():
 p=load();assert p["validation"]=="PASS";assert p["summary"]["module_count"]==14;assert len({x["module"] for x in p["modules"]})==14;assert p["summary"]["orchestrator_command_count"]==10;assert p["summary"]["mapped_validated_command_artifact_count"]==13
def test_legacy_unvalidated_sources_are_not_readiness_gates():
 p=load();assert p["source_validation"]["legacy_side_effects"] is None;assert p["source_validation"]["legacy_golden"] is None;assert all(x["use"].endswith("NOT_READINESS_GATE") or "NOT_EXECUTED_OR_OWNER_APPROVED" in x["use"] for x in p["evidence_policy"]["legacy_unvalidated_artifacts"])
def test_static_and_synthetic_counts_are_pinned():
 p=load();assert p["summary"]["legacy_static_command_trace_count"]==11;assert p["summary"]["legacy_mutation_command_count"]==8;assert p["summary"]["legacy_synthetic_golden_case_count"]==77
def test_no_runtime_dimension_or_readiness_is_overclaimed():
 p=load();s=p["summary"];assert s["owner_approved_golden_case_count"]==0 and s["executed_golden_case_count"]==0;assert s["runtime_authorization_proven_module_count"]==0;assert s["runtime_atomicity_proven_module_count"]==0;assert s["runtime_effect_parity_proven_module_count"]==0;assert s["runtime_retry_idempotency_proven_module_count"]==0;assert s["command_ready_module_count"]==0 and s["pilot_ready_module_count"]==0
def test_every_module_has_five_truth_table_dimensions_and_blockers():
 for x in load()["modules"]:
  assert set(x["truth_table_dimensions"])=={"authorization","transaction_owner","mutation_set","outcome_retry_idempotency","golden_cases"};assert len(x["universal_blockers"])==5;assert not x["command_ready"]
def test_shared_truth_table_has_full_command_lifecycle():
 assert [x["stage"] for x in load()["shared_truth_table"]]==["authorize","validate","begin unit of work","mutate","audit/outbox","commit","retry"]
def test_risk_safety_and_manifest():
 p=load();assert p["summary"]["risk_count"]==84;assert not p["risk_decision"]["new_risk_created"];assert set(v for k,v in p["safety"].items() if k!="mode")=={0}
 for row in p["source_manifest"]:
  path=ROOT/row["path"];assert path.stat().st_size==row["size_bytes"];assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
