"""Build focused static command contracts for order, sale, and return entry."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


TARGETS = {
    "VN.SDS.Sales.UI.Order.FormOrderDataEntry": {
        "workflow": "sales_order_entry",
        "target_command_candidate": "order.save",
        "extra_methods": {"ViewObjectAndCancelConfirmCheck"},
    },
    "VN.SDS.Sales.UI.Sale.FormSaleDataEntry": {
        "workflow": "order_to_sale_entry",
        "target_command_candidate": "order.convert_to_sale",
        "extra_methods": set(),
    },
    "VN.SDS.Sales.UI.RetSale.FormRetSaleDataEntry": {
        "workflow": "sales_return_entry",
        "target_command_candidate": "sales_return.save",
        "extra_methods": set(),
    },
}

REQUIRED_METHODS = {
    "CreateNewDataObject",
    "ValidateCurrentData",
    "ValidateData",
    "SaveCommand",
    "UIOnPostCommandExecute",
}

OPTIONAL_METHODS = {"ApplyUserPermission"}

ACTION_SUFFIXES = (
    ".SaveCommand",
    ".SaveCommandFromPeygiri",
    ".AfterSaveOrder",
    ".AfterSaveRetSale",
    ".DirectOrderToSale",
    ".OrderToSaleSaveCommand",
    ".InsertOrderCredit",
    ".UpdateOrderCredit",
    ".SaveNewBatchNumberS",
    ".UpdateOrderNo",
    ".DoEVC",
    ".UpdateEVCTable",
)

RULE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("CUSTOMER_CREDIT_GUARD", ("CustomerCredit", "ValidateCustomerCredit")),
    ("DEALER_OR_SUPERVISOR_CREDIT_GUARD", ("DealerCredit", "OrderCredit")),
    ("STOCK_ON_HAND_GUARD", ("StockQty", "OnHand", "Mojodi")),
    ("RESERVED_QUANTITY_GUARD", ("ReservedOrderQty", "RemPishForooshQty")),
    ("CONTRACT_OR_PUBLIC_PRICE_GUARD", ("CPrice", "Price")),
    ("DUPLICATE_LINE_GUARD", ("DuplicateOrder", "DuplicateOrderItm")),
    ("BATCH_OR_SERIAL_GUARD", ("Batch", "SerialNo")),
    ("CUSTOMER_GOODS_OR_PREVENT_SALE_GUARD", ("CheckGoodsCust", "PreventSale", "GoodsNoSale")),
    ("PAYMENT_USANCE_GUARD", ("PaymentUsance",)),
    ("DIRECT_ORDER_TO_SALE_BRANCH", ("DirectOrderToSale", "OrderToSaleSaveCommand")),
    ("EVC_PRICING_OR_PRIZE_BRANCH", ("EVC", "Evc", "Prize")),
    ("CONFIRM_CANCEL_EDITABILITY_GUARD", ("Confirm", "CancelFlag")),
    ("RETURN_SOURCE_OR_REMAINING_GUARD", ("Remaining", "MandeFactor", "FactorIsNotReturnable", "RetOrder")),
    ("RETURN_HEALTH_CODE_OR_PERMISSION_GUARD", ("HealthCode", "Permission")),
    ("RETURN_STOCK_CONTROL_BRANCH", ("ControlStockRetSale",)),
)


def _role(method: str) -> str:
    if method == "SaveCommand":
        return "mutation_command_boundary"
    if method in {"ValidateData", "ValidateCurrentData"}:
        return "validation_boundary"
    if method == "UIOnPostCommandExecute":
        return "post_command_ui_boundary"
    if method == "ApplyUserPermission":
        return "permission_projection_boundary"
    if method == "CreateNewDataObject":
        return "new_draft_default_boundary"
    return "state_editability_boundary"


def _rule_signals(calls: list[str]) -> list[str]:
    return sorted(
        signal
        for signal, fragments in RULE_PATTERNS
        if any(fragment.casefold() in call.casefold() for fragment in fragments for call in calls)
    )


def _safe_fragments(method: dict[str, Any]) -> list[str]:
    return sorted(
        {
            row["safe_literal"]
            for row in method["string_literals"]
            if row.get("persisted_as") == "allowlisted_business_literal"
            and row.get("safe_literal")
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    located: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for assembly in source["raw_il"]:
        for target in assembly["target_types"]:
            if target["type"] in TARGETS:
                located[target["type"]] = (assembly, target)

    errors: list[str] = []
    contracts: list[dict[str, Any]] = []
    all_fields: set[str] = set()
    all_action_calls: set[str] = set()
    all_first_party_business_calls: set[str] = set()
    all_first_party_data_access_calls: set[str] = set()
    all_rule_signals: set[str] = set()
    all_config_getters: set[str] = set()
    total_instruction_count = 0
    direct_sql_method_count = 0
    commit_method_count = 0
    for type_name, settings in TARGETS.items():
        if type_name not in located:
            errors.append(f"target type missing: {type_name}")
            continue
        assembly, target = located[type_name]
        required = REQUIRED_METHODS | settings["extra_methods"]
        wanted = required | OPTIONAL_METHODS
        by_name = {row["method"]: row for row in target["methods"]}
        missing = sorted(required - set(by_name))
        if missing:
            errors.append(f"selected methods missing for {type_name}: {missing}")
        methods = []
        for method_name in sorted(wanted & set(by_name)):
            method = by_name[method_name]
            calls = method["calls"]
            form_fields = sorted(
                field for field in method["referenced_fields"] if field.startswith(type_name + ".")
            )
            action_calls = sorted(call for call in calls if call.endswith(ACTION_SUFFIXES))
            first_party_business_calls = sorted(
                call for call in calls
                if call.startswith("VN.SDS.") and ".Business." in call
            )
            first_party_data_access_calls = sorted(
                call for call in calls
                if call.startswith("VN.SDS.") and ".DataAccess." in call
            )
            data_context_calls = sorted(
                call for call in calls
                if call.startswith("Thunderstruck.DataContext.")
            )
            direct_sql_calls = sorted(
                call for call in calls
                if call.endswith((".ExecuteNonQuery", ".ExecuteScalar", ".ExecuteReader"))
            )
            entity_setters = sorted(
                call for call in calls
                if ".Entity." in call and ".set_" in call
            )
            helper_setters = sorted(
                call for call in calls
                if ".EntityHelper." in call and ".set_" in call
            )
            config_getters = sorted(
                call for call in calls
                if ("ServerConfigEntity.get_" in call or "GeneralConfigEntity.get_" in call)
            )
            context_getters = sorted(
                call for call in calls if "UserSessionInfo.get_" in call
            )
            validators = sorted(
                call for call in calls
                if any(fragment in call for fragment in ("Validator", "Validation", ".Validate", ".Check"))
            )
            permission_calls = sorted(
                call for call in calls if "Permission" in call or "Persmission" in call
            )
            signals = _rule_signals(calls)
            total_instruction_count += method["instruction_count"]
            direct_sql_method_count += int(bool(direct_sql_calls))
            commit_method_count += int("Thunderstruck.DataContext.Commit" in calls)
            all_fields.update(form_fields)
            all_action_calls.update(action_calls)
            all_first_party_business_calls.update(first_party_business_calls)
            all_first_party_data_access_calls.update(first_party_data_access_calls)
            all_rule_signals.update(signals)
            all_config_getters.update(config_getters)
            methods.append(
                {
                    "method": method_name,
                    "role": _role(method_name),
                    "instruction_count": method["instruction_count"],
                    "referenced_form_fields": form_fields,
                    "business_action_calls": action_calls,
                    "first_party_business_calls": first_party_business_calls,
                    "first_party_data_access_calls": first_party_data_access_calls,
                    "data_context_calls": data_context_calls,
                    "direct_sql_execution_calls": direct_sql_calls,
                    "entity_property_setters": entity_setters,
                    "helper_input_setters": helper_setters,
                    "configuration_getters": config_getters,
                    "user_context_getters": context_getters,
                    "validator_or_check_calls": validators,
                    "permission_calls": permission_calls,
                    "rule_signals": signals,
                    "allowlisted_structural_literals": _safe_fragments(method),
                    "branch_order_runtime_values_and_effects_proven": False,
                }
            )
        save = next((row for row in methods if row["method"] == "SaveCommand"), None)
        if save is None or not save["business_action_calls"]:
            errors.append(f"save command business action missing for {type_name}")
        contracts.append(
            {
                "workflow": settings["workflow"],
                "form_type": type_name,
                "assembly": assembly["file"],
                "assembly_sha256": assembly["sha256"],
                "selected_method_count": len(methods),
                "permission_override_present": "ApplyUserPermission" in by_name,
                "methods": methods,
                "rule_signals": sorted(
                    {signal for method in methods for signal in method["rule_signals"]}
                ),
                "target_command_candidate": settings["target_command_candidate"],
                "legacy_boundary": "UI_SAVE_ORCHESTRATES_DOMAIN_HANDLERS_AND_SHARED_DATA_CONTEXT",
                "target_boundary_candidate": "WEB_SUBMITS_VERSIONED_IDEMPOTENT_COMMAND_APPLICATION_HANDLER_OWNS_ATOMICITY",
                "owner_approved": False,
                "runtime_success_or_effect_parity_proven": False,
            }
        )

    artifact = {
        "artifact": "varanegar_order_sale_return_entry_static_command_validation_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_HASHED_REDACTED_DATA_ENTRY_IL",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "application_or_business_commands_executed": 0,
            "raw_non_allowlisted_literals_or_business_values_persisted": 0,
            "runtime_branch_order_values_success_or_effects_inferred": 0,
        },
        "summary": {
            "target_form_count": len(TARGETS),
            "resolved_target_form_count": len(contracts),
            "selected_method_count": sum(row["selected_method_count"] for row in contracts),
            "selected_instruction_count": total_instruction_count,
            "unique_referenced_form_field_count": len(all_fields),
            "unique_business_action_call_count": len(all_action_calls),
            "unique_first_party_business_call_count": len(
                all_first_party_business_calls
            ),
            "unique_first_party_data_access_call_count": len(
                all_first_party_data_access_calls
            ),
            "unique_configuration_getter_count": len(all_config_getters),
            "unique_rule_signal_count": len(all_rule_signals),
            "form_with_permission_override_count": sum(
                row["permission_override_present"] for row in contracts
            ),
            "method_with_data_context_commit_count": commit_method_count,
            "method_with_direct_sql_execution_count": direct_sql_method_count,
            "owner_approved_contract_count": 0,
            "runtime_success_or_effect_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "contracts": contracts,
        "validation_errors": errors,
        "limits": [
            "Static call co-occurrence does not prove branch order, effective configuration values, messages, rollback or successful effects.",
            "Business action calls identify orchestration boundaries but not every transitive SQL target or trigger effect.",
            "Target command names are review candidates and remain unapproved until owner and Golden-case closure.",
            "A shared DataContext Commit signal does not by itself prove every called handler participates in one atomic transaction.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
