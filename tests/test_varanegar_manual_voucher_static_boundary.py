import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_manual_voucher_static_boundary_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_manual_voucher_static_boundary_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"m.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_cancel_is_ui_close_not_mutation():
 x=load()["findings"]["internal_cancel"];assert x["classification"]=="UI_CLOSE_ONLY_NOT_ACCOUNTING_CANCEL" and x["only_form_close"] and not x["mutation_claim"]
def test_false_candidate_is_rejected():assert load()["semantic_correction"]["effect_on_command_inventory"].startswith("remove one false")
def test_save_is_generic_and_commit_unresolved():
 x=load()["findings"]["save"];assert x["generic_save_call"] and x["handler_instance_call"] and not x["local_commit_call"] and x["exact_adapter_or_procedure"]=="UNRESOLVED_BEHIND_GENERIC_TYPESPECROW"
def test_no_runtime_claim():assert load()["summary"]["runtime_effect_parity_proven_count"]==0
def test_source_hash_pinned():assert len(load()["source_assembly"]["sha256"])==64 and not load()["source_assembly"]["assembly_executed"]
def test_manifests_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
