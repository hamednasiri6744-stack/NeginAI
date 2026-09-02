"""Inspect local read-only Varanegar object metadata without reading row values.

This is a reusable discovery aid. It accepts exact two-part object names and
returns schema, columns, keys, triggers, row counts, foreign keys, and module
consumers. It inherits the pinned local-clone and deny-writer safety checks.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from extract_varanegar_org_domain import (
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
    _table_metadata,
)


def _object_id(cursor: Any, object_name: str) -> int:
    rows = _rows(cursor, "SELECT OBJECT_ID(%s, 'U') object_id", (object_name,))
    object_id = rows[0]["object_id"]
    if object_id is None:
        raise ValueError(f"table not found: {object_name}")
    return int(object_id)


def collect(objects: list[str], find_pattern: str | None = None) -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        discovered = []
        if find_pattern is not None:
            discovered = _rows(cursor, """
              SELECT s.name schema_name,t.name table_name,
                     SUM(CASE WHEN p.index_id IN (0,1) THEN p.rows ELSE 0 END) row_count
              FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
              LEFT JOIN sys.partitions p ON p.object_id=t.object_id
              WHERE t.name LIKE %s
              GROUP BY s.name,t.name ORDER BY s.name,t.name
            """, (find_pattern,))
        ids = [_object_id(cursor, name) for name in objects]
        id_csv = ",".join(str(value) for value in ids)
        metadata = [
            _table_metadata(cursor, name, "ad_hoc_metadata_inspection")
            for name in objects
        ]
        foreign_keys = [] if not ids else _rows(cursor, f"""
          SELECT fk.name constraint_name,
                 OBJECT_SCHEMA_NAME(fk.parent_object_id) parent_schema,
                 OBJECT_NAME(fk.parent_object_id) parent_table,pc.name parent_column,
                 OBJECT_SCHEMA_NAME(fk.referenced_object_id) referenced_schema,
                 OBJECT_NAME(fk.referenced_object_id) referenced_table,rc.name referenced_column,
                 fk.delete_referential_action_desc on_delete,
                 fk.update_referential_action_desc on_update,fk.is_disabled,fk.is_not_trusted
          FROM sys.foreign_keys fk
          JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
          JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
          JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
          WHERE fk.parent_object_id IN ({id_csv}) OR fk.referenced_object_id IN ({id_csv})
          ORDER BY parent_schema,parent_table,fk.name,fkc.constraint_column_id
        """)
        consumers = [] if not ids else _rows(cursor, f"""
          SELECT DISTINCT OBJECT_SCHEMA_NAME(d.referencing_id) consumer_schema,
                 OBJECT_NAME(d.referencing_id) consumer_name,o.type_desc consumer_type,
                 OBJECT_SCHEMA_NAME(d.referenced_id) source_schema,
                 OBJECT_NAME(d.referenced_id) source_table,o.modify_date
          FROM sys.sql_expression_dependencies d
          JOIN sys.objects o ON o.object_id=d.referencing_id
          WHERE d.referenced_id IN ({id_csv})
          ORDER BY source_schema,source_table,consumer_schema,consumer_name
        """)
        return {
            "scope": "local read-only clone; metadata only",
            "safety": safety,
            "objects": metadata,
            "formal_foreign_keys": foreign_keys,
            "module_consumers": consumers,
            "matching_tables": discovered,
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("objects", nargs="*")
    parser.add_argument("--find-pattern")
    args = parser.parse_args()
    if not args.objects and args.find_pattern is None:
        parser.error("provide object names or --find-pattern")
    print(json.dumps(collect(args.objects, args.find_pattern), ensure_ascii=False, indent=2,
                     default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
