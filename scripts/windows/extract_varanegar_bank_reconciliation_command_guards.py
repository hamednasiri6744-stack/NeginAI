"""Extract permission, validation and transaction guards for bank reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile  # noqa: F401 - the delegated IL parser uses the same metadata dependency

from extract_varanegar_targeted_il_contracts import _analyze_assembly


ASSEMBLY = "TreasuryOld.Forms.dll"
TARGET_METHODS = {
    "TreasuryOld.Forms.frmBankReconciliation": set(),
    "TreasuryOld.Forms.frmBankReconciliationList": {"SetFormPermission"},
    "TreasuryOld.Forms.frmReconciliation": {
        "AddNewReconcileItem",
        "btnDelete_Click",
    },
    "TreasuryOld.Forms.frmReconciliationSetup": {
        "AddNewBankBill",
        "AddNewReconcile",
        "DataIsValid",
        "SaveData",
        "SetFormPermission",
        "btnAccept_Click",
        "btnDelete_Click",
    },
}
BUSINESS_CALL_PREFIXES = (
    "TreasuryOld.",
    "TransferList.",
    "ReconciliationSetup.",
    "Question.",
    "Error.",
)
FORM_FIELD_PREFIX = "TreasuryOld.Forms."


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

    analysis = _analyze_assembly(source, set(TARGET_METHODS))
    contracts = []
    found_types = set()
    found_methods: set[tuple[str, str]] = set()
    for type_row in analysis["target_types"]:
        form_type = type_row["type"]
        if type_row["found"]:
            found_types.add(form_type)
        selected = TARGET_METHODS[form_type]
        for method in type_row["methods"]:
            if method["method"] not in selected:
                continue
            found_methods.add((form_type, method["method"]))
            contracts.append(
                {
                    "form_type": form_type,
                    "method": method["method"],
                    "instruction_count": method["instruction_count"],
                    "business_calls": sorted(
                        call
                        for call in method["calls"]
                        if call.startswith(BUSINESS_CALL_PREFIXES)
                    ),
                    "referenced_fields": sorted(
                        field
                        for field in method["referenced_fields"]
                        if field.startswith(FORM_FIELD_PREFIX)
                    ),
                    "string_literal_values_persisted": 0,
                }
            )

    required_methods = {
        (form_type, method)
        for form_type, methods in TARGET_METHODS.items()
        for method in methods
    }
    missing_methods = sorted(
        {"form_type": form_type, "method": method}
        for form_type, method in required_methods - found_methods
    )
    errors = []
    if hash_mismatches:
        errors.append("source package hash mismatch")
    if found_types != set(TARGET_METHODS):
        errors.append("target form type coverage incomplete")
    if missing_methods:
        errors.append("selected method coverage incomplete")
    if analysis["method_body_error_count"]:
        errors.append("method body parse failure")

    artifact = {
        "artifact": "varanegar_bank_reconciliation_command_guard_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_TARGETED_IL_METHOD_CONTRACT_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "business_row_values_read_or_persisted": 0,
            "string_literal_or_config_payload_values_persisted": 0,
        },
        "source": {
            "assembly": ASSEMBLY,
            "sha256": actual_hash,
            "inventory_sha256_match": not hash_mismatches,
        },
        "summary": {
            "target_form_type_count": len(TARGET_METHODS),
            "found_form_type_count": len(found_types),
            "selected_method_contract_count": len(contracts),
            "missing_selected_method_count": len(missing_methods),
            "source_hash_mismatch_count": len(hash_mismatches),
            "method_body_error_count": analysis["method_body_error_count"],
            "validation_error_count": len(errors),
        },
        "method_contracts": sorted(
            contracts, key=lambda row: (row["form_type"], row["method"])
        ),
        "target_contract": {
            "aggregate": "BankReconciliationSession",
            "direct_table_crud_allowed": False,
            "permission_alias_copy_allowed": False,
            "authorization_layers": [
                {
                    "surface": "reconciliation_list",
                    "observed_permission_alias": "TransferList",
                    "observed_capability_getters": ["AddNew", "Edit", "Delete"],
                    "operation_date_closed_gate_observed": True,
                    "target_rule": "map to named bank-reconciliation capabilities after authenticated parity; do not reuse the legacy alias blindly",
                },
                {
                    "surface": "reconciliation_setup",
                    "observed_permission_alias": "ReconciliationSetup",
                    "observed_capability_getters": ["Edit", "Delete"],
                    "operation_date_closed_gate_observed": False,
                    "target_rule": "separate import/edit/delete permissions and combine them with fiscal, account and operation-date scope",
                },
            ],
            "required_input_candidates": [
                "bank_account",
                "bank_date",
                "bank_file",
            ],
            "import_dispatch_candidates": [
                "getDataFromDBF",
                "getDataFromTXT",
                "getDataFromXLS",
                "WriteSchemaFile",
            ],
            "transaction_boundaries": [
                {
                    "command": "delete_reconciliation_item",
                    "ui_layer_start_commit_rollback_observed": True,
                },
                {
                    "command": "import_and_save_reconciliation",
                    "ui_layer_start_commit_rollback_observed": False,
                    "target_gate": "service transaction owner must be explicit before implementation-ready",
                },
            ],
            "delete_reconciliation_candidate": {
                "confirmation_call_observed": True,
                "loads_bank_bills_and_reconciliation_items": True,
                "target_gate": "define aggregate cascade, idempotency and reconciliation before enabling",
            },
        },
        "missing_selected_methods": missing_methods,
        "source_hash_mismatches": hash_mismatches,
        "method_body_errors": analysis["method_body_errors"],
        "validation_errors": errors,
        "limits": [
            "Permission getter presence does not prove the exact runtime boolean branch or an authenticated role outcome.",
            "The TransferList alias is observed reuse and is not a recommended target capability name.",
            "Static IL does not prove parser result quality, database commit success or rollback completeness.",
            "No assembly, form, application command, procedure or trigger was executed.",
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
