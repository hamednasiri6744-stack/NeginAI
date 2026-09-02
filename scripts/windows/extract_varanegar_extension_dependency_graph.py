"""Trace extension UI capabilities into first-party Business and DataAccess."""

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
from extract_varanegar_priority_gap_call_graph import _type_from_call
from extract_varanegar_targeted_il_contracts import _analyze_assembly, _full_type_name


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _layer(type_name: str, assembly: str, inventory_layer: str) -> str:
    lowered = type_name.casefold()
    if ".datalayer." in lowered or ".dataaccess." in lowered or inventory_layer == "DataAccess":
        return "data_access"
    if ".ibusiness." in lowered or inventory_layer == "IBusiness":
        return "business_contract"
    if ".business." in lowered or inventory_layer == "Business" or type_name.startswith("Application.BusinessLayer."):
        return "business_implementation"
    if inventory_layer in {"UI", "UIComponent", "Forms"}:
        return "ui_or_ui_component"
    return "shared_or_framework"


def _member(call: str, type_name: str) -> str:
    prefix = type_name + "."
    return call[len(prefix):] if call.startswith(prefix) else call.rsplit(".", 1)[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--resolved-routes", required=True, type=Path)
    parser.add_argument("--capabilities", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = _load(args.binary_inventory)
    resolved = _load(args.resolved_routes)
    capability_map = _load(args.capabilities)
    inventory_by_file = {row["name"]: row for row in inventory["files"]}

    type_index: dict[str, list[dict[str, str]]] = defaultdict(list)
    metadata_failures = []
    source_hash_mismatches = []
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
                        "inventory_layer": source["layer"],
                        "layer": _layer(type_name, source["name"], source["layer"]),
                    }
                )
        except Exception as exc:
            metadata_failures.append({"file": source["name"], "error_class": type(exc).__name__})

    ui_contract_by_type = {
        matched["type"]: contract["contract"]
        for route in resolved["routes"]
        for matched, contract in zip(route["matched_types"], route["matched_type_contracts"])
    }
    capability_by_type = {row["type"]: row["capability_hint"] for row in capability_map["capabilities"]}

    ui_edges: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    unresolved_call_types = set()
    for ui_type, contract in ui_contract_by_type.items():
        for call in contract["external_contract_calls"]:
            target_name = _type_from_call(call)
            definitions = type_index.get(target_name.casefold(), [])
            if not definitions:
                if target_name.startswith(("VN.", "TreasuryOld.", "Application.", "VNMembers")):
                    unresolved_call_types.add(target_name)
                continue
            for definition in definitions:
                key = (ui_type, definition["type"], definition["assembly"], _member(call, target_name))
                ui_edges[key] = {
                    "source_capability": capability_by_type[ui_type],
                    "source_ui_type": ui_type,
                    "target_type": definition["type"],
                    "target_assembly": definition["assembly"],
                    "target_layer": definition["layer"],
                    "called_member": _member(call, target_name),
                }

    business_targets: dict[str, set[str]] = defaultdict(set)
    direct_data_targets: dict[str, set[str]] = defaultdict(set)
    for edge in ui_edges.values():
        if edge["target_layer"] in {"business_contract", "business_implementation"}:
            business_targets[edge["target_assembly"]].add(edge["target_type"])
        elif edge["target_layer"] == "data_access":
            direct_data_targets[edge["target_assembly"]].add(edge["target_type"])

    business_assemblies = [
        _analyze_assembly(args.source_directory / assembly, targets)
        for assembly, targets in sorted(business_targets.items())
    ]
    business_contracts = {
        target["type"]: {"assembly": assembly["file"], "found": target["found"], "contract": _method_summary(target)}
        for assembly in business_assemblies
        for target in assembly["target_types"]
    }

    business_to_data_edges: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    data_targets = defaultdict(set, {name: set(values) for name, values in direct_data_targets.items()})
    for source_type, record in business_contracts.items():
        for call in record["contract"]["external_contract_calls"]:
            target_name = _type_from_call(call)
            for definition in type_index.get(target_name.casefold(), []):
                if definition["layer"] != "data_access":
                    continue
                key = (source_type, definition["type"], definition["assembly"], _member(call, target_name))
                business_to_data_edges[key] = {
                    "source_business_type": source_type,
                    "source_assembly": record["assembly"],
                    "target_data_access_type": definition["type"],
                    "target_assembly": definition["assembly"],
                    "called_member": _member(call, target_name),
                }
                data_targets[definition["assembly"]].add(definition["type"])

    data_assemblies = [
        _analyze_assembly(args.source_directory / assembly, targets)
        for assembly, targets in sorted(data_targets.items())
    ]
    data_contracts = {
        target["type"]: {"assembly": assembly["file"], "found": target["found"], "contract": _method_summary(target)}
        for assembly in data_assemblies
        for target in assembly["target_types"]
    }
    assembly_errors = [
        {"file": assembly["file"], **error}
        for assembly in business_assemblies + data_assemblies
        for error in assembly["method_body_errors"]
    ]

    per_capability = []
    for capability in capability_map["capabilities"]:
        ui_type = capability["type"]
        edges = [edge for edge in ui_edges.values() if edge["source_ui_type"] == ui_type]
        direct_da = [edge for edge in edges if edge["target_layer"] == "data_access"]
        business = [edge for edge in edges if edge["target_layer"] in {"business_contract", "business_implementation"}]
        business_types = {edge["target_type"] for edge in business}
        downstream = [edge for edge in business_to_data_edges.values() if edge["source_business_type"] in business_types]
        per_capability.append(
            {
                "capability_hint": capability["capability_hint"],
                "ui_type": ui_type,
                "first_party_edge_count": len(edges),
                "ui_to_business_edge_count": len(business),
                "ui_to_business_type_count": len(business_types),
                "direct_ui_to_data_access_edge_count": len(direct_da),
                "direct_ui_to_data_access_type_count": len({edge["target_type"] for edge in direct_da}),
                "business_to_data_access_edge_count": len(downstream),
                "business_to_data_access_type_count": len({edge["target_data_access_type"] for edge in downstream}),
                "has_direct_ui_data_access_coupling": bool(direct_da),
                "has_business_mediation_evidence": bool(business),
            }
        )

    errors = []
    if set(ui_contract_by_type) != set(capability_by_type):
        errors.append("capability/type coverage mismatch")
    if source_hash_mismatches:
        errors.append("source hash mismatch")
    if metadata_failures:
        errors.append("metadata failure")
    if assembly_errors:
        errors.append("targeted method body parse error")
    if any(not row["found"] for row in business_contracts.values()):
        errors.append("missing business target")
    if any(not row["found"] for row in data_contracts.values()):
        errors.append("missing data-access target")

    artifact = {
        "artifact": "varanegar_extension_ui_business_dataaccess_dependency_graph",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_COMPLETE_PACKAGE_METADATA_AND_TARGETED_IL_DEPENDENCY_TRACE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "config_or_resource_payloads_read": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "capability_count": len(per_capability),
            "first_party_ui_edge_count": len(ui_edges),
            "ui_to_business_edge_count": sum(edge["target_layer"] in {"business_contract", "business_implementation"} for edge in ui_edges.values()),
            "business_target_type_count": len(business_contracts),
            "business_target_method_body_count": sum(row["contract"]["method_body_count"] for row in business_contracts.values()),
            "direct_ui_to_data_access_edge_count": sum(edge["target_layer"] == "data_access" for edge in ui_edges.values()),
            "capability_with_direct_ui_data_access_count": sum(row["has_direct_ui_data_access_coupling"] for row in per_capability),
            "business_to_data_access_edge_count": len(business_to_data_edges),
            "data_access_target_type_count": len(data_contracts),
            "data_access_target_method_body_count": sum(row["contract"]["method_body_count"] for row in data_contracts.values()),
            "capability_with_business_mediation_count": sum(row["has_business_mediation_evidence"] for row in per_capability),
            "unresolved_first_party_like_call_type_count": len(unresolved_call_types),
            "targeted_method_body_error_count": len(assembly_errors),
            "source_hash_mismatch_count": len(source_hash_mismatches),
            "metadata_failure_count": len(metadata_failures),
            "validation_error_count": len(errors),
        },
        "capabilities": per_capability,
        "ui_first_party_edges": sorted(ui_edges.values(), key=lambda row: (row["source_capability"], row["target_layer"], row["target_type"], row["called_member"])),
        "business_to_data_access_edges": sorted(business_to_data_edges.values(), key=lambda row: (row["source_business_type"], row["target_data_access_type"], row["called_member"])),
        "business_contracts": [{"type": name, **record} for name, record in sorted(business_contracts.items())],
        "data_access_contracts": [{"type": name, **record} for name, record in sorted(data_contracts.items())],
        "unresolved_first_party_like_call_types": sorted(unresolved_call_types),
        "targeted_method_body_errors": assembly_errors,
        "source_hash_mismatches": source_hash_mismatches,
        "metadata_failures": metadata_failures,
        "limits": [
            "Static call edges do not prove runtime branch execution, transaction atomicity, or effective authorization.",
            "Interface dispatch and dependency injection can hide concrete business implementations.",
            "Direct UI-to-DataAccess coupling is a legacy dependency signal and must not be copied into the target web UI.",
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
