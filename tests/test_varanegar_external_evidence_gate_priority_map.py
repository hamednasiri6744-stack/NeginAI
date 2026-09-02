import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_external_evidence_gate_priority_map_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_external_evidence_gate_priority_map_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "priority.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_dependency_aware_order():
    rows = load()["priority_map"]
    assert [row["gate_id"] for row in rows] == ["CG-06", "CG-05", "CG-01", "CG-02", "CG-03", "CG-04"]
    ranks = {row["gate_id"]: row["priority_rank"] for row in rows}
    assert all(ranks[dependency] < row["priority_rank"] for row in rows for dependency in row["dependency_gate_ids"])


def test_packets_do_not_promote_readiness():
    data = load()
    assert all(len(row["required_evidence_packet"]) == 4 for row in data["priority_map"])
    assert all(row["promotion_effect_before_acceptance"] == "NONE" for row in data["priority_map"])
    assert data["summary"]["command_ready_module_count"] == data["summary"]["pilot_ready_module_count"] == 0


def test_safety_and_baseline():
    data = load()
    assert set(data["safety"].values()) == {0, False}
    assert data["summary"]["risk_count"] == 84
    assert data["summary"]["mapped_risk_assignment_count"] == 343
