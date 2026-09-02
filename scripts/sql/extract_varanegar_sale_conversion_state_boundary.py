"""Extract order-to-sale conversion, projection and deletion boundaries read-only."""

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
    ("SLE", "usp_sdsnet_CreateSaleByOrder"),
    ("SLE", "usp_CreateSaleByOrder"),
    ("SLE", "trg_tblSaleHdr_FillDetail"),
    ("SLE", "trg_tblSaleHdr_Ebtal"),
    ("SLE", "trg_tblSaleHdr_CancelFlag_DeletePayment98"),
    ("SLE", "Trg_tblSaleHdr_UpdateStockGoods"),
    ("SLE", "trg_VN_Replication_tblSaleHdr_DELETE"),
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _code(definition: str) -> str:
    return " ".join(
        _executable_text(definition).replace("[", "").replace("]", "").casefold().split()
    )


def _count(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code, re.I | re.S))


def _pos(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


def _profiles(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    profiles: list[dict[str, Any]] = []
    codes: dict[str, str] = {}
    for schema, name in MODULES:
        result = _rows(
            cursor,
            """
            SELECT s.name schema_name,o.name object_name,o.type_desc,o.create_date,o.modify_date,
              CASE WHEN t.object_id IS NULL THEN NULL ELSE t.is_disabled END is_disabled,
              CASE WHEN t.object_id IS NULL THEN NULL ELSE t.is_instead_of_trigger END
                is_instead_of_trigger,m.definition
            FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
            LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
            LEFT JOIN sys.triggers t ON t.object_id=o.object_id
            WHERE s.name=%s AND o.name=%s
            """,
            (schema, name),
        )
        if len(result) != 1:
            raise AssertionError({"missing_or_duplicate_module": f"{schema}.{name}"})
        row = result[0]
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
                "begin_transaction_signal_count": _count(code, r"\bbegin\s+(?:tran|transaction)\b"),
                "save_transaction_signal_count": _count(code, r"\bsave\s+transaction\b"),
                "commit_signal_count": _count(code, r"\bcommit\b"),
                "rollback_signal_count": _count(code, r"\brollback\b"),
                "try_catch_signal": "begin try" in code and "begin catch" in code,
                "raiserror_signal_count": _count(code, r"\braiserror\b"),
                "throw_signal_count": _count(code, r"\bthrow\b"),
                "insert_signal_count": _count(code, r"\binsert\b"),
                "update_signal_count": _count(code, r"\bupdate\b"),
                "delete_signal_count": _count(code, r"\bdelete\b"),
                "cursor_signal_count": _count(code, r"\bcursor\b"),
                "replication_mode_bypass_signal": "ufn_isreplicationmode" in code
                and bool(re.search(r"\breturn\b", code)),
                "definition_or_literal_values_persisted": False,
            }
        )
    return profiles, codes


