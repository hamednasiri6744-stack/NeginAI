"""Extract the deployed NGT payment replication adapter from PE metadata only.

Assemblies are parsed as files and are never loaded or executed. Arbitrary
string literals are never persisted. SQL-looking literals are reduced to a
hash, length, safe object identifiers, and named payment/crosswalk signals.
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
from extract_varanegar_ngt_payment_runtime_boundary import _scan as _payment_scan  # noqa: E402


TARGET_FILE = "NGT.Business.dll"
CROSSWALK_SCAN_FILES = (
    "NGT.Business.dll",
    "NGT.DataAccess.dll",
    "NGT.WebApi.dll",
)
TARGET_OWNER = re.compile(
    r"NGT\.Business\.Domain\.TourDomain\+<(?:ReplicateTour|NewReplicateTour(?:ForPreviewOrderMode)?)[^>]*>d__\d+",
    re.IGNORECASE,
)
EVENT_SIGNAL = re.compile(
    r"(?:BeginTransaction|Commit|Rollback|ExecuteSqlCommand|ToListAsync|"
    r"SaveChanges|UpdateBatch|ReplicateToBackOffice|FinishTour|RollBackTour|"
    r"ReplicateResultViewModel|BackOfficeReceipt|BackOfficeUniqueId|BackOfficeRef|"
    r"BackOfficeNo|EntityUniqueId|CustomerCallPayment|TourHistory|CustomCommit|"
    r"CustomRollback|ReplicateTour)",
    re.IGNORECASE,
)
SQL_OBJECT_REF = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT\s+(?:INTO\s+)?|UPDATE|DELETE\s+FROM|MERGE\s+INTO|FROM|JOIN)\s+"
    r"(?P<object>(?:(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC|INV)\]|"
    r"(?:dbo|NGT|FRU|SLE|GNR|ACC|INV))\.)?"
    r"(?:\[[A-Za-z_][A-Za-z0-9_]*\]|#{0,2}[A-Za-z_][A-Za-z0-9_]*))",
    re.IGNORECASE,
)
SQL_LIKE = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT|UPDATE|DELETE|MERGE|SELECT|CREATE\s+TABLE|DROP\s+TABLE)\b",
    re.IGNORECASE,
)
GUID_LITERAL = re.compile(
    r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[1-5][0-9A-Fa-f]{3}-"
    r"[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}(?![0-9A-Fa-f])"
)
SQL_SIGNALS = (
    "NGT_DoReplicateTour",
    "CustomerCallPayments",
    "BackOfficeReceiptUniqueId",
    "BackOfficeReceiptRef",
    "BackOfficeReceiptNo",
    "TourHistory",
    "#CustomerCallIdList",
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean_object(value: str) -> str:
    return value.replace("[", "").replace("]", "")


def _method_contracts(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError(f"not a .NET assembly: {path}")
    method_owners, field_owners, type_names = _owner_maps(pe)
    methods: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = type_names[type_index]
        if not TARGET_OWNER.search(owner):
            continue
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva or _text(method.Name) != "MoveNext":
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:  # pragma: no cover - evidence path
                errors.append(
                    {
                        "owner": owner,
                        "method": _text(method.Name),
                        "error_type": type(exc).__name__,
                    }
                )
                continue
            events: list[dict[str, Any]] = []
            sql_templates: list[dict[str, Any]] = []
            call_counts: dict[str, int] = {}
            for instruction in body.instructions:
                operand = instruction.operand
                if instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    raw = "" if item is None else _text(item.value)
                    if not SQL_LIKE.search(raw):
                        continue
                    refs = sorted(
                        {
                            _clean_object(match.group("object"))
                            for match in SQL_OBJECT_REF.finditer(raw)
                        },
                        key=str.casefold,
                    )
                    sql_templates.append(
                        {
                            "offset": instruction.offset,
                            "literal_sha256": _sha256(raw),
                            "literal_length": len(raw),
                            "guid_literal_count": len(GUID_LITERAL.findall(raw)),
                            "safe_sql_object_references": refs,
                            "named_signal_counts": {
                                signal: len(re.findall(re.escape(signal), raw, re.I))
                                for signal in SQL_SIGNALS
                            },
                        }
                    )
                elif isinstance(operand, Token):
                    resolved = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                    value = _text(resolved)
                    if instruction.mnemonic in {"call", "callvirt", "newobj"}:
                        call_counts[value] = call_counts.get(value, 0) + 1
                    if EVENT_SIGNAL.search(value):
                        events.append(
                            {
                                "offset": instruction.offset,
                                "opcode": instruction.mnemonic,
                                "operand": value,
                            }
                        )
            methods.append(
                {
                    "owner": owner,
                    "method": _text(method.Name),
                    "method_metadata_token": f"0x06{method_index.row_index:06x}",
                    "parameter_count": _parameter_count(method),
                    "signature_hex": _signature_bytes(method).hex(),
                    "instruction_count": len(body.instructions),
                    "has_exception_regions": bool(body.exception_handlers),
                    "event_ledger": events,
                    "selected_call_counts": [
                        {"call": name, "count": count}
                        for name, count in sorted(call_counts.items(), key=lambda item: item[0].casefold())
                        if EVENT_SIGNAL.search(name)
                    ],
                    "sql_template_profiles": sql_templates,
                }
            )
    return methods, errors


def _crosswalk_reference_candidates(source_directory: Path) -> list[dict[str, Any]]:
    candidates = []
    for file_name in CROSSWALK_SCAN_FILES:
        scan = _payment_scan(source_directory / file_name)
        for row in scan["methods"]:
            refs = [
                *row["call_references_in_order"],
                *row["behavior_references_in_order"],
                *row["state_references_in_order"],
            ]
            crosswalk_refs = [
                value for value in refs if "backofficereceipt" in value.casefold()
            ]
            if not crosswalk_refs:
                continue
            setters = [value for value in crosswalk_refs if ".set_" in value]
            getters = [value for value in crosswalk_refs if ".get_" in value]
            candidates.append(
                {
                    "file": file_name,
                    "owner": row["owner"],
                    "method": row["method"],
                    "method_metadata_token": row["method_metadata_token"],
                    "instruction_count": row["instruction_count"],
                    "crosswalk_setter_references": setters,
                    "crosswalk_getter_references": getters,
                    "mutation_calls_in_order": row["mutation_calls_in_order"],
                    "safe_sql_object_references": row["safe_sql_object_references"],
                    "has_conditional_branch": row["has_conditional_branch"],
                    "has_exception_regions": row["has_exception_regions"],
                }
            )
    return candidates


def collect(source_directory: Path) -> dict[str, Any]:
    path = source_directory / TARGET_FILE
    methods, errors = _method_contracts(path)
    crosswalk_candidates = _crosswalk_reference_candidates(source_directory)
    replicate = next(
        (row for row in methods if re.search(r"\+<ReplicateTour>d__", row["owner"])),
        None,
    )
    replicate_events = [] if replicate is None else replicate["event_ledger"]
    new_replicate_offsets = [
        row["offset"]
        for row in replicate_events
        if row["operand"].endswith("TourDomain.NewReplicateTour")
    ]
    payment_setter_events = [
        row
        for row in replicate_events
        if "CustomerCallPayment.set_BackOfficeReceipt" in row["operand"]
    ]
    commit_offsets = [
        row["offset"]
        for row in replicate_events
        if row["operand"].endswith(".Commit")
        or row["operand"].endswith(".CustomCommit")
    ]
    first_payment_setter_offset = (
        None if not payment_setter_events else min(row["offset"] for row in payment_setter_events)
    )
    derived = {
        "replicate_tour_method_present": replicate is not None,
        "new_replicate_tour_call_count": len(new_replicate_offsets),
        "payment_crosswalk_setter_event_count": len(payment_setter_events),
        "payment_crosswalk_setter_members": sorted(
            {row["operand"] for row in payment_setter_events}
        ),
        "commit_event_count": len(commit_offsets),
        "first_payment_setter_offset": first_payment_setter_offset,
        "new_replication_call_precedes_payment_setters_in_linear_il": bool(
            new_replicate_offsets
            and first_payment_setter_offset is not None
            and min(new_replicate_offsets) < first_payment_setter_offset
        ),
        "commit_exists_before_payment_setters_in_linear_il": bool(
            first_payment_setter_offset is not None
            and any(offset < first_payment_setter_offset for offset in commit_offsets)
        ),
        "commit_exists_after_payment_setters_in_linear_il": bool(
            first_payment_setter_offset is not None
            and any(offset > first_payment_setter_offset for offset in commit_offsets)
        ),
        "warning": (
            "Linear IL order is a strong control-flow clue but branch reachability must not be "
            "treated as one guaranteed runtime path without controlled fault injection."
        ),
    }
    return {
        "artifact": "varanegar_ngt_payment_replication_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS" if methods and not errors else "FAIL",
        "source": {
            "assembly_file": path.name,
            "assembly_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "assembly_bytes": path.stat().st_size,
        },
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
            "selected_method_count": len(methods),
            "method_body_error_count": len(errors),
            "instruction_count": sum(row["instruction_count"] for row in methods),
            "event_count": sum(len(row["event_ledger"]) for row in methods),
            "sql_template_count": sum(len(row["sql_template_profiles"]) for row in methods),
            "crosswalk_reference_candidate_count": len(crosswalk_candidates),
            "crosswalk_setter_candidate_count": sum(
                1 for row in crosswalk_candidates if row["crosswalk_setter_references"]
            ),
            "crosswalk_setter_with_mutation_call_count": sum(
                1
                for row in crosswalk_candidates
                if row["crosswalk_setter_references"] and row["mutation_calls_in_order"]
            ),
        },
        "method_contracts": methods,
        "crosswalk_reference_candidates": crosswalk_candidates,
        "replicate_tour_crosswalk_writeback_contract": derived,
        "body_errors": errors,
        "evidence_limits": [
            "Static IL proves deployed call/field shape, not successful runtime execution.",
            "SQL templates are fingerprinted and reduced to safe identifiers; parameter values and text are not persisted.",
            "ExecuteSqlCommand call order does not prove which conditional branch ran for a specific tour.",
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
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
