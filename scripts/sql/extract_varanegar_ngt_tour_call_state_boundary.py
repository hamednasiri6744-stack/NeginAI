"""Extract a privacy-safe NGT tour and customer-call state boundary.

Only the approved local READ_ONLY clone is queried. The artifact contains safe
catalog identifiers, definition hashes, semantic status labels, and anonymous
aggregates. No stored procedure or application command is executed and no raw
row identifier, customer, user, location, comment, host, or configuration value
is persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
    ("NGT", "BaseValues"),
    ("NGT", "BaseTypes"),
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
UUID_LITERAL = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _catalog(cursor: Any) -> list[dict[str, Any]]:
    predicate = " OR ".join(
        f"(s.name=N'{schema}' AND t.name=N'{table}')" for schema, table in TABLES
    )
    rows = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
               ty.name data_type,c.is_nullable,c.is_identity,dc.definition
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        LEFT JOIN sys.default_constraints dc
          ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
        WHERE {predicate}
        ORDER BY s.name,t.name,c.column_id
        """,
    )
    result: list[dict[str, Any]] = []
    for schema, table in TABLES:
        selected = [
            row
            for row in rows
            if row["schema_name"] == schema and row["table_name"] == table
        ]
        result.append(
            {
                "qualified_name": f"{schema}.{table}",
                "column_count": len(selected),
                "columns": [
                    {
                        "column_name": row["column_name"],
                        "data_type": row["data_type"],
                        "is_nullable": bool(row["is_nullable"]),
                        "is_identity": bool(row["is_identity"]),
                        "has_default": row["definition"] is not None,
                        "default_definition_sha256": None
                        if row["definition"] is None
                        else _sha(row["definition"]),
                    }
                    for row in selected
                ],
            }
        )
    return result


