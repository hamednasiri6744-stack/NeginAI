import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p3_p4_evidence_invalidation_reopen_propagation_matrix_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p3_p4_evidence_invalidation_reopen_propagation_matrix_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "propagation.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_invalidation_and_graph_totals():
    summary = load()["summary"]
    assert (summary["packet_count"], summary["custody_requirement_count"], summary["invalidation_cause_count"]) == (8, 54, 12)
    assert summary["cause_requirement_assignment_count"] == 648
    assert (summary["requirement_pair_edge_count"], summary["requirement_profile_edge_count"], summary["requirement_receipt_slot_edge_count"]) == (54, 54, 54)
    assert (summary["pair_promotion_guard_edge_count"], summary["receipt_slot_packet_edge_count"]) == (96, 27)
    assert summary["total_dependency_edge_count"] == 285
    assert summary["reopen_action_count"] == 8


def test_every_requirement_maps_to_exactly_one_pair_profile_and_slot():
    document = load()
    for key in ("requirement_pair_edges", "requirement_profile_edges", "requirement_receipt_slot_edges"):
        edges = document[key]
        assert len(edges) == 54
        assert len({edge["custody_requirement_id"] for edge in edges}) == 54


def test_every_pair_maps_to_all_twelve_promotion_guards():
    edges = load()["pair_promotion_guard_edges"]
    by_pair = {}
    for edge in edges:
        by_pair.setdefault(edge["capture_pair_id"], set()).add(edge["promotion_guard_id"])
    assert len(by_pair) == 8
    assert all(len(guards) == 12 for guards in by_pair.values())


def test_all_causes_fail_closed_and_no_event_is_observed():
    document = load()
    assert all(cause["effect"] == "INVALIDATE_AND_REOPEN_DEPENDENT_GATES" for cause in document["invalidation_causes"])
    assert all(item["current_status"] == "NO_EVENT_OBSERVED" for item in document["cause_requirement_assignments"])
    assert all(action["automatic_reacceptance_allowed"] is False for action in document["reopen_actions"])


def test_no_invalidation_reacceptance_parity_or_readiness_claim():
    document = load()
    summary = document["summary"]
    for field in (
        "observed_invalidation_event_count",
        "invalidated_custody_requirement_count",
        "reopened_handoff_pair_count",
        "invalidated_adapter_profile_count",
        "reopened_cg05_receipt_slot_count",
        "reopened_promotion_guard_count",
        "reaccepted_evidence_count",
        "result_parity_proven_packet_count",
        "cg05_closed_packet_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ):
        assert summary[field] == 0
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_invalidation_matrix"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

