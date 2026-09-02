"""Checkpoint the P0 external-evidence collection activation packets."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "packets": "artifacts/varanegar_analysis/varanegar_p0_external_evidence_collection_activation_packets_20260829.json",
    "previous": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_role_handoff_checkpoint_20260829.json",
    "builder": "scripts/windows/build_varanegar_p0_external_evidence_collection_activation_packets_20260829.py",
    "checkpoint_builder": "scripts/windows/build_varanegar_p0_external_evidence_collection_activation_checkpoint_20260829.py",
    "test": "tests/test_varanegar_p0_external_evidence_collection_activation_packets.py",
    "checkpoint_test": "tests/test_varanegar_p0_external_evidence_collection_activation_checkpoint.py",
    "doc": "docs/varanegar_reconstruction/P0_EXTERNAL_EVIDENCE_COLLECTION_ACTIVATION_PACKETS_20260829_FA.md",
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
    packets = load(paths["packets"])
    previous = load(paths["previous"])
    summary = packets["summary"]
    checks = {
        "sources_pass": packets["validation"] == previous["validation"] == "PASS",
        "p0_7_cases_49": (summary["activation_packet_count"], summary["covered_case_count"]) == (7, 49),
        "candidate_3_none_4_routes_4_3": (
            summary["candidate_bearing_packet_count"],
            summary["explicit_none_packet_count"],
            summary["alias_or_new_action_packet_count"],
            summary["semantic_equivalence_packet_count"],
        ) == (3, 4, 4, 3),
        "pairs_66_20_46": (
            summary["same_kind_case_pair_count"],
            summary["failure_injection_pair_count"],
            summary["control_pair_count"],
        ) == (66, 20, 46),
        "slots_roles_gates_70_14_35": (
            summary["receipt_slot_count"],
            summary["accountable_role_assignment_count"],
            summary["gate_assignment_count"],
        ) == (70, 14, 35),
        "all_not_activated_zero": summary["named_owner_assignment_count"]
        == summary["role_accepted_receipt_count"]
        == summary["accepted_prerequisite_count"]
        == summary["activated_packet_count"]
        == summary["accepted_route_decision_count"]
        == 0,
        "execution_readiness_zero": summary["executed_case_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_p0_activation"]
        == summary["design_lower_bound_after_p0_activation"]
        == 1404,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
        "safety_zero": set(packets["safety"].values()) == {0},
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p0_external_evidence_collection_activation_checkpoint_20260829",
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
