import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_cross_gate_diagnostic_playbook_addendum_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_cross_gate_diagnostic_playbook_addendum_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "playbook.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_eight_unique_addenda_with_ten_steps():
    data = load()
    assert len(data["playbooks"]) == 8
    assert len({row["id"] for row in data["playbooks"]}) == 8
    assert all(len(row["steps"]) >= 10 for row in data["playbooks"])
    assert data["summary"]["duplicate_playbook_id_count"] == 0


def test_latest_boundaries_are_bound():
    summary = load()["summary"]
    assert summary["identity_triage_required_unit_count"] == 139
    assert summary["pos_static_work_queue_count"] == 5
    assert summary["report_formula_policy_obligation_count"] == 123
    assert summary["blocked_handoff_edge_count"] == 9


def test_formula_and_graph_scenarios_do_not_overclaim():
    rows = {row["id"]: row for row in load()["playbooks"]}
    assert "UNKNOWN_UNTIL_TEMPLATE_EXTRACTION" in " ".join(rows["XG-PB-06"]["specific_steps"])
    assert "lower bound" in " ".join(rows["XG-PB-04"]["specific_steps"])
    assert "key-set" in " ".join(rows["XG-PB-05"]["specific_steps"])


def test_diagnostic_result_contract_and_stop_conditions():
    data = load()
    assert set(data["diagnostic_result_contract"]) == {
        "EXPECTED_BOUNDARY",
        "STATIC_EVIDENCE_GAP",
        "DATA_OR_CONFIGURATION_DEBT",
        "CONTRACT_OR_IMPLEMENTATION_DEFECT",
        "UNPROVEN",
    }
    assert all(len(row["stop_conditions"]) == 4 for row in data["playbooks"])


def test_safe_and_no_readiness():
    data = load()
    assert set(data["safety"].values()) == {0}
    assert data["summary"]["runtime_diagnosis_count"] == 0
    assert data["summary"]["command_ready_module_count"] == data["summary"]["pilot_ready_module_count"] == 0
