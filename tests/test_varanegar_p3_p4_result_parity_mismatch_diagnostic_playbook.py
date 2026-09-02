import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "playbook.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_playbook_and_assignment_totals():
    summary = load()["summary"]
    assert (
        summary["diagnostic_playbook_count"],
        summary["minimum_step_count"],
        summary["diagnostic_step_assignment_count"],
        summary["diagnostic_outcome_count"],
    ) == (10, 10, 100, 4)
    assert (summary["fixture_contract_count"], summary["covered_golden_case_count"]) == (8, 56)
    assert (summary["playbook_packet_assignment_count"], summary["playbook_golden_case_assignment_count"], summary["parity_dimension_link_count"]) == (72, 504, 34)


def test_lane_specific_render_and_export_playbooks():
    playbooks = load()["diagnostic_playbooks"]
    render = next(row for row in playbooks if row["scenario"] == "REPORT_RENDER_PRESENTATION_OR_COMPLETION_MISMATCH")
    export = next(row for row in playbooks if row["scenario"] == "EXPORT_SCHEMA_FORMAT_ENCODING_OR_LOCALE_MISMATCH")
    assert (render["applicable_lanes"], render["applicable_packet_count"]) == (["P3"], 5)
    assert (export["applicable_lanes"], export["applicable_packet_count"]) == (["P4"], 3)


def test_stop_rule_has_no_repair_or_replay():
    document = load()
    assert "do not repair, replay, recapture or promote automatically" in document["stop_rule"]
    assert all(row["repair_or_replay_performed_count"] == 0 for row in document["diagnostic_playbooks"])
    assert all(row["current_status"] == "DESIGNED_NOT_RUN_NO_CAPTURE_AUTHORIZATION" for row in document["diagnostic_playbooks"])


def test_all_runs_and_promotions_zero():
    document = load()
    summary = document["summary"]
    assert summary["diagnostic_run_count"] == 0
    assert summary["match_confirmed_count"] == 0
    assert summary["accepted_exception_count"] == 0
    assert summary["invalid_evidence_count"] == 0
    assert summary["unexplained_block_count"] == 0
    assert summary["repair_or_replay_performed_count"] == 0
    assert summary["owner_approved_resolution_count"] == 0
    assert summary["result_parity_proven_packet_count"] == 0
    assert summary["executed_case_count"] == 0
    assert summary["command_ready_module_count"] == 0
    assert summary["pilot_ready_module_count"] == 0
    assert summary["design_lower_bound_before_diagnostic_playbook"] == summary["design_lower_bound_after_diagnostic_playbook"] == 1404
    assert set(document["safety"].values()) == {0}


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
