"""Read declared field metadata for the seven priority Varanegar form gaps."""

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

from extract_varanegar_targeted_il_contracts import _full_type_name


PREFIXES = {
    "text": ("txt", "text"),
    "choice": ("cmb", "combo", "rad", "radio"),
    "boolean": ("chk", "check"),
    "lookup": ("look", "lookup", "ddl"),
    "grid": ("grid", "grd", "vngrid", "vgrid"),
    "date": ("date", "dt"),
    "numeric": ("num", "nud", "spin"),
    "command": ("btn", "button", "menu", "cmd"),
    "container": ("group", "panel", "tab", "split"),
    "media": ("pic", "image"),
    "label": ("label", "lbl"),
}

SENSITIVE_FIELD_FRAGMENTS = (
    "password",
    "connection",
    "credential",
    "secret",
    "token",
    "hostname",
    "servername",
)

BASE_TYPE_ASSEMBLY = {
    "BaseClasses.Objects.VNForm": "BaseClasses.dll",
    "Application.BaseTemaplateV2.UIBase.FormBaseSimpleDialog": "Application.BaseTemaplateV2.dll",
}


def _kind(name: str) -> str:
    lowered = name.casefold()
    return next(
        (kind for kind, prefixes in PREFIXES.items() if lowered.startswith(prefixes)),
        "unclassified_declared_field",
    )


def _safe_field_name(name: str) -> bool:
    lowered = name.casefold()
    return (
        bool(name)
        and "<" not in name
        and ">" not in name
        and lowered not in {"components", "disposed", "resourcemanager"}
        and not any(fragment in lowered for fragment in SENSITIVE_FIELD_FRAGMENTS)
    )


def _declared_fields(row: Any) -> tuple[list[dict[str, Any]], int]:
    fields = []
    excluded_sensitive_count = 0
    for field_index in row.FieldList or []:
        field_row = field_index.row
        field_name = "" if field_row is None else str(field_row.Name)
        if any(fragment in field_name.casefold() for fragment in SENSITIVE_FIELD_FRAGMENTS):
            excluded_sensitive_count += 1
            continue
        if not _safe_field_name(field_name):
            continue
        fields.append(
            {
                "field_name": field_name,
                "inferred_control_kind": _kind(field_name),
                "declared_in_type_metadata": True,
                "runtime_control_type": "UNPROVEN",
                "required_or_nullable_semantics": "UNPROVEN",
                "data_binding_or_source_column": "UNPROVEN",
                "visibility_or_enabled_state": "UNPROVEN",
            }
        )
    return sorted(fields, key=lambda item: item["field_name"].casefold()), excluded_sensitive_count


