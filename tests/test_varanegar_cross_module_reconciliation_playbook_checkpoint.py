import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_playbook_checkpoint_20260829.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_checkpoint_passes():
    data = load()
    assert data["validation"] == "PASS" and not data["failed_checks"]


def test_chain_and_counts():
    checks = load()["checks"]
    assert checks["sources_pass"] and checks["seven_playbooks"] and checks["nine_steps"] and checks["thirty_five_cases"]


def test_sources_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(load()["safety"].values()) == {0}
