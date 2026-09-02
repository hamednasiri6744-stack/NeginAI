import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_fiscal_period_close_reopen_adjustment_lock_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_fiscal_period_close_reopen_adjustment_lock_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "fiscal-period.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_totals():
    summary = load()["summary"]
    assert (summary["module_count"], summary["fiscal_period_dimension_count"], summary["module_dimension_assignment_count"]) == (14, 14, 196)
    assert (summary["lifecycle_stage_count"], summary["module_stage_assignment_count"]) == (12, 168)
    assert (summary["fiscal_lock_policy_field_count"], summary["close_receipt_field_count"], summary["reopen_receipt_field_count"], summary["adjustment_receipt_field_count"]) == (24, 22, 22, 22)
    assert (summary["failure_case_count"], summary["module_failure_assignment_count"]) == (18, 252)
    assert (summary["gate_count"], summary["module_gate_assignment_count"]) == (24, 336)
    assert (summary["role_type_count"], summary["module_role_assignment_count"], summary["typed_outcome_count"]) == (7, 98, 14)


def test_every_module_has_full_coverage():
    data = load()
    module_ids = {item["module_id"] for item in data["module_fiscal_period_plans"]}
    assert len(module_ids) == 14
    for module_id in module_ids:
        assert len({x["dimension"] for x in data["module_dimension_assignments"] if x["module_id"] == module_id}) == 14
        assert len({x["stage_id"] for x in data["module_stage_assignments"] if x["module_id"] == module_id}) == 12
        assert len({x["failure_case_id"] for x in data["module_failure_assignments"] if x["module_id"] == module_id}) == 18
        assert len({x["gate_id"] for x in data["module_gate_assignments"] if x["module_id"] == module_id}) == 24
        assert len({x["role_type"] for x in data["module_role_assignments"] if x["module_id"] == module_id}) == 7


def test_rules_are_fail_closed():
    for value in load()["fiscal_period_rule"].values():
        assert value is False


def test_no_runtime_or_readiness_claim():
    data = load()
    summary = data["summary"]
    for name in ("operational_period_ledger_document_balance_or_entry_read_count", "fiscal_policy_approved_count", "period_close_or_reopen_run_count", "adjusting_reversing_or_late_posting_run_count", "reconciliation_or_rollover_run_count", "accepted_operational_receipt_count", "owner_approved_module_count", "command_ready_module_count", "pilot_ready_module_count"):
        assert summary[name] == 0
    assert set(data["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_fiscal_period_contract"] == 1404


def test_source_manifest_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
