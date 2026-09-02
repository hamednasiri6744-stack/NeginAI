"""Extract stock-voucher confirm, unconfirm and delete state boundaries read-only."""

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
    ("dbo", "USP_SDSNET_ConfirmVocher"),
    ("dbo", "USP_SDSNET_ConfirmVocherValidation"),
    ("dbo", "USP_SDSNET_UnConfirmVocher"),
    ("dbo", "USP_SDSNET_UnConfirmVocherValidation"),
    ("dbo", "usp_sdsnet_Vocher_Save"),
    ("inv", "AfterInvVocherHdr"),
    ("inv", "trg_tblVocherHdr_UpdateStockGoods"),
    ("inv", "trg_tblVocherItm_UpdateStockGoods"),
    ("inv", "trg_tblVocherHdr_ToVocherHdrLog_IU"),
    ("inv", "trg_tblVocherHdr_ToVocherHdrLog_D"),
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pos(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


def _count(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code, re.I | re.S))


def _profiles(cursor: Any) -> list[dict[str, Any]]:
    profiles = []
    for schema, name in MODULES:
        row = _rows(
            cursor,
            """
            SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,m.definition
            FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
            LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
            WHERE s.name=%s AND o.name=%s
            """,
            (schema, name),
        )[0]
        definition = row.pop("definition") or ""
        code = " ".join(
            _executable_text(definition).replace("[", "").replace("]", "").casefold().split()
        )
        begin_tx = _pos(code, r"\bbegin\s+(?:tran|transaction)\b")
        commit = _pos(code, r"\bcommit\b")
        confirm_update = _pos(
            code,
            r"\bupdate\s+(?:inv\.)?tblvocherhdr\s+set\s+confirmdate\s*=\s*(?:getdate\(\)|@\w+)",
        )
        unconfirm_update = _pos(
            code,
            r"\bupdate\s+(?:inv\.)?tblvocherhdr\s+set\s+confirmdate\s*=\s*null",
        )
        validation_call = _pos(
            code,
            r"\b(?:exec|execute)\s+(?:dbo\.)?usp_sdsnet_(?:un)?confirmvochervalidation\b",
        )
        after_hook = _pos(code, r"\b(?:exec|execute)\s+(?:inv\.)?afterinvvocherhdr\b")
        profiles.append(
            {
                **row,
                "qualified_name": f"{schema}.{name}",
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "owns_explicit_transaction_or_savepoint": begin_tx is not None,
                "begin_transaction_signal_count": _count(
                    code, r"\bbegin\s+(?:tran|transaction)\b"
                ),
                "save_transaction_signal_count": _count(code, r"\bsave\s+transaction\b"),
                "commit_signal_count": _count(code, r"\bcommit\b"),
                "rollback_signal_count": _count(code, r"\brollback\b"),
                "has_try_catch": "begin try" in code and "begin catch" in code,
                "uses_cursor_signal": bool(re.search(r"\bdeclare\s+\w+\s+cursor\b", code)),
                "calls_validation": validation_call is not None,
                "validation_precedes_transaction": validation_call is not None
                and begin_tx is not None
                and validation_call < begin_tx,
                "sets_confirm_date_nonnull": confirm_update is not None,
                "sets_confirm_date_null": unconfirm_update is not None,
                "calls_after_inventory_hook": after_hook is not None,
                "first_commit_precedes_after_hook": commit is not None
                and after_hook is not None
                and commit < after_hook,
                "after_hook_precedes_first_commit": after_hook is not None
                and commit is not None
                and after_hook < commit,
                "calls_confirm_procedure": bool(
                    re.search(
                        r"\b(?:exec|execute)\s+(?:dbo\.)?usp_sdsnet_confirmvocher\b",
                        code,
                    )
                ),
                "deletes_voucher_detail": bool(
                    re.search(r"\bdelete\b.*?\binv\.tblvocheritmdetail\b", code, re.I | re.S)
                ),
                "deletes_voucher_item": bool(
                    re.search(r"\bdelete\b.*?\binv\.tblvocheritm\b", code, re.I | re.S)
                ),
                "deletes_voucher_header": bool(
                    re.search(r"\bdelete\b.*?\binv\.tblvocherhdr\b", code, re.I | re.S)
                ),
                "references_inserted_and_deleted": " inserted " in f" {code} "
                and " deleted " in f" {code} ",
                "references_stock_projection": "tblstockgoods" in code,
                "replication_mode_bypass_signal": "ufn_isreplicationmode" in code
                and bool(re.search(r"\breturn\b", code)),
                "xact_abort_off_signal": "set xact_abort off" in code,
                "skips_special_voucher_type_signal": all(
                    token in code for token in ("60", "21", "64", "65")
                ),
                "writes_domain_audit_log": "insert into inv.tblvocherhdrlog" in code,
                "suppresses_confirmed_date_only_audit_signal": bool(
                    re.search(r"confirmdate\s+is\s+not\s+null", code)
                    and "vocherdate" in code
                    and "return" in code
                ),
                "definition_or_offsets_persisted": False,
            }
        )
    return profiles


