"""Build an offline static control/field dictionary for high-impact data-entry forms."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


CONTROL_PREFIXES = {
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
}


def _kind(field_name: str) -> str | None:
    lowered = field_name.casefold()
    for kind, prefixes in CONTROL_PREFIXES.items():
        if lowered.startswith(prefixes):
            return kind
    return None


def _signals(method_name: str) -> list[str]:
    lowered = method_name.casefold()
    signals = []
    if any(token in lowered for token in ("valid", "leave", "check")):
        signals.append("validation_or_guard")
    if any(token in lowered for token in ("save", "insert", "update", "create", "delete", "remove", "btnok", "buttonok")):
        signals.append("write_or_submit")
    if any(token in lowered for token in ("reload", "lookup", "selector", "buttonclick", "button_click")):
        signals.append("selector_or_lookup")
    if any(token in lowered for token in ("permission", "allow", "access", "authorize")):
        signals.append("permission")
    if any(token in lowered for token in ("load", "init")):
        signals.append("initialization")
    return signals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.data_entry_il.read_text(encoding="utf-8-sig"))
    catalog_by_type = {row["type"]: row for row in source["forms"]}
    forms = []
    all_fields: list[dict[str, Any]] = []
    for assembly in source["raw_il"]:
        for target in assembly["target_types"]:
            form_type = target["type"]
            catalog = catalog_by_type[form_type]
            field_usage: dict[str, dict[str, Any]] = {}
            safe_ui_labels: set[str] = set()
            for method in target["methods"]:
                method_signals = _signals(method["method"])
                for literal in method["string_literals"]:
                    if literal["persisted_as"] == "allowlisted_ui_literal" and "safe_ui_literal" in literal:
                        safe_ui_labels.add(literal["safe_ui_literal"])
                for reference in method["referenced_fields"]:
                    prefix = form_type + "."
                    if not reference.startswith(prefix):
                        continue
                    field_name = reference[len(prefix):]
                    kind = _kind(field_name)
                    if kind is None or "<" in field_name or ">" in field_name:
                        continue
                    record = field_usage.setdefault(field_name, {
                        "field_name": field_name,
                        "inferred_control_kind": kind,
                        "referencing_methods": set(),
                        "usage_signals": set(),
                        "required_or_nullable_semantics": "UNPROVEN",
                        "data_binding_or_source_column": "UNPROVEN",
                    })
                    record["referencing_methods"].add(method["method"])
                    record["usage_signals"].update(method_signals)
            field_rows = []
            for record in field_usage.values():
                row = {
                    **record,
                    "referencing_methods": sorted(record["referencing_methods"]),
                    "usage_signals": sorted(record["usage_signals"]),
                }
                field_rows.append(row)
                all_fields.append({"form_type": form_type, **row})
            fields_by_kind = Counter(row["inferred_control_kind"] for row in field_rows)
            forms.append({
                "assembly": assembly["file"],
                "form_type": form_type,
                "page_shape": catalog["page_shape"],
                "primary_domain_id": catalog["primary_domain_id"],
                "review_priority": catalog["review_priority"],
                "field_candidate_count": len(field_rows),
                "field_kind_counts": dict(sorted(fields_by_kind.items())),
                "safe_unpaired_ui_labels": sorted(safe_ui_labels),
                "safe_unpaired_ui_label_count": len(safe_ui_labels),
                "fields": sorted(field_rows, key=lambda row: row["field_name"].casefold()),
                "label_to_field_pairing_status": "NOT_INFERRED_FROM_LITERAL_ORDER",
            })

    errors = []
    if source.get("summary", {}).get("selected_form_count") != len(forms):
        errors.append("selected form count differs from data-entry IL source")
    if any(row["label_to_field_pairing_status"] != "NOT_INFERRED_FROM_LITERAL_ORDER" for row in forms):
        errors.append("unsafe label-field pairing inferred")
    kind_counts = Counter(row["inferred_control_kind"] for row in all_fields)
    signal_counts = Counter(signal for row in all_fields for signal in row["usage_signals"])
    artifact = {
        "artifact": "varanegar_data_entry_static_control_field_dictionary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "OFFLINE_DERIVATION_FROM_REDACTED_TARGETED_IL",
            "database_connections": 0,
            "network_reads_or_writes": 0,
            "live_ui_actions": 0,
            "assemblies_loaded_or_executed": 0,
            "application_commands_executed": 0,
            "raw_non_allowlisted_strings_persisted": 0,
            "label_to_field_pairings_inferred": 0,
        },
        "summary": {
            "selected_data_entry_form_count": len(forms),
            "form_with_field_candidate_count": sum(row["field_candidate_count"] > 0 for row in forms),
            "form_without_field_candidate_count": sum(row["field_candidate_count"] == 0 for row in forms),
            "field_candidate_count": len(all_fields),
            "unique_field_name_count": len({row["field_name"] for row in all_fields}),
            "field_kind_counts": dict(sorted(kind_counts.items())),
            "field_usage_signal_counts": dict(sorted(signal_counts.items())),
            "safe_unpaired_ui_label_count": sum(row["safe_unpaired_ui_label_count"] for row in forms),
            "form_with_safe_ui_label_count": sum(row["safe_unpaired_ui_label_count"] > 0 for row in forms),
            "proven_required_or_nullable_field_count": 0,
            "proven_data_binding_field_count": 0,
            "validation_error_count": len(errors),
        },
        "forms": sorted(forms, key=lambda row: row["form_type"]),
        "validation_errors": errors,
        "limits": [
            "Control kind is inferred from field-name prefixes and is not runtime type proof.",
            "UI labels are persisted only when already allowlisted and are not paired to controls by literal order.",
            "Required/nullability, source-column binding, visibility and effective enabled state remain unproven.",
            "Coverage is the 141 selected data-entry/master-detail forms, not every one of the 445 candidates.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
