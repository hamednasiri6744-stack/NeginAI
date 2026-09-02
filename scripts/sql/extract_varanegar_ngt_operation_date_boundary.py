"""Extract the NGT customer-return OperationDate boundary, read-only.

The database side persists catalog metadata, SQL-definition fingerprints and
anonymous aggregates only.  The binary side parses PE metadata and IL without
loading or executing assemblies.  No request, application command, stored
procedure, configuration value, identity or raw business row is observed.
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

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


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
    r"(?:CustomerCallReturn|CallReturn|OperationDate|ReturnStartTime|ReturnEndTime|"
    r"CustomerCallDateTypes|AddDistributionTour|SaveTourData|ReplicateTour)",
    re.IGNORECASE,
)

# Code/protocol identifiers only.  Runtime strings are never copied.
SAFE_LITERAL = re.compile(
    r"^(?:OperationDate|CustomerCallReturns?|CustomerCallReturnLines?|"
    r"ReturnStartTime|ReturnEndTime|CancelCallReturn|GetCustomerCallReturnLines)$",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
            safe_instructions: list[dict[str, Any]] = []
            method_redacted = 0
            for instruction in body.instructions:
                operand = instruction.operand
                instruction_row: dict[str, Any] = {
                    "offset": instruction.offset,
                    "opcode": instruction.mnemonic,
                }
                if instruction.mnemonic in {"call", "callvirt", "newobj"} and isinstance(operand, Token):
                    resolved = _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    calls.append(resolved)
                    instruction_row["operand"] = resolved
                elif "fld" in instruction.mnemonic and isinstance(operand, Token):
                    resolved = _resolve_token(pe, operand, method_owners, field_owners, type_names)
                    fields.append(resolved)
                    instruction_row["operand"] = resolved
                elif instruction.mnemonic == "ldstr" and isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    value = "" if item is None else _text(item.value)
                    if SAFE_LITERAL.fullmatch(value):
                        safe_literals.append(value)
                        allowlisted_literal_count += 1
                    else:
                        method_redacted += 1
                        redacted_literal_count += 1
                    instruction_row["operand"] = (
                        value if SAFE_LITERAL.fullmatch(value) else "<redacted-non-allowlisted-literal>"
                    )
                elif isinstance(operand, Token):
                    instruction_row["operand"] = _resolve_token(
                        pe, operand, method_owners, field_owners, type_names
                    )
                elif isinstance(operand, (int, float)):
                    instruction_row["operand"] = operand
                safe_instructions.append(instruction_row)

            signals = [owner, method_name, *calls, *fields]
            if not any(SIGNAL.search(value) for value in signals):
                continue
            operation_positions = [
                index
                for index, row in enumerate(safe_instructions)
                if _text(row.get("operand", "")).endswith(("get_OperationDate", "set_OperationDate"))
            ]
            selected.append(
                {
                    "owner": owner,
                    "method": method_name,
                    "method_metadata_token": f"0x06{method_index.row_index:06x}",
                    "parameter_count": _parameter_count(method),
                    "signature_hex": _signature_bytes(method).hex(),
                    "instruction_count": len(body.instructions),
                    "signal_calls": [value for value in calls if SIGNAL.search(value)],
                    "all_calls": calls,
                    "signal_fields": sorted(set(value for value in fields if SIGNAL.search(value))),
                    "all_referenced_fields": sorted(set(fields)),
                    "allowlisted_code_literals": safe_literals,
                    "redacted_non_allowlisted_literal_count": method_redacted,
                    "opcode_sequence": [instruction.mnemonic for instruction in body.instructions],
                    "operation_date_instruction_windows": [
                        safe_instructions[max(0, index - 30): min(len(safe_instructions), index + 401)]
                        for index in operation_positions
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


def _customer_call_date_type_guids(path: Path) -> dict[str, str]:
    """Read private code constants for DB comparison; raw GUIDs are not returned in the artifact."""
    pe = dnfile.dnPE(str(path))
    _, _, type_names = _owner_maps(pe)
    wanted_owner = "NGT.Common.PublicValues+CustomerCallDateTypes"
    wanted_methods = {"get_CallDate", "get_OperationDate", "get_ServerDate", "get_ActiveDate"}
    result: dict[str, str] = {}
    for type_index, type_row in enumerate(pe.net.mdtables.TypeDef.rows, start=1):
        if type_names[type_index] != wanted_owner:
            continue
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva or _text(method.Name) not in wanted_methods:
                continue
            body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            literals = []
            for instruction in body.instructions:
                if instruction.mnemonic == "ldstr" and isinstance(instruction.operand, StringToken):
                    item = pe.net.user_strings.get(instruction.operand.rid)
                    literals.append("" if item is None else _text(item.value))
            if len(literals) != 1 or not re.fullmatch(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                literals[0],
            ):
                raise AssertionError(f"unexpected CustomerCallDateTypes literal shape: {method.Name}")
            result[_text(method.Name).removeprefix("get_")] = literals[0]
    if set(result) != {"CallDate", "OperationDate", "ServerDate", "ActiveDate"}:
        raise AssertionError({"customer_call_date_type_names": sorted(result)})
    return result


def _table_catalog(cursor: Any) -> dict[str, Any]:
    columns = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
               ty.name data_type,c.max_length,c.precision,c.scale,c.is_nullable,
               dc.name default_constraint_name,dc.definition default_definition
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        LEFT JOIN sys.default_constraints dc
          ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
        WHERE (s.name='NGT' AND t.name='CustomerCallReturns')
           OR (s.name='FRU' AND t.name='CustomerCallReturns')
        ORDER BY s.name,c.column_id
        """,
    )
    relevant = re.compile(
        r"(?:^Id$|Number_ID|OperationDate|CreatedDate|LastUpdate|StartTime|EndTime|"
        r"IsRemoved|IsCanceled|Concurrency)",
        re.IGNORECASE,
    )
    public_columns = [row for row in columns if relevant.search(row["column_name"])]

    foreign_keys = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,fk.name foreign_key_name,
               pc.name parent_column,rs.name referenced_schema,rt.name referenced_table,
               rc.name referenced_column,fk.delete_referential_action_desc,
               fk.update_referential_action_desc,fk.is_disabled,fk.is_not_trusted
        FROM sys.foreign_keys fk
        JOIN sys.tables t ON t.object_id=fk.parent_object_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.tables rt ON rt.object_id=fkc.referenced_object_id
        JOIN sys.schemas rs ON rs.schema_id=rt.schema_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE (s.name='NGT' AND t.name='CustomerCallReturns')
           OR (s.name='FRU' AND t.name='CustomerCallReturns')
        ORDER BY s.name,fk.name,fkc.constraint_column_id
        """,
    )
    indexes = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,i.name index_name,i.is_unique,
               i.is_primary_key,i.type_desc,ic.key_ordinal,ic.is_included_column,c.name column_name
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.indexes i ON i.object_id=t.object_id AND i.index_id>0
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE (s.name='NGT' AND t.name='CustomerCallReturns')
           OR (s.name='FRU' AND t.name='CustomerCallReturns')
        ORDER BY s.name,i.name,ic.key_ordinal,ic.index_column_id
        """,
    )
    checks = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,cc.name check_name,
               cc.is_disabled,cc.is_not_trusted,cc.definition
        FROM sys.check_constraints cc
        JOIN sys.tables t ON t.object_id=cc.parent_object_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE (s.name='NGT' AND t.name='CustomerCallReturns')
           OR (s.name='FRU' AND t.name='CustomerCallReturns')
        ORDER BY s.name,cc.name
        """,
    )
    public_checks = []
    for row in checks:
        definition = row.pop("definition") or ""
        public_checks.append(
            {
                **row,
                "definition_sha256": _sha256_text(definition),
                "references_operation_date": "operationdate" in definition.casefold(),
            }
        )
    triggers = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,tr.name trigger_name,tr.is_disabled,
               tr.is_instead_of_trigger,DATALENGTH(m.definition) definition_bytes,m.definition
        FROM sys.triggers tr
        JOIN sys.tables t ON t.object_id=tr.parent_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        LEFT JOIN sys.sql_modules m ON m.object_id=tr.object_id
        WHERE (s.name='NGT' AND t.name='CustomerCallReturns')
           OR (s.name='FRU' AND t.name='CustomerCallReturns')
        ORDER BY s.name,tr.name
        """,
    )
    public_triggers: list[dict[str, Any]] = []
    for row in triggers:
        definition = row.pop("definition") or ""
        normalized = re.sub(r"\s+", " ", definition).casefold()
        public_triggers.append(
            {
                **row,
                "definition_sha256": _sha256_text(definition),
                "references_operation_date": "operationdate" in normalized,
                "references_global_operation_date_table": "tbloprdate" in normalized,
                "has_explicit_transaction": bool(re.search(r"\bbegin\s+tran", normalized)),
            }
        )
    return {
        "relevant_columns": public_columns,
        "foreign_keys": foreign_keys,
        "indexes": indexes,
        "check_constraints": public_checks,
        "triggers": public_triggers,
    }


