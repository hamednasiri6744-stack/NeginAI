"""Compose web-screen candidates for order, sale conversion, and return entry."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-contracts", required=True, type=Path)
    parser.add_argument("--full-field-metadata", required=True, type=Path)
    parser.add_argument("--layout-bindings", required=True, type=Path)
    parser.add_argument("--ui-labels", required=True, type=Path)
    parser.add_argument("--golden-cases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    commands = _load(args.command_contracts)
    metadata = _load(args.full_field_metadata)
    layouts = _load(args.layout_bindings)
    labels = _load(args.ui_labels)
    golden = _load(args.golden_cases)
    sources = [commands, metadata, layouts, labels, golden]
    errors: list[str] = []
    if any(source.get("validation") != "PASS" for source in sources):
        errors.append("one or more source artifacts failed validation")

    command_by_form = {row["form_type"]: row for row in commands["contracts"]}
    layout_by_form = {row["form_type"]: row for row in layouts["forms"]}
    label_by_form = {row["form_type"]: row for row in labels["forms"]}
    cases_by_command: dict[str, list[dict[str, Any]]] = {}
    for row in golden["cases"]:
        cases_by_command.setdefault(row["command"], []).append(row)

    screens: list[dict[str, Any]] = []
    for form in metadata["forms"]:
        form_type = form["form_type"]
        command = command_by_form.get(form_type)
        layout = layout_by_form.get(form_type)
        label = label_by_form.get(form_type)
        if not command or not layout or not label:
            errors.append(f"cross-source form contract missing: {form_type}")
            continue
        bindings = {
            row["control_field"]: row for row in layout["bindings"]
        }
        referenced_by_method: dict[str, list[str]] = {}
        for method in command["methods"]:
            for field in method["referenced_form_fields"]:
                referenced_by_method.setdefault(field.rsplit(".", 1)[-1], []).append(
                    method["method"]
                )
        input_fields = []
        command_controls = []
        for field in form["fields"]:
            if field["web_input_candidate"]:
                binding = bindings.get(field["field_name"])
                input_fields.append(
                    {
                        "legacy_control": field["field_name"],
                        "clr_field_type": field["clr_field_type"],
                        "input_kind_candidate": field["static_component_kind"],
                        "layout_item": None
                        if binding is None
                        else binding["layout_field"],
                        "static_label_candidate": None
                        if binding is None
                        else binding["static_label_candidate"],
                        "selected_command_or_validation_method_references": sorted(
                            referenced_by_method.get(field["field_name"], [])
                        ),
                        "target_request_property": "OWNER_DECISION_REQUIRED",
                        "requiredness_default_mask_lookup_population_and_binding": "UNPROVEN",
                        "runtime_visibility_enabled_state_and_authorization": "UNPROVEN",
                    }
                )
            elif field["static_component_kind"] == "command":
                command_controls.append(
                    {
                        "legacy_control": field["field_name"],
                        "clr_field_type": field["clr_field_type"],
                        "static_text_candidate": field["static_ui_text_candidate"],
                        "command_mapping": "UNPROVEN",
                        "runtime_visibility_enabled_state_and_authorization": "UNPROVEN",
                    }
                )
        target_command = command["target_command_candidate"]
        golden_cases = cases_by_command.get(target_command, [])
        screens.append(
            {
                "screen_id": f"web.{target_command}",
                "workflow": command["workflow"],
                "legacy_form": form_type,
                "likely_static_title_candidates": label.get(
                    "likely_form_title_candidates", []
                ),
                "target_command": target_command,
                "legacy_boundary": command["legacy_boundary"],
                "target_boundary_candidate": command[
                    "target_boundary_candidate"
                ],
                "rule_signals": command["rule_signals"],
                "input_control_candidates": input_fields,
                "command_control_candidates": command_controls,
                "selected_method_contracts": [
                    {
                        "method": row["method"],
                        "role": row["role"],
                        "business_action_calls": row["business_action_calls"],
                        "rule_signals": row["rule_signals"],
                        "branch_order_runtime_values_and_effects_proven": row[
                            "branch_order_runtime_values_and_effects_proven"
                        ],
                    }
                    for row in command["methods"]
                ],
                "synthetic_golden_case_ids": [
                    row["case_id"] for row in golden_cases
                ],
                "synthetic_golden_case_count": len(golden_cases),
                "owner_approved": False,
                "implementation_ready": False,
                "runtime_golden_executed": False,
            }
        )

    inputs = [row for screen in screens for row in screen["input_control_candidates"]]
    referenced_inputs = [
        row
        for row in inputs
        if row["selected_command_or_validation_method_references"]
    ]
    artifact = {
        "artifact": "negin_erp_order_sale_return_web_screen_contract_candidates",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_READ_ONLY_EVIDENCE_COMPOSITION",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "application_or_business_commands_executed": 0,
            "legacy_or_clone_writes": 0,
            "runtime_binding_requiredness_visibility_authorization_or_effect_inferred": 0,
        },
        "summary": {
            "screen_candidate_count": len(screens),
            "target_command_count": len({row["target_command"] for row in screens}),
            "input_control_candidate_count": len(inputs),
            "input_with_static_layout_label_candidate_count": sum(
                bool(row["static_label_candidate"]) for row in inputs
            ),
            "input_without_static_layout_label_candidate_count": sum(
                not row["static_label_candidate"] for row in inputs
            ),
            "input_referenced_by_selected_command_or_validation_method_count": len(
                referenced_inputs
            ),
            "command_control_candidate_count": sum(
                len(row["command_control_candidates"]) for row in screens
            ),
            "unique_rule_signal_count": len(
                {signal for row in screens for signal in row["rule_signals"]}
            ),
            "linked_synthetic_golden_case_count": sum(
                row["synthetic_golden_case_count"] for row in screens
            ),
            "owner_approved_screen_count": 0,
            "implementation_ready_screen_count": 0,
            "runtime_golden_executed_screen_count": 0,
            "validation_error_count": len(errors),
        },
        "screens": screens,
        "validation_errors": errors,
        "limits": [
            "Static layout and call evidence is sufficient for owner review, not for implementation-ready field semantics.",
            "The 48 linked Golden cases are synthetic target-test designs and have not executed a source or target business command.",
            "Requiredness, defaults, masks, lookup population, binding, dynamic visibility, effective permissions and exact branch messages remain open.",
            "Save orchestration must preserve credit, stock, reservation, pricing, prize, batch/serial, conversion and post-save invariants behind an idempotent versioned command boundary.",
        ],
    }
    if len(screens) != 3 or any(row["synthetic_golden_case_count"] != 16 for row in screens):
        artifact["validation_errors"].append(
            "expected three screens with sixteen linked synthetic Golden cases each"
        )
        artifact["summary"]["validation_error_count"] = len(
            artifact["validation_errors"]
        )
        artifact["validation"] = "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
