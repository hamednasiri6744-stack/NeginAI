import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_platform_traceability_delta_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_platform_traceability_delta_20260829.json"
def test_rebuild(tmp_path):o=tmp_path/"a.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text())["validation"]=="PASS"
def test_links():s=json.loads(A.read_text(encoding="utf-8-sig"))["summary"];assert (s["platform_evidence_count"],s["requirement_contract_delta_count"],s["module_evidence_link_count"],s["risk_evidence_link_count"])==(5,10,40,50)
