"""Build compact call contracts for every high-confidence Varanegar form."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_data_entry_il_contracts import _method_summary, _review_priority
from extract_varanegar_targeted_il_contracts import _analyze_assembly


REPORT_METHOD = re.compile(r"(?:report|print|preview|export|excel|pdf|chart|dashboard)", re.IGNORECASE)
TRANSACTION_CALL = re.compile(r"(?:Transaction|DataContext\.(?:Commit|Rollback)|BeginTransaction|\.Commit|\.RollBack|\.Rollback)$", re.IGNORECASE)
FIRST_PARTY_TYPE = re.compile(r"^(?:VN\.SDS\.|TreasuryOld\.)")
MODULE = re.compile(r"^VN\.SDS\.(MainData|Sales|Stock|Treasury|CreateVoucher|Setting)\.")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _type_from_call(call: str) -> str:
    if call.endswith("..ctor"):
        return call[:-6]
    return call.rsplit(".", 1)[0] if "." in call else call


def _module_from_call(call: str) -> str | None:
    match = MODULE.match(call)
    if match:
        return match.group(1)
    if call.startswith("TreasuryOld."):
        return "TreasuryOld"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--form-catalog", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    catalog = _load(args.form_catalog)
    binaries = _load(args.binary_inventory)
    expected_hashes = {row["name"]: row["sha256"] for row in binaries["files"]}
    selected = [
        row for row in catalog["forms"] if row["form_evidence_confidence"] == "high"
    ]
    target_map: dict[str, set[str]] = {}
    catalog_by_type: dict[str, dict[str, Any]] = {}
    for row in selected:
        target_map.setdefault(row["assembly"], set()).add(row["type"])
        catalog_by_type[row["type"]] = row

    source_hash_mismatches = []
    assemblies = []
    for assembly_name, targets in sorted(target_map.items()):
        path = args.source_directory / assembly_name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hashes.get(assembly_name):
            source_hash_mismatches.append(assembly_name)
        assemblies.append(_analyze_assembly(path, targets))

    forms = []
    for assembly in assemblies:
        for target in assembly["target_types"]:
            catalog_row = catalog_by_type[target["type"]]
            method_summary = _method_summary(target) if target["found"] else None
            methods = target["methods"]
            calls = [] if method_summary is None else method_summary["external_contract_calls"]
            first_party_calls = sorted({call for call in calls if FIRST_PARTY_TYPE.match(call)})
            first_party_types = sorted({_type_from_call(call) for call in first_party_calls})
            called_modules = sorted({module for call in first_party_calls if (module := _module_from_call(call))})
            literal_counts = Counter(
                literal["persisted_as"]
                for method in methods
                for literal in method["string_literals"]
            )
            contract = {
                **(method_summary or {}),
                "report_or_output_methods": sorted({method["method"] for method in methods if REPORT_METHOD.search(method["method"])}),
                "transaction_signal_calls": [call for call in calls if TRANSACTION_CALL.search(call)],
                "first_party_external_calls": first_party_calls,
                "first_party_external_types": first_party_types,
                "called_module_families": called_modules,
                "literal_persistence_counts": dict(sorted(literal_counts.items())),
            }
            forms.append(
                {
                    "assembly": assembly["file"],
                    "type": target["type"],
                    "found": target["found"],
                    "base_type": catalog_row["base_type"],
                    "page_shape": catalog_row["page_shape"],
                    "primary_domain_id": catalog_row["primary_domain_id"],
                    "review_priority": _review_priority(contract) if target["found"] else None,
                    "contract": contract if target["found"] else None,
                }
            )

    errors = [error for assembly in assemblies for error in assembly["method_body_errors"]]
    business_errors = [error for error in errors if error["method"] != "InitializeComponent"]
    page_shape_counts = Counter(row["page_shape"] for row in forms)
    domain_counts = Counter(str(row["primary_domain_id"] or "unmapped") for row in forms)
    module_pair_counts = Counter(
        "+".join(row["contract"]["called_module_families"])
        for row in forms
        if len(row["contract"]["called_module_families"]) > 1
    )
    business_module_pair_counts = Counter(
        "+".join(sorted(set(row["contract"]["called_module_families"]) - {"Setting"}))
        for row in forms
        if len(set(row["contract"]["called_module_families"]) - {"Setting"}) > 1
    )
    artifact = {
        "artifact": "varanegar_all_high_confidence_form_compact_call_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": {
            "directory": str(args.source_directory),
            "form_catalog": args.form_catalog.as_posix(),
            "binary_inventory": args.binary_inventory.as_posix(),
            "selection": "all high-confidence form candidates",
        },
        "safety": {
            "mode": "READ_ONLY_COMPACT_PE_METADATA_AND_IL_FROM_RUNTIME_SHARE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "config_or_resource_payloads_read": 0,
            "raw_non_allowlisted_strings_persisted": 0,
            "raw_method_il_persisted": 0,
        },
        "summary": {
            "selected_form_count": len(selected),
            "assembly_count": len(assemblies),
            "found_form_count": sum(row["found"] for row in forms),
            "missing_form_count": sum(not row["found"] for row in forms),
            "method_body_count": sum(row["method_bodies_read"] for row in assemblies),
            "method_body_error_count": len(errors),
            "business_method_body_error_count": len(business_errors),
            "source_hash_mismatch_count": len(source_hash_mismatches),
            "write_like_form_count": sum(bool(row["contract"]["write_like_methods"]) for row in forms),
            "destructive_or_reversing_form_count": sum(bool(row["contract"]["destructive_or_reversing_methods"]) for row in forms),
            "validation_form_count": sum(bool(row["contract"]["validation_methods"]) for row in forms),
            "permission_form_count": sum(bool(row["contract"]["permission_methods"]) for row in forms),
            "report_or_output_form_count": sum(bool(row["contract"]["report_or_output_methods"]) for row in forms),
            "transaction_signal_form_count": sum(bool(row["contract"]["transaction_signal_calls"]) for row in forms),
            "first_party_call_count": sum(len(row["contract"]["first_party_external_calls"]) for row in forms),
            "cross_module_form_count": sum(len(row["contract"]["called_module_families"]) > 1 for row in forms),
            "cross_business_module_form_count_excluding_setting": sum(
                len(set(row["contract"]["called_module_families"]) - {"Setting"}) > 1
                for row in forms
            ),
            "page_shape_counts": dict(sorted(page_shape_counts.items())),
            "primary_domain_counts": dict(sorted(domain_counts.items())),
        },
        "source_hash_mismatches": source_hash_mismatches,
        "method_body_errors": errors,
        "cross_module_family_combinations": dict(sorted(module_pair_counts.items(), key=lambda row: (-row[1], row[0]))),
        "cross_business_module_family_combinations_excluding_setting": dict(
            sorted(business_module_pair_counts.items(), key=lambda row: (-row[1], row[0]))
        ),
        "forms": sorted(forms, key=lambda row: (row["assembly"], row["type"])),
        "limits": [
            "Compact contracts omit raw IL and non-allowlisted string content.",
            "Direct calls can miss inheritance, reflection, ORM, events and runtime configuration branches.",
            "Form capacity does not prove current-menu authorization or recent operational use.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if not source_hash_mismatches and artifact["summary"]["missing_form_count"] == 0 and not business_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
