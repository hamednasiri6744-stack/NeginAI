import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_24h_continuation_gap_refresh_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_24h_continuation_gap_refresh_20260829.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "gap.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_six_ranked_and_reporting_selected():
    data = load()
    assert [x["rank"] for x in data["prioritized_gaps"]] == list(range(1, 7))
    assert data["summary"]["selected_gap_id"] == "G24-REPORTING-OUTCOME-RETRY"


def test_reporting_counts_and_contract_gap():
    summary = load()["summary"]
    assert summary["outcome_target_contract_module_count"] == 6
    assert summary["report_command_surface_count"] == summary["report_partial_failure_case_count"] == 8


def test_external_gates_separate():
    summary = load()["summary"]
    assert summary["static_or_design_advanceable_count"] == 4 and summary["external_authority_required_count"] == 2


def test_sources_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(value for key, value in load()["safety"].items() if key != "mode") == {0}
