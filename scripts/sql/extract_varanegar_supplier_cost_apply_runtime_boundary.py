"""Extract static managed apply/reapply transaction signals for supplier costing.

Assemblies are parsed as PE metadata and IL only; they are never loaded or executed.
String literals are reduced to allowlisted procedure-presence signals and hashes.
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


TARGETS = {
    "VN.SDS.Stock.Business.dll": {
        "VN.SDS.Stock.Business.CalcPrice.CalcPriceHandler": {"StartReApplySupInvoice"},
        "VN.SDS.Stock.Business.SupInvInvoiceRelation.SupInvInvoiceRelationHandler": {
            "ApplySupInvoice"
        },
    },
    "VN.SDS.Stock.DataAccess.dll": {
        "VN.SDS.Stock.DataAccess.DataAdapter.CalcPrice.CalcPriceAdapter": {
            "StartReApplySupInvoice"
        },
        "VN.SDS.Stock.DataAccess.DataAdapter.SupInvInvoiceRelation.SupInvInvoiceRelationAdapter": {
            "ApplySupInvoice"
        },
    },
}

SAFE_MEMBERS = {
    "Thunderstruck.DataContext..ctor",
    "Thunderstruck.DataContext.Query",
    "Thunderstruck.DataContext.Execute",
    "Thunderstruck.DataContext.Commit",
    "Thunderstruck.DataContext.Dispose",
    "Thunderstruck.DataContext.BeginTransaction",
    "System.Data.Common.DbConnection.BeginTransaction",
    "System.Data.SqlClient.SqlConnection.BeginTransaction",
    "VN.SDS.Stock.DataAccess.DataAdapter.CalcPrice.CalcPriceAdapter.StartReApplySupInvoice",
    "VN.SDS.Stock.DataAccess.DataAdapter.SupInvInvoiceRelation.SupInvInvoiceRelationAdapter.ApplySupInvoice",
}
PROCEDURE_MARKERS = {
    "ICA.usp_ReApplySupInvoice": "reapply_procedure_literal_present",
    "ICA.usp_ApplySupInvoice": "apply_procedure_literal_present",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _method_contract(
    pe: dnfile.dnPE,
    owner: str,
    method_index: Any,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
) -> dict[str, Any]:
    method = method_index.row
    body = read_method_body_from_bytes(pe.get_data(method.Rva, 131072))
    events: list[dict[str, Any]] = []
    literal_fingerprints: list[dict[str, Any]] = []
    procedure_signals = {signal: False for signal in PROCEDURE_MARKERS.values()}
    for instruction in body.instructions:
        operand = instruction.operand
        if isinstance(operand, StringToken):
            item = pe.net.user_strings.get(operand.rid)
            value = "" if item is None else str(item.value)
            literal_fingerprints.append(
                {
                    "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                    "length": len(value),
                    "raw_value_persisted": False,
                }
            )
            for marker, signal in PROCEDURE_MARKERS.items():
                if marker in value:
                    procedure_signals[signal] = True
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
        "assembly_file": "",
        "type": owner,
        "method": str(method.Name),
        "instruction_count": len(body.instructions),
        "has_exception_regions": bool(body.exception_handlers),
        "event_ledger": events,
        "literal_fingerprints": literal_fingerprints,
        "procedure_signals": procedure_signals,
    }


def _has(method: dict[str, Any], member: str) -> bool:
    return any(row["member"] == member for row in method["event_ledger"])


def _offset(method: dict[str, Any], member: str) -> int | None:
    return next(
        (row["offset"] for row in method["event_ledger"] if row["member"] == member),
        None,
    )


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = _load(binary_inventory)
    expected_hashes = {row["name"]: row["sha256"] for row in inventory["files"]}
    sources = []
    methods = []
    errors = []
    for assembly, type_targets in TARGETS.items():
        path = source_directory / assembly
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        hash_match = actual_hash == expected_hashes.get(assembly)
        sources.append(
            {
                "assembly_file": assembly,
                "assembly_bytes": path.stat().st_size,
                "assembly_sha256": actual_hash,
                "inventory_sha256_match": hash_match,
            }
        )
        if not hash_match:
            errors.append({"assembly_file": assembly, "error": "inventory hash mismatch"})
        pe = dnfile.dnPE(str(path))
        method_owners, field_owners = _owner_maps(pe)
        types = {
            _full_type_name(row): row for row in pe.net.mdtables.TypeDef.rows
        }
        for owner, selected_names in type_targets.items():
            type_row = types.get(owner)
            if type_row is None:
                errors.append({"assembly_file": assembly, "type": owner, "error": "type absent"})
                continue
            found = set()
            for method_index in type_row.MethodList or []:
                method = method_index.row
                if method is None or not method.Rva or str(method.Name) not in selected_names:
                    continue
                found.add(str(method.Name))
                try:
                    contract = _method_contract(
                        pe, owner, method_index, method_owners, field_owners
                    )
                    contract["assembly_file"] = assembly
                    methods.append(contract)
                except Exception as exc:
                    errors.append(
                        {
                            "assembly_file": assembly,
                            "type": owner,
                            "method": str(method.Name),
                            "error": type(exc).__name__,
                        }
                    )
            for missing in selected_names - found:
                errors.append(
                    {
                        "assembly_file": assembly,
                        "type": owner,
                        "method": missing,
                        "error": "method absent",
                    }
                )

    by_key = {(row["type"], row["method"]): row for row in methods}
    reapply_handler = by_key.get(
        (
            "VN.SDS.Stock.Business.CalcPrice.CalcPriceHandler",
            "StartReApplySupInvoice",
        )
    )
    reapply_adapter = by_key.get(
        (
            "VN.SDS.Stock.DataAccess.DataAdapter.CalcPrice.CalcPriceAdapter",
            "StartReApplySupInvoice",
        )
    )
    apply_handler = by_key.get(
        (
            "VN.SDS.Stock.Business.SupInvInvoiceRelation.SupInvInvoiceRelationHandler",
            "ApplySupInvoice",
        )
    )
    apply_adapter = by_key.get(
        (
            "VN.SDS.Stock.DataAccess.DataAdapter.SupInvInvoiceRelation.SupInvInvoiceRelationAdapter",
            "ApplySupInvoice",
        )
    )
    if not all((reapply_handler, reapply_adapter, apply_handler, apply_adapter)):
        errors.append({"error": "selected runtime coverage incomplete"})

    apply_call_offset = None if apply_handler is None else _offset(
        apply_handler,
        "VN.SDS.Stock.DataAccess.DataAdapter.SupInvInvoiceRelation.SupInvInvoiceRelationAdapter.ApplySupInvoice",
    )
    apply_commit_offset = None if apply_handler is None else _offset(
        apply_handler, "Thunderstruck.DataContext.Commit"
    )
    contract = {
        "reapply_business_calls_adapter": bool(
            reapply_handler
            and _has(
                reapply_handler,
                "VN.SDS.Stock.DataAccess.DataAdapter.CalcPrice.CalcPriceAdapter.StartReApplySupInvoice",
            )
        ),
        "reapply_adapter_queries_allowlisted_reapply_procedure": bool(
            reapply_adapter
            and reapply_adapter["procedure_signals"]["reapply_procedure_literal_present"]
            and _has(reapply_adapter, "Thunderstruck.DataContext.Query")
        ),
        "reapply_selected_path_has_data_context_commit_signal": bool(
            (reapply_handler and _has(reapply_handler, "Thunderstruck.DataContext.Commit"))
            or (reapply_adapter and _has(reapply_adapter, "Thunderstruck.DataContext.Commit"))
        ),
        "reapply_selected_path_has_begin_transaction_signal": bool(
            any(
                row["member"].endswith(".BeginTransaction")
                for method in (reapply_handler, reapply_adapter)
                if method is not None
                for row in method["event_ledger"]
            )
        ),
        "apply_business_calls_adapter": bool(
            apply_handler
            and _has(
                apply_handler,
                "VN.SDS.Stock.DataAccess.DataAdapter.SupInvInvoiceRelation.SupInvInvoiceRelationAdapter.ApplySupInvoice",
            )
        ),
        "apply_adapter_calls_data_context_execute": bool(
            apply_adapter and _has(apply_adapter, "Thunderstruck.DataContext.Execute")
        ),
        "apply_business_has_commit_signal": bool(
            apply_handler and _has(apply_handler, "Thunderstruck.DataContext.Commit")
        ),
        "apply_adapter_call_precedes_business_commit_in_linear_il": bool(
            apply_call_offset is not None
            and apply_commit_offset is not None
            and apply_call_offset < apply_commit_offset
        ),
        "managed_data_context_constructor_transaction_semantics_proven": False,
        "branch_specific_commit_reachability_proven": False,
    }
    return {
        "artifact": "varanegar_supplier_cost_apply_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "application_endpoint_or_command_executions": 0,
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
        "managed_apply_reapply_contract": contract,
        "method_contracts": methods,
        "errors": errors,
        "evidence_limits": [
            "Linear IL order does not prove branch-specific execution or failure behavior.",
            "DataContext constructor transaction semantics were not inferred from a constructor call.",
            "Static runtime signals do not prove a partial supplier-cost incident occurred.",
            "Only four allowlisted methods were parsed; dynamic, reflection and other callers remain outside this boundary.",
            "Assemblies were never loaded or executed, and no raw string or SQL literal was persisted.",
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
    print(json.dumps(payload["managed_apply_reapply_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
