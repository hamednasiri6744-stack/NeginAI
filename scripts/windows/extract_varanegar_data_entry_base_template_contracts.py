"""Extract shared base-template contracts for forms with no local control fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile

from extract_varanegar_data_entry_declared_fields import _kind
from extract_varanegar_targeted_il_contracts import _analyze_assembly, _full_type_name


def _method_signals(name: str) -> list[str]:
    lowered = name.casefold()
    signals = []
    if any(token in lowered for token in ("save", "insert", "update", "create", "delete", "remove")):
        signals.append("write_or_delete")
    if any(token in lowered for token in ("valid", "check", "guard")):
        signals.append("validation_or_guard")
    if any(token in lowered for token in ("permission", "allow", "access", "authorize")):
        signals.append("permission")
    if any(token in lowered for token in ("load", "init", "fill", "refresh")):
        signals.append("load_or_refresh")
    if any(token in lowered for token in ("select", "filter", "search")):
        signals.append("selection_or_filter")
    return signals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--declared-fields", required=True, type=Path)
    parser.add_argument("--all-form-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = json.loads(args.binary_inventory.read_text(encoding="utf-8-sig"))
    declared = json.loads(args.declared_fields.read_text(encoding="utf-8-sig"))
    all_forms = json.loads(args.all_form_contracts.read_text(encoding="utf-8-sig"))
    inventory_by_name = {row["name"]: row for row in inventory["files"]}
    forms_by_type = {row["type"]: row for row in all_forms["forms"]}
    uncovered = [row for row in declared["forms"] if row["declared_control_field_count"] == 0]
    base_forms: dict[str, list[str]] = {}
    for row in uncovered:
        base = forms_by_type[row["form_type"]]["base_type"]
        base_forms.setdefault(base, []).append(row["form_type"])
    target_file = "Application.BaseTemaplateV2.dll"
    source_record = inventory_by_name[target_file]
    source_path = args.source_directory / target_file
    actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    analyzed = _analyze_assembly(source_path, set(base_forms))

    pe = dnfile.dnPE(str(source_path))
    table = getattr(pe.net.mdtables, "TypeDef", None)
    type_rows = {_full_type_name(row): row for row in ([] if not table else table.rows)}
    analyzed_by_type = {row["type"]: row for row in analyzed["target_types"]}
    templates = []
    for base_type, dependent_forms in sorted(base_forms.items()):
        type_row = type_rows.get(base_type)
        analyzed_type = analyzed_by_type.get(base_type)
        if type_row is None or analyzed_type is None or not analyzed_type["found"]:
            templates.append({
                "base_type": base_type,
                "found": False,
                "dependent_forms": sorted(dependent_forms),
                "declared_control_fields": [],
                "method_contracts": [],
            })
            continue
        base_row = getattr(getattr(type_row, "Extends", None), "row", None)
        inherited_base = "" if base_row is None else _full_type_name(base_row)
        fields = []
        for field_index in type_row.FieldList or []:
            field_row = field_index.row
            name = "" if field_row is None else str(field_row.Name)
            kind = _kind(name)
            if kind and "<" not in name and ">" not in name:
                fields.append({"field_name": name, "inferred_control_kind": kind, "runtime_control_type": "UNPROVEN"})
        methods = [
            {
                "method": row["method"],
                "signals": _method_signals(row["method"]),
                "instruction_count": row["instruction_count"],
                "call_count": len(row["calls"]),
            }
            for row in analyzed_type["methods"]
            if _method_signals(row["method"])
        ]
        templates.append({
            "base_type": base_type,
            "found": True,
            "inherited_base_type": inherited_base,
            "dependent_form_count": len(dependent_forms),
            "dependent_forms": sorted(dependent_forms),
            "declared_control_field_count": len(fields),
            "declared_control_fields": sorted(fields, key=lambda row: row["field_name"].casefold()),
            "method_body_count": len(analyzed_type["methods"]),
            "signaled_method_count": len(methods),
            "method_contracts": sorted(methods, key=lambda row: row["method"]),
            "local_form_field_gap_interpretation": "BEHAVIOR_AND_CONTROLS_ARE_BASE_TEMPLATE_DRIVEN_NOT_FIELDLESS",
        })

    all_base_fields = [field for row in templates for field in row["declared_control_fields"]]
    method_signal_counts = Counter(signal for row in templates for method in row["method_contracts"] for signal in method["signals"])
    errors = []
    if declared.get("validation") != "PASS":
        errors.append("declared-field source artifact not PASS")
    if all_forms.get("artifact") != "varanegar_all_high_confidence_form_compact_call_contracts":
        errors.append("unexpected all-form contract source")
    if actual_hash != source_record["sha256"]:
        errors.append("base template source hash mismatch")
    if any(not row["found"] for row in templates):
        errors.append("base template type missing")
    if analyzed["method_body_error_count"]:
        errors.append("base template method body parsing error")
    artifact = {
        "artifact": "varanegar_data_entry_shared_base_template_field_and_method_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_HASH_VERIFIED_TARGETED_BASE_TEMPLATE_METADATA_AND_IL_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "field_values_resources_or_config_payloads_read_or_persisted": 0,
            "raw_string_literals_persisted": 0,
            "runtime_behavior_or_binding_inferred": 0,
        },
        "summary": {
            "local_field_gap_form_count": len(uncovered),
            "unique_base_template_count": len(templates),
            "resolved_base_template_count": sum(row["found"] for row in templates),
            "base_template_declared_control_field_count": len(all_base_fields),
            "unique_base_template_field_name_count": len({row["field_name"] for row in all_base_fields}),
            "base_template_method_body_count": sum(row.get("method_body_count", 0) for row in templates),
            "base_template_signaled_method_count": sum(row.get("signaled_method_count", 0) for row in templates),
            "method_signal_counts": dict(sorted(method_signal_counts.items())),
            "form_reclassified_as_base_template_driven_count": sum(len(row["dependent_forms"]) for row in templates if row["found"]),
            "truly_fieldless_form_proven_count": 0,
            "source_hash_mismatch_count": int(actual_hash != source_record["sha256"]),
            "targeted_method_body_error_count": analyzed["method_body_error_count"],
            "runtime_behavior_or_binding_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "base_templates": templates,
        "validation_errors": errors,
        "limits": [
            "Base-template metadata and IL prove shared static structure, not actual runtime instantiation or field binding.",
            "Derived forms can add controls dynamically through resources, composition or later calls.",
            "Method-name signals do not prove a branch, authorization decision or successful write.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
