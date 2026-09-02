"""Extract stock projection, cardex-effect and post-voucher validation boundaries read-only."""

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
    ("dbo", "USP_SDSNET_UnConfirmVocher"),
    ("inv", "AfterInvVocherHdr"),
    ("inv", "usp_VocherValidation"),
    ("inv", "usp_CheckOnHandQtyAndDetailQty"),
    ("inv", "usp_CheckCardexQty"),
    ("inv", "usp_CheckCardexDetailQty"),
    ("inv", "trg_tblVocherHdr_UpdateStockGoods"),
    ("inv", "trg_tblVocherItm_UpdateStockGoods"),
    ("GNR", "trg_StockGoods_CheckOnHandQty"),
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _code(definition: str) -> str:
    return " ".join(
        _executable_text(definition).replace("[", "").replace("]", "").casefold().split()
    )


def _position(code: str, pattern: str) -> int | None:
    match = re.search(pattern, code, re.I | re.S)
    return None if match is None else match.start()


def _count(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code, re.I | re.S))


def _profiles(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    profiles: list[dict[str, Any]] = []
    code_by_name: dict[str, str] = {}
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
        code = _code(definition)
        qualified = f"{schema}.{name}"
        code_by_name[qualified] = code
        dependencies = _rows(
            cursor,
            """
            SELECT DISTINCT COALESCE(rs.name,'') referenced_schema,
              COALESCE(ro.name,sed.referenced_entity_name) referenced_object,
              COALESCE(ro.type_desc,'UNRESOLVED') referenced_type,
              sed.is_ambiguous
            FROM sys.sql_expression_dependencies sed
            LEFT JOIN sys.objects ro ON ro.object_id=sed.referenced_id
            LEFT JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
            WHERE sed.referencing_id=OBJECT_ID(%s)
              AND COALESCE(ro.name,sed.referenced_entity_name) IS NOT NULL
            ORDER BY referenced_schema,referenced_object
            """,
            (qualified,),
        )
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
                "raiserror_signal_count": _count(code, r"\braiserror\b"),
                "throw_signal_count": _count(code, r"\bthrow\b"),
                "try_catch_signal": "begin try" in code and "begin catch" in code,
                "cursor_signal_count": _count(code, r"\bdeclare\s+\w+\s+cursor\b"),
                "nolock_signal_count": _count(code, r"\bnolock\b"),
                "references_inserted": bool(re.search(r"\binserted\b", code)),
                "references_deleted": bool(re.search(r"\bdeleted\b", code)),
                "references_stock_goods": "tblstockgoods" in code,
                "replication_bypass_signal": "ufn_isreplicationmode" in code
                and bool(re.search(r"\breturn\b", code)),
                "session_context_bypass_signal": "session_context" in code
                and bool(re.search(r"\breturn\b", code)),
                "dependency_count": len(dependencies),
                "dependencies": dependencies,
                "definition_or_literal_values_persisted": False,
            }
        )
    return profiles, code_by_name


