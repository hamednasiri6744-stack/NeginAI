"""Fingerprint the deployed NGT mobile-return runtime without executing code.

PE metadata and IL bytes are parsed as inert files. Arbitrary literals, raw
identifiers, configuration values and business rows are never persisted.
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


ASSEMBLY_FILES = (
    "NGT.Business.dll",
    "NGT.DataAccess.dll",
    "NGT.WebApi.dll",
    "NGT.VnLite.DataAccess.dll",
    "NGT.VnSds.DataAccess.dll",
)
TARGET_OWNER = re.compile(
    r"(?:CustomerCallReturnDomain\+<(?:CancelCallReturn|UpdateFromNGT)>|"
    r"CustomerCallController\+<CancelCallReturn>|"
    r"CustomerCallDomain\+<AddOrUpdateCustomerCallFromDevice>|"
    r"TourDomain\+<(?:ReplicateTour|NewReplicateTour(?:ForPreviewOrderMode)?)>)d__",
    re.I,
)
TARGET_CALL = re.compile(
    r"(?:CustomerCallReturnDomain\.(?:CancelCallReturn|UpdateFromNGT)|"
    r"TourDomain\.(?:ReplicateTour|NewReplicateTour)|"
    r"CustomerCallReturn(?:Line)?\.set_BackOfficeReturn(?:Order|Invoice))",
    re.I,
)
EVENT_SIGNAL = re.compile(
    r"(?:CustomerCallReturn|BackOfficeReturn|ReplicateReturn|RetSale|RetOrder|"
    r"TourHistory|BeginTransaction|Commit|Rollback|SaveChanges|UpdateBatch|"
    r"AddAsync|UpdateAsync|ExecuteNonQuery|IsCanceled|IsRemoved|OperationDate|"
    r"NewReplicateTour|ReplicateTour|RollBackTour)",
    re.I,
)
SQL_LIKE = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT|UPDATE|DELETE|MERGE|SELECT|CREATE\s+TABLE|DROP\s+TABLE)\b",
    re.I,
)
SQL_OBJECT_REF = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT\s+(?:INTO\s+)?|UPDATE|DELETE\s+FROM|MERGE\s+INTO|FROM|JOIN)\s+"
    r"(?P<object>(?:(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC|INV)\]|"
    r"(?:dbo|NGT|FRU|SLE|GNR|ACC|INV))\.)?"
    r"(?:\[[A-Za-z_][A-Za-z0-9_]*\]|#{0,2}[A-Za-z_][A-Za-z0-9_]*))",
    re.I,
)
GUID_LITERAL = re.compile(
    r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[1-5][0-9A-Fa-f]{3}-"
    r"[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}(?![0-9A-Fa-f])"
)
SQL_SIGNALS = (
    "NGT_DoReplicateTour",
    "CustomerCallReturns",
    "CustomerCallReturnLines",
    "BackOfficeReturnOrder",
    "BackOfficeReturnInvoice",
    "TourHistory",
    "#FinalResult",
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _scan(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError(f"not a .NET assembly: {path}")
    method_owners, field_owners, type_names = _owner_maps(pe)
    selected: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    body_count = 0
    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = type_names[type_index]
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 131072))
            except Exception as exc:  # pragma: no cover - deployed evidence path
                if TARGET_OWNER.search(owner):
                    errors.append(
                        {
                            "file": path.name,
                            "owner": owner,
                            "method": _text(method.Name),
                            "error_type": type(exc).__name__,
                        }
                    )
                continue
            body_count += 1
            calls: list[dict[str, Any]] = []
            events: list[dict[str, Any]] = []
            literals: list[dict[str, Any]] = []
            for instruction in body.instructions:
                operand = instruction.operand
                if instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    raw = "" if item is None else _text(item.value)
                    if not SQL_LIKE.search(raw):
                        continue
                    literals.append(
                        {
                            "offset": instruction.offset,
                            "literal_sha256": _sha(raw),
                            "literal_length": len(raw),
                            "guid_literal_count": len(GUID_LITERAL.findall(raw)),
                            "safe_sql_object_references": sorted(
                                {
                                    match.group("object").replace("[", "").replace("]", "")
                                    for match in SQL_OBJECT_REF.finditer(raw)
                                },
                                key=str.casefold,
                            ),
                            "named_signal_counts": {
                                signal: len(re.findall(re.escape(signal), raw, re.I))
                                for signal in SQL_SIGNALS
                            },
                        }
                    )
                    continue
                if not isinstance(operand, Token):
                    continue
                value = _text(
                    _resolve_token(pe, operand, method_owners, field_owners, type_names)
                )
                if instruction.mnemonic in {"call", "callvirt", "newobj"}:
                    calls.append(
                        {
                            "offset": instruction.offset,
                            "opcode": instruction.mnemonic,
                            "operand": value,
                        }
                    )
                if EVENT_SIGNAL.search(value):
                    events.append(
                        {
                            "offset": instruction.offset,
                            "opcode": instruction.mnemonic,
                            "operand": value,
                        }
                    )
            is_named_target = bool(TARGET_OWNER.search(owner)) and _text(method.Name) == "MoveNext"
            calls_target = any(TARGET_CALL.search(row["operand"]) for row in calls)
            has_return_crosswalk_setter = any(
                re.search(r"\.set_BackOfficeReturn(?:Order|Invoice)", row["operand"], re.I)
                for row in calls
            )
            if not (is_named_target or calls_target or has_return_crosswalk_setter):
                continue
            selected.append(
                {
                    "file": path.name,
                    "owner": owner,
                    "method": _text(method.Name),
                    "method_metadata_token": f"0x06{method_index.row_index:06x}",
                    "parameter_count": _parameter_count(method),
                    "signature_hex": _signature_bytes(method).hex(),
                    "instruction_count": len(body.instructions),
                    "has_exception_regions": bool(body.exception_handlers),
                    "is_named_target": is_named_target,
                    "calls_target": calls_target,
                    "event_ledger": events,
                    "target_call_ledger": [
                        row for row in calls if TARGET_CALL.search(row["operand"])
                    ],
                    "sql_template_profiles": literals,
                }
            )
    return selected, errors, body_count


def _count(events: list[dict[str, Any]], pattern: str) -> int:
    rx = re.compile(pattern, re.I)
    return sum(bool(rx.search(row["operand"])) for row in events)


def collect(source_directory: Path) -> dict[str, Any]:
    methods: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    sources = []
    body_count = 0
    for file_name in ASSEMBLY_FILES:
        path = source_directory / file_name
        part, part_errors, part_body_count = _scan(path)
        methods.extend(part)
        errors.extend(part_errors)
        body_count += part_body_count
        sources.append(
            {
                "assembly_file": file_name,
                "assembly_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "assembly_bytes": path.stat().st_size,
            }
        )
    cancel = next(
        (row for row in methods if "CustomerCallReturnDomain+<CancelCallReturn>" in row["owner"]),
        None,
    )
    update = next(
        (row for row in methods if "CustomerCallReturnDomain+<UpdateFromNGT>" in row["owner"]),
        None,
    )
    replicate = next(
        (row for row in methods if "TourDomain+<ReplicateTour>" in row["owner"]),
        None,
    )
    ingest = next(
        (
            row
            for row in methods
            if "CustomerCallDomain+<AddOrUpdateCustomerCallFromDevice>" in row["owner"]
        ),
        None,
    )
    endpoint = next(
        (row for row in methods if "CustomerCallController+<CancelCallReturn>" in row["owner"]),
        None,
    )
    update_callers = [
        row
        for row in methods
        if any(
            call["operand"].endswith("CustomerCallReturnDomain.UpdateFromNGT")
            for call in row["target_call_ledger"]
        )
    ]

    def events(row: dict[str, Any] | None) -> list[dict[str, Any]]:
        return [] if row is None else row["event_ledger"]

    all_events = [event for row in methods for event in row["event_ledger"]]
    replicate_events = events(replicate)
    replication_offsets = [
        row["offset"]
        for row in replicate_events
        if row["operand"].endswith("TourDomain.NewReplicateTour")
    ]
    return_setter_events = [
        row
        for row in replicate_events
        if re.search(r"\.set_BackOfficeReturn(?:Order|Invoice)", row["operand"], re.I)
    ]
    transaction_begin_offsets = [
        row["offset"]
        for row in replicate_events
        if row["operand"].endswith("Database.BeginTransaction")
    ]
    commit_offsets = [
        row["offset"]
        for row in replicate_events
        if row["operand"].endswith("DbContextTransaction.Commit")
    ]
    contract = {
        "cancel_domain_present": cancel is not None,
        "cancel_endpoint_present": endpoint is not None,
        "cancel_endpoint_calls_domain_count": _count(
            events(endpoint), r"CustomerCallReturnDomain\.CancelCallReturn$"
        ),
        "cancel_is_canceled_setter_count": _count(events(cancel), r"\.set_IsCanceled$"),
        "cancel_is_removed_setter_count": _count(events(cancel), r"\.set_IsRemoved$"),
        "cancel_save_changes_count": _count(events(cancel), r"SaveChanges"),
        "cancel_transaction_event_count": _count(
            events(cancel), r"BeginTransaction|\.Commit$|\.Rollback$"
        ),
        "update_from_ngt_present": update is not None,
        "update_from_ngt_save_changes_count": _count(events(update), r"SaveChanges"),
        "update_from_ngt_is_canceled_setter_count": _count(
            events(update), r"\.set_IsCanceled$"
        ),
        "update_from_ngt_is_removed_setter_count": _count(
            events(update), r"\.set_IsRemoved$"
        ),
        "update_from_ngt_transaction_event_count": _count(
            events(update), r"BeginTransaction|\.Commit$|\.Rollback$"
        ),
        "update_from_ngt_caller_count": len(update_callers),
        "update_from_ngt_caller_save_changes_count": sum(
            _count(events(row), r"SaveChanges") for row in update_callers
        ),
        "update_from_ngt_caller_transaction_event_count": sum(
            _count(events(row), r"BeginTransaction|\.Commit$|\.Rollback$")
            for row in update_callers
        ),
        "ingest_method_present": ingest is not None,
        "ingest_save_changes_count": _count(events(ingest), r"SaveChanges"),
        "replicate_tour_present": replicate is not None,
        "replicate_tour_new_replication_call_count": _count(
            events(replicate), r"TourDomain\.NewReplicateTour$"
        ),
        "replicate_tour_return_projection_event_count": _count(
            events(replicate), r"CustomerCallReturn|ReplicateReturn"
        ),
        "replicate_tour_transaction_event_count": _count(
            events(replicate), r"BeginTransaction|\.Commit$|\.Rollback$"
        ),
        "runtime_return_crosswalk_setter_count": _count(
            all_events, r"\.set_BackOfficeReturn(?:Order|Invoice)"
        ),
        "runtime_return_crosswalk_setter_members": sorted(
            {
                row["operand"]
                for row in all_events
                if re.search(r"\.set_BackOfficeReturn(?:Order|Invoice)", row["operand"], re.I)
            }
        ),
        "replicate_tour_return_crosswalk_setter_count": len(return_setter_events),
        "replicate_tour_line_crosswalk_setter_count": sum(
            "CustomerCallReturnLine.set_BackOfficeReturn" in row["operand"]
            for row in return_setter_events
        ),
        "replicate_tour_call_collection_setter_count": sum(
            "CustomerCall.set_BackOfficeReturnOrderNoCollection" in row["operand"]
            for row in return_setter_events
        ),
        "new_replication_call_offset": None
        if not replication_offsets
        else min(replication_offsets),
        "first_managed_transaction_begin_offset": None
        if not transaction_begin_offsets
        else min(transaction_begin_offsets),
        "first_return_crosswalk_setter_offset": None
        if not return_setter_events
        else min(row["offset"] for row in return_setter_events),
        "new_replication_call_precedes_managed_transaction_in_linear_il": bool(
            replication_offsets
            and transaction_begin_offsets
            and min(replication_offsets) < min(transaction_begin_offsets)
        ),
        "new_replication_call_precedes_return_crosswalk_setters_in_linear_il": bool(
            replication_offsets
            and return_setter_events
            and min(replication_offsets)
            < min(row["offset"] for row in return_setter_events)
        ),
        "managed_commit_exists_before_return_crosswalk_setters_in_linear_il": bool(
            commit_offsets
            and return_setter_events
            and any(
                offset < min(row["offset"] for row in return_setter_events)
                for offset in commit_offsets
            )
        ),
        "managed_commit_exists_after_return_crosswalk_setters_in_linear_il": bool(
            commit_offsets
            and return_setter_events
            and any(
                offset > max(row["offset"] for row in return_setter_events)
                for offset in commit_offsets
            )
        ),
    }
    required = all(
        (
            contract["cancel_domain_present"],
            contract["cancel_endpoint_present"],
            contract["update_from_ngt_present"],
            contract["ingest_method_present"],
            contract["replicate_tour_present"],
        )
    )
    return {
        "artifact": "varanegar_ngt_return_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS" if required and not errors else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_execution": 0,
            "application_endpoint_or_command_executions": 0,
            "database_connections": 0,
            "configuration_or_business_data_reads": 0,
            "raw_string_or_sql_literals_persisted": 0,
            "guid_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "parsed_method_body_count": body_count,
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "method_body_error_count": len(errors),
            "return_crosswalk_setter_count": contract[
                "runtime_return_crosswalk_setter_count"
            ],
        },
        "return_runtime_contract": contract,
        "method_contracts": methods,
        "body_errors": errors,
        "evidence_limits": [
            "Static IL proves deployed references and local transaction signals, not successful runtime execution.",
            "State-machine IL is reduced to named call/property signals; branch reachability requires controlled tests.",
            "Absence of a managed-code crosswalk setter does not exclude SQL-side write-back.",
        ],
    }


def main() -> int:
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    logging.getLogger("dnfile.stream").setLevel(logging.CRITICAL)
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
    print(json.dumps(payload["return_runtime_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
