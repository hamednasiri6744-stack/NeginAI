"""Correlate NGT missing order targets to retained generic delete logs read-only."""

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
from extract_varanegar_ngt_order_target_deletion_boundary import _executable_text


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _deletes_main_log(definition: str) -> bool:
    folded = " ".join(definition.casefold().split())
    target = r"\[?gnr\]?\s*\.\s*\[?tbllog\]?(?![\w])"
    return any(
        re.search(pattern, folded) is not None
        for pattern in (
            rf"\bdelete\s+from\s+{target}",
            rf"\bdelete\s+{target}",
            rf"\bdelete\s+\[?\w+\]?\s+from\s+{target}",
            rf"\btruncate\s+table\s+{target}",
        )
    )


def _module_definition(cursor: Any, qualified_name: str) -> str:
    return _rows(
        cursor,
        "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(%s)",
        (qualified_name,),
    )[0]["definition"] or ""


def _trigger_contract(cursor: Any) -> dict[str, Any]:
    definition = _module_definition(cursor, "SLE.trg_VN_Replication_tblorderhdr_DELETE")
    compact = "".join(definition.casefold().split())
    return {
        "definition_sha256": _sha(definition),
        "definition_character_count": len(definition),
        "reads_deleted_id": "selectidfromdeleted" in compact,
        "operation_type_delete_literal": "@operationtypevarchar(20)=<literal>" in compact
        or "@operationtypevarchar(20)='delete'" in compact,
        "operation_table_target_literal": "@operationtablevarchar(100)='sle.tblorderhdr'"
        in compact,
        "operation_id_from_deleted_record": "set@operationid=@recordid" in compact,
        "canonical_delete_script_signal": "delete sle.tblorderhdr" in definition.casefold()
        and "where" in definition.casefold()
        and "id=" in definition.casefold(),
        "calls_insert_to_log": "inserttolog" in compact,
        "definition_persisted": False,
    }


def _retention_contract(cursor: Any) -> list[dict[str, Any]]:
    names = ("USP_VSA_SortTblLog", "usp_Replication_ClearReplicationReceive")
    placeholders = ",".join("%s" for _ in names)
    rows = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition
        FROM sys.sql_modules m
        JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE o.name IN ({placeholders}) ORDER BY s.name,o.name
        """,
        names,
    )
    result = []
    for row in rows:
        definition = row.pop("definition") or ""
        compact = "".join(definition.casefold().split())
        result.append(
            {
                **row,
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "deletes_main_log_signal": _deletes_main_log(definition),
                "uses_last_exec_watermark_signal": "lastexeclog" in compact,
                "uses_date_cutoff_signal": any(
                    token in compact for token in ("dateadd(", "datediff(", "getdate(")
                ),
                "definition_persisted": False,
            }
        )
    return result


def _delete_targets_in_order(definition: str) -> list[tuple[int, str]]:
    code = _executable_text(definition).casefold()
    qualified = r"(?:\[?\w+\]?\s*\.\s*)?\[?\w+\]?"
    pattern = re.compile(
        rf"(?is)\bdelete\s+(?:"
        rf"from\s+(?P<from_target>{qualified})"
        rf"|\[?\w+\]?\s+from\s+(?P<alias_target>{qualified})"
        rf"|(?P<direct_target>{qualified})\s+(?=where\b)"
        rf")"
    )
    result = []
    for match in pattern.finditer(code):
        raw = next(value for value in match.groupdict().values() if value is not None)
        normalized = re.sub(r"[\[\]\s]", "", raw).split(".")[-1]
        result.append((match.start(), normalized))
    return result


def _static_delete_sequences(cursor: Any) -> list[dict[str, Any]]:
    names = (
        "NGT_RollBackTour",
        "usp_sdsnet_Order_Delete",
        "USP_sdsnet_UndoUserExtraInfo",
        "usp_sdsnet_ConfirmFreeInvoice",
    )
    placeholders = ",".join("%s" for _ in names)
    rows = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,o.name object_name,m.definition
        FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE o.name IN ({placeholders}) ORDER BY s.name,o.name
        """,
        names,
    )
    result = []
    for row in rows:
        definition = row.pop("definition") or ""
        targets = _delete_targets_in_order(definition)
        aliases = {
            "sale_header": "tblsalehdr",
            "order_item": "tblorderitm",
            "visit_order": "visit_boorder",
            "order_header": "tblorderhdr",
            "tour_history": "tourhistory",
        }
        positions = {
            label: next((position for position, target in targets if target == table), None)
            for label, table in aliases.items()
        }
        present = sorted(
            ((position, name) for name, position in positions.items() if position is not None)
        )
        result.append(
            {
                **row,
                "definition_sha256": _sha(definition),
                "delete_target_sequence": [name for _, name in present],
                "item_before_visit_before_header": all(
                    positions[name] is not None
                    for name in ("order_item", "visit_order", "order_header")
                )
                and positions["order_item"] < positions["visit_order"] < positions["order_header"],
                "visit_before_item_before_header": all(
                    positions[name] is not None
                    for name in ("order_item", "visit_order", "order_header")
                )
                and positions["visit_order"] < positions["order_item"] < positions["order_header"],
                "sale_delete_precedes_order_item": positions["sale_header"] is not None
                and positions["order_item"] is not None
                and positions["sale_header"] < positions["order_item"],
                "tour_history_delete_follows_order_header": positions["tour_history"] is not None
                and positions["order_header"] is not None
                and positions["tour_history"] > positions["order_header"],
                "definition_or_character_offsets_persisted": False,
            }
        )
    return result


