import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_treasury_command_outcome_envelope_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_treasury_command_outcome_envelope_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "treasury.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_twelve_unique_commands_have_static_or_design_classification():
    commands = load()["commands"]
    assert len(commands) == len({command["id"] for command in commands}) == 12
    assert {command["evidence_level"] for command in commands} <= {
        "HASH_PINNED_STATIC_PATH",
        "HASH_PINNED_STATIC_PATH_WITH_CLONE_AGGREGATE",
        "HASH_PINNED_STATIC_CONTROL_FLOW",
        "TARGET_DESIGN_NOT_IMPLEMENTED",
    }


def test_seven_static_and_five_design_only():
    summary = load()["summary"]
    assert summary["legacy_static_command_count"] == 7 and summary["target_design_only_command_count"] == 5


def test_delete_transaction_gap_is_not_promoted():
    command = next(command for command in load()["commands"] if command["command"] == "received_cheque.delete")
    assert command["transaction_owner"].startswith("UNPROVEN")


def test_outcome_envelope_handles_durable_and_unknown_effects():
    codes = load()["target_outcome_retry_envelope"]["outcome_codes"]
    assert "REJECTED_WITH_DURABLE_EFFECT" in codes and "UNKNOWN_REQUIRES_READBACK" in codes


def test_runtime_and_owner_counts_remain_zero():
    summary = load()["summary"]
    assert summary["runtime_effect_parity_proven_count"] == summary["executed_acceptance_case_count"] == summary["owner_approved_count"] == 0


def test_sources_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]


def test_safety_zero():
    assert set(value for key, value in load()["safety"].items() if key != "mode") == {0}
