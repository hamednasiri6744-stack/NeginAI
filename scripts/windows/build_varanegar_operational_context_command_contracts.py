"""Build static operational-year, stock/DC, and stock-accounting contracts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


TARGETS = {
    "VN.SDS.MainData.UI.AccYear.FormAccYear": {
        "command": "organization_context.operational_year.save",
        "methods": {"CreateNewDataObject", "DeleteCommand", "LoadDetailData", "LoadInitData", "LoadLayout", "SaveCommand", "ValidateCurrentData", "ValidateData"},
    },
    "VN.SDS.MainData.UI.StockDC.FormStockDC": {
        "command": "organization_context.stock_dc.save",
        "methods": {"CreateNewDataObject", "DeleteCommand", "LoadDetailData", "LoadInitData", "LoadLayout", "LoadLookups", "SaveCommand", "SetLookUpDefaults", "StockTypeValue", "UIOnPostCommandExecute", "UIOnPreCommandExecute", "UIValidateCommand", "ValidateCurrentData", "ValidateData", "StockTypeFlag1CheckEdit_CheckedChanged", "StockTypeFlag2CheckEdit_CheckedChanged", "StockTypeFlag4CheckEdit_CheckedChanged", "StockTypeFlag8CheckEdit_CheckedChanged", "StockTypeFlag16CheckEdit_CheckedChanged"},
    },
    "VN.SDS.Stock.UI.ICAstockdcinfo.FormICAstockdcinfo": {
        "command": "inventory.stock_accounting_context.save",
        "methods": {"AddRowtoStocklookup", "CreateNewDataObject", "CurrenICAstockdcinfo", "DeleteCommand", "LoadDetailData", "LoadInitData", "LoadLayout", "LoadLookups", "RemoveRowFromStocklookup", "SaveCommand", "UIOnPostCommandExecute", "UIOnPreCommandExecute", "ValidateCurrentData", "ValidateData"},
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
                "validator_or_guard_calls": [x for x in calls if any(y in x for y in ("Valid", "StockHasPrice", "Check"))],
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
    signals_by_needle = {
        "OPERATIONAL_YEAR_SEPARATE_FROM_FISCAL_YEAR": ("AccYearHandler", "AccYearValidator"),
        "STOCK_DC_TO_DC_SALE_OFFICE_RELATION": ("DCSaleOffice", "set_SORef", "set_DCRef"),
        "STOCK_DC_SHIP_TYPE_RELATION": ("ShipType",),
        "STOCK_TYPE_FIVE_FLAG_ENCODING": ("StockTypeFlag1", "StockTypeFlag2", "StockTypeFlag4", "StockTypeFlag8", "StockTypeFlag16"),
        "STOCK_DC_VALIDATION": ("StockDCValidation", "StockDCValidator"),
        "STOCK_ACCOUNTING_PRICE_METHOD": ("get_PriceMethod", "set_PriceMethod"),
        "STOCK_ACCOUNTING_CONTEXT_HAS_PRICE_GUARD": ("StockHasPrice",),
        "STOCK_ACCOUNTING_LOOKUP_MEMBERSHIP": ("StockDCGridLookUpForStockAccountingMainData",),
        "SHARED_DATA_CONTEXT_COMMIT": ("Thunderstruck.DataContext.Commit",),
    }
    signals = sorted(name for name, needles in signals_by_needle.items() if any(needle.casefold() in call.casefold() for needle in needles for call in all_calls))
    artifact = {
        "artifact": "varanegar_operational_year_stock_dc_and_stock_accounting_static_command_contracts",
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
            "Operational year is not proven interchangeable with fiscal year.",
            "Stock/DC, sale office, warehouse/stock, ship type, accounting price method, and five stock-type flags must remain distinct contracts.",
            "Static calls do not prove effective branch values, permission, requiredness, successful commit, or runtime parity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
