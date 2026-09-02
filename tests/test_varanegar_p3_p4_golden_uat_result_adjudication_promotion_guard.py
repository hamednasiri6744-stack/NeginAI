import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "adjudication.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_scope_and_assignment_totals():
    summary = load()["summary"]
    assert (summary["packet_count"], summary["p3_packet_count"], summary["p4_packet_count"]) == (8, 5, 3)
    assert (summary["covered_golden_case_count"], summary["diagnostic_outcome_count"]) == (56, 4)
    assert (summary["adjudication_route_count"], summary["outcome_case_assignment_count"]) == (32, 224)
    assert (summary["promotion_guard_count"], summary["promotion_guard_assignment_count"]) == (12, 96)
    assert (summary["parity_dimension_assignment_count"], summary["cg05_receipt_assignment_count"]) == (160, 27)


def test_only_hash_evidence_match_can_enter_cg05_acceptance_review():
    rules = load()["outcome_adjudication_rules"]
    eligible = [rule for rule in rules if rule["can_enter_cg05_acceptance_review"]]
    assert [rule["diagnostic_outcome"] for rule in eligible] == ["MATCH_CONFIRMED_BY_ACCEPTED_HASH_ONLY_EVIDENCE"]
    assert all(rule["automatic_cg05_closure"] is False for rule in rules)
    assert all(rule["automatic_readiness_promotion"] is False for rule in rules)


def test_exception_recollection_and_unexplained_paths_remain_blocking():
    by_outcome = {rule["diagnostic_outcome"]: rule for rule in load()["outcome_adjudication_rules"]}
    assert by_outcome["EXPLAINED_OWNER_APPROVED_VERSIONED_EXCEPTION"]["cg05_effect"] == "KEEP_OPEN_REQUIRES_SEPARATE_RISK_ACCEPTANCE"
    assert by_outcome["INVALID_OR_STALE_EVIDENCE_RECOLLECTION_REQUIRED"]["cg05_effect"] == "KEEP_OPEN_RECOLLECT_CURRENT_EVIDENCE"
    assert by_outcome["UNEXPLAINED_DIFFERENCE_BLOCKS_CG05"]["cg05_effect"] == "HARD_BLOCK_CG05"


def test_all_current_adjudication_and_promotion_counts_zero():
    document = load()
    summary = document["summary"]
    zero_fields = [
        "adjudicated_route_count",
        "accepted_match_route_count",
        "accepted_exception_route_count",
        "recollection_route_count",
        "unexplained_block_route_count",
        "cg05_acceptance_review_entered_packet_count",
        "cg05_closed_packet_count",
        "owner_approved_packet_count",
        "executed_case_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ]
    assert all(summary[field] == 0 for field in zero_fields)
    assert all(route["current_outcome"] is None for route in document["packet_adjudication_routes"])
    assert all(route["readiness_effect"] == "ZERO" for route in document["packet_adjudication_routes"])
    assert set(document["safety"].values()) == {0}


def test_guard_order_starts_with_manifest_and_ends_with_pilot_boundary():
    guards = load()["promotion_guards"]
    assert guards[0]["guard_id"] == "PG-01" and guards[0]["guard"] == "current_hash_pinned_fixture_output_and_comparison_manifests"
    assert guards[-1]["guard_id"] == "PG-12" and guards[-1]["guard"] == "separate_command_and_pilot_readiness_decision"
    assert all(guard["currently_satisfied"] is False for guard in guards)


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

