"""Build static contextual-price and discount-rule command contracts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


TARGETS = {
    "VN.SDS.MainData.UI.CPrice.FormCPrice": {
        "command": "pricing_rules.contextual_price.save",
        "methods": {
            "CreateCopyDataObject", "CreateNewDataObject", "DeleteCommand", "SaveCommand",
            "ChangePriorityOnGrid", "SetPriority", "RefreshDataAndStateAfterSave",
            "CPriceInfoClose", "CPriceMoreInfoClose", "LoadBatchNoGroupLookup",
            "LoadBatchNoLookup", "LoadUnitLookup", "LoadLookups", "SetLookUpDefaults",
            "CustRefLookUpEdit_EditValueChanged", "DCRefLookUpEdit_EditValueChanged",
            "CurrencyRefLookUpEdit_EditValueChanged", "MainCustTypeRefLookUpEdit_EditValueChanged",
            "StateRefLookUpEdit_EditValueChanged", "CountyRefLookUpEdit_EditValueChanged",
            "BuyTypeRefLookUpEdit_EditValueChanged", "BatchNoLookUpEdit_EditValueChanged",
            "BatchNoGroupLookUpEdit_EditValueChanged", "UIOnPostCommandExecute",
            "UIOnPreCommandExecute", "ValidateCurrentData", "ValidateData",
        },
    },
    "VN.SDS.MainData.UI.Discount.FormDiscount": {
        "command": "pricing_rules.discount_rule.save",
        "methods": {
            "CreateNewDataObject", "DeleteCommand", "SaveCommand", "SaveDiscountPerventSale",
            "CloseRule", "closeRulesBtn_Click", "CreateDataTables", "FillDataTables",
            "GenerateDiscountCondition", "GetGroupOperator", "checkarranges",
            "btnArranges_Click", "btnCondition_Click", "btnCustomer_Click",
            "btnCustomerGroup_Click", "btnGoodGroup_Click", "btnMultiGoods_Click",
            "btnOrder_Click", "btnOrderType_Click", "btnPrizePackInsert_Click",
            "btnRuleResult_Click", "inActiveBtn_Click", "CopyNew_Click",
            "SetGoodsDiscount", "UIOnPostCommandExecute", "UIOnPreCommandExecute",
            "UIValidateCommand", "ValidateCurrentData", "ValidateData",
        },
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    located = {}
    for assembly in source["raw_il"]:
        for target in assembly["target_types"]:
            if target["type"] in TARGETS:
                located[target["type"]] = (assembly, target)
    errors: list[str] = []
    contracts = []
    all_calls: set[str] = set()
    all_fields: set[str] = set()
    for form, settings in TARGETS.items():
        if form not in located:
            errors.append(f"form missing: {form}")
            continue
        assembly, target = located[form]
        by_name = {row["method"]: row for row in target["methods"]}
        errors.extend(f"method missing for {form}: {name}" for name in sorted(settings["methods"] - set(by_name)))
        methods = []
        for name in sorted(settings["methods"] & set(by_name)):
            row = by_name[name]
            calls = sorted(set(row["calls"]))
            fields = sorted(x for x in row["referenced_fields"] if x.startswith(form + "."))
            all_calls.update(calls)
            all_fields.update(fields)
            methods.append({
                "method": name,
                "instruction_count": row["instruction_count"],
                "referenced_form_fields": fields,
                "business_calls": [x for x in calls if ".Business." in x],
                "data_context_calls": [x for x in calls if x.startswith("Thunderstruck.DataContext")],
                "configuration_calls": [x for x in calls if "Config" in x or "Setting" in x],
                "validator_or_guard_calls": [x for x in calls if any(y in x for y in ("Valid", "Check", "Close", "Prevent"))],
                "entity_getters_and_setters": [x for x in calls if ".Entity." in x and any(y in x for y in (".get_", ".set_"))],
                "runtime_branch_values_and_effects_proven": False,
            })
        contracts.append({
            "form_type": form,
            "assembly": assembly["file"],
            "assembly_sha256": assembly["sha256"],
            "selected_method_count": len(methods),
            "methods": methods,
            "target_command_candidate": settings["command"],
            "secondary_delete_command_candidate": settings["command"].removesuffix(".save") + ".delete",
            "owner_approved": False,
            "implementation_ready": False,
            "runtime_effect_parity_proven": False,
        })
    needles = {
        "CPRICE_CUSTOMER_AND_TYPE_SCOPE": ("CustRef", "CustType"),
        "CPRICE_GEOGRAPHY_SCOPE": ("StateRef", "CountyRef"),
        "CPRICE_DC_AND_BUY_TYPE_SCOPE": ("DCRef", "BuyTypeRef"),
        "CPRICE_CURRENCY_SCOPE": ("CurrencyRef",),
        "CPRICE_BATCH_PACKAGE_UNIT_SCOPE": ("BatchNo", "Package", "Unit"),
        "CPRICE_PRIORITY_ORDER": ("Priority",),
        "CPRICE_CLOSE_AND_HISTORY": ("CPriceInfoClose", "CPriceMoreInfoClose"),
        "DISCOUNT_CUSTOMER_GOODS_ORDER_SCOPE": ("DiscountCustomer", "DiscountGoods", "DiscountOrder"),
        "DISCOUNT_GROUP_AND_DYNAMIC_SCOPE": ("DynamicGroup", "GoodsGroup", "CustomerGroup"),
        "DISCOUNT_CONDITION_DSL": ("DiscountCondition", "GroupOperator"),
        "DISCOUNT_ARRANGEMENT": ("Arrange",),
        "DISCOUNT_PRIZE_AND_PACKAGE": ("Prize", "GoodsPackage"),
        "DISCOUNT_PREVENT_SALE": ("PerventSale", "PreventSale"),
        "DISCOUNT_EFFECTIVE_STATE_AND_CLOSE": ("InActive", "CloseRule", "FutureRules"),
        "SHARED_DATA_CONTEXT_COMMIT": ("Thunderstruck.DataContext.Commit",),
    }
    signals = sorted(name for name, tokens in needles.items() if any(token.casefold() in call.casefold() for token in tokens for call in all_calls))
    artifact = {
        "artifact": "varanegar_contextual_price_and_discount_rule_static_command_scope_precedence_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_HASHED_REDACTED_DATA_ENTRY_IL",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "live_ui_actions": 0,
            "application_or_business_commands_executed": 0,
            "row_values_read_or_persisted": 0,
        },
        "summary": {
            "target_form_count": len(TARGETS),
            "resolved_target_form_count": len(contracts),
            "selected_method_count": sum(row["selected_method_count"] for row in contracts),
            "selected_instruction_count": sum(method["instruction_count"] for row in contracts for method in row["methods"]),
            "unique_referenced_form_field_count": len(all_fields),
            "unique_rule_signal_count": len(signals),
            "method_with_data_context_commit_count": sum("Thunderstruck.DataContext.Commit" in method["data_context_calls"] for row in contracts for method in row["methods"]),
            "owner_approved_contract_count": 0,
            "implementation_ready_contract_count": 0,
            "runtime_effect_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "contracts": contracts,
        "rule_signals": signals,
        "validation_errors": errors,
        "limits": [
            "Static scope and call signals do not prove effective precedence, qualification, price calculation, rounding, branch values, or runtime results.",
            "Contextual price and discount/prize rules require separate versioned publication, effective-date, priority, explain, and close/reversal contracts.",
            "Customer, product, geography, DC, batch, currency, order, arrangement, condition, and prize scopes must not be flattened into one nullable rule row.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
