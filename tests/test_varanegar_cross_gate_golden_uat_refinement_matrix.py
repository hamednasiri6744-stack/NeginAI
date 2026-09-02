import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_cross_gate_golden_uat_refinement_matrix_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_cross_gate_golden_uat_refinement_matrix_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "matrix.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_count_and_lane_split():
    summary = load()["summary"]
    assert summary["refinement_template_count"] == 32
    assert (summary["identity_refinement_template_count"], summary["pos_refinement_template_count"], summary["report_refinement_template_count"], summary["handoff_refinement_template_count"]) == (8, 8, 10, 6)


def test_refinement_is_not_additive():
    data = load()
    assert data["summary"]["additive_design_obligation_count"] == 0
    assert data["summary"]["design_lower_bound_before_refinement"] == data["summary"]["design_lower_bound_after_refinement"] == 1404
    assert all(row["counting_effect"] == "REFINEMENT_NOT_ADDITIVE" for row in data["refinement_templates"])


def test_every_template_has_failure_oracle_and_five_receipts():
    rows = load()["refinement_templates"]
    assert len({row["id"] for row in rows}) == 32
    assert all(row["failure_oracle"]["default_when_receipts_missing_or_stale"] == "UNPROVEN" for row in rows)
    assert all(len(row["required_receipts"]) == 5 for row in rows)


def test_source_boundary_references_are_preserved():
    rows = load()["refinement_templates"]
    refs = {row["source_reference"] for row in rows}
    assert {"IA-GAP-01", "POS-STATIC-01", "FP-01", "CG-01", "CG-06"} <= refs


def test_execution_acceptance_and_readiness_remain_zero():
    data = load()
    summary = data["summary"]
    assert summary["accepted_refinement_receipt_slot_count"] == summary["executed_refinement_case_count"] == summary["owner_accepted_refinement_case_count"] == 0
    assert summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0
    assert set(data["safety"].values()) == {0}
