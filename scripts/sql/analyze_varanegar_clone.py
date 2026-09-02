"""Extract reproducible, read-only catalog evidence from the Varanegar clone.

The script is deliberately pinned to the local ``NeginPakhsh_WebDev`` clone.
It refuses to continue unless the target is local and the database is read-only.
Passwords are read from ``.env`` and are never included in the output.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytds
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
SERVER = "127.0.0.1"
DATABASE = "NeginPakhsh_WebDev"


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return "0x" + value.hex()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _rows(cursor: Any, sql: str) -> list[dict[str, Any]]:
    cursor.execute(sql)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _try_rows(cursor: Any, sql: str) -> dict[str, Any]:
    try:
        return {"rows": _rows(cursor, sql), "error": None}
    except Exception as exc:  # Evidence gaps belong in the result, not stderr only.
        return {"rows": [], "error": str(exc)}


def _connect() -> Any:
    load_dotenv(ENV_PATH, override=True)
    user = os.environ.get("SQL_USERNAME", "")
    password = os.environ.get("SQL_PASSWORD", "")
    if user != "Negin_Report_ReadOnly" or not password:
        raise RuntimeError("The expected read-only analysis credentials are missing from .env.")
    return pytds.connect(
        dsn=SERVER,
        database=DATABASE,
        user=user,
        password=password,
        login_timeout=6,
        timeout=180,
        readonly=True,
        autocommit=True,
    )


def _assert_safe_target(cursor: Any) -> dict[str, Any]:
    context = _rows(
        cursor,
        """
        SELECT
            CONVERT(nvarchar(128), SERVERPROPERTY('MachineName')) AS machine_name,
            CONVERT(nvarchar(128), @@SERVERNAME) AS server_name,
            DB_NAME() AS database_name,
            SUSER_SNAME() AS login_name,
            USER_NAME() AS database_user,
            DATABASEPROPERTYEX(DB_NAME(), 'Updateability') AS updateability,
            HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'SELECT') AS can_select,
            HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION') AS can_view_definition,
            HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DATABASE STATE') AS can_view_database_state,
            HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'SHOWPLAN') AS can_showplan,
            IS_MEMBER('db_denydatawriter') AS denies_data_writes
        """,
    )[0]
    local_names = {
        socket.gethostname().casefold(),
        os.environ.get("COMPUTERNAME", "").casefold(),
        "localhost",
    }
    if str(context["machine_name"]).casefold() not in local_names:
        raise RuntimeError(f"Safety stop: SQL target is not local: {context!r}")
    if context["database_name"] != DATABASE:
        raise RuntimeError(f"Safety stop: unexpected database: {context!r}")
    if context["updateability"] != "READ_ONLY":
        raise RuntimeError(f"Safety stop: clone is not read-only: {context!r}")
    if context["can_select"] != 1 or context["can_view_definition"] != 1:
        raise RuntimeError(f"Safety stop: analysis permissions are incomplete: {context!r}")
    return context


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        result: dict[str, Any] = {
            "generated_at": datetime.now().astimezone(),
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "catalog and metadata only; no data mutation",
            },
        }
        result["connection"] = _assert_safe_target(cursor)

        result["database_options"] = _rows(
            cursor,
            """
            SELECT name, state_desc, user_access_desc, recovery_model_desc,
                   containment_desc, is_read_only, is_auto_close_on,
                   is_auto_shrink_on, is_read_committed_snapshot_on,
                   snapshot_isolation_state_desc, is_query_store_on,
                   compatibility_level, create_date
            FROM sys.databases
            WHERE name = DB_NAME()
            """,
        )

        result["object_counts"] = _rows(
            cursor,
            """
            SELECT type, type_desc, COUNT_BIG(*) AS object_count
            FROM sys.objects
            WHERE is_ms_shipped = 0
            GROUP BY type, type_desc
            ORDER BY object_count DESC, type_desc
            """,
        )

        result["schema_counts"] = _rows(
            cursor,
            """
            SELECT s.name AS schema_name,
                   SUM(CASE WHEN o.type = 'U' THEN 1 ELSE 0 END) AS table_count,
                   SUM(CASE WHEN o.type = 'V' THEN 1 ELSE 0 END) AS view_count,
                   SUM(CASE WHEN o.type = 'P' THEN 1 ELSE 0 END) AS procedure_count,
                   SUM(CASE WHEN o.type IN ('FN','IF','TF','FS','FT') THEN 1 ELSE 0 END) AS function_count,
                   SUM(CASE WHEN o.type IN ('TR','TA') THEN 1 ELSE 0 END) AS trigger_count
            FROM sys.schemas AS s
            LEFT JOIN sys.objects AS o
              ON o.schema_id = s.schema_id AND o.is_ms_shipped = 0
            GROUP BY s.name
            HAVING COUNT(o.object_id) > 0
            ORDER BY table_count DESC, view_count DESC, s.name
            """,
        )

        result["structural_counts"] = _rows(
            cursor,
            """
            SELECT
                (SELECT COUNT_BIG(*) FROM sys.tables WHERE is_ms_shipped = 0) AS tables,
                (SELECT COUNT_BIG(*) FROM sys.views WHERE is_ms_shipped = 0) AS views,
                (SELECT COUNT_BIG(*) FROM sys.procedures WHERE is_ms_shipped = 0) AS procedures,
                (SELECT COUNT_BIG(*) FROM sys.foreign_keys WHERE is_ms_shipped = 0) AS foreign_keys,
                (SELECT COUNT_BIG(*) FROM sys.key_constraints WHERE type = 'PK') AS primary_keys,
                (SELECT COUNT_BIG(*) FROM sys.triggers WHERE is_ms_shipped = 0) AS triggers,
                (SELECT COUNT_BIG(*) FROM sys.synonyms) AS synonyms,
                (SELECT COUNT_BIG(*) FROM sys.tables t WHERE t.is_ms_shipped = 0
                  AND NOT EXISTS (SELECT 1 FROM sys.key_constraints k
                                  WHERE k.parent_object_id=t.object_id AND k.type='PK')) AS tables_without_pk
            """,
        )

        result["encrypted_objects"] = _rows(
            cursor,
            """
            SELECT
                o.object_id,
                s.name AS schema_name,
                o.name AS object_name,
                o.type,
                o.type_desc,
                OBJECTPROPERTYEX(o.object_id, 'IsEncrypted') AS is_encrypted,
                CASE WHEN m.definition IS NULL THEN 1 ELSE 0 END AS definition_unavailable,
                ps.name AS parent_schema,
                po.name AS parent_object,
                po.type_desc AS parent_type,
                o.create_date,
                o.modify_date
            FROM sys.objects AS o
            JOIN sys.schemas AS s ON s.schema_id = o.schema_id
            LEFT JOIN sys.sql_modules AS m ON m.object_id = o.object_id
            LEFT JOIN sys.objects AS po ON po.object_id = o.parent_object_id
            LEFT JOIN sys.schemas AS ps ON ps.schema_id = po.schema_id
            WHERE o.is_ms_shipped = 0
              AND o.type IN ('P','PC','V','FN','IF','TF','FS','FT','TR','TA')
              AND OBJECTPROPERTYEX(o.object_id, 'IsEncrypted') = 1
            ORDER BY o.type_desc, s.name, o.name
            """,
        )

        result["modules_without_definition"] = _rows(
            cursor,
            """
            SELECT o.object_id, s.name AS schema_name, o.name AS object_name,
                   o.type, o.type_desc,
                   OBJECTPROPERTYEX(o.object_id, 'IsEncrypted') AS is_encrypted
            FROM sys.objects AS o
            JOIN sys.schemas AS s ON s.schema_id = o.schema_id
            LEFT JOIN sys.sql_modules AS m ON m.object_id = o.object_id
            WHERE o.is_ms_shipped = 0
              AND o.type IN ('P','PC','V','FN','IF','TF','FS','FT','TR','TA')
              AND m.definition IS NULL
            ORDER BY o.type_desc, s.name, o.name
            """,
        )

        result["encrypted_inbound_dependencies"] = _rows(
            cursor,
            """
            WITH encrypted AS (
                SELECT object_id
                FROM sys.objects
                WHERE is_ms_shipped = 0
                  AND OBJECTPROPERTYEX(object_id, 'IsEncrypted') = 1
            )
            SELECT
                d.referenced_id AS encrypted_object_id,
                QUOTENAME(rs.name) + '.' + QUOTENAME(ro.name) AS encrypted_object,
                d.referencing_id,
                QUOTENAME(s.name) + '.' + QUOTENAME(o.name) AS referencing_object,
                o.type_desc AS referencing_type,
                d.referenced_minor_id,
                d.is_schema_bound_reference,
                d.is_caller_dependent,
                d.referenced_class_desc
            FROM sys.sql_expression_dependencies AS d
            JOIN encrypted AS e ON e.object_id = d.referenced_id
            JOIN sys.objects AS ro ON ro.object_id = d.referenced_id
            JOIN sys.schemas AS rs ON rs.schema_id = ro.schema_id
            LEFT JOIN sys.objects AS o ON o.object_id = d.referencing_id
            LEFT JOIN sys.schemas AS s ON s.schema_id = o.schema_id
            ORDER BY encrypted_object, referencing_object
            """,
        )

        result["encrypted_outbound_dependencies"] = _rows(
            cursor,
            """
            WITH encrypted AS (
                SELECT object_id
                FROM sys.objects
                WHERE is_ms_shipped = 0
                  AND OBJECTPROPERTYEX(object_id, 'IsEncrypted') = 1
            )
            SELECT
                d.referencing_id AS encrypted_object_id,
                QUOTENAME(s.name) + '.' + QUOTENAME(o.name) AS encrypted_object,
                d.referenced_id,
                COALESCE(QUOTENAME(rs.name) + '.', '') + QUOTENAME(ro.name) AS referenced_object,
                ro.type_desc AS referenced_type,
                d.referenced_server_name,
                d.referenced_database_name,
                d.referenced_schema_name,
                d.referenced_entity_name,
                d.is_schema_bound_reference,
                d.is_caller_dependent
            FROM sys.sql_expression_dependencies AS d
            JOIN encrypted AS e ON e.object_id = d.referencing_id
            JOIN sys.objects AS o ON o.object_id = d.referencing_id
            JOIN sys.schemas AS s ON s.schema_id = o.schema_id
            LEFT JOIN sys.objects AS ro ON ro.object_id = d.referenced_id
            LEFT JOIN sys.schemas AS rs ON rs.schema_id = ro.schema_id
            ORDER BY encrypted_object, referenced_object
            """,
        )

        result["encrypted_parameter_signatures"] = _rows(
            cursor,
            """
            SELECT p.object_id, s.name AS schema_name, o.name AS object_name,
                   p.parameter_id, p.name AS parameter_name,
                   TYPE_NAME(p.user_type_id) AS data_type,
                   p.max_length, p.precision, p.scale, p.is_output,
                   p.has_default_value, CONVERT(nvarchar(4000), p.default_value) AS default_value
            FROM sys.parameters AS p
            JOIN sys.objects AS o ON o.object_id = p.object_id
            JOIN sys.schemas AS s ON s.schema_id = o.schema_id
            WHERE OBJECTPROPERTYEX(o.object_id, 'IsEncrypted') = 1
            ORDER BY s.name, o.name, p.parameter_id
            """,
        )

        # Text search complements catalog dependencies for dynamic SQL and
        # non-schema-bound references.  Only object identity is retained; the
        # caller definition itself is intentionally not exported.
        result["encrypted_textual_references"] = _rows(
            cursor,
            """
            WITH encrypted AS (
                SELECT o.object_id, s.name AS schema_name, o.name AS object_name
                FROM sys.objects AS o
                JOIN sys.schemas AS s ON s.schema_id = o.schema_id
                WHERE o.is_ms_shipped = 0
                  AND OBJECTPROPERTYEX(o.object_id, 'IsEncrypted') = 1
            )
            SELECT e.object_id AS encrypted_object_id,
                   QUOTENAME(e.schema_name) + '.' + QUOTENAME(e.object_name) AS encrypted_object,
                   o.object_id AS referencing_id,
                   QUOTENAME(s.name) + '.' + QUOTENAME(o.name) AS referencing_object,
                   o.type_desc AS referencing_type
            FROM encrypted AS e
            JOIN sys.sql_modules AS m
              ON m.definition LIKE '%' + e.object_name + '%'
            JOIN sys.objects AS o ON o.object_id = m.object_id
            JOIN sys.schemas AS s ON s.schema_id = o.schema_id
            WHERE o.object_id <> e.object_id
            ORDER BY encrypted_object, referencing_object
            """,
        )

        # Compute graph reachability in Python so cycles and many converging
        # paths cannot cause a recursive SQL CTE to explode combinatorially.
        dependency_edges = _rows(
            cursor,
            """
            SELECT DISTINCT referenced_id AS source_id, referencing_id AS target_id
            FROM sys.sql_expression_dependencies
            WHERE referenced_id IS NOT NULL AND referencing_id IS NOT NULL
            """,
        )
        adjacency: dict[int, set[int]] = {}
        for edge in dependency_edges:
            adjacency.setdefault(int(edge["source_id"]), set()).add(int(edge["target_id"]))
        transitive_impact: list[dict[str, Any]] = []
        for encrypted_object in result["encrypted_objects"]:
            root_id = int(encrypted_object["object_id"])
            visited = {root_id}
            frontier = {root_id}
            depth = 0
            while frontier and depth < 12:
                next_frontier: set[int] = set()
                for source_id in frontier:
                    next_frontier.update(adjacency.get(source_id, set()))
                next_frontier.difference_update(visited)
                if not next_frontier:
                    break
                visited.update(next_frontier)
                frontier = next_frontier
                depth += 1
            transitive_impact.append(
                {
                    "encrypted_object": (
                        f"[{encrypted_object['schema_name']}].[{encrypted_object['object_name']}]"
                    ),
                    "distinct_impacted_objects": len(visited) - 1,
                    "maximum_dependency_depth": depth,
                    "depth_limit_reached": bool(frontier and depth == 12),
                }
            )
        result["encrypted_transitive_impact"] = {
            "rows": sorted(
                transitive_impact,
                key=lambda row: (-row["distinct_impacted_objects"], row["encrypted_object"]),
            ),
            "error": None,
        }

        result["change_capture_capabilities"] = _rows(
            cursor,
            """
            SELECT
                (SELECT COUNT_BIG(*) FROM sys.tables WHERE temporal_type <> 0) AS temporal_tables,
                (SELECT COUNT_BIG(*) FROM sys.tables WHERE is_tracked_by_cdc = 1) AS cdc_tables,
                CASE WHEN EXISTS (SELECT 1 FROM sys.change_tracking_databases
                                  WHERE database_id=DB_ID()) THEN 1 ELSE 0 END AS change_tracking_enabled,
                (SELECT is_cdc_enabled FROM sys.databases WHERE database_id=DB_ID()) AS database_cdc_enabled
            """,
        )

        result["top_tables_by_rows"] = _rows(
            cursor,
            """
            SELECT TOP (100)
                s.name AS schema_name,
                t.name AS table_name,
                SUM(p.row_count) AS row_count,
                SUM(p.reserved_page_count) * 8 AS reserved_kb,
                MAX(t.modify_date) AS catalog_modify_date
            FROM sys.tables AS t
            JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            JOIN sys.dm_db_partition_stats AS p ON p.object_id = t.object_id
            WHERE t.is_ms_shipped = 0 AND p.index_id IN (0,1)
            GROUP BY s.name, t.name
            ORDER BY row_count DESC, reserved_kb DESC
            """,
        )

        result["recent_catalog_changes_90d"] = _rows(
            cursor,
            """
            SELECT s.name AS schema_name, o.name AS object_name, o.type_desc,
                   o.create_date, o.modify_date
            FROM sys.objects AS o
            JOIN sys.schemas AS s ON s.schema_id = o.schema_id
            WHERE o.is_ms_shipped = 0
              AND (o.create_date >= DATEADD(day,-90,SYSDATETIME())
                   OR o.modify_date >= DATEADD(day,-90,SYSDATETIME()))
            ORDER BY o.modify_date DESC, o.create_date DESC
            """,
        )

        result["query_store_options"] = _try_rows(
            cursor,
            """
            SELECT actual_state_desc, desired_state_desc, readonly_reason,
                   current_storage_size_mb, max_storage_size_mb,
                   query_capture_mode_desc, stale_query_threshold_days
            FROM sys.database_query_store_options
            """,
        )

        result["index_usage_updates"] = _try_rows(
            cursor,
            """
            SELECT TOP (100) s.name AS schema_name, t.name AS table_name,
                   MAX(ius.last_user_update) AS last_user_update,
                   SUM(COALESCE(ius.user_updates,0)) AS user_updates_since_restart
            FROM sys.tables AS t
            JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            LEFT JOIN sys.dm_db_index_usage_stats AS ius
              ON ius.database_id = DB_ID() AND ius.object_id=t.object_id
            WHERE t.is_ms_shipped = 0
            GROUP BY s.name, t.name
            HAVING MAX(ius.last_user_update) IS NOT NULL
            ORDER BY last_user_update DESC, user_updates_since_restart DESC
            """,
        )

        result["server_start_time"] = _try_rows(
            cursor,
            "SELECT sqlserver_start_time FROM sys.dm_os_sys_info",
        )
        return result
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON output path")
    args = parser.parse_args()
    result = collect()
    payload = json.dumps(result, ensure_ascii=False, indent=2, default=_json_default)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(args.output.resolve())
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
