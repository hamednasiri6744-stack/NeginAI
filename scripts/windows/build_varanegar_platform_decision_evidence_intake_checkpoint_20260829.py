from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "contract": "artifacts/varanegar_analysis/varanegar_platform_decision_evidence_intake_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_external_evidence_gate_priority_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_platform_decision_evidence_intake_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_platform_decision_evidence_intake_checkpoint_20260829.py",
    "test": "tests/test_varanegar_platform_decision_evidence_intake_contract.py",
    "checkpoint_test": "tests/test_varanegar_platform_decision_evidence_intake_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/PLATFORM_DECISION_EVIDENCE_INTAKE_CONTRACT_20260829_FA.md",
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
        "cg06_open": contract["scope"]["gate_id"] == "CG-06"
        and contract["scope"]["gate_closed"] is False,
        "eight_slots_zero_accepted": summary["decision_slot_count"] == 8
        and summary["accepted_current_packet_count"] == 0,
        "proposal_not_approval": "PROPOSAL never satisfies an approval slot"
        in contract["intake_contract"]["canonical_rules"],
        "runtime_readiness_zero": summary["implemented_command_count"]
        == summary["executed_restore_drill_count"]
        == summary["runtime_external_effect_parity_proven_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(contract["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_platform_decision_evidence_intake_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "platform_operations": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
