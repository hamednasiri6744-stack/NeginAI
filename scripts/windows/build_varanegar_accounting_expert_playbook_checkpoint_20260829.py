"""Chain the accounting expert playbooks and target ERP contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "playbook": "artifacts/varanegar_analysis/varanegar_accounting_expert_playbook_contract_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_report_golden_fixture_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_accounting_expert_playbook_contract_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_accounting_expert_playbook_checkpoint_20260829.py",
    "test": "tests/test_varanegar_accounting_expert_playbook_contract.py",
    "doc": "docs/varanegar_reconstruction/ACCOUNTING_EXPERT_PLAYBOOK_AND_ERP_CONTRACT_20260829_FA.md",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / value for name, value in SOURCES.items()}
    playbook = load(paths["playbook"])
    previous = load(paths["previous"])
    summary = playbook["summary"]
    checks = {
        "sources_pass": playbook["validation"] == previous["validation"] == "PASS",
        "five_playbooks": summary["playbook_count"] == 5,
        "nine_contract_sections": summary["target_contract_section_count"] == 9,
        "golden_gate_42": summary["golden_case_gate_count"] == 42,
        "no_runtime_or_repair_claim": summary["runtime_incidents_diagnosed_count"] == summary["repairs_performed_count"] == 0,
        "risk_trace_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343 and summary["new_risk_count"] == 0,
        "safety_zero": set(value for key, value in playbook["safety"].items() if key != "mode") == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_accounting_expert_playbook_checkpoint_20260829",
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
        "safety": {
            "commands_forms_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "data_mutations": 0,
            "sensitive_values_persisted": 0,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
