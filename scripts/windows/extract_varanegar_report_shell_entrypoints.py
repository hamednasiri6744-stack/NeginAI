"""Find callers, inheritance and exact-name references for unresolved report shells."""

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

from extract_varanegar_targeted_il_contracts import _full_type_name, _owner_maps, _resolve_token


KNOWN_NONBUSINESS_BODY_ERRORS = {
    ("VN.SDS.MainData.UI.dll", "VN.SDS.MainData.UI.ServerConfig.FormServerConfig", "InitializeComponent", "MethodBodyFormatError"),
    ("VN.SDS.Report.PersonnalDashboard.DashboardForm.dll", "VN.SDS.Report.PersonnalDashboard.DashboardForm.DesignerForm", "InitializeComponent", "MethodBodyFormatError"),
}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _base_type_name(row: Any) -> str:
    base = getattr(getattr(row, "Extends", None), "row", None)
    return "" if base is None else _full_type_name(base)


def _match(reference: str, targets: tuple[str, ...]) -> str | None:
    return next((target for target in targets if reference == target or reference.startswith(target + ".")), None)


def _scan(path: Path, expected_sha: str, targets: tuple[str, ...]) -> dict[str, Any]:
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    pe = dnfile.dnPE(str(path))
    method_owners, field_owners = _owner_maps(pe)
    table = getattr(pe.net.mdtables, "TypeDef", None)
    type_rows = [] if not table else table.rows
    token_refs: list[dict[str, Any]] = []
    inheritance: list[dict[str, str]] = []
    string_refs: list[dict[str, str]] = []
    errors: list[dict[str, Any]] = []
    method_count = 0
    for type_row in type_rows:
        caller_type = _full_type_name(type_row)
        base = _base_type_name(type_row)
        target_base = _match(base, targets)
        if target_base:
            inheritance.append({"derived_type": caller_type, "base_target": target_base})
        for method_index in type_row.MethodList or []:
            method = method_index.row
            if method is None or not method.Rva:
                continue
            method_name = _text(getattr(method, "Name", ""))
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception as exc:
                errors.append({"caller_type": caller_type, "caller_method": method_name, "error_class": type(exc).__name__})
                continue
            method_count += 1
            seen_tokens: set[tuple[str, str, str]] = set()
            seen_strings: set[tuple[str, str]] = set()
            for instruction in body.instructions:
                operand = instruction.operand
                if isinstance(operand, Token):
                    resolved = _resolve_token(pe, operand, method_owners, field_owners)
                    target = _match(resolved, targets)
                    if target:
                        key = (instruction.mnemonic, resolved, target)
                        if key not in seen_tokens:
                            seen_tokens.add(key)
                            token_refs.append({
                                "caller_type": caller_type,
                                "caller_method": method_name,
                                "opcode": instruction.mnemonic,
                                "target_type": target,
                                "resolved_member": resolved,
                                "is_self_reference": caller_type == target,
                            })
                elif isinstance(operand, StringToken):
                    item = pe.net.user_strings.get(operand.rid)
                    value = "" if item is None else _text(item)
                    for target in targets:
                        simple = target.rsplit(".", 1)[-1]
                        if value in {target, simple} and (value, target) not in seen_strings:
                            seen_strings.add((value, target))
                            string_refs.append({
                                "caller_type": caller_type,
                                "caller_method": method_name,
                                "target_type": target,
                                "literal_kind": "full_type_name" if value == target else "simple_type_name",
                            })
    return {
        "file": path.name,
        "hash_matches": actual_sha == expected_sha,
        "type_count": max(0, len(type_rows) - 1),
        "method_body_count": method_count,
        "token_references": token_refs,
        "inheritance_edges": inheritance,
        "exact_name_references": string_refs,
        "method_body_errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--report-gaps", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)

    inventory = json.loads(args.binary_inventory.read_text(encoding="utf-8-sig"))
    gaps = json.loads(args.report_gaps.read_text(encoding="utf-8-sig"))
    targets = tuple(sorted(row["legacy_type"] for row in gaps["reports"] if row["evidence_level"].startswith("L0_")))
    selected = sorted(
        (row for row in inventory["files"] if row["name"].casefold().endswith((".dll", ".exe"))),
        key=lambda row: row["name"].casefold(),
    )
    scans = [_scan(args.source_directory / row["name"], row["sha256"], targets) for row in selected]
    token_refs = [dict(file=scan["file"], **row) for scan in scans for row in scan["token_references"]]
    external_refs = [row for row in token_refs if not row["is_self_reference"]]
    constructors = [row for row in external_refs if row["opcode"] == "newobj" and row["resolved_member"].endswith("..ctor")]
    inheritance = [dict(file=scan["file"], **row) for scan in scans for row in scan["inheritance_edges"]]
    string_refs = [dict(file=scan["file"], **row) for scan in scans for row in scan["exact_name_references"]]
    body_errors = [dict(file=scan["file"], **row) for scan in scans for row in scan["method_body_errors"]]
    unexpected_errors = [row for row in body_errors if (row["file"], row["caller_type"], row["caller_method"], row["error_class"]) not in KNOWN_NONBUSINESS_BODY_ERRORS]
    resolutions = []
    for target in targets:
        refs = [row for row in external_refs if row["target_type"] == target]
        ctors = [row for row in constructors if row["target_type"] == target]
        strings = [row for row in string_refs if row["target_type"] == target]
        derived = [row for row in inheritance if row["base_target"] == target]
        resolutions.append({
            "target_type": target,
            "external_token_reference_count": len(refs),
            "external_constructor_reference_count": len(ctors),
            "exact_name_reference_count": len(strings),
            "derived_type_count": len(derived),
            "entrypoint_status": "CALLER_OR_DYNAMIC_ENTRYPOINT_FOUND" if refs or strings or derived else "NO_EXTERNAL_ENTRYPOINT_IN_PACKAGE_IL",
            "external_token_references": refs,
            "constructor_entrypoints": ctors,
            "exact_name_references": strings,
            "derived_types": derived,
        })
    validation_errors = []
    if gaps.get("validation") != "PASS":
        validation_errors.append("report gap input is not PASS")
    if any(not scan["hash_matches"] for scan in scans):
        validation_errors.append("source package hash mismatch")
    if unexpected_errors:
        validation_errors.append("unexpected method body parsing errors")
    artifact = {
        "artifact": "varanegar_unresolved_report_shell_all_assembly_entrypoint_scan",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_COMPLETE_PACKAGE_METADATA_AND_IL_ENTRYPOINT_SCAN",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_or_reports_executed": 0,
            "resource_payloads_or_config_files_read": 0,
            "raw_non_target_string_literals_persisted": 0,
        },
        "summary": {
            "target_report_shell_count": len(targets),
            "assembly_count": len(scans),
            "type_count": sum(row["type_count"] for row in scans),
            "method_body_count": sum(row["method_body_count"] for row in scans),
            "target_token_reference_count": len(token_refs),
            "external_token_reference_count": len(external_refs),
            "external_constructor_reference_count": len(constructors),
            "exact_name_reference_count": len(string_refs),
            "target_inheritance_edge_count": len(inheritance),
            "target_with_entrypoint_evidence_count": sum(row["entrypoint_status"] == "CALLER_OR_DYNAMIC_ENTRYPOINT_FOUND" for row in resolutions),
            "target_without_entrypoint_evidence_count": sum(row["entrypoint_status"] == "NO_EXTERNAL_ENTRYPOINT_IN_PACKAGE_IL" for row in resolutions),
            "method_body_error_count": len(body_errors),
            "unexpected_method_body_error_count": len(unexpected_errors),
            "source_hash_mismatch_count": sum(not row["hash_matches"] for row in scans),
            "runtime_execution_or_result_parity_proven_count": 0,
            "validation_error_count": len(validation_errors),
        },
        "resolutions": resolutions,
        "method_body_errors": body_errors,
        "validation_errors": validation_errors,
        "limits": [
            "Reflection with computed type names, resources and framework-owned report engines may remain invisible.",
            "An IL reference proves static reachability only, not runtime branch execution or result parity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}, ensure_ascii=False))
    return 0 if not validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