def _log_schema(cursor: Any) -> dict[str, Any]:
    columns = _rows(
        cursor,
        """
        SELECT c.name column_name,t.name type_name,c.is_nullable
        FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id
        WHERE c.object_id=OBJECT_ID(N'GNR.tblLog') ORDER BY c.column_id
        """,
    )
    indexes = _rows(
        cursor,
        """
        SELECT i.name index_name,i.is_unique,c.name column_name,ic.key_ordinal
        FROM sys.indexes i
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID(N'GNR.tblLog') AND i.index_id>0
        ORDER BY i.index_id,ic.key_ordinal
        """,
    )
    names = {row["column_name"] for row in columns}
    return {
        "column_count": len(columns),
        "has_operation_type": "OperationType" in names,
        "has_operation_table": "OperationTable" in names,
        "has_operation_id": "OperationId" in names,
        "has_transaction_date": "TransDate" in names,
        "has_app_name": "AppName" in names,
        "has_user_name": "UserName" in names,
        "has_host_name": "HostName" in names,
        "has_session_id": "SPID" in names,
        "operation_table_id_index_present": any(
            row["column_name"] == "OperationTable" for row in indexes
        ) and any(row["column_name"] == "OperationId" for row in indexes),
        "column_names_or_index_definitions_persisted": False,
    }