def _keys(cursor: Any) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,i.name index_name,
               i.is_unique,i.is_primary_key,ic.key_ordinal,ic.is_included_column,
               c.name column_name
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.indexes i ON i.object_id=t.object_id AND i.index_id>0
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=t.object_id AND c.column_id=ic.column_id
        WHERE s.name=N'NGT' AND t.name IN (N'Tours',N'CustomerCalls')
          AND (i.is_unique=1 OR i.is_primary_key=1)
        ORDER BY t.name,i.index_id,ic.key_ordinal,ic.index_column_id
        """,
    )
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["table_name"], row["index_name"])
        item = grouped.setdefault(
            key,
            {
                "qualified_table": f"NGT.{row['table_name']}",
                "index_name": row["index_name"],
                "is_unique": bool(row["is_unique"]),
                "is_primary_key": bool(row["is_primary_key"]),
                "key_columns": [],
                "included_columns": [],
            },
        )
        item["included_columns" if row["is_included_column"] else "key_columns"].append(
            row["column_name"]
        )
    return list(grouped.values())


def _status_catalog(cursor: Any) -> dict[str, Any]:
    rows = _rows(
        cursor,
        """
        SELECT bt.BaseTypeName base_type_name,bv.BaseValueName base_value_name,
               CAST(bv.IsRemoved AS int) is_removed,
               COUNT(DISTINCT bv.Id) referenced_key_count,
               SUM(CASE WHEN x.reference_kind='TOUR_STATUS' THEN x.reference_count ELSE 0 END) tour_count,
               SUM(CASE WHEN x.reference_kind='CALL_STATUS' THEN x.reference_count ELSE 0 END) call_status_count,
               SUM(CASE WHEN x.reference_kind='VISIT_STATUS' THEN x.reference_count ELSE 0 END) visit_status_count
        FROM NGT.BaseValues bv
        JOIN NGT.BaseTypes bt ON bt.Id=bv.BaseTypeId
        JOIN (
          SELECT TourStatusUniqueId value_id,'TOUR_STATUS' reference_kind,COUNT_BIG(*) reference_count
          FROM NGT.Tours GROUP BY TourStatusUniqueId
          UNION ALL
          SELECT CallStatusUniqueId,'CALL_STATUS',COUNT_BIG(*)
          FROM NGT.CustomerCalls GROUP BY CallStatusUniqueId
          UNION ALL
          SELECT VisitStatusUniqueId,'VISIT_STATUS',COUNT_BIG(*)
          FROM NGT.CustomerCalls GROUP BY VisitStatusUniqueId
        ) x ON x.value_id=bv.Id
        GROUP BY bt.BaseTypeName,bv.BaseValueName,CAST(bv.IsRemoved AS int)
        ORDER BY bt.BaseTypeName,bv.BaseValueName,CAST(bv.IsRemoved AS int)
        """,
    )
    integrity = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM NGT.Tours t LEFT JOIN NGT.BaseValues bv ON bv.Id=t.TourStatusUniqueId WHERE bv.Id IS NULL) unresolved_tour_status_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCalls c LEFT JOIN NGT.BaseValues bv ON bv.Id=c.CallStatusUniqueId WHERE bv.Id IS NULL) unresolved_call_status_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCalls c LEFT JOIN NGT.BaseValues bv ON bv.Id=c.VisitStatusUniqueId WHERE bv.Id IS NULL) unresolved_visit_status_count,
          (SELECT COUNT_BIG(*) FROM NGT.Tours t JOIN NGT.BaseValues bv ON bv.Id=t.TourStatusUniqueId JOIN NGT.BaseTypes bt ON bt.Id=bv.BaseTypeId WHERE bt.BaseTypeName<>N'TourStatus') wrong_base_type_tour_status_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCalls c JOIN NGT.BaseValues bv ON bv.Id=c.CallStatusUniqueId JOIN NGT.BaseTypes bt ON bt.Id=bv.BaseTypeId WHERE bt.BaseTypeName<>N'CallStatus') wrong_base_type_call_status_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCalls c JOIN NGT.BaseValues bv ON bv.Id=c.VisitStatusUniqueId JOIN NGT.BaseTypes bt ON bt.Id=bv.BaseTypeId WHERE bt.BaseTypeName<>N'VisitStatus') wrong_base_type_visit_status_count,
          (SELECT COUNT_BIG(*) FROM NGT.Tours t JOIN NGT.BaseValues bv ON bv.Id=t.TourStatusUniqueId WHERE bv.IsRemoved=1) removed_tour_status_reference_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCalls c JOIN NGT.BaseValues bv ON bv.Id=c.CallStatusUniqueId WHERE bv.IsRemoved=1) removed_call_status_reference_count,
          (SELECT COUNT_BIG(*) FROM NGT.CustomerCalls c JOIN NGT.BaseValues bv ON bv.Id=c.VisitStatusUniqueId WHERE bv.IsRemoved=1) removed_visit_status_reference_count
        """,
    )[0]
    return {"semantic_status_rows": rows, "reference_integrity": integrity}


