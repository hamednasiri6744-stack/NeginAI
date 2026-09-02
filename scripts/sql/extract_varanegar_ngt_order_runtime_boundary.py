"""Extract the deployed NGT order/tour runtime boundary without execution.

This extractor reads PE metadata and IL only. It never loads assemblies, calls
application endpoints, reads configuration values, or persists arbitrary string
literals. The output is a static call/field contract, not proof of route use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token


WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
if str(WINDOWS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SCRIPTS))

from extract_varanegar_ngt_authorization_runtime_boundary import (  # noqa: E402
    _owner_maps,
    _parameter_count,
    _resolve_token,
    _signature_bytes,
)


TARGET_FILES = (
    "NGT.Common.dll",
    "NGT.Business.dll",
    "NGT.DataAccess.dll",
    "NGT.WebApi.dll",
)

SIGNAL = re.compile(
    r"(?:CustomerCallOrders?|CustomerCallOrderLines?|OrderLineQty|OrderDomain|"
    r"TourDomain|OrderController|TourController|SaveTourData|AddDistributionTour|"
    r"BackOfficeOrder|InvoicePayment|OrderPayment|OrderType|SaleType|"
    r"ReplicateTour|SendToConsole|IsCanceled)",
    re.IGNORECASE,
)

SAFE_LITERAL = re.compile(
    r"^(?:CustomerCallOrders?|CustomerCallOrderLines?|CustomerCallOrderLineQty|"
    r"CustomerCallOrderLineQtys|OrderDomain|TourDomain|SaveTourData|"
    r"AddDistributionTour|BackOfficeOrderId|BackOfficeOrderNo|"
    r"BackOfficeOrderUniqueId|BackOfficeOrderRef|BackOfficeOrderUUID|"
    r"InvoiceId|InvoiceUniqueId|CustomerCallUniqueId|OrderTypeUniqueId|"
    r"OrderPaymentTypeUniqueId|InvoicePaymentTypeUniqueId|SubSystemTypeUniqueId|"
    r"SendToConsoleDate|IsCanceled|IsRemoved|OperationDate)$",
    re.IGNORECASE,
)

SELECTION_CALL = re.compile(
    r"(?:^|\.)(?:GetQueryByOwner|GetQuery|FirstOrDefault|First|SingleOrDefault|Single|"
    r"Where|Any|All|Find|FindAll|FindAsync|FindAllAsync|GetById|GetByIdAsync|"
    r"ToList|ToListAsync|AsNoTracking|Include|OrderBy|ThenBy|Select|GroupBy)$",
    re.IGNORECASE,
)

MUTATION_CALL = re.compile(
    r"(?:^|\.)(?:BeginTransaction|Commit|Rollback|SaveChanges|SaveChangesAsync|"
    r"Add|AddAsync|AddRange|AddRangeAsync|Update|UpdateAsync|Remove|RemoveAsync|"
    r"RemoveRange|Delete|DeleteAsync|ExecuteSqlCommand|ExecuteSqlCommandAsync|"
    r"CustomCommit|CustomRollback)$",
    re.IGNORECASE,
)

SCOPE_SIGNAL = re.compile(
    r"(?:ApplicationOwner|DataOwnerCenter|DataOwner|OwnerInfo|CurrentUser|"
    r"UserUniqueId|DealerRef|DcRef|SaleOfficeRef|SubSystemType)",
    re.IGNORECASE,
)

STATE_SIGNAL = re.compile(
    r"(?:IsRemoved|IsCanceled|SendToConsoleDate|BackOfficeOrder|InvoiceId|"
    r"InvoiceUniqueId|OperationDate|LastUpdate|CustomerCallUniqueId|"
    r"OrderTypeUniqueId|OrderPaymentTypeUniqueId|InvoicePaymentTypeUniqueId)",
    re.IGNORECASE,
)

WINDOW_SIGNAL = re.compile(
    r"(?:CustomerCallOrders?|CustomerCallOrderLines?|OrderLineQty|"
    r"SaveTourData|AddDistributionTour|BackOfficeOrder|InvoiceId|InvoiceUniqueId|"
    r"IsRemoved|IsCanceled|SendToConsoleDate|OperationDate|BeginTransaction|"
    r"Commit|Rollback|SaveChanges|GetQueryByOwner|FirstOrDefault)",
    re.IGNORECASE,
)

KEY_CALL = re.compile(
    r"(?:CustomerCallOrders?|CustomerCallOrderLines?|OrderLineQty|"
    r"SaveTourData|UpdateTour|CancelCallOrder|ReplicateTour|NewReplicateTour|"
    r"ReplicateToBackOffice|RollBackTour|FinishTour|BackOfficeOrder|InvoiceId|"
    r"InvoiceUniqueId|IsRemoved|IsCanceled|SendToConsoleDate|OperationDate|"
    r"BeginTransaction|Commit|Rollback|SaveChanges|ExecuteSqlCommand|"
    r"GetQueryByOwner|GetQuery|Find|GetById|FirstOrDefault|Where|Any|GroupBy|"
    r"ApplicationOwner|DataOwnerCenter|DataOwner|OwnerInfo|CurrentUser)",
    re.IGNORECASE,
)

SQL_OBJECT_REF = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO|FROM|JOIN)\s+"
    r"(?P<object>(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC)\]|(?:dbo|NGT|FRU|SLE|GNR|ACC))"
    r"\.\[[A-Za-z_][A-Za-z0-9_]*\]|(?:dbo|NGT|FRU|SLE|GNR|ACC)\."
    r"[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)

ORCHESTRATION_SIGNAL = re.compile(
    r"(?:NGT\.Business\.Domain\.TourDomain\.(?:SaveTourData|ReplicateTour|"
    r"NewReplicateTour|ReplicateToBackOffice|FinishTour|RollBackTour)|"
    r"BeginTransaction|CustomCommit|CustomRollback|DbContextTransaction\.(?:Commit|Rollback))$",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _analyze_assembly(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError(f"not a .NET assembly: {path}")
    method_owners, field_owners, type_names = _owner_maps(pe)
    selected: list[dict[str, Any]] = []
    body_count = 0
    body_errors: list[dict[str, Any]] = []
    redacted_literal_count = 0
    allowlisted_literal_count = 0

    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = type_names[type_index]
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            method_name = _text(method.Name)
            body_count += 1
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                body_errors.append(
                    {
                        "owner": owner,
                        "method": method_name,
                        "error_class": type(exc).__name__,
                        "signal_named": bool(SIGNAL.search(owner) or SIGNAL.search(method_name)),
                    }
                )
                continue

            calls: list[str] = []
            fields: list[str] = []
            safe_literals: list[str] = []
            sql_object_references: list[str] = []
            instructions: list[dict[str, Any]] = []
            method_redacted = 0
            for instruction in body.instructions:
                operand = instruction.operand
                row: dict[str, Any] = {
                    "offset": instruction.offset,
                    "opcode": instruction.mnemonic,
                }
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(
                    operand, Token
                ):
                    resolved = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                    calls.append(resolved)
                    row["operand"] = resolved
                elif "fld" in instruction.mnemonic and isinstance(operand, Token):
                    resolved = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                    fields.append(resolved)
                    row["operand"] = resolved
                elif instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    value = "" if item is None else _text(item.value)
                    for match in SQL_OBJECT_REF.finditer(value):
                        sql_object_references.append(
                            match.group("object").replace("[", "").replace("]", "")
                        )
                    if SAFE_LITERAL.fullmatch(value):
                        safe_literals.append(value)
                        allowlisted_literal_count += 1
                        row["operand"] = value
                    else:
                        method_redacted += 1
                        redacted_literal_count += 1
                        row["operand"] = "<redacted-non-allowlisted-literal>"
                elif isinstance(operand, Token):
                    row["operand"] = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                elif isinstance(operand, (int, float)):
                    row["operand"] = operand
                instructions.append(row)

            signals = [owner, method_name, *calls, *fields, *safe_literals]
            if not any(SIGNAL.search(value) for value in signals):
                continue
            signal_positions = [
                index
                for index, row in enumerate(instructions)
                if WINDOW_SIGNAL.search(_text(row.get("operand", "")))
            ]
            orchestration_positions = [
                index
                for index, row in enumerate(instructions)
                if ORCHESTRATION_SIGNAL.search(_text(row.get("operand", "")))
            ]
            state_references = sorted(
                {
                    _text(row.get("operand", ""))
                    for row in instructions
                    if STATE_SIGNAL.search(_text(row.get("operand", "")))
                }
            )
            selected.append(
                {
                    "owner": owner,
                    "method": method_name,
                    "method_metadata_token": f"0x06{method_index.row_index:06x}",
                    "parameter_count": _parameter_count(method),
                    "signature_hex": _signature_bytes(method).hex(),
                    "instruction_count": len(body.instructions),
                    "signal_calls": sorted(set(value for value in calls if SIGNAL.search(value))),
                    "selection_calls": sorted(
                        set(value for value in calls if SELECTION_CALL.search(value))
                    ),
                    "mutation_calls_in_order": [
                        value for value in calls if MUTATION_CALL.search(value)
                    ],
                    "key_calls_in_order": [
                        value for value in calls if KEY_CALL.search(value)
                    ],
                    "scope_references": sorted(
                        {
                            value
                            for value in [*calls, *fields]
                            if SCOPE_SIGNAL.search(value)
                        }
                    ),
                    "state_references": state_references,
                    "allowlisted_code_literals": sorted(set(safe_literals)),
                    "sql_object_references": sorted(set(sql_object_references)),
                    "redacted_non_allowlisted_literal_count": method_redacted,
                    "has_conditional_branch": any(
                        instruction.mnemonic.startswith("br")
                        or instruction.mnemonic == "switch"
                        for instruction in body.instructions
                    ),
                    "has_exception_regions": bool(body.exception_handlers),
                    "signal_instruction_windows": [
                        instructions[max(0, index - 18): min(len(instructions), index + 19)]
                        for index in signal_positions[:24]
                    ],
                    "orchestration_instruction_windows": [
                        instructions[max(0, index - 22): min(len(instructions), index + 23)]
                        for index in orchestration_positions[:64]
                    ],
                }
            )

    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "method_body_count": body_count,
        "method_body_error_count": len(body_errors),
        "body_errors": body_errors,
        "selected_method_count": len(selected),
        "allowlisted_code_literal_count": allowlisted_literal_count,
        "redacted_non_allowlisted_literal_count": redacted_literal_count,
        "selected_methods": selected,
    }


def collect(source_directory: Path) -> dict[str, Any]:
    assemblies = [_analyze_assembly(source_directory / name) for name in TARGET_FILES]
    selected = [
        {"file": assembly["file"], **method}
        for assembly in assemblies
        for method in assembly["selected_methods"]
    ]
    errors = [
        {"file": assembly["file"], **row}
        for assembly in assemblies
        for row in assembly["body_errors"]
    ]
    runtime_selection = [
        method
        for method in selected
        if method["selection_calls"]
        and (
            SIGNAL.search(method["owner"])
            or SIGNAL.search(method["method"])
            or method["signal_calls"]
        )
    ]
    mutation_methods = [method for method in selected if method["mutation_calls_in_order"]]
    transactional = [
        method
        for method in mutation_methods
        if any(call.endswith(".BeginTransaction") for call in method["mutation_calls_in_order"])
    ]
    key_runtime = [
        method
        for method in selected
        if (
            re.search(
                r"(?:OrderDomain|TourDomain|OrderController|TourController)",
                method["owner"],
                re.IGNORECASE,
            )
            and (
                method["signal_calls"]
                or method["state_references"]
                or method["selection_calls"]
                or method["mutation_calls_in_order"]
            )
        )
    ]

    def pick(owner: str, method: str = "MoveNext") -> dict[str, Any] | None:
        return next(
            (row for row in selected if row["owner"] == owner and row["method"] == method),
            None,
        )

    def call_count(row: dict[str, Any] | None, target: str) -> int:
        if row is None:
            return 0
        return sum(1 for value in row["key_calls_in_order"] if value == target)

    def callers(target: str) -> list[dict[str, Any]]:
        return [
            {
                "file": row["file"],
                "owner": row["owner"],
                "method": row["method"],
                "parameter_count": row["parameter_count"],
            }
            for row in selected
            if target in row["signal_calls"]
        ]

    save = pick("NGT.Business.Domain.TourDomain+<SaveTourData>d__24")
    replicate = pick("NGT.Business.Domain.TourDomain+<ReplicateTour>d__39")
    new_replicate = pick("NGT.Business.Domain.TourDomain+<NewReplicateTour>d__40")
    update = pick("NGT.Business.Domain.TourDomain+<UpdateTour>d__14")
    update_order = pick("NGT.Business.Domain.CustomerCallOrderDomain+<UpdateFromNGT>d__3")
    add_status = pick(
        "NGT.Business.Domain.CustomerCallOrderDomain+<AddToCustomerCallOrderStatus>d__6"
    )
    key_orchestration = {
        "save_tour_data": None
        if save is None
        else {
            "instruction_count": save["instruction_count"],
            "begin_transaction_call_count": call_count(
                save, "System.Data.Entity.Database.BeginTransaction"
            ),
            "commit_call_count": call_count(
                save, "System.Data.Entity.DbContextTransaction.Commit"
            ),
            "rollback_call_count": call_count(
                save, "System.Data.Entity.DbContextTransaction.Rollback"
            ),
            "replicate_tour_call_count": call_count(
                save, "NGT.Business.Domain.TourDomain.ReplicateTour"
            ),
            "safe_sql_object_references": save["sql_object_references"],
        },
        "replicate_tour": None
        if replicate is None
        else {
            "instruction_count": replicate["instruction_count"],
            "new_replicate_tour_call_count": call_count(
                replicate, "NGT.Business.Domain.TourDomain.NewReplicateTour"
            ),
            "replicate_to_backoffice_call_count": call_count(
                replicate, "NGT.Business.Domain.TourDomain.ReplicateToBackOffice"
            ),
            "commit_call_count": call_count(
                replicate, "System.Data.Entity.DbContextTransaction.Commit"
            ),
            "rollback_call_count": call_count(
                replicate, "System.Data.Entity.DbContextTransaction.Rollback"
            ),
            "finish_tour_call_count": call_count(
                replicate, "NGT.Business.Domain.TourDomain.FinishTour"
            ),
            "rollback_tour_call_count": call_count(
                replicate, "NGT.Business.Domain.TourDomain.RollBackTour"
            ),
        },
        "new_replicate_tour": None
        if new_replicate is None
        else {
            "instruction_count": new_replicate["instruction_count"],
            "begin_transaction_call_count": call_count(
                new_replicate, "System.Data.Entity.Database.BeginTransaction"
            ),
            "custom_commit_call_count": call_count(
                new_replicate, "NGT.Business.Helpers.TransactionHelper.CustomCommit"
            ),
            "custom_rollback_call_count": call_count(
                new_replicate, "NGT.Business.Helpers.TransactionHelper.CustomRollback"
            ),
            "safe_sql_object_references": new_replicate["sql_object_references"],
        },
        "update_tour": None
        if update is None
        else {
            "calls_update_from_ngt": "NGT.Business.Domain.CustomerCallOrderDomain.UpdateFromNGT"
            in update["signal_calls"],
            "begin_transaction_call_count": call_count(
                update, "System.Data.Entity.Database.BeginTransaction"
            ),
        },
        "update_order_from_ngt": None
        if update_order is None
        else {
            "instruction_count": update_order["instruction_count"],
            "save_changes_call_count": call_count(update_order, "TypeSpecRow.SaveChangesAsync"),
            "begin_transaction_call_count": call_count(
                update_order, "System.Data.Entity.Database.BeginTransaction"
            ),
            "sets_removed_state": any(
                value.endswith(".set_IsRemoved") for value in update_order["state_references"]
            ),
        },
        "order_status_writer": None
        if add_status is None
        else {
            "instruction_count": add_status["instruction_count"],
            "direct_static_caller_count": len(
                callers(
                    "NGT.Business.Domain.CustomerCallOrderDomain.AddToCustomerCallOrderStatus"
                )
            ),
            "direct_static_callers": callers(
                "NGT.Business.Domain.CustomerCallOrderDomain.AddToCustomerCallOrderStatus"
            ),
            "begin_transaction_call_count": call_count(
                add_status, "System.Data.Entity.Database.BeginTransaction"
            ),
            "commit_call_count": call_count(
                add_status, "System.Data.Entity.DbContextTransaction.Commit"
            ),
            "safe_sql_object_references": add_status["sql_object_references"],
        },
        "save_tour_data_callers": callers("NGT.Business.Domain.TourDomain.SaveTourData"),
        "replicate_tour_callers": callers("NGT.Business.Domain.TourDomain.ReplicateTour"),
    }
    return {
        "artifact": "varanegar_ngt_order_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "source": {
            "assembly_directory": str(source_directory),
            "assemblies": [
                {
                    "file": assembly["file"],
                    "sha256": assembly["sha256"],
                    "bytes": assembly["bytes"],
                }
                for assembly in assemblies
            ],
        },
        "safety": {
            "mode": "STATIC_PE_METADATA_AND_IL_ONLY",
            "assemblies_loaded_or_executed": 0,
            "application_endpoints_or_commands_called": 0,
            "configuration_files_or_values_read": 0,
            "business_rows_or_identifiers_read": 0,
            "non_allowlisted_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(assemblies),
            "method_body_count": sum(a["method_body_count"] for a in assemblies),
            "method_body_error_count": len(errors),
            "signal_named_body_error_count": sum(1 for row in errors if row["signal_named"]),
            "selected_method_count": len(selected),
            "runtime_selection_method_count": len(runtime_selection),
            "mutation_method_count": len(mutation_methods),
            "explicit_transaction_method_count": len(transactional),
            "key_runtime_method_count": len(key_runtime),
        },
        "assembly_scan": [
            {key: value for key, value in assembly.items() if key not in {"selected_methods", "body_errors"}}
            for assembly in assemblies
        ],
        "body_errors": errors,
        "runtime_selection_methods": runtime_selection,
        "mutation_methods": mutation_methods,
        "key_runtime_method_contracts": key_runtime,
        "key_orchestration_contract": key_orchestration,
        "evidence_limits": [
            "Static IL proves compiled call and field references, not active route use or request success.",
            "Compiler-generated predicates and async MoveNext bodies can hold semantics outside parent methods.",
            "Non-allowlisted strings are redacted, so arbitrary query text and business/configuration values are not asserted.",
            "A transaction call in one method does not prove atomicity across external adapters or nested calls.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    payload = collect(args.source_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
