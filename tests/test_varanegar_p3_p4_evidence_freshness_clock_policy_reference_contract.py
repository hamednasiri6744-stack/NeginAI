import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/windows"))
from varanegar_evidence_freshness_reference import OUTCOMES, evaluate  # noqa: E402

BUILDER = ROOT / "scripts/windows/build_varanegar_p3_p4_evidence_freshness_clock_policy_reference_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p3_p4_evidence_freshness_clock_policy_reference_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "freshness.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_reference_contract_totals():
    summary = load()["summary"]
    assert (summary["temporal_artifact_type_count"], summary["freshness_outcome_count"], summary["synthetic_vector_count"]) == (4, 8, 12)
    assert (summary["synthetic_evaluation_count"], summary["synthetic_evaluation_pass_count"], summary["synthetic_evaluation_fail_count"]) == (48, 48, 0)
    assert summary["custody_requirement_count"] == 54
    assert summary["freshness_obligation_count"] == 216
    assert (summary["temporal_envelope_field_count"], summary["clock_policy_rule_count"]) == (16, 10)


def test_all_vectors_reproduce_expected_outcome_directly():
    document = load()
    for vector in document["synthetic_freshness_vectors"]:
        assert evaluate(vector["synthetic_envelope"]) == vector["expected_outcome"]
    assert set(OUTCOMES) == set(document["freshness_outcomes"])


def test_boundary_semantics_are_explicit():
    document = load()
    rules = document["freshness_rule"]
    assert rules["valid_from_boundary"] == "INCLUSIVE"
    assert rules["expires_at_boundary"] == "EXCLUSIVE"
    assert rules["timezone_aware_required"] is True
    assert rules["automatic_expiry_extension_allowed"] is False
    assert rules["system_wall_clock_used_by_synthetic_vectors"] is False


def test_obligations_cover_four_temporal_types_per_custody_requirement():
    obligations = load()["freshness_obligations"]
    by_requirement = {}
    for item in obligations:
        by_requirement.setdefault(item["custody_requirement_id"], set()).add(item["temporal_artifact_type"])
        assert item["current_outcome"] == "MISSING_TEMPORAL_EVIDENCE"
    assert len(by_requirement) == 54
    assert all(len(types) == 4 for types in by_requirement.values())


def test_no_real_evaluation_acceptance_parity_or_readiness_claim():
    document = load()
    summary = document["summary"]
    for field in (
        "real_clock_evaluation_count",
        "current_evidence_count",
        "accepted_freshness_count",
        "comparison_handoff_ready_count",
        "result_parity_proven_packet_count",
        "cg05_closed_packet_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ):
        assert summary[field] == 0
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_freshness_contract"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

