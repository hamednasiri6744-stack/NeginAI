"""Trace discovered report-shell caller types through Business into DataAccess."""

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

from extract_varanegar_extension_dependency_graph import _layer, _member
from extract_varanegar_priority_gap_call_graph import _type_from_call
from extract_varanegar_targeted_il_contracts import _analyze_assembly, _full_type_name


EXECUTION_SUFFIXES = (".ExecuteNonQuery", ".ExecuteScalar", ".ExecuteReader", ".Fill", ".Query", ".GetValue")
MUTATION_SUFFIXES = (".ExecuteNonQuery", ".Update", ".Commit")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _type_index(source_directory: Path, files: list[dict[str, Any]]) -> tuple[dict[str, dict[str, str]], list[str], list[str]]:
    index: dict[str, dict[str, str]] = {}
    hash_mismatches: list[str] = []
    metadata_failures: list[str] = []
    for source in files:
        path = source_directory / source["name"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            hash_mismatches.append(source["name"])
        try:
            pe = dnfile.dnPE(str(path))
            table = getattr(pe.net.mdtables, "TypeDef", None)
            for row in ([] if not table else table.rows):
                name = _full_type_name(row)
                if name != "<Module>":
                    index[name.casefold()] = {"type": name, "assembly": source["name"]}
        except Exception:
            metadata_failures.append(source["name"])
    return index, hash_mismatches, metadata_failures


def _analyze_types(source_directory: Path, index: dict[str, dict[str, str]], names: set[str]) -> tuple[list[dict[str, Any]], list[str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    unresolved: list[str] = []
    for name in names:
        found = index.get(name.casefold())
        if found:
            grouped[found["assembly"]].add(found["type"])
        else:
            unresolved.append(name)
    return [
        _analyze_assembly(source_directory / assembly, targets)
        for assembly, targets in sorted(grouped.items())
    ], sorted(unresolved)


def _records(assemblies: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        target["type"]: {"assembly": assembly["file"], **target}
        for assembly in assemblies
        for target in assembly["target_types"]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--entrypoints", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    inventory = _load(args.binary_inventory)
    entrypoints = _load(args.entrypoints)
    index, hash_mismatches, metadata_failures = _type_index(args.source_directory, inventory["files"])
    shell_callers: dict[str, set[str]] = {}
    for resolution in entrypoints["resolutions"]:
        shell_callers[resolution["target_type"]] = {
            row["caller_type"] for row in resolution["external_token_references"]
        }
    caller_names = set().union(*shell_callers.values()) if shell_callers else set()
    caller_assemblies, unresolved_callers = _analyze_types(args.source_directory, index, caller_names)
    caller_records = _records(caller_assemblies)

    caller_edges: list[dict[str, str]] = []
    called_business_members: dict[str, set[str]] = defaultdict(set)
    direct_data_members: dict[str, set[str]] = defaultdict(set)
    for caller_type, record in caller_records.items():
        for method in record["methods"]:
            for call in method["calls"]:
                target_type = _type_from_call(call)
                raw_layer = _layer(target_type, "", "")
                layer = "business" if raw_layer in {"business_implementation", "business_contract"} else raw_layer
                if layer not in {"business", "data_access"}:
                    continue
                target_member = _member(call, target_type)
                caller_edges.append({
                    "caller_type": caller_type,
                    "caller_method": method["method"],
                    "target_type": target_type,
                    "target_member": target_member,
                    "target_layer": layer,
                })
                if layer == "business":
                    called_business_members[target_type].add(target_member)
                else:
                    direct_data_members[target_type].add(target_member)

    business_assemblies, unresolved_business_types = _analyze_types(args.source_directory, index, set(called_business_members))
    business_records = _records(business_assemblies)
    business_edges: list[dict[str, str]] = []
    business_data_members: dict[str, set[str]] = defaultdict(set)
    unresolved_business_methods: list[str] = []
    for business_type, members in called_business_members.items():
        record = business_records.get(business_type)
        if not record:
            continue
        for member in members:
            matches = [method for method in record["methods"] if method["method"] == member]
            if not matches:
                unresolved_business_methods.append(f"{business_type}.{member}")
            for method in matches:
                for call in method["calls"]:
                    target_type = _type_from_call(call)
                    if _layer(target_type, "", "") != "data_access":
                        continue
                    target_member = _member(call, target_type)
                    business_edges.append({
                        "source_business_type": business_type,
                        "source_business_method": member,
                        "target_data_access_type": target_type,
                        "target_data_access_member": target_member,
                    })
                    business_data_members[target_type].add(target_member)

    all_data_members: dict[str, set[str]] = defaultdict(set)
    for source in (direct_data_members, business_data_members):
        for type_name, members in source.items():
            all_data_members[type_name].update(members)
    data_assemblies, unresolved_data_types = _analyze_types(args.source_directory, index, set(all_data_members))
    data_records = _records(data_assemblies)
    terminal_methods: list[dict[str, Any]] = []
    unresolved_data_methods: list[str] = []
    for data_type, members in all_data_members.items():
        record = data_records.get(data_type)
        if not record:
            continue
        for member in members:
            matches = [method for method in record["methods"] if method["method"] == member]
            if not matches:
                unresolved_data_methods.append(f"{data_type}.{member}")
            for method in matches:
                terminal_methods.append({
                    "data_access_type": data_type,
                    "assembly": record["assembly"],
                    "method": member,
                    "instruction_count": method["instruction_count"],
                    "execution_calls": sorted(call for call in method["calls"] if call.endswith(EXECUTION_SUFFIXES)),
                    "mutation_calls": sorted(call for call in method["calls"] if call.endswith(MUTATION_SUFFIXES)),
                    "raw_non_allowlisted_literals_persisted": 0,
                })

    reports = []
    for shell, callers in sorted(shell_callers.items()):
        scoped_caller_edges = [row for row in caller_edges if row["caller_type"] in callers]
        scoped_business = {row["target_type"] for row in scoped_caller_edges if row["target_layer"] == "business"}
        scoped_direct_data = {row["target_type"] for row in scoped_caller_edges if row["target_layer"] == "data_access"}
        scoped_business_edges = [row for row in business_edges if row["source_business_type"] in scoped_business]
        scoped_data = scoped_direct_data | {row["target_data_access_type"] for row in scoped_business_edges}
        scoped_terminal = [row for row in terminal_methods if row["data_access_type"] in scoped_data]
        reports.append({
            "report_shell_type": shell,
            "caller_types": sorted(callers),
            "caller_to_business_or_data_edge_count": len(scoped_caller_edges),
            "business_to_data_edge_count": len(scoped_business_edges),
            "terminal_data_access_method_count": len(scoped_terminal),
            "terminal_execution_signal_count": sum(bool(row["execution_calls"]) for row in scoped_terminal),
            "terminal_mutation_signal_count": sum(bool(row["mutation_calls"]) for row in scoped_terminal),
            "path_status": "CALLER_TO_DATA_ACCESS_PATH_FOUND" if scoped_terminal else "CALLER_FOUND_BUT_NO_DATA_ACCESS_PATH_IN_SCOPED_TRACE" if callers else "NO_CALLER_FOUND",
        })

    method_errors = [
        {"file": assembly["file"], **row}
        for group in (caller_assemblies, business_assemblies, data_assemblies)
        for assembly in group
        for row in assembly["method_body_errors"]
    ]
    errors: list[str] = []
    if entrypoints.get("validation") != "PASS":
        errors.append("entrypoint input is not PASS")
    if hash_mismatches:
        errors.append("source package hash mismatch")
    if metadata_failures:
        errors.append("metadata failures")
    if unresolved_callers or unresolved_business_types or unresolved_data_types:
        errors.append("one or more first-party target types could not be resolved")
    if method_errors:
        errors.append("targeted method body errors")
    artifact = {
        "artifact": "varanegar_report_shell_caller_to_dataaccess_scoped_paths",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_COMPLETE_PACKAGE_TARGETED_CALLER_BUSINESS_DATAACCESS_IL_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_or_reports_executed": 0,
            "config_or_resource_payloads_read": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "report_shell_count": len(reports),
            "discovered_caller_type_count": len(caller_names),
            "caller_to_business_or_data_edge_count": len(caller_edges),
            "called_business_type_count": len(called_business_members),
            "scoped_business_to_data_edge_count": len(business_edges),
            "called_data_access_type_count": len(all_data_members),
            "terminal_data_access_method_count": len(terminal_methods),
            "terminal_method_with_execution_signal_count": sum(bool(row["execution_calls"]) for row in terminal_methods),
            "terminal_method_with_mutation_signal_count": sum(bool(row["mutation_calls"]) for row in terminal_methods),
            "report_shell_with_data_access_path_count": sum(row["path_status"] == "CALLER_TO_DATA_ACCESS_PATH_FOUND" for row in reports),
            "unresolved_caller_type_count": len(unresolved_callers),
            "unresolved_business_type_count": len(unresolved_business_types),
            "unresolved_business_method_count": len(set(unresolved_business_methods)),
            "unresolved_data_access_type_count": len(unresolved_data_types),
            "unresolved_data_access_method_count": len(set(unresolved_data_methods)),
            "targeted_method_body_error_count": len(method_errors),
            "source_hash_mismatch_count": len(hash_mismatches),
            "metadata_failure_count": len(metadata_failures),
            "runtime_execution_or_result_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "reports": reports,
        "caller_edges": sorted(caller_edges, key=lambda row: (row["caller_type"], row["caller_method"], row["target_type"], row["target_member"])),
        "scoped_business_to_data_edges": sorted(business_edges, key=lambda row: (row["source_business_type"], row["source_business_method"], row["target_data_access_type"], row["target_data_access_member"])),
        "terminal_data_access_methods": sorted(terminal_methods, key=lambda row: (row["data_access_type"], row["method"])),
        "unresolved_caller_types": unresolved_callers,
        "unresolved_business_types": unresolved_business_types,
        "unresolved_business_methods": sorted(set(unresolved_business_methods)),
        "unresolved_data_access_types": unresolved_data_types,
        "unresolved_data_access_methods": sorted(set(unresolved_data_methods)),
        "targeted_method_body_errors": method_errors,
        "source_hash_mismatches": hash_mismatches,
        "metadata_failures": metadata_failures,
        "validation_errors": errors,
        "limits": [
            "All methods on a discovered caller type are scanned; a path may belong to another caller branch.",
            "Name-based overload matching can include multiple bodies.",
            "Static reachability and execution-call signals do not prove runtime execution or result parity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
