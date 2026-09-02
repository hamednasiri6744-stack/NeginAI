import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_alias_cross_lane_role_handoff_worklist_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_alias_cross_lane_role_handoff_worklist_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "worklist.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_role_assignment_totals():
    summary = load()["summary"]
    assert summary["role_worklist_count"] == 13
    assert summary["role_packet_assignment_count"] == 58
    assert summary["role_case_assignment_count"] == 406
    assert summary["role_receipt_slot_assignment_count"] == 580
    assert (
        summary["underlying_intake_item_count"],
        summary["underlying_case_count"],
        summary["underlying_receipt_slot_count"],
    ) == (29, 203, 290)


def test_worklists_are_unassigned_and_non_promoting():
    document = load()
    summary = document["summary"]
    assert summary["owner_roster_field_count"] == 10
    assert summary["named_owner_assignment_count"] == 0
    assert summary["accepted_owner_roster_count"] == 0
    assert summary["received_receipt_count"] == 0
    assert summary["role_accepted_receipt_count"] == 0
    assert summary["accepted_route_decision_count"] == 0
    assert summary["executed_case_count"] == 0
    assert summary["owner_approved_case_count"] == 0
    assert summary["command_ready_module_count"] == 0
    assert summary["pilot_ready_module_count"] == 0
    assert summary["design_lower_bound_before_role_handoff"] == summary["design_lower_bound_after_role_handoff"] == 1404
    assert all(row["handoff_status"] == "UNASSIGNED_NAMED_OWNER" and row["readiness_effect"] == "ZERO" for row in document["role_worklists"])
    assert set(document["safety"].values()) == {0}


def test_receipt_slot_hashes_current():
    for row in load()["role_worklists"]:
        payload = "\n".join(sorted(row["receipt_slot_ids"])).encode("utf-8")
        assert hashlib.sha256(payload).hexdigest() == row["receipt_slot_id_set_sha256"]


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
