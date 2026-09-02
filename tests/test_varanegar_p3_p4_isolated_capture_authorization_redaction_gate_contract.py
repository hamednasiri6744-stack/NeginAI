import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "capture-auth.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_packet_side_schema_and_assignment_totals():
    summary = load()["summary"]
    assert (summary["packet_count"], summary["golden_case_count"], summary["capture_side_count"]) == (8, 56, 2)
    assert summary["capture_channel_count"] == 16
    assert (summary["authorization_request_field_count"], summary["redaction_attestation_field_count"]) == (24, 18)
    assert (summary["authorization_gate_count"], summary["authorization_gate_assignment_count"]) == (14, 224)
    assert (summary["role_type_count"], summary["role_assignment_count"], summary["sod_rule_count"]) == (6, 96, 5)


def test_each_packet_has_two_separately_authorized_capture_channels():
    channels = load()["capture_channels"]
    by_packet = {}
    for channel in channels:
        by_packet.setdefault(channel["cg05_packet_id"], set()).add(channel["capture_side"])
        assert channel["authorization_status"] == "NOT_REQUESTED"
        assert channel["authorization_token_reference"] is None
    assert len(by_packet) == 8
    assert all(sides == {"LEGACY_REFERENCE", "TARGET_CANDIDATE"} for sides in by_packet.values())


def test_all_gates_and_roles_are_unmet_or_unassigned():
    document = load()
    assert all(assignment["status"] == "UNMET" for assignment in document["authorization_gate_assignments"])
    assert all(assignment["status"] == "UNASSIGNED" for assignment in document["role_assignments"])
    assert all(rule["currently_satisfied"] is False for rule in document["segregation_of_duties_rules"])


def test_raw_sensitive_categories_are_prohibited_and_hash_only_is_allowed():
    document = load()
    assert len(document["allowed_persistence_categories"]) == 8
    assert len(document["prohibited_capture_or_persistence_categories"]) == 14
    assert "hash_only_manifest_and_dimension_disposition" in document["allowed_persistence_categories"]
    assert "raw_business_values" in document["prohibited_capture_or_persistence_categories"]
    assert "credentials_or_connection_strings" in document["prohibited_capture_or_persistence_categories"]


def test_no_authorization_capture_acceptance_or_readiness_claim():
    document = load()
    summary = document["summary"]
    zero_fields = [
        "authorization_request_count",
        "approved_authorization_count",
        "active_authorization_count",
        "capture_attempt_count",
        "captured_side_count",
        "redaction_attestation_count",
        "accepted_capture_receipt_count",
        "result_parity_proven_packet_count",
        "owner_approved_packet_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ]
    assert all(summary[field] == 0 for field in zero_fields)
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_capture_authorization_contract"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

