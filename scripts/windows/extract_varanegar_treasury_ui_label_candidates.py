from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

from extract_varanegar_targeted_il_contracts import (
    _full_type_name,
    _owner_maps,
    _resolve_token,
    _text,
)


ALLOWED_SETTERS = {"set_Text", "set_Caption", "set_HeaderText", "set_Title"}
UNSAFE_TEXT = re.compile(
    r"(?:https?://|\\\\|[A-Za-z]:\\|@|password|pwd|connection\s*string|"
    r"select\s+.+\s+from|insert\s+into|update\s+.+\s+set|delete\s+from)",
    re.IGNORECASE,
)


def _safe_ui_text(value: str) -> bool:
    return (
        0 < len(value) <= 160
        and value.strip() == value
        and not any(character in value for character in "\r\n\t")
        and all(character.isprintable() for character in value)
        and any(character.isalpha() for character in value)
        and UNSAFE_TEXT.search(value) is None
    )


def _assembly_map(declared: dict[str, Any]) -> dict[str, str]:
    return {
        row["form_type"]: row["assembly"]
        for row in declared["forms"]
        if row.get("form_type") and row.get("assembly")
    }


def _field_map(declared: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        row["form_type"]: {field["field_name"]: field for field in row["fields"]}
        for row in declared["forms"]
    }


def _find_type(pe: dnfile.dnPE, full_name: str) -> Any | None:
    table = getattr(pe.net.mdtables, "TypeDef", None)
    if not table:
        return None
    return next((row for row in table.rows if _full_type_name(row) == full_name), None)


def _initializer(type_row: Any) -> Any | None:
    for index in type_row.MethodList or []:
        row = index.row
        if row is not None and _text(row.Name) == "InitializeComponent" and row.Rva:
            return row
    return None


def _resolved_operand(
    pe: dnfile.dnPE,
    operand: Any,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
) -> str | None:
    if not isinstance(operand, Token):
        return None
    return _resolve_token(pe, operand, method_owners, field_owners)


