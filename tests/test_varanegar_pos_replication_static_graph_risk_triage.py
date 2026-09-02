import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_pos_replication_static_graph_risk_triage_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_pos_replication_static_graph_risk_triage_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "triage.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_boundary_and_opaque_queue_are_not_conflated():
    summary = load()["summary"]
    assert summary["depth_boundary_callable_module_count"] == 151
    assert summary["opaque_unexpanded_queue_count"] == 160
    assert summary["graph_truncated_at_safety_cap"] is True


def test_unresolved_names_are_refined_not_erased():
    summary = load()["summary"]
    assert summary["unresolved_dependency_count"] == 179
    assert summary["sql_pseudotable_reference_count"] == 168
    assert summary["actionable_unresolved_name_or_type_count"] == 11


def test_cycles_and_write_targets_are_preserved():
    summary = load()["summary"]
    assert summary["cyclic_component_count"] == 11
    assert summary["cyclic_node_count"] == 68
    assert summary["resolved_write_target_count"] == 48


def test_no_runtime_or_readiness_claim():
    data = load()
    summary = data["summary"]
    assert summary["runtime_atomicity_proven_command_count"] == 0
    assert summary["runtime_effect_parity_proven_count"] == 0
    assert summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0
    assert set(data["safety"].values()) == {0}