def _current(cursor: Any) -> dict[str, Any]:
    aggregate = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) voucher_count,
          SUM(CASE WHEN ConfirmDate IS NULL THEN 1 ELSE 0 END) unconfirmed_count,
          SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirmed_count,
          (SELECT COUNT_BIG(*) FROM inv.tblVocherItm) item_count,
          (SELECT COUNT_BIG(*) FROM inv.tblVocherItmDetail) detail_count,
          (SELECT COUNT_BIG(*) FROM GNR.tblStockGoods) stock_projection_row_count
        FROM inv.tblVocherHdr
        """,
    )[0]
    by_type = _rows(
        cursor,
        """
        SELECT VocherTypeCode,COUNT_BIG(*) current_count,
          SUM(CASE WHEN ConfirmDate IS NULL THEN 1 ELSE 0 END) unconfirmed_count,
          SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) confirmed_count
        FROM inv.tblVocherHdr GROUP BY VocherTypeCode ORDER BY VocherTypeCode
        """,
    )
    return {"aggregate": aggregate, "by_voucher_type": by_type}


def _audit(cursor: Any) -> dict[str, Any]:
    operations = _rows(
        cursor,
        """
        SELECT OperationType,COUNT_BIG(*) event_count,COUNT(DISTINCT VocherHdrRef) voucher_count,
          SUM(CASE WHEN ModifiedDate>='20260601' AND ModifiedDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_event_count,MIN(ModifiedDate) first_event_date,
          MAX(ModifiedDate) last_event_date,
          SUM(CASE WHEN ConfirmDate IS NULL THEN 1 ELSE 0 END) null_confirm_date_count,
          SUM(CASE WHEN ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) nonnull_confirm_date_count
        FROM inv.tblVocherHdrLog GROUP BY OperationType ORDER BY OperationType
        """,
    )
    transitions = _rows(
        cursor,
        """
        WITH x AS (
          SELECT ID,VocherHdrRef,OperationType,ModifiedDate,ConfirmDate,
            LAG(ConfirmDate) OVER(PARTITION BY VocherHdrRef ORDER BY ID) previous_confirm_date
          FROM inv.tblVocherHdrLog
        ), y AS (
          SELECT ModifiedDate,CASE
            WHEN OperationType='U' AND previous_confirm_date IS NULL AND ConfirmDate IS NOT NULL
              THEN 'CONFIRM'
            WHEN OperationType='U' AND previous_confirm_date IS NOT NULL AND ConfirmDate IS NULL
              THEN 'UNCONFIRM'
            WHEN OperationType='U' AND previous_confirm_date IS NULL AND ConfirmDate IS NULL
              THEN 'DRAFT_UPDATE'
            WHEN OperationType='U' AND previous_confirm_date IS NOT NULL AND ConfirmDate IS NOT NULL
              THEN 'CONFIRMED_UPDATE'
            ELSE OperationType END transition_shape
          FROM x
        )
        SELECT transition_shape,COUNT_BIG(*) event_count,
          SUM(CASE WHEN ModifiedDate>='20260601' AND ModifiedDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_event_count,MIN(ModifiedDate) first_event_date,
          MAX(ModifiedDate) last_event_date
        FROM y GROUP BY transition_shape ORDER BY transition_shape
        """,
    )
    delete_lifecycle = _rows(
        cursor,
        """
        WITH x AS (
          SELECT ID,VocherHdrRef,OperationType,ModifiedDate,ConfirmDate,
            LAG(ConfirmDate) OVER(PARTITION BY VocherHdrRef ORDER BY ID) previous_confirm_date
          FROM inv.tblVocherHdrLog
        ), e AS (
          SELECT *,CASE
            WHEN OperationType='U' AND previous_confirm_date IS NULL AND ConfirmDate IS NOT NULL
              THEN 'CONFIRM'
            WHEN OperationType='U' AND previous_confirm_date IS NOT NULL AND ConfirmDate IS NULL
              THEN 'UNCONFIRM'
            ELSE OperationType END transition_shape
          FROM x
        ), z AS (
          SELECT *,LAG(transition_shape) OVER(PARTITION BY VocherHdrRef ORDER BY ID)
              previous_transition_shape,
            MAX(CASE WHEN transition_shape='CONFIRM' THEN 1 ELSE 0 END)
              OVER(PARTITION BY VocherHdrRef) had_confirm,
            MAX(CASE WHEN transition_shape='UNCONFIRM' THEN 1 ELSE 0 END)
              OVER(PARTITION BY VocherHdrRef) had_unconfirm
          FROM e
        ), d AS (
          SELECT ModifiedDate,CASE
            WHEN previous_transition_shape='UNCONFIRM' THEN 'IMMEDIATE_UNCONFIRM_DELETE'
            WHEN had_unconfirm=1 THEN 'PRIOR_UNCONFIRM_DELETE'
            WHEN had_confirm=1 THEN 'PRIOR_CONFIRM_NO_UNCONFIRM_DELETE'
            ELSE 'NEVER_CONFIRMED_DELETE' END delete_shape
          FROM z WHERE OperationType='D'
        )
        SELECT delete_shape,COUNT_BIG(*) delete_count,
          SUM(CASE WHEN ModifiedDate>='20260601' AND ModifiedDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_count
        FROM d GROUP BY delete_shape ORDER BY delete_shape
        """,
    )
    coverage = _rows(
        cursor,
        """
        WITH l AS (
          SELECT VocherHdrRef,
            SUM(CASE WHEN OperationType='I' THEN 1 ELSE 0 END) insert_count,
            SUM(CASE WHEN OperationType='D' THEN 1 ELSE 0 END) delete_count
          FROM inv.tblVocherHdrLog GROUP BY VocherHdrRef
        )
        SELECT COUNT_BIG(*) logged_voucher_count,
          SUM(CASE WHEN h.ID IS NOT NULL THEN 1 ELSE 0 END) currently_present_count,
          SUM(CASE WHEN h.ID IS NULL THEN 1 ELSE 0 END) currently_absent_count,
          SUM(CASE WHEN insert_count>0 AND delete_count>0 THEN 1 ELSE 0 END) both_event_count,
          SUM(CASE WHEN insert_count=0 AND delete_count>0 THEN 1 ELSE 0 END) delete_only_count,
          SUM(CASE WHEN insert_count>0 AND delete_count=0 AND h.ID IS NULL THEN 1 ELSE 0 END)
            insert_only_but_absent_count,
          SUM(CASE WHEN delete_count>0 AND h.ID IS NOT NULL THEN 1 ELSE 0 END)
            deleted_but_present_count
        FROM l LEFT JOIN inv.tblVocherHdr h ON h.ID=l.VocherHdrRef
        """,
    )[0]
    gap = _rows(
        cursor,
        """
        WITH i AS (
          SELECT VocherHdrRef,MIN(ModifiedDate) first_insert,MAX(ModifiedDate) last_insert
          FROM inv.tblVocherHdrLog WHERE OperationType='I' GROUP BY VocherHdrRef
        ), d AS (
          SELECT DISTINCT VocherHdrRef FROM inv.tblVocherHdrLog WHERE OperationType='D'
        )
        SELECT COUNT_BIG(*) insert_logged_absent_without_delete_count,
          MIN(first_insert) first_insert_date,MAX(last_insert) last_insert_date,
          DATEDIFF(millisecond,MIN(first_insert),MAX(last_insert)) spread_milliseconds,
          SUM(CASE WHEN last_insert>='20260601' AND last_insert<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_count
        FROM i LEFT JOIN d ON d.VocherHdrRef=i.VocherHdrRef
        LEFT JOIN inv.tblVocherHdr h ON h.ID=i.VocherHdrRef
        WHERE h.ID IS NULL AND d.VocherHdrRef IS NULL
        """,
    )[0]
    type_activity = _rows(
        cursor,
        """
        WITH x AS (
          SELECT ID,VocherHdrRef,VocherTypeCode,OperationType,ModifiedDate,ConfirmDate,
            LAG(ConfirmDate) OVER(PARTITION BY VocherHdrRef ORDER BY ID) previous_confirm_date
          FROM inv.tblVocherHdrLog
        ), e AS (
          SELECT *,CASE
            WHEN OperationType='U' AND previous_confirm_date IS NULL AND ConfirmDate IS NOT NULL
              THEN 'CONFIRM'
            WHEN OperationType='U' AND previous_confirm_date IS NOT NULL AND ConfirmDate IS NULL
              THEN 'UNCONFIRM'
            ELSE OperationType END transition_shape
          FROM x
        )
        SELECT VocherTypeCode,transition_shape,COUNT_BIG(*) event_count,
          SUM(CASE WHEN ModifiedDate>='20260601' AND ModifiedDate<'20260901' THEN 1 ELSE 0 END)
            recent_three_month_count
        FROM e WHERE transition_shape IN ('CONFIRM','UNCONFIRM','D')
        GROUP BY VocherTypeCode,transition_shape
        HAVING SUM(CASE WHEN ModifiedDate>='20260601' AND ModifiedDate<'20260901'
          THEN 1 ELSE 0 END)>0
        ORDER BY recent_three_month_count DESC,VocherTypeCode,transition_shape
        """,
    )
    return {
        "operation_counts": operations,
        "derived_transition_counts": transitions,
        "delete_lifecycle_counts": delete_lifecycle,
        "logged_voucher_coverage": coverage,
        "insert_logged_absent_without_delete_batch": gap,
        "recent_activity_by_voucher_type": type_activity,
    }


def _storage(cursor: Any) -> dict[str, Any]:
    tables = _rows(
        cursor,
        """
        SELECT s.name schema_name,t.name table_name,t.temporal_type_desc,t.is_tracked_by_cdc,
          CASE WHEN ct.object_id IS NULL THEN 0 ELSE 1 END change_tracking_enabled
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        LEFT JOIN sys.change_tracking_tables ct ON ct.object_id=t.object_id
        WHERE t.object_id IN (OBJECT_ID(N'inv.tblVocherHdr'),OBJECT_ID(N'inv.tblVocherItm'),
          OBJECT_ID(N'inv.tblVocherItmDetail'),OBJECT_ID(N'inv.tblVocherHdrLog'),
          OBJECT_ID(N'GNR.tblStockGoods'))
        ORDER BY s.name,t.name
        """,
    )
    triggers = _rows(
        cursor,
        """
        SELECT ps.name schema_name,po.name parent_name,t.name trigger_name,t.is_disabled,
          t.is_instead_of_trigger
        FROM sys.triggers t JOIN sys.objects po ON po.object_id=t.parent_id
        JOIN sys.schemas ps ON ps.schema_id=po.schema_id
        WHERE t.parent_id IN (OBJECT_ID(N'inv.tblVocherHdr'),OBJECT_ID(N'inv.tblVocherItm'),
          OBJECT_ID(N'inv.tblVocherItmDetail'))
        ORDER BY ps.name,po.name,t.name
        """,
    )
    return {"table_capabilities": tables, "active_triggers": triggers}


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safe = _assert_safe_target(cursor)
        profiles = _profiles(cursor)
        current = _current(cursor)
        audit = _audit(cursor)
        storage = _storage(cursor)
    finally:
        connection.close()

    by_name = {row["qualified_name"]: row for row in profiles}
    confirm = by_name["dbo.USP_SDSNET_ConfirmVocher"]
    unconfirm = by_name["dbo.USP_SDSNET_UnConfirmVocher"]
    save = by_name["dbo.usp_sdsnet_Vocher_Save"]
    header_trigger = by_name["inv.trg_tblVocherHdr_UpdateStockGoods"]
    item_trigger = by_name["inv.trg_tblVocherItm_UpdateStockGoods"]
    audit_iu = by_name["inv.trg_tblVocherHdr_ToVocherHdrLog_IU"]
    audit_d = by_name["inv.trg_tblVocherHdr_ToVocherHdrLog_D"]
    transitions = {
        row["transition_shape"]: row for row in audit["derived_transition_counts"]
    }
    delete_shapes = {
        row["delete_shape"]: row for row in audit["delete_lifecycle_counts"]
    }
    operations = {row["OperationType"]: row for row in audit["operation_counts"]}
    return {
        "artifact": "varanegar_stock_voucher_state_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AUDIT_AGGREGATES",
            "database_updateability": safe["updateability"],
            "can_select": safe["can_select"],
            "can_view_definition": safe["can_view_definition"],
            "can_update": safe["can_update"],
            "denies_data_writes": safe["denies_data_writes"],
            "stored_procedure_trigger_form_or_application_command_executions": 0,
            "voucher_goods_stock_supplier_document_comment_user_host_or_log_row_values_persisted": 0,
            "sql_definitions_or_business_identifiers_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "selected_sql_module_count": len(profiles),
            "current_voucher_count": current["aggregate"]["voucher_count"],
            "current_confirmed_voucher_count": current["aggregate"]["confirmed_count"],
            "current_unconfirmed_voucher_count": current["aggregate"]["unconfirmed_count"],
            "retained_confirm_transition_count": transitions["CONFIRM"]["event_count"],
            "retained_unconfirm_transition_count": transitions["UNCONFIRM"]["event_count"],
            "retained_delete_count": operations["D"]["event_count"],
            "recent_confirm_transition_count": transitions["CONFIRM"][
                "recent_three_month_event_count"
            ],
            "recent_unconfirm_transition_count": transitions["UNCONFIRM"][
                "recent_three_month_event_count"
            ],
            "recent_delete_count": operations["D"]["recent_three_month_event_count"],
            "deleted_after_any_unconfirm_count": delete_shapes[
                "IMMEDIATE_UNCONFIRM_DELETE"
            ]["delete_count"]
            + delete_shapes["PRIOR_UNCONFIRM_DELETE"]["delete_count"],
            "deleted_never_confirmed_count": delete_shapes["NEVER_CONFIRMED_DELETE"][
                "delete_count"
            ],
            "direct_confirmed_delete_without_unconfirm_count": delete_shapes.get(
                "PRIOR_CONFIRM_NO_UNCONFIRM_DELETE", {"delete_count": 0}
            )["delete_count"],
            "insert_logged_absent_without_delete_count": audit[
                "insert_logged_absent_without_delete_batch"
            ]["insert_logged_absent_without_delete_count"],
        },
        "sql_module_profiles": profiles,
        "static_state_contract": {
            "confirm_validates_before_transaction": confirm["validation_precedes_transaction"],
            "confirm_uses_cursor_transaction_or_savepoint": confirm[
                "owns_explicit_transaction_or_savepoint"
            ]
            and confirm["uses_cursor_signal"]
            and confirm["save_transaction_signal_count"] >= 1,
            "confirm_commits_header_before_after_hook_without_ambient_transaction": confirm[
                "sets_confirm_date_nonnull"
            ]
            and confirm["first_commit_precedes_after_hook"],
            "unconfirm_validates_before_transaction": unconfirm[
                "validation_precedes_transaction"
            ],
            "unconfirm_owns_transaction_and_rollback": unconfirm[
                "owns_explicit_transaction_or_savepoint"
            ]
            and unconfirm["commit_signal_count"] >= 1
            and unconfirm["rollback_signal_count"] >= 1,
            "unconfirm_deletes_linked_detail_item_header": unconfirm[
                "deletes_voucher_detail"
            ]
            and unconfirm["deletes_voucher_item"]
            and unconfirm["deletes_voucher_header"],
            "unconfirm_after_hook_precedes_commit": unconfirm[
                "after_hook_precedes_first_commit"
            ],
            "save_wraps_confirm_in_outer_transaction": save[
                "owns_explicit_transaction_or_savepoint"
            ]
            and save["calls_confirm_procedure"]
            and save["commit_signal_count"] >= 1,
            "header_trigger_projects_confirm_transition_with_special_type_skips": header_trigger[
                "references_inserted_and_deleted"
            ]
            and header_trigger["references_stock_projection"]
            and header_trigger["skips_special_voucher_type_signal"],
            "item_trigger_projects_confirmed_item_mutations": item_trigger[
                "references_inserted_and_deleted"
            ]
            and item_trigger["references_stock_projection"],
            "projection_triggers_have_replication_bypass_and_xact_abort_off": header_trigger[
                "replication_mode_bypass_signal"
            ]
            and item_trigger["replication_mode_bypass_signal"]
            and header_trigger["xact_abort_off_signal"]
            and item_trigger["xact_abort_off_signal"],
            "domain_audit_triggers_cover_insert_update_delete": audit_iu[
                "writes_domain_audit_log"
            ]
            and audit_d["writes_domain_audit_log"],
            "audit_iu_has_confirmed_voucher_date_suppression": audit_iu[
                "suppresses_confirmed_date_only_audit_signal"
            ],
        },
        "current_state": current,
        "domain_audit": audit,
        "storage_contract": storage,
        "evidence_limits": [
            "ConfirmDate transitions are derived from ordered full-row audit snapshots; they do not identify the invoking UI, procedure, reason or operator.",
            "The first SQL COMMIT token preceding AfterInvVocherHdr proves a structural no-ambient-transaction window, not that a post-hook failure occurred.",
            "The save route supplies an outer transaction around nested confirm, while direct adapter execution may not; runtime route frequency is not inferred from audit rows.",
            "Voucher types 60, 21, 64, 65 and selected type-20 paths have specialized trigger handling and must not be generalized from the common projection branch.",
            "The 15 insert-logged absent vouchers without a retained delete event are historical and are not attributed to migration, trigger bypass or a particular command.",
            "No procedure, trigger, form or application command was executed and no voucher, goods, stock, supplier, document, comment, user, host or log-row value was persisted.",
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
    print(json.dumps(payload["static_state_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
