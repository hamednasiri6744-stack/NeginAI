import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_reporting_output_readiness_delta_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_reporting_output_readiness_delta_20260829.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "delta.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_six_to_seven_and_one_changed():
    summary = load()["summary"]
    assert summary["outcome_target_contract_module_count_before"] == 6
    assert summary["outcome_target_contract_module_count_after"] == 7 and summary["changed_module_count"] == 1


def test_reporting_only_changed():
    data = load()
    reporting = next(x for x in data["modules"] if x["module"] == "reporting_documents")
    assert reporting["truth_table_dimensions"]["outcome_retry_idempotency"]["target_contract"] is True
    assert data["checks"]["one_changed"]


def test_runtime_readiness_zero():
    summary = load()["summary"]
    assert summary["runtime_retry_idempotency_proven_module_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0


def test_sources_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(value for key, value in load()["safety"].items() if key != "mode") == {0}
