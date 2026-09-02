"""Trace report methods through called Business methods into DataAccess methods."""

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

from extract_varanegar_extension_dependency_graph import _layer, _member
from extract_varanegar_priority_gap_call_graph import _type_from_call
from extract_varanegar_targeted_il_contracts import _analyze_assembly, _full_type_name


EXECUTION_CALL_SUFFIXES = (
    ".ExecuteNonQuery",
    ".ExecuteScalar",
    ".ExecuteReader",
    ".Fill",
    ".Query",
    ".GetValue",
)
MUTATION_CALL_SUFFIXES = (".ExecuteNonQuery", ".Update", ".Commit")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _methods_by_type(assemblies: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        target["type"]: {"assembly": assembly["file"], "methods": target["methods"], "found": target["found"]}
        for assembly in assemblies
        for target in assembly["target_types"]
    }


def _matching_methods(record: dict[str, Any], member: str) -> list[dict[str, Any]]:
    return [method for method in record["methods"] if method["method"] == member]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--all-form-contracts", required=True, type=Path)
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = _load(args.binary_inventory)
    forms = _load(args.all_form_contracts)
    reports = _load(args.reports)
    form_by_type = {row["type"]: row for row in forms["forms"]}

    type_index: dict[str, list[dict[str, str]]] = defaultdict(list)
    source_hash_mismatches = []
    metadata_failures = []
    for source in inventory["files"]:
        path = args.source_directory / source["name"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            source_hash_mismatches.append(source["name"])
        try:
            pe = dnfile.dnPE(str(path))
            table = getattr(pe.net.mdtables, "TypeDef", None)
            for row in ([] if not table else table.rows):
                type_name = _full_type_name(row)
                if type_name == "<Module>":
                    continue
                type_index[type_name.casefold()].append(
                    {
                        "type": type_name,
                        "assembly": source["name"],
                        "layer": _layer(type_name, source["name"], source["layer"]),
                    }
                )
        except Exception as exc:
            metadata_failures.append({"file": source["name"], "error_class": type(exc).__name__})

    ui_targets: dict[str, set[str]] = defaultdict(set)
    report_type_by_ui = {}
    missing_report_forms = []
    for report in reports["surfaces"]:
        form = form_by_type.get(report["type"])
        if not form:
            missing_report_forms.append(report["type"])
            continue
        ui_targets[form["assembly"]].add(report["type"])
        report_type_by_ui[report["type"]] = report
    ui_assemblies = [
        _analyze_assembly(args.source_directory / assembly, targets)
        for assembly, targets in sorted(ui_targets.items())
    ]
    ui_records = _methods_by_type(ui_assemblies)

    ui_edges = []
    business_targets: dict[str, set[str]] = defaultdict(set)
    data_targets: dict[str, set[str]] = defaultdict(set)
    for ui_type, record in ui_records.items():
        for method in record["methods"]:
            for call in method["calls"]:
                target_name = _type_from_call(call)
                for definition in type_index.get(target_name.casefold(), []):
                    if definition["layer"] not in {"business_contract", "business_implementation", "data_access"}:
                        continue
                    edge = {
                        "report_type": ui_type,
                        "source_ui_method": method["method"],
                        "target_type": definition["type"],
                        "target_assembly": definition["assembly"],
                        "target_layer": definition["layer"],
                        "target_member": _member(call, target_name),
                    }
                    ui_edges.append(edge)
                    if definition["layer"] in {"business_contract", "business_implementation"}:
                        business_targets[definition["assembly"]].add(definition["type"])
                    else:
                        data_targets[definition["assembly"]].add(definition["type"])

    business_assemblies = [
        _analyze_assembly(args.source_directory / assembly, targets)
        for assembly, targets in sorted(business_targets.items())
    ]
    business_records = _methods_by_type(business_assemblies)
    business_edges = []
    unresolved_called_business_methods = []
    for ui_edge in [edge for edge in ui_edges if edge["target_layer"] in {"business_contract", "business_implementation"}]:
        record = business_records.get(ui_edge["target_type"])
        methods = [] if not record else _matching_methods(record, ui_edge["target_member"])
        if not methods:
            unresolved_called_business_methods.append({key: ui_edge[key] for key in ("report_type", "source_ui_method", "target_type", "target_member")})
            continue
        for method in methods:
            for call in method["calls"]:
                target_name = _type_from_call(call)
                for definition in type_index.get(target_name.casefold(), []):
                    if definition["layer"] != "data_access":
                        continue
                    edge = {
                        "report_type": ui_edge["report_type"],
                        "source_ui_method": ui_edge["source_ui_method"],
                        "source_business_type": ui_edge["target_type"],
                        "source_business_method": method["method"],
                        "target_data_access_type": definition["type"],
                        "target_assembly": definition["assembly"],
                        "target_data_access_member": _member(call, target_name),
                    }
                    business_edges.append(edge)
                    data_targets[definition["assembly"]].add(definition["type"])

    data_assemblies = [
        _analyze_assembly(args.source_directory / assembly, targets)
        for assembly, targets in sorted(data_targets.items())
    ]
    data_records = _methods_by_type(data_assemblies)
    terminal_methods: dict[tuple[str, str], dict[str, Any]] = {}
    unresolved_called_data_methods = []
    scoped_data_calls = [
        {
            "report_type": edge["report_type"],
            "source_path": f"{edge['report_type']}.{edge['source_ui_method']}",
            "target_type": edge["target_type"],
            "target_member": edge["target_member"],
            "path_kind": "DIRECT_UI_TO_DATA_ACCESS",
        }
        for edge in ui_edges
        if edge["target_layer"] == "data_access"
    ] + [
        {
            "report_type": edge["report_type"],
            "source_path": f"{edge['source_business_type']}.{edge['source_business_method']}",
            "target_type": edge["target_data_access_type"],
            "target_member": edge["target_data_access_member"],
            "path_kind": "UI_TO_BUSINESS_TO_DATA_ACCESS",
        }
        for edge in business_edges
    ]
    terminal_edges = []
    for call in scoped_data_calls:
        record = data_records.get(call["target_type"])
        methods = [] if not record else _matching_methods(record, call["target_member"])
        if not methods:
            unresolved_called_data_methods.append(call)
            continue
        for method in methods:
            execution_calls = sorted({target for target in method["calls"] if target.endswith(EXECUTION_CALL_SUFFIXES)})
            mutation_calls = sorted({target for target in method["calls"] if target.endswith(MUTATION_CALL_SUFFIXES)})
            safe_literals = [
                literal["safe_literal"]
                for literal in method["string_literals"]
                if literal.get("persisted_as") in {"allowlisted_business_literal", "allowlisted_ui_literal"}
                and literal.get("safe_literal")
            ]
            fingerprints = [
                {"sha256": literal["sha256"], "length": literal["length"]}
                for literal in method["string_literals"]
                if literal.get("persisted_as") == "fingerprint_only"
            ]
            key = (call["target_type"], method["method"])
            terminal_methods[key] = {
                "data_access_type": call["target_type"],
                "assembly": record["assembly"],
                "method": method["method"],
                "instruction_count": method["instruction_count"],
                "execution_calls": execution_calls,
                "mutation_calls": mutation_calls,
                "safe_static_literals": sorted(set(safe_literals)),
                "fingerprint_only_literals": fingerprints,
                "raw_non_allowlisted_literals_persisted": 0,
            }
            terminal_edges.append({**call, "terminal_method_key": f"{call['target_type']}.{method['method']}"})

    report_rows = []
    for report_type in sorted(report_type_by_ui):
        report_ui_edges = [edge for edge in ui_edges if edge["report_type"] == report_type]
        report_business_edges = [edge for edge in business_edges if edge["report_type"] == report_type]
        report_terminal_edges = [edge for edge in terminal_edges if edge["report_type"] == report_type]
        terminal_keys = {(edge["target_type"], edge["target_member"]) for edge in report_terminal_edges}
        terminals = [terminal_methods[key] for key in sorted(terminal_keys)]
        report_rows.append(
            {
                "report_type": report_type,
                "ui_method_to_business_or_data_edge_count": len(report_ui_edges),
                "scoped_business_method_to_data_edge_count": len(report_business_edges),
                "terminal_data_access_method_count": len(terminals),
                "terminal_method_with_execution_signal_count": sum(bool(row["execution_calls"]) for row in terminals),
                "terminal_method_with_mutation_signal_count": sum(bool(row["mutation_calls"]) for row in terminals),
                "direct_ui_to_data_access_terminal_count": sum(edge["path_kind"] == "DIRECT_UI_TO_DATA_ACCESS" for edge in report_terminal_edges),
                "terminal_methods": [f"{row['data_access_type']}.{row['method']}" for row in terminals],
                "runtime_execution_or_result_parity_proven": False,
            }
        )

    assembly_errors = [
        {"file": assembly["file"], **error}
        for assembly in ui_assemblies + business_assemblies + data_assemblies
        for error in assembly["method_body_errors"]
    ]
    errors = []
    if missing_report_forms:
        errors.append("missing report form contracts")
    if source_hash_mismatches:
        errors.append("source hash mismatch")
    if metadata_failures:
        errors.append("metadata failure")
    if assembly_errors:
        errors.append("targeted method body parse error")

    terminal_values = list(terminal_methods.values())
    artifact = {
        "artifact": "varanegar_report_scoped_ui_business_dataaccess_method_paths",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_COMPLETE_PACKAGE_TARGETED_METHOD_BODY_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_or_reports_executed": 0,
            "config_or_resource_payloads_read": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "report_surface_count": len(report_rows),
            "ui_type_count": len(ui_records),
            "ui_method_to_business_or_data_edge_count": len(ui_edges),
            "called_business_type_count": len(business_records),
            "scoped_business_method_to_data_edge_count": len(business_edges),
            "called_data_access_type_count": len(data_records),
            "terminal_data_access_method_count": len(terminal_values),
            "terminal_method_with_execution_signal_count": sum(bool(row["execution_calls"]) for row in terminal_values),
            "terminal_method_with_mutation_signal_count": sum(bool(row["mutation_calls"]) for row in terminal_values),
            "direct_ui_to_data_access_terminal_edge_count": sum(edge["path_kind"] == "DIRECT_UI_TO_DATA_ACCESS" for edge in terminal_edges),
            "safe_static_literal_count": sum(len(row["safe_static_literals"]) for row in terminal_values),
            "fingerprint_only_literal_count": sum(len(row["fingerprint_only_literals"]) for row in terminal_values),
            "unresolved_called_business_method_count": len(unresolved_called_business_methods),
            "unresolved_called_data_method_count": len(unresolved_called_data_methods),
            "targeted_method_body_error_count": len(assembly_errors),
            "source_hash_mismatch_count": len(source_hash_mismatches),
            "metadata_failure_count": len(metadata_failures),
            "runtime_execution_or_result_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "reports": report_rows,
        "ui_method_edges": sorted(ui_edges, key=lambda row: (row["report_type"], row["source_ui_method"], row["target_type"], row["target_member"])),
        "scoped_business_to_data_edges": sorted(business_edges, key=lambda row: (row["report_type"], row["source_business_type"], row["source_business_method"], row["target_data_access_type"], row["target_data_access_member"])),
        "terminal_edges": sorted(terminal_edges, key=lambda row: (row["report_type"], row["path_kind"], row["target_type"], row["target_member"])),
        "terminal_data_access_methods": sorted(terminal_values, key=lambda row: (row["data_access_type"], row["method"])),
        "unresolved_called_business_methods": unresolved_called_business_methods,
        "unresolved_called_data_methods": unresolved_called_data_methods,
        "targeted_method_body_errors": assembly_errors,
        "source_hash_mismatches": source_hash_mismatches,
        "metadata_failures": metadata_failures,
        "validation_errors": errors,
        "limits": [
            "Name-based overload matching can include more than one method body with the same member name.",
            "Interface dispatch, inherited base methods, delegates and report engines can hide later calls.",
            "Execution-call signals in IL do not prove runtime execution, SQL identity, filter semantics or result parity.",
            "Mutation signals on Statement or print paths require separate target commands; report reads remain read-only.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

