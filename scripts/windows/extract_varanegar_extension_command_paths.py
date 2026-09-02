"""Trace twelve material extension capabilities at method level without execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_data_entry_il_contracts import (
    DESTRUCTIVE_OR_REVERSING_METHOD,
    PERMISSION_METHOD,
    VALIDATION_METHOD,
    WRITE_METHOD,
)
from extract_varanegar_priority_gap_call_graph import _type_from_call
from extract_varanegar_targeted_il_contracts import _analyze_assembly


SELECTED_CAPABILITIES = {
    "pos.charge_device": "external/device and value-changing surface",
    "pos.instalment_method": "instalment rule and collection boundary",
    "pos.linear_discount": "pricing rule mutation and validation",
    "pos.safe": "POS treasury context",
    "pos.session": "POS session and settlement context",
    "pos.subscriber": "customer/subscriber master mutation",
    "configuration.accounting_article_template": "posting template mutation",
    "configuration.general": "material effective rule configuration",
    "authorization.stock_accounting_access": "permission/configuration coupling",
    "configuration.web_service": "integration and secret boundary",
    "tablet.dealer_day_path": "route planning mutation",
    "tablet.visit_template": "visit planning template mutation",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _member(call: str, type_name: str) -> str:
    prefix = type_name + "."
    return call[len(prefix):] if call.startswith(prefix) else call.rsplit(".", 1)[-1]


def _method_role(method_name: str, called_members: list[str]) -> str:
    joined = " ".join([method_name, *called_members])
    if DESTRUCTIVE_OR_REVERSING_METHOD.search(joined):
        return "destructive_or_reversing_command_candidate"
    if WRITE_METHOD.search(joined):
        return "write_command_candidate"
    if PERMISSION_METHOD.search(joined):
        return "permission_guard_candidate"
    if VALIDATION_METHOD.search(joined):
        return "validation_guard_candidate"
    return "query_event_or_context_path"


def _transaction_signals(calls: list[str]) -> list[str]:
    signals = []
    for call in calls:
        lowered = call.casefold()
        if any(term in lowered for term in (
            "transaction.start", "transaction.begin", "transaction.commit",
            "transaction.rollback", "transaction.rollBack".casefold(),
            "sqltransaction.commit", "sqltransaction.rollback",
        )):
            signals.append(call)
    return sorted(set(signals))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--resolved-routes", required=True, type=Path)
    parser.add_argument("--capabilities", required=True, type=Path)
    parser.add_argument("--dependencies", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = _load(args.binary_inventory)
    resolved = _load(args.resolved_routes)
    capabilities = _load(args.capabilities)
    dependencies = _load(args.dependencies)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}

    cap_rows = {row["capability_hint"]: row for row in capabilities["capabilities"]}
    selected_rows = [cap_rows[name] for name in sorted(SELECTED_CAPABILITIES)]
    type_to_assembly = {
        matched["type"]: matched["assembly"]
        for route in resolved["routes"]
        for matched in route["matched_types"]
    }
    ui_targets: dict[str, set[str]] = defaultdict(set)
    for row in selected_rows:
        ui_targets[type_to_assembly[row["type"]]].add(row["type"])
    ui_assemblies = [
        _analyze_assembly(args.source_directory / assembly, targets)
        for assembly, targets in sorted(ui_targets.items())
    ]
    ui_raw = {
        target["type"]: target
        for assembly in ui_assemblies
        for target in assembly["target_types"]
    }
    dep_ui_edges = dependencies["ui_first_party_edges"]
    ui_paths = []
    reachable_business_types = set()
    for cap in selected_rows:
        ui_type = cap["type"]
        relevant_dep_edges = [edge for edge in dep_ui_edges if edge["source_ui_type"] == ui_type]
        dep_index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for edge in relevant_dep_edges:
            dep_index[(edge["target_type"].casefold(), edge["called_member"])].append(edge)
        method_paths = []
        for method in ui_raw[ui_type]["methods"]:
            edges = []
            for call in method["calls"]:
                target_type = _type_from_call(call)
                member = _member(call, target_type)
                edges.extend(dep_index.get((target_type.casefold(), member), []))
            unique_edges = {
                (edge["target_type"], edge["target_assembly"], edge["target_layer"], edge["called_member"]): edge
                for edge in edges
            }
            edges = sorted(unique_edges.values(), key=lambda row: (row["target_layer"], row["target_type"], row["called_member"]))
            if not edges:
                continue
            business = [edge for edge in edges if edge["target_layer"] in {"business_contract", "business_implementation"}]
            reachable_business_types.update(edge["target_type"] for edge in business)
            called_members = [edge["called_member"] for edge in edges]
            method_paths.append(
                {
                    "ui_method": method["method"],
                    "role": _method_role(method["method"], called_members),
                    "first_party_edge_count": len(edges),
                    "business_edge_count": len(business),
                    "direct_data_access_edge_count": sum(edge["target_layer"] == "data_access" for edge in edges),
                    "transaction_signals": _transaction_signals(method["calls"]),
                    "edges": edges,
                }
            )
        ui_paths.append(
            {
                "capability_hint": cap["capability_hint"],
                "selection_reason": SELECTED_CAPABILITIES[cap["capability_hint"]],
                "ui_type": ui_type,
                "ui_assembly": type_to_assembly[ui_type],
                "method_body_count": len(ui_raw[ui_type]["methods"]),
                "path_method_count": len(method_paths),
                "method_role_counts": dict(sorted(defaultdict(int, {
                    role: sum(row["role"] == role for row in method_paths)
                    for role in sorted({row["role"] for row in method_paths})
                }).items())),
                "methods": method_paths,
            }
        )

    business_meta = {row["type"]: row for row in dependencies["business_contracts"]}
    business_targets: dict[str, set[str]] = defaultdict(set)
    for type_name in reachable_business_types:
        business_targets[business_meta[type_name]["assembly"]].add(type_name)
    business_assemblies = [
        _analyze_assembly(args.source_directory / assembly, targets)
        for assembly, targets in sorted(business_targets.items())
    ]
    business_raw = {
        target["type"]: target
        for assembly in business_assemblies
        for target in assembly["target_types"]
    }
    data_edge_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in dependencies["business_to_data_access_edges"]:
        data_edge_index[edge["source_business_type"]].append(edge)

    called_business_members: dict[str, set[str]] = defaultdict(set)
    for cap in ui_paths:
        for method in cap["methods"]:
            for edge in method["edges"]:
                if edge["target_layer"] in {"business_contract", "business_implementation"}:
                    called_business_members[edge["target_type"]].add(edge["called_member"])

    business_paths = []
    for type_name in sorted(reachable_business_types):
        target = business_raw[type_name]
        wanted = called_business_members[type_name]
        data_edges = data_edge_index[type_name]
        target_paths = []
        for method in target["methods"]:
            if method["method"] not in wanted:
                continue
            resolved_edges = []
            for call in method["calls"]:
                call_type = _type_from_call(call)
                member = _member(call, call_type)
                resolved_edges.extend(
                    edge for edge in data_edges
                    if edge["target_data_access_type"].casefold() == call_type.casefold()
                    and edge["called_member"] == member
                )
            unique = {
                (edge["target_data_access_type"], edge["target_assembly"], edge["called_member"]): edge
                for edge in resolved_edges
            }
            target_paths.append(
                {
                    "business_method": method["method"],
                    "called_from_ui": True,
                    "data_access_edges": sorted(unique.values(), key=lambda row: (row["target_data_access_type"], row["called_member"])),
                    "transaction_signals": _transaction_signals(method["calls"]),
                }
            )
        business_paths.append(
            {
                "business_type": type_name,
                "assembly": business_meta[type_name]["assembly"],
                "called_member_count": len(wanted),
                "resolved_method_body_count": len(target_paths),
                "interface_or_unresolved_body_count": len(wanted) - len(target_paths),
                "methods": target_paths,
            }
        )

    all_assemblies = ui_assemblies + business_assemblies
    method_errors = [
        {"file": assembly["file"], **error}
        for assembly in all_assemblies
        for error in assembly["method_body_errors"]
    ]
    source_hash_mismatches = [
        assembly["file"] for assembly in all_assemblies
        if assembly["sha256"] != expected[assembly["file"]]
    ]
    errors = []
    if set(cap["capability_hint"] for cap in selected_rows) != set(SELECTED_CAPABILITIES):
        errors.append("selected capability coverage mismatch")
    if any(not target["found"] for target in ui_raw.values()):
        errors.append("missing UI target")
    if any(not target["found"] for target in business_raw.values()):
        errors.append("missing business target")
    if method_errors:
        errors.append("targeted method body error")
    if source_hash_mismatches:
        errors.append("source hash mismatch")

    ui_method_rows = [method for cap in ui_paths for method in cap["methods"]]
    business_method_rows = [method for target in business_paths for method in target["methods"]]
    unique_ui_business_edges = {
        (edge["source_capability"], edge["target_type"], edge["called_member"])
        for row in ui_method_rows for edge in row["edges"]
        if edge["target_layer"] in {"business_contract", "business_implementation"}
    }
    unique_ui_data_edges = {
        (edge["source_capability"], edge["target_type"], edge["called_member"])
        for row in ui_method_rows for edge in row["edges"]
        if edge["target_layer"] == "data_access"
    }
    unique_business_data_edges = {
        (edge["source_business_type"], edge["target_data_access_type"], edge["called_member"])
        for row in business_method_rows for edge in row["data_access_edges"]
    }
    artifact = {
        "artifact": "varanegar_material_extension_method_command_guard_dependency_paths",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_TARGETED_METHOD_LEVEL_IL_PATH_TRACE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "config_or_resource_payloads_read": 0,
            "string_literals_persisted": 0,
        },
        "summary": {
            "selected_capability_count": len(ui_paths),
            "selected_ui_type_count": len(ui_raw),
            "selected_ui_method_body_count": sum(cap["method_body_count"] for cap in ui_paths),
            "ui_path_method_count": len(ui_method_rows),
            "ui_command_candidate_method_count": sum("command_candidate" in row["role"] for row in ui_method_rows),
            "ui_guard_candidate_method_count": sum("guard_candidate" in row["role"] for row in ui_method_rows),
            "ui_query_event_context_method_count": sum(row["role"] == "query_event_or_context_path" for row in ui_method_rows),
            "ui_path_business_edge_occurrence_count": sum(row["business_edge_count"] for row in ui_method_rows),
            "ui_path_unique_business_edge_count": len(unique_ui_business_edges),
            "ui_path_direct_data_access_edge_occurrence_count": sum(row["direct_data_access_edge_count"] for row in ui_method_rows),
            "ui_path_unique_direct_data_access_edge_count": len(unique_ui_data_edges),
            "reachable_business_type_count": len(business_paths),
            "called_business_member_count": sum(row["called_member_count"] for row in business_paths),
            "resolved_business_method_body_count": len(business_method_rows),
            "interface_or_unresolved_business_body_count": sum(row["interface_or_unresolved_body_count"] for row in business_paths),
            "business_method_data_access_edge_occurrence_count": sum(len(row["data_access_edges"]) for row in business_method_rows),
            "business_method_unique_data_access_edge_count": len(unique_business_data_edges),
            "ui_transaction_signal_count": sum(len(row["transaction_signals"]) for row in ui_method_rows),
            "business_transaction_signal_count": sum(len(row["transaction_signals"]) for row in business_method_rows),
            "targeted_method_body_error_count": len(method_errors),
            "source_hash_mismatch_count": len(source_hash_mismatches),
            "validation_error_count": len(errors),
        },
        "capability_paths": ui_paths,
        "business_paths": business_paths,
        "targeted_method_body_errors": method_errors,
        "source_hash_mismatches": source_hash_mismatches,
        "limits": [
            "Method roles are name-and-call heuristics and do not prove an executed command or side effect.",
            "Interface methods without bodies are retained as unresolved implementation paths.",
            "Absence of a transaction signal in selected methods does not prove absence of a transaction deeper in the stack.",
        ],
        "validation_errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
