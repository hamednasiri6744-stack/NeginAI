"""Trace the seven priority form gaps through parent launchers and data-layer IL."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_data_entry_il_contracts import _method_summary
from extract_varanegar_targeted_il_contracts import _analyze_assembly


BASE_TARGETS = {
    "Application.BaseTemaplateV2.dll": {
        "Application.BaseTemaplateV2.UIBase.FormBaseSimpleDialog"
    }
}
TREASURY_DATA_TYPE = re.compile(r"^TreasuryOld\.DataLayer\.")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _type_from_call(call: str) -> str:
    if call.endswith("..ctor"):
        return call[:-6]
    return call.rsplit(".", 1)[0] if "." in call else call


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--all-form-calls", required=True, type=Path)
    parser.add_argument("--gap-catalog", required=True, type=Path)
    parser.add_argument("--static-routes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    binaries = _load(args.binary_inventory)
    all_forms = _load(args.all_form_calls)
    gaps = _load(args.gap_catalog)
    static_routes = _load(args.static_routes)
    expected_hashes = {row["name"]: row["sha256"] for row in binaries["files"]}
    high = [row for row in gaps["forms"] if row["priority"] == "high"]
    high_types = {row["type"] for row in high}
    forms_by_type = {row["type"]: row for row in all_forms["forms"]}

    parent_types = set()
    compact_launch_refs = []
    for form in all_forms["forms"]:
        for call in form["contract"]["first_party_external_calls"]:
            target_type = _type_from_call(call)
            if target_type in high_types:
                parent_types.add(form["type"])
                compact_launch_refs.append(
                    {"parent_form": form["type"], "target_form": target_type, "called_member": call.rsplit(".", 1)[-1]}
                )

    ui_targets: dict[str, set[str]] = {name: set(types) for name, types in BASE_TARGETS.items()}
    for type_name in sorted(high_types | parent_types):
        row = forms_by_type[type_name]
        ui_targets.setdefault(row["assembly"], set()).add(type_name)

    source_hash_mismatches = []
    ui_assemblies = []
    for assembly_name, targets in sorted(ui_targets.items()):
        path = args.source_directory / assembly_name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hashes.get(assembly_name):
            source_hash_mismatches.append(assembly_name)
        ui_assemblies.append(_analyze_assembly(path, targets))
    ui_type_index = {
        target["type"]: target
        for assembly in ui_assemblies
        for target in assembly["target_types"]
    }

    precise_reference_edges = []
    for parent_type in sorted(parent_types):
        target = ui_type_index[parent_type]
        for method in target["methods"]:
            for call in method["calls"]:
                target_type = _type_from_call(call)
                if target_type in high_types:
                    precise_reference_edges.append(
                        {"parent_form": parent_type, "parent_method": method["method"], "target_form": target_type, "called_member": call.rsplit(".", 1)[-1]}
                    )
    constructor_launcher_edges = [
        edge
        for edge in precise_reference_edges
        if edge["called_member"] == "ctor"
        and edge["parent_form"] != edge["target_form"]
    ]

    data_targets = set()
    high_contracts = []
    for row in high:
        target = ui_type_index[row["type"]]
        contract = _method_summary(target)
        for call in contract["external_contract_calls"]:
            type_name = _type_from_call(call)
            if TREASURY_DATA_TYPE.match(type_name):
                data_targets.add(type_name)
        high_contracts.append(
            {
                "type": row["type"],
                "base_type": forms_by_type[row["type"]]["base_type"],
                "page_shape": row["page_shape"],
                "gap_codes_before_trace": row["gap_codes"],
                "contract": contract,
            }
        )

    data_assemblies = []
    if data_targets:
        path = args.source_directory / "TreasuryOld.DataAccess.dll"
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hashes.get(path.name):
            source_hash_mismatches.append(path.name)
        data_assemblies.append(_analyze_assembly(path, data_targets))
    primary_data_targets = {
        target["type"]: target
        for assembly in data_assemblies
        for target in assembly["target_types"]
    }
    # The vendor package contains at least one legacy helper whose namespace says
    # DataLayer but whose TypeDef is embedded in TreasuryOld.Forms.dll. Resolve
    # such namespace/assembly mismatches explicitly instead of reporting a false
    # missing type.
    unresolved_data_targets = {
        type_name
        for type_name, target in primary_data_targets.items()
        if not target["found"]
    }
    fallback_data_assemblies = []
    if unresolved_data_targets:
        path = args.source_directory / "TreasuryOld.Forms.dll"
        fallback_data_assemblies.append(_analyze_assembly(path, unresolved_data_targets))
    fallback_data_targets = {
        target["type"]: target
        for assembly in fallback_data_assemblies
        for target in assembly["target_types"]
    }
    data_contracts = []
    for type_name in sorted(data_targets):
        primary = primary_data_targets[type_name]
        fallback = fallback_data_targets.get(type_name)
        selected = fallback if fallback and fallback["found"] else primary
        source_assembly = (
            "TreasuryOld.Forms.dll"
            if fallback and fallback["found"]
            else "TreasuryOld.DataAccess.dll"
        )
        data_contracts.append(
            {
                "type": type_name,
                "found": selected["found"],
                "definition_assembly": source_assembly if selected["found"] else None,
                "namespace_assembly_mismatch": bool(
                    selected["found"] and source_assembly == "TreasuryOld.Forms.dll"
                ),
                "contract": _method_summary(selected),
            }
        )
    errors = [
        error
        for assembly in ui_assemblies + data_assemblies + fallback_data_assemblies
        for error in assembly["method_body_errors"]
    ]
    launched_targets = {row["target_form"] for row in constructor_launcher_edges}
    resolutions = []
    domain_hints = {
        "TreasuryOld.Forms.frmBankReconciliation": "receivables_treasury/bank_reconciliation_detail",
        "TreasuryOld.Forms.frmBankReconciliationList": "receivables_treasury/bank_reconciliation_queue",
        "TreasuryOld.Forms.frmChek": "procurement_payables/cheque_print_layout_dialog",
        "TreasuryOld.Forms.frmList": "reporting_documents/legacy_treasury_report_list",
        "TreasuryOld.Forms.frmReconciliation": "receivables_treasury/bank_statement_matching",
        "TreasuryOld.Forms.frmReconciliationSetup": "receivables_treasury/bank_statement_import_and_reconciliation_setup",
        "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict": "configuration/special_district_options_unconfirmed",
    }
    for row in high:
        type_name = row["type"]
        launchers = [
            edge
            for edge in constructor_launcher_edges
            if edge["target_form"] == type_name
        ]
        if launchers:
            status = "RESOLVED_AS_CHILD_OR_NESTED_SURFACE"
        else:
            status = "ROOT_ENTRYPOINT_STILL_UNRESOLVED"
        resolutions.append(
            {
                "type": type_name,
                "status": status,
                "launcher_count": len(launchers),
                "launchers": launchers,
                "static_forminfo_or_menu_match_count": 0,
                "target_domain_hint_not_final_mapping": domain_hints[type_name],
                "next_action": (
                    "attach to parent route/capability and remove direct-route requirement"
                    if launchers
                    else "trace reflection/resource/base/event or confirm unused/unconfigured with business owner"
                ),
            }
        )

    artifact = {
        "artifact": "varanegar_priority_form_gap_parent_and_datalayer_call_graph",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "safety": {
            "mode": "READ_ONLY_PE_METADATA_AND_IL_PLUS_STATIC_ROUTE_EVIDENCE",
            "assemblies_loaded_or_executed": 0,
            "database_queries_executed_by_this_builder": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "priority_gap_count": len(high_types),
            "parent_form_count": len(parent_types),
            "precise_type_reference_edge_count": len(precise_reference_edges),
            "constructor_launcher_edge_count": len(constructor_launcher_edges),
            "resolved_as_child_or_nested_surface_count": len(launched_targets),
            "root_entrypoint_unresolved_count": len(high_types - launched_targets),
            "static_forminfo_or_menu_match_count": static_routes["summary"]["matched_static_row_count"],
            "treasury_data_layer_type_count": len(data_contracts),
            "treasury_data_layer_type_found_count": sum(row["found"] for row in data_contracts),
            "treasury_data_layer_namespace_assembly_mismatch_count": sum(
                row["namespace_assembly_mismatch"] for row in data_contracts
            ),
            "method_body_error_count": len(errors),
            "source_hash_mismatch_count": len(set(source_hash_mismatches)),
        },
        "source_hash_mismatches": sorted(set(source_hash_mismatches)),
        "method_body_errors": errors,
        "compact_type_references": compact_launch_refs,
        "precise_type_reference_edges": precise_reference_edges,
        "constructor_launcher_edges": constructor_launcher_edges,
        "priority_form_contracts": high_contracts,
        "treasury_data_layer_contracts": sorted(data_contracts, key=lambda row: row["type"]),
        "resolutions": sorted(resolutions, key=lambda row: row["type"]),
        "base_simple_dialog_contract": _method_summary(
            ui_type_index["Application.BaseTemaplateV2.UIBase.FormBaseSimpleDialog"]
        ),
        "limits": [
            "No FormInfo/menu match plus no direct constructor still does not prove a dead form.",
            "Domain hints are evidence routing suggestions and are not final mappings.",
            "Static call graphs can miss reflection, resources, interfaces, events and runtime feature branches.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    complete = (
        not errors
        and not source_hash_mismatches
        and all(row["found"] for row in data_contracts)
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
