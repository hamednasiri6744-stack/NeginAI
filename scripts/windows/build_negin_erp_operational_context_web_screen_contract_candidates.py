"""Compose operational-year, stock/DC, and stock-accounting screen candidates."""

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
    parser.add_argument("--main-fields", required=True, type=Path)
    parser.add_argument("--main-layout", required=True, type=Path)
    parser.add_argument("--main-labels", required=True, type=Path)
    parser.add_argument("--stock-fields", required=True, type=Path)
    parser.add_argument("--stock-layout", required=True, type=Path)
    parser.add_argument("--stock-labels", required=True, type=Path)
    parser.add_argument("--golden-cases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    commands = _load(args.command_contracts)
    groups = [
        (_load(args.main_fields), _load(args.main_layout), _load(args.main_labels)),
        (_load(args.stock_fields), _load(args.stock_layout), _load(args.stock_labels)),
    ]
    golden = _load(args.golden_cases)
    sources = [commands, golden, *(artifact for group in groups for artifact in group)]
    errors = [] if all(row.get("validation") == "PASS" for row in sources) else ["source validation failure"]
    command_by_form = {row["form_type"]: row for row in commands["contracts"]}
    screens = []
    for fields_artifact, layout_artifact, labels_artifact in groups:
        layout_by_form = {row["form_type"]: row for row in layout_artifact["forms"]}
        labels_by_form = {row["form_type"]: row for row in labels_artifact["forms"]}
        for form in fields_artifact["forms"]:
            form_type = form["form_type"]
            contract = command_by_form.get(form_type)
            if contract is None:
                errors.append(f"command contract missing: {form_type}")
                continue
            layout = layout_by_form[form_type]
            labels = labels_by_form[form_type]
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
            screens.append({
                "screen_id": f"web.{contract['target_command_candidate']}",
                "legacy_form": form_type,
                "likely_static_title_candidates": labels.get("likely_form_title_candidates", []),
                "primary_target_command": contract["target_command_candidate"],
                "secondary_delete_command_candidate": contract["secondary_delete_command_candidate"],
                "rule_signals": commands["rule_signals"],
                "input_control_candidates": inputs,
                "linked_synthetic_golden_case_ids": linked_golden,
                "golden_contract_gap": None if linked_golden else "OPERATIONAL_CONTEXT_SAVE_DELETE_CASES_NOT_YET_DEFINED",
                "owner_approved": False,
                "implementation_ready": False,
                "runtime_golden_executed": False,
            })
    all_inputs = [row for screen in screens for row in screen["input_control_candidates"]]
    artifact = {
        "artifact": "negin_erp_operational_year_stock_dc_and_stock_accounting_web_screen_contract_candidates",
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
            "input_control_candidate_count": len(all_inputs),
            "input_with_static_layout_label_candidate_count": sum(bool(row["layout_static_label_candidate"]) for row in all_inputs),
            "input_without_any_static_text_candidate_count": sum(not row["layout_static_label_candidate"] and not row["direct_static_ui_text_candidate"] for row in all_inputs),
            "input_referenced_by_selected_method_count": sum(bool(row["selected_method_references"]) for row in all_inputs),
            "unique_rule_signal_count": len(commands["rule_signals"]),
            "linked_synthetic_golden_case_count": sum(len(row["linked_synthetic_golden_case_ids"]) for row in screens),
            "screen_with_missing_golden_contract_count": sum(bool(row["golden_contract_gap"]) for row in screens),
            "owner_approved_screen_count": 0,
            "implementation_ready_screen_count": 0,
            "runtime_golden_executed_screen_count": 0,
            "validation_error_count": len(errors),
        },
        "screens": screens,
        "validation_errors": errors,
        "limits": [
            "Operational year, fiscal year, DC, sale office, stock/warehouse, ship type, and stock-accounting price method remain separate target concepts.",
            "Five StockType flags are static signals; exact bit/code compatibility and effective runtime values require owner review and isolated tests.",
            "Golden save/delete cases are designed but unexecuted and therefore still block implementation readiness.",
        ],
    }
    if len(screens) != 3:
        artifact["validation_errors"].append("expected three operational-context screens")
        artifact["summary"]["validation_error_count"] = len(artifact["validation_errors"])
        artifact["validation"] = "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
