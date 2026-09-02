import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_cross_module_reconciliation_traceability_delta_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_cross_module_reconciliation_traceability_delta_20260829.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "trace.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_counts():
    summary = load()["summary"]
    assert summary["cross_module_evidence_count"] == 3 and summary["requirement_contract_delta_count"] == 10
    assert summary["module_evidence_link_count"] == 21 and summary["risk_evidence_link_count"] == 30


def test_existing_only_and_module_consistent():
    data = load()
    assert data["summary"]["unique_linked_risk_count"] == 10 and data["checks"]["module_consistent"]


def test_additive_no_promotion():
    data = load()
    assert data["policy"]["relationship"] == "ADDITIVE_EVIDENCE_DELTA_ONLY"
    assert data["summary"]["new_risk_count"] == data["summary"]["runtime_readiness_promotions"] == 0


def test_sources_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(value for key, value in load()["safety"].items() if key != "mode") == {0}
