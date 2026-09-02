"""Compose customer and goods master-data web-screen candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-contracts", required=True, type=Path)
    parser.add_argument("--customer-fields", required=True, type=Path)
    parser.add_argument("--customer-layout", required=True, type=Path)
    parser.add_argument("--customer-labels", required=True, type=Path)
    parser.add_argument("--goods-fields", required=True, type=Path)
    parser.add_argument("--goods-layout", required=True, type=Path)
    parser.add_argument("--goods-labels", required=True, type=Path)
    parser.add_argument("--golden-cases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    commands = _load(args.command_contracts)
    groups = [
        (_load(args.customer_fields), _load(args.customer_layout), _load(args.customer_labels)),
        (_load(args.goods_fields), _load(args.goods_layout), _load(args.goods_labels)),
    ]
    golden = _load(args.golden_cases)
    sources = [commands, golden, *(x for group in groups for x in group)]
    errors = [] if all(x.get("validation") == "PASS" for x in sources) else ["source validation failure"]
    command_by_form = {row["form_type"]: row for row in commands["contracts"]}
    golden_by_command = {}
    for case in golden["cases"]:
        golden_by_command.setdefault(case["command"], []).append(case["case_id"])
    screens = []
    for metadata, layout_artifact, label_artifact in groups:
        form = metadata["forms"][0]
        form_type = form["form_type"]
        command = command_by_form.get(form_type)
        if command is None:
            errors.append(f"command contract missing: {form_type}")
            continue
        layout = layout_artifact["forms"][0]
        label = label_artifact["forms"][0]
        bindings = {row["control_field"]: row for row in layout["bindings"]}
        method_refs = {}
        for method in command["methods"]:
            for reference in method["referenced_form_fields"]:
                method_refs.setdefault(reference.rsplit(".", 1)[-1], []).append(method["method"])
        inputs = []
        command_controls = []
        for field in form["fields"]:
            if field["web_input_candidate"]:
                binding = bindings.get(field["field_name"])
                inputs.append({
                    "legacy_control": field["field_name"],
                    "clr_field_type": field["clr_field_type"],
                    "input_kind_candidate": field["static_component_kind"],
                    "layout_item": None if binding is None else binding["layout_field"],
                    "layout_static_label_candidate": None if binding is None else binding["static_label_candidate"],
                    "direct_static_ui_text_candidate": field["static_ui_text_candidate"],
                    "selected_method_references": sorted(method_refs.get(field["field_name"], [])),
                    "target_request_property": "OWNER_DECISION_REQUIRED",
                    "requiredness_default_lookup_binding_runtime_permission_and_value": "UNPROVEN",
                })
            elif field["static_component_kind"] == "command":
                command_controls.append({
                    "legacy_control": field["field_name"],
                    "static_text_candidate": field["static_ui_text_candidate"],
                    "command_mapping_and_runtime_authorization": "UNPROVEN",
                })
        linked_golden_ids = sorted(
            golden_by_command.get(command["target_command_candidate"], [])
            + golden_by_command.get(command["secondary_delete_command_candidate"], [])
        )
        if not linked_golden_ids:
            errors.append(f"Golden contracts missing: {form_type}")
        screens.append({
            "screen_id": f"web.{command['target_command_candidate']}",
            "legacy_form": form_type,
            "likely_static_title_candidates": label.get("likely_form_title_candidates", []),
            "primary_target_command": command["target_command_candidate"],
            "secondary_delete_command_candidate": command["secondary_delete_command_candidate"],
            "rule_signals": commands["rule_signals"],
            "input_control_candidates": inputs,
            "command_control_candidates": command_controls,
            "linked_synthetic_golden_case_ids": linked_golden_ids,
            "golden_contract_gap": None if linked_golden_ids else "SAVE_AND_DELETE_CASES_NOT_YET_DEFINED",
            "owner_approved": False,
            "implementation_ready": False,
            "runtime_golden_executed": False,
        })
    inputs = [x for screen in screens for x in screen["input_control_candidates"]]
    artifact = {
        "artifact": "negin_erp_customer_goods_master_data_web_screen_contract_candidates",
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
            "primary_target_command_count": len(screens),
            "secondary_delete_command_candidate_count": len(screens),
            "input_control_candidate_count": len(inputs),
            "input_with_static_layout_label_candidate_count": sum(bool(x["layout_static_label_candidate"]) for x in inputs),
            "input_with_direct_static_ui_text_candidate_count": sum(bool(x["direct_static_ui_text_candidate"]) for x in inputs),
            "input_without_any_static_text_candidate_count": sum(not x["layout_static_label_candidate"] and not x["direct_static_ui_text_candidate"] for x in inputs),
            "input_referenced_by_selected_method_count": sum(bool(x["selected_method_references"]) for x in inputs),
            "command_control_candidate_count": sum(len(x["command_control_candidates"]) for x in screens),
            "unique_rule_signal_count": len(commands["rule_signals"]),
            "linked_synthetic_golden_case_count": sum(len(x["linked_synthetic_golden_case_ids"]) for x in screens),
            "screen_with_missing_golden_contract_count": sum(bool(x["golden_contract_gap"]) for x in screens),
            "owner_approved_screen_count": 0,
            "implementation_ready_screen_count": 0,
            "runtime_golden_executed_screen_count": 0,
            "validation_error_count": len(errors),
        },
        "screens": screens,
        "validation_errors": errors,
        "limits": [
            "Static fields and labels are owner-review candidates, not implementation-ready semantics.",
            "Customer and goods save/delete Golden contracts are designed but have not been executed; implementation readiness remains blocked.",
            "Dynamic permission, requiredness, lookup population, binding, status and merge/delete effects remain unproven.",
            "Goods child collections for barcode, supplier, package, batch and DC allocation must remain structured relations.",
        ],
    }
    if len(screens) != 2:
        artifact["validation_errors"].append("expected two screens")
        artifact["summary"]["validation_error_count"] = len(artifact["validation_errors"])
        artifact["validation"] = "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
