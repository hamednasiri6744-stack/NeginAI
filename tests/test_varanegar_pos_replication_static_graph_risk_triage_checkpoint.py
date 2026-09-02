import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_pos_replication_static_graph_risk_triage_checkpoint_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_pos_replication_static_graph_risk_triage_checkpoint_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "checkpoint.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_chain_and_manifest():
    data = load()
    assert data["validation"] == "PASS"
    assert data["previous_checkpoint"]["path"].endswith("varanegar_external_gate_handoff_acceptance_checkpoint_20260829.json")
    assert {row["name"] for row in data["source_manifest"]} == {
        "triage",
        "previous",
        "builder",
        "checkpoint_builder",
        "test",
        "checkpoint_test",
        "doc",
    }
