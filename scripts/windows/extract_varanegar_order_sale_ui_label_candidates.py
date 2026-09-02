"""Extract static UI label candidates for three order-to-sale entry forms."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_treasury_ui_label_candidates import (
    _assembly_map,
    _extract_form,
    _field_map,
)


TARGET_FORMS = (
    "VN.SDS.Sales.UI.Order.FormOrderDataEntry",
    "VN.SDS.Sales.UI.Sale.FormSaleDataEntry",
    "VN.SDS.Sales.UI.RetSale.FormRetSaleDataEntry",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--declared-fields", required=True, type=Path)
    parser.add_argument("--target-form", action="append", dest="target_forms")
    parser.add_argument(
        "--artifact-identity",
        default="varanegar_order_sale_return_static_ui_label_candidates",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    declared: dict[str, Any] = json.loads(
        args.declared_fields.read_text(encoding="utf-8-sig")
    )
    assemblies = _assembly_map(declared)
    fields = _field_map(declared)
    target_forms = tuple(args.target_forms or TARGET_FORMS)
    errors: list[str] = []
    forms: list[dict[str, Any]] = []
    assembly_hashes: dict[str, str] = {}
    for form_type in target_forms:
        assembly = assemblies.get(form_type)
        if not assembly:
            errors.append(f"assembly not resolved for {form_type}")
            continue
        path = args.source_directory / assembly
        if not path.is_file():
            errors.append(f"assembly missing: {assembly}")
            continue
        assembly_hashes[assembly] = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            row = _extract_form(path, form_type, fields.get(form_type, {}))
            row["assembly"] = assembly
            forms.append(row)
        except Exception as exc:
            errors.append(f"{form_type}:{type(exc).__name__}")
    if len(forms) != len(target_forms) or any(
        not form.get("found") or not form.get("initializer_found") for form in forms
    ):
        errors.append("not all selected InitializeComponent methods were resolved")

    assignments = [item for form in forms for item in form.get("assignments", [])]
    field_assignments = [
        item
        for item in assignments
        if item["target_kind"] in {"DECLARED_CONTROL", "UNREGISTERED_FORM_FIELD"}
    ]
    declared_field_assignments = [
        item for item in assignments if item["target_kind"] == "DECLARED_CONTROL"
    ]
    likely_titles = []
    for form in forms:
        candidates = [
            item
            for item in form.get("assignments", [])
            if item["target_kind"] == "FORM_OR_UNRESOLVED_TARGET"
            and item["setter_call"] == "System.Windows.Forms.Control.set_Text"
            and any("\u0600" <= character <= "\u06ff" for character in item["ui_text"])
        ]
        selected = max(candidates, key=lambda row: row["instruction_offset"], default=None)
        form["likely_form_title_candidates"] = [] if selected is None else [
            {
                "ui_text": selected["ui_text"],
                "ui_text_sha256": selected["ui_text_sha256"],
                "resolution": "LAST_UNATTRIBUTED_PERSIAN_CONTROL_TEXT_STATIC_HEURISTIC",
                "runtime_title_proven": False,
            }
        ]
        likely_titles.extend(form["likely_form_title_candidates"])
    duplicate_counts: dict[tuple[str, str], int] = {}
    for form in forms:
        for item in form.get("assignments", []):
            if item["field_name"]:
                key = (form["form_type"], item["field_name"])
                duplicate_counts[key] = duplicate_counts.get(key, 0) + 1
    ambiguous = [
        {"form_type": key[0], "field_name": key[1], "assignment_count": count}
        for key, count in sorted(duplicate_counts.items())
        if count > 1
    ]
    artifact = {
        "artifact": args.artifact_identity,
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_STATIC_INITIALIZE_COMPONENT_IL_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "business_rows_or_field_values_read_or_persisted": 0,
            "non_ui_setter_string_literals_persisted": 0,
        },
        "summary": {
            "target_form_count": len(target_forms),
            "resolved_initializer_count": sum(
                bool(form.get("initializer_found")) for form in forms
            ),
            "declared_control_field_count": sum(
                form.get("declared_field_count", 0) for form in forms
            ),
            "static_ui_assignment_candidate_count": len(assignments),
            "declared_control_label_candidate_count": len(declared_field_assignments),
            "unregistered_form_field_label_candidate_count": len(field_assignments)
            - len(declared_field_assignments),
            "likely_form_title_candidate_count": len(likely_titles),
            "form_or_unresolved_target_candidate_count": len(assignments)
            - len(field_assignments),
            "unique_form_field_with_label_candidate_count": len(
                duplicate_counts
            ),
            "ambiguous_declared_control_count": len(ambiguous),
            "rejected_literal_count": sum(
                form.get("rejected_literal_count", 0) for form in forms
            ),
            "runtime_visibility_or_effective_text_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "source_assembly_sha256": assembly_hashes,
        "forms": forms,
        "ambiguous_declared_controls": ambiguous,
        "validation_errors": errors,
        "limits": [
            "Static InitializeComponent text does not prove runtime visibility, dynamic resources, effective permission state or label-to-input layout pairing.",
            "Likely form titles use the last unattributed Persian Control.set_Text assignment heuristic and remain runtime-unproven.",
            "Only inline strings assigned to allowlisted UI text setters are persisted; business values and other string literals are excluded.",
            "Repeated static assignments are preserved as ambiguous and must not be chosen silently.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
