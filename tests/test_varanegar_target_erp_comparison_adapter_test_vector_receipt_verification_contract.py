import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_test_vector_receipt_verification_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "vectors.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_vector_and_verification_totals():
    summary = load()["summary"]
    assert (summary["adapter_profile_count"], summary["canonical_positive_vector_count"], summary["negative_error_vector_count"]) == (8, 12, 16)
    assert summary["total_test_vector_count"] == 28
    assert (summary["profile_vector_assignment_count"], summary["expected_digest_count"]) == (224, 12)
    assert (summary["authenticity_metadata_field_count"], summary["verification_outcome_count"]) == (16, 8)
    assert (summary["key_lifecycle_state_count"], summary["rotation_rule_count"], summary["verification_step_count"]) == (6, 8, 10)


def test_positive_vector_digest_is_independently_reproducible():
    vector = load()["canonical_positive_vectors"][0]
    canonical = json.dumps(vector["synthetic_canonical_object"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    expected = hashlib.sha256((vector["domain_tag"] + "\0" + canonical).encode("utf-8")).hexdigest()
    assert expected == vector["expected_sha256"]
    assert vector["synthetic_only"] is True and vector["contains_business_value"] is False


def test_negative_vectors_cover_adapter_error_taxonomy_exactly():
    document = load()
    assert {vector["expected_error_code"] for vector in document["negative_error_vectors"]} == set(document["adapter_error_codes"])
    assert all(vector["expected_verification_or_adapter_acceptance"] is False for vector in document["negative_error_vectors"])


def test_authenticity_contract_contains_no_key_or_signature_material():
    document = load()
    contract = document["receipt_authenticity_contract"]
    assert contract["selected_runtime_algorithm_profile"] is None
    assert contract["private_key_material_persisted"] is False
    assert contract["public_key_material_persisted"] is False
    assert contract["signature_bytes_persisted"] is False
    assert "private_key_material" in document["prohibited_persistence_categories"]
    assert "signature_bytes" in document["prohibited_persistence_categories"]


def test_all_signing_verification_and_readiness_counts_zero():
    document = load()
    summary = document["summary"]
    fields = [
        "selected_algorithm_profile_count",
        "registered_verification_key_count",
        "signed_receipt_count",
        "verification_run_count",
        "authentic_receipt_count",
        "accepted_receipt_count",
        "result_parity_proven_profile_count",
        "executed_case_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ]
    assert all(summary[field] == 0 for field in fields)
    assert set(document["safety"].values()) == {0}


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