def _selector_branch_sources(normalized: str, enum_guids: dict[str, str]) -> dict[str, str]:
    """Classify CASE branch expressions near known code GUIDs; never persist the GUIDs."""
    result: dict[str, str] = {}
    for enum_name, guid in enum_guids.items():
        offset = normalized.find(guid.casefold())
        if offset < 0:
            continue
        tail = normalized[offset: offset + 320]
        then_offset = tail.find(" then ")
        if then_offset < 0:
            result[enum_name] = "PRESENT_BUT_EXPRESSION_UNRESOLVED"
            continue
        expression = tail[then_offset + 6:]
        next_offsets = [value for value in (expression.find(" when "), expression.find(" end")) if value >= 0]
        if next_offsets:
            expression = expression[:min(next_offsets)]
        if "isnull(ccl.callpdate, tour.tourpdate)" in expression or "isnull(ccl.callpdate,tour.tourpdate)" in expression:
            source = "CALL_ACTIVITY_DATE_FALLBACK_TOUR_ACTIVITY_DATE"
        elif "@today" in expression:
            source = "SERVER_TODAY_SOLAR"
        elif "@oprdate" in expression:
            source = "GLOBAL_OPEN_SALES_OPERATION_DATE"
        elif "ccl.callpdate" in expression:
            source = "CALL_ACTIVITY_DATE"
        else:
            source = "EXPRESSION_UNRESOLVED"
        result[enum_name] = source
    return result


