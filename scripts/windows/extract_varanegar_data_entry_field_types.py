"""Decode CLR field-signature types for declared data-entry control candidates."""

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


PRIMITIVES = {
    0x02: "System.Boolean", 0x03: "System.Char", 0x04: "System.SByte", 0x05: "System.Byte",
    0x06: "System.Int16", 0x07: "System.UInt16", 0x08: "System.Int32", 0x09: "System.UInt32",
    0x0A: "System.Int64", 0x0B: "System.UInt64", 0x0C: "System.Single", 0x0D: "System.Double",
    0x0E: "System.String", 0x1C: "System.Object",
}


def _compressed(raw: bytes, index: int) -> tuple[int, int]:
    first = raw[index]
    if first & 0x80 == 0:
        return first, index + 1
    if first & 0xC0 == 0x80:
        return ((first & 0x3F) << 8) | raw[index + 1], index + 2
    if first & 0xE0 == 0xC0:
        value = ((first & 0x1F) << 24) | (raw[index + 1] << 16) | (raw[index + 2] << 8) | raw[index + 3]
        return value, index + 4
    raise ValueError("invalid compressed integer")


def _type_from_coded(pe: Any, coded: int) -> tuple[str, str]:
    tag = coded & 0x03
    rid = coded >> 2
    table_name = {0: "TypeDef", 1: "TypeRef", 2: "TypeSpec"}.get(tag)
    if table_name is None or rid <= 0:
        return "", "INVALID_TYPEDEF_OR_REF"
    table = getattr(pe.net.mdtables, table_name, None)
    rows = [] if table is None else table.rows
    if rid > len(rows):
        return "", "TYPE_TOKEN_OUT_OF_RANGE"
    if table_name == "TypeSpec":
        return f"TypeSpec#{rid}", "TYPESPEC_TOKEN_NOT_EXPANDED"
    return _full_type_name(rows[rid - 1]), "RESOLVED_TYPEDEF_OR_TYPEREF"


def _decode(pe: Any, raw: bytes) -> tuple[str, str]:
    if not raw or raw[0] != 0x06:
        return "", "NOT_A_FIELD_SIGNATURE"
    index = 1
    while index < len(raw) and raw[index] in {0x1F, 0x20}:
        _, index = _compressed(raw, index + 1)
    while index < len(raw) and raw[index] in {0x10, 0x1D, 0x45}:
        index += 1
    if index >= len(raw):
        return "", "TRUNCATED_SIGNATURE"
    element = raw[index]
    index += 1
    if element in PRIMITIVES:
        return PRIMITIVES[element], "RESOLVED_PRIMITIVE"
    if element in {0x11, 0x12}:
        coded, _ = _compressed(raw, index)
        return _type_from_coded(pe, coded)
    if element == 0x15:
        if index >= len(raw) or raw[index] not in {0x11, 0x12}:
            return "", "INVALID_GENERIC_INSTANCE"
        coded, _ = _compressed(raw, index + 1)
        name, status = _type_from_coded(pe, coded)
        return name, "RESOLVED_GENERIC_DEFINITION" if status == "RESOLVED_TYPEDEF_OR_TYPEREF" else status
    return f"ELEMENT_TYPE_0x{element:02x}", "UNSUPPORTED_ELEMENT_TYPE"


