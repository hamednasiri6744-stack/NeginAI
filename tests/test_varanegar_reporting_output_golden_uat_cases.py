import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_reporting_output_golden_uat_cases_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_reporting_output_golden_uat_cases_20260829.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "golden.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_eight_by_seven():
    summary = load()["summary"]
    assert summary["command_surface_count"] == 8 and summary["case_count"] == 56 and summary["case_count_per_surface"] == 7


def test_unique_ids_and_special_assertions():
    cases = load()["cases"]
    assert len({x["case_id"] for x in cases}) == 56
    assert len({x["contract_id"] for x in cases}) == 8 and all(len(x["assertions"]) == 5 for x in cases)


def test_partial_and_unknown_present():
    outcomes = {x["expected_outcome"] for x in load()["cases"]}
    assert any(x.startswith("PARTIAL_BATCH") for x in outcomes) and any("UNKNOWN_REQUIRES_READBACK" in x for x in outcomes)


def test_unexecuted_and_runtime_zero():
    data = load()
    assert {x["status"] for x in data["cases"]} == {"DESIGNED_NOT_EXECUTED"}
    summary = data["summary"]
    assert summary["executed_case_count"] == summary["owner_approved_case_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0


def test_sources_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(value for key, value in load()["safety"].items() if key != "mode") == {0}
