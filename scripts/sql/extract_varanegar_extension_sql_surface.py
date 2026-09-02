"""Extract catalog-only SQL candidates for material Varanegar extensions.

The extractor is pinned to the local read-only NeginPakhsh_WebDev clone. It
persists schema metadata and definition fingerprints only; no business rows,
module definitions, credentials, or identity grants are persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
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


SEARCH_TERMS: dict[str, tuple[str, ...]] = {
    "authorization.stock_accounting_access": (
        "StockAccAccess",
        "StockUserAndGroupAccess",
        "UserDCAccess",
        "UserDistAccess",
        "UserSaleAccess",
    ),
    "configuration.accounting_article_template": ("ArticleTemplate",),
    "configuration.general": ("GeneralConfig",),
    "configuration.web_service": ("WebConfig", "WebServiceConfig"),
    "pos.charge_device": ("BaseChargeDevice",),
    "pos.instalment_method": ("InstalmentMethod",),
    "pos.linear_discount": ("LinearDiscount", "POSLineDiscount"),
    "pos.safe": ("POSSafe",),
    "pos.session": ("POSSession", "ReplicateSalesReceipt"),
    "pos.subscriber": ("Subscriber",),
    "tablet.dealer_day_path": ("DealerDayPath", "DealerPath", "DealersDay"),
    "tablet.visit_template": ("VisitTemplate", "VisiteTemplate"),
}


def _normalized(value: str) -> str:
    return "".join(char for char in value.casefold() if char.isalnum())


def _catalog_candidates(cursor: Any) -> list[dict[str, Any]]:
    candidates: dict[int, dict[str, Any]] = {}
    matches: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for capability, terms in SEARCH_TERMS.items():
        for term in terms:
            rows = _rows(
                cursor,
                """
                SELECT o.object_id,s.name AS schema_name,o.name AS object_name,
                       o.type,o.type_desc,o.create_date,o.modify_date,
                       m.definition
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.is_ms_shipped=0 AND o.name LIKE %s
                  AND o.type IN ('U','V','P','FN','IF','TF','TR')
                ORDER BY s.name,o.name,o.type
                """,
                (f"%{term}%",),
            )
            for row in rows:
                row["type"] = str(row["type"]).strip()
                object_id = int(row["object_id"])
                candidates[object_id] = row
                matches[object_id][capability].add(term)

    result = []
    for object_id, row in sorted(
        candidates.items(), key=lambda pair: (pair[1]["schema_name"], pair[1]["object_name"], pair[1]["type"])
    ):
        definition = row.pop("definition") or ""
        capability_matches = [
            {"capability": capability, "matched_terms": sorted(terms)}
            for capability, terms in sorted(matches[object_id].items())
        ]
        normalized_name = _normalized(row["object_name"])
        all_terms = sorted({term for values in matches[object_id].values() for term in values})
        match_strength = "EXACT_NORMALIZED_NAME" if normalized_name in {_normalized(term) for term in all_terms} else "NAME_CONTAINS_TERM"
        result.append(
            {
                **row,
                "definition_length": len(definition),
                "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest() if definition else None,
                "match_strength": match_strength,
                "capability_matches": capability_matches,
            }
        )
    return result


def _columns(cursor: Any, ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not ids:
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    rows = _rows(
        cursor,
        f"""
        SELECT c.object_id,c.column_id,c.name AS column_name,
               TYPE_NAME(c.user_type_id) AS data_type,c.max_length,c.precision,c.scale,
               c.is_nullable,c.is_identity,c.is_computed,
               CASE WHEN pk.column_id IS NULL THEN 0 ELSE 1 END AS is_primary_key
        FROM sys.columns c
        LEFT JOIN (
            SELECT ic.object_id,ic.column_id
            FROM sys.indexes i
            JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
            WHERE i.is_primary_key=1
        ) pk ON pk.object_id=c.object_id AND pk.column_id=c.column_id
        WHERE c.object_id IN ({placeholders})
        ORDER BY c.object_id,c.column_id
        """,
        tuple(ids),
    )
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row.pop("object_id"))].append(row)
    return grouped


def _parameters(cursor: Any, ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not ids:
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    rows = _rows(
        cursor,
        f"""
        SELECT p.object_id,p.parameter_id,p.name AS parameter_name,
               TYPE_NAME(p.user_type_id) AS data_type,p.max_length,p.precision,p.scale,p.is_output
        FROM sys.parameters p
        WHERE p.object_id IN ({placeholders})
        ORDER BY p.object_id,p.parameter_id
        """,
        tuple(ids),
    )
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row.pop("object_id"))].append(row)
    return grouped


def _dependencies(cursor: Any, ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not ids:
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    rows = _rows(
        cursor,
        f"""
        SELECT DISTINCT d.referencing_id,
               COALESCE(d.referenced_schema_name,OBJECT_SCHEMA_NAME(d.referenced_id)) AS schema_name,
               COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) AS object_name,
               COALESCE(o.type_desc,'UNRESOLVED_OR_COLUMN_REFERENCE') AS type_desc
        FROM sys.sql_expression_dependencies d
        LEFT JOIN sys.objects o ON o.object_id=d.referenced_id
        WHERE d.referencing_id IN ({placeholders})
          AND COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) IS NOT NULL
        ORDER BY d.referencing_id,schema_name,object_name,type_desc
        """,
        tuple(ids),
    )
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row.pop("referencing_id"))].append(row)
    return grouped


def _table_metadata(cursor: Any, ids: list[int]) -> tuple[dict[int, int], dict[int, list[dict[str, Any]]], dict[int, list[dict[str, Any]]]]:
    if not ids:
        return {}, {}, {}
    placeholders = ",".join(["%s"] * len(ids))
    counts = _rows(
        cursor,
        f"""
        SELECT p.object_id,SUM(CASE WHEN p.index_id IN (0,1) THEN p.row_count ELSE 0 END) AS row_count
        FROM sys.dm_db_partition_stats p
        WHERE p.object_id IN ({placeholders})
        GROUP BY p.object_id
        """,
        tuple(ids),
    )
    row_counts = {int(row["object_id"]): int(row["row_count"] or 0) for row in counts}
    foreign_keys = _rows(
        cursor,
        f"""
        SELECT fk.parent_object_id,fk.name AS constraint_name,
               COL_NAME(fkc.parent_object_id,fkc.parent_column_id) AS parent_column,
               OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS referenced_schema,
               OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
               COL_NAME(fkc.referenced_object_id,fkc.referenced_column_id) AS referenced_column
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        WHERE fk.parent_object_id IN ({placeholders})
        ORDER BY fk.parent_object_id,fk.name,fkc.constraint_column_id
        """,
        tuple(ids),
    )
    triggers = _rows(
        cursor,
        f"""
        SELECT tr.parent_id,tr.name AS trigger_name,tr.is_disabled,
               LEN(COALESCE(m.definition,'')) AS definition_length,
               HASHBYTES('SHA2_256',CONVERT(varbinary(max),COALESCE(m.definition,''))) AS definition_hash
        FROM sys.triggers tr
        LEFT JOIN sys.sql_modules m ON m.object_id=tr.object_id
        WHERE tr.parent_id IN ({placeholders})
        ORDER BY tr.parent_id,tr.name
        """,
        tuple(ids),
    )
    fk_grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    trigger_grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in foreign_keys:
        fk_grouped[int(row.pop("parent_object_id"))].append(row)
    for row in triggers:
        object_id = int(row.pop("parent_id"))
        raw_hash = row.pop("definition_hash")
        row["definition_sha256"] = bytes(raw_hash).hex() if raw_hash is not None else None
        trigger_grouped[object_id].append(row)
    return row_counts, fk_grouped, trigger_grouped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            objects = _catalog_candidates(cursor)
            ids = [int(row["object_id"]) for row in objects]
            table_ids = [int(row["object_id"]) for row in objects if row["type"] == "U"]
            columns = _columns(cursor, ids)
            parameters = _parameters(cursor, ids)
            dependencies = _dependencies(cursor, ids)
            row_counts, foreign_keys, triggers = _table_metadata(cursor, table_ids)

    by_capability: dict[str, list[str]] = defaultdict(list)
    for row in objects:
        object_id = int(row["object_id"])
        row["columns"] = columns.get(object_id, [])
        row["parameters"] = parameters.get(object_id, [])
        row["dependencies"] = dependencies.get(object_id, [])
        row["row_count_metadata"] = row_counts.get(object_id) if row["type"] == "U" else None
        row["foreign_keys"] = foreign_keys.get(object_id, [])
        row["triggers"] = triggers.get(object_id, [])
        for match in row["capability_matches"]:
            by_capability[match["capability"]].append(f"{row['schema_name']}.{row['object_name']}")
        del row["object_id"]

    capability_coverage = [
        {
            "capability": capability,
            "search_terms": list(terms),
            "candidate_objects": sorted(set(by_capability.get(capability, []))),
            "candidate_count": len(set(by_capability.get(capability, []))),
            "status": "CATALOG_CANDIDATES_FOUND" if by_capability.get(capability) else "NO_NAME_MATCH_REQUIRES_DEEPER_TRACE",
        }
        for capability, terms in SEARCH_TERMS.items()
    ]
    errors = []
    if context["database_name"] != DATABASE or context["updateability"] != "READ_ONLY":
        errors.append("unsafe database context")
    artifact = {
        "artifact": "varanegar_material_extension_clone_sql_catalog_surface",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_METADATA_ONLY",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_definitions_persisted": 0,
            "credentials_or_secrets_persisted": 0,
            "identity_grants_read_or_persisted": 0,
            "procedures_functions_or_triggers_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": {
            "capability_count": len(SEARCH_TERMS),
            "capability_with_candidate_count": sum(bool(row["candidate_count"]) for row in capability_coverage),
            "capability_without_candidate_count": sum(not row["candidate_count"] for row in capability_coverage),
            "candidate_object_count": len(objects),
            "candidate_table_count": sum(row["type"] == "U" for row in objects),
            "candidate_module_count": sum(row["type"] != "U" for row in objects),
            "column_metadata_count": sum(len(row["columns"]) for row in objects),
            "foreign_key_metadata_count": sum(len(row["foreign_keys"]) for row in objects),
            "trigger_metadata_count": sum(len(row["triggers"]) for row in objects),
            "module_dependency_count": sum(len(row["dependencies"]) for row in objects),
            "validation_error_count": len(errors),
        },
        "capability_coverage": capability_coverage,
        "objects": objects,
        "validation_errors": errors,
        "limits": [
            "Object-name matching yields candidates, not a proven UI-to-SQL execution path.",
            "The clone can lag operational Varanegar; freshness must be measured before migration or release use.",
            "Row counts come from partition metadata; no business row values were selected.",
            "Encrypted, dynamic SQL, ORM mapping and runtime configuration can hide dependencies.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
