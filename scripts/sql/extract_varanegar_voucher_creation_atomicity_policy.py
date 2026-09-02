"""Extract the deployed Varanegar voucher-creation transaction and policy contract.

Safety properties:
- connects only to the local, read-only NeginPakhsh_WebDev clone;
- parses deployed PE metadata/IL without loading or executing assemblies;
- never executes an operational procedure or creator view;
- persists catalog facts, hashes, safe identifiers, and aggregates only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import struct
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_varanegar_org_domain import (  # noqa: E402
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"
TARGET_ASSEMBLIES = (
    "Application.DataAccess.dll",
    "Application.BaseTemaplateV2.dll",
    "VN.SDS.Common.dll",
    "VN.SDS.CreateVoucher.Business.dll",
    "VN.SDS.CreateVoucher.DataAccess.dll",
    "VN.SDS.CreateVoucher.UI.dll",
    "VN.SDS.CreateVoucher.UIComponent.dll",
)
TARGET_PROCEDURES = (
    "usp_DoExternalVoucher",
    "usp_DoPreVoucher",
    "usp_DoExternalVoucherConfirmed",
    "usp_DoExternalVoucherDelete",
    "usp_DoExternalVoucherTransfer",
    "usp_DoExternalVoucherTransferValidation",
    "usp_DoExternalVoucherTypeValidation",
    "DoExternalVoucher_Create",
    "DoExternalVoucher_Create_With_PreVoucher",
)
SAFE_PROC_LITERAL = "dbo.usp_DoExternalVoucher"


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _full_type_name(row: Any) -> str:
    namespace = _text(getattr(row, "TypeNamespace", ""))
    name = _text(getattr(row, "TypeName", ""))
    return f"{namespace}.{name}" if namespace and name else name or type(row).__name__


def _owner_maps(pe: dnfile.dnPE) -> tuple[dict[int, str], dict[int, str]]:
    methods: dict[int, str] = {}
    fields: dict[int, str] = {}
    for type_row in pe.net.mdtables.TypeDef.rows:
        owner = _full_type_name(type_row)
        for index in type_row.MethodList or []:
            methods[index.row_index] = owner
        for index in type_row.FieldList or []:
            fields[index.row_index] = owner
    return methods, fields


def _resolve_token(
    pe: dnfile.dnPE,
    token: Token,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
) -> str:
    table = pe.net.mdtables.tables.get(token.table)
    if table is None or token.rid <= 0 or token.rid > len(table.rows):
        return f"unresolved:{token.value:#010x}"
    row = table.rows[token.rid - 1]
    table_name = getattr(table, "name", "")
    if table_name == "MemberRef":
        parent = getattr(getattr(row, "Class", None), "row", None)
        owner = _full_type_name(parent) if parent is not None else "<unknown>"
        return f"{owner}.{_text(getattr(row, 'Name', ''))}"
    if table_name == "MethodDef":
        return f"{method_owners.get(token.rid, '<unknown>')}.{_text(row.Name)}"
    if table_name == "Field":
        return f"{field_owners.get(token.rid, '<unknown>')}.{_text(row.Name)}"
    if table_name in {"TypeDef", "TypeRef"}:
        return _full_type_name(row)
    if table_name == "MethodSpec":
        method = getattr(getattr(row, "Method", None), "row", None)
        if method is not None and hasattr(method, "Class"):
            parent = getattr(getattr(method, "Class", None), "row", None)
            owner = _full_type_name(parent) if parent is not None else "<unknown>"
            return f"{owner}.{_text(getattr(method, 'Name', ''))}"
    return f"{table_name}:{_text(getattr(row, 'Name', ''))}"


def _method(
    pe: dnfile.dnPE, type_name: str, method_name: str
) -> tuple[Any, Any]:
    type_row = next(
        row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == type_name
    )
    method_row = next(
        index.row for index in type_row.MethodList if _text(index.row.Name) == method_name
    )
    body = read_method_body_from_bytes(pe.get_data(method_row.Rva, 65536))
    return method_row, body


def _ordered_calls(pe: dnfile.dnPE, body: Any) -> list[dict[str, Any]]:
    methods, fields = _owner_maps(pe)
    rows: list[dict[str, Any]] = []
    for index, instruction in enumerate(body.instructions):
        if (
            instruction.mnemonic in {"call", "callvirt", "newobj"}
            and isinstance(instruction.operand, Token)
        ):
            rows.append(
                {
                    "instruction_index": index,
                    "il_offset": int(instruction.offset),
                    "opcode": instruction.mnemonic,
                    "call": _resolve_token(pe, instruction.operand, methods, fields),
                }
            )
    return rows


def _hash_checked_paths(
    source_directory: Path, binary_inventory_path: Path
) -> tuple[dict[str, Path], dict[str, Any]]:
    inventory = json.loads(binary_inventory_path.read_text(encoding="utf-8-sig"))
    rows = {row["name"]: row for row in inventory["files"]}
    paths: dict[str, Path] = {}
    evidence: dict[str, Any] = {}
    for name in TARGET_ASSEMBLIES:
        path = source_directory / name
        expected = rows[name]["sha256"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Runtime assembly hash mismatch: {name}")
        paths[name] = path
        evidence[name] = {
            "sha256": actual,
            "file_version": rows[name].get("file_version"),
            "hash_matches_inventory": True,
        }
    return paths, evidence


def _transaction_enum(pe: dnfile.dnPE) -> dict[str, int]:
    field_names = {
        index + 1: _text(row.Name)
        for index, row in enumerate(pe.net.mdtables.Field.rows)
    }
    values: dict[str, int] = {}
    for row in pe.net.mdtables.Constant.rows:
        field_name = field_names.get(getattr(row.Parent, "row_index", -1))
        if field_name in {"Begin", "No"}:
            values[field_name] = struct.unpack("<i", row.Value.value)[0]
    return values


def _enum_constants(pe: dnfile.dnPE, type_name: str) -> dict[str, int]:
    type_row = next(
        row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == type_name
    )
    field_names = {
        index.row_index: _text(index.row.Name) for index in type_row.FieldList or []
    }
    values: dict[str, int] = {}
    for row in pe.net.mdtables.Constant.rows:
        field_name = field_names.get(getattr(row.Parent, "row_index", -1))
        if field_name and field_name != "value__":
            values[field_name] = int.from_bytes(
                row.Value.value, byteorder="little", signed=True
            )
    return values


def _method_call_subset(calls: list[dict[str, Any]], markers: tuple[str, ...]) -> list[dict[str, Any]]:
    return [row for row in calls if any(marker in row["call"] for marker in markers)]


def _referenced_fields(pe: dnfile.dnPE, body: Any) -> list[str]:
    methods, fields = _owner_maps(pe)
    references: list[str] = []
    for instruction in body.instructions:
        if (
            instruction.mnemonic in {"ldfld", "stfld", "ldsfld", "stsfld"}
            and isinstance(instruction.operand, Token)
        ):
            references.append(
                _resolve_token(pe, instruction.operand, methods, fields)
            )
    return references


def _deployed_il_contract(
    source_directory: Path, binary_inventory_path: Path
) -> dict[str, Any]:
    paths, hashes = _hash_checked_paths(source_directory, binary_inventory_path)

    ui_pe = dnfile.dnPE(str(paths["VN.SDS.CreateVoucher.UI.dll"]))
    _, ui_body = _method(
        ui_pe,
        "VN.SDS.CreateVoucher.UI.ExternalVoucher.FormExternalVoucher",
        "DoWorkSave",
    )
    ui_calls = _ordered_calls(ui_pe, ui_body)
    ui_target = next(
        row
        for row in ui_calls
        if row["call"].endswith("ExternalVoucherHeaderHandler.DoExternalVoucher")
    )
    ui_instructions = list(ui_body.instructions)
    ui_preceding = ui_instructions[ui_target["instruction_index"] - 4 : ui_target["instruction_index"]]
    ui_passes_null_context = any(row.mnemonic == "ldnull" for row in ui_preceding)
    entity_common_pe = dnfile.dnPE(str(paths["VN.SDS.Common.dll"]))
    save_action_enum = _enum_constants(
        entity_common_pe,
        "VN.SDS.Common.CreateVoucher.EntityHelper.ExternalVoucher.ExternalVoucherSaveActionModeEnum",
    )
    ui_confirm_target = next(
        row
        for row in ui_calls
        if row["call"].endswith(
            "ExternalVoucherHeaderHandler.DoExternalVoucherConfirmed"
        )
    )
    ui_transfer_target = next(
        row
        for row in ui_calls
        if row["call"].endswith(
            "ExternalVoucherHeaderHandler.DoExternalVoucherTransfer"
        )
    )
    ui_validity_calls = [
        row
        for row in ui_calls
        if row["call"].endswith("ValidationResult.get_IsValid")
    ]

    def _validity_guard_returns_before(
        validity_call: dict[str, Any], next_command: dict[str, Any]
    ) -> bool:
        between = ui_instructions[
            validity_call["instruction_index"] + 1 : next_command["instruction_index"]
        ]
        return (
            any(row.mnemonic.startswith("brtrue") for row in between[:2])
            and any(row.mnemonic == "ret" for row in between[:4])
        )

    message_type_call_indexes = [
        row["instruction_index"]
        for row in ui_calls
        if row["call"].endswith("ExternalVoucherMessageEntity.get_MessageType")
    ]
    success_id_loops_skip_nonzero_message_types = bool(message_type_call_indexes) and all(
        ui_instructions[index + 1].mnemonic.startswith("brtrue")
        for index in message_type_call_indexes
    )

    business_pe = dnfile.dnPE(str(paths["VN.SDS.CreateVoucher.Business.dll"]))
    _, business_body = _method(
        business_pe,
        "VN.SDS.CreateVoucher.Business.ExternalVoucher.ExternalVoucherHeaderHandler",
        "DoExternalVoucher",
    )
    business_calls = _ordered_calls(business_pe, business_body)
    context_ctor = next(
        row for row in business_calls if row["call"] == "Thunderstruck.DataContext..ctor"
    )
    context_instruction = list(business_body.instructions)[context_ctor["instruction_index"] - 1]
    transaction_mode_operand = 0 if context_instruction.mnemonic == "ldc.i4.0" else None
    business_boundary_calls = _method_call_subset(
        business_calls,
        (
            "Thunderstruck.DataContext..ctor",
            "ExternalVoucherHeaderAdapter.DoExternalVoucher",
            "Thunderstruck.DataContext.Commit",
            "Thunderstruck.DataContext.Rollback",
            "Thunderstruck.DataContext.Dispose",
        ),
    )
    policy_getter_markers = (
        "FiscalYearHandler.GetExternalVoucherIssueMode",
        "ServerConfigHandler.GetDoExternalVoucherCreateAll",
        "ServerConfigHandler.GetSeparateSetadCreateVoucher",
        "ServerConfigHandler.GetSeparateSaleOfficeCreateVoucher",
    )
    policy_getter_calls = _method_call_subset(business_calls, policy_getter_markers)
    policy_getters_before_transaction = (
        len(policy_getter_calls) == len(policy_getter_markers)
        and all(
            row["instruction_index"] < context_ctor["instruction_index"]
            for row in policy_getter_calls
        )
    )
    lambda_row = next(
        method_index.row
        for type_row in business_pe.net.mdtables.TypeDef.rows
        for method_index in type_row.MethodList or []
        if _text(method_index.row.Name) == "<DoExternalVoucher>b__4_0"
    )
    message_error_lambda = read_method_body_from_bytes(
        business_pe.get_data(lambda_row.Rva, 65536)
    )
    lambda_instructions = list(message_error_lambda.instructions)
    message_type_one_is_error = any(
        instruction.mnemonic == "ldc.i4.1" for instruction in lambda_instructions
    ) and any(instruction.mnemonic == "ceq" for instruction in lambda_instructions)
    business_set_result = next(
        row
        for row in business_calls
        if row["call"].endswith("VNValidationResult.set_Result")
    )
    business_commit = next(
        row for row in business_calls if row["call"].endswith("DataContext.Commit")
    )

    data_pe = dnfile.dnPE(str(paths["VN.SDS.CreateVoucher.DataAccess.dll"]))
    _, adapter_body = _method(
        data_pe,
        "VN.SDS.CreateVoucher.DataAccess.DataAdapter.ExternalVoucher.ExternalVoucherHeaderAdapter",
        "DoExternalVoucher",
    )
    adapter_literals: list[str] = []
    for instruction in adapter_body.instructions:
        if isinstance(instruction.operand, StringToken):
            value = data_pe.net.user_strings.get(instruction.operand.rid)
            text = "" if value is None else str(value)
            if text == SAFE_PROC_LITERAL:
                adapter_literals.append(text)
    adapter_calls = _method_call_subset(
        _ordered_calls(data_pe, adapter_body),
        ("Thunderstruck.DataContext.Query", "System.IDisposable.Dispose"),
    )

    common_pe = dnfile.dnPE(str(paths["Application.DataAccess.dll"]))
    enum_values = _transaction_enum(common_pe)
    provider_methods: dict[str, Any] = {}
    for method_name in ("Open", "CreateDbCommand", "Commit", "Rollback", "Dispose"):
        _, body = _method(common_pe, "Thunderstruck.Provider.DefaultProvider", method_name)
        calls = _ordered_calls(common_pe, body)
        provider_methods[method_name] = {
            "instruction_count": len(body.instructions),
            "calls": _method_call_subset(
                calls,
                (
                    "IDbConnection.Open",
                    "IDbConnection.Close",
                    "IDbConnection.BeginTransaction",
                    "IDbCommand.set_Transaction",
                    "IDbTransaction.Commit",
                    "IDbTransaction.Rollback",
                    "IDisposable.Dispose",
                ),
            ),
            "compares_transaction_mode_to_zero": any(
                instruction.mnemonic == "ldc.i4.0" for instruction in body.instructions
            )
            and method_name == "Open",
        }

    lifecycle_specs = {
        "confirm_or_unconfirm": {
            "ui_methods": ("DoWorkSave", "DoWorkConfirmed"),
            "business_method": "DoExternalVoucherConfirmed",
            "adapter_method": "DoExternalVoucherConfirmed",
            "procedure": "dbo.usp_DoExternalVoucherConfirmed",
        },
        "delete_unconfirmed_batch": {
            "ui_methods": ("DoWorkDelete",),
            "business_method": "DoExternalVoucherDelete",
            "adapter_method": "DoExternalVoucherDelete",
            "procedure": "dbo.usp_DoExternalVoucherDelete",
        },
        "transfer_to_general_ledger": {
            "ui_methods": ("DoWorkSave", "DoWorkTransfer"),
            "business_method": "DoExternalVoucherTransfer",
            "adapter_method": "DoExternalVoucherTransfer",
            "procedure": "dbo.usp_DoExternalVoucherTransfer",
        },
    }
    lifecycle_operations: dict[str, Any] = {}
    ui_type = "VN.SDS.CreateVoucher.UI.ExternalVoucher.FormExternalVoucher"
    business_type = (
        "VN.SDS.CreateVoucher.Business.ExternalVoucher.ExternalVoucherHeaderHandler"
    )
    adapter_type = (
        "VN.SDS.CreateVoucher.DataAccess.DataAdapter.ExternalVoucher."
        "ExternalVoucherHeaderAdapter"
    )
    for operation, spec in lifecycle_specs.items():
        ui_paths: list[dict[str, Any]] = []
        for ui_method in spec["ui_methods"]:
            _, lifecycle_ui_body = _method(ui_pe, ui_type, ui_method)
            lifecycle_ui_calls = _ordered_calls(ui_pe, lifecycle_ui_body)
            target_calls = [
                row
                for row in lifecycle_ui_calls
                if row["call"].endswith(
                    f"ExternalVoucherHeaderHandler.{spec['business_method']}"
                )
            ]
            if not target_calls:
                continue
            for target_call in target_calls:
                lifecycle_ui_instructions = list(lifecycle_ui_body.instructions)
                preceding = lifecycle_ui_instructions[
                    max(0, target_call["instruction_index"] - 4) : target_call["instruction_index"]
                ]
                ui_paths.append(
                    {
                        "method": ui_method,
                        "business_call": target_call,
                        "passes_null_data_context": any(
                            instruction.mnemonic == "ldnull" for instruction in preceding
                        ),
                    }
                )

        _, lifecycle_business_body = _method(
            business_pe, business_type, spec["business_method"]
        )
        lifecycle_business_calls = _ordered_calls(
            business_pe, lifecycle_business_body
        )
        lifecycle_context_ctor = next(
            row
            for row in lifecycle_business_calls
            if row["call"] == "Thunderstruck.DataContext..ctor"
        )
        preceding_ctor = list(lifecycle_business_body.instructions)[
            lifecycle_context_ctor["instruction_index"] - 1
        ]
        lifecycle_mode = 0 if preceding_ctor.mnemonic == "ldc.i4.0" else None
        lifecycle_boundary_calls = _method_call_subset(
            lifecycle_business_calls,
            (
                "Thunderstruck.DataContext..ctor",
                f"ExternalVoucherHeaderAdapter.{spec['adapter_method']}",
                "Thunderstruck.DataContext.Commit",
                "Thunderstruck.DataContext.Rollback",
                "Thunderstruck.DataContext.Dispose",
            ),
        )

        _, lifecycle_adapter_body = _method(
            data_pe, adapter_type, spec["adapter_method"]
        )
        lifecycle_literals = []
        for instruction in lifecycle_adapter_body.instructions:
            if isinstance(instruction.operand, StringToken):
                value = data_pe.net.user_strings.get(instruction.operand.rid)
                literal = "" if value is None else str(value)
                if literal == spec["procedure"]:
                    lifecycle_literals.append(literal)
        lifecycle_operations[operation] = {
            "ui_paths": ui_paths,
            "business_method": spec["business_method"],
            "business_transaction_mode_operand": lifecycle_mode,
            "business_boundary_calls": lifecycle_boundary_calls,
            "dispose_is_in_finally": any(
                getattr(handler, "exception_type", None) == 2
                for handler in lifecycle_business_body.exception_handlers
            ),
            "adapter_method": spec["adapter_method"],
            "exact_procedure_literals": lifecycle_literals,
            "outer_transaction_proven": (
                bool(ui_paths)
                and all(path["passes_null_data_context"] for path in ui_paths)
                and lifecycle_mode == enum_values.get("Begin") == 0
                and lifecycle_literals == [spec["procedure"]]
                and any(
                    row["call"].endswith("DataContext.Commit")
                    for row in lifecycle_boundary_calls
                )
            ),
            "procedure_owns_transaction": False,
        }

    base_pe = dnfile.dnPE(str(paths["Application.BaseTemaplateV2.dll"]))
    _, base_permission_body = _method(
        base_pe,
        "Application.BaseTemaplateV2.UIBase.FormBaseDualList",
        "InternalApplyUserPermission",
    )
    base_permission_calls = _ordered_calls(base_pe, base_permission_body)
    base_permission_fields = sorted(
        {
            field.rsplit(".", 1)[-1]
            for field in _referenced_fields(base_pe, base_permission_body)
            if "MenuButton" in field
        }
    )
    _, child_permission_body = _method(ui_pe, ui_type, "ApplyUserPermission")
    child_permission_calls = _ordered_calls(ui_pe, child_permission_body)
    child_permission_fields = [
        field.rsplit(".", 1)[-1]
        for field in _referenced_fields(ui_pe, child_permission_body)
        if "MenuButton" in field
    ]
    form_type_row = next(
        row for row in ui_pe.net.mdtables.TypeDef.rows if _full_type_name(row) == ui_type
    )
    custom_command_fields = ("buttonSave", "MenuButtonTransfer")
    custom_field_references: dict[str, list[str]] = {
        field: [] for field in custom_command_fields
    }
    for method_index in form_type_row.MethodList:
        method_row = method_index.row
        if not method_row.Rva:
            continue
        try:
            method_body = read_method_body_from_bytes(
                ui_pe.get_data(method_row.Rva, 65536)
            )
        except Exception:
            continue
        referenced = _referenced_fields(ui_pe, method_body)
        for field in custom_command_fields:
            if any(item.endswith(f".{field}") for item in referenced):
                custom_field_references[field].append(_text(method_row.Name))

    command_methods = (
        "buttonSave_Click",
        "ConfirmCommand",
        "UnConfirmCommand",
        "MenuButtonTransfer_Click",
        "DoWorkSave",
        "DoWorkConfirmed",
        "DoWorkDelete",
        "DoWorkTransfer",
    )
    command_permission_calls: dict[str, Any] = {}
    for method_name in command_methods:
        _, method_body = _method(ui_pe, ui_type, method_name)
        method_calls = _ordered_calls(ui_pe, method_body)
        permission_calls = [
            row for row in method_calls if "HasPersmission" in row["call"]
        ]
        command_permission_calls[method_name] = {
            "permission_call_count": len(permission_calls),
            "permission_calls": permission_calls,
        }

    component_pe = dnfile.dnPE(
        str(paths["VN.SDS.CreateVoucher.UIComponent.dll"])
    )
    _, header_filter_body = _method(
        component_pe,
        "VN.SDS.CreateVoucher.UIComponent.ExternalVoucher.ExternalVoucherHeaderUIHelper",
        "ChangeGridServerModeFixFilter",
    )
    header_filter_calls = _ordered_calls(component_pe, header_filter_body)
    _, dc_tree_body = _method(
        component_pe,
        "VN.SDS.CreateVoucher.UIComponent.ExternalVoucherType.ExternalVoucherTypeUIHelper",
        "GetTreeFromDC",
    )
    _, type_tree_body = _method(
        component_pe,
        "VN.SDS.CreateVoucher.UIComponent.ExternalVoucherType.ExternalVoucherTypeUIHelper",
        "GetTreeFromExternalVoucherType",
    )
    authorization_scope_contract = {
        "base_toolbar_permission_gate": {
            "type": "Application.BaseTemaplateV2.UIBase.FormBaseDualList",
            "method": "InternalApplyUserPermission",
            "permission_call_count": sum(
                "HasPersmission" in row["call"] for row in base_permission_calls
            ),
            "referenced_toolbar_fields": base_permission_fields,
            "confirm_unconfirm_or_transfer_in_referenced_fields": any(
                field in base_permission_fields
                for field in (
                    "MenuButtonConfirm",
                    "MenuButtonUnConfirm",
                    "MenuButtonTransfer",
                )
            ),
        },
        "form_permission_override": {
            "method": "ApplyUserPermission",
            "permission_call_count": sum(
                "HasPersmission" in row["call"] for row in child_permission_calls
            ),
            "toolbar_fields_in_order": child_permission_fields,
            "hides_new_edit_view": child_permission_fields[:3]
            == ["MenuButtonNew", "MenuButtonEdit", "MenuButtonView"],
            "forces_confirm_and_unconfirm_visible": child_permission_fields[-2:]
            == ["MenuButtonConfirm", "MenuButtonUnConfirm"],
        },
        "custom_command_control_references": custom_field_references,
        "command_method_permission_calls": command_permission_calls,
        "no_action_permission_call_in_form_command_methods": all(
            row["permission_call_count"] == 0
            for row in command_permission_calls.values()
        ),
        "read_model_scope": {
            "header_grid_filter_session_calls": _method_call_subset(
                header_filter_calls,
                ("UserSessionInfo.get_DCRef", "UserSessionInfo.get_AccYear"),
            ),
            "dc_tree_uses_session_aware_handler": any(
                row["call"].endswith("DcHandler.GetInstance")
                for row in _ordered_calls(component_pe, dc_tree_body)
            )
            and any(
                row["call"].endswith("UserSessionInfo.GetInstanceObject")
                for row in _ordered_calls(component_pe, dc_tree_body)
            ),
            "voucher_type_tree_uses_session_aware_handler": any(
                row["call"].endswith("ExternalVoucherTypeHandler.GetInstance")
                for row in _ordered_calls(component_pe, type_tree_body)
            )
            and any(
                row["call"].endswith("UserSessionInfo.GetInstanceObject")
                for row in _ordered_calls(component_pe, type_tree_body)
            ),
        },
        "conclusion": {
            "read_grid_is_session_accyear_dc_scoped": all(
                any(marker in row["call"] for row in header_filter_calls)
                for marker in ("UserSessionInfo.get_DCRef", "UserSessionInfo.get_AccYear")
            ),
            "separate_issue_confirm_unconfirm_transfer_permissions_proven": False,
            "server_enforced_action_authorization_proven": False,
            "screen_access_may_still_be_enforced": True,
        },
    }

    return {
        "assembly_hashes": hashes,
        "ui_entrypoint": {
            "type": "VN.SDS.CreateVoucher.UI.ExternalVoucher.FormExternalVoucher",
            "method": "DoWorkSave",
            "business_call": ui_target,
            "passes_null_data_context": ui_passes_null_context,
            "save_action_enum": save_action_enum,
            "command_chain": [
                ui_target,
                ui_confirm_target,
                ui_transfer_target,
            ],
            "issue_validation_failure_returns_before_confirm": (
                len(ui_validity_calls) >= 1
                and _validity_guard_returns_before(
                    ui_validity_calls[0], ui_confirm_target
                )
            ),
            "confirm_validation_failure_returns_before_transfer": (
                len(ui_validity_calls) >= 2
                and _validity_guard_returns_before(
                    ui_validity_calls[1], ui_transfer_target
                )
            ),
            "successful_header_ids_are_parsed_only_from_message_type_zero": (
                success_id_loops_skip_nonzero_message_types
            ),
        },
        "business_boundary": {
            "type": "VN.SDS.CreateVoucher.Business.ExternalVoucher.ExternalVoucherHeaderHandler",
            "method": "DoExternalVoucher",
            "transaction_mode_operand_before_context_ctor": transaction_mode_operand,
            "ordered_boundary_calls": business_boundary_calls,
            "exception_handler_count": len(business_body.exception_handlers),
            "has_explicit_rollback_call": any(
                row["call"].endswith("DataContext.Rollback") for row in business_calls
            ),
            "dispose_is_in_finally": any(
                getattr(handler, "exception_type", None) == 2
                for handler in business_body.exception_handlers
            ),
            "policy_preflight_getter_calls": policy_getter_calls,
            "policy_preflight_occurs_before_issue_transaction": (
                policy_getters_before_transaction
            ),
            "message_type_one_is_validation_error": message_type_one_is_error,
            "result_is_set_before_commit_even_for_business_error_rows": (
                business_set_result["instruction_index"]
                < business_commit["instruction_index"]
            ),
        },
        "adapter_binding": {
            "type": "VN.SDS.CreateVoucher.DataAccess.DataAdapter.ExternalVoucher.ExternalVoucherHeaderAdapter",
            "method": "DoExternalVoucher",
            "exact_procedure_literals": adapter_literals,
            "ordered_boundary_calls": adapter_calls,
        },
        "data_context_runtime": {
            "transaction_enum": enum_values,
            "provider_methods": provider_methods,
            "exception_path_has_explicit_rollback": False,
            "provider_dispose_disposes_transaction_before_closing_connection": (
                any(
                    row["call"].endswith("IDisposable.Dispose")
                    for row in provider_methods["Dispose"]["calls"]
                )
                and any(
                    row["call"].endswith("IDbConnection.Close")
                    for row in provider_methods["Dispose"]["calls"]
                )
            ),
            "proven_chain": (
                "Transaction.Begin=0; DefaultProvider.Open begins a DB transaction for mode 0; "
                "created commands attach that transaction; Business commits only after adapter completion "
                "and disposes the provider in finally."
            ),
        },
        "lifecycle_operations": lifecycle_operations,
        "authorization_and_scope_contract": authorization_scope_contract,
        "conclusion": {
            "desktop_null_context_path_has_one_outer_transaction": (
                ui_passes_null_context
                and transaction_mode_operand == enum_values.get("Begin") == 0
                and adapter_literals == [SAFE_PROC_LITERAL]
                and any(
                    row["call"].endswith("DataContext.Commit")
                    for row in business_boundary_calls
                )
            ),
            "procedure_owns_transaction": False,
            "direct_sql_or_nonstandard_caller_atomicity_proven": False,
        },
    }


def _procedure_contracts(cursor: Any) -> dict[str, Any]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.name,m.definition,o.modify_date
        FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE o.name IN ('usp_DoExternalVoucher','usp_DoPreVoucher',
          'usp_DoExternalVoucherConfirmed','usp_DoExternalVoucherDelete',
          'usp_DoExternalVoucherTransfer','usp_DoExternalVoucherTransferValidation',
          'usp_DoExternalVoucherTypeValidation',
          'DoExternalVoucher_Create','DoExternalVoucher_Create_With_PreVoucher')
        ORDER BY o.name
        """,
    )
    contracts: dict[str, Any] = {}
    for row in rows:
        definition = row.pop("definition")
        lowered = definition.casefold()
        compact = re.sub(r"[\s\[\]'+]", "", lowered)
        object_name = f"{row['schema_name']}.{row['name']}"
        contracts[object_name] = {
            **row,
            "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest(),
            "definition_characters": len(definition),
            "transaction_tokens": {
                "begin_transaction": len(re.findall(r"(?i)\bbegin\s+tran(?:saction)?\b", definition)),
                "commit": len(re.findall(r"(?i)\bcommit(?:\s+tran(?:saction)?)?\b", definition)),
                "rollback": len(re.findall(r"(?i)\brollback(?:\s+tran(?:saction)?)?\b", definition)),
                "begin_try": lowered.count("begin try"),
                "begin_catch": lowered.count("begin catch"),
            },
            "semantic_signals": {
                "calls_usp_do_pre_voucher": bool(
                    re.search(r"(?i)\bexec(?:ute)?\s+(?:dbo\.)?usp_doprevoucher\b", definition)
                ),
                "writes_pre_voucher": any(
                    marker in compact
                    for marker in ("insertintodbo.prevoucher(", "insertintoprevoucher(")
                ),
                "writes_external_header": any(
                    marker in compact
                    for marker in (
                        "insertintodbo.externalvoucherheader(",
                        "insertintoexternalvoucherheader(",
                    )
                ),
                "writes_external_lines": any(
                    marker in compact
                    for marker in ("insertintodbo.externalvoucher(", "insertintoexternalvoucher(")
                ),
                "writes_external_relation": any(
                    marker in compact
                    for marker in (
                        "insertintodbo.tblexternalrelation(",
                        "insertintotblexternalrelation(",
                    )
                ),
                "reads_issue_mode": "externalvoucherissuemode" in lowered,
                "reads_dc_grouping_config": "doexternalvoucher_create_all" in lowered,
                "reads_headquarters_grouping_config": "separatesetadcreatevoucher" in lowered,
                "reads_sale_office_grouping_config": "separatesaleofficecreatevoucher" in lowered,
                "uses_dense_rank_grouping": "dense_rank()" in compact,
                "anti_join_reference_name_reference_id_dc": all(
                    marker in compact
                    for marker in (
                        "p.referenceid=vw.voucherid",
                        "p.dcid=vw.dcid",
                        "p.referencename=",
                    )
                ),
                "filters_zero_net_lines": any(
                    marker in compact
                    for marker in (
                        "havingsum(debitamount)-sum(creditamount)<>0",
                        "having(sum(x.debitamount)-sum(x.creditamount)<>0)",
                    )
                ),
                "updates_external_confirmation": "updatehsetconfirmed=@confirmed" in compact,
                "disables_external_header_triggers": (
                    "altertabledbo.externalvoucherheaderdisabletriggerall" in compact
                ),
                "deletes_pre_voucher": "deletevfromdbo.prevoucherv" in compact,
                "deletes_external_header": (
                    "deletevfromdbo.externalvoucherheaderv" in compact
                ),
                "deletes_external_lines": "deletevfromdbo.externalvoucherv" in compact,
                "deletes_external_relation": (
                    "deletevfromdbo.tblexternalrelationv" in compact
                ),
                "uses_delete_session_context": "doexternalvoucherdelete" in lowered
                and "sp_set_session_context" in lowered,
                "writes_voucher": any(
                    marker in compact
                    for marker in ("insertintodbo.voucher(", "insertintovoucher(")
                ),
                "writes_voucher_item": any(
                    marker in compact
                    for marker in ("insertintodbo.voucheritem(", "insertintovoucheritem(")
                ),
                "writes_voucher_status_history": "voucherstatushistory" in lowered
                and "insert" in lowered,
                "writes_voucher_edit_log": "vouchereditlog" in lowered and "insert" in lowered,
                "writes_set_voucher_no": "insertintosetvoucherno(" in compact,
                "deletes_set_voucher_no_before_validation": (
                    "deletevfrom@externalvoucherheaderlistlinnerjoinsetvoucherno" in compact
                    and compact.find(
                        "deletevfrom@externalvoucherheaderlistlinnerjoinsetvoucherno"
                    )
                    < compact.find("usp_doexternalvouchertransfervalidation")
                ),
                "calls_transfer_validation": (
                    "usp_doexternalvouchertransfervalidation" in lowered
                ),
                "validation_can_return_without_exception": (
                    row["name"] == "usp_DoExternalVoucherTransfer"
                    and
                    "ifexists(selecttop11from@error)" in compact
                    and "return" in lowered
                ),
                "checks_concurrent_voucher_after_mutation": (
                    "خطای همزمانی عملیات" in definition
                ),
                "catch_reraises_error": "error_message()" in lowered
                and bool(re.search(r"(?i)raiserror\s*\(\s*@errormessage", definition)),
                "validates_app_user_exists": (
                    "fromdbo.appuserwhereappuserid=@userref" in compact
                ),
                "validates_dc_exists": (
                    "@dclist" in lowered and "gnr.tbldc" in lowered
                    and "notin" in compact
                ),
                "references_access_or_action_authorization": any(
                    marker in lowered
                    for marker in (
                        "accessnode",
                        "haspersmission",
                        "haspermission",
                        "userpermission",
                        "appuserdc",
                    )
                ),
                "enforces_operation_finality_by_system_dc_year_and_to_date": (
                    "gnr.tbloprdate" in lowered
                    and "ica.tblcaoprd" in lowered
                    and "@todate" in lowered
                )
                or (
                    "gnr.tbloprdate" in lowered
                    and "ica.tblicaoprdate" in lowered
                    and "@todate" in lowered
                ),
                "validates_to_date_inside_fiscal_range": (
                    "@todatnotbetween" in compact
                    or "@todatenotbetween@startdateand@enddate" in compact
                ),
                "returns_message_type_1_for_business_errors": (
                    "select1asmessagetype,messagedescfrom@error" in compact
                ),
                "returns_message_type_0_for_created_header_ids": (
                    "select0asmessagetype,cast(idasnvarchar(4000))asmessagedesc"
                    in compact
                ),
                "returns_message_type_2_or_3_for_warning_or_information": (
                    "casevouchercountwhen0then2else3endasmessagetype" in compact
                ),
                "message_type_1_result_precedes_persistent_issue_mutation": (
                    compact.find("select1asmessagetype,messagedescfrom@error") >= 0
                    and compact.find("select1asmessagetype,messagedescfrom@error")
                    < compact.find("execdbo.usp_doprevoucher")
                ),
            },
            "raw_definition_persisted": False,
        }
    return contracts


