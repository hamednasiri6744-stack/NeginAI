import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p1_p4_external_evidence_activation_sequence_matrix_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p1_p4_external_evidence_activation_sequence_matrix_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "sequence.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_scope_routes_and_pairs():
    summary = load()["summary"]
    assert (summary["lane_count"], summary["sequence_item_count"], summary["covered_case_count"]) == (4, 22, 154)
    assert (summary["candidate_bearing_packet_count"], summary["explicit_none_packet_count"]) == (17, 5)
    assert (
        summary["alias_or_new_action_packet_count"],
        summary["semantic_equivalence_packet_count"],
        summary["report_effect_and_result_packet_count"],
        summary["export_effect_and_result_packet_count"],
    ) == (5, 9, 5, 3)
    assert (
        summary["same_kind_case_pair_count"],
        summary["failure_injection_pair_count"],
        summary["control_pair_count"],
    ) == (180, 58, 122)
    assert (summary["outcome_exact_pair_count"], summary["fully_exact_pair_count"], summary["exact_effect_family_set_pair_count"]) == (2, 0, 0)


def test_lane_partition_and_gate_burden():
    document = load()
    lane_values = [
        (row["packet_count"], row["case_count"], row["receipt_slot_count"], row["accountable_role_assignment_count"], row["gate_assignment_count"])
        for row in document["lane_sequence"]
    ]
    assert lane_values == [(8, 56, 80, 16, 40), (6, 42, 60, 12, 30), (5, 35, 50, 10, 30), (3, 21, 30, 6, 15)]
    summary = document["summary"]
    assert (summary["receipt_slot_count"], summary["accountable_role_assignment_count"], summary["gate_assignment_count"]) == (220, 44, 115)
    assert (summary["distinct_accountable_role_type_count"], summary["cg05_result_parity_packet_count"]) == (12, 8)


def test_cg05_is_mandatory_for_p3_p4_only():
    rows = load()["packet_sequence"]
    assert all(row["requires_cg05_result_parity"] == (row["lane"] in {"P3", "P4"}) for row in rows)
    assert sum(row["requires_cg05_result_parity"] for row in rows) == 8


def test_all_packets_not_activated_and_zero_promotion():
    document = load()
    summary = document["summary"]
    assert all(row["activated_for_evidence_collection"] is False for row in document["packet_sequence"])
    assert all(row["operational_execution_authorized"] is False and row["readiness_effect"] == "ZERO" for row in document["packet_sequence"])
    assert summary["named_owner_assignment_count"] == 0
    assert summary["role_accepted_receipt_count"] == 0
    assert summary["activated_packet_count"] == 0
    assert summary["accepted_route_decision_count"] == 0
    assert summary["executed_case_count"] == 0
    assert summary["owner_approved_case_count"] == 0
    assert summary["command_ready_module_count"] == 0
    assert summary["pilot_ready_module_count"] == 0
    assert summary["design_lower_bound_before_p1_p4_sequence"] == summary["design_lower_bound_after_p1_p4_sequence"] == 1404
    assert set(document["safety"].values()) == {0}


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
