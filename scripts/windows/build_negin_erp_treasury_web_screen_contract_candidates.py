from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {row[key]: row for row in items}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-fields", required=True, type=Path)
    parser.add_argument("--ui-labels", required=True, type=Path)
    parser.add_argument("--validation-contracts", required=True, type=Path)
    parser.add_argument("--command-paths", required=True, type=Path)
    parser.add_argument("--target-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    fields_source = _load(args.web_fields)
    labels_source = _load(args.ui_labels)
    validation_source = _load(args.validation_contracts)
    paths_source = _load(args.command_paths)
    target_source = _load(args.target_contracts)
    errors: list[str] = []
    sources = [
        fields_source,
        labels_source,
        validation_source,
        paths_source,
        target_source,
    ]
    if any(source.get("validation") != "PASS" for source in sources):
        errors.append("one or more source artifacts failed validation")

    labels_by_form = _by(labels_source["forms"], "form_type")
    validations_by_form = _by(validation_source["contracts"], "form_type")
    paths_by_form = _by(paths_source["contracts"], "form_type")
    targets_by_form = _by(target_source["contracts"], "legacy_form")
    obligations_by_command: dict[str, list[dict[str, Any]]] = {}
    for row in target_source["acceptance_obligations"]:
        obligations_by_command.setdefault(row["surface"], []).append(row)

    screens: list[dict[str, Any]] = []
    for form in fields_source["forms"]:
        form_type = form["form_type"]
        label_contract = labels_by_form.get(form_type)
        validation_contract = validations_by_form.get(form_type)
        path_contract = paths_by_form.get(form_type)
        target_contract = targets_by_form.get(form_type)
        if not all([label_contract, validation_contract, path_contract, target_contract]):
            errors.append(f"cross-source form contract missing: {form_type}")
            continue
        assignments = label_contract["assignments"]
        text_by_field = {
            row["field_name"]: row["ui_text"]
            for row in assignments
            if row["field_name"]
        }
        title_candidates = [
            row["ui_text"]
            for row in assignments
            if row["target_kind"] == "FORM_OR_UNRESOLVED_TARGET"
            and row["setter"] == "set_Text"
        ]
        fields = []
        command_controls = []
        unpaired_labels = []
        for field in form["fields"]:
            item = {
                "legacy_control": field["field_name"],
                "control_type": field["clr_field_type"],
                "control_kind": field["resolved_control_kind"],
                "static_caption_candidate": text_by_field.get(field["field_name"]),
                "usage_signals": field["usage_signals"],
                "legacy_property_candidates": field["property_candidates"],
                "source_column_candidates": field["source_column_candidates"],
                "candidate_status": field["target_web_field_contract_status"],
                "label_pairing": "UNRESOLVED_UNLESS_CONTROL_HAS_DIRECT_STATIC_CAPTION",
                "requiredness": "UNPROVEN",
                "runtime_visibility_and_enabled_state": "UNPROVEN",
                "authorization_effective_scope": "UNPROVEN",
                "target_request_property": "OWNER_DECISION_REQUIRED",
            }
            if field["resolved_control_kind"] == "command":
                command_controls.append(item)
            elif field["resolved_control_kind"] == "label":
                unpaired_labels.append(item)
            elif field["resolved_control_kind"] not in {"container", "media"}:
                fields.append(item)
        rule_signals = sorted(
            {
                signal
                for method in validation_contract["methods"]
                for signal in method["rule_signals"]
            }
        )
        selected_methods = [
            {
                "method": method["method"],
                "role": method["role"],
                "rule_signals": method["rule_signals"],
                "exact_branch_message_and_effect_proven": method[
                    "exact_branch_condition_message_and_effect_proven"
                ],
            }
            for method in validation_contract["methods"]
        ]
        command = target_contract["command"]
        screens.append(
            {
                "screen_id": f"web.{command}",
                "workflow": form["workflow"],
                "legacy_form": form_type,
                "static_title_candidates": title_candidates,
                "target_command": command,
                "target_module": target_contract["target_module"],
                "aggregate": target_contract["aggregate"],
                "target_input_contract": target_contract["input_fields"],
                "authorization_contract": target_contract["authorization"],
                "idempotency_contract": target_contract["idempotency_contract"],
                "concurrency_contract": target_contract["concurrency_contract"],
                "transaction_contract": target_contract["transaction_contract"],
                "source_write_policy": target_contract["source_write_policy"],
                "legacy_write_model": path_contract["write_model"],
                "target_boundary": path_contract["target_erp_boundary"],
                "input_control_candidates": fields,
                "command_control_candidates": command_controls,
                "unpaired_static_label_candidates": unpaired_labels,
                "rule_signals": rule_signals,
                "selected_validation_methods": selected_methods,
                "acceptance_obligation_ids": [
                    row["case_id"] for row in obligations_by_command.get(command, [])
                ],
                "promotion_status": "NOT_IMPLEMENTATION_READY",
                "owner_approved": target_contract["owner_approved"],
                "runtime_golden_proven": False,
            }
        )

    all_fields = [field for screen in screens for field in screen["input_control_candidates"]]
    artifact = {
        "artifact": "negin_erp_treasury_web_screen_contract_candidates",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_READ_ONLY_EVIDENCE_COMPOSITION",
            "live_ui_actions": 0,
            "database_connections": 0,
            "application_commands_executed": 0,
            "legacy_or_clone_writes": 0,
            "runtime_field_binding_requiredness_or_effect_inferred": 0,
        },
        "summary": {
            "screen_candidate_count": len(screens),
            "target_command_count": len({row["target_command"] for row in screens}),
            "input_control_candidate_count": len(all_fields),
            "input_with_direct_static_caption_candidate_count": sum(
                bool(row["static_caption_candidate"]) for row in all_fields
            ),
            "command_control_candidate_count": sum(
                len(row["command_control_candidates"]) for row in screens
            ),
            "unpaired_static_label_candidate_count": sum(
                len(row["unpaired_static_label_candidates"]) for row in screens
            ),
            "unique_rule_signal_count": len(
                {signal for row in screens for signal in row["rule_signals"]}
            ),
            "acceptance_obligation_count": sum(
                len(row["acceptance_obligation_ids"]) for row in screens
            ),
            "owner_approved_screen_count": sum(row["owner_approved"] for row in screens),
            "implementation_ready_screen_count": 0,
            "runtime_golden_proven_screen_count": 0,
            "validation_error_count": len(errors),
        },
        "promotion_gate": target_source["promotion_gate"],
        "screens": screens,
        "validation_errors": errors,
        "limits": [
            "This is a cross-linked candidate contract for design and owner review, not an implementation-ready UI specification.",
            "Separate label controls are deliberately unpaired because static control names alone do not prove layout association.",
            "Requiredness, defaults, masks, lookup populations, authorization scope and effective branch messages require owner and runtime Golden proof.",
            "The web command boundary must preserve atomic ledger, history, accounting and control-total effects without writing back to Varanegar.",
        ],
    }
    if len(screens) != 3:
        artifact["validation_errors"].append("expected exactly three treasury edit screens")
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
