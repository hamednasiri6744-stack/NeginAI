from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_effect_parity_evidence_intake_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_terminal_owner_uat_evidence_intake_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_terminal_owner_uat_evidence_intake_checkpoint_20260829.py",
    "test": "tests/test_varanegar_terminal_owner_uat_evidence_intake_contract.py",
    "checkpoint_test": "tests/test_varanegar_terminal_owner_uat_evidence_intake_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/TERMINAL_OWNER_UAT_EVIDENCE_INTAKE_CONTRACT_20260829_FA.md",
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
    contract = load(paths["contract"])
    previous = load(paths["previous"])
    summary = contract["summary"]
    checks = {
        "sources_pass": contract["validation"] == previous["validation"] == "PASS",
        "cg04_open_terminal": contract["scope"]["gate_id"] == "CG-04"
        and contract["scope"]["execution_requires_all_five_upstream_gates_accepted"] is True
        and contract["scope"]["gate_closed"] is False,
        "fourteen_modules_1229_design": summary["module_count"] == 14
        and summary["synthetic_acceptance_design_obligation_count"] == 1229,
        "nine_dimensions_sixteen_fields": summary["acceptance_dimension_count"] == 9
        and summary["required_packet_field_count"] == 16,
        "upstream_open": summary["upstream_gate_count"] == 5
        and summary["upstream_required_packet_or_slot_count"] == 70
        and summary["upstream_current_accepted_packet_or_slot_count"] == 0,
        "execution_approval_readiness_zero": summary["executed_obligation_count"]
        == summary["accepted_module_packet_count"]
        == summary["owner_approved_module_count"]
        == summary["promotion_approved_module_count"]
        == summary["cg04_closed_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(contract["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_terminal_owner_uat_evidence_intake_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "uat_or_approvals": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
