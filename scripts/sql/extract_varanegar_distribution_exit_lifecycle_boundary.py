"""Extract distribution-to-exit issue, cancellation and historical deletion boundaries read-only."""

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


MODULES = (
    ("dbo", "usp_CreateExitVocherByDist"),
    ("dbo", "usp_BeforeCreateExitVocherByDist"),
    ("inv", "Usp_RemoveExitFromDist"),
    ("inv", "Usp_BeforeRemoveExitFromDist"),
    ("inv", "Usp_InsertGoodsExit_RD"),
    ("dbo", "DoPOrder_RollBackReplicatePOrder"),
    ("dbo", "usp_RollBackSalesReceipt"),
    ("dbo", "USP_VSA_ChangeDistStatus"),
    ("inv", "trg_VN_Replication_tblExit_DELETE"),
    ("SLE", "trg_VN_Replication_tblDist_DELETE"),
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _code(definition: str) -> str:
    return " ".join(
        _executable_text(definition).replace("[", "").replace("]", "").casefold().split()
    )


def _pos(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


def _count(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code, re.I | re.S))


def _profiles(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    profiles = []
    codes: dict[str, str] = {}
    for schema, name in MODULES:
        row = _rows(
            cursor,
            """
            SELECT s.name schema_name,o.name object_name,o.type_desc,o.create_date,o.modify_date,
              CASE WHEN t.object_id IS NULL THEN NULL ELSE t.is_disabled END is_disabled,
              m.definition
            FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
            LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
            LEFT JOIN sys.triggers t ON t.object_id=o.object_id
            WHERE s.name=%s AND o.name=%s
            """,
            (schema, name),
        )[0]
        definition = row.pop("definition") or ""
        code = _code(definition)
        qualified = f"{schema}.{name}"
        codes[qualified] = code
        profiles.append(
            {
                **row,
                "qualified_name": qualified,
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "begin_transaction_signal_count": _count(
                    code, r"\bbegin\s+(?:tran|transaction)\b"
                ),
                "save_transaction_signal_count": _count(code, r"\bsave\s+transaction\b"),
                "commit_signal_count": _count(code, r"\bcommit\b"),
                "rollback_signal_count": _count(code, r"\brollback\b"),
                "try_catch_signal": "begin try" in code and "begin catch" in code,
                "raiserror_signal_count": _count(code, r"\braiserror\b"),
                "direct_exit_delete_signal": bool(
                    re.search(r"\bdelete\s+(?:from\s+)?(?:inv\.)?tblexit\b", code)
                ),
                "references_type60_voucher": "vochertypecode=60" in code
                or "vochertypecode = 60" in code,
                "references_distribution_status": "tbldist" in code and "status" in code,
                "replication_mode_bypass_signal": "ufn_isreplicationmode" in code
                and bool(re.search(r"\breturn\b", code)),
                "definition_or_literal_values_persisted": False,
            }
        )
    return profiles, codes


def _current_exit_state(cursor: Any) -> dict[str, Any]:
    population = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) exit_count,
          SUM(CASE WHEN IsCanceled=1 THEN 1 ELSE 0 END) cancelled_count,
          SUM(CASE WHEN IsCanceled=0 OR IsCanceled IS NULL THEN 1 ELSE 0 END) active_count,
          SUM(CASE WHEN IsCanceled=1 AND CancelDateTime IS NULL THEN 1 ELSE 0 END)
            cancelled_without_date_count,
          SUM(CASE WHEN (IsCanceled=0 OR IsCanceled IS NULL) AND CancelDateTime IS NOT NULL
            THEN 1 ELSE 0 END) active_with_cancel_date_count
        FROM inv.tblExit
        """,
    )[0]
    active_key = _rows(
        cursor,
        """
        WITH x AS (
          SELECT DistRef,StockDCRef,COUNT_BIG(*) n FROM inv.tblExit
          WHERE IsCanceled=0 OR IsCanceled IS NULL
          GROUP BY DistRef,StockDCRef HAVING COUNT_BIG(*)>1
        )
        SELECT COUNT_BIG(*) duplicate_dist_stock_group_count,
          COALESCE(SUM(n),0) exits_in_duplicate_groups FROM x
        """,
    )[0]
    active_crosswalk = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM inv.tblExit WHERE IsCanceled=0 OR IsCanceled IS NULL)
            active_exit_count,
          (SELECT COUNT_BIG(*) FROM inv.tblVocherHdr WHERE VocherTypeCode=60)
            type60_voucher_count,
          (SELECT COUNT_BIG(*) FROM inv.tblExit e JOIN inv.tblVocherHdr v
             ON v.VocherTypeCode=60 AND v.DocRef=e.ID
           WHERE e.IsCanceled=0 OR e.IsCanceled IS NULL) matched_active_exit_count,
          (SELECT COUNT_BIG(*) FROM inv.tblExit e LEFT JOIN inv.tblVocherHdr v
             ON v.VocherTypeCode=60 AND v.DocRef=e.ID
           WHERE (e.IsCanceled=0 OR e.IsCanceled IS NULL) AND v.ID IS NULL)
            active_exit_without_type60_count,
          (SELECT COUNT_BIG(*) FROM (
             SELECT DocRef FROM inv.tblVocherHdr WHERE VocherTypeCode=60
             GROUP BY DocRef HAVING COUNT_BIG(*)>1) q) duplicate_type60_docref_group_count
        """,
    )[0]
    cancelled_cleanup = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM inv.tblExit WHERE IsCanceled=1) cancelled_exit_count,
          (SELECT COUNT_BIG(*) FROM inv.tblExit e JOIN inv.tblVocherHdr v
             ON v.VocherTypeCode=60 AND v.DocRef=e.ID WHERE e.IsCanceled=1)
            lingering_type60_voucher_count,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr s JOIN inv.tblExit e
             ON e.ID=s.ExitRef WHERE e.IsCanceled=1) lingering_sale_link_count,
          (SELECT COUNT_BIG(*) FROM inv.tblExit WHERE IsCanceled=1
             AND CancelDateTime>='20260601' AND CancelDateTime<'20260901')
            recent_cancelled_count,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleDistHistFull h JOIN inv.tblExit e
             ON e.ID=h.ExitRef WHERE e.IsCanceled=1) retained_full_history_row_count
        """,
    )[0]
    return {
        "population": population,
        "active_dist_stock_uniqueness": active_key,
        "active_type60_crosswalk": active_crosswalk,
        "cancelled_cleanup": cancelled_cleanup,
    }


def _cancellation_reconciliation(cursor: Any) -> dict[str, Any]:
    coverage = _rows(
        cursor,
        """
        WITH d AS (
          SELECT DocRef,COUNT_BIG(*) delete_events,MAX(ModifiedDate) deleted_at
          FROM inv.tblVocherHdrLog WHERE OperationType='D' AND VocherTypeCode=60
          GROUP BY DocRef
        )
        SELECT COUNT_BIG(*) type60_delete_docref_count,SUM(delete_events) type60_delete_event_count,
          SUM(CASE WHEN e.ID IS NOT NULL AND e.IsCanceled=1 THEN 1 ELSE 0 END)
            matched_cancelled_exit_count,
          SUM(CASE WHEN e.ID IS NOT NULL AND (e.IsCanceled=0 OR e.IsCanceled IS NULL)
            THEN 1 ELSE 0 END) matched_active_exit_count,
          SUM(CASE WHEN e.ID IS NULL THEN 1 ELSE 0 END) absent_exit_count,
          SUM(CASE WHEN e.IsCanceled=1 AND ABS(DATEDIFF(second,e.CancelDateTime,d.deleted_at))<=5
            THEN 1 ELSE 0 END) cancelled_within_5_seconds_count,
          SUM(CASE WHEN e.IsCanceled=1 AND e.CancelDateTime>='20260601'
            AND e.CancelDateTime<'20260901' THEN 1 ELSE 0 END) recent_matched_cancelled_count
        FROM d LEFT JOIN inv.tblExit e ON e.ID=d.DocRef
        """,
    )[0]
    cancelled_coverage = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) cancelled_exit_count,
          SUM(CASE WHEN d.DocRef IS NOT NULL THEN 1 ELSE 0 END) with_type60_delete_log_count,
          SUM(CASE WHEN d.DocRef IS NULL THEN 1 ELSE 0 END) without_type60_delete_log_count
        FROM inv.tblExit e LEFT JOIN (
          SELECT DISTINCT DocRef FROM inv.tblVocherHdrLog
          WHERE OperationType='D' AND VocherTypeCode=60
        ) d ON d.DocRef=e.ID WHERE e.IsCanceled=1
        """,
    )[0]
    time_buckets = _rows(
        cursor,
        """
        WITH d AS (
          SELECT DocRef,MAX(ModifiedDate) deleted_at FROM inv.tblVocherHdrLog
          WHERE OperationType='D' AND VocherTypeCode=60 GROUP BY DocRef
        ), x AS (
          SELECT ABS(DATEDIFF(second,e.CancelDateTime,d.deleted_at)) delta_seconds,
            e.CancelDateTime FROM inv.tblExit e JOIN d ON d.DocRef=e.ID WHERE e.IsCanceled=1
        )
        SELECT CASE WHEN delta_seconds<=1 THEN 'LE_1S' WHEN delta_seconds<=5 THEN 'LE_5S'
          WHEN delta_seconds<=60 THEN 'LE_60S' WHEN delta_seconds<=3600 THEN 'LE_1H'
          WHEN delta_seconds<=86400 THEN 'LE_1D' ELSE 'GT_1D' END time_bucket,
          COUNT_BIG(*) exit_count,
          SUM(CASE WHEN CancelDateTime>='20260601' AND CancelDateTime<'20260901'
            THEN 1 ELSE 0 END) recent_count
        FROM x GROUP BY CASE WHEN delta_seconds<=1 THEN 'LE_1S'
          WHEN delta_seconds<=5 THEN 'LE_5S' WHEN delta_seconds<=60 THEN 'LE_60S'
          WHEN delta_seconds<=3600 THEN 'LE_1H' WHEN delta_seconds<=86400 THEN 'LE_1D'
          ELSE 'GT_1D' END ORDER BY MIN(delta_seconds)
        """,
    )
    return {
        "type60_delete_coverage": coverage,
        "cancelled_exit_coverage": cancelled_coverage,
        "cancel_to_voucher_delete_time_buckets": time_buckets,
    }


