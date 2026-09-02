import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_accounting_expert_playbook_contract_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_accounting_expert_playbook_contract_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"p.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_five_playbooks_have_diagnostic_depth():assert len(load()["playbooks"])==5 and all(len(x["steps"])>=7 for x in load()["playbooks"])
def test_rejected_misinterpretations_explicit():
 r=load()["evidence_classification"]["REJECTED"];assert "UI close" in r and "error text" in r and "MAX(history)" in r
def test_target_contract_has_required_guards():
 c=load()["target_erp_contract"];assert len(c)==9 and c["authorization"].startswith("deny-first") and "unique command_id" in c["idempotency"] and len(c["quarantine"])==4
def test_acceptance_gate_uses_42_cases():assert load()["summary"]["golden_case_gate_count"]==42
def test_no_incident_or_repair_claim():assert load()["summary"]["runtime_incidents_diagnosed_count"]==load()["summary"]["repairs_performed_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