def _retained_delete_summary(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) retained_delete_log_count,
          COUNT(DISTINCT OperationId) distinct_delete_target_count,
          MIN(TransDate) first_retained_delete,MAX(TransDate) last_retained_delete,
          SUM(CASE WHEN Script LIKE 'DELETE SLE.tblorderhdr WHERE ID=%' THEN 1 ELSE 0 END)
            canonical_delete_script_count,
          COUNT(DISTINCT Direction) distinct_direction_count
        FROM GNR.tblLog WITH(INDEX(IX_Nc_tbllog_operationTable))
        WHERE OperationTable='SLE.tblorderhdr' AND OperationType='DELETE'
        """,
    )[0]


MISSING_CTE = """
missing AS (
  SELECT t.BackOfficeRef,MIN(t.CreatedDate) first_history,
         MAX(t.CreatedDate) last_history,COUNT_BIG(*) line_history_count,
         COUNT(DISTINCT l.CustomerCallOrderUniqueId) parent_count
  FROM dbo.TourHistory t
  JOIN NGT.CustomerCallOrderLines l ON l.Id=t.EntityUniqueId
  LEFT JOIN SLE.tblOrderHdr o
    ON o.ID=t.BackOfficeRef AND o.UniqueId=t.BackOfficeUniqueId
  WHERE t.Type=1 AND o.ID IS NULL
  GROUP BY t.BackOfficeRef
),
deletes AS (
  SELECT OperationId,MIN(TransDate) first_delete,MAX(TransDate) last_delete,
         COUNT_BIG(*) delete_log_count
  FROM GNR.tblLog WITH(INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
  WHERE OperationTable='SLE.tblorderhdr' AND OperationType='DELETE'
  GROUP BY OperationId
)
"""


def _missing_match(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        f"""
        WITH {MISSING_CTE}
        SELECT COUNT_BIG(*) missing_target_count,
          SUM(line_history_count) missing_history_line_count,
          SUM(CASE WHEN deletes.OperationId IS NOT NULL THEN 1 ELSE 0 END)
            missing_with_delete_log_count,
          SUM(CASE WHEN deletes.OperationId IS NULL THEN 1 ELSE 0 END)
            missing_without_delete_log_count,
          SUM(ISNULL(deletes.delete_log_count,0)) matching_delete_log_count,
          MIN(deletes.first_delete) first_matching_delete,
          MAX(deletes.last_delete) last_matching_delete,
          SUM(CASE WHEN deletes.last_delete>='20260601' AND deletes.last_delete<'20260901'
                   THEN 1 ELSE 0 END) recent_missing_target_delete_count
        FROM missing LEFT JOIN deletes ON deletes.OperationId=missing.BackOfficeRef
        """,
    )[0]


def _chronology(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        f"""
        WITH {MISSING_CTE}
        SELECT COUNT_BIG(*) target_count,
          SUM(CASE WHEN deletes.first_delete>=missing.last_history THEN 1 ELSE 0 END)
            delete_at_or_after_last_history_count,
          SUM(CASE WHEN deletes.first_delete<missing.first_history THEN 1 ELSE 0 END)
            delete_before_first_history_count,
          SUM(CASE WHEN deletes.first_delete>=missing.first_history
                    AND deletes.first_delete<missing.last_history THEN 1 ELSE 0 END)
            delete_between_history_count,
          SUM(CASE WHEN DATEDIFF(DAY,missing.last_history,deletes.first_delete)=0 THEN 1 ELSE 0 END)
            same_day_count,
          SUM(CASE WHEN DATEDIFF(DAY,missing.last_history,deletes.first_delete) BETWEEN 1 AND 7
                   THEN 1 ELSE 0 END) lag_1_7_day_count,
          SUM(CASE WHEN DATEDIFF(DAY,missing.last_history,deletes.first_delete) BETWEEN 8 AND 30
                   THEN 1 ELSE 0 END) lag_8_30_day_count,
          SUM(CASE WHEN DATEDIFF(DAY,missing.last_history,deletes.first_delete)>30 THEN 1 ELSE 0 END)
            lag_over_30_day_count,
          MIN(DATEDIFF(MINUTE,missing.last_history,deletes.first_delete)) min_lag_minutes,
          MAX(DATEDIFF(MINUTE,missing.last_history,deletes.first_delete)) max_lag_minutes
        FROM missing JOIN deletes ON deletes.OperationId=missing.BackOfficeRef
        """,
    )[0]


def _monthly(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        f"""
        WITH {MISSING_CTE}
        SELECT CONVERT(char(7),deletes.first_delete,120) month_bucket,
               COUNT_BIG(*) matched_delete_count
        FROM missing JOIN deletes ON deletes.OperationId=missing.BackOfficeRef
        GROUP BY CONVERT(char(7),deletes.first_delete,120)
        ORDER BY month_bucket
        """,
    )


def _retained_delete_partition(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH d AS (
          SELECT DISTINCT OperationId
          FROM GNR.tblLog WITH(INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='SLE.tblorderhdr' AND OperationType='DELETE'
        ), m AS (
          SELECT DISTINCT t.BackOfficeRef
          FROM dbo.TourHistory t
          LEFT JOIN SLE.tblOrderHdr o
            ON o.ID=t.BackOfficeRef AND o.UniqueId=t.BackOfficeUniqueId
          WHERE t.Type=1 AND o.ID IS NULL
        )
        SELECT COUNT_BIG(*) retained_delete_id_count,
          SUM(CASE WHEN o.ID IS NOT NULL THEN 1 ELSE 0 END) id_currently_present_count,
          SUM(CASE WHEN m.BackOfficeRef IS NOT NULL THEN 1 ELSE 0 END)
            missing_type1_target_count,
          SUM(CASE WHEN o.ID IS NULL AND m.BackOfficeRef IS NULL THEN 1 ELSE 0 END)
            other_currently_absent_count
        FROM d LEFT JOIN SLE.tblOrderHdr o ON o.ID=d.OperationId
        LEFT JOIN m ON m.BackOfficeRef=d.OperationId
        """,
    )[0]


