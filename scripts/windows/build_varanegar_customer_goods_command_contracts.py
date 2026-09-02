"""Build focused customer and goods master-data command contracts from static IL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


TARGETS = {
    "VN.SDS.Sales.UI.Customers.FormCustomers": {
        "command": "master_data.customer.save",
        "methods": {"CreateNewDataObject", "SaveCommand", "DeleteCommand", "ApplyUserPermission", "ApplySetadPermission", "ValidateCurrentData", "ValidateData", "UIOnPostCommandExecute", "gridView_ValidateRow"},
    },
    "VN.SDS.MainData.UI.Goods.FormGoods": {
        "command": "master_data.goods.save",
        "methods": {"CreateNewDataObject", "SaveCommand", "DeleteCommand", "ApplySetadPermission", "ValidateCurrentData", "ValidateData", "UIValidateCommand", "UIOnPostCommandExecute", "BatchPackageValidation", "PackageSaveBtn_Click", "GridGoodsBarcode_RowUpdated", "GridGoodsSupplier_KeyDown"},
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
    errors = []
    contracts = []
    all_calls: set[str] = set()
    all_fields: set[str] = set()
    for form, settings in TARGETS.items():
        if form not in located:
            errors.append(f"form missing: {form}")
            continue
        assembly, target = located[form]
        by_name = {row["method"]: row for row in target["methods"]}
        missing = settings["methods"] - set(by_name)
        errors.extend(f"method missing for {form}: {name}" for name in sorted(missing))
        methods = []
        for name in sorted(settings["methods"] & set(by_name)):
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
                "permission_calls": [x for x in calls if "Permission" in x],
                "configuration_calls": [x for x in calls if "ConfigEntity.get_" in x or "GlobalVariables" in x],
                "validator_or_check_calls": [x for x in calls if any(y in x for y in ("Valid", "Check", "BeforeSave"))],
                "entity_setters": [x for x in calls if ".Entity." in x and ".set_" in x],
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
    fragments = {
        "CUSTOMER_PERMISSION_AND_HEADQUARTERS_SCOPE": ("HasPermission", "ApplySetadPermission"),
        "CUSTOMER_PARENT_AND_DL_CODE_RULE": ("ParentCustomerId", "AutoupdatDLCodeToCustCode"),
        "CUSTOMER_STATUS_AND_CREDIT_ACCOUNT_RULE": ("SetCustomerStatus", "CustAccountValidator"),
        "GOODS_BARCODE_RELATION": ("GoodsBarcode",),
        "GOODS_SUPPLIER_RELATION": ("GoodsSupplier", "GetValidSupplier"),
        "GOODS_BATCH_PACKAGE_RULE": ("BatchPackage",),
        "GOODS_PACKAGE_RULE": ("PackageValidation", "PackageHandler"),
        "GOODS_GROUP_CROSSWALK_RULE": ("ProductMainGroupUniqueId", "ProductSubGroupUniqueId"),
        "GOODS_REPLICATION_DELETE_GUARD": ("AllowDeleteGoodsAfterReplicate",),
        "SHARED_DATA_CONTEXT_COMMIT": ("Thunderstruck.DataContext.Commit",),
    }
    signals = sorted(name for name, needles in fragments.items() if any(needle.casefold() in call.casefold() for needle in needles for call in all_calls))
    artifact = {
        "artifact": "varanegar_customer_goods_master_data_static_command_validation_permission_contracts",
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
            "selected_method_count": sum(x["selected_method_count"] for x in contracts),
            "selected_instruction_count": sum(m["instruction_count"] for x in contracts for m in x["methods"]),
            "unique_referenced_form_field_count": len(all_fields),
            "unique_rule_signal_count": len(signals),
            "method_with_data_context_commit_count": sum("Thunderstruck.DataContext.Commit" in m["data_context_calls"] for x in contracts for m in x["methods"]),
            "owner_approved_contract_count": 0,
            "implementation_ready_contract_count": 0,
            "runtime_effect_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "contracts": contracts,
        "rule_signals": signals,
        "validation_errors": errors,
        "limits": [
            "Static calls do not prove effective permissions, configuration values, branch order, binding or successful effects.",
            "Customer and goods delete commands need separate usage, replication, merge and dependency Golden contracts.",
            "Goods barcode, supplier, package, batch and DC relations must remain child aggregates rather than flattened fields.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
