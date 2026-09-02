"""Extract DevExpress layout-item to control bindings for selected sales forms."""

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
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import Token

from extract_varanegar_targeted_il_contracts import (
    _full_type_name,
    _owner_maps,
    _resolve_token,
    _text,
)


def _type_row(pe: dnfile.dnPE, full_name: str) -> Any | None:
    table = getattr(pe.net.mdtables, "TypeDef", None)
    return next(
        (row for row in ([] if not table else table.rows) if _full_type_name(row) == full_name),
        None,
    )


def _initializer(row: Any) -> Any | None:
    return next(
        (
            index.row
            for index in row.MethodList or []
            if index.row is not None
            and _text(index.row.Name) == "InitializeComponent"
            and index.row.Rva
        ),
        None,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--full-field-metadata", required=True, type=Path)
    parser.add_argument(
        "--artifact-identity",
        default="varanegar_order_sale_return_static_layout_item_control_bindings",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    metadata: dict[str, Any] = json.loads(
        args.full_field_metadata.read_text(encoding="utf-8-sig")
    )
    fields_by_form = {
        form["form_type"]: {field["field_name"]: field for field in form["fields"]}
        for form in metadata["forms"]
    }
    forms_by_assembly: dict[str, list[str]] = {}
    for form in metadata["forms"]:
        forms_by_assembly.setdefault(form["assembly"], []).append(form["form_type"])

    forms: list[dict[str, Any]] = []
    errors: list[str] = []
    assembly_hashes: dict[str, str] = {}
    for assembly, form_types in sorted(forms_by_assembly.items()):
        path = args.source_directory / assembly
        if not path.is_file():
            errors.append(f"assembly missing: {assembly}")
            continue
        assembly_hashes[assembly] = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            pe = dnfile.dnPE(str(path))
            method_owners, field_owners = _owner_maps(pe)
            for form_type in sorted(form_types):
                row = _type_row(pe, form_type)
                method = None if row is None else _initializer(row)
                if row is None or method is None:
                    errors.append(f"InitializeComponent missing: {form_type}")
                    continue
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
                instructions = list(body.instructions)
                form_fields = fields_by_form[form_type]
                bindings: list[dict[str, Any]] = []
                rejected_shape_count = 0
                for position, instruction in enumerate(instructions):
                    if instruction.mnemonic not in {"call", "callvirt"} or not isinstance(
                        instruction.operand, Token
                    ):
                        continue
                    called = _resolve_token(
                        pe, instruction.operand, method_owners, field_owners
                    )
                    if not called.endswith(".set_Control"):
                        continue
                    referenced: list[str] = []
                    for prior_position in range(max(0, position - 14), position):
                        prior = instructions[prior_position]
                        if "fld" not in prior.mnemonic or not isinstance(prior.operand, Token):
                            continue
                        resolved = _resolve_token(
                            pe, prior.operand, method_owners, field_owners
                        )
                        if resolved.startswith(form_type + "."):
                            candidate = resolved.rsplit(".", 1)[-1]
                            if candidate in form_fields:
                                referenced.append(candidate)
                    if len(referenced) < 2:
                        rejected_shape_count += 1
                        continue
                    layout_field, control_field = referenced[-2:]
                    layout = form_fields[layout_field]
                    control = form_fields[control_field]
                    if layout["static_component_kind"] != "layout":
                        rejected_shape_count += 1
                        continue
                    bindings.append(
                        {
                            "layout_field": layout_field,
                            "layout_clr_type": layout["clr_field_type"],
                            "static_label_candidate": layout[
                                "static_ui_text_candidate"
                            ],
                            "control_field": control_field,
                            "control_clr_type": control["clr_field_type"],
                            "control_component_kind": control[
                                "static_component_kind"
                            ],
                            "web_input_candidate": control["web_input_candidate"],
                            "setter_call": called,
                            "static_initialize_component_binding": True,
                            "runtime_layout_visibility_or_effective_label_proven": False,
                        }
                    )
                unique = {
                    (item["layout_field"], item["control_field"]): item
                    for item in bindings
                }
                control_counts = Counter(
                    item["control_field"] for item in unique.values()
                )
                forms.append(
                    {
                        "assembly": assembly,
                        "form_type": form_type,
                        "initializer_instruction_count": len(instructions),
                        "layout_binding_candidate_count": len(unique),
                        "web_input_layout_binding_candidate_count": sum(
                            item["web_input_candidate"] for item in unique.values()
                        ),
                        "web_input_binding_with_static_label_candidate_count": sum(
                            item["web_input_candidate"]
                            and bool(item["static_label_candidate"])
                            for item in unique.values()
                        ),
                        "control_with_multiple_layout_binding_candidate_count": sum(
                            count > 1 for count in control_counts.values()
                        ),
                        "rejected_set_control_shape_count": rejected_shape_count,
                        "bindings": sorted(
                            unique.values(),
                            key=lambda item: (item["layout_field"], item["control_field"]),
                        ),
                    }
                )
        except Exception as exc:
            errors.append(f"{assembly}:{type(exc).__name__}")

    bindings = [item for form in forms for item in form["bindings"]]
    web_bindings = [item for item in bindings if item["web_input_candidate"]]
    if metadata.get("validation") != "PASS":
        errors.append("source full field metadata is not PASS")
    if len(forms) != len(fields_by_form):
        errors.append("not all selected forms resolved")
    artifact = {
        "artifact": args.artifact_identity,
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_STATIC_INITIALIZE_COMPONENT_LAYOUT_SET_CONTROL_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "business_rows_field_values_resources_or_configuration_persisted": 0,
            "runtime_layout_visibility_effective_label_or_binding_inferred": 0,
        },
        "summary": {
            "target_form_count": len(fields_by_form),
            "resolved_form_count": len(forms),
            "layout_binding_candidate_count": len(bindings),
            "web_input_layout_binding_candidate_count": len(web_bindings),
            "web_input_binding_with_static_label_candidate_count": sum(
                bool(item["static_label_candidate"]) for item in web_bindings
            ),
            "unique_bound_control_count": len(
                {(form["form_type"], item["control_field"]) for form in forms for item in form["bindings"]}
            ),
            "control_with_multiple_layout_binding_candidate_count": sum(
                form["control_with_multiple_layout_binding_candidate_count"]
                for form in forms
            ),
            "rejected_set_control_shape_count": sum(
                form["rejected_set_control_shape_count"] for form in forms
            ),
            "runtime_layout_visibility_effective_label_or_binding_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "source_assembly_sha256": assembly_hashes,
        "forms": forms,
        "validation_errors": errors,
        "limits": [
            "The pair is an exact static LayoutItem.set_Control IL candidate but runtime layout visibility and dynamic relayout remain unproven.",
            "A layout item may have empty or resource-backed text and repeated control bindings require owner/runtime review.",
            "Layout pairing does not prove data binding, default, requiredness, validation order, authorization or target request mapping.",
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
