"""Extract hash-pinned static IL for stock-voucher state routes."""

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
    "VN.SDS.Stock.Business.dll": {
        "VN.SDS.Stock.Business.Vocher.VocherHdrHandler": {
            "MainConfirmVocher",
            "UpdateVocherConfirmUnonfirm",
            "UpdateVocherConfirmUnonfirmBedehkar",
            "Confirm",
            "UnConfirm",
            "ConfirmValidation",
            "GenerateRetVocher",
        }
    },
    "VN.SDS.Stock.DataAccess.dll": {
        "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter": {
            "Confirm",
            "UnConfirm",
            "ConfirmValidation",
            "GenerateRetVocher",
        }
    },
}

SAFE_MEMBERS = {
    "Thunderstruck.DataContext..ctor",
    "Thunderstruck.DataContext.Execute",
    "Thunderstruck.DataContext.Query",
    "Thunderstruck.DataContext.Commit",
    "Thunderstruck.DataContext.RollBack",
    "Thunderstruck.DataContext.Dispose",
    "VN.SDS.Stock.Business.Vocher.VocherHdrHandler.MainConfirmVocher",
    "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter.Confirm",
    "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter.UnConfirm",
    "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter.ConfirmValidation",
    "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter.GenerateRetVocher",
    "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.CheckCardexQty",
    "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.CheckOnHandQty",
    "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.CheckOnHandQtyBedehkar",
    "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.CheckStockGoodsFull",
    "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.UpdateVocherConfirmUnonfirm",
    "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.UpdateVocherConfirmUnonfirmBedehkar",
}

PROCEDURE_SIGNALS = {
    "dbo.USP_SDSNET_ConfirmVocher",
    "dbo.USP_SDSNET_UnConfirmVocher",
    "dbo.USP_SDSNET_ConfirmVocherValidation",
    "dbo.USP_SDSNET_GenerateRetVocher",
}


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
    body = read_method_body_from_bytes(pe.get_data(row.Rva, 131072))
    events = []
    literals = []
    procedure_signals = set()
    dynamic_confirm_update_signal = False
    dynamic_unconfirm_update_signal = False
    for instruction in body.instructions:
        operand = instruction.operand
        if isinstance(operand, StringToken):
            item = pe.net.user_strings.get(operand.rid)
            value = "" if item is None else str(item.value)
            for procedure in PROCEDURE_SIGNALS:
                if procedure.casefold() in value.casefold():
                    procedure_signals.add(procedure)
            compact = " ".join(value.replace("[", "").replace("]", "").casefold().split())
            if "update inv.tblvocherhdr set confirmdate" in compact:
                if "confirmdate = null" in compact or "confirmdate=null" in compact:
                    dynamic_unconfirm_update_signal = True
                else:
                    dynamic_confirm_update_signal = True
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
    return {
        "assembly_file": assembly,
        "type": owner,
        "method": str(row.Name),
        "instruction_count": len(body.instructions),
        "has_exception_regions": bool(body.exception_handlers),
        "event_ledger": events,
        "procedure_name_signals": sorted(procedure_signals),
        "dynamic_confirm_update_signal": dynamic_confirm_update_signal,
        "dynamic_unconfirm_update_signal": dynamic_unconfirm_update_signal,
        "literal_fingerprints": literals,
    }


