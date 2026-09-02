"""Extract redacted clone SQL semantics for order-to-sale IL anchors."""

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


OPERATIONS = {
    "select": re.compile(r"\bselect\b", re.IGNORECASE),
    "insert": re.compile(r"\binsert\b", re.IGNORECASE),
    "update": re.compile(r"\bupdate\b", re.IGNORECASE),
    "delete": re.compile(r"\bdelete\b", re.IGNORECASE),
    "merge": re.compile(r"\bmerge\b", re.IGNORECASE),
    "execute": re.compile(r"\bexec(?:ute)?\b", re.IGNORECASE),
    "dynamic_sql": re.compile(r"\bsp_executesql\b|\bexec\s*\(", re.IGNORECASE),
    "transaction": re.compile(
        r"\bbegin\s+tran(?:saction)?\b|\bcommit\b|\brollback\b",
        re.IGNORECASE,
    ),
    "try_catch": re.compile(r"\bbegin\s+try\b|\bbegin\s+catch\b", re.IGNORECASE),
}
IDENTIFIER = r"(?:[#@]\w+|\[[^\]]+\]|\w+)(?:\.(?:\[[^\]]+\]|\w+)){0,2}"
MUTATIONS = {
    "insert": re.compile(rf"\binsert\s+(?:into\s+)?(?P<target>{IDENTIFIER})", re.IGNORECASE),
    "update": re.compile(rf"\bupdate\s+(?P<target>{IDENTIFIER})", re.IGNORECASE),
    "delete": re.compile(rf"\bdelete\s+(?:from\s+)?(?P<target>{IDENTIFIER})", re.IGNORECASE),
    "merge": re.compile(rf"\bmerge\s+(?:into\s+)?(?P<target>{IDENTIFIER})", re.IGNORECASE),
}


