"""Extract hash-pinned static IL for order-to-sale conversion routes."""

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


TARGETS = {
    "VN.SDS.Sales.UI.dll": {
        "VN.SDS.Sales.UI.Sale.FormSaleDataEntry": {"SaveCommand"}
    },
    "VN.SDS.Sales.Business.dll": {
        "VN.SDS.Sales.Business.Sale.SaleHandler": {"OrderToSaleSaveCommand"},
        "VN.SDS.Sales.Business.Order.OrderHandler": {"CreateSaleByOrder"},
    },
    "VN.SDS.Sales.DataAccess.dll": {
        "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter": {"CreateSaleByOrder"}
    },
}

SAFE_MEMBERS = {
    "Thunderstruck.DataContext..ctor",
    "Thunderstruck.DataContext.Execute",
    "Thunderstruck.DataContext.Query",
    "Thunderstruck.DataContext.Commit",
    "Thunderstruck.DataContext.RollBack",
    "Thunderstruck.DataContext.Dispose",
    "VN.SDS.Sales.Business.Sale.SaleHandler.OrderToSaleSaveCommand",
    "VN.SDS.Sales.Business.Order.OrderHandler.CreateSaleByOrder",
    "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter.CreateSaleByOrder",
}

PROCEDURE_SIGNALS = {"SLE.usp_CreateSaleByOrder", "SLE.usp_sdsnet_CreateSaleByOrder"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _method(
    pe: dnfile.dnPE,
    assembly: str,
    owner: str,
    index: Any,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
) -> dict[str, Any]:
    row = index.row
    body = read_method_body_from_bytes(pe.get_data(row.Rva, 524288))
    events: list[dict[str, Any]] = []
    procedures: set[str] = set()
    literals: list[dict[str, Any]] = []
    for instruction in body.instructions:
        operand = instruction.operand
        if isinstance(operand, StringToken):
            item = pe.net.user_strings.get(operand.rid)
            value = "" if item is None else str(item.value)
            compact = " ".join(value.replace("[", "").replace("]", "").split())
            for procedure in PROCEDURE_SIGNALS:
                if procedure.casefold() in compact.casefold():
                    procedures.add(procedure)
            literals.append(
                {
                    "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                    "length": len(value),
                    "raw_value_persisted": False,
                }
            )
        elif isinstance(operand, Token):
            member = _resolve_token(pe, operand, method_owners, field_owners)
            if member in SAFE_MEMBERS or "WithOutRollback" in member:
                events.append(
                    {
                        "offset": int(instruction.offset),
                        "opcode": instruction.mnemonic,
                        "member": member,
                    }
                )
    return {
        "assembly_file": assembly,
        "type": owner,
        "method": str(row.Name),
        "instruction_count": len(body.instructions),
        "has_exception_regions": bool(body.exception_handlers),
        "event_ledger": events,
        "procedure_name_signals": sorted(procedures),
        "literal_fingerprints": literals,
    }


def _offsets(method: dict[str, Any] | None, member: str) -> list[int]:
    if method is None:
        return []
    return [row["offset"] for row in method["event_ledger"] if row["member"] == member]


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = _load(binary_inventory)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    sources: list[dict[str, Any]] = []
    methods: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for assembly, type_targets in TARGETS.items():
        path = source_directory / assembly
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        match = actual == expected.get(assembly)
        sources.append(
            {
                "assembly_file": assembly,
                "assembly_bytes": path.stat().st_size,
                "assembly_sha256": actual,
                "inventory_sha256_match": match,
            }
        )
        if not match:
            errors.append({"assembly_file": assembly, "error": "inventory hash mismatch"})
        pe = dnfile.dnPE(str(path))
        method_owners, field_owners = _owner_maps(pe)
        types = {_full_type_name(row): row for row in pe.net.mdtables.TypeDef.rows}
        for owner, selected in type_targets.items():
            type_row = types.get(owner)
            if type_row is None:
                errors.append({"assembly_file": assembly, "type": owner, "error": "type absent"})
                continue
            found: set[str] = set()
            for index in type_row.MethodList or []:
                row = index.row
                if row is None or not row.Rva or str(row.Name) not in selected:
                    continue
                found.add(str(row.Name))
                try:
                    methods.append(_method(pe, assembly, owner, index, method_owners, field_owners))
                except Exception as exc:
                    errors.append(
                        {
                            "assembly_file": assembly,
                            "type": owner,
                            "method": str(row.Name),
                            "error": type(exc).__name__,
                        }
                    )
            for missing in selected - found:
                errors.append(
                    {"assembly_file": assembly, "type": owner, "method": missing, "error": "method absent"}
                )

    ui_type = "VN.SDS.Sales.UI.Sale.FormSaleDataEntry"
    sale_business_type = "VN.SDS.Sales.Business.Sale.SaleHandler"
    order_business_type = "VN.SDS.Sales.Business.Order.OrderHandler"
    adapter_type = "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter"

    def selected(owner: str, name: str) -> list[dict[str, Any]]:
        return [row for row in methods if row["type"] == owner and row["method"] == name]

    ui = selected(ui_type, "SaveCommand")
    sale_business = selected(sale_business_type, "OrderToSaleSaveCommand")
    order_business = selected(order_business_type, "CreateSaleByOrder")
    adapter = selected(adapter_type, "CreateSaleByOrder")
    if not (len(ui) == 1 and len(sale_business) == 1 and len(order_business) == 2 and len(adapter) == 1):
        errors.append({"error": "selected runtime overload coverage incomplete"})
    ui_method = ui[0] if len(ui) == 1 else None
    sale_method = sale_business[0] if len(sale_business) == 1 else None
    adapter_method = adapter[0] if len(adapter) == 1 else None
    order_delegate = next(
        (
            row
            for row in order_business
            if _offsets(row, "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter.CreateSaleByOrder")
        ),
        None,
    )
    order_other = next((row for row in order_business if row is not order_delegate), None)

    def ordered(method: dict[str, Any] | None, before: str, after: str) -> bool:
        left, right = _offsets(method, before), _offsets(method, after)
        return bool(left and right and min(left) < max(right))

    ui_call = "VN.SDS.Sales.Business.Sale.SaleHandler.OrderToSaleSaveCommand"
    order_call = "VN.SDS.Sales.Business.Order.OrderHandler.CreateSaleByOrder"
    adapter_call = "VN.SDS.Sales.DataAccess.DataAdapter.Order.OrderAdapter.CreateSaleByOrder"
    with_out_events = [
        event
        for row in methods
        for event in row["event_ledger"]
        if "WithOutRollback" in event["member"]
    ]
    contract = {
        "ui_save_delegates_without_explicit_context_commit_or_rollback": bool(
            _offsets(ui_method, ui_call)
            and not _offsets(ui_method, "Thunderstruck.DataContext..ctor")
            and not _offsets(ui_method, "Thunderstruck.DataContext.Commit")
            and not _offsets(ui_method, "Thunderstruck.DataContext.RollBack")
        ),
        "sale_business_constructs_context_calls_create_then_commits": bool(
            ordered(sale_method, "Thunderstruck.DataContext..ctor", order_call)
            and ordered(sale_method, order_call, "Thunderstruck.DataContext.Commit")
        ),
        "sale_business_has_explicit_rollback_signal": bool(
            _offsets(sale_method, "Thunderstruck.DataContext.RollBack")
        ),
        "order_business_has_two_overloads_and_one_thin_adapter_delegate": len(order_business) == 2
        and order_delegate is not None and order_other is not None,
        "adapter_uses_named_orchestrator_and_commits": bool(
            adapter_method
            and "SLE.usp_sdsnet_CreateSaleByOrder" in adapter_method["procedure_name_signals"]
            and (_offsets(adapter_method, "Thunderstruck.DataContext.Query")
                 or _offsets(adapter_method, "Thunderstruck.DataContext.Execute"))
            and _offsets(adapter_method, "Thunderstruck.DataContext.Commit")
        ),
        "with_out_rollback_helper_member_is_referenced": bool(with_out_events),
        "selected_methods_have_nested_business_and_adapter_commit_signals": bool(
            _offsets(sale_method, "Thunderstruck.DataContext.Commit")
            and _offsets(adapter_method, "Thunderstruck.DataContext.Commit")
        ),
        "normal_ui_to_business_route_selection_proven": bool(_offsets(ui_method, ui_call)),
        "with_out_rollback_runtime_value_and_branch_proven": False,
        "physical_transaction_enlistment_across_business_and_adapter_contexts_proven": False,
    }
    return {
        "artifact": "varanegar_sale_conversion_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "application_endpoint_form_or_command_executions": 0,
            "database_connections": 0,
            "configuration_order_sale_customer_goods_user_or_host_values_read": 0,
            "raw_string_sql_or_identifier_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "order_business_create_overload_count": len(order_business),
            "source_hash_mismatch_count": sum(not row["inventory_sha256_match"] for row in sources),
            "method_or_coverage_error_count": len(errors),
        },
        "managed_conversion_contract": contract,
        "method_contracts": methods,
        "errors": errors,
        "evidence_limits": [
            "Linear IL proves selected call ordering, not branch-specific execution, runtime frequency or successful effects.",
            "Both the business orchestrator and adapter show Commit signals; shared physical connection and transaction enlistment are not inferred.",
            "The WithOutRollback helper member can be located, but its effective runtime value and SQL branch are not proven by this scoped extraction.",
            "Procedure-name presence is allowlisted metadata derived from literals; raw SQL, parameters and identifiers are not persisted.",
            "Assemblies were never loaded or executed and no configuration or business value was read.",
        ],
    }


def main() -> int:
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect(args.source_directory, args.binary_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(json.dumps(payload["managed_conversion_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
