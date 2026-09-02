"""Resolve 34 configured routes against all TypeDefs in the active package."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile

from extract_varanegar_data_entry_il_contracts import _method_summary
from extract_varanegar_targeted_il_contracts import _analyze_assembly, _full_type_name


CLASSIFICATION = "CONFIGURED_LEAF_PRESENT_PACKAGE_TYPE_UNMATCHED"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _value(record: dict[str, Any] | None) -> str | None:
    if not record:
        return None
    value = record.get("value")
    return value if isinstance(value, str) and value.upper() != "NULL" else None


def _base(type_row: Any) -> str:
    row = getattr(getattr(type_row, "Extends", None), "row", None)
    return "" if row is None else _full_type_name(row)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--scope-freeze", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = _load(args.binary_inventory)
    scope = _load(args.scope_freeze)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    files = sorted(expected)

    type_defs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    simple_defs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_hash_mismatches = []
    metadata_failures = []
    total_type_count = 0
    for name in files:
        path = args.source_directory / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            source_hash_mismatches.append(name)
        try:
            pe = dnfile.dnPE(str(path))
            table = getattr(pe.net.mdtables, "TypeDef", None)
            rows = [] if not table else table.rows
            for type_row in rows:
                full = _full_type_name(type_row)
                if full == "<Module>":
                    continue
                total_type_count += 1
                record = {"type": full, "assembly": name, "base_type": _base(type_row)}
                type_defs[full.casefold()].append(record)
                simple_defs[full.rsplit(".", 1)[-1].casefold()].append(record)
        except Exception as exc:
            metadata_failures.append({"file": name, "error_class": type(exc).__name__})

    candidates = [
        row for row in scope["candidates"] if row["classification"] == CLASSIFICATION
    ]
    preliminary = []
    targets_by_assembly: dict[str, set[str]] = defaultdict(set)
    for candidate in candidates:
        class_name = _value(candidate["class_name"])
        file_hint = _value(candidate["file_name"])
        matches: dict[str, dict[str, Any]] = {}
        signals: list[dict[str, str]] = []

        def add(strategy: str, lookup: str | None, index: dict[str, list[dict[str, Any]]]) -> None:
            if not lookup:
                return
            for record in index.get(lookup.casefold(), []):
                matches[record["type"]] = record
                signals.append({"strategy": strategy, "lookup": lookup, "matched_type": record["type"], "assembly": record["assembly"]})

        add("exact_file_hint_as_type", file_hint, type_defs)
        if file_hint and "." in file_hint and class_name:
            add("file_namespace_plus_class", file_hint.rsplit(".", 1)[0] + "." + class_name, type_defs)
        add("class_name_as_full_type", class_name, type_defs)
        add("unique_or_ambiguous_simple_class", class_name, simple_defs)
        matched = sorted(matches.values(), key=lambda row: (row["assembly"], row["type"]))
        if len(matched) == 1:
            status = "RESOLVED_UNIQUE_TYPEDEF"
        elif len(matched) > 1:
            status = "AMBIGUOUS_CONFLICTING_ROUTE_METADATA"
        else:
            status = "UNRESOLVED_IN_PRESENT_PACKAGE_TYPEDEFS"
        for row in matched:
            targets_by_assembly[row["assembly"]].add(row["type"])
        preliminary.append(
            {
                "menu_id": candidate["menu_id"],
                "priority": candidate["priority"],
                "root_menu_id": candidate["root_menu_id"],
                "root_section_module_hints_not_final_ownership": candidate["root_section_module_hints_not_final_ownership"],
                "class_name": candidate["class_name"],
                "file_name": candidate["file_name"],
                "resolution_status": status,
                "resolution_signals": signals,
                "matched_types": matched,
            }
        )

    il_assemblies = [
        _analyze_assembly(args.source_directory / name, targets)
        for name, targets in sorted(targets_by_assembly.items())
    ]
    target_contracts = {
        target["type"]: {
            "found": target["found"],
            "assembly": assembly["file"],
            "contract": _method_summary(target),
        }
        for assembly in il_assemblies
        for target in assembly["target_types"]
    }
    errors = [
        {"file": assembly["file"], **row}
        for assembly in il_assemblies
        for row in assembly["method_body_errors"]
    ]
    results = []
    for row in preliminary:
        results.append(
            {
                **row,
                "matched_type_contracts": [target_contracts[item["type"]] for item in row["matched_types"]],
                "scope_disposition": "REVIEW_REQUIRED_NEVER_AUTO_IMPLEMENTED_OR_RETIRED",
            }
        )

    status_counts: defaultdict[str, int] = defaultdict(int)
    for row in results:
        status_counts[row["resolution_status"]] += 1
    errors_for_validation = []
    if len(results) != 34:
        errors_for_validation.append("present-package candidate count changed")
    if source_hash_mismatches:
        errors_for_validation.append("source hash mismatch")
    if metadata_failures:
        errors_for_validation.append("metadata failure")
    if errors:
        errors_for_validation.append("target method body parse error")
    if any(not contract["found"] for contract in target_contracts.values()):
        errors_for_validation.append("resolved target not found in targeted IL pass")

    artifact = {
        "artifact": "varanegar_present_package_unmatched_route_typedef_and_il_resolution",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors_for_validation else "FAIL",
        "safety": {
            "mode": "READ_ONLY_COMPLETE_PACKAGE_TYPEDEF_AND_TARGETED_IL_RESOLUTION",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "config_or_resource_payloads_read": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "candidate_count": len(results),
            "package_file_count": len(files),
            "package_typedef_count": total_type_count,
            "resolution_status_counts": dict(sorted(status_counts.items())),
            "distinct_matched_type_count": len(target_contracts),
            "target_assembly_count": len(targets_by_assembly),
            "target_method_body_count": sum(item["contract"]["method_body_count"] for item in target_contracts.values()),
            "target_with_write_like_method_count": sum(bool(item["contract"]["write_like_methods"]) for item in target_contracts.values()),
            "target_with_permission_method_count": sum(bool(item["contract"]["permission_methods"]) for item in target_contracts.values()),
            "target_method_body_error_count": len(errors),
            "source_hash_mismatch_count": len(source_hash_mismatches),
            "metadata_failure_count": len(metadata_failures),
            "auto_implemented_or_retired_count": 0,
            "validation_error_count": len(errors_for_validation),
        },
        "source_hash_mismatches": source_hash_mismatches,
        "metadata_failures": metadata_failures,
        "target_method_body_errors": errors,
        "routes": results,
        "limits": [
            "A resolved TypeDef proves package presence, not current usage, permission, or target scope.",
            "Conflicting class/file hints remain ambiguous and require owner or runtime evidence.",
            "Write-like and permission-like method names are heuristics, not executed side effects or effective rights.",
        ],
        "validation_errors": errors_for_validation,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors_for_validation else 1


if __name__ == "__main__":
    raise SystemExit(main())