def _tour_state(cursor: Any) -> dict[str, Any]:
    aggregate = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) tour_count,
          SUM(CASE WHEN t.IsRemoved=0 THEN 1 ELSE 0 END) active_count,
          SUM(CASE WHEN t.IsRemoved=1 THEN 1 ELSE 0 END) removed_count,
          SUM(CASE WHEN t.StartTime IS NOT NULL THEN 1 ELSE 0 END) started_count,
          SUM(CASE WHEN t.EndTime IS NOT NULL THEN 1 ELSE 0 END) ended_count,
          SUM(CASE WHEN t.StartTime IS NOT NULL AND t.EndTime IS NOT NULL THEN 1 ELSE 0 END) started_and_ended_count,
          SUM(CASE WHEN t.StartTime IS NOT NULL AND t.EndTime IS NOT NULL AND t.EndTime<t.StartTime THEN 1 ELSE 0 END) end_before_start_count,
          SUM(CASE WHEN t.PaymentApproved=1 THEN 1 ELSE 0 END) payment_approved_count,
          SUM(CASE WHEN t.StockLevelApproved=1 THEN 1 ELSE 0 END) stock_level_approved_count,
          SUM(CASE WHEN t.PreviousStatusUniqueId IS NOT NULL THEN 1 ELSE 0 END) previous_status_present_count,
          SUM(CASE WHEN t.PreviousStatusUniqueId IS NOT NULL AND pbv.Id IS NULL THEN 1 ELSE 0 END) unresolved_previous_status_count,
          SUM(CASE WHEN t.ApplicationOwnerId<>bv.ApplicationOwnerId THEN 1 ELSE 0 END) status_application_owner_difference_count,
          SUM(CASE WHEN t.DataOwnerId<>bv.DataOwnerId THEN 1 ELSE 0 END) status_data_owner_difference_count,
          SUM(CASE WHEN t.DataOwnerCenterId<>bv.DataOwnerCenterId THEN 1 ELSE 0 END) status_center_difference_count,
          SUM(CASE WHEN t.ApplicationOwnerId<>bv.ApplicationOwnerId OR t.DataOwnerId<>bv.DataOwnerId OR t.DataOwnerCenterId<>bv.DataOwnerCenterId THEN 1 ELSE 0 END) status_lookup_scope_difference_count
        FROM NGT.Tours t
        JOIN NGT.BaseValues bv ON bv.Id=t.TourStatusUniqueId
        LEFT JOIN NGT.BaseValues pbv ON pbv.Id=t.PreviousStatusUniqueId
        """,
    )[0]
    matrix = _rows(
        cursor,
        """
        SELECT bv.BaseValueName current_status_name,
               COALESCE(pbv.BaseValueName,N'<NULL_OR_UNRESOLVED>') previous_status_name,
               COUNT_BIG(*) tour_count,
               SUM(CASE WHEN t.StartTime IS NOT NULL THEN 1 ELSE 0 END) started_count,
               SUM(CASE WHEN t.EndTime IS NOT NULL THEN 1 ELSE 0 END) ended_count,
               SUM(CASE WHEN t.PaymentApproved=1 THEN 1 ELSE 0 END) payment_approved_count,
               SUM(CASE WHEN t.StockLevelApproved=1 THEN 1 ELSE 0 END) stock_level_approved_count
        FROM NGT.Tours t
        JOIN NGT.BaseValues bv ON bv.Id=t.TourStatusUniqueId
        LEFT JOIN NGT.BaseValues pbv ON pbv.Id=t.PreviousStatusUniqueId
        GROUP BY bv.BaseValueName,COALESCE(pbv.BaseValueName,N'<NULL_OR_UNRESOLVED>')
        ORDER BY bv.BaseValueName,previous_status_name
        """,
    )
    month_status = _rows(
        cursor,
        f"""
        SELECT CONVERT(char(7),t.LastUpdate,120) month_bucket,
               bv.BaseValueName current_status_name,COUNT_BIG(*) tour_count
        FROM NGT.Tours t JOIN NGT.BaseValues bv ON bv.Id=t.TourStatusUniqueId
        WHERE t.LastUpdate>='{WINDOW_START}' AND t.LastUpdate<'{WINDOW_END_EXCLUSIVE}'
        GROUP BY CONVERT(char(7),t.LastUpdate,120),bv.BaseValueName
        ORDER BY month_bucket,current_status_name
        """,
    )
    return {
        "aggregate": aggregate,
        "current_previous_status_matrix": matrix,
        "three_month_last_update_status_buckets": month_status,
    }


def _call_state(cursor: Any) -> dict[str, Any]:
    aggregate = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) call_count,
          SUM(CASE WHEN c.IsRemoved=0 THEN 1 ELSE 0 END) active_count,
          SUM(CASE WHEN c.IsRemoved=1 THEN 1 ELSE 0 END) removed_count,
          SUM(CASE WHEN t.Id IS NULL THEN 1 ELSE 0 END) orphan_tour_count,
          SUM(CASE WHEN c.IsRemoved=0 AND t.IsRemoved=1 THEN 1 ELSE 0 END) active_call_under_removed_tour_count,
          SUM(CASE WHEN t.Id IS NOT NULL AND (c.ApplicationOwnerId<>t.ApplicationOwnerId OR c.DataOwnerId<>t.DataOwnerId OR c.DataOwnerCenterId<>t.DataOwnerCenterId) THEN 1 ELSE 0 END) tour_scope_mismatch_count,
          SUM(CASE WHEN c.CallDate IS NULL THEN 1 ELSE 0 END) null_call_date_count,
          SUM(CASE WHEN c.StartTime IS NOT NULL THEN 1 ELSE 0 END) started_count,
          SUM(CASE WHEN c.EndTime IS NOT NULL THEN 1 ELSE 0 END) ended_count,
          SUM(CASE WHEN c.StartTime IS NOT NULL AND c.EndTime IS NOT NULL AND c.EndTime<c.StartTime THEN 1 ELSE 0 END) end_before_start_count,
          SUM(CASE WHEN c.VisitDuration<0 THEN 1 ELSE 0 END) negative_visit_duration_count,
          SUM(CASE WHEN c.ManualStartTime IS NOT NULL THEN 1 ELSE 0 END) manual_started_count,
          SUM(CASE WHEN c.ManualEndTime IS NOT NULL THEN 1 ELSE 0 END) manual_ended_count,
          SUM(CASE WHEN c.ManualStartTime IS NOT NULL AND c.ManualEndTime IS NOT NULL AND c.ManualEndTime<c.ManualStartTime THEN 1 ELSE 0 END) manual_end_before_start_count,
          SUM(CASE WHEN c.ManualVisitDuration<0 THEN 1 ELSE 0 END) negative_manual_visit_duration_count,
          SUM(CASE WHEN c.NoSaleReasonUniqueId IS NOT NULL THEN 1 ELSE 0 END) no_sale_reason_present_count,
          SUM(CASE WHEN c.SendToConsoleDate IS NOT NULL THEN 1 ELSE 0 END) sent_to_console_count,
          SUM(CASE WHEN c.DistributionUniqueId IS NOT NULL THEN 1 ELSE 0 END) distribution_link_count
        FROM NGT.CustomerCalls c
        LEFT JOIN NGT.Tours t ON t.Id=c.TourUniqueId
        """,
    )[0]
    matrix = _rows(
        cursor,
        """
        WITH active_order_calls AS (
          SELECT DISTINCT CustomerCallUniqueId
          FROM NGT.CustomerCallOrders WHERE IsRemoved=0
        )
        SELECT cbt.BaseTypeName call_status_base_type,cbv.BaseValueName call_status_name,
               vbt.BaseTypeName visit_status_base_type,vbv.BaseValueName visit_status_name,
               CASE WHEN c.NoSaleReasonUniqueId IS NULL THEN 0 ELSE 1 END has_no_sale_reason,
               CASE WHEN a.CustomerCallUniqueId IS NULL THEN 0 ELSE 1 END has_active_order,
               COUNT_BIG(*) call_count
        FROM NGT.CustomerCalls c
        LEFT JOIN active_order_calls a ON a.CustomerCallUniqueId=c.Id
        JOIN NGT.BaseValues cbv ON cbv.Id=c.CallStatusUniqueId
        JOIN NGT.BaseTypes cbt ON cbt.Id=cbv.BaseTypeId
        JOIN NGT.BaseValues vbv ON vbv.Id=c.VisitStatusUniqueId
        JOIN NGT.BaseTypes vbt ON vbt.Id=vbv.BaseTypeId
        GROUP BY cbt.BaseTypeName,cbv.BaseValueName,vbt.BaseTypeName,vbv.BaseValueName,
                 CASE WHEN c.NoSaleReasonUniqueId IS NULL THEN 0 ELSE 1 END,
                 CASE WHEN a.CustomerCallUniqueId IS NULL THEN 0 ELSE 1 END
        ORDER BY call_status_name,visit_status_name,has_no_sale_reason,has_active_order
        """,
    )
    time_matrix = _rows(
        cursor,
        """
        SELECT cbv.BaseValueName call_status_name,vbv.BaseValueName visit_status_name,
               COUNT_BIG(*) call_count,
               SUM(CASE WHEN c.CallDate IS NULL THEN 1 ELSE 0 END) null_call_date_count,
               SUM(CASE WHEN c.StartTime IS NOT NULL THEN 1 ELSE 0 END) started_count,
               SUM(CASE WHEN c.EndTime IS NOT NULL THEN 1 ELSE 0 END) ended_count,
               SUM(CASE WHEN c.VisitDuration<0 THEN 1 ELSE 0 END) negative_visit_duration_count,
               SUM(CASE WHEN c.SendToConsoleDate IS NOT NULL THEN 1 ELSE 0 END) sent_to_console_count
        FROM NGT.CustomerCalls c
        JOIN NGT.BaseValues cbv ON cbv.Id=c.CallStatusUniqueId
        JOIN NGT.BaseValues vbv ON vbv.Id=c.VisitStatusUniqueId
        GROUP BY cbv.BaseValueName,vbv.BaseValueName
        ORDER BY call_status_name,visit_status_name
        """,
    )
    duplicate_pairs = _rows(
        cursor,
        """
        WITH pairs AS (
          SELECT TourUniqueId,CustomerUniqueId,COUNT_BIG(*) pair_count
          FROM NGT.CustomerCalls
          GROUP BY TourUniqueId,CustomerUniqueId
        )
        SELECT SUM(CASE WHEN pair_count>1 THEN 1 ELSE 0 END) duplicate_tour_customer_group_count,
               SUM(CASE WHEN pair_count>1 THEN pair_count ELSE 0 END) calls_in_duplicate_tour_customer_groups,
               MAX(pair_count) maximum_calls_per_tour_customer
        FROM pairs
        """,
    )[0]
    month_status = _rows(
        cursor,
        f"""
        SELECT CONVERT(char(7),c.LastUpdate,120) month_bucket,
               cbv.BaseValueName call_status_name,vbv.BaseValueName visit_status_name,
               COUNT_BIG(*) call_count
        FROM NGT.CustomerCalls c
        JOIN NGT.BaseValues cbv ON cbv.Id=c.CallStatusUniqueId
        JOIN NGT.BaseValues vbv ON vbv.Id=c.VisitStatusUniqueId
        WHERE c.LastUpdate>='{WINDOW_START}' AND c.LastUpdate<'{WINDOW_END_EXCLUSIVE}'
        GROUP BY CONVERT(char(7),c.LastUpdate,120),cbv.BaseValueName,vbv.BaseValueName
        ORDER BY month_bucket,call_status_name,visit_status_name
        """,
    )
    return {
        "aggregate": aggregate,
        "call_visit_order_state_matrix": matrix,
        "call_visit_time_state_matrix": time_matrix,
        "duplicate_tour_customer_contract": duplicate_pairs,
        "three_month_last_update_status_buckets": month_status,
    }


