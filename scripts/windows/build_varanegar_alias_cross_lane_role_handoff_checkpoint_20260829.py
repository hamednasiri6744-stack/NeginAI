"""Checkpoint the role-scoped cross-lane evidence handoff worklist."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "worklist": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_role_handoff_worklist_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_alias_cross_lane_role_handoff_worklist_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_alias_cross_lane_role_handoff_checkpoint_20260829.py",
    "test": "tests/test_varanegar_alias_cross_lane_role_handoff_worklist.py",
    "checkpoint_test": "tests/test_varanegar_alias_cross_lane_role_handoff_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/ALIAS_CROSS_LANE_ROLE_HANDOFF_WORKLIST_20260829_FA.md",
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
    worklist = load(paths["worklist"])
    previous = load(paths["previous"])
    summary = worklist["summary"]
    checks = {
        "sources_pass": worklist["validation"] == previous["validation"] == "PASS",
        "roles_13_assignments_58": (summary["role_worklist_count"], summary["role_packet_assignment_count"]) == (13, 58),
        "assignment_totals_406_580": (summary["role_case_assignment_count"], summary["role_receipt_slot_assignment_count"]) == (406, 580),
        "underlying_29_203_290": (
            summary["underlying_intake_item_count"],
            summary["underlying_case_count"],
            summary["underlying_receipt_slot_count"],
        ) == (29, 203, 290),
        "roster_unassigned_zero": summary["named_owner_assignment_count"]
        == summary["delegate_assignment_count"]
        == summary["accepted_owner_roster_count"]
        == summary["received_receipt_count"]
        == summary["role_accepted_receipt_count"]
        == summary["accepted_route_decision_count"]
        == 0,
        "execution_readiness_zero": summary["executed_case_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_role_handoff"]
        == summary["design_lower_bound_after_role_handoff"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(worklist["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_alias_cross_lane_role_handoff_checkpoint_20260829",
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
        "safety": {"database_connections": 0, "operational_or_uat_execution": 0, "data_mutations": 0},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
