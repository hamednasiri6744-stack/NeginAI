import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_continuation_traceability_delta_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_continuation_traceability_delta_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "trace-delta.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_seven_unique_evidence_mappings():
    mappings = load()["mappings"]
    assert len(mappings) == 7 and len({mapping["source"] for mapping in mappings}) == 7


def test_every_mapping_has_contract_module_risk_and_effect():
    assert all(mapping["requirement_contracts"] and mapping["modules"] and mapping["risk_ids"] and mapping["effect"] for mapping in load()["mappings"])


def test_base_registers_are_not_rewritten_or_promoted():
    artifact = load()
    assert artifact["policy"]["relationship"] == "ADDITIVE_EVIDENCE_DELTA_ONLY"
    assert artifact["summary"]["base_risk_count"] == 84
    assert artifact["summary"]["base_mapped_risk_assignment_count"] == 343
    assert artifact["summary"]["new_risk_count"] == artifact["summary"]["runtime_readiness_promotions"] == 0


def test_risk_links_are_existing_and_module_consistent():
    checks = load()["checks"]
    assert checks["all_risks_exist"] and checks["each_risk_matches_a_mapped_module"]


def test_sources_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]


def test_safety_zero():
    assert set(value for key, value in load()["safety"].items() if key != "mode") == {0}
