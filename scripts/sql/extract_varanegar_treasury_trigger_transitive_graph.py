"""Build a bounded transitive graph rooted at selected catalog triggers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path

from extract_varanegar_extension_sql_semantics import _mask_comments_and_strings
from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _rows
from extract_varanegar_pos_replication_transitive_graph import _operation_tokens


FOLLOW_TYPES = {"P", "TR", "FN", "IF", "TF", "V"}
MAX_DEPTH = 3
MAX_NODES = 500


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger-semantics", required=True, type=Path)
    parser.add_argument(
        "--artifact-identity",
        default="varanegar_treasury_trigger_bounded_transitive_sql_dependency_graph",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.trigger_semantics.read_text(encoding="utf-8-sig"))
    if "triggers" in source:
        root_names = sorted(row["object"] for row in source["triggers"])
    else:
        root_names = sorted(
            f"{row['object'].split('.', 1)[0]}.{trigger['name']}"
            for row in source.get("objects", [])
            for trigger in row.get("triggers", [])
            if not trigger.get("is_disabled")
        )
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            catalog_rows = _rows(cursor, """
                SELECT o.object_id,s.name AS schema_name,o.name AS object_name,o.type,o.type_desc,
                       o.parent_object_id,m.definition
                FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
                LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.is_ms_shipped=0
            """)
            dependency_rows = _rows(cursor, """
                SELECT referencing_id,referenced_id,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id IS NOT NULL
            """)

    by_id = {}
    by_full = {}
    by_name = defaultdict(list)
    triggers_by_parent = defaultdict(list)
    for row in catalog_rows:
        object_id = int(row["object_id"])
        row["type"] = str(row["type"]).strip()
        by_id[object_id] = row
        full = f"{row['schema_name']}.{row['object_name']}"
        by_full[full.casefold()] = object_id
        by_name[str(row["object_name"]).casefold()].append(object_id)
        if row["type"] == "TR" and row["parent_object_id"]:
            triggers_by_parent[int(row["parent_object_id"])].append(object_id)
    dependencies = defaultdict(list)
    for row in dependency_rows:
        dependencies[int(row["referencing_id"])].append(row)

    def resolve(schema, name, referenced_id):
        if referenced_id is not None and int(referenced_id) in by_id:
            return int(referenced_id), "REFERENCED_ID"
        if not name:
            return None, "MISSING_NAME"
        if schema:
            result = by_full.get(f"{schema}.{name}".casefold())
            return (result, "SCHEMA_NAME") if result is not None else (None, "UNRESOLVED_SCHEMA_NAME")
        dbo = by_full.get(f"dbo.{name}".casefold())
        if dbo is not None:
            return dbo, "DEFAULT_DBO_NAME"
        candidates = by_name.get(str(name).casefold(), [])
        return (candidates[0], "UNIQUE_OBJECT_NAME") if len(candidates) == 1 else (None, "AMBIGUOUS_NAME" if candidates else "UNRESOLVED_NAME")

    root_ids = {by_full[name.casefold()] for name in root_names if name.casefold() in by_full}
    errors = []
    if source.get("validation") != "PASS":
        errors.append("trigger semantic source is not PASS")
    if len(root_ids) != len(root_names):
        errors.append("one or more trigger roots are missing")
    depth = {root_id: 0 for root_id in root_ids}
    queue = deque(sorted(root_ids))
    edges = {}
    unresolved = []
    while queue and len(depth) < MAX_NODES:
        source_id = queue.popleft()
        source_depth = depth[source_id]
        if source_depth >= MAX_DEPTH:
            continue
        for dep in dependencies.get(source_id, []):
            target_id, resolution = resolve(dep["referenced_schema_name"], dep["referenced_entity_name"], dep["referenced_id"])
            if target_id is None:
                unresolved.append({
                    "source": f"{by_id[source_id]['schema_name']}.{by_id[source_id]['object_name']}",
                    "referenced_schema_name": dep["referenced_schema_name"],
                    "referenced_entity_name": dep["referenced_entity_name"],
                    "source_depth": source_depth,
                    "resolution": resolution,
                })
                continue
            edges[(source_id, target_id, "SQL_EXPRESSION_DEPENDENCY")] = resolution
            next_depth = source_depth + 1
            if target_id not in depth and len(depth) < MAX_NODES:
                depth[target_id] = next_depth
                if by_id[target_id]["type"] in FOLLOW_TYPES:
                    queue.append(target_id)
            if by_id[target_id]["type"] == "U":
                for trigger_id in triggers_by_parent.get(target_id, []):
                    edges[(target_id, trigger_id, "TABLE_TRIGGER")] = "PARENT_OBJECT_ID"
                    trigger_depth = min(MAX_DEPTH, next_depth + 1)
                    if trigger_id not in depth and len(depth) < MAX_NODES:
                        depth[trigger_id] = trigger_depth
                        if trigger_depth < MAX_DEPTH:
                            queue.append(trigger_id)

    operation_records = []
    for source_id, source_depth in sorted(depth.items(), key=lambda pair: (pair[1], pair[0])):
        definition = by_id[source_id].get("definition") or ""
        for verb, token in _operation_tokens(definition):
            parts = token.split(".")
            target_id, resolution = resolve(parts[0] if len(parts) == 2 else None, parts[-1], None)
            operation_records.append({"source_id": source_id, "source_depth": source_depth, "verb": verb, "target_id": target_id, "resolution": resolution})
            if target_id is not None:
                edges[(source_id, target_id, f"LEXICAL_{verb}")] = resolution
                if target_id not in depth and len(depth) < MAX_NODES:
                    depth[target_id] = min(MAX_DEPTH, source_depth + 1)

    nodes = []
    for object_id, node_depth in sorted(depth.items(), key=lambda pair: (pair[1], by_id[pair[0]]["schema_name"], by_id[pair[0]]["object_name"])):
        row = by_id[object_id]
        definition = row.get("definition") or ""
        masked = _mask_comments_and_strings(definition)
        nodes.append({
            "node_id": object_id,
            "object": f"{row['schema_name']}.{row['object_name']}",
            "type": row["type"],
            "type_desc": row["type_desc"],
            "depth": node_depth,
            "is_root_trigger": object_id in root_ids,
            "definition_length": len(definition),
            "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest() if definition else None,
            "definition_persisted": False,
            "has_transaction_signal": bool(re.search(r"\b(?:BEGIN\s+TRAN|COMMIT|ROLLBACK)\b", masked, re.IGNORECASE)),
            "has_try_catch": bool(re.search(r"\bBEGIN\s+TRY\b", masked, re.IGNORECASE) and re.search(r"\bBEGIN\s+CATCH\b", masked, re.IGNORECASE)),
            "has_dynamic_sql_signal": bool(re.search(r"\bsp_executesql\b|\bEXEC(?:UTE)?\s*\(", masked, re.IGNORECASE)),
        })
    names = {row["node_id"]: row["object"] for row in nodes}
    persisted_edges = [{
        "source": names[source_id], "target": names[target_id], "edge_kind": kind, "resolution": resolution,
    } for (source_id, target_id, kind), resolution in sorted(edges.items()) if source_id in names and target_id in names]
    resolved_write_targets = sorted({names[row["target_id"]] for row in operation_records if row["target_id"] in names})
    adjacency = defaultdict(set)
    for edge in persisted_edges:
        adjacency[edge["source"]].add(edge["target"])
    node_by_name = {row["object"]: row for row in nodes}
    root_impacts = []
    write_target_set = set(resolved_write_targets)
    for root in root_names:
        seen = {root: 0}
        root_queue = deque([root])
        while root_queue:
            current = root_queue.popleft()
            current_depth = seen[current]
            if current_depth >= MAX_DEPTH:
                continue
            for target in adjacency.get(current, set()):
                if target not in seen or current_depth + 1 < seen[target]:
                    seen[target] = current_depth + 1
                    root_queue.append(target)
        reachable = set(seen) - {root}
        root_writes = sorted(reachable & write_target_set)
        root_impacts.append({
            "root_trigger": root,
            "reachable_node_count": len(reachable),
            "reachable_trigger_count": sum(node_by_name[name]["type"] == "TR" for name in reachable if name in node_by_name),
            "resolved_write_target_count": len(root_writes),
            "resolved_write_targets": root_writes,
            "reachability_status": "BOUNDED_STATIC_GRAPH_NOT_RUNTIME_BRANCH_PROOF",
        })
    operation_counts = Counter(row["verb"] for row in operation_records)
    type_counts = Counter(row["type_desc"] for row in nodes)
    graph_truncated = len(depth) >= MAX_NODES
    summary = {
        "root_trigger_count": len(root_ids),
        "maximum_depth": MAX_DEPTH,
        "node_count": len(nodes),
        "edge_count": len(persisted_edges),
        "node_type_counts": dict(sorted(type_counts.items())),
        "module_node_count": sum(row["type"] in FOLLOW_TYPES for row in nodes),
        "table_node_count": sum(row["type"] == "U" for row in nodes),
        "trigger_node_count": sum(row["type"] == "TR" for row in nodes),
        "module_with_transaction_signal_count": sum(row["has_transaction_signal"] for row in nodes),
        "module_with_try_catch_count": sum(row["has_try_catch"] for row in nodes),
        "module_with_dynamic_sql_signal_count": sum(row["has_dynamic_sql_signal"] for row in nodes),
        "lexical_operation_count": len(operation_records),
        "lexical_operation_counts": dict(sorted(operation_counts.items())),
        "resolved_write_target_count": len(resolved_write_targets),
        "root_with_resolved_write_target_count": sum(bool(row["resolved_write_target_count"]) for row in root_impacts),
        "maximum_root_reachable_node_count": max((row["reachable_node_count"] for row in root_impacts), default=0),
        "maximum_root_resolved_write_target_count": max((row["resolved_write_target_count"] for row in root_impacts), default=0),
        "unresolved_dependency_count": len(unresolved),
        "graph_truncated_at_safety_cap": graph_truncated,
        "unexpanded_frontier_count": len(queue),
        "definition_persisted_count": sum(row["definition_persisted"] for row in nodes),
        "runtime_execution_or_effect_parity_proven_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": args.artifact_identity,
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "max_depth": MAX_DEPTH, "max_nodes": MAX_NODES},
        "safety": {
            "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_AND_IN_MEMORY_REDACTED_DEFINITION_GRAPH",
            "database_updateability": context["updateability"], "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "business_row_values_read_or_persisted": 0, "module_definitions_or_string_literals_persisted": 0,
            "procedures_functions_views_or_triggers_executed": 0, "application_or_live_ui_actions": 0,
        },
        "summary": summary,
        "roots": root_names,
        "nodes": nodes,
        "edges": persisted_edges,
        "resolved_write_targets": resolved_write_targets,
        "root_impacts": sorted(root_impacts, key=lambda row: (-row["resolved_write_target_count"], -row["reachable_node_count"], row["root_trigger"])),
        "unresolved_dependencies": unresolved,
        "warnings": ["node safety cap reached" ] if graph_truncated else [],
        "validation_errors": errors,
        "limits": ["Depth and node caps bound the graph.", "Masked lexical parsing omits string-built dynamic SQL.", "No module was executed and effect parity remains unproven."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
