import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_transaction_owner_saga_compensation_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_transaction_owner_saga_compensation_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "transaction.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_contract_totals():
    summary = load()["summary"]
    assert (summary["module_count"], summary["target_command_count"], summary["module_dependency_edge_count"]) == (14, 49, 38)
    assert summary["command_dependency_coordination_assignment_count"] == 159
    assert (summary["transaction_pattern_count"], summary["command_pattern_candidate_assignment_count"]) == (4, 196)
    assert (summary["transaction_boundary_field_count"], summary["saga_step_receipt_field_count"], summary["compensation_receipt_field_count"]) == (18, 20, 18)
    assert (summary["failure_stage_count"], summary["command_failure_stage_assignment_count"]) == (12, 588)
    assert (summary["gate_count"], summary["command_gate_assignment_count"]) == (16, 784)
    assert (summary["role_type_count"], summary["command_role_assignment_count"], summary["typed_outcome_count"]) == (6, 294, 10)


def test_every_command_has_patterns_failures_gates_and_roles():
    document = load(); command_ids = {x["target_command_id"] for x in document["target_command_transaction_contracts"]}
    assert len(command_ids) == 49
    for command_id in command_ids:
        assert len({x["transaction_pattern"] for x in document["command_pattern_candidate_assignments"] if x["target_command_id"] == command_id}) == 4
        assert len({x["failure_stage_id"] for x in document["command_failure_stage_assignments"] if x["target_command_id"] == command_id}) == 12
        assert len({x["gate_id"] for x in document["command_gate_assignments"] if x["target_command_id"] == command_id}) == 16
        assert len({x["role_type"] for x in document["command_role_assignments"] if x["target_command_id"] == command_id}) == 6


def test_transaction_and_saga_rules_fail_closed():
    rule = load()["transaction_and_saga_rule"]
    assert rule["distributed_transaction_is_default"] is False
    assert rule["cross_module_direct_table_write_allowed"] is False
    assert rule["child_or_participant_success_is_parent_success"] is False
    assert rule["external_effect_allowed_before_durable_local_commit_receipt"] is False
    assert rule["commit_unknown_allows_retry_or_compensation_without_reconciliation"] is False
    assert rule["compensation_is_database_rollback"] is False
    assert rule["compensation_must_be_idempotent_versioned_and_audited"] is True
    assert rule["noncompensable_unknown_effect_requires_manual_quarantine"] is True
    assert rule["automatic_pattern_selection_or_readiness"] is False


def test_no_selection_runtime_compensation_or_readiness_claim():
    document = load(); summary = document["summary"]
    for field in ("selected_transaction_pattern_count", "named_transaction_owner_count", "fault_injection_run_count", "runtime_atomicity_proven_command_count", "saga_completed_command_count", "compensation_executed_or_accepted_count", "owner_approved_command_count", "command_ready_count", "pilot_ready_module_count"):
        assert summary[field] == 0
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_transaction_contract"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
