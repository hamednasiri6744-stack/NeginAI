"""Checkpoint the cross-lane external-evidence intake queue."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "queue": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_external_evidence_intake_queue_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_closure_route_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_alias_cross_lane_external_evidence_intake_queue_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_alias_cross_lane_external_evidence_intake_checkpoint_20260829.py",
    "test": "tests/test_varanegar_alias_cross_lane_external_evidence_intake_queue.py",
    "checkpoint_test": "tests/test_varanegar_alias_cross_lane_external_evidence_intake_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/ALIAS_CROSS_LANE_EXTERNAL_EVIDENCE_INTAKE_QUEUE_20260829_FA.md",
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
    queue = load(paths["queue"])
    previous = load(paths["previous"])
    summary = queue["summary"]
    checks = {
        "sources_pass": queue["validation"] == previous["validation"] == "PASS",
        "queue_29_cases_203": (summary["queue_item_count"], summary["covered_case_count"]) == (29, 203),
        "routes_9_12_5_3": (
            summary["alias_or_new_action_packet_count"],
            summary["semantic_equivalence_packet_count"],
            summary["report_effect_and_result_parity_packet_count"],
            summary["export_effect_and_result_parity_packet_count"],
        ) == (9, 12, 5, 3),
        "cases_63_84_35_21": (
            summary["alias_or_new_action_case_count"],
            summary["semantic_equivalence_case_count"],
            summary["report_effect_and_result_parity_case_count"],
            summary["export_effect_and_result_parity_case_count"],
        ) == (63, 84, 35, 21),
        "roles_58": summary["accountable_role_assignment_count"] == 58,
        "external_receipts_zero": summary["named_owner_assignment_count"]
        == summary["received_evidence_receipt_count"]
        == summary["accepted_evidence_receipt_count"]
        == summary["accepted_route_decision_count"]
        == summary["accepted_case_disposition_count"]
        == 0,
        "execution_readiness_zero": summary["executed_case_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_intake_queue"]
        == summary["design_lower_bound_after_intake_queue"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(queue["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_alias_cross_lane_external_evidence_intake_checkpoint_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "previous_checkpoint": {
            "path": SOURCES["previous"],
            "sha256": sha256(paths["previous"]),
        },
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
            "operational_or_uat_execution": 0,
            "data_mutations": 0,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
