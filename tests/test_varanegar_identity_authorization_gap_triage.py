import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_identity_authorization_gap_triage_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_identity_authorization_gap_triage_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "triage.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_endpoint_and_verb_split():
    summary = load()["summary"]
    assert summary["declaration_gap_endpoint_count"] == 60
    assert summary["mutating_declaration_gap_endpoint_count"] == 38
    assert summary["read_declaration_gap_endpoint_count"] == 22
    assert summary["gap_http_verb_counts"] == {"DELETE": 1, "GET": 22, "POST": 31, "PUT": 6}


def test_manual_signal_classes_do_not_claim_enforcement():
    summary = load()["summary"]
    assert summary["named_manual_authorization_decision_candidate_count"] == 0
    assert summary["authorization_data_only_candidate_count"] == 6
    assert summary["identity_context_only_candidate_count"] == 3
    assert summary["no_named_decision_data_or_identity_signal_count"] == 51


def test_scope_mismatch_is_one_observed_class():
    summary = load()["summary"]
    assert summary["scope_consistency_mismatch_count"] == 58
    assert summary["membership_user_scope_mismatch_count"] == 58
    assert summary["other_scope_mismatch_count"] == 0


def test_triage_and_role_uat_stay_unaccepted():
    summary = load()["summary"]
    assert summary["triage_lane_count"] == 7
    assert summary["triage_required_unit_count"] == 139
    assert summary["triage_current_accepted_unit_count"] == 0
    assert summary["synthetic_role_uat_case_count"] == 184
    assert summary["owner_approved_role_uat_case_count"] == 0


def test_no_incident_or_readiness_claim():
    data = load()
    assert data["scope"]["anonymous_reachability_or_incident_claimed"] is False
    assert data["scope"]["cg01_closed"] is False
    assert data["summary"]["runtime_authorization_proven_module_count"] == 0
    assert data["summary"]["command_ready_module_count"] == data["summary"]["pilot_ready_module_count"] == 0
    assert set(data["safety"].values()) == {0}
