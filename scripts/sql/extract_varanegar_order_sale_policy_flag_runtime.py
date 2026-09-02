"""Extract static caller evidence for order-to-sale policy control flags.

Assemblies are parsed as PE metadata and IL only; they are never loaded or
executed.  Persisted instruction windows contain only opcodes, numeric
constants, argument/local slots, and allowlisted member names.
"""

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
from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _full_type_name,
    _owner_maps,
    _resolve_token,
)


ASSEMBLIES = (
    "VN.SDS.Sales.UI.dll",
    "VN.SDS.Sales.Business.dll",
    "VN.SDS.Sales.DataAccess.dll",
)

FLAGS = (
    "chkNotStock",
    "chkNotCPrice",
    "chkNotPrice",
    "chkNotBedCredit",
    "chkNotAsnCredit",
    "chkNotBedCreditDealer",
    "chkNotAsnCreditDealer",
    "chkNotCheckMaxLimit",
    "IgnoreValidateExpDate",
    "WithOutRollback",
)

HELPER_PREFIX = "VN.SDS.Common.Sales.EntityHelper.OrderToSale.CreateSaleByOrderHelper."
ROUTE_MARKERS = (
    "VN.SDS.Sales.Business.Sale.SaleHandler.OrderToSaleSaveCommand",
    "VN.SDS.Sales.Business.Order.OrderHandler.CreateSaleByOrder",
    "VN.SDS.Sales.Business.Order.OrderHandler.CreateSaleByOrderV2",
    "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter.CreateSaleByOrder",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_relevant(member: str) -> bool:
    return member in ROUTE_MARKERS or (
        member.startswith(HELPER_PREFIX) and any(flag in member for flag in FLAGS)
    )


def _numeric_constant(instruction: Any) -> int | float | None:
    mnemonic = instruction.mnemonic
    shorthand = {
        "ldc.i4.m1": -1,
        "ldc.i4.0": 0,
        "ldc.i4.1": 1,
        "ldc.i4.2": 2,
        "ldc.i4.3": 3,
        "ldc.i4.4": 4,
        "ldc.i4.5": 5,
        "ldc.i4.6": 6,
        "ldc.i4.7": 7,
        "ldc.i4.8": 8,
    }
    if mnemonic in shorthand:
        return shorthand[mnemonic]
    if mnemonic in {"ldc.i4", "ldc.i4.s", "ldc.i8", "ldc.r4", "ldc.r8"}:
        operand = instruction.operand
        return operand if isinstance(operand, (int, float)) else None
    return None


def _instruction_summary(
    pe: dnfile.dnPE,
    instruction: Any,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "offset": int(instruction.offset),
        "opcode": instruction.mnemonic,
    }
    constant = _numeric_constant(instruction)
    if constant is not None:
        row["numeric_constant"] = constant
    operand = instruction.operand
    if isinstance(operand, Token) and not isinstance(operand, StringToken):
        member = _resolve_token(pe, operand, method_owners, field_owners)
        if (
            _is_relevant(member)
            or "CheckNotSaleItmStock" in member
            or "VN.SDS.Sales.UI.OrderToSale.FormOrderToSale." in member
            or any(
                keyword in member
                for keyword in (
                    "Credit",
                    "MaxLimit",
                    "CheckOrder",
                    "ValidateOrder",
                    "ValidationResult",
                )
            )
            or member.startswith("System.Convert.")
            or member.endswith(".get_Checked")
            or member.endswith(".get_EditValue")
        ):
            row["member"] = member
        else:
            row["operand_class"] = "NON_ALLOWLISTED_METADATA_TOKEN"
    elif isinstance(operand, StringToken):
        row["operand_class"] = "REDACTED_STRING_TOKEN"
    elif instruction.mnemonic.startswith(("ldarg", "ldloc", "stloc")):
        value = str(operand) if operand is not None else None
        if value and len(value) <= 24:
            row["slot"] = value
    return row


def _value_source(window: list[dict[str, Any]], target_member: str) -> dict[str, Any]:
    target_index = next(
        (index for index, row in enumerate(window) if row.get("member") == target_member),
        len(window),
    )
    preceding = window[:target_index]
    if preceding and preceding[-1].get("numeric_constant") is not None:
        return {
            "class": "IMMEDIATE_NUMERIC_CONSTANT",
            "numeric_constant": preceding[-1]["numeric_constant"],
        }
    ui_members = [
        row["member"]
        for row in preceding
        if "member" in row
        and (
            "FormOrderToSale." in row["member"]
            or "FormSaleDataEntry.CheckNotSaleItmStock" in row["member"]
        )
    ]
    if ui_members:
        return {"class": "UI_FIELD_OR_CONTROL", "member": ui_members[-1]}
    if any(row["opcode"].startswith("ldloc") for row in preceding[-3:]):
        return {"class": "COMPUTED_LOCAL_VALUE"}
    return {"class": "STATIC_SOURCE_NOT_RESOLVED_IN_BOUNDED_WINDOW"}


def _scan_assembly(path: Path, expected_hash: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    source = {
        "assembly_file": path.name,
        "assembly_bytes": path.stat().st_size,
        "assembly_sha256": actual_hash,
        "inventory_sha256_match": actual_hash == expected_hash,
    }
    pe = dnfile.dnPE(str(path))
    method_owners, field_owners = _owner_maps(pe)
    matches: list[dict[str, Any]] = []
    for type_row in pe.net.mdtables.TypeDef.rows:
        owner = _full_type_name(type_row)
        for index in type_row.MethodList or []:
            method_row = index.row
            if method_row is None or not method_row.Rva:
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method_row.Rva, 524288))
            except Exception:
                continue
            instructions = list(body.instructions)
            relevant_indexes: list[tuple[int, str]] = []
            for offset, instruction in enumerate(instructions):
                operand = instruction.operand
                if not isinstance(operand, Token) or isinstance(operand, StringToken):
                    continue
                member = _resolve_token(pe, operand, method_owners, field_owners)
                if _is_relevant(member):
                    relevant_indexes.append((offset, member))
            if not relevant_indexes:
                continue
            events = []
            for offset, member in relevant_indexes:
                start = max(0, offset - 8)
                stop = min(len(instructions), offset + 3)
                window = [
                    _instruction_summary(pe, instruction, method_owners, field_owners)
                    for instruction in instructions[start:stop]
                ]
                events.append(
                    {
                        "member": member,
                        "value_source": _value_source(window, member)
                        if ".set_" in member
                        else None,
                        "instruction_window": window,
                    }
                )
            matches.append(
                {
                    "assembly_file": path.name,
                    "type": owner,
                    "method": str(method_row.Name),
                    "instruction_count": len(instructions),
                    "has_exception_regions": bool(body.exception_handlers),
                    "events": events,
                }
            )
    return source, matches


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = _load(binary_inventory)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    sources: list[dict[str, Any]] = []
    methods: list[dict[str, Any]] = []
    for assembly in ASSEMBLIES:
        source, found = _scan_assembly(source_directory / assembly, expected.get(assembly))
        sources.append(source)
        methods.extend(found)

    flag_events = {
        flag: [
            {
                "assembly_file": method["assembly_file"],
                "type": method["type"],
                "method": method["method"],
                "member": event["member"],
                "value_source": event["value_source"],
            }
            for method in methods
            for event in method["events"]
            if flag in event["member"]
        ]
        for flag in FLAGS
    }
    ui_save = [
        method
        for method in methods
        if method["type"] == "VN.SDS.Sales.UI.Sale.FormSaleDataEntry"
        and method["method"] == "SaveCommand"
    ]
    assertions = {
        "all_source_hashes_match": all(row["inventory_sha256_match"] for row in sources),
        "form_sale_save_command_is_covered_once": len(ui_save) == 1,
        "form_sale_save_sets_stock_cprice_and_price_flags": bool(
            ui_save
            and all(
                any(flag in event["member"] for event in ui_save[0]["events"])
                for flag in ("chkNotStock", "chkNotCPrice", "chkNotPrice")
            )
        ),
        "runtime_route_markers_are_observed": all(
            any(event["member"] == marker for method in methods for event in method["events"])
            for marker in ROUTE_MARKERS
        ),
        "assemblies_were_not_loaded_or_executed": True,
    }
    return {
        "artifact": "varanegar_order_sale_policy_flag_runtime",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if all(assertions.values()) else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "database_connections": 0,
            "application_form_or_command_executions": 0,
            "raw_strings_or_business_values_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "matched_method_count": len(methods),
            "matched_event_count": sum(len(method["events"]) for method in methods),
            "flag_with_runtime_member_reference_count": sum(bool(rows) for rows in flag_events.values()),
            "flag_without_runtime_member_reference_count": sum(not rows for rows in flag_events.values()),
            "source_hash_mismatch_count": sum(not row["inventory_sha256_match"] for row in sources),
        },
        "flag_event_index": flag_events,
        "assertions": assertions,
        "methods": methods,
        "limits": [
            "Static IL proves member assignment and routing, not the runtime value for every branch.",
            "No claim is made that an unobserved helper member is unreachable from reflection or another assembly.",
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
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
