"""Fingerprint the managed NGT sale-crosswalk write-back path from static IL."""

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
from dncil.clr.token import Token

WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
if str(WINDOWS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SCRIPTS))
from extract_varanegar_ngt_authorization_runtime_boundary import (  # noqa: E402
    _owner_maps,
    _parameter_count,
    _resolve_token,
    _signature_bytes,
)

ASSEMBLY_FILES = ("NGT.Business.dll", "NGT.DataAccess.dll", "NGT.WebApi.dll")
OWNER = re.compile(
    r"(?:TourDomain\+<(?:ReplicateTour|SaveTourData)>|"
    r"StockLevelDomain\+<AddConflictVoucherToCustomerCall>)d__",
    re.I,
)
SIGNAL = re.compile(
    r"(?:CustomerCallOrder\.set_(?:BackOfficeInvoice|Sale)|NewReplicateTour|"
    r"BeginTransaction|DbContextTransaction\.(?:Commit|Rollback)|SaveChanges|UpdateBatch)",
    re.I,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _scan(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    pe = dnfile.dnPE(str(path))
    method_owners, field_owners, type_names = _owner_maps(pe)
    methods: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    body_count = 0
    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        owner = type_names[type_index]
        if not OWNER.search(owner):
            continue
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva or _text(method.Name) != "MoveNext":
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 131072))
            except Exception as exc:  # pragma: no cover
                errors.append(
                    {"file": path.name, "owner": owner, "error_type": type(exc).__name__}
                )
                continue
            body_count += 1
            events = []
            for instruction in body.instructions:
                if not isinstance(instruction.operand, Token):
                    continue
                value = _text(
                    _resolve_token(
                        pe, instruction.operand, method_owners, field_owners, type_names
                    )
                )
                if SIGNAL.search(value):
                    events.append(
                        {
                            "offset": instruction.offset,
                            "opcode": instruction.mnemonic,
                            "operand": value,
                        }
                    )
            methods.append(
                {
                    "file": path.name,
                    "owner": owner,
                    "method": _text(method.Name),
                    "method_metadata_token": f"0x06{method_index.row_index:06x}",
                    "parameter_count": _parameter_count(method),
                    "signature_hex": _signature_bytes(method).hex(),
                    "instruction_count": len(body.instructions),
                    "has_exception_regions": bool(body.exception_handlers),
                    "event_ledger": events,
                }
            )
    return methods, errors, body_count


def collect(source_directory: Path) -> dict[str, Any]:
    methods: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    sources = []
    body_count = 0
    for file_name in ASSEMBLY_FILES:
        path = source_directory / file_name
        part, part_errors, count = _scan(path)
        methods.extend(part)
        errors.extend(part_errors)
        body_count += count
        sources.append(
            {
                "assembly_file": file_name,
                "assembly_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "assembly_bytes": path.stat().st_size,
            }
        )
    replicate = next(
        (row for row in methods if "TourDomain+<ReplicateTour>" in row["owner"]), None
    )
    replicate_events = [] if replicate is None else replicate["event_ledger"]
    setters = [
        row
        for row in replicate_events
        if "CustomerCallOrder.set_BackOfficeInvoice" in row["operand"]
        or "CustomerCallOrder.set_SaleIdSDS" in row["operand"]
        or "CustomerCallOrder.set_SaleNoSDS" in row["operand"]
        or "CustomerCallOrder.set_SaleOfficeRefSDS" in row["operand"]
    ]
    new_offsets = [
        row["offset"]
        for row in replicate_events
        if row["operand"].endswith("TourDomain.NewReplicateTour")
    ]
    begin_offsets = [
        row["offset"]
        for row in replicate_events
        if row["operand"].endswith("Database.BeginTransaction")
    ]
    commits = [
        row["offset"]
        for row in replicate_events
        if row["operand"].endswith("DbContextTransaction.Commit")
    ]
    contract = {
        "replicate_tour_present": replicate is not None,
        "new_replication_call_count": len(new_offsets),
        "sale_crosswalk_setter_count": len(setters),
        "sale_crosswalk_setter_members": sorted({row["operand"] for row in setters}),
        "new_replication_call_precedes_managed_transaction_in_linear_il": bool(
            new_offsets and begin_offsets and min(new_offsets) < min(begin_offsets)
        ),
        "new_replication_call_precedes_sale_crosswalk_setters_in_linear_il": bool(
            new_offsets and setters and min(new_offsets) < min(row["offset"] for row in setters)
        ),
        "managed_commit_exists_before_sale_crosswalk_setters_in_linear_il": bool(
            commits and setters and any(x < min(row["offset"] for row in setters) for x in commits)
        ),
        "managed_commit_exists_after_sale_crosswalk_setters_in_linear_il": bool(
            commits and setters and any(x > max(row["offset"] for row in setters) for x in commits)
        ),
    }
    return {
        "artifact": "varanegar_ngt_sale_replication_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS" if replicate is not None and not errors else "FAIL",
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
            "parsed_target_method_body_count": body_count,
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "method_body_error_count": len(errors),
            "sale_crosswalk_setter_count": len(setters),
        },
        "sale_runtime_contract": contract,
        "method_contracts": methods,
        "body_errors": errors,
        "evidence_limits": [
            "Linear IL order is a strong control-flow clue, not branch execution proof.",
            "Static setter references do not prove historical invocation frequency.",
            "Assemblies were parsed as inert files and never loaded or executed.",
        ],
    }


def main() -> int:
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
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
    print(json.dumps(payload["sale_runtime_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
