import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_backup_restore_rehearsal_evidence_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_backup_restore_rehearsal_evidence_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "restore.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_recovery_contract_totals():
    summary = load()["summary"]
    assert (summary["module_count"], summary["recovery_asset_class_count"], summary["module_asset_obligation_count"]) == (14, 6, 84)
    assert (summary["rehearsal_scenario_count"], summary["module_scenario_assignment_count"]) == (12, 168)
    assert (summary["recovery_objective_field_count"], summary["rehearsal_evidence_field_count"]) == (18, 20)
    assert (summary["recovery_gate_count"], summary["module_gate_assignment_count"]) == (14, 196)
    assert (summary["recovery_role_type_count"], summary["module_role_assignment_count"]) == (5, 70)
    assert summary["typed_outcome_count"] == 8


def test_every_module_covers_all_assets_scenarios_and_gates():
    document = load()
    modules = {item["module_id"] for item in document["module_recovery_contracts"]}
    assert len(modules) == 14
    for module_id in modules:
        assert len({x["asset_class"] for x in document["module_asset_obligations"] if x["module_id"] == module_id}) == 6
        assert len({x["scenario_id"] for x in document["module_scenario_assignments"] if x["module_id"] == module_id}) == 12
        assert len({x["gate_id"] for x in document["module_gate_assignments"] if x["module_id"] == module_id}) == 14


def test_all_targets_owners_and_rehearsals_are_unapproved_or_unexecuted():
    document = load()
    assert all(item["rpo_target_status"] == "UNAPPROVED" for item in document["module_recovery_contracts"])
    assert all(item["rto_target_status"] == "UNAPPROVED" for item in document["module_recovery_contracts"])
    assert all(item["status"] == "UNEXECUTED" for item in document["module_scenario_assignments"])
    assert all(item["status"] == "UNMET" for item in document["module_gate_assignments"])
    assert all(item["status"] == "UNASSIGNED" for item in document["module_role_assignments"])


def test_restore_success_requires_reconciliation_not_boot_only():
    rule = load()["rehearsal_rule"]
    assert rule["service_started_is_restore_success"] is False
    assert rule["schema_load_is_restore_success"] is False
    assert rule["cross_module_reconciliation_required"] is True
    assert rule["rpo_rto_measured_not_assumed"] is True
    assert rule["production_restore_allowed"] is False


def test_no_backup_restore_target_approval_or_readiness_claim():
    document = load()
    summary = document["summary"]
    for field in (
        "approved_rpo_target_count",
        "approved_rto_target_count",
        "backup_set_created_or_read_count",
        "restore_rehearsal_run_count",
        "passed_restore_rehearsal_count",
        "reconciled_restore_count",
        "owner_approved_module_count",
        "recovery_ready_module_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ):
        assert summary[field] == 0
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_restore_contract"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

