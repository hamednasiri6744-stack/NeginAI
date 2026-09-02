"""Extract sale-cancellation command, linkage and projection boundaries read-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows
from extract_varanegar_ngt_order_target_deletion_boundary import _executable_text


MODULES = (
    ("dbo", "usp_sdsnet_Sale_Cancel"),
    ("SLE", "trg_tblSaleHdr_Ebtal"),
    ("SLE", "trg_tblSaleHdr_CancelFlag_DeletePayment98"),
    ("SLE", "trg_tblSaleHdr_FillDetail"),
    ("SLE", "Trg_tblSaleHdr_UpdateStockGoods"),
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _code(definition: str) -> str:
    return " ".join(_executable_text(definition).replace("[", "").replace("]", "").casefold().split())


def _count(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code, re.I | re.S))


def _pos(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


def _profiles(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    profiles, codes = [], {}
    for schema, name in MODULES:
        result = _rows(
            cursor,
            """
            SELECT s.name schema_name,o.name object_name,o.object_id,o.type_desc,
              o.create_date,o.modify_date,CASE WHEN t.object_id IS NULL THEN NULL ELSE t.is_disabled END is_disabled,
              CASE WHEN t.object_id IS NULL THEN NULL ELSE t.is_instead_of_trigger END is_instead_of_trigger,
              m.definition
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
        object_id = row.pop("object_id")
        definition = row.pop("definition") or ""
        code = _code(definition)
        qualified = f"{schema}.{name}"
        codes[qualified] = code
        dependencies = _rows(
            cursor,
            """
            SELECT DISTINCT COALESCE(referenced_schema_name,'') referenced_schema,
              COALESCE(referenced_entity_name,'') referenced_entity
            FROM sys.sql_expression_dependencies WHERE referencing_id=%s
              AND referenced_entity_name IS NOT NULL
            ORDER BY referenced_schema,referenced_entity
            """,
            (object_id,),
        )
        profiles.append(
            {
                **row,
                "qualified_name": qualified,
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "dependency_count": len(dependencies),
                "dependencies": [
                    ".".join(part for part in (d["referenced_schema"], d["referenced_entity"]) if part)
                    for d in dependencies
                ],
                "begin_transaction_signal_count": _count(code, r"\bbegin\s+(?:tran|transaction)\b"),
                "save_transaction_signal_count": _count(code, r"\bsave\s+transaction\b"),
                "commit_signal_count": _count(code, r"\bcommit\b"),
                "rollback_signal_count": _count(code, r"\brollback\b"),
                "try_catch_signal": "begin try" in code and "begin catch" in code,
                "raiserror_signal_count": _count(code, r"\braiserror\b"),
                "insert_signal_count": _count(code, r"\binsert\b"),
                "update_signal_count": _count(code, r"\bupdate\b"),
                "delete_signal_count": _count(code, r"\bdelete\b"),
                "cursor_signal_count": _count(code, r"\bcursor\b"),
                "definition_or_literal_values_persisted": False,
            }
        )
    return profiles, codes