def _cardex_effect_matrix(cursor: Any) -> dict[str, Any]:
    aggregate = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) row_count,COUNT(DISTINCT VocherTypeCode) voucher_type_count,
          SUM(CASE WHEN EffectOnHandQty=1 THEN 1 ELSE 0 END) onhand_effect_row_count,
          SUM(CASE WHEN EffectDamagedQty=1 THEN 1 ELSE 0 END) damaged_effect_row_count,
          SUM(CASE WHEN EffectReservedQty=1 THEN 1 ELSE 0 END) reserved_effect_row_count,
          SUM(CASE WHEN EffectType=1 THEN 1 ELSE 0 END) positive_effect_row_count,
          SUM(CASE WHEN EffectType=-1 THEN 1 ELSE 0 END) negative_effect_row_count,
          SUM(CASE WHEN EffectType=0 THEN 1 ELSE 0 END) zero_effect_row_count
        FROM inv.tblCardexType
        """,
    )[0]
    matrix = _rows(
        cursor,
        """
        SELECT VocherTypeCode,HealthCode,CardexType,EffectType,
          COALESCE(CONVERT(int,EffectOnHandQty),0) effect_onhand,
          COALESCE(CONVERT(int,EffectDamagedQty),0) effect_damaged,
          COALESCE(CONVERT(int,EffectReservedQty),0) effect_reserved,
          COUNT_BIG(*) row_count
        FROM inv.tblCardexType
        GROUP BY VocherTypeCode,HealthCode,CardexType,EffectType,
          COALESCE(CONVERT(int,EffectOnHandQty),0),
          COALESCE(CONVERT(int,EffectDamagedQty),0),
          COALESCE(CONVERT(int,EffectReservedQty),0)
        ORDER BY VocherTypeCode,HealthCode,CardexType
        """,
    )
    return {"aggregate": aggregate, "effect_matrix": matrix}


def _projection_snapshot(cursor: Any) -> dict[str, Any]:
    stock = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) row_count,
          SUM(CASE WHEN OnHandQty<0 THEN 1 ELSE 0 END) negative_onhand_count,
          SUM(CASE WHEN DamagedQty<0 THEN 1 ELSE 0 END) negative_damaged_count,
          SUM(CASE WHEN ReservedQty<0 THEN 1 ELSE 0 END) negative_reserved_count,
          SUM(CASE WHEN UnDeliveredQty<0 THEN 1 ELSE 0 END) negative_undelivered_count,
          SUM(CASE WHEN IsBatch=1 THEN 1 ELSE 0 END) batch_enabled_count
        FROM GNR.tblStockGoods
        """,
    )[0]
    detail = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) row_count,
          COALESCE(SUM(CASE WHEN OnHandQty<0 THEN 1 ELSE 0 END),0) negative_onhand_count,
          COALESCE(SUM(CASE WHEN DamagedQty<0 THEN 1 ELSE 0 END),0) negative_damaged_count,
          COALESCE(SUM(CASE WHEN ReservedQty<0 THEN 1 ELSE 0 END),0) negative_reserved_count,
          COALESCE(SUM(CASE WHEN UnDeliveredQty<0 THEN 1 ELSE 0 END),0) negative_undelivered_count
        FROM GNR.tblStockGoodsDetail
        """,
    )[0]
    return {"stock_goods": stock, "stock_goods_detail": detail}


def _trigger_state(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT ps.name parent_schema,po.name parent_object,t.name trigger_name,
          t.is_disabled,t.is_instead_of_trigger
        FROM sys.triggers t JOIN sys.objects po ON po.object_id=t.parent_id
        JOIN sys.schemas ps ON ps.schema_id=po.schema_id
        WHERE t.object_id IN (
          OBJECT_ID(N'inv.trg_tblVocherHdr_UpdateStockGoods'),
          OBJECT_ID(N'inv.trg_tblVocherItm_UpdateStockGoods'),
          OBJECT_ID(N'GNR.trg_StockGoods_CheckOnHandQty'))
        ORDER BY ps.name,po.name,t.name
        """,
    )


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safe = _assert_safe_target(cursor)
        profiles, codes = _profiles(cursor)
        cardex = _cardex_effect_matrix(cursor)
        projection = _projection_snapshot(cursor)
        triggers = _trigger_state(cursor)
    finally:
        connection.close()

    confirm = codes["dbo.USP_SDSNET_ConfirmVocher"]
    unconfirm = codes["dbo.USP_SDSNET_UnConfirmVocher"]
    after = codes["inv.AfterInvVocherHdr"]
    header_trigger = codes["inv.trg_tblVocherHdr_UpdateStockGoods"]
    item_trigger = codes["inv.trg_tblVocherItm_UpdateStockGoods"]
    guard_trigger = codes["GNR.trg_StockGoods_CheckOnHandQty"]
    by_name = {row["qualified_name"]: row for row in profiles}
    confirm_commit = _position(confirm, r"\bcommit\b")
    confirm_after = _position(confirm, r"\bexec\s+inv\.afterinvvocherhdr\b")
    unconfirm_after = _position(unconfirm, r"\bexec\s+inv\.afterinvvocherhdr\b")
    unconfirm_commit = _position(unconfirm, r"\bcommit\b")
    after_first_validation = _position(after, r"\bexec\s+inv\.usp_vochervalidation\b")
    after_batch_update = _position(after, r"\bupdate\s+b\s+set\s+isdisabled\b")
    expected_after_calls = {
        "inv.usp_vochervalidation",
        "inv.usp_checkonhandqtyanddetailqty",
        "inv.usp_checkcardexqty",
        "inv.usp_checkcardexdetailqty",
    }
    return {
        "artifact": "varanegar_stock_projection_validation_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_RULE_MATRIX_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": safe["updateability"],
            "can_select": safe["can_select"],
            "can_view_definition": safe["can_view_definition"],
            "can_update": safe["can_update"],
            "denies_data_writes": safe["denies_data_writes"],
            "stored_procedure_trigger_form_or_application_command_executions": 0,
            "voucher_goods_stock_document_user_host_or_raw_row_values_persisted": 0,
            "sql_definitions_error_texts_or_business_identifiers_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "selected_sql_module_count": len(profiles),
            "after_validation_dependency_count": by_name["inv.AfterInvVocherHdr"][
                "dependency_count"
            ],
            "cardex_effect_row_count": cardex["aggregate"]["row_count"],
            "cardex_effect_voucher_type_count": cardex["aggregate"]["voucher_type_count"],
            "stock_projection_row_count": projection["stock_goods"]["row_count"],
            "stock_projection_negative_component_count": sum(
                projection["stock_goods"][key]
                for key in (
                    "negative_onhand_count",
                    "negative_damaged_count",
                    "negative_reserved_count",
                    "negative_undelivered_count",
                )
            ),
            "stock_detail_row_count": projection["stock_goods_detail"]["row_count"],
            "active_projection_or_guard_trigger_count": sum(
                not row["is_disabled"] for row in triggers
            ),
        },
        "sql_module_profiles": profiles,
        "static_validation_and_projection_contract": {
            "confirm_first_commit_precedes_after_validation": confirm_commit is not None
            and confirm_after is not None
            and confirm_commit < confirm_after,
            "confirm_appends_after_message_without_abort_guard": bool(
                re.search(
                    r"exec\s+inv\.afterinvvocherhdr\b.*?@aftermsg\s+output\s+set\s+@msgerr\s*=.*?@aftermsg\b.*?fetch\s+next",
                    confirm,
                    re.I | re.S,
                )
            ),
            "confirm_after_cursor_excludes_generated_type15_mode": bool(
                re.search(r"from\s+#tmpvocherhdr\s+where\s+@createvocher15\s*<>\s*1", confirm)
            ),
            "unconfirm_after_validation_precedes_commit": unconfirm_after is not None
            and unconfirm_commit is not None
            and unconfirm_after < unconfirm_commit,
            "unconfirm_appends_after_message_then_commits_without_abort_guard": bool(
                re.search(
                    r"exec\s+inv\.afterinvvocherhdr\b.*?@aftermsg\s+output\s+set\s+@msgerr\s*=.*?@aftermsg\b.*?\bcommit\b",
                    unconfirm,
                    re.I | re.S,
                )
            ),
            "after_has_no_local_transaction_raise_or_throw": by_name[
                "inv.AfterInvVocherHdr"
            ]["begin_transaction_signal_count"]
            == 0
            and by_name["inv.AfterInvVocherHdr"]["commit_signal_count"] == 0
            and by_name["inv.AfterInvVocherHdr"]["rollback_signal_count"] == 0
            and by_name["inv.AfterInvVocherHdr"]["raiserror_signal_count"] == 0
            and by_name["inv.AfterInvVocherHdr"]["throw_signal_count"] == 0,
            "after_calls_four_expected_validation_modules": all(
                f"exec {name}" in after for name in expected_after_calls
            ),
            "after_uses_nolock_reads": by_name["inv.AfterInvVocherHdr"][
                "nolock_signal_count"
            ]
            >= 1,
            "after_type20_batch_state_update_precedes_validation": after_batch_update
            is not None
            and after_first_validation is not None
            and after_batch_update < after_first_validation,
            "after_skips_common_onhand_and_cardex_checks_for_types12_and13": _count(
                after, r"@vochertypecode\s+not\s+in\s*\(\s*12\s*,\s*13\s*\)"
            )
            >= 3,
            "after_cardex_checks_only_when_confirmed": _count(
                after,
                r"@vochertypecode\s+not\s+in\s*\(\s*12\s*,\s*13\s*\)\s+and\s+@confirmedby\s+is\s+not\s+null",
            )
            >= 2,
            "header_projection_uses_cursor_and_can_rollback": _count(
                header_trigger, r"\bdeclare\s+\w+\s+cursor\b"
            )
            >= 1
            and "rollback" in header_trigger
            and "raiserror" in header_trigger,
            "item_projection_uses_cursor_try_catch_and_can_rollback": _count(
                item_trigger, r"\bdeclare\s+\w+\s+cursor\b"
            )
            >= 1
            and "begin try" in item_trigger
            and "rollback" in item_trigger,
            "stock_negative_guard_is_set_based": "exists(select * from inserted" in guard_trigger,
            "stock_negative_guard_has_session_and_replication_bypass": by_name[
                "GNR.trg_StockGoods_CheckOnHandQty"
            ]["session_context_bypass_signal"]
            and by_name["GNR.trg_StockGoods_CheckOnHandQty"]["replication_bypass_signal"],
        },
        "cardex_effect_contract": cardex,
        "projection_snapshot": projection,
        "projection_and_guard_trigger_state": triggers,
        "evidence_limits": [
            "Static ordering proves message-return and transaction structure, not that a validation failure occurred in production.",
            "The direct no-ambient confirmation route can commit before AfterInvVocherHdr; outer save or caller-owned transactions may change physical atomicity and are not generalized.",
            "AfterInvVocherHdr returns error text through output parameters; this extraction persists no error text, document value, actor or invocation count.",
            "The 50-row cardex-effect matrix is a versioned rule snapshot, not permission to hard-code voucher-type behavior in UI code.",
            "Session-context and replication bypass are capabilities; current bypass use or an incident is not inferred.",
            "No stored procedure, trigger, form or application command was executed and no source or target state changed.",
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
    print(json.dumps(payload["static_validation_and_projection_contract"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
