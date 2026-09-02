from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from app.config import Settings
from app.business_terms import expand_business_query
from app.database import sql_connection, sqlite_connection
from app.schema_catalog import sync_schema_catalog


SCHEMA_SQL = """
SELECT s.name AS schema_name, o.name AS object_name,
       CASE o.type WHEN 'U' THEN 'TABLE' WHEN 'V' THEN 'VIEW' END AS object_type,
       c.column_id, c.name AS column_name, t.name AS data_type,
       c.max_length, c.precision, c.scale, c.is_nullable, c.is_identity,
       CAST(ep.value AS nvarchar(4000)) AS column_caption,
       CASE WHEN pk.column_id IS NULL THEN 0 ELSE 1 END AS is_primary_key
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id = o.schema_id
JOIN sys.columns c ON c.object_id = o.object_id
JOIN sys.types t ON t.user_type_id = c.user_type_id
LEFT JOIN (
    SELECT ic.object_id, ic.column_id
    FROM sys.indexes i
    JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
    WHERE i.is_primary_key = 1
) pk ON pk.object_id = o.object_id AND pk.column_id = c.column_id
LEFT JOIN sys.extended_properties ep ON ep.major_id = o.object_id
    AND ep.minor_id = c.column_id AND ep.name = 'MS_Description'
WHERE o.type IN ('U', 'V') AND o.is_ms_shipped = 0
ORDER BY s.name, o.name, c.column_id
"""

FK_SQL = """
SELECT ss.name AS source_schema, so.name AS source_table, sc.name AS source_column,
       ts.name AS target_schema, tor.name AS target_table, tc.name AS target_column,
       fk.name AS constraint_name
FROM sys.foreign_key_columns fkc
JOIN sys.foreign_keys fk ON fk.object_id = fkc.constraint_object_id
JOIN sys.objects so ON so.object_id = fkc.parent_object_id
JOIN sys.schemas ss ON ss.schema_id = so.schema_id
JOIN sys.columns sc ON sc.object_id = so.object_id AND sc.column_id = fkc.parent_column_id
JOIN sys.objects tor ON tor.object_id = fkc.referenced_object_id
JOIN sys.schemas ts ON ts.schema_id = tor.schema_id
JOIN sys.columns tc ON tc.object_id = tor.object_id AND tc.column_id = fkc.referenced_column_id
ORDER BY ss.name, so.name, fk.name, fkc.constraint_column_id
"""

VIEW_TABLE_USAGE_SQL = """
SELECT VIEW_SCHEMA AS view_schema, VIEW_NAME AS view_name,
       TABLE_SCHEMA AS target_schema, TABLE_NAME AS target_table
FROM INFORMATION_SCHEMA.VIEW_TABLE_USAGE
ORDER BY VIEW_SCHEMA, VIEW_NAME, TABLE_SCHEMA, TABLE_NAME
"""

_SEARCH_TOKEN_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _index_terms(value: str) -> set[str]:
    """Return lookup terms, including parts of technical camel-case names."""
    terms: set[str] = set()
    for token in _SEARCH_TOKEN_RE.findall(value.replace("_", " ")):
        normalized = token.casefold()
        if len(normalized) > 1:
            terms.add(normalized)
        split = _CAMEL_BOUNDARY_RE.sub(" ", token)
        for part in split.split():
            part = part.casefold()
            if len(part) > 1:
                terms.add(part)
    return terms


def rebuild_schema_search_index(settings: Settings) -> int:
    """Build the local, inverted schema index after a metadata/catalog sync."""
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            "SELECT schema_name, object_name, details_json FROM schema_objects"
        ).fetchall()
        entries = [
            (term, row["schema_name"], row["object_name"])
            for row in rows
            for term in _index_terms(row["details_json"])
        ]
        conn.execute("DELETE FROM schema_search_terms")
        conn.executemany(
            "INSERT OR IGNORE INTO schema_search_terms (term, schema_name, object_name) VALUES (?, ?, ?)",
            entries,
        )
    return len(entries)


