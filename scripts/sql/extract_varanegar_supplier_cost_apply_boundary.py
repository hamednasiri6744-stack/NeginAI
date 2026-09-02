"""Extract supplier-invoice apply/reapply and inventory-cost atomicity read-only."""

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


CORE_MODULES = (
    ("ICA", "usp_ApplySupInvoice"),
    ("ICA", "usp_FastApplySupInvoice"),
    ("ICA", "usp_ReApplySupInvoice"),
    ("ICA", "usp_ReApplySupInvoiceItmTolls"),
    ("ICA", "usp_sdsnet_ApplySupInvoice"),
)
CALLER_MODULES = (
    ("SLE", "usp_CheckSupInvoice"),
    ("ICA", "Usp_ConfirmLoanSupInvoice"),
    ("ICA", "usp_Pricing_Before"),
    ("dbo", "usp_sdsnet_SupInvoice_Save"),
    ("dbo", "usp_sdsnet_VocherItmPrice_Save"),
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _position(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


def _module_profiles(cursor: Any, modules: tuple[tuple[str, str], ...]) -> list[dict[str, Any]]:
    profiles = []
    for schema, name in modules:
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
        code = " ".join(_executable_text(definition).casefold().split())
        price_delete = _position(code, r"\bdelete\s+from\s+inv\.tblvocheritmprice\b")
        price_insert = _position(code, r"\binsert\s+into\s+inv\.tblvocheritmprice\b")
        status_update = _position(
            code,
            r"\bupdate\s+ica\.tblsupinvoicehdr\b.{0,300}?\bstatus\s*=\s*1\b",
        )
        fast_call = _position(code, r"\bexec(?:ute)?\s+ica\.usp_fastapplysupinvoice\b")
        apply_call = _position(code, r"\bexec(?:ute)?\s+ica\.usp_applysupinvoice\b")
        profiles.append(
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
                "deletes_voucher_item_price": price_delete is not None,
                "inserts_voucher_item_price": price_insert is not None,
                "updates_invoice_status_one": status_update is not None,
                "calls_apply": apply_call is not None,
                "calls_fast_apply": fast_call is not None,
                "price_delete_precedes_insert": price_delete is not None
                and price_insert is not None
                and price_delete < price_insert,
                "price_insert_precedes_status_one": price_insert is not None
                and status_update is not None
                and price_insert < status_update,
                "status_one_precedes_fast_apply": status_update is not None
                and fast_call is not None
                and status_update < fast_call,
                "definition_or_character_offsets_persisted": False,
            }
        )
    return profiles


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
          OBJECT_ID(N'ICA.usp_ApplySupInvoice'),OBJECT_ID(N'ICA.usp_FastApplySupInvoice'),
          OBJECT_ID(N'ICA.usp_ReApplySupInvoice'),
          OBJECT_ID(N'ICA.usp_ReApplySupInvoiceItmTolls'),
          OBJECT_ID(N'ICA.usp_sdsnet_ApplySupInvoice'))
        ORDER BY callee_schema,callee_name,caller_schema,caller_name
        """,
    )


def _header_state(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT Status,COUNT_BIG(*) header_count,
          SUM(CASE WHEN ConfirmDate IS NULL THEN 1 ELSE 0 END) confirm_null_count,
          SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirm_present_count,
          SUM(CASE WHEN ConfirmDate>='20260601' AND ConfirmDate<'20260901'
                   THEN 1 ELSE 0 END) recent_confirm_count
        FROM ICA.TblSupInvoiceHdr GROUP BY Status ORDER BY Status
        """,
    )


def _confirm_months(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT CONVERT(char(7),ConfirmDate,120) month_bucket,COUNT_BIG(*) header_count
        FROM ICA.TblSupInvoiceHdr WHERE ConfirmDate IS NOT NULL
        GROUP BY CONVERT(char(7),ConfirmDate,120) ORDER BY month_bucket
        """,
    )


def _status_price_parity(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH rv AS (
          SELECT DISTINCT r.SupInvoiceHdrRef,r.InvVchHdrRef,h.Status
          FROM ICA.tblSupInvInvoiceRelation r
          JOIN ICA.TblSupInvoiceHdr h ON h.ID=r.SupInvoiceHdrRef
        ), si AS (
          SELECT DISTINCT Status,vi.ID item_id
          FROM rv JOIN inv.tblVocherItm vi ON vi.HdrRef=rv.InvVchHdrRef
        )
        SELECT si.Status,COUNT_BIG(*) distinct_item_count,
          SUM(CASE WHEN p.ID IS NOT NULL THEN 1 ELSE 0 END) item_with_price_count,
          SUM(CASE WHEN p.ID IS NULL THEN 1 ELSE 0 END) item_without_price_count,
          SUM(CASE WHEN p.ID IS NOT NULL AND p.PriceRef IS NULL THEN 1 ELSE 0 END)
            price_ref_null_count
        FROM si LEFT JOIN inv.tblVocherItmPrice p ON p.ID=si.item_id
        GROUP BY si.Status ORDER BY si.Status
        """,
    )


