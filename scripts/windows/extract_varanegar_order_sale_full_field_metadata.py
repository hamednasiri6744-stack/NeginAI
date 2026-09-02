"""Decode every declared field for selected order-to-sale entry forms."""

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

from extract_varanegar_data_entry_field_types import _decode
from extract_varanegar_targeted_il_contracts import _full_type_name


TARGET_FORMS = (
    "VN.SDS.Sales.UI.Order.FormOrderDataEntry",
    "VN.SDS.Sales.UI.Sale.FormSaleDataEntry",
    "VN.SDS.Sales.UI.RetSale.FormRetSaleDataEntry",
)


def _selected_kind(type_name: str) -> str:
    lowered = type_name.casefold()
    checks = (
        ("lookup", ("lookup", "searchedit")),
        ("boolean", ("checkedit", "checkbox", "toggle")),
        ("date", ("dateedit", "persiandate", "datetimeedit")),
        ("numeric", ("calcedit", "spinedit", "numeric")),
        ("editor", ("textedit", "memoedit", "buttonedit", "richedit")),
        ("command", ("simplebutton", "barbuttonitem", "menuitem")),
        ("grid", ("gridcontrol", "gridview", "treelist", "gridcolumn")),
        ("label", ("label",)),
        ("layout", ("layout", "emptyspace", "splitcontainer", "tabnavigation", "panelcontrol", "groupcontrol")),
        ("infrastructure", ("bindingsource", "icontainer", "backgroundworker", "components")),
    )
    return next(
        (kind for kind, tokens in checks if any(token in lowered for token in tokens)),
        "state_or_unclassified",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--ui-labels", required=True, type=Path)
    parser.add_argument("--assembly", default="VN.SDS.Sales.UI.dll")
    parser.add_argument(
        "--artifact-identity",
        default="varanegar_order_sale_return_complete_declared_field_type_and_label_metadata",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    inventory: dict[str, Any] = json.loads(
        args.binary_inventory.read_text(encoding="utf-8-sig")
    )
    labels: dict[str, Any] = json.loads(args.ui_labels.read_text(encoding="utf-8-sig"))
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    assembly = args.assembly
    target_forms = tuple(row["form_type"] for row in labels["forms"])
    path = args.source_directory / assembly
    errors: list[str] = []
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected.get(assembly) != actual_hash:
        errors.append("selected assembly hash differs from binary inventory")
    labels_by_form = {
        row["form_type"]: {
            item["field_name"]: item
            for item in row["assignments"]
            if item["field_name"]
        }
        for row in labels["forms"]
    }
    forms: list[dict[str, Any]] = []
    decode_failures: list[dict[str, str]] = []
    try:
        pe = dnfile.dnPE(str(path))
        table = getattr(pe.net.mdtables, "TypeDef", None)
        types = {
            _full_type_name(row): row for row in ([] if not table else table.rows)
        }
        for form_type in target_forms:
            type_row = types.get(form_type)
            if type_row is None:
                errors.append(f"type missing: {form_type}")
                continue
            fields = []
            form_labels = labels_by_form.get(form_type, {})
            for index in type_row.FieldList or []:
                row = index.row
                if row is None:
                    continue
                field_name = str(row.Name)
                type_name, status = _decode(pe, bytes(row.Signature.value))
                if not status.startswith("RESOLVED_"):
                    decode_failures.append(
                        {
                            "form_type": form_type,
                            "field_name": field_name,
                            "status": status,
                        }
                    )
                kind = _selected_kind(type_name)
                label = form_labels.get(field_name)
                fields.append(
                    {
                        "field_name": field_name,
                        "clr_field_type": type_name,
                        "type_resolution_status": status,
                        "static_component_kind": kind,
                        "ui_component_candidate": kind
                        not in {"state_or_unclassified", "infrastructure"},
                        "web_input_candidate": kind
                        in {"lookup", "boolean", "date", "numeric", "editor"},
                        "compiler_generated_or_backing_field": "<" in field_name
                        or ">" in field_name,
                        "static_ui_text_candidate": None
                        if label is None
                        else label["ui_text"],
                        "static_ui_text_target_kind": None
                        if label is None
                        else label["target_kind"],
                        "runtime_visibility_enabled_state_binding_requiredness_and_value": "UNPROVEN",
                    }
                )
            forms.append(
                {
                    "assembly": assembly,
                    "form_type": form_type,
                    "declared_field_count": len(fields),
                    "ui_component_candidate_count": sum(
                        row["ui_component_candidate"] for row in fields
                    ),
                    "web_input_candidate_count": sum(
                        row["web_input_candidate"] for row in fields
                    ),
                    "ui_component_with_static_text_candidate_count": sum(
                        row["ui_component_candidate"]
                        and bool(row["static_ui_text_candidate"])
                        for row in fields
                    ),
                    "state_or_infrastructure_field_count": sum(
                        not row["ui_component_candidate"] for row in fields
                    ),
                    "fields": fields,
                }
            )
    except Exception as exc:
        errors.append(f"metadata parse failed: {type(exc).__name__}")

    all_fields = [row for form in forms for row in form["fields"]]
    component_fields = [row for row in all_fields if row["ui_component_candidate"]]
    web_inputs = [row for row in all_fields if row["web_input_candidate"]]
    status_counts = Counter(row["type_resolution_status"] for row in all_fields)
    kind_counts = Counter(row["static_component_kind"] for row in all_fields)
    if labels.get("validation") != "PASS":
        errors.append("source UI-label artifact is not PASS")
    if len(forms) != len(target_forms):
        errors.append("not all selected form types resolved")
    artifact = {
        "artifact": args.artifact_identity,
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_HASH_VERIFIED_FIELD_SIGNATURE_TYPE_AND_STATIC_UI_LABEL_METADATA_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "field_values_resources_configuration_or_business_rows_read_or_persisted": 0,
            "runtime_visibility_enabled_state_binding_requiredness_or_value_inferred": 0,
        },
        "summary": {
            "target_form_count": len(target_forms),
            "resolved_form_count": len(forms),
            "declared_field_count": len(all_fields),
            "resolved_field_type_count": sum(
                row["type_resolution_status"].startswith("RESOLVED_")
                for row in all_fields
            ),
            "unresolved_field_type_count": sum(
                not row["type_resolution_status"].startswith("RESOLVED_")
                for row in all_fields
            ),
            "ui_component_candidate_count": len(component_fields),
            "web_input_candidate_count": len(web_inputs),
            "ui_component_with_static_text_candidate_count": sum(
                bool(row["static_ui_text_candidate"]) for row in component_fields
            ),
            "state_or_infrastructure_field_count": len(all_fields)
            - len(component_fields),
            "compiler_generated_or_backing_field_count": sum(
                row["compiler_generated_or_backing_field"] for row in all_fields
            ),
            "static_component_kind_counts": dict(sorted(kind_counts.items())),
            "type_resolution_status_counts": dict(sorted(status_counts.items())),
            "runtime_behavior_binding_requiredness_or_value_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "source_assembly_sha256": {assembly: actual_hash},
        "forms": forms,
        "decode_failures": decode_failures,
        "validation_errors": errors,
        "limits": [
            "Every declared field is retained so control fields are not lost by legacy naming-prefix filters.",
            "Static CLR type and UI text do not prove runtime visibility, enabled state, layout, binding, default, requiredness, value or authorization.",
            "Other-or-unclassified fields may include domain state, event infrastructure, custom controls or unsupported signatures and require separate review.",
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
