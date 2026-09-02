import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_inventory_synthetic_reference_evaluator_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_inventory_synthetic_reference_evaluator_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"inventory-reference.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_vectors_pass():s=load()["summary"];assert s["positive_vector_count"]==s["positive_pass_count"]==7;assert s["negative_vector_count"]==s["negative_pass_count"]==21;assert s["total_vector_count"]==s["total_pass_count"]==28 and s["distinct_typed_outcome_count"]>=19
def test_precedence_explicit():assert load()["outcome_precedence"][:5]==["SCHEMA","SCOPE","LOT_SERIAL_DATE","VERSION_IDEMPOTENCY","UNKNOWN_COMMIT"]
def test_no_operational_or_readiness_claim():
 d=load();s=d["summary"]
 for f in ("operational_inventory_costing_or_traceability_implementation_count","operational_item_lot_serial_quantity_cost_value_or_ledger_read_count","move_allocate_cost_transfer_count_revalue_or_reconcile_run_count","accepted_operational_receipt_count","command_ready_module_count","pilot_ready_module_count"):assert s[f]==0
 assert set(d["safety"].values())=={0};assert s["risk_count"]==84 and s["mapped_risk_assignment_count"]==343 and s["design_lower_bound_after_reference_evaluator"]==1404
def test_source_manifest_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
