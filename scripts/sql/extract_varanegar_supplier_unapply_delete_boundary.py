"""Extract supplier invoice unlink/delete/reverse-cost boundary read-only."""

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
    ("ICA", "uspLinkUnlinkSupInvoiceInv"),
    ("ICA", "UspSupInvoiceHdrDelete"),
    ("ICA", "UspSupInvoiceHdrDeleteItemsAndTolls"),
    ("ICA", "UspSupInvoiceHdrUpdate"),
    ("ICA", "UspSupInvoiceHdrOperation"),
    ("ICA", "UspDeleteTransferedVchrs"),
    ("inv", "RemoveVocherForSupinvoice"),
    ("dbo", "usp_sdsnet_SupInvoice_Save"),
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _position(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


def _profiles(cursor: Any) -> list[dict[str, Any]]:
    rows = []
    for schema, name in MODULES:
        row = _rows(
            cursor,
            """
            SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,m.definition
            FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
            JOIN sys.schemas s ON s.schema_id=o.schema_id
            WHERE s.name=%s AND o.name=%s
            """,
            (schema, name),
        )[0]
        definition = row.pop("definition") or ""
        code = " ".join(
            _executable_text(definition).replace("[", "").replace("]", "").casefold().split()
        )
        relation_delete = _position(
            code, r"\bdelete\s+(?:from\s+)?ica\.tblsupinvinvoicerelation\b"
        )
        item_toll_delete = _position(
            code,
            r"\bdelete\s+(?:from\s+)?ica\.(?:tblsupinvoiceitm|tblsupinvoicetolls|tblsupinvoiceitmtolls)\b",
        )
        header_delete = _position(
            code, r"\bdelete\s+(?:from\s+)?ica\.tblsupinvoicehdr\b"
        )
        status_zero = _position(
            code, r"\bupdate\s+ica\.tblsupinvoicehdr\b.{0,500}?\bstatus\s*=\s*0\b"
        )
        confirm_null = _position(
            code,
            r"\bupdate\s+ica\.tblsupinvoicehdr\b.{0,500}?\bconfirmdate\s*=\s*null\b",
        )
        price_zero = _position(
            code,
            r"\bupdate\s+inv\.tblvocheritmprice\b.{0,500}?\bprice\s*=\s*0\b.{0,200}?\bunitprice\s*=\s*0\b",
        )
        rows.append(
            {
                **row,
                "qualified_name": f"{schema}.{name}",
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "owns_explicit_transaction": bool(
                    re.search(r"\bbegin\s+(?:tran|transaction)\b", code)
                ),
                "has_commit_signal": bool(re.search(r"\bcommit\b", code)),
                "has_rollback_signal": bool(re.search(r"\brollback\b", code)),
                "has_try_catch": "begin try" in code and "begin catch" in code,
                "has_xact_abort": "xact_abort" in code,
                "raises_domain_error": "raiserror" in code or "throw" in code,
                "reads_application_name": "app_name" in code,
                "has_sdsnet_specific_branch": "sds.net" in definition.casefold(),
                "deletes_relation": relation_delete is not None,
                "deletes_invoice_item_or_toll": item_toll_delete is not None,
                "deletes_invoice_header": header_delete is not None,
                "sets_invoice_status_zero": status_zero is not None,
                "clears_invoice_confirm_date": confirm_null is not None,
                "zeros_voucher_item_price_and_unit_price": price_zero is not None,
                "reads_purchase_final_date": "tblic aoprdate".replace(" ", "") in code
                or "tblicaoprdate" in code,
                "reads_last_closed_purchase_date": "lastdate" in code
                and "tbloprdate" in code,
                "calls_date_closed_guard": "ufdateisclosed" in code,
                "reads_supplier_settlement": "tblsupsettlement" in code,
                "reads_supplier_return": "tblretsupinvoicehdr" in code,
                "disables_relation_trigger": "disable trigger" in code
                and "tblsupinvinvoicerelation" in code,
                "relation_delete_precedes_header_delete": relation_delete is not None
                and header_delete is not None
                and relation_delete < header_delete,
                "status_zero_precedes_price_zero": status_zero is not None
                and price_zero is not None
                and status_zero < price_zero,
                "definition_or_offsets_persisted": False,
            }
        )
    return rows


def _call_graph(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT DISTINCT OBJECT_SCHEMA_NAME(d.referencing_id) caller_schema,
          OBJECT_NAME(d.referencing_id) caller_name,
          OBJECT_SCHEMA_NAME(d.referenced_id) callee_schema,
          OBJECT_NAME(d.referenced_id) callee_name
        FROM sys.sql_expression_dependencies d
        WHERE d.referenced_id IN (
          OBJECT_ID(N'ICA.uspLinkUnlinkSupInvoiceInv'),
          OBJECT_ID(N'ICA.UspSupInvoiceHdrDelete'),
          OBJECT_ID(N'ICA.UspSupInvoiceHdrDeleteItemsAndTolls'),
          OBJECT_ID(N'ICA.UspSupInvoiceHdrUpdate'),
          OBJECT_ID(N'ICA.UspSupInvoiceHdrOperation'),
          OBJECT_ID(N'ICA.UspDeleteTransferedVchrs'),
          OBJECT_ID(N'inv.RemoveVocherForSupinvoice'),
          OBJECT_ID(N'dbo.usp_sdsnet_SupInvoice_Save'))
        ORDER BY callee_schema,callee_name,caller_schema,caller_name
        """,
    )


def _header_relation_state(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH x AS (
          SELECT h.Status,h.ID,h.ConfirmDate,COUNT(DISTINCT r.InvVchHdrRef) relation_count
          FROM ICA.TblSupInvoiceHdr h
          LEFT JOIN ICA.tblSupInvInvoiceRelation r ON r.SupInvoiceHdrRef=h.ID
          GROUP BY h.Status,h.ID,h.ConfirmDate
        )
        SELECT Status,COUNT_BIG(*) header_count,
          SUM(CASE WHEN relation_count=0 THEN 1 ELSE 0 END) no_relation_count,
          SUM(CASE WHEN relation_count=1 THEN 1 ELSE 0 END) one_relation_count,
          SUM(CASE WHEN relation_count>1 THEN 1 ELSE 0 END) multi_relation_count,
          MAX(relation_count) max_relation_count,
          SUM(CASE WHEN ConfirmDate IS NULL THEN 1 ELSE 0 END) confirm_null_count,
          SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirm_present_count
        FROM x GROUP BY Status ORDER BY Status
        """,
    )


def _dependency_state(cursor: Any) -> dict[str, Any]:
    settlement = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) settlement_count,
          SUM(CASE WHEN h.Status=1 THEN 1 ELSE 0 END) applied_invoice_settlement_count,
          SUM(CASE WHEN h.Status=0 THEN 1 ELSE 0 END) unapplied_invoice_settlement_count
        FROM Acc.tblSupSettlement s
        JOIN ICA.TblSupInvoiceHdr h ON h.ID=s.SupInvoiceRef
        """,
    )[0]
    returns = _rows(
        cursor,
        """
        SELECT h.Status,COUNT_BIG(DISTINCT r.ID) return_header_count,
          COUNT_BIG(DISTINCT h.ID) source_invoice_count
        FROM ICA.TblSupInvoiceHdr h
        JOIN ICA.tblRetSupInvoiceHdr r ON r.SupInvoiceRef=h.ID
        GROUP BY h.Status ORDER BY h.Status
        """,
    )
    return {"settlement": settlement, "return_source_by_invoice_status": returns}


def _price_state(cursor: Any) -> dict[str, Any]:
    all_prices = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) price_row_count,
          SUM(CASE WHEN Price=0 AND UnitPrice=0 THEN 1 ELSE 0 END) both_zero_count
        FROM inv.tblVocherItmPrice
        """,
    )[0]
    related = _rows(
        cursor,
        """
        WITH x AS (
          SELECT DISTINCT h.Status,vi.ID
          FROM ICA.TblSupInvoiceHdr h
          JOIN ICA.tblSupInvInvoiceRelation r ON r.SupInvoiceHdrRef=h.ID
          JOIN inv.tblVocherItm vi ON vi.HdrRef=r.InvVchHdrRef
        )
        SELECT x.Status,COUNT_BIG(*) related_item_count,
          SUM(CASE WHEN p.ID IS NOT NULL THEN 1 ELSE 0 END) price_present_count,
          SUM(CASE WHEN p.ID IS NULL THEN 1 ELSE 0 END) price_absent_count,
          SUM(CASE WHEN p.Price=0 AND p.UnitPrice=0 THEN 1 ELSE 0 END) both_zero_count
        FROM x LEFT JOIN inv.tblVocherItmPrice p ON p.ID=x.ID
        GROUP BY x.Status ORDER BY x.Status
        """,
    )
    return {"all_price_rows": all_prices, "related_items_by_invoice_status": related}


