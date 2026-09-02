"""Compose the offline Supplier master-data web-screen candidate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-contract", required=True, type=Path)
    parser.add_argument("--fields", required=True, type=Path)
    parser.add_argument("--layout", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--golden-cases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    command, fields, layout_artifact, labels, golden = map(_load, (args.command_contract, args.fields, args.layout, args.labels, args.golden_cases))
    errors = [] if all(row.get("validation") == "PASS" for row in (command, fields, layout_artifact, labels, golden)) else ["source validation failure"]
    contract = command["contract"]
    form = fields["forms"][0]
    layout = layout_artifact["forms"][0]
    bindings = {row["control_field"]: row for row in layout["bindings"]}
    method_refs: dict[str, list[str]] = {}
    for method in contract["methods"]:
        for reference in method["referenced_form_fields"]:
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
            "layout_static_label_candidate": None if binding is None else binding["static_label_candidate"],
            "direct_static_ui_text_candidate": field["static_ui_text_candidate"],
            "selected_method_references": sorted(method_refs.get(field["field_name"], [])),
            "target_request_property": "OWNER_DECISION_REQUIRED",
            "requiredness_lookup_binding_runtime_permission_and_value": "UNPROVEN",
        })
    linked_golden = sorted(row["case_id"] for row in golden["cases"] if row["command"] in {contract["target_command_candidate"], contract["secondary_delete_command_candidate"]})
    screen = {
        "screen_id": "web.master_data.supplier",
        "legacy_form": contract["form_type"],
        "likely_static_title_candidates": labels["forms"][0].get("likely_form_title_candidates", []),
        "primary_target_command": contract["target_command_candidate"],
        "secondary_delete_command_candidate": contract["secondary_delete_command_candidate"],
        "rule_signals": contract["rule_signals"],
        "input_control_candidates": inputs,
        "linked_synthetic_golden_case_ids": linked_golden,
        "golden_contract_gap": None if linked_golden else "SUPPLIER_SAVE_DELETE_CASES_NOT_YET_DEFINED",
        "owner_approved": False,
        "implementation_ready": False,
        "runtime_golden_executed": False,
    }
    artifact = {
        "artifact": "negin_erp_supplier_master_data_web_screen_contract_candidate",
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
            "screen_candidate_count": 1,
            "input_control_candidate_count": len(inputs),
            "input_with_static_layout_label_candidate_count": sum(bool(row["layout_static_label_candidate"]) for row in inputs),
            "input_without_any_static_text_candidate_count": sum(not row["layout_static_label_candidate"] and not row["direct_static_ui_text_candidate"] for row in inputs),
            "input_referenced_by_selected_method_count": sum(bool(row["selected_method_references"]) for row in inputs),
            "unique_rule_signal_count": len(contract["rule_signals"]),
            "linked_synthetic_golden_case_count": len(linked_golden),
            "screen_with_missing_golden_contract_count": 0 if linked_golden else 1,
            "owner_approved_screen_count": 0,
            "implementation_ready_screen_count": 0,
            "runtime_golden_executed_screen_count": 0,
            "validation_error_count": len(errors),
        },
        "screen": screen,
        "validation_errors": errors,
        "limits": [
            "Static field/label candidates require owner review and do not establish requiredness, visibility, lookup values, or request binding.",
            "Supplier save/delete Golden cases are designed but unexecuted and therefore still block implementation readiness.",
            "Payment usage, accounting group, contact/DL, attachment, and cardex dependencies must be preserved as relations and guards.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
