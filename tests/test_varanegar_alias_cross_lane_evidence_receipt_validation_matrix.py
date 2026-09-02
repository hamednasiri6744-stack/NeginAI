import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "matrix.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_slot_partition():
    summary = load()["summary"]
    assert (summary["intake_item_count"], summary["receipt_slot_count"]) == (29, 290)
    assert (
        summary["alias_or_new_action_receipt_slot_count"],
        summary["semantic_equivalence_receipt_slot_count"],
        summary["report_effect_and_result_receipt_slot_count"],
        summary["export_effect_and_result_receipt_slot_count"],
    ) == (90, 120, 50, 30)


def test_validation_schema_and_taxonomy():
    document = load()
    summary = document["summary"]
    assert summary["required_metadata_field_count"] == 14
    assert summary["rejection_code_count"] == 14
    assert summary["state_count"] == 8
    assert len({slot["receipt_slot_id"] for slot in document["receipt_slots"]}) == 290
    assert "RAW_SENSITIVE_VALUE_DETECTED" in document["rejection_codes"]
    assert "redaction_attestation" in document["required_metadata_fields"]


def test_p3_per_item_failure_receipts_are_multiclass_and_include_cg05():
    document = load()
    rows = [slot for slot in document["receipt_slots"] if slot["receipt_type"] == "failure_stage_and_per_item_outcome_receipt"]
    assert len(rows) == 5
    assert all(set(row["receipt_classes"]) == {"TRANSACTION_FAILURE_RECOVERY", "RESULT_RENDER_EXPORT", "SEMANTIC_EFFECT"} for row in rows)
    assert all(row["applicable_gate_ids"] == ["CG-02", "CG-03", "CG-05", "CG-04"] for row in rows)
    assert document["summary"]["multi_class_receipt_slot_count"] == 14
    assert document["summary"]["cg05_scoped_receipt_slot_count"] == 27


def test_all_slots_missing_and_zero_promotion():
    document = load()
    summary = document["summary"]
    assert all(slot["current_state"] == "MISSING" and slot["readiness_effect"] == "ZERO" for slot in document["receipt_slots"])
    assert summary["received_receipt_count"] == 0
    assert summary["hash_validated_receipt_count"] == 0
    assert summary["content_validated_receipt_count"] == 0
    assert summary["role_accepted_receipt_count"] == 0
    assert summary["accepted_route_decision_count"] == 0
    assert summary["executed_case_count"] == 0
    assert summary["owner_approved_case_count"] == 0
    assert summary["command_ready_module_count"] == 0
    assert summary["pilot_ready_module_count"] == 0
    assert summary["design_lower_bound_before_receipt_matrix"] == summary["design_lower_bound_after_receipt_matrix"] == 1404
    assert set(document["safety"].values()) == {0}


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
