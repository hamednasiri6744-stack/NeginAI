"""Trace high-impact Varanegar data-entry forms into Business/DataAccess IL."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_targeted_il_contracts import _analyze_assembly


BUSINESS_TYPE = re.compile(r"^VN\.SDS\.(MainData|Sales|Stock|Treasury)\.Business\.")
DATA_ACCESS_TYPE = re.compile(r"^VN\.SDS\.(MainData|Sales|Stock|Treasury)\.DataAccess\.")
WRITE_NAME = re.compile(r"(?:Save|Insert|Update|Delete|Remove|Create|Cancel|Reverse|Undo|Post|Close|Approve|Generate)", re.IGNORECASE)
VALIDATION_NAME = re.compile(r"(?:Valid|Check|Can|Guard|Verify|Control|Duplicate|Remain|Balance)", re.IGNORECASE)
TRANSACTION_CALL = re.compile(r"(?:Transaction|DataContext\.(?:Commit|Rollback)|BeginTransaction|\.Commit|\.RollBack|\.Rollback)$", re.IGNORECASE)
PERSISTENCE_CALL = re.compile(r"(?:ExecuteNonQuery|\.Insert|\.Update|\.Delete|\.Save|DataContext\.Commit)", re.IGNORECASE)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _type_from_call(call: str) -> str:
    if call.endswith("..ctor"):
        return call[:-6]
    return call.rsplit(".", 1)[0] if "." in call else call


def _assembly_for(type_name: str, layer: str) -> str:
    match = re.match(r"^VN\.SDS\.(MainData|Sales|Stock|Treasury)\.", type_name)
    if not match:
        raise ValueError(f"cannot map type to first-party assembly: {type_name}")
    return f"VN.SDS.{match.group(1)}.{layer}.dll"


def _index_types(assemblies: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        target["type"]: {"assembly": assembly["file"], **target}
        for assembly in assemblies
        for target in assembly["target_types"]
    }


def _contract(type_row: dict[str, Any]) -> dict[str, Any]:
    methods = type_row["methods"]
    calls = sorted({call for method in methods for call in method["calls"]})
    return {
        "assembly": type_row["assembly"],
        "type": type_row["type"],
        "found": type_row["found"],
        "method_body_count": len(methods),
        "write_like_methods": sorted({m["method"] for m in methods if WRITE_NAME.search(m["method"])}),
        "validation_like_methods": sorted({m["method"] for m in methods if VALIDATION_NAME.search(m["method"])}),
        "transaction_signal_calls": [call for call in calls if TRANSACTION_CALL.search(call)],
        "persistence_signal_calls": [call for call in calls if PERSISTENCE_CALL.search(call)],
        "first_party_external_calls": [call for call in calls if call.startswith("VN.SDS.") and not call.startswith(type_row["type"] + ".")],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--data-entry-il", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--top-form-count", type=int, default=12)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    data_entry = _load(args.data_entry_il)
    binaries = _load(args.binary_inventory)
    expected_hashes = {row["name"]: row["sha256"] for row in binaries["files"]}
    selected_forms = sorted(
        (row for row in data_entry["forms"] if row["review_priority"]["level"] == "high"),
        key=lambda row: (-row["contract"]["external_contract_call_count"], row["type"]),
    )[: args.top_form_count]

    form_business_edges = []
    business_targets: dict[str, set[str]] = {}
    for form in selected_forms:
        grouped: dict[str, set[str]] = {}
        for call in form["contract"]["external_contract_calls"]:
            target_type = _type_from_call(call)
            if BUSINESS_TYPE.match(target_type):
                grouped.setdefault(target_type, set()).add(call.rsplit(".", 1)[-1])
                business_targets.setdefault(_assembly_for(target_type, "Business"), set()).add(target_type)
        for target_type, methods in sorted(grouped.items()):
            form_business_edges.append(
                {"from_form": form["type"], "to_business_type": target_type, "called_members": sorted(methods)}
            )

    source_hash_mismatches = []
    business_assemblies = []
    for assembly_name, targets in sorted(business_targets.items()):
        path = args.source_directory / assembly_name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hashes.get(assembly_name):
            source_hash_mismatches.append(assembly_name)
        business_assemblies.append(_analyze_assembly(path, targets))
    business_index = _index_types(business_assemblies)
    business_contracts = [_contract(row) for row in business_index.values()]
    business_contract_by_type = {row["type"]: row for row in business_contracts}
    business_types_by_form: dict[str, set[str]] = {}
    for edge in form_business_edges:
        business_types_by_form.setdefault(edge["from_form"], set()).add(
            edge["to_business_type"]
        )
    form_transaction_signals = []
    for form in selected_forms:
        direct = sorted(
            call
            for call in form["contract"]["external_contract_calls"]
            if TRANSACTION_CALL.search(call)
        )
        transacting_business_types = sorted(
            type_name
            for type_name in business_types_by_form.get(form["type"], set())
            if business_contract_by_type[type_name]["transaction_signal_calls"]
        )
        form_transaction_signals.append(
            {
                "form": form["type"],
                "direct_ui_transaction_signals": direct,
                "called_business_types_with_transaction_signals": transacting_business_types,
                "has_any_observed_transaction_signal": bool(direct or transacting_business_types),
            }
        )

    business_data_edges = []
    data_targets: dict[str, set[str]] = {}
    for business in business_contracts:
        grouped: dict[str, set[str]] = {}
        for call in business["first_party_external_calls"]:
            target_type = _type_from_call(call)
            if DATA_ACCESS_TYPE.match(target_type):
                grouped.setdefault(target_type, set()).add(call.rsplit(".", 1)[-1])
                data_targets.setdefault(_assembly_for(target_type, "DataAccess"), set()).add(target_type)
        for target_type, methods in sorted(grouped.items()):
            business_data_edges.append(
                {"from_business_type": business["type"], "to_data_access_type": target_type, "called_members": sorted(methods)}
            )

    data_assemblies = []
    for assembly_name, targets in sorted(data_targets.items()):
        path = args.source_directory / assembly_name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hashes.get(assembly_name):
            source_hash_mismatches.append(assembly_name)
        data_assemblies.append(_analyze_assembly(path, targets))
    data_index = _index_types(data_assemblies)
    data_contracts = [_contract(row) for row in data_index.values()]
    all_assemblies = business_assemblies + data_assemblies
    errors = [error for assembly in all_assemblies for error in assembly["method_body_errors"]]

    artifact = {
        "artifact": "varanegar_high_impact_form_to_business_dataaccess_call_graph",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": {
            "directory": str(args.source_directory),
            "data_entry_il": args.data_entry_il.as_posix(),
            "binary_inventory": args.binary_inventory.as_posix(),
            "selection": f"top {args.top_form_count} high-review-priority forms by external call count",
        },
        "safety": {
            "mode": "READ_ONLY_PE_METADATA_AND_IL_FROM_RUNTIME_SHARE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "config_or_resource_payloads_read": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "selected_form_count": len(selected_forms),
            "business_assembly_count": len(business_assemblies),
            "business_type_count": len(business_contracts),
            "business_type_found_count": sum(row["found"] for row in business_contracts),
            "data_access_assembly_count": len(data_assemblies),
            "data_access_type_count": len(data_contracts),
            "data_access_type_found_count": sum(row["found"] for row in data_contracts),
            "form_to_business_edge_count": len(form_business_edges),
            "business_to_data_access_edge_count": len(business_data_edges),
            "business_method_body_count": sum(row["method_bodies_read"] for row in business_assemblies),
            "data_access_method_body_count": sum(row["method_bodies_read"] for row in data_assemblies),
            "method_body_error_count": len(errors),
            "source_hash_mismatch_count": len(set(source_hash_mismatches)),
            "business_type_with_transaction_signal_count": sum(bool(row["transaction_signal_calls"]) for row in business_contracts),
            "business_type_with_persistence_signal_count": sum(bool(row["persistence_signal_calls"]) for row in business_contracts),
            "selected_form_with_any_transaction_signal_count": sum(
                row["has_any_observed_transaction_signal"]
                for row in form_transaction_signals
            ),
        },
        "source_hash_mismatches": sorted(set(source_hash_mismatches)),
        "method_body_errors": errors,
        "selected_forms": [
            {"assembly": row["assembly"], "type": row["type"], "primary_domain_id": row["primary_domain_id"], "external_contract_call_count": row["contract"]["external_contract_call_count"]}
            for row in selected_forms
        ],
        "form_to_business_edges": form_business_edges,
        "form_transaction_signals": form_transaction_signals,
        "business_contracts": sorted(business_contracts, key=lambda row: row["type"]),
        "business_to_data_access_edges": business_data_edges,
        "data_access_contracts": sorted(data_contracts, key=lambda row: row["type"]),
        "raw_il": {"business": business_assemblies, "data_access": data_assemblies},
        "interpretation_limits": [
            "A direct UI call can omit inherited, interface, reflection, ORM or event-driven paths.",
            "A transaction signal in one type does not prove end-to-end atomicity across called modules.",
            "No observed call proves current-user authorization or recent operational use.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    complete = (
        artifact["summary"]["business_type_count"] == artifact["summary"]["business_type_found_count"]
        and artifact["summary"]["data_access_type_count"] == artifact["summary"]["data_access_type_found_count"]
        and not errors
        and not source_hash_mismatches
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
