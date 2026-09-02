import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_command_idempotency_outbox_inbox_convergence_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_command_idempotency_outbox_inbox_convergence_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "command_convergence.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_contract_totals():
    summary = load()["summary"]
    assert (summary["module_count"], summary["target_command_count"]) == (14, 49)
    assert (summary["command_envelope_field_count"], summary["idempotency_receipt_field_count"], summary["outbox_record_field_count"], summary["inbox_record_field_count"]) == (22, 20, 16, 14)
    assert (summary["failure_stage_count"], summary["command_failure_stage_assignment_count"]) == (14, 686)
    assert (summary["convergence_dimension_count"], summary["command_convergence_assignment_count"]) == (8, 392)
    assert (summary["command_gate_count"], summary["command_gate_assignment_count"]) == (16, 784)
    assert (summary["role_type_count"], summary["command_role_assignment_count"], summary["typed_outcome_count"]) == (5, 245, 10)


def test_every_command_has_full_failure_convergence_gate_and_role_coverage():
    document = load()
    command_ids = {item["target_command_id"] for item in document["target_commands"]}
    assert len(command_ids) == 49
    for command_id in command_ids:
        assert len({x["failure_stage_id"] for x in document["command_failure_stage_assignments"] if x["target_command_id"] == command_id}) == 14
        assert len({x["convergence_dimension"] for x in document["command_convergence_assignments"] if x["target_command_id"] == command_id}) == 8
        assert len({x["gate_id"] for x in document["command_gate_assignments"] if x["target_command_id"] == command_id}) == 16
        assert len({x["role_type"] for x in document["command_role_assignments"] if x["target_command_id"] == command_id}) == 5


def test_idempotency_and_message_rules_are_fail_closed():
    rule = load()["idempotency_and_convergence_rule"]
    assert rule["same_key_same_fingerprint_returns_original_receipt"] is True
    assert rule["same_key_different_fingerprint_is_conflict"] is True
    assert rule["attempt_number_or_retry_may_change_idempotency_key"] is False
    assert rule["business_effect_receipt_and_outbox_share_transaction_owner"] is True
    assert rule["commit_unknown_allows_blind_retry"] is False
    assert rule["consumer_duplicate_delivery_may_create_new_effect"] is False
    assert rule["recovery_replay_allowed_before_restore_and_watermark_reconciliation"] is False
    assert rule["raw_command_payload_or_business_values_may_be_persisted_in_evidence"] is False
    assert rule["automatic_command_or_pilot_readiness"] is False


def test_no_implementation_fault_run_or_readiness_claim():
    document = load()
    summary = document["summary"]
    for field in (
        "implemented_idempotency_contract_count",
        "fault_injection_run_count",
        "same_key_replay_proven_command_count",
        "outbox_atomicity_proven_command_count",
        "inbox_convergence_proven_command_count",
        "unknown_outcome_reconciled_command_count",
        "owner_approved_command_count",
        "command_ready_count",
        "pilot_ready_module_count",
    ):
        assert summary[field] == 0
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_convergence_contract"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
