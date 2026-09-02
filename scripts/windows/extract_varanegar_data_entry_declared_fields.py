"""Read declared field metadata for selected Varanegar data-entry form types."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile

from extract_varanegar_targeted_il_contracts import _full_type_name


PREFIXES = {
    "text": ("txt", "text"),
    "choice": ("cmb", "combo", "rad", "radio"),
    "boolean": ("chk", "check"),
    "lookup": ("look", "lookup", "ddl"),
    "grid": ("grid", "grd", "vngrid"),
    "date": ("date", "dt"),
    "numeric": ("num", "nud", "spin"),
    "command": ("btn", "button", "menu"),
    "container": ("group", "panel", "tab", "split"),
    "media": ("pic", "image"),
    "label": ("label", "lbl"),
}


def _kind(name: str) -> str | None:
    lowered = name.casefold()
    return next((kind for kind, prefixes in PREFIXES.items() if lowered.startswith(prefixes)), None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--field-dictionary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = json.loads(args.binary_inventory.read_text(encoding="utf-8-sig"))
    il_source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    dictionary = json.loads(args.field_dictionary.read_text(encoding="utf-8-sig"))
    expected_hash = {row["name"]: row["sha256"] for row in inventory["files"]}
    targets_by_assembly = {
        assembly["file"]: {target["type"] for target in assembly["target_types"]}
        for assembly in il_source["raw_il"]
    }
    usage_by_form = {
        row["form_type"]: {field["field_name"]: field for field in row["fields"]}
        for row in dictionary["forms"]
    }
    form_catalog = {row["type"]: row for row in il_source["forms"]}
    forms = []
    hash_mismatches: list[str] = []
    missing_types: list[str] = []
    metadata_failures: list[str] = []
    for assembly_name, target_names in sorted(targets_by_assembly.items()):
        path = args.source_directory / assembly_name
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash[assembly_name]:
            hash_mismatches.append(assembly_name)
        try:
            pe = dnfile.dnPE(str(path))
            table = getattr(pe.net.mdtables, "TypeDef", None)
            types = {_full_type_name(row): row for row in ([] if not table else table.rows)}
            for form_type in sorted(target_names):
                row = types.get(form_type)
                if row is None:
                    missing_types.append(form_type)
                    continue
                fields = []
                usage = usage_by_form[form_type]
                for field_index in row.FieldList or []:
                    field_row = field_index.row
                    field_name = "" if field_row is None else str(field_row.Name)
                    kind = _kind(field_name)
                    if kind is None or "<" in field_name or ">" in field_name:
                        continue
                    enriched = usage.get(field_name)
                    fields.append({
                        "field_name": field_name,
                        "inferred_control_kind": kind,
                        "declared_in_type_metadata": True,
                        "referenced_in_selected_method_bodies": enriched is not None,
                        "referencing_methods": [] if enriched is None else enriched["referencing_methods"],
                        "usage_signals": [] if enriched is None else enriched["usage_signals"],
                        "runtime_control_type": "UNPROVEN",
                        "required_or_nullable_semantics": "UNPROVEN",
                        "data_binding_or_source_column": "UNPROVEN",
                    })
                forms.append({
                    "assembly": assembly_name,
                    "form_type": form_type,
                    "page_shape": form_catalog[form_type]["page_shape"],
                    "primary_domain_id": form_catalog[form_type]["primary_domain_id"],
                    "declared_control_field_count": len(fields),
                    "usage_enriched_field_count": sum(item["referenced_in_selected_method_bodies"] for item in fields),
                    "declared_only_field_count": sum(not item["referenced_in_selected_method_bodies"] for item in fields),
                    "fields": sorted(fields, key=lambda item: item["field_name"].casefold()),
                })
        except Exception as exc:
            metadata_failures.append(f"{assembly_name}:{type(exc).__name__}")

    all_fields = [field for form in forms for field in form["fields"]]
    kind_counts = Counter(field["inferred_control_kind"] for field in all_fields)
    errors = []
    if dictionary.get("validation") != "PASS" or il_source.get("summary", {}).get("selected_form_count") != len(target_names := set(form_catalog)):
        errors.append("source field dictionary or data-entry selection is inconsistent")
    if hash_mismatches:
        errors.append("source package hash mismatch")
    if missing_types or metadata_failures:
        errors.append("selected type metadata missing or failed")
    artifact = {
        "artifact": "varanegar_data_entry_declared_control_field_metadata",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_TARGETED_TYPE_AND_FIELD_METADATA_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "field_values_string_literals_resources_or_config_payloads_read_or_persisted": 0,
            "runtime_type_binding_or_requiredness_inferred": 0,
        },
        "summary": {
            "selected_data_entry_form_count": len(form_catalog),
            "resolved_form_type_count": len(forms),
            "form_with_declared_control_field_count": sum(row["declared_control_field_count"] > 0 for row in forms),
            "form_without_declared_control_field_count": sum(row["declared_control_field_count"] == 0 for row in forms),
            "declared_control_field_count": len(all_fields),
            "unique_declared_field_name_count": len({field["field_name"] for field in all_fields}),
            "usage_enriched_field_count": sum(field["referenced_in_selected_method_bodies"] for field in all_fields),
            "declared_only_field_count": sum(not field["referenced_in_selected_method_bodies"] for field in all_fields),
            "field_kind_counts": dict(sorted(kind_counts.items())),
            "runtime_control_type_proven_count": 0,
            "required_or_nullable_proven_count": 0,
            "data_binding_proven_count": 0,
            "missing_form_type_count": len(missing_types),
            "source_hash_mismatch_count": len(hash_mismatches),
            "metadata_failure_count": len(metadata_failures),
            "validation_error_count": len(errors),
        },
        "forms": sorted(forms, key=lambda row: row["form_type"]),
        "missing_form_types": missing_types,
        "source_hash_mismatches": hash_mismatches,
        "metadata_failures": metadata_failures,
        "validation_errors": errors,
        "limits": [
            "Field-name prefixes identify control candidates but do not decode the CLR field signature.",
            "Declared fields may be layout-only, inactive or hidden and inherited controls are not listed.",
            "Runtime control type, label pairing, binding, requiredness, visibility and enabled state remain unproven.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
