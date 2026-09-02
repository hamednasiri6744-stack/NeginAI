"""Extract redacted static SQL bindings for the RPT-15 stock report family.

The target assembly is parsed as PE/CLR metadata and IL. It is never imported,
loaded, reflected at runtime, or executed. Raw SQL literals are not persisted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _full_type_name,
    _owner_maps,
    _resolve_token,
    _text,
)

TARGET_TYPE = "VN.SDS.Stock.DataAccess.DataAdapter.StockGoods.StockGoodsAdapter"
TARGET_METHODS = {
    "GetBatchHistory", "GetBatchesCardexReport", "GetCardexReport",
    "GetFreeInvoiceList", "GetListOfDamagedInventory",
    "GetListOfPOrderWithOutTransfer", "GetListOfUnapprovedOutputs",
    "GetOpenOrderList", "GetOpenSaleList", "GetReservedGoodsReasonList",
}
EXPECTED_SHA256 = "05ad31992521fe0b169fc63d5747d2f84c88e6f5b565e21879957ef40078853f"
OBJECT_RE = re.compile(r"(?i)\b(?:exec(?:ute)?\s+)?((?:\[?[A-Za-z_]\w*\]?\.){1,2}\[?[A-Za-z_]\w*\]?)")
EXEC_RE = re.compile(r"(?i)\bexec(?:ute)?\s+((?:\[?[A-Za-z_]\w*\]?\.){0,2}\[?[A-Za-z_]\w*\]?)")
PARAM_RE = re.compile(r"@[A-Za-z_]\w*")
FORMAT_RE = re.compile(r"\{(\d+)(?:[^}]*)\}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_object_candidates(sql: str) -> list[str]:
    candidates = []
    for match in [*EXEC_RE.finditer(sql), *OBJECT_RE.finditer(sql)]:
        value = match.group(1).replace("[", "").replace("]", "")
        head = value.split(".", 1)[0].casefold()
        if head in {"system", "thunderstruck"}:
            continue
        if value not in candidates:
            candidates.append(value)
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assembly", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw = args.assembly.read_bytes()
    assembly_hash = sha256_bytes(raw)
    pe = dnfile.dnPE(str(args.assembly))
    method_owners, field_owners = _owner_maps(pe)
    types = getattr(pe.net.mdtables, "TypeDef", None)
    target = next((row for row in types.rows if _full_type_name(row) == TARGET_TYPE), None)
    errors = []
    if assembly_hash != EXPECTED_SHA256:
        errors.append("assembly_sha256_mismatch")
    if target is None:
        errors.append("target_type_missing")
    rows = []
    if target is not None:
        for index in target.MethodList or []:
            method = index.row
            name = _text(getattr(method, "Name", ""))
            if name not in TARGET_METHODS or not method.Rva:
                continue
            body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            calls, property_getters, literals = set(), set(), []
            for instruction in body.instructions:
                operand = instruction.operand
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(operand, Token):
                    call = _resolve_token(pe, operand, method_owners, field_owners)
                    calls.add(call)
                    if ".get_" in call:
                        property_getters.add(call.rsplit(".get_", 1)[1])
                if isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    value = "" if item is None else _text(item)
                    literals.append(value)
            sql_literals = [value for value in literals if "DataContext.Query" not in value and ("@" in value or "{" in value or "exec" in value.casefold())]
            literal_rows = [{
                "sha256": sha256_bytes(value.encode("utf-8")),
                "length": len(value),
                "object_candidates": safe_object_candidates(value),
                "named_parameters": sorted(set(PARAM_RE.findall(value)), key=str.casefold),
                "format_argument_indices": sorted({int(x) for x in FORMAT_RE.findall(value)}),
                "statement_shape": "EXEC_OR_PROCEDURE_CALL" if "exec" in value.casefold() else "FORMATTED_QUERY_OR_CALL",
            } for value in sql_literals]
            rows.append({
                "method": name,
                "instruction_count": len(body.instructions),
                "uses_data_context_query": "Thunderstruck.DataContext.Query" in calls,
                "uses_string_format": "System.String.Format" in calls,
                "entity_property_getters": sorted(property_getters),
                "redacted_sql_literals": literal_rows,
                "raw_sql_persisted": False,
            })
    rows.sort(key=lambda row: row["method"])
    found = {row["method"] for row in rows}
    if found != TARGET_METHODS:
        errors.append("target_method_set_incomplete")
    if any(not row["uses_data_context_query"] or not row["redacted_sql_literals"] for row in rows):
        errors.append("query_or_sql_literal_missing")
    payload = {
        "artifact": "varanegar_stock_report_query_bindings_20260829",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "source": {"file_name": args.assembly.name, "size_bytes": args.assembly.stat().st_size, "sha256": assembly_hash, "expected_sha256": EXPECTED_SHA256},
        "safety": {"mode": "STATIC_PE_CLR_METADATA_AND_IL", "assembly_loads_or_executions": 0, "database_connections": 0, "query_or_procedure_executions": 0, "raw_sql_literals_persisted": 0, "business_rows_or_values_read_or_persisted": 0},
        "summary": {"target_method_count": len(TARGET_METHODS), "extracted_method_count": len(rows), "query_method_count": sum(row["uses_data_context_query"] for row in rows), "redacted_sql_literal_count": sum(len(row["redacted_sql_literals"]) for row in rows), "exact_object_candidate_method_count": sum(bool(row["redacted_sql_literals"][0]["object_candidates"]) for row in rows if row["redacted_sql_literals"]), "validation_error_count": len(errors)},
        "methods": rows,
        "validation_errors": errors,
        "confidence": {"method_to_literal_binding": "CONFIRMED_STATIC_IL", "runtime_execution": "UNPROVEN", "result_parity": "UNPROVEN"},
        "limits": ["Object names and parameters are statically parsed from redacted string literals; runtime branches and server resolution are not proven.", "No SQL text, business literal, row identity, or result value is persisted."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve()); print(payload["validation"]); print(json.dumps(payload["summary"]))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
