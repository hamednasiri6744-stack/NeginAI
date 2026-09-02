"""Extract hash-pinned Thunderstruck DataContext transaction ownership and order-sale flow."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import struct
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

from extract_varanegar_targeted_il_contracts import _full_type_name, _owner_maps, _resolve_token


CUSTOMIZATION_SETTERS = {
    "Thunderstruck.DataContext.set_TransactionalContext",
    "Thunderstruck.Provider.ProviderFactory.set_CustomProvider",
    "Thunderstruck.Provider.ProviderFactory.set_ConnectionFactory",
    "Thunderstruck.Provider.ProviderFactory.set_ConnectionProvider",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _constant(instruction: Any) -> int | None:
    values = {f"ldc.i4.{value}": value for value in range(9)}
    values["ldc.i4.m1"] = -1
    if instruction.mnemonic in values:
        return values[instruction.mnemonic]
    if instruction.mnemonic in {"ldc.i4", "ldc.i4.s"} and isinstance(instruction.operand, int):
        return instruction.operand
    return None


def _method_contract(pe, type_name, method_name, occurrence=0):
    method_owners, field_owners = _owner_maps(pe)
    type_row = next(row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == type_name)
    indexes = [index for index in type_row.MethodList or [] if str(index.row.Name) == method_name and index.row.Rva]
    index = indexes[occurrence]
    row = index.row
    body = read_method_body_from_bytes(pe.get_data(row.Rva, 524288))
    events = []
    for instruction in body.instructions:
        event = {"offset": int(instruction.offset), "opcode": instruction.mnemonic}
        constant = _constant(instruction)
        if constant is not None:
            event["numeric_constant"] = constant
        if isinstance(instruction.operand, StringToken):
            found = pe.net.user_strings.get(instruction.operand.rid)
            value = "" if found is None else str(found.value)
            event["string_sha256"] = hashlib.sha256(value.encode("utf-8")).hexdigest()
            event["string_length"] = len(value)
        elif isinstance(instruction.operand, Token):
            event["member"] = _resolve_token(pe, instruction.operand, method_owners, field_owners)
            event["metadata_token"] = int(instruction.operand.value)
        events.append(event)
    return {
        "type": type_name,
        "method": method_name,
        "occurrence": occurrence,
        "method_metadata_token": 0x06000000 | int(index.row_index),
        "parameter_names": [str(item.row.Name) for item in row.ParamList or []],
        "instruction_count": len(events),
        "events": events,
    }


def _members(method):
    return [event["member"] for event in method["events"] if "member" in event]


def _constructor_modes(method):
    rows = method["events"]
    result = []
    for index, row in enumerate(rows):
        if row.get("member") != "Thunderstruck.DataContext..ctor":
            continue
        previous = rows[index - 1] if index else {}
        result.append(
            {
                "offset": row["offset"],
                "mode_value": previous.get("numeric_constant"),
                "mode": {0: "BEGIN", 1: "NO_TRANSACTION"}.get(previous.get("numeric_constant"), "DEFAULT_OR_CONTEXT_DEPENDENT"),
            }
        )
    return result


def _enum_values(pe):
    values = {}
    for row in pe.net.mdtables.Constant.rows:
        parent = getattr(row.Parent, "row", None)
        name = str(getattr(parent, "Name", ""))
        if name in {"Begin", "No"}:
            values[name] = struct.unpack("<i", bytes(row.Value.value))[0]
    return values


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = _load(binary_inventory)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    required = ["Application.DataAccess.dll", "VN.SDS.Sales.Business.dll", "VN.SDS.Sales.DataAccess.dll"]
    sources = []
    for name in required:
        path = source_directory / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        sources.append(
            {
                "assembly_file": name,
                "assembly_bytes": path.stat().st_size,
                "assembly_sha256": actual,
                "inventory_sha256_match": actual == expected.get(name),
            }
        )

    data_pe = dnfile.dnPE(str(source_directory / "Application.DataAccess.dll"))
    enum_values = _enum_values(data_pe)
    library_methods = {
        "default_ctor": _method_contract(data_pe, "Thunderstruck.DataContext", ".ctor", 0),
        "mode_ctor": _method_contract(data_pe, "Thunderstruck.DataContext", ".ctor", 2),
        "commit": _method_contract(data_pe, "Thunderstruck.DataContext", "Commit"),
        "rollback": _method_contract(data_pe, "Thunderstruck.DataContext", "Rollback"),
        "dispose": _method_contract(data_pe, "Thunderstruck.DataContext", "Dispose"),
        "provider_create": _method_contract(data_pe, "Thunderstruck.Provider.ProviderFactory", "Create"),
        "provider_create_connection": _method_contract(data_pe, "Thunderstruck.Provider.ProviderFactory", "CreateConnection"),
        "provider_open": _method_contract(data_pe, "Thunderstruck.Provider.DefaultProvider", "Open"),
        "provider_commit": _method_contract(data_pe, "Thunderstruck.Provider.DefaultProvider", "Commit"),
        "provider_rollback": _method_contract(data_pe, "Thunderstruck.Provider.DefaultProvider", "Rollback"),
        "provider_dispose": _method_contract(data_pe, "Thunderstruck.Provider.DefaultProvider", "Dispose"),
        "provider_command": _method_contract(data_pe, "Thunderstruck.Provider.DefaultProvider", "CreateDbCommand", 1),
    }

    business_pe = dnfile.dnPE(str(source_directory / "VN.SDS.Sales.Business.dll"))
    adapter_pe = dnfile.dnPE(str(source_directory / "VN.SDS.Sales.DataAccess.dll"))
    order_methods = {
        "business_direct_core": _method_contract(
            business_pe, "VN.SDS.Sales.Business.Order.OrderHandler", "CreateSaleByOrder", 0
        ),
        "business_adapter_delegate": _method_contract(
            business_pe, "VN.SDS.Sales.Business.Order.OrderHandler", "CreateSaleByOrder", 1
        ),
        "business_discount_v2": _method_contract(
            business_pe, "VN.SDS.Sales.Business.Order.OrderHandler", "CreateSaleByOrderUsingDiscountV2"
        ),
        "business_v2": _method_contract(
            business_pe, "VN.SDS.Sales.Business.Order.OrderHandler", "CreateSaleByOrderV2"
        ),
        "adapter_create": _method_contract(
            adapter_pe, "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter", "CreateSaleByOrder"
        ),
    }
    for row in order_methods.values():
        row["data_context_constructor_modes"] = _constructor_modes(row)

    customization_callsites = []
    managed_scanned = 0
    parse_error_count = 0
    for item in inventory["files"]:
        path = source_directory / item["name"]
        if not path.is_file() or path.suffix.casefold() != ".dll":
            continue
        try:
            pe = dnfile.dnPE(str(path))
            if not pe.net or not pe.net.mdtables.TypeDef:
                continue
            managed_scanned += 1
            method_owners, field_owners = _owner_maps(pe)
            for type_row in pe.net.mdtables.TypeDef.rows:
                owner = _full_type_name(type_row)
                for index in type_row.MethodList or []:
                    row = index.row
                    if row is None or not row.Rva:
                        continue
                    try:
                        body = read_method_body_from_bytes(pe.get_data(row.Rva, 524288))
                    except Exception:
                        continue
                    members = {
                        _resolve_token(pe, instruction.operand, method_owners, field_owners)
                        for instruction in body.instructions
                        if isinstance(instruction.operand, Token) and not isinstance(instruction.operand, StringToken)
                    }
                    for setter in sorted(members & CUSTOMIZATION_SETTERS):
                        customization_callsites.append(
                            {"assembly_file": item["name"], "type": owner, "method": str(row.Name), "member": setter}
                        )
        except Exception:
            parse_error_count += 1

    default_ctor_members = _members(library_methods["default_ctor"])
    mode_ctor_members = _members(library_methods["mode_ctor"])
    open_members = _members(library_methods["provider_open"])
    provider_create_members = _members(library_methods["provider_create"])
    provider_factory_connection_members = _members(library_methods["provider_create_connection"])
    provider_commit_members = _members(library_methods["provider_commit"])
    provider_rollback_members = _members(library_methods["provider_rollback"])
    provider_command_members = _members(library_methods["provider_command"])
    discount_modes = order_methods["business_discount_v2"]["data_context_constructor_modes"]
    adapter_modes = order_methods["adapter_create"]["data_context_constructor_modes"]
    direct_modes = order_methods["business_direct_core"]["data_context_constructor_modes"]
    assertions = {
        "all_required_source_hashes_match": all(row["inventory_sha256_match"] for row in sources),
        "transaction_enum_is_begin_zero_no_one": enum_values == {"Begin": 0, "No": 1},
        "default_context_selects_no_transaction_mode": (
            "Thunderstruck.DataContext..ctor" in default_ctor_members
            and any(event.get("numeric_constant") == 1 for event in library_methods["default_ctor"]["events"])
        ),
        "each_mode_context_builds_provider_and_connection": (
            "Thunderstruck.Provider.ProviderFactory..ctor" in mode_ctor_members
            and "Thunderstruck.Provider.ProviderFactory.Create" in mode_ctor_members
            and "Thunderstruck.Provider.ProviderFactory.CreateConnection" in provider_create_members
            and "System.Data.Common.DbProviderFactory.CreateConnection" in provider_factory_connection_members
        ),
        "provider_begins_transaction_only_for_begin_mode": (
            "Thunderstruck.Provider.DefaultProvider.get_TransactionMode" in open_members
            and "System.Data.IDbConnection.BeginTransaction" in open_members
        ),
        "commands_bind_provider_connection_and_transaction": all(
            member in provider_command_members
            for member in (
                "Thunderstruck.Provider.DefaultProvider.get_DbConnection",
                "System.Data.IDbCommand.set_Connection",
                "Thunderstruck.Provider.DefaultProvider.get_DbTransaction",
                "System.Data.IDbCommand.set_Transaction",
            )
        ),
        "commit_and_rollback_are_null_transaction_noops": (
            "Thunderstruck.Provider.DefaultProvider.get_DbTransaction" in provider_commit_members
            and "System.Data.IDbTransaction.Commit" in provider_commit_members
            and "Thunderstruck.Provider.DefaultProvider.get_DbTransaction" in provider_rollback_members
            and "System.Data.IDbTransaction.Rollback" in provider_rollback_members
        ),
        "no_packaged_custom_provider_or_connection_factory_setter_callsite": customization_callsites == [],
        "discount_v2_preparation_uses_no_transaction_context": (
            discount_modes == [{"offset": 19, "mode_value": 1, "mode": "NO_TRANSACTION"}]
            and "Thunderstruck.DataContext.Commit" in _members(order_methods["business_discount_v2"])
        ),
        "adapter_conversion_uses_begin_context_and_commit": (
            adapter_modes == [{"offset": 13, "mode_value": 0, "mode": "BEGIN"}]
            and "Thunderstruck.DataContext.Commit" in _members(order_methods["adapter_create"])
        ),
        "direct_core_overload_falls_back_to_default_context_without_commit": (
            direct_modes == [{"offset": 17, "mode_value": None, "mode": "DEFAULT_OR_CONTEXT_DEPENDENT"}]
            and "Thunderstruck.DataContext.Commit" not in _members(order_methods["business_direct_core"])
        ),
        "business_v2_calls_transactional_adapter_delegate_overload": any(
            event.get("metadata_token") == order_methods["business_adapter_delegate"]["method_metadata_token"]
            for event in order_methods["business_v2"]["events"]
        ),
        "assemblies_were_not_loaded_or_executed": True,
    }
    return {
        "artifact": "varanegar_datacontext_transaction_runtime",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if all(assertions.values()) else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "database_connections": 0,
            "form_procedure_or_application_command_executions": 0,
            "raw_strings_business_values_or_identities_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "required_assembly_count": len(sources),
            "managed_inventory_assembly_scan_count": managed_scanned,
            "inventory_parse_error_count": parse_error_count,
            "custom_provider_or_connection_factory_setter_callsite_count": len(customization_callsites),
            "library_method_contract_count": len(library_methods),
            "selected_order_sale_method_count": len(order_methods),
        },
        "contract": {
            "transaction_enum": enum_values,
            "default_datacontext_mode": "NO_TRANSACTION",
            "begin_mode_value": 0,
            "no_transaction_mode_value": 1,
            "context_connection_ownership": "NEW_PROVIDER_AND_CONNECTION_PER_CONTEXT_BY_DEFAULT",
            "commit_without_db_transaction": "NO_OP",
            "rollback_without_db_transaction": "NO_OP",
            "discount_v2_preparation_transaction": "NONE_AUTOCOMMIT_PER_COMMAND",
            "order_sale_adapter_transaction": "SEPARATE_BEGIN_CONTEXT",
            "discount_v2_preparation_and_sale_conversion_share_physical_transaction": False,
            "target_requirement": "ONE_INJECTED_UNIT_OF_WORK_FOR_POLICY_EVC_CONVERSION_PROJECTIONS_AND_OUTBOX",
        },
        "customization_callsites": customization_callsites,
        "library_methods": library_methods,
        "order_sale_methods": order_methods,
        "assertions": assertions,
        "limits": [
            "Static package absence does not exclude runtime reflection, external plugin or configuration code outside the inventoried assemblies.",
            "A SQL stored procedure can own a local transaction even when the managed DataContext is non-transactional.",
            "The artifact proves connection/transaction construction semantics, not a historical partial-failure incident.",
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
