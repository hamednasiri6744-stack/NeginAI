import hashlib,json,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_report_golden_fixture_design_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_report_golden_fixture_design_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
 o=tmp_path/"r.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_all_20_have_four_base_cases():
 base=[x for x in load()["cases"] if not x["case_id"].endswith("command_partial_failure")];assert len(base)==80 and set(Counter(x["contract_id"] for x in base).values())=={4}
def test_eight_command_cases():assert load()["summary"]["command_partial_failure_case_count"]==8 and load()["summary"]["case_count"]==88
def test_shells_do_not_invent_value_parity():assert all("no independent value-parity claim" in x["assertions"] for x in load()["cases"] if x["ownership_class"] in {"HOST_OR_VIEW_SHELL","SELECTOR_OR_ROUTE"} and not x["case_id"].endswith("command_partial_failure"))
def test_no_execution_or_owner_claim():assert load()["summary"]["executed_case_count"]==load()["summary"]["result_parity_proven_surface_count"]==load()["summary"]["owner_approved_surface_count"]==0
def test_sources_current():
 for x in load()["source_manifest"]:
  p=ROOT/x["path"];assert p.stat().st_size==x["size_bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"]
def test_safety_zero():assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
