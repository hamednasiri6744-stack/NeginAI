import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p0_external_evidence_collection_activation_packets_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p0_external_evidence_collection_activation_packets_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "packets.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_p0_partition_and_pairs():
    summary = load()["summary"]
    assert (summary["activation_packet_count"], summary["covered_case_count"]) == (7, 49)
    assert (summary["candidate_bearing_packet_count"], summary["explicit_none_packet_count"]) == (3, 4)
    assert (summary["alias_or_new_action_packet_count"], summary["semantic_equivalence_packet_count"]) == (4, 3)
    assert (
        summary["same_kind_case_pair_count"],
        summary["failure_injection_pair_count"],
        summary["control_pair_count"],
    ) == (66, 20, 46)
    assert (summary["outcome_exact_pair_count"], summary["fully_exact_pair_count"], summary["exact_effect_family_set_pair_count"]) == (2, 0, 0)


def test_activation_dependencies():
    document = load()
    summary = document["summary"]
    assert (
        summary["receipt_slot_count"],
        summary["accountable_role_assignment_count"],
        summary["distinct_accountable_role_type_count"],
        summary["gate_assignment_count"],
    ) == (70, 14, 7, 35)
    assert all(len(packet["receipt_slot_ids"]) == 10 for packet in document["activation_packets"])
    assert all(len(packet["required_gate_ids"]) == 5 for packet in document["activation_packets"])


def test_all_packets_not_activated_and_zero_promotion():
    document = load()
    summary = document["summary"]
    assert all(packet["evidence_collection_activation_status"] == "NOT_ACTIVATED_EXTERNAL_EVIDENCE_MISSING" for packet in document["activation_packets"])
    assert all(packet["operational_execution_authorized"] is False for packet in document["activation_packets"])
    assert summary["named_owner_assignment_count"] == 0
    assert summary["role_accepted_receipt_count"] == 0
    assert summary["activated_packet_count"] == 0
    assert summary["accepted_route_decision_count"] == 0
    assert summary["executed_case_count"] == 0
    assert summary["owner_approved_case_count"] == 0
    assert summary["command_ready_module_count"] == 0
    assert summary["pilot_ready_module_count"] == 0
    assert summary["design_lower_bound_before_p0_activation"] == summary["design_lower_bound_after_p0_activation"] == 1404
    assert set(document["safety"].values()) == {0}


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
