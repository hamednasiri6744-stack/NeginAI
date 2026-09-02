import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/"scripts/windows/build_varanegar_pricing_rule_expert_playbook_checkpoint_20260829.py";A=ROOT/"artifacts/varanegar_analysis/varanegar_pricing_rule_expert_playbook_checkpoint_20260829.json"
def test_checkpoint(tmp_path):
 output=tmp_path/"pricing_rule_expert_playbook_checkpoint.json";subprocess.run([sys.executable,str(B),"--output",str(output)],cwd=ROOT,check=True);d=json.loads(output.read_text(encoding="utf-8"));assert d["validation"]=="PASS" and all(d["checks"].values())
