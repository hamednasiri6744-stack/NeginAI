import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/windows"))
from varanegar_comparison_adapter_reference_codec import ERROR_RULES, baseline_envelope, mutated_envelope, validate  # noqa: E402

BUILDER = ROOT / "scripts/windows/build_varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_contract_20260829.py"
ARTIFACT = ROOT / "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_contract_20260829.json"


def load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))


def test_rebuild(tmp_path):
    output = tmp_path / "codec.json"
    subprocess.run([sys.executable, str(BUILDER), "--output", str(output)], check=True)
    assert json.loads(output.read_text(encoding="utf-8"))["validation"] == "PASS"


def test_reference_codec_totals():
    summary = load()["summary"]
    assert (summary["adapter_profile_count"], summary["validator_rule_count"], summary["mutation_vector_count"]) == (8, 16, 16)
    assert (summary["positive_baseline_run_count"], summary["positive_baseline_pass_count"]) == (8, 8)
    assert (summary["synthetic_negative_run_count"], summary["synthetic_negative_pass_count"], summary["synthetic_negative_fail_count"]) == (128, 128, 0)


def test_direct_reference_validation_for_all_rules():
    baseline = baseline_envelope("SYNTH_PROFILE")
    assert validate(baseline)["accepted"] is True
    for trigger, expected_code, expected_status in ERROR_RULES:
        result = validate(mutated_envelope("SYNTH_PROFILE", trigger))
        assert result == {
            "accepted": False,
            "trigger_class": trigger,
            "error_code": expected_code,
            "typed_status": expected_status,
        }


def test_each_mutation_changes_one_control_field_only():
    baseline = baseline_envelope("SYNTH_PROFILE")
    for trigger, _, _ in ERROR_RULES:
        mutated = mutated_envelope("SYNTH_PROFILE", trigger)
        changed = [key for key in baseline if baseline[key] != mutated[key]]
        assert len(changed) == 1


def test_error_precedence_is_deterministic():
    envelope = mutated_envelope("SYNTH_PROFILE", "raw_payload_persistence_attempt")
    envelope["manifest_present"] = False
    assert validate(envelope)["error_code"] == "MANIFEST_MISSING"
    assert load()["error_precedence"] == [rule[1] for rule in ERROR_RULES]


def test_no_operational_or_parity_claim():
    document = load()
    summary = document["summary"]
    assert summary["reference_codec_implementation_count"] == 1
    for field in (
        "operational_adapter_implementation_count",
        "operational_adapter_run_count",
        "legacy_or_target_capture_count",
        "emitted_receipt_count",
        "accepted_receipt_count",
        "result_parity_proven_profile_count",
        "command_ready_module_count",
        "pilot_ready_module_count",
    ):
        assert summary[field] == 0
    assert set(document["safety"].values()) == {0}
    assert summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343


def test_source_manifest_current():
    for source in load()["source_manifest"]:
        path = ROOT / source["path"]
        assert path.stat().st_size == source["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]

