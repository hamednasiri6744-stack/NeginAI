"""Extract read-only command idempotency guards and current duplicate shapes."""

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


COMMANDS = (
    ("SLE", "usp_sdsnet_CreateSaleByOrder"),
    ("dbo", "usp_sdsnet_Sale_Cancel"),
    ("dbo", "USP_SDSNET_GenerateRetSaleVocher"),
    ("dbo", "usp_CreateExitVocherByDist"),
    ("dbo", "USP_SDSNET_ConfirmVocher"),
    ("dbo", "USP_SDSNET_UnConfirmVocher"),
    ("dbo", "usp_DoExternalVoucher"),
    ("dbo", "usp_DoExternalVoucherTransfer"),
    ("SLE", "usp_FillSaleVocher"),
    ("SLE", "usp_SetPrintedDoc"),
)

TABLES = (
    ("SLE", "tblSaleHdr"),
    ("SLE", "tblRetSaleHdr"),
    ("inv", "tblExit"),
    ("inv", "tblVocherHdr"),
    ("GNR", "tblPrintedDoc"),
    ("dbo", "PreVoucher"),
    ("dbo", "TourHistory"),
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _code(definition: str) -> str:
    return " ".join(
        _executable_text(definition).replace("[", "").replace("]", "").casefold().split()
    )


def _count(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code, re.I | re.S))


def _command_profiles(cursor: Any) -> list[dict[str, Any]]:
    profiles = []
    for schema, name in COMMANDS:
        found = _rows(
            cursor,
            """
            SELECT s.name schema_name,o.name object_name,o.type_desc,o.create_date,o.modify_date,
                   m.definition
            FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
            JOIN sys.sql_modules m ON m.object_id=o.object_id
            WHERE s.name=%s AND o.name=%s
            """,
            (schema, name),
        )
        if len(found) != 1:
            raise AssertionError({"missing_or_duplicate_command": f"{schema}.{name}"})
        row = found[0]
        definition = row.pop("definition") or ""
        code = _code(definition)
        parameters = _rows(
            cursor,
            """
            SELECT p.parameter_id,p.name parameter_name,TYPE_NAME(p.user_type_id) data_type,
                   p.max_length,p.is_output
            FROM sys.parameters p
            WHERE p.object_id=OBJECT_ID(%s)
            ORDER BY p.parameter_id
            """,
            (f"{schema}.{name}",),
        )
        idempotency_parameters = [
            parameter["parameter_name"]
            for parameter in parameters
            if re.search(
                r"(?i)(idempot|command.?id|request.?id|correlation|attempt.?id|retry.?key)",
                parameter["parameter_name"],
            )
        ]
        profiles.append(
            {
                **row,
                "qualified_name": f"{schema}.{name}",
                "definition_sha256": _sha(definition),
                "definition_character_count": len(definition),
                "parameter_count": len(parameters),
                "parameters": parameters,
                "explicit_idempotency_parameter_count": len(idempotency_parameters),
                "explicit_idempotency_parameters": idempotency_parameters,
                "begin_transaction_signal_count": _count(code, r"\bbegin\s+(?:tran|transaction)\b"),
                "save_transaction_signal_count": _count(code, r"\bsave\s+transaction\b"),
                "commit_signal_count": _count(code, r"\bcommit\b"),
                "rollback_signal_count": _count(code, r"\brollback\b"),
                "try_catch_signal": "begin try" in code and "begin catch" in code,
                "if_exists_signal_count": _count(code, r"\bif\s+exists\s*\("),
                "not_exists_signal_count": _count(code, r"\bnot\s+exists\s*\("),
                "new_id_allocator_signal_count": _count(
                    code, r"\b(?:uspgetnextid|usp_getnextid|newid)\b"
                ),
                "max_plus_one_signal_count": _count(
                    code, r"\bmax\s*\([^)]*\)\s*\+\s*1\b"
                ),
                "insert_signal_count": _count(code, r"\binsert\b"),
                "update_signal_count": _count(code, r"\bupdate\b"),
                "delete_signal_count": _count(code, r"\bdelete\b"),
                "definition_or_literal_values_persisted": False,
            }
        )
    return profiles


