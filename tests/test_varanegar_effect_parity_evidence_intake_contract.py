import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_effect_parity_evidence_intake_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_effect_parity_evidence_intake_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "contract.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_module_evidence_boundary():
    summary = load()["summary"]
    assert summary["module_count"] == 14
    assert summary["legacy_static_or_target_mutation_evidence_module_count"] == 12
    assert summary["target_design_only_legacy_static_incomplete_module_count"] == 2
    assert summary["runtime_effect_parity_proven_module_count"] == 0


def test_all_effect_layers_are_separate():
    evidence = {row["required_evidence"] for row in load()["parity_categories"]}
    assert len(evidence) == 10
    assert "RESULT_CONTRACT_RECEIPT" in evidence
    assert "EXTERNAL_EFFECT_OR_QUARANTINE_RECEIPT" in evidence
    assert "APPEND_ONLY_COMPENSATION_RECEIPT" in evidence


def test_dependencies_open_and_safe():
    data = load()
    assert data["scope"]["runtime_execution_requires_cg06_and_cg02_accepted"] is True
    assert data["summary"]["cg02_current_accepted_module_packet_count"] == 0
    assert data["summary"]["accepted_module_packet_count"] == 0
    assert set(data["safety"].values()) == {0}
