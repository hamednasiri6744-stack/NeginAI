import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_golden_uat_design_delta_audit_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_golden_uat_design_delta_audit_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "audit.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_baseline_delta_and_lower_bound():
    summary = load()["summary"]
    assert summary["consolidated_snapshot_design_obligation_count"] == 1229
    assert summary["exact_non_duplicated_post_consolidated_delta_count"] == 175
    assert summary["current_proven_non_duplicated_design_lower_bound"] == 1404


def test_exact_deltas_require_matching_reuse_base():
    rows = load()["module_design_delta_audit"]
    exact = [row for row in rows if row["exact_additive_delta_count"]]
    assert {row["module"] for row in exact} == {
        "organization_context",
        "identity_authorization",
        "configuration",
        "master_data",
        "integration_migration",
    }
    assert all(row["newer_artifact_existing_reused_count"] == row["consolidated_design_count"] for row in exact)


def test_platform_is_not_double_counted():
    row = next(row for row in load()["module_design_delta_audit"] if row["module"] == "platform")
    assert row["consolidated_design_count"] == row["newer_artifact_design_count"] == 42
    assert row["exact_additive_delta_count"] == 0
    assert row["counting_status"].startswith("ALREADY_INCLUDED")


def test_unresolved_crosswalks_add_zero():
    data = load()
    assert data["summary"]["unresolved_or_narrower_crosswalk_module_count"] == 5
    assert data["summary"]["unresolved_case_count_added_to_lower_bound"] == 0
    assert len(data["unresolved_crosswalk_work_queue"]) == 5


def test_design_is_not_execution_or_readiness():
    data = load()
    summary = data["summary"]
    assert summary["executed_case_count"] == summary["owner_approved_module_count"] == 0
    assert summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0
    assert set(data["safety"].values()) == {0}