def _counter_candidates(cursor: Any) -> dict[str, Any]:
    aggregate = _rows(
        cursor,
        """
        WITH order_rollup AS (
          SELECT CustomerCallUniqueId,
                 MAX(CASE WHEN IsRemoved=0 THEN 1 ELSE 0 END) has_active_order,
                 MAX(CASE WHEN IsRemoved=0 AND IsInvoice=1 THEN 1 ELSE 0 END) has_active_invoice
          FROM NGT.CustomerCallOrders GROUP BY CustomerCallUniqueId
        ), call_rollup AS (
          SELECT c.TourUniqueId,
                 COUNT_BIG(*) child_call_count,
                 COUNT(DISTINCT c.CustomerUniqueId) distinct_customer_count,
                 SUM(CASE WHEN c.StartTime IS NOT NULL THEN 1 ELSE 0 END) started_call_count,
                 SUM(CASE WHEN c.EndTime IS NOT NULL THEN 1 ELSE 0 END) ended_call_count,
                 SUM(ISNULL(o.has_active_order,0)) ordered_call_count,
                 SUM(ISNULL(o.has_active_invoice,0)) invoiced_call_count
          FROM NGT.CustomerCalls c
          LEFT JOIN order_rollup o ON o.CustomerCallUniqueId=c.Id
          GROUP BY c.TourUniqueId
        )
        SELECT COUNT_BIG(*) tour_count,
          SUM(CASE WHEN cr.TourUniqueId IS NULL THEN 1 ELSE 0 END) tour_without_call_count,
          SUM(CASE WHEN t.CustomerCount=ISNULL(cr.child_call_count,0) THEN 1 ELSE 0 END) customer_count_matches_call_count,
          SUM(CASE WHEN t.CustomerCount=ISNULL(cr.distinct_customer_count,0) THEN 1 ELSE 0 END) customer_count_matches_distinct_customer_count,
          SUM(CASE WHEN t.VisitCount=ISNULL(cr.started_call_count,0) THEN 1 ELSE 0 END) visit_count_matches_started_call_count,
          SUM(CASE WHEN t.VisitCount=ISNULL(cr.ended_call_count,0) THEN 1 ELSE 0 END) visit_count_matches_ended_call_count,
          SUM(CASE WHEN t.OrderCount=ISNULL(cr.ordered_call_count,0) THEN 1 ELSE 0 END) order_count_matches_ordered_call_count,
          SUM(CASE WHEN t.InvoiceCount=ISNULL(cr.invoiced_call_count,0) THEN 1 ELSE 0 END) invoice_count_matches_invoiced_call_count,
          SUM(CASE WHEN t.CustomerCount<0 OR t.VisitCount<0 OR t.NoVisitCount<0 OR t.OrderCount<0 OR t.NoOrderCount<0 OR t.UndetermindCount<0 OR t.InvoiceCount<0 OR t.ReturnInvoiceRequestCount<0 OR t.ReturnInvoiceCount<0 THEN 1 ELSE 0 END) negative_stored_counter_tour_count
        FROM NGT.Tours t LEFT JOIN call_rollup cr ON cr.TourUniqueId=t.Id
        """,
    )[0]
    return {
        "aggregate_candidate_matches": aggregate,
        "interpretation": (
            "These are candidate equalities only. A mismatch does not prove corruption, "
            "because stored counters may use different status, removal, or business filters."
        ),
    }


