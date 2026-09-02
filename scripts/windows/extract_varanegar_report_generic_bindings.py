"""Extract generic handler/entity-helper bindings for discovered report-shell callers."""

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

from extract_varanegar_priority_gap_call_graph import _type_from_call
from extract_varanegar_targeted_il_contracts import _analyze_assembly, _full_type_name


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _member(call: str, type_name: str) -> str:
    prefix = type_name + "."
    return call[len(prefix):] if call.startswith(prefix) else call.rsplit(".", 1)[-1]


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
    inventory_by_name = {row["name"]: row for row in inventory["files"]}
    type_index: dict[str, dict[str, str]] = {}
    metadata_failures: list[str] = []
    hash_mismatches: list[str] = []
    for source in inventory["files"]:
        path = args.source_directory / source["name"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            hash_mismatches.append(source["name"])
        try:
            pe = dnfile.dnPE(str(path))
            table = getattr(pe.net.mdtables, "TypeDef", None)
            for row in ([] if not table else table.rows):
                name = _full_type_name(row)
                if name != "<Module>":
                    type_index[name.casefold()] = {"type": name, "assembly": source["name"]}
        except Exception:
            metadata_failures.append(source["name"])

    shell_callers: dict[str, set[str]] = {}
    for resolution in entrypoints["resolutions"]:
        shell_callers[resolution["target_type"]] = {row["caller_type"] for row in resolution["external_token_references"]}
    caller_names = set().union(*shell_callers.values()) if shell_callers else set()
    grouped: dict[str, set[str]] = defaultdict(set)
    unresolved_callers: list[str] = []
    for caller in caller_names:
        found = type_index.get(caller.casefold())
        if found:
            grouped[found["assembly"]].add(found["type"])
        else:
            unresolved_callers.append(caller)
    assemblies = [_analyze_assembly(args.source_directory / assembly, targets) for assembly, targets in sorted(grouped.items())]
    records = {target["type"]: {"assembly": assembly["file"], **target} for assembly in assemblies for target in assembly["target_types"]}

    caller_contracts: list[dict[str, Any]] = []
    for caller in sorted(caller_names):
        record = records[caller]
        entity_helpers: set[str] = set()
        helper_filter_members: set[str] = set()
        business_handlers: set[str] = set()
        generic_calls: set[str] = set()
        method_bindings: list[dict[str, Any]] = []
        for method in record["methods"]:
            method_helpers: set[str] = set()
            method_filters: set[str] = set()
            method_handlers: set[str] = set()
            method_generic: set[str] = set()
            for call in method["calls"]:
                target_type = _type_from_call(call)
                member = _member(call, target_type)
                if ".EntityHelper." in target_type:
                    method_helpers.add(target_type)
                    if member.startswith("set_"):
                        method_filters.add(member[4:])
                if ".Business." in target_type and target_type.endswith(("Handler", "Validator")):
                    method_handlers.add(target_type)
                if target_type.startswith("TypeSpecRow") and member in {"GetAllView", "Create", "Start", "get_Task", "set_FetchReason"}:
                    method_generic.add(member)
            if method_helpers or method_handlers or method_generic:
                method_bindings.append({
                    "method": method["method"],
                    "entity_helper_types": sorted(method_helpers),
                    "filter_members": sorted(method_filters),
                    "business_handler_types": sorted(method_handlers),
                    "generic_dispatch_members": sorted(method_generic),
                })
            entity_helpers.update(method_helpers)
            helper_filter_members.update(method_filters)
            business_handlers.update(method_handlers)
            generic_calls.update(method_generic)
        caller_contracts.append({
            "caller_type": caller,
            "assembly": record["assembly"],
            "method_body_count": len(record["methods"]),
            "entity_helper_types": sorted(entity_helpers),
            "filter_members": sorted(helper_filter_members),
            "business_handler_types": sorted(business_handlers),
            "generic_dispatch_members": sorted(generic_calls),
            "method_bindings": method_bindings,
            "binding_status": "GENERIC_QUERY_BINDING_SIGNAL" if "GetAllView" in generic_calls else "NO_GET_ALL_VIEW_SIGNAL",
        })

    reports = []
    by_caller = {row["caller_type"]: row for row in caller_contracts}
    for shell, callers in sorted(shell_callers.items()):
        scoped = [by_caller[caller] for caller in sorted(callers)]
        reports.append({
            "report_shell_type": shell,
            "caller_type_count": len(scoped),
            "caller_types": [row["caller_type"] for row in scoped],
            "entity_helper_types": sorted({item for row in scoped for item in row["entity_helper_types"]}),
            "filter_members": sorted({item for row in scoped for item in row["filter_members"]}),
            "business_handler_types": sorted({item for row in scoped for item in row["business_handler_types"]}),
            "generic_dispatch_members": sorted({item for row in scoped for item in row["generic_dispatch_members"]}),
            "binding_status": "GENERIC_QUERY_BINDING_SIGNAL" if any(row["binding_status"] == "GENERIC_QUERY_BINDING_SIGNAL" for row in scoped) else "NO_GENERIC_QUERY_BINDING_SIGNAL",
        })

    method_errors = [{"file": assembly["file"], **row} for assembly in assemblies for row in assembly["method_body_errors"]]
    errors: list[str] = []
    if entrypoints.get("validation") != "PASS":
        errors.append("entrypoint input is not PASS")
    if hash_mismatches:
        errors.append("source package hash mismatch")
    if metadata_failures:
        errors.append("metadata failures")
    if unresolved_callers:
        errors.append("caller types unresolved")
    if method_errors:
        errors.append("targeted method body errors")
    artifact = {
        "artifact": "varanegar_report_shell_generic_handler_entityhelper_bindings",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_TARGETED_CALLER_IL_GENERIC_BINDING_EXTRACTION",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_or_reports_executed": 0,
            "config_or_resource_payloads_read": 0,
            "string_literals_persisted": 0,
        },
        "summary": {
            "report_shell_count": len(reports),
            "caller_type_count": len(caller_contracts),
            "caller_with_generic_query_binding_count": sum(row["binding_status"] == "GENERIC_QUERY_BINDING_SIGNAL" for row in caller_contracts),
            "unique_entity_helper_type_count": len({item for row in caller_contracts for item in row["entity_helper_types"]}),
            "unique_filter_member_count": len({item for row in caller_contracts for item in row["filter_members"]}),
            "unique_business_handler_type_count": len({item for row in caller_contracts for item in row["business_handler_types"]}),
            "report_shell_with_generic_query_binding_count": sum(row["binding_status"] == "GENERIC_QUERY_BINDING_SIGNAL" for row in reports),
            "targeted_method_body_error_count": len(method_errors),
            "unresolved_caller_type_count": len(unresolved_callers),
            "source_hash_mismatch_count": len(hash_mismatches),
            "metadata_failure_count": len(metadata_failures),
            "runtime_execution_sql_identity_or_result_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "reports": reports,
        "caller_contracts": caller_contracts,
        "targeted_method_body_errors": method_errors,
        "unresolved_caller_types": sorted(unresolved_callers),
        "source_hash_mismatches": hash_mismatches,
        "metadata_failures": metadata_failures,
        "validation_errors": errors,
        "limits": [
            "Generic TypeSpec tokens do not reveal the concrete runtime adapter or final SQL in this extraction.",
            "Setter names are filter-shape evidence, not proof that every field is used on every branch.",
            "No report, query, command, assembly or UI action was executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