def _anonymous_origin(cursor: Any) -> dict[str, Any]:
    base = """
      WITH missing AS (
        SELECT DISTINCT t.BackOfficeRef
        FROM dbo.TourHistory t
        LEFT JOIN SLE.tblOrderHdr o
          ON o.ID=t.BackOfficeRef AND o.UniqueId=t.BackOfficeUniqueId
        WHERE t.Type=1 AND o.ID IS NULL
      ), x AS (
        SELECT l.AppName,l.UserName,l.HostName,l.SPID
        FROM GNR.tblLog l WITH(INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
        JOIN missing m ON m.BackOfficeRef=l.OperationId
        WHERE l.OperationTable='SLE.tblorderhdr' AND l.OperationType='DELETE'
      )
    """
    cardinality = _rows(
        cursor,
        base
        + """
        SELECT COUNT_BIG(*) row_count,COUNT(DISTINCT AppName) distinct_app_count,
          COUNT(DISTINCT UserName) distinct_user_count,
          COUNT(DISTINCT HostName) distinct_host_count,
          COUNT(DISTINCT SPID) distinct_session_count,
          SUM(CASE WHEN AppName IS NULL THEN 1 ELSE 0 END) null_app_count,
          SUM(CASE WHEN UserName IS NULL THEN 1 ELSE 0 END) null_user_count
        FROM x
        """,
    )[0]
    concentration = _rows(
        cursor,
        base
        + """,
        a AS (SELECT AppName,COUNT_BIG(*) n FROM x GROUP BY AppName),
        h AS (SELECT HostName,COUNT_BIG(*) n FROM x GROUP BY HostName),
        p AS (SELECT AppName,HostName,COUNT_BIG(*) n FROM x GROUP BY AppName,HostName)
        SELECT (SELECT MAX(n) FROM a) max_rows_single_app,
          (SELECT MAX(n) FROM h) max_rows_single_host,
          (SELECT MAX(n) FROM p) max_rows_single_app_host_pair,
          (SELECT COUNT_BIG(*) FROM p) distinct_app_host_pair_count
        """,
    )[0]
    return cardinality | concentration


