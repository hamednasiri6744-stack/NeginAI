"""Extract static bank-statement parser, file and Office side-effect boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile  # noqa: F401 - documents the metadata parser used by the delegated analyzer

from extract_varanegar_targeted_il_contracts import _analyze_assembly


ASSEMBLY = "TreasuryOld.Forms.dll"
FORM_TYPE = "TreasuryOld.Forms.frmReconciliationSetup"
SELECTED_METHODS = {
    "getDataFromDBF",
    "getDataFromTXT",
    "getDataFromXLS",
    "WriteSchemaFile",
    "SaveAsExcel",
    "btnAccept_Click",
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
    expected_hash = {row["name"]: row["sha256"] for row in inventory["files"]}
    source = args.source_directory / ASSEMBLY
    actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    hash_mismatches = [] if actual_hash == expected_hash.get(ASSEMBLY) else [ASSEMBLY]
    analysis = _analyze_assembly(source, {FORM_TYPE})
    target = next(row for row in analysis["target_types"] if row["type"] == FORM_TYPE)

    methods = []
    found = set()
    for row in target["methods"]:
        if row["method"] not in SELECTED_METHODS:
            continue
        found.add(row["method"])
        methods.append(
            {
                "method": row["method"],
                "instruction_count": row["instruction_count"],
                "calls": row["calls"],
                "referenced_fields": row["referenced_fields"],
                "string_literal_values_persisted": 0,
            }
        )
    missing = sorted(SELECTED_METHODS - found)

    ole_db_methods = [
        row for row in methods if "System.Data.OleDb.OleDbConnection..ctor" in row["calls"]
    ]
    file_side_effect_methods = [
        row
        for row in methods
        if any(call.startswith(("System.IO.File.Create", "System.IO.File.Delete", "System.IO.File.Copy")) for call in row["calls"])
    ]
    office_methods = [
        row
        for row in methods
        if any(call.startswith("Microsoft.Office.Interop.Excel.") for call in row["calls"])
    ]
    process_kill_methods = [
        row for row in methods if "System.Diagnostics.Process.Kill" in row["calls"]
    ]
    errors = []
    if hash_mismatches:
        errors.append("source package hash mismatch")
    if not target["found"]:
        errors.append("target form type missing")
    if missing:
        errors.append("selected import method coverage incomplete")
    if analysis["method_body_error_count"]:
        errors.append("target method body parse failure")

    artifact = {
        "artifact": "varanegar_bank_statement_import_parser_file_and_office_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_TARGETED_IL_IMPORT_AND_FILE_SIDE_EFFECT_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "files_created_deleted_or_opened": 0,
            "office_processes_started_or_killed": 0,
            "string_literal_or_config_payload_values_persisted": 0,
        },
        "source": {
            "assembly": ASSEMBLY,
            "form_type": FORM_TYPE,
            "sha256": actual_hash,
            "inventory_sha256_match": not hash_mismatches,
        },
        "summary": {
            "selected_method_contract_count": len(methods),
            "missing_selected_method_count": len(missing),
            "ole_db_import_method_count": len(ole_db_methods),
            "file_write_or_delete_method_count": len(file_side_effect_methods),
            "office_automation_method_count": len(office_methods),
            "process_kill_method_count": len(process_kill_methods),
            "source_hash_mismatch_count": len(hash_mismatches),
            "method_body_error_count": analysis["method_body_error_count"],
            "validation_error_count": len(errors),
        },
        "methods": sorted(methods, key=lambda row: row["method"]),
        "legacy_boundary_findings": [
            {
                "boundary": "DBF_TXT_XLS_IMPORT",
                "evidence": "three parser methods construct OleDbConnection/OleDbCommand and fill DataTable",
                "security_classification": "DYNAMIC_PROVIDER_AND_QUERY_BOUNDARY_REQUIRES_ISOLATION",
            },
            {
                "boundary": "SCHEMA_FILE",
                "evidence": "WriteSchemaFile creates/deletes a file and writes lines",
                "security_classification": "LEGACY_FILESYSTEM_SIDE_EFFECT_NOT_A_WEB_CONTRACT",
            },
            {
                "boundary": "EXCEL_CONVERSION",
                "evidence": "SaveAsExcel automates Excel, copies/deletes files and calls Process.Kill",
                "security_classification": "DESKTOP_AUTOMATION_AND_BROAD_PROCESS_SIDE_EFFECT",
            },
            {
                "boundary": "IMPORT_DISPATCH",
                "evidence": "btnAccept references FormatExtension, HDR, SchemaFile and SQLStatement before dispatching parsers",
                "security_classification": "CONFIG_DRIVEN_IMPORT_BEHAVIOR_REQUIRES_ALLOWLIST_AND_VERSIONING",
            },
        ],
        "target_contract": {
            "aggregate": "BankReconciliationSession",
            "accepted_format_profiles": ["DBF", "TXT", "XLS_LEGACY"],
            "arbitrary_provider_or_query_execution_allowed": False,
            "desktop_office_automation_allowed": False,
            "arbitrary_process_kill_allowed": False,
            "arbitrary_path_write_allowed": False,
            "direct_import_to_accounting_ledger_allowed": False,
            "required_pipeline": [
                "upload_to_isolated_object_store",
                "size_type_and_signature_validation",
                "versioned_bank_format_profile_lookup",
                "sandboxed_parser_without_office_automation",
                "canonical_row_staging",
                "schema_amount_date_and_duplicate_validation",
                "quarantine_or_preview",
                "idempotent_import_commit",
                "separate_match_and_confirm_commands",
            ],
            "config_profile_rules": [
                "bank format profiles are versioned and approved",
                "query templates are server-owned allowlisted templates rather than raw client input",
                "file paths and provider strings are never accepted from the browser as executable configuration",
            ],
        },
        "missing_selected_methods": missing,
        "source_hash_mismatches": hash_mismatches,
        "method_body_errors": analysis["method_body_errors"],
        "validation_errors": errors,
        "limits": [
            "Call presence proves a boundary, not an exploitable injection or an observed malicious file.",
            "No provider string, SQLStatement value, file path, file content or business row was persisted.",
            "Static IL does not prove the exact format branch, parser result quality or commit outcome.",
            "No assembly, file, Office process, form, database or application command was opened or executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
