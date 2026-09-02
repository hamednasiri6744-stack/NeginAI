from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "varanegar_analysis" / "varanegar_25h_opening_gap_map_20260829.json"
CHECKPOINT = ROOT / "artifacts" / "varanegar_analysis" / "varanegar_25h_gap_checkpoint_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_gap_map_preserves_drift_free_baseline() -> None:
    payload = load()
    assert payload["validation"] == "PASS"
    assert payload["baseline"]["manifest_entry_count"] == 45
    assert payload["baseline"]["drift_count"] == 0
    assert payload["drift"] == []


def test_report_parity_is_first_and_not_overclaimed() -> None:
    first = load()["prioritized_gaps"][0]
    assert first["gap_id"] == "G25-REPORT-IDENTITY-SCOPE-PARITY"
    assert first["confidence"] == "CONFIRMED_GAP"
    assert first["evidence"]["result_parity_proven_count"] == 0
    assert first["evidence"]["offline_golden_case_count"] == 175
    assert "R-031" in first["risk_links"]


def test_gap_map_does_not_inflate_risk_or_readiness() -> None:
    baseline = load()["baseline"]
    assert baseline["risk_count"] == 84
    assert baseline["mapped_risk_assignment_count"] == 343
    assert baseline["command_ready_module_count"] == 0


def test_source_manifest_is_hash_pinned() -> None:
    for row in load()["source_manifest"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_safety_is_zero_execution_and_zero_mutation() -> None:
    safety = load()["safety"]
    assert safety["mode"] == "OFFLINE_EXISTING_ARTIFACT_CROSSWALK"
    assert set(value for key, value in safety.items() if key != "mode") == {0}


def test_checkpoint_chains_to_passing_prior_bundle() -> None:
    payload = json.loads(CHECKPOINT.read_text(encoding="utf-8-sig"))
    assert payload["validation"] == "PASS"
    prior = ROOT / payload["previous_checkpoint"]["path"]
    assert hashlib.sha256(prior.read_bytes()).hexdigest() == payload["previous_checkpoint"]["sha256"]
    assert set(payload["safety"].values()) == {0}
