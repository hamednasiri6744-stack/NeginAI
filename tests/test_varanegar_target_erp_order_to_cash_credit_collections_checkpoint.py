import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_target_erp_order_to_cash_credit_collections_checkpoint_20260901.py";C=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_order_to_cash_credit_collections_checkpoint_20260901.json"
def test_rebuild(tmp_path):o=tmp_path/"checkpoint.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_checkpoint_chain_and_safety():
 d=json.loads(C.read_text(encoding="utf-8-sig"));assert d["validation"]=="PASS" and not d["failed_checks"];assert d["previous_checkpoint"]["path"].endswith("varanegar_target_erp_procure_to_pay_synthetic_reference_evaluator_checkpoint_20260901.json");assert set(d["safety"].values())=={0}
 for x in d["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
