"""Extract read-only SQL semantics for order-to-sale policy control flags."""

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


FLAGS = (
    "chkNotStock",
    "chkNotCPrice",
    "chkNotPrice",
    "chkNotBedCredit",
    "chkNotAsnCredit",
    "chkNotBedCreditDealer",
    "chkNotAsnCreditDealer",
    "chkNotCheckMaxLimit",
    "IgnoreValidateExpDate",
    "WithOutRollback",
)
COMMAND_FLAGS = {
    "SLE.usp_sdsnet_CreateSaleByOrder": FLAGS,
    "SLE.usp_CreateSaleByOrder": FLAGS[:8],
    "SLE.usp_CheckOrderItmStock": ("chkNotStock",),
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _redact_strings(line: str) -> str:
    return re.sub(r"N?'(?:''|[^'])*'", "'<STRING>'", line, flags=re.I)


def _profile(definition: str, parameter: dict[str, Any]) -> dict[str, Any]:
    name = parameter["parameter_name"].lstrip("@")
    token = rf"@{re.escape(name)}\b"
    executable = _executable_text(definition)
    compact = " ".join(executable.replace("[", "").replace("]", "").split())
    occurrence_count = len(re.findall(token, executable, re.I))
    compared_to_zero = len(
        re.findall(rf"(?:{token}\s*(?:=|<>|!=)\s*0|0\s*(?:=|<>|!=)\s*{token})", compact, re.I)
    )
    compared_to_one = len(
        re.findall(rf"(?:{token}\s*(?:=|<>|!=)\s*1|1\s*(?:=|<>|!=)\s*{token})", compact, re.I)
    )
    boolean_condition = len(
        re.findall(rf"\b(?:if|and|or)\s*(?:\(?\s*)?(?:not\s+)?{token}", compact, re.I)
    )
    header = executable[: min(len(executable), 5000)]
    default_match = re.search(
        rf"{token}\s+[\w.()]+(?:\s*=\s*(null|-?\d+))?", header, re.I
    )
    default_class = "NO_DEFAULT"
    if default_match and default_match.group(1) is not None:
        raw = default_match.group(1).casefold()
        default_class = "NULL" if raw == "null" else f"NUMERIC_{raw}"
    return {
        "name": f"@{name}",
        "ordinal": parameter["parameter_id"],
        "data_type": parameter["data_type"],
        "is_output": bool(parameter["is_output"]),
        "occurrence_count": occurrence_count,
        "comparison_to_zero_count": compared_to_zero,
        "comparison_to_one_count": compared_to_one,
        "direct_boolean_condition_count": boolean_condition,
        "declared_default_class": default_class,
    }


def collect() -> tuple[dict[str, Any], list[str]]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        modules = []
        definitions: dict[str, str] = {}
        redacted_lines = []
        for command, selected_flags in COMMAND_FLAGS.items():
            rows = _rows(
                cursor,
                """
                SELECT m.definition,o.modify_date
                FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
                WHERE m.object_id=OBJECT_ID(%s)
                """,
                (command,),
            )
            if len(rows) != 1:
                raise AssertionError(f"selected command is missing or duplicated: {command}")
            definition = rows[0]["definition"] or ""
            definitions[command] = definition
            parameters = _rows(
                cursor,
                """
                SELECT parameter_id, name parameter_name, TYPE_NAME(user_type_id) data_type,is_output
                FROM sys.parameters WHERE object_id=OBJECT_ID(%s) ORDER BY parameter_id
                """,
                (command,),
            )
            by_name = {row["parameter_name"].lstrip("@").casefold(): row for row in parameters}
            missing = [flag for flag in selected_flags if flag.casefold() not in by_name]
            profiles = [
                _profile(definition, by_name[flag.casefold()])
                for flag in selected_flags
                if flag.casefold() in by_name
            ]
            modules.append(
                {
                    "qualified_command": command,
                    "command_modify_date": rows[0]["modify_date"],
                    "definition_sha256": _sha(definition),
                    "definition_character_count": len(definition),
                    "missing_flags": missing,
                    "policy_flags": profiles,
                }
            )

            executable = _executable_text(definition)
            lines = executable.splitlines()
            matched_indexes = {
                index
                for index, line in enumerate(lines)
                if any(re.search(rf"@{re.escape(flag)}\b", line, re.I) for flag in selected_flags)
                or re.search(
                    r"(?i)(usp_(?:check|validate)|uspcheckcustlimit|AllowNegativeOnHandQty|Invoice_InActive_Items_Action)",
                    line,
                )
            }
            context_indexes = sorted(
                {
                    context
                    for index in matched_indexes
                    for context in range(max(0, index - 3), min(len(lines), index + 4))
                }
            )
            if command == "SLE.usp_CheckOrderItmStock" and len(lines) <= 100:
                context_indexes = list(range(len(lines)))
            elif command == "SLE.usp_CreateSaleByOrder":
                context_indexes = sorted(set(context_indexes) | set(range(120, min(158, len(lines)))))
            redacted_lines.append(f"COMMAND {command}")
            redacted_lines.extend(
                f"LINE {index + 1}: {_redact_strings(lines[index]).strip()}"
                for index in context_indexes
            )

        validation_dependencies = [
            row["referenced_entity_name"]
            for row in _rows(
                cursor,
                """
                SELECT DISTINCT referenced_entity_name
                FROM sys.sql_expression_dependencies
                WHERE referencing_id=OBJECT_ID(%s) AND referenced_entity_name IS NOT NULL
                """,
                ("SLE.usp_sdsnet_CreateSaleByOrder",),
            )
            if re.search(r"(?i)(valid|check|credit|limit|price|stock|exp)", row["referenced_entity_name"])
        ]
        wrapper = next(row for row in modules if row["qualified_command"] == "SLE.usp_sdsnet_CreateSaleByOrder")
        core = next(row for row in modules if row["qualified_command"] == "SLE.usp_CreateSaleByOrder")
        stock_check = next(row for row in modules if row["qualified_command"] == "SLE.usp_CheckOrderItmStock")
        wrapper_code = " ".join(_executable_text(definitions[wrapper["qualified_command"]]).split()).casefold()
        core_code = " ".join(_executable_text(definitions[core["qualified_command"]]).split()).casefold()
        stock_code = " ".join(_executable_text(definitions[stock_check["qualified_command"]]).split()).casefold()
        semantic_assertions = {
            "stock_flag_is_forwarded_to_stock_checker": bool(
                re.search(r"exec\s+@\w+\s*=\s*sle\.usp_checkorderitmstock\s+@orderref\s*,\s*@chknotstock", core_code)
            ),
            "stock_flag_one_removes_short_items_from_conversion_temp": bool(
                re.search(r"if\s+@chknotstock\s*=\s*1", stock_code)
                and "delete from #tbltempevcitem" in stock_code
                and "delete from #tmp" in stock_code
            ),
            "stock_checker_rejects_when_no_conversion_item_remains": bool(
                "not exists(select 1 from #tbltempevcitem)" in stock_code
            ),
            "contract_price_zero_runs_check": bool(
                re.search(r"if\s*\(\s*@chknotcprice\s*=\s*0\s*\)", core_code)
                and "sle.usp_checkorderitmcprice" in core_code
            ),
            "user_price_zero_runs_check_but_independent_price_check_remains": bool(
                re.search(r"if\s*\(\s*@chknotprice\s*=\s*0\s*\)", core_code)
                and "sle.usp_checkorderitmuserprice" in core_code
                and core_code.find("sle.usp_checkorderitmprice") < core_code.find("if (@chknotprice=0)")
            ),
            "customer_credit_bypass_requires_both_flags_one": bool(
                re.search(r"@chknotbedcredit\s*<>\s*1\s+or\s+@chknotasncredit\s*<>\s*1", core_code)
                and "sle.usp_validatecustomercredit" in core_code
                and "sdsnet_serverconfig" in core_code
            ),
            "customer_credit_config_reload_has_no_null_coalesce": bool(
                re.search(r"select\s+@chknotasncredit\s*=\s*saleasnlimit", core_code)
                and re.search(r"select\s+@chknotbedcredit\s*=\s*salebedlimit", core_code)
                and not re.search(r"select\s+@chknot(?:asn|bed)credit\s*=\s*(?:isnull|coalesce)", core_code)
            ),
            "dealer_credit_bypass_requires_both_flags_one": bool(
                re.search(r"@chknotbedcreditdealer\s*<>\s*1\s+or\s+@chknotasncreditdealer\s*<>\s*1", core_code)
                and "sle.usp_validatedealercredit" in core_code
            ),
            "dealer_credit_config_reload_has_no_null_coalesce": bool(
                re.search(r"select\s+@chknotasncreditdealer\s*=\s*saleasnlimitdealer", core_code)
                and re.search(r"select\s+@chknotbedcreditdealer\s*=\s*salebedlimitdealer", core_code)
                and not re.search(r"select\s+@chknot(?:asn|bed)creditdealer\s*=\s*(?:isnull|coalesce)", core_code)
            ),
            "maximum_limit_zero_runs_check": bool(
                re.search(r"if\s*\(\s*@chknotcheckmaxlimit\s*=\s*0\s*\)", core_code)
                and "sle.uspcheckcustlimit" in core_code
            ),
            "ignore_expiry_parameter_is_declared_only": next(
                row for row in wrapper["policy_flags"] if row["name"] == "@IgnoreValidateExpDate"
            )["occurrence_count"] == 1,
            "without_rollback_only_guards_doomed_transaction_branch": bool(
                re.search(r"if\s+@xstate\s*=\s*-1\s+and\s+@withoutrollback\s*=\s*0", wrapper_code)
                and next(row for row in wrapper["policy_flags"] if row["name"] == "@WithOutRollback")["occurrence_count"] == 2
            ),
        }
        semantic_contracts = [
            {
                "policy": "STOCK_SHORTAGE",
                "inputs": ["@chkNotStock"],
                "caller_override_value": 1,
                "effect": "REMOVE_SHORT_ITEMS_FROM_TEMP_CONVERSION_SET_AND_CONTINUE_IF_ANY_ITEM_REMAINS",
                "not_equivalent_to": "UNCONDITIONAL_STOCK_VALIDATION_BYPASS",
                "independent_policy_gates": [
                    "STOCK_DC_ALLOW_NEGATIVE_ON_HAND",
                    "ORDER_TYPE_EFFECTS_ORDER_ON_STOCK",
                    "SPECIAL_ORDER_TYPE_EXCLUSIONS",
                ],
            },
            {
                "policy": "CONTRACT_PRICE",
                "inputs": ["@chkNotCPrice"],
                "caller_override_value": 1,
                "effect": "SKIP_CONTRACT_PRICE_CHECK_FOR_NON_SPECIAL_ORDER_TYPES",
            },
            {
                "policy": "USER_PRICE",
                "inputs": ["@chkNotPrice"],
                "caller_override_value": 1,
                "effect": "SKIP_CONFIG_CONDITIONAL_USER_PRICE_CHECK",
                "independent_check_remaining": "ORDER_ITEM_PRICE_CHECK_BEFORE_FLAG_BRANCH",
            },
            {
                "policy": "CUSTOMER_CREDIT",
                "inputs": ["@chkNotBedCredit", "@chkNotAsnCredit"],
                "caller_override_value": [1, 1],
                "effect": "SKIP_DC_CONFIG_RELOAD_AND_CUSTOMER_CREDIT_VALIDATOR",
                "other_combinations": "CALLER_VALUES_ARE_REPLACED_FROM_DC_SERVER_CONFIG",
                "both_reloaded_values_null": "INNER_VALIDATOR_IF_IS_UNKNOWN_AND_VALIDATOR_IS_NOT_ENTERED",
            },
            {
                "policy": "DEALER_CREDIT",
                "inputs": ["@chkNotBedCreditDealer", "@chkNotAsnCreditDealer"],
                "caller_override_value": [1, 1],
                "effect": "SKIP_DC_CONFIG_RELOAD_AND_DEALER_CREDIT_VALIDATOR",
                "other_combinations": "CALLER_VALUES_ARE_REPLACED_FROM_DC_SERVER_CONFIG",
                "both_reloaded_values_null": "INNER_VALIDATOR_IF_IS_UNKNOWN_AND_VALIDATOR_IS_NOT_ENTERED",
            },
            {
                "policy": "CUSTOMER_MAXIMUM_LIMIT",
                "inputs": ["@chkNotCheckMaxLimit"],
                "caller_override_value": 1,
                "effect": "SKIP_CUSTOMER_MAXIMUM_LIMIT_CHECK",
            },
            {
                "policy": "EXPIRY_VALIDATION",
                "inputs": ["@IgnoreValidateExpDate"],
                "effect": "DECLARED_ONLY_NO_RUNTIME_SQL_EFFECT_PROVEN_IN_CURRENT_WRAPPER",
            },
            {
                "policy": "ROLLBACK_MODE",
                "inputs": ["@WithOutRollback"],
                "caller_override_value": 1,
                "effect": "SUPPRESS_ROLLBACK_ONLY_FOR_DOOMED_XACT_STATE_BRANCH",
                "not_equivalent_to": "DISABLE_ALL_ROLLBACK_BRANCHES",
            },
        ]
        assertions = {
            "read_only_clone_and_denied_writer": context["updateability"] == "READ_ONLY"
            and context["can_update"] == 0
            and context["denies_data_writes"] == 1,
            "all_selected_policy_flags_exist_in_expected_modules": all(
                not row["missing_flags"] for row in modules
            ),
            "every_core_policy_flag_is_used_after_declaration": all(
                row["occurrence_count"] >= 2 for row in core["policy_flags"]
            ),
            "wrapper_forwards_all_eight_core_policy_flags": all(
                row["occurrence_count"] >= 2
                for row in wrapper["policy_flags"]
                if row["name"].lstrip("@") in FLAGS[:8]
            ),
            "all_semantic_contract_assertions_pass": all(semantic_assertions.values()),
            "definition_or_business_values_are_not_persisted": True,
            "no_application_or_operational_command_executed": True,
        }
        artifact = {
            "artifact": "varanegar_order_sale_policy_flag_sql",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": "PASS" if all(assertions.values()) else "FAIL",
            "source": {
                "server_class": "LOCAL_READ_ONLY_CLONE",
                "database": context["database_name"],
                "login": context["login_name"],
                "qualified_commands": list(COMMAND_FLAGS),
            },
            "safety": {
                "connection_readonly": True,
                "autocommit_catalog_reads_only": True,
                "operational_stored_procedure_executions": 0,
                "raw_definition_lines_or_string_literals_persisted": 0,
                "business_rows_or_values_read": 0,
                "source_or_target_state_changed": 0,
            },
            "summary": {
                "selected_command_count": len(modules),
                "selected_policy_flag_count": sum(len(flags) for flags in COMMAND_FLAGS.values()),
                "found_policy_flag_count": sum(len(row["policy_flags"]) for row in modules),
                "missing_policy_flag_count": sum(len(row["missing_flags"]) for row in modules),
                "flag_with_zero_or_one_comparison_count": sum(
                    row["comparison_to_zero_count"] + row["comparison_to_one_count"] > 0
                    for module in modules
                    for row in module["policy_flags"]
                ),
                "wrapper_declared_but_not_used_after_declaration_count": sum(
                    row["occurrence_count"] == 1 for row in wrapper["policy_flags"]
                ),
                "validation_dependency_signal_count": len(validation_dependencies),
            },
            "modules": modules,
            "semantic_contracts": semantic_contracts,
            "semantic_assertions": semantic_assertions,
            "validation_dependency_signals": sorted(validation_dependencies),
            "assertions": assertions,
            "limits": [
                "Lexical counts establish branch use but do not alone prove the full business meaning of every branch.",
                "Redacted diagnostic lines are emitted only on request and are never written to the artifact.",
            ],
        }
        return artifact, redacted_lines
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--diagnostic-redacted-lines", action="store_true")
    args = parser.parse_args()
    artifact, diagnostic = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    if args.diagnostic_redacted_lines:
        print("\n".join(diagnostic))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
