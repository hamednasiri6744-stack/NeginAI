"""Extract a privacy-safe NGT order persistence and replication boundary.

The extractor runs only against the approved local READ_ONLY clone. It stores
catalog identifiers, SQL-definition hashes, anonymous state aggregates, and
date buckets. It never executes a stored procedure or application command and
never persists raw order, customer, user, configuration, host, or path values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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


TABLES = (
    ("NGT", "Tours"),
    ("NGT", "CustomerCalls"),
    ("NGT", "CustomerCallOrders"),
    ("NGT", "CustomerCallOrderLines"),
    ("NGT", "CustomerCallOrderLineOrderQtyDetails"),
    ("NGT", "CustomerCallOrderLineInvoiceQtyDetails"),
    ("NGT", "CustomerCallOrderStatus"),
)

WINDOW_START = "2026-05-22T00:00:00"
WINDOW_END_EXCLUSIVE = "2026-08-23T00:00:00"

SQL_OBJECT_REF = re.compile(
    r"\b(?:EXEC(?:UTE)?|INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO|FROM|JOIN)\s+"
    r"(?P<object>(?:\[(?:dbo|NGT|FRU|SLE|GNR|ACC)\]|(?:dbo|NGT|FRU|SLE|GNR|ACC))"
    r"\.\[[A-Za-z_][A-Za-z0-9_]*\]|(?:dbo|NGT|FRU|SLE|GNR|ACC)\."
    r"[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)


def _qualified(schema: str, table: str) -> str:
    return f"{schema}.{table}"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _catalog_columns(cursor: Any) -> list[dict[str, Any]]:
    predicates = " OR ".join(
        f"(s.name=N'{schema}' AND t.name=N'{table}')" for schema, table in TABLES
    )
    return _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
               ty.name data_type,c.is_nullable,c.is_identity,
               dc.definition default_definition
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        LEFT JOIN sys.default_constraints dc
          ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
        WHERE {predicates}
        ORDER BY s.name,t.name,c.column_id
        """,
    )


