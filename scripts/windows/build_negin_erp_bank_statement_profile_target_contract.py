"""Build a target profile-catalog contract from validated Varanegar evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-state", required=True, type=Path)
    parser.add_argument("--parser-row", required=True, type=Path)
    parser.add_argument("--owner-decisions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    inputs = {
        "profile_state": _load(args.profile_state),
        "parser_row": _load(args.parser_row),
        "owner_decisions": _load(args.owner_decisions),
    }
    invalid = sorted(name for name, value in inputs.items() if value.get("validation") != "PASS")
    profile = inputs["profile_state"]
    parser_row = inputs["parser_row"]
    decisions = inputs["owner_decisions"]
    canonical_columns = parser_row["target_contract"]["canonical_columns_are_schema_validated_before_commit"]
    dormant_decision = next(
        row for row in decisions["decisions"] if row["decision_id"] == "BR-DEC-004"
    )

    entities = [
        {
            "entity": "BankStatementFormatProfile",
            "purpose": "versioned server-owned parser selection and lifecycle",
            "fields": [
                ["profile_id", "uuid", "primary key"],
                ["profile_family_id", "uuid", "stable identity across versions"],
                ["version", "positive integer", "unique within family"],
                ["bank_id", "uuid/reference", "required approved bank scope"],
                ["bank_account_type_id", "uuid/reference", "required selection scope"],
                ["parser_kind", "enum", "DBF_ADAPTER, DELIMITED_TEXT, FIXED_WIDTH_TEXT, SPREADSHEET_TABLE"],
                ["lifecycle_state", "enum", "DRAFT, PENDING_APPROVAL, APPROVED, RETIRED"],
                ["effective_from", "instant", "required only when approved"],
                ["effective_to", "instant/null", "exclusive upper bound"],
                ["content_sha256", "sha256", "covers profile and ordered mappings"],
                ["created_by_actor_id", "uuid/reference", "audited target identity"],
                ["created_at", "instant", "server timestamp"],
                ["approved_by_actor_id", "uuid/reference/null", "required only when approved"],
                ["approved_at", "instant/null", "required only when approved"],
            ],
        },
        {
            "entity": "BankStatementFieldMapping",
            "purpose": "typed mapping to the six canonical staging columns",
            "fields": [
                ["mapping_id", "uuid", "primary key"],
                ["profile_id", "uuid/reference", "immutable profile version"],
                ["canonical_field", "enum", canonical_columns],
                ["source_selector_kind", "enum", "COLUMN_NAME, COLUMN_INDEX, FIXED_RANGE"],
                ["source_column_name", "bounded string/null", "data only, never SQL"],
                ["source_start", "nonnegative integer/null", "typed index/range"],
                ["source_end", "nonnegative integer/null", "typed range"],
                ["normalizer_kind", "enum", "allowlisted pure transform"],
                ["ordinal", "nonnegative integer", "stable mapping order"],
            ],
        },
        {
            "entity": "BankStatementProfileParserOptions",
            "purpose": "typed optional parser settings with explicit activation evidence",
            "fields": [
                ["profile_id", "uuid/reference", "one-to-one profile version"],
                ["header_mode", "enum/null", "ABSENT, PRESENT; not raw HDR pass-through"],
                ["start_row", "nonnegative integer/null", "parser-supported only"],
                ["delimiter", "single unicode scalar/null", "delimited parser only"],
                ["text_direction", "enum/null", "AUTO, RTL, LTR"],
                ["options_activation_status", "enum", "INERT_PENDING_APPROVAL or ACTIVE"],
            ],
        },
    ]

    invariants = [
        "profile versions are immutable after approval or first use",
        "one approved effective profile per bank and account type at an instant",
        "content hash changes whenever any profile option or ordered mapping changes",
        "approver actor differs from the actor who submitted the version",
        "raw SQL, provider names, connection strings, executable expressions and filesystem paths have no schema field",
        "parser kind and source selector kind are closed server-owned enums",
        "all six canonical fields are present exactly once before a profile can be approved",
        "mapping ranges are valid and parser-kind compatible",
        "dormant legacy options stay inert until BR-DEC-004 is approved and typed parser tests pass",
        "profile selection is server-side and constrained by bank, account type, effective time and approval state",
        "retirement never mutates a historical version used by an import",
        "preview and commit require the same profile_id, version and content_sha256",
    ]
    commands = [
        {
            "command": "CreateProfileDraft",
            "capability": "bank_reconciliation.profile.manage",
            "allowed_state": None,
            "result_state": "DRAFT",
        },
        {
            "command": "SubmitProfileForApproval",
            "capability": "bank_reconciliation.profile.manage",
            "allowed_state": "DRAFT",
            "result_state": "PENDING_APPROVAL",
        },
        {
            "command": "ApproveProfileVersion",
            "capability": "bank_reconciliation.profile.approve",
            "allowed_state": "PENDING_APPROVAL",
            "result_state": "APPROVED",
        },
        {
            "command": "RetireProfileVersion",
            "capability": "bank_reconciliation.profile.approve",
            "allowed_state": "APPROVED",
            "result_state": "RETIRED",
        },
    ]
    acceptance = [
        "draft cannot be selected by an import",
        "unapproved and retired versions cannot be selected for a new import",
        "overlapping approved effective ranges are rejected",
        "missing or duplicate canonical mapping is rejected",
        "raw SQL/provider/path input is rejected as an unknown field and never evaluated",
        "unsupported parser or selector enum is rejected",
        "submitter cannot approve the same version",
        "stale expected version causes zero mutation",
        "same idempotency key returns the original command result",
        "preview-to-commit profile hash change is rejected",
        "an import retains its historical profile version after retirement",
        "dormant options remain inert while BR-DEC-004 is NOT_APPROVED",
    ]
    errors: list[str] = []
    if invalid:
        errors.append("invalid inputs: " + ", ".join(invalid))
    expected_columns = {"Date", "Comment", "Debit", "Credit", "No1", "BaLance"}
    if set(canonical_columns) != expected_columns:
        errors.append("canonical parser columns changed")
    if profile["summary"]["profile_table_row_count_snapshot"] != 0:
        errors.append("profile clone snapshot is no longer empty; refresh parity interpretation")
    if dormant_decision["decision_status"] != "NOT_APPROVED":
        errors.append("BR-DEC-004 approval state changed and requires contract review")

    payload = {
        "artifact": "negin_erp_bank_statement_versioned_profile_catalog_target_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "SCHEMA_AND_COMMAND_CONTRACT_READY_NOT_IMPLEMENTED_OR_OWNER_APPROVED",
        "safety": {
            "mode": "OFFLINE_VALIDATED_ARTIFACT_COMPOSITION",
            "database_connections": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_rows_or_identity_values_read": 0,
            "owner_approvals_inferred": 0,
        },
        "source_facts": {
            "legacy_profile_table_count": profile["summary"]["profile_table_count"],
            "legacy_profile_row_count_snapshot": profile["summary"]["profile_table_row_count_snapshot"],
            "legacy_runtime_profile_field_count": profile["summary"]["observed_runtime_profile_field_count"],
            "legacy_profile_has_version_effective_or_approval": False,
            "canonical_columns": canonical_columns,
            "dormant_option_decision_id": dormant_decision["decision_id"],
            "dormant_option_decision_status": dormant_decision["decision_status"],
        },
        "summary": {
            "source_artifact_count": len(inputs),
            "entity_count": len(entities),
            "field_count": sum(len(row["fields"]) for row in entities),
            "invariant_count": len(invariants),
            "command_contract_count": len(commands),
            "distinct_profile_capability_count": 2,
            "acceptance_obligation_count": len(acceptance),
            "approved_owner_decision_count": decisions["summary"]["approved_decision_count"],
            "implementation_execution_count": 0,
            "validation_error_count": len(errors),
        },
        "entities": entities,
        "invariants": invariants,
        "command_contracts": commands,
        "acceptance_obligations": acceptance,
        "non_inference_rules": [
            "legacy table-column presence does not activate a parser option",
            "an empty clone does not prove production has no profiles",
            "the target schema contract is not a deployed migration or runtime parity result",
        ],
        "validation_errors": errors,
        "limits": [
            "No real profile row exists in the current clone for value parity.",
            "Capability names and role assignment remain owner/security proposals.",
            "No database migration or application implementation is produced by this artifact.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(json.dumps({"validation": payload["validation"], "summary": payload["summary"]}, ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