def _base_chain(
    initial_type: str | None,
    type_index: dict[str, Any],
) -> list[dict[str, Any]]:
    chain = []
    current = initial_type
    visited = set()
    while current and current not in visited:
        visited.add(current)
        row = type_index.get(current)
        if row is None:
            break
        fields, excluded_sensitive_count = _declared_fields(row)
        chain.append(
            {
                "base_type": current,
                "declared_field_count": len(fields),
                "excluded_sensitive_field_name_count": excluded_sensitive_count,
                "fields": fields,
            }
        )
        extends = None if not row.Extends else row.Extends.row
        current = "" if extends is None else _full_type_name(extends)
    return chain


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--form-gaps", required=True, type=Path)
    parser.add_argument("--call-graph", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = json.loads(args.binary_inventory.read_text(encoding="utf-8-sig"))
    gaps = json.loads(args.form_gaps.read_text(encoding="utf-8-sig"))
    call_graph = json.loads(args.call_graph.read_text(encoding="utf-8-sig"))
    expected_hash = {row["name"]: row["sha256"] for row in inventory["files"]}
    targets = [row for row in gaps["forms"] if row.get("priority") == "high"]
    target_by_assembly: dict[str, list[dict[str, Any]]] = {}
    for row in targets:
        target_by_assembly.setdefault(row["assembly"], []).append(row)
    resolution_by_type = {
        row["type"]: row for row in call_graph.get("resolutions", [])
    }
    contract_by_type = {
        row["type"]: row for row in call_graph.get("priority_form_contracts", [])
    }

    forms = []
    hash_mismatches: list[str] = []
    missing_types: list[str] = []
    metadata_failures: list[str] = []
    sensitive_field_name_count = 0
    base_type_indexes: dict[str, dict[str, Any]] = {}
    for assembly_name in sorted(set(BASE_TYPE_ASSEMBLY.values())):
        path = args.source_directory / assembly_name
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash.get(assembly_name):
            hash_mismatches.append(assembly_name)
        try:
            pe = dnfile.dnPE(str(path))
            type_table = getattr(pe.net.mdtables, "TypeDef", None)
            base_type_indexes[assembly_name] = {
                _full_type_name(row): row for row in ([] if not type_table else type_table.rows)
            }
        except Exception as exc:
            metadata_failures.append(f"{assembly_name}:{type(exc).__name__}")

    for assembly_name, assembly_targets in sorted(target_by_assembly.items()):
        path = args.source_directory / assembly_name
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash.get(assembly_name):
            hash_mismatches.append(assembly_name)
        try:
            pe = dnfile.dnPE(str(path))
            type_table = getattr(pe.net.mdtables, "TypeDef", None)
            types = {
                _full_type_name(row): row for row in ([] if not type_table else type_table.rows)
            }
            for target in sorted(assembly_targets, key=lambda item: item["type"]):
                form_type = target["type"]
                row = types.get(form_type)
                if row is None:
                    missing_types.append(form_type)
                    continue
                fields, excluded_sensitive_count = _declared_fields(row)
                sensitive_field_name_count += excluded_sensitive_count
                resolution = resolution_by_type.get(form_type, {})
                contract = contract_by_type.get(form_type, {}).get("contract", {})
                base_type = contract_by_type.get(form_type, {}).get("base_type")
                base_assembly = BASE_TYPE_ASSEMBLY.get(base_type)
                base_chain = _base_chain(
                    base_type,
                    base_type_indexes.get(base_assembly, {}),
                )
                inherited_base_field_count = sum(
                    item["declared_field_count"] for item in base_chain
                )
                forms.append(
                    {
                        "assembly": assembly_name,
                        "form_type": form_type,
                        "base_type": base_type,
                        "base_metadata_assembly": base_assembly or "EXTERNAL_OR_UNMAPPED",
                        "base_type_chain": base_chain,
                        "inherited_base_field_count": inherited_base_field_count,
                        "page_shape": target["page_shape"],
                        "entrypoint_status": resolution.get("status", "UNPROVEN"),
                        "declared_control_field_count": len(fields),
                        "excluded_sensitive_field_name_count": excluded_sensitive_count,
                        "write_like_methods": contract.get("write_like_methods", []),
                        "permission_methods": contract.get("permission_methods", []),
                        "fields": sorted(fields, key=lambda item: item["field_name"].casefold()),
                    }
                )
        except Exception as exc:
            metadata_failures.append(f"{assembly_name}:{type(exc).__name__}")

    all_fields = [field for form in forms for field in form["fields"]]
    all_inherited_fields = [
        field
        for form in forms
        for base in form["base_type_chain"]
        for field in base["fields"]
    ]
    errors = []
    if len(targets) != 7:
        errors.append("priority form set no longer contains seven forms")
    if hash_mismatches:
        errors.append("source package hash mismatch")
    if missing_types or metadata_failures:
        errors.append("priority type metadata missing or failed")
    if len(forms) != len(targets):
        errors.append("priority form metadata coverage incomplete")

    artifact = {
        "artifact": "varanegar_priority_gap_declared_field_metadata",
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
            "runtime_binding_requiredness_or_visibility_inferred": 0,
        },
        "summary": {
            "selected_priority_form_count": len(targets),
            "resolved_form_type_count": len(forms),
            "form_with_declared_control_field_count": sum(
                row["declared_control_field_count"] > 0 for row in forms
            ),
            "form_without_declared_control_field_count": sum(
                row["declared_control_field_count"] == 0 for row in forms
            ),
            "declared_control_field_count": len(all_fields),
            "inherited_base_field_count": len(all_inherited_fields),
            "base_type_chain_row_count": sum(len(row["base_type_chain"]) for row in forms),
            "unique_declared_field_name_count": len(
                {field["field_name"] for field in all_fields}
            ),
            "field_kind_counts": dict(
                sorted(Counter(field["inferred_control_kind"] for field in all_fields).items())
            ),
            "sensitive_field_name_excluded_count": sensitive_field_name_count,
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
            "Declared CLR field names do not prove runtime visibility, enabled state, label text, binding or requiredness.",
            "Inherited base fields are reported separately and remain framework capability evidence, not proof that every control is visible on the derived form.",
            "Entrypoint status is inherited from the bounded 62-assembly call-graph scan.",
            "No assembly was loaded or executed and no UI or database action occurred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