def _catalog_profiles(cursor: Any, columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in columns:
        by_table[_qualified(row["schema_name"], row["table_name"])].append(row)
    result = []
    for schema, table in TABLES:
        qualified = _qualified(schema, table)
        table_columns = by_table[qualified]
        names = {row["column_name"] for row in table_columns}
        aggregates = ["COUNT_BIG(*) row_count"]
        if "IsRemoved" in names:
            aggregates.extend(
                [
                    "SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed_count",
                    "SUM(CASE WHEN ISNULL(IsRemoved,0)=0 THEN 1 ELSE 0 END) active_count",
                ]
            )
        counts = _rows(
            cursor,
            f"SELECT {','.join(aggregates)} FROM [{schema}].[{table}]",
        )[0]
        result.append(
            {
                "qualified_name": qualified,
                "column_count": len(table_columns),
                "columns": [
                    {
                        "column_name": row["column_name"],
                        "data_type": row["data_type"],
                        "is_nullable": bool(row["is_nullable"]),
                        "is_identity": bool(row["is_identity"]),
                        "has_default": row["default_definition"] is not None,
                        "default_definition_sha256": None
                        if row["default_definition"] is None
                        else _sha256(row["default_definition"]),
                    }
                    for row in table_columns
                ],
                "anonymous_counts": counts,
            }
        )
    return result


def _unique_indexes(cursor: Any) -> list[dict[str, Any]]:
    predicates = " OR ".join(
        f"(s.name=N'{schema}' AND t.name=N'{table}')" for schema, table in TABLES
    )
    rows = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,i.name index_name,
               i.is_unique,i.is_primary_key,i.has_filter,i.filter_definition,
               ic.key_ordinal,ic.is_included_column,c.name column_name
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.indexes i ON i.object_id=t.object_id AND i.index_id>0
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE ({predicates}) AND (i.is_unique=1 OR i.is_primary_key=1)
        ORDER BY s.name,t.name,i.index_id,ic.key_ordinal,ic.index_column_id
        """,
    )
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        qualified = _qualified(row["schema_name"], row["table_name"])
        key = (qualified, row["index_name"])
        contract = grouped.setdefault(
            key,
            {
                "qualified_table": qualified,
                "index_name": row["index_name"],
                "is_unique": bool(row["is_unique"]),
                "is_primary_key": bool(row["is_primary_key"]),
                "has_filter": bool(row["has_filter"]),
                "filter_uses_removed_state": "isremoved"
                in (row["filter_definition"] or "").casefold(),
                "key_columns": [],
                "included_columns": [],
            },
        )
        destination = "included_columns" if row["is_included_column"] else "key_columns"
        contract[destination].append(row["column_name"])
    return list(grouped.values())


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    target_names = {_qualified(schema, table).casefold() for schema, table in TABLES}
    rows = _rows(
        cursor,
        """
        SELECT fk.name constraint_name,fk.is_disabled,fk.is_not_trusted,
               ps.name parent_schema,pt.name parent_table,pc.name parent_column,
               rs.name referenced_schema,rt.name referenced_table,rc.name referenced_column,
               fkc.constraint_column_id
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.tables pt ON pt.object_id=fk.parent_object_id
        JOIN sys.schemas ps ON ps.schema_id=pt.schema_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.tables rt ON rt.object_id=fk.referenced_object_id
        JOIN sys.schemas rs ON rs.schema_id=rt.schema_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        ORDER BY ps.name,pt.name,fk.name,fkc.constraint_column_id
        """,
    )
    result = []
    for row in rows:
        parent = _qualified(row["parent_schema"], row["parent_table"])
        referenced = _qualified(row["referenced_schema"], row["referenced_table"])
        if parent.casefold() not in target_names and referenced.casefold() not in target_names:
            continue
        result.append(
            {
                "constraint_name": row["constraint_name"],
                "parent_table": parent,
                "parent_column": row["parent_column"],
                "referenced_table": referenced,
                "referenced_column": row["referenced_column"],
                "is_disabled": bool(row["is_disabled"]),
                "is_not_trusted": bool(row["is_not_trusted"]),
                "constraint_column_id": row["constraint_column_id"],
            }
        )
    return result


def _triggers(cursor: Any) -> list[dict[str, Any]]:
    predicates = " OR ".join(
        f"(s.name=N'{schema}' AND t.name=N'{table}')" for schema, table in TABLES
    )
    rows = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,tr.name trigger_name,
               tr.is_disabled,tr.is_instead_of_trigger,sm.definition
        FROM sys.triggers tr
        JOIN sys.tables t ON t.object_id=tr.parent_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        LEFT JOIN sys.sql_modules sm ON sm.object_id=tr.object_id
        WHERE {predicates}
        ORDER BY s.name,t.name,tr.name
        """,
    )
    return [
        {
            "qualified_table": _qualified(row["schema_name"], row["table_name"]),
            "trigger_name": row["trigger_name"],
            "is_disabled": bool(row["is_disabled"]),
            "is_instead_of_trigger": bool(row["is_instead_of_trigger"]),
            "definition_sha256": None
            if row["definition"] is None
            else _sha256(row["definition"]),
            "definition_length": 0 if row["definition"] is None else len(row["definition"]),
        }
        for row in rows
    ]


