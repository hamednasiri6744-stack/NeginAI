import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_checkpoint_20260829.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_checkpoint_passes():
    data = load()
    assert data["validation"] == "PASS" and not data["failed_checks"]


def test_chain_shape_and_gates():
    checks = load()["checks"]
    assert checks["sources_pass"] and checks["eight_surfaces"] and checks["contract_shape"] and checks["runtime_zero"]


def test_sources_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(load()["safety"].values()) == {0}