def _history_candidates(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,
               CASE WHEN t.name LIKE '%History%' THEN 1 ELSE 0 END name_signals_history,
               CASE WHEN t.name LIKE '%Status%' THEN 1 ELSE 0 END name_signals_status
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        WHERE s.name=N'NGT'
          AND (t.name LIKE N'%Tour%' OR t.name LIKE N'%CustomerCall%')
          AND (t.name LIKE N'%History%' OR t.name LIKE N'%Status%')
        ORDER BY s.name,t.name
        """,
    )


def _module_profiles(cursor: Any) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.name object_name,o.type_desc,sm.definition
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules sm ON sm.object_id=o.object_id
        WHERE sm.definition LIKE N'%NGT.Tours%'
           OR sm.definition LIKE N'%NGT].[Tours%'
           OR sm.definition LIKE N'%NGT.CustomerCalls%'
           OR sm.definition LIKE N'%NGT].[CustomerCalls%'
           OR sm.definition LIKE N'%TourStatusUniqueId%'
           OR sm.definition LIKE N'%CallStatusUniqueId%'
           OR sm.definition LIKE N'%VisitStatusUniqueId%'
        ORDER BY s.name,o.name
        """,
    )
    result = []
    for row in rows:
        definition = row["definition"] or ""
        refs = sorted(
            {
                match.group("object").replace("[", "").replace("]", "")
                for match in SQL_OBJECT_REF.finditer(definition)
            }
        )
        result.append(
            {
                "qualified_name": f"{row['schema_name']}.{row['object_name']}",
                "type_desc": row["type_desc"],
                "definition_sha256": _sha(definition),
                "definition_length": len(definition),
                "safe_sql_object_references": refs,
                "uuid_literal_count": len(UUID_LITERAL.findall(definition)),
                "begin_transaction_token_count": len(
                    re.findall(r"\bBEGIN\s+TRAN(?:SACTION)?\b", definition, re.IGNORECASE)
                ),
                "commit_token_count": len(
                    re.findall(r"\bCOMMIT\s+TRAN(?:SACTION)?\b", definition, re.IGNORECASE)
                ),
                "rollback_token_count": len(
                    re.findall(r"\bROLLBACK\s+TRAN(?:SACTION)?\b", definition, re.IGNORECASE)
                ),
                "throw_or_raiserror_token_count": len(
                    re.findall(r"\b(?:THROW|RAISERROR)\b", definition, re.IGNORECASE)
                ),
            }
        )
    return result


