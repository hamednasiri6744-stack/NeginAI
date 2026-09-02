import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "artifacts/varanegar_analysis"
BUNDLE = ANALYSIS / "varanegar_24h_continuation_wave01_bundle_20260829.json"
TEST_RESULT = ANALYSIS / "varanegar_24h_continuation_test_result_20260829.json"
BUILDER = ROOT / "scripts/windows/build_varanegar_24h_continuation_wave01_bundle_20260829.py"


def load() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "bundle.json"
    subprocess.run([sys.executable, str(BUILDER), "--test-result", str(TEST_RESULT), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_wave_is_explicitly_non_final():
    assert load()["scope"]["wave"] == 1 and load()["scope"]["continuation_complete"] is False


def test_all_gates_pass():
    assert load()["validation"] == "PASS" and not load()["failed_checks"] and all(load()["checks"].values())


def test_baseline_is_honest():
    baseline = load()["baseline"]
    assert baseline["checkpoint_count"] == baseline["passing_checkpoint_count"] >= 63
    assert baseline["risk_count"] == 84 and baseline["mapped_risk_assignment_count"] == 343
    assert baseline["command_ready_module_count"] == baseline["pilot_ready_module_count"] == 0
    assert baseline["accounting_golden_executed_count"] == baseline["report_result_parity_proven_count"] == 0


def test_requirement_audit_has_eight_items():
    assert len(load()["requirement_audit"]) == 8


def test_next_wave_is_preserved():
    assert len(load()["next_wave_priorities"]) == 4


def test_manifest_current():
    for item in load()["manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(load()["safety"].values()) == {0}
