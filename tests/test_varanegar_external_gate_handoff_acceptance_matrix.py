import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_external_gate_handoff_acceptance_matrix_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "matrix.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_six_open_gates_and_84_units():
    summary = load()["summary"]
    assert summary["gate_count"] == summary["open_gate_count"] == 6
    assert summary["required_acceptance_unit_count"] == 84
    assert summary["current_accepted_unit_count"] == summary["closed_gate_count"] == 0


def test_dependency_handoffs_are_exact_and_blocked():
    data = load()
    edges = {(row["from_gate_id"], row["to_gate_id"]) for row in data["dependency_handoff_edges"]}
    assert len(edges) == 9
    assert ("CG-06", "CG-01") in edges
    assert ("CG-02", "CG-03") in edges
    assert ("CG-05", "CG-04") in edges
    assert {row["handoff_state"] for row in data["dependency_handoff_edges"]} == {"BLOCKED_SOURCE_GATE_OPEN"}


def test_no_identity_payload_or_readiness_promotion():
    data = load()
    assert all(role.endswith("_ROLE") for row in data["gate_handoff_matrix"] for role in row["accountable_role_types"])
    assert {row["readiness_effect_before_gate_closure"] for row in data["gate_handoff_matrix"]} == {"NONE"}
    assert set(data["safety"].values()) == {0}


def test_state_machine_rejects_premature_promotion():
    machine = load()["handoff_state_machine"]
    assert "ACCEPTED_CURRENT" in machine["states"]
    assert "PREMATURE_READINESS_PROMOTION_ATTEMPT" in machine["rejection_codes"]
