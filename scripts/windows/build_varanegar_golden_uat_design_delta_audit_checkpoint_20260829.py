from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "audit": "artifacts/varanegar_analysis/varanegar_golden_uat_design_delta_audit_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_cross_gate_diagnostic_playbook_addendum_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_golden_uat_design_delta_audit_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_golden_uat_design_delta_audit_checkpoint_20260829.py",
    "test": "tests/test_varanegar_golden_uat_design_delta_audit.py",
    "checkpoint_test": "tests/test_varanegar_golden_uat_design_delta_audit_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/GOLDEN_UAT_DESIGN_DELTA_AUDIT_20260829_FA.md",
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
    audit = load(paths["audit"])
    previous = load(paths["previous"])
    summary = audit["summary"]
    checks = {
        "sources_pass": audit["validation"] == previous["validation"] == "PASS",
        "baseline_1229_delta_175_lower_1404": summary["consolidated_snapshot_design_obligation_count"] == 1229
        and summary["exact_non_duplicated_post_consolidated_delta_count"] == 175
        and summary["current_proven_non_duplicated_design_lower_bound"] == 1404,
        "five_exact_five_unresolved": summary["exact_additive_delta_module_count"] == 5
        and summary["unresolved_or_narrower_crosswalk_module_count"] == 5,
        "unresolved_not_counted": summary["unresolved_case_count_added_to_lower_bound"] == 0,
        "execution_approval_readiness_zero": summary["executed_case_count"]
        == summary["owner_approved_module_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(audit["safety"].values()) == {0},
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "artifact": "varanegar_golden_uat_design_delta_audit_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "golden_or_uat_execution": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
