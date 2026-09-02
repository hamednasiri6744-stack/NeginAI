"""Extract read-only SQL and current anonymous operation-date boundaries for order-to-sale."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import _assert_safe_target, _connect, _rows
from extract_varanegar_ngt_order_target_deletion_boundary import _executable_text


COMMANDS = (
    "SLE.usp_sdsnet_CreateSaleByOrder",
    "SLE.usp_CreateSaleByOrder",
    "SLE.usp_IsSaleDateOpen",
    "SLE.usp_ValidateOrderNo",
    "dbo.usp_sdsnet_CheckOprdateToSet",
    "dbo.usp_SDSNet_OprDate_getList",
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _redact_strings(line: str) -> str:
    return re.sub(r"N?'(?:''|[^'])*'", "'<STRING>'", line, flags=re.I)


def collect() -> tuple[dict[str, Any], list[str]]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        modules = []
        definitions = {}
        diagnostics = []
        for command in COMMANDS:
            rows = _rows(
                cursor,
                """
                SELECT m.definition,o.modify_date,o.type_desc
                FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
                WHERE m.object_id=OBJECT_ID(%s)
                """,
                (command,),
            )
            if len(rows) != 1:
                raise AssertionError(f"operation-date command absent or duplicated: {command}")
            definition = rows[0]["definition"] or ""
            definitions[command] = definition
            parameters = _rows(
                cursor,
                """
                SELECT parameter_id,name parameter_name,TYPE_NAME(user_type_id) data_type,is_output
                FROM sys.parameters WHERE object_id=OBJECT_ID(%s) ORDER BY parameter_id
                """,
                (command,),
            )
            dependencies = _rows(
                cursor,
                """
                SELECT DISTINCT COALESCE(referenced_schema_name,'?') referenced_schema,
                  referenced_entity_name
                FROM sys.sql_expression_dependencies
                WHERE referencing_id=OBJECT_ID(%s) AND referenced_entity_name IS NOT NULL
                """,
                (command,),
            )
            executable = _executable_text(definition)
            compact = " ".join(executable.replace("[", "").replace("]", "").split()).casefold()
            modules.append(
                {
                    "qualified_command": command,
                    "type_desc": rows[0]["type_desc"],
                    "modify_date": rows[0]["modify_date"],
                    "definition_sha256": _sha(definition),
                    "definition_character_count": len(definition),
                    "parameters": parameters,
                    "operation_date_token_count": len(re.findall(r"@(oprdate|createsaledate)\b", compact, re.I)),
                    "operation_date_dependencies": [
                        f"{row['referenced_schema']}.{row['referenced_entity_name']}"
                        for row in dependencies
                        if re.search(r"(?i)(oprdate|accyear|sale|order)", row["referenced_entity_name"])
                    ],
                }
            )
            lines = executable.splitlines()
            indexes = {
                index
                for index, line in enumerate(lines)
                if re.search(r"(?i)(@OprDate|@CreateSaleDate|tblOprDate|LastDate|IsClosed|AccYear)", line)
            }
            context_indexes = sorted(
                {position for index in indexes for position in range(max(0, index - 2), min(len(lines), index + 3))}
            )
            diagnostics.append(f"COMMAND {command}")
            diagnostics.extend(
                f"LINE {index + 1}: {_redact_strings(lines[index]).strip()}" for index in context_indexes
            )

        profiles = _rows(
            cursor,
            """
            SELECT SysRef,AccYear,IsClosed,OprDate,LastDate,COUNT_BIG(*) profile_row_count
            FROM GNR.tblOprDate
            GROUP BY SysRef,AccYear,IsClosed,OprDate,LastDate
            ORDER BY SysRef,AccYear,IsClosed,OprDate,LastDate
            """,
        )
        totals = _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) row_count,COUNT_BIG(DISTINCT DCRef) dc_count,
              SUM(CASE WHEN D.ID IS NULL THEN 1 ELSE 0 END) orphan_dc_count,
              SUM(CASE WHEN OprDate IS NULL THEN 1 ELSE 0 END) null_oprdate_count,
              SUM(CASE WHEN LastDate IS NULL THEN 1 ELSE 0 END) null_lastdate_count,
              SUM(CASE WHEN OprDate>LastDate THEN 1 ELSE 0 END) oprdate_after_lastdate_count,
              SUM(CASE WHEN OprDate=LastDate THEN 1 ELSE 0 END) oprdate_equal_lastdate_count,
              SUM(CASE WHEN OprDate<LastDate THEN 1 ELSE 0 END) oprdate_before_lastdate_count
            FROM GNR.tblOprDate O LEFT JOIN GNR.tblDC D ON D.ID=O.DCRef
            """,
        )[0]
        sale_boundary_totals = _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) sale_boundary_row_count,
              SUM(CASE WHEN IsClosed=0 THEN 1 ELSE 0 END) open_sale_boundary_row_count,
              SUM(CASE WHEN IsClosed=1 THEN 1 ELSE 0 END) closed_sale_boundary_row_count,
              SUM(CASE WHEN OprDate IS NULL OR OprDate='' THEN 1 ELSE 0 END) missing_sale_oprdate_count,
              SUM(CASE WHEN LastDate IS NULL OR LastDate='' THEN 1 ELSE 0 END) missing_sale_lastdate_count
            FROM GNR.tblOprDate WHERE SysRef=1
            """,
        )[0]
        special_type_profiles = _rows(
            cursor,
            """
            SELECT T.ID order_type,T.Selectable,T.IsDefault,T.IsFreeInvoice,T.DontCheckMojodi,
              T.EffectOrderOnStockGoods,
              (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr O WHERE O.OrderType=T.ID) current_order_count,
              (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr S WHERE S.OrderType=T.ID) current_sale_count,
              (SELECT COUNT_BIG(*) FROM SLE.tblOrderHdr O WHERE O.OrderType=T.ID
                 AND O.ModifiedDate>=DATEADD(month,-3,SYSDATETIME())) recent_order_count,
              (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr S WHERE S.OrderType=T.ID
                 AND S.ModifiedDate>=DATEADD(month,-3,SYSDATETIME())) recent_sale_count
            FROM SLE.tblOrderType T WHERE T.ID IN (1007,1008) ORDER BY T.ID
            """,
        )
        special_type_totals = {
            "configured_special_order_type_count": len(special_type_profiles),
            "current_special_order_count": sum(int(row["current_order_count"]) for row in special_type_profiles),
            "current_special_sale_count": sum(int(row["current_sale_count"]) for row in special_type_profiles),
            "recent_special_order_count": sum(int(row["recent_order_count"]) for row in special_type_profiles),
            "recent_special_sale_count": sum(int(row["recent_sale_count"]) for row in special_type_profiles),
        }
        wrapper = " ".join(_executable_text(definitions[COMMANDS[0]]).split()).casefold()
        core = " ".join(_executable_text(definitions[COMMANDS[1]]).split()).casefold()
        date_open = " ".join(_executable_text(definitions[COMMANDS[2]]).split()).casefold()
        validate_order = " ".join(_executable_text(definitions[COMMANDS[3]]).split()).casefold()
        check_to_set = " ".join(_executable_text(definitions[COMMANDS[4]]).split()).casefold()
        get_list = " ".join(_executable_text(definitions[COMMANDS[5]]).split()).casefold()
        semantic_assertions = {
            "wrapper_forwards_create_sale_date_to_core": bool(
                re.search(r"exec\s+@\w+\s*=\s*sle\.usp_createsalebyorder[\s\S]*@createsaledate", wrapper)
            ),
            "core_uses_operation_date_for_price_and_open_date_checks": (
                "sle.usp_checkorderitmprice @oprdate" in core
                and "sle.usp_checkorderitmcprice @orderref, @oprdate" in core
                and "sle.usp_issaledateopen @orderref,@oprdate" in core
            ),
            "date_open_command_reads_operation_date_boundary": "tbloprdate" in date_open,
            "date_open_rejects_closed_or_not_after_last_date": (
                "if (@isclosed = 1)" in date_open and "if (@saledate <= @lastdate)" in date_open
            ),
            "date_open_is_skipped_for_order_types_1007_and_1008": bool(
                re.search(r"if\s+@ordertype\s+not\s+in\s*\(1007\s*,\s*1008\)[\s\S]*usp_issaledateopen", core)
            ),
            "missing_boundary_row_has_no_explicit_rejection": (
                "if not exists" not in date_open and "if (@isclosed = 1)" in date_open
            ),
            "order_validator_is_separate_from_operation_date_parameter": (
                "@oprdate" not in validate_order and "@createsaledate" not in validate_order
            ),
            "desktop_check_to_set_reads_operation_date_boundary": "tbloprdate" in check_to_set
            or "oprdate" in check_to_set,
            "fetch_reason_two_returns_last_date_then_operation_date": bool(
                re.search(
                    r"if\s+@fetchreason\s*=\s*2[\s\S]*select\s+top\s+1\s+lastdate\s*,\s*oprdate\s+from\s+gnr\.tbloprdate",
                    get_list,
                )
            ),
            "both_date_open_exception_types_are_configured_but_have_no_current_clone_instances": (
                len(special_type_profiles) == 2
                and all(row["order_type"] in (1007, 1008) for row in special_type_profiles)
                and all(row["current_order_count"] == 0 and row["current_sale_count"] == 0 for row in special_type_profiles)
            ),
        }
        semantic_contracts = [
            {
                "boundary": "ORDER_TO_SALE_CREATE_DATE_SOURCE",
                "contract": "WRAPPER_FORWARDS_CREATE_SALE_DATE_TO_CORE_AS_OPERATION_DATE",
                "consumers": ["ORDER_ITEM_PRICE", "CONTRACT_PRICE", "SALE_DATE_OPEN", "EVC", "CUSTOMER_LIMIT"],
            },
            {
                "boundary": "STANDARD_ORDER_DATE_FINALITY",
                "applies_when": "ORDER_TYPE_NOT_IN_1007_1008",
                "reject_when": ["SALE_PERIOD_IS_CLOSED", "CREATE_SALE_DATE_LESS_THAN_OR_EQUAL_TO_LAST_DATE"],
                "comparison_representation": "VARCHAR_10_LEXICAL_PERSIAN_DATE",
            },
            {
                "boundary": "SPECIAL_ORDER_DATE_EXCEPTION",
                "applies_when": "ORDER_TYPE_IN_1007_1008",
                "sale_date_open_check": "SKIPPED",
                "other_operation_date_consumers": "REMAIN_PRESENT",
            },
            {
                "boundary": "MISSING_OPERATION_DATE_ROW",
                "legacy_behavior": "NO_EXPLICIT_REJECTION_IN_SELECTED_SALE_DATE_OPEN_COMMAND",
                "effective_null_branch_behavior": "FAIL_OPEN_BY_SQL_THREE_VALUED_LOGIC",
                "target_requirement": "REQUIRE_EXACTLY_ONE_CURRENT_SALE_BOUNDARY_AND_FAIL_CLOSED_IF_MISSING_OR_AMBIGUOUS",
            },
            {
                "boundary": "DESKTOP_FETCH_REASON_TWO_COLUMN_ORDER",
                "result_columns": ["LAST_DATE", "OPERATION_DATE"],
                "target_requirement": "USE_NAMED_FIELDS_AND_DO_NOT_COPY_POSITIONAL_SESSION_ASSIGNMENT_WITHOUT_DYNAMIC_PROOF",
            },
        ]
        assertions = {
            "read_only_clone_and_denied_writer": context["updateability"] == "READ_ONLY"
            and context["can_update"] == 0
            and context["denies_data_writes"] == 1,
            "all_selected_modules_found": len(modules) == len(COMMANDS),
            "current_operation_date_rows_have_current_dc": totals["orphan_dc_count"] == 0,
            "all_semantic_assertions_pass": all(semantic_assertions.values()),
            "no_operational_command_executed": True,
        }
        return {
            "artifact": "varanegar_order_sale_operation_date_sql",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": "PASS" if all(assertions.values()) else "FAIL",
            "source": {
                "server_class": "LOCAL_READ_ONLY_CLONE",
                "database": context["database_name"],
                "login": context["login_name"],
            },
            "safety": {
                "connection_readonly": True,
                "operational_stored_procedure_executions": 0,
                "dc_ids_user_ids_or_business_document_rows_persisted": 0,
                "raw_sql_definitions_messages_or_string_literals_persisted": 0,
                "source_or_target_state_changed": 0,
            },
            "summary": {
                "selected_sql_module_count": len(modules),
                "operation_date_profile_count": len(profiles),
                **{key: int(value or 0) for key, value in totals.items()},
                **{key: int(value or 0) for key, value in sale_boundary_totals.items()},
                **special_type_totals,
            },
            "modules": modules,
            "anonymous_operation_date_profiles": profiles,
            "date_open_exception_type_profiles": special_type_profiles,
            "semantic_contracts": semantic_contracts,
            "semantic_assertions": semantic_assertions,
            "assertions": assertions,
            "limits": [
                "Current anonymous operation-date rows do not prove the session date used by any historical conversion.",
                "Static SQL establishes validation capability and parameter flow, not branch frequency.",
            ],
        }, diagnostics
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--diagnostic-redacted-lines", action="store_true")
    args = parser.parse_args()
    artifact, diagnostics = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(artifact["validation"])
    if args.diagnostic_redacted_lines:
        print("\n".join(diagnostics))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