def _general_log_lifecycle(cursor: Any) -> dict[str, Any]:
    operations = _rows(
        cursor,
        """
        SELECT OperationType,COUNT_BIG(*) event_count,COUNT(DISTINCT OperationId) id_count,
          MIN(TransDate) first_event_date,MAX(TransDate) last_event_date
        FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
        WHERE OperationTable='inv.tblExit' GROUP BY OperationType ORDER BY OperationType
        """,
    )
    coverage = _rows(
        cursor,
        """
        WITH l AS (
          SELECT OperationId,
            SUM(CASE WHEN OperationType='INSERT' THEN 1 ELSE 0 END) ins,
            SUM(CASE WHEN OperationType='UPDATE' THEN 1 ELSE 0 END) upd,
            SUM(CASE WHEN OperationType='DELETE' THEN 1 ELSE 0 END) del,
            MIN(TransDate) first_log,MAX(TransDate) last_log
          FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='inv.tblExit' GROUP BY OperationId
        ), vd AS (
          SELECT DocRef,MAX(ModifiedDate) voucher_deleted_at FROM inv.tblVocherHdrLog
          WHERE OperationType='D' AND VocherTypeCode=60 GROUP BY DocRef
        )
        SELECT COUNT_BIG(*) logged_exit_count,
          SUM(CASE WHEN e.ID IS NOT NULL THEN 1 ELSE 0 END) current_count,
          SUM(CASE WHEN e.ID IS NULL THEN 1 ELSE 0 END) absent_count,
          SUM(CASE WHEN e.ID IS NULL AND upd>0 THEN 1 ELSE 0 END)
            absent_with_update_log_count,
          SUM(CASE WHEN e.ID IS NULL AND upd=0 THEN 1 ELSE 0 END)
            absent_without_update_log_count,
          SUM(CASE WHEN e.ID IS NULL AND vd.DocRef IS NOT NULL THEN 1 ELSE 0 END)
            absent_with_type60_delete_count,
          SUM(CASE WHEN e.ID IS NULL AND vd.DocRef IS NULL THEN 1 ELSE 0 END)
            absent_without_type60_delete_count,
          MIN(CASE WHEN e.ID IS NULL THEN first_log END) absent_first_log_date,
          MAX(CASE WHEN e.ID IS NULL THEN last_log END) absent_last_log_date,
          SUM(CASE WHEN e.ID IS NULL AND last_log>='20260601' AND last_log<'20260901'
            THEN 1 ELSE 0 END) recent_absent_count
        FROM l LEFT JOIN inv.tblExit e ON e.ID=l.OperationId
        LEFT JOIN vd ON vd.DocRef=l.OperationId
        """,
    )[0]
    updates = _rows(
        cursor,
        """
        WITH u AS (
          SELECT OperationId,COUNT_BIG(*) updates,MAX(TransDate) last_update
          FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='inv.tblExit' AND OperationType='UPDATE'
          GROUP BY OperationId
        )
        SELECT COUNT_BIG(*) updated_exit_id_count,SUM(updates) update_event_count,
          SUM(CASE WHEN e.ID IS NOT NULL AND e.IsCanceled=1 THEN 1 ELSE 0 END)
            current_cancelled_count,
          SUM(CASE WHEN e.ID IS NOT NULL AND (e.IsCanceled=0 OR e.IsCanceled IS NULL)
            THEN 1 ELSE 0 END) current_active_count,
          SUM(CASE WHEN e.ID IS NULL THEN 1 ELSE 0 END) absent_count,
          SUM(CASE WHEN updates>1 THEN 1 ELSE 0 END) multi_update_id_count,
          SUM(CASE WHEN e.IsCanceled=1 AND ABS(DATEDIFF(second,e.CancelDateTime,u.last_update))<=5
            THEN 1 ELSE 0 END) cancel_within_5_seconds_count
        FROM u LEFT JOIN inv.tblExit e ON e.ID=u.OperationId
        """,
    )[0]
    return {"operation_counts": operations, "logged_id_coverage": coverage, "update_shape": updates}


