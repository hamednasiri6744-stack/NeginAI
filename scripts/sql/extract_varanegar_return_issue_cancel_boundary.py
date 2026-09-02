"""Extract official sales-return issue/cancel state and SQL ownership read-only."""

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
    ("dbo", "usp_Sdsnet_RetSale_Save"),
    ("SLE", "usp_AfterSaveRetSale"),
    ("dbo", "USP_SDSNET_GenerateRetSaleVocher"),
    ("dbo", "USP_SDSNET_GenerateCancelRetSaleVocher"),
    ("SLE", "USP_SDSNET_CancelRetSaleHdr"),
    ("SLE", "USP_CreatePaymentFromRetSale"),
    ("SLE", "usp_CheckRetSaleAmountDiscount"),
    ("SLE", "trg_tblretsalehdr_UPD"),
    ("SLE", "trg_VN_Replication_tblRetSaleHdr_DELETE"),
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _code(definition: str) -> str:
    return " ".join(_executable_text(definition).replace("[", "").replace("]", "").casefold().split())


def _count(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code, re.I | re.S))


def _profiles(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    profiles, codes = [], {}
    for schema, name in MODULES:
        rows = _rows(cursor, """
          SELECT s.name schema_name,o.name object_name,o.object_id,o.type_desc,o.create_date,o.modify_date,
            CASE WHEN t.object_id IS NULL THEN NULL ELSE t.is_disabled END is_disabled,
            m.definition
          FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
          LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
          LEFT JOIN sys.triggers t ON t.object_id=o.object_id
          WHERE s.name=%s AND o.name=%s
        """, (schema, name))
        if len(rows) != 1:
            raise AssertionError({"missing_or_duplicate_module": f"{schema}.{name}"})
        row = rows[0]
        object_id, definition = row.pop("object_id"), row.pop("definition") or ""
        code, qualified = _code(definition), f"{schema}.{name}"
        codes[qualified] = code
        dependencies = _rows(cursor, """
          SELECT DISTINCT COALESCE(referenced_schema_name,'') referenced_schema,
            COALESCE(referenced_entity_name,'') referenced_entity
          FROM sys.sql_expression_dependencies WHERE referencing_id=%s
            AND referenced_entity_name IS NOT NULL ORDER BY referenced_schema,referenced_entity
        """, (object_id,))
        profiles.append({
            **row, "qualified_name": qualified, "definition_sha256": _sha(definition),
            "definition_character_count": len(definition), "dependency_count": len(dependencies),
            "dependencies": [".".join(x for x in (d["referenced_schema"], d["referenced_entity"]) if x)
                             for d in dependencies],
            "begin_transaction_signal_count": _count(code, r"\bbegin\s+(?:tran|transaction)\b"),
            "save_transaction_signal_count": _count(code, r"\bsave\s+transaction\b"),
            "commit_signal_count": _count(code, r"\bcommit\b"),
            "rollback_signal_count": _count(code, r"\brollback\b"),
            "try_catch_signal": "begin try" in code and "begin catch" in code,
            "raiserror_or_throw_signal_count": _count(code, r"\b(?:raiserror|throw)\b"),
            "insert_signal_count": _count(code, r"\binsert\b"),
            "update_signal_count": _count(code, r"\bupdate\b"),
            "delete_signal_count": _count(code, r"\bdelete\b"),
            "definition_or_literal_values_persisted": False,
        })
    return profiles, codes


def _current_state(cursor: Any) -> dict[str, Any]:
    by_cancel = _rows(cursor, """
      WITH v AS (
        SELECT DocRef,COUNT_BIG(*) voucher_count,
          SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirmed_count
        FROM INV.tblVocherHdr WHERE VocherTypeCode=10 AND DocRef IS NOT NULL GROUP BY DocRef
      ), p AS (SELECT RetSaleRef,COUNT_BIG(*) payment_count FROM Acc.tblPayments
        WHERE RetSaleRef IS NOT NULL GROUP BY RetSaleRef)
      SELECT h.CancelFlag,COUNT_BIG(*) return_count,
        SUM(CASE WHEN h.VocherFlag=1 THEN 1 ELSE 0 END) voucher_flag_one_count,
        SUM(CASE WHEN v.DocRef IS NOT NULL THEN 1 ELSE 0 END) with_type10_voucher_count,
        SUM(CASE WHEN COALESCE(v.voucher_count,0)>1 THEN 1 ELSE 0 END) multi_type10_voucher_count,
        SUM(COALESCE(v.confirmed_count,0)) confirmed_type10_voucher_count,
        SUM(CASE WHEN p.RetSaleRef IS NOT NULL THEN 1 ELSE 0 END) with_payment_count,
        SUM(COALESCE(p.payment_count,0)) payment_count,
        SUM(CASE WHEN h.DistRef IS NOT NULL THEN 1 ELSE 0 END) distribution_link_count,
        SUM(CASE WHEN h.TSaleRef IS NOT NULL THEN 1 ELSE 0 END) source_sale_link_count,
        SUM(CASE WHEN h.SaleSettlementRef IS NOT NULL THEN 1 ELSE 0 END) settlement_hint_count,
        SUM(CASE WHEN h.RetOrderRef IS NOT NULL THEN 1 ELSE 0 END) request_link_count,
        SUM(CASE WHEN h.RetSaleDate>='1405/03/01' AND h.RetSaleDate<='1405/05/31' THEN 1 ELSE 0 END)
          recent_business_date_count
      FROM SLE.tblRetSaleHdr h LEFT JOIN v ON v.DocRef=h.ID LEFT JOIN p ON p.RetSaleRef=h.ID
      GROUP BY h.CancelFlag ORDER BY h.CancelFlag
    """)
    voucher_integrity = _rows(cursor, """
      WITH v AS (SELECT DocRef,COUNT_BIG(*) voucher_count,
        SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirmed_count
        FROM INV.tblVocherHdr WHERE VocherTypeCode=10 AND DocRef IS NOT NULL GROUP BY DocRef)
      SELECT COUNT_BIG(*) current_type10_voucher_count,
        SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) voucher_without_current_return_count,
        SUM(CASE WHEN h.CancelFlag=1 THEN 1 ELSE 0 END) voucher_linked_cancelled_return_count,
        SUM(CASE WHEN h.CancelFlag=0 THEN 1 ELSE 0 END) voucher_linked_active_return_count,
        SUM(CASE WHEN h.CancelFlag=0 AND v.voucher_count<>1 THEN 1 ELSE 0 END) active_return_non_single_voucher_count,
        SUM(CASE WHEN h.CancelFlag=0 AND v.confirmed_count<>v.voucher_count THEN 1 ELSE 0 END)
          active_return_unconfirmed_voucher_count
      FROM v LEFT JOIN SLE.tblRetSaleHdr h ON h.ID=v.DocRef
    """)[0]
    return {"by_cancel_flag": by_cancel, "voucher_integrity": voucher_integrity}


def _general_log(cursor: Any) -> dict[str, Any]:
    operations = _rows(cursor, """
      SELECT OperationType,COUNT_BIG(*) event_count,COUNT(DISTINCT OperationId) id_count,
        SUM(CASE WHEN TransDate>='20260601' AND TransDate<'20260901' THEN 1 ELSE 0 END) recent_event_count,
        MIN(TransDate) first_event_date,MAX(TransDate) last_event_date
      FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
      WHERE OperationTable='SLE.tblRetSaleHdr' GROUP BY OperationType ORDER BY OperationType
    """)
    coverage = _rows(cursor, """
      WITH l AS (
        SELECT OperationId,SUM(CASE WHEN OperationType='DELETE' THEN 1 ELSE 0 END) del,
          MIN(TransDate) first_log,MAX(TransDate) last_log
        FROM GNR.tblLog WITH (INDEX(IX_NC_tbllog_OperationTable_OperationId_Id))
        WHERE OperationTable='SLE.tblRetSaleHdr' GROUP BY OperationId
      )
      SELECT COUNT_BIG(*) logged_return_count,
        SUM(CASE WHEN h.ID IS NOT NULL THEN 1 ELSE 0 END) current_count,
        SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) absent_count,
        SUM(CASE WHEN h.ID IS NULL AND del>0 THEN 1 ELSE 0 END) absent_with_delete_count,
        SUM(CASE WHEN h.ID IS NULL AND del=0 THEN 1 ELSE 0 END) absent_without_delete_count,
        SUM(CASE WHEN h.ID IS NULL AND last_log>='20260601' AND last_log<'20260901' THEN 1 ELSE 0 END)
          recent_absent_count,MIN(CASE WHEN h.ID IS NULL THEN first_log END) absent_first_log_date,
        MAX(CASE WHEN h.ID IS NULL THEN last_log END) absent_last_log_date
      FROM l LEFT JOIN SLE.tblRetSaleHdr h ON h.ID=l.OperationId
    """)[0]
    return {"operation_counts": operations, "logged_id_coverage": coverage}


def _direct_delete_candidates(cursor: Any) -> list[dict[str, Any]]:
    rows = _rows(cursor, """
      SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition
      FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
      JOIN sys.schemas s ON s.schema_id=o.schema_id WHERE m.definition LIKE '%tblRetSaleHdr%'
    """)
    result = []
    for row in rows:
        definition, code = row.pop("definition") or "", ""
        code = _code(definition)
        if not re.search(r"\bdelete\s+(?:from\s+)?(?:sle\.)?tblretsalehdr\b", code):
            continue
        result.append({**row, "qualified_name": f"{row['schema_name']}.{row['object_name']}",
                       "definition_sha256": _sha(definition),
                       "begin_transaction_signal_count": _count(code, r"\bbegin\s+(?:tran|transaction)\b"),
                       "save_transaction_signal_count": _count(code, r"\bsave\s+transaction\b"),
                       "commit_signal_count": _count(code, r"\bcommit\b"),
                       "rollback_signal_count": _count(code, r"\brollback\b"),
                       "replication_mode_bypass_signal": "ufn_isreplicationmode" in code and "return" in code,
                       "definition_or_literal_values_persisted": False})
    return sorted(result, key=lambda x: x["qualified_name"].casefold())


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safe = _assert_safe_target(cursor)
        profiles, codes = _profiles(cursor)
        state, audit, deletes = _current_state(cursor), _general_log(cursor), _direct_delete_candidates(cursor)
    finally:
        connection.close()
    generate = codes["dbo.USP_SDSNET_GenerateRetSaleVocher"]
    cancel_voucher = codes["dbo.USP_SDSNET_GenerateCancelRetSaleVocher"]
    cancel_header = codes["SLE.USP_SDSNET_CancelRetSaleHdr"]
    save = codes["dbo.usp_Sdsnet_RetSale_Save"]
    after = codes["SLE.usp_AfterSaveRetSale"]
    replication_delete = codes["SLE.trg_VN_Replication_tblRetSaleHdr_DELETE"]
    active = next(x for x in state["by_cancel_flag"] if x["CancelFlag"] == 0)
    cancelled = next(x for x in state["by_cancel_flag"] if x["CancelFlag"] == 1)
    operations = {x["OperationType"]: x for x in audit["operation_counts"]}
    return {
        "artifact": "varanegar_return_issue_cancel_boundary", "schema_version": 1,
        "generated_at": datetime.now().astimezone(), "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {"mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_RETURN_AGGREGATES",
                   "database_updateability": safe["updateability"], "can_select": safe["can_select"],
                   "can_view_definition": safe["can_view_definition"], "can_update": safe["can_update"],
                   "denies_data_writes": safe["denies_data_writes"],
                   "stored_procedure_trigger_form_or_application_command_executions": 0,
                   "return_sale_voucher_payment_customer_user_host_or_raw_values_persisted": 0,
                   "sql_definitions_error_texts_or_business_identifiers_persisted": 0,
                   "source_or_target_state_changed": 0},
        "summary": {"selected_sql_module_count": len(profiles),
                    "active_return_count": active["return_count"], "cancelled_return_count": cancelled["return_count"],
                    "active_return_with_type10_voucher_count": active["with_type10_voucher_count"],
                    "cancelled_return_with_type10_voucher_count": cancelled["with_type10_voucher_count"],
                    "cancelled_return_with_payment_count": cancelled["with_payment_count"],
                    "recent_cancelled_return_count": cancelled["recent_business_date_count"],
                    "current_type10_voucher_count": state["voucher_integrity"]["current_type10_voucher_count"],
                    "direct_physical_return_delete_candidate_count": len(deletes),
                    "retained_return_delete_log_count": operations.get("DELETE", {"event_count": 0})["event_count"],
                    "logged_return_absent_count": audit["logged_id_coverage"]["absent_count"]},
        "sql_module_profiles": profiles,
        "static_issue_cancel_contract": {
            "save_has_local_transaction_try_catch_commit_and_rollback": all(x in save for x in ("begin transaction","begin try","begin catch","commit","rollback")),
            "save_orchestrates_issue_cancel_header_and_cancel_voucher_routes": all(
                x in save for x in ("generateretsalevocher", "generatecancelretsalevocher", "cancelretsalehdr")
            ),
            "save_can_delete_return_payments_and_voucher_graph": all(
                x in save for x in ("tblpayments", "tblvocherhdr", "tblvocheritm")
            ) and _count(save, r"\bdelete\b") > 0,
            "after_save_has_no_local_transaction_but_can_rollback": not bool(
                re.search(r"\bbegin\s+(?:tran|transaction)\b|\bsave\s+transaction\b", after)
            ) and "rollback" in after,
            "generate_has_transaction_or_savepoint_commit_and_rollback": ("begin transaction" in generate or "save transaction" in generate) and "commit" in generate and "rollback" in generate,
            "generate_inserts_type10_voucher_updates_flag_and_can_create_payment": all(x in generate for x in ("tblvocherhdr","tblvocheritm","vocherflag","createpaymentfromretsale")),
            "generate_performs_some_validation_after_voucher_inserts": generate.find("insert into inv.tblvocherhdr") >= 0 and generate.rfind("raiserror") > generate.find("insert into inv.tblvocherhdr"),
            "cancel_voucher_has_local_transaction_try_catch_commit_and_rollback": bool(
                re.search(r"\bbegin\s+(?:tran|transaction)\b", cancel_voucher)
            ) and all(x in cancel_voucher for x in ("begin try", "begin catch", "commit", "rollback")),
            "cancel_voucher_mutates_voucher_graph_and_checks_stock": all(
                x in cancel_voucher for x in ("tblvocherhdr", "tblvocheritm", "checkstockgoodsqty")
            ) and _count(cancel_voucher, r"\bdelete\b") > 0 and _count(cancel_voucher, r"\binsert\b") > 0,
            "cancel_header_updates_cancel_flag_and_removes_payment_relation": all(
                x in cancel_header for x in ("cancelflag", "tblpaywithpaymentrelation")
            ) and _count(cancel_header, r"\bupdate\b") > 0,
            "replication_delete_trigger_is_bypassable": "ufn_isreplicationmode" in replication_delete and "return" in replication_delete,
        },
        "current_return_state": state, "generic_return_log_lifecycle": audit,
        "direct_physical_return_delete_candidates": deletes,
        "evidence_limits": [
            "Static SQL proves capability and textual ordering, not the runtime branch, caller, success or causal attribution.",
            "Current voucher and payment cleanup is consistent with cancellation rules but does not prove every historical cancellation used one procedure.",
            "A direct-delete candidate proves capability, not attribution of an absent return.",
            "No procedure, trigger, form or command was executed and no return, sale, voucher, payment, customer, user, host, error text or raw identifier was persisted.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True, type=Path); args = parser.parse_args()
    payload = collect(); args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default)+"\n", encoding="utf-8")
    print(args.output.resolve()); print(json.dumps(payload["summary"], ensure_ascii=False)); print(json.dumps(payload["static_issue_cancel_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
