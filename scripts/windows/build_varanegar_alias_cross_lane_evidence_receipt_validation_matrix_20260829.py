"""Expand the cross-lane intake queue into evidence-receipt validation slots."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "queue": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_external_evidence_intake_queue_20260829.json",
    "queue_checkpoint": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_external_evidence_intake_checkpoint_20260829.json",
    "gate_matrix": "artifacts/varanegar_analysis/varanegar_external_gate_handoff_acceptance_matrix_20260829.json",
    "terminal_gate": "artifacts/varanegar_analysis/varanegar_terminal_owner_uat_evidence_intake_contract_20260829.json",
    "report_gate": "artifacts/varanegar_analysis/varanegar_report_parity_evidence_intake_contract_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

REQUIRED_METADATA_FIELDS = [
    "receipt_id",
    "receipt_type",
    "source_artifact_reference",
    "source_artifact_sha256",
    "captured_at",
    "collection_environment_class",
    "fixture_or_case_set_hash",
    "producer_role_type",
    "independent_reviewer_role_type",
    "policy_version",
    "expires_at",
    "conflict_or_supersession_reference",
    "redaction_attestation",
    "validation_status",
]

REJECTION_CODES = {
    "RECEIPT_MISSING": "the required receipt has not been submitted",
    "HASH_MISSING_OR_MISMATCH": "the artifact digest is absent or does not match the submitted artifact",
    "SOURCE_NOT_FROZEN": "the evidence source or fixture can change after collection",
    "ENVIRONMENT_UNDECLARED": "the collection environment class is absent or ambiguous",
    "FIXTURE_OR_CASE_HASH_MISSING": "the receipt is not pinned to the frozen fixture or case set",
    "ROLE_SEPARATION_VIOLATION": "producer and independent reviewer separation is absent where required",
    "POLICY_VERSION_MISSING": "the governing policy or configuration version is not pinned",
    "RECEIPT_EXPIRED": "the receipt is outside its approved validity window",
    "CONFLICT_UNRESOLVED": "contradictory evidence has no adjudicated resolution",
    "SUPERSESSION_UNRESOLVED": "replacement evidence does not explicitly supersede the older receipt",
    "RAW_SENSITIVE_VALUE_DETECTED": "raw credentials, identity, PII, customer rules or business values are present",
    "GATE_SCOPE_MISMATCH": "the receipt does not satisfy the applicable external gate scope",
    "INSUFFICIENT_CONTENT": "the receipt lacks the observable needed for the claimed disposition",
    "NON_REPRODUCIBLE": "the artifact, fixture or validation procedure cannot be independently reproduced",
}

STATE_MACHINE = [
    {"state": "MISSING", "promotion_allowed": False},
    {"state": "RECEIVED_UNVALIDATED", "promotion_allowed": False},
    {"state": "HASH_VALIDATED", "promotion_allowed": False},
    {"state": "CONTENT_VALIDATED", "promotion_allowed": False},
    {"state": "ROLE_ACCEPTED", "promotion_allowed": True},
    {"state": "REJECTED", "promotion_allowed": False},
    {"state": "EXPIRED", "promotion_allowed": False},
    {"state": "SUPERSEDED", "promotion_allowed": False},
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt_classes(receipt_type: str) -> list[str]:
    categories = []
    if "authorization" in receipt_type or "denial" in receipt_type:
        categories.append("AUTHORIZATION_SCOPE")
    if any(token in receipt_type for token in ("transaction", "retry", "failure_stage")):
        categories.append("TRANSACTION_FAILURE_RECOVERY")
    if any(token in receipt_type for token in ("result", "rowset", "render", "file", "export", "query_identity", "per_item")):
        categories.append("RESULT_RENDER_EXPORT")
    if "role" in receipt_type:
        categories.append("OWNER_REVIEW")
    if any(token in receipt_type for token in ("policy", "conflict", "supersession")):
        categories.append("POLICY_CONFLICT")
    if any(token in receipt_type for token in ("effect", "assertion", "outcome", "candidate_pair")):
        categories.append("SEMANTIC_EFFECT")
    return categories or ["IDENTITY_AND_CLASSIFICATION"]


def applicable_gate_ids(receipt_type: str, route_gate_ids: list[str]) -> list[str]:
    preferred_by_category = {
        "AUTHORIZATION_SCOPE": ["CG-01", "CG-04"],
        "TRANSACTION_FAILURE_RECOVERY": ["CG-02", "CG-03", "CG-04"],
        "RESULT_RENDER_EXPORT": ["CG-03", "CG-05", "CG-04"],
        "OWNER_REVIEW": ["CG-04"],
        "POLICY_CONFLICT": ["CG-06", "CG-04"],
        "SEMANTIC_EFFECT": ["CG-03", "CG-04"],
        "IDENTITY_AND_CLASSIFICATION": ["CG-06", "CG-04"],
    }
    preferred = {
        gate_id
        for category in receipt_classes(receipt_type)
        for gate_id in preferred_by_category[category]
    }
    selected = [gate_id for gate_id in route_gate_ids if gate_id in preferred]
    return selected or list(route_gate_ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = {name: ROOT / value for name, value in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    queue = documents["queue"]["intake_queue"]
    known_gate_ids = {
        row["gate_id"] for row in documents["gate_matrix"]["gate_handoff_matrix"]
    }

    slots = []
    by_route = Counter()
    by_class = Counter()
    by_lane = Counter()
    for intake in queue:
        for receipt_index, receipt_type in enumerate(intake["required_evidence_receipts"], 1):
            categories = receipt_classes(receipt_type)
            slot = {
                "receipt_slot_id": f"{intake['intake_id']}-R{receipt_index:02d}",
                "intake_id": intake["intake_id"],
                "cross_lane_status_id": intake["cross_lane_status_id"],
                "source_packet_id": intake["source_packet_id"],
                "lane": intake["lane"],
                "priority_rank": intake["priority_rank"],
                "module": intake["module"],
                "newer_action_or_surface": intake["newer_action_or_surface"],
                "required_decision_route": intake["required_decision_route"],
                "receipt_type": receipt_type,
                "receipt_class": categories[0],
                "receipt_classes": categories,
                "applicable_gate_ids": applicable_gate_ids(receipt_type, intake["required_gate_ids"]),
                "accountable_role_types": intake["accountable_role_types"],
                "required_metadata_fields": REQUIRED_METADATA_FIELDS,
                "current_state": "MISSING",
                "received_receipt_count": 0,
                "hash_validated_count": 0,
                "content_validated_count": 0,
                "role_accepted_count": 0,
                "rejected_receipt_count": 0,
                "expired_receipt_count": 0,
                "superseded_receipt_count": 0,
                "readiness_effect": "ZERO",
            }
            slots.append(slot)
            by_route[intake["required_decision_route"]] += 1
            for category in categories:
                by_class[category] += 1
            by_lane[intake["lane"]] += 1

    distinct_receipt_types = sorted({slot["receipt_type"] for slot in slots})
    summary = {
        "intake_item_count": len(queue),
        "receipt_slot_count": len(slots),
        "receipt_type_count": len(distinct_receipt_types),
        "receipt_class_count": len(by_class),
        "required_metadata_field_count": len(REQUIRED_METADATA_FIELDS),
        "rejection_code_count": len(REJECTION_CODES),
        "state_count": len(STATE_MACHINE),
        "multi_class_receipt_slot_count": sum(len(slot["receipt_classes"]) > 1 for slot in slots),
        "cg05_scoped_receipt_slot_count": sum("CG-05" in slot["applicable_gate_ids"] for slot in slots),
        "alias_or_new_action_receipt_slot_count": by_route["EXTERNAL_ALIAS_OR_NEW_ACTION_DECISION_REQUIRED"],
        "semantic_equivalence_receipt_slot_count": by_route["EXTERNAL_SEMANTIC_EQUIVALENCE_DECISION_REQUIRED"],
        "report_effect_and_result_receipt_slot_count": by_route["EXTERNAL_SEMANTIC_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
        "export_effect_and_result_receipt_slot_count": by_route["EXTERNAL_EXPORT_EFFECT_AND_RESULT_PARITY_DECISION_REQUIRED"],
        "received_receipt_count": 0,
        "hash_validated_receipt_count": 0,
        "content_validated_receipt_count": 0,
        "role_accepted_receipt_count": 0,
        "rejected_receipt_count": 0,
        "expired_receipt_count": 0,
        "superseded_receipt_count": 0,
        "accepted_route_decision_count": 0,
        "executed_case_count": 0,
        "owner_approved_case_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_receipt_matrix": 1404,
        "design_lower_bound_after_receipt_matrix": 1404,
        "official_test_file_count": documents["tests"]["runner"]["test_file_count"],
        "official_passed_test_count": documents["tests"]["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }

    checks = {
        "sources_pass": all(document.get("validation") == "PASS" for document in documents.values()),
        "queue_29_slots_290": (summary["intake_item_count"], summary["receipt_slot_count"]) == (29, 290),
        "route_slots_90_120_50_30": (
            summary["alias_or_new_action_receipt_slot_count"],
            summary["semantic_equivalence_receipt_slot_count"],
            summary["report_effect_and_result_receipt_slot_count"],
            summary["export_effect_and_result_receipt_slot_count"],
        ) == (90, 120, 50, 30),
        "ten_slots_per_intake": all(
            sum(slot["intake_id"] == intake["intake_id"] for slot in slots) == 10 for intake in queue
        ),
        "slot_ids_unique": len({slot["receipt_slot_id"] for slot in slots}) == len(slots),
        "gate_ids_known": all(set(slot["applicable_gate_ids"]) <= known_gate_ids for slot in slots),
        "metadata_schema_14": summary["required_metadata_field_count"] == 14,
        "rejection_taxonomy_14": summary["rejection_code_count"] == 14,
        "p3_composite_receipts_span_cg02_cg03_cg05_cg04": all(
            set(slot["receipt_classes"]) == {"TRANSACTION_FAILURE_RECOVERY", "RESULT_RENDER_EXPORT", "SEMANTIC_EFFECT"}
            and slot["applicable_gate_ids"] == ["CG-02", "CG-03", "CG-05", "CG-04"]
            for slot in slots
            if slot["receipt_type"] == "failure_stage_and_per_item_outcome_receipt"
        ),
        "multi_class_14_cg05_slots_27": (
            summary["multi_class_receipt_slot_count"],
            summary["cg05_scoped_receipt_slot_count"],
        ) == (14, 27),
        "all_missing_zero": all(
            slot["current_state"] == "MISSING"
            and slot["received_receipt_count"] == 0
            and slot["hash_validated_count"] == 0
            and slot["content_validated_count"] == 0
            and slot["role_accepted_count"] == 0
            and slot["rejected_receipt_count"] == 0
            and slot["expired_receipt_count"] == 0
            and slot["superseded_receipt_count"] == 0
            and slot["readiness_effect"] == "ZERO"
            for slot in slots
        ),
        "execution_readiness_zero": summary["accepted_route_decision_count"]
        == summary["executed_case_count"]
        == summary["owner_approved_case_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_receipt_matrix"]
        == summary["design_lower_bound_after_receipt_matrix"]
        == 1404,
        "official_tests_pass": documents["tests"]["runner"]["exit_code"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)

    output = {
        "artifact": "varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "OFFLINE_EVIDENCE_RECEIPT_SLOT_VALIDATION_DESIGN",
            "continuation_complete": False,
            "receipt_content_collected": False,
        },
        "safety": {
            "database_connections": 0,
            "operational_forms_reports_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "write_access_created": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "required_metadata_fields": REQUIRED_METADATA_FIELDS,
        "rejection_codes": REJECTION_CODES,
        "state_machine": STATE_MACHINE,
        "receipt_type_catalog": distinct_receipt_types,
        "receipt_class_distribution": dict(sorted(by_class.items())),
        "lane_slot_distribution": dict(sorted(by_lane.items())),
        "receipt_slots": slots,
        "validation_rule": "a slot reaches ROLE_ACCEPTED only after hash, frozen-source, content, scope, expiry, conflict/supersession, redaction and independent-role checks pass; all other states contribute zero promotion",
        "redaction_rule": "persist references, hashes and categorical outcomes only; raw credentials, identity, PII, customer rules and business values are prohibited",
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
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "The matrix defines empty receipt slots and validation rules; it contains no submitted external evidence.",
            "ROLE_ACCEPTED is a receipt state, not semantic closure or command/pilot readiness by itself.",
            "No operational execution, owner acceptance, runtime parity or result parity is claimed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(output["validation"])
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