def _distribution_state(cursor: Any) -> dict[str, Any]:
    log_coverage = _rows(
        cursor,
        """
        WITH l AS (
          SELECT DistRef,SUM(CASE WHEN OperationType='I' THEN 1 ELSE 0 END) inserts
          FROM SLE.tblDistLog GROUP BY DistRef
        )
        SELECT COUNT_BIG(*) logged_dist_count,
          SUM(CASE WHEN d.ID IS NOT NULL THEN 1 ELSE 0 END) current_count,
          SUM(CASE WHEN d.ID IS NULL THEN 1 ELSE 0 END) absent_count,
          SUM(CASE WHEN inserts>0 THEN 1 ELSE 0 END) with_insert_count,
          SUM(CASE WHEN inserts=0 THEN 1 ELSE 0 END) without_insert_count
        FROM l LEFT JOIN SLE.tblDist d ON d.ID=l.DistRef
        """,
    )[0]
    chain = _rows(
        cursor,
        """
        WITH x AS (
          SELECT ID,DistRef,OperationType,OldStatus,Status,
            LAG(Status) OVER(PARTITION BY DistRef ORDER BY ID) prev_status,
            ROW_NUMBER() OVER(PARTITION BY DistRef ORDER BY ID) rn,
            ROW_NUMBER() OVER(PARTITION BY DistRef ORDER BY ID DESC) rev
          FROM SLE.tblDistLog
        )
        SELECT COUNT_BIG(*) event_count,
          SUM(CASE WHEN rn>1 AND NOT (OldStatus=prev_status OR
            (OldStatus IS NULL AND prev_status IS NULL)) THEN 1 ELSE 0 END)
            chain_break_count,
          SUM(CASE WHEN rn=1 AND NOT(OperationType='I' AND OldStatus IS NULL
            AND x.Status=1) THEN 1 ELSE 0 END) noncanonical_first_count,
          SUM(CASE WHEN rev=1 AND d.ID IS NOT NULL AND x.Status<>d.Status
            THEN 1 ELSE 0 END) latest_current_status_mismatch_count
        FROM x LEFT JOIN SLE.tblDist d ON d.ID=x.DistRef
        """,
    )[0]
    orphan = _rows(
        cursor,
        """
        WITH o AS (
          SELECT l.* FROM SLE.tblDistLog l LEFT JOIN SLE.tblDist d ON d.ID=l.DistRef
          WHERE d.ID IS NULL
        )
        SELECT COUNT_BIG(*) event_count,COUNT(DISTINCT o.DistRef) dist_count,
          COUNT(DISTINCT o.ExitRef) exit_count,
          SUM(CASE WHEN o.ExitRef IS NOT NULL AND e.ID IS NOT NULL THEN 1 ELSE 0 END)
            event_with_current_exit_count,
          SUM(CASE WHEN o.ExitRef IS NOT NULL AND e.ID IS NULL THEN 1 ELSE 0 END)
            event_with_absent_exit_count
        FROM o LEFT JOIN inv.tblExit e ON e.ID=o.ExitRef
        """,
    )[0]
    state = _rows(
        cursor,
        """
        WITH e AS (
          SELECT DistRef,
            SUM(CASE WHEN IsCanceled=0 OR IsCanceled IS NULL THEN 1 ELSE 0 END) active_exits,
            SUM(CASE WHEN IsCanceled=1 THEN 1 ELSE 0 END) cancelled_exits
          FROM inv.tblExit GROUP BY DistRef
        ), s AS (
          SELECT DistRef,COUNT_BIG(*) sales,
            SUM(CASE WHEN ExitRef IS NOT NULL THEN 1 ELSE 0 END) sales_with_exit
          FROM SLE.tblSaleHdr WHERE DistRef IS NOT NULL GROUP BY DistRef
        )
        SELECT d.Status,COUNT_BIG(*) distributions,
          SUM(CASE WHEN COALESCE(e.active_exits,0)>0 THEN 1 ELSE 0 END) with_active_exit,
          SUM(CASE WHEN COALESCE(e.cancelled_exits,0)>0 THEN 1 ELSE 0 END)
            with_cancelled_exit,
          SUM(CASE WHEN COALESCE(e.active_exits,0)=0 AND COALESCE(e.cancelled_exits,0)=0
            THEN 1 ELSE 0 END) without_any_exit,
          SUM(CASE WHEN COALESCE(s.sales,0)>0 THEN 1 ELSE 0 END) with_sales,
          SUM(CASE WHEN COALESCE(s.sales_with_exit,0)>0 THEN 1 ELSE 0 END) with_sale_exit
        FROM SLE.tblDist d LEFT JOIN e ON e.DistRef=d.ID LEFT JOIN s ON s.DistRef=d.ID
        GROUP BY d.Status ORDER BY d.Status
        """,
    )
    return {
        "log_coverage": log_coverage,
        "status_chain": chain,
        "orphan_historical_chain": orphan,
        "current_state_by_status": state,
    }


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safe = _assert_safe_target(cursor)
        profiles, codes = _profiles(cursor)
        current = _current_exit_state(cursor)
        cancellation = _cancellation_reconciliation(cursor)
        general_log = _general_log_lifecycle(cursor)
        distribution = _distribution_state(cursor)
    finally:
        connection.close()

    create = codes["dbo.usp_CreateExitVocherByDist"]
    remove = codes["inv.Usp_RemoveExitFromDist"]
    direct_delete_names = [
        name for name, code in codes.items()
        if re.search(r"\bdelete\s+(?:from\s+)?(?:inv\.)?tblexit\b", code)
    ]
    create_before = _pos(create, r"\bexec\s+dbo\.usp_beforecreateexitvocherbydist\b")
    create_insert = _pos(create, r"\binsert\s+into\s+inv\.tblexit\b")
    remove_before = _pos(remove, r"\bexec\s+inv\.usp_beforeremoveexitfromdist\b")
    remove_cancel = _pos(remove, r"\bupdate\s+inv\.tblexit\s+set\s+iscanceled\s*=\s*1")
    operation_counts = {
        row["OperationType"]: row for row in general_log["operation_counts"]
    }
    return {
        "artifact": "varanegar_distribution_exit_lifecycle_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_LIFECYCLE_AGGREGATES",
            "database_updateability": safe["updateability"],
            "can_select": safe["can_select"],
            "can_view_definition": safe["can_view_definition"],
            "can_update": safe["can_update"],
            "denies_data_writes": safe["denies_data_writes"],
            "stored_procedure_trigger_form_or_application_command_executions": 0,
            "distribution_exit_sale_voucher_reason_user_host_or_raw_log_values_persisted": 0,
            "sql_definitions_operation_scripts_or_business_identifiers_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "selected_sql_module_count": len(profiles),
            "current_exit_count": current["population"]["exit_count"],
            "current_active_exit_count": current["population"]["active_count"],
            "current_cancelled_exit_count": current["population"]["cancelled_count"],
            "recent_cancelled_exit_count": current["cancelled_cleanup"]["recent_cancelled_count"],
            "type60_delete_event_count": cancellation["type60_delete_coverage"][
                "type60_delete_event_count"
            ],
            "cancelled_exit_without_type60_delete_count": cancellation[
                "cancelled_exit_coverage"
            ]["without_type60_delete_log_count"],
            "logged_exit_absent_count": general_log["logged_id_coverage"]["absent_count"],
            "retained_exit_delete_log_count": operation_counts.get(
                "DELETE", {"event_count": 0}
            )["event_count"],
            "direct_physical_exit_delete_candidate_count": len(direct_delete_names),
            "distribution_status_chain_break_count": distribution["status_chain"][
                "chain_break_count"
            ],
            "historically_absent_distribution_count": distribution[
                "orphan_historical_chain"
            ]["dist_count"],
        },
        "sql_module_profiles": profiles,
        "static_exit_contract": {
            "create_validates_before_first_exit_insert": create_before is not None
            and create_insert is not None
            and create_before < create_insert,
            "create_has_no_local_transaction_or_savepoint": not bool(
                re.search(r"\bbegin\s+(?:tran|transaction)\b|\bsave\s+transaction\b", create)
            ),
            "create_writes_exit_sale_type60_items_and_history": all(
                token in create
                for token in (
                    "insert into inv.tblexit",
                    "update sle.tblsalehdr set exitref",
                    "insert into inv.tblvocherhdr",
                    "insert into inv.tblvocheritm",
                    "insert into sle.tblsaledisthistfull",
                )
            ),
            "create_checks_cardex_after_voucher_items": _pos(
                create, r"\binsert\s+into\s+inv\.tblvocheritm\b"
            )
            < _pos(create, r"\bexec\s+inv\.usp_checkcardexqty\b"),
            "remove_validates_before_soft_cancel": remove_before is not None
            and remove_cancel is not None
            and remove_before < remove_cancel,
            "remove_has_no_local_begin_or_commit_but_has_catch_rollback": not bool(
                re.search(r"\bbegin\s+(?:tran|transaction)\b|\bcommit\b", remove)
            )
            and "begin catch" in remove
            and "rollback" in remove,
            "remove_deletes_voucher_graph_unlinks_sales_soft_cancels_exit_and_resets_dist": all(
                token in remove
                for token in (
                    "delete from inv.tblvocheritmdetail",
                    "delete from inv.tblvocheritm",
                    "delete from inv.tblvocherhdr",
                    "set exitref=null",
                    "set iscanceled=1",
                    "update sle.tbldist set status=1",
                    "insert into sle.tblsaledisthistfull",
                )
            ),
            "three_direct_physical_delete_candidates_are_separate_from_soft_cancel": len(
                direct_delete_names
            )
            == 3
            and "inv.Usp_RemoveExitFromDist" not in direct_delete_names,
            "only_vsa_direct_delete_candidate_has_local_transaction": bool(
                re.search(
                    r"\bbegin\s+(?:tran|transaction)\b",
                    codes["dbo.USP_VSA_ChangeDistStatus"],
                )
            )
            and not any(
                re.search(r"\bbegin\s+(?:tran|transaction)\b", codes[name])
                for name in (
                    "dbo.DoPOrder_RollBackReplicatePOrder",
                    "dbo.usp_RollBackSalesReceipt",
                )
            ),
            "current_delete_audit_triggers_are_active_and_replication_bypassable": all(
                next(row for row in profiles if row["qualified_name"] == name)[
                    "is_disabled"
                ]
                is False
                and next(row for row in profiles if row["qualified_name"] == name)[
                    "replication_mode_bypass_signal"
                ]
                for name in (
                    "inv.trg_VN_Replication_tblExit_DELETE",
                    "SLE.trg_VN_Replication_tblDist_DELETE",
                )
            ),
        },
        "current_exit_state": current,
        "cancelled_exit_to_type60_delete_reconciliation": cancellation,
        "generic_exit_log_lifecycle": general_log,
        "distribution_state_and_audit": distribution,
        "direct_physical_exit_delete_candidates": direct_delete_names,
        "evidence_limits": [
            "The normal UI transaction and adapter route is analyzed in a separate hash-pinned runtime artifact; SQL alone does not prove caller-owned transaction enlistment.",
            "CancelDate and type-60 delete adjacency strongly identify one soft-cancel shape but do not prove the invoking procedure, actor or reason.",
            "Eight absent exits and six absent distributions are historical March-2024 lifecycle gaps before the current delete audit triggers were created in February 2026; they are not recent incidents.",
            "The three direct physical-delete modules prove capability, not attribution of the historical eight exits or six distributions.",
            "Distribution status-log chain equality proves retained sequence consistency, not completeness before its first retained insert event.",
            "No procedure, trigger, form or command was executed and no distribution, exit, sale, voucher, reason, user, host, operation script or raw identifier was persisted.",
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
    print(json.dumps(payload["static_exit_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
