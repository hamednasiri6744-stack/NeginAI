"""Extract hash-pinned managed sale-cancellation call and commit boundaries."""

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
        "VN.SDS.Sales.UI.Sale.FormSaleList": {"CancelCommand", "CheckCancelPermission"},
    },
    "VN.SDS.Sales.Business.dll": {
        "VN.SDS.Sales.Business.Sale.SaleHandler": {"CancelSale"},
    },
    "VN.SDS.Sales.DataAccess.dll": {
        "VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter": {"CancelSale"},
    },
}

SAFE_MEMBERS = {
    "Thunderstruck.DataContext..ctor",
    "Thunderstruck.DataContext.Execute",
    "Thunderstruck.DataContext.Query",
    "Thunderstruck.DataContext.Commit",
    "Thunderstruck.DataContext.RollBack",
    "Thunderstruck.DataContext.Dispose",
    "VN.SDS.Sales.UI.Sale.FormSaleList.CheckCancelPermission",
    "VN.SDS.Sales.UI.Sale.FormCancelReason..ctor",
    "VN.SDS.MainData.IBusiness.OprDate.IOprDateHandler.CheckSetOprDate",
    "VN.SDS.Sales.Business.Sale.SaleHandler.CancelSale",
    "VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter.CancelSale",
}
PROCEDURE_SIGNALS = {"dbo.usp_sdsnet_Sale_Cancel"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _method(pe: dnfile.dnPE, assembly: str, owner: str, index: Any,
            method_owners: dict[int, str], field_owners: dict[int, str]) -> dict[str, Any]:
    body = read_method_body_from_bytes(pe.get_data(index.row.Rva, 524288))
    events, literals, procedures = [], [], set()
    for instruction in body.instructions:
        operand = instruction.operand
        if isinstance(operand, StringToken):
            item = pe.net.user_strings.get(operand.rid)
            value = "" if item is None else str(item.value)
            compact = " ".join(value.replace("[", "").replace("]", "").split())
            for procedure in PROCEDURE_SIGNALS:
                if procedure.casefold() in compact.casefold():
                    procedures.add(procedure)
            literals.append({"sha256": hashlib.sha256(value.encode()).hexdigest(),
                             "length": len(value), "raw_value_persisted": False})
        elif isinstance(operand, Token):
            member = _resolve_token(pe, operand, method_owners, field_owners)
            if member in SAFE_MEMBERS:
                events.append({"offset": int(instruction.offset), "opcode": instruction.mnemonic,
                               "member": member})
    return {
        "assembly_file": assembly, "type": owner, "method": str(index.row.Name),
        "instruction_count": len(body.instructions),
        "has_exception_regions": bool(body.exception_handlers), "event_ledger": events,
        "procedure_name_signals": sorted(procedures), "literal_fingerprints": literals,
    }


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    expected = {row["name"]: row["sha256"] for row in _load(binary_inventory)["files"]}
    sources, methods, errors = [], [], []
    for assembly, type_targets in TARGETS.items():
        path = source_directory / assembly
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        matched = actual == expected.get(assembly)
        sources.append({"assembly_file": assembly, "assembly_bytes": path.stat().st_size,
                        "assembly_sha256": actual, "inventory_sha256_match": matched})
        if not matched:
            errors.append({"assembly_file": assembly, "error": "inventory hash mismatch"})
        pe = dnfile.dnPE(str(path))
        method_owners, field_owners = _owner_maps(pe)
        types = {_full_type_name(row): row for row in pe.net.mdtables.TypeDef.rows}
        for owner, selected in type_targets.items():
            type_row = types.get(owner)
            if type_row is None:
                errors.append({"assembly_file": assembly, "type": owner, "error": "type absent"})
                continue
            found = set()
            for index in type_row.MethodList or []:
                row = index.row
                if row is None or not row.Rva or str(row.Name) not in selected:
                    continue
                found.add(str(row.Name))
                try:
                    methods.append(_method(pe, assembly, owner, index, method_owners, field_owners))
                except Exception as exc:
                    errors.append({"assembly_file": assembly, "type": owner,
                                   "method": str(row.Name), "error": type(exc).__name__})
            for missing in selected - found:
                errors.append({"assembly_file": assembly, "type": owner,
                               "method": missing, "error": "method absent"})

    def chosen(owner: str, name: str) -> list[dict[str, Any]]:
        return [row for row in methods if row["type"] == owner and row["method"] == name]

    def offsets(method: dict[str, Any] | None, member: str) -> list[int]:
        return [] if method is None else [e["offset"] for e in method["event_ledger"] if e["member"] == member]

    ui_type = "VN.SDS.Sales.UI.Sale.FormSaleList"
    business_type = "VN.SDS.Sales.Business.Sale.SaleHandler"
    adapter_type = "VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter"
    ui_cancel = chosen(ui_type, "CancelCommand")
    ui_permission = chosen(ui_type, "CheckCancelPermission")
    business = chosen(business_type, "CancelSale")
    adapter = chosen(adapter_type, "CancelSale")
    if not all(len(rows) == 1 for rows in (ui_cancel, ui_permission, business, adapter)):
        errors.append({"error": "selected runtime method coverage incomplete"})
    u = ui_cancel[0] if len(ui_cancel) == 1 else None
    p = ui_permission[0] if len(ui_permission) == 1 else None
    b = business[0] if len(business) == 1 else None
    a = adapter[0] if len(adapter) == 1 else None
    context = "Thunderstruck.DataContext..ctor"
    commit = "Thunderstruck.DataContext.Commit"
    rollback = "Thunderstruck.DataContext.RollBack"
    business_call = "VN.SDS.Sales.Business.Sale.SaleHandler.CancelSale"
    adapter_call = "VN.SDS.Sales.DataAccess.DataAdapter.Sale.SaleAdapter.CancelSale"
    contract = {
        "ui_cancel_checks_permission_and_operation_date_then_calls_business": bool(
            offsets(u, "VN.SDS.Sales.UI.Sale.FormSaleList.CheckCancelPermission")
            and offsets(u, "VN.SDS.MainData.IBusiness.OprDate.IOprDateHandler.CheckSetOprDate")
            and offsets(u, business_call)),
        "ui_cancel_collects_cancel_reason_before_business_call": bool(
            offsets(u, "VN.SDS.Sales.UI.Sale.FormCancelReason..ctor") and offsets(u, business_call)
            and min(offsets(u, "VN.SDS.Sales.UI.Sale.FormCancelReason..ctor")) < max(offsets(u, business_call))),
        "ui_cancel_has_no_explicit_context_commit_or_rollback": bool(
            u and not offsets(u, context) and not offsets(u, commit) and not offsets(u, rollback)),
        "business_is_thin_adapter_delegate_without_explicit_context": bool(
            offsets(b, adapter_call) and not offsets(b, context) and not offsets(b, commit) and not offsets(b, rollback)),
        "adapter_uses_named_cancel_procedure": bool(a and "dbo.usp_sdsnet_Sale_Cancel" in a["procedure_name_signals"]),
        "adapter_constructs_context_and_queries_or_executes": bool(
            offsets(a, context) and (offsets(a, "Thunderstruck.DataContext.Query")
                                     or offsets(a, "Thunderstruck.DataContext.Execute"))),
        "adapter_has_explicit_commit_signal": bool(offsets(a, commit)),
        "adapter_has_explicit_rollback_signal": bool(offsets(a, rollback)),
        "physical_transaction_enlistment_between_managed_context_and_sql_local_transaction_proven": False,
    }
    return {
        "artifact": "varanegar_sale_cancellation_runtime_boundary", "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL", "source": sources,
        "safety": {"mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
                   "assembly_loads_or_executions": 0, "application_form_or_command_executions": 0,
                   "database_connections": 0, "configuration_sale_order_customer_user_or_host_values_read": 0,
                   "raw_string_sql_or_identifier_literals_persisted": 0, "source_or_target_state_changed": 0},
        "summary": {"assembly_count": len(sources), "selected_method_count": len(methods),
                    "selected_instruction_count": sum(row["instruction_count"] for row in methods),
                    "source_hash_mismatch_count": sum(not row["inventory_sha256_match"] for row in sources),
                    "method_or_coverage_error_count": len(errors)},
        "managed_cancellation_contract": contract, "method_contracts": methods, "errors": errors,
        "evidence_limits": [
            "Linear IL proves selected call presence and ordering, not branch execution or successful effects.",
            "The SQL procedure owns a local transaction, but physical enlistment with the managed DataContext is not inferred.",
            "Procedure names are allowlisted; raw literals, parameters and business identifiers are not persisted.",
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
    print(json.dumps(payload["managed_cancellation_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
