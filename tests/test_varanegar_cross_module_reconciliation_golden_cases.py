import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_cross_module_reconciliation_golden_cases_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_golden_cases_20260829.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "golden.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_seven_by_five():
    summary = load()["summary"]
    assert summary["edge_type_count"] == 7 and summary["case_count"] == 35 and summary["case_count_per_edge"] == 5


def test_unique_case_ids():
    assert len({case["case_id"] for case in load()["cases"]}) == 35


def test_each_edge_has_five_cases():
    cases = load()["cases"]
    assert {sum(x["edge_type"] == edge for x in cases) for edge in {x["edge_type"] for x in cases}} == {5}


def test_semantic_guards():
    text = " ".join(a for case in load()["cases"] for a in case["assertions"])
    assert "amount scope does not" in text and "multiple sources is valid" in text and "physical absence" in text


def test_unexecuted_and_runtime_zero():
    data = load()
    assert {x["status"] for x in data["cases"]} == {"DESIGNED_NOT_EXECUTED"}
    summary = data["summary"]
    assert summary["executed_case_count"] == summary["owner_approved_case_count"] == summary["runtime_reconciliation_proven_edge_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0


def test_sources_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(value for key, value in load()["safety"].items() if key != "mode") == {0}
