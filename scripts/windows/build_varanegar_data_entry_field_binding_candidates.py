"""Build conservative static field-to-property binding candidates from method co-occurrence."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_priority_gap_call_graph import _type_from_call


FIELD_PREFIXES = ("menubutton", "button", "lookup", "look", "combo", "cmb", "check", "chk", "radio", "rad", "grid", "grd", "text", "txt", "date", "dt", "num", "nud", "spin")
FIELD_SUFFIXES = ("repositoryitem", "bindingSource", "gridview", "lookupedit", "lookuptable", "textedit", "dateedit", "editbox", "textbox", "control", "view")


def _normalized(value: str) -> str:
    return "".join(char for char in value.casefold() if char.isalnum())


def _field_core(name: str) -> str:
    value = _normalized(name)
    changed = True
    while changed:
        changed = False
        for prefix in FIELD_PREFIXES:
            if value.startswith(prefix.casefold()) and len(value) - len(prefix) >= 3:
                value = value[len(prefix):]
                changed = True
                break
        for suffix in FIELD_SUFFIXES:
            if value.endswith(suffix.casefold()) and len(value) - len(suffix) >= 3:
                value = value[: -len(suffix)]
                changed = True
                break
    return value


def _property(call: str) -> tuple[str, str] | None:
    target_type = _type_from_call(call)
    prefix = target_type + "."
    member = call[len(prefix):] if call.startswith(prefix) else call.rsplit(".", 1)[-1]
    if not member.startswith(("get_", "set_")):
        return None
    lowered = target_type.casefold()
    if any(token in lowered for token in ("system.", "devexpress.", "janus.", "windows.forms", ".ui.", ".uicomponent.")):
        return None
    if not any(token in lowered for token in (".datalayer.", ".dataaccess.", ".entityhelper.", ".entity.", ".business.", "treasuryold.datalayer.")):
        return None
    return f"{target_type}.{member}", member[4:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--field-types", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    il_source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    typed = json.loads(args.field_types.read_text(encoding="utf-8-sig"))
    typed_by_form = {row["form_type"]: row for row in typed["forms"]}
    forms = []
    all_fields = []
    for assembly in il_source["raw_il"]:
        for target in assembly["target_types"]:
            form_type = target["type"]
            typed_form = typed_by_form[form_type]
            typed_fields = {row["field_name"]: row for row in typed_form["fields"]}
            candidate_calls: dict[str, set[str]] = {name: set() for name in typed_fields}
            strong_calls: dict[str, set[str]] = {name: set() for name in typed_fields}
            singleton_calls: dict[str, set[str]] = {name: set() for name in typed_fields}
            evidence_methods: dict[str, set[str]] = {name: set() for name in typed_fields}
            for method in target["methods"]:
                local_fields = sorted({
                    ref[len(form_type) + 1:]
                    for ref in method["referenced_fields"]
                    if ref.startswith(form_type + ".") and ref[len(form_type) + 1:] in typed_fields
                })
                properties = sorted({item for call in method["calls"] if (item := _property(call)) is not None})
                for field_name in local_fields:
                    field_core = _field_core(field_name)
                    for full_call, property_name in properties:
                        candidate_calls[field_name].add(full_call)
                        property_core = _normalized(property_name)
                        if min(len(field_core), len(property_core)) >= 4 and (field_core == property_core or field_core.endswith(property_core) or property_core.endswith(field_core)):
                            strong_calls[field_name].add(full_call)
                            evidence_methods[field_name].add(method["method"])
                    if len(local_fields) == 1 and len(properties) == 1:
                        singleton_calls[field_name].add(properties[0][0])
                        evidence_methods[field_name].add(method["method"])
            field_rows = []
            for field_name, source_field in typed_fields.items():
                strong = sorted(strong_calls[field_name])
                singleton = sorted(singleton_calls[field_name] - strong_calls[field_name])
                cooccurrence = sorted(candidate_calls[field_name] - strong_calls[field_name] - singleton_calls[field_name])
                if strong:
                    status = "STRONG_NAME_AND_METHOD_COOCCURRENCE_CANDIDATE"
                elif singleton:
                    status = "SINGLE_FIELD_SINGLE_PROPERTY_METHOD_COOCCURRENCE_CANDIDATE"
                elif cooccurrence:
                    status = "AMBIGUOUS_METHOD_COOCCURRENCE_ONLY"
                else:
                    status = "NO_ENTITY_OR_DATA_PROPERTY_CANDIDATE"
                row = {
                    "field_name": field_name,
                    "clr_field_type": source_field["clr_field_type"],
                    "resolved_control_kind": source_field["resolved_control_kind"],
                    "binding_candidate_status": status,
                    "strong_name_property_calls": strong,
                    "singleton_method_property_calls": singleton,
                    "ambiguous_cooccurring_property_calls": cooccurrence,
                    "evidence_methods": sorted(evidence_methods[field_name]),
                    "runtime_binding_proven": False,
                    "source_column_or_query_parameter_proven": False,
                }
                field_rows.append(row)
                all_fields.append({"form_type": form_type, **row})
            forms.append({
                "assembly": assembly["file"],
                "form_type": form_type,
                "field_count": len(field_rows),
                "binding_candidate_status_counts": dict(sorted(Counter(row["binding_candidate_status"] for row in field_rows).items())),
                "fields": sorted(field_rows, key=lambda row: row["field_name"].casefold()),
            })

    status_counts = Counter(row["binding_candidate_status"] for row in all_fields)
    unique_strong_calls = {call for row in all_fields for call in row["strong_name_property_calls"]}
    errors = []
    if il_source.get("summary", {}).get("selected_form_count") != len(forms) or typed.get("validation") != "PASS":
        errors.append("source form or type coverage mismatch")
    if len(all_fields) != typed["summary"]["declared_field_candidate_count"]:
        errors.append("field count mismatch")
    artifact = {
        "artifact": "varanegar_data_entry_static_field_to_property_binding_candidates",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_METHOD_LEVEL_COOCCURRENCE_FROM_REDACTED_IL_AND_FIELD_TYPES",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "application_commands_executed": 0,
            "field_values_string_literals_or_business_rows_read_or_persisted": 0,
            "runtime_bindings_source_columns_or_query_parameters_inferred_as_proven": 0,
        },
        "summary": {
            "selected_data_entry_form_count": len(forms),
            "field_candidate_count": len(all_fields),
            "binding_candidate_status_counts": dict(sorted(status_counts.items())),
            "field_with_strong_name_candidate_count": status_counts["STRONG_NAME_AND_METHOD_COOCCURRENCE_CANDIDATE"],
            "field_with_singleton_method_candidate_count": status_counts["SINGLE_FIELD_SINGLE_PROPERTY_METHOD_COOCCURRENCE_CANDIDATE"],
            "field_with_ambiguous_cooccurrence_count": status_counts["AMBIGUOUS_METHOD_COOCCURRENCE_ONLY"],
            "field_without_property_candidate_count": status_counts["NO_ENTITY_OR_DATA_PROPERTY_CANDIDATE"],
            "unique_strong_name_property_call_count": len(unique_strong_calls),
            "runtime_binding_proven_count": 0,
            "source_column_or_query_parameter_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "forms": sorted(forms, key=lambda row: row["form_type"]),
        "validation_errors": errors,
        "limits": [
            "A field and entity property used in one method can still belong to different branches or records.",
            "Strong name correspondence is a mapping candidate, not runtime binding or source-column proof.",
            "Properties reached through generic dispatch, reflection, resources or inherited base methods can be missed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
