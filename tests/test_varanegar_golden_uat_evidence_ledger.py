import json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/"scripts/windows/build_varanegar_golden_uat_evidence_ledger_20260829.py"
ARTIFACT=ROOT/"artifacts/varanegar_analysis/varanegar_golden_uat_evidence_ledger_20260829.json"

def load(): return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):
    out=tmp_path/"ledger.json"; subprocess.run([sys.executable,str(BUILDER),"--output",str(out)],check=True)
    assert json.loads(out.read_text(encoding="utf-8"))["validation"]=="PASS"
def test_counts_are_pinned():
    s=load()["summary"]; assert (s["synthetic_command_case_count"],s["command_module_count"],s["report_surface_count"],s["risk_count"])==(77,14,20,84)
def test_no_false_runtime_claims():
    s=load()["summary"]; assert all(s[k]==0 for k in ("executed_case_count","result_parity_proven_count","owner_approved_golden_count","uat_ready_track_count","pilot_ready_track_count"))
def test_ladder_is_ordered():
    assert [x["level"] for x in load()["evidence_ladder"]]==[1,2,3,4]
def test_tracks_not_ready():
    assert {x["track"] for x in load()["tracks"]}=={"COMMAND","REPORT"}; assert not any(x["ready"] for x in load()["tracks"])
def test_sources_are_hashed():
    assert all(len(x["sha256"])==64 and x["size_bytes"]>0 for x in load()["source_manifest"])
def test_safety_is_zero():
    assert set(v for k,v in load()["safety"].items() if k!="mode")=={0}