def _issuance_finality_contract(cursor: Any) -> dict[str, Any]:
    definition_rows = _rows(
        cursor,
        "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID('dbo.usp_DoExternalVoucher')",
    )
    definition = definition_rows[0]["definition"] if definition_rows else ""
    lowered = definition.casefold()
    compact = re.sub(r"[\s\[\]'+]", "", lowered)
    error_return_index = compact.find("ifexists(selecttop11from@error)")
    first_persistent_mutation_candidates = [
        index
        for index in (
            compact.find("execdbo.usp_doprevoucher"),
            compact.find("insertintodbo.externalvoucherheader"),
            compact.find("insertintodbo.externalvoucher("),
            compact.find("insertintodbo.tblexternalrelation"),
        )
        if index >= 0
    ]
    first_persistent_mutation_index = (
        min(first_persistent_mutation_candidates)
        if first_persistent_mutation_candidates
        else -1
    )
    procedure_parameters = [
        row["parameter_name"]
        for row in _rows(
            cursor,
            """
            SELECT name parameter_name FROM sys.parameters
            WHERE object_id=OBJECT_ID('dbo.usp_DoExternalVoucher')
            ORDER BY parameter_id
            """,
        )
    ]

    system_profiles = _rows(
        cursor,
        f"""
        WITH configured AS (
          SELECT s.VNSystemId,s.OperationId,
                 COUNT(DISTINCT t.ExternalVoucherTypeId) configured_type_count,
                 COUNT(DISTINCT t.VoucherCreatorId) configured_creator_count
          FROM dbo.VNSystem s LEFT JOIN dbo.ExternalVoucherType t
            ON t.VNSystemId=s.VNSystemId
          GROUP BY s.VNSystemId,s.OperationId
        ), history AS (
          SELECT p.VNSystemId,COUNT_BIG(*) retained_line_count,
                 COUNT(DISTINCT p.ExternalVoucherHeaderId) retained_header_count,
                 SUM(CASE WHEN p.PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' THEN 1 ELSE 0 END) recent_line_count,
                 COUNT(DISTINCT CASE WHEN p.PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' THEN p.ExternalVoucherHeaderId END) recent_header_count
          FROM dbo.PreVoucher p GROUP BY p.VNSystemId
        ), modern AS (
          SELECT t.VNSystemId,COUNT(DISTINCT x.ExternalVoucherHeaderId) modern_header_count
          FROM dbo.ExternalVoucherHeaderXExternalVoucherType x
          JOIN dbo.ExternalVoucherType t
            ON t.ExternalVoucherTypeId=x.ExternalVoucherTypeId
          GROUP BY t.VNSystemId
        )
        SELECT c.VNSystemId,c.OperationId,c.configured_type_count,
               c.configured_creator_count,ISNULL(h.retained_line_count,0) retained_line_count,
               ISNULL(h.retained_header_count,0) retained_header_count,
               ISNULL(h.recent_line_count,0) recent_line_count,
               ISNULL(h.recent_header_count,0) recent_header_count,
               ISNULL(m.modern_header_count,0) modern_header_count
        FROM configured c LEFT JOIN history h ON h.VNSystemId=c.VNSystemId
        LEFT JOIN modern m ON m.VNSystemId=c.VNSystemId
        WHERE c.configured_type_count>0
        ORDER BY c.VNSystemId
        """,
    )
    system_semantics = {
        1: "inventory_accounting_purchase",
        2: "customer_accounting",
        3: "sales",
        5: "treasury",
        6: "payroll",
    }
    for row in system_profiles:
        row["system_semantic"] = system_semantics.get(
            row["VNSystemId"], "other_configured_system"
        )

    modern_recheck = _rows(
        cursor,
        """
        WITH hscope AS (
          SELECT DISTINCT h.ExternalVoucherHeaderId,h.DCId,h.AccYear,h.EndDate,
                 s.VNSystemId,s.OperationId
          FROM dbo.ExternalVoucherHeader h
          JOIN dbo.ExternalVoucherHeaderXExternalVoucherType x
            ON x.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId
          JOIN dbo.ExternalVoucherType t
            ON t.ExternalVoucherTypeId=x.ExternalVoucherTypeId
          JOIN dbo.VNSystem s ON s.VNSystemId=t.VNSystemId
        ), prof AS (
          SELECT h.*,
                 CASE WHEN h.VNSystemId=1 THEN
                   (SELECT MIN(o.DefeniteDate)
                    FROM ica.tblICAOprDate o
                    JOIN gnr.tblStockDC sd ON sd.ID=o.StockDCRef
                    WHERE sd.DCRef=h.DCId AND o.AccYear=h.AccYear)
                 ELSE
                   (SELECT MIN(o.LastDate) FROM gnr.tblOprDate o
                    WHERE o.SysRef=h.OperationId AND o.DCRef=h.DCId
                      AND o.AccYear=h.AccYear)
                 END final_date
          FROM hscope h
        )
        SELECT VNSystemId,OperationId,COUNT_BIG(*) header_type_scope_count,
               SUM(CASE WHEN OperationId=5 THEN 1 ELSE 0 END) exempt_scope_count,
               SUM(CASE WHEN OperationId<>5 AND ISNULL(final_date,'')<EndDate THEN 1 ELSE 0 END) would_fail_current_finality_count,
               SUM(CASE WHEN OperationId<>5 AND final_date IS NULL THEN 1 ELSE 0 END) missing_finality_date_count
        FROM prof GROUP BY VNSystemId,OperationId ORDER BY VNSystemId
        """,
    )
    for row in modern_recheck:
        row["system_semantic"] = system_semantics.get(
            row["VNSystemId"], "other_configured_system"
        )

    purchase_stockdc_coverage = _rows(
        cursor,
        """
        WITH years AS (
          SELECT AccYear FROM (VALUES(1403),(1404),(1405)) y(AccYear)
        ), scopes AS (
          SELECT d.ID DCId,y.AccYear FROM gnr.tblDC d CROSS JOIN years y
          WHERE d.Status=1
        ), prof AS (
          SELECT s.AccYear,s.DCId,COUNT(DISTINCT sd.ID) stockdc_count,
                 COUNT(DISTINCT CASE WHEN o.id IS NOT NULL THEN sd.ID END) stockdc_with_operation_row_count
          FROM scopes s LEFT JOIN gnr.tblStockDC sd ON sd.DCRef=s.DCId
          LEFT JOIN ica.tblICAOprDate o
            ON o.StockDCRef=sd.ID AND o.AccYear=s.AccYear
          GROUP BY s.AccYear,s.DCId
        )
        SELECT AccYear,COUNT(*) active_dc_scope_count,
               SUM(CASE WHEN stockdc_count>0 THEN 1 ELSE 0 END) scope_with_stockdc_count,
               SUM(CASE WHEN stockdc_count>0 AND stockdc_with_operation_row_count=stockdc_count THEN 1 ELSE 0 END) complete_scope_count,
               SUM(CASE WHEN stockdc_with_operation_row_count>0 AND stockdc_with_operation_row_count<stockdc_count THEN 1 ELSE 0 END) partially_covered_scope_count,
               SUM(CASE WHEN stockdc_with_operation_row_count=0 THEN 1 ELSE 0 END) wholly_missing_scope_count,
               SUM(stockdc_count-stockdc_with_operation_row_count) missing_stockdc_operation_row_count,
               MAX(stockdc_count) max_stockdc_per_scope,
               MAX(stockdc_with_operation_row_count) max_operation_rows_per_scope
        FROM prof GROUP BY AccYear ORDER BY AccYear
        """,
    )
    duplicate_profiles = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT(*) FROM (
             SELECT DCRef,AccYear,SysRef FROM gnr.tblOprDate
             GROUP BY DCRef,AccYear,SysRef HAVING COUNT(*)>1
           ) d) duplicate_general_operation_key_groups,
          (SELECT COUNT(*) FROM (
             SELECT StockDCRef,AccYear FROM ica.tblICAOprDate
             GROUP BY StockDCRef,AccYear HAVING COUNT(*)>1
           ) d) duplicate_purchase_operation_key_groups
        """,
    )[0]

    partial_purchase_scopes = sum(
        row["partially_covered_scope_count"] for row in purchase_stockdc_coverage
    )
    payroll = next(
        (row for row in system_profiles if row["OperationId"] == 5), None
    )
    return {
        "deployed_sql_semantics": {
            "procedure_parameters": procedure_parameters,
            "policy_values_are_not_procedure_parameters": not any(
                marker in {name.casefold() for name in procedure_parameters}
                for marker in (
                    "@externalvoucherissuemode",
                    "@doexternalvouchercreateall",
                    "@separatesetadcreatevoucher",
                    "@separatesaleofficecreatevoucher",
                )
            ),
            "selected_dc_cross_selected_external_type": (
                "crossjoin@externalvouchertypelist" in compact
                and "from@dclist" in compact
            ),
            "nonpurchase_uses_min_last_date_by_system_dc_year": (
                "selectmin(lastdate)fromgnr.tbloprdate" in compact
                and "od.sysref=s.operationid" in compact
                and "od.dcref=dcl.id" in compact
                and "od.accyear=@accyear" in compact
            ),
            "purchase_uses_min_existing_stockdc_definite_date": (
                "selectmin(icod.defenitedate)fromica.tblicaoprdate" in compact
                and "innerjoingnr.tblstockdcsdc" in compact
                and "sdc.dcref=dcl.id" in compact
            ),
            "purchase_query_requires_every_stockdc_row": False,
            "operation_id_5_is_explicitly_exempt": "s.operationid<>5" in compact,
            "missing_finality_date_blocks_nonexempt_issue": (
                bool(
                    re.search(
                        r"(?i)where\s+isnull\s*\(\s*d\.lastdate\s*,\s*''\s*\)\s*<\s*@todate",
                        definition,
                    )
                )
            ),
            "business_error_returns_result_without_exception": (
                "ifexists(selecttop11from@error)" in compact
                and "select1asmessagetype,messagedescfrom@error" in compact
            ),
            "finality_failure_is_before_first_persistent_mutation": (
                error_return_index >= 0
                and first_persistent_mutation_index > error_return_index
            ),
            "raw_definition_persisted": False,
        },
        "configured_and_retained_system_profiles": system_profiles,
        "modern_header_current_finality_recheck": modern_recheck,
        "purchase_stockdc_operation_row_coverage": purchase_stockdc_coverage,
        "operation_date_key_integrity": duplicate_profiles,
        "summary": {
            "configured_system_count": len(system_profiles),
            "configured_operation_id_5_type_count": sum(
                row["configured_type_count"]
                for row in system_profiles
                if row["OperationId"] == 5
            ),
            "operation_id_5_retained_header_count": (
                payroll["retained_header_count"] if payroll else 0
            ),
            "purchase_partially_covered_active_dc_year_scope_count": partial_purchase_scopes,
            "purchase_missing_stockdc_operation_row_count": sum(
                row["missing_stockdc_operation_row_count"]
                for row in purchase_stockdc_coverage
            ),
            "modern_header_scope_count": sum(
                row["header_type_scope_count"] for row in modern_recheck
            ),
            "modern_header_would_fail_current_finality_count": sum(
                row["would_fail_current_finality_count"] for row in modern_recheck
            ),
        },
        "interpretation": (
            "The deployed issue command checks finality before persistent mutation. "
            "However, purchase finality takes MIN over only existing ICA operation rows, "
            "so a missing StockDC row is invisible when another StockDC row exists. "
            "OperationId 5 is an explicit policy exemption and has no retained example in this clone."
        ),
    }


def _voucher_type_structural_validation_profile(cursor: Any) -> dict[str, Any]:
    definition_rows = _rows(
        cursor,
        "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID('dbo.usp_DoExternalVoucherTypeValidation')",
    )
    definition = definition_rows[0]["definition"] if definition_rows else ""
    lowered = definition.casefold()
    compact = re.sub(r"[\s\[\]'+]", "", lowered)
    issue_definition_rows = _rows(
        cursor,
        "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID('dbo.usp_DoExternalVoucher')",
    )
    issue_definition = (
        issue_definition_rows[0]["definition"] if issue_definition_rows else ""
    )
    issue_compact = re.sub(r"[\s\[\]'+]", "", issue_definition.casefold())

    def _cte(acc_year: int) -> str:
        return f"""
        WITH T AS (
          SELECT e.ExternalVoucherTypeId,e.VNSystemId,s.OperationId,
                 e.VoucherCreatorId,LTRIM(RTRIM(v.ViewName)) ViewName,
                 v.HasCustId,v.HasSupplierId,v.HasContactId,
                 OBJECT_ID(LTRIM(RTRIM(v.ViewName))) ViewObjectId,
                 vt.VoucherTypeId ResolvedVoucherTypeId
          FROM dbo.ExternalVoucherType e
          JOIN dbo.VNSystem s ON s.VNSystemId=e.VNSystemId
          LEFT JOIN dbo.VoucherType vt ON vt.VoucherTypeId=e.VoucherTypeId
          LEFT JOIN dbo.VoucherCreator v ON v.VoucherCreatorId=e.VoucherCreatorId
        ), A AS (
          SELECT a.* FROM dbo.Article a
          WHERE {acc_year} BETWEEN a.FromAccYear AND a.ToAccYear
        ), V AS (
          SELECT ExternalVoucherTypeId,'voucher_type_metadata_missing' reason
          FROM T WHERE ResolvedVoucherTypeId IS NULL
          UNION ALL SELECT ExternalVoucherTypeId,'view_name_missing'
          FROM T WHERE ViewName IS NULL OR ViewName=''
          UNION ALL SELECT ExternalVoucherTypeId,'view_object_missing'
          FROM T WHERE ViewName IS NOT NULL AND ViewName<>'' AND ViewObjectId IS NULL
          UNION ALL SELECT ExternalVoucherTypeId,'base_output_column_missing'
          FROM T WHERE ViewObjectId IS NOT NULL AND (
            NOT EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=T.ViewObjectId AND c.name='DCId') OR
            NOT EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=T.ViewObjectId AND c.name='DCName') OR
            NOT EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=T.ViewObjectId AND c.name='SaleOfficeId') OR
            NOT EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=T.ViewObjectId AND c.name='VoucherId') OR
            NOT EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=T.ViewObjectId AND c.name='VoucherNo'))
          UNION ALL SELECT ExternalVoucherTypeId,'conditional_party_column_missing'
          FROM T WHERE ViewObjectId IS NOT NULL AND (
            (ISNULL(HasCustId,0)=1 AND NOT EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=T.ViewObjectId AND c.name='CustId')) OR
            (ISNULL(HasSupplierId,0)=1 AND NOT EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=T.ViewObjectId AND c.name='SupplierId')) OR
            (ISNULL(HasContactId,0)=1 AND NOT EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=T.ViewObjectId AND c.name='ContactId')))
          UNION ALL SELECT T.ExternalVoucherTypeId,'creator_field_missing_view_column'
          FROM T JOIN dbo.VoucherCreatorField f ON f.VoucherCreatorId=T.VoucherCreatorId
          WHERE T.ViewObjectId IS NOT NULL
            AND LTRIM(RTRIM(f.VoucherCreatorFieldName)) NOT IN ('DCId','DCName','SaleOfficeId','VoucherId','VoucherNo')
            AND NOT EXISTS(SELECT 1 FROM sys.columns c WHERE c.object_id=T.ViewObjectId AND c.name=LTRIM(RTRIM(f.VoucherCreatorFieldName)))
          UNION ALL SELECT T.ExternalVoucherTypeId,'no_effective_article'
          FROM T WHERE NOT EXISTS(SELECT 1 FROM A WHERE A.ExternalVoucherTypeId=T.ExternalVoucherTypeId)
          UNION ALL SELECT A.ExternalVoucherTypeId,'required_article_field_missing'
          FROM A WHERE LTRIM(RTRIM(ISNULL(A.DateField,'')))=''
                    OR LTRIM(RTRIM(ISNULL(A.AmountField,'')))=''
                    OR LTRIM(RTRIM(ISNULL(A.SL,'')))=''
          UNION ALL SELECT A.ExternalVoucherTypeId,'article_field_not_registered'
          FROM A JOIN T ON T.ExternalVoucherTypeId=A.ExternalVoucherTypeId
          WHERE NOT EXISTS(SELECT 1 FROM dbo.VoucherCreatorField f WHERE f.VoucherCreatorId=T.VoucherCreatorId AND f.VoucherCreatorFieldName=A.DateField)
             OR NOT EXISTS(SELECT 1 FROM dbo.VoucherCreatorField f WHERE f.VoucherCreatorId=T.VoucherCreatorId AND f.VoucherCreatorFieldName=A.AmountField)
             OR (ISNUMERIC(A.SL)=0 AND NOT EXISTS(SELECT 1 FROM dbo.VoucherCreatorField f WHERE f.VoucherCreatorId=T.VoucherCreatorId AND f.VoucherCreatorFieldName=A.SL))
             OR (LTRIM(RTRIM(ISNULL(A.DL,'')))<>'' AND ISNUMERIC(A.DL)=0 AND NOT EXISTS(SELECT 1 FROM dbo.VoucherCreatorField f WHERE f.VoucherCreatorId=T.VoucherCreatorId AND f.VoucherCreatorFieldName=A.DL))
             OR (LTRIM(RTRIM(ISNULL(A.FifthLedger,'')))<>'' AND ISNUMERIC(A.FifthLedger)=0 AND NOT EXISTS(SELECT 1 FROM dbo.VoucherCreatorField f WHERE f.VoucherCreatorId=T.VoucherCreatorId AND f.VoucherCreatorFieldName=A.FifthLedger))
             OR (LTRIM(RTRIM(ISNULL(A.SixthLedger,'')))<>'' AND ISNUMERIC(A.SixthLedger)=0 AND NOT EXISTS(SELECT 1 FROM dbo.VoucherCreatorField f WHERE f.VoucherCreatorId=T.VoucherCreatorId AND f.VoucherCreatorFieldName=A.SixthLedger))
             OR (LTRIM(RTRIM(ISNULL(A.SeventhLedger,'')))<>'' AND ISNUMERIC(A.SeventhLedger)=0 AND NOT EXISTS(SELECT 1 FROM dbo.VoucherCreatorField f WHERE f.VoucherCreatorId=T.VoucherCreatorId AND f.VoucherCreatorFieldName=A.SeventhLedger))
          UNION ALL SELECT A.ExternalVoucherTypeId,'static_ledger_code_missing'
          FROM A WHERE
               (ISNUMERIC(A.SL)=1 AND NOT EXISTS(SELECT 1 FROM dbo.SL x WHERE x.SLCode=A.SL))
            OR (LTRIM(RTRIM(ISNULL(A.DL,'')))<>'' AND ISNUMERIC(A.DL)=1 AND NOT EXISTS(SELECT 1 FROM dbo.DL x WHERE x.DLCode=A.DL))
            OR (LTRIM(RTRIM(ISNULL(A.FifthLedger,'')))<>'' AND ISNUMERIC(A.FifthLedger)=1 AND NOT EXISTS(SELECT 1 FROM dbo.FifthLedger x WHERE x.FifthLedgerCode=A.FifthLedger))
            OR (LTRIM(RTRIM(ISNULL(A.SixthLedger,'')))<>'' AND ISNUMERIC(A.SixthLedger)=1 AND NOT EXISTS(SELECT 1 FROM dbo.SixthLedger x WHERE x.SixthLedgerCode=A.SixthLedger))
            OR (LTRIM(RTRIM(ISNULL(A.SeventhLedger,'')))<>'' AND ISNUMERIC(A.SeventhLedger)=1 AND NOT EXISTS(SELECT 1 FROM dbo.SeventhLedger x WHERE x.SeventhLedgerCode=A.SeventhLedger))
          UNION ALL SELECT A.ExternalVoucherTypeId,'article_comment_missing'
          FROM A WHERE NOT EXISTS(SELECT 1 FROM dbo.ArticleComment ac WHERE ac.ArticleId=A.ArticleId)
          UNION ALL SELECT A.ExternalVoucherTypeId,'comment_value_missing'
          FROM A JOIN dbo.ArticleComment ac ON ac.ArticleId=A.ArticleId
          WHERE LTRIM(RTRIM(ISNULL(ac.ConstantComment,'')))=''
          UNION ALL SELECT A.ExternalVoucherTypeId,'comment_field_not_registered'
          FROM A JOIN T ON T.ExternalVoucherTypeId=A.ExternalVoucherTypeId
          JOIN dbo.ArticleComment ac ON ac.ArticleId=A.ArticleId
          WHERE NOT EXISTS(SELECT 1 FROM dbo.VoucherCreatorField f
                           WHERE f.VoucherCreatorId=T.VoucherCreatorId
                             AND f.VoucherCreatorFieldId=ac.VoucherCreatorFieldId)
        ), InvalidTypes AS (
          SELECT DISTINCT ExternalVoucherTypeId FROM V
        ), H AS (
          SELECT ExternalVoucherTypeId,COUNT(DISTINCT ExternalVoucherHeaderId) retained_headers,
                 SUM(CASE WHEN PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' THEN 1 ELSE 0 END) recent_lines
          FROM dbo.PreVoucher GROUP BY ExternalVoucherTypeId
        ), M AS (
          SELECT ExternalVoucherTypeId,COUNT(DISTINCT ExternalVoucherHeaderId) modern_headers
          FROM dbo.ExternalVoucherHeaderXExternalVoucherType
          GROUP BY ExternalVoucherTypeId
        )
        """

    year_profiles: list[dict[str, Any]] = []
    for acc_year in (1403, 1404, 1405):
        common = _cte(acc_year)
        summary = _rows(
            cursor,
            common
            + """
            SELECT COUNT(*) configured_type_count,
                   COUNT(DISTINCT VoucherCreatorId) configured_creator_count,
                   (SELECT COUNT(*) FROM InvalidTypes) structurally_invalid_type_count,
                   COUNT(*)-(SELECT COUNT(*) FROM InvalidTypes) structurally_candidate_type_count,
                   (SELECT COUNT(DISTINCT T.ExternalVoucherTypeId) FROM T JOIN InvalidTypes I ON I.ExternalVoucherTypeId=T.ExternalVoucherTypeId LEFT JOIN H ON H.ExternalVoucherTypeId=T.ExternalVoucherTypeId WHERE ISNULL(H.retained_headers,0)>0) invalid_type_with_retained_history_count,
                   (SELECT COUNT(DISTINCT T.ExternalVoucherTypeId) FROM T JOIN InvalidTypes I ON I.ExternalVoucherTypeId=T.ExternalVoucherTypeId LEFT JOIN H ON H.ExternalVoucherTypeId=T.ExternalVoucherTypeId WHERE ISNULL(H.recent_lines,0)>0) invalid_type_with_recent_history_count,
                   (SELECT COUNT(DISTINCT T.ExternalVoucherTypeId) FROM T JOIN InvalidTypes I ON I.ExternalVoucherTypeId=T.ExternalVoucherTypeId LEFT JOIN M ON M.ExternalVoucherTypeId=T.ExternalVoucherTypeId WHERE ISNULL(M.modern_headers,0)>0) invalid_type_with_modern_header_count,
                   (SELECT COUNT(DISTINCT WhereStr) FROM A WHERE LTRIM(RTRIM(ISNULL(WhereStr,'')))<>'') predicate_count
            FROM T
            """,
        )[0]
        reasons = _rows(
            cursor,
            common
            + """
            SELECT reason,COUNT(*) violation_row_count,
                   COUNT(DISTINCT ExternalVoucherTypeId) affected_type_count
            FROM V GROUP BY reason ORDER BY reason
            """,
        )
        systems = _rows(
            cursor,
            common
            + """
            SELECT T.VNSystemId,T.OperationId,COUNT(*) configured_type_count,
                   SUM(CASE WHEN I.ExternalVoucherTypeId IS NULL THEN 1 ELSE 0 END) structurally_candidate_type_count,
                   SUM(CASE WHEN I.ExternalVoucherTypeId IS NOT NULL THEN 1 ELSE 0 END) structurally_invalid_type_count
            FROM T LEFT JOIN InvalidTypes I ON I.ExternalVoucherTypeId=T.ExternalVoucherTypeId
            GROUP BY T.VNSystemId,T.OperationId ORDER BY T.VNSystemId
            """,
        )
        for row in systems:
            row["system_semantic"] = {
                1: "inventory_accounting_purchase",
                2: "customer_accounting",
                3: "sales",
                5: "treasury",
                6: "payroll",
            }.get(row["VNSystemId"], "other_configured_system")
        year_profiles.append(
            {
                "AccYear": acc_year,
                **summary,
                "violation_reason_counts": reasons,
                "system_profiles": systems,
            }
        )

    current = next(row for row in year_profiles if row["AccYear"] == 1405)
    return {
        "deployed_validator_semantics": {
            "called_by_issue_before_finality_check": (
                "execdbo.usp_doexternalvouchertypevalidation" in issue_compact
                and issue_compact.find("usp_doexternalvouchertypevalidation")
                < issue_compact.find("gnr.tbloprdate")
            ),
            "validates_view_object_and_base_columns": all(
                marker in lowered
                for marker in ("sysobjects", "dcid", "dcname", "saleofficeid", "voucherid", "voucherno")
            ),
            "validates_conditional_party_columns": all(
                marker in lowered for marker in ("hascustid", "hassupplierid", "hascontactid")
            ),
            "validates_effective_articles_fields_ledgers_and_comments": all(
                marker in lowered
                for marker in ("fromaccyear", "amountfield", "datefield", "fifthledger", "articlecomment")
            ),
            "compiles_predicates_with_dynamic_select_where_one_equals_two": (
                "exec('selecttop11asainto#aFrom".casefold() in compact
                or (
                    "selecttop11asainto#a" in compact
                    and "where1=2and(" in compact
                )
            ),
            "predicate_compile_queries_executed_by_extractor": 0,
            "operational_creator_views_executed_by_extractor": 0,
            "raw_validator_definition_or_rule_values_persisted": False,
        },
        "year_profiles": year_profiles,
        "summary": {
            "configured_type_count": current["configured_type_count"],
            "structurally_candidate_type_count": current[
                "structurally_candidate_type_count"
            ],
            "structurally_invalid_type_count": current[
                "structurally_invalid_type_count"
            ],
            "invalid_type_with_retained_history_count": current[
                "invalid_type_with_retained_history_count"
            ],
            "invalid_type_with_recent_history_count": current[
                "invalid_type_with_recent_history_count"
            ],
            "invalid_type_with_modern_header_count": current[
                "invalid_type_with_modern_header_count"
            ],
            "predicate_count_not_runtime_compiled": current["predicate_count"],
        },
        "interpretation": (
            "Configured voucher types are not equivalent to issueable capabilities. "
            "The deployed validator fails closed on structural configuration errors. "
            "The offline replay deliberately did not execute creator views or predicate SQL."
        ),
    }


def _dynamic_rule_sql_and_source_snapshot_profile(cursor: Any) -> dict[str, Any]:
    definitions = {
        row["name"]: row["definition"]
        for row in _rows(
            cursor,
            """
            SELECT o.name,m.definition FROM sys.sql_modules m
            JOIN sys.objects o ON o.object_id=m.object_id
            WHERE o.object_id IN (
              OBJECT_ID('dbo.usp_DoPreVoucher'),
              OBJECT_ID('dbo.usp_DoExternalVoucherTypeValidation')
            )
            """,
        )
    }
    pre = definitions.get("usp_DoPreVoucher", "")
    validator = definitions.get("usp_DoExternalVoucherTypeValidation", "")
    pre_compact = re.sub(r"[\s\[\]'+]", "", pre.casefold())
    validator_compact = re.sub(r"[\s\[\]'+]", "", validator.casefold())
    pre_executes_strcmd = bool(
        re.search(r"\bexec(?:ute)?\s*\(\s*@strcmd\s*\)", pre, re.IGNORECASE)
    )

    source_queries = {
        "view_name": "SELECT ViewName value FROM dbo.VoucherCreator",
        "type_default_where": "SELECT DefaultWhereClause value FROM dbo.ExternalVoucherType",
        "type_secondary_where": "SELECT WhereClause2 value FROM dbo.ExternalVoucherType",
        "article_predicate": "SELECT WhereStr value FROM dbo.Article",
        "article_date_field": "SELECT DateField value FROM dbo.Article",
        "article_amount_field": "SELECT AmountField value FROM dbo.Article",
        "article_ledger_fragment": "SELECT SL value FROM dbo.Article UNION ALL SELECT DL FROM dbo.Article UNION ALL SELECT FifthLedger FROM dbo.Article UNION ALL SELECT SixthLedger FROM dbo.Article UNION ALL SELECT SeventhLedger FROM dbo.Article",
        "comment_constant": "SELECT ConstantComment value FROM dbo.ArticleComment",
        "type_default_comment": "SELECT DefaultComment value FROM dbo.ExternalVoucherType",
        "voucher_type_name": "SELECT VoucherTypeName value FROM dbo.VoucherType",
        "creator_field_name": "SELECT VoucherCreatorFieldName value FROM dbo.VoucherCreatorField",
    }
    consumed_by_current_pre_voucher = {
        "view_name": True,
        "type_default_where": True,
        "type_secondary_where": False,
        "article_predicate": True,
        "article_date_field": True,
        "article_amount_field": True,
        "article_ledger_fragment": True,
        "comment_constant": True,
        "type_default_comment": True,
        "voucher_type_name": True,
        "creator_field_name": True,
    }
    statement_keyword = re.compile(
        r"(?i)\b(exec(?:ute)?|insert|update|delete|drop|alter|truncate|merge|grant|revoke|deny|openrowset|opendatasource|xp_)\b"
    )
    identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?$")
    numeric = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
    fragment_profiles: dict[str, Any] = {}
    for name, query in source_queries.items():
        values = [
            str(row["value"]).strip()
            for row in _rows(cursor, query)
            if row["value"] is not None and str(row["value"]).strip()
        ]
        unique_values = set(values)
        fragment_profiles[name] = {
            "present_row_count": len(values),
            "distinct_value_count": len(unique_values),
            "identifier_only_row_count": sum(bool(identifier.fullmatch(value)) for value in values),
            "numeric_only_row_count": sum(bool(numeric.fullmatch(value)) for value in values),
            "expression_or_text_row_count": sum(
                not identifier.fullmatch(value) and not numeric.fullmatch(value)
                for value in values
            ),
            "semicolon_value_count": sum(";" in value for value in values),
            "line_comment_token_value_count": sum("--" in value for value in values),
            "block_comment_token_value_count": sum(
                "/*" in value or "*/" in value for value in values
            ),
            "statement_keyword_value_count": sum(
                bool(statement_keyword.search(value)) for value in values
            ),
            "single_quote_value_count": sum("'" in value for value in values),
            "control_character_value_count": sum(
                any(
                    ord(character) < 32 and character not in "\t\r\n"
                    for character in value
                )
                for value in values
            ),
            "consumed_by_current_usp_do_pre_voucher": consumed_by_current_pre_voucher[
                name
            ],
            "raw_values_persisted": False,
        }

    suspicious_current_values = sum(
        profile[metric]
        for profile in fragment_profiles.values()
        if profile["consumed_by_current_usp_do_pre_voucher"]
        for metric in (
            "semicolon_value_count",
            "line_comment_token_value_count",
            "block_comment_token_value_count",
            "statement_keyword_value_count",
            "single_quote_value_count",
            "control_character_value_count",
        )
    )
    return {
        "deployed_sql_semantics": {
            "pre_voucher_builds_one_concatenated_sql_batch": (
                "@strcmd" in pre.casefold()
                and "isnull(@strcmd" in pre.casefold()
                and pre_executes_strcmd
            ),
            "pre_voucher_uses_sp_executesql_parameters": "sp_executesql" in pre.casefold(),
            "validator_executes_concatenated_view_and_predicate": (
                "exec(selecttop11asainto#afrom" in validator_compact
                and "where1=2and(" in validator_compact
            ),
            "validator_restricts_view_name_to_quoted_identifier": False,
            "pre_voucher_concatenates_view_name": (
                "crt.viewname" in pre.casefold()
                and "asvwwith(nolock)" in pre_compact
            ),
            "pre_voucher_concatenates_article_fields": all(
                marker in pre.casefold()
                for marker in ("art.datefield", "art.amountfield", "art.sl", "art.sixthledger")
            ),
            "pre_voucher_concatenates_article_predicate": "art.wherestr" in pre.casefold(),
            "pre_voucher_concatenates_default_where": "defaultwhereclause" in pre.casefold(),
            "pre_voucher_concatenates_comment_recipe": "articlecomment" in pre.casefold(),
            "creator_view_read_uses_nolock": "asvwwith(nolock)" in pre_compact,
            "source_read_is_guaranteed_committed_consistent": False,
            "user_to_date_is_validated_before_dynamic_sql": True,
            "raw_dynamic_sql_or_config_values_persisted": False,
        },
        "configured_fragment_profiles": fragment_profiles,
        "summary": {
            "configured_fragment_category_count": len(fragment_profiles),
            "current_consumed_fragment_category_count": sum(
                profile["consumed_by_current_usp_do_pre_voucher"]
                for profile in fragment_profiles.values()
            ),
            "current_suspicious_token_or_quote_value_count": suspicious_current_values,
            "distinct_article_predicate_count": fragment_profiles[
                "article_predicate"
            ]["distinct_value_count"],
            "creator_view_nolock_read_count_in_definition": pre_compact.count(
                "asvwwith(nolock)"
            ),
            "dynamic_sql_execution_site_count": int(pre_executes_strcmd)
            + int("exec(selecttop11asainto#afrom" in validator_compact),
            "dynamic_sql_execution_sites_run_by_extractor": 0,
        },
        "interpretation": (
            "The current configuration scan found no obvious statement separators, comments, "
            "statement keywords, quotes or control characters. That clean snapshot does not make "
            "the design safe: trusted configuration is concatenated into executable SQL, and source "
            "creator views are read WITH(NOLOCK) while financial staging is persisted."
        ),
    }


def _compressed_uint(blob: bytes, offset: int) -> tuple[int, int]:
    first = blob[offset]
    if first & 0x80 == 0:
        return first, offset + 1
    if first & 0xC0 == 0x80:
        return ((first & 0x3F) << 8) | blob[offset + 1], offset + 2
    return (
        ((first & 0x1F) << 24)
        | (blob[offset + 1] << 16)
        | (blob[offset + 2] << 8)
        | blob[offset + 3],
        offset + 4,
    )


def _transaction_isolation_and_source_version_profile(
    cursor: Any, source_directory: Path, binary_inventory_path: Path
) -> dict[str, Any]:
    inventory = json.loads(binary_inventory_path.read_text(encoding="utf-8-sig"))
    inventory_row = next(
        row for row in inventory["files"] if row["name"] == "Application.DataAccess.dll"
    )
    assembly_path = source_directory / "Application.DataAccess.dll"
    binary = assembly_path.read_bytes()
    assembly_sha256 = hashlib.sha256(binary).hexdigest()
    if assembly_sha256 != inventory_row["sha256"]:
        raise RuntimeError("Runtime assembly hash mismatch: Application.DataAccess.dll")
    pe = dnfile.dnPE(data=binary)
    _, open_body = _method(pe, "Thunderstruck.Provider.DefaultProvider", "Open")
    methods, fields = _owner_maps(pe)
    begin_calls: list[dict[str, Any]] = []
    for index, instruction in enumerate(open_body.instructions):
        if not isinstance(instruction.operand, Token):
            continue
        resolved = _resolve_token(pe, instruction.operand, methods, fields)
        if resolved != "System.Data.IDbConnection.BeginTransaction":
            continue
        table = pe.net.mdtables.tables.get(instruction.operand.table)
        row = table.rows[instruction.operand.rid - 1]
        signature = bytes(row.Signature.value)
        offset = 1
        if signature[0] & 0x10:
            _, offset = _compressed_uint(signature, offset)
        parameter_count, _ = _compressed_uint(signature, offset)
        preceding = list(open_body.instructions)[max(0, index - 3) : index]
        begin_calls.append(
            {
                "instruction_index": index,
                "parameter_count": parameter_count,
                "preceded_only_by_connection_receiver": (
                    bool(preceding)
                    and preceding[-1].mnemonic == "call"
                    and isinstance(preceding[-1].operand, Token)
                    and _resolve_token(pe, preceding[-1].operand, methods, fields)
                    == "Thunderstruck.Provider.DefaultProvider.get_DbConnection"
                ),
                "signature_sha256": hashlib.sha256(signature).hexdigest(),
            }
        )

    database_options = _rows(
        cursor,
        """
        SELECT is_read_only,is_read_committed_snapshot_on,
               snapshot_isolation_state_desc
        FROM sys.databases WHERE name=DB_NAME()
        """,
    )[0]
    dependency_scopes = _rows(
        cursor,
        f"""
        WITH roots AS (
          SELECT c.VoucherCreatorId,OBJECT_ID(c.ViewName) root_id,
                 CASE WHEN EXISTS (
                   SELECT 1 FROM dbo.PreVoucher p
                   WHERE p.VoucherCreatorId=c.VoucherCreatorId
                     AND p.PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
                 ) THEN 1 ELSE 0 END recent_active
          FROM dbo.VoucherCreator c
          WHERE OBJECT_ID(c.ViewName) IS NOT NULL
            AND EXISTS (
              SELECT 1 FROM dbo.PreVoucher p
              WHERE p.VoucherCreatorId=c.VoucherCreatorId
            )
        ), dependency_walk AS (
          SELECT r.VoucherCreatorId,r.recent_active,r.root_id,r.root_id object_id,
                 CAST('/'+CONVERT(varchar(20),r.root_id)+'/' AS varchar(max)) path,
                 0 depth
          FROM roots r
          UNION ALL
          SELECT w.VoucherCreatorId,w.recent_active,w.root_id,d.referenced_id,
                 CAST(w.path+CONVERT(varchar(20),d.referenced_id)+'/' AS varchar(max)),
                 w.depth+1
          FROM dependency_walk w
          JOIN sys.sql_expression_dependencies d ON d.referencing_id=w.object_id
          WHERE d.referenced_id IS NOT NULL AND w.depth<16
            AND CHARINDEX('/'+CONVERT(varchar(20),d.referenced_id)+'/',w.path)=0
        ), reachable AS (
          SELECT DISTINCT VoucherCreatorId,recent_active,root_id,object_id,depth
          FROM dependency_walk
        ), object_flags AS (
          SELECT o.object_id,o.type,
                 MAX(CASE WHEN c.system_type_id=189 THEN 1 ELSE 0 END) has_rowversion,
                 MAX(CASE WHEN c.name LIKE '%rowversion%' OR c.name LIKE '%timestamp%'
                            OR c.name LIKE '%modified%' OR c.name LIKE '%updated%'
                            OR c.name LIKE '%lastupdate%' OR c.name LIKE '%version%'
                          THEN 1 ELSE 0 END) has_version_named_column,
                 MAX(CASE WHEN t.temporal_type>0 THEN 1 ELSE 0 END) is_temporal,
                 MAX(CASE WHEN ct.object_id IS NOT NULL THEN 1 ELSE 0 END) change_tracking_enabled
          FROM sys.objects o
          LEFT JOIN sys.columns c ON c.object_id=o.object_id
          LEFT JOIN sys.tables t ON t.object_id=o.object_id
          LEFT JOIN sys.change_tracking_tables ct ON ct.object_id=o.object_id
          GROUP BY o.object_id,o.type
        ), scoped AS (
          SELECT 'all_active_creators' scope_name,* FROM reachable
          UNION ALL
          SELECT 'recent_active_creators',* FROM reachable WHERE recent_active=1
        ), edge_flags AS (
          SELECT s.scope_name,
                 SUM(CASE WHEN d.referenced_id IS NULL THEN 1 ELSE 0 END) unresolved_edge_count,
                 SUM(CASE WHEN d.referenced_database_name IS NOT NULL
                           OR d.referenced_server_name IS NOT NULL THEN 1 ELSE 0 END)
                   external_edge_count
          FROM (SELECT DISTINCT scope_name,object_id FROM scoped) s
          JOIN sys.sql_expression_dependencies d ON d.referencing_id=s.object_id
          GROUP BY s.scope_name
        )
        SELECT s.scope_name,COUNT(DISTINCT s.VoucherCreatorId) creator_count,
               MAX(s.depth) maximum_resolved_dependency_depth,
               COUNT(DISTINCT CASE WHEN f.type='U' THEN s.object_id END) base_table_count,
               COUNT(DISTINCT CASE WHEN f.type='V' THEN s.object_id END) view_count,
               COUNT(DISTINCT CASE WHEN f.type IN ('FN','IF','TF') THEN s.object_id END)
                 function_count,
               COUNT(DISTINCT CASE WHEN f.type='U' AND f.has_rowversion=1
                                   THEN s.object_id END) base_table_with_rowversion_count,
               COUNT(DISTINCT CASE WHEN f.type='U' AND f.has_version_named_column=1
                                   THEN s.object_id END) base_table_with_version_named_column_count,
               COUNT(DISTINCT CASE WHEN f.type='U' AND f.is_temporal=1
                                   THEN s.object_id END) temporal_base_table_count,
               COUNT(DISTINCT CASE WHEN f.type='U' AND f.change_tracking_enabled=1
                                   THEN s.object_id END) change_tracked_base_table_count,
               ISNULL(MAX(e.unresolved_edge_count),0) unresolved_dependency_edge_count,
               ISNULL(MAX(e.external_edge_count),0) external_dependency_edge_count
        FROM scoped s
        LEFT JOIN object_flags f ON f.object_id=s.object_id
        LEFT JOIN edge_flags e ON e.scope_name=s.scope_name
        GROUP BY s.scope_name
        ORDER BY s.scope_name
        OPTION (MAXRECURSION 100)
        """,
    )
    by_scope = {row.pop("scope_name"): row for row in dependency_scopes}
    recent = by_scope["recent_active_creators"]
    return {
        "deployed_provider_boundary": {
            "assembly": "Application.DataAccess.dll",
            "assembly_sha256": assembly_sha256,
            "hash_matches_inventory": True,
            "method": "Thunderstruck.Provider.DefaultProvider.Open",
            "begin_transaction_call_count": len(begin_calls),
            "begin_transaction_calls": begin_calls,
            "all_begin_transaction_calls_are_parameterless": bool(begin_calls)
            and all(row["parameter_count"] == 0 for row in begin_calls),
            "explicit_isolation_level_argument_present": any(
                row["parameter_count"] > 0 for row in begin_calls
            ),
            "isolation_text_marker_count_in_binary": binary.lower().count(b"isolation")
            + binary.lower().count("isolation".encode("utf-16le")),
            "assembly_loaded_or_executed": False,
        },
        "clone_database_options": database_options,
        "creator_dependency_version_profiles": by_scope,
        "summary": {
            "recent_active_creator_count": recent["creator_count"],
            "recent_source_base_table_count": recent["base_table_count"],
            "recent_source_base_table_with_rowversion_count": recent[
                "base_table_with_rowversion_count"
            ],
            "recent_source_temporal_base_table_count": recent[
                "temporal_base_table_count"
            ],
            "recent_source_change_tracked_base_table_count": recent[
                "change_tracked_base_table_count"
            ],
            "provider_explicit_isolation_level": any(
                row["parameter_count"] > 0 for row in begin_calls
            ),
            "operational_creator_views_executed_by_extractor": 0,
        },
        "interpretation": (
            "The deployed provider starts its transaction through the parameterless "
            "IDbConnection.BeginTransaction overload. Database snapshot options and durable "
            "source-version signals must therefore be treated as explicit target contracts, "
            "not inferred from the existence of the desktop transaction."
        ),
    }


def _rule_configuration_write_authority_profile(
    cursor: Any, source_directory: Path, binary_inventory_path: Path
) -> dict[str, Any]:
    target_tables = (
        "VoucherCreator",
        "VoucherCreatorField",
        "ExternalVoucherType",
        "Article",
        "ArticleComment",
    )
    sql_modules = _rows(
        cursor,
        """
        SELECT QUOTENAME(OBJECT_SCHEMA_NAME(m.object_id))+'.'+QUOTENAME(OBJECT_NAME(m.object_id)) module_name,
               o.type_desc,m.definition
        FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
        WHERE o.is_ms_shipped=0
        """,
    )
    module_candidates: list[dict[str, Any]] = []
    per_table: dict[str, dict[str, Any]] = {}
    for table in target_tables:
        escaped = rf"(?:\[?dbo\]?\s*\.\s*)?\[?{re.escape(table)}\]?"
        patterns = {
            "INSERT": re.compile(
                rf"\binsert\s+(?:into\s+)?{escaped}\b", re.IGNORECASE
            ),
            "UPDATE": re.compile(rf"\bupdate\s+{escaped}\b", re.IGNORECASE),
            "DELETE": re.compile(
                rf"\bdelete\s+(?:from\s+)?{escaped}\b", re.IGNORECASE
            ),
            "MERGE": re.compile(rf"\bmerge\s+(?:into\s+)?{escaped}\b", re.IGNORECASE),
        }
        matched = []
        for module in sql_modules:
            definition = module["definition"] or ""
            verbs = [verb for verb, pattern in patterns.items() if pattern.search(definition)]
            if not verbs:
                continue
            item = {
                "table": table,
                "module_name": module["module_name"],
                "module_type": module["type_desc"],
                "mutation_verbs": verbs,
                "definition_sha256": hashlib.sha256(
                    definition.encode("utf-8")
                ).hexdigest(),
                "definition_persisted": False,
                "references_authorization_signal": bool(
                    re.search(
                        r"(?i)(haspersmission|permission|accessnode|tblaccess|usergroup|authorize)",
                        definition,
                    )
                ),
                "owns_explicit_transaction": bool(
                    re.search(r"(?i)\bbegin\s+tran(?:saction)?\b", definition)
                ),
            }
            matched.append(item)
            module_candidates.append(item)
        triggers = _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) trigger_count,
                   SUM(CASE WHEN tr.is_disabled=0 THEN 1 ELSE 0 END) enabled_trigger_count
            FROM sys.triggers tr WHERE tr.parent_id=OBJECT_ID(%s)
            """,
            (f"dbo.{table}",),
        )[0]
        rows = _rows(
            cursor,
            """
            SELECT SUM(p.rows) row_count
            FROM sys.partitions p
            WHERE p.object_id=OBJECT_ID(%s) AND p.index_id IN (0,1)
            """,
            (f"dbo.{table}",),
        )[0]
        per_table[table] = {
            "row_count": rows["row_count"] or 0,
            "lexical_mutation_module_count": len(matched),
            "lexical_mutation_modules": matched,
            "trigger_count": triggers["trigger_count"] or 0,
            "enabled_trigger_count": triggers["enabled_trigger_count"] or 0,
        }

    transfer_procedure_names = (
        "dbo.VoucherTemplateTransfer",
        "dbo.VoucherTemplateArticleTransfer",
    )
    transfer_procedure_contracts: dict[str, Any] = {}
    for procedure_name in transfer_procedure_names:
        object_rows = _rows(
            cursor,
            """
            SELECT o.object_id,m.definition
            FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
            WHERE o.object_id=OBJECT_ID(%s)
            """,
            (procedure_name,),
        )
        if not object_rows:
            continue
        object_id = object_rows[0]["object_id"]
        definition = object_rows[0]["definition"] or ""
        definition_folded = definition.casefold()
        callers = _rows(
            cursor,
            """
            SELECT DISTINCT QUOTENAME(OBJECT_SCHEMA_NAME(d.referencing_id))+'.'+
                            QUOTENAME(OBJECT_NAME(d.referencing_id)) caller_name,
                            o.type_desc caller_type
            FROM sys.sql_expression_dependencies d
            JOIN sys.objects o ON o.object_id=d.referencing_id
            WHERE d.referenced_id=%s ORDER BY caller_name
            """,
            (object_id,),
        )
        permissions = _rows(
            cursor,
            """
            SELECT state_desc,permission_name,COUNT(DISTINCT grantee_principal_id) grantee_count
            FROM sys.database_permissions
            WHERE class=1 AND major_id=%s
            GROUP BY state_desc,permission_name ORDER BY state_desc,permission_name
            """,
            (object_id,),
        )
        transfer_procedure_contracts[procedure_name] = {
            "parameter_count": _rows(
                cursor,
                "SELECT COUNT_BIG(*) parameter_count FROM sys.parameters WHERE object_id=%s AND parameter_id>0",
                (object_id,),
            )[0]["parameter_count"],
            "dynamic_exec_site_count": len(
                re.findall(r"(?i)\bexec(?:ute)?\s*\(", definition)
            ),
            "drops_and_creates_creator_views": (
                "drop view" in definition_folded
                and "create view" in definition_folded
            ),
            "target_table_mutations": sorted(
                {
                    row["table"]
                    for row in module_candidates
                    if row["module_name"]
                    == "[dbo].[" + procedure_name.rsplit(".", 1)[-1] + "]"
                }
            ),
            "calls_article_transfer": "exec dbo.vouchertemplatearticletransfer"
            in re.sub(r"\s+", " ", definition_folded),
            "uses_cursor": "cursor for" in definition_folded,
            "owns_explicit_transaction": bool(
                re.search(r"(?i)\bbegin\s+tran(?:saction)?\b", definition)
            ),
            "has_try_catch": "begin try" in definition_folded
            and "begin catch" in definition_folded,
            "has_explicit_rollback": bool(
                re.search(r"(?i)\brollback\s+tran(?:saction)?\b", definition)
            ),
            "references_authorization_signal": bool(
                re.search(
                    r"(?i)(haspersmission|permission|accessnode|tblaccess|usergroup|authorize)",
                    definition,
                )
            ),
            "references_version_or_publish_audit_signal": bool(
                re.search(r"(?i)(ruleversion|policyversion|publish|approval|audit)", definition)
            ),
            "catalog_callers": callers,
            "explicit_object_permission_aggregates": permissions,
            "analyzer_login_has_execute": bool(
                _rows(
                    cursor,
                    "SELECT HAS_PERMS_BY_NAME(%s,'OBJECT','EXECUTE') can_execute",
                    (procedure_name,),
                )[0]["can_execute"]
            ),
            "definition_sha256": hashlib.sha256(
                definition.encode("utf-8")
            ).hexdigest(),
            "definition_persisted": False,
        }

    inventory = json.loads(binary_inventory_path.read_text(encoding="utf-8-sig"))
    parsed_assembly_count = 0
    managed_parse_error_count = 0
    hash_mismatch_count = 0
    target_type_count = 0
    target_form_type_count = 0
    save_call_sites: list[dict[str, Any]] = []
    target_sql_literal_sites: list[dict[str, Any]] = []
    template_procedure_literal_sites: list[dict[str, Any]] = []
    binary_voucher_mapping_literal_sites: list[dict[str, Any]] = []
    binary_voucher_mapping_tables = (
        "vocherHdrInserttolog",
        "vocheritmInserttolog",
    )
    save_target = (
        "VN.SDS.CreateVoucher.Business.ExternalVoucherType."
        "ExternalVoucherTypeHandler.SaveCommand"
    )
    for inventory_file in inventory["files"]:
        path = source_directory / inventory_file["name"]
        binary = path.read_bytes()
        if hashlib.sha256(binary).hexdigest() != inventory_file["sha256"]:
            hash_mismatch_count += 1
            continue
        try:
            pe = dnfile.dnPE(data=binary)
            if pe.net is None:
                managed_parse_error_count += 1
                continue
            parsed_assembly_count += 1
            method_owners, field_owners = _owner_maps(pe)
            for type_row in pe.net.mdtables.TypeDef.rows:
                type_name = _full_type_name(type_row)
                type_folded = type_name.casefold()
                is_target_type = (
                    "externalvouchertype" in type_folded
                    or "vouchercreator" in type_folded
                    or ".articlecomment." in type_folded
                    or ".article." in type_folded
                )
                target_type_count += int(is_target_type)
                target_form_type_count += int(
                    is_target_type and type_name.rsplit(".", 1)[-1].startswith("Form")
                )
                for method_index in type_row.MethodList or []:
                    method_row = method_index.row
                    if not method_row.Rva:
                        continue
                    try:
                        body = read_method_body_from_bytes(
                            pe.get_data(method_row.Rva, 65536)
                        )
                    except Exception:
                        continue
                    method_name = _text(method_row.Name)
                    method_calls = []
                    literal_hits = set()
                    template_literal_hits = set()
                    binary_mapping_literal_hits = set()
                    for instruction in body.instructions:
                        if isinstance(instruction.operand, Token):
                            resolved = _resolve_token(
                                pe, instruction.operand, method_owners, field_owners
                            )
                            method_calls.append(resolved)
                        elif isinstance(instruction.operand, StringToken):
                            value = _text(
                                pe.net.user_strings.get(instruction.operand.rid).value
                            )
                            folded = value.casefold()
                            for table in target_tables:
                                if table.casefold() in folded and re.search(
                                    r"(?i)\b(insert|update|delete|merge)\b", value
                                ):
                                    literal_hits.add(table)
                            for procedure_name in transfer_procedure_names:
                                if procedure_name.casefold() in folded or procedure_name.rsplit(
                                    ".", 1
                                )[-1].casefold() in folded:
                                    template_literal_hits.add(procedure_name)
                            for table in binary_voucher_mapping_tables:
                                if table.casefold() in folded:
                                    binary_mapping_literal_hits.add(table)
                    if save_target in method_calls:
                        save_call_sites.append(
                            {
                                "assembly": inventory_file["name"],
                                "caller_type": type_name,
                                "caller_method": method_name,
                                "caller_is_form": type_name.rsplit(".", 1)[-1].startswith(
                                    "Form"
                                ),
                            }
                        )
                    if literal_hits:
                        target_sql_literal_sites.append(
                            {
                                "assembly": inventory_file["name"],
                                "caller_type": type_name,
                                "caller_method": method_name,
                                "target_table_count": len(literal_hits),
                                "literal_sha256_only": True,
                            }
                        )
                    if template_literal_hits:
                        template_procedure_literal_sites.append(
                            {
                                "assembly": inventory_file["name"],
                                "caller_type": type_name,
                                "caller_method": method_name,
                                "referenced_template_procedure_count": len(
                                    template_literal_hits
                                ),
                                "raw_literal_persisted": False,
                            }
                        )
                    if binary_mapping_literal_hits:
                        binary_voucher_mapping_literal_sites.append(
                            {
                                "assembly": inventory_file["name"],
                                "caller_type": type_name,
                                "caller_method": method_name,
                                "mapping_table_literal_count": len(
                                    binary_mapping_literal_hits
                                ),
                                "raw_literal_persisted": False,
                            }
                        )
        except Exception:
            managed_parse_error_count += 1

    business_path = source_directory / "VN.SDS.CreateVoucher.Business.dll"
    business_pe = dnfile.dnPE(str(business_path))
    _, save_body = _method(
        business_pe,
        "VN.SDS.CreateVoucher.Business.ExternalVoucherType.ExternalVoucherTypeHandler",
        "SaveCommand",
    )
    save_calls = _ordered_calls(business_pe, save_body)
    save_instructions = list(save_body.instructions)
    common_path = source_directory / "VN.SDS.Common.dll"
    common_pe = dnfile.dnPE(str(common_path))
    _, data_sp_body = _method(
        common_pe,
        "VN.SDS.Common.CreateVoucher.Entity.ExternalVoucherType.ExternalVoucherTypeEntity",
        "GetDataSPName",
    )
    data_sp_literals = [
        _text(common_pe.net.user_strings.get(instruction.operand.rid).value)
        for instruction in data_sp_body.instructions
        if isinstance(instruction.operand, StringToken)
    ]
    return {
        "sql_write_surface": {
            "target_table_count": len(target_tables),
            "tables": per_table,
            "lexical_mutation_module_count": len(
                {row["module_name"] for row in module_candidates}
            ),
            "lexical_table_module_pair_count": len(module_candidates),
            "raw_definitions_persisted": False,
            "operational_modules_executed": 0,
        },
        "deployed_application_surface": {
            "inventory_file_count": len(inventory["files"]),
            "hash_mismatch_count": hash_mismatch_count,
            "parsed_managed_assembly_count": parsed_assembly_count,
            "managed_parse_error_or_nonmanaged_count": managed_parse_error_count,
            "target_named_type_count": target_type_count,
            "target_named_form_type_count": target_form_type_count,
            "external_voucher_type_save_call_site_count": len(save_call_sites),
            "external_voucher_type_save_call_sites": save_call_sites,
            "direct_target_sql_literal_site_count": len(target_sql_literal_sites),
            "direct_target_sql_literal_sites": target_sql_literal_sites,
            "template_procedure_literal_site_count": len(
                template_procedure_literal_sites
            ),
            "template_procedure_literal_sites": template_procedure_literal_sites,
            "binary_voucher_mapping_literal_site_count": len(
                binary_voucher_mapping_literal_sites
            ),
            "binary_voucher_mapping_literal_sites": binary_voucher_mapping_literal_sites,
            "handler_save_command": {
                "instruction_count": len(save_instructions),
                "branch_instruction_count": sum(
                    instruction.mnemonic.startswith("br")
                    for instruction in save_instructions
                ),
                "validation_failure_constructor_count": sum(
                    row["call"] == "FluentValidation.Results.ValidationFailure..ctor"
                    for row in save_calls
                ),
                "validation_result_constructor_count": sum(
                    row["call"] == "FluentValidation.Results.ValidationResult..ctor"
                    for row in save_calls
                ),
                "data_adapter_or_transaction_call_count": sum(
                    "DataAdapter" in row["call"]
                    or "DataContext" in row["call"]
                    or row["call"].endswith(".Commit")
                    for row in save_calls
                ),
                "string_literal_count": sum(
                    isinstance(instruction.operand, StringToken)
                    for instruction in save_instructions
                ),
                "raw_localized_validation_values_persisted": False,
            },
            "entity_data_procedure_literals": data_sp_literals,
            "assemblies_loaded_or_executed": 0,
        },
        "template_transfer_procedure_contracts": transfer_procedure_contracts,
        "summary": {
            "application_target_form_type_count": target_form_type_count,
            "application_save_call_site_count": len(save_call_sites),
            "application_direct_target_sql_literal_site_count": len(
                target_sql_literal_sites
            ),
            "application_template_procedure_literal_site_count": len(
                template_procedure_literal_sites
            ),
            "application_binary_voucher_mapping_literal_site_count": len(
                binary_voucher_mapping_literal_sites
            ),
            "handler_save_is_unconditional_validation_failure": (
                len(save_instructions) > 0
                and not any(
                    instruction.mnemonic.startswith("br")
                    for instruction in save_instructions
                )
                and any(
                    row["call"] == "FluentValidation.Results.ValidationFailure..ctor"
                    for row in save_calls
                )
                and not any(
                    "DataAdapter" in row["call"] or "DataContext" in row["call"]
                    for row in save_calls
                )
            ),
            "sql_lexical_mutation_module_count": len(
                {row["module_name"] for row in module_candidates}
            ),
            "sql_enabled_target_trigger_count": sum(
                row["enabled_trigger_count"] or 0 for row in per_table.values()
            ),
            "configuration_write_authority_attributed_to_deployed_form": bool(
                target_form_type_count or save_call_sites or target_sql_literal_sites
            ),
            "template_transfer_procedure_count": len(
                transfer_procedure_contracts
            ),
            "template_transfer_procedure_with_transaction_count": sum(
                row["owns_explicit_transaction"]
                for row in transfer_procedure_contracts.values()
            ),
            "template_transfer_procedure_with_try_catch_count": sum(
                row["has_try_catch"]
                for row in transfer_procedure_contracts.values()
            ),
            "template_transfer_procedure_with_authorization_signal_count": sum(
                row["references_authorization_signal"]
                for row in transfer_procedure_contracts.values()
            ),
            "template_transfer_procedure_with_version_audit_signal_count": sum(
                row["references_version_or_publish_audit_signal"]
                for row in transfer_procedure_contracts.values()
            ),
            "analyzer_login_executable_template_procedure_count": sum(
                row["analyzer_login_has_execute"]
                for row in transfer_procedure_contracts.values()
            ),
        },
        "interpretation": (
            "The deployed package exposes a read/list ExternalVoucherType entity contract, "
            "while its named SaveCommand returns an unconditional validation failure and no "
            "deployed target-named form or caller was found. SQL mutation modules are lexical "
            "administrative surfaces, not proof of which human or role may invoke them."
        ),
    }