def _header_state(cursor: Any) -> dict[str, Any]:
    aggregate = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) total_count,
          SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active_count,
          SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed_count,
          SUM(CASE WHEN IsCanceled=1 THEN 1 ELSE 0 END) canceled_count,
          SUM(CASE WHEN SendToConsoleDate IS NOT NULL THEN 1 ELSE 0 END) sent_to_console_count,
          SUM(CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0 THEN 1 ELSE 0 END) backoffice_order_id_count,
          SUM(CASE WHEN BackOfficeOrderUniqueId IS NOT NULL THEN 1 ELSE 0 END) backoffice_order_uuid_count,
          SUM(CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N''))>0 THEN 1 ELSE 0 END) backoffice_invoice_id_count,
          SUM(CASE WHEN BackOfficeInvoiceUniqueId IS NOT NULL THEN 1 ELSE 0 END) backoffice_invoice_uuid_count,
          SUM(CASE WHEN IsInvoice=1 THEN 1 ELSE 0 END) invoice_flag_count,
          SUM(CASE WHEN IsCanceled=1 AND TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0 THEN 1 ELSE 0 END) canceled_with_backoffice_order_count,
          SUM(CASE WHEN SendToConsoleDate IS NOT NULL AND ISNULL(TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N'')),0)<=0 THEN 1 ELSE 0 END) sent_without_numeric_order_id_count,
          SUM(CASE WHEN SendToConsoleDate IS NULL AND TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0 THEN 1 ELSE 0 END) unsent_with_numeric_order_id_count,
          SUM(CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0 AND BackOfficeOrderUniqueId IS NULL THEN 1 ELSE 0 END) numeric_order_without_uuid_count,
          SUM(CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N''))>0 AND BackOfficeInvoiceUniqueId IS NULL THEN 1 ELSE 0 END) numeric_invoice_without_uuid_count
        FROM NGT.CustomerCallOrders
        """,
    )[0]
    matrix = _rows(
        cursor,
        """
        SELECT CAST(IsRemoved AS int) is_removed,
               CAST(IsCanceled AS int) is_canceled,
               CASE WHEN SendToConsoleDate IS NULL THEN 0 ELSE 1 END has_send_to_console_date,
               CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0 THEN 1 ELSE 0 END has_numeric_backoffice_order_id,
               CASE WHEN BackOfficeOrderUniqueId IS NULL THEN 0 ELSE 1 END has_backoffice_order_uuid,
               CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N''))>0 THEN 1 ELSE 0 END has_numeric_backoffice_invoice_id,
               CASE WHEN BackOfficeInvoiceUniqueId IS NULL THEN 0 ELSE 1 END has_backoffice_invoice_uuid,
               CAST(IsInvoice AS int) is_invoice,
               COUNT_BIG(*) row_count
        FROM NGT.CustomerCallOrders
        GROUP BY CAST(IsRemoved AS int),CAST(IsCanceled AS int),
                 CASE WHEN SendToConsoleDate IS NULL THEN 0 ELSE 1 END,
                 CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0 THEN 1 ELSE 0 END,
                 CASE WHEN BackOfficeOrderUniqueId IS NULL THEN 0 ELSE 1 END,
                 CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N''))>0 THEN 1 ELSE 0 END,
                 CASE WHEN BackOfficeInvoiceUniqueId IS NULL THEN 0 ELSE 1 END,
                 CAST(IsInvoice AS int)
        ORDER BY is_removed,is_canceled,has_send_to_console_date,
                 has_numeric_backoffice_order_id,has_backoffice_order_uuid,
                 has_numeric_backoffice_invoice_id,has_backoffice_invoice_uuid,is_invoice
        """,
    )
    duplicate_groups = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM (
             SELECT TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N'')) value
             FROM NGT.CustomerCallOrders
             WHERE TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0
             GROUP BY TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))
             HAVING COUNT_BIG(*)>1
           ) d) duplicate_numeric_backoffice_order_id_group_count,
          (SELECT COALESCE(SUM(group_count),0) FROM (
             SELECT COUNT_BIG(*) group_count
             FROM NGT.CustomerCallOrders
             WHERE TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0
             GROUP BY TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))
             HAVING COUNT_BIG(*)>1
           ) d) headers_in_duplicate_numeric_order_id_groups,
          (SELECT COALESCE(MAX(group_count),0) FROM (
             SELECT COUNT_BIG(*) group_count
             FROM NGT.CustomerCallOrders
             WHERE TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0
             GROUP BY TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))
           ) d) maximum_headers_per_numeric_backoffice_order_id,
          (SELECT COUNT_BIG(*) FROM (
             SELECT TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N'')) value
             FROM NGT.CustomerCallOrders
             WHERE TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N''))>0
             GROUP BY TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N''))
             HAVING COUNT_BIG(*)>1
           ) d) duplicate_numeric_backoffice_invoice_id_group_count,
          (SELECT COALESCE(MAX(group_count),0) FROM (
             SELECT COUNT_BIG(*) group_count
             FROM NGT.CustomerCallOrders
             WHERE TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N''))>0
             GROUP BY TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N''))
           ) d) maximum_headers_per_numeric_backoffice_invoice_id,
          (SELECT COUNT_BIG(*) FROM (
             SELECT BackOfficeInvoiceUniqueId value
             FROM NGT.CustomerCallOrders
             WHERE BackOfficeInvoiceUniqueId IS NOT NULL
             GROUP BY BackOfficeInvoiceUniqueId
             HAVING COUNT_BIG(*)>1
           ) d) duplicate_backoffice_invoice_uuid_group_count
        """,
    )[0]
    return {
        "aggregate": aggregate,
        "state_matrix": matrix,
        "duplicate_crosswalk_groups": duplicate_groups,
    }


