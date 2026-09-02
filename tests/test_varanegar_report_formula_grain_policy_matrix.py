import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_report_formula_grain_policy_matrix_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_matrix_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "matrix.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_result_owner_partition():
    summary = load()["summary"]
    assert summary["result_owner_surface_count"] == 11
    assert summary["query_bound_result_owner_count"] == 8
    assert summary["external_template_result_owner_count"] == 2
    assert summary["typed_bank_summary_result_owner_count"] == 1


def test_policy_obligations_and_packet_schema():
    data = load()
    assert data["summary"]["policy_dimension_count"] == 14
    assert data["summary"]["surface_policy_obligation_count"] == 123
    assert len(data["formula_packet_schema"]["required_fields"]) == 20


def test_fifty_fixtures_are_design_only():
    summary = load()["summary"]
    assert summary["designed_golden_fixture_count"] == 50
    assert summary["executed_golden_fixture_count"] == 0
    assert summary["owner_approved_formula_surface_count"] == 0
    assert summary["result_parity_proven_surface_count"] == 0


def test_template_and_bank_evidence_are_not_overclaimed():
    rows = {row["contract_id"]: row for row in load()["result_owner_formula_grain_matrix"]}
    assert rows["RPT-11"]["grain_policy_status"] == "UNKNOWN_UNTIL_TEMPLATE_EXTRACTION"
    assert rows["RPT-12"]["grain_policy_status"] == "UNKNOWN_UNTIL_TEMPLATE_EXTRACTION"
    assert "RUNTIME_AND_OWNER_PARITY_MISSING" in rows["RPT-19"]["formula_policy_status"]


def test_safe_and_not_ready():
    data = load()
    assert set(data["safety"].values()) == {0}
    assert data["scope"]["cg05_closed"] is False
    assert data["summary"]["command_ready_module_count"] == data["summary"]["pilot_ready_module_count"] == 0
