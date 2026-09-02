"""Trace three extension SQL-name gaps through related static .NET types.

Assemblies are parsed as PE metadata/IL only and are never loaded or executed.
Non-allowlisted strings remain fingerprints via the shared IL analyzer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile

from extract_varanegar_targeted_il_contracts import _analyze_assembly, _full_type_name


TARGET_FAMILIES: dict[str, tuple[str, ...]] = {
    "VN.SDS.POSSystem.Business.dll": ("lineardiscount", "possession"),
    "VN.SDS.POSSystem.DataAccess.dll": ("lineardiscount", "possession"),
    "VN.SDS.POSSystem.IBusiness.dll": ("lineardiscount", "possession"),
    "VN.SDS.Tablet.UI.dll": ("dealerdaypath",),
    "VN.SDS.Tablet.Business.dll": ("dealerdaypath",),
    "VN.SDS.Tablet.DataAccess.dll": ("dealerdaypath",),
    "VN.SDS.Tablet.IBusiness.dll": ("dealerdaypath",),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    inventory = _load(args.binary_inventory)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    missing_files = sorted(set(TARGET_FAMILIES) - set(expected))
    hash_mismatches = []
    metadata_failures = []
    targets: dict[str, set[str]] = {}
    type_family: dict[str, str] = {}
    for assembly, tokens in TARGET_FAMILIES.items():
        path = args.source_directory / assembly
        if not path.exists():
            continue
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected[assembly]:
            hash_mismatches.append(assembly)
        try:
            pe = dnfile.dnPE(str(path))
            table = getattr(pe.net.mdtables, "TypeDef", None)
            matched = set()
            for row in ([] if table is None else table.rows):
                full = _full_type_name(row)
                folded = full.casefold()
                for token in tokens:
                    if token in folded:
                        matched.add(full)
                        type_family[full] = (
                            "pos.linear_discount" if token == "lineardiscount"
                            else "pos.session" if token == "possession"
                            else "tablet.dealer_day_path"
                        )
            targets[assembly] = matched
        except Exception as exc:
            metadata_failures.append({"file": assembly, "error_class": type(exc).__name__})

    analyses = [
        _analyze_assembly(args.source_directory / assembly, names)
        for assembly, names in sorted(targets.items())
    ]
    method_errors = [
        {"file": analysis["file"], **row}
        for analysis in analyses
        for row in analysis["method_body_errors"]
    ]
    type_contracts = []
    literal_counts = {"allowlisted_business_literal": 0, "allowlisted_ui_literal": 0, "fingerprint_only": 0}
    for analysis in analyses:
        for target in analysis["target_types"]:
            for method in target["methods"]:
                for literal in method["string_literals"]:
                    literal_counts[literal["persisted_as"]] = literal_counts.get(literal["persisted_as"], 0) + 1
            type_contracts.append(
                {
                    "capability": type_family[target["type"]],
                    "assembly": analysis["file"],
                    **target,
                }
            )

    by_capability = []
    for capability in ("pos.linear_discount", "pos.session", "tablet.dealer_day_path"):
        rows = [row for row in type_contracts if row["capability"] == capability]
        safe_literals = sorted(
            {
                literal["safe_literal"]
                for row in rows
                for method in row["methods"]
                for literal in method["string_literals"]
                if literal["persisted_as"] == "allowlisted_business_literal"
            }
        )
        first_party_calls = sorted(
            {
                call
                for row in rows
                for method in row["methods"]
                for call in method["calls"]
                if call.startswith(("VN.SDS.", "Application.", "Thunderstruck.", "TreasuryOld."))
            }
        )
        by_capability.append(
            {
                "capability": capability,
                "type_count": len(rows),
                "method_count": sum(len(row["methods"]) for row in rows),
                "allowlisted_business_literals": safe_literals,
                "first_party_calls": first_party_calls,
            }
        )

    errors = []
    if missing_files:
        errors.append("required assembly missing from inventory")
    if hash_mismatches:
        errors.append("source hash mismatch")
    if metadata_failures:
        errors.append("metadata parse failure")
    if method_errors:
        errors.append("method body parse error")
    if any(not row["type_count"] for row in by_capability):
        errors.append("gap capability has no related type")
    artifact = {
        "artifact": "varanegar_three_extension_gap_related_type_and_il_paths",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_TARGETED_PE_METADATA_AND_IL_GAP_TRACE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "config_or_resource_payloads_read": 0,
            "raw_non_allowlisted_strings_persisted": 0,
        },
        "summary": {
            "capability_gap_count": len(by_capability),
            "assembly_count": len(analyses),
            "related_type_count": len(type_contracts),
            "method_body_count": sum(len(row["methods"]) for row in type_contracts),
            "call_count": sum(len(method["calls"]) for row in type_contracts for method in row["methods"]),
            "string_literal_count": sum(literal_counts.values()),
            "allowlisted_business_literal_count": literal_counts.get("allowlisted_business_literal", 0),
            "allowlisted_ui_literal_count": literal_counts.get("allowlisted_ui_literal", 0),
            "fingerprint_only_literal_count": literal_counts.get("fingerprint_only", 0),
            "missing_file_count": len(missing_files),
            "source_hash_mismatch_count": len(hash_mismatches),
            "metadata_failure_count": len(metadata_failures),
            "method_body_error_count": len(method_errors),
            "validation_error_count": len(errors),
        },
        "capability_paths": by_capability,
        "type_contracts": type_contracts,
        "missing_files": missing_files,
        "source_hash_mismatches": hash_mismatches,
        "metadata_failures": metadata_failures,
        "method_body_errors": method_errors,
        "validation_errors": errors,
        "limits": [
            "Related type-name families and static IL calls do not prove runtime execution or final scope.",
            "Dynamic SQL, reflection, base-class hooks and runtime configuration can hide dependencies.",
            "Only allowlisted business literals are readable; all other strings remain fingerprints.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