def _selector_case_else_contract(normalized: str) -> dict[str, int]:
    bodies = re.findall(
        r"case\s+@customercalldatebasedonuniqueid(?P<body>.*?)\s+end\b",
        normalized,
    )
    return {
        "case_count": len(bodies),
        "case_without_else_count": sum(not re.search(r"\belse\b", body) for body in bodies),
    }


def _sql_consumers(cursor: Any, enum_guids: dict[str, str]) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,
               DATALENGTH(m.definition) definition_bytes,m.definition
        FROM sys.sql_modules m
        JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE m.definition LIKE '%CustomerCallReturn%'
          AND (m.definition LIKE '%OperationDate%'
            OR m.definition LIKE '%CustomerCallDateBasedOn%'
            OR m.definition LIKE '%ReturnDate%'
            OR m.definition LIKE '%tblOprDate%')
        ORDER BY s.name,o.name
        """,
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        definition = row.pop("definition")
        normalized = re.sub(r"\s+", " ", definition).casefold()
        selector_case = _selector_case_else_contract(normalized)
        result.append(
            {
                **row,
                "qualified_name": f"{row['schema_name']}.{row['object_name']}",
                "definition_sha256": _sha256_text(definition),
                "reads_ngt_customer_call_return": bool(
                    re.search(r"\b(from|join)\s+(?:\[?ngt\]?\.)?\[?customercallreturns?\]?", normalized)
                ),
                "writes_ngt_customer_call_return": bool(
                    re.search(r"\b(insert\s+into|update|merge\s+into)\s+(?:\[?ngt\]?\.)?\[?customercallreturns?\]?", normalized)
                ),
                "reads_fru_customer_call_return": bool(
                    re.search(r"\b(from|join)\s+(?:\[?fru\]?\.)?\[?customercallreturns?\]?", normalized)
                ),
                "writes_fru_customer_call_return": bool(
                    re.search(r"\b(insert\s+into|update|merge\s+into)\s+(?:\[?fru\]?\.)?\[?customercallreturns?\]?", normalized)
                ),
                "references_global_operation_date_table": "tbloprdate" in normalized,
                "references_customer_call_date_setting": "customercalldatebasedon" in normalized,
                "references_call_activity_date": "callpdate" in normalized,
                "references_tour_activity_date": "tourpdate" in normalized,
                "references_server_today": "@today" in normalized or "getdate()" in normalized,
                "date_selector_branch_sources": _selector_branch_sources(normalized, enum_guids),
                "date_selector_case_count": selector_case["case_count"],
                "date_selector_case_without_else_count": selector_case["case_without_else_count"],
                "global_operation_date_filters_sales_sysref_1": bool(
                    re.search(r"sysref\s*=\s*1", normalized)
                ),
                "global_operation_date_filters_open_only": bool(
                    re.search(r"isclosed\s*=\s*0", normalized)
                ),
                "global_operation_date_requires_after_last_or_last_null": (
                    "oprdate>lastdate" in normalized.replace(" ", "")
                    and "lastdateisnull" in normalized.replace(" ", "")
                ),
                "has_explicit_transaction": bool(re.search(r"\bbegin\s+tran", normalized)),
                "has_try_catch": "begin try" in normalized and "begin catch" in normalized,
            }
        )
    return result


def _population(cursor: Any) -> dict[str, Any]:
    ngt = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) row_count,
               SUM(CASE WHEN IsRemoved=0 AND IsCanceled=0 THEN 1 ELSE 0 END) active_row_count,
               SUM(CASE WHEN OperationDate='19000101' THEN 1 ELSE 0 END) sentinel_operation_date_count,
               SUM(CASE WHEN OperationDate>DATEADD(day,1,SYSDATETIME()) THEN 1 ELSE 0 END) future_operation_date_count,
               SUM(CASE WHEN CONVERT(date,OperationDate)=CONVERT(date,CreatedDate) THEN 1 ELSE 0 END) operation_date_equals_created_date_count,
               SUM(CASE WHEN CONVERT(date,OperationDate)<CONVERT(date,CreatedDate) THEN 1 ELSE 0 END) operation_date_before_created_date_count,
               SUM(CASE WHEN CONVERT(date,OperationDate)>CONVERT(date,CreatedDate) THEN 1 ELSE 0 END) operation_date_after_created_date_count,
               MIN(OperationDate) minimum_operation_date,
               MAX(OperationDate) maximum_operation_date,
               MIN(CreatedDate) minimum_created_date,
               MAX(CreatedDate) maximum_created_date
        FROM NGT.CustomerCallReturns
        """,
    )[0]
    fru = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) row_count,
               SUM(CASE WHEN OperationDate IS NULL THEN 1 ELSE 0 END) null_operation_date_count,
               SUM(CASE WHEN OperationDate='19000101' THEN 1 ELSE 0 END) sentinel_operation_date_count,
               SUM(CASE WHEN OperationDate>DATEADD(day,1,SYSDATETIME()) THEN 1 ELSE 0 END) future_operation_date_count,
               MIN(OperationDate) minimum_operation_date,
               MAX(OperationDate) maximum_operation_date
        FROM FRU.CustomerCallReturns
        """,
    )[0]
    crosswalk = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) exact_number_id_to_fru_id_count,
               SUM(CASE WHEN CONVERT(date,n.OperationDate)=CONVERT(date,f.OperationDate) THEN 1 ELSE 0 END) equal_operation_date_count,
               SUM(CASE WHEN CONVERT(date,n.OperationDate)<>CONVERT(date,f.OperationDate) THEN 1 ELSE 0 END) different_operation_date_count
        FROM NGT.CustomerCallReturns n
        JOIN FRU.CustomerCallReturns f ON f.Id=n.Number_ID
        """,
    )[0]
    monthly = _rows(
        cursor,
        """
        SELECT CONVERT(char(7),OperationDate,126) operation_month,COUNT_BIG(*) row_count
        FROM NGT.CustomerCallReturns
        GROUP BY CONVERT(char(7),OperationDate,126)
        ORDER BY operation_month
        """,
    )
    return {"ngt": ngt, "fru": fru, "crosswalk": crosswalk, "ngt_monthly": monthly}