def _current_state(cursor: Any) -> dict[str, Any]:
    population = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) sale_count,
          SUM(CASE WHEN CancelFlag=0 THEN 1 ELSE 0 END) active_count,
          SUM(CASE WHEN CancelFlag=1 THEN 1 ELSE 0 END) cancelled_count,
          SUM(CASE WHEN SaleNo IS NOT NULL THEN 1 ELSE 0 END) numbered_count,
          SUM(CASE WHEN SaleNo IS NULL THEN 1 ELSE 0 END) unnumbered_count,
          SUM(CASE WHEN SaleDate>='1405/03/01' AND SaleDate<='1405/05/31' THEN 1 ELSE 0 END)
            recent_sale_date_count,
          SUM(CASE WHEN SaleDate>='1405/03/01' AND SaleDate<='1405/05/31' AND CancelFlag=1
            THEN 1 ELSE 0 END) recent_cancelled_count
        FROM SLE.tblSaleHdr
        """,
    )[0]
    status = _rows(
        cursor,
        """
        SELECT Status,CancelFlag,CASE WHEN SaleNo IS NULL THEN 0 ELSE 1 END has_sale_no,
          COUNT_BIG(*) sale_count
        FROM SLE.tblSaleHdr
        GROUP BY Status,CancelFlag,CASE WHEN SaleNo IS NULL THEN 0 ELSE 1 END
        ORDER BY Status,CancelFlag,has_sale_no
        """,
    )
    relationship = _rows(
        cursor,
        """
        WITH x AS (
          SELECT OrderRef,COUNT_BIG(*) attempts,
            SUM(CASE WHEN CancelFlag=0 THEN 1 ELSE 0 END) active_attempts
          FROM SLE.tblSaleHdr GROUP BY OrderRef
        )
        SELECT COUNT_BIG(*) order_with_sale_count,
          SUM(CASE WHEN attempts>1 THEN 1 ELSE 0 END) multi_attempt_order_count,
          SUM(CASE WHEN active_attempts>1 THEN 1 ELSE 0 END) multi_active_attempt_order_count,
          SUM(CASE WHEN o.SaleHdrRef IS NULL THEN 1 ELSE 0 END) order_without_selected_sale_count,
          SUM(CASE WHEN o.SaleHdrRef IS NOT NULL AND selected.ID IS NULL THEN 1 ELSE 0 END)
            selected_pointer_missing_count,
          SUM(CASE WHEN selected.ID IS NOT NULL AND selected.OrderRef<>o.ID THEN 1 ELSE 0 END)
            selected_reverse_mismatch_count,
          SUM(CASE WHEN selected.CancelFlag=1 THEN 1 ELSE 0 END) selected_cancelled_count
        FROM x JOIN SLE.tblOrderHdr o ON o.ID=x.OrderRef
        LEFT JOIN SLE.tblSaleHdr selected ON selected.ID=o.SaleHdrRef
        """,
    )[0]
    return {"population": population, "status_distribution": status, "order_relationship": relationship}


def _detail_projection(cursor: Any) -> dict[str, Any]:
    overview = _rows(
        cursor,
        """
        WITH ranked AS (
          SELECT d.*,ROW_NUMBER() OVER(PARTITION BY HdrRef ORDER BY ModifiedDate DESC,ID DESC) rev,
            ROW_NUMBER() OVER(PARTITION BY HdrRef ORDER BY ModifiedDate,ID) rn
          FROM SLE.tblSaleHdrDetail d
        )
        SELECT COUNT_BIG(*) detail_count,COUNT(DISTINCT HdrRef) sale_count,
          SUM(CASE WHEN rev=1 AND h.ID IS NULL THEN 1 ELSE 0 END) absent_sale_count,
          SUM(CASE WHEN rev=1 AND h.ID IS NOT NULL AND r.Status<>h.Status THEN 1 ELSE 0 END)
            latest_status_mismatch_count,
          SUM(CASE WHEN rn=1 AND r.Status NOT IN (1,2) THEN 1 ELSE 0 END)
            noncanonical_initial_status_count,
          SUM(CASE WHEN rev=1 AND h.CancelFlag=1 AND r.Status NOT IN (0,3) THEN 1 ELSE 0 END)
            cancelled_header_unexpected_latest_status_count,
          SUM(CASE WHEN rev=1 AND h.CancelFlag=1 AND r.Status IN (0,3) THEN 1 ELSE 0 END)
            cancelled_header_expected_terminal_detail_count,
          SUM(CASE WHEN rev=1 AND h.CancelFlag=1 AND r.Status=0 THEN 1 ELSE 0 END)
            cancelled_header_status0_detail_count,
          SUM(CASE WHEN rev=1 AND h.CancelFlag=1 AND r.Status=3 THEN 1 ELSE 0 END)
            cancelled_header_status3_detail_count,
          SUM(CASE WHEN rev=1 AND h.CancelFlag=0 AND r.Status<>h.Status THEN 1 ELSE 0 END)
            active_header_latest_status_mismatch_count
        FROM ranked r LEFT JOIN SLE.tblSaleHdr h ON h.ID=r.HdrRef
        """,
    )[0]
    transitions = _rows(
        cursor,
        """
        WITH x AS (
          SELECT HdrRef,Status,
            LAG(Status) OVER(PARTITION BY HdrRef ORDER BY ModifiedDate,ID) previous_status
          FROM SLE.tblSaleHdrDetail
        )
        SELECT previous_status,Status,COUNT_BIG(*) transition_count,COUNT(DISTINCT HdrRef) sale_count
        FROM x WHERE previous_status IS NOT NULL
        GROUP BY previous_status,Status ORDER BY previous_status,Status
        """,
    )
    latest_matrix = _rows(
        cursor,
        """
        WITH ranked AS (
          SELECT d.HdrRef,d.Status,d.ModifiedDate,
            ROW_NUMBER() OVER(PARTITION BY HdrRef ORDER BY ModifiedDate DESC,ID DESC) rev
          FROM SLE.tblSaleHdrDetail d
        )
        SELECT h.Status header_status,h.CancelFlag header_cancel_flag,r.Status latest_detail_status,
          COUNT_BIG(*) sale_count,MIN(r.ModifiedDate) first_latest_detail_date,
          MAX(r.ModifiedDate) last_latest_detail_date,
          SUM(CASE WHEN r.ModifiedDate>='20260601' AND r.ModifiedDate<'20260901'
            THEN 1 ELSE 0 END) recent_count
        FROM ranked r JOIN SLE.tblSaleHdr h ON h.ID=r.HdrRef WHERE r.rev=1
        GROUP BY h.Status,h.CancelFlag,r.Status
        ORDER BY h.Status,h.CancelFlag,r.Status
        """,
    )
    return {
        "overview": overview,
        "latest_header_detail_matrix": latest_matrix,
        "transition_matrix": transitions,
    }


def _conversion_attempts(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH s AS (SELECT OrderRef,COUNT_BIG(*) sale_attempts FROM SLE.tblSaleHdr GROUP BY OrderRef),
        t AS (SELECT OrderRef,COUNT_BIG(*) timed_attempts FROM SLE.tblOrderToSaleTime GROUP BY OrderRef),
        keys AS (SELECT OrderRef FROM s UNION SELECT OrderRef FROM t)
        SELECT COUNT_BIG(*) order_count,
          SUM(CASE WHEN COALESCE(s.sale_attempts,0)=COALESCE(t.timed_attempts,0) THEN 1 ELSE 0 END)
            equal_attempt_count_order_count,
          SUM(CASE WHEN COALESCE(s.sale_attempts,0)>COALESCE(t.timed_attempts,0) THEN 1 ELSE 0 END)
            more_sale_than_timing_order_count,
          SUM(CASE WHEN COALESCE(s.sale_attempts,0)<COALESCE(t.timed_attempts,0) THEN 1 ELSE 0 END)
            more_timing_than_sale_order_count,
          SUM(COALESCE(s.sale_attempts,0)) sale_attempt_count,
          SUM(COALESCE(t.timed_attempts,0)) timed_attempt_count,
          SUM(CASE WHEN s.OrderRef IS NOT NULL AND t.OrderRef IS NULL THEN 1 ELSE 0 END)
            sale_order_without_timing_count,
          SUM(CASE WHEN s.OrderRef IS NULL AND t.OrderRef IS NOT NULL THEN 1 ELSE 0 END)
            timing_order_without_sale_count
        FROM keys k LEFT JOIN s ON s.OrderRef=k.OrderRef LEFT JOIN t ON t.OrderRef=k.OrderRef
        """,
    )[0]


