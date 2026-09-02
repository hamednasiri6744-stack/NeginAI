import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_atomicity_fault_evidence_intake_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_atomicity_fault_evidence_intake_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "contract.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_module_evidence_boundary():
    summary = load()["summary"]
    assert summary["module_count"] == 14
    assert summary["legacy_static_or_design_present_module_count"] == 12
    assert summary["target_design_only_legacy_static_incomplete_module_count"] == 2
    assert summary["runtime_atomicity_proven_module_count"] == 0


def test_fault_matrix_covers_unknown_and_external_boundaries():
    outcomes = {row["required_outcome"] for row in load()["fault_categories"]}
    assert len(outcomes) == 10
    assert "UNKNOWN_OUTCOME_STOP_AND_ESCALATE" in outcomes
    assert "PENDING_OUTBOX_RETRY_WITHOUT_DUPLICATE" in outcomes
    assert "CONVERGE_TO_ONE_APPROVED_STATE" in outcomes


def test_runtime_gated_and_safe():
    data = load()
    assert data["scope"]["runtime_execution_requires_cg06_accepted"] is True
    assert data["scope"]["may_execute_in_parallel_with_cg01_after_cg06"] is True
    assert data["summary"]["accepted_module_packet_count"] == 0
    assert set(data["safety"].values()) == {0}