def _state_and_links(cursor: Any) -> dict[str, Any]:
    overview = _rows(
        cursor,
        """
        WITH p AS (SELECT DISTINCT SaleRef FROM Acc.tblPayments WHERE SaleRef IS NOT NULL),
        sel AS (SELECT SaleHdrRef,CancelFlag order_cancel_flag FROM SLE.tblOrderHdr WHERE SaleHdrRef IS NOT NULL)
        SELECT h.CancelFlag,COUNT_BIG(*) sale_count,
          SUM(CASE WHEN p.SaleRef IS NOT NULL THEN 1 ELSE 0 END) sale_with_payment_count,
          SUM(CASE WHEN h.ExitRef IS NOT NULL THEN 1 ELSE 0 END) sale_with_exit_link_count,
          SUM(CASE WHEN h.DistRef IS NOT NULL THEN 1 ELSE 0 END) sale_with_dist_link_count,
          SUM(CASE WHEN e.ID IS NOT NULL AND (e.IsCanceled=0 OR e.IsCanceled IS NULL) THEN 1 ELSE 0 END)
            sale_with_active_exit_count,
          SUM(CASE WHEN e.ID IS NOT NULL AND e.IsCanceled=1 THEN 1 ELSE 0 END)
            sale_with_cancelled_exit_count,
          SUM(CASE WHEN sel.SaleHdrRef IS NOT NULL THEN 1 ELSE 0 END) selected_by_order_count,
          SUM(CASE WHEN sel.SaleHdrRef IS NOT NULL AND sel.order_cancel_flag=0 THEN 1 ELSE 0 END)
            selected_by_active_order_count,
          SUM(CASE WHEN sel.SaleHdrRef IS NOT NULL AND sel.order_cancel_flag=1 THEN 1 ELSE 0 END)
            selected_by_cancelled_order_count
        FROM SLE.tblSaleHdr h LEFT JOIN p ON p.SaleRef=h.ID
        LEFT JOIN inv.tblExit e ON e.ID=h.ExitRef LEFT JOIN sel ON sel.SaleHdrRef=h.ID
        GROUP BY h.CancelFlag ORDER BY h.CancelFlag
        """,
    )
    cancelled_by_status = _rows(
        cursor,
        """
        WITH p AS (SELECT SaleRef,COUNT_BIG(*) payment_count FROM Acc.tblPayments
          WHERE SaleRef IS NOT NULL GROUP BY SaleRef)
        SELECT h.Status,CASE WHEN h.SaleNo IS NULL THEN 0 ELSE 1 END has_sale_no,
          COUNT_BIG(*) sale_count,SUM(CASE WHEN p.SaleRef IS NOT NULL THEN 1 ELSE 0 END)
            sale_with_payment_count,SUM(COALESCE(p.payment_count,0)) payment_count,
          SUM(CASE WHEN h.ExitRef IS NOT NULL THEN 1 ELSE 0 END) sale_with_exit_link_count,
          SUM(CASE WHEN h.DistRef IS NOT NULL THEN 1 ELSE 0 END) sale_with_dist_link_count
        FROM SLE.tblSaleHdr h LEFT JOIN p ON p.SaleRef=h.ID WHERE h.CancelFlag=1
        GROUP BY h.Status,CASE WHEN h.SaleNo IS NULL THEN 0 ELSE 1 END
        ORDER BY h.Status,has_sale_no
        """,
    )
    return {"by_cancel_flag": overview, "cancelled_by_status": cancelled_by_status}