def _pathway_fingerprint(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH missing AS (
          SELECT DISTINCT t.BackOfficeRef
          FROM dbo.TourHistory t
          LEFT JOIN SLE.tblOrderHdr o
            ON o.ID=t.BackOfficeRef AND o.UniqueId=t.BackOfficeUniqueId
          WHERE t.Type=1 AND o.ID IS NULL
        ), d AS (
          SELECT l.ID,l.SPID,l.TransDate
          FROM GNR.tblLog l WITH(INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          JOIN missing m ON m.BackOfficeRef=l.OperationId
          WHERE l.OperationTable='SLE.tblorderhdr' AND l.OperationType='DELETE'
        ), f AS (
          SELECT d.ID,
            MAX(CASE WHEN n.OperationTable='dbo.visit_BOOrder' AND n.OperationType='DELETE'
                     THEN n.ID END) last_visit_id,
            MAX(CASE WHEN n.OperationTable='SLE.tblOrderItm' AND n.OperationType='DELETE'
                     THEN n.ID END) last_item_id,
            MAX(CASE WHEN n.OperationTable='SLE.tblSaleHdr' AND n.OperationType='DELETE'
                     THEN 1 ELSE 0 END) has_sale_header_delete
          FROM d LEFT JOIN GNR.tblLog n WITH(INDEX(PK_tblLog))
            ON n.ID BETWEEN d.ID-1000 AND d.ID-1 AND n.SPID=d.SPID
            AND n.TransDate BETWEEN DATEADD(SECOND,-30,d.TransDate) AND d.TransDate
          GROUP BY d.ID
        )
        SELECT COUNT_BIG(*) target_count,
          SUM(CASE WHEN last_item_id IS NOT NULL AND last_visit_id IS NOT NULL
                    AND last_item_id<last_visit_id AND last_visit_id<ID THEN 1 ELSE 0 END)
            item_before_visit_before_header_count,
          SUM(CASE WHEN last_item_id IS NOT NULL AND last_visit_id IS NOT NULL
                    AND last_visit_id<last_item_id AND last_item_id<ID THEN 1 ELSE 0 END)
            visit_before_item_before_header_count,
          SUM(CASE WHEN last_item_id IS NULL THEN 1 ELSE 0 END) no_item_signal_count,
          SUM(CASE WHEN last_visit_id IS NULL THEN 1 ELSE 0 END) no_visit_signal_count,
          SUM(CASE WHEN last_visit_id=ID-1 THEN 1 ELSE 0 END)
            immediately_preceding_visit_count,
          SUM(CASE WHEN last_visit_id<ID-1 THEN 1 ELSE 0 END)
            non_adjacent_preceding_visit_count,
          SUM(has_sale_header_delete) preceding_sale_header_delete_signal_count
        FROM f
        """,
    )[0]


def _order_type_partition(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH targets AS (
          SELECT DISTINCT t.BackOfficeRef,l.CustomerCallOrderUniqueId
          FROM dbo.TourHistory t JOIN NGT.CustomerCallOrderLines l ON l.Id=t.EntityUniqueId
          LEFT JOIN SLE.tblOrderHdr o
            ON o.ID=t.BackOfficeRef AND o.UniqueId=t.BackOfficeUniqueId
          WHERE t.Type=1 AND o.ID IS NULL
        )
        SELECT COUNT_BIG(*) target_count,
          COUNT(DISTINCT CustomerCallOrderUniqueId) parent_count,
          SUM(CASE WHEN ot.IsFreeInvoice=1 THEN 1 ELSE 0 END) free_invoice_true_target_count,
          COUNT(DISTINCT CASE WHEN ot.IsFreeInvoice=1 THEN CustomerCallOrderUniqueId END)
            free_invoice_true_parent_count,
          SUM(CASE WHEN ot.IsFreeInvoice=0 THEN 1 ELSE 0 END) free_invoice_false_target_count,
          SUM(CASE WHEN ot.IsFreeInvoice IS NULL THEN 1 ELSE 0 END)
            free_invoice_null_target_count
        FROM targets x JOIN NGT.CustomerCallOrders n ON n.Id=x.CustomerCallOrderUniqueId
        LEFT JOIN SLE.tblOrderType ot ON ot.UniqueId=n.OrderTypeUniqueId
        """,
    )[0]


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        trigger = _trigger_contract(cursor)
        retention = _retention_contract(cursor)
        static_sequences = _static_delete_sequences(cursor)
        log_schema = _log_schema(cursor)
        retained = _retained_delete_summary(cursor)
        match = _missing_match(cursor)
        chronology = _chronology(cursor)
        monthly = _monthly(cursor)
        partition = _retained_delete_partition(cursor)
        origin = _anonymous_origin(cursor)
        pathway = _pathway_fingerprint(cursor)
        order_types = _order_type_partition(cursor)
    finally:
        connection.close()
    return {
        "artifact": "varanegar_ngt_order_delete_log_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": safety["updateability"],
            "can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_trigger_or_application_command_executions": 0,
            "business_rows_or_identifiers_persisted": 0,
            "sql_definitions_persisted": 0,
            "app_user_host_or_session_values_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "retained_order_delete_log_count": int(retained["retained_delete_log_count"]),
            "missing_target_count": int(match["missing_target_count"]),
            "missing_target_with_exact_delete_log_count": int(
                match["missing_with_delete_log_count"]
            ),
            "missing_target_without_delete_log_count": int(
                match["missing_without_delete_log_count"]
            ),
            "delete_after_last_history_count": int(
                chronology["delete_at_or_after_last_history_count"]
            ),
            "recent_three_month_matched_delete_target_count": int(
                match["recent_missing_target_delete_count"]
            ),
        },
        "delete_trigger_contract": trigger,
        "log_schema_contract": log_schema,
        "log_retention_profiles": retention,
        "static_delete_sequence_contracts": static_sequences,
        "retained_delete_log_contract": retained,
        "missing_target_delete_match_contract": match,
        "history_delete_chronology_contract": chronology,
        "monthly_matched_delete_counts": monthly,
        "retained_delete_partition": partition,
        "anonymous_origin_cardinality_and_concentration": origin,
        "delete_pathway_fingerprint": pathway,
        "missing_target_order_type_partition": order_types,
        "evidence_limits": [
            "Exact OperationId matches and chronology prove target deletion after history creation, not the calling procedure or business reason.",
            "The logged item-visit-header tail excludes the normal successful NGT rollback sequence but is shared by more than one SQL deletion procedure.",
            "App, user, host and session values are reduced to anonymous cardinality and concentration counts.",
            "The two inspected replication-maintenance procedures do not delete the main log; completeness before the first retained date is still not established.",
            "No procedure, trigger, endpoint or generated script was executed and no raw log row or identifier is persisted.",
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
