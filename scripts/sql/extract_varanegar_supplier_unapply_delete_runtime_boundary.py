"""Extract hash-pinned static IL for supplier invoice unlink/delete paths."""

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
    "VN.SDS.Stock.UI.dll": {
        "VN.SDS.Stock.UI.SupInvoice.FormSupInvoiceList": {"DeleteCommand"},
        "VN.SDS.Stock.UI.SupInvoice.FormSupInvoiceDataEntry": {"DeleteCommand"},
    },
    "VN.SDS.Stock.Business.dll": {
        "VN.SDS.Stock.Business.SupInvInvoiceRelation.SupInvInvoiceRelationHandler": {
            "Unlink"
        },
    },
    "VN.SDS.Stock.DataAccess.dll": {
        "VN.SDS.Stock.DataAccess.DataAdapter.SupInvInvoiceRelation.SupInvInvoiceRelationAdapter": {
            "LinkUnlinkSupInvoiceInv"
        },
    },
}

SAFE_MEMBERS = {
    "Thunderstruck.DataContext..ctor",
    "Thunderstruck.DataContext.Execute",
    "Thunderstruck.DataContext.Commit",
    "Thunderstruck.DataContext.Dispose",
    "TypeSpecRow.SaveCommand",
    "Application.BaseData.UserSessionInfo.get_LastClosedDate_Buy",
    "VN.SDS.Stock.Business.SupInvoice.SupInvoiceHdrHandler.GetSupInvoiceSupSettlementNos",
    "VN.SDS.Stock.DataAccess.DataAdapter.SupInvInvoiceRelation.SupInvInvoiceRelationAdapter.LinkUnlinkSupInvoiceInv",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _method_contract(
    pe: dnfile.dnPE,
    assembly: str,
    owner: str,
    method_index: Any,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
) -> dict[str, Any]:
    method = method_index.row
    body = read_method_body_from_bytes(pe.get_data(method.Rva, 131072))
    events = []
    literals = []
    constants = []
    for instruction in body.instructions:
        operand = instruction.operand
        if isinstance(operand, StringToken):
            item = pe.net.user_strings.get(operand.rid)
            value = "" if item is None else str(item.value)
            literals.append(
                {
                    "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                    "length": len(value),
                    "raw_value_persisted": False,
                }
            )
        elif isinstance(operand, Token):
            member = _resolve_token(pe, operand, method_owners, field_owners)
            if member in SAFE_MEMBERS:
                events.append(
                    {
                        "offset": int(instruction.offset),
                        "opcode": instruction.mnemonic,
                        "member": member,
                    }
                )
        if instruction.mnemonic.startswith("ldc.i4"):
            encoded = instruction.mnemonic.removeprefix("ldc.i4.")
            value: int | None = None
            if encoded in {"0", "1", "2", "3", "4", "5", "6", "7", "8"}:
                value = int(encoded)
            elif encoded == "m1":
                value = -1
            elif instruction.mnemonic in {"ldc.i4", "ldc.i4.s"} and operand is not None:
                try:
                    value = int(operand)
                except (TypeError, ValueError):
                    value = None
            if value is not None:
                constants.append({"offset": int(instruction.offset), "value": value})
    return {
        "assembly_file": assembly,
        "type": owner,
        "method": str(method.Name),
        "parameters": [
            {"sequence": int(row.row.Sequence), "name": str(row.row.Name)}
            for row in (method.ParamList or [])
        ],
        "instruction_count": len(body.instructions),
        "has_exception_regions": bool(body.exception_handlers),
        "event_ledger": events,
        "integer_constants": constants,
        "literal_fingerprints": literals,
    }


def _events(method: dict[str, Any], member: str) -> list[int]:
    return [row["offset"] for row in method["event_ledger"] if row["member"] == member]


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = _load(binary_inventory)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    sources = []
    methods = []
    errors = []
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
            found = set()
            for method_index in type_row.MethodList or []:
                method = method_index.row
                if method is None or not method.Rva or str(method.Name) not in selected:
                    continue
                found.add(str(method.Name))
                try:
                    methods.append(
                        _method_contract(
                            pe,
                            assembly,
                            owner,
                            method_index,
                            method_owners,
                            field_owners,
                        )
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "assembly_file": assembly,
                            "type": owner,
                            "method": str(method.Name),
                            "error": type(exc).__name__,
                        }
                    )
            for missing in selected - found:
                errors.append(
                    {"assembly_file": assembly, "type": owner, "method": missing, "error": "method absent"}
                )
    by_key = {(row["type"], row["method"]): row for row in methods}
    list_delete = by_key.get(
        ("VN.SDS.Stock.UI.SupInvoice.FormSupInvoiceList", "DeleteCommand")
    )
    entry_delete = by_key.get(
        ("VN.SDS.Stock.UI.SupInvoice.FormSupInvoiceDataEntry", "DeleteCommand")
    )
    unlink = by_key.get(
        (
            "VN.SDS.Stock.Business.SupInvInvoiceRelation.SupInvInvoiceRelationHandler",
            "Unlink",
        )
    )
    adapter = by_key.get(
        (
            "VN.SDS.Stock.DataAccess.DataAdapter.SupInvInvoiceRelation.SupInvInvoiceRelationAdapter",
            "LinkUnlinkSupInvoiceInv",
        )
    )
    if not all((list_delete, entry_delete, unlink, adapter)):
        errors.append({"error": "selected runtime coverage incomplete"})

    save = [] if unlink is None else _events(unlink, "TypeSpecRow.SaveCommand")
    link = [] if unlink is None else _events(
        unlink,
        "VN.SDS.Stock.DataAccess.DataAdapter.SupInvInvoiceRelation.SupInvInvoiceRelationAdapter.LinkUnlinkSupInvoiceInv",
    )
    commit = [] if unlink is None else _events(unlink, "Thunderstruck.DataContext.Commit")
    operation_three = [] if unlink is None else [
        row["offset"] for row in unlink["integer_constants"] if row["value"] == 3
    ]
    contract = {
        "list_delete_checks_last_closed_purchase_date": bool(
            list_delete
            and _events(
                list_delete, "Application.BaseData.UserSessionInfo.get_LastClosedDate_Buy"
            )
        ),
        "list_delete_generic_save_precedes_commit_in_linear_il": bool(
            list_delete
            and _events(list_delete, "TypeSpecRow.SaveCommand")
            and _events(list_delete, "Thunderstruck.DataContext.Commit")
            and min(_events(list_delete, "TypeSpecRow.SaveCommand"))
            < min(_events(list_delete, "Thunderstruck.DataContext.Commit"))
        ),
        "list_delete_has_settlement_diagnostic_signal": bool(
            list_delete
            and _events(
                list_delete,
                "VN.SDS.Stock.Business.SupInvoice.SupInvoiceHdrHandler.GetSupInvoiceSupSettlementNos",
            )
        ),
        "entry_delete_generic_save_precedes_commit_in_linear_il": bool(
            entry_delete
            and _events(entry_delete, "TypeSpecRow.SaveCommand")
            and _events(entry_delete, "Thunderstruck.DataContext.Commit")
            and min(_events(entry_delete, "TypeSpecRow.SaveCommand"))
            < min(_events(entry_delete, "Thunderstruck.DataContext.Commit"))
        ),
        "unlink_relation_save_precedes_operation_call": bool(
            save and link and min(save) < min(link)
        ),
        "unlink_operation_code_three_precedes_operation_call": bool(
            operation_three
            and link
            and any(0 < min(link) - offset <= 16 for offset in operation_three)
        ),
        "unlink_operation_call_precedes_commit_in_linear_il": bool(
            link and commit and min(link) < min(commit)
        ),
        "unlink_adapter_data_context_execute_call_count": 0
        if adapter is None
        else len(_events(adapter, "Thunderstruck.DataContext.Execute")),
        "unlink_adapter_has_commit_signal": bool(
            adapter and _events(adapter, "Thunderstruck.DataContext.Commit")
        ),
        "generic_save_command_exact_table_mutation_semantics_proven": False,
        "branch_specific_commit_and_rollback_reachability_proven": False,
    }
    return {
        "artifact": "varanegar_supplier_unapply_delete_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "application_endpoint_form_or_command_executions": 0,
            "database_connections": 0,
            "configuration_or_business_data_reads": 0,
            "raw_string_or_sql_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "source_hash_mismatch_count": sum(
                not row["inventory_sha256_match"] for row in sources
            ),
            "method_or_coverage_error_count": len(errors),
        },
        "managed_unlink_delete_contract": contract,
        "method_contracts": methods,
        "errors": errors,
        "evidence_limits": [
            "Linear IL order does not prove branch-specific execution or exception behavior.",
            "The generic SaveCommand signal does not identify exact table mutations without its runtime entity mapping.",
            "A DataContext constructor or Commit call alone does not prove every nested SQL entry point shares one physical transaction.",
            "Only four allowlisted methods were parsed; reflection, dynamic SQL and other callers remain outside this boundary.",
            "Assemblies were never loaded or executed and no raw literal was persisted.",
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
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(json.dumps(payload["managed_unlink_delete_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