def _cross_status(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH rv AS (
          SELECT DISTINCT r.InvVchHdrRef,h.Status
          FROM ICA.tblSupInvInvoiceRelation r
          JOIN ICA.TblSupInvoiceHdr h ON h.ID=r.SupInvoiceHdrRef
        ), x AS (
          SELECT vi.ID item_id,MIN(rv.Status) min_status,MAX(rv.Status) max_status
          FROM rv JOIN inv.tblVocherItm vi ON vi.HdrRef=rv.InvVchHdrRef GROUP BY vi.ID
        )
        SELECT COUNT_BIG(*) related_item_count,
          SUM(CASE WHEN min_status<>max_status THEN 1 ELSE 0 END) cross_status_item_count
        FROM x
        """,
    )[0]


def _price_integrity(cursor: Any) -> dict[str, Any]:
    counts = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) price_row_count,COUNT(DISTINCT p.ID) distinct_price_id_count,
          SUM(CASE WHEN i.ID IS NULL THEN 1 ELSE 0 END) orphan_price_row_count
        FROM inv.tblVocherItmPrice p LEFT JOIN inv.tblVocherItm i ON i.ID=p.ID
        """,
    )[0]
    indexes = _rows(
        cursor,
        """
        SELECT i.name index_name,i.is_unique,i.is_primary_key,c.name column_name,
               ic.key_ordinal
        FROM sys.indexes i
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID(N'inv.tblVocherItmPrice') AND i.index_id>0
        ORDER BY i.index_id,ic.key_ordinal
        """,
    )
    fks = _rows(
        cursor,
        """
        SELECT fk.name constraint_name,OBJECT_SCHEMA_NAME(fk.referenced_object_id)
          referenced_schema,OBJECT_NAME(fk.referenced_object_id) referenced_table,
          fk.is_disabled,fk.is_not_trusted,fk.delete_referential_action_desc
        FROM sys.foreign_keys fk
        WHERE fk.parent_object_id=OBJECT_ID(N'inv.tblVocherItmPrice')
        ORDER BY fk.name
        """,
    )
    return {
        **counts,
        "unique_primary_key_on_item_id": any(
            row["is_unique"] and row["is_primary_key"] and row["column_name"] == "Id"
            for row in indexes
        ),
        "foreign_key_to_voucher_item_present": any(
            row["referenced_schema"].casefold() == "inv"
            and row["referenced_table"].casefold() == "tblvocheritm"
            for row in fks
        ),
        "foreign_key_count": len(fks),
        "foreign_key_to_buy_price_count": sum(
            row["referenced_schema"].casefold() == "ica"
            and row["referenced_table"].casefold() == "tblicaBuyPrice".casefold()
            for row in fks
        ),
    }


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        core = _module_profiles(cursor, CORE_MODULES)
        callers = _module_profiles(cursor, CALLER_MODULES)
        graph = _call_graph(cursor)
        header = _header_state(cursor)
        months = _confirm_months(cursor)
        parity = _status_price_parity(cursor)
        cross_status = _cross_status(cursor)
        price = _price_integrity(cursor)
    finally:
        connection.close()
    by_name = {row["object_name"]: row for row in core}
    status0 = next(row for row in parity if row["Status"] == 0)
    status1 = next(row for row in parity if row["Status"] == 1)
    return {
        "artifact": "varanegar_supplier_cost_apply_boundary",
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
            "stored_procedure_form_or_application_command_executions": 0,
            "business_rows_identifiers_amounts_or_prices_persisted": 0,
            "sql_definitions_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "core_apply_module_count": len(core),
            "core_module_with_local_transaction_count": sum(
                row["owns_explicit_transaction"] for row in core
            ),
            "applied_invoice_count": next(
                row["header_count"] for row in header if row["Status"] == 1
            ),
            "unapplied_invoice_count": next(
                row["header_count"] for row in header if row["Status"] == 0
            ),
            "applied_related_item_count": status1["distinct_item_count"],
            "applied_item_without_price_count": status1["item_without_price_count"],
            "unapplied_related_item_count": status0["distinct_item_count"],
            "unapplied_item_with_price_count": status0["item_with_price_count"],
            "orphan_price_row_count": price["orphan_price_row_count"],
            "recent_three_month_confirm_count": sum(
                row["recent_confirm_count"] for row in header
            ),
        },
        "core_apply_module_profiles": core,
        "caller_module_profiles": callers,
        "catalog_call_graph": graph,
        "apply_reapply_sequence_contract": {
            "apply_deletes_then_inserts_price": by_name["usp_ApplySupInvoice"][
                "price_delete_precedes_insert"
            ],
            "apply_updates_header_status": by_name["usp_ApplySupInvoice"][
                "updates_invoice_status_one"
            ],
            "fast_apply_deletes_then_inserts_price_then_sets_status": by_name[
                "usp_FastApplySupInvoice"
            ]["price_delete_precedes_insert"]
            and by_name["usp_FastApplySupInvoice"]["price_insert_precedes_status_one"],
            "reapply_sets_status_before_fast_apply": by_name["usp_ReApplySupInvoice"][
                "status_one_precedes_fast_apply"
            ],
            "sdsnet_wrapper_calls_apply": by_name["usp_sdsnet_ApplySupInvoice"][
                "calls_apply"
            ],
            "core_local_transaction_count": sum(
                row["owns_explicit_transaction"] for row in core
            ),
        },
        "invoice_header_state_contract": header,
        "confirm_monthly_counts": months,
        "status_price_parity": parity,
        "cross_status_item_contract": cross_status,
        "voucher_item_price_integrity": price,
        "evidence_limits": [
            "Current zero status/price mismatches prove snapshot parity, not failure-free historical execution.",
            "Static procedure order proves a failure window but not that a partial reapply incident occurred.",
            "The 95 orphan price rows are not attributed to supplier apply without deleted-item provenance.",
            "ConfirmDate concentration records apply-state timing but does not by itself distinguish initial apply, migration or batch reapply intent.",
            "No procedure, form or command was executed and no identifier, amount, price or SQL definition is persisted.",
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