def _extract_form(
    path: Path,
    form_type: str,
    declared_fields: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    method_owners, field_owners = _owner_maps(pe)
    type_row = _find_type(pe, form_type)
    if type_row is None:
        return {"form_type": form_type, "found": False, "assignments": []}
    method = _initializer(type_row)
    if method is None:
        return {
            "form_type": form_type,
            "found": True,
            "initializer_found": False,
            "assignments": [],
        }
    body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
    instructions = list(body.instructions)
    assignments: list[dict[str, Any]] = []
    rejected_literal_count = 0
    for position, instruction in enumerate(instructions):
        if instruction.mnemonic not in {"call", "callvirt"}:
            continue
        called = _resolved_operand(
            pe, instruction.operand, method_owners, field_owners
        )
        if called is None or called.rsplit(".", 1)[-1] not in ALLOWED_SETTERS:
            continue
        literal_position = None
        literal_value = None
        for prior_position in range(position - 1, max(-1, position - 13), -1):
            operand = instructions[prior_position].operand
            if isinstance(operand, StringToken):
                item = pe.net.user_strings.get(operand.rid)
                literal_position = prior_position
                literal_value = "" if item is None else _text(item)
                break
            if instructions[prior_position].mnemonic in {"call", "callvirt", "newobj"}:
                break
        if literal_position is None or literal_value is None:
            continue
        if not _safe_ui_text(literal_value):
            rejected_literal_count += 1
            continue
        field_name = None
        field_declared = False
        for prior_position in range(literal_position - 1, max(-1, literal_position - 9), -1):
            prior = instructions[prior_position]
            if "fld" in prior.mnemonic:
                resolved = _resolved_operand(
                    pe, prior.operand, method_owners, field_owners
                )
                candidate = None if resolved is None else resolved.rsplit(".", 1)[-1]
                if resolved is not None and resolved.startswith(form_type + "."):
                    field_name = candidate
                    field_declared = candidate in declared_fields
                    break
            if prior.mnemonic in {"call", "callvirt"}:
                break
        target_kind = (
            "DECLARED_CONTROL"
            if field_name and field_declared
            else "UNREGISTERED_FORM_FIELD"
            if field_name
            else "FORM_OR_UNRESOLVED_TARGET"
        )
        assignments.append(
            {
                "target_kind": target_kind,
                "field_name": field_name,
                "setter": called.rsplit(".", 1)[-1],
                "setter_call": called,
                "ui_text": literal_value,
                "ui_text_sha256": hashlib.sha256(
                    literal_value.encode("utf-8")
                ).hexdigest(),
                "instruction_offset": int(instruction.offset),
                "static_initialize_component_candidate": True,
                "runtime_visibility_or_effective_text_proven": False,
            }
        )
    unique = {
        (row["field_name"], row["setter"], row["ui_text"]): row
        for row in assignments
    }
    return {
        "form_type": form_type,
        "found": True,
        "initializer_found": True,
        "initializer_instruction_count": len(instructions),
        "declared_field_count": len(declared_fields),
        "assignment_count": len(unique),
        "declared_control_assignment_count": sum(
            row["target_kind"] == "DECLARED_CONTROL" for row in unique.values()
        ),
        "form_or_unresolved_assignment_count": sum(
            row["target_kind"] == "FORM_OR_UNRESOLVED_TARGET"
            for row in unique.values()
        ),
        "unregistered_form_field_assignment_count": sum(
            row["target_kind"] == "UNREGISTERED_FORM_FIELD"
            for row in unique.values()
        ),
        "rejected_literal_count": rejected_literal_count,
        "assignments": sorted(
            unique.values(),
            key=lambda row: (
                row["field_name"] or "",
                row["setter"],
                row["ui_text"],
            ),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--declared-fields", required=True, type=Path)
    parser.add_argument("--treasury-web-fields", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    declared = json.loads(args.declared_fields.read_text(encoding="utf-8-sig"))
    treasury = json.loads(args.treasury_web_fields.read_text(encoding="utf-8-sig"))
    assemblies = _assembly_map(declared)
    fields = _field_map(declared)
    target_forms = sorted(row["form_type"] for row in treasury["forms"])
    forms: list[dict[str, Any]] = []
    assembly_hashes: dict[str, str] = {}
    errors: list[str] = []
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

    assignments = [item for form in forms for item in form.get("assignments", [])]
    field_assignments = [
        item for item in assignments if item["target_kind"] == "DECLARED_CONTROL"
    ]
    duplicate_field_texts = Counter(
        (form["form_type"], item["field_name"])
        for form in forms
        for item in form.get("assignments", [])
        if item["field_name"]
    )
    ambiguous_fields = [
        {"form_type": form_type, "field_name": field_name, "assignment_count": count}
        for (form_type, field_name), count in sorted(duplicate_field_texts.items())
        if count > 1
    ]
    if len(forms) != len(target_forms) or any(
        not form.get("found") or not form.get("initializer_found") for form in forms
    ):
        errors.append("not all target InitializeComponent methods were resolved")
    artifact = {
        "artifact": "varanegar_treasury_static_ui_label_candidates",
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
            "static_ui_assignment_candidate_count": len(assignments),
            "declared_control_label_candidate_count": len(field_assignments),
            "form_or_unresolved_target_candidate_count": len(assignments)
            - len(field_assignments),
            "unique_declared_control_with_label_candidate_count": len(
                {
                    (form["form_type"], item["field_name"])
                    for form in forms
                    for item in form.get("assignments", [])
                    if item["field_name"]
                }
            ),
            "ambiguous_declared_control_count": len(ambiguous_fields),
            "rejected_literal_count": sum(
                form.get("rejected_literal_count", 0) for form in forms
            ),
            "runtime_visibility_or_effective_text_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "source_assembly_sha256": assembly_hashes,
        "forms": forms,
        "ambiguous_declared_controls": ambiguous_fields,
        "validation_errors": errors,
        "limits": [
            "The evidence is a static InitializeComponent assignment candidate, not a runtime screenshot or visibility proof.",
            "Only allowlisted UI text setters with inline string operands are persisted; resource-backed captions remain unresolved.",
            "Form-or-unresolved targets are not attributed to a field and ambiguous field assignments must not be chosen silently.",
            "Labels do not prove binding, requiredness, authorization, validation order or write semantics.",
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
