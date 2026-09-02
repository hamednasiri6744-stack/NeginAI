import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p3_p4_capture_to_comparison_evidence_handoff_matrix_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p3_p4_capture_to_comparison_evidence_handoff_matrix_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "handoff.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_handoff_mapping_totals():
    summary = load()["summary"]
    assert (summary["packet_count"], summary["capture_channel_count"], summary["capture_pair_count"]) == (8, 16, 8)
    assert (summary["cg05_receipt_slot_count"], summary["channel_receipt_slot_link_count"]) == (27, 54)
    assert (summary["parity_dimension_count"], summary["channel_dimension_link_count"]) == (20, 320)
    assert (summary["adapter_profile_count"], summary["profile_channel_link_count"]) == (8, 16)
    assert (summary["handoff_envelope_field_count"], summary["handoff_gate_count"], summary["handoff_gate_assignment_count"]) == (20, 12, 96)


def test_each_pair_has_legacy_target_and_one_adapter_profile():
    pairs = load()["capture_pairs"]
    assert len(pairs) == 8
    assert all(set(pair["capture_channel_ids_by_side"]) == {"LEGACY_REFERENCE", "TARGET_CANDIDATE"} for pair in pairs)
    assert len({pair["adapter_profile_id"] for pair in pairs}) == 8
    assert all(pair["handoff_status"] == "NOT_READY_NO_AUTHORIZED_CAPTURE" for pair in pairs)


def test_link_sets_are_complete_and_unique():
    document = load()
    receipt_links = document["channel_receipt_slot_links"]
    dimension_links = document["channel_dimension_links"]
    assert len({(x["capture_channel_id"], x["cg05_receipt_slot_id"]) for x in receipt_links}) == 54
    assert len({(x["capture_channel_id"], x["parity_dimension_id"]) for x in dimension_links}) == 320
    assert all(x["accepted_evidence_count"] == 0 for x in receipt_links + dimension_links)


def test_all_handoff_gates_are_unmet_and_fail_closed():
    document = load()
    assert all(item["status"] == "UNMET" for item in document["handoff_gate_assignments"])
    assert all(gate["failure_effect"] == "BLOCK_COMPARISON_HANDOFF" for gate in document["handoff_gates"])
    assert document["handoff_rule"]["payload_transfer_allowed"] is False
    assert document["handoff_rule"]["hash_count_status_reference_only"] is True


def test_no_handoff_comparison_receipt_or_readiness_claim():
    document = load()
    summary = document["summary"]
    for field in (
        "ready_handoff_count",
        "accepted_handoff_count",
        "adapter_request_count",
        "comparison_run_count",
        "emitted_receipt_count",
        "accepted_receipt_count",
        "result_parity_proven_packet_count",
        "cg05_closed_packet_count",
        "owner_approved_packet_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ):
        assert summary[field] == 0
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_handoff_matrix"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

