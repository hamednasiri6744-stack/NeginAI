import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_platform_decision_evidence_intake_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_platform_decision_evidence_intake_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "contract.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_eight_dependency_ordered_slots():
    slots = load()["decision_slots"]
    assert len(slots) == 8
    ranks = {slot["decision_slot_id"]: slot["rank"] for slot in slots}
    assert all(ranks[dependency] < slot["rank"] for slot in slots for dependency in slot["dependency_slot_ids"])


def test_proposal_and_conflict_rules():
    contract = load()["intake_contract"]
    assert "PROPOSAL never satisfies an approval slot" in contract["canonical_rules"]
    assert "CONFLICTING_CURRENT_APPROVALS" in contract["validation_outcomes"]
    assert "DEPENDENCY_NOT_APPROVED" in contract["validation_outcomes"]


def test_gate_remains_open_and_safe():
    data = load()
    assert data["scope"]["gate_closed"] is False
    assert data["summary"]["selected_decision_slot_count"] == 0
    assert data["summary"]["accepted_current_packet_count"] == 0
    assert data["summary"]["runtime_external_effect_parity_proven_count"] == 0
    assert set(data["safety"].values()) == {0}