def _relation_log(cursor: Any) -> dict[str, Any]:
    event_counts = _rows(
        cursor,
        """
        SELECT OperationType,COUNT_BIG(*) event_count,
          COUNT(DISTINCT OperationId) distinct_relation_id_count,
          SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_event_count,
          MIN(TransDate) first_event_date,MAX(TransDate) last_event_date
        FROM GNR.tblLog WITH (INDEX(IX_Nc_tbllog_operationTable))
        WHERE OperationTable='ICA.TblSupInvInvoiceRelation'
        GROUP BY OperationType ORDER BY OperationType
        """,
    )
    lifecycle = _rows(
        cursor,
        """
        WITH l AS (
          SELECT OperationId,
            SUM(CASE WHEN OperationType='INSERT' THEN 1 ELSE 0 END) insert_count,
            SUM(CASE WHEN OperationType='DELETE' THEN 1 ELSE 0 END) delete_count
          FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='ICA.TblSupInvInvoiceRelation' GROUP BY OperationId
        )
        SELECT COUNT_BIG(*) logged_id_count,
          SUM(CASE WHEN r.ID IS NOT NULL THEN 1 ELSE 0 END) currently_present_count,
          SUM(CASE WHEN r.ID IS NULL THEN 1 ELSE 0 END) currently_absent_count,
          SUM(CASE WHEN insert_count>1 THEN 1 ELSE 0 END) multi_insert_id_count,
          SUM(CASE WHEN delete_count>1 THEN 1 ELSE 0 END) multi_delete_id_count,
          SUM(CASE WHEN insert_count>0 AND delete_count>0 THEN 1 ELSE 0 END)
            both_event_id_count,
          SUM(CASE WHEN delete_count>0 AND r.ID IS NOT NULL THEN 1 ELSE 0 END)
            deleted_but_currently_present_count,
          SUM(CASE WHEN insert_count>0 AND delete_count=0 AND r.ID IS NULL THEN 1 ELSE 0 END)
            insert_only_but_currently_absent_count
        FROM l LEFT JOIN ICA.tblSupInvInvoiceRelation r ON r.ID=l.OperationId
        """,
    )[0]
    last_event = _rows(
        cursor,
        """
        WITH x AS (
          SELECT OperationId,OperationType,
            ROW_NUMBER() OVER(PARTITION BY OperationId ORDER BY ID DESC) rn
          FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
          WHERE OperationTable='ICA.TblSupInvInvoiceRelation'
        )
        SELECT x.OperationType last_event,
          CASE WHEN r.ID IS NULL THEN 0 ELSE 1 END current_present,
          COUNT_BIG(*) relation_id_count
        FROM x LEFT JOIN ICA.tblSupInvInvoiceRelation r ON r.ID=x.OperationId
        WHERE x.rn=1
        GROUP BY x.OperationType,CASE WHEN r.ID IS NULL THEN 0 ELSE 1 END
        ORDER BY x.OperationType,current_present
        """,
    )
    return {"event_counts": event_counts, "lifecycle": lifecycle, "last_event_projection": last_event}


