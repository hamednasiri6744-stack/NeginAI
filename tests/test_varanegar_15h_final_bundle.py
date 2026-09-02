from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "artifacts" / "varanegar_analysis"
BUNDLE = ANALYSIS / "varanegar_15h_final_baseline_bundle_20260829.json"
TEST_RESULT = ANALYSIS / "varanegar_15h_final_test_result_20260829.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_final_bundle_has_complete_passing_axis_baseline() -> None:
    payload = load(BUNDLE)
    assert payload["validation"] == "PASS"
    assert payload["baseline"]["checkpoint_count_20260829"] == 36
    assert payload["baseline"]["passing_checkpoint_count_20260829"] == 36
    assert len(payload["axis_evidence"]) == 7
    assert all(
        row["validation"] == "PASS"
        for rows in payload["axis_evidence"].values()
        for row in rows
    )


def test_final_bundle_preserves_risk_and_readiness_baseline() -> None:
    baseline = load(BUNDLE)["baseline"]
    assert (baseline["risk_count"], baseline["critical_risk_count"]) == (84, 50)
    assert (baseline["high_risk_count"], baseline["medium_risk_count"]) == (31, 3)
    assert baseline["mapped_risk_assignment_count"] == 343
    assert baseline["command_ready_module_count"] == 0


def test_final_bundle_safety_boundary_is_zero_mutation_and_zero_execution() -> None:
    safety = load(BUNDLE)["safety"]
    assert set(safety.values()) == {0}


def test_final_test_manifest_is_current_and_offline() -> None:
    payload = load(TEST_RESULT)
    assert payload["validation"] == "PASS"
    assert payload["runner"]["pytest_plugin_autoload_disabled"] is True
    assert payload["runner"]["passed_test_count"] >= 525
    assert payload["runner"]["test_file_count"] == len(payload["test_manifest"])
    assert payload["safety"] == {
        "database_connections_created_by_runner": 0,
        "assemblies_loaded_or_executed_by_runner": 0,
        "operational_commands_executed_by_runner": 0,
        "raw_pytest_output_persisted": False,
    }
    for row in payload["test_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert sha256(path) == row["sha256"]
