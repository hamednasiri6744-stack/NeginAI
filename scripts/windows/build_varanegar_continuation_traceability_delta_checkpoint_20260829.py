"""Chain the continuation requirement/risk traceability evidence delta."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "delta": "artifacts/varanegar_analysis/varanegar_continuation_traceability_delta_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_accounting_expert_playbook_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_continuation_traceability_delta_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_continuation_traceability_delta_checkpoint_20260829.py",
    "test": "tests/test_varanegar_continuation_traceability_delta.py",
    "doc": "docs/varanegar_reconstruction/CONTINUATION_TRACEABILITY_RISK_DELTA_20260829_FA.md",
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
    delta = load(paths["delta"])
    previous = load(paths["previous"])
    summary = delta["summary"]
    checks = {
        "sources_pass": delta["validation"] == previous["validation"] == "PASS",
        "seven_evidence_items": summary["continuation_evidence_count"] == 7,
        "ten_requirement_contracts": summary["requirement_contract_delta_count"] == 10,
        "links_pinned": summary["module_evidence_link_count"] == 26 and summary["risk_evidence_link_count"] == 36,
        "sixteen_existing_risks": summary["unique_linked_risk_count"] == 16,
        "base_counts_stable": summary["base_risk_count"] == 84 and summary["base_mapped_risk_assignment_count"] == 343,
        "no_new_risk_or_promotion": summary["new_risk_count"] == summary["runtime_readiness_promotions"] == 0,
        "safety_zero": set(value for key, value in delta["safety"].items() if key != "mode") == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_continuation_traceability_delta_checkpoint_20260829",
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
