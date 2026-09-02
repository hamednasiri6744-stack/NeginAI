"""Fingerprint the deployed NGT replication-compensation path from PE files.

Assemblies are parsed as inert files. They are never loaded or executed. Raw
string/SQL literals are reduced to hashes, lengths, safe object identifiers,
and named orchestration signals before persistence.
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
TARGET_OWNER = "NGT.Business.Domain.TourDomain"
TARGET_METHOD = "RollBackTour"
TARGET_REFERENCE = f"{TARGET_OWNER}.{TARGET_METHOD}"
ADAPTER_OWNERS = {
    "NGT.VnLite.DataAccess.DataAdapter.VnLiteTourAdapter",
    "NGT.VnSds.DataAccess.DataAdapter.VnSdsTourAdapter",
}
EVENT_SIGNAL = re.compile(
    r"(?:RollBackTour|RollbackTour|UndoReplicate|BeginTransaction|Commit|Rollback|"
    r"ExecuteSqlCommand|DataContext\.(?:Execute|Commit|Rollback)|SaveChanges|UpdateBatch|"
    r"GetTempTableQuery|SCHEMA_EntityUniqueIdList|RetrieveInfo|get_RequestType|set_RequestType|"
    r"ReplicatedCalls|get_EntityUniqueId|entitiesUniqueIdCollection|TourHistory|CustomerCall(?:Payment|Order|Return)|"
    r"BackOffice(?:Receipt|Order|Return|Invoice|UniqueId|Ref|No)|IsRemoved|IsCanceled|CustomRollback)",
    re.IGNORECASE,
)
SQL_OBJECT_REF = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT\s+(?:INTO\s+)?|UPDATE|DELETE\s+FROM|MERGE\s+INTO|FROM|JOIN)\s+"
    r"(?P<object>(?:(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC|INV)\]|"
    r"(?:dbo|NGT|FRU|SLE|GNR|ACC|INV))\.)?"
    r"(?:\[[A-Za-z_][A-Za-z0-9_]*\]|#{0,2}[A-Za-z_][A-Za-z0-9_]*))",
    re.IGNORECASE,
)
LITERAL_SIGNALS = (
    "NGT_RollBackTour",
    "USP_NGT_UndoReplicateTour",
    "#EntityUniqueIdList",
    "EntityUniqueIdList",
    "TourHistory",
    "CustomerCallPayments",
    "BackOfficeReceiptUniqueId",
    "BackOfficeReceiptRef",
    "BackOfficeReceiptNo",
)
GUID_LITERAL = re.compile(
    r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[1-5][0-9A-Fa-f]{3}-"
    r"[89ABab][0-9A-Fa-f]{3}-[0-9A-Fa-f]{12}(?![0-9A-Fa-f])"
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean_object(value: str) -> str:
    return value.replace("[", "").replace("]", "")


def _integer_constant(instruction: Any) -> int | None:
    short = {
        "ldc.i4.m1": -1,
        "ldc.i4.0": 0,
        "ldc.i4.1": 1,
        "ldc.i4.2": 2,
        "ldc.i4.3": 3,
        "ldc.i4.4": 4,
        "ldc.i4.5": 5,
        "ldc.i4.6": 6,
        "ldc.i4.7": 7,
        "ldc.i4.8": 8,
    }
    if instruction.mnemonic in short:
        return short[instruction.mnemonic]
    if instruction.mnemonic in {"ldc.i4", "ldc.i4.s"}:
        return int(instruction.operand)
    return None


def _scan(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pe = dnfile.dnPE(str(path))
    if not getattr(pe, "net", None):
        raise ValueError(f"not a .NET assembly: {path}")
    method_owners, field_owners, type_names = _owner_maps(pe)
    selected: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = type_names[type_index]
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 131072))
            except Exception as exc:  # pragma: no cover - deployed evidence path
                if owner == TARGET_OWNER and _text(method.Name) == TARGET_METHOD:
                    errors.append(
                        {
                            "file": path.name,
                            "owner": owner,
                            "method": _text(method.Name),
                            "error_type": type(exc).__name__,
                        }
                    )
                continue
            calls: list[dict[str, Any]] = []
            events: list[dict[str, Any]] = []
            literal_profiles: list[dict[str, Any]] = []
            request_type_assignments: list[dict[str, int]] = []
            switch_profiles: list[dict[str, Any]] = []
            leave_offsets: list[int] = []
            retrieve_info_result_pop_offsets: list[int] = []
            calls_target = False
            instructions = list(body.instructions)
            for instruction_index, instruction in enumerate(instructions):
                operand = instruction.operand
                if instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    raw = "" if item is None else _text(item.value)
                    signal_counts = {
                        signal: len(re.findall(re.escape(signal), raw, re.I))
                        for signal in LITERAL_SIGNALS
                    }
                    if not any(signal_counts.values()):
                        continue
                    literal_profiles.append(
                        {
                            "offset": instruction.offset,
                            "literal_sha256": _sha256(raw),
                            "literal_length": len(raw),
                            "guid_literal_count": len(GUID_LITERAL.findall(raw)),
                            "safe_sql_object_references": sorted(
                                {
                                    _clean_object(match.group("object"))
                                    for match in SQL_OBJECT_REF.finditer(raw)
                                },
                                key=str.casefold,
                            ),
                            "named_signal_counts": signal_counts,
                        }
                    )
                    continue
                if instruction.mnemonic == "switch":
                    constants = [
                        _integer_constant(candidate)
                        for candidate in instructions[max(0, instruction_index - 5):instruction_index]
                    ]
                    constants = [value for value in constants if value is not None]
                    targets = [int(value) for value in instruction.operand]
                    base = None if not constants else constants[-1]
                    switch_profiles.append(
                        {
                            "offset": instruction.offset,
                            "case_base": base,
                            "case_target_offsets": targets,
                            "request_type_20_target_offset": None
                            if base is None or not (base <= 20 < base + len(targets))
                            else targets[20 - base],
                        }
                    )
                    continue
                if instruction.mnemonic == "leave" or instruction.mnemonic == "leave.s":
                    leave_offsets.append(instruction.offset)
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
                    calls_target = calls_target or value == TARGET_REFERENCE
                    if (
                        value.endswith(".RetrieveInfo")
                        and instruction_index + 1 < len(instructions)
                        and instructions[instruction_index + 1].mnemonic == "pop"
                    ):
                        retrieve_info_result_pop_offsets.append(instruction.offset)
                    if value.endswith("BackOfficeInfoRetrieverViewModel.set_RequestType"):
                        constants = [
                            _integer_constant(candidate)
                            for candidate in instructions[max(0, instruction_index - 4):instruction_index]
                        ]
                        constants = [value for value in constants if value is not None]
                        if constants:
                            request_type_assignments.append(
                                {"offset": instruction.offset, "request_type": constants[-1]}
                            )
                if EVENT_SIGNAL.search(value):
                    events.append(
                        {
                            "offset": instruction.offset,
                            "opcode": instruction.mnemonic,
                            "operand": value,
                        }
                    )
            is_target = owner == TARGET_OWNER and _text(method.Name) == TARGET_METHOD
            is_adapter = owner in ADAPTER_OWNERS and _text(method.Name) == "RetrieveInfo"
            is_case20_selector = _text(method.Name) in {
                "<RetrieveInfo>b__4_20",
                "<RetrieveInfo>b__2_28",
            }
            is_case20_appender = _text(method.Name) in {
                "<RetrieveInfo>b__21",
                "<RetrieveInfo>b__29",
            }
            if not (
                is_target
                or is_adapter
                or is_case20_selector
                or is_case20_appender
                or calls_target
                or literal_profiles
            ):
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
                    "pop_instruction_count": sum(
                        instruction.mnemonic == "pop" for instruction in instructions
                    ),
                    "return_instruction_count": sum(
                        instruction.mnemonic == "ret" for instruction in instructions
                    ),
                    "retrieve_info_call_count": sum(
                        row["operand"].endswith(".RetrieveInfo") for row in calls
                    ),
                    "retrieve_info_result_pop_count": len(
                        retrieve_info_result_pop_offsets
                    ),
                    "is_target_method": is_target,
                    "is_tour_adapter_method": is_adapter,
                    "is_case20_entity_selector": is_case20_selector,
                    "is_case20_temp_row_appender": is_case20_appender,
                    "calls_target_method": calls_target,
                    "event_ledger": events,
                    "target_call_offsets": [
                        row["offset"] for row in calls if row["operand"] == TARGET_REFERENCE
                    ],
                    "literal_profiles": literal_profiles,
                    "request_type_assignments": request_type_assignments,
                    "switch_profiles": switch_profiles,
                    "leave_offsets": leave_offsets,
                }
            )
    return selected, errors


def collect(source_directory: Path) -> dict[str, Any]:
    methods: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    sources = []
    for file_name in ASSEMBLY_FILES:
        path = source_directory / file_name
        part, part_errors = _scan(path)
        methods.extend(part)
        errors.extend(part_errors)
        sources.append(
            {
                "assembly_file": file_name,
                "assembly_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "assembly_bytes": path.stat().st_size,
            }
        )
    target = next((row for row in methods if row["is_target_method"]), None)
    adapters = [row for row in methods if row["is_tour_adapter_method"]]
    selectors = [row for row in methods if row["is_case20_entity_selector"]]
    appenders = [row for row in methods if row["is_case20_temp_row_appender"]]
    target_events = [] if target is None else target["event_ledger"]
    target_literals = [] if target is None else target["literal_profiles"]
    setters = [row for row in target_events if ".set_BackOffice" in row["operand"]]
    transaction_events = [
        row
        for row in target_events
        if re.search(r"(?:BeginTransaction|\.Commit|\.Rollback|CustomRollback)$", row["operand"], re.I)
    ]
    adapter_case_20 = []
    for adapter in adapters:
        switch = next(
            (
                row
                for row in adapter["switch_profiles"]
                if row["request_type_20_target_offset"] is not None
            ),
            None,
        )
        if switch is None:
            continue
        start = switch["request_type_20_target_offset"]
        later_leaves = [value for value in adapter["leave_offsets"] if value > start]
        end = later_leaves[1] + 1 if len(later_leaves) >= 2 else 2**31 - 1
        case_events = [
            row for row in adapter["event_ledger"] if start <= row["offset"] < end
        ]
        case_literals = [
            row for row in adapter["literal_profiles"] if start <= row["offset"] < end
        ]
        adapter_case_20.append(
            {
                "file": adapter["file"],
                "owner": adapter["owner"],
                "request_type": 20,
                "start_offset": start,
                "exclusive_end_offset": end,
                "event_ledger": case_events,
                "literal_profiles": case_literals,
                "active_rollback_sql_signal_count": sum(
                    row["named_signal_counts"]["NGT_RollBackTour"]
                    for row in case_literals
                ),
                "entity_temp_table_signal_count": sum(
                    row["named_signal_counts"]["EntityUniqueIdList"]
                    for row in case_literals
                ),
                "execute_event_count": sum(
                    1 for row in case_events if row["operand"].endswith("DataContext.Execute")
                ),
                "commit_event_count": sum(
                    1 for row in case_events if row["operand"].endswith("DataContext.Commit")
                ),
                "rollback_event_count": sum(
                    1 for row in case_events if row["operand"].endswith("DataContext.Rollback")
                ),
            }
        )
    derived = {
        "target_method_present": target is not None,
        "target_instruction_count": None if target is None else target["instruction_count"],
        "target_has_exception_regions": False if target is None else target["has_exception_regions"],
        "sql_literal_profile_count": len(target_literals),
        "active_rollback_sql_signal_count": sum(
            row["named_signal_counts"]["NGT_RollBackTour"] for row in target_literals
        ),
        "dead_legacy_undo_sql_signal_count": sum(
            row["named_signal_counts"]["USP_NGT_UndoReplicateTour"]
            for row in target_literals
        ),
        "entity_temp_table_signal_count": sum(
            row["named_signal_counts"]["#EntityUniqueIdList"] for row in target_literals
        ),
        "backoffice_crosswalk_setter_count": len(setters),
        "backoffice_crosswalk_setter_members": sorted({row["operand"] for row in setters}),
        "transaction_event_count": len(transaction_events),
        "transaction_event_members": [row["operand"] for row in transaction_events],
        "retrieve_info_call_count": 0
        if target is None
        else target["retrieve_info_call_count"],
        "retrieve_info_result_pop_count": 0
        if target is None
        else target["retrieve_info_result_pop_count"],
        "adapter_result_is_discarded": False
        if target is None
        else target["retrieve_info_call_count"] == 1
        and target["retrieve_info_result_pop_count"] == 1,
        "caller_method_count": sum(1 for row in methods if row["calls_target_method"]),
        "business_request_type_20_assignment_count": 0
        if target is None
        else sum(
            1 for row in target["request_type_assignments"] if row["request_type"] == 20
        ),
        "adapter_request_type_20_contracts": adapter_case_20,
        "case20_entity_selector_contracts": [
            {
                "file": row["file"],
                "owner": row["owner"],
                "method": row["method"],
                "entity_unique_id_getter_count": sum(
                    1 for event in row["event_ledger"] if event["operand"].endswith("get_EntityUniqueId")
                ),
            }
            for row in selectors
        ],
        "case20_temp_row_appender_contracts": [
            {
                "file": row["file"],
                "owner": row["owner"],
                "method": row["method"],
                "entity_collection_reference_count": sum(
                    1 for event in row["event_ledger"] if "entitiesUniqueIdCollection" in event["operand"]
                ),
            }
            for row in appenders
        ],
    }
    return {
        "artifact": "varanegar_ngt_replication_compensation_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS" if target is not None and not errors else "FAIL",
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
            "selected_method_count": len(methods),
            "method_body_error_count": len(errors),
            "instruction_count": sum(row["instruction_count"] for row in methods),
            "target_caller_method_count": derived["caller_method_count"],
            "target_event_count": len(target_events),
            "target_literal_profile_count": len(target_literals),
            "target_crosswalk_setter_count": len(setters),
            "target_retrieve_info_result_pop_count": derived[
                "retrieve_info_result_pop_count"
            ],
            "tour_adapter_method_count": len(adapters),
            "adapter_request_type_20_contract_count": len(adapter_case_20),
            "adapter_case_20_active_rollback_signal_count": sum(
                row["active_rollback_sql_signal_count"] for row in adapter_case_20
            ),
            "case20_entity_selector_count": len(selectors),
            "case20_temp_row_appender_count": len(appenders),
        },
        "method_contracts": methods,
        "rollback_tour_contract": derived,
        "body_errors": errors,
        "evidence_limits": [
            "Static IL proves deployed reference and transaction shape, not successful runtime execution.",
            "Literal bodies are never persisted; hashes and named safe signals cannot recover branch semantics alone.",
            "Linear IL order is not treated as a guaranteed runtime branch without controlled fault injection.",
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
