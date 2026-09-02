"""Build a bounded closure contract for the three unresolved Varanegar roots."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOTS = (
    "TreasuryOld.Forms.frmBankReconciliationList",
    "TreasuryOld.Forms.frmReconciliationSetup",
    "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-entrypoints", required=True, type=Path)
    parser.add_argument("--deployment-scan", required=True, type=Path)
    parser.add_argument("--declared-fields", required=True, type=Path)
    parser.add_argument("--profile-state-boundary", required=True, type=Path)
    parser.add_argument("--special-options-assessment", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    entrypoints = _load(args.root_entrypoints)
    deployment = _load(args.deployment_scan)
    fields = _load(args.declared_fields)
    profile_state = _load(args.profile_state_boundary)
    special = _load(args.special_options_assessment)
    for name, payload in (
        ("root entrypoints", entrypoints),
        ("deployment scan", deployment),
        ("declared fields", fields),
        ("profile/state boundary", profile_state),
        ("special options assessment", special),
    ):
        legacy_root_scan_is_valid = (
            name == "root entrypoints"
            and payload.get("schema_version") == 1
            and payload.get("summary", {}).get("unexpected_method_body_error_count") == 0
        )
        if payload.get("validation") != "PASS" and not legacy_root_scan_is_valid:
            raise ValueError(f"validated {name} artifact is required")

    entry_by_type = {row["type"]: row for row in entrypoints["resolutions"]}
    deployment_by_type = {
        row["target_type"]: row for row in deployment["target_resolutions"]
    }
    fields_by_type = {row["form_type"]: row for row in fields["forms"]}
    if set(entry_by_type) != set(ROOTS) or set(deployment_by_type) != set(ROOTS):
        raise ValueError("unresolved root set changed")

    common_static_evidence = {
        "all_assembly_count": entrypoints["summary"]["assembly_count"],
        "all_assembly_external_reference_count": entrypoints["summary"]["external_target_token_reference_count"],
        "deployment_selected_file_count": deployment["summary"]["selected_file_count"],
        "deployment_bytes_scanned": deployment["summary"]["bytes_scanned"],
        "deployment_external_occurrence_count": deployment["summary"]["external_occurrence_count"],
    }
    root_contracts = [
        {
            "root_type": ROOTS[0],
            "classification": profile_state["misleading_named_root_boundary"]["classification"],
            "business_logic_evidence": {
                "declared_control_field_count": fields_by_type[ROOTS[0]]["declared_control_field_count"],
                "applying_filter_instruction_count": profile_state["misleading_named_root_boundary"]["list_applying_filter_instruction_count"],
                "applying_filter_call_count": len(profile_state["misleading_named_root_boundary"]["list_applying_filter_calls"]),
                "permission_alias_calls": profile_state["misleading_named_root_boundary"]["permission_alias_calls"],
                "row_state_call": profile_state["misleading_named_root_boundary"]["row_state_call"],
                "child_is_file_preview": profile_state["misleading_named_root_boundary"]["child_read_xls_uses_office_interop"],
                "core_reconcile_query_or_load_observed": False,
            },
            "provisional_target_disposition": "DO_NOT_CREATE_RECONCILIATION_QUEUE_ROUTE",
            "runtime_telemetry_required": True,
            "owner_question": "Was this screen ever used as a transfer-derived file preview, and is it present in any active menu or shortcut?",
            "closure_if_observed": "capture the exact launcher, parent/menu key and read source; then reclassify from runtime evidence",
            "closure_if_not_observed": "owner signs scope exclusion while preserving artifact for audit",
        },
        {
            "root_type": ROOTS[1],
            "classification": "REAL_BANK_STATEMENT_IMPORT_AND_SESSION_SETUP_LOGIC_WITH_UNRESOLVED_LAUNCHER",
            "business_logic_evidence": {
                "declared_control_field_count": fields_by_type[ROOTS[1]]["declared_control_field_count"],
                "write_like_methods": fields_by_type[ROOTS[1]]["write_like_methods"],
                "permission_methods": fields_by_type[ROOTS[1]]["permission_methods"],
                "profile_runtime_field_count": profile_state["summary"]["observed_runtime_profile_field_count"],
                "format_dispatch_key_count": profile_state["summary"]["format_dispatch_key_count"],
                "source_model_and_command_contracts_exist": True,
            },
            "provisional_target_disposition": "KEEP_IMPORT_WORKFLOW_IN_SCOPE_BUT_ROUTE_MAPPING_PROVISIONAL",
            "runtime_telemetry_required": True,
            "owner_question": "From which active menu, shortcut, reflection dispatcher or parent action is statement import opened today?",
            "closure_if_observed": "bind the exact launcher and permission node to the existing import contract",
            "closure_if_not_observed": "owner decides whether the workflow is replaced by a new approved web entrypoint; do not infer a legacy route",
        },
        {
            "root_type": ROOTS[2],
            "classification": special["assessment"]["classification"],
            "business_logic_evidence": {
                "declared_control_field_count": special["summary"]["direct_declared_field_count"],
                "business_method_count": special["summary"]["form_business_method_count"],
                "static_route_count": special["summary"]["static_route_count"],
                "clone_catalog_candidate_count": special["summary"]["clone_catalog_candidate_count"],
            },
            "provisional_target_disposition": "NO_TARGET_SCHEMA_COMMAND_OR_ROUTE_INFERENCE",
            "runtime_telemetry_required": True,
            "owner_question": "Is Special Options District licensed or used in any environment, and what business capability would it represent?",
            "closure_if_observed": "capture launcher, entitlement and bound data object before defining any target capability",
            "closure_if_not_observed": "owner signs scope exclusion; deletion of source remains separately governed",
        },
    ]
    for row in root_contracts:
        root = row["root_type"]
        row["static_entrypoint_evidence"] = {
            **common_static_evidence,
            "entrypoint_status": entry_by_type[root]["status"],
            "constructor_entrypoint_count": entry_by_type[root]["constructor_entrypoint_count"],
            "exact_or_embedded_string_reference_count": entry_by_type[root]["exact_string_reference_count"]
            + entry_by_type[root]["embedded_string_reference_count"],
            "deployment_reference_status": deployment_by_type[root]["deployment_reference_status"],
            "external_deployment_occurrence_count": deployment_by_type[root]["external_occurrence_count"],
        }
        row["automatic_deletion_or_scope_exclusion_authorized"] = False
        row["additional_identical_static_scan_recommended"] = False

    errors: list[str] = []
    if len(root_contracts) != 3:
        errors.append("root closure coverage incomplete")
    if any(row["static_entrypoint_evidence"]["constructor_entrypoint_count"] for row in root_contracts):
        errors.append("root constructor evidence changed")
    if any(row["static_entrypoint_evidence"]["external_deployment_occurrence_count"] for row in root_contracts):
        errors.append("external deployment reference evidence changed")
    if any(row["automatic_deletion_or_scope_exclusion_authorized"] for row in root_contracts):
        errors.append("unsafe automatic scope disposition")

    telemetry_contract = {
        "mode": "ALLOWLISTED_RUNTIME_ACTIVATION_TELEMETRY_WITHOUT_BUSINESS_VALUES_OR_IDENTITY",
        "events": [
            "form_activation_attempted",
            "form_activation_succeeded_or_failed",
            "menu_or_dispatcher_route_selected",
            "form_data_source_bound_or_remained_empty",
        ],
        "allowed_fields": [
            "captured_at_utc",
            "environment_key",
            "application_version",
            "assembly_name_and_sha256",
            "allowlisted_form_type",
            "activation_source_kind",
            "allowlisted_parent_form_type_or_menu_key",
            "permission_node_key_without_assignment",
            "success_or_failure_class",
            "data_source_type_name_without_query_or_values",
        ],
        "forbidden_fields": [
            "user_identity_or_group_membership",
            "credential_or_connection_string",
            "business_row_or_field_value",
            "file_path_or_file_content",
            "raw_sql_or_exception_payload",
        ],
        "minimum_sessions": 3,
        "required_variations": [
            "one allowed role/account context",
            "one denied role/account context",
            "one direct owner-guided navigation attempt",
        ],
        "source_write_or_command_execution_required": False,
    }
    artifact = {
        "artifact": "varanegar_three_unresolved_root_evidence_closure_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "STATIC_SCAN_EXHAUSTED_RUNTIME_OR_OWNER_EVIDENCE_REQUIRED",
        "safety": {
            "mode": "OFFLINE_DERIVED_FROM_VALIDATED_READ_ONLY_ARTIFACTS",
            "database_connections": 0,
            "network_reads": 0,
            "live_ui_actions": 0,
            "application_or_business_commands_executed": 0,
            "identity_or_business_values_used": 0,
            "source_or_target_changes": 0,
        },
        "summary": {
            "root_count": len(root_contracts),
            "real_logic_unresolved_launcher_count": 1,
            "template_or_preview_candidate_count": 1,
            "placeholder_or_dynamic_candidate_count": 1,
            "resolved_by_static_evidence_count": 0,
            "automatic_scope_exclusion_count": 0,
            "runtime_or_owner_evidence_required_count": 3,
            "additional_identical_static_scan_recommended_count": 0,
            "validation_error_count": len(errors),
        },
        "root_contracts": root_contracts,
        "runtime_telemetry_contract": telemetry_contract,
        "decision_policy": {
            "absence_of_static_reference_proves_unused": False,
            "empty_or_template_shape_authorizes_deletion": False,
            "real_business_logic_without_launcher_stays_in_domain_scope": True,
            "target_navigation_mapping_requires_runtime_or_owner_evidence": True,
            "scope_exclusion_requires_named_owner_signoff": True,
        },
        "source_evidence": [path.as_posix() for path in (
            args.root_entrypoints,
            args.deployment_scan,
            args.declared_fields,
            args.profile_state_boundary,
            args.special_options_assessment,
        )],
        "validation_errors": errors,
        "limits": [
            "This contract does not observe a live authenticated session or identify a user.",
            "Runtime telemetry is specified but not installed or collected.",
            "Owner questions are unresolved and no root is authorized for deletion or automatic exclusion.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], "summary": artifact["summary"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
