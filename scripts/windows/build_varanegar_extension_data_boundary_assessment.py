"""Assess legacy UI/DataAccess boundaries against clone catalog candidates."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _edge_kind(member: str) -> str:
    if member == "Commit":
        return "EXPLICIT_UI_COMMIT_BOUNDARY"
    if member in {".ctor", "Dispose"}:
        return "UI_OWNS_DATA_CONTEXT_LIFECYCLE"
    if member.startswith(("get_", "Get", "Is", "Has", "Select", "Load")):
        return "DIRECT_UI_READ_OR_CONTEXT_LOOKUP"
    return "DIRECT_UI_DATA_ACCESS_UNCLASSIFIED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-paths", required=True, type=Path)
    parser.add_argument("--target-contracts", required=True, type=Path)
    parser.add_argument("--sql-surface", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = _load(args.command_paths)
    target = _load(args.target_contracts)
    sql = _load(args.sql_surface)
    errors: list[str] = []
    for name, payload in (("command paths", paths), ("target contracts", target), ("SQL surface", sql)):
        if payload.get("validation") != "PASS":
            errors.append(f"source is not PASS: {name}")

    target_by_capability: dict[str, list[dict[str, str]]] = {}
    for row in target["commands"]:
        target_by_capability.setdefault(row["capability"], []).append(
            {"surface": row["command"], "surface_kind": "command", "owner": row["owner"]}
        )
    for row in target["queries"]:
        target_by_capability.setdefault(row["capability"], []).append(
            {"surface": row["query"], "surface_kind": "query", "owner": row["owner"]}
        )
    sql_coverage = {row["capability"]: row for row in sql["capability_coverage"]}
    sql_objects_by_capability: dict[str, list[dict[str, Any]]] = {}
    for capability in target_by_capability:
        sql_objects_by_capability[capability] = [
            row
            for row in sql["objects"]
            if capability in {match["capability"] for match in row["capability_matches"]}
        ]

    assessments = []
    boundary_counts: Counter[str] = Counter()
    for path in paths["capability_paths"]:
        capability = path["capability_hint"]
        target_surfaces = target_by_capability.get(capability)
        if target_surfaces is None:
            errors.append(f"missing target surface: {capability}")
            continue
        direct_methods = []
        direct_edges: set[tuple[str, str, str]] = set()
        for method in path["methods"]:
            edges = [edge for edge in method["edges"] if edge["target_layer"] == "data_access"]
            if not edges:
                continue
            method_edges = []
            for edge in edges:
                kind = _edge_kind(edge["called_member"])
                direct_edges.add((edge["target_type"], edge["called_member"], kind))
                method_edges.append({"target_type": edge["target_type"], "called_member": edge["called_member"], "boundary_kind": kind})
            direct_methods.append({"ui_method": method["ui_method"], "role": method["role"], "edges": method_edges})

        kinds = sorted({kind for _, _, kind in direct_edges})
        if "EXPLICIT_UI_COMMIT_BOUNDARY" in kinds:
            classification = "LEGACY_UI_OWNS_EXPLICIT_COMMIT"
        elif "UI_OWNS_DATA_CONTEXT_LIFECYCLE" in kinds:
            classification = "LEGACY_UI_OWNS_DATA_CONTEXT_WITHOUT_OBSERVED_COMMIT"
        elif direct_edges:
            classification = "LEGACY_UI_DIRECT_READ_CONTEXT_COUPLING"
        else:
            classification = "NO_DIRECT_UI_DATA_ACCESS_IN_SELECTED_PATHS"
        boundary_counts[classification] += 1

        candidate_objects = sql_objects_by_capability[capability]
        exact = [
            f"{row['schema_name']}.{row['object_name']}"
            for row in candidate_objects
            if row["match_strength"] == "EXACT_NORMALIZED_NAME"
        ]
        tables = [row for row in candidate_objects if row["type"] == "U"]
        modules = [row for row in candidate_objects if row["type"] != "U"]
        material_tables = [
            {
                "object": f"{row['schema_name']}.{row['object_name']}",
                "row_count_metadata": row["row_count_metadata"],
                "primary_key_columns": [column["column_name"] for column in row["columns"] if column["is_primary_key"]],
                "column_count": len(row["columns"]),
                "foreign_key_count": len(row["foreign_keys"]),
                "trigger_count": len(row["triggers"]),
            }
            for row in tables
        ]
        assessments.append(
            {
                "capability": capability,
                "target_surfaces": target_surfaces,
                "legacy_boundary_classification": classification,
                "direct_ui_data_access_method_count": len(direct_methods),
                "direct_ui_data_access_unique_edge_count": len(direct_edges),
                "boundary_kinds": kinds,
                "direct_methods": direct_methods,
                "clone_catalog": {
                    "status": sql_coverage[capability]["status"],
                    "candidate_count": len(candidate_objects),
                    "exact_normalized_name_candidates": sorted(exact),
                    "table_count": len(tables),
                    "module_count": len(modules),
                    "material_tables": material_tables,
                    "module_candidates": sorted(f"{row['schema_name']}.{row['object_name']}" for row in modules),
                    "link_confidence": "NAME_CANDIDATE_NOT_EXECUTION_PROOF" if candidate_objects else "UNRESOLVED_NO_NAME_MATCH",
                },
                "target_boundary": {
                    "ui": "collects input and renders result only; no DataContext, repository or transaction ownership",
                    "application": "authorizes scope, validates command/query, owns idempotency and transaction orchestration",
                    "domain": "enforces aggregate invariants without infrastructure commit calls",
                    "infrastructure": "implements scoped repositories/projections behind application-owned unit of work",
                },
                "required_next_evidence": [
                    "prove repository-to-SQL objects through adapter IL, ORM mapping or definition dependency",
                    "verify clone freshness before treating row counts or definitions as current operational truth",
                    "capture owner-approved fields, effective scopes and expected values in role UAT",
                ],
            }
        )

    summary = {
        "capability_count": len(assessments),
        "target_command_count": len(target["commands"]),
        "target_query_count": len(target["queries"]),
        "capability_with_direct_ui_data_access_count": sum(row["direct_ui_data_access_unique_edge_count"] > 0 for row in assessments),
        "direct_ui_data_access_method_count": sum(row["direct_ui_data_access_method_count"] for row in assessments),
        "direct_ui_data_access_unique_edge_count": sum(row["direct_ui_data_access_unique_edge_count"] for row in assessments),
        "legacy_boundary_classification_counts": dict(sorted(boundary_counts.items())),
        "capability_with_clone_catalog_candidate_count": sum(row["clone_catalog"]["candidate_count"] > 0 for row in assessments),
        "capability_without_clone_catalog_candidate_count": sum(row["clone_catalog"]["candidate_count"] == 0 for row in assessments),
        "clone_catalog_candidate_count": sum(row["clone_catalog"]["candidate_count"] for row in assessments),
        "clone_catalog_table_candidate_count": sum(row["clone_catalog"]["table_count"] for row in assessments),
        "clone_catalog_module_candidate_count": sum(row["clone_catalog"]["module_count"] for row in assessments),
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_extension_legacy_data_boundary_and_clone_catalog_assessment",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_ASSESSMENT_FROM_REDACTED_IL_AND_READ_ONLY_CLONE_CATALOG_METADATA",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "source_or_target_commands_executed": 0,
            "business_row_values_read_or_persisted": 0,
            "module_definitions_or_secrets_persisted": 0,
        },
        "summary": summary,
        "assessments": assessments,
        "validation_errors": errors,
        "limits": [
            "Direct UI DataAccess calls prove coupling, but read-like naming does not prove absence of hidden writes.",
            "Catalog name matches are candidates and are not a proven runtime execution path.",
            "Clone row counts and definitions can be stale relative to operational Varanegar.",
            "No application command, SQL module, trigger or business-data query was executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
