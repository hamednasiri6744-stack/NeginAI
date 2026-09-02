"""Extract catalog-resolved column dependency evidence for writable treasury views."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlglot import exp, parse_one

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _rows


VIEWS = ("dbo.RCheque", "dbo.RCashDraft")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    contracts: list[dict[str, Any]] = []
    errors: list[str] = []
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            for view in VIEWS:
                columns = _rows(
                    cursor,
                    """
                    SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS data_type,c.is_nullable
                    FROM sys.columns c WHERE c.object_id=OBJECT_ID(%s) ORDER BY c.column_id
                    """,
                    (view,),
                )
                definition_rows = _rows(
                    cursor,
                    "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(%s)",
                    (view,),
                )
                definition = definition_rows[0]["definition"] if definition_rows else ""
                try:
                    refs = _rows(
                        cursor,
                        """
                        SELECT referencing_minor_id,referenced_schema_name,referenced_entity_name,
                               referenced_minor_name,referenced_minor_id,
                               is_selected,is_updated,is_select_all,is_insert_all,
                               is_caller_dependent,is_ambiguous
                        FROM sys.dm_sql_referenced_entities(%s,'OBJECT')
                        ORDER BY referencing_minor_id,referenced_schema_name,referenced_entity_name,referenced_minor_id
                        """,
                        (view,),
                    )
                except Exception as exc:
                    errors.append(f"referenced entity resolution failed for {view}: {type(exc).__name__}")
                    refs = []
                try:
                    described = _rows(
                        cursor,
                        """
                        SELECT column_ordinal,name,system_type_name,is_nullable,
                               source_server,source_database,source_schema,source_table,source_column,
                               is_hidden,error_number,error_severity,error_state,error_message,error_type,error_type_desc
                        FROM sys.dm_exec_describe_first_result_set_for_object(OBJECT_ID(%s),1)
                        ORDER BY column_ordinal
                        """,
                        (view,),
                    )
                except Exception:
                    described = []
                object_description_errors = [{
                    "number": row["error_number"],
                    "severity": row["error_severity"],
                    "state": row["error_state"],
                    "type": row["error_type"],
                    "type_desc": row["error_type_desc"],
                } for row in described if row["error_number"]]
                if object_description_errors:
                    safe_select = "SELECT * FROM " + ".".join(f"[{part}]" for part in view.split("."))
                    try:
                        described = _rows(
                            cursor,
                            """
                            SELECT column_ordinal,name,system_type_name,is_nullable,
                                   source_server,source_database,source_schema,source_table,source_column,
                                   is_hidden,error_number,error_severity,error_state,error_message,error_type,error_type_desc
                            FROM sys.dm_exec_describe_first_result_set(%s,NULL,1)
                            ORDER BY column_ordinal
                            """,
                            (safe_select,),
                        )
                    except Exception:
                        described = []
                names = {int(row["column_id"]): row["name"] for row in columns}
                lineage = []
                for row in refs:
                    minor = int(row["referencing_minor_id"] or 0)
                    lineage.append({
                        "view_column_ordinal": minor,
                        "view_column": names.get(minor),
                        "referenced_object": (
                            f"{row['referenced_schema_name']}.{row['referenced_entity_name']}"
                            if row["referenced_schema_name"] and row["referenced_entity_name"]
                            else row["referenced_entity_name"]
                        ),
                        "referenced_column": row["referenced_minor_name"],
                        "referenced_column_id": int(row["referenced_minor_id"] or 0),
                        "is_selected": bool(row["is_selected"]),
                        "is_updated": bool(row["is_updated"]),
                        "is_select_all": bool(row["is_select_all"]),
                        "is_insert_all": bool(row["is_insert_all"]),
                        "is_caller_dependent": bool(row["is_caller_dependent"]),
                        "is_ambiguous": bool(row["is_ambiguous"]),
                        "lineage_status": "CATALOG_RESOLVED_DEPENDENCY_NOT_RUNTIME_BRANCH_PROOF",
                    })
                parsed_candidates = []
                parse_error = None
                try:
                    referenced_objects_by_column: dict[str, set[str]] = {}
                    for ref in refs:
                        if not ref["referenced_minor_name"] or not ref["referenced_entity_name"]:
                            continue
                        ref_object = (
                            f"{ref['referenced_schema_name']}.{ref['referenced_entity_name']}"
                            if ref["referenced_schema_name"]
                            else ref["referenced_entity_name"]
                        )
                        referenced_objects_by_column.setdefault(str(ref["referenced_minor_name"]).casefold(), set()).add(ref_object)
                    tree = parse_one(definition, read="tsql")
                    select = tree.find(exp.Select)
                    aliases = {}
                    for table in select.find_all(exp.Table):
                        object_name = ".".join(part for part in (table.catalog, table.db, table.name) if part)
                        aliases[table.alias_or_name.casefold()] = object_name
                        aliases[table.name.casefold()] = object_name
                    for ordinal, expression in enumerate(select.expressions, 1):
                        output_name = expression.alias_or_name or names.get(ordinal)
                        source_refs = []
                        for column in expression.find_all(exp.Column):
                            qualifier = column.table or ""
                            source_object = aliases.get(qualifier.casefold()) if qualifier else None
                            resolution = "QUALIFIED_ALIAS_RESOLVED" if source_object else "UNRESOLVED_UNQUALIFIED_IDENTIFIER"
                            if not source_object:
                                object_candidates = sorted(referenced_objects_by_column.get(column.name.casefold(), set()))
                                if len(object_candidates) == 1:
                                    source_object = object_candidates[0]
                                    resolution = "UNIQUE_REFERENCED_COLUMN_NAME_CANDIDATE"
                                elif len(object_candidates) > 1:
                                    resolution = "AMBIGUOUS_REFERENCED_COLUMN_NAME"
                            source_refs.append({
                                "source_object_candidate": source_object,
                                "source_qualifier": qualifier or None,
                                "source_column": column.name,
                                "resolution": resolution,
                            })
                        unique_refs = {(row["source_object_candidate"], row["source_qualifier"], row["source_column"], row["resolution"]): row for row in source_refs}
                        parsed_candidates.append({
                            "ordinal": ordinal,
                            "output_column": output_name,
                            "expression_kind": expression.this.key.upper() if isinstance(expression, exp.Alias) else expression.key.upper(),
                            "source_identifier_candidates": list(unique_refs.values()),
                            "lineage_status": "IN_MEMORY_PARSED_IDENTIFIER_CANDIDATES_NOT_BINDING_OR_RUNTIME_PROOF",
                        })
                except Exception as exc:
                    parse_error = type(exc).__name__
                visible_without_direct = [row["name"] for row in described if not row["is_hidden"] and not row["source_column"]]
                contracts.append({
                    "view": view,
                    "column_count": len(columns),
                    "columns": [{
                        "ordinal": int(row["column_id"]),
                        "name": row["name"],
                        "data_type": row["data_type"],
                        "is_nullable": bool(row["is_nullable"]),
                    } for row in columns],
                    "lineage_edge_count": len(lineage),
                    "column_level_lineage_edge_count": sum(bool(row["view_column"] and row["referenced_column"]) for row in lineage),
                    "lineage": lineage,
                    "view_column_with_column_lineage_count": len({row["view_column"] for row in lineage if row["view_column"] and row["referenced_column"]}),
                    "described_result_columns": [{
                        "ordinal": int(row["column_ordinal"] or 0),
                        "name": row["name"],
                        "system_type_name": row["system_type_name"],
                        "is_nullable": bool(row["is_nullable"]) if row["is_nullable"] is not None else None,
                        "source_object": (
                            f"{row['source_schema']}.{row['source_table']}"
                            if row["source_schema"] and row["source_table"]
                            else row["source_table"]
                        ),
                        "source_column": row["source_column"],
                        "is_hidden": bool(row["is_hidden"]),
                        "description_error": {
                            "number": row["error_number"],
                            "severity": row["error_severity"],
                            "state": row["error_state"],
                            "type": row["error_type"],
                            "type_desc": row["error_type_desc"],
                        } if row["error_number"] else None,
                    } for row in described],
                    "described_result_column_count": len(described),
                    "described_result_column_with_source_lineage_count": sum(bool(row["source_table"] and row["source_column"]) for row in described),
                    "visible_described_result_column_count": sum(not bool(row["is_hidden"]) for row in described),
                    "visible_described_result_column_with_source_lineage_count": sum(not bool(row["is_hidden"]) and bool(row["source_table"] and row["source_column"]) for row in described),
                    "hidden_browse_lineage_column_count": sum(bool(row["is_hidden"]) for row in described),
                    "visible_column_without_direct_source_lineage": visible_without_direct,
                    "object_describe_first_result_set_errors": object_description_errors,
                    "parsed_select_candidate_count": len(parsed_candidates),
                    "parsed_select_candidate_with_source_identifier_count": sum(bool(row["source_identifier_candidates"]) for row in parsed_candidates),
                    "parsed_select_lineage_candidates": parsed_candidates,
                    "direct_metadata_gap_with_parsed_identifier_candidate_count": sum(
                        row["output_column"] in visible_without_direct and bool(row["source_identifier_candidates"])
                        for row in parsed_candidates
                    ),
                    "definition_parse_error_type": parse_error,
                    "definition_persisted": False,
                    "runtime_read_write_or_trigger_effect_proven": False,
                })

    summary = {
        "target_view_count": len(VIEWS),
        "resolved_view_count": sum(bool(row["columns"]) for row in contracts),
        "view_column_count": sum(row["column_count"] for row in contracts),
        "lineage_edge_count": sum(row["lineage_edge_count"] for row in contracts),
        "column_level_lineage_edge_count": sum(row["column_level_lineage_edge_count"] for row in contracts),
        "view_column_with_column_lineage_count": sum(row["view_column_with_column_lineage_count"] for row in contracts),
        "described_result_column_count": sum(row["described_result_column_count"] for row in contracts),
        "described_result_column_with_source_lineage_count": sum(row["described_result_column_with_source_lineage_count"] for row in contracts),
        "visible_described_result_column_count": sum(row["visible_described_result_column_count"] for row in contracts),
        "visible_described_result_column_with_source_lineage_count": sum(row["visible_described_result_column_with_source_lineage_count"] for row in contracts),
        "hidden_browse_lineage_column_count": sum(row["hidden_browse_lineage_column_count"] for row in contracts),
        "visible_column_without_direct_source_lineage_count": sum(len(row["visible_column_without_direct_source_lineage"]) for row in contracts),
        "parsed_select_candidate_count": sum(row["parsed_select_candidate_count"] for row in contracts),
        "parsed_select_candidate_with_source_identifier_count": sum(row["parsed_select_candidate_with_source_identifier_count"] for row in contracts),
        "definition_parse_error_count": sum(bool(row["definition_parse_error_type"]) for row in contracts),
        "definition_persisted_count": sum(row["definition_persisted"] for row in contracts),
        "direct_metadata_gap_with_parsed_identifier_candidate_count": sum(row["direct_metadata_gap_with_parsed_identifier_candidate_count"] for row in contracts),
        "ambiguous_lineage_edge_count": sum(sum(edge["is_ambiguous"] for edge in row["lineage"]) for row in contracts),
        "runtime_read_write_or_trigger_effect_proven_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_treasury_writable_view_catalog_resolved_column_lineage",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_REFERENCED_ENTITY_COLUMN_LINEAGE",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "business_row_values_or_string_literals_read_or_persisted": 0,
            "view_definitions_read_in_memory_count": len(VIEWS),
            "view_definitions_persisted": 0,
            "procedures_functions_views_triggers_or_application_commands_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": summary,
        "views": contracts,
        "validation_errors": errors,
        "limits": [
            "Catalog-resolved referenced entities describe static view dependencies, not trigger write mappings.",
            "Computed expressions can depend on multiple source columns and need semantic review.",
            "No view or trigger was executed and runtime branch/effect parity remains unproven.",
            "Parsed select identifiers are candidates only; expression semantics and trigger write mapping need separate proof.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
