import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_24h_continuation_wave01_checkpoint_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_24h_continuation_wave01_checkpoint_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "checkpoint.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_checkpoint_passes_and_is_non_final():
    checkpoint = load()
    assert checkpoint["validation"] == "PASS" and not checkpoint["failed_checks"]
    assert checkpoint["checks"]["explicitly_non_final"]


def test_prior_chain_and_base_counts_are_pinned():
    checks = load()["checks"]
    assert checks["all_prior_checkpoints_current"] and checks["base_counts_stable"]


def test_runtime_gates_remain_zero():
    assert load()["checks"]["runtime_gates_zero"]


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
