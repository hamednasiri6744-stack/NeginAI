import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/"scripts/windows/build_varanegar_target_erp_command_authorization_scope_decision_trace_checkpoint_20260829.py"
CHECKPOINT=ROOT/"artifacts/varanegar_analysis/varanegar_target_erp_command_authorization_scope_decision_trace_checkpoint_20260829.json"
def test_rebuild(tmp_path):
    out=tmp_path/"checkpoint.json";subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True);assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_checkpoint_chain_and_safety():
    d=json.loads(CHECKPOINT.read_text(encoding="utf-8-sig"));assert d["validation"]=="PASS" and not d["failed_checks"];assert d["previous_checkpoint"]["path"].endswith("varanegar_target_erp_transaction_owner_saga_compensation_checkpoint_20260829.json");assert set(d["safety"].values())=={0}
    for x in d["source_manifest"]:
        p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"];assert hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