def _general_log(cursor: Any) -> dict[str, Any]:
    operations = _rows(
        cursor,
        """
        SELECT OperationType,COUNT_BIG(*) event_count,COUNT(DISTINCT OperationId) id_count,
          SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END)
            recent_event_count,
          MIN(TransDate) first_event_date,MAX(TransDate) last_event_date
        FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
        WHERE OperationTable='SLE.tblSaleHdr'
        GROUP BY OperationType ORDER BY OperationType
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
          WHERE OperationTable='SLE.tblSaleHdr' GROUP BY OperationId
        )
        SELECT COUNT_BIG(*) logged_sale_count,
          SUM(CASE WHEN h.ID IS NOT NULL THEN 1 ELSE 0 END) current_count,
          SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) absent_count,
          SUM(CASE WHEN h.ID IS NULL AND del>0 THEN 1 ELSE 0 END) absent_with_delete_count,
          SUM(CASE WHEN h.ID IS NULL AND del=0 THEN 1 ELSE 0 END) absent_without_delete_count,
          SUM(CASE WHEN h.ID IS NULL AND del>0 AND last_log>='20260601' AND last_log<'20260901'
            THEN 1 ELSE 0 END) recent_absent_with_delete_count,
          SUM(CASE WHEN h.ID IS NULL AND del=0 AND last_log>='20260601' AND last_log<'20260901'
            THEN 1 ELSE 0 END) recent_absent_without_delete_count,
          MIN(CASE WHEN h.ID IS NULL THEN first_log END) absent_first_log_date,
          MAX(CASE WHEN h.ID IS NULL THEN last_log END) absent_last_log_date,
          SUM(CASE WHEN h.ID IS NULL AND last_log>='20260601' AND last_log<'20260901'
            THEN 1 ELSE 0 END) recent_absent_count
        FROM l LEFT JOIN SLE.tblSaleHdr h ON h.ID=l.OperationId
        """,
    )[0]
    return {"operation_counts": operations, "logged_id_coverage": coverage}


