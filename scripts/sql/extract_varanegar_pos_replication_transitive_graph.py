"""Extract a bounded transitive SQL dependency graph for POS receipt replication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_extension_sql_semantics import _mask_comments_and_strings
from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows


ROOT_OBJECT = "dbo.usp_ReplicateSalesReceipt"
FOLLOW_TYPES = {"P", "TR", "FN", "IF", "TF", "V"}
MAX_DEPTH = 3
MAX_NODES = 500


def _clean_identifier(value: str) -> str:
    return re.sub(r"[\[\]\s]", "", value).rstrip(";,)" )


def _operation_tokens(definition: str) -> list[tuple[str, str]]:
    masked = _mask_comments_and_strings(definition)
    pattern = re.compile(
        r"\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE(?:\s+INTO)?)\s+((?:\[[^\]]+\]|[A-Za-z_][\w$#]*)(?:\s*\.\s*(?:\[[^\]]+\]|[A-Za-z_][\w$#]*))?)",
        re.IGNORECASE,
    )
    return [
        (re.sub(r"\s+", "_", match.group(1).upper()), _clean_identifier(match.group(2)))
        for match in pattern.finditer(masked)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            catalog_rows = _rows(
                cursor,
                """
                SELECT o.object_id,s.name AS schema_name,o.name AS object_name,
                       o.type,o.type_desc,o.parent_object_id,m.definition
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.is_ms_shipped=0
                """,
            )
            dependency_rows = _rows(
                cursor,
                """
                SELECT d.referencing_id,d.referenced_id,d.referenced_schema_name,d.referenced_entity_name
                FROM sys.sql_expression_dependencies d
                WHERE d.referencing_id IS NOT NULL
                """,
            )

    by_id: dict[int, dict[str, Any]] = {}
    by_full: dict[str, int] = {}
    by_name: dict[str, list[int]] = defaultdict(list)
    triggers_by_parent: dict[int, list[int]] = defaultdict(list)
    for row in catalog_rows:
        object_id = int(row["object_id"])
        row["type"] = str(row["type"]).strip()
        by_id[object_id] = row
        full = f"{row['schema_name']}.{row['object_name']}"
        by_full[full.casefold()] = object_id
        by_name[str(row["object_name"]).casefold()].append(object_id)
        if row["type"] == "TR" and row["parent_object_id"]:
            triggers_by_parent[int(row["parent_object_id"])].append(object_id)

    dependencies_by_source: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in dependency_rows:
        dependencies_by_source[int(row["referencing_id"])].append(row)

    def resolve(schema: str | None, name: str | None, referenced_id: Any) -> tuple[int | None, str]:
        if referenced_id is not None:
            candidate = int(referenced_id)
            if candidate in by_id:
                return candidate, "REFERENCED_ID"
        if not name:
            return None, "MISSING_NAME"
        if schema:
            candidate = by_full.get(f"{schema}.{name}".casefold())
            return (candidate, "SCHEMA_NAME") if candidate is not None else (None, "UNRESOLVED_SCHEMA_NAME")
        dbo = by_full.get(f"dbo.{name}".casefold())
        if dbo is not None:
            return dbo, "DEFAULT_DBO_NAME"
        candidates = by_name.get(name.casefold(), [])
        if len(candidates) == 1:
            return candidates[0], "UNIQUE_OBJECT_NAME"
        return None, "AMBIGUOUS_NAME" if candidates else "UNRESOLVED_NAME"

    root_id = by_full.get(ROOT_OBJECT.casefold())
    errors: list[str] = []
    if root_id is None:
        errors.append("root object missing")

    depth_by_id: dict[int, int] = {}
    edge_keys: set[tuple[int, int, str]] = set()
    edges: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    queue: deque[int] = deque()
    if root_id is not None:
        depth_by_id[root_id] = 0
        queue.append(root_id)

    while queue and len(depth_by_id) < MAX_NODES:
        source_id = queue.popleft()
        source_depth = depth_by_id[source_id]
        if source_depth >= MAX_DEPTH:
            continue
        for dependency in dependencies_by_source.get(source_id, []):
            target_id, resolution = resolve(
                dependency["referenced_schema_name"],
                dependency["referenced_entity_name"],
                dependency["referenced_id"],
            )
            if target_id is None:
                unresolved.append(
                    {
                        "source": f"{by_id[source_id]['schema_name']}.{by_id[source_id]['object_name']}",
                        "referenced_schema_name": dependency["referenced_schema_name"],
                        "referenced_entity_name": dependency["referenced_entity_name"],
                        "resolution": resolution,
                        "source_depth": source_depth,
                    }
                )
                continue
            key = (source_id, target_id, "SQL_EXPRESSION_DEPENDENCY")
            if key not in edge_keys:
                edge_keys.add(key)
                edges.append({"source_id": source_id, "target_id": target_id, "edge_kind": key[2], "resolution": resolution})
            next_depth = source_depth + 1
            if target_id not in depth_by_id or next_depth < depth_by_id[target_id]:
                depth_by_id[target_id] = next_depth
                if by_id[target_id]["type"] in FOLLOW_TYPES:
                    queue.append(target_id)
            if by_id[target_id]["type"] == "U":
                for trigger_id in triggers_by_parent.get(target_id, []):
                    trigger_key = (target_id, trigger_id, "TABLE_TRIGGER")
                    if trigger_key not in edge_keys:
                        edge_keys.add(trigger_key)
                        edges.append({"source_id": target_id, "target_id": trigger_id, "edge_kind": trigger_key[2], "resolution": "PARENT_OBJECT_ID"})
                    trigger_depth = min(MAX_DEPTH, next_depth + 1)
                    if trigger_id not in depth_by_id or trigger_depth < depth_by_id[trigger_id]:
                        depth_by_id[trigger_id] = trigger_depth
                        if trigger_depth < MAX_DEPTH:
                            queue.append(trigger_id)

    graph_truncated = len(depth_by_id) >= MAX_NODES
    warnings: list[str] = []
    if graph_truncated:
        warnings.append("node safety cap reached; queued modules were not expanded")

    # Add lexical mutation edges for visited modules. These can expose aliases;
    # only catalog-resolved targets become graph edges.
    operation_records = []
    for source_id, depth in sorted(depth_by_id.items(), key=lambda pair: (pair[1], pair[0])):
        row = by_id[source_id]
        definition = row.get("definition") or ""
        if not definition:
            continue
        for verb, token in _operation_tokens(definition):
            parts = token.split(".")
            target_id, resolution = resolve(parts[0] if len(parts) == 2 else None, parts[-1], None)
            operation = {
                "source_id": source_id,
                "source_depth": depth,
                "verb": verb,
                "target_token": token if target_id is not None else None,
                "target_id": target_id,
                "resolution": resolution,
            }
            operation_records.append(operation)
            if target_id is not None:
                key = (source_id, target_id, f"LEXICAL_{verb}")
                if key not in edge_keys:
                    edge_keys.add(key)
                    edges.append({"source_id": source_id, "target_id": target_id, "edge_kind": key[2], "resolution": resolution})
                if target_id not in depth_by_id and len(depth_by_id) < MAX_NODES:
                    depth_by_id[target_id] = min(MAX_DEPTH, depth + 1)

    nodes = []
    for object_id, depth in sorted(depth_by_id.items(), key=lambda pair: (pair[1], by_id[pair[0]]["schema_name"], by_id[pair[0]]["object_name"])):
        row = by_id[object_id]
        definition = row.get("definition") or ""
        masked = _mask_comments_and_strings(definition)
        nodes.append(
            {
                "node_id": object_id,
                "object": f"{row['schema_name']}.{row['object_name']}",
                "type": row["type"],
                "type_desc": row["type_desc"],
                "depth": depth,
                "definition_length": len(definition),
                "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest() if definition else None,
                "definition_persisted": False,
                "has_begin_transaction": bool(re.search(r"\bBEGIN\s+TRAN(?:SACTION)?\b", masked, re.IGNORECASE)),
                "has_commit": bool(re.search(r"\bCOMMIT(?:\s+TRAN(?:SACTION)?)?\b", masked, re.IGNORECASE)),
                "has_rollback": bool(re.search(r"\bROLLBACK(?:\s+TRAN(?:SACTION)?)?\b", masked, re.IGNORECASE)),
                "has_try_catch": bool(re.search(r"\bBEGIN\s+TRY\b", masked, re.IGNORECASE) and re.search(r"\bBEGIN\s+CATCH\b", masked, re.IGNORECASE)),
                "has_dynamic_sql_signal": bool(re.search(r"\bsp_executesql\b|\bEXEC(?:UTE)?\s*\(", masked, re.IGNORECASE)),
            }
        )

    node_name = {row["node_id"]: row["object"] for row in nodes}
    persisted_edges = [
        {
            "source": node_name.get(edge["source_id"], f"object_id:{edge['source_id']}"),
            "target": node_name.get(edge["target_id"], f"object_id:{edge['target_id']}"),
            "edge_kind": edge["edge_kind"],
            "resolution": edge["resolution"],
        }
        for edge in edges
        if edge["source_id"] in node_name and edge["target_id"] in node_name
    ]
    operation_counts = Counter(row["verb"] for row in operation_records)
    write_targets = sorted(
        {
            node_name[row["target_id"]]
            for row in operation_records
            if row["target_id"] in node_name
        }
    )
    type_counts = Counter(row["type_desc"] for row in nodes)
    schema_counts = Counter(row["object"].split(".", 1)[0] for row in nodes)
    summary = {
        "maximum_depth": MAX_DEPTH,
        "node_count": len(nodes),
        "edge_count": len(persisted_edges),
        "node_type_counts": dict(sorted(type_counts.items())),
        "schema_counts": dict(sorted(schema_counts.items())),
        "module_node_count": sum(row["type"] in FOLLOW_TYPES for row in nodes),
        "table_node_count": sum(row["type"] == "U" for row in nodes),
        "trigger_node_count": sum(row["type"] == "TR" for row in nodes),
        "module_with_transaction_signal_count": sum(row["has_begin_transaction"] or row["has_commit"] or row["has_rollback"] for row in nodes),
        "module_with_try_catch_count": sum(row["has_try_catch"] for row in nodes),
        "module_with_dynamic_sql_signal_count": sum(row["has_dynamic_sql_signal"] for row in nodes),
        "lexical_operation_count": len(operation_records),
        "lexical_operation_counts": dict(sorted(operation_counts.items())),
        "resolved_write_target_count": len(write_targets),
        "unresolved_dependency_count": len(unresolved),
        "graph_truncated_at_safety_cap": graph_truncated,
        "unexpanded_frontier_count": len(queue),
        "definition_persisted_count": sum(row["definition_persisted"] for row in nodes),
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_pos_receipt_replication_bounded_transitive_sql_graph",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "root_object": ROOT_OBJECT, "max_depth": MAX_DEPTH, "max_nodes": MAX_NODES},
        "safety": {
            "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_AND_IN_MEMORY_REDACTED_DEFINITION_GRAPH",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_definitions_or_string_literals_persisted": 0,
            "credentials_or_identity_grants_persisted": 0,
            "procedures_functions_views_or_triggers_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": summary,
        "nodes": nodes,
        "edges": persisted_edges,
        "resolved_write_targets": write_targets,
        "unresolved_dependencies": unresolved,
        "warnings": warnings,
        "validation_errors": errors,
        "limits": [
            "The graph is bounded to depth three and does not represent every possible runtime branch.",
            "PASS validates extraction safety and internal consistency; it does not mean the graph is complete when graph_truncated_at_safety_cap is true.",
            "String literals and comments are masked, so dynamic SQL and values are intentionally absent.",
            "Unresolved aliases and dependencies remain explicit; nested external code and operational drift are not proven.",
            "No SQL module, view, function, trigger or business command was executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