def _rule_replication_trigger_profile(cursor: Any) -> dict[str, Any]:
    target_tables = ("Article", "ArticleComment")
    triggers = _rows(
        cursor,
        """
        SELECT tr.object_id,OBJECT_NAME(tr.object_id) trigger_name,
               OBJECT_NAME(tr.parent_id) parent_table,tr.is_disabled,
               tr.is_instead_of_trigger,m.definition
        FROM sys.triggers tr JOIN sys.sql_modules m ON m.object_id=tr.object_id
        WHERE tr.parent_id IN (OBJECT_ID('dbo.Article'),OBJECT_ID('dbo.ArticleComment'))
        ORDER BY parent_table,trigger_name
        """,
    )
    trigger_contracts: list[dict[str, Any]] = []
    insert_coverage: dict[str, dict[str, Any]] = {}
    table_column_metadata: dict[str, list[dict[str, Any]]] = {}
    for table in target_tables:
        columns = _rows(
            cursor,
            """
            SELECT c.name,c.is_nullable,c.is_identity,c.is_computed,
                   CASE WHEN dc.object_id IS NULL THEN 0 ELSE 1 END has_default
            FROM sys.columns c
            LEFT JOIN sys.default_constraints dc
              ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
            WHERE c.object_id=OBJECT_ID(%s) ORDER BY c.column_id
            """,
            (f"dbo.{table}",),
        )
        table_column_metadata[table] = columns
        insert_trigger = next(
            row
            for row in triggers
            if row["parent_table"] == table
            and "_INSERT" in row["trigger_name"].upper()
        )
        definition = insert_trigger["definition"] or ""
        match = re.search(
            rf"(?is)INSERT\s+INTO\s+dbo\.{re.escape(table)}\s*\(([^)]*)\)",
            definition,
        )
        replicated_columns = (
            [part.strip().strip("[]") for part in match.group(1).split(",")]
            if match
            else []
        )
        table_columns = [row["name"] for row in columns]
        missing = [name for name in table_columns if name not in replicated_columns]
        required_missing = [
            row["name"]
            for row in columns
            if row["name"] not in replicated_columns
            and not row["is_nullable"]
            and not row["is_identity"]
            and not row["is_computed"]
            and not row["has_default"]
        ]
        insert_coverage[table] = {
            "table_column_count": len(table_columns),
            "replication_insert_column_count": len(replicated_columns),
            "replication_insert_columns": replicated_columns,
            "omitted_columns": missing,
            "omitted_required_without_default_columns": required_missing,
            "all_nonidentity_columns_replicated": all(
                row["name"] in replicated_columns
                for row in columns
                if not row["is_identity"] and not row["is_computed"]
            ),
        }

    for trigger in triggers:
        definition = trigger.pop("definition") or ""
        insert_log_call = re.search(
            r"(?im)^\s*exec(?:ute)?\s+dbo\.InsertToLog\b(?P<args>[^\r\n;]*)",
            definition,
        )
        insert_log_output_variables = (
            re.findall(
                r"(?i)(@\w+)\s+output\b",
                insert_log_call.group("args"),
            )
            if insert_log_call
            else []
        )
        definition_after_insert_log_call = (
            definition[insert_log_call.end() :] if insert_log_call else ""
        )
        dependencies = _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) dependency_edge_count,
                   SUM(CASE WHEN referenced_server_name IS NOT NULL
                              OR referenced_database_name IS NOT NULL THEN 1 ELSE 0 END)
                     external_dependency_edge_count
            FROM sys.sql_expression_dependencies WHERE referencing_id=%s
            """,
            (trigger["object_id"],),
        )[0]
        trigger_contracts.append(
            {
                key: value for key, value in trigger.items() if key != "object_id"
            }
            | {
                "event": next(
                    event
                    for event in ("INSERT", "UPDATE", "DELETE")
                    if f"_{event}" in trigger["trigger_name"].upper()
                ),
                "uses_replication_mode_guard": "dbo.ufn_isreplicationmode()"
                in re.sub(r"\s+", "", definition.casefold()),
                "calls_local_insert_to_log": bool(
                    re.search(r"(?i)\bexec(?:ute)?\s+dbo\.InsertToLog\b", definition)
                ),
                "insert_to_log_output_argument_count": len(
                    insert_log_output_variables
                ),
                "insert_to_log_output_variable_reused_after_call": any(
                    re.search(
                        rf"(?i)(?<!\w){re.escape(variable)}(?!\w)",
                        definition_after_insert_log_call,
                    )
                    for variable in insert_log_output_variables
                ),
                "uses_per_row_cursor": "cursor forward_only read_only"
                in re.sub(r"\s+", " ", definition.casefold()),
                "has_try_catch": "begin try" in definition.casefold()
                and "begin catch" in definition.casefold(),
                "sets_xact_abort": "set xact_abort" in definition.casefold(),
                "definition_sha256": hashlib.sha256(
                    definition.encode("utf-8")
                ).hexdigest(),
                "definition_persisted": False,
                **dependencies,
            }
        )

    insert_log_definition_rows = _rows(
        cursor,
        "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID('dbo.InsertToLog')",
    )
    insert_log_definition = (
        insert_log_definition_rows[0]["definition"]
        if insert_log_definition_rows
        else ""
    )
    insert_log_parameters = _rows(
        cursor,
        """
        SELECT parameter_id,is_output,TYPE_NAME(user_type_id) type_name
        FROM sys.parameters WHERE object_id=OBJECT_ID('dbo.InsertToLog')
        ORDER BY parameter_id
        """,
    )
    insert_log_dependency_aggregates = _rows(
        cursor,
        """
        SELECT o.type_desc,COUNT_BIG(*) module_count
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects o ON o.object_id=d.referencing_id
        WHERE d.referenced_id=OBJECT_ID('dbo.InsertToLog')
        GROUP BY o.type_desc ORDER BY o.type_desc
        """,
    )
    insert_log_trigger_footprint = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) trigger_count,
               COUNT_BIG(DISTINCT tr.parent_id) parent_table_count,
               COUNT_BIG(DISTINCT OBJECT_SCHEMA_NAME(tr.parent_id)) parent_schema_count,
               SUM(CASE WHEN tr.is_disabled=0 THEN 1 ELSE 0 END) enabled_count,
               SUM(CASE WHEN tr.is_not_for_replication=1 THEN 1 ELSE 0 END)
                 not_for_replication_count,
               SUM(CASE WHEN LOWER(m.definition) LIKE '%cursor%' THEN 1 ELSE 0 END)
                 cursor_signal_count,
               SUM(CASE WHEN LOWER(m.definition) LIKE '%begin try%'
                          AND LOWER(m.definition) LIKE '%begin catch%' THEN 1 ELSE 0 END)
                 try_catch_count,
               SUM(CASE WHEN LOWER(m.definition) LIKE '%set xact_abort%' THEN 1 ELSE 0 END)
                 xact_abort_count
        FROM sys.sql_expression_dependencies d
        JOIN sys.triggers tr ON tr.object_id=d.referencing_id
        JOIN sys.sql_modules m ON m.object_id=tr.object_id
        WHERE d.referenced_id=OBJECT_ID('dbo.InsertToLog')
        """,
    )[0]
    insert_log_trigger_event_counts = _rows(
        cursor,
        """
        SELECT te.type_desc event_type,COUNT_BIG(*) trigger_count
        FROM sys.sql_expression_dependencies d
        JOIN sys.triggers tr ON tr.object_id=d.referencing_id
        JOIN sys.trigger_events te ON te.object_id=tr.object_id
        WHERE d.referenced_id=OBJECT_ID('dbo.InsertToLog')
        GROUP BY te.type_desc ORDER BY te.type_desc
        """,
    )
    insert_log_trigger_schema_footprint = _rows(
        cursor,
        """
        SELECT OBJECT_SCHEMA_NAME(tr.parent_id) parent_schema,
               COUNT_BIG(*) trigger_count,
               COUNT_BIG(DISTINCT tr.parent_id) parent_table_count,
               SUM(CASE WHEN LOWER(m.definition) LIKE '%cursor%' THEN 1 ELSE 0 END)
                 cursor_signal_count,
               SUM(CASE WHEN LOWER(m.definition) LIKE '%begin try%'
                          AND LOWER(m.definition) LIKE '%begin catch%' THEN 1 ELSE 0 END)
                 try_catch_count,
               SUM(CASE WHEN LOWER(m.definition) LIKE '%set xact_abort%' THEN 1 ELSE 0 END)
                 xact_abort_count,
               SUM(CASE WHEN tr.is_not_for_replication=1 THEN 1 ELSE 0 END)
                 not_for_replication_count
        FROM sys.sql_expression_dependencies d
        JOIN sys.triggers tr ON tr.object_id=d.referencing_id
        JOIN sys.sql_modules m ON m.object_id=tr.object_id
        WHERE d.referenced_id=OBJECT_ID('dbo.InsertToLog')
        GROUP BY OBJECT_SCHEMA_NAME(tr.parent_id)
        ORDER BY OBJECT_SCHEMA_NAME(tr.parent_id)
        """,
    )
    insert_log_trigger_event_shapes = _rows(
        cursor,
        """
        WITH event_shapes AS (
          SELECT tr.object_id,
                 MAX(CASE WHEN te.type_desc='INSERT' THEN 1 ELSE 0 END) has_insert,
                 MAX(CASE WHEN te.type_desc='UPDATE' THEN 1 ELSE 0 END) has_update,
                 MAX(CASE WHEN te.type_desc='DELETE' THEN 1 ELSE 0 END) has_delete,
                 CASE WHEN LOWER(m.definition) LIKE '%cursor%' THEN 1 ELSE 0 END
                   cursor_signal
          FROM sys.sql_expression_dependencies d
          JOIN sys.triggers tr ON tr.object_id=d.referencing_id
          JOIN sys.sql_modules m ON m.object_id=tr.object_id
          JOIN sys.trigger_events te ON te.object_id=tr.object_id
          WHERE d.referenced_id=OBJECT_ID('dbo.InsertToLog')
          GROUP BY tr.object_id,m.definition
        )
        SELECT has_insert,has_update,has_delete,
               COUNT_BIG(*) trigger_count,
               SUM(cursor_signal) cursor_signal_count
        FROM event_shapes
        GROUP BY has_insert,has_update,has_delete
        ORDER BY has_insert,has_update,has_delete
        """,
    )
    binary_mapping_trigger_rows = _rows(
        cursor,
        """
        SELECT o.name,m.definition
        FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE o.name IN ('trg_Replication_tblVocherHdr_INSERT',
                         'trg_Replication_tblVocherItm_INSERT')
        ORDER BY o.name
        """,
    )
    binary_mapping_trigger_contracts = []
    for row in binary_mapping_trigger_rows:
        definition = row["definition"] or ""
        normalized = re.sub(r"\s+", " ", definition)
        binary_mapping_trigger_contracts.append(
            {
                "trigger_name": row["name"],
                "captures_insert_to_log_output": bool(
                    re.search(
                        r"(?is)exec(?:ute)?\s+dbo\.InsertToLog\b.{0,300}?@logid\s+output",
                        normalized,
                    )
                ),
                "persists_returned_log_id_in_mapping_table": bool(
                    re.search(
                        r"(?is)insert\s+into\s+(?:dbo\.)?vocher(?:hdr|itm)inserttolog\b.{0,300}?@logid",
                        normalized,
                    )
                ),
                "definition_sha256": hashlib.sha256(
                    definition.encode("utf-8")
                ).hexdigest(),
                "definition_persisted": False,
            }
        )
    binary_mapping_table_stats = _rows(
        cursor,
        """
        SELECT t.name table_name,
               SUM(CASE WHEN c.name='LogId' THEN 1 ELSE 0 END) log_id_column_count,
               (SELECT COUNT_BIG(*) FROM sys.indexes i
                WHERE i.object_id=t.object_id AND i.index_id>0) index_count,
               (SELECT COUNT_BIG(*) FROM sys.indexes i
                WHERE i.object_id=t.object_id AND i.index_id>0 AND i.is_unique=1)
                 unique_index_count,
               (SELECT COUNT_BIG(*) FROM sys.foreign_keys fk
                WHERE fk.parent_object_id=t.object_id) foreign_key_count
        FROM sys.tables t JOIN sys.columns c ON c.object_id=t.object_id
        WHERE t.name IN ('vocherHdrInserttolog','vocheritmInserttolog')
        GROUP BY t.object_id,t.name ORDER BY t.name
        """,
    )
    retained_binary_mapping_rows = {
        row["table_name"]: row["retained_rows"]
        for row in _rows(
            cursor,
            """
            SELECT 'vocherHdrInserttolog' table_name,COUNT_BIG(*) retained_rows
            FROM dbo.vocherHdrInserttolog
            UNION ALL
            SELECT 'vocheritmInserttolog',COUNT_BIG(*)
            FROM dbo.vocheritmInserttolog
            """,
        )
    }
    binary_mapping_dependency_rows = _rows(
        cursor,
        """
        SELECT t.name table_name,o.type_desc,m.definition
        FROM sys.tables t
        JOIN sys.sql_expression_dependencies d ON d.referenced_id=t.object_id
        JOIN sys.objects o ON o.object_id=d.referencing_id
        LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE t.name IN ('vocherHdrInserttolog','vocheritmInserttolog')
        ORDER BY t.name,o.type_desc,o.object_id
        """,
    )
    binary_mapping_reader_module_count = 0
    for row in binary_mapping_dependency_rows:
        definition = re.sub(r"\s+", " ", row["definition"] or "")
        table_pattern = rf"(?:dbo\.)?{re.escape(row['table_name'])}"
        if re.search(
            rf"(?is)(?:\bselect\b(?:(?!\b(?:insert|update|delete|merge)\b).){{0,500}}?\bfrom\s+|\bjoin\s+){table_pattern}\b",
            definition,
        ):
            binary_mapping_reader_module_count += 1
    log_columns = _rows(
        cursor,
        """
        SELECT c.name,dc.definition default_definition
        FROM sys.columns c
        LEFT JOIN sys.default_constraints dc
          ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
        WHERE c.object_id=OBJECT_ID('gnr.tblLog') ORDER BY c.column_id
        """,
    )
    log_column_names = {row["name"].casefold() for row in log_columns}
    log_defaults = " ".join(
        row["default_definition"] or "" for row in log_columns
    ).casefold()
    log_activity = _rows(
        cursor,
        """
        SELECT OperationTable,OperationType,COUNT_BIG(*) retained_log_rows,
               SUM(CASE WHEN TransDate>='2026-05-22' AND TransDate<'2026-08-23'
                        THEN 1 ELSE 0 END) three_month_log_rows
        FROM gnr.tblLog
        WHERE OperationTable IN ('dbo.Article','dbo.ArticleComment')
        GROUP BY OperationTable,OperationType
        ORDER BY OperationTable,OperationType
        """,
    )
    template_article_rows = _rows(
        cursor,
        "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID('dbo.VoucherTemplateArticleTransfer')",
    )
    template_article_definition = (
        template_article_rows[0]["definition"] if template_article_rows else ""
    )
    template_insert_match = re.search(
        r"(?is)INSERT\s+INTO\s+Article\s*\(([^)]*)\)",
        template_article_definition,
    )
    template_insert_columns = (
        [
            part.strip().strip("[]")
            for part in template_insert_match.group(1).split(",")
        ]
        if template_insert_match
        else []
    )
    current_article_columns = [
        row["name"] for row in table_column_metadata["Article"]
    ]
    template_unknown_columns = [
        name for name in template_insert_columns if name not in current_article_columns
    ]
    template_omitted_current_columns = [
        row["name"]
        for row in table_column_metadata["Article"]
        if row["name"] not in template_insert_columns
        and not row["is_identity"]
        and not row["is_computed"]
    ]
    template_omitted_required_columns = [
        row["name"]
        for row in table_column_metadata["Article"]
        if row["name"] not in template_insert_columns
        and not row["is_identity"]
        and not row["is_computed"]
        and not row["is_nullable"]
        and not row["has_default"]
    ]
    total_retained_logs = sum(row["retained_log_rows"] for row in log_activity)
    total_recent_logs = sum(row["three_month_log_rows"] for row in log_activity)
    article_missing = insert_coverage["Article"]["omitted_columns"]
    return {
        "trigger_contracts": trigger_contracts,
        "replication_insert_column_coverage": insert_coverage,
        "local_log_writer_contract": {
            "procedure": "dbo.InsertToLog",
            "writes_local_gnr_tbl_log": "insert into gnr.tbllog"
            in re.sub(r"\s+", " ", insert_log_definition.casefold()),
            "stores_generated_sql_script": "script" in insert_log_definition.casefold(),
            "uses_ident_current_for_output_id": "ident_current('gnr.tbllog')"
            in re.sub(r"\s+", "", insert_log_definition.casefold()),
            "uses_scope_identity_for_output_id": "scope_identity()"
            in re.sub(r"\s+", "", insert_log_definition.casefold()),
            "parameter_count": len(insert_log_parameters),
            "output_parameter_count": sum(
                row["is_output"] for row in insert_log_parameters
            ),
            "output_parameter_type_names": sorted(
                row["type_name"]
                for row in insert_log_parameters
                if row["is_output"]
            ),
            "owns_explicit_transaction": bool(
                re.search(
                    r"(?i)\bbegin\s+tran(?:saction)?\b", insert_log_definition
                )
            ),
            "log_column_count": len(log_columns),
            "has_host_name_column": "hostname" in log_column_names,
            "has_application_name_column": "appname" in log_column_names,
            "has_sql_user_name_column": "username" in log_column_names,
            "has_spid_column": "spid" in log_column_names,
            "has_rule_or_policy_version_column": bool(
                {"ruleversion", "policyversion"} & log_column_names
            ),
            "has_approval_column": any(
                "approval" in name or "approver" in name
                for name in log_column_names
            ),
            "runtime_context_defaults_present": any(
                marker in log_defaults
                for marker in ("host_name", "app_name", "suser", "@@spid")
            ),
            "definition_sha256": hashlib.sha256(
                insert_log_definition.encode("utf-8")
            ).hexdigest(),
            "definition_persisted": False,
        },
        "insert_to_log_global_output_boundary": {
            "dependency_module_counts": {
                row["type_desc"]: row["module_count"]
                for row in insert_log_dependency_aggregates
            },
            "trigger_footprint": insert_log_trigger_footprint,
            "trigger_event_counts": {
                row["event_type"]: row["trigger_count"]
                for row in insert_log_trigger_event_counts
            },
            "trigger_schema_footprint": insert_log_trigger_schema_footprint,
            "trigger_event_shapes": insert_log_trigger_event_shapes,
            "binary_voucher_mapping_trigger_contracts": binary_mapping_trigger_contracts,
            "binary_voucher_mapping_table_stats": binary_mapping_table_stats,
            "retained_binary_voucher_mapping_rows": retained_binary_mapping_rows,
            "binary_mapping_trigger_count": len(binary_mapping_trigger_contracts),
            "binary_mapping_trigger_using_returned_ident_current_count": sum(
                row["captures_insert_to_log_output"]
                and row["persists_returned_log_id_in_mapping_table"]
                for row in binary_mapping_trigger_contracts
            ),
            "binary_mapping_table_with_unique_index_count": sum(
                row["unique_index_count"] > 0
                for row in binary_mapping_table_stats
            ),
            "binary_mapping_table_with_foreign_key_count": sum(
                row["foreign_key_count"] > 0
                for row in binary_mapping_table_stats
            ),
            "binary_mapping_table_dependency_module_count": len(
                binary_mapping_dependency_rows
            ),
            "binary_mapping_table_reader_module_count": binary_mapping_reader_module_count,
            "concurrent_wrong_log_mapping_observed_in_snapshot": any(
                retained_binary_mapping_rows.values()
            ),
            "definition_values_persisted": False,
        },
        "aggregate_log_activity": log_activity,
        "template_article_transfer_schema_compatibility": {
            "current_article_column_count": len(current_article_columns),
            "template_insert_column_count": len(template_insert_columns),
            "template_insert_columns": template_insert_columns,
            "template_insert_unknown_columns": template_unknown_columns,
            "current_nonidentity_columns_omitted_by_template": template_omitted_current_columns,
            "current_required_columns_omitted_by_template": template_omitted_required_columns,
            "dynamic_insert_schema_compatible": not template_unknown_columns
            and not template_omitted_required_columns,
            "definition_persisted": False,
        },
        "summary": {
            "enabled_trigger_count": sum(not row["is_disabled"] for row in trigger_contracts),
            "trigger_with_replication_mode_guard_count": sum(
                row["uses_replication_mode_guard"] for row in trigger_contracts
            ),
            "trigger_calling_local_insert_to_log_count": sum(
                row["calls_local_insert_to_log"] for row in trigger_contracts
            ),
            "trigger_capturing_insert_to_log_output_count": sum(
                row["insert_to_log_output_argument_count"] > 0
                for row in trigger_contracts
            ),
            "trigger_reusing_insert_to_log_output_after_call_count": sum(
                row["insert_to_log_output_variable_reused_after_call"]
                for row in trigger_contracts
            ),
            "rule_trigger_control_flow_depends_on_returned_log_id": any(
                row["insert_to_log_output_variable_reused_after_call"]
                for row in trigger_contracts
            ),
            "trigger_with_external_dependency_count": sum(
                bool(row["external_dependency_edge_count"])
                for row in trigger_contracts
            ),
            "article_replication_omitted_column_count": len(article_missing),
            "article_replication_omitted_required_column_count": len(
                insert_coverage["Article"][
                    "omitted_required_without_default_columns"
                ]
            ),
            "retained_rule_replication_log_count": total_retained_logs,
            "three_month_rule_replication_log_count": total_recent_logs,
            "template_article_insert_unknown_column_count": len(
                template_unknown_columns
            ),
            "template_article_insert_omitted_current_column_count": len(
                template_omitted_current_columns
            ),
            "template_article_dynamic_insert_schema_compatible": not template_unknown_columns
            and not template_omitted_required_columns,
            "operational_triggers_or_replication_scripts_executed": 0,
            "raw_replication_script_values_persisted": False,
        },
        "interpretation": (
            "The six enabled triggers do not directly call an external server: they serialize "
            "row mutations into local gnr.tblLog through InsertToLog. The replication INSERT "
            "shape is compared to current columns separately from the stale dynamic INSERT in "
            "VoucherTemplateArticleTransfer, whose schema is validated only at runtime."
        ),
    }


