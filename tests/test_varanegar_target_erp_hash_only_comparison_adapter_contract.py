import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "adapter.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_profile_and_schema_totals():
    summary = load()["summary"]
    assert (summary["adapter_profile_count"], summary["p3_profile_count"], summary["p4_profile_count"]) == (8, 5, 3)
    assert (summary["covered_golden_case_count"], summary["input_envelope_field_count"], summary["output_receipt_field_count"]) == (56, 18, 18)
    assert (summary["canonicalization_stage_count"], summary["error_code_count"], summary["typed_status_count"]) == (12, 16, 6)
    assert (summary["parity_dimension_assignment_count"], summary["cg05_receipt_assignment_count"]) == (160, 27)


def test_canonicalization_is_versioned_domain_separated_and_hash_only():
    document = load()
    algorithm = document["digest_contract"]
    assert algorithm["hash_algorithm"] == "SHA-256"
    assert algorithm["domain_separation_required"] is True
    assert algorithm["floating_point_serialization_allowed"] is False
    assert algorithm["raw_value_persistence_allowed"] is False
    assert document["canonicalization_stages"][0] == "validate_manifest_schema_hashes_versions_and_packet_scope"
    assert document["canonicalization_stages"][-1] == "emit_hash_only_dimension_dispositions_and_receipt"


def test_idempotency_replays_same_receipt_and_rejects_conflicts():
    contract = load()["idempotency_contract"]
    assert len(contract["key_components"]) == 5
    assert contract["same_key_same_inputs"] == "RETURN_ORIGINAL_RECEIPT_HASH"
    assert contract["same_key_different_inputs"] == "REJECT_IDEMPOTENCY_CONFLICT"
    assert contract["retry_after_unknown"] == "READ_RECEIPT_BY_KEY_BEFORE_RETRY"


def test_raw_payload_categories_are_denied():
    document = load()
    assert len(document["prohibited_persistence_categories"]) == 10
    assert "raw_rows_or_items" in document["prohibited_persistence_categories"]
    assert "rendered_documents_or_export_files" in document["prohibited_persistence_categories"]
    assert "credentials_connection_strings_or_tokens" in document["prohibited_persistence_categories"]
    assert all(profile["raw_payload_persistence_allowed"] is False for profile in document["adapter_profiles"])


def test_all_execution_receipt_and_promotion_counts_zero():
    document = load()
    summary = document["summary"]
    fields = [
        "adapter_request_count",
        "canonicalization_run_count",
        "comparison_run_count",
        "emitted_receipt_count",
        "accepted_receipt_count",
        "result_parity_proven_profile_count",
        "executed_case_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ]
    assert all(summary[field] == 0 for field in fields)
    assert all(profile["current_status"] == "DESIGNED_NOT_IMPLEMENTED_OR_RUN" for profile in document["adapter_profiles"])
    assert set(document["safety"].values()) == {0}


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

