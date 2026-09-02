import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_accounting_expert_playbook_checkpoint_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_accounting_expert_playbook_checkpoint_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "checkpoint.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_checkpoint_passes():
    assert load()["validation"] == "PASS" and not load()["failed_checks"]


def test_contract_and_playbook_checks_are_pinned():
    checks = load()["checks"]
    assert checks["five_playbooks"] and checks["nine_contract_sections"] and checks["golden_gate_42"]


def test_no_runtime_or_repair_claim():
    assert load()["checks"]["no_runtime_or_repair_claim"]


def test_previous_checkpoint_is_hash_pinned():
    previous = load()["previous_checkpoint"]
    path = ROOT / previous["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == previous["sha256"]


def test_sources_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]


def test_safety_zero():
    assert set(load()["safety"].values()) == {0}
