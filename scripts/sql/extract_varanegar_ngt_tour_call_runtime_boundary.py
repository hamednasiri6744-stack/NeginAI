"""Extract the deployed NGT tour/customer-call lifecycle from static IL only.

Assemblies are parsed as PE metadata and IL bytes. They are never loaded or
executed. Arbitrary literals are counted and redacted; only safe SQL object
identifiers recovered from literal text are retained.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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

FOCUSED_OWNER = re.compile(
    r"(?:NGT\.Business\.Domain\.(?:TourDomain|CustomerCallDomain)|"
    r"NGT\.WebApi\.Controllers\.V2\.(?:TourController|CustomerCallController))",
    re.IGNORECASE,
)

SIGNAL = re.compile(
    r"(?:TourStatus|PreviousStatus|CallStatus|VisitStatus|CustomerCall|TourDomain|"
    r"TourController|FinishTour|CloseTour|CancelTour|DeactivateTour|ActivateTour|"
    r"TourReceived|TourSent|ReadySend|ReplicateCall|SaveTourData)",
    re.IGNORECASE,
)

STATE_REF = re.compile(
    r"(?:TourStatus|PreviousStatus|CallStatus|VisitStatus|PaymentApproved|"
    r"StockLevelApproved|StartTime|EndTime|ReceiveDate|SendDate|SendToConsoleDate|"
    r"SaleDate|DeliveryDate|ManualStartTime|ManualEndTime|VisitDuration|"
    r"ManualVisitDuration|NoSaleReason|HasCancelInvoice|IsOutOfPath|IsNewCustomer|"
    r"ByStockLevelConflict|DistributionUniqueId|DistributionRef|IsRemoved|"
    r"CustomerCount|VisitCount|NoVisitCount|OrderCount|NoOrderCount|"
    r"UndetermindCount|InvoiceCount|ReturnInvoiceCount|ReturnInvoiceRequestCount)",
    re.IGNORECASE,
)

SCOPE_REF = re.compile(
    r"(?:ApplicationOwner|DataOwnerCenter|DataOwner|OwnerInfo|CurrentUser|"
    r"UserUniqueId|AgentUniqueId|CustomerUniqueId)",
    re.IGNORECASE,
)

MUTATION_CALL = re.compile(
    r"(?:^|\.)(?:BeginTransaction|Commit|Rollback|SaveChanges|SaveChangesAsync|"
    r"Add|AddAsync|AddRange|AddRangeAsync|Update|UpdateAsync|UpdateBatchAsync|"
    r"UpdateRange|Remove|RemoveAsync|RemoveRange|Delete|DeleteAsync|"
    r"ExecuteSqlCommand|ExecuteSqlCommandAsync|ExecuteNonQuery|"
    r"CustomCommit|CustomRollback)$",
    re.IGNORECASE,
)

SELECTION_CALL = re.compile(
    r"(?:^|\.)(?:GetQueryByOwner|GetQuery|FirstOrDefault|First|SingleOrDefault|"
    r"Single|Where|Any|All|Find|FindAll|FindAsync|FindAllAsync|GetById|"
    r"GetByIdAsync|ToList|ToListAsync|AsNoTracking|Include|OrderBy|ThenBy|"
    r"Select|GroupBy)$",
    re.IGNORECASE,
)

BEHAVIOR_REF = re.compile(
    r"(?:BeginTransaction|Commit|Rollback|SaveChanges|UpdateAsync|AddAsync|"
    r"RemoveAsync|ExecuteSqlCommand|CustomCommit|CustomRollback|"
    r"ConfirmTour|WithdrawTour|CancelTour|DeactivateTour|ActivateTour|"
    r"TourReceived|TourSent|ReadySend|CloseTour|FinishTour|RollBackTour|"
    r"ReplicateTour|ReplicateCall|UpdateTourOutline|UpdateFromNGT|"
    r"AddOrUpdateCustomerCallFromDevice|PublicValues|TourStatus|CallStatus|"
    r"VisitStatus|PreviousStatus)",
    re.IGNORECASE,
)

SQL_OBJECT_REF = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO|FROM|JOIN)\s+"
    r"(?P<object>(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC)\]|(?:dbo|NGT|FRU|SLE|GNR|ACC))"
    r"\.\[[A-Za-z_][A-Za-z0-9_]*\]|(?:dbo|NGT|FRU|SLE|GNR|ACC)\."
    r"[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)

LIFECYCLE_METHODS = (
    "ConfirmTourReceived",
    "ConfirmTourPayments",
    "ConfirmDistTour",
    "WithdrawTourPayments",
    "CancelTour",
    "DeactivateTour",
    "ActivateTour",
    "TourReceived",
    "TourSentOld",
    "TourSent",
    "backToReadySendStatusTour",
    "CloseTour",
    "FinishTour",
    "SaveTourData",
    "ReplicateTour",
    "CancelCallCancelation",
    "UpdateFromNGT",
    "AddOrUpdateCustomerCallFromDevice",
    "ReplicateCallrPreviewOrderMode",
    "ReplicateCall",
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _scan(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError(f"not a .NET assembly: {path}")
    method_owners, field_owners, type_names = _owner_maps(pe)
    methods: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    method_body_count = 0
    redacted_literal_count = 0

    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = type_names[type_index]
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            method_name = _text(method.Name)
            method_body_count += 1
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                errors.append(
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
            ordered_references: list[str] = []
            safe_sql_refs: list[str] = []
            method_redacted = 0
            for instruction in body.instructions:
                operand = instruction.operand
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(
                    operand, Token
                ):
                    resolved = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                    calls.append(resolved)
                    ordered_references.append(resolved)
                elif "fld" in instruction.mnemonic and isinstance(operand, Token):
                    resolved = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                    fields.append(resolved)
                    ordered_references.append(resolved)
                elif instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    value = "" if item is None else _text(item.value)
                    for match in SQL_OBJECT_REF.finditer(value):
                        safe_sql_refs.append(
                            match.group("object").replace("[", "").replace("]", "")
                        )
                    method_redacted += 1
                    redacted_literal_count += 1
                elif isinstance(operand, Token):
                    ordered_references.append(
                        _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    )

            references = ordered_references
            if not (
                FOCUSED_OWNER.search(owner)
                or SIGNAL.search(owner)
                or SIGNAL.search(method_name)
                or any(SIGNAL.search(value) for value in references)
            ):
                continue
            methods.append(
                {
                    "owner": owner,
                    "method": method_name,
                    "method_metadata_token": f"0x06{method_index.row_index:06x}",
                    "parameter_count": _parameter_count(method),
                    "signature_hex": _signature_bytes(method).hex(),
                    "instruction_count": len(body.instructions),
                    "mutation_calls_in_order": [
                        value for value in calls if MUTATION_CALL.search(value)
                    ],
                    "call_references_in_order": calls,
                    "selection_calls": sorted(
                        {value for value in calls if SELECTION_CALL.search(value)}
                    ),
                    "behavior_references_in_order": [
                        value
                        for value in references
                        if BEHAVIOR_REF.search(value) and not value.startswith(owner + ".")
                    ],
                    "state_references_in_order": [
                        value
                        for value in references
                        if STATE_REF.search(value) and not value.startswith(owner + ".")
                    ],
                    "scope_references": sorted(
                        {
                            value
                            for value in references
                            if SCOPE_REF.search(value) and not value.startswith(owner + ".")
                        }
                    ),
                    "safe_sql_object_references": sorted(set(safe_sql_refs)),
                    "redacted_non_allowlisted_literal_count": method_redacted,
                    "has_conditional_branch": any(
                        instruction.mnemonic.startswith("br")
                        or instruction.mnemonic == "switch"
                        for instruction in body.instructions
                    ),
                    "has_exception_regions": bool(body.exception_handlers),
                }
            )

    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "method_body_count": method_body_count,
        "method_body_error_count": len(errors),
        "selected_method_count": len(methods),
        "redacted_non_allowlisted_literal_count": redacted_literal_count,
        "body_errors": errors,
        "methods": methods,
    }


def collect(source_directory: Path) -> dict[str, Any]:
    scans = [_scan(source_directory / file_name) for file_name in TARGET_FILES]
    methods = [
        {"file": scan["file"], **method}
        for scan in scans
        for method in scan["methods"]
    ]
    errors = [
        {"file": scan["file"], **error}
        for scan in scans
        for error in scan["body_errors"]
    ]

    focused = [
        row
        for row in methods
        if FOCUSED_OWNER.search(row["owner"])
        and (
            row["mutation_calls_in_order"]
            or row["selection_calls"]
            or row["state_references_in_order"]
            or row["behavior_references_in_order"]
        )
    ]

    def async_body(name: str) -> dict[str, Any] | None:
        return next(
            (
                row
                for row in focused
                if f"<{name}>" in row["owner"] and row["method"] == "MoveNext"
            ),
            None,
        )

    def compact(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "file": row["file"],
            "owner": row["owner"],
            "method": row["method"],
            "method_metadata_token": row["method_metadata_token"],
            "instruction_count": row["instruction_count"],
            "mutation_calls_in_order": row["mutation_calls_in_order"],
            "call_references_in_order": row["call_references_in_order"],
            "selection_calls": row["selection_calls"],
            "behavior_references_in_order": row["behavior_references_in_order"],
            "state_references_in_order": row["state_references_in_order"],
            "scope_references": row["scope_references"],
            "safe_sql_object_references": row["safe_sql_object_references"],
            "has_conditional_branch": row["has_conditional_branch"],
            "has_exception_regions": row["has_exception_regions"],
        }

    lifecycle = {name: compact(async_body(name)) for name in LIFECYCLE_METHODS}

    targets = (
        "NGT.Business.Domain.TourDomain.ConfirmTourReceived",
        "NGT.Business.Domain.TourDomain.ConfirmTourPayments",
        "NGT.Business.Domain.TourDomain.ConfirmDistTour",
        "NGT.Business.Domain.TourDomain.WithdrawTourPayments",
        "NGT.Business.Domain.TourDomain.CancelTour",
        "NGT.Business.Domain.TourDomain.DeactivateTour",
        "NGT.Business.Domain.TourDomain.ActivateTour",
        "NGT.Business.Domain.TourDomain.TourReceived",
        "NGT.Business.Domain.TourDomain.TourSent",
        "NGT.Business.Domain.TourDomain.backToReadySendStatusTour",
        "NGT.Business.Domain.TourDomain.CloseTour",
        "NGT.Business.Domain.TourDomain.FinishTour",
        "NGT.Business.Domain.CustomerCallDomain.CancelCallCancelation",
        "NGT.Business.Domain.CustomerCallDomain.AddOrUpdateCustomerCallFromDevice",
        "NGT.Business.Domain.CustomerCallDomain.ReplicateCall",
    )
    callers = {
        target: [
            {
                "file": row["file"],
                "owner": row["owner"],
                "method": row["method"],
                "parameter_count": row["parameter_count"],
            }
            for row in methods
            if target in row["call_references_in_order"]
        ]
        for target in targets
    }

    return {
        "artifact": "varanegar_ngt_tour_call_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "source": {
            "assembly_directory": str(source_directory),
            "assemblies": [
                {key: scan[key] for key in ("file", "sha256", "bytes")}
                for scan in scans
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
            "assembly_count": len(scans),
            "method_body_count": sum(scan["method_body_count"] for scan in scans),
            "method_body_error_count": len(errors),
            "signal_named_body_error_count": sum(1 for row in errors if row["signal_named"]),
            "selected_method_count": len(methods),
            "focused_method_count": len(focused),
            "focused_mutation_method_count": sum(
                1 for row in focused if row["mutation_calls_in_order"]
            ),
            "lifecycle_method_count": sum(1 for row in lifecycle.values() if row is not None),
            "missing_lifecycle_method_count": sum(1 for row in lifecycle.values() if row is None),
        },
        "assembly_scan": [
            {
                key: value
                for key, value in scan.items()
                if key not in {"methods", "body_errors"}
            }
            for scan in scans
        ],
        "body_errors": errors,
        "lifecycle_method_contracts": lifecycle,
        "direct_static_callers": callers,
        "focused_method_contracts": focused,
        "evidence_limits": [
            "Static IL proves compiled references, not active route use or successful requests.",
            "Status getter/setter names are semantic references; they do not alone prove every branch outcome.",
            "Async MoveNext and compiler-generated predicates split one source method across multiple bodies.",
            "Arbitrary literals are never persisted; safe SQL object identifiers are extracted separately.",
            "Absence of a local transaction call does not exclude an ambient or delegated transaction.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
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
