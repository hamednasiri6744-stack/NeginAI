"""Build the stock-voucher UI-to-business command boundary from static IL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


FORM = "VN.SDS.Stock.UI.Vocher.FormVocherDataEntry"
HANDLER = "VN.SDS.Stock.Business.Vocher.VocherHdrHandler"
METHODS = {
    "CreateNewDataObject",
    "GridView_ValidateRow",
    "GridView_ValidatingEditor",
    "SaveCommand",
    "UIOnPreCommandExecute",
    "OnPostCommandExecute",
    "ValidateCurrentData",
    "ValidateData",
    "OtherButtonCommand",
}
TARGET_COMMANDS = [
    "stock_voucher.save",
    "stock_voucher.confirm_or_unconfirm",
    "stock_voucher.generate_return",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--high-impact-graph", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    graph = json.loads(args.high_impact_graph.read_text(encoding="utf-8-sig"))
    located = None
    assembly_row = None
    for assembly in source["raw_il"]:
        for target in assembly["target_types"]:
            if target["type"] == FORM:
                located, assembly_row = target, assembly
    errors: list[str] = []
    if located is None:
        errors.append(f"form missing: {FORM}")
        selected = []
    else:
        by_name = {row["method"]: row for row in located["methods"]}
        errors.extend(f"method missing: {name}" for name in sorted(METHODS - set(by_name)))
        selected = [by_name[name] for name in sorted(METHODS & set(by_name))]

    methods = []
    all_calls: set[str] = set()
    fields: set[str] = set()
    for row in selected:
        calls = sorted(set(row["calls"]))
        all_calls.update(calls)
        form_fields = sorted(x for x in row["referenced_fields"] if x.startswith(FORM + "."))
        fields.update(form_fields)
        methods.append(
            {
                "method": row["method"],
                "instruction_count": row["instruction_count"],
                "referenced_form_fields": form_fields,
                "business_calls": [x for x in calls if ".Business." in x],
                "data_context_calls": [x for x in calls if x.startswith("Thunderstruck.DataContext")],
                "validator_or_check_calls": [
                    x for x in calls if any(y in x for y in ("Valid", "Check", "BeforeSave"))
                ],
                "resource_rule_signals": [x for x in calls if ".Resources.Vocher_Res.get_" in x],
                "runtime_branch_order_or_effect_proven": False,
            }
        )

    handler = next((x for x in graph["business_contracts"] if x["type"] == HANDLER), None)
    if handler is None:
        errors.append(f"handler contract missing: {HANDLER}")
        handler_summary = None
    else:
        handler_summary = {
            "type": handler["type"],
            "write_like_methods": handler["write_like_methods"],
            "validation_like_methods": handler["validation_like_methods"],
            "transaction_signal_calls": handler["transaction_signal_calls"],
            "persistence_signal_calls": handler["persistence_signal_calls"],
            "data_access_calls": [x for x in handler["first_party_external_calls"] if ".DataAccess." in x],
        }

    rule_fragments = {
        "BATCH_OR_SERIAL_REQUIRED": ("Batch", "Serial"),
        "DUPLICATE_GOODS_OR_BATCH_GUARD": ("DuplicateGoods",),
        "POSITIVE_QUANTITY_GUARD": ("UnitQtyLess", "EnterUnitQty"),
        "ACTIVE_GOODS_GUARD": ("GoodsIsInActive",),
        "ACCOUNTING_YEAR_AND_STOCK_SCOPE": ("set_AccYear", "StockDC"),
        "CARDEx_OR_ON_HAND_GUARD": ("CheckCardexQty", "CheckOnHandQty"),
        "CONFIRM_UNCONFIRM_TRANSITION": ("Confirm", "UnConfirm"),
        "RETURN_VOUCHER_TRANSITION": ("GenerateRetVocher", "ValidRetVocher"),
    }
    evidence_calls = set(all_calls)
    if handler:
        evidence_calls.update(handler["first_party_external_calls"])
        evidence_calls.update(handler["write_like_methods"])
        evidence_calls.update(handler["validation_like_methods"])
    signals = sorted(
        name for name, fragments in rule_fragments.items()
        if any(fragment.casefold() in call.casefold() for fragment in fragments for call in evidence_calls)
    )
    artifact = {
        "artifact": "varanegar_stock_voucher_static_command_validation_transition_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_HASHED_REDACTED_IL",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "live_ui_actions": 0,
            "business_commands_executed": 0,
        },
        "summary": {
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in selected),
            "referenced_form_field_count": len(fields),
            "rule_signal_count": len(signals),
            "target_command_count": len(TARGET_COMMANDS),
            "handler_transaction_signal_count": len(handler_summary["transaction_signal_calls"]) if handler_summary else 0,
            "handler_persistence_signal_count": len(handler_summary["persistence_signal_calls"]) if handler_summary else 0,
            "owner_approved_contract_count": 0,
            "runtime_effect_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "form_type": FORM,
        "assembly": assembly_row["file"] if assembly_row else None,
        "assembly_sha256": assembly_row["sha256"] if assembly_row else None,
        "methods": methods,
        "handler_contract": handler_summary,
        "rule_signals": signals,
        "target_command_candidates": TARGET_COMMANDS,
        "target_contract": "VERSIONED_IDEMPOTENT_APPLICATION_COMMAND_WITH_SEPARATE_DRAFT_CONFIRM_UNCONFIRM_AND_RETURN_TRANSITIONS",
        "owner_approved": False,
        "runtime_effect_parity_proven": False,
        "validation_errors": errors,
        "limits": [
            "TypeSpecRow.SaveCommand is a generic static call and does not reveal the selected runtime implementation.",
            "Static call co-occurrence does not prove branch order, configured values, rollback or successful effects.",
            "Confirm, unconfirm and return remain distinct state transitions; they must not be flattened into edit/save CRUD.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
