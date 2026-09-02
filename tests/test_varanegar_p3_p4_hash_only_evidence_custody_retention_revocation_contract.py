import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "custody.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_custody_contract_totals():
    summary = load()["summary"]
    assert (summary["capture_pair_count"], summary["capture_channel_count"], summary["cg05_receipt_slot_count"]) == (8, 16, 27)
    assert summary["custody_requirement_count"] == 54
    assert (summary["custody_metadata_field_count"], summary["custody_state_count"], summary["transition_rule_count"]) == (20, 9, 12)
    assert (summary["custody_gate_count"], summary["custody_gate_assignment_count"]) == (10, 540)
    assert (summary["custody_role_type_count"], summary["custody_role_assignment_count"]) == (4, 216)
    assert (summary["retention_rule_count"], summary["rejection_code_count"]) == (8, 12)


def test_every_channel_receipt_link_has_one_missing_custody_requirement():
    requirements = load()["custody_requirements"]
    keys = {(item["capture_channel_id"], item["cg05_receipt_slot_id"]) for item in requirements}
    assert len(keys) == len(requirements) == 54
    assert all(item["current_state"] == "MISSING" for item in requirements)
    assert all(item["custody_receipt_reference"] is None for item in requirements)


def test_gates_roles_and_transitions_fail_closed():
    document = load()
    assert all(item["status"] == "UNMET" for item in document["custody_gate_assignments"])
    assert all(item["status"] == "UNASSIGNED" for item in document["custody_role_assignments"])
    assert all(rule["automatic_promotion_allowed"] is False for rule in document["transition_rules"])
    assert document["custody_rule"]["expired_revoked_or_superseded_receipt_usable"] is False


def test_retention_preserves_hash_tombstone_but_not_raw_payload():
    document = load()
    assert len(document["retention_rules"]) == 8
    assert document["custody_rule"]["raw_payload_or_file_storage_allowed"] is False
    assert document["custody_rule"]["hash_only_tombstone_after_disposition_required"] is True
    assert "raw_business_values" in document["prohibited_persistence_categories"]
    assert "hash_only_tombstone" in document["allowed_persistence_categories"]


def test_no_custody_receipt_acceptance_parity_or_readiness_claim():
    document = load()
    summary = document["summary"]
    for field in (
        "created_custody_receipt_count",
        "transferred_custody_receipt_count",
        "accepted_current_custody_receipt_count",
        "expired_custody_receipt_count",
        "revoked_custody_receipt_count",
        "superseded_custody_receipt_count",
        "accepted_evidence_count",
        "comparison_handoff_ready_count",
        "result_parity_proven_packet_count",
        "cg05_closed_packet_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ):
        assert summary[field] == 0
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_custody_contract"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