def _query_dicts(cursor: Any, sql: str) -> list[dict[str, Any]]:
    cursor.execute(sql)
    columns = [str(column[0]) for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def scan_schema(settings: Settings) -> dict[str, int]:
    objects: dict[tuple[str, str], dict[str, Any]] = {}
    with sql_connection(settings) as conn:
        cursor = conn.cursor()
        for row in _query_dicts(cursor, SCHEMA_SQL):
            key = (row["schema_name"], row["object_name"])
            item = objects.setdefault(key, {"schema": row["schema_name"], "name": row["object_name"],
                                            "type": row["object_type"], "columns": [], "foreign_keys": [],
                                            "referenced_by": [], "referenced_tables": []})
            item["columns"].append({
                "ordinal": row["column_id"], "name": row["column_name"], "data_type": row["data_type"],
                "max_length": row["max_length"], "precision": row["precision"], "scale": row["scale"],
                "nullable": bool(row["is_nullable"]), "identity": bool(row["is_identity"]),
                "primary_key": bool(row["is_primary_key"]),
                "official_persian_name": str(row["column_caption"] or "").strip() or None,
            })
        foreign_keys = _query_dicts(cursor, FK_SQL)
        view_table_usage = _query_dicts(cursor, VIEW_TABLE_USAGE_SQL)

    for row in foreign_keys:
        key = (row["source_schema"], row["source_table"])
        if key in objects:
            objects[key]["foreign_keys"].append({
                "name": row["constraint_name"], "column": row["source_column"],
                "target_schema": row["target_schema"], "target_table": row["target_table"],
                "target_column": row["target_column"],
            })
        target_key = (row["target_schema"], row["target_table"])
        if target_key in objects:
            objects[target_key]["referenced_by"].append({
                "name": row["constraint_name"], "source_schema": row["source_schema"],
                "source_table": row["source_table"], "source_column": row["source_column"],
                "target_column": row["target_column"],
            })

    for row in view_table_usage:
        key = (row["view_schema"], row["view_name"])
        if key in objects:
            objects[key]["referenced_tables"].append({
                "schema": row["target_schema"], "name": row["target_table"],
            })

    now = datetime.utcnow().isoformat()
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute("DELETE FROM schema_objects")
        conn.executemany(
            """INSERT INTO schema_objects
               (schema_name, object_name, object_type, details_json, scanned_at)
               VALUES (?, ?, ?, ?, ?)""",
            [(data["schema"], data["name"], data["type"], json.dumps(data, ensure_ascii=False), now)
             for data in objects.values()],
        )
    catalog = sync_schema_catalog(settings)
    indexed_terms = rebuild_schema_search_index(settings)
    return {"objects": len(objects), "columns": sum(len(item["columns"]) for item in objects.values()),
            "foreign_keys": len(foreign_keys), "view_table_dependencies": len(view_table_usage),
            "indexed_terms": indexed_terms, **catalog}


def search_schema(
    settings: Settings,
    query: str,
    limit: int = 50,
    *,
    object_type: str | None = None,
) -> list[dict[str, Any]]:
    """Search cached schema objects, optionally restricting to Views or Tables."""
    terms = expand_business_query(query)
    if not terms:
        return []
    with sqlite_connection(settings.sqlite_path) as conn:
        index_count = int(conn.execute("SELECT COUNT(*) FROM schema_search_terms").fetchone()[0])
    # Existing deployments have a schema cache created before this index was
    # introduced.  Build it once lazily; every following lookup is indexed.
    if index_count == 0:
        rebuild_schema_search_index(settings)
    with sqlite_connection(settings.sqlite_path) as conn:
        placeholders = ", ".join("?" for _ in terms)
        rows = conn.execute(
            f"""SELECT so.details_json
                FROM schema_search_terms AS si
                JOIN schema_objects AS so
                  ON so.schema_name = si.schema_name AND so.object_name = si.object_name
                WHERE si.term IN ({placeholders})
                GROUP BY so.schema_name, so.object_name""",
            terms,
        ).fetchall()

    ranked: list[tuple[int, str, str, dict[str, Any]]] = []
    for row in rows:
        item = json.loads(row["details_json"])
        if object_type and str(item.get("type") or "").upper() != object_type.upper():
            continue
        schema_name = str(item.get("schema", "")).casefold()
        object_name = str(item.get("name", "")).casefold()
        column_names = [str(column.get("name", "")).casefold() for column in item.get("columns", [])]
        full_text = row["details_json"].casefold()
        score = 0
        for term in terms:
            if object_name == term:
                score += 100
            elif object_name.startswith(term):
                score += 50
            elif term in object_name:
                score += 25
            if term in schema_name:
                score += 10
            if term in column_names:
                score += 8
            elif any(term in column for column in column_names):
                score += 4
            elif term in full_text:
                score += 1
        if score:
            ranked.append((score, schema_name, object_name, item))

    ranked.sort(key=lambda value: (-value[0], value[1], value[2]))
    return [value[3] for value in ranked[:limit]]


def summarize_schema_results(results: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    terms = expand_business_query(query)
    summaries = []
    for item in results:
        columns = item.get("columns", [])
        matched_columns = [
            str(column.get("name", ""))
            for column in columns
            if any(term in str(column.get("name", "")).casefold() for term in terms)
        ][:15]
        summaries.append({
            "schema": item.get("schema"),
            "name": item.get("name"),
            "type": item.get("type"),
            "column_count": len(columns),
            "matched_columns": matched_columns,
            "foreign_key_count": len(item.get("foreign_keys", [])),
            "referenced_by_count": len(item.get("referenced_by", [])),
            "persian_name": (item.get("catalog") or {}).get("persian_name"),
            "domain": (item.get("catalog") or {}).get("domain"),
            "classification": (item.get("catalog") or {}).get("classification"),
            "seller_access": (item.get("catalog") or {}).get("seller_access"),
        })
    return summaries


def get_schema_object(settings: Settings, schema: str, name: str) -> dict[str, Any] | None:
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT details_json FROM schema_objects WHERE schema_name = ? AND object_name = ?",
            (schema, name),
        ).fetchone()
    return json.loads(row["details_json"]) if row else None


def list_schema_catalog(settings: Settings) -> list[dict[str, Any]]:
    """Return the cached schema inventory for the human-facing catalog."""
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            """SELECT details_json FROM schema_objects
               ORDER BY schema_name COLLATE NOCASE, object_name COLLATE NOCASE"""
        ).fetchall()
    return [json.loads(row["details_json"]) for row in rows]


def schema_stats(settings: Settings) -> dict[str, int | str | None]:
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            "SELECT object_type, COUNT(*) AS count FROM schema_objects GROUP BY object_type"
        ).fetchall()
        last_scan = conn.execute("SELECT MAX(scanned_at) FROM schema_objects").fetchone()[0]
        classifications = {
            str(row["data_classification"]): int(row["count"])
            for row in conn.execute(
                """SELECT data_classification, COUNT(*) AS count
                   FROM schema_catalog GROUP BY data_classification"""
            ).fetchall()
        }
    counts = {row["object_type"]: row["count"] for row in rows}
    tables = int(counts.get("TABLE", 0))
    views = int(counts.get("VIEW", 0))
    return {
        "tables": tables,
        "views": views,
        "total_objects": tables + views,
        "last_scan": last_scan,
        "classifications": classifications,
    }