def _line_boundary(cursor: Any) -> dict[str, Any]:
    aggregate = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) line_count,
          SUM(CASE WHEN l.IsRemoved=0 THEN 1 ELSE 0 END) active_line_count,
          SUM(CASE WHEN h.Id IS NULL THEN 1 ELSE 0 END) orphan_line_count,
          SUM(CASE WHEN l.IsRemoved=0 AND h.IsRemoved=1 THEN 1 ELSE 0 END) active_line_under_removed_header_count,
          SUM(CASE WHEN TRY_CONVERT(bigint,NULLIF(l.BackOfficeOrderRef,N''))>0 THEN 1 ELSE 0 END) numeric_backoffice_order_ref_count,
          SUM(CASE WHEN l.BackOfficeOrderUniqueId IS NOT NULL THEN 1 ELSE 0 END) backoffice_order_uuid_count,
          SUM(CASE WHEN TRY_CONVERT(bigint,NULLIF(l.BackOfficeOrderRef,N''))>0 AND l.BackOfficeOrderUniqueId IS NULL THEN 1 ELSE 0 END) numeric_ref_without_uuid_count,
          SUM(CASE WHEN l.IsRemoved=0 AND ISNULL(TRY_CONVERT(bigint,NULLIF(l.BackOfficeOrderRef,N'')),0)<=0 AND TRY_CONVERT(bigint,NULLIF(h.BackOfficeOrderId,N''))>0 THEN 1 ELSE 0 END) active_unmapped_line_under_mapped_header_count,
          SUM(CASE WHEN l.IsRemoved=0 AND TRY_CONVERT(bigint,NULLIF(l.BackOfficeOrderRef,N''))>0 AND ISNULL(TRY_CONVERT(bigint,NULLIF(h.BackOfficeOrderId,N'')),0)<=0 THEN 1 ELSE 0 END) active_mapped_line_under_unmapped_header_count,
          SUM(CASE WHEN l.ApplicationOwnerId<>h.ApplicationOwnerId OR l.DataOwnerId<>h.DataOwnerId OR l.DataOwnerCenterId<>h.DataOwnerCenterId THEN 1 ELSE 0 END) parent_scope_mismatch_count
        FROM NGT.CustomerCallOrderLines l
        LEFT JOIN NGT.CustomerCallOrders h ON h.Id=l.CustomerCallOrderUniqueId
        """,
    )[0]
    groups = _rows(
        cursor,
        """
        WITH line_state AS (
          SELECT CustomerCallOrderUniqueId,
            COUNT_BIG(*) line_count,
            SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active_line_count,
            SUM(CASE WHEN IsRemoved=0 AND TRY_CONVERT(bigint,NULLIF(BackOfficeOrderRef,N''))>0 THEN 1 ELSE 0 END) active_mapped_line_count,
            COUNT(DISTINCT CASE WHEN IsRemoved=0 THEN TRY_CONVERT(bigint,NULLIF(BackOfficeOrderRef,N'')) END) distinct_backoffice_order_count
          FROM NGT.CustomerCallOrderLines
          GROUP BY CustomerCallOrderUniqueId
        )
        SELECT COUNT_BIG(*) order_with_lines_count,
          SUM(CASE WHEN active_mapped_line_count=active_line_count AND active_line_count>0 THEN 1 ELSE 0 END) all_active_lines_mapped_order_count,
          SUM(CASE WHEN active_mapped_line_count>0 AND active_mapped_line_count<active_line_count THEN 1 ELSE 0 END) partially_mapped_order_count,
          SUM(CASE WHEN distinct_backoffice_order_count>1 THEN 1 ELSE 0 END) split_backoffice_order_count,
          MAX(distinct_backoffice_order_count) maximum_backoffice_orders_per_ngt_order
        FROM line_state
        """,
    )[0]
    matrix = _rows(
        cursor,
        """
        WITH line_state AS (
          SELECT CustomerCallOrderUniqueId,
            SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active_line_count,
            SUM(CASE WHEN IsRemoved=0 AND TRY_CONVERT(bigint,NULLIF(BackOfficeOrderRef,N''))>0 THEN 1 ELSE 0 END) active_mapped_line_count
          FROM NGT.CustomerCallOrderLines
          GROUP BY CustomerCallOrderUniqueId
        )
        SELECT CASE WHEN TRY_CONVERT(bigint,NULLIF(h.BackOfficeOrderId,N''))>0 THEN 1 ELSE 0 END has_numeric_header_order_id,
               CASE WHEN ls.active_line_count=0 THEN 'NO_ACTIVE_LINES'
                    WHEN ls.active_mapped_line_count=0 THEN 'NONE_MAPPED'
                    WHEN ls.active_mapped_line_count=ls.active_line_count THEN 'ALL_MAPPED'
                    ELSE 'PARTIAL' END active_line_mapping_state,
               COUNT_BIG(*) order_count,
               SUM(ls.active_line_count) active_line_count,
               SUM(ls.active_mapped_line_count) active_mapped_line_count
        FROM NGT.CustomerCallOrders h
        JOIN line_state ls ON ls.CustomerCallOrderUniqueId=h.Id
        GROUP BY CASE WHEN TRY_CONVERT(bigint,NULLIF(h.BackOfficeOrderId,N''))>0 THEN 1 ELSE 0 END,
                 CASE WHEN ls.active_line_count=0 THEN 'NO_ACTIVE_LINES'
                      WHEN ls.active_mapped_line_count=0 THEN 'NONE_MAPPED'
                      WHEN ls.active_mapped_line_count=ls.active_line_count THEN 'ALL_MAPPED'
                      ELSE 'PARTIAL' END
        ORDER BY has_numeric_header_order_id,active_line_mapping_state
        """,
    )
    return {
        "aggregate": aggregate,
        "parent_mapping_groups": groups,
        "header_line_mapping_matrix": matrix,
    }


def _quantity_boundary(cursor: Any) -> list[dict[str, Any]]:
    result = []
    for table in (
        "CustomerCallOrderLineOrderQtyDetails",
        "CustomerCallOrderLineInvoiceQtyDetails",
    ):
        row = _rows(
            cursor,
            f"""
            SELECT COUNT_BIG(*) row_count,
              SUM(CASE WHEN d.IsRemoved=0 THEN 1 ELSE 0 END) active_count,
              SUM(CASE WHEN l.Id IS NULL THEN 1 ELSE 0 END) orphan_line_count,
              SUM(CASE WHEN d.IsRemoved=0 AND l.IsRemoved=1 THEN 1 ELSE 0 END) active_detail_under_removed_line_count,
              SUM(CASE WHEN d.ApplicationOwnerId<>l.ApplicationOwnerId OR d.DataOwnerId<>l.DataOwnerId OR d.DataOwnerCenterId<>l.DataOwnerCenterId THEN 1 ELSE 0 END) parent_scope_mismatch_count
            FROM NGT.[{table}] d
            LEFT JOIN NGT.CustomerCallOrderLines l ON l.Id=d.CustomerCallOrderLineUniqueId
            """,
        )[0]
        result.append({"qualified_table": f"NGT.{table}", **row})
    return result


def _window_activity(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        f"""
        SELECT CONVERT(char(7),LastUpdate,120) month_bucket,
               COUNT_BIG(*) updated_header_count,
               SUM(CASE WHEN IsCanceled=1 THEN 1 ELSE 0 END) canceled_header_count,
               SUM(CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeOrderId,N''))>0 THEN 1 ELSE 0 END) mapped_order_header_count,
               SUM(CASE WHEN TRY_CONVERT(bigint,NULLIF(BackOfficeInvoiceId,N''))>0 THEN 1 ELSE 0 END) mapped_invoice_header_count
        FROM NGT.CustomerCallOrders
        WHERE LastUpdate >= CONVERT(datetime2,N'{WINDOW_START}',126)
          AND LastUpdate < CONVERT(datetime2,N'{WINDOW_END_EXCLUSIVE}',126)
        GROUP BY CONVERT(char(7),LastUpdate,120)
        ORDER BY month_bucket
        """,
    )


def _mapping_strategy_timeline(cursor: Any) -> dict[str, Any]:
    base = """
        WITH line_state AS (
          SELECT CustomerCallOrderUniqueId,
            SUM(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) active_line_count,
            SUM(CASE WHEN IsRemoved=0 AND TRY_CONVERT(bigint,NULLIF(BackOfficeOrderRef,N''))>0 THEN 1 ELSE 0 END) active_mapped_line_count
          FROM NGT.CustomerCallOrderLines
          GROUP BY CustomerCallOrderUniqueId
        ), strategy AS (
          SELECT h.Id,h.LastUpdate,
            CASE WHEN TRY_CONVERT(bigint,NULLIF(h.BackOfficeOrderId,N''))>0
                   AND ISNULL(ls.active_mapped_line_count,0)=0 THEN 'HEADER_NUMERIC_ONLY'
                 WHEN ISNULL(TRY_CONVERT(bigint,NULLIF(h.BackOfficeOrderId,N'')),0)<=0
                   AND ls.active_line_count>0
                   AND ls.active_mapped_line_count=ls.active_line_count THEN 'ALL_ACTIVE_LINES_ONLY'
                 WHEN ISNULL(TRY_CONVERT(bigint,NULLIF(h.BackOfficeOrderId,N'')),0)<=0
                   AND ls.active_mapped_line_count>0
                   AND ls.active_mapped_line_count<ls.active_line_count THEN 'PARTIAL_ACTIVE_LINES_ONLY'
                 WHEN ISNULL(ls.active_mapped_line_count,0)=0 THEN 'NO_NUMERIC_CROSSWALK'
                 ELSE 'MIXED_OR_OTHER' END mapping_strategy
          FROM NGT.CustomerCallOrders h
          LEFT JOIN line_state ls ON ls.CustomerCallOrderUniqueId=h.Id
        )
    """
    all_time = _rows(
        cursor,
        base
        + """
        SELECT mapping_strategy,COUNT_BIG(*) order_count,
               MIN(LastUpdate) minimum_last_update,
               MAX(LastUpdate) maximum_last_update
        FROM strategy
        GROUP BY mapping_strategy
        ORDER BY mapping_strategy
        """,
    )
    window = _rows(
        cursor,
        base
        + f"""
        SELECT CONVERT(char(7),LastUpdate,120) month_bucket,mapping_strategy,
               COUNT_BIG(*) order_count
        FROM strategy
        WHERE LastUpdate >= CONVERT(datetime2,N'{WINDOW_START}',126)
          AND LastUpdate < CONVERT(datetime2,N'{WINDOW_END_EXCLUSIVE}',126)
        GROUP BY CONVERT(char(7),LastUpdate,120),mapping_strategy
        ORDER BY month_bucket,mapping_strategy
        """,
    )
    return {"all_time": all_time, "window_month_buckets": window}


def _module_profiles(cursor: Any) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.name object_name,o.type_desc,sm.definition
        FROM sys.sql_modules sm
        JOIN sys.objects o ON o.object_id=sm.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE sm.definition LIKE N'%CustomerCallOrder%'
           OR (s.name=N'dbo' AND o.name=N'NGT_DoReplicateTour')
        ORDER BY s.name,o.name
        """,
    )
    result = []
    for row in rows:
        definition = row["definition"] or ""
        folded = definition.casefold()
        refs_by_fold: dict[str, str] = {}
        for match in SQL_OBJECT_REF.finditer(definition):
            value = match.group("object").replace("[", "").replace("]", "")
            refs_by_fold.setdefault(value.casefold(), value)
        refs = sorted(refs_by_fold.values(), key=str.casefold)
        result.append(
            {
                "qualified_name": _qualified(row["schema_name"], row["object_name"]),
                "type_desc": row["type_desc"],
                "definition_sha256": _sha256(definition),
                "definition_length": len(definition),
                "references_customer_call_orders": "customercallorders" in folded,
                "references_customer_call_order_lines": "customercallorderlines" in folded,
                "references_backoffice_order_fields": "backofficeorder" in folded,
                "references_backoffice_invoice_fields": "backofficeinvoice" in folded,
                "references_removed_state": "isremoved" in folded,
                "references_canceled_state": "iscanceled" in folded,
                "begin_transaction_token_count": len(
                    re.findall(r"\bbegin\s+tran(?:saction)?\b", definition, re.IGNORECASE)
                ),
                "commit_token_count": len(
                    re.findall(r"\bcommit\s+tran(?:saction)?\b", definition, re.IGNORECASE)
                ),
                "rollback_token_count": len(
                    re.findall(r"\brollback\s+tran(?:saction)?\b", definition, re.IGNORECASE)
                ),
                "throw_or_raiserror_token_count": len(
                    re.findall(r"\b(?:throw|raiserror)\b", definition, re.IGNORECASE)
                ),
                "safe_sql_object_references": refs,
            }
        )
    return result


