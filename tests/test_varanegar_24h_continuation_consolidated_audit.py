import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"scripts/windows/build_varanegar_24h_continuation_consolidated_audit_20260829.py";A=R/"artifacts/varanegar_analysis/varanegar_24h_continuation_consolidated_audit_20260829.json"
def load():return json.loads(A.read_text(encoding="utf-8-sig"))
def test_rebuild(tmp_path):o=tmp_path/"a.json";subprocess.run([sys.executable,str(B),"--output",str(o)],check=True);assert json.loads(o.read_text())["validation"]=="PASS"
def test_coverage_and_runtime_boundary():s=load()["summary"];assert s["module_count"]==s["outcome_retry_target_contract_module_count"]==14 and s["runtime_effect_parity_proven_module_count"]==s["executed_case_count"]==0
def test_reports_and_chain():s=load()["summary"];assert s["report_surface_count"]==20 and s["report_result_parity_proven_count"]==0 and s["checkpoint_count_before_consolidated_checkpoint"]==119 and s["stale_source_manifest_node_count"]==0
def test_non_final_and_safe():d=load();assert d["scope"]["continuation_complete"] is False and set(d["safety"].values())=={0}
