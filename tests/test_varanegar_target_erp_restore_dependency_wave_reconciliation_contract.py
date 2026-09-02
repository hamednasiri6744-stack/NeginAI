import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_restore_dependency_wave_reconciliation_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_restore_dependency_wave_reconciliation_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "restore_dependency.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_dependency_wave_totals():
    summary = load()["summary"]
    assert (summary["module_count"], summary["module_dependency_edge_count"], summary["restore_wave_count"]) == (14, 38, 7)
    assert (summary["restore_stage_count"], summary["module_restore_stage_assignment_count"]) == (10, 140)
    assert (summary["reconciliation_dimension_count"], summary["edge_reconciliation_assignment_count"]) == (4, 152)
    assert (summary["wave_gate_count"], summary["wave_gate_assignment_count"]) == (14, 98)
    assert (summary["role_type_count"], summary["wave_role_assignment_count"]) == (5, 35)
    assert (summary["reconciliation_receipt_field_count"], summary["typed_outcome_count"]) == (20, 9)


def test_every_dependency_precedes_its_dependent_module():
    document = load()
    levels = {item["module_id"]: item["restore_wave_number"] for item in document["module_restore_plans"]}
    assert document["restore_waves"][0]["module_ids"] == ["platform"]
    for edge in document["module_dependency_edges"]:
        assert levels[edge["upstream_module_id"]] < levels[edge["downstream_module_id"]]
        assert edge["status"] == "UNRECONCILED_NO_RESTORE_EVIDENCE"


def test_every_module_stage_edge_dimension_and_wave_gate_is_covered():
    document = load()
    assert len({(x["module_id"], x["stage_id"]) for x in document["module_restore_stage_assignments"]}) == 140
    assert len({(x["dependency_edge_id"], x["reconciliation_dimension"]) for x in document["edge_reconciliation_assignments"]}) == 152
    assert len({(x["wave_id"], x["gate_id"]) for x in document["wave_gate_assignments"]}) == 98
    assert len({(x["wave_id"], x["role_type"]) for x in document["wave_role_assignments"]}) == 35


def test_fail_closed_restore_order_rules():
    rule = load()["restore_order_rule"]
    assert rule["dependency_must_be_reconciled_before_dependent_restore"] is True
    assert rule["service_start_or_schema_load_is_reconciliation"] is False
    assert rule["read_model_is_authoritative_restore_source"] is False
    assert rule["outbox_inbox_replay_allowed_before_idempotency_reconciliation"] is False
    assert rule["blocking_unknown_or_unreviewed_difference_allows_enablement"] is False
    assert rule["production_environment_restore_allowed"] is False
    assert rule["automatic_wave_promotion_or_service_enablement"] is False


def test_no_restore_reconciliation_or_enablement_claim():
    document = load()
    summary = document["summary"]
    for field in (
        "authorized_restore_wave_count",
        "restore_run_count",
        "reconciled_dependency_edge_count",
        "reconciled_module_count",
        "owner_approved_wave_count",
        "service_enabled_module_count",
        "recovery_ready_module_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ):
        assert summary[field] == 0
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_dependency_contract"] == 1404


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
