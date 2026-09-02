"""Chain the P3/P4 isolated capture authorization and redaction gate contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "capture_authorization": "artifacts/varanegar_analysis/varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_p3_p4_isolated_capture_authorization_redaction_gate_checkpoint_20260829.py",
    "test": "tests/test_varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract.py",
    "checkpoint_test": "tests/test_varanegar_p3_p4_isolated_capture_authorization_redaction_gate_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/P3_P4_ISOLATED_CAPTURE_AUTHORIZATION_REDACTION_GATE_20260829_FA.md",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    contract = load(paths["capture_authorization"])
    previous = load(paths["previous"])
    summary = contract["summary"]
    checks = {
        "sources_pass": contract["validation"] == previous["validation"] == "PASS",
        "packets_channels_8_16": summary["packet_count"] == 8 and summary["capture_channel_count"] == 16,
        "schemas_gates_roles_complete": (
            summary["authorization_request_field_count"],
            summary["redaction_attestation_field_count"],
            summary["authorization_gate_count"],
            summary["authorization_gate_assignment_count"],
            summary["role_type_count"],
            summary["role_assignment_count"],
        )
        == (24, 18, 14, 224, 6, 96),
        "authorization_capture_parity_zero": summary["authorization_request_count"]
        == summary["approved_authorization_count"]
        == summary["active_authorization_count"]
        == summary["capture_attempt_count"]
        == summary["captured_side_count"]
        == summary["redaction_attestation_count"]
        == summary["accepted_capture_receipt_count"]
        == summary["result_parity_proven_packet_count"]
        == 0,
        "readiness_zero": summary["owner_approved_packet_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84
        and summary["mapped_risk_assignment_count"] == 343
        and summary["design_lower_bound_after_capture_authorization_contract"] == 1404,
        "safety_zero": set(contract["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_isolated_capture_authorization_redaction_gate_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "previous_checkpoint": {"path": SOURCES["previous"], "sha256": sha256(paths["previous"])},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {
                "name": name,
                "path": SOURCES[name],
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for name, path in sorted(paths.items())
        ],
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes_to_varanegar_or_erp": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "capture_authorizations_issued": 0,
            "capture_attempts": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