def _clean(value: str) -> str:
    return value.replace("[", "").replace("]", "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dependency-graph", required=True, type=Path)
    parser.add_argument(
        "--artifact-identity",
        default="varanegar_order_sale_return_sql_redacted_semantic_footprints",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    graph: dict[str, Any] = json.loads(
        args.dependency_graph.read_text(encoding="utf-8-sig")
    )
    selected_objects = sorted(
        set(
            graph.get("safe_sql_object_anchors")
            or graph.get("sql_object_anchors")
            or []
        ),
        key=str.casefold,
    )
    modules: list[dict[str, Any]] = []
    lookup_failures: list[str] = []
    result_shape_failures: list[dict[str, str]] = []
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            for full_name in selected_objects:
                schema_name, object_name = full_name.split(".", 1)
                found = _rows(
                    cursor,
                    """
                    SELECT o.object_id,o.type,o.type_desc,m.definition
                    FROM sys.objects o
                    JOIN sys.schemas s ON s.schema_id=o.schema_id
                    LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                    WHERE s.name=%s AND o.name=%s AND o.is_ms_shipped=0
                    """,
                    (schema_name, object_name),
                )
                if len(found) != 1:
                    lookup_failures.append(full_name)
                    continue
                source = found[0]
                object_id = int(source["object_id"])
                definition = source["definition"] or ""
                operation_counts = {
                    name: len(pattern.findall(definition))
                    for name, pattern in OPERATIONS.items()
                }
                target_classes = Counter()
                durable_targets: set[str] = set()
                for pattern in MUTATIONS.values():
                    for match in pattern.finditer(definition):
                        target = _clean(match.group("target"))
                        if target.startswith(("#", "@")):
                            target_classes["TEMP_OR_TABLE_VARIABLE"] += 1
                            continue
                        resolved = _rows(
                            cursor,
                            """
                            SELECT OBJECT_SCHEMA_NAME(OBJECT_ID(%s)) AS schema_name,
                                   OBJECT_NAME(OBJECT_ID(%s)) AS object_name
                            """,
                            (target, target),
                        )[0]
                        if resolved["schema_name"] and resolved["object_name"]:
                            target_classes["CATALOG_RESOLVED_DURABLE"] += 1
                            durable_targets.add(
                                f"{resolved['schema_name']}.{resolved['object_name']}"
                            )
                        else:
                            target_classes["UNRESOLVED_IDENTIFIER_OR_ALIAS"] += 1
                parameters = _rows(
                    cursor,
                    """
                    SELECT parameter_id,name,TYPE_NAME(user_type_id) AS data_type,
                           max_length,precision,scale,is_output
                    FROM sys.parameters WHERE object_id=%s ORDER BY parameter_id
                    """,
                    (object_id,),
                )
                dependencies = _rows(
                    cursor,
                    """
                    SELECT DISTINCT COALESCE(referenced_schema_name,'?') AS schema_name,
                           COALESCE(referenced_entity_name,'?') AS entity_name,
                           referenced_class_desc
                    FROM sys.sql_expression_dependencies
                    WHERE referencing_id=%s
                    ORDER BY schema_name,entity_name,referenced_class_desc
                    """,
                    (object_id,),
                )
                result_columns: list[dict[str, Any]] = []
                result_shape_status = "NO_DESCRIBED_RESULT_COLUMNS"
                try:
                    described = _rows(
                        cursor,
                        """
                        SELECT column_ordinal,name,system_type_name,is_nullable,error_type_desc
                        FROM sys.dm_exec_describe_first_result_set_for_object(%s,0)
                        ORDER BY column_ordinal
                        """,
                        (object_id,),
                    )
                    error_types = sorted(
                        {
                            str(row["error_type_desc"])
                            for row in described
                            if row.get("error_type_desc")
                        }
                    )
                    result_columns = [
                        {
                            "ordinal": int(row["column_ordinal"]),
                            "name": row["name"],
                            "system_type_name": row["system_type_name"],
                            "is_nullable": None
                            if row["is_nullable"] is None
                            else bool(row["is_nullable"]),
                        }
                        for row in described
                        if row.get("column_ordinal") is not None
                        and not row.get("error_type_desc")
                    ]
                    result_shape_status = (
                        "DESCRIBED"
                        if result_columns
                        else "METADATA_ERROR_TYPE"
                        if error_types
                        else result_shape_status
                    )
                    if error_types:
                        result_shape_failures.append(
                            {"object": full_name, "error_class": ",".join(error_types)}
                        )
                except Exception as exc:
                    result_shape_status = "METADATA_QUERY_EXCEPTION"
                    result_shape_failures.append(
                        {"object": full_name, "error_class": type(exc).__name__}
                    )
                modules.append(
                    {
                        "object": f"{schema_name}.{object_name}",
                        "type": str(source["type"]).strip(),
                        "type_desc": source["type_desc"],
                        "definition_length": len(definition),
                        "definition_sha256": hashlib.sha256(
                            definition.encode("utf-8")
                        ).hexdigest()
                        if definition
                        else None,
                        "definition_persisted": False,
                        "operation_token_counts": operation_counts,
                        "mutation_token_count": sum(
                            operation_counts[name]
                            for name in ("insert", "update", "delete", "merge")
                        ),
                        "mutation_target_class_counts": dict(
                            sorted(target_classes.items())
                        ),
                        "durable_mutation_targets": sorted(durable_targets),
                        "parameters": [
                            {
                                "ordinal": int(row["parameter_id"]),
                                "name": row["name"],
                                "data_type": row["data_type"],
                                "max_length": int(row["max_length"]),
                                "precision": int(row["precision"]),
                                "scale": int(row["scale"]),
                                "is_output": bool(row["is_output"]),
                            }
                            for row in parameters
                        ],
                        "dependencies": [
                            {
                                "object": f"{row['schema_name']}.{row['entity_name']}",
                                "referenced_class_desc": row[
                                    "referenced_class_desc"
                                ],
                            }
                            for row in dependencies
                        ],
                        "result_shape_status": result_shape_status,
                        "result_columns": result_columns,
                        "execution_result_or_effect_parity_proven": False,
                    }
                )

    errors: list[str] = []
    if graph.get("validation") != "PASS":
        errors.append("source dependency graph is not PASS")
    if lookup_failures:
        errors.append("one or more IL SQL anchors did not resolve uniquely")
    totals = Counter()
    for module in modules:
        totals.update(module["operation_token_counts"])
    artifact = {
        "artifact": args.artifact_identity,
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {
            "server": SERVER,
            "database": DATABASE,
            "snapshot_kind": "READ_ONLY_CLONE",
        },
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_AND_RESULT_METADATA_WITH_TRANSIENT_DEFINITION_SCAN",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_definitions_or_string_literals_persisted": 0,
            "credentials_identity_grants_or_secrets_persisted": 0,
            "procedures_functions_views_or_triggers_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": {
            "selected_anchor_count": len(selected_objects),
            "resolved_module_count": len(modules),
            "stored_procedure_count": sum(row["type"] == "P" for row in modules),
            "parameter_count": sum(len(row["parameters"]) for row in modules),
            "dependency_count": sum(len(row["dependencies"]) for row in modules),
            "operation_token_counts": dict(sorted(totals.items())),
            "module_with_transaction_token_count": sum(
                row["operation_token_counts"]["transaction"] > 0 for row in modules
            ),
            "module_with_dynamic_sql_token_count": sum(
                row["operation_token_counts"]["dynamic_sql"] > 0 for row in modules
            ),
            "module_with_mutation_token_count": sum(
                row["mutation_token_count"] > 0 for row in modules
            ),
            "catalog_resolved_durable_mutation_target_count": len(
                {target for row in modules for target in row["durable_mutation_targets"]}
            ),
            "described_result_column_count": sum(
                len(row["result_columns"]) for row in modules
            ),
            "result_shape_metadata_failure_count": len(result_shape_failures),
            "definition_persisted_count": 0,
            "execution_result_or_effect_parity_proven_count": 0,
            "lookup_failure_count": len(lookup_failures),
            "validation_error_count": len(errors),
        },
        "modules": modules,
        "result_shape_failures": result_shape_failures,
        "lookup_failures": lookup_failures,
        "validation_errors": errors,
        "limits": [
            "IL string anchors plus unique catalog resolution are static candidates, not runtime execution proof.",
            "Lexical token counts can include dead branches, comments, temporary objects, aliases and dynamic SQL fragments.",
            "Resolved durable targets are incomplete when SQL is dynamic or target identifiers are aliases.",
            "Result metadata does not execute the module and does not prove values, messages, trigger effects or parity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