def _actual_kind(type_name: str) -> str:
    lowered = type_name.casefold()
    checks = (
        ("text", ("textbox", "editbox", "memoedit", "richedit")),
        ("boolean", ("checkbox", "checkedit", "toggle")),
        ("choice", ("combobox", "radiobutton", "radiogroup", "checkedcombo")),
        ("lookup", ("lookup", "searchedit")),
        ("grid", ("grid", "treelist", "listview")),
        ("date", ("dateedit", "persiandate", "datetime")),
        ("numeric", ("numeric", "spinedit", "calcedit")),
        ("command", ("button", "menuitem", "baritem")),
        ("container", ("panel", "groupbox", "tab", "split", "layout")),
        ("media", ("picture", "image")),
        ("label", ("label",)),
    )
    return next((kind for kind, tokens in checks if any(token in lowered for token in tokens)), "other_or_unclassified")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--declared-fields", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = json.loads(args.binary_inventory.read_text(encoding="utf-8-sig"))
    declared = json.loads(args.declared_fields.read_text(encoding="utf-8-sig"))
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    forms_by_assembly: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for form in declared["forms"]:
        forms_by_assembly[form["assembly"]].append(form)
    forms = []
    hash_mismatches: list[str] = []
    metadata_failures: list[str] = []
    decode_failures: list[dict[str, str]] = []
    for assembly_name, source_forms in sorted(forms_by_assembly.items()):
        path = args.source_directory / assembly_name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[assembly_name]:
            hash_mismatches.append(assembly_name)
        try:
            pe = dnfile.dnPE(str(path))
            table = getattr(pe.net.mdtables, "TypeDef", None)
            type_rows = {_full_type_name(row): row for row in ([] if not table else table.rows)}
            for form in source_forms:
                type_row = type_rows[form["form_type"]]
                metadata_fields = {str(index.row.Name): index.row for index in type_row.FieldList or [] if index.row is not None}
                typed_fields = []
                for candidate in form["fields"]:
                    field_name = candidate["field_name"]
                    field_row = metadata_fields[field_name]
                    type_name, status = _decode(pe, bytes(field_row.Signature.value))
                    if not status.startswith("RESOLVED_"):
                        decode_failures.append({"form_type": form["form_type"], "field_name": field_name, "status": status})
                    actual_kind = _actual_kind(type_name)
                    typed_fields.append({
                        **candidate,
                        "clr_field_type": type_name,
                        "type_resolution_status": status,
                        "resolved_control_kind": actual_kind,
                        "prefix_kind_matches_resolved_kind": actual_kind == candidate["inferred_control_kind"],
                        "runtime_instance_behavior_visibility_binding_and_requiredness": "UNPROVEN",
                    })
                forms.append({
                    "assembly": assembly_name,
                    "form_type": form["form_type"],
                    "field_count": len(typed_fields),
                    "resolved_field_type_count": sum(row["type_resolution_status"].startswith("RESOLVED_") for row in typed_fields),
                    "prefix_kind_match_count": sum(row["prefix_kind_matches_resolved_kind"] for row in typed_fields),
                    "fields": typed_fields,
                })
        except Exception as exc:
            metadata_failures.append(f"{assembly_name}:{type(exc).__name__}")

    all_fields = [field for form in forms for field in form["fields"]]
    status_counts = Counter(field["type_resolution_status"] for field in all_fields)
    type_counts = Counter(field["clr_field_type"] for field in all_fields if field["clr_field_type"])
    actual_kind_counts = Counter(field["resolved_control_kind"] for field in all_fields)
    errors = []
    if declared.get("validation") != "PASS":
        errors.append("declared field source not PASS")
    if hash_mismatches or metadata_failures:
        errors.append("source package hash or metadata failure")
    if len(all_fields) != declared["summary"]["declared_control_field_count"]:
        errors.append("typed field count differs from declared field count")
    artifact = {
        "artifact": "varanegar_data_entry_declared_field_clr_type_resolution",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_HASH_VERIFIED_FIELD_SIGNATURE_AND_TYPEDEF_TYPEREF_METADATA_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "field_values_string_literals_resources_or_config_payloads_read_or_persisted": 0,
            "runtime_instance_behavior_visibility_binding_or_requiredness_inferred": 0,
        },
        "summary": {
            "selected_data_entry_form_count": len(forms),
            "declared_field_candidate_count": len(all_fields),
            "resolved_clr_field_type_count": sum(field["type_resolution_status"].startswith("RESOLVED_") for field in all_fields),
            "unresolved_clr_field_type_count": sum(not field["type_resolution_status"].startswith("RESOLVED_") for field in all_fields),
            "unique_resolved_clr_type_count": len(type_counts),
            "type_resolution_status_counts": dict(sorted(status_counts.items())),
            "resolved_control_kind_counts": dict(sorted(actual_kind_counts.items())),
            "prefix_kind_match_count": sum(field["prefix_kind_matches_resolved_kind"] for field in all_fields),
            "prefix_kind_mismatch_or_unclassified_count": sum(not field["prefix_kind_matches_resolved_kind"] for field in all_fields),
            "runtime_behavior_visibility_binding_or_requiredness_proven_count": 0,
            "source_hash_mismatch_count": len(hash_mismatches),
            "metadata_failure_count": len(metadata_failures),
            "validation_error_count": len(errors),
        },
        "top_resolved_clr_types": [{"clr_field_type": name, "field_count": count} for name, count in type_counts.most_common(40)],
        "forms": sorted(forms, key=lambda row: row["form_type"]),
        "decode_failures": decode_failures,
        "source_hash_mismatches": hash_mismatches,
        "metadata_failures": metadata_failures,
        "validation_errors": errors,
        "limits": [
            "Resolved CLR field type is static metadata, not proof that a runtime control instance is visible or enabled.",
            "TypeSpec generic signatures are not expanded and remain explicit failures.",
            "Field type does not prove label pairing, source binding, validation, requiredness or authorization.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