def _offsets(method: dict[str, Any] | None, member: str) -> list[int]:
    if method is None:
        return []
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

    business_type = "VN.SDS.Stock.Business.Vocher.VocherHdrHandler"
    adapter_type = "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter"
    business = [row for row in methods if row["type"] == business_type]
    adapter = [row for row in methods if row["type"] == adapter_type]
    main_methods = [row for row in business if row["method"] == "MainConfirmVocher"]
    writer_main = next(
        (
            row
            for row in main_methods
            if _offsets(
                row,
                "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.UpdateVocherConfirmUnonfirm",
            )
        ),
        None,
    )
    validator_main = next(
        (
            row
            for row in main_methods
            if _offsets(row, "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.CheckCardexQty")
        ),
        None,
    )

    def one(rows: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
        selected = [row for row in rows if row["method"] == name]
        return selected[0] if len(selected) == 1 else None

    dynamic = one(business, "UpdateVocherConfirmUnonfirm")
    dynamic_debit = one(business, "UpdateVocherConfirmUnonfirmBedehkar")
    business_confirm = one(business, "Confirm")
    business_unconfirm = one(business, "UnConfirm")
    adapter_confirm = one(adapter, "Confirm")
    adapter_unconfirm = one(adapter, "UnConfirm")
    adapter_validation = one(adapter, "ConfirmValidation")
    adapter_return = one(adapter, "GenerateRetVocher")
    required = (
        writer_main,
        validator_main,
        dynamic,
        dynamic_debit,
        business_confirm,
        business_unconfirm,
        adapter_confirm,
        adapter_unconfirm,
        adapter_validation,
        adapter_return,
    )
    if not all(required):
        errors.append({"error": "selected runtime coverage incomplete"})

    writer_update = _offsets(
        writer_main,
        "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.UpdateVocherConfirmUnonfirm",
    )
    writer_debit = _offsets(
        writer_main,
        "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.UpdateVocherConfirmUnonfirmBedehkar",
    )
    writer_commit = _offsets(writer_main, "Thunderstruck.DataContext.Commit")
    adapter_confirm_execute = _offsets(adapter_confirm, "Thunderstruck.DataContext.Execute")
    adapter_confirm_commit = _offsets(adapter_confirm, "Thunderstruck.DataContext.Commit")
    adapter_unconfirm_execute = _offsets(adapter_unconfirm, "Thunderstruck.DataContext.Execute")
    adapter_unconfirm_commit = _offsets(adapter_unconfirm, "Thunderstruck.DataContext.Commit")
    contract = {
        "main_confirm_has_separate_validation_and_writer_overloads": len(main_methods) == 2
        and writer_main is not None
        and validator_main is not None,
        "main_validator_checks_cardex_onhand_and_projection": bool(
            _offsets(
                validator_main,
                "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.CheckCardexQty",
            )
            and _offsets(
                validator_main,
                "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.CheckOnHandQty",
            )
            and _offsets(
                validator_main,
                "VN.SDS.Stock.IBusiness.Vocher.IVocherHdrHandler.CheckStockGoodsFull",
            )
        ),
        "main_writer_calls_direct_update_routes_before_commit": bool(
            writer_update
            and writer_debit
            and writer_commit
            and min(writer_update) < min(writer_commit)
            and min(writer_debit) < min(writer_commit)
        ),
        "main_writer_has_no_adapter_confirm_or_unconfirm_call": not _offsets(
            writer_main,
            "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter.Confirm",
        )
        and not _offsets(
            writer_main,
            "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter.UnConfirm",
        ),
        "direct_update_method_uses_dynamic_header_sql_without_local_commit": bool(
            dynamic
            and dynamic["dynamic_confirm_update_signal"]
            and _offsets(dynamic, "Thunderstruck.DataContext.Execute")
            and not _offsets(dynamic, "Thunderstruck.DataContext.Commit")
        ),
        "debit_update_method_executes_dynamic_sql_without_local_commit": bool(
            dynamic_debit
            and _offsets(dynamic_debit, "Thunderstruck.DataContext.Execute")
            and not _offsets(dynamic_debit, "Thunderstruck.DataContext.Commit")
        ),
        "thin_business_confirm_and_unconfirm_delegate_to_adapter": bool(
            _offsets(
                business_confirm,
                "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter.Confirm",
            )
            and _offsets(
                business_unconfirm,
                "VN.SDS.Stock.DataAccess.DataAdapter.Vocher.VocherHdrAdapter.UnConfirm",
            )
        ),
        "adapter_confirm_executes_named_procedure_then_commits": bool(
            adapter_confirm
            and "dbo.USP_SDSNET_ConfirmVocher" in adapter_confirm["procedure_name_signals"]
            and adapter_confirm_execute
            and adapter_confirm_commit
            and min(adapter_confirm_execute) < min(adapter_confirm_commit)
        ),
        "adapter_unconfirm_executes_named_procedure_then_commits": bool(
            adapter_unconfirm
            and "dbo.USP_SDSNET_UnConfirmVocher" in adapter_unconfirm["procedure_name_signals"]
            and adapter_unconfirm_execute
            and adapter_unconfirm_commit
            and min(adapter_unconfirm_execute) < min(adapter_unconfirm_commit)
        ),
        "adapter_validation_uses_named_validation_procedure": bool(
            adapter_validation
            and "dbo.USP_SDSNET_ConfirmVocherValidation"
            in adapter_validation["procedure_name_signals"]
        ),
        "selected_methods_have_no_explicit_rollback_signal": not any(
            _offsets(row, "Thunderstruck.DataContext.RollBack") for row in methods
        ),
        "main_writer_runtime_callsite_and_branch_selection_proven": False,
        "physical_transaction_enlistment_across_dynamic_and_adapter_routes_proven": False,
    }
    return {
        "artifact": "varanegar_stock_voucher_state_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "application_endpoint_form_or_command_executions": 0,
            "database_connections": 0,
            "configuration_voucher_goods_stock_supplier_document_user_or_host_values_read": 0,
            "raw_string_sql_or_identifier_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "main_confirm_overload_count": len(main_methods),
            "source_hash_mismatch_count": sum(
                not row["inventory_sha256_match"] for row in sources
            ),
            "method_or_coverage_error_count": len(errors),
        },
        "managed_state_contract": contract,
        "method_contracts": methods,
        "errors": errors,
        "evidence_limits": [
            "Linear IL proves selected call ordering, not branch-specific execution, runtime call frequency or successful effects.",
            "MainConfirmVocher has validation and writer overloads; the external runtime callsite and overload selection are not proven by this scoped extraction.",
            "Dynamic header updates and named-procedure adapters are distinct static routes; shared physical transaction enlistment is not assumed.",
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
    print(json.dumps(payload["managed_state_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
