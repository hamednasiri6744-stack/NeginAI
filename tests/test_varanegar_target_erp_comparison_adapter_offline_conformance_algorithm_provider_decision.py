import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_offline_conformance_algorithm_provider_decision_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "conformance.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_offline_synthetic_conformance_totals():
    summary = load()["summary"]
    assert (summary["adapter_profile_count"], summary["positive_vector_count"], summary["negative_vector_count"]) == (8, 12, 16)
    assert (summary["offline_digest_evaluation_count"], summary["offline_digest_pass_count"], summary["offline_digest_fail_count"]) == (96, 96, 0)
    assert (summary["negative_taxonomy_lint_count"], summary["negative_taxonomy_lint_pass_count"]) == (128, 128)


def test_every_observed_digest_is_independently_reproducible():
    document = load()
    vectors = {vector["test_vector_id"]: vector for vector in document["canonical_positive_vectors"]}
    for result in document["offline_digest_conformance_results"]:
        vector = vectors[result["test_vector_id"]]
        canonical = json.dumps(vector["synthetic_canonical_object"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256((vector["domain_tag"] + "\0" + canonical).encode("utf-8")).hexdigest()
        assert result["observed_sha256"] == result["expected_sha256"] == expected
        assert result["validation"] == "PASS"
        assert result["operational_adapter_execution"] is False


def test_negative_cases_are_taxonomy_lints_not_runtime_executions():
    document = load()
    error_codes = set(document["adapter_error_codes"])
    assert {result["expected_error_code"] for result in document["negative_taxonomy_lint_results"]} == error_codes
    assert all(result["validation"] == "PASS" for result in document["negative_taxonomy_lint_results"])
    assert all(result["runtime_error_injected"] is False for result in document["negative_taxonomy_lint_results"])


def test_algorithm_provider_decision_is_explicitly_open():
    document = load()
    summary = document["summary"]
    assert (summary["algorithm_candidate_count"], summary["provider_pattern_count"]) == (4, 4)
    assert (summary["decision_criterion_count"], summary["candidate_criterion_assignment_count"]) == (14, 112)
    assert summary["decision_gate_count"] == 10
    assert summary["selected_algorithm_count"] == summary["selected_provider_count"] == 0
    assert document["decision_status"] == "NEEDS_PLATFORM_SECURITY_OWNER_DECISION"
    assert all(candidate["selection_status"] == "CANDIDATE_NOT_SELECTED" for candidate in document["algorithm_candidates"])
    assert all(candidate["selection_status"] == "CANDIDATE_NOT_SELECTED" for candidate in document["provider_patterns"])


def test_no_key_signature_operational_or_parity_claim():
    document = load()
    summary = document["summary"]
    zero_fields = [
        "key_material_created_or_loaded_count",
        "signature_created_or_loaded_count",
        "signing_run_count",
        "cryptographic_verification_run_count",
        "operational_adapter_run_count",
        "accepted_receipt_count",
        "result_parity_proven_profile_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ]
    assert all(summary[field] == 0 for field in zero_fields)
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_conformance_contract"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