def _filter_class(filter_definition: str | None) -> str:
    value = (filter_definition or "").casefold().replace("[", "").replace("]", "")
    if "iscanceled" in value:
        return "ACTIVE_EXIT_ONLY"
    if "cancelflag" in value and "retorderref" in value:
        return "ACTIVE_RETURN_WITH_SOURCE_ONLY"
    if ("vouchertypecode" in value or "vochertypecode" in value) and "docref" in value:
        return "VOUCHER_TYPE_WITH_SOURCE_ONLY"
    if "vouchertypecode" in value or "vochertypecode" in value:
        return "VOUCHER_TYPE_ONLY"
    if re.search(r"(?:^|\W)type(?:\W|$)", value):
        return "ONE_HISTORY_TYPE_ONLY"
    return "UNFILTERED" if not value else "OTHER_FILTER"


def _table_guard_profiles(cursor: Any) -> list[dict[str, Any]]:
    profiles = []
    for schema, table in TABLES:
        qualified = f"{schema}.{table}"
        rows = _rows(
            cursor,
            """
            SELECT i.index_id,i.is_unique,i.is_primary_key,i.has_filter,i.filter_definition,
              STRING_AGG(CASE WHEN ic.is_included_column=0 THEN c.name END, ',')
                WITHIN GROUP (ORDER BY ic.key_ordinal) key_columns
            FROM sys.indexes i
            JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
            JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
            WHERE i.object_id=OBJECT_ID(%s) AND i.is_hypothetical=0 AND i.is_unique=1
            GROUP BY i.index_id,i.is_unique,i.is_primary_key,i.has_filter,i.filter_definition
            ORDER BY i.index_id
            """,
            (qualified,),
        )
        guards = []
        for row in rows:
            filter_definition = row.pop("filter_definition")
            key_columns = [value for value in (row.pop("key_columns") or "").split(",") if value]
            contains_identity_key = any(value.casefold() == "id" for value in key_columns)
            guards.append(
                {
                    **row,
                    "key_columns": key_columns,
                    "contains_identity_key": contains_identity_key,
                    "semantic_guard_candidate": bool(
                        row["is_unique"]
                        and not row["is_primary_key"]
                        and not contains_identity_key
                    ),
                    "filter_class": _filter_class(filter_definition),
                    "filter_definition_sha256": _sha(filter_definition or ""),
                    "filter_literal_or_index_name_persisted": False,
                }
            )
        profiles.append(
            {
                "qualified_name": qualified,
                "unique_index_count": len(guards),
                "semantic_unique_guard_count": sum(
                    guard["semantic_guard_candidate"] for guard in guards
                ),
                "unique_guards": guards,
            }
        )
    return profiles