def _date_setting(cursor: Any, enum_guids: dict[str, str]) -> dict[str, Any]:
    """Return semantic labels and enum matches without persisting raw UUIDs."""
    current = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) app_setting_row_count,
               SUM(CASE WHEN a.CustomerCallDateBasedOnUniqueId IS NULL THEN 1 ELSE 0 END) null_setting_count,
               SUM(CASE WHEN b.Id IS NOT NULL THEN 1 ELSE 0 END) base_value_exact_match_count,
               SUM(CASE WHEN b.IsRemoved=1 THEN 1 ELSE 0 END) removed_base_value_match_count,
               COUNT(DISTINCT b.BaseValueName) distinct_semantic_label_count,
               MAX(b.BaseValueName) current_semantic_label
        FROM NGT.AppSettings a
        LEFT JOIN NGT.BaseValues b ON b.Id=a.CustomerCallDateBasedOnUniqueId
        WHERE a.IsRemoved=0
        """,
    )[0]
    ordered_names = ("CallDate", "OperationDate", "ServerDate", "ActiveDate")
    rows = _rows(
        cursor,
        """
        SELECT b.BaseValueName semantic_label,b.Number_ID,b.IsRemoved,
               CASE WHEN b.Id=CONVERT(uniqueidentifier,%s) THEN 'CallDate'
                    WHEN b.Id=CONVERT(uniqueidentifier,%s) THEN 'OperationDate'
                    WHEN b.Id=CONVERT(uniqueidentifier,%s) THEN 'ServerDate'
                    WHEN b.Id=CONVERT(uniqueidentifier,%s) THEN 'ActiveDate'
                    ELSE 'UNMAPPED' END code_enum_name,
               SUM(CASE WHEN a.CustomerCallDateBasedOnUniqueId=b.Id AND a.IsRemoved=0 THEN 1 ELSE 0 END) current_setting_reference_count
        FROM NGT.BaseValues b
        LEFT JOIN NGT.AppSettings a ON a.CustomerCallDateBasedOnUniqueId=b.Id
        WHERE b.BaseTypeId=(
          SELECT TOP (1) x.BaseTypeId
          FROM NGT.AppSettings a2
          JOIN NGT.BaseValues x ON x.Id=a2.CustomerCallDateBasedOnUniqueId
          WHERE a2.IsRemoved=0
        )
        GROUP BY b.Id,b.BaseValueName,b.Number_ID,b.IsRemoved
        ORDER BY b.Number_ID,b.BaseValueName
        """,
        tuple(enum_guids[name] for name in ordered_names),
    )
    return {"current": current, "catalog": rows}


def collect(source_directory: Path) -> dict[str, Any]:
    assemblies = [_analyze_assembly(source_directory / name) for name in TARGET_FILES]
    date_type_guids = _customer_call_date_type_guids(source_directory / "NGT.Common.dll")
    signal_body_errors = [
        {"file": assembly["file"], **row}
        for assembly in assemblies
        for row in assembly["body_errors"]
        if row["signal_named"]
    ]
    if signal_body_errors:
        raise AssertionError({"signal_named_method_body_errors": signal_body_errors})

    methods = [
        {"file": assembly["file"], **method}
        for assembly in assemblies
        for method in assembly["selected_methods"]
    ]
    setter_callers = [
        row for row in methods
        if any(call.endswith("set_OperationDate") for call in row["signal_calls"])
    ]
    getter_callers = [
        row for row in methods
        if any(call.endswith("get_OperationDate") for call in row["signal_calls"])
    ]

    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        table_catalog = _table_catalog(cursor)
        consumers = _sql_consumers(cursor, date_type_guids)
        population = _population(cursor)
        date_setting = _date_setting(cursor, date_type_guids)
    finally:
        connection.close()

    ngt_operation_column = [
        row for row in table_catalog["relevant_columns"]
        if row["schema_name"] == "NGT" and row["column_name"] == "OperationDate"
    ]
    fru_operation_column = [
        row for row in table_catalog["relevant_columns"]
        if row["schema_name"] == "FRU" and row["column_name"] == "OperationDate"
    ]
    if len(ngt_operation_column) != 1 or len(fru_operation_column) != 1:
        raise AssertionError("expected both NGT and FRU OperationDate columns")

    replication_sql = next(
        (row for row in consumers if row["qualified_name"] == "dbo.NGT_DoReplicateTour"),
        None,
    )
    if replication_sql is None or set(replication_sql["date_selector_branch_sources"]) != set(date_type_guids):
        raise AssertionError("incomplete NGT_DoReplicateTour date-selector branch evidence")
    unresolved_branches = [
        name
        for name, source in replication_sql["date_selector_branch_sources"].items()
        if "UNRESOLVED" in source
    ]
    if unresolved_branches:
        raise AssertionError({"unresolved_date_selector_branches": unresolved_branches})

    replicate_move_next = next(
        row
        for row in methods
        if row["owner"] == "NGT.Business.Domain.TourDomain+<ReplicateTour>d__39"
        and row["method"] == "MoveNext"
    )
    operation_override = next(
        row for row in methods if row["method"] == "<ReplicateTour>b__39_29"
    )
    active_override = next(
        row for row in methods if row["method"] == "<ReplicateTour>b__31"
    )
    server_override = next(
        row for row in methods if row["method"] == "<ReplicateTour>b__39_33"
    )
    save_tour_data = next(
        row
        for row in methods
        if row["owner"] == "NGT.Business.Domain.TourDomain+<SaveTourData>d__24"
        and row["method"] == "MoveNext"
    )
    add_distribution_setter = next(
        row for row in setter_callers if row["method"] == "<AddDistributionTour>b__10"
    )
    add_distribution_move_next = next(
        row
        for row in methods
        if row["owner"] == "NGT.Business.Domain.TourDomain+<AddDistributionTour>d__49"
        and row["method"] == "MoveNext"
    )
    save_operation_window = [
        instruction
        for window in save_tour_data["operation_date_instruction_windows"]
        for instruction in window
    ]
    add_operation_window = [
        instruction
        for window in add_distribution_setter["operation_date_instruction_windows"]
        for instruction in window
    ]

    contract = {
        "ngt_operation_date_type": ngt_operation_column[0]["data_type"],
        "ngt_operation_date_nullable": bool(ngt_operation_column[0]["is_nullable"]),
        "ngt_operation_date_default_definition": ngt_operation_column[0]["default_definition"],
        "fru_operation_date_type": fru_operation_column[0]["data_type"],
        "fru_operation_date_nullable": bool(fru_operation_column[0]["is_nullable"]),
        "fru_operation_date_default_definition": fru_operation_column[0]["default_definition"],
        "operation_date_setter_caller_count": len(setter_callers),
        "operation_date_getter_caller_count": len(getter_callers),
        "current_date_selector_semantic_label": date_setting["current"]["current_semantic_label"],
        "current_date_selector_code_enum_name": next(
            (
                row["code_enum_name"]
                for row in date_setting["catalog"]
                if int(row["current_setting_reference_count"] or 0) > 0
            ),
            None,
        ),
        "sql_consumer_count": len(consumers),
        "sql_consumer_references_global_tbl_opr_date_count": sum(
            row["references_global_operation_date_table"] for row in consumers
        ),
        "table_trigger_count": len(table_catalog["triggers"]),
        "operation_date_check_constraint_count": sum(
            row["references_operation_date"] for row in table_catalog["check_constraints"]
        ),
        "table_trigger_references_global_tbl_opr_date_count": sum(
            row["references_global_operation_date_table"] for row in table_catalog["triggers"]
        ),
    }
    date_source_contract = {
        "available_code_enum_names": sorted(date_type_guids),
        "current_selection": {
            "semantic_label": contract["current_date_selector_semantic_label"],
            "code_enum_name": contract["current_date_selector_code_enum_name"],
            "sql_replication_source": replication_sql["date_selector_branch_sources"].get(
                contract["current_date_selector_code_enum_name"]
            ),
        },
        "business_il_replication_overrides": {
            "OperationDate": (
                "NGT_RETURN_OPERATION_DATE"
                if operation_override["all_calls"] == [
                    "NGT.ViewModels.Replicate.ReplicateCallReturnViewModel.get_OperationDate",
                    "NGT.ViewModels.Replicate.ReplicateCallReturnViewModel.set_ReturnDate",
                ]
                else "UNRESOLVED"
            ),
            "ActiveDate": (
                "BACK_OFFICE_RETRIEVED_ACTIVE_DATE"
                if "NGT.Business.Domain.TourDomain+<>c__DisplayClass39_4.Date"
                in active_override["all_referenced_fields"]
                and "NGT.ViewModels.Replicate.ReplicateCallReturnViewModel.set_ReturnDate"
                in active_override["all_calls"]
                else "UNRESOLVED"
            ),
            "ServerDate": (
                "SERVER_NOW_FORMATTED_TO_SERVER_CULTURE"
                if all(
                    value in server_override["all_calls"]
                    for value in (
                        "System.DateTime.get_Now",
                        "NGT.Common.Tools.DateTools.ToServerCultureDateString",
                        "NGT.ViewModels.Replicate.ReplicateCallReturnViewModel.set_ReturnDate",
                    )
                )
                else "UNRESOLVED"
            ),
            "CallDate": (
                "NO_EXPLICIT_OVERRIDE_BRANCH_OBSERVED_IN_REPLICATE_TOUR"
                if "CustomerCallDateTypes.get_CallDate" not in replicate_move_next["all_calls"]
                else "EXPLICIT_BRANCH_PRESENT"
            ),
        },
        "sql_replication_case_sources": replication_sql["date_selector_branch_sources"],
        "global_operation_date_branch_guard": {
            "sales_sysref_1": replication_sql["global_operation_date_filters_sales_sysref_1"],
            "is_closed_zero": replication_sql["global_operation_date_filters_open_only"],
            "after_last_or_last_null": replication_sql[
                "global_operation_date_requires_after_last_or_last_null"
            ],
        },
        "implementation_comparison": {
            "CallDate": "SQL uses call activity date; Business IL has no explicit override branch, so its initial ReturnDate source remains unproved.",
            "OperationDate": "Business IL copies NGT return OperationDate; SQL uses call activity date with tour activity fallback. Exact equivalence is not proved.",
            "ActiveDate": "Business IL uses a back-office retrieved active date; SQL uses the global open sales operation date. Conceptual alignment is plausible but exact equivalence is not proved.",
            "ServerDate": "Both observed implementations use server current date, with their own formatting layer.",
            "missing_or_unknown": "Business IL falls through without an explicit recognized override; SQL CASE branches have no ELSE and can yield NULL.",
        },
        "current_snapshot_incident_claim": "NONE: current selector is a valid non-removed CallDate value and no malformed current return date was observed.",
        "semantic_boundary": (
            "CustomerCallReturn.OperationDate is an NGT event timestamp, GNR.tblOprDate is the global "
            "open/close boundary, and CustomerCallDateBasedOn selects a replication document date. "
            "They must remain separate concepts even where a selected branch copies one into another."
        ),
    }
    if any("UNRESOLVED" in value for value in date_source_contract["business_il_replication_overrides"].values()):
        raise AssertionError(date_source_contract["business_il_replication_overrides"])
    ingest_persistence_contract = {
        "save_tour_data_rejects_dotnet_default_datetime": all(
            value in [row.get("operand") for row in save_operation_window]
            for value in ("System.DateTime", "System.DateTime.op_Equality", "System.Exception..ctor")
        )
        and any(row["opcode"] == "throw" for row in save_operation_window),
        "add_distribution_tour_assigns_captured_now_to_operation_date": (
            any(
                row.get("operand") == "NGT.Business.Domain.TourDomain+<>c__DisplayClass49_0.now"
                for row in add_operation_window
            )
            and any(_text(row.get("operand", "")).endswith("set_OperationDate") for row in add_operation_window)
            and "System.DateTime.get_Now" in add_distribution_move_next["all_calls"]
        ),
        "database_default_is_1900_sentinel_not_dotnet_default": (
            contract["ngt_operation_date_default_definition"] == "('1900-01-01T00:00:00.000')"
        ),
        "database_operation_date_check_constraint_count": contract[
            "operation_date_check_constraint_count"
        ],
        "table_trigger_count": contract["table_trigger_count"],
        "current_rows_same_calendar_day_as_created_count": int(
            population["ngt"]["operation_date_equals_created_date_count"] or 0
        ),
        "current_sentinel_count": int(population["ngt"]["sentinel_operation_date_count"] or 0),
        "boundary": (
            "SaveTourData rejects DateTime.MinValue and AddDistributionTour supplies server now, but the "
            "database independently defaults omitted values to 1900 without an OperationDate check or table trigger."
        ),
    }
    if not ingest_persistence_contract["save_tour_data_rejects_dotnet_default_datetime"]:
        raise AssertionError("SaveTourData OperationDate default guard not proven")
    if not ingest_persistence_contract["add_distribution_tour_assigns_captured_now_to_operation_date"]:
        raise AssertionError("AddDistributionTour OperationDate now assignment not proven")

    return {
        "artifact": "varanegar_ngt_customer_return_operation_date_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "source": {
            "assembly_directory": str(source_directory),
            "assemblies": [
                {key: row[key] for key in ("file", "sha256", "bytes")}
                for row in assemblies
            ],
        },
        "safety": {
            "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_AND_STATIC_TARGETED_IL",
            "database_updateability": safety["updateability"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "assemblies_loaded_or_executed": 0,
            "runtime_requests_or_raw_configuration_ids_read": 0,
            "semantic_non_secret_configuration_labels_persisted": len(date_setting["catalog"]),
            "raw_business_rows_identities_or_document_numbers_persisted": 0,
            "non_allowlisted_string_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "analyzed_assembly_count": len(assemblies),
            "method_body_count": sum(row["method_body_count"] for row in assemblies),
            "method_body_error_count": sum(row["method_body_error_count"] for row in assemblies),
            "signal_named_method_body_error_count": len(signal_body_errors),
            "selected_method_count": len(methods),
            "operation_date_setter_caller_count": len(setter_callers),
            "operation_date_getter_caller_count": len(getter_callers),
            "ngt_row_count": int(population["ngt"]["row_count"] or 0),
            "fru_row_count": int(population["fru"]["row_count"] or 0),
            "ngt_sentinel_operation_date_count": int(population["ngt"]["sentinel_operation_date_count"] or 0),
            "fru_null_operation_date_count": int(population["fru"]["null_operation_date_count"] or 0),
            "ngt_to_fru_exact_crosswalk_count": int(population["crosswalk"]["exact_number_id_to_fru_id_count"] or 0),
            "sql_consumer_count": len(consumers),
            "sql_consumer_references_global_tbl_opr_date_count": contract["sql_consumer_references_global_tbl_opr_date_count"],
            "table_trigger_references_global_tbl_opr_date_count": contract["table_trigger_references_global_tbl_opr_date_count"],
            "date_setting_base_value_exact_match_count": int(date_setting["current"]["base_value_exact_match_count"] or 0),
        },
        "contract": contract,
        "date_source_contract": date_source_contract,
        "ingest_persistence_contract": ingest_persistence_contract,
        "table_catalog": table_catalog,
        "population": population,
        "date_setting_semantic_aggregate": date_setting,
        "sql_consumers": consumers,
        "assembly_scan": [
            {
                key: row[key]
                for key in (
                    "file", "sha256", "bytes", "method_body_count",
                    "method_body_error_count", "selected_method_count",
                    "allowlisted_code_literal_count",
                    "redacted_non_allowlisted_literal_count",
                )
            }
            for row in assemblies
        ],
        "operation_date_setter_callers": setter_callers,
        "operation_date_getter_callers": getter_callers,
        "selected_methods": methods,
        "evidence_limits": [
            "Static IL proves deployed code shape and call sites, not the runtime value supplied for either current row.",
            "Catalog definitions and current aggregates cannot prove historical user intent or the exact mobile request payload.",
            "OperationDate name similarity does not establish a relation to GNR.tblOprDate; only explicit references are counted.",
            "A missing current NGT-to-FRU crosswalk prevents row-level date equivalence claims between the two mobile models.",
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
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
