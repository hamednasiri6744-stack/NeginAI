import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_terminal_owner_uat_evidence_intake_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "contract.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_terminal_dependencies_and_counts():
    data = load()
    assert set(data["upstream_gate_requirements"]) == {"CG-01", "CG-02", "CG-03", "CG-05", "CG-06"}
    assert data["summary"]["upstream_required_packet_or_slot_count"] == 70
    assert data["summary"]["upstream_current_accepted_packet_or_slot_count"] == 0


def test_design_is_not_execution_or_approval():
    summary = load()["summary"]
    assert summary["synthetic_acceptance_design_obligation_count"] == 1229
    assert summary["executed_obligation_count"] == 0
    assert summary["owner_approved_module_count"] == 0
    assert summary["promotion_approved_module_count"] == 0


def test_gate_open_and_safe():
    data = load()
    assert data["scope"]["execution_requires_all_five_upstream_gates_accepted"] is True
    assert data["scope"]["gate_closed"] is False
    assert set(data["safety"].values()) == {0}