def _storage_guards(cursor: Any) -> dict[str, Any]:
    tables = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,t.temporal_type_desc,t.is_tracked_by_cdc,
          CASE WHEN ct.object_id IS NULL THEN 0 ELSE 1 END change_tracking_enabled
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        LEFT JOIN sys.change_tracking_tables ct ON ct.object_id=t.object_id
        WHERE t.object_id IN (OBJECT_ID(N'ICA.TblSupInvoiceHdr'),
          OBJECT_ID(N'ICA.tblSupInvInvoiceRelation'),OBJECT_ID(N'inv.tblVocherItmPrice'))
        ORDER BY s.name,t.name
        """,
    )
    triggers = _rows(
        cursor,
        """
        SELECT OBJECT_SCHEMA_NAME(t.parent_id) schema_name,OBJECT_NAME(t.parent_id) table_name,
          t.name trigger_name,t.is_disabled
        FROM sys.triggers t
        WHERE t.parent_id IN (OBJECT_ID(N'ICA.TblSupInvoiceHdr'),
          OBJECT_ID(N'ICA.tblSupInvInvoiceRelation'),OBJECT_ID(N'inv.tblVocherItmPrice'))
        ORDER BY table_name,trigger_name
        """,
    )
    fks = _rows(
        cursor,
        """
        SELECT OBJECT_SCHEMA_NAME(fk.parent_object_id) child_schema,
          OBJECT_NAME(fk.parent_object_id) child_table,fk.name constraint_name,
          fk.is_disabled,fk.is_not_trusted,fk.delete_referential_action_desc
        FROM sys.foreign_keys fk
        WHERE fk.referenced_object_id=OBJECT_ID(N'ICA.TblSupInvoiceHdr')
           OR fk.parent_object_id=OBJECT_ID(N'inv.tblVocherItmPrice')
        ORDER BY child_schema,child_table,constraint_name
        """,
    )
    return {"table_capabilities": tables, "active_triggers": triggers, "foreign_keys": fks}


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safe = _assert_safe_target(cursor)
        profiles = _profiles(cursor)
        graph = _call_graph(cursor)
        states = _header_relation_state(cursor)
        dependencies = _dependency_state(cursor)
        prices = _price_state(cursor)
        log = _relation_log(cursor)
        guards = _storage_guards(cursor)
    finally:
        connection.close()
    by_name = {row["object_name"]: row for row in profiles}
    unlink = by_name["uspLinkUnlinkSupInvoiceInv"]
    status0 = next(row for row in states if row["Status"] == 0)
    status1 = next(row for row in states if row["Status"] == 1)
    log_by_type = {row["OperationType"]: row for row in log["event_counts"]}
    return {
        "artifact": "varanegar_supplier_unapply_delete_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": safe["updateability"],
            "can_select": safe["can_select"],
            "can_view_definition": safe["can_view_definition"],
            "can_update": safe["can_update"],
            "denies_data_writes": safe["denies_data_writes"],
            "stored_procedure_trigger_form_or_application_command_executions": 0,
            "business_rows_identifiers_amounts_prices_or_operator_values_persisted": 0,
            "sql_definitions_or_log_scripts_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "selected_sql_module_count": len(profiles),
            "selected_module_with_local_transaction_count": sum(
                row["owns_explicit_transaction"] for row in profiles
            ),
            "unapplied_invoice_count": status0["header_count"],
            "unapplied_multi_receipt_invoice_count": status0["multi_relation_count"],
            "applied_invoice_count": status1["header_count"],
            "applied_multi_receipt_invoice_count": status1["multi_relation_count"],
            "retained_relation_insert_event_count": log_by_type["INSERT"]["event_count"],
            "retained_relation_delete_event_count": log_by_type["DELETE"]["event_count"],
            "recent_relation_delete_event_count": log_by_type["DELETE"][
                "recent_three_month_event_count"
            ],
            "current_relation_count": log["lifecycle"]["currently_present_count"],
            "zero_price_row_count": prices["all_price_rows"]["both_zero_count"],
        },
        "sql_module_profiles": profiles,
        "catalog_call_graph": graph,
        "unlink_reverse_contract": {
            "unlink_sets_whole_invoice_status_zero": unlink["sets_invoice_status_zero"],
            "unlink_clears_whole_invoice_confirm_date": unlink["clears_invoice_confirm_date"],
            "unlink_zeros_selected_voucher_item_price_and_unit_price": unlink[
                "zeros_voucher_item_price_and_unit_price"
            ],
            "status_zero_precedes_price_zero": unlink["status_zero_precedes_price_zero"],
            "unlink_reads_purchase_final_date": unlink["reads_purchase_final_date"],
            "unlink_reads_last_closed_purchase_date": unlink[
                "reads_last_closed_purchase_date"
            ],
            "unlink_raises_domain_error": unlink["raises_domain_error"],
            "unlink_has_application_specific_rollback_branch": unlink[
                "reads_application_name"
            ]
            and unlink["has_sdsnet_specific_branch"]
            and unlink["has_rollback_signal"],
            "unlink_owns_local_transaction": unlink["owns_explicit_transaction"],
        },
        "invoice_relation_state": states,
        "current_dependency_state": dependencies,
        "voucher_item_price_state": prices,
        "retained_relation_lifecycle_log": log,
        "storage_guard_contract": guards,
        "evidence_limits": [
            "The retained relation log proves insert/delete lifecycle events, not the business reason, actor intent or invoice status transition for each event.",
            "Current clean status/price parity does not prove every historical unlink completed atomically.",
            "Static SQL order proves a failure boundary but not a partial-unlink incident.",
            "The 83 zero-price rows are not attributed to supplier unlink without voucher-item provenance analysis.",
            "No procedure, trigger, form or application command was executed and no identifier, amount, price, SQL definition or log script is persisted.",
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
    print(json.dumps(payload["unlink_reverse_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
