import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_cross_module_reconciliation_playbook_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_playbook_20260829.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "playbook.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_seven_with_nine_steps():
    assert len(load()["playbooks"]) == 7 and all(len(x["steps"]) == 9 for x in load()["playbooks"])


def test_one_per_edge_and_valid_quarantine():
    data = load()
    assert len({x["edge_type"] for x in data["playbooks"]}) == 7 and data["checks"]["quarantines_valid"]


def test_four_way_only():
    assert load()["diagnostic_result_contract"]["allowed"] == ["NATURAL_BEHAVIOR", "DATA_DEBT", "BUG", "UNPROVEN"]


def test_runtime_zero():
    summary = load()["summary"]
    assert summary["runtime_incidents_diagnosed_count"] == summary["repairs_performed_count"] == summary["retries_performed_count"] == summary["owner_approved_count"] == 0


def test_sources_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(value for key, value in load()["safety"].items() if key != "mode") == {0}
