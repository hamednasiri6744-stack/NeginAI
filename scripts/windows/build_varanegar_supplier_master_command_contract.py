"""Build a focused static Supplier master command contract from redacted IL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


FORM = "VN.SDS.MainData.UI.Supplier.FormSupplier"
METHODS = {
    "ApplyUserPermission", "CreateNewDataObject", "DeleteCommand",
    "EconCodeTextEdit_KeyPress", "GetDataAttachmentAnNoteObject",
    "LoadDetailData", "LoadInitData", "LoadLayout", "LoadLookups",
    "NationalCodeTextEdit_KeyPress", "SaveCommand", "SetLookUpDefaults",
    "SetUIVisibility", "TextEditLengthSet", "UIEnableEditing",
    "UIOnPostCommandExecute", "UIOnPreCommandExecute",
    "ValidateCurrentData", "ValidateData",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    located = []
    for assembly in source["raw_il"]:
        for target in assembly["target_types"]:
            if target["type"] == FORM:
                located.append((assembly, target))
    errors: list[str] = []
    if len(located) != 1:
        errors.append(f"expected one Supplier form, found {len(located)}")
    methods = []
    all_calls: set[str] = set()
    all_fields: set[str] = set()
    assembly_info = None
    if located:
        assembly, target = located[0]
        assembly_info = {"file": assembly["file"], "sha256": assembly["sha256"]}
        by_name = {row["method"]: row for row in target["methods"]}
        errors.extend(f"method missing: {name}" for name in sorted(METHODS - set(by_name)))
        for name in sorted(METHODS & set(by_name)):
            row = by_name[name]
            calls = sorted(set(row["calls"]))
            fields = sorted(x for x in row["referenced_fields"] if x.startswith(FORM + "."))
            all_calls.update(calls)
            all_fields.update(fields)
            methods.append({
                "method": name,
                "instruction_count": row["instruction_count"],
                "referenced_form_fields": fields,
                "business_calls": [x for x in calls if ".Business." in x],
                "data_context_calls": [x for x in calls if x.startswith("Thunderstruck.DataContext")],
                "permission_calls": [x for x in calls if "Permission" in x],
                "configuration_calls": [x for x in calls if "Config" in x or "FilterRange" in x],
                "validator_or_guard_calls": [x for x in calls if any(y in x for y in ("Valid", "IsUsed", "Check", "BeforeSave"))],
                "entity_setters": [x for x in calls if ".Entity." in x and ".set_" in x],
                "runtime_branch_values_and_effects_proven": False,
            })
    signal_needles = {
        "SUPPLIER_PERMISSION_SCOPE": ("HasPermission",),
        "SUPPLIER_PAYMENT_USAGE_DELETE_GUARD": ("IsUsedInPay",),
        "SUPPLIER_AFTER_SAVE_HOOK": ("AfterSaveSupplier",),
        "SUPPLIER_CONTACT_AND_DL_RELATION": ("ContactDLCode", "set_ContactId", "set_DLCode"),
        "SUPPLIER_ACCOUNTING_GROUP_RELATION": ("AccountingSupplierGroup",),
        "SUPPLIER_STATUS_LOOKUP": ("StatusGridLookUp",),
        "SUPPLIER_NATIONAL_AND_ECONOMIC_CODE_INPUT_RULE": ("NationalCode", "EconCode"),
        "SUPPLIER_ATTACHMENT_SIZE_CONFIG": ("AttachmentSize",),
        "SHARED_DATA_CONTEXT_COMMIT": ("Thunderstruck.DataContext.Commit",),
    }
    signals = sorted(name for name, needles in signal_needles.items() if any(needle.casefold() in call.casefold() for needle in needles for call in all_calls))
    artifact = {
        "artifact": "varanegar_supplier_master_static_command_validation_permission_relation_contract",
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
            "target_form_count": 1,
            "resolved_target_form_count": 1 if located else 0,
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "unique_referenced_form_field_count": len(all_fields),
            "unique_rule_signal_count": len(signals),
            "method_with_data_context_commit_count": sum("Thunderstruck.DataContext.Commit" in row["data_context_calls"] for row in methods),
            "owner_approved_contract_count": 0,
            "implementation_ready_contract_count": 0,
            "runtime_effect_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "contract": {
            "form_type": FORM,
            "assembly": assembly_info,
            "methods": methods,
            "target_command_candidate": "master_data.supplier.save",
            "secondary_delete_command_candidate": "master_data.supplier.delete",
            "rule_signals": signals,
            "owner_approved": False,
            "implementation_ready": False,
            "runtime_effect_parity_proven": False,
        },
        "validation_errors": errors,
        "limits": [
            "Static calls do not prove effective permissions, requiredness, branch order, lookup values, or successful effects.",
            "Supplier delete must preserve payment, accounting, cardex, contact, attachment, and document provenance.",
            "Supplier is a separate role/aggregate boundary; do not flatten it into customer despite shared party/contact concepts.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
