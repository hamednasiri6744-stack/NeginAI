import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_alias_cross_lane_external_evidence_intake_queue_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_alias_cross_lane_external_evidence_intake_queue_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "queue.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_route_partition_and_cases():
    summary = load()["summary"]
    assert (summary["queue_item_count"], summary["covered_case_count"], summary["route_group_count"]) == (29, 203, 4)
    assert (
        summary["alias_or_new_action_packet_count"],
        summary["semantic_equivalence_packet_count"],
        summary["report_effect_and_result_parity_packet_count"],
        summary["export_effect_and_result_parity_packet_count"],
    ) == (9, 12, 5, 3)
    assert (
        summary["alias_or_new_action_case_count"],
        summary["semantic_equivalence_case_count"],
        summary["report_effect_and_result_parity_case_count"],
        summary["export_effect_and_result_parity_case_count"],
    ) == (63, 84, 35, 21)


def test_queue_is_external_and_zero_promotion():
    document = load()
    summary = document["summary"]
    assert summary["accountable_role_assignment_count"] == 58
    assert summary["named_owner_assignment_count"] == 0
    assert summary["received_evidence_receipt_count"] == 0
    assert summary["accepted_evidence_receipt_count"] == 0
    assert summary["accepted_route_decision_count"] == 0
    assert summary["accepted_case_disposition_count"] == 0
    assert summary["executed_case_count"] == 0
    assert summary["owner_approved_case_count"] == 0
    assert summary["command_ready_module_count"] == 0
    assert summary["pilot_ready_module_count"] == 0
    assert summary["design_lower_bound_before_intake_queue"] == summary["design_lower_bound_after_intake_queue"] == 1404
    assert all(row["counting_effect"] == "ZERO" for row in document["intake_queue"])
    assert set(document["safety"].values()) == {0}


def test_report_and_export_routes_require_report_gate():
    rows = load()["intake_queue"]
    bounded = [row for row in rows if row["priority_rank"] in {3, 4}]
    assert len(bounded) == 8
    assert all("CG-05" in row["required_gate_ids"] for row in bounded)
    assert all("frozen_fixture_result_parity_receipt" in row["required_evidence_receipts"] or "frozen_fixture_value_and_rowset_parity_receipt" in row["required_evidence_receipts"] for row in bounded)


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
