"""Extract hash-pinned operation-date gates on order-to-sale conversion."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
sys.path.insert(0, str(WINDOWS_SCRIPTS))
from extract_varanegar_targeted_il_contracts import _full_type_name, _owner_maps, _resolve_token  # noqa: E402


TARGETS = {
    "VN.SDS.Sales.UI.dll": {
        "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale": {
            "CheckSetOprDate",
            "SetUpInitial",
            "AcceptCommandOld",
            "AcceptCommandDiscountV2",
        }
    },
    "VN.SDS.MainData.Business.dll": {
        "VN.SDS.MainData.Business.OprDate.OprDateHandler": {
            "CheckSetOprDate",
            "IsBiggerlastDate",
        }
    },
}

ALLOWLISTED_LITERALS = {"VN.SDS.Sales", "SetOprDate"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _constant(instruction: Any) -> int | float | None:
    values = {f"ldc.i4.{value}": value for value in range(9)}
    values["ldc.i4.m1"] = -1
    if instruction.mnemonic in values:
        return values[instruction.mnemonic]
    if instruction.mnemonic in {"ldc.i4", "ldc.i4.s", "ldc.i8", "ldc.r4", "ldc.r8"}:
        return instruction.operand if isinstance(instruction.operand, (int, float)) else None
    return None


def _instruction(pe, item, method_owners, field_owners):
    row: dict[str, Any] = {"offset": int(item.offset), "opcode": item.mnemonic}
    value = _constant(item)
    if value is not None:
        row["numeric_constant"] = value
    operand = item.operand
    variable_index = getattr(operand, "index", None)
    if isinstance(variable_index, int):
        row["variable_index"] = variable_index
    if item.mnemonic.startswith(("br", "beq", "bne", "ble", "blt", "bge", "bgt", "leave")):
        target = getattr(operand, "offset", operand)
        if isinstance(target, int):
            row["branch_target_offset"] = target
    if isinstance(operand, StringToken):
        found = pe.net.user_strings.get(operand.rid)
        text = "" if found is None else str(found.value)
        row["string_literal"] = {
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "length": len(text),
            "allowlisted_value": text if text in ALLOWLISTED_LITERALS else None,
            "raw_non_allowlisted_value_persisted": False,
        }
    elif isinstance(operand, Token):
        row["member"] = _resolve_token(pe, operand, method_owners, field_owners)
    return row


def _method(pe, assembly, owner, index, method_owners, field_owners):
    row = index.row
    body = read_method_body_from_bytes(pe.get_data(row.Rva, 524288))
    instructions = [
        _instruction(pe, item, method_owners, field_owners) for item in body.instructions
    ]
    return {
        "assembly_file": assembly,
        "type": owner,
        "method": str(row.Name),
        "instruction_count": len(instructions),
        "has_exception_regions": bool(body.exception_handlers),
        "instructions": instructions,
    }


def _members(method: dict[str, Any] | None) -> list[str]:
    return [] if method is None else [row["member"] for row in method["instructions"] if "member" in row]


def _local_index(instruction: dict[str, Any]) -> int | None:
    if "variable_index" in instruction:
        return instruction["variable_index"]
    match = __import__("re").fullmatch(r"(?:ld|st)loc\.(\d+)", instruction["opcode"])
    return int(match.group(1)) if match else None


def _automatic_date_flows(method: dict[str, Any] | None) -> list[dict[str, Any]]:
    if method is None:
        return []
    rows = method["instructions"]
    flows = []
    for index, row in enumerate(rows):
        if row.get("member") != "VN.SDS.MainData.Business.OprDate.OprDateHandler.IsBiggerlastDate":
            continue
        output_rows = rows[max(0, index - 3) : index]
        output_locals = [_local_index(item) for item in output_rows if item["opcode"].startswith("ldloca")]
        setter_index = next(
            (
                candidate
                for candidate in range(index + 1, min(len(rows), index + 25))
                if rows[candidate].get("member") == "Application.BaseData.UserSessionInfo.set_OperationdDate_Sale"
            ),
            None,
        )
        session_local = _local_index(rows[setter_index - 1]) if setter_index is not None else None
        flows.append(
            {
                "call_offset": row["offset"],
                "last_date_output_local": output_locals[0] if len(output_locals) == 2 else None,
                "operation_date_output_local": output_locals[1] if len(output_locals) == 2 else None,
                "session_operation_date_source_local": session_local,
                "session_uses_operation_date_output": len(output_locals) == 2 and session_local == output_locals[1],
            }
        )
    return flows


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = _load(binary_inventory)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    sources = []
    methods = []
    errors = []
    for assembly, types in TARGETS.items():
        path = source_directory / assembly
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        sources.append(
            {
                "assembly_file": assembly,
                "assembly_bytes": path.stat().st_size,
                "assembly_sha256": actual,
                "inventory_sha256_match": actual == expected.get(assembly),
            }
        )
        pe = dnfile.dnPE(str(path))
        method_owners, field_owners = _owner_maps(pe)
        type_rows = {_full_type_name(row): row for row in pe.net.mdtables.TypeDef.rows}
        for owner, names in types.items():
            type_row = type_rows.get(owner)
            if type_row is None:
                errors.append({"assembly": assembly, "type": owner, "error": "TYPE_ABSENT"})
                continue
            found = set()
            for index in type_row.MethodList or []:
                row = index.row
                if row is None or not row.Rva or str(row.Name) not in names:
                    continue
                found.add(str(row.Name))
                try:
                    methods.append(_method(pe, assembly, owner, index, method_owners, field_owners))
                except Exception as exc:
                    errors.append(
                        {"assembly": assembly, "type": owner, "method": str(row.Name), "error": type(exc).__name__}
                    )
            for name in names - found:
                errors.append({"assembly": assembly, "type": owner, "method": name, "error": "METHOD_ABSENT"})

    def one(owner: str, name: str) -> dict[str, Any] | None:
        rows = [row for row in methods if row["type"] == owner and row["method"] == name]
        return rows[0] if len(rows) == 1 else None

    ui_owner = "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale"
    business_owner = "VN.SDS.MainData.Business.OprDate.OprDateHandler"
    ui_check = one(ui_owner, "CheckSetOprDate")
    setup = one(ui_owner, "SetUpInitial")
    old = one(ui_owner, "AcceptCommandOld")
    v2 = one(ui_owner, "AcceptCommandDiscountV2")
    business_check = one(business_owner, "CheckSetOprDate")
    bigger = one(business_owner, "IsBiggerlastDate")
    business_members = _members(business_check)
    ui_members = _members(ui_check)
    setup_members = _members(setup)
    old_members = _members(old)
    v2_members = _members(v2)
    permission_literals = {
        row["string_literal"]["allowlisted_value"]
        for row in (business_check or {}).get("instructions", [])
        if row.get("string_literal", {}).get("allowlisted_value")
    }
    bigger_stores = []
    if bigger is not None:
        rows = bigger["instructions"]
        for index, row in enumerate(rows):
            if row["opcode"] != "stind.ref":
                continue
            previous_members = [item["member"] for item in rows[max(0, index - 8) : index] if "member" in item]
            bigger_stores.append(previous_members[-1] if previous_members else None)
    automatic_date_flows = _automatic_date_flows(business_check)
    assertions = {
        "all_source_hashes_match": all(row["inventory_sha256_match"] for row in sources),
        "selected_methods_complete": len(methods) == 6 and not errors,
        "business_gate_calls_named_permission": "Application.BaseData.UserSessionInfo.HasPersmission" in business_members,
        "business_gate_permission_resource_and_action_are_allowlisted": permission_literals
        == {"VN.SDS.Sales", "SetOprDate"},
        "business_gate_reads_and_sets_session_operation_date": all(
            member in business_members
            for member in (
                "Application.BaseData.UserSessionInfo.get_OperationdDate_IsSet",
                "Application.BaseData.UserSessionInfo.set_OperationdDate_IsSet",
                "Application.BaseData.UserSessionInfo.set_OperationdDate_Sale",
            )
        ),
        "business_gate_checks_closed_and_last_date": (
            "VN.SDS.Common.MainData.Entity.OprDate.OprDateEntity.get_IsClosed" in business_members
            and "VN.SDS.MainData.Business.OprDate.OprDateHandler.IsBiggerlastDate" in business_members
        ),
        "fetch_reason_two_outputs_last_date_then_operation_date": bigger_stores
        == [
            "VN.SDS.Common.MainData.Entity.OprDate.OprDateEntity.get_LastDate",
            "VN.SDS.Common.MainData.Entity.OprDate.OprDateEntity.get_OprDate",
        ],
        "automatic_session_assignment_uses_operation_date_second_output": (
            len(automatic_date_flows) == 2
            and all(row["session_uses_operation_date_output"] for row in automatic_date_flows)
        ),
        "ui_gate_can_open_operation_date_form_and_disable_toolbar": (
            "VN.SDS.Core.Helper.MdiManager.ShowForm" in ui_members
            and "System.Windows.Forms.Control.set_Enabled" in ui_members
        ),
        "setup_uses_session_sale_operation_date": "Application.BaseData.UserSessionInfo.get_OperationdDate_Sale"
        in setup_members,
        "both_conversion_routes_use_session_operation_date_as_create_sale_date": all(
            "Application.BaseData.UserSessionInfo.get_OperationdDate_Sale" in members
            and "VN.SDS.Common.Sales.EntityHelper.OrderToSale.CreateSaleByOrderHelper.set_CreateSaleDate" in members
            for members in (old_members, v2_members)
        ),
        "assemblies_were_not_loaded_or_executed": True,
    }
    return {
        "artifact": "varanegar_order_sale_operation_date_runtime",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if all(assertions.values()) else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "database_connections": 0,
            "form_or_application_command_executions": 0,
            "raw_non_allowlisted_strings_or_business_values_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "source_hash_mismatch_count": sum(not row["inventory_sha256_match"] for row in sources),
            "method_or_coverage_error_count": len(errors),
        },
        "contract": {
            "set_operation_date_permission_resource": "VN.SDS.Sales",
            "set_operation_date_permission_action": "SetOprDate",
            "conversion_create_date_source": "USER_SESSION_OPERATION_DATE_SALE",
            "fetch_reason_two_output_order": ["LAST_DATE", "OPERATION_DATE"],
            "automatic_session_operation_date_source": "FETCH_REASON_TWO_OPERATION_DATE_SECOND_OUTPUT",
            "automatic_date_flows": automatic_date_flows,
            "ui_gate_rejection_effect": "DISABLE_FORM_TOOLBAR_OR_REQUIRE_OPERATION_DATE_FORM",
            "operation_date_permission_is_conversion_permission": False,
            "server_command_revalidates_actor_set_operation_date_permission": False,
        },
        "assertions": assertions,
        "errors": errors,
        "methods": methods,
        "limits": [
            "Static IL proves the selected desktop gate and value flow, not the effective permission of any identity.",
            "The permission controls changing the session operation date, not authorization to convert an order.",
            "Server-side revalidation of operation date against every final command branch is not proven by this UI/business artifact.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    artifact = collect(args.source_directory, args.binary_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
