"""Extract redacted semantic footprints for selected extension SQL modules.

Definitions are read from the local read-only clone and parsed in memory. The
artifact stores hashes, counts, parameter metadata and resolved object names;
it never stores module text, string literals, business rows, or credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


MODULES: tuple[dict[str, str], ...] = (
    {"object": "dbo.usp_ReplicateSalesReceipt", "capability": "pos.session", "role": "receipt replication command"},
    {"object": "dbo.USP_SDSNET_DealersDayPathList_SAVE", "capability": "tablet.dealer_day_path", "role": "dealer-day list persistence candidate"},
    {"object": "dbo.USP_SDSNET_DealersDayPath_SAVE", "capability": "tablet.dealer_day_path", "role": "dealer-day detail persistence candidate"},
    {"object": "SLE.USP_SDSNET_POSLineDiscountValidation", "capability": "pos.linear_discount", "role": "linear-discount validation"},
    {"object": "dbo.usp_sdsnet_WebConfigSetting_Save", "capability": "configuration.web_service", "role": "web-service configuration persistence candidate"},
    {"object": "dbo.usp_sdsnet_UserDCAccessRights_Save", "capability": "authorization.stock_accounting_access", "role": "organization-scope grant persistence candidate"},
    {"object": "dbo.usp_sdsnet_ConfirmBaseChargeDevice", "capability": "pos.charge_device", "role": "charge-device confirmation candidate"},
    {"object": "dbo.USP_SDSNET_VisitTemplate_Save", "capability": "tablet.visit_template", "role": "visit-template persistence candidate"},
)


def _mask_comments_and_strings(sql: str) -> str:
    result = list(sql)
    index = 0
    state = "code"
    while index < len(sql):
        char = sql[index]
        nxt = sql[index + 1] if index + 1 < len(sql) else ""
        if state == "code":
            if char == "'":
                result[index] = " "
                state = "string"
            elif char == "-" and nxt == "-":
                result[index] = result[index + 1] = " "
                state = "line_comment"
                index += 1
            elif char == "/" and nxt == "*":
                result[index] = result[index + 1] = " "
                state = "block_comment"
                index += 1
        elif state == "string":
            result[index] = " "
            if char == "'":
                if nxt == "'":
                    result[index + 1] = " "
                    index += 1
                else:
                    state = "code"
        elif state == "line_comment":
            if char in "\r\n":
                state = "code"
            else:
                result[index] = " "
        elif state == "block_comment":
            result[index] = " "
            if char == "*" and nxt == "/":
                result[index + 1] = " "
                index += 1
                state = "code"
        index += 1
    return "".join(result)


def _clean_identifier(value: str) -> str:
    return value.replace("[", "").replace("]", "").rstrip(";,)")


def _module_contract(cursor: Any, item: dict[str, str], catalog_names: dict[str, list[str]]) -> dict[str, Any]:
    identity = _rows(
        cursor,
        """
        SELECT o.object_id,s.name AS schema_name,o.name AS object_name,o.type_desc,m.definition
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE o.object_id=OBJECT_ID(%s)
        """,
        (item["object"],),
    )
    if not identity:
        return {**item, "found": False}
    row = identity[0]
    object_id = int(row.pop("object_id"))
    definition = row.pop("definition") or ""
    masked = _mask_comments_and_strings(definition)
    parameters = _rows(
        cursor,
        """
        SELECT p.parameter_id,p.name AS parameter_name,TYPE_NAME(p.user_type_id) AS data_type,
               p.max_length,p.precision,p.scale,p.is_output
        FROM sys.parameters p WHERE p.object_id=%s ORDER BY p.parameter_id
        """,
        (object_id,),
    )
    dependencies = _rows(
        cursor,
        """
        SELECT DISTINCT COALESCE(d.referenced_schema_name,OBJECT_SCHEMA_NAME(d.referenced_id)) AS schema_name,
               COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) AS object_name,
               COALESCE(o.type_desc,'UNRESOLVED_OR_COLUMN_REFERENCE') AS type_desc
        FROM sys.sql_expression_dependencies d
        LEFT JOIN sys.objects o ON o.object_id=d.referenced_id
        WHERE d.referencing_id=%s
          AND COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) IS NOT NULL
        ORDER BY schema_name,object_name,type_desc
        """,
        (object_id,),
    )

    operation_pattern = re.compile(
        r"\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE(?:\s+INTO)?)\s+((?:\[[^\]]+\]|[A-Za-z_][\w$#]*)(?:\s*\.\s*(?:\[[^\]]+\]|[A-Za-z_][\w$#]*))?)",
        re.IGNORECASE,
    )
    operations = []
    for match in operation_pattern.finditer(masked):
        verb = re.sub(r"\s+", "_", match.group(1).upper())
        raw_target = re.sub(r"\s+", "", _clean_identifier(match.group(2)))
        parts = raw_target.split(".")
        normalized = raw_target
        resolution = "UNRESOLVED_LEXICAL_TARGET"
        if len(parts) == 2:
            key = raw_target.casefold()
            if key in catalog_names:
                normalized = catalog_names[key][0]
                resolution = "RESOLVED_SCHEMA_OBJECT"
        else:
            candidates = catalog_names.get(parts[0].casefold(), [])
            if len(candidates) == 1:
                normalized = candidates[0]
                resolution = "RESOLVED_UNIQUE_OBJECT_NAME"
            elif len(candidates) > 1:
                resolution = "AMBIGUOUS_UNQUALIFIED_OBJECT_NAME"
        operations.append({"verb": verb, "target": normalized, "resolution": resolution})

    keyword_counts = {
        "begin_transaction": len(re.findall(r"\bBEGIN\s+TRAN(?:SACTION)?\b", masked, re.IGNORECASE)),
        "commit": len(re.findall(r"\bCOMMIT(?:\s+TRAN(?:SACTION)?)?\b", masked, re.IGNORECASE)),
        "rollback": len(re.findall(r"\bROLLBACK(?:\s+TRAN(?:SACTION)?)?\b", masked, re.IGNORECASE)),
        "try": len(re.findall(r"\bBEGIN\s+TRY\b", masked, re.IGNORECASE)),
        "catch": len(re.findall(r"\bBEGIN\s+CATCH\b", masked, re.IGNORECASE)),
        "throw": len(re.findall(r"\bTHROW\b", masked, re.IGNORECASE)),
        "raiserror": len(re.findall(r"\bRAISERROR\b", masked, re.IGNORECASE)),
        "cursor": len(re.findall(r"\bCURSOR\b", masked, re.IGNORECASE)),
        "merge": len(re.findall(r"\bMERGE\b", masked, re.IGNORECASE)),
        "temp_table_tokens": len(re.findall(r"#[A-Za-z_][\w$#]*", masked)),
        "nolock": len(re.findall(r"\bNOLOCK\b", masked, re.IGNORECASE)),
        "sp_executesql": len(re.findall(r"\bsp_executesql\b", masked, re.IGNORECASE)),
        "exec_tokens": len(re.findall(r"\bEXEC(?:UTE)?\b", masked, re.IGNORECASE)),
    }
    dynamic_sql_signal = bool(keyword_counts["sp_executesql"] or re.search(r"\bEXEC(?:UTE)?\s*\(", masked, re.IGNORECASE))
    operation_counts = Counter(operation["verb"] for operation in operations)
    resolved_targets = sorted({operation["target"] for operation in operations if operation["resolution"].startswith("RESOLVED")})
    return {
        **item,
        "found": True,
        **row,
        "definition_length": len(definition),
        "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest(),
        "definition_persisted": False,
        "parameter_count": len(parameters),
        "parameters": parameters,
        "dependency_count": len(dependencies),
        "dependencies": dependencies,
        "lexical_operation_count": len(operations),
        "lexical_operation_counts": dict(sorted(operation_counts.items())),
        "lexical_operations": operations,
        "resolved_mutation_targets": resolved_targets,
        "keyword_counts": keyword_counts,
        "has_explicit_transaction_envelope": bool(keyword_counts["begin_transaction"] and keyword_counts["commit"]),
        "has_explicit_error_handler": bool(keyword_counts["catch"] and (keyword_counts["throw"] or keyword_counts["raiserror"])),
        "has_dynamic_sql_signal": dynamic_sql_signal,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            catalog = _rows(
                cursor,
                """
                SELECT s.name AS schema_name,o.name AS object_name
                FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE o.is_ms_shipped=0
                """,
            )
            catalog_names: dict[str, list[str]] = {}
            for row in catalog:
                full = f"{row['schema_name']}.{row['object_name']}"
                catalog_names.setdefault(full.casefold(), []).append(full)
                catalog_names.setdefault(str(row["object_name"]).casefold(), []).append(full)
            contracts = [_module_contract(cursor, item, catalog_names) for item in MODULES]

    missing = [row["object"] for row in contracts if not row["found"]]
    errors = []
    if missing:
        errors.append("required module missing")
    summary = {
        "module_count": len(contracts),
        "found_module_count": sum(row["found"] for row in contracts),
        "parameter_count": sum(row.get("parameter_count", 0) for row in contracts),
        "dependency_count": sum(row.get("dependency_count", 0) for row in contracts),
        "lexical_operation_count": sum(row.get("lexical_operation_count", 0) for row in contracts),
        "resolved_mutation_target_count": len({target for row in contracts for target in row.get("resolved_mutation_targets", [])}),
        "module_with_explicit_transaction_envelope_count": sum(row.get("has_explicit_transaction_envelope", False) for row in contracts),
        "module_with_explicit_error_handler_count": sum(row.get("has_explicit_error_handler", False) for row in contracts),
        "module_with_dynamic_sql_signal_count": sum(row.get("has_dynamic_sql_signal", False) for row in contracts),
        "definition_persisted_count": sum(row.get("definition_persisted", False) for row in contracts),
        "missing_module_count": len(missing),
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_selected_extension_sql_module_redacted_semantic_footprints",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_CLONE_MODULE_DEFINITION_IN_MEMORY_REDACTED_SEMANTIC_PARSE",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_definitions_persisted": 0,
            "string_literals_persisted": 0,
            "credentials_or_secrets_persisted": 0,
            "procedures_functions_or_triggers_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": summary,
        "modules": contracts,
        "missing_modules": missing,
        "validation_errors": errors,
        "limits": [
            "Lexical operations are static candidates; comments and string literals are masked, so dynamic SQL targets are intentionally omitted.",
            "Resolved mutation targets rely on the clone catalog and do not prove every runtime branch executes.",
            "Nested procedure, trigger, ORM and cross-database side effects require transitive analysis.",
            "The clone can lag operational Varanegar; no module was executed and no business row was selected.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
