"""Trace report UI surfaces into first-party Business and DataAccess types."""

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
from extract_varanegar_extension_dependency_graph import _layer, _member
from extract_varanegar_priority_gap_call_graph import _type_from_call
from extract_varanegar_targeted_il_contracts import _analyze_assembly, _full_type_name


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    report_types = {row["type"] for row in reports["surfaces"]}
    form_by_type = {row["type"]: row for row in forms["forms"]}

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

    ui_edges: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    unresolved_call_types = set()
    missing_report_contracts = sorted(report_types - set(form_by_type))
    for report_type in sorted(report_types):
        form = form_by_type.get(report_type)
        if not form:
            continue
        for call in form["contract"]["external_contract_calls"]:
            target_name = _type_from_call(call)
            definitions = type_index.get(target_name.casefold(), [])
            if not definitions:
                if target_name.startswith(("VN.", "TreasuryOld.", "Application.", "VNMembers")):
                    unresolved_call_types.add(target_name)
                continue
            for definition in definitions:
                key = (report_type, definition["type"], definition["assembly"], _member(call, target_name))
                ui_edges[key] = {
                    "source_report_type": report_type,
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

    report_rows = []
    for report in reports["surfaces"]:
        report_type = report["type"]
        edges = [edge for edge in ui_edges.values() if edge["source_report_type"] == report_type]
        direct_data = [edge for edge in edges if edge["target_layer"] == "data_access"]
        business = [edge for edge in edges if edge["target_layer"] in {"business_contract", "business_implementation"}]
        business_types = {edge["target_type"] for edge in business}
        downstream = [edge for edge in business_to_data_edges.values() if edge["source_business_type"] in business_types]
        report_rows.append(
            {
                "report_type": report_type,
                "classification": report["classification"],
                "primary_domain_id": report["primary_domain_id"],
                "first_party_edge_count": len(edges),
                "ui_to_business_edge_count": len(business),
                "ui_to_business_types": sorted(business_types),
                "direct_ui_to_data_access_edge_count": len(direct_data),
                "direct_ui_to_data_access_types": sorted({edge["target_type"] for edge in direct_data}),
                "business_to_data_access_edge_count": len(downstream),
                "business_to_data_access_types": sorted({edge["target_data_access_type"] for edge in downstream}),
                "static_query_path_status": (
                    "BUSINESS_TO_DATA_ACCESS_PATH_FOUND"
                    if downstream
                    else "DIRECT_UI_TO_DATA_ACCESS_PATH_FOUND"
                    if direct_data
                    else "NO_DATA_ACCESS_PATH_IN_ONE_HOP_BUSINESS_TRACE"
                ),
                "runtime_execution_or_result_parity_proven": False,
            }
        )

    errors = []
    if missing_report_contracts:
        errors.append("missing report form contracts")
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
        "artifact": "varanegar_report_ui_business_dataaccess_static_dependency_graph",
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
            "report_surface_count": len(report_rows),
            "first_party_ui_edge_count": len(ui_edges),
            "ui_to_business_edge_count": sum(edge["target_layer"] in {"business_contract", "business_implementation"} for edge in ui_edges.values()),
            "business_target_type_count": len(business_contracts),
            "business_target_method_body_count": sum(row["contract"]["method_body_count"] for row in business_contracts.values()),
            "direct_ui_to_data_access_edge_count": sum(edge["target_layer"] == "data_access" for edge in ui_edges.values()),
            "business_to_data_access_edge_count": len(business_to_data_edges),
            "data_access_target_type_count": len(data_contracts),
            "data_access_target_method_body_count": sum(row["contract"]["method_body_count"] for row in data_contracts.values()),
            "report_with_business_to_data_access_path_count": sum(row["static_query_path_status"] == "BUSINESS_TO_DATA_ACCESS_PATH_FOUND" for row in report_rows),
            "report_with_direct_ui_to_data_access_path_count": sum(row["static_query_path_status"] == "DIRECT_UI_TO_DATA_ACCESS_PATH_FOUND" for row in report_rows),
            "report_with_any_direct_ui_to_data_access_coupling_count": sum(bool(row["direct_ui_to_data_access_edge_count"]) for row in report_rows),
            "report_without_one_hop_data_access_path_count": sum(row["static_query_path_status"] == "NO_DATA_ACCESS_PATH_IN_ONE_HOP_BUSINESS_TRACE" for row in report_rows),
            "unresolved_first_party_like_call_type_count": len(unresolved_call_types),
            "targeted_method_body_error_count": len(assembly_errors),
            "source_hash_mismatch_count": len(source_hash_mismatches),
            "metadata_failure_count": len(metadata_failures),
            "runtime_execution_or_result_parity_proven_count": 0,
            "validation_error_count": len(errors),
        },
        "reports": report_rows,
        "ui_first_party_edges": sorted(ui_edges.values(), key=lambda row: (row["source_report_type"], row["target_layer"], row["target_type"], row["called_member"])),
        "business_to_data_access_edges": sorted(business_to_data_edges.values(), key=lambda row: (row["source_business_type"], row["target_data_access_type"], row["called_member"])),
        "business_contracts": [{"type": name, **record} for name, record in sorted(business_contracts.items())],
        "data_access_contracts": [{"type": name, **record} for name, record in sorted(data_contracts.items())],
        "unresolved_first_party_like_call_types": sorted(unresolved_call_types),
        "targeted_method_body_errors": assembly_errors,
        "source_hash_mismatches": source_hash_mismatches,
        "metadata_failures": metadata_failures,
        "validation_errors": errors,
        "limits": [
            "Static edges do not prove a runtime branch, query result, calculation parity, filter semantics or effective authorization.",
            "Interface dispatch, inherited base forms and report engines can hide deeper query implementations.",
            "Direct UI-to-DataAccess coupling is a legacy dependency signal and must not be copied into target web UI.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
