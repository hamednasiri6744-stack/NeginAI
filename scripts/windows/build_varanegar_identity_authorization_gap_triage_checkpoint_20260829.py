from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "triage": "artifacts/varanegar_analysis/varanegar_identity_authorization_gap_triage_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_report_formula_grain_policy_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_identity_authorization_gap_triage_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_identity_authorization_gap_triage_checkpoint_20260829.py",
    "test": "tests/test_varanegar_identity_authorization_gap_triage.py",
    "checkpoint_test": "tests/test_varanegar_identity_authorization_gap_triage_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/IDENTITY_AUTHORIZATION_GAP_TRIAGE_20260829_FA.md",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    triage = load(paths["triage"])
    previous = load(paths["previous"])
    summary = triage["summary"]
    checks = {
        "sources_pass": triage["validation"] == previous["validation"] == "PASS",
        "endpoint_split": summary["declaration_gap_endpoint_count"] == 60
        and summary["mutating_declaration_gap_endpoint_count"] == 38
        and summary["read_declaration_gap_endpoint_count"] == 22,
        "manual_decision_zero": summary["named_manual_authorization_decision_candidate_count"] == 0,
        "scope_mismatch_one_class": summary["scope_consistency_mismatch_count"]
        == summary["membership_user_scope_mismatch_count"]
        == 58,
        "seven_lanes_139_units_zero_acceptance": summary["triage_lane_count"] == 7
        and summary["triage_required_unit_count"] == 139
        and summary["triage_current_accepted_unit_count"] == 0,
        "role_uat_184_approval_zero": summary["synthetic_role_uat_case_count"] == 184
        and summary["owner_approved_role_uat_case_count"] == 0,
        "runtime_security_readiness_zero": summary["runtime_authorization_proven_module_count"]
        == summary["security_approved_module_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(triage["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_identity_authorization_gap_triage_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "previous_checkpoint": {"path": SOURCES["previous"], "sha256": sha256(paths["previous"])},
        "checks": checks,
        "failed_checks": failed,
        "source_manifest": [
            {"name": name, "path": SOURCES[name], "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(paths.items())
        ],
        "safety": {"database_connections": 0, "endpoint_or_identity_execution": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