def _duplicate_shapes(cursor: Any) -> dict[str, Any]:
    sale = _rows(
        cursor,
        """
        WITH x AS (
          SELECT OrderRef,COUNT_BIG(*) active_count
          FROM SLE.tblSaleHdr WHERE CancelFlag=0 GROUP BY OrderRef
        )
        SELECT COUNT_BIG(*) active_order_group_count,
          SUM(CASE WHEN active_count>1 THEN 1 ELSE 0 END) duplicate_active_order_group_count,
          MAX(active_count) maximum_active_sales_per_order
        FROM x
        """,
    )[0]
    returns = _rows(
        cursor,
        """
        WITH x AS (
          SELECT DCRef,RetOrderRef,COUNT_BIG(*) active_count
          FROM SLE.tblRetSaleHdr WHERE CancelFlag=0 AND RetOrderRef IS NOT NULL
          GROUP BY DCRef,RetOrderRef
        )
        SELECT COUNT_BIG(*) active_source_group_count,
          SUM(CASE WHEN active_count>1 THEN 1 ELSE 0 END) duplicate_active_source_group_count,
          MAX(active_count) maximum_active_returns_per_source
        FROM x
        """,
    )[0]
    exits = _rows(
        cursor,
        """
        WITH x AS (
          SELECT DistRef,StockDCRef,AccYear,COUNT_BIG(*) active_count
          FROM inv.tblExit WHERE IsCanceled=0 GROUP BY DistRef,StockDCRef,AccYear
        )
        SELECT COUNT_BIG(*) active_distribution_stock_year_group_count,
          SUM(CASE WHEN active_count>1 THEN 1 ELSE 0 END) duplicate_active_group_count,
          MAX(active_count) maximum_active_exits_per_group
        FROM x
        """,
    )[0]
    return_vouchers = _rows(
        cursor,
        """
        WITH x AS (
          SELECT DocRef,HealthCode,COUNT_BIG(*) voucher_count
          FROM inv.tblVocherHdr WHERE VocherTypeCode=10 AND DocRef IS NOT NULL
          GROUP BY DocRef,HealthCode
        )
        SELECT COUNT_BIG(*) source_health_group_count,
          SUM(CASE WHEN voucher_count>1 THEN 1 ELSE 0 END) duplicate_source_health_group_count,
          MAX(voucher_count) maximum_vouchers_per_source_health
        FROM x
        """,
    )[0]
    printed = _rows(
        cursor,
        """
        WITH x AS (
          SELECT DocType,DocRef,COUNT_BIG(*) event_count
          FROM GNR.tblPrintedDoc GROUP BY DocType,DocRef
        )
        SELECT COUNT_BIG(*) printed_document_group_count,
          SUM(CASE WHEN event_count>1 THEN 1 ELSE 0 END) repeated_document_group_count,
          MAX(event_count) maximum_events_per_document
        FROM x
        """,
    )[0]
    pre_voucher = _rows(
        cursor,
        """
        WITH x AS (
          SELECT VoucherCreatorId,ReferenceId,ArticleId,SLCode,DLCode,FifthLedgerCode,
                 SixthLedgerCode,SeventhLedgerCode,PreVoucherItemComment,COUNT_BIG(*) line_count
          FROM dbo.PreVoucher
          GROUP BY VoucherCreatorId,ReferenceId,ArticleId,SLCode,DLCode,FifthLedgerCode,
                   SixthLedgerCode,SeventhLedgerCode,PreVoucherItemComment
        )
        SELECT COUNT_BIG(*) signature_group_count,
          SUM(CASE WHEN line_count>1 THEN 1 ELSE 0 END) duplicate_signature_group_count,
          MAX(line_count) maximum_lines_per_signature
        FROM x
        """,
    )[0]
    tour = _rows(
        cursor,
        """
        WITH x AS (
          SELECT Type,EntityUniqueId,COUNT_BIG(*) history_count
          FROM dbo.TourHistory WHERE Type IN (1,2,8,10)
          GROUP BY Type,EntityUniqueId
        )
        SELECT Type,COUNT_BIG(*) entity_group_count,
          SUM(CASE WHEN history_count>1 THEN 1 ELSE 0 END) duplicate_entity_group_count,
          MAX(history_count) maximum_histories_per_entity
        FROM x GROUP BY Type ORDER BY Type
        """,
    )
    return {
        "sale_active_order": sale,
        "sales_return_active_source": returns,
        "distribution_active_exit": exits,
        "sales_return_type_voucher": return_vouchers,
        "printed_document_event": printed,
        "pre_voucher_line_signature": pre_voucher,
        "tour_history_by_type": tour,
    }


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        if str(context["updateability"]).upper() != "READ_ONLY" or int(
            context["can_update"] or 0
        ) != 0:
            raise RuntimeError("analysis database is not safely read-only")
        commands = _command_profiles(cursor)
        tables = _table_guard_profiles(cursor)
        shapes = _duplicate_shapes(cursor)
        command_map = {item["qualified_name"]: item for item in commands}
        table_map = {item["qualified_name"]: item for item in tables}
        tour_rows = {int(item["Type"]): item for item in shapes["tour_history_by_type"]}

        contract = {
            "all_selected_commands_lack_explicit_idempotency_parameter": all(
                item["explicit_idempotency_parameter_count"] == 0 for item in commands
            ),
            "sale_has_no_semantic_unique_guard_for_one_active_sale_per_order": (
                table_map["SLE.tblSaleHdr"]["semantic_unique_guard_count"] == 0
                and int(shapes["sale_active_order"]["duplicate_active_order_group_count"] or 0)
                == 0
            ),
            "sales_return_has_active_source_semantic_unique_guard": any(
                item["semantic_guard_candidate"]
                and item["filter_class"] == "ACTIVE_RETURN_WITH_SOURCE_ONLY"
                and "RetOrderRef" in item["key_columns"]
                for item in table_map["SLE.tblRetSaleHdr"]["unique_guards"]
            ),
            "distribution_exit_has_active_semantic_unique_guard": any(
                item["semantic_guard_candidate"]
                and item["filter_class"] == "ACTIVE_EXIT_ONLY"
                and {"DistRef", "StockDCRef", "AccYear"}.issubset(item["key_columns"])
                for item in table_map["inv.tblExit"]["unique_guards"]
            ),
            "sales_return_voucher_has_source_health_semantic_unique_guard": any(
                item["semantic_guard_candidate"]
                and item["filter_class"] == "VOUCHER_TYPE_WITH_SOURCE_ONLY"
                and {"DocRef", "HealthCode"}.issubset(item["key_columns"])
                for item in table_map["inv.tblVocherHdr"]["unique_guards"]
            ),
            "printed_document_has_no_semantic_unique_guard": table_map[
                "GNR.tblPrintedDoc"
            ]["semantic_unique_guard_count"]
            == 0,
            "pre_voucher_has_line_signature_semantic_unique_guard": any(
                item["semantic_guard_candidate"]
                and {"VoucherCreatorId", "ReferenceId", "ArticleId"}.issubset(
                    item["key_columns"]
                )
                for item in table_map["dbo.PreVoucher"]["unique_guards"]
            ),
            "tour_history_semantic_unique_guard_is_scoped_to_one_type_only": (
                table_map["dbo.TourHistory"]["semantic_unique_guard_count"] == 1
                and any(
                    item["semantic_guard_candidate"]
                    and item["filter_class"] == "ONE_HISTORY_TYPE_ONLY"
                    for item in table_map["dbo.TourHistory"]["unique_guards"]
                )
                and int(tour_rows[1]["duplicate_entity_group_count"] or 0) == 0
                and int(tour_rows[8]["duplicate_entity_group_count"] or 0) > 0
                and int(tour_rows[10]["duplicate_entity_group_count"] or 0) > 0
            ),
            "selected_mutating_commands_allocate_ids_but_have_no_retry_key": (
                sum(item["new_id_allocator_signal_count"] for item in commands) > 0
                and all(item["explicit_idempotency_parameter_count"] == 0 for item in commands)
            ),
            "current_guarded_business_shapes_are_duplicate_free": (
                int(shapes["sales_return_active_source"]["duplicate_active_source_group_count"] or 0)
                == 0
                and int(shapes["distribution_active_exit"]["duplicate_active_group_count"] or 0)
                == 0
                and int(shapes["sales_return_type_voucher"]["duplicate_source_health_group_count"] or 0)
                == 0
                and int(shapes["pre_voucher_line_signature"]["duplicate_signature_group_count"] or 0)
                == 0
            ),
        }
        validation = "PASS" if all(contract.values()) else "FAIL"
        return {
            "artifact": "varanegar_idempotency_guard_boundary_20260829",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": validation,
            "scope": {"server": SERVER, "database": DATABASE},
            "safety": {
                "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_DUPLICATE_AGGREGATES",
                "database_updateability": context["updateability"],
                "can_select": context["can_select"],
                "can_view_definition": context["can_view_definition"],
                "can_update": context["can_update"],
                "denies_data_writes": context["denies_data_writes"],
                "stored_procedure_trigger_form_report_or_application_command_executions": 0,
                "assembly_loads_or_executions": 0,
                "business_rows_ids_names_messages_index_names_filters_or_raw_values_persisted": 0,
                "sql_definitions_comments_or_literal_values_persisted": 0,
                "source_or_target_state_changed": 0,
            },
            "summary": {
                "selected_command_count": len(commands),
                "selected_command_with_explicit_idempotency_parameter_count": sum(
                    item["explicit_idempotency_parameter_count"] > 0 for item in commands
                ),
                "selected_command_with_id_allocator_count": sum(
                    item["new_id_allocator_signal_count"] > 0 for item in commands
                ),
                "selected_table_count": len(tables),
                "selected_table_with_semantic_unique_guard_count": sum(
                    item["semantic_unique_guard_count"] > 0 for item in tables
                ),
                "current_guarded_duplicate_group_count": sum(
                    int(value or 0)
                    for value in (
                        shapes["sales_return_active_source"]["duplicate_active_source_group_count"],
                        shapes["distribution_active_exit"]["duplicate_active_group_count"],
                        shapes["sales_return_type_voucher"]["duplicate_source_health_group_count"],
                        shapes["pre_voucher_line_signature"]["duplicate_signature_group_count"],
                    )
                ),
                "current_guarded_zero_population_shape_count": sum(
                    int(value or 0) == 0
                    for value in (
                        shapes["sales_return_active_source"]["active_source_group_count"],
                        shapes["distribution_active_exit"]["active_distribution_stock_year_group_count"],
                        shapes["sales_return_type_voucher"]["source_health_group_count"],
                        shapes["pre_voucher_line_signature"]["signature_group_count"],
                    )
                ),
                "current_sale_multi_active_order_group_count": int(
                    shapes["sale_active_order"]["duplicate_active_order_group_count"] or 0
                ),
                "printed_document_repeated_group_count": int(
                    shapes["printed_document_event"]["repeated_document_group_count"] or 0
                ),
                "tour_history_type8_duplicate_entity_group_count": int(
                    tour_rows[8]["duplicate_entity_group_count"] or 0
                ),
                "tour_history_type10_duplicate_entity_group_count": int(
                    tour_rows[10]["duplicate_entity_group_count"] or 0
                ),
            },
            "command_profiles": commands,
            "table_unique_guard_profiles": tables,
            "anonymous_duplicate_shapes": shapes,
            "static_and_current_idempotency_contract": contract,
            "target_contract": {
                "request_identity": "caller supplied CommandId plus canonical PayloadHash",
                "same_key_same_payload": "return the original typed outcome and receipt without new effects",
                "same_key_different_payload": "reject before mutation as an idempotency-key conflict",
                "concurrent_same_key": "one writer wins; all callers observe the same accepted or rejected receipt",
                "natural_guard_role": "retain semantic unique constraints as final storage protection, not as the command receipt",
                "retry_vs_new_intent": "a retry reuses CommandId; a legitimate repeat such as reprint uses a new CommandId linked to the prior attempt",
                "unknown_commit": "quarantine and reconcile by CommandId before any automatic replay",
            },
            "evidence_limits": [
                "Parameter names and static SQL signals prove deployed command shape, not runtime branch frequency.",
                "A clean current duplicate aggregate does not prove retry safety without an immutable command receipt.",
                "A semantic unique index can stop one duplicate projection but cannot reproduce the original command result or protect every side effect.",
                "Repeated print events include legitimate reprints; no incident or duplicate-retry attribution is made.",
                "No procedure, trigger, form, report or application command was executed.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(artifact["validation"])
    print(json.dumps(artifact["summary"], ensure_ascii=False, default=_json_default))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
