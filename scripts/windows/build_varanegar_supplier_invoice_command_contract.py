"""Build supplier-invoice and return command/validation contracts from static IL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


FORMS = {
    "VN.SDS.Stock.UI.SupInvoice.FormSupInvoiceDataEntry": "supplier_invoice.save",
    "VN.SDS.Stock.UI.RetSupInvoice.FormRetSupInvoiceDataEntry": "supplier_return.save",
}
SECONDARY_COMMANDS = {
    "VN.SDS.Stock.UI.SupInvoice.FormSupInvoiceDataEntry": ["supplier_invoice.delete"],
    "VN.SDS.Stock.UI.RetSupInvoice.FormRetSupInvoiceDataEntry": ["supplier_return.delete"],
}
REQUIRED = {"CreateNewDataObject", "SaveCommand", "DeleteCommand", "ValidateCurrentData", "ValidateData", "UIOnPostCommandExecute", "ApplyUserPermission"}
OPTIONAL = {"gridView_ValidateRow", "GridList_ValidatingEditor", "btnDelete_Click"}
HANDLER_PREFIXES = (
    "VN.SDS.Stock.Business.SupInvoice.",
    "VN.SDS.Stock.Business.RetSupInvoice.",
    "VN.SDS.Stock.Business.SupInvoiceTolls.",
    "VN.SDS.Stock.Business.RetSupInvoiceTolls.",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--high-impact-graph", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    graph = json.loads(args.high_impact_graph.read_text(encoding="utf-8-sig"))

    located = {}
    for assembly in source["raw_il"]:
        for target in assembly["target_types"]:
            if target["type"] in FORMS:
                located[target["type"]] = (assembly, target)
    errors: list[str] = []
    contracts = []
    all_fields: set[str] = set()
    all_calls: set[str] = set()
    for form, command in FORMS.items():
        if form not in located:
            errors.append(f"form missing: {form}")
            continue
        assembly, target = located[form]
        by_name = {row["method"]: row for row in target["methods"]}
        errors.extend(f"method missing for {form}: {name}" for name in sorted(REQUIRED - set(by_name)))
        methods = []
        for name in sorted((REQUIRED | OPTIONAL) & set(by_name)):
            row = by_name[name]
            calls = sorted(set(row["calls"]))
            all_calls.update(calls)
            fields = sorted(x for x in row["referenced_fields"] if x.startswith(form + "."))
            all_fields.update(fields)
            methods.append({
                "method": name,
                "instruction_count": row["instruction_count"],
                "referenced_form_fields": fields,
                "business_calls": [x for x in calls if ".Business." in x],
                "data_context_calls": [x for x in calls if x.startswith("Thunderstruck.DataContext")],
                "validator_or_check_calls": [x for x in calls if any(y in x for y in ("Valid", "Check", "Duplicate"))],
                "configuration_or_context_calls": [x for x in calls if any(y in x for y in ("ServerConfig", "GeneralConfig", "UserSessionInfo"))],
                "runtime_branch_order_or_effect_proven": False,
            })
        contracts.append({
            "form_type": form,
            "assembly": assembly["file"],
            "assembly_sha256": assembly["sha256"],
            "selected_method_count": len(methods),
            "methods": methods,
            "target_command_candidate": command,
            "secondary_command_candidates_without_complete_golden_contract": SECONDARY_COMMANDS[form],
            "permission_override_present": "ApplyUserPermission" in by_name,
            "owner_approved": False,
            "runtime_effect_parity_proven": False,
        })

    business = [row for row in graph["business_contracts"] if row["type"].startswith(HANDLER_PREFIXES)]
    data_access = [row for row in graph["data_access_contracts"] if "SupInvoice" in row["type"]]
    static_sql_literals = []
    for assembly in graph["raw_il"]["data_access"]:
        for target in assembly["target_types"]:
            if "SupInvoice" not in target["type"]:
                continue
            for method in target["methods"]:
                for literal in method["string_literals"]:
                    safe = literal.get("safe_literal")
                    if safe and any(token in safe.casefold() for token in ("delete from", "alter table", "exec ", "usp_")):
                        static_sql_literals.append({
                            "data_access_type": target["type"],
                            "method": method["method"],
                            "safe_literal": safe,
                            "sha256": literal["sha256"],
                            "runtime_executed": False,
                        })

    signal_fragments = {
        "SUPPLIER_ACTIVE_GUARD": ("SupplierIsActive",),
        "DUPLICATE_INVOICE_OR_GOODS_GUARD": ("Duplicate", "IsSupInvoiceNoDuplicate"),
        "QUANTITY_AND_REMAINING_GUARD": ("QtyValidation", "UnitQtyRemaining"),
        "PRICE_AND_FINAL_AMOUNT_GUARD": ("PriceGreater", "FinalEffectiveAmount"),
        "TOLL_AND_XTOLL_ORCHESTRATION": ("Toll", "XToll"),
        "SOURCE_INVOICE_AND_STOCK_VOUCHER_GUARD": ("SupInvoiceRefValidation", "InvVocherRefValidation"),
        "TRIGGER_GUARD_TOGGLE_AROUND_RELATION_DELETE": ("ENABLE TRIGGER", "DISABLE TRIGGER"),
        "SHARED_DATA_CONTEXT_COMMIT": ("Thunderstruck.DataContext.Commit",),
    }
    evidence = set(all_calls)
    evidence.update(x["safe_literal"] for x in static_sql_literals)
    for row in business:
        evidence.update(row["write_like_methods"])
        evidence.update(row["validation_like_methods"])
        evidence.update(row["transaction_signal_calls"])
    signals = sorted(name for name, fragments in signal_fragments.items() if any(f.casefold() in item.casefold() for f in fragments for item in evidence))
    artifact = {
        "artifact": "varanegar_supplier_invoice_return_static_command_validation_trigger_guard_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_HASHED_REDACTED_IL",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "live_ui_actions": 0,
            "business_or_sql_commands_executed": 0,
            "row_values_persisted": 0,
        },
        "summary": {
            "target_form_count": len(FORMS),
            "resolved_target_form_count": len(contracts),
            "selected_method_count": sum(x["selected_method_count"] for x in contracts),
            "selected_instruction_count": sum(m["instruction_count"] for x in contracts for m in x["methods"]),
            "unique_referenced_form_field_count": len(all_fields),
            "business_contract_count": len(business),
            "data_access_contract_count": len(data_access),
            "static_sql_literal_count": len(static_sql_literals),
            "trigger_enable_disable_literal_count": sum(" trigger " in x["safe_literal"].casefold() for x in static_sql_literals),
            "unique_rule_signal_count": len(signals),
            "method_with_data_context_commit_count": sum("Thunderstruck.DataContext.Commit" in m["data_context_calls"] for x in contracts for m in x["methods"]),
            "owner_approved_contract_count": 0,
            "runtime_effect_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "contracts": contracts,
        "business_contracts": business,
        "data_access_contracts": data_access,
        "static_sql_literals": static_sql_literals,
        "rule_signals": signals,
        "target_boundary": "VERSIONED_IDEMPOTENT_COMMAND_WITH_SEPARATE_SAVE_DELETE_RETURN_AND_PROTECTIVE_INVARIANT_OWNERSHIP",
        "validation_errors": errors,
        "limits": [
            "Static IL proves possible call and SQL-literal paths, not runtime branch selection, values or successful effects.",
            "TypeSpecRow persistence is generic; every concrete table and trigger effect is not yet resolved.",
            "Legacy trigger enable/disable literals are evidence to replace safely, never instructions to execute.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
