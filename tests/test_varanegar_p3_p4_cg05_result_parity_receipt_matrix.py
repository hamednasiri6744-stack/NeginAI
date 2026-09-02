import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "matrix.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_packet_and_dimension_partition():
    summary = load()["summary"]
    assert (summary["packet_count"], summary["p3_packet_count"], summary["p4_packet_count"], summary["covered_case_count"]) == (8, 5, 3, 56)
    assert (
        summary["policy_dimension_count"],
        summary["output_specific_dimension_count"],
        summary["required_parity_dimension_count"],
        summary["required_parity_dimension_assignment_count"],
    ) == (14, 6, 20, 160)


def test_cg05_receipt_scope_includes_multiclass_per_item_receipts():
    document = load()
    summary = document["summary"]
    assert (
        summary["cg05_receipt_slot_count"],
        summary["p3_cg05_receipt_slot_count"],
        summary["p4_cg05_receipt_slot_count"],
        summary["multi_class_cg05_receipt_slot_count"],
    ) == (27, 15, 12, 5)
    assert all(len(packet["cg05_receipt_slot_ids"]) == (3 if packet["lane"] == "P3" else 4) for packet in document["cg05_packets"])
    p3_receipts = [receipt for packet in document["cg05_packets"] if packet["lane"] == "P3" for receipt in packet["cg05_receipt_types"]]
    assert p3_receipts.count("failure_stage_and_per_item_outcome_receipt") == 5


def test_effect_and_result_gap_is_explicit():
    summary = load()["summary"]
    assert (summary["candidate_case_pair_count"], summary["exact_effect_family_set_pair_count"]) == (52, 0)
    assert (summary["newer_file_or_artifact_receipt_pair_count"], summary["baseline_file_or_artifact_receipt_pair_count"]) == (52, 18)
    assert (summary["newer_render_or_export_completion_pair_count"], summary["baseline_render_or_export_completion_pair_count"]) == (52, 2)
    assert (summary["newer_per_item_partial_outcome_pair_count"], summary["baseline_per_item_partial_outcome_pair_count"]) == (52, 0)
    assert (summary["newer_result_or_content_parity_pair_count"], summary["baseline_result_or_content_parity_pair_count"]) == (0, 6)


def test_all_packets_open_and_zero_promotion():
    document = load()
    summary = document["summary"]
    assert all(packet["current_status"] == "OPEN_CG05_RECEIPTS_AND_DIMENSION_DISPOSITIONS_REQUIRED" for packet in document["cg05_packets"])
    assert all(packet["result_parity_proven"] is False and packet["render_or_export_parity_proven"] is False for packet in document["cg05_packets"])
    assert summary["accepted_parity_dimension_count"] == 0
    assert summary["role_accepted_cg05_receipt_count"] == 0
    assert summary["result_parity_proven_packet_count"] == 0
    assert summary["owner_approved_packet_count"] == 0
    assert summary["executed_case_count"] == 0
    assert summary["command_ready_module_count"] == 0
    assert summary["pilot_ready_module_count"] == 0
    assert summary["design_lower_bound_before_cg05_matrix"] == summary["design_lower_bound_after_cg05_matrix"] == 1404
    assert set(document["safety"].values()) == {0}


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