def _triggers(cursor: Any) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,tr.name trigger_name,
               tr.is_disabled,tr.is_instead_of_trigger,sm.definition
        FROM sys.triggers tr
        JOIN sys.tables t ON t.object_id=tr.parent_id
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        LEFT JOIN sys.sql_modules sm ON sm.object_id=tr.object_id
        WHERE s.name=N'NGT' AND t.name IN (N'Tours',N'CustomerCalls')
        ORDER BY t.name,tr.name
        """,
    )
    result = []
    for row in rows:
        definition = row["definition"] or ""
        result.append(
            {
                "qualified_table": f"{row['schema_name']}.{row['table_name']}",
                "trigger_name": row["trigger_name"],
                "is_disabled": bool(row["is_disabled"]),
                "is_instead_of_trigger": bool(row["is_instead_of_trigger"]),
                "definition_sha256": _sha(definition),
                "definition_length": len(definition),
                "uuid_literal_count": len(UUID_LITERAL.findall(definition)),
                "rollback_token_count": len(re.findall(r"\bROLLBACK\b", definition, re.IGNORECASE)),
                "throw_or_raiserror_token_count": len(
                    re.findall(r"\b(?:THROW|RAISERROR)\b", definition, re.IGNORECASE)
                ),
            }
        )
    return result


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        catalog = _catalog(cursor)
        keys = _keys(cursor)
        statuses = _status_catalog(cursor)
        tours = _tour_state(cursor)
        calls = _call_state(cursor)
        counters = _counter_candidates(cursor)
        histories = _history_candidates(cursor)
        modules = _module_profiles(cursor)
        triggers = _triggers(cursor)
    finally:
        connection.close()

    summary = {
        "target_table_count": len(catalog),
        "catalog_column_count": sum(row["column_count"] for row in catalog),
        "tour_count": tours["aggregate"]["tour_count"],
        "customer_call_count": calls["aggregate"]["call_count"],
        "semantic_status_row_count": len(statuses["semantic_status_rows"]),
        "tour_status_matrix_row_count": len(tours["current_previous_status_matrix"]),
        "call_visit_order_matrix_row_count": len(calls["call_visit_order_state_matrix"]),
        "unique_or_primary_index_count": len(keys),
        "history_or_status_named_table_count": len(histories),
        "target_trigger_count": len(triggers),
        "target_sql_module_count": len(modules),
        "tour_month_status_bucket_count": len(tours["three_month_last_update_status_buckets"]),
        "call_month_status_bucket_count": len(calls["three_month_last_update_status_buckets"]),
    }
    return {
        "artifact": "varanegar_ngt_tour_call_state_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "source": {
            "server": SERVER,
            "database": DATABASE,
            "window_start": WINDOW_START,
            "window_end_exclusive": WINDOW_END_EXCLUSIVE,
        },
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_AND_ANONYMOUS_STATE_AGGREGATES",
            "database_updateability": safety["updateability"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "business_rows_customer_user_location_comment_configuration_values_or_identifiers_persisted": 0,
            "sql_definitions_persisted": 0,
            "safe_schema_table_column_status_label_and_module_identifiers_persisted": True,
            "source_or_target_state_changed": 0,
        },
        "summary": summary,
        "table_catalog_profiles": catalog,
        "target_unique_index_contracts": keys,
        "semantic_status_contract": statuses,
        "tour_state_contract": tours,
        "customer_call_state_contract": calls,
        "tour_counter_candidate_contract": counters,
        "history_or_status_named_table_candidates": histories,
        "target_trigger_contracts": triggers,
        "target_sql_module_profiles": modules,
        "evidence_limits": [
            "Current aggregate state is not a transition log and cannot prove the historical path of one row.",
            "BaseValueName and BaseTypeName are semantic catalog labels; raw BaseValue identifiers are not persisted.",
            "Stored tour counters are compared only with plausible child aggregates and require owner confirmation before interpretation.",
            "A status BaseType mismatch proves taxonomy drift in current references, not an end-user incident by itself.",
            "SQL definitions are hashed and token-counted but never persisted or executed.",
        ],
    }


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
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
