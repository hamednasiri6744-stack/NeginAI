import hashlib,json,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_accounting_golden_uat_cases_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_accounting_golden_uat_cases_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"g.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_six_commands_seven_cases_each():
 x=load();assert x["summary"]["command_count"]==6 and x["summary"]["case_count"]==42;assert set(Counter(c["command_id"] for c in x["cases"]).values())=={7}
def test_false_cancel_family_removed():assert not any("manual_voucher.cancel" in x["command_id"] for x in load()["cases"])
def test_transfer_durable_error_case():
 x=next(x for x in load()["cases"] if x["case_id"].endswith("business_error_after_cleanup"));assert x["expected_outcome"]=="BUSINESS_ERROR_WITH_DURABLE_EFFECT" and "retry blocked pending read-back" in x["expected_assertions"]
def test_all_are_design_only():assert all(x["execution_status"]=="DESIGNED_NOT_EXECUTED" and x["owner_approval"]=="NOT_OBSERVED" for x in load()["cases"])
def test_isolated_gate():assert load()["execution_gate"]["environment"]=="isolated target test database only"
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
