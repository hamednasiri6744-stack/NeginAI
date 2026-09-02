import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_fiscal_period_synthetic_reference_evaluator_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "fiscal-reference.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_all_vectors_pass_with_distinct_outcomes():
    summary = load()["summary"]
    assert summary["positive_vector_count"] == summary["positive_pass_count"] == 5
    assert summary["negative_vector_count"] == summary["negative_pass_count"] == 18
    assert summary["total_vector_count"] == summary["total_pass_count"] == 23
    assert summary["distinct_typed_outcome_count"] >= 14


def test_precedence_is_explicit():
    assert load()["outcome_precedence"] == ["SCHEMA", "SCOPE", "VERSION", "STATE", "LOCK_PATH_COVERAGE", "BLOCKING_UNKNOWN", "CLOSE_DEPENDENCIES", "NUMBERING_ROLLOVER", "ADJUSTMENT", "REOPEN", "RECLOSE", "ACCEPTED"]


def test_no_operational_or_readiness_claim():
    data = load()
    summary = data["summary"]
    for name in ("operational_period_lock_or_posting_implementation_count", "operational_period_ledger_document_balance_or_entry_read_count", "close_reopen_adjustment_reversal_or_posting_run_count", "accepted_operational_receipt_count", "command_ready_module_count", "pilot_ready_module_count"):
        assert summary[name] == 0
    assert set(data["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343
    assert summary["design_lower_bound_after_reference_evaluator"] == 1404


def test_source_manifest_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
