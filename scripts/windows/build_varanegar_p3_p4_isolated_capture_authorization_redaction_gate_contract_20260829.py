"""Build a design-only isolated-capture authorization and redaction gate contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "fixture": "artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.json",
    "cg05": "artifacts/varanegar_analysis/varanegar_p3_p4_cg05_result_parity_receipt_matrix_20260829.json",
    "adjudication": "artifacts/varanegar_analysis/varanegar_p3_p4_golden_uat_result_adjudication_promotion_guard_20260829.json",
    "adapter": "artifacts/varanegar_analysis/varanegar_target_erp_hash_only_comparison_adapter_contract_20260829.json",
    "codec": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_contract_20260829.json",
    "codec_checkpoint": "artifacts/varanegar_analysis/varanegar_target_erp_comparison_adapter_synthetic_negative_reference_codec_checkpoint_20260829.json",
    "tests": "artifacts/varanegar_analysis/varanegar_25h_final_test_result_20260829.json",
    "risk": "artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json",
    "trace": "artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json",
}

AUTHORIZATION_REQUEST_FIELDS = [
    "capture_authorization_request_id",
    "cg05_packet_id",
    "fixture_contract_id",
    "capture_side",
    "isolated_environment_reference",
    "environment_attestation_sha256",
    "golden_case_id_set_sha256",
    "parity_dimension_id_set_sha256",
    "requested_capture_operation_class",
    "capture_command_allowlist_sha256",
    "requesting_role_receipt_reference",
    "data_owner_approval_receipt_reference",
    "security_approval_receipt_reference",
    "execution_operator_role_receipt_reference",
    "independent_reviewer_role_receipt_reference",
    "redaction_policy_version_sha256",
    "scope_policy_version_sha256",
    "valid_from",
    "valid_until",
    "maximum_capture_attempt_count",
    "temporary_storage_ttl_seconds",
    "revocation_receipt_reference",
    "previous_authorization_sha256",
    "authorization_status",
]

REDACTION_ATTESTATION_FIELDS = [
    "capture_authorization_request_id",
    "capture_attempt_id",
    "capture_side",
    "input_manifest_sha256",
    "hash_only_output_manifest_sha256",
    "redaction_policy_version_sha256",
    "prohibited_category_scan_status",
    "category_count_map_sha256",
    "raw_payload_persisted",
    "temporary_material_destroyed",
    "execution_operator_role_receipt_reference",
    "independent_reviewer_role_receipt_reference",
    "produced_at",
    "expires_at",
    "previous_attestation_sha256",
    "attestation_receipt_sha256",
    "exception_count",
    "attestation_status",
]

AUTHORIZATION_GATES = [
    ("CAG-01", "packet_case_and_dimension_scope_exact"),
    ("CAG-02", "isolated_environment_attested"),
    ("CAG-03", "legacy_source_read_only_and_no_mutation_proven"),
    ("CAG-04", "target_candidate_non_production_and_disposable"),
    ("CAG-05", "network_egress_and_unapproved_endpoint_denied"),
    ("CAG-06", "capture_operation_allowlist_hash_approved"),
    ("CAG-07", "legacy_and_target_have_separate_authorization_tokens"),
    ("CAG-08", "bounded_time_window_attempt_count_and_ttl"),
    ("CAG-09", "request_approval_operation_review_sod"),
    ("CAG-10", "redaction_and_scope_policy_versions_pinned"),
    ("CAG-11", "prohibited_category_fail_closed_scan"),
    ("CAG-12", "only_hash_count_status_and_reference_persistence"),
    ("CAG-13", "temporary_material_destruction_attestation_required"),
    ("CAG-14", "abort_revocation_incident_and_recollection_plan"),
]

ROLE_TYPES = [
    "CAPTURE_REQUESTER_ROLE",
    "DATA_OWNER_APPROVER_ROLE",
    "SECURITY_APPROVER_ROLE",
    "CAPTURE_EXECUTION_OPERATOR_ROLE",
    "INDEPENDENT_CAPTURE_REVIEWER_ROLE",
    "EVIDENCE_CUSTODIAN_ROLE",
]

SOD_RULES = [
    ("SOD-CAP-01", "requester_must_not_be_data_owner_approver"),
    ("SOD-CAP-02", "requester_must_not_be_security_approver"),
    ("SOD-CAP-03", "execution_operator_must_not_be_independent_reviewer"),
    ("SOD-CAP-04", "evidence_custodian_must_not_approve_own_exception"),
    ("SOD-CAP-05", "one_person_must_not_control_request_approval_execution_and_acceptance"),
]

AUTHORIZATION_STATES = [
    "DRAFT",
    "PENDING_DATA_OWNER_AND_SECURITY",
    "APPROVED_NOT_ACTIVE",
    "ACTIVE_BOUNDED",
    "COMPLETED_PENDING_REVIEW",
    "EXPIRED",
    "REVOKED",
    "CLOSED_WITH_ATTESTATION",
]

ALLOWED_PERSISTENCE = [
    "opaque_references",
    "sha256_hashes",
    "bounded_counts",
    "typed_statuses_and_error_codes",
    "policy_and_schema_version_hashes",
    "authorization_and_role_receipt_references",
    "timestamps_expiry_and_ttl_metadata",
    "hash_only_manifest_and_dimension_disposition",
]

PROHIBITED_CATEGORIES = [
    "raw_business_values",
    "row_or_item_payloads",
    "customer_supplier_personnel_or_user_identity",
    "pii_contact_address_or_financial_identifier",
    "credentials_or_connection_strings",
    "sql_rule_or_procedure_text",
    "report_render_or_export_file_bytes",
    "filesystem_or_network_endpoint_details",
    "authentication_tokens_or_session_material",
    "cryptographic_private_or_public_key_material",
    "signature_bytes",
    "unredacted_exception_samples",
    "screen_image_or_print_preview_content",
    "database_backup_snapshot_or_transaction_log_content",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_hash(values: list[str]) -> str:
    payload = json.dumps(sorted(values), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {name: ROOT / relative for name, relative in SOURCES.items()}
    documents = {name: load(path) for name, path in paths.items()}
    fixture = documents["fixture"]
    official = documents["tests"]

    channels = []
    gate_assignments = []
    role_assignments = []
    for contract in fixture["fixture_contracts"]:
        for side in contract["required_capture_sides"]:
            channel_id = f"CAP-{contract['cg05_packet_id']}-{side}"
            channels.append(
                {
                    "capture_channel_id": channel_id,
                    "cg05_packet_id": contract["cg05_packet_id"],
                    "fixture_contract_id": contract["fixture_contract_id"],
                    "lane": contract["lane"],
                    "command_or_surface": contract["command_or_surface"],
                    "golden_case_count": contract["golden_case_count"],
                    "golden_case_id_set_sha256": contract["golden_case_id_set_sha256"],
                    "parity_dimension_id_set_sha256": set_hash(contract["required_parity_dimension_ids"]),
                    "capture_side": side,
                    "authorization_status": "NOT_REQUESTED",
                    "authorization_token_reference": None,
                    "authorization_request_count": 0,
                    "approved_authorization_count": 0,
                    "capture_attempt_count": 0,
                    "redaction_attestation_count": 0,
                    "accepted_capture_receipt_count": 0,
                    "result_parity_effect": "NONE_UNTIL_SEPARATE_ADJUDICATION",
                }
            )
            gate_assignments.extend(
                {
                    "capture_channel_id": channel_id,
                    "gate_id": gate_id,
                    "status": "UNMET",
                    "accepted_evidence_count": 0,
                }
                for gate_id, _ in AUTHORIZATION_GATES
            )
            role_assignments.extend(
                {
                    "capture_channel_id": channel_id,
                    "role_type": role,
                    "status": "UNASSIGNED",
                    "role_receipt_reference": None,
                }
                for role in ROLE_TYPES
            )

    summary = {
        "packet_count": len(fixture["fixture_contracts"]),
        "golden_case_count": sum(contract["golden_case_count"] for contract in fixture["fixture_contracts"]),
        "capture_side_count": len({side for contract in fixture["fixture_contracts"] for side in contract["required_capture_sides"]}),
        "capture_channel_count": len(channels),
        "authorization_request_field_count": len(AUTHORIZATION_REQUEST_FIELDS),
        "redaction_attestation_field_count": len(REDACTION_ATTESTATION_FIELDS),
        "authorization_gate_count": len(AUTHORIZATION_GATES),
        "authorization_gate_assignment_count": len(gate_assignments),
        "role_type_count": len(ROLE_TYPES),
        "role_assignment_count": len(role_assignments),
        "sod_rule_count": len(SOD_RULES),
        "authorization_state_count": len(AUTHORIZATION_STATES),
        "allowed_persistence_category_count": len(ALLOWED_PERSISTENCE),
        "prohibited_category_count": len(PROHIBITED_CATEGORIES),
        "authorization_request_count": 0,
        "approved_authorization_count": 0,
        "active_authorization_count": 0,
        "capture_attempt_count": 0,
        "captured_side_count": 0,
        "redaction_attestation_count": 0,
        "accepted_capture_receipt_count": 0,
        "result_parity_proven_packet_count": 0,
        "owner_approved_packet_count": 0,
        "command_ready_module_count": 0,
        "pilot_ready_module_count": 0,
        "design_lower_bound_before_capture_authorization_contract": 1404,
        "design_lower_bound_after_capture_authorization_contract": 1404,
        "official_test_file_count": official["runner"]["test_file_count"],
        "official_passed_test_count": official["runner"]["passed_test_count"],
        "risk_count": documents["risk"]["summary"]["risk_count"],
        "mapped_risk_assignment_count": documents["trace"]["summary"]["mapped_risk_assignment_count"],
        "new_risk_count": 0,
    }
    checks = {
        "sources_pass": all(
            documents[name].get("validation") == "PASS"
            for name in ("fixture", "cg05", "adjudication", "adapter", "codec", "codec_checkpoint", "tests")
        ),
        "packets_8_cases_56_sides_2_channels_16": (
            summary["packet_count"],
            summary["golden_case_count"],
            summary["capture_side_count"],
            summary["capture_channel_count"],
        )
        == (8, 56, 2, 16),
        "schemas_24_18": (summary["authorization_request_field_count"], summary["redaction_attestation_field_count"])
        == (24, 18),
        "gates_14_assignments_224": summary["authorization_gate_count"] == 14
        and summary["authorization_gate_assignment_count"] == 224,
        "roles_6_assignments_96_sod_5": (
            summary["role_type_count"],
            summary["role_assignment_count"],
            summary["sod_rule_count"],
        )
        == (6, 96, 5),
        "two_separate_channels_per_packet": all(
            {channel["capture_side"] for channel in channels if channel["cg05_packet_id"] == contract["cg05_packet_id"]}
            == {"LEGACY_REFERENCE", "TARGET_CANDIDATE"}
            for contract in fixture["fixture_contracts"]
        ),
        "all_gates_unmet_roles_unassigned": all(item["status"] == "UNMET" for item in gate_assignments)
        and all(item["status"] == "UNASSIGNED" for item in role_assignments),
        "persistence_allow_8_prohibit_14": summary["allowed_persistence_category_count"] == 8
        and summary["prohibited_category_count"] == 14,
        "authorization_capture_parity_readiness_zero": summary["authorization_request_count"]
        == summary["approved_authorization_count"]
        == summary["active_authorization_count"]
        == summary["capture_attempt_count"]
        == summary["captured_side_count"]
        == summary["redaction_attestation_count"]
        == summary["accepted_capture_receipt_count"]
        == summary["result_parity_proven_packet_count"]
        == summary["owner_approved_packet_count"]
        == summary["command_ready_module_count"]
        == summary["pilot_ready_module_count"]
        == 0,
        "non_additive_1404": summary["design_lower_bound_before_capture_authorization_contract"]
        == summary["design_lower_bound_after_capture_authorization_contract"]
        == 1404,
        "official_tests_pass": official["validation"] == "PASS" and official["runner"]["bootstrap_excluded_test_file_count"] == 0,
        "base_stable": summary["risk_count"] == 84 and summary["mapped_risk_assignment_count"] == 343,
    }
    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "artifact": "varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not failed else "FAIL",
        "scope": {
            "mode": "design_only_isolated_capture_authorization_and_redaction_gate",
            "continuation_complete": False,
            "authorization_or_capture_granted": False,
        },
        "safety": {
            "database_connections": 0,
            "network_reads_or_writes_to_varanegar_or_erp": 0,
            "operational_forms_reports_queries_or_procedures_executed": 0,
            "assemblies_loaded_or_executed": 0,
            "data_mutations": 0,
            "capture_authorizations_issued": 0,
            "capture_attempts": 0,
            "raw_business_values_identity_or_credentials_persisted": 0,
        },
        "summary": summary,
        "authorization_request_fields": AUTHORIZATION_REQUEST_FIELDS,
        "redaction_attestation_fields": REDACTION_ATTESTATION_FIELDS,
        "authorization_states": AUTHORIZATION_STATES,
        "authorization_gates": [
            {"gate_id": gate_id, "gate": gate, "failure_effect": "DENY_CAPTURE"}
            for gate_id, gate in AUTHORIZATION_GATES
        ],
        "role_types": ROLE_TYPES,
        "segregation_of_duties_rules": [
            {"rule_id": rule_id, "rule": rule, "currently_satisfied": False}
            for rule_id, rule in SOD_RULES
        ],
        "allowed_persistence_categories": ALLOWED_PERSISTENCE,
        "prohibited_capture_or_persistence_categories": PROHIBITED_CATEGORIES,
        "capture_channels": channels,
        "authorization_gate_assignments": gate_assignments,
        "role_assignments": role_assignments,
        "authorization_rule": {
            "legacy_and_target_authorized_separately": True,
            "all_fourteen_gates_required": True,
            "approval_auto_activates_capture": False,
            "activation_requires_bounded_window_attempt_count_and_ttl": True,
            "expired_or_revoked_authorization_reusable": False,
            "authorization_scope_expansion_allowed": False,
            "capture_success_implies_result_parity": False,
            "redaction_attestation_required_before_evidence_intake": True,
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
                "path": "scripts/windows/build_varanegar_p3_p4_isolated_capture_authorization_redaction_gate_contract_20260829.py",
                "size_bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            }
        ],
        "limits": [
            "This artifact defines authorization requirements but does not request issue activate or approve an authorization.",
            "No legacy or target capture occurred and no raw values files identities credentials endpoints or signatures are stored.",
            "A future authorized capture still requires an isolated environment named accountable owners and independently accepted receipts.",
            "Capture completion does not establish result parity CG-05 closure UAT or readiness.",
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

