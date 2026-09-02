"""Compose stock-voucher and supplier-invoice web-screen candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


STOCK_FORM = "VN.SDS.Stock.UI.Vocher.FormVocherDataEntry"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock-command-contract", required=True, type=Path)
    parser.add_argument("--supplier-command-contract", required=True, type=Path)
    parser.add_argument("--full-field-metadata", required=True, type=Path)
    parser.add_argument("--layout-bindings", required=True, type=Path)
    parser.add_argument("--ui-labels", required=True, type=Path)
    parser.add_argument("--golden-cases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    stock = _load(args.stock_command_contract)
    supplier = _load(args.supplier_command_contract)
    fields = _load(args.full_field_metadata)
    layouts = _load(args.layout_bindings)
    labels = _load(args.ui_labels)
    golden = _load(args.golden_cases)
    sources = (stock, supplier, fields, layouts, labels, golden)
    errors = [] if all(x.get("validation") == "PASS" for x in sources) else ["source validation failure"]

    command_by_form = {
        row["form_type"]: {**row, "rule_signals": supplier["rule_signals"]}
        for row in supplier["contracts"]
    }
    command_by_form[STOCK_FORM] = {
        "form_type": STOCK_FORM,
        "methods": stock["methods"],
        "rule_signals": stock["rule_signals"],
        "target_command_candidate": "stock_voucher.save",
        "secondary_command_candidates_without_complete_screen_mapping": [
            "stock_voucher.confirm_or_unconfirm", "stock_voucher.generate_return"
        ],
    }
    layout_by_form = {row["form_type"]: row for row in layouts["forms"]}
    label_by_form = {row["form_type"]: row for row in labels["forms"]}
    cases_by_command = {}
    for row in golden["cases"]:
        cases_by_command.setdefault(row["command"], []).append(row)

    screens = []
    for form in fields["forms"]:
        form_type = form["form_type"]
        command = command_by_form.get(form_type)
        layout = layout_by_form.get(form_type)
        label = label_by_form.get(form_type)
        if not command or not layout or not label:
            errors.append(f"cross-source form missing: {form_type}")
            continue
        bindings = {row["control_field"]: row for row in layout["bindings"]}
        method_refs = {}
        for method in command["methods"]:
            for reference in method.get("referenced_form_fields", []):
                method_refs.setdefault(reference.rsplit(".", 1)[-1], []).append(method["method"])
        inputs = []
        for field in form["fields"]:
            if not field["web_input_candidate"]:
                continue
            binding = bindings.get(field["field_name"])
            inputs.append({
                "legacy_control": field["field_name"],
                "clr_field_type": field["clr_field_type"],
                "input_kind_candidate": field["static_component_kind"],
                "layout_item": None if binding is None else binding["layout_field"],
                "static_label_candidate": None if binding is None else binding["static_label_candidate"],
                "selected_method_references": sorted(method_refs.get(field["field_name"], [])),
                "target_request_property": "OWNER_DECISION_REQUIRED",
                "requiredness_default_lookup_binding_and_runtime_authorization": "UNPROVEN",
            })
        primary = command["target_command_candidate"]
        secondary = command.get(
            "secondary_command_candidates_without_complete_screen_mapping",
            command.get("secondary_command_candidates_without_complete_golden_contract", []),
        )
        commands = [primary, *secondary]
        linked = [case for name in commands for case in cases_by_command.get(name, [])]
        screens.append({
            "screen_id": f"web.{primary}",
            "legacy_form": form_type,
            "likely_static_title_candidates": label.get("likely_form_title_candidates", []),
            "primary_target_command": primary,
            "secondary_transition_or_delete_command_candidates": secondary,
            "rule_signals": command["rule_signals"],
            "input_control_candidates": inputs,
            "synthetic_golden_case_ids": [row["case_id"] for row in linked],
            "synthetic_golden_case_count": len(linked),
            "owner_approved": False,
            "implementation_ready": False,
            "runtime_golden_executed": False,
        })
    all_inputs = [x for screen in screens for x in screen["input_control_candidates"]]
    artifact = {
        "artifact": "negin_erp_stock_voucher_supplier_invoice_return_web_screen_contract_candidates",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_READ_ONLY_EVIDENCE_COMPOSITION",
            "assemblies_or_commands_executed": 0,
            "database_connections": 0,
            "live_ui_actions": 0,
            "legacy_or_clone_writes": 0,
            "runtime_binding_requiredness_visibility_authorization_or_effect_inferred": 0,
        },
        "summary": {
            "screen_candidate_count": len(screens),
            "primary_target_command_count": len({x["primary_target_command"] for x in screens}),
            "secondary_command_candidate_count": sum(len(x["secondary_transition_or_delete_command_candidates"]) for x in screens),
            "input_control_candidate_count": len(all_inputs),
            "input_with_static_layout_label_candidate_count": sum(bool(x["static_label_candidate"]) for x in all_inputs),
            "input_without_static_layout_label_candidate_count": sum(not x["static_label_candidate"] for x in all_inputs),
            "input_referenced_by_selected_method_count": sum(bool(x["selected_method_references"]) for x in all_inputs),
            "unique_rule_signal_count": len({signal for x in screens for signal in x["rule_signals"]}),
            "linked_synthetic_golden_case_count": sum(x["synthetic_golden_case_count"] for x in screens),
            "owner_approved_screen_count": 0,
            "implementation_ready_screen_count": 0,
            "runtime_golden_executed_screen_count": 0,
            "validation_error_count": len(errors),
        },
        "screens": screens,
        "validation_errors": errors,
        "limits": [
            "Static fields, labels and layout are review candidates, not implementation-ready field semantics.",
            "Requiredness, defaults, lookups, bindings, dynamic visibility and effective permissions remain unproven.",
            "Linked Golden cases are synthetic and no source or target business command was executed.",
            "Delete candidates lack complete Golden contracts and must stay disabled until separately specified.",
        ],
    }
    if len(screens) != 3:
        artifact["validation_errors"].append("expected three screens")
        artifact["summary"]["validation_error_count"] = len(artifact["validation_errors"])
        artifact["validation"] = "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
