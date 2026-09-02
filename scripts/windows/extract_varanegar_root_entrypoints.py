"""Trace unresolved Varanegar form entrypoints across every selected assembly.

The extractor parses PE metadata and IL only. It never loads an assembly and it
persists only references to the three explicit target type names.
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
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

from extract_varanegar_targeted_il_contracts import (
    _full_type_name,
    _owner_maps,
    _resolve_token,
)


TARGETS = (
    "TreasuryOld.Forms.frmBankReconciliationList",
    "TreasuryOld.Forms.frmReconciliationSetup",
    "VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict",
)
KNOWN_NONBUSINESS_BODY_ERRORS = {
    (
        "VN.SDS.MainData.UI.dll",
        "VN.SDS.MainData.UI.ServerConfig.FormServerConfig",
        "InitializeComponent",
        "MethodBodyFormatError",
    ),
    (
        "VN.SDS.Report.PersonnalDashboard.DashboardForm.dll",
        "VN.SDS.Report.PersonnalDashboard.DashboardForm.DesignerForm",
        "InitializeComponent",
        "MethodBodyFormatError",
    ),
}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _base_type_name(type_row: Any) -> str:
    base_row = getattr(getattr(type_row, "Extends", None), "row", None)
    return "" if base_row is None else _full_type_name(base_row)


def _matches_target(reference: str) -> str | None:
    for target in TARGETS:
        if reference == target or reference.startswith(target + "."):
            return target
    return None


def _analyze(path: Path, expected_sha256: str) -> dict[str, Any]:
    actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    pe = dnfile.dnPE(str(path))
    method_owners, field_owners = _owner_maps(pe)
    type_table = getattr(pe.net.mdtables, "TypeDef", None)
    type_rows = [] if not type_table else type_table.rows
    token_references: list[dict[str, Any]] = []
    inheritance_edges: list[dict[str, str]] = []
    exact_user_string_references: list[dict[str, Any]] = []
    embedded_user_string_references: list[dict[str, Any]] = []
    resource_name_references: list[dict[str, str]] = []
    method_body_errors: list[dict[str, Any]] = []
    method_body_count = 0
    string_tokens_inspected = 0

    for type_row in type_rows:
        caller_type = _full_type_name(type_row)
        base_type = _base_type_name(type_row)
        matched_base = _matches_target(base_type)
        if matched_base:
            inheritance_edges.append(
                {"derived_type": caller_type, "base_target": matched_base}
            )
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            method_name = _text(getattr(method, "Name", ""))
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                method_body_errors.append(
                    {
                        "caller_type": caller_type,
                        "caller_method": method_name,
                        "rva": int(method.Rva),
                        "error_class": type(exc).__name__,
                    }
                )
                continue
            method_body_count += 1
            seen_tokens: set[tuple[str, str, str]] = set()
            seen_strings: set[str] = set()
            for instruction in body.instructions:
                operand = instruction.operand
                if isinstance(operand, Token):
                    resolved = _resolve_token(pe, operand, method_owners, field_owners)
                    matched = _matches_target(resolved)
                    if matched:
                        key = (instruction.mnemonic, resolved, matched)
                        if key not in seen_tokens:
                            seen_tokens.add(key)
                            token_references.append(
                                {
                                    "caller_type": caller_type,
                                    "caller_method": method_name,
                                    "opcode": instruction.mnemonic,
                                    "target_type": matched,
                                    "resolved_member": resolved,
                                    "is_self_reference": caller_type == matched,
                                }
                            )
                elif isinstance(operand, StringToken):
                    string_tokens_inspected += 1
                    item = pe.net.user_strings.get(operand.rid)
                    value = "" if item is None else _text(item)
                    for target in TARGETS:
                        simple = target.rsplit(".", 1)[-1]
                        if value in {target, simple} and value not in seen_strings:
                            seen_strings.add(value)
                            exact_user_string_references.append(
                                {
                                    "caller_type": caller_type,
                                    "caller_method": method_name,
                                    "target_type": target,
                                    "literal_kind": "full_type_name" if value == target else "simple_type_name",
                                }
                            )
                        elif (
                            (target in value or simple in value)
                            and value not in seen_strings
                        ):
                            seen_strings.add(value)
                            embedded_user_string_references.append(
                                {
                                    "caller_type": caller_type,
                                    "caller_method": method_name,
                                    "target_type": target,
                                    "literal_kind": (
                                        "embedded_full_type_name"
                                        if target in value
                                        else "embedded_simple_type_name"
                                    ),
                                    "raw_literal_persisted": False,
                                }
                            )

    resources = getattr(pe.net.mdtables, "ManifestResource", None)
    for row in ([] if not resources else resources.rows):
        name = _text(getattr(row, "Name", ""))
        for target in TARGETS:
            if target in name or target.rsplit(".", 1)[-1] in name:
                resource_name_references.append(
                    {"target_type": target, "resource_name": name}
                )

    return {
        "file": path.name,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual_sha256,
        "hash_matches": actual_sha256 == expected_sha256,
        "type_count": max(0, len(type_rows) - 1),
        "method_body_count": method_body_count,
        "string_token_count_inspected_transiently": string_tokens_inspected,
        "token_references": token_references,
        "inheritance_edges": inheritance_edges,
        "exact_user_string_references": exact_user_string_references,
        "embedded_user_string_references": embedded_user_string_references,
        "resource_name_references": resource_name_references,
        "method_body_errors": method_body_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--assembly-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    inventory = json.loads(args.binary_inventory.read_text(encoding="utf-8-sig"))
    contracts = json.loads(args.assembly_contracts.read_text(encoding="utf-8-sig"))
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    # Scan the complete active first-party package, not only the seven core
    # families used by the earlier business-metadata catalog. Entrypoints may
    # live in Setting, POS, Tablet, shared framework, report, or container code.
    selected_files = sorted(
        row["name"]
        for row in inventory["files"]
        if row["name"].casefold().endswith((".dll", ".exe"))
    )
    assemblies = [
        _analyze(args.source_directory / name, expected[name])
        for name in selected_files
    ]
    token_refs = [row for assembly in assemblies for row in assembly["token_references"]]
    external_token_refs = [row for row in token_refs if not row["is_self_reference"]]
    constructor_refs = [
        row
        for row in external_token_refs
        if row["opcode"] == "newobj" and row["resolved_member"].endswith("..ctor")
    ]
    string_refs = [row for assembly in assemblies for row in assembly["exact_user_string_references"]]
    embedded_string_refs = [
        row for assembly in assemblies for row in assembly["embedded_user_string_references"]
    ]
    inheritance = [row for assembly in assemblies for row in assembly["inheritance_edges"]]
    resources = [row for assembly in assemblies for row in assembly["resource_name_references"]]
    errors = [
        {"file": assembly["file"], **row}
        for assembly in assemblies
        for row in assembly["method_body_errors"]
    ]
    unexpected_errors = [
        row
        for row in errors
        if (
            row["file"],
            row["caller_type"],
            row["caller_method"],
            row["error_class"],
        )
        not in KNOWN_NONBUSINESS_BODY_ERRORS
    ]
    resolutions = []
    for target in TARGETS:
        direct = [row for row in constructor_refs if row["target_type"] == target]
        exact_dynamic = [row for row in string_refs if row["target_type"] == target]
        embedded_dynamic = [
            row for row in embedded_string_refs if row["target_type"] == target
        ]
        dynamic = exact_dynamic + embedded_dynamic
        resolutions.append(
            {
                "type": target,
                "constructor_entrypoint_count": len(direct),
                "exact_string_reference_count": len(exact_dynamic),
                "embedded_string_reference_count": len(embedded_dynamic),
                "status": (
                    "RESOLVED_BY_NON_FORM_ASSEMBLY_SCAN"
                    if direct or dynamic
                    else "ENTRYPOINT_STILL_UNRESOLVED_AFTER_ALL_ASSEMBLY_IL_SCAN"
                ),
                "constructor_entrypoints": direct,
                "exact_string_references": exact_dynamic,
                "embedded_string_references": embedded_dynamic,
            }
        )

    artifact = {
        "artifact": "varanegar_unresolved_root_entrypoint_all_assembly_scan",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "safety": {
            "mode": "READ_ONLY_ALL_SELECTED_ASSEMBLY_METADATA_AND_IL",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "resource_payloads_read": 0,
            "config_files_read": 0,
            "raw_non_target_string_literals_persisted": 0,
        },
        "summary": {
            "target_root_count": len(TARGETS),
            "assembly_count": len(assemblies),
            "core_metadata_baseline_assembly_count": len(contracts["assemblies"]),
            "type_count": sum(row["type_count"] for row in assemblies),
            "method_body_count": sum(row["method_body_count"] for row in assemblies),
            "method_body_error_count": len(errors),
            "source_hash_mismatch_count": sum(not row["hash_matches"] for row in assemblies),
            "target_token_reference_count": len(token_refs),
            "self_target_token_reference_count": sum(row["is_self_reference"] for row in token_refs),
            "external_target_token_reference_count": len(external_token_refs),
            "external_constructor_entrypoint_count": len(constructor_refs),
            "exact_target_string_reference_count": len(string_refs),
            "embedded_target_string_reference_count": len(embedded_string_refs),
            "target_inheritance_edge_count": len(inheritance),
            "target_resource_name_reference_count": len(resources),
            "resolved_root_count": sum(row["status"].startswith("RESOLVED") for row in resolutions),
            "still_unresolved_root_count": sum("STILL_UNRESOLVED" in row["status"] for row in resolutions),
            "known_nonbusiness_method_body_error_count": len(errors) - len(unexpected_errors),
            "unexpected_method_body_error_count": len(unexpected_errors),
        },
        "resolutions": resolutions,
        "external_target_token_references": external_token_refs,
        "embedded_target_string_references": embedded_string_refs,
        "target_inheritance_edges": inheritance,
        "target_resource_name_references": resources,
        "method_body_errors": errors,
        "assemblies": [
            {
                "file": row["file"],
                "actual_sha256": row["actual_sha256"],
                "hash_matches": row["hash_matches"],
                "type_count": row["type_count"],
                "method_body_count": row["method_body_count"],
                "string_token_count_inspected_transiently": row["string_token_count_inspected_transiently"],
                "target_reference_count": len(row["token_references"]),
                "method_body_error_count": len(row["method_body_errors"]),
            }
            for row in assemblies
        ],
        "limits": [
            "No explicit IL reference does not prove a dead form; native launchers, encrypted resources, external plugins or runtime configuration may remain.",
            "Only exact or embedded allowlisted target type-name matches are persisted; raw embedded literals and all other strings are discarded.",
            "Manifest resource names are metadata only; resource payloads are not read.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    complete = not unexpected_errors and not any(not row["hash_matches"] for row in assemblies)
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