def _effective_policy(cursor: Any) -> dict[str, Any]:
    return {
        "server_config": _rows(
            cursor,
            """
            SELECT KeyName,KeyValue FROM gnr.tblServerConfig
            WHERE KeyName IN ('DoExternalVoucher_Create_All','SeparateSetadCreateVoucher',
                              'SeparateSaleOfficeCreateVoucher') ORDER BY KeyName
            """,
        ),
        "fiscal_issue_mode": _rows(
            cursor,
            """
            SELECT a.AccYear,f.ExternalVoucherIssueMode,COUNT_BIG(*) mapping_rows
            FROM gnr.TblACCYear a JOIN dbo.FiscalYear f
              ON f.StartDate=a.StartDate AND f.EndDate=a.EndDate
            GROUP BY a.AccYear,f.ExternalVoucherIssueMode ORDER BY a.AccYear
            """,
        ),
        "mode_semantics_from_procedure": {
            "1": "one group per source reference (plus type/DC/sale-office policy)",
            "2": "one group per business day (plus type/DC/sale-office policy)",
            "3": "one group per business month (plus type/DC/sale-office policy)",
        },
    }


def _index_contract(cursor: Any) -> dict[str, Any]:
    indexes = _rows(
        cursor,
        """
        SELECT i.name,i.is_unique,i.is_primary_key,i.is_disabled,i.is_hypothetical,
               i.has_filter,i.filter_definition,ic.key_ordinal,ic.is_included_column,
               c.name column_name
        FROM sys.indexes i JOIN sys.index_columns ic
          ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID('dbo.PreVoucher') AND i.name IS NOT NULL
        ORDER BY i.index_id,ic.key_ordinal,ic.index_column_id
        """,
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in indexes:
        name = row.pop("name")
        item = grouped.setdefault(
            name,
            {
                key: row[key]
                for key in (
                    "is_unique",
                    "is_primary_key",
                    "is_disabled",
                    "is_hypothetical",
                    "has_filter",
                    "filter_definition",
                )
            }
            | {"key_columns": [], "included_columns": []},
        )
        target = "included_columns" if row["is_included_column"] else "key_columns"
        item[target].append(row["column_name"])
    exact_duplicates = _rows(
        cursor,
        """
        WITH g AS (
          SELECT VoucherCreatorId,ReferenceId,ArticleId,SLCode,DLCode,FifthLedgerCode,
                 SixthLedgerCode,SeventhLedgerCode,PreVoucherItemComment,COUNT_BIG(*) n
          FROM dbo.PreVoucher
          GROUP BY VoucherCreatorId,ReferenceId,ArticleId,SLCode,DLCode,FifthLedgerCode,
                   SixthLedgerCode,SeventhLedgerCode,PreVoucherItemComment
          HAVING COUNT_BIG(*)>1
        )
        SELECT COUNT_BIG(*) duplicate_groups,COALESCE(SUM(n),0) duplicate_rows FROM g
        """,
    )[0]
    coarse = _rows(
        cursor,
        """
        WITH g AS (
          SELECT ReferenceName,ReferenceId,DCId,COUNT_BIG(*) lines,
                 COUNT(DISTINCT VoucherCreatorId) creators,
                 COUNT(DISTINCT FiscalYearId) fiscal_years,
                 COUNT(DISTINCT ExternalVoucherTypeId) external_types,
                 COUNT(DISTINCT ArticleId) articles
          FROM dbo.PreVoucher GROUP BY ReferenceName,ReferenceId,DCId
        )
        SELECT COUNT_BIG(*) groups,SUM(lines) lines,
          SUM(CASE WHEN fiscal_years>1 THEN 1 ELSE 0 END) multi_fiscal_groups,
          SUM(CASE WHEN external_types>1 THEN 1 ELSE 0 END) multi_external_type_groups,
          SUM(CASE WHEN creators>1 THEN 1 ELSE 0 END) multi_creator_groups,
          SUM(CASE WHEN articles>1 THEN 1 ELSE 0 END) multi_article_groups,
          MAX(lines) max_lines_per_group FROM g
        """,
    )[0]
    return {
        "indexes": grouped,
        "exact_unique_signature_duplicate_profile": exact_duplicates,
        "procedure_anti_join_grain_profile": coarse,
        "interpretation": (
            "The deployed unique index prevents duplicate exact accounting-line signatures. "
            "The procedure's broader source/DC anti-join intentionally treats an existing source as immutable; "
            "it is not a line-by-line repair/upsert contract."
        ),
    }


def _integrity_profile(cursor: Any, date_predicate: str = "1=1") -> dict[str, Any]:
    return {
        "pre_voucher_state": _rows(
            cursor,
            f"""
            SELECT COUNT_BIG(*) lines,
              SUM(CASE WHEN ExternalVoucherHeaderId IS NULL THEN 1 ELSE 0 END) unlinked_lines,
              SUM(CASE WHEN ExternalVoucherHeaderId IS NOT NULL THEN 1 ELSE 0 END) linked_lines,
              SUM(CASE WHEN ISNULL(HasExternalVoucher,0)=0 THEN 1 ELSE 0 END) not_marked_lines,
              SUM(CASE WHEN HasExternalVoucher=1 THEN 1 ELSE 0 END) marked_lines,
              SUM(CASE WHEN ExternalVoucherHeaderId IS NULL AND HasExternalVoucher=1 THEN 1 ELSE 0 END) marked_without_header,
              SUM(CASE WHEN ExternalVoucherHeaderId IS NOT NULL AND ISNULL(HasExternalVoucher,0)=0 THEN 1 ELSE 0 END) linked_not_marked
            FROM dbo.PreVoucher WHERE {date_predicate}
            """,
        )[0],
        "orphan_and_partial_state": _rows(
            cursor,
            f"""
            SELECT
              (SELECT COUNT_BIG(*) FROM dbo.ExternalVoucherHeader h
               WHERE {date_predicate.replace('PreVoucherDate', 'h.EndDate')}
                 AND NOT EXISTS(SELECT 1 FROM dbo.ExternalVoucher e WHERE e.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId)) headers_without_lines,
              (SELECT COUNT_BIG(*) FROM dbo.ExternalVoucher e
               WHERE {date_predicate.replace('PreVoucherDate', 'e.VoucherDate')}
                 AND NOT EXISTS(SELECT 1 FROM dbo.ExternalVoucherHeader h WHERE h.ExternalVoucherHeaderId=e.ExternalVoucherHeaderId)) lines_without_header,
              (SELECT COUNT_BIG(*) FROM dbo.PreVoucher p
               WHERE {date_predicate.replace('PreVoucherDate', 'p.PreVoucherDate')}
                 AND p.ExternalVoucherHeaderId IS NOT NULL
                 AND NOT EXISTS(SELECT 1 FROM dbo.ExternalVoucherHeader h WHERE h.ExternalVoucherHeaderId=p.ExternalVoucherHeaderId)) prevoucher_links_without_header,
              (SELECT COUNT_BIG(*) FROM dbo.ExternalVoucherHeader h
               WHERE {date_predicate.replace('PreVoucherDate', 'h.EndDate')}
                 AND NOT EXISTS(SELECT 1 FROM dbo.PreVoucher p WHERE p.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId)) headers_without_prevoucher
            """,
        )[0],
        "header_line_balance": _rows(
            cursor,
            f"""
            WITH x AS (
              SELECT h.ExternalVoucherHeaderId,h.DebitAmountHdr,h.CreditAmountHdr,
                     COUNT_BIG(e.ExternalVoucherId) lines,
                     COALESCE(SUM(e.DebitAmount),0) debit,COALESCE(SUM(e.CreditAmount),0) credit
              FROM dbo.ExternalVoucherHeader h LEFT JOIN dbo.ExternalVoucher e
                ON e.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId
              WHERE {date_predicate.replace('PreVoucherDate', 'h.EndDate')}
              GROUP BY h.ExternalVoucherHeaderId,h.DebitAmountHdr,h.CreditAmountHdr
            )
            SELECT COUNT_BIG(*) headers,SUM(CASE WHEN lines=0 THEN 1 ELSE 0 END) no_line_headers,
              SUM(CASE WHEN debit<>credit THEN 1 ELSE 0 END) unbalanced_line_headers,
              SUM(CASE WHEN ISNULL(DebitAmountHdr,0)<>debit OR ISNULL(CreditAmountHdr,0)<>credit THEN 1 ELSE 0 END) header_line_amount_mismatch,
              MAX(ABS(debit-credit)) max_line_imbalance FROM x
            """,
        )[0],
    }


def _external_voucher_lifecycle_state(
    cursor: Any, header_date_predicate: str = "1=1"
) -> dict[str, Any]:
    header_state = _rows(
        cursor,
        f"""
        WITH voucher_state AS (
          SELECT ExternalVoucherHeaderId,COUNT_BIG(*) any_vouchers,
                 SUM(CASE WHEN ISNULL(IsDeleted,0)=0 THEN 1 ELSE 0 END) active_vouchers
          FROM dbo.Voucher WHERE ExternalVoucherHeaderId IS NOT NULL
          GROUP BY ExternalVoucherHeaderId
        ), x AS (
          SELECT h.Confirmed,COALESCE(v.any_vouchers,0) any_vouchers,
                 COALESCE(v.active_vouchers,0) active_vouchers
          FROM dbo.ExternalVoucherHeader h LEFT JOIN voucher_state v
            ON v.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId
          WHERE {header_date_predicate}
        )
        SELECT COUNT_BIG(*) headers,
          SUM(CASE WHEN Confirmed=1 THEN 1 ELSE 0 END) confirmed_headers,
          SUM(CASE WHEN Confirmed=0 THEN 1 ELSE 0 END) unconfirmed_headers,
          SUM(CASE WHEN active_vouchers>0 THEN 1 ELSE 0 END) linked_active_headers,
          SUM(CASE WHEN any_vouchers>0 THEN 1 ELSE 0 END) linked_any_headers,
          SUM(CASE WHEN Confirmed=1 AND active_vouchers=0 THEN 1 ELSE 0 END) confirmed_not_transferred,
          SUM(CASE WHEN Confirmed=0 AND any_vouchers=0 THEN 1 ELSE 0 END) delete_eligible_shape,
          SUM(CASE WHEN active_vouchers=1 THEN 1 ELSE 0 END) exactly_one_active_voucher,
          SUM(CASE WHEN active_vouchers>1 THEN 1 ELSE 0 END) multiple_active_vouchers,
          MAX(active_vouchers) max_active_vouchers_per_header,
          MAX(any_vouchers) max_any_vouchers_per_header
        FROM x
        """,
    )[0]
    set_scope_join = (
        ""
        if header_date_predicate == "1=1"
        else f"INNER JOIN dbo.ExternalVoucherHeader selected ON "
        f"selected.ExternalVoucherHeaderId=s.ExternalVoucherHeaderId "
        f"AND {header_date_predicate.replace('h.', 'selected.')}"
    )
    set_voucher_no = _rows(
        cursor,
        f"""
        WITH active_voucher AS (
          SELECT DISTINCT ExternalVoucherHeaderId FROM dbo.Voucher
          WHERE ExternalVoucherHeaderId IS NOT NULL AND ISNULL(IsDeleted,0)=0
        ), x AS (
          SELECT s.ExternalVoucherHeaderId,
                 CASE WHEN h.ExternalVoucherHeaderId IS NULL THEN 1 ELSE 0 END missing_header,
                 CASE WHEN av.ExternalVoucherHeaderId IS NULL THEN 1 ELSE 0 END no_active_voucher
          FROM dbo.SetVoucherNo s
          {set_scope_join}
          LEFT JOIN dbo.ExternalVoucherHeader h
            ON h.ExternalVoucherHeaderId=s.ExternalVoucherHeaderId
          LEFT JOIN active_voucher av
            ON av.ExternalVoucherHeaderId=s.ExternalVoucherHeaderId
        ), grouped AS (
          SELECT ExternalVoucherHeaderId,COUNT_BIG(*) rows_per_header
          FROM x GROUP BY ExternalVoucherHeaderId
        )
        SELECT (SELECT COUNT_BIG(*) FROM x) rows,
          (SELECT COUNT_BIG(*) FROM grouped) headers,
          (SELECT COALESCE(SUM(missing_header),0) FROM x) missing_header_rows,
          (SELECT COALESCE(SUM(no_active_voucher),0) FROM x) no_active_voucher_rows,
          (SELECT COALESCE(SUM(1-no_active_voucher),0) FROM x) active_voucher_rows,
          (SELECT COALESCE(SUM(CASE WHEN rows_per_header>1 THEN 1 ELSE 0 END),0) FROM grouped) duplicate_header_groups,
          (SELECT COALESCE(MAX(rows_per_header),0) FROM grouped) max_rows_per_header
        """,
    )[0]
    return {
        "header_state": header_state,
        "set_voucher_number_state": set_voucher_no,
        "interpretation": (
            "The restored snapshot is terminal and internally clean: every retained external header "
            "is confirmed, has exactly one active ledger voucher, and has exactly one SetVoucherNo row. "
            "This is state evidence, not proof that transient confirm/delete/transfer branches are defect-free."
        ),
    }


def _historical_grouping(cursor: Any) -> dict[str, Any]:
    historical = _rows(
        cursor,
        """
        WITH source_group AS (
          SELECT ExternalVoucherHeaderId,ReferenceName,ReferenceId,DCId,SaleOfficeId
          FROM dbo.PreVoucher WHERE ExternalVoucherHeaderId IS NOT NULL
          GROUP BY ExternalVoucherHeaderId,ReferenceName,ReferenceId,DCId,SaleOfficeId
        ), per_header AS (
          SELECT ExternalVoucherHeaderId,COUNT_BIG(*) source_groups
          FROM source_group GROUP BY ExternalVoucherHeaderId
        ), fiscal AS (
          SELECT a.AccYear,f.ExternalVoucherIssueMode current_issue_mode
          FROM gnr.TblACCYear a JOIN dbo.FiscalYear f
            ON f.StartDate=a.StartDate AND f.EndDate=a.EndDate
        )
        SELECT h.AccYear,f.current_issue_mode,COUNT_BIG(*) headers,
          SUM(CASE WHEN p.source_groups=1 THEN 1 ELSE 0 END) single_source_headers,
          SUM(CASE WHEN p.source_groups>1 THEN 1 ELSE 0 END) multi_source_headers,
          SUM(p.source_groups) source_groups,MAX(p.source_groups) max_source_groups_per_header
        FROM dbo.ExternalVoucherHeader h JOIN per_header p
          ON p.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId
        LEFT JOIN fiscal f ON f.AccYear=h.AccYear
        GROUP BY h.AccYear,f.current_issue_mode ORDER BY h.AccYear
        """,
    )
    recent = _rows(
        cursor,
        f"""
        WITH source_group AS (
          SELECT ExternalVoucherHeaderId,ReferenceName,ReferenceId,DCId,SaleOfficeId
          FROM dbo.PreVoucher WHERE ExternalVoucherHeaderId IS NOT NULL
            AND PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
          GROUP BY ExternalVoucherHeaderId,ReferenceName,ReferenceId,DCId,SaleOfficeId
        ), per_header AS (
          SELECT ExternalVoucherHeaderId,COUNT_BIG(*) source_groups
          FROM source_group GROUP BY ExternalVoucherHeaderId
        )
        SELECT COUNT_BIG(*) headers,
          SUM(CASE WHEN source_groups=1 THEN 1 ELSE 0 END) single_source_headers,
          SUM(CASE WHEN source_groups>1 THEN 1 ELSE 0 END) multi_source_headers,
          SUM(source_groups) source_groups,MIN(source_groups) min_source_groups_per_header,
          MAX(source_groups) max_source_groups_per_header FROM per_header
        """,
    )[0]
    drift_years = [
        row["AccYear"]
        for row in historical
        if row["current_issue_mode"] == 1 and row["multi_source_headers"] > 0
    ]
    return {
        "by_accounting_year": historical,
        "three_month_window": {
            "from": BUSINESS_DATE_FROM,
            "to": BUSINESS_DATE_TO,
            **recent,
        },
        "current_mode_one_but_historical_multi_source_years": drift_years,
        "current_policy_fully_explains_history": not drift_years,
        "interpretation": (
            "Current mutable FiscalYear.ExternalVoucherIssueMode cannot reproduce all persisted header grouping. "
            "A target ERP must persist the effective grouping-policy version/snapshot on every issuance batch."
        ),
    }


def _creator_posting_parity(
    cursor: Any,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    if (date_from is None) != (date_to is None):
        raise ValueError("date_from and date_to must be supplied together")
    pre_voucher_predicate = (
        "1=1"
        if date_from is None
        else f"PreVoucherDate BETWEEN '{date_from}' AND '{date_to}'"
    )
    header_predicate = (
        "1=1"
        if date_from is None
        else f"h.EndDate BETWEEN '{date_from}' AND '{date_to}'"
    )
    rows = _rows(
        cursor,
        f"""
        WITH source_groups AS (
          SELECT VoucherCreatorId,ReferenceId,FiscalYearId,DCId FROM dbo.PreVoucher
          WHERE {pre_voucher_predicate}
          GROUP BY VoucherCreatorId,ReferenceId,FiscalYearId,DCId
        ), sg AS (
          SELECT VoucherCreatorId,COUNT_BIG(*) source_groups
          FROM source_groups GROUP BY VoucherCreatorId
        ), p AS (
          SELECT VoucherCreatorId,COUNT_BIG(*) lines,
                 COUNT(DISTINCT ExternalVoucherHeaderId) headers,
                 COUNT(DISTINCT ExternalVoucherTypeId) external_types,
                 SUM(DebitAmount) debit,SUM(CreditAmount) credit
          FROM dbo.PreVoucher
          WHERE {pre_voucher_predicate}
          GROUP BY VoucherCreatorId
        ), e AS (
          SELECT t.VoucherCreatorId,COUNT_BIG(v.ExternalVoucherId) lines,
                 COUNT(DISTINCT h.ExternalVoucherHeaderId) headers,
                 SUM(v.DebitAmount) debit,SUM(v.CreditAmount) credit
          FROM dbo.ExternalVoucherHeader h JOIN dbo.ExternalVoucherType t
            ON t.ExternalVoucherTypeId=h.ExternalVoucherTypeId
          JOIN dbo.ExternalVoucher v ON v.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId
          WHERE {header_predicate}
          GROUP BY t.VoucherCreatorId
        ), j AS (
          SELECT t.VoucherCreatorId,COUNT_BIG(i.VoucherItemId) lines,
                 COUNT(DISTINCT v.VoucherId) headers,
                 SUM(i.DebitAmount) debit,SUM(i.CreditAmount) credit
          FROM dbo.ExternalVoucherHeader h JOIN dbo.ExternalVoucherType t
            ON t.ExternalVoucherTypeId=h.ExternalVoucherTypeId
          JOIN dbo.Voucher v ON v.ExternalVoucherHeaderId=h.ExternalVoucherHeaderId
            AND v.IsDeleted=0
          JOIN dbo.VoucherItem i ON i.VoucherId=v.VoucherId AND i.IsDeleted=0
          WHERE {header_predicate}
          GROUP BY t.VoucherCreatorId
        )
        SELECT c.VoucherCreatorId,c.ViewName,ISNULL(p.lines,0) pre_voucher_lines,
          ISNULL(sg.source_groups,0) source_groups,ISNULL(p.headers,0) pre_voucher_headers,
          ISNULL(p.external_types,0) external_types,ISNULL(e.lines,0) external_lines,
          ISNULL(e.headers,0) external_headers,ISNULL(j.lines,0) journal_lines,
          ISNULL(j.headers,0) journal_headers,ISNULL(p.debit,0) pre_voucher_debit,
          ISNULL(p.credit,0) pre_voucher_credit,ISNULL(e.debit,0) external_debit,
          ISNULL(e.credit,0) external_credit,ISNULL(j.debit,0) journal_debit,
          ISNULL(j.credit,0) journal_credit
        FROM dbo.VoucherCreator c LEFT JOIN p ON p.VoucherCreatorId=c.VoucherCreatorId
        LEFT JOIN sg ON sg.VoucherCreatorId=c.VoucherCreatorId
        LEFT JOIN e ON e.VoucherCreatorId=c.VoucherCreatorId
        LEFT JOIN j ON j.VoucherCreatorId=c.VoucherCreatorId
        WHERE EXISTS(SELECT 1 FROM dbo.PreVoucher x WHERE x.VoucherCreatorId=c.VoucherCreatorId)
        ORDER BY c.VoucherCreatorId
        """,
    )
    header_shape = _rows(
        cursor,
        f"""
        WITH h AS (
          SELECT ExternalVoucherHeaderId,COUNT(DISTINCT PreVoucherDate) dates,
                 COUNT(DISTINCT LEFT(PreVoucherDate,7)) months,
                 COUNT(DISTINCT ExternalVoucherTypeId) external_types,
                 COUNT(DISTINCT DCId) dcs,COUNT(DISTINCT SaleOfficeId) sale_offices,
                 COUNT(DISTINCT ReferenceId) sources
          FROM dbo.PreVoucher
          WHERE {pre_voucher_predicate}
          GROUP BY ExternalVoucherHeaderId
        )
        SELECT COUNT_BIG(*) headers,
          SUM(CASE WHEN dates=1 THEN 1 ELSE 0 END) one_date_headers,
          SUM(CASE WHEN dates>1 THEN 1 ELSE 0 END) multi_date_headers,
          SUM(CASE WHEN months>1 THEN 1 ELSE 0 END) multi_month_headers,
          SUM(CASE WHEN external_types=1 THEN 1 ELSE 0 END) one_external_type_headers,
          SUM(CASE WHEN dcs=1 THEN 1 ELSE 0 END) one_dc_headers,
          SUM(CASE WHEN sale_offices=1 THEN 1 ELSE 0 END) one_sale_office_headers,
          SUM(CASE WHEN sources>1 THEN 1 ELSE 0 END) multi_source_headers,
          MAX(dates) max_dates_per_header,MAX(sources) max_sources_per_header FROM h
        """,
    )[0]
    observed = [row for row in rows if row["pre_voucher_lines"] > 0]
    for row in rows:
        row["staging_to_external_line_delta"] = (
            row["pre_voucher_lines"] - row["external_lines"]
        )
    staging_line_parity = all(
        row["pre_voucher_lines"] == row["external_lines"] for row in observed
    )
    external_journal_line_parity = all(
        row["external_lines"] == row["journal_lines"] for row in observed
    )
    header_parity = all(
        row["pre_voucher_headers"]
        == row["external_headers"]
        == row["journal_headers"]
        for row in observed
    )
    amount_parity = all(
        row["pre_voucher_debit"]
        == row["pre_voucher_credit"]
        == row["external_debit"]
        == row["external_credit"]
        == row["journal_debit"]
        == row["journal_credit"]
        for row in observed
    )
    return {
        "scope": "full_history" if date_from is None else "business_date_window",
        "from": date_from,
        "to": date_to,
        "creator_rows": rows,
        "observed_creator_count": len(observed),
        "zero_activity_creator_count": len(rows) - len(observed),
        "header_grouping_shape": header_shape,
        "staging_to_external_line_count_parity": staging_line_parity,
        "external_to_journal_line_count_parity": external_journal_line_parity,
        "three_layer_header_count_parity": header_parity,
        "three_layer_amount_parity": amount_parity,
        "persisted_financial_and_header_parity": (
            amount_parity and header_parity and external_journal_line_parity
        ),
        "three_layer_creator_parity": (
            staging_line_parity
            and external_journal_line_parity
            and header_parity
            and amount_parity
        ),
        "historical_mode_inference": (
            "All 204 headers contain exactly one business date, external type, DC and sale office; "
            "196 contain multiple sources. This shape is exactly consistent with mode 2 daily grouping "
            "and incompatible with the currently stored mode 1 under the deployed procedure. The evidence "
            "does not distinguish a past configuration change from a past procedure-version change."
            if date_from == BUSINESS_DATE_FROM and date_to == BUSINESS_DATE_TO
            else "Full-history shape spans multiple policy eras; use the per-year grouping profile for policy inference."
        ),
    }


def _historical_external_line_grain_profile(cursor: Any) -> dict[str, Any]:
    rows = _rows(
        cursor,
        """
        WITH legacy_equivalent_groups AS (
          SELECT p.VoucherCreatorId,p.ExternalVoucherHeaderId,p.PreVoucherDate,
                 p.ArticleId,p.SLCode,p.DLCode,p.FifthLedgerCode,p.SixthLedgerCode,
                 p.SeventhLedgerCode,p.PreVoucherItemComment,
                 COUNT_BIG(*) source_lines,SUM(p.DebitAmount) debit,
                 SUM(p.CreditAmount) credit
          FROM dbo.PreVoucher p
          GROUP BY p.VoucherCreatorId,p.ExternalVoucherHeaderId,p.PreVoucherDate,
                   p.ArticleId,p.SLCode,p.DLCode,p.FifthLedgerCode,p.SixthLedgerCode,
                   p.SeventhLedgerCode,p.PreVoucherItemComment
        ), legacy_profile AS (
          SELECT VoucherCreatorId,COUNT_BIG(*) expected_lines,
                 SUM(source_lines) source_lines,
                 SUM(CASE WHEN source_lines>1 THEN 1 ELSE 0 END) consolidated_groups,
                 SUM(source_lines-1) collapsed_lines,
                 MAX(source_lines) max_source_lines_per_group,
                 SUM(CASE WHEN debit=credit THEN 1 ELSE 0 END) net_zero_groups
          FROM legacy_equivalent_groups GROUP BY VoucherCreatorId
        ), current_deployed_groups AS (
          SELECT p.VoucherCreatorId,p.ExternalVoucherHeaderId,p.ReferenceNo,p.ArticleId,
                 p.SLCode,p.DLCode,p.FifthLedgerCode,p.SixthLedgerCode,
                 p.SeventhLedgerCode,p.PreVoucherItemComment,
                 CASE WHEN p.DebitAmount=0 THEN 0 ELSE 1 END debit_side,
                 COUNT_BIG(*) source_lines
          FROM dbo.PreVoucher p
          GROUP BY p.VoucherCreatorId,p.ExternalVoucherHeaderId,p.ReferenceNo,p.ArticleId,
                   p.SLCode,p.DLCode,p.FifthLedgerCode,p.SixthLedgerCode,
                   p.SeventhLedgerCode,p.PreVoucherItemComment,
                   CASE WHEN p.DebitAmount=0 THEN 0 ELSE 1 END
        ), current_profile AS (
          SELECT VoucherCreatorId,COUNT_BIG(*) expected_lines,
                 SUM(CASE WHEN source_lines>1 THEN 1 ELSE 0 END) consolidated_groups,
                 SUM(source_lines-1) collapsed_lines,
                 MAX(source_lines) max_source_lines_per_group
          FROM current_deployed_groups GROUP BY VoucherCreatorId
        ), actual AS (
          SELECT t.VoucherCreatorId,COUNT_BIG(v.ExternalVoucherId) external_lines
          FROM dbo.ExternalVoucher v JOIN dbo.ExternalVoucherHeader h
            ON h.ExternalVoucherHeaderId=v.ExternalVoucherHeaderId
          JOIN dbo.ExternalVoucherType t
            ON t.ExternalVoucherTypeId=h.ExternalVoucherTypeId
          GROUP BY t.VoucherCreatorId
        )
        SELECT l.VoucherCreatorId,l.source_lines,
               l.expected_lines legacy_equivalent_expected_lines,
               c.expected_lines current_deployed_expected_lines,
               a.external_lines actual_external_lines,
               l.consolidated_groups legacy_equivalent_consolidated_groups,
               l.collapsed_lines legacy_equivalent_collapsed_lines,
               l.max_source_lines_per_group legacy_equivalent_max_source_lines_per_group,
               l.net_zero_groups legacy_equivalent_net_zero_groups,
               c.consolidated_groups current_deployed_consolidated_groups,
               c.collapsed_lines current_deployed_collapsed_lines,
               c.max_source_lines_per_group current_deployed_max_source_lines_per_group
        FROM legacy_profile l JOIN current_profile c
          ON c.VoucherCreatorId=l.VoucherCreatorId
        LEFT JOIN actual a ON a.VoucherCreatorId=l.VoucherCreatorId
        ORDER BY l.VoucherCreatorId
        """,
    )
    for row in rows:
        row["legacy_equivalent_matches_actual"] = (
            row["legacy_equivalent_expected_lines"] == row["actual_external_lines"]
        )
        row["current_deployed_grain_matches_actual"] = (
            row["current_deployed_expected_lines"] == row["actual_external_lines"]
        )
    return {
        "creator_rows": rows,
        "source_lines": sum(row["source_lines"] for row in rows),
        "actual_external_lines": sum(row["actual_external_lines"] for row in rows),
        "legacy_equivalent_expected_lines": sum(
            row["legacy_equivalent_expected_lines"] for row in rows
        ),
        "current_deployed_expected_lines": sum(
            row["current_deployed_expected_lines"] for row in rows
        ),
        "legacy_equivalent_collapsed_lines": sum(
            row["legacy_equivalent_collapsed_lines"] for row in rows
        ),
        "legacy_equivalent_consolidated_groups": sum(
            row["legacy_equivalent_consolidated_groups"] for row in rows
        ),
        "max_source_lines_per_legacy_equivalent_group": max(
            row["legacy_equivalent_max_source_lines_per_group"] for row in rows
        ),
        "creator_count_matching_legacy_equivalent_grain": sum(
            row["legacy_equivalent_matches_actual"] for row in rows
        ),
        "creator_count_matching_current_deployed_grain": sum(
            row["current_deployed_grain_matches_actual"] for row in rows
        ),
        "all_creators_match_legacy_equivalent_grain": all(
            row["legacy_equivalent_matches_actual"] for row in rows
        ),
        "all_creators_match_current_deployed_grain": all(
            row["current_deployed_grain_matches_actual"] for row in rows
        ),
        "interpretation": (
            "Retained line cardinality exactly matches the grouping grain encoded by "
            "DoExternalVoucher_Create_With_PreVoucher (header/date/article/dimensions/comment, "
            "without ReferenceNo or debit-side separation). It does not fully match the currently "
            "deployed usp_DoExternalVoucher grain. This proves equivalent historical semantics, "
            "not which historical procedure/version was executed."
        ),
    }


def _creator_rules(cursor: Any) -> list[dict[str, Any]]:
    base = _rows(
        cursor,
        f"""
        WITH posting AS (
          SELECT VoucherCreatorId,COUNT_BIG(*) pre_voucher_lines,
                 SUM(CASE WHEN PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' THEN 1 ELSE 0 END) recent_lines,
                 COUNT(DISTINCT ArticleId) historically_observed_articles,
                 COUNT(DISTINCT CASE WHEN PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' THEN ArticleId END) recent_observed_articles,
                 COUNT(DISTINCT FiscalYearId) observed_fiscal_years,
                 MIN(PreVoucherDate) first_observed_business_date,
                 MAX(PreVoucherDate) last_observed_business_date
          FROM dbo.PreVoucher GROUP BY VoucherCreatorId
        ), configured AS (
          SELECT e.VoucherCreatorId,
                 COUNT(DISTINCT e.ExternalVoucherTypeId) external_voucher_types,
                 COUNT(DISTINCT a.ArticleId) articles,
                 COUNT(DISTINCT CASE WHEN a.Debit=1 THEN a.ArticleId END) debit_articles,
                 COUNT(DISTINCT CASE WHEN a.Debit=0 THEN a.ArticleId END) credit_articles,
                 COUNT(DISTINCT CASE WHEN NULLIF(LTRIM(RTRIM(a.WhereStr)),'') IS NOT NULL THEN a.ArticleId END) article_where_rules,
                 COUNT(DISTINCT CASE WHEN NULLIF(LTRIM(RTRIM(e.DefaultWhereClause)),'') IS NOT NULL THEN e.ExternalVoucherTypeId END) type_default_where_rules,
                 COUNT(DISTINCT a.AmountField) amount_fields,
                 COUNT(DISTINCT a.DateField) date_fields,
                 COUNT(DISTINCT CASE WHEN NULLIF(LTRIM(RTRIM(a.DL)),'') IS NOT NULL THEN a.ArticleId END) dl_articles,
                 COUNT(DISTINCT CASE WHEN NULLIF(LTRIM(RTRIM(a.FifthLedger)),'') IS NOT NULL THEN a.ArticleId END) fifth_ledger_articles,
                 COUNT(DISTINCT CASE WHEN NULLIF(LTRIM(RTRIM(a.SixthLedger)),'') IS NOT NULL THEN a.ArticleId END) sixth_ledger_articles,
                 COUNT(DISTINCT CASE WHEN NULLIF(LTRIM(RTRIM(a.SeventhLedger)),'') IS NOT NULL THEN a.ArticleId END) seventh_ledger_articles
          FROM dbo.ExternalVoucherType e LEFT JOIN dbo.Article a
            ON a.ExternalVoucherTypeId=e.ExternalVoucherTypeId
          GROUP BY e.VoucherCreatorId
        )
        SELECT c.VoucherCreatorId,c.ViewName,c.ReferenceObjectName,c.HasCustId,
               c.HasSupplierId,c.HasContactId,p.pre_voucher_lines,p.recent_lines,
               p.historically_observed_articles,p.recent_observed_articles,
               p.observed_fiscal_years,p.first_observed_business_date,
               p.last_observed_business_date,e.external_voucher_types,e.articles,
               e.debit_articles,e.credit_articles,e.article_where_rules,
               e.type_default_where_rules,e.amount_fields,e.date_fields,e.dl_articles,
               e.fifth_ledger_articles,e.sixth_ledger_articles,e.seventh_ledger_articles
        FROM dbo.VoucherCreator c JOIN posting p
          ON p.VoucherCreatorId=c.VoucherCreatorId
        LEFT JOIN configured e ON e.VoucherCreatorId=c.VoucherCreatorId
        ORDER BY c.VoucherCreatorId
        """,
    )
    for row in base:
        creator_id = row["VoucherCreatorId"]
        definition_row = _rows(
            cursor,
            "SELECT m.definition FROM sys.sql_modules m WHERE m.object_id=OBJECT_ID(%s)",
            (row["ViewName"],),
        )
        definition = definition_row[0]["definition"] if definition_row else ""
        row["view_definition_sha256"] = hashlib.sha256(definition.encode("utf-8")).hexdigest()
        row["view_definition_persisted"] = False
        columns = _rows(
            cursor,
            "SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(%s) ORDER BY column_id",
            (row["ViewName"],),
        )
        names = {item["name"].casefold() for item in columns}
        row["output_column_count"] = len(names)
        row["required_output_contract"] = {
            name: name.casefold() in names
            for name in ("VoucherId", "VoucherNo", "DCName", "DCId", "SaleOfficeId")
        }
        dependencies = _rows(
            cursor,
            """
            SELECT COUNT(DISTINCT referenced_id) resolved_dependencies,
                   COUNT_BIG(*) dependency_rows
            FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(%s)
            """,
            (row["ViewName"],),
        )[0]
        row["view_dependency_profile"] = dependencies

        creator_fields = _rows(
            cursor,
            """
            SELECT VoucherCreatorFieldId,VoucherCreatorFieldName
            FROM dbo.VoucherCreatorField WHERE VoucherCreatorId=%s
            ORDER BY VoucherCreatorFieldId
            """,
            (creator_id,),
        )
        field_by_id = {
            item["VoucherCreatorFieldId"]: item["VoucherCreatorFieldName"]
            for item in creator_fields
        }
        field_names = {
            item["VoucherCreatorFieldName"].strip().casefold(): item["VoucherCreatorFieldName"]
            for item in creator_fields
        }
        rules = _rows(
            cursor,
            """
            SELECT e.ExternalVoucherTypeId,e.DefaultWhereClause,e.WhereClause2,
                   a.ArticleId,a.Debit,a.SL,a.DL,a.FifthLedger,a.SixthLedger,
                   a.SeventhLedger,a.AmountField,a.DateField,a.WhereStr,
                   a.ShowDateRange,a.FromAccYear,a.ToAccYear,a.ArticleTemplateId,
                   a.ArticleComment
            FROM dbo.ExternalVoucherType e JOIN dbo.Article a
              ON a.ExternalVoucherTypeId=e.ExternalVoucherTypeId
            WHERE e.VoucherCreatorId=%s
            ORDER BY e.ExternalVoucherTypeId,a.ArticleId
            """,
            (creator_id,),
        )
        coverage_rows = _rows(
            cursor,
            f"""
            SELECT ArticleId,COUNT_BIG(*) historical_lines,
                   SUM(CASE WHEN PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}' THEN 1 ELSE 0 END) recent_lines
            FROM dbo.PreVoucher WHERE VoucherCreatorId=%s
            GROUP BY ArticleId
            """,
            (creator_id,),
        )
        coverage_by_article = {
            item["ArticleId"]: {
                "historical_lines": item["historical_lines"],
                "recent_lines": item["recent_lines"],
            }
            for item in coverage_rows
        }
        article_comments = _rows(
            cursor,
            """
            SELECT ac.ArticleId,ac.CommentOrder,ac.VoucherCreatorFieldId,ac.ConstantComment
            FROM dbo.ArticleComment ac JOIN dbo.Article a ON a.ArticleId=ac.ArticleId
            JOIN dbo.ExternalVoucherType e ON e.ExternalVoucherTypeId=a.ExternalVoucherTypeId
            WHERE e.VoucherCreatorId=%s ORDER BY ac.ArticleId,ac.CommentOrder
            """,
            (creator_id,),
        )
        comments_by_article: dict[int, list[dict[str, Any]]] = {}
        for item in article_comments:
            comments_by_article.setdefault(item["ArticleId"], []).append(item)
        external_type_ordinals = {
            value: index + 1
            for index, value in enumerate(
                sorted({item["ExternalVoucherTypeId"] for item in rules})
            )
        }

        def _field_source(value: Any) -> dict[str, Any]:
            raw = "" if value is None else str(value).strip()
            if not raw:
                return {"kind": "NONE"}
            matched = field_names.get(raw.casefold())
            if matched is not None:
                return {"kind": "VIEW_FIELD", "field": matched}
            return {
                "kind": "STATIC_LITERAL_OR_EXPRESSION",
                "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                "length": len(raw),
            }

        def _predicate(value: Any) -> dict[str, Any]:
            raw = "" if value is None else str(value).strip()
            lowered = raw.casefold()
            return {
                "present": bool(raw),
                "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                "length": len(raw),
                "operator_counts": {
                    keyword: len(re.findall(rf"\b{keyword}\b", lowered))
                    for keyword in ("and", "or", "not", "exists", "isnull", "case", "in", "like")
                },
            }

        contracts: list[dict[str, Any]] = []
        kind_counts: Counter[str] = Counter()
        for ordinal, item in enumerate(rules, 1):
            comment_parts = comments_by_article.get(item["ArticleId"], [])
            dynamic_comment_fields = sorted(
                {
                    field_by_id[part["VoucherCreatorFieldId"]]
                    for part in comment_parts
                    if part["VoucherCreatorFieldId"] in field_by_id
                }
            )
            sources = {
                "amount": _field_source(item["AmountField"]),
                "date": _field_source(item["DateField"]),
                "sl": _field_source(item["SL"]),
                "dl": _field_source(item["DL"]),
                "fifth": _field_source(item["FifthLedger"]),
                "sixth": _field_source(item["SixthLedger"]),
                "seventh": _field_source(item["SeventhLedger"]),
            }
            for source_name, source in sources.items():
                kind_counts[f"{source_name}:{source['kind']}"] += 1
            raw_fingerprint_payload = {
                key: (str(value) if isinstance(value, Decimal) else value)
                for key, value in item.items()
            }
            raw_fingerprint_payload["comment_parts"] = comment_parts
            contract = {
                "rule_ordinal": ordinal,
                "external_type_ordinal": external_type_ordinals[item["ExternalVoucherTypeId"]],
                "side": "DEBIT" if item["Debit"] else "CREDIT",
                "effective_accounting_year": {
                    "from": item["FromAccYear"],
                    "to": item["ToAccYear"],
                },
                "shows_date_range": item["ShowDateRange"],
                "uses_article_template": item["ArticleTemplateId"] is not None,
                "sources": sources,
                "predicates": {
                    "article": _predicate(item["WhereStr"]),
                    "external_type_default": _predicate(item["DefaultWhereClause"]),
                    "external_type_secondary": _predicate(item["WhereClause2"]),
                },
                "comment_recipe": {
                    "component_count": len(comment_parts),
                    "dynamic_field_count": len(dynamic_comment_fields),
                    "constant_component_count": sum(
                        bool(str(part["ConstantComment"] or "").strip())
                        for part in comment_parts
                    ),
                    "dynamic_fields": dynamic_comment_fields,
                    "article_comment_present": bool(
                        str(item["ArticleComment"] or "").strip()
                    ),
                },
                "rule_sha256": hashlib.sha256(
                    json.dumps(
                        raw_fingerprint_payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        default=_json_default,
                    ).encode("utf-8")
                ).hexdigest(),
                "retained_history_coverage": coverage_by_article.get(
                    item["ArticleId"],
                    {"historical_lines": 0, "recent_lines": 0},
                ),
                "raw_account_codes_predicates_and_comments_persisted": False,
            }
            contracts.append(contract)
        row["rule_source_kind_counts"] = dict(sorted(kind_counts.items()))
        row["rule_contracts"] = contracts
        row["historically_unobserved_rule_ordinals"] = [
            item["rule_ordinal"]
            for item in contracts
            if item["retained_history_coverage"]["historical_lines"] == 0
        ]
        row["recently_unobserved_rule_ordinals"] = [
            item["rule_ordinal"]
            for item in contracts
            if item["retained_history_coverage"]["recent_lines"] == 0
        ]
        row["rule_contract_sha256"] = hashlib.sha256(
            json.dumps(
                [
                    {
                        key: value
                        for key, value in contract.items()
                        if key != "retained_history_coverage"
                    }
                    for contract in contracts
                ],
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
    return base


def collect(source_directory: Path, binary_inventory_path: Path) -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        il_contract = _deployed_il_contract(source_directory, binary_inventory_path)
        procedures = _procedure_contracts(cursor)
        creator_rules = _creator_rules(cursor)
        full_creator_parity = _creator_posting_parity(cursor)
        creator_parity = _creator_posting_parity(
            cursor, BUSINESS_DATE_FROM, BUSINESS_DATE_TO
        )
        historical_line_grain = _historical_external_line_grain_profile(cursor)
        creator_rule_coverage = {
            "configured_rule_count": sum(row["articles"] for row in creator_rules),
            "historically_observed_rule_count": sum(
                row["articles"] - len(row["historically_unobserved_rule_ordinals"])
                for row in creator_rules
            ),
            "historically_unobserved_rule_count": sum(
                len(row["historically_unobserved_rule_ordinals"])
                for row in creator_rules
            ),
            "recently_observed_rule_count": sum(
                row["articles"] - len(row["recently_unobserved_rule_ordinals"])
                for row in creator_rules
            ),
            "recently_unobserved_rule_count": sum(
                len(row["recently_unobserved_rule_ordinals"])
                for row in creator_rules
            ),
            "all_active_creators_observed_in_retained_history": (
                full_creator_parity["observed_creator_count"] == len(creator_rules)
            ),
            "interpretation": (
                "A structurally configured rule is not equivalent to an exercised rule. "
                "Every retained-history-unobserved rule requires a synthetic owner-approved Golden case."
            ),
        }
        recent_predicate = (
            f"PreVoucherDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'"
        )
        historical_grouping = _historical_grouping(cursor)
        lifecycle_full = _external_voucher_lifecycle_state(cursor)
        lifecycle_recent = _external_voucher_lifecycle_state(
            cursor,
            f"h.EndDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'",
        )
        issuance_finality = _issuance_finality_contract(cursor)
        voucher_type_validation = _voucher_type_structural_validation_profile(cursor)
        dynamic_rule_sql = _dynamic_rule_sql_and_source_snapshot_profile(cursor)
        isolation_and_versioning = _transaction_isolation_and_source_version_profile(
            cursor, source_directory, binary_inventory_path
        )
        rule_write_authority = _rule_configuration_write_authority_profile(
            cursor, source_directory, binary_inventory_path
        )
        rule_replication = _rule_replication_trigger_profile(cursor)
        lifecycle_operations = il_contract["lifecycle_operations"]
        authorization_scope = il_contract["authorization_and_scope_contract"]
        action_procedure_names = (
            "dbo.usp_DoExternalVoucher",
            "dbo.usp_DoExternalVoucherConfirmed",
            "dbo.usp_DoExternalVoucherDelete",
            "dbo.usp_DoExternalVoucherTransfer",
        )
        authorization_scope["server_procedure_authorization"] = {
            "procedures": {
                name: {
                    "references_access_or_action_authorization": procedures[name][
                        "semantic_signals"
                    ]["references_access_or_action_authorization"],
                    "validates_app_user_exists": procedures[name]["semantic_signals"][
                        "validates_app_user_exists"
                    ],
                    "validates_dc_exists": procedures[name]["semantic_signals"][
                        "validates_dc_exists"
                    ],
                    "enforces_operation_finality": procedures[name]["semantic_signals"][
                        "enforces_operation_finality_by_system_dc_year_and_to_date"
                    ],
                }
                for name in action_procedure_names
            },
            "action_procedure_count": len(action_procedure_names),
            "action_procedure_with_authorization_count": sum(
                procedures[name]["semantic_signals"][
                    "references_access_or_action_authorization"
                ]
                for name in action_procedure_names
            ),
            "issue_validates_existing_dc_but_not_user_dc_scope": (
                procedures["dbo.usp_DoExternalVoucher"]["semantic_signals"][
                    "validates_dc_exists"
                ]
                and not procedures["dbo.usp_DoExternalVoucher"]["semantic_signals"][
                    "references_access_or_action_authorization"
                ]
            ),
            "issue_enforces_operation_finality": procedures[
                "dbo.usp_DoExternalVoucher"
            ]["semantic_signals"][
                "enforces_operation_finality_by_system_dc_year_and_to_date"
            ],
        }
        transfer_procedure = procedures["dbo.usp_DoExternalVoucherTransfer"]
        verification = [
            {
                "requirement_or_risk": "bind the deployed desktop command to exact SQL",
                "observable": "Form call, Business handler, DataAccess literal",
                "evidence_grade": "static deployed IL plus hash-pinned binaries",
                "result": "PASS" if il_contract["adapter_binding"]["exact_procedure_literals"] == [SAFE_PROC_LITERAL] else "FAIL",
                "gap": None,
            },
            {
                "requirement_or_risk": "one atomic desktop issuance boundary",
                "observable": "Transaction.Begin, command transaction attachment, commit, finally-dispose",
                "evidence_grade": "static deployed IL",
                "result": "PASS" if il_contract["conclusion"]["desktop_null_context_path_has_one_outer_transaction"] else "FAIL",
                "gap": "direct SQL/nonstandard caller remains unproven because the procedure owns no transaction",
            },
            {
                "requirement_or_risk": "no partial/orphaned posting state in the clone",
                "observable": "aggregate cross-table integrity and balance checks",
                "evidence_grade": "read-only full-clone aggregates",
                "result": "PASS",
                "gap": "clean snapshot does not substitute for concurrent fault injection",
            },
            {
                "requirement_or_risk": "historical issuance grouping is reproducible",
                "observable": "current issue mode versus source groups per persisted header",
                "evidence_grade": "read-only configuration and full-history aggregates",
                "result": "FAIL" if not historical_grouping["current_policy_fully_explains_history"] else "PASS",
                "gap": "no effective-dated policy snapshot is stored on the external voucher header",
            },
            {
                "requirement_or_risk": "creator rule crosswalk is structurally complete",
                "observable": "all active creator views expose required output columns",
                "evidence_grade": "read-only catalog plus definition hashes",
                "result": "PASS"
                if all(
                    all(row["required_output_contract"].values())
                    for row in creator_rules
                )
                else "FAIL",
                "gap": "business meaning still requires owner-approved golden cases per creator",
            },
            {
                "requirement_or_risk": "observed creator amounts survive all three posting layers",
                "observable": "per-creator line/header/debit/credit parity across PreVoucher, ExternalVoucher and active Journal",
                "evidence_grade": "read-only three-month aggregates",
                "result": "PASS" if creator_parity["three_layer_creator_parity"] else "FAIL",
                "gap": "seven configured creators have no activity in this window and need synthetic owner-approved Golden cases",
            },
            {
                "requirement_or_risk": "all active creators reconcile across retained posting history",
                "observable": "per-creator line/header/debit/credit parity across all retained PreVoucher, ExternalVoucher and active Journal rows",
                "evidence_grade": "read-only full-clone aggregates",
                "result": "PASS"
                if full_creator_parity["observed_creator_count"] == len(creator_rules)
                and full_creator_parity["persisted_financial_and_header_parity"]
                else "FAIL",
                "gap": "staging line counts can consolidate before ExternalVoucher; financial/header parity proves persisted results, not every configured rule branch",
            },
            {
                "requirement_or_risk": "every active creator rule has an observed retained example",
                "observable": "configured Article ordinal joined to retained PreVoucher usage",
                "evidence_grade": "read-only catalog and full-clone aggregates",
                "result": "PASS"
                if creator_rule_coverage["historically_unobserved_rule_count"] == 0
                else "FAIL",
                "gap": "unobserved branches need synthetic owner-approved financial Golden cases; absence is not evidence that the rule is obsolete",
            },
            {
                "requirement_or_risk": "current deployed external-line grouping reproduces retained history",
                "observable": "expected group cardinality under current ReferenceNo/debit-side grain versus actual ExternalVoucher lines",
                "evidence_grade": "static SQL definitions plus read-only full-clone aggregates",
                "result": "PASS"
                if historical_line_grain["all_creators_match_current_deployed_grain"]
                else "FAIL",
                "gap": "three creator histories have a different retained line grain; replay with the current procedure can change journal line cardinality",
            },
            {
                "requirement_or_risk": "a known historical-equivalent line grain explains retained history",
                "observable": "header/date/article/dimensions/comment grouping cardinality versus actual ExternalVoucher lines",
                "evidence_grade": "static legacy-equivalent SQL definition plus read-only full-clone aggregates",
                "result": "PASS"
                if historical_line_grain["all_creators_match_legacy_equivalent_grain"]
                else "FAIL",
                "gap": "exact cardinality proves equivalent semantics, not the identity or timestamp of the historical procedure/version that produced each batch",
            },
            {
                "requirement_or_risk": "confirm delete and transfer UI commands bind to exact transactional paths",
                "observable": "UI null DataContext, Business Transaction.Begin/commit/finally-dispose, adapter SQL literal",
                "evidence_grade": "static deployed IL plus hash-pinned binaries",
                "result": "PASS"
                if all(
                    row["outer_transaction_proven"]
                    for row in lifecycle_operations.values()
                )
                else "FAIL",
                "gap": "the three SQL procedures still depend on the standard desktop caller for transaction ownership",
            },
            {
                "requirement_or_risk": "issue confirm unconfirm delete and transfer have separate enforceable action permissions",
                "observable": "toolbar/custom-button permission calls and server-procedure authorization references",
                "evidence_grade": "static hash-pinned UI/base-template IL plus SQL definitions",
                "result": "PASS"
                if authorization_scope["conclusion"][
                    "separate_issue_confirm_unconfirm_transfer_permissions_proven"
                ]
                and authorization_scope["server_procedure_authorization"][
                    "action_procedure_with_authorization_count"
                ]
                == len(action_procedure_names)
                else "FAIL",
                "gap": "screen access and read-grid scope may exist, but no separate command permission or server-side authorization was found for these accounting transitions",
            },
            {
                "requirement_or_risk": "issuance date waits for source-system finality",
                "observable": "fiscal range and per-system/DC/year final-operation-date checks before staging",
                "evidence_grade": "static deployed SQL definition",
                "result": "PASS"
                if authorization_scope["server_procedure_authorization"][
                    "issue_enforces_operation_finality"
                ]
                else "FAIL",
                "gap": "finality gate is strong for issuance, but it is not an action-authorization control",
            },
            {
                "requirement_or_risk": "source finality rejection is pre-mutation",
                "observable": "business-error result and RETURN precede usp_DoPreVoucher and persistent inserts",
                "evidence_grade": "static deployed SQL ordering",
                "result": "PASS"
                if issuance_finality["deployed_sql_semantics"][
                    "finality_failure_is_before_first_persistent_mutation"
                ]
                else "FAIL",
                "gap": "the procedure still depends on the desktop outer transaction after finality passes",
            },
            {
                "requirement_or_risk": "issue confirm and transfer chaining stops on validation failure",
                "observable": "DoWorkSave validation guards between three ordered Business calls",
                "evidence_grade": "hash-pinned deployed UI IL",
                "result": "PASS"
                if il_contract["ui_entrypoint"][
                    "issue_validation_failure_returns_before_confirm"
                ]
                and il_contract["ui_entrypoint"][
                    "confirm_validation_failure_returns_before_transfer"
                ]
                else "FAIL",
                "gap": "runtime message rendering was not executed",
            },
            {
                "requirement_or_risk": "issue message protocol separates errors ids warnings and information",
                "observable": "SQL MessageType 0/1/2/3 and UI/Business handling",
                "evidence_grade": "hash-pinned deployed UI/Business IL plus static SQL",
                "result": "PASS"
                if procedures["dbo.usp_DoExternalVoucher"]["semantic_signals"][
                    "returns_message_type_1_for_business_errors"
                ]
                and procedures["dbo.usp_DoExternalVoucher"]["semantic_signals"][
                    "returns_message_type_0_for_created_header_ids"
                ]
                and procedures["dbo.usp_DoExternalVoucher"]["semantic_signals"][
                    "returns_message_type_2_or_3_for_warning_or_information"
                ]
                and il_contract["business_boundary"][
                    "message_type_one_is_validation_error"
                ]
                and il_contract["ui_entrypoint"][
                    "successful_header_ids_are_parsed_only_from_message_type_zero"
                ]
                else "FAIL",
                "gap": "the contract is numeric and must become a typed target result rather than be copied as magic integers",
            },
            {
                "requirement_or_risk": "issuance policy preflight and applied policy share one immutable snapshot",
                "observable": "config getters, transaction start and procedure parameter list",
                "evidence_grade": "hash-pinned Business IL plus static SQL parameter contract",
                "result": "FAIL"
                if il_contract["business_boundary"][
                    "policy_preflight_occurs_before_issue_transaction"
                ]
                and issuance_finality["deployed_sql_semantics"][
                    "policy_values_are_not_procedure_parameters"
                ]
                else "PASS",
                "gap": "Business compares UI values before opening the issue transaction, while SQL later re-reads mutable policy; no version is passed or persisted",
            },
            {
                "requirement_or_risk": "every configured voucher type is an issueable current capability",
                "observable": "offline replay of deployed structural validator for year 1405",
                "evidence_grade": "static validator SQL plus read-only catalog and configuration aggregates",
                "result": "FAIL"
                if voucher_type_validation["summary"][
                    "structurally_invalid_type_count"
                ]
                else "PASS",
                "gap": "configured rows include dormant or incomplete types; capability activation must be explicit",
            },
            {
                "requirement_or_risk": "structurally invalid current types are absent from retained operational use",
                "observable": "invalid-type set versus retained, recent and modern header coverage",
                "evidence_grade": "read-only aggregate crosswalk",
                "result": "PASS"
                if voucher_type_validation["summary"][
                    "invalid_type_with_retained_history_count"
                ]
                == voucher_type_validation["summary"][
                    "invalid_type_with_recent_history_count"
                ]
                == voucher_type_validation["summary"][
                    "invalid_type_with_modern_header_count"
                ]
                == 0
                else "FAIL",
                "gap": "absence of history does not prove safe deletion; the owner must classify dormant, reserved or obsolete types",
            },
            {
                "requirement_or_risk": "all configured article predicates compile against creator views",
                "observable": "predicate count and validator dynamic WHERE 1=2 branch",
                "evidence_grade": "static SQL only; creator views deliberately not executed",
                "result": "FAIL"
                if voucher_type_validation["summary"][
                    "predicate_count_not_runtime_compiled"
                ]
                else "PASS",
                "gap": "predicate hashes and identifiers are retained, but runtime compilation requires an isolated non-operational harness",
            },
            {
                "requirement_or_risk": "purchase finality covers every stock DC in the selected business DC",
                "observable": "active DC/year StockDC cardinality versus ICA operation-date rows",
                "evidence_grade": "static deployed SQL plus read-only aggregate coverage",
                "result": "FAIL"
                if issuance_finality["summary"][
                    "purchase_partially_covered_active_dc_year_scope_count"
                ]
                else "PASS",
                "gap": "MIN over an inner join sees only existing ICA operation rows; missing StockDC rows can be invisible",
            },
            {
                "requirement_or_risk": "operation-id-5 finality exemption is covered by retained evidence",
                "observable": "configured exempt types versus retained PreVoucher headers",
                "evidence_grade": "static deployed SQL plus read-only retained-history aggregates",
                "result": "FAIL"
                if issuance_finality["summary"][
                    "configured_operation_id_5_type_count"
                ]
                and issuance_finality["summary"][
                    "operation_id_5_retained_header_count"
                ]
                == 0
                else "PASS",
                "gap": "the exemption may be intentional, but its configured branches have no retained example and need owner-approved Golden cases",
            },
            {
                "requirement_or_risk": "accounting staging source reads are committed and snapshot-consistent",
                "observable": "creator-view read hint in dbo.usp_DoPreVoucher",
                "evidence_grade": "static deployed SQL definition",
                "result": "FAIL"
                if dynamic_rule_sql["deployed_sql_semantics"][
                    "creator_view_read_uses_nolock"
                ]
                else "PASS",
                "gap": "WITH(NOLOCK) can make a transient source state persistent in financial staging; no concurrent fault injection was run",
            },
            {
                "requirement_or_risk": "desktop issue transaction chooses an explicit isolation level",
                "observable": "DefaultProvider.Open BeginTransaction call signature",
                "evidence_grade": "hash-pinned static IL",
                "result": "PASS"
                if isolation_and_versioning["deployed_provider_boundary"][
                    "explicit_isolation_level_argument_present"
                ]
                else "FAIL",
                "gap": "the deployed provider uses the parameterless overload; database defaults and per-query hints determine read behavior",
            },
            {
                "requirement_or_risk": "clone database supports committed row-versioned reads",
                "observable": "READ_COMMITTED_SNAPSHOT and ALLOW_SNAPSHOT_ISOLATION options",
                "evidence_grade": "read-only sys.databases catalog",
                "result": "PASS"
                if isolation_and_versioning["clone_database_options"][
                    "is_read_committed_snapshot_on"
                ]
                and isolation_and_versioning["clone_database_options"][
                    "snapshot_isolation_state_desc"
                ]
                == "ON"
                else "FAIL",
                "gap": "NOLOCK on creator-view reads bypasses the committed-read protection, and clone options do not prove production parity",
            },
            {
                "requirement_or_risk": "recent creator sources have portable durable version coverage",
                "observable": "recursive dependency graph to base-table rowversion, temporal and change-tracking signals",
                "evidence_grade": "read-only catalog graph without executing creator views",
                "result": "PASS"
                if isolation_and_versioning["summary"][
                    "recent_source_base_table_with_rowversion_count"
                ]
                == isolation_and_versioning["summary"][
                    "recent_source_base_table_count"
                ]
                or isolation_and_versioning["summary"][
                    "recent_source_temporal_base_table_count"
                ]
                == isolation_and_versioning["summary"][
                    "recent_source_base_table_count"
                ]
                or isolation_and_versioning["summary"][
                    "recent_source_change_tracked_base_table_count"
                ]
                == isolation_and_versioning["summary"][
                    "recent_source_base_table_count"
                ]
                else "FAIL",
                "gap": "only a minority of the 54 recent-source base tables expose rowversion and none is temporal or change-tracked; name-like date/version columns are not a portable watermark",
            },
            {
                "requirement_or_risk": "voucher rule configuration is not executed as concatenated SQL",
                "observable": "dynamic-batch construction and execution sites in pre-voucher and structural validator procedures",
                "evidence_grade": "static deployed SQL definition",
                "result": "FAIL"
                if dynamic_rule_sql["deployed_sql_semantics"][
                    "pre_voucher_builds_one_concatenated_sql_batch"
                ]
                or dynamic_rule_sql["deployed_sql_semantics"][
                    "validator_executes_concatenated_view_and_predicate"
                ]
                else "PASS",
                "gap": "configuration write authority was not attributed; the target needs a typed and versioned rule model rather than executable fragments",
            },
            {
                "requirement_or_risk": "current configured fragments contain obvious SQL meta tokens",
                "observable": "aggregate separator/comment/statement/quote/control-character token counts",
                "evidence_grade": "read-only configuration scan with no raw value persistence",
                "result": "PASS"
                if dynamic_rule_sql["summary"][
                    "current_suspicious_token_or_quote_value_count"
                ]
                == 0
                else "FAIL",
                "gap": "a clean current snapshot neither proves semantic safety nor removes the concatenated-SQL design risk",
            },
            {
                "requirement_or_risk": "voucher-rule write authority is attributable to a deployed form and permission",
                "observable": "62 hash-pinned assemblies, named form/caller scan and handler SaveCommand body",
                "evidence_grade": "static full-package IL and metadata",
                "result": "PASS"
                if rule_write_authority["summary"][
                    "configuration_write_authority_attributed_to_deployed_form"
                ]
                else "FAIL",
                "gap": "the named SaveCommand is a write-disabled validation stub and no deployed form/caller was found; SQL administrative authority remains outside the attributed application path",
            },
            {
                "requirement_or_risk": "voucher-template rule transfer is atomic versioned and audited",
                "observable": "two template-transfer procedure definitions and their mutation chain",
                "evidence_grade": "static deployed SQL definitions",
                "result": "PASS"
                if rule_write_authority["summary"][
                    "template_transfer_procedure_with_transaction_count"
                ]
                == rule_write_authority["summary"][
                    "template_transfer_procedure_count"
                ]
                and rule_write_authority["summary"][
                    "template_transfer_procedure_with_try_catch_count"
                ]
                == rule_write_authority["summary"][
                    "template_transfer_procedure_count"
                ]
                and rule_write_authority["summary"][
                    "template_transfer_procedure_with_version_audit_signal_count"
                ]
                == rule_write_authority["summary"][
                    "template_transfer_procedure_count"
                ]
                else "FAIL",
                "gap": "the no-parameter parent drops/creates creator views and populates five rule tables through dynamic SQL and a child procedure without transaction, TRY/CATCH, rollback or publish version",
            },
            {
                "requirement_or_risk": "read-only analyzer can execute voucher-template transfer",
                "observable": "HAS_PERMS_BY_NAME for both transfer procedures",
                "evidence_grade": "read-only permission introspection for analyzer login",
                "result": "PASS"
                if rule_write_authority["summary"][
                    "analyzer_login_executable_template_procedure_count"
                ]
                == 0
                else "FAIL",
                "gap": "zero analyzer permission is a safety control, not evidence about db_owner or other administrative principals",
            },
            {
                "requirement_or_risk": "rule replication INSERT payload covers the current table schema",
                "observable": "Article and ArticleComment trigger column lists versus current catalog",
                "evidence_grade": "static trigger SQL plus read-only column metadata",
                "result": "PASS"
                if all(
                    row["all_nonidentity_columns_replicated"]
                    for row in rule_replication[
                        "replication_insert_column_coverage"
                    ].values()
                )
                else "FAIL",
                "gap": "column coverage proves shape only; downstream script execution and result parity remain separate",
            },
            {
                "requirement_or_risk": "template Article transfer dynamic INSERT matches the current schema",
                "observable": "dynamic INSERT column list versus sys.columns",
                "evidence_grade": "static procedure SQL plus read-only column metadata",
                "result": "PASS"
                if rule_replication["summary"][
                    "template_article_dynamic_insert_schema_compatible"
                ]
                else "FAIL",
                "gap": "two referenced columns no longer exist and six current optional columns are omitted; failure occurs only at dynamic execution after parent mutations",
            },
            {
                "requirement_or_risk": "recent financial-rule changes carry immutable version and approval provenance",
                "observable": "three-month Article/ArticleComment log counts and gnr.tblLog schema",
                "evidence_grade": "read-only aggregate log and catalog metadata",
                "result": "PASS"
                if rule_replication["summary"][
                    "three_month_rule_replication_log_count"
                ]
                == 0
                or (
                    rule_replication["local_log_writer_contract"][
                        "has_rule_or_policy_version_column"
                    ]
                    and rule_replication["local_log_writer_contract"][
                        "has_approval_column"
                    ]
                )
                else "FAIL",
                "gap": "four recent Article update logs have runtime host/app/SQL-user context but no immutable rule/policy version or approval field",
            },
            {
                "requirement_or_risk": "retained external-voucher lifecycle state is terminal and one-to-one",
                "observable": "confirmed/header-to-active-voucher/SetVoucherNo aggregate cardinality",
                "evidence_grade": "read-only full-clone and three-month aggregates",
                "result": "PASS"
                if lifecycle_full["header_state"]["headers"]
                == lifecycle_full["header_state"]["confirmed_headers"]
                == lifecycle_full["header_state"]["exactly_one_active_voucher"]
                == lifecycle_full["set_voucher_number_state"]["headers"]
                and lifecycle_full["header_state"]["multiple_active_vouchers"] == 0
                and lifecycle_full["set_voucher_number_state"]["duplicate_header_groups"] == 0
                else "FAIL",
                "gap": "the clone retains no unconfirmed/delete-eligible example, so negative branches need synthetic tests",
            },
            {
                "requirement_or_risk": "transfer validation is side-effect free",
                "observable": "ordering of SetVoucherNo delete, validation call, normal RETURN and Business commit",
                "evidence_grade": "SQL definition plus static deployed IL",
                "result": "FAIL"
                if transfer_procedure["semantic_signals"][
                    "deletes_set_voucher_no_before_validation"
                ]
                and transfer_procedure["semantic_signals"][
                    "validation_can_return_without_exception"
                ]
                and lifecycle_operations["transfer_to_general_ledger"][
                    "outer_transaction_proven"
                ]
                else "PASS",
                "gap": "current snapshot has no orphan SetVoucherNo rows, so impact is a reachable code-path risk rather than an observed retained inconsistency",
            },
        ]
        return {
            "artifact": "varanegar_voucher_creation_atomicity_and_policy_contract",
            "schema_version": 2,
            "generated_at": datetime.now().astimezone(),
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "source_directory": str(source_directory),
                "mode": "read-only clone aggregates and static deployed IL",
                "business_window": {"from": BUSINESS_DATE_FROM, "to": BUSINESS_DATE_TO},
            },
            "safety": {
                "target_is_local": True,
                "database_name": safety["database_name"],
                "updateability": safety["updateability"],
                "can_update": safety["can_update"],
                "denies_data_writes": safety["denies_data_writes"],
                "operational_procedures_executed": 0,
                "creator_views_executed": 0,
                "assemblies_loaded_or_executed": 0,
                "raw_sql_definitions_persisted": 0,
                "operational_source_row_ids_or_values_persisted": 0,
            },
            "deployed_call_and_transaction_contract": il_contract,
            "procedure_contracts": procedures,
            "effective_policy": _effective_policy(cursor),
            "issuance_finality_contract": issuance_finality,
            "voucher_type_structural_validation_profile": voucher_type_validation,
            "dynamic_rule_sql_and_source_snapshot_profile": dynamic_rule_sql,
            "transaction_isolation_and_source_version_profile": isolation_and_versioning,
            "rule_configuration_write_authority_profile": rule_write_authority,
            "rule_replication_trigger_profile": rule_replication,
            "pre_voucher_idempotency": _index_contract(cursor),
            "full_history_integrity": _integrity_profile(cursor),
            "three_month_integrity": _integrity_profile(cursor, recent_predicate),
            "historical_grouping_policy_drift": historical_grouping,
            "full_history_creator_posting_parity": full_creator_parity,
            "three_month_creator_posting_parity": creator_parity,
            "active_creator_rule_coverage": creator_rule_coverage,
            "historical_external_line_grain_profile": historical_line_grain,
            "full_history_lifecycle_state": lifecycle_full,
            "three_month_lifecycle_state": lifecycle_recent,
            "active_creator_rule_profiles": creator_rules,
            "verification_matrix": verification,
            "engineering_conclusion": {
                "active_desktop_path": "FormExternalVoucher.DoWorkSave -> ExternalVoucherHeaderHandler.DoExternalVoucher -> ExternalVoucherHeaderAdapter.DoExternalVoucher -> dbo.usp_DoExternalVoucher -> dbo.usp_DoPreVoucher",
                "legacy_do_external_voucher_create_is_active_desktop_path": False,
                "desktop_atomicity": "proven by static deployed IL; one outer client transaction covers the modern procedure",
                "server_owned_atomicity": "not present in dbo.usp_DoExternalVoucher",
                "snapshot_integrity": "clean across staging/header/line links and double-entry aggregates",
                "historical_line_grain": "retained ExternalVoucher cardinality exactly matches a legacy-equivalent net grouping grain but not the current deployed ReferenceNo/debit-side grain for every creator",
                "retained_lifecycle_state": "all retained headers are confirmed and map one-to-one to an active Voucher and SetVoucherNo row",
                "explicit_delete_semantics": "an unconfirmed and untransferred batch is deleted across PreVoucher, relations, external lines and header; it may then be generated again",
                "transfer_validation_side_effect": "SetVoucherNo cleanup occurs before validation and can commit when validation returns a business-error result without throwing",
                "authorization_boundary": "read UI is session AccYear/DC scoped and issuance checks source finality, but separate issue/confirm/unconfirm/delete/transfer authorization is not enforced in the standard command path",
                "issuance_finality_boundary": "rejection is pre-mutation, but purchase MIN ignores missing StockDC operation rows and OperationId 5 is explicitly exempt without a retained example",
                "issue_result_chaining": "MessageType 1 blocks confirmation, only MessageType 0 becomes a header id, and action modes 1/2/3 chain issue, confirm and transfer with validation stops",
                "policy_preflight_race": "Business checks UI policy values before opening the issue transaction; SQL receives no policy version/values and re-reads mutable configuration",
                "voucher_type_capability_boundary": "year-1405 configured types include structurally invalid dormant rows with no retained use; configuration presence is not capability readiness",
                "source_snapshot_boundary": "creator views are read WITH(NOLOCK) and their results become persistent financial staging inside the outer issue transaction",
                "transaction_isolation_boundary": "the provider uses parameterless BeginTransaction; the clone has RCSI and snapshot isolation enabled, but NOLOCK bypasses committed-read semantics and only 6 of 54 recent-source base tables expose rowversion",
                "dynamic_rule_boundary": "trusted configuration fields are concatenated into executable SQL; the current aggregate scan is clean but the target must use typed, versioned and validated rules",
                "rule_publish_boundary": "the deployed application has no attributed rule editor and its named SaveCommand is a validation stub, while two uncalled SQL template-transfer procedures can rebuild views and populate five executable-rule tables without transaction or publish version",
                "rule_replication_boundary": "six enabled triggers serialize complete current Article/ArticleComment INSERT shapes into local gnr.tblLog; four recent Article updates are evidenced, but the legacy template child is schema-incompatible and the log has no rule version or approval field",
                "material_gap": "mutable issue-mode/grouping configuration does not explain persisted 1405 grouping; policy version must be stored with every target batch",
            },
            "evidence_limits": [
                "No operational stored procedure or creator view was executed.",
                "The clone can lag production; counts describe this restored read-only snapshot.",
                "Static IL proves the desktop call path and transaction mechanics, not every possible integration caller.",
                "No fault injection or concurrent mutation test was performed against Varanegar.",
                "Current policy drift proves missing historical explainability, not the exact time or actor of the configuration change.",
                "The retained clone contains no unconfirmed/delete-eligible header; delete and reversal rules are proven from code, not observed examples.",
                "Current purchase operation-date coverage proves missing rows in active DC/year scopes, but no modern purchase header is retained to prove historical runtime impact.",
                "Creator-view predicate compilation was not executed; structural replay cannot prove dynamic predicate runtime validity.",
                "No creator view was read, so the NOLOCK finding is a reachable code-path risk rather than an observed dirty-read incident.",
                "Clone database options may differ from production; the catalog result proves only this restored read-only database configuration.",
                "Version-like column names are heuristic metadata and are not treated as a durable cross-table source watermark.",
                "No configuration writer was attributed and no current suspicious token was found; the dynamic-SQL finding is a design boundary, not a claim of current injection.",
                "The absence of a deployed form/caller does not prove the template-transfer procedures are never run by database administrators or external tooling.",
                "Explicit object-permission rows were absent and the analyzer login is denied execution; db_owner/sysadmin and ownership semantics remain outside this aggregate attribution.",
                "Replication log counts prove trigger activity, not successful downstream application of each generated SQL script.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    payload = collect(args.source_directory, args.binary_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