def _direct_delete_candidates(cursor: Any) -> list[dict[str, Any]]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition
        FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE m.definition LIKE '%tblSaleHdr%'
        """,
    )
    candidates = []
    for row in rows:
        definition = row.pop("definition") or ""
        code = _code(definition)
        if not re.search(r"\bdelete\s+(?:from\s+)?(?:sle\.)?tblsalehdr\b", code):
            continue
        candidates.append(
            {
                **row,
                "qualified_name": f"{row['schema_name']}.{row['object_name']}",
                "definition_sha256": _sha(definition),
                "begin_transaction_signal_count": _count(code, r"\bbegin\s+(?:tran|transaction)\b"),
                "save_transaction_signal_count": _count(code, r"\bsave\s+transaction\b"),
                "commit_signal_count": _count(code, r"\bcommit\b"),
                "rollback_signal_count": _count(code, r"\brollback\b"),
                "replication_mode_bypass_signal": "ufn_isreplicationmode" in code
                and bool(re.search(r"\breturn\b", code)),
                "definition_or_literal_values_persisted": False,
            }
        )
    return sorted(candidates, key=lambda row: row["qualified_name"].casefold())


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safe = _assert_safe_target(cursor)
        profiles, codes = _profiles(cursor)
        current = _current_state(cursor)
        detail = _detail_projection(cursor)
        timing = _conversion_attempts(cursor)
        general_log = _general_log(cursor)
        delete_candidates = _direct_delete_candidates(cursor)
    finally:
        connection.close()

    orchestration = codes["SLE.usp_sdsnet_CreateSaleByOrder"]
    core = codes["SLE.usp_CreateSaleByOrder"]
    fill_detail = codes["SLE.trg_tblSaleHdr_FillDetail"]
    cancel_payment = codes["SLE.trg_tblSaleHdr_CancelFlag_DeletePayment98"]
    stock = codes["SLE.Trg_tblSaleHdr_UpdateStockGoods"]
    operations = {row["OperationType"]: row for row in general_log["operation_counts"]}
    recent_projection_exception_count = sum(
        row["recent_count"]
        for row in detail["latest_header_detail_matrix"]
        if (row["header_cancel_flag"] == 0 and row["header_status"] != row["latest_detail_status"])
        or (row["header_cancel_flag"] == 1 and row["latest_detail_status"] not in (0, 3))
    )
    core_call = orchestration.find("usp_createsalebyorder")
    core_call = None if core_call < 0 else core_call
    pointer_update = _pos(orchestration, r"\bupdate\s+(?:sle\.)?tblorderhdr\b")
    return {
        "artifact": "varanegar_sale_conversion_state_boundary",
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
            "order_sale_customer_goods_user_host_or_raw_log_values_persisted": 0,
            "sql_definitions_error_texts_or_business_identifiers_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "selected_sql_module_count": len(profiles),
            "current_sale_count": current["population"]["sale_count"],
            "current_active_sale_count": current["population"]["active_count"],
            "current_cancelled_sale_count": current["population"]["cancelled_count"],
            "recent_sale_count": current["population"]["recent_sale_date_count"],
            "recent_cancelled_sale_count": current["population"]["recent_cancelled_count"],
            "sale_detail_count": detail["overview"]["detail_count"],
            "latest_detail_status_mismatch_count": detail["overview"]["latest_status_mismatch_count"],
            "active_latest_detail_status_mismatch_count": detail["overview"][
                "active_header_latest_status_mismatch_count"
            ],
            "cancelled_unexpected_latest_detail_status_count": detail["overview"][
                "cancelled_header_unexpected_latest_status_count"
            ],
            "recent_projection_exception_count": recent_projection_exception_count,
            "direct_physical_sale_delete_candidate_count": len(delete_candidates),
            "logged_sale_absent_count": general_log["logged_id_coverage"]["absent_count"],
            "retained_sale_delete_log_count": operations.get("DELETE", {"event_count": 0})["event_count"],
            "recent_retained_sale_delete_log_count": operations.get(
                "DELETE", {"recent_event_count": 0}
            )["recent_event_count"],
            "absent_without_delete_log_count": general_log["logged_id_coverage"][
                "absent_without_delete_count"
            ],
        },
        "sql_module_profiles": profiles,
        "static_conversion_and_projection_contract": {
            "orchestrator_has_with_out_rollback_parameter_and_branches": "@withoutrollback" in orchestration
            and _count(orchestration, r"@withoutrollback") >= 2,
            "orchestrator_has_local_transaction_try_catch_commit_and_rollback": all(
                token in orchestration
                for token in ("begin transaction", "begin try", "begin catch", "commit", "rollback")
            ),
            "orchestrator_calls_core_before_order_selected_sale_pointer_update": core_call is not None
            and pointer_update is not None
            and core_call < pointer_update,
            "orchestrator_writes_conversion_timing_and_order_sale_pointer": "tblordertosaletime" in orchestration
            and "tblorderhdr" in orchestration and "salehdrref" in orchestration,
            "orchestrator_mutates_payment_batch_reserved_prize_and_item_detail": all(
                token in orchestration
                for token in ("tblpayments", "tblbatchno", "tblreservedprize", "tblsaleitmdetail")
            ),
            "orchestrator_contains_dynamic_sql": bool(re.search(r"\bexec\s*\(", orchestration))
            or "sp_executesql" in orchestration,
            "core_has_no_local_transaction": not bool(
                re.search(r"\bbegin\s+(?:tran|transaction)\b|\bsave\s+transaction\b", core)
            ),
            "core_inserts_sale_header_and_items": "tblsalehdr" in core and "tblsaleitm" in core
            and _count(core, r"\binsert\b") > 0,
            "detail_trigger_inserts_sale_detail_on_header_change": "tblsalehdrdetail" in fill_detail
            and _count(fill_detail, r"\binsert\b") > 0,
            "cancel_trigger_deletes_payment_on_cancel_flag_change": "tblpayments" in cancel_payment
            and _count(cancel_payment, r"\bdelete\b") > 0,
            "stock_trigger_mutates_stock_goods_from_sale_header": "stockgoods" in stock
            and _count(stock, r"\bupdate\b") > 0,
            "current_replication_delete_trigger_is_bypassable": next(
                row for row in profiles if row["qualified_name"] == "SLE.trg_VN_Replication_tblSaleHdr_DELETE"
            )["replication_mode_bypass_signal"],
        },
        "current_sale_state": current,
        "sale_detail_projection": detail,
        "conversion_attempt_timing_reconciliation": timing,
        "generic_sale_log_lifecycle": general_log,
        "direct_physical_sale_delete_candidates": delete_candidates,
        "evidence_limits": [
            "Static SQL structure proves capabilities and relative textual order, not branch execution, runtime frequency or successful effects.",
            "The WithOutRollback parameter is a legacy control-flow capability; this artifact does not assert which runtime caller values were used.",
            "Latest detail is ranked by ModifiedDate then ID; equality supports retained projection consistency but cannot prove missing pre-retention history.",
            "Conversion timing rows are operational timing evidence, not a complete idempotency ledger or business lead-time measure.",
            "Direct-delete modules prove capability, not attribution of any absent historical sale.",
            "No procedure, trigger, form or command was executed and no order, sale, customer, goods, user, host, error text or raw identifier was persisted.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(json.dumps(payload["static_conversion_and_projection_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
