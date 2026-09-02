import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/windows/build_varanegar_reporting_output_outcome_envelope_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_reporting_output_outcome_envelope_20260829.json"


def load():
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "envelope.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_eight_surfaces_and_five_outcomes():
    data = load()
    assert len(data["surfaces"]) == 8 and len(data["outcome_contract"]["allowed_outcomes"]) == 5


def test_request_response_shape():
    summary = load()["summary"]
    assert summary["common_request_field_count"] == 10 and summary["common_response_field_count"] == 9


def test_completion_is_not_attempt_and_exports_are_external():
    checks = load()["checks"]
    assert checks["completion_not_attempt"] and checks["external_exports_no_erp_mutation"]


def test_sale_history_and_bank_delegation_pinned():
    summary = load()["summary"]
    assert summary["sale_print_event_count"] == 308432 and summary["repeated_sale_printed_document_count"] == 34840
    assert summary["post_terminal_cancel_sale_print_event_count"] == 143 and summary["bank_delegated_command_count"] == 5


def test_runtime_and_readiness_zero():
    summary = load()["summary"]
    assert summary["runtime_outcome_parity_proven_count"] == summary["implemented_command_count"] == summary["owner_approved_count"] == summary["command_ready_module_count"] == summary["pilot_ready_module_count"] == 0


def test_sources_current():
    for item in load()["source_manifest"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_safety_zero():
    assert set(value for key, value in load()["safety"].items() if key != "mode") == {0}