def _replication_procedure_contract(cursor: Any) -> dict[str, Any]:
    parameters = _rows(
        cursor,
        """
        SELECT p.parameter_id,p.name parameter_name,ty.name data_type,
               p.max_length,p.precision,p.scale,p.is_output
        FROM sys.parameters p
        JOIN sys.types ty ON ty.user_type_id=p.user_type_id
        WHERE p.object_id=OBJECT_ID(N'dbo.NGT_DoReplicateTour')
        ORDER BY p.parameter_id
        """,
    )
    result = _rows(
        cursor,
        """
        SELECT column_ordinal,name column_name,system_type_name,is_nullable,error_number
        FROM sys.dm_exec_describe_first_result_set_for_object(
          OBJECT_ID(N'dbo.NGT_DoReplicateTour'),0
        )
        ORDER BY column_ordinal
        """,
    )
    return {
        "qualified_name": "dbo.NGT_DoReplicateTour",
        "parameters": [
            {
                **row,
                "is_output": bool(row["is_output"]),
            }
            for row in parameters
        ],
        "result_set_contract": result,
    }


def collect() -> dict[str, Any]:
    with _connect() as connection:
        cursor = connection.cursor()
        _assert_safe_target(cursor)
        database_state = _rows(
            cursor,
            """
            SELECT CONVERT(varchar(30),DATABASEPROPERTYEX(DB_NAME(),'Updateability')) updateability,
                   HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','UPDATE') can_update
            """,
        )[0]
        columns = _catalog_columns(cursor)
        profiles = _catalog_profiles(cursor, columns)
        indexes = _unique_indexes(cursor)
        foreign_keys = _foreign_keys(cursor)
        triggers = _triggers(cursor)
        header_state = _header_state(cursor)
        line_boundary = _line_boundary(cursor)
        quantity = _quantity_boundary(cursor)
        activity = _window_activity(cursor)
        mapping_timeline = _mapping_strategy_timeline(cursor)
        modules = _module_profiles(cursor)
        procedure = _replication_procedure_contract(cursor)

    profile_by_name = {row["qualified_name"]: row for row in profiles}
    payload = {
        "artifact": "varanegar_ngt_order_persistence_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "source": {
            "server": SERVER,
            "database": DATABASE,
            "approved_target": True,
        },
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": database_state["updateability"],
            "can_update": database_state["can_update"],
            "denies_data_writes": 1 if database_state["can_update"] == 0 else 0,
            "stored_procedure_or_application_command_executions": 0,
            "business_rows_customer_user_configuration_values_or_identifiers_persisted": 0,
            "sql_definitions_persisted": 0,
            "safe_schema_table_column_parameter_and_module_identifiers_persisted": True,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "target_table_count": len(profiles),
            "catalog_column_count": sum(row["column_count"] for row in profiles),
            "order_header_count": profile_by_name["NGT.CustomerCallOrders"][
                "anonymous_counts"
            ]["row_count"],
            "order_line_count": profile_by_name["NGT.CustomerCallOrderLines"][
                "anonymous_counts"
            ]["row_count"],
            "order_status_event_count": profile_by_name["NGT.CustomerCallOrderStatus"][
                "anonymous_counts"
            ]["row_count"],
            "unique_or_primary_index_count": len(indexes),
            "related_foreign_key_edge_count": len(foreign_keys),
            "untrusted_related_foreign_key_edge_count": sum(
                1 for row in foreign_keys if row["is_not_trusted"]
            ),
            "target_trigger_count": len(triggers),
            "state_matrix_group_count": len(header_state["state_matrix"]),
            "partially_mapped_order_count": line_boundary["parent_mapping_groups"][
                "partially_mapped_order_count"
            ],
            "split_backoffice_order_count": line_boundary["parent_mapping_groups"][
                "split_backoffice_order_count"
            ],
            "target_sql_module_count": len(modules),
            "activity_month_bucket_count": len(activity),
            "mapping_strategy_count": len(mapping_timeline["all_time"]),
        },
        "table_catalog_profiles": profiles,
        "target_unique_index_contracts": indexes,
        "related_foreign_key_contracts": foreign_keys,
        "target_trigger_contracts": triggers,
        "header_state_contract": header_state,
        "line_persistence_contract": line_boundary,
        "quantity_detail_contracts": quantity,
        "last_update_activity_window": {
            "basis": "NGT.CustomerCallOrders.LastUpdate",
            "start_inclusive": WINDOW_START,
            "end_exclusive": WINDOW_END_EXCLUSIVE,
            "month_buckets": activity,
        },
        "crosswalk_mapping_strategy_timeline": mapping_timeline,
        "target_sql_module_profiles": modules,
        "replication_procedure_contract": procedure,
        "evidence_limits": [
            "Anonymous current-state aggregates cannot reconstruct the exact chronological state transition history.",
            "CustomerCallOrderStatus is empty in this clone, so it cannot serve as an observed audit history here.",
            "LastUpdate month buckets are technical update activity, not order business dates or human approval events.",
            "SQL-definition fingerprints and token counts prove compiled text shape, not successful runtime execution.",
            "A mapped identifier or UUID proves linkage shape, not business correctness of the generated order or invoice.",
        ],
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False, default=_json_default))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
