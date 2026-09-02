"""Extract hash-pinned static IL for distribution exit issue/cancel routes."""

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
    "VN.SDS.Sales.Business.dll": {
        "VN.SDS.Sales.Business.Dist.DistHandler": {
            "BeforeRemoveExitFromDist",
            "CreateExitVocherByDist",
            "MergeGoodsExit",
            "RemoveExitFromDist",
        }
    },
    "VN.SDS.Sales.DataAccess.dll": {
        "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter": {
            "BeforeRemoveExitFromDist",
            "CreateExitVocherByDist",
            "MergeGoodsExit",
            "RemoveExitFromDist",
        }
    },
    "VN.SDS.Sales.UI.dll": {
        "VN.SDS.Sales.UI.DistManagement.FormDistManagementList": {
            "MergeGoodsExitData",
            "RemoveExitFromDist",
            "SetExitexportation",
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
    "VN.SDS.Sales.Business.Dist.DistHandler.BeforeRemoveExitFromDist",
    "VN.SDS.Sales.Business.Dist.DistHandler.CreateExitVocherByDist",
    "VN.SDS.Sales.Business.Dist.DistHandler.MergeGoodsExit",
    "VN.SDS.Sales.Business.Dist.DistHandler.RemoveExitFromDist",
    "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter.BeforeRemoveExitFromDist",
    "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter.CreateExitVocherByDist",
    "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter.MergeGoodsExit",
    "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter.RemoveExitFromDist",
}

PROCEDURE_SIGNALS = {
    "dbo.usp_CreateExitVocherByDist",
    "inv.Usp_BeforeRemoveExitFromDist",
    "inv.Usp_InsertGoodsExit_RD",
    "inv.Usp_RemoveExitFromDist",
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
    body = read_method_body_from_bytes(pe.get_data(row.Rva, 262144))
    events: list[dict[str, Any]] = []
    procedure_signals: set[str] = set()
    literal_fingerprints: list[dict[str, Any]] = []
    for instruction in body.instructions:
        operand = instruction.operand
        if isinstance(operand, StringToken):
            item = pe.net.user_strings.get(operand.rid)
            value = "" if item is None else str(item.value)
            compact = " ".join(value.replace("[", "").replace("]", "").split())
            for procedure in PROCEDURE_SIGNALS:
                if procedure.casefold() in compact.casefold():
                    procedure_signals.add(procedure)
            literal_fingerprints.append(
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
        "literal_fingerprints": literal_fingerprints,
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

    business_type = "VN.SDS.Sales.Business.Dist.DistHandler"
    adapter_type = "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter"
    ui_type = "VN.SDS.Sales.UI.DistManagement.FormDistManagementList"

    def one(owner: str, name: str) -> dict[str, Any] | None:
        selected = [row for row in methods if row["type"] == owner and row["method"] == name]
        return selected[0] if len(selected) == 1 else None

    business_create = one(business_type, "CreateExitVocherByDist")
    business_before_remove = one(business_type, "BeforeRemoveExitFromDist")
    business_remove = one(business_type, "RemoveExitFromDist")
    business_merge = one(business_type, "MergeGoodsExit")
    adapter_create = one(adapter_type, "CreateExitVocherByDist")
    adapter_before_remove = one(adapter_type, "BeforeRemoveExitFromDist")
    adapter_remove = one(adapter_type, "RemoveExitFromDist")
    adapter_merge = one(adapter_type, "MergeGoodsExit")
    ui_issue = one(ui_type, "SetExitexportation")
    ui_remove = one(ui_type, "RemoveExitFromDist")
    ui_merge = one(ui_type, "MergeGoodsExitData")
    selected = (
        business_create,
        business_before_remove,
        business_remove,
        business_merge,
        adapter_create,
        adapter_before_remove,
        adapter_remove,
        adapter_merge,
        ui_issue,
        ui_remove,
        ui_merge,
    )
    if not all(selected):
        errors.append({"error": "selected runtime coverage incomplete"})

    def delegates(method: dict[str, Any] | None, member: str) -> bool:
        return bool(_offsets(method, member))

    def ordered(method: dict[str, Any] | None, before: str, after: str) -> bool:
        left, right = _offsets(method, before), _offsets(method, after)
        return bool(left and right and min(left) < max(right))

    issue_member = "VN.SDS.Sales.Business.Dist.DistHandler.CreateExitVocherByDist"
    before_remove_member = "VN.SDS.Sales.Business.Dist.DistHandler.BeforeRemoveExitFromDist"
    remove_member = "VN.SDS.Sales.Business.Dist.DistHandler.RemoveExitFromDist"
    contract = {
        "business_methods_are_thin_adapter_delegates": all(
            (
                delegates(business_create, "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter.CreateExitVocherByDist"),
                delegates(business_before_remove, "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter.BeforeRemoveExitFromDist"),
                delegates(business_remove, "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter.RemoveExitFromDist"),
                delegates(business_merge, "VN.SDS.Sales.DataAccess.DataAdapter.Dist.DistAdapter.MergeGoodsExit"),
            )
        ),
        "create_adapter_queries_named_procedure_without_local_commit": bool(
            adapter_create
            and "dbo.usp_CreateExitVocherByDist" in adapter_create["procedure_name_signals"]
            and _offsets(adapter_create, "Thunderstruck.DataContext.Query")
            and not _offsets(adapter_create, "Thunderstruck.DataContext.Commit")
        ),
        "remove_validation_adapter_queries_named_procedure_without_local_commit": bool(
            adapter_before_remove
            and "inv.Usp_BeforeRemoveExitFromDist" in adapter_before_remove["procedure_name_signals"]
            and _offsets(adapter_before_remove, "Thunderstruck.DataContext.Query")
            and not _offsets(adapter_before_remove, "Thunderstruck.DataContext.Commit")
        ),
        "remove_adapter_queries_named_procedure_without_local_commit": bool(
            adapter_remove
            and "inv.Usp_RemoveExitFromDist" in adapter_remove["procedure_name_signals"]
            and _offsets(adapter_remove, "Thunderstruck.DataContext.Query")
            and not _offsets(adapter_remove, "Thunderstruck.DataContext.Commit")
        ),
        "merge_adapter_executes_named_procedure_without_local_commit": bool(
            adapter_merge
            and "inv.Usp_InsertGoodsExit_RD" in adapter_merge["procedure_name_signals"]
            and _offsets(adapter_merge, "Thunderstruck.DataContext.Execute")
            and not _offsets(adapter_merge, "Thunderstruck.DataContext.Commit")
        ),
        "normal_issue_ui_constructs_context_then_calls_create_then_commits": bool(
            ordered(ui_issue, "Thunderstruck.DataContext..ctor", issue_member)
            and ordered(ui_issue, issue_member, "Thunderstruck.DataContext.Commit")
        ),
        "normal_remove_ui_validates_then_constructs_context_removes_and_commits": bool(
            ordered(ui_remove, before_remove_member, "Thunderstruck.DataContext..ctor")
            and ordered(ui_remove, "Thunderstruck.DataContext..ctor", remove_member)
            and ordered(ui_remove, remove_member, "Thunderstruck.DataContext.Commit")
        ),
        "merge_ui_delegates_without_explicit_context_or_commit": bool(
            delegates(ui_merge, "VN.SDS.Sales.Business.Dist.DistHandler.MergeGoodsExit")
            and not _offsets(ui_merge, "Thunderstruck.DataContext..ctor")
            and not _offsets(ui_merge, "Thunderstruck.DataContext.Commit")
        ),
        "selected_methods_have_no_explicit_rollback_signal": not any(
            _offsets(row, "Thunderstruck.DataContext.RollBack") for row in methods
        ),
        "normal_ui_route_selection_proven_for_issue_and_remove": True,
        "physical_transaction_enlistment_across_ui_and_nested_adapter_contexts_proven": False,
        "alternate_direct_sql_callsite_selection_proven": False,
    }
    return {
        "artifact": "varanegar_distribution_exit_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "application_endpoint_form_or_command_executions": 0,
            "database_connections": 0,
            "configuration_distribution_sale_exit_stock_user_or_host_values_read": 0,
            "raw_string_sql_or_identifier_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "source_hash_mismatch_count": sum(not row["inventory_sha256_match"] for row in sources),
            "method_or_coverage_error_count": len(errors),
        },
        "managed_exit_contract": contract,
        "method_contracts": methods,
        "errors": errors,
        "evidence_limits": [
            "Linear IL proves selected call ordering, not branch-specific execution, runtime frequency or successful effects.",
            "The normal issue and remove UI methods visibly create and commit a DataContext around handler calls, but the handlers instantiate adapters and physical enlistment with adapter-created contexts is not proven.",
            "The merge UI method has no explicit transaction owner in its selected IL; this is a static ownership gap, not proof of partial runtime data.",
            "Procedure-name presence is allowlisted metadata derived from literals; raw SQL, parameters and identifiers are not persisted.",
            "Physical-delete SQL candidates are outside these selected managed routes; their runtime callers are not attributed by this artifact.",
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
    print(json.dumps(payload["managed_exit_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