def _terminal_detail(cursor: Any) -> dict[str, Any]:
    overview = _rows(
        cursor,
        """
        WITH r AS (
          SELECT HdrRef,Status,ModifiedDate,
            ROW_NUMBER() OVER(PARTITION BY HdrRef ORDER BY ModifiedDate DESC,ID DESC) rev
          FROM SLE.tblSaleHdrDetail
        )
        SELECT COUNT_BIG(*) cancelled_sale_count,
          SUM(CASE WHEN r.Status=0 THEN 1 ELSE 0 END) terminal_status0_count,
          SUM(CASE WHEN r.Status=3 THEN 1 ELSE 0 END) terminal_status3_count,
          SUM(CASE WHEN r.Status NOT IN (0,3) THEN 1 ELSE 0 END) unexpected_terminal_count,
          SUM(CASE WHEN r.Status NOT IN (0,3) AND r.ModifiedDate>='20260601'
            AND r.ModifiedDate<'20260901' THEN 1 ELSE 0 END) recent_unexpected_terminal_count,
          SUM(CASE WHEN r.Status IN (0,3) AND r.ModifiedDate>='20260601'
            AND r.ModifiedDate<'20260901' THEN 1 ELSE 0 END) recent_terminal_count
        FROM SLE.tblSaleHdr h JOIN r ON r.HdrRef=h.ID AND r.rev=1 WHERE h.CancelFlag=1
        """,
    )[0]
    matrix = _rows(
        cursor,
        """
        WITH r AS (
          SELECT HdrRef,Status,ModifiedDate,
            ROW_NUMBER() OVER(PARTITION BY HdrRef ORDER BY ModifiedDate DESC,ID DESC) rev
          FROM SLE.tblSaleHdrDetail
        )
        SELECT h.Status header_status,r.Status terminal_detail_status,COUNT_BIG(*) sale_count,
          SUM(CASE WHEN r.ModifiedDate>='20260601' AND r.ModifiedDate<'20260901'
            THEN 1 ELSE 0 END) recent_count
        FROM SLE.tblSaleHdr h JOIN r ON r.HdrRef=h.ID AND r.rev=1 WHERE h.CancelFlag=1
        GROUP BY h.Status,r.Status ORDER BY h.Status,r.Status
        """,
    )
    return {"overview": overview, "header_terminal_matrix": matrix}


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safe = _assert_safe_target(cursor)
        profiles, codes = _profiles(cursor)
        links = _state_and_links(cursor)
        terminal = _terminal_detail(cursor)
    finally:
        connection.close()

    cancel = codes["dbo.usp_sdsnet_Sale_Cancel"]
    ebtal = codes["SLE.trg_tblSaleHdr_Ebtal"]
    payment = codes["SLE.trg_tblSaleHdr_CancelFlag_DeletePayment98"]
    detail = codes["SLE.trg_tblSaleHdr_FillDetail"]
    stock = codes["SLE.Trg_tblSaleHdr_UpdateStockGoods"]
    cancel_profile = next(row for row in profiles if row["qualified_name"] == "dbo.usp_sdsnet_Sale_Cancel")
    cancel_dependencies = {name.casefold() for name in cancel_profile["dependencies"]}
    cancel_update = _pos(cancel, r"\bupdate\s+(?:sle\.)?tblsalehdr\b")
    order_update = _pos(cancel, r"\bupdate\s+(?:sle\.)?tblorderhdr\b")
    cancelled = next(row for row in links["by_cancel_flag"] if row["CancelFlag"] == 1)
    return {
        "artifact": "varanegar_sale_cancellation_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_CANCELLATION_AGGREGATES",
            "database_updateability": safe["updateability"],
            "can_select": safe["can_select"],
            "can_view_definition": safe["can_view_definition"],
            "can_update": safe["can_update"],
            "denies_data_writes": safe["denies_data_writes"],
            "stored_procedure_trigger_form_or_application_command_executions": 0,
            "sale_order_payment_exit_customer_user_host_or_raw_values_persisted": 0,
            "sql_definitions_error_texts_or_business_identifiers_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "selected_sql_module_count": len(profiles),
            "cancelled_sale_count": cancelled["sale_count"],
            "cancelled_sale_with_payment_count": cancelled["sale_with_payment_count"],
            "cancelled_sale_with_exit_link_count": cancelled["sale_with_exit_link_count"],
            "cancelled_sale_with_dist_link_count": cancelled["sale_with_dist_link_count"],
            "cancelled_sale_selected_by_order_count": cancelled["selected_by_order_count"],
            "cancelled_sale_selected_by_active_order_count": cancelled["selected_by_active_order_count"],
            "cancelled_sale_unexpected_terminal_detail_count": terminal["overview"]["unexpected_terminal_count"],
            "recent_cancelled_sale_terminal_detail_count": terminal["overview"]["recent_terminal_count"],
        },
        "sql_module_profiles": profiles,
        "static_cancellation_contract": {
            "cancel_has_local_transaction_try_catch_commit_and_rollback": all(
                token in cancel for token in ("begin transaction", "begin try", "begin catch", "commit", "rollback")
            ),
            "cancel_updates_sale_before_or_without_order_pointer_update": cancel_update is not None
            and (order_update is None or cancel_update < order_update),
            "cancel_directly_references_sale_order_payment_and_detail_domains": all(
                name in cancel_dependencies
                for name in ("sle.tblsalehdr", "sle.tblorderhdr", "acc.tblpayments", "sle.tblsaleitmdetail")
            ),
            "cancel_has_no_direct_exit_or_distribution_dependency": not any(
                token in name for name in cancel_dependencies for token in ("tblexit", "tbldist")
            ),
            "cancel_has_dynamic_sql_capability": bool(re.search(r"\bexec\s*\(", cancel))
            or "sp_executesql" in cancel,
            "ebtal_trigger_reacts_to_cancel_flag_and_updates_order_or_sale_state": "cancelflag" in ebtal
            and _count(ebtal, r"\bupdate\b") > 0,
            "payment_trigger_deletes_direct_sale_payments_on_cancel": "tblpayments" in payment
            and "saleref" in payment and _count(payment, r"\bdelete\b") > 0,
            "detail_trigger_records_header_state_change": "tblsalehdrdetail" in detail
            and _count(detail, r"\binsert\b") > 0,
            "stock_trigger_updates_stock_projection_on_cancel_or_state_change": "stockgoods" in stock
            and _count(stock, r"\bupdate\b") > 0,
        },
        "current_sale_cancellation_links": links,
        "terminal_detail_projection": terminal,
        "evidence_limits": [
            "Static SQL proves capability and textual ordering, not which runtime branch executed or whether every dependent effect succeeded.",
            "A retained payment, exit or distribution link on a cancelled sale is reported as state shape, not automatically classified as an error without the owning business rule.",
            "Status 0 or 3 terminal detail is treated as the observed cancellation vocabulary; three historical exceptions are not attributed to a command or actor.",
            "No procedure, trigger, form or command was executed and no sale, order, payment, exit, customer, user, host, error text or raw identifier was persisted.",
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
    print(json.dumps(payload["static_cancellation_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
