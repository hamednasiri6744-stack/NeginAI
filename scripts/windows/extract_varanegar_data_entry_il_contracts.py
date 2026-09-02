"""Read IL for every high-confidence Varanegar data-entry/master-detail form.

Assemblies are parsed as PE metadata and IL; they are never loaded or executed.
String persistence uses the same redaction policy as the targeted IL extractor.
"""

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


WRITE_METHOD = re.compile(
    r"(?:save|insert|update|delete|remove|create|addnew|edit|submit|approve|"
    r"cancel|reverse|undo|post|close|issue|follow|setstatus)", re.IGNORECASE
)
DESTRUCTIVE_OR_REVERSING_METHOD = re.compile(
    r"(?:delete|remove|cancel|reverse|undo|backto|rollback|free)", re.IGNORECASE
)
VALIDATION_METHOD = re.compile(r"(?:valid|check|can|guard|verify|control)", re.IGNORECASE)
PERMISSION_METHOD = re.compile(r"(?:permission|persmission|access|authorize|right)", re.IGNORECASE)
MATERIAL_CONTRACT = re.compile(
    r"(?:Voucher|Cardex|Cheque|Receipt|Pay|Distribution|\.Dist|Stock|Sale|Order|"
    r"Accounting|Journal|Posting|Settlement)", re.IGNORECASE
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _method_summary(target: dict[str, Any]) -> dict[str, Any]:
    methods = target["methods"]
    names = [row["method"] for row in methods]
    calls = sorted({call for row in methods for call in row["calls"]})
    external_calls = [
        call
        for call in calls
        if not call.startswith(("System.", "Microsoft.", "DevExpress."))
        and not call.startswith(target["type"] + ".")
    ]
    return {
        "method_body_count": len(methods),
        "write_like_methods": sorted({name for name in names if WRITE_METHOD.search(name)}),
        "destructive_or_reversing_methods": sorted(
            {name for name in names if DESTRUCTIVE_OR_REVERSING_METHOD.search(name)}
        ),
        "validation_methods": sorted({name for name in names if VALIDATION_METHOD.search(name)}),
        "permission_methods": sorted({name for name in names if PERMISSION_METHOD.search(name)}),
        "external_contract_calls": external_calls,
        "external_contract_call_count": len(external_calls),
        "string_literal_count": sum(len(row["string_literals"]) for row in methods),
    }


def _review_priority(contract: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    if contract["destructive_or_reversing_methods"]:
        reasons.append("destructive_or_reversing_method")
    if contract["write_like_methods"] and any(
        MATERIAL_CONTRACT.search(call) for call in contract["external_contract_calls"]
    ):
        reasons.append("write_to_material_business_contract")
    if reasons:
        return {"level": "high", "reasons": reasons}
    if contract["write_like_methods"]:
        return {"level": "medium", "reasons": ["write_like_method"]}
    return {"level": "low", "reasons": ["no_write_like_method_observed"]}


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
        row
        for row in catalog["forms"]
        if row["form_evidence_confidence"] == "high"
        and row["page_shape"] in {"data_entry", "master_detail_entry"}
    ]
    target_map: dict[str, set[str]] = {}
    catalog_by_type: dict[str, dict[str, Any]] = {}
    for row in selected:
        target_map.setdefault(row["assembly"], set()).add(row["type"])
        catalog_by_type[row["type"]] = row

    assemblies = []
    source_hash_mismatches = []
    for assembly_name, target_names in sorted(target_map.items()):
        path = args.source_directory / assembly_name
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hashes.get(assembly_name):
            source_hash_mismatches.append(assembly_name)
        assemblies.append(_analyze_assembly(path, target_names))

    forms = []
    for assembly in assemblies:
        for target in assembly["target_types"]:
            catalog_row = catalog_by_type[target["type"]]
            contract = _method_summary(target) if target["found"] else None
            forms.append(
                {
                    "assembly": assembly["file"],
                    "type": target["type"],
                    "found": target["found"],
                    "page_shape": catalog_row["page_shape"],
                    "primary_domain_id": catalog_row["primary_domain_id"],
                    "catalog_flags": {
                        "has_create_or_save_method": catalog_row["has_create_or_save_method"],
                        "has_delete_method": catalog_row["has_delete_method"],
                        "has_permission_method": catalog_row["has_permission_method"],
                    },
                    "contract": contract,
                    "review_priority": _review_priority(contract) if contract else None,
                }
            )
    all_literals = [
        literal
        for assembly in assemblies
        for target in assembly["target_types"]
        for method in target["methods"]
        for literal in method["string_literals"]
    ]
    all_body_errors = [
        error for assembly in assemblies for error in assembly["method_body_errors"]
    ]
    business_body_errors = [
        error for error in all_body_errors if error["method"] != "InitializeComponent"
    ]
    assembly_summary: dict[str, dict[str, int]] = {}
    domain_summary: dict[str, dict[str, int]] = {}
    for row in forms:
        for key, bucket in (
            (row["assembly"], assembly_summary),
            (str(row["primary_domain_id"] or "unmapped"), domain_summary),
        ):
            values = bucket.setdefault(
                key,
                {"form_count": 0, "high_review_priority": 0, "write_like": 0, "destructive_or_reversing": 0},
            )
            values["form_count"] += 1
            values["high_review_priority"] += row["review_priority"]["level"] == "high"
            values["write_like"] += bool(row["contract"]["write_like_methods"])
            values["destructive_or_reversing"] += bool(row["contract"]["destructive_or_reversing_methods"])
    artifact = {
        "artifact": "varanegar_all_data_entry_form_il_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "source": {
            "directory": str(args.source_directory),
            "form_catalog": args.form_catalog.as_posix(),
            "binary_inventory": args.binary_inventory.as_posix(),
            "selection": "high-confidence data_entry or master_detail_entry forms",
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
            "selected_form_count": len(selected),
            "assembly_count": len(assemblies),
            "found_form_count": sum(row["found"] for row in forms),
            "missing_form_count": sum(not row["found"] for row in forms),
            "method_body_count": sum(row["method_bodies_read"] for row in assemblies),
            "method_body_error_count": sum(row["method_body_error_count"] for row in assemblies),
            "business_method_body_error_count": len(business_body_errors),
            "form_with_write_like_method_count": sum(bool((row["contract"] or {}).get("write_like_methods")) for row in forms),
            "form_with_destructive_or_reversing_method_count": sum(bool((row["contract"] or {}).get("destructive_or_reversing_methods")) for row in forms),
            "form_with_validation_method_count": sum(bool((row["contract"] or {}).get("validation_methods")) for row in forms),
            "form_with_permission_method_count": sum(bool((row["contract"] or {}).get("permission_methods")) for row in forms),
            "external_contract_call_count": sum((row["contract"] or {}).get("external_contract_call_count", 0) for row in forms),
            "string_literal_count": len(all_literals),
            "allowlisted_business_literal_count": sum(row["persisted_as"] == "allowlisted_business_literal" for row in all_literals),
            "allowlisted_ui_literal_count": sum(row["persisted_as"] == "allowlisted_ui_literal" for row in all_literals),
            "fingerprint_only_literal_count": sum(row["persisted_as"] == "fingerprint_only" for row in all_literals),
            "source_hash_mismatch_count": len(source_hash_mismatches),
            "review_priority_counts": {
                level: sum(row["review_priority"]["level"] == level for row in forms)
                for level in ("high", "medium", "low")
            },
        },
        "source_hash_mismatches": source_hash_mismatches,
        "assembly_summary": dict(sorted(assembly_summary.items())),
        "domain_summary": dict(sorted(domain_summary.items())),
        "method_body_errors": all_body_errors,
        "forms": sorted(forms, key=lambda row: (row["assembly"], row["type"])),
        "raw_il": assemblies,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0 if not source_hash_mismatches and artifact["summary"]["missing_form_count"] == 0 and not business_body_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
