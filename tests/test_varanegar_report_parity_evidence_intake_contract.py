import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_report_parity_evidence_intake_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "contract.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_surface_packet_partition():
    data = load()
    assert data["summary"]["report_surface_count"] == 20
    assert data["summary"]["result_parity_packet_surface_count"] == 11
    assert data["summary"]["command_outcome_packet_surface_count"] == 2
    assert data["summary"]["routing_view_packet_surface_count"] == 7


def test_only_result_owners_receive_parity_packets():
    rows = load()["surface_intake_map"]
    assert all(
        (row["packet_class"] == "RESULT_PARITY_PACKET") == row["independent_result_parity_applicable"]
        for row in rows
    )


def test_gate_open_zero_execution_and_safe():
    data = load()
    assert data["scope"]["logical_dependency_on_cg06_acceptance"] is False
    assert data["scope"]["gate_closed"] is False
    assert data["summary"]["accepted_packet_count"] == 0
    assert data["summary"]["result_parity_proven_surface_count"] == 0
    assert data["summary"]["owner_approved_surface_count"] == 0
    assert set(data["safety"].values()) == {0}
