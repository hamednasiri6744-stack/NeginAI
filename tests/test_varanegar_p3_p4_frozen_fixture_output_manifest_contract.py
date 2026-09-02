import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "contract.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_contract_and_golden_case_partition():
    summary = load()["summary"]
    assert (
        summary["fixture_contract_count"],
        summary["p3_fixture_contract_count"],
        summary["p4_fixture_contract_count"],
        summary["covered_golden_case_count"],
        summary["case_count_per_contract"],
    ) == (8, 5, 3, 56, 7)


def test_exact_command_mapping_and_case_hashes():
    contracts = load()["fixture_contracts"]
    assert len({contract["command_or_surface"] for contract in contracts}) == 8
    assert len({contract["golden_case_id_set_sha256"] for contract in contracts}) == 8
    assert all(len(contract["golden_case_ids"]) == 7 for contract in contracts)
    expected = {"authorization": 1, "failure_injection": 2, "idempotency": 1, "partial_failure": 1, "success": 1, "versioning": 1}
    assert all(contract["golden_case_kind_distribution"] == expected for contract in contracts)


def test_manifest_schema_and_assignments():
    document = load()
    summary = document["summary"]
    assert (
        summary["fixture_manifest_field_count"],
        summary["output_manifest_field_count"],
        summary["comparison_manifest_field_count"],
        summary["manifest_field_assignment_count"],
    ) == (16, 16, 16, 512)
    assert (summary["required_capture_side_count"], summary["acquisition_step_count"], summary["acquisition_step_assignment_count"]) == (16, 7, 56)
    assert (summary["required_parity_dimension_assignment_count"], summary["cg05_receipt_slot_assignment_count"]) == (160, 27)
    assert "stable_key_set_sha256" in document["output_manifest_fields"]
    assert "canonical_value_difference_sha256" in document["comparison_manifest_fields"]
    assert "redaction_attestation" in document["fixture_manifest_fields"]


def test_all_contracts_designed_not_captured():
    document = load()
    summary = document["summary"]
    assert all(contract["current_status"] == "DESIGNED_NOT_CAPTURED_SEPARATE_AUTHORIZATION_REQUIRED" for contract in document["fixture_contracts"])
    assert all(contract["operational_execution_authorized"] is False and contract["readiness_effect"] == "ZERO" for contract in document["fixture_contracts"])
    assert summary["captured_fixture_manifest_count"] == 0
    assert summary["captured_output_manifest_count"] == 0
    assert summary["captured_comparison_manifest_count"] == 0
    assert summary["result_parity_proven_contract_count"] == 0
    assert summary["owner_approved_contract_count"] == 0
    assert summary["executed_case_count"] == 0
    assert summary["command_ready_module_count"] == 0
    assert summary["pilot_ready_module_count"] == 0
    assert summary["design_lower_bound_before_fixture_contract"] == summary["design_lower_bound_after_fixture_contract"] == 1404
    assert set(document["safety"].values()) == {0}


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
