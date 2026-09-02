import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_authorization_runtime_evidence_intake_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_authorization_runtime_evidence_intake_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "contract.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_fourteen_modules_design_not_runtime():
    summary = load()["summary"]
    assert summary["module_count"] == summary["authorization_design_module_count"] == 14
    assert summary["runtime_authorization_proven_module_count"] == 0


def test_deny_first_server_side_matrix():
    data = load()
    expected = {row["expected"] for row in data["scenario_categories"]}
    assert len(data["scenario_categories"]) == 8
    assert {"DENY", "DENY_AND_SESSION_INVALIDATED", "SERVER_DECISION_CONTROLS"} <= expected
    assert any("UI visibility" in rule for rule in data["global_validation_rules"])


def test_cg06_dependency_and_safety():
    data = load()
    assert data["scope"]["runtime_execution_requires_cg06_accepted"] is True
    assert data["summary"]["cg06_current_accepted_decision_slot_count"] == 0
    assert data["summary"]["accepted_module_packet_count"] == 0
    assert set(data["safety"].values()) == {0}
