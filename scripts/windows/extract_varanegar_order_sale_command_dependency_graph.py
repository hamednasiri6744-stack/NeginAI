"""Trace selected order-to-sale UI methods into Business and DataAccess IL."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_targeted_il_contracts import _analyze_assembly


FIRST_PARTY = re.compile(r"^VN\.SDS\.(MainData|Sales|Stock|Treasury)\.(Business|DataAccess)\.")
TRANSACTION = re.compile(
    r"(?:DataContext\.(?:Commit|Rollback)|Transaction\.(?:Start|Commit|RollBack)|BeginTransaction|\.Commit|\.Rollback)$",
    re.IGNORECASE,
)
PERSISTENCE = re.compile(
    r"(?:ExecuteNonQuery|\.Insert|\.Update|\.Delete|\.Save|\.PreUpdate|DataContext\.Commit)$",
    re.IGNORECASE,
)
SQL_ANCHOR = re.compile(r"^(?:dbo|SLE|GNR|INV|Acc)\.[A-Za-z_][A-Za-z0-9_]*$", re.IGNORECASE)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _type_member(call: str) -> tuple[str, str]:
    if call.endswith("..ctor"):
        return call[:-6], ".ctor"
    return call.rsplit(".", 1) if "." in call else (call, "")


def _assembly(type_name: str, layer: str) -> str:
    match = re.match(r"^VN\.SDS\.(MainData|Sales|Stock|Treasury)\.", type_name)
    if not match:
        raise ValueError(f"unsupported first-party type: {type_name}")
    return f"VN.SDS.{match.group(1)}.{layer}.dll"


def _analyze_targets(
    source_directory: Path,
    expected_hashes: dict[str, str],
    targets: dict[str, set[str]],
) -> tuple[dict[str, dict[str, Any]], list[str], list[dict[str, Any]], dict[str, str]]:
    by_assembly: dict[str, set[str]] = defaultdict(set)
    for type_name in targets:
        layer = "Business" if ".Business." in type_name else "DataAccess"
        by_assembly[_assembly(type_name, layer)].add(type_name)
    index: dict[str, dict[str, Any]] = {}
    mismatches: list[str] = []
    body_errors: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    for assembly_name, type_names in sorted(by_assembly.items()):
        path = source_directory / assembly_name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[assembly_name] = actual
        if actual != expected_hashes.get(assembly_name):
            mismatches.append(assembly_name)
        analyzed = _analyze_assembly(path, type_names)
        body_errors.extend(analyzed["method_body_errors"])
        for row in analyzed["target_types"]:
            index[row["type"]] = {"assembly": assembly_name, **row}
    return index, mismatches, body_errors, hashes


def _selected_methods(
    index: dict[str, dict[str, Any]], requested: dict[str, set[str]]
) -> tuple[list[dict[str, Any]], list[str]]:
    selected: list[dict[str, Any]] = []
    missing: list[str] = []
    for type_name, members in sorted(requested.items()):
        row = index.get(type_name)
        if row is None or not row.get("found"):
            missing.append(f"type:{type_name}")
            continue
        by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for method in row["methods"]:
            by_name[method["method"]].append(method)
        for member in sorted(members):
            matches = by_name.get(member, [])
            if not matches:
                missing.append(f"member:{type_name}.{member}")
            for method in matches:
                selected.append(
                    {
                        "assembly": row["assembly"],
                        "type": type_name,
                        **method,
                    }
                )
    return selected, missing


def _safe_anchors(method: dict[str, Any]) -> list[str]:
    return sorted(
        {
            row["safe_literal"]
            for row in method["string_literals"]
            if row.get("persisted_as") == "allowlisted_business_literal"
            and SQL_ANCHOR.fullmatch(row.get("safe_literal", ""))
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--command-contracts", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--business-depth", type=int, default=2)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    contracts = _load(args.command_contracts)
    inventory = _load(args.binary_inventory)
    expected_hashes = {row["name"]: row["sha256"] for row in inventory["files"]}
    errors: list[str] = []
    root_edges: list[dict[str, Any]] = []
    frontier: dict[str, set[str]] = defaultdict(set)
    for contract in contracts["contracts"]:
        for method in contract["methods"]:
            for call in method["first_party_business_calls"]:
                type_name, member = _type_member(call)
                frontier[type_name].add(member)
                root_edges.append(
                    {
                        "from_form": contract["form_type"],
                        "from_method": method["method"],
                        "to_business_type": type_name,
                        "called_member": member,
                    }
                )

    business_nodes: list[dict[str, Any]] = []
    business_edges: list[dict[str, Any]] = []
    data_requested: dict[str, set[str]] = defaultdict(set)
    processed: dict[str, set[str]] = defaultdict(set)
    all_mismatches: list[str] = []
    all_body_errors: list[dict[str, Any]] = []
    assembly_hashes: dict[str, str] = {}
    missing_members: list[str] = []
    for depth in range(1, args.business_depth + 1):
        requested = {
            type_name: members - processed[type_name]
            for type_name, members in frontier.items()
            if members - processed[type_name]
        }
        if not requested:
            break
        index, mismatches, body_errors, hashes = _analyze_targets(
            args.source_directory, expected_hashes, requested
        )
        all_mismatches.extend(mismatches)
        all_body_errors.extend(body_errors)
        assembly_hashes.update(hashes)
        selected, missing = _selected_methods(index, requested)
        missing_members.extend(missing)
        next_frontier: dict[str, set[str]] = defaultdict(set)
        for type_name, members in requested.items():
            processed[type_name].update(members)
        for method in selected:
            transaction_calls = sorted(
                call for call in method["calls"] if TRANSACTION.search(call)
            )
            persistence_calls = sorted(
                call for call in method["calls"] if PERSISTENCE.search(call)
            )
            anchors = _safe_anchors(method)
            business_nodes.append(
                {
                    "depth": depth,
                    "assembly": method["assembly"],
                    "type": method["type"],
                    "method": method["method"],
                    "instruction_count": method["instruction_count"],
                    "transaction_signal_calls": transaction_calls,
                    "persistence_signal_calls": persistence_calls,
                    "safe_sql_object_anchors": anchors,
                    "runtime_branch_order_values_and_effects_proven": False,
                }
            )
            for call in method["calls"]:
                if not FIRST_PARTY.match(call):
                    continue
                target_type, member = _type_member(call)
                edge = {
                    "from_type": method["type"],
                    "from_method": method["method"],
                    "to_type": target_type,
                    "called_member": member,
                    "from_depth": depth,
                }
                if ".Business." in target_type:
                    edge["target_layer"] = "Business"
                    next_frontier[target_type].add(member)
                elif ".DataAccess." in target_type:
                    edge["target_layer"] = "DataAccess"
                    data_requested[target_type].add(member)
                else:
                    continue
                business_edges.append(edge)
        frontier = next_frontier

    data_index, mismatches, body_errors, hashes = _analyze_targets(
        args.source_directory, expected_hashes, data_requested
    ) if data_requested else ({}, [], [], {})
    all_mismatches.extend(mismatches)
    all_body_errors.extend(body_errors)
    assembly_hashes.update(hashes)
    data_methods, missing = _selected_methods(data_index, data_requested)
    missing_members.extend(missing)
    data_nodes = []
    for method in data_methods:
        data_nodes.append(
            {
                "assembly": method["assembly"],
                "type": method["type"],
                "method": method["method"],
                "instruction_count": method["instruction_count"],
                "transaction_signal_calls": sorted(
                    call for call in method["calls"] if TRANSACTION.search(call)
                ),
                "persistence_signal_calls": sorted(
                    call for call in method["calls"] if PERSISTENCE.search(call)
                ),
                "safe_sql_object_anchors": _safe_anchors(method),
                "runtime_sql_execution_result_or_effect_proven": False,
            }
        )

    root_edges = [dict(row) for row in {tuple(sorted(row.items())): row for row in root_edges}.values()]
    business_edges = [dict(row) for row in {tuple(sorted(row.items())): row for row in business_edges}.values()]
    errors.extend(f"source hash mismatch: {name}" for name in sorted(set(all_mismatches)))
    errors.extend(f"method body error: {row}" for row in all_body_errors)
    errors.extend(f"unresolved selected member: {row}" for row in sorted(set(missing_members)))
    if contracts.get("validation") != "PASS":
        errors.append("source command contracts are not PASS")
    all_anchors = sorted(
        {
            anchor
            for row in business_nodes + data_nodes
            for anchor in row["safe_sql_object_anchors"]
        }
    )
    artifact = {
        "artifact": "varanegar_order_sale_return_bounded_business_dataaccess_dependency_graph",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_HASH_VERIFIED_PE_METADATA_AND_TARGETED_IL_GRAPH",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_or_business_commands_executed": 0,
            "raw_non_allowlisted_literals_or_business_values_persisted": 0,
            "runtime_branch_order_values_sql_results_or_effects_inferred": 0,
        },
        "summary": {
            "root_form_count": len({row["from_form"] for row in root_edges}),
            "root_form_method_to_business_edge_count": len(root_edges),
            "business_depth_limit": args.business_depth,
            "selected_business_method_node_count": len(business_nodes),
            "business_dependency_edge_count": len(business_edges),
            "selected_data_access_method_node_count": len(data_nodes),
            "business_method_with_transaction_signal_count": sum(
                bool(row["transaction_signal_calls"]) for row in business_nodes
            ),
            "business_method_with_persistence_signal_count": sum(
                bool(row["persistence_signal_calls"]) for row in business_nodes
            ),
            "data_access_method_with_transaction_signal_count": sum(
                bool(row["transaction_signal_calls"]) for row in data_nodes
            ),
            "data_access_method_with_persistence_signal_count": sum(
                bool(row["persistence_signal_calls"]) for row in data_nodes
            ),
            "safe_sql_object_anchor_count": len(all_anchors),
            "source_hash_mismatch_count": len(set(all_mismatches)),
            "method_body_error_count": len(all_body_errors),
            "unresolved_selected_member_count": len(set(missing_members)),
            "runtime_execution_result_or_effect_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "source_assembly_sha256": assembly_hashes,
        "root_edges": sorted(root_edges, key=lambda row: (row["from_form"], row["from_method"], row["to_business_type"], row["called_member"])),
        "business_method_nodes": sorted(business_nodes, key=lambda row: (row["depth"], row["type"], row["method"])),
        "business_dependency_edges": sorted(business_edges, key=lambda row: (row["from_type"], row["from_method"], row["to_type"], row["called_member"])),
        "data_access_method_nodes": sorted(data_nodes, key=lambda row: (row["type"], row["method"])),
        "safe_sql_object_anchors": all_anchors,
        "unresolved_selected_members": sorted(set(missing_members)),
        "validation_errors": errors,
        "limits": [
            "The Business graph is bounded to two selected member-call layers; reflection, events, interfaces, ORM conventions and deeper calls may be absent.",
            "A transaction or persistence signal in one method does not prove end-to-end atomicity or every runtime branch.",
            "Safe SQL object anchors are structural string evidence, not proof of execution, parameter values, row results, trigger effects or recent use.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
