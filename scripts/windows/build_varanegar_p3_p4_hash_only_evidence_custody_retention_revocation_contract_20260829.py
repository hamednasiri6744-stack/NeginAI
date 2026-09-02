"""Build hash-only custody, retention, expiry, revocation, and supersession requirements."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "handoff": "artifacts/varanegar_analysis/varanegar_p3_p4_capture_to_comparison_evidence_handoff_matrix_20260829.json",
    "handoff_checkpoint": "artifacts/varanegar_analysis/varanegar_p3_p4_capture_to_comparison_evidence_handoff_checkpoint_20260829.json",
    "capture": "artifacts/varanegar_analysis/varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829.json",
    "receipt_validation": "artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.json",
    "cg05": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.json",
    "adapter": "artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

CUSTODY_METADATA_FIELDS = [
    "custody_receipt_id",
    "custody_requirement_id",
    "capture_pair_id",
    "capture_channel_id",
    "capture_side",
    "cg05_receipt_slot_id",
    "receipt_type",
    "evidence_manifest_sha256",
    "redaction_attestation_sha256",
    "source_authorization_reference",
    "producer_role_receipt_reference",
    "transferrer_role_receipt_reference",
    "custodian_role_receipt_reference",
    "independent_reviewer_role_receipt_reference",
    "retention_policy_version_sha256",
    "created_at",
    "expires_at",
    "previous_custody_receipt_sha256",
    "revocation_or_supersession_reference",
    "custody_state",
]

CUSTODY_STATES = [
    "MISSING",
    "CREATED_HASH_ONLY",
    "TRANSFER_PENDING",
    "IN_CUSTODY",
    "REVIEW_PENDING",
    "ACCEPTED_CURRENT",
    "EXPIRED",
    "REVOKED",
    "SUPERSEDED",
]

TRANSITIONS = [
    ("MISSING", "CREATED_HASH_ONLY", "create_with_redaction_and_authorization_receipts"),
    ("CREATED_HASH_ONLY", "TRANSFER_PENDING", "initiate_custody_transfer"),
    ("TRANSFER_PENDING", "IN_CUSTODY", "accept_transfer_with_hash_match"),
    ("IN_CUSTODY", "REVIEW_PENDING", "request_independent_review"),
    ("REVIEW_PENDING", "ACCEPTED_CURRENT", "accept_current_after_all_gates"),
    ("CREATED_HASH_ONLY", "REVOKED", "revoke_before_transfer"),
    ("TRANSFER_PENDING", "REVOKED", "revoke_during_transfer"),
    ("IN_CUSTODY", "REVOKED", "revoke_in_custody"),
    ("REVIEW_PENDING", "REVOKED", "revoke_during_review"),
    ("ACCEPTED_CURRENT", "EXPIRED", "expire_without_extension"),
    ("ACCEPTED_CURRENT", "SUPERSEDED", "supersede_with_new_linked_receipt"),
    ("ACCEPTED_CURRENT", "REVOKED", "revoke_after_acceptance_and_reopen_gate"),
]

CUSTODY_GATES = [
    ("ECG-01", "source_capture_authorization_current_and_in_scope"),
    ("ECG-02", "redaction_attestation_current_and_accepted"),
    ("ECG-03", "evidence_manifest_hash_reproduced"),
    ("ECG-04", "producer_and_transfer_roles_attested"),
    ("ECG-05", "custodian_and_independent_reviewer_separated"),
    ("ECG-06", "retention_policy_version_pinned"),
    ("ECG-07", "expiry_current_and_no_automatic_extension"),
    ("ECG-08", "revocation_and_supersession_chain_resolved"),
    ("ECG-09", "raw_payload_absent_and_temporary_material_destroyed"),
    ("ECG-10", "previous_receipt_hash_chain_continuous"),
]

CUSTODY_ROLE_TYPES = [
    "EVIDENCE_PRODUCER_ROLE",
    "EVIDENCE_TRANSFER_OPERATOR_ROLE",
    "EVIDENCE_CUSTODIAN_ROLE",
    "INDEPENDENT_EVIDENCE_REVIEWER_ROLE",
]

RETENTION_RULES = [
    "retention_window_is_policy_versioned_and_bounded",
    "expiry_never_auto_extends_or_preserves_acceptance",
    "revocation_immediately_reopens_dependent_handoff_gates",
    "supersession_requires_bidirectional_old_new_hash_links",
    "temporary_raw_material_destroyed_before_custody_acceptance",
    "legal_or_incident_hold_requires_separate_owner_approved_receipt",
    "disposition_preserves_hash_only_tombstone_and_audit_lineage",
    "retention_end_never_deletes_risk_decision_or_cg05_lineage_reference",
]

REJECTION_CODES = [
    "CUSTODY_SOURCE_AUTHORIZATION_INVALID",
    "CUSTODY_REDACTION_ATTESTATION_INVALID",
    "CUSTODY_MANIFEST_HASH_MISMATCH",
    "CUSTODY_ROLE_OR_SOD_INVALID",
    "CUSTODY_RETENTION_POLICY_UNPINNED",
    "CUSTODY_RECEIPT_EXPIRED",
    "CUSTODY_RECEIPT_REVOKED",
    "CUSTODY_SUPERSESSION_CONFLICT",
    "CUSTODY_RAW_PAYLOAD_DETECTED",
    "CUSTODY_TEMPORARY_MATERIAL_NOT_DESTROYED",
    "CUSTODY_HASH_CHAIN_BROKEN",
    "CUSTODY_DUPLICATE_OR_REPLAY_CONFLICT",
]

ALLOWED_PERSISTENCE = [
    "opaque_references",
    "sha256_hashes",
    "bounded_counts",
    "typed_states_and_rejection_codes",
    "policy_version_hashes",
    "timestamps_expiry_and_ttl_metadata",
    "hash_only_tombstone",
]

PROHIBITED_PERSISTENCE = [
    "raw_business_values",
    "row_or_item_payloads",
    "report_render_or_export_file_bytes",
    "pii_identity_or_contact_values",
    "credentials_connection_strings_or_tokens",
    "sql_rule_or_procedure_text",
    "network_or_filesystem_endpoint_details",
    "cryptographic_key_material_or_signature_bytes",
    "unredacted_exception_samples",
    "screen_or_print_content",
    "database_backup_or_transaction_log_content",
    "temporary_capture_material_after_attestation",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    handoff = documents["handoff"]
    receipt_validation = documents["receipt_validation"]
    official = documents["tests"]
    slot_catalog = {slot["receipt_slot_id"]: slot for slot in receipt_validation["receipt_slots"]}

    requirements = []
    gate_assignments = []
    role_assignments = []
    for index, link in enumerate(handoff["channel_receipt_slot_links"], start=1):
        slot = slot_catalog[link["cg05_receipt_slot_id"]]
        requirement_id = f"ECR-{index:03d}"
        requirements.append(
            {
                "custody_requirement_id": requirement_id,
                "capture_pair_id": link["capture_pair_id"],
                "capture_channel_id": link["capture_channel_id"],
                "capture_side": link["capture_side"],
                "cg05_receipt_slot_id": link["cg05_receipt_slot_id"],
                "receipt_type": slot["receipt_type"],
                "receipt_classes": slot["receipt_classes"],
                "required_metadata_fields": CUSTODY_METADATA_FIELDS,
                "required_gate_ids": [gate_id for gate_id, _ in CUSTODY_GATES],
                "required_role_types": CUSTODY_ROLE_TYPES,
                "current_state": "MISSING",
                "custody_receipt_reference": None,
                "created_receipt_count": 0,
                "accepted_current_receipt_count": 0,
                "readiness_effect": "NONE",
            }
        )
        gate_assignments.extend(
            {
                "custody_requirement_id": requirement_id,
                "gate_id": gate_id,
                "status": "UNMET",
                "accepted_evidence_count": 0,
            }
            for gate_id, _ in CUSTODY_GATES
        )
        role_assignments.extend(
            {
                "custody_requirement_id": requirement_id,
                "role_type": role,
                "status": "UNASSIGNED",
                "role_receipt_reference": None,
            }
            for role in CUSTODY_ROLE_TYPES
        )

    summary = {
        "capture_pair_count": len(handoff["capture_pairs"]),
        "capture_channel_count": handoff["summary"]["capture_channel_count"],
        "cg05_receipt_slot_count": handoff["summary"]["cg05_receipt_slot_count"],
        "custody_requirement_count": len(requirements),
        "custody_metadata_field_count": len(CUSTODY_METADATA_FIELDS),
        "custody_state_count": len(CUSTODY_STATES),
        "transition_rule_count": len(TRANSITIONS),
        "custody_gate_count": len(CUSTODY_GATES),
        "custody_gate_assignment_count": len(gate_assignments),
        "custody_role_type_count": len(CUSTODY_ROLE_TYPES),
        "custody_role_assignment_count": len(role_assignments),
        "retention_rule_count": len(RETENTION_RULES),
        "rejection_code_count": len(REJECTION_CODES),
        "created_custody_receipt_count": 0,
        "transferred_custody_receipt_count": 0,
        "accepted_current_custody_receipt_count": 0,
        "expired_custody_receipt_count": 0,
        "revoked_custody_receipt_count": 0,
        "superseded_custody_receipt_count": 0,
        "accepted_evidence_count": 0,
        "comparison_handoff_ready_count": 0,
        "result_parity_proven_packet_count": 0,
        "cg05_closed_packet_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_custody_contract": 1404,
        "design_lower_bound_after_custody_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(
            documents[name].get("validation") == "PASS"
            for name in ("handoff", "handoff_checkpoint", "capture", "receipt_validation", "cg05", "adapter", "tests")
        ),
        "pairs_8_channels_16_slots_27_requirements_54": (
            summary["capture_pair_count"],
            summary["capture_channel_count"],
            summary["cg05_receipt_slot_count"],
            summary["custody_requirement_count"],
        )
        == (8, 16, 27, 54),
        "metadata_20_states_9_transitions_12": (
            summary["custody_metadata_field_count"],
            summary["custody_state_count"],
            summary["transition_rule_count"],
        )
        == (20, 9, 12),
        "gates_10_assignments_540": summary["custody_gate_count"] == 10
        and summary["custody_gate_assignment_count"] == 540,
        "roles_4_assignments_216": summary["custody_role_type_count"] == 4
        and summary["custody_role_assignment_count"] == 216,
        "retention_8_rejections_12": summary["retention_rule_count"] == 8
        and summary["rejection_code_count"] == 12,
        "all_missing_gates_unmet_roles_unassigned": all(item["current_state"] == "MISSING" for item in requirements)
        and all(item["status"] == "UNMET" for item in gate_assignments)
        and all(item["status"] == "UNASSIGNED" for item in role_assignments),
        "custody_acceptance_parity_readiness_zero": summary["created_custody_receipt_count"]
        == summary["transferred_custody_receipt_count"]
        == summary["accepted_current_custody_receipt_count"]
        == summary["expired_custody_receipt_count"]
        == summary["revoked_custody_receipt_count"]
        == summary["superseded_custody_receipt_count"]
        == summary["accepted_evidence_count"]
        == summary["comparison_handoff_ready_count"]
        == summary["result_parity_proven_packet_count"]
        == summary["cg05_closed_packet_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_custody_contract"]
        == summary["design_lower_bound_after_custody_contract"]
        == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "design_only_hash_reference_status_custody",
            "continuation_complete": False,
            "evidence_received_or_custody_assumed": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes_to_varanegar_or_erp": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "external_evidence_or_custody_receipts_received": 0,
            "raw_payloads_or_files_persisted": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "custody_metadata_fields": CUSTODY_METADATA_FIELDS,
        "custody_states": CUSTODY_STATES,
        "transition_rules": [
            {
                "from_state": from_state,
                "to_state": to_state,
                "event": event,
                "automatic_promotion_allowed": False,
            }
            for from_state, to_state, event in TRANSITIONS
        ],
        "custody_gates": [
            {"gate_id": gate_id, "gate": gate, "failure_effect": "REJECT_OR_REOPEN_CUSTODY"}
            for gate_id, gate in CUSTODY_GATES
        ],
        "custody_role_types": CUSTODY_ROLE_TYPES,
        "retention_rules": RETENTION_RULES,
        "rejection_codes": REJECTION_CODES,
        "allowed_persistence_categories": ALLOWED_PERSISTENCE,
        "prohibited_persistence_categories": PROHIBITED_PERSISTENCE,
        "custody_requirements": requirements,
        "custody_gate_assignments": gate_assignments,
        "custody_role_assignments": role_assignments,
        "custody_rule": {
            "raw_payload_or_file_storage_allowed": False,
            "hash_only_tombstone_after_disposition_required": True,
            "expired_revoked_or_superseded_receipt_usable": False,
            "automatic_expiry_extension_allowed": False,
            "automatic_state_promotion_allowed": False,
            "revocation_reopens_dependent_handoff_gate": True,
            "supersession_requires_old_new_hash_links": True,
            "accepted_custody_alone_proves_result_parity": False,
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
        ]
        + [
            {
                "name": "builder",
                "path": "scripts/windows/build_varanegar_p3_p4_hash_only_evidence_custody_retention_revocation_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "All fifty-four custody requirements are empty design slots; no external evidence or custody receipt was received.",
            "No raw payload file business value identity credential endpoint key or signature is stored.",
            "Accepted-current custody in a future authorized workflow would still not establish result parity CG-05 closure UAT or readiness.",
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

