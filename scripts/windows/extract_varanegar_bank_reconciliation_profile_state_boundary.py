"""Extract bank-reconciliation profile and state contracts without execution.

The extractor parses allowlisted static IL, consumes the already persisted
read-only clone source-model artifact, and reads SQL Server system catalogs for
the BankAccount2 projection. It does not load an assembly, open a form, execute
a procedure or business command, read a business row, or modify data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.clr.token import StringToken, Token

SQL_SCRIPTS = Path(__file__).resolve().parents[1] / "sql"
if str(SQL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SQL_SCRIPTS))

from extract_varanegar_bank_reconciliation_matching_boundary import (  # noqa: E402
    _method_body,
    _string_value,
)
from extract_varanegar_org_domain import (  # noqa: E402
    _assert_safe_target,
    _connect,
    _rows,
)
from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _analyze_assembly,
    _owner_maps,
    _resolve_token,
)


FORM_ASSEMBLY = "TreasuryOld.Forms.dll"
DATA_ASSEMBLY = "TreasuryOld.DataAccess.dll"
SETUP_TYPE = "TreasuryOld.Forms.frmReconciliationSetup"
DETAIL_TYPE = "TreasuryOld.Forms.frmReconciliation"
MISLEADING_LIST_TYPE = "TreasuryOld.Forms.frmBankReconciliationList"
FILE_PREVIEW_TYPE = "TreasuryOld.Forms.frmBankReconciliation"
BANK_ACCOUNT_ADAPTER = "TreasuryOld.DataLayer.BankAccountAdapter"
PROFILE_GETTERS = {
    "TreasuryOld.DataLayer.BankAccount.get_FormatExtension": "FormatExtension",
    "TreasuryOld.DataLayer.BankAccount.get_HDR": "HDR",
    "TreasuryOld.DataLayer.BankAccount.get_SQLStatement": "SQLStatement",
    "TreasuryOld.DataLayer.BankAccount.get_SchemaFile": "SchemaFile",
}
PROFILE_TABLES = (
    "dbo.BankBillFormat",
    "dbo.BankBillFormatItem",
    "dbo.BankBillFormatType",
    "dbo.ReconciliationColumn",
)
PROFILE_SQL_IDENTIFIERS = {
    "BankAccount2",
    "BankBillFormat",
    "BankBillFormatType",
    "BankAccountType",
    "FormatExtension",
    "FormatFileName",
    "SQLStatement",
    "SchemaFile",
    "HDR",
    "BankBillFormatId",
    "BankBillFormatTypeId",
    "BankId",
    "BankAccountTypeId",
}
FORMAT_KEYS = {"dbf", "txt", "xls"}
COMMAND_KEYS = {"Return", "Ok", "Delete", "Default"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _has_call(row: dict[str, Any], suffix: str) -> bool:
    return any(call.endswith(suffix) for call in row["calls"])


def _contract(type_name: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": type_name,
        "method": row["method"],
        "instruction_count": row["instruction_count"],
        "calls": row["calls"],
        "referenced_fields": row["referenced_fields"],
        "string_literal_values_persisted": 0,
    }


def _allowlisted_literals(
    pe: dnfile.dnPE, type_name: str, method_name: str, allowlist: set[str]
) -> list[str]:
    return sorted(
        {
            value
            for instruction in _method_body(pe, type_name, method_name).instructions
            if isinstance(instruction.operand, StringToken)
            for value in [_string_value(pe, instruction.operand)]
            if value in allowlist
        }
    )


def _inline_profile_projection(pe: dnfile.dnPE) -> dict[str, Any]:
    body = _method_body(pe, BANK_ACCOUNT_ADAPTER, "GetBankAccountWhere")
    sql_literals = [
        _string_value(pe, instruction.operand)
        for instruction in body.instructions
        if isinstance(instruction.operand, StringToken)
        and len(_string_value(pe, instruction.operand)) > 100
    ]
    sql_text = next(iter(sql_literals), "")
    observed_identifiers = sorted(
        identifier
        for identifier in PROFILE_SQL_IDENTIFIERS
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(identifier)}(?![A-Za-z0-9_])", sql_text, re.IGNORECASE)
    )
    return {
        "type": BANK_ACCOUNT_ADAPTER,
        "method": "GetBankAccountWhere",
        "instruction_count": len(body.instructions),
        "inline_projection_sql_sha256": hashlib.sha256(sql_text.encode("utf-8")).hexdigest(),
        "inline_projection_sql_length": len(sql_text),
        "allowlisted_identifier_names": observed_identifiers,
        "raw_sql_text_persisted": False,
        "non_allowlisted_literal_values_persisted": 0,
    }


def _amount_zero_before_set(pe: dnfile.dnPE) -> bool:
    body = _method_body(pe, DETAIL_TYPE, "DoAccept")
    method_owners, field_owners = _owner_maps(pe)
    instructions = list(body.instructions)
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction.operand, Token):
            continue
        resolved = _resolve_token(pe, instruction.operand, method_owners, field_owners)
        if not resolved.endswith("Reconcile.set_Amount"):
            continue
        previous = instructions[max(0, index - 8) : index]
        return any(
            isinstance(candidate.operand, Token)
            and _resolve_token(pe, candidate.operand, method_owners, field_owners)
            == "System.Decimal.Zero"
            for candidate in previous
        )
    return False


def _command_dispatch(pe: dnfile.dnPE) -> dict[str, Any]:
    body = _method_body(pe, DETAIL_TYPE, "cb_CommandClick")
    method_owners, field_owners = _owner_maps(pe)
    instructions = list(body.instructions)
    offsets = {int(instruction.offset): index for index, instruction in enumerate(instructions)}
    rows: list[dict[str, Any]] = []
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction.operand, StringToken):
            continue
        key = _string_value(pe, instruction.operand)
        if key not in COMMAND_KEYS:
            continue
        branch = next(
            (
                candidate
                for candidate in instructions[index + 1 : index + 4]
                if candidate.mnemonic.startswith("brtrue")
            ),
            None,
        )
        target_offset = int(branch.operand) if branch is not None else -1
        target_index = offsets.get(target_offset, -1)
        calls: list[str] = []
        if target_index >= 0:
            for candidate in instructions[target_index : target_index + 45]:
                if candidate.mnemonic in {"call", "callvirt"} and isinstance(candidate.operand, Token):
                    calls.append(
                        _resolve_token(pe, candidate.operand, method_owners, field_owners)
                    )
                if candidate.mnemonic == "ret":
                    break
        rows.append(
            {
                "command_key": key,
                "branch_target_il_offset": target_offset,
                "allowlisted_target_calls": sorted(
                    call
                    for call in set(calls)
                    if call.endswith(("DoAccept", "Form.Close", "BankBill.Update"))
                ),
            }
        )
    return {"method": "cb_CommandClick", "dispatches": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--source-model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = _load(args.binary_inventory)
    source_model = _load(args.source_model)
    expected_hashes = {row["name"]: row["sha256"] for row in inventory["files"]}
    paths = {
        FORM_ASSEMBLY: args.source_directory / FORM_ASSEMBLY,
        DATA_ASSEMBLY: args.source_directory / DATA_ASSEMBLY,
    }
    source_hashes = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in paths.items()
    }
    hash_mismatches = [
        name for name, digest in source_hashes.items() if digest != expected_hashes.get(name)
    ]

    form_analysis = _analyze_assembly(
        paths[FORM_ASSEMBLY],
        {SETUP_TYPE, DETAIL_TYPE, MISLEADING_LIST_TYPE, FILE_PREVIEW_TYPE},
    )
    data_analysis = _analyze_assembly(paths[DATA_ASSEMBLY], {BANK_ACCOUNT_ADAPTER})
    form_by_type = {
        row["type"]: {method["method"]: method for method in row["methods"]}
        for row in form_analysis["target_types"]
    }
    setup = form_by_type[SETUP_TYPE]
    detail = form_by_type[DETAIL_TYPE]
    misleading_list = form_by_type[MISLEADING_LIST_TYPE]
    file_preview = form_by_type[FILE_PREVIEW_TYPE]
    selected = [
        _contract(SETUP_TYPE, setup["cmbBankAccountName_ValueChanged"]),
        _contract(SETUP_TYPE, setup["btnAccept_Click"]),
        _contract(SETUP_TYPE, setup["SaveData"]),
        _contract(DETAIL_TYPE, detail["RefreshSummary"]),
        _contract(DETAIL_TYPE, detail["DoAccept"]),
        _contract(DETAIL_TYPE, detail["cb_CommandClick"]),
        _contract(MISLEADING_LIST_TYPE, misleading_list["ApplyingFilter"]),
        _contract(MISLEADING_LIST_TYPE, misleading_list["SetFormPermission"]),
        _contract(MISLEADING_LIST_TYPE, misleading_list["vGrid_CurrentCellChanged"]),
        _contract(FILE_PREVIEW_TYPE, file_preview["ReadXLS"]),
    ]

    form_pe = dnfile.dnPE(str(paths[FORM_ASSEMBLY]))
    data_pe = dnfile.dnPE(str(paths[DATA_ASSEMBLY]))
    selection_calls = set(setup["cmbBankAccountName_ValueChanged"]["calls"])
    observed_profile_getters = sorted(
        field_name for call, field_name in PROFILE_GETTERS.items() if call in selection_calls
    )
    format_dispatch_keys = _allowlisted_literals(
        form_pe, SETUP_TYPE, "btnAccept_Click", FORMAT_KEYS
    )
    projection = _inline_profile_projection(data_pe)
    command_dispatch = _command_dispatch(form_pe)
    amount_zero = _amount_zero_before_set(form_pe)

    tables_by_name = {row["object"]: row for row in source_model["tables"]}
    profile_tables = [tables_by_name[name] for name in PROFILE_TABLES]
    reconcile = tables_by_name["dbo.Reconcile"]
    profile_row_count = sum(int(row["row_count_snapshot"]) for row in profile_tables)
    reconcile_columns = {row["name"]: row for row in reconcile["columns"]}
    state_marker_columns = [
        reconcile_columns[name] for name in ("ConfirmerId", "ConfirmDate", "Amount")
    ]

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            projection_objects = _rows(
                cursor,
                """
                SELECT o.object_id,s.name AS schema_name,o.name,o.type_desc
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE s.name=%s AND o.name=%s AND o.is_ms_shipped=0
                """,
                ("dbo", "BankAccount2"),
            )
            projection_object_id = (
                int(projection_objects[0]["object_id"])
                if projection_objects
                else -1
            )
            projection_columns = [] if projection_object_id < 0 else _rows(
                cursor,
                """
                SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS data_type,
                       c.is_nullable
                FROM sys.columns c
                WHERE c.object_id=%s
                ORDER BY c.column_id
                """,
                (projection_object_id,),
            )
            projection_dependencies = [] if projection_object_id < 0 else _rows(
                cursor,
                """
                SELECT DISTINCT
                       COALESCE(ds.name,d.referenced_schema_name) AS referenced_schema,
                       COALESCE(do.name,d.referenced_entity_name) AS referenced_object,
                       do.type_desc AS referenced_type_desc,d.is_ambiguous
                FROM sys.sql_expression_dependencies d
                LEFT JOIN sys.objects do ON do.object_id=d.referenced_id
                LEFT JOIN sys.schemas ds ON ds.schema_id=do.schema_id
                WHERE d.referencing_id=%s
                ORDER BY referenced_schema,referenced_object
                """,
                (projection_object_id,),
            )

    ok_dispatch = next(
        (row for row in command_dispatch["dispatches"] if row["command_key"] == "Ok"),
        {},
    )
    errors: list[str] = []
    if hash_mismatches:
        errors.append("source package hash mismatch")
    if len(selected) != 10:
        errors.append("profile/state selected method coverage incomplete")
    if set(observed_profile_getters) != {"FormatExtension", "HDR", "SQLStatement", "SchemaFile"}:
        errors.append("account selection profile projection changed")
    if set(format_dispatch_keys) != FORMAT_KEYS:
        errors.append("format dispatch contract changed")
    if not {"BankAccount2", "FormatExtension", "SQLStatement", "SchemaFile", "HDR"}.issubset(
        set(projection["allowlisted_identifier_names"])
    ):
        errors.append("profile inline projection coverage changed")
    projection_column_names = {row["name"] for row in projection_columns}
    if not {"FormatExtension", "FormatFileName", "BankBillFormatId", "BankBillFormatTypeId", "SQLStatement", "SchemaFile", "HDR"}.issubset(
        projection_column_names
    ):
        errors.append("BankAccount2 profile projection catalog changed")
    projection_dependency_names = {row["referenced_object"] for row in projection_dependencies}
    if not {"BankAccount", "BankBillFormat", "BankBillFormatType"}.issubset(
        projection_dependency_names
    ):
        errors.append("BankAccount2 dependency contract changed")
    if not any(call.endswith("DoAccept") for call in ok_dispatch.get("allowlisted_target_calls", [])):
        errors.append("Ok command no longer dispatches confirmation")
    if not amount_zero:
        errors.append("legacy confirm amount-zero assignment changed")
    if misleading_list["ApplyingFilter"]["instruction_count"] != 1 or misleading_list["ApplyingFilter"]["calls"]:
        errors.append("misleading list empty-loading contract changed")
    if not all(
        _has_call(misleading_list["SetFormPermission"], suffix)
        for suffix in ("TransferList.get_AddNew", "TransferList.get_Edit", "TransferList.get_Delete")
    ):
        errors.append("misleading list transfer permission coupling changed")
    if not _has_call(misleading_list["vGrid_CurrentCellChanged"], "Transfer.get_IsTransferGenerated"):
        errors.append("misleading list transfer row coupling changed")
    if not _has_call(file_preview["ReadXLS"], "Excel.Workbooks.Open"):
        errors.append("file preview Excel boundary changed")
    if profile_row_count != 0 or int(reconcile["row_count_snapshot"]) != 0:
        errors.append("clone business-row emptiness assumption changed")
    if any(name not in reconcile_columns for name in ("ConfirmerId", "ConfirmDate", "Amount")):
        errors.append("reconciliation state marker columns missing")
    if form_analysis["method_body_errors"] or data_analysis["method_body_errors"]:
        errors.append("target method body parse failure")
    if context["updateability"] != "READ_ONLY" or context["can_update"] != 0:
        errors.append("unsafe clone target")

    artifact = {
        "artifact": "varanegar_bank_reconciliation_profile_and_state_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {
            "source_model_artifact": str(args.source_model),
            "snapshot_kind": "STATIC_IL_AND_EXISTING_READ_ONLY_CLONE_CATALOG_ARTIFACT",
        },
        "safety": {
            "mode": "READ_ONLY_STATIC_IL_EXISTING_SOURCE_MODEL_AND_SQL_SYSTEM_CATALOG",
            "assemblies_loaded_or_executed": 0,
            "forms_or_application_commands_executed": 0,
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "database_connections": 1,
            "business_rows_or_values_read_or_persisted": 0,
            "raw_sql_or_profile_values_persisted": 0,
            "unknown_string_literal_values_persisted": 0,
        },
        "summary": {
            "selected_method_contract_count": len(selected),
            "observed_runtime_profile_field_count": len(observed_profile_getters),
            "format_dispatch_key_count": len(format_dispatch_keys),
            "profile_table_count": len(profile_tables),
            "profile_table_row_count_snapshot": profile_row_count,
            "profile_projection_column_count": len(projection_columns),
            "profile_projection_dependency_count": len(projection_dependencies),
            "state_marker_column_count": len(state_marker_columns),
            "explicit_legacy_state_column_count": 0,
            "confirmed_marker_count": 2,
            "source_hash_mismatch_count": len(hash_mismatches),
            "method_body_error_count": len(form_analysis["method_body_errors"])
            + len(data_analysis["method_body_errors"]),
            "validation_error_count": len(errors),
        },
        "source_hashes": [
            {
                "assembly": name,
                "sha256": digest,
                "inventory_sha256_match": name not in hash_mismatches,
            }
            for name, digest in sorted(source_hashes.items())
        ],
        "method_contracts": selected,
        "profile_boundary": {
            "account_selection_method": f"{SETUP_TYPE}.cmbBankAccountName_ValueChanged",
            "observed_runtime_profile_fields": observed_profile_getters,
            "format_dispatch_keys": format_dispatch_keys,
            "inline_bank_account_profile_projection": projection,
            "clone_profile_projection_object": projection_objects[0]
            if projection_objects
            else None,
            "clone_profile_projection_columns": [
                {
                    **row,
                    "column_id": int(row["column_id"]),
                    "is_nullable": bool(row["is_nullable"]),
                }
                for row in projection_columns
            ],
            "clone_profile_projection_dependencies": [
                {**row, "is_ambiguous": bool(row["is_ambiguous"])}
                for row in projection_dependencies
            ],
            "profile_tables": profile_tables,
            "profile_tables_have_version_or_effective_date_column": False,
            "profile_tables_have_active_or_approval_column": False,
            "start_row_separator_and_arabic_form_getter_observed": False,
            "profile_values_available_in_clone_snapshot": False,
        },
        "legacy_state_boundary": {
            "storage_has_explicit_state_or_status_column": False,
            "state_marker_columns": state_marker_columns,
            "confirm_command_dispatch": ok_dispatch,
            "confirm_method": f"{DETAIL_TYPE}.DoAccept",
            "confirm_sets_confirmer_id": _has_call(detail["DoAccept"], "Reconcile.set_ConfirmerId"),
            "confirm_sets_confirm_date": _has_call(detail["DoAccept"], "Reconcile.set_ConfirmDate"),
            "confirm_sets_amount_to_decimal_zero": amount_zero,
            "confirm_updates_reconcile": _has_call(detail["DoAccept"], "Reconcile.Update"),
            "confirm_updates_bank_account_cardex": _has_call(
                detail["DoAccept"], "ReconcileAdapter.UpdateBankAccountCardex"
            ),
            "confirm_transaction_calls": sorted(
                call for call in detail["DoAccept"]["calls"] if "Transaction." in call
            ),
            "detail_form_has_own_permission_method": False,
            "detail_form_has_operation_date_guard_call": False,
            "cancel_or_reverse_state_marker_observed": False,
        },
        "misleading_named_root_boundary": {
            "list_type": MISLEADING_LIST_TYPE,
            "list_applying_filter_instruction_count": misleading_list["ApplyingFilter"]["instruction_count"],
            "list_applying_filter_calls": misleading_list["ApplyingFilter"]["calls"],
            "permission_alias_calls": sorted(
                call
                for call in misleading_list["SetFormPermission"]["calls"]
                if call.startswith("TransferList.")
            ),
            "row_state_call": "TreasuryOld.DataLayer.Transfer.get_IsTransferGenerated",
            "child_type": FILE_PREVIEW_TYPE,
            "child_read_xls_uses_office_interop": True,
            "core_reconcile_query_or_row_load_observed": False,
            "classification": "UNRESOLVED_TEMPLATE_OR_FILE_PREVIEW_SURFACE_NOT_A_PROVEN_RECONCILIATION_QUEUE",
            "direct_target_route_or_command_inference_allowed": False,
            "deletion_or_scope_exclusion_authorized": False,
            "requires_runtime_telemetry_or_process_owner_confirmation": True,
        },
        "target_contract": {
            "profile_aggregate": "BankStatementFormatProfile",
            "profile_is_versioned_approved_and_immutable_after_use": True,
            "raw_sql_provider_or_path_configuration_allowed": False,
            "parser_kind_is_typed_enum_not_extension_string": True,
            "profile_selection_is_server_owned_by_bank_and_account_type": True,
            "states": [
                "IMPORTED_UNCONFIRMED",
                "CONFIRMED",
                "INCONSISTENT_LEGACY_MARKERS_QUARANTINED",
            ],
            "unconfirmed_marker": "ConfirmerId IS NULL AND ConfirmDate IS NULL",
            "confirmed_marker": "ConfirmerId IS NOT NULL AND ConfirmDate IS NOT NULL",
            "inconsistent_marker": "exactly one of ConfirmerId or ConfirmDate is NULL",
            "confirm_requires_explicit_state_permission_scope_date_and_version_guards": True,
            "legacy_amount_zero_is_not_a_computed_reconciliation_result": True,
            "cancelled_or_reversed_state_inferred_from_legacy": False,
            "cancel_and_reverse_require_separate_owner_approved_contracts": True,
            "authorization_must_be_enforced_server_side_not_inherited_from_parent_ui": True,
        },
        "method_body_errors": form_analysis["method_body_errors"]
        + data_analysis["method_body_errors"],
        "validation_errors": errors,
        "limits": [
            "Profile tables and Reconcile are empty in the current clone source-model snapshot.",
            "Static IL proves field and call shape, not a successful authenticated workflow.",
            "No parser result, profile value, SQL text, file content, identity, or business row was read or persisted.",
            "Null-marker states are a target normalization contract; legacy row distributions are unavailable.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], "summary": artifact["summary"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
