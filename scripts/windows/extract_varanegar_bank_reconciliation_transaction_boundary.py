"""Extract nested legacy transaction semantics around bank reconciliation confirm."""

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
    _analyze_assembly,
    _full_type_name,
    _owner_maps,
    _resolve_token,
)


FORM_ASSEMBLY = "TreasuryOld.Forms.dll"
DATA_ASSEMBLY = "TreasuryOld.DataAccess.dll"
FORM_TYPE = "TreasuryOld.Forms.frmReconciliation"
DATA_TYPES = {
    "TreasuryOld.DataLayer.Reconcile",
    "TreasuryOld.DataLayer.ReconcileAdapter",
    "TreasuryOld.DataLayer.Transaction",
}
TRANSACTION_TYPE = "TreasuryOld.DataLayer.Transaction"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _transaction_metadata(path: Path) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    pe = dnfile.dnPE(str(path))
    method_owners, field_owners = _owner_maps(pe)
    transaction_type = next(
        row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == TRANSACTION_TYPE
    )
    transaction_fields = {
        id(index.row): index.row for index in (transaction_type.FieldList or []) if index.row
    }
    thread_static_field_ids = set()
    attributes = getattr(pe.net.mdtables, "CustomAttribute", None)
    for attribute in ([] if not attributes else attributes.rows):
        parent = getattr(getattr(attribute, "Parent", None), "row", None)
        if id(parent) not in transaction_fields:
            continue
        constructor = getattr(getattr(attribute, "Type", None), "row", None)
        owner = getattr(getattr(constructor, "Class", None), "row", None)
        if owner is not None and _full_type_name(owner).endswith("ThreadStaticAttribute"):
            thread_static_field_ids.add(id(parent))

    fields = [
        {
            "field_name": str(row.Name),
            "static": bool(row.Flags.fdStatic),
            "thread_static_attribute_observed": id(row) in thread_static_field_ids,
            "field_value_or_connection_string_persisted": False,
        }
        for row in transaction_fields.values()
    ]
    instructions: dict[str, list[dict[str, Any]]] = {}
    for method_index in transaction_type.MethodList or []:
        method = method_index.row
        if method is None or not method.Rva or str(method.Name) not in {"Start", "Commit", "RollBack"}:
            continue
        body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
        rows = []
        for instruction in body.instructions:
            operand = instruction.operand
            if isinstance(operand, Token):
                safe_operand = _resolve_token(pe, operand, method_owners, field_owners)
            elif isinstance(operand, StringToken):
                safe_operand = "STRING_LITERAL_OMITTED"
            elif operand is None:
                safe_operand = None
            else:
                safe_operand = str(operand)
            rows.append(
                {
                    "offset": int(instruction.offset),
                    "opcode": instruction.mnemonic,
                    "safe_operand": safe_operand,
                }
            )
        instructions[str(method.Name)] = rows
    return sorted(fields, key=lambda row: row["field_name"]), instructions


def _has_call(method: dict[str, Any], call: str) -> bool:
    return call in method["calls"]


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
    source_paths = {
        FORM_ASSEMBLY: args.source_directory / FORM_ASSEMBLY,
        DATA_ASSEMBLY: args.source_directory / DATA_ASSEMBLY,
    }
    actual_hashes = {
        name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in source_paths.items()
    }
    hash_mismatches = [
        name for name, actual in actual_hashes.items() if actual != expected_hash.get(name)
    ]

    form_analysis = _analyze_assembly(source_paths[FORM_ASSEMBLY], {FORM_TYPE})
    data_analysis = _analyze_assembly(source_paths[DATA_ASSEMBLY], DATA_TYPES)
    form_row = form_analysis["target_types"][0]
    data_by_type = {row["type"]: row for row in data_analysis["target_types"]}

    methods = []
    do_accept = next(row for row in form_row["methods"] if row["method"] == "DoAccept")
    methods.append({"type": FORM_TYPE, **{key: value for key, value in do_accept.items() if key != "string_literals"}})
    reconcile_update = next(
        row
        for row in data_by_type["TreasuryOld.DataLayer.Reconcile"]["methods"]
        if row["method"] == "Update"
        and _has_call(row, "TreasuryOld.DataLayer.Transaction.Start")
    )
    methods.append(
        {"type": "TreasuryOld.DataLayer.Reconcile", **{key: value for key, value in reconcile_update.items() if key != "string_literals"}}
    )
    cardex = next(
        row
        for row in data_by_type["TreasuryOld.DataLayer.ReconcileAdapter"]["methods"]
        if row["method"] == "UpdateBankAccountCardex"
    )
    methods.append(
        {"type": "TreasuryOld.DataLayer.ReconcileAdapter", **{key: value for key, value in cardex.items() if key != "string_literals"}}
    )
    for method_name in ("Start", "Commit", "RollBack"):
        row = next(
            item
            for item in data_by_type[TRANSACTION_TYPE]["methods"]
            if item["method"] == method_name
        )
        methods.append(
            {"type": TRANSACTION_TYPE, **{key: value for key, value in row.items() if key != "string_literals"}}
        )

    transaction_fields, instruction_evidence = _transaction_metadata(source_paths[DATA_ASSEMBLY])
    start_ops = [row["opcode"] for row in instruction_evidence["Start"]]
    commit_ops = [row["opcode"] for row in instruction_evidence["Commit"]]
    rollback_ops = [row["opcode"] for row in instruction_evidence["RollBack"]]
    start_only_zero = (
        "brtrue.s" in start_ops
        and any(row["safe_operand"] == "System.Data.SqlClient.SqlConnection.BeginTransaction" for row in instruction_evidence["Start"])
        and "add" in start_ops
    )
    commit_only_one = (
        "bne.un.s" in commit_ops
        and any(row["safe_operand"] == "System.Data.Common.DbTransaction.Commit" for row in instruction_evidence["Commit"])
        and "sub" in commit_ops
    )
    rollback_to_zero = (
        "ldc.i4.0" in rollback_ops
        and any(row["safe_operand"] == "TreasuryOld.DataLayer.Transaction.TransactionLevel" and row["opcode"] == "stsfld" for row in instruction_evidence["RollBack"])
        and any(row["safe_operand"] == "System.Data.Common.DbTransaction.Rollback" for row in instruction_evidence["RollBack"])
    )
    method_errors = form_analysis["method_body_errors"] + data_analysis["method_body_errors"]
    errors = []
    if hash_mismatches:
        errors.append("source package hash mismatch")
    if len(methods) != 6:
        errors.append("selected transaction method coverage incomplete")
    if len(transaction_fields) != 4 or not all(row["static"] for row in transaction_fields):
        errors.append("legacy transaction static field contract changed")
    if any(row["thread_static_attribute_observed"] for row in transaction_fields):
        errors.append("thread-static transaction evidence changed")
    if not (start_only_zero and commit_only_one and rollback_to_zero):
        errors.append("nested transaction counter semantics changed")
    if method_errors:
        errors.append("target method body parse failure")

    artifact = {
        "artifact": "varanegar_bank_reconciliation_nested_static_transaction_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "safety": {
            "mode": "READ_ONLY_TARGETED_IL_AND_FIELD_ATTRIBUTE_TRANSACTION_PARSE",
            "assemblies_loaded_or_executed": 0,
            "database_connections": 0,
            "network_writes": 0,
            "live_ui_actions": 0,
            "application_commands_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "string_literal_or_connection_string_values_persisted": 0,
        },
        "summary": {
            "selected_method_contract_count": len(methods),
            "static_transaction_field_count": sum(row["static"] for row in transaction_fields),
            "thread_static_transaction_field_count": sum(row["thread_static_attribute_observed"] for row in transaction_fields),
            "source_hash_mismatch_count": len(hash_mismatches),
            "method_body_error_count": len(method_errors),
            "validation_error_count": len(errors),
        },
        "source_hashes": actual_hashes,
        "method_contracts": methods,
        "transaction_fields": transaction_fields,
        "transaction_instruction_evidence": instruction_evidence,
        "legacy_transaction_semantics": {
            "outer_confirm_scope": "TreasuryOld.Forms.frmReconciliation.DoAccept",
            "outer_scope_calls_reconcile_update_and_cardex_update": True,
            "reconcile_update_starts_and_commits_nested_scope": True,
            "cardex_update_starts_and_commits_nested_scope": True,
            "start_opens_physical_transaction_only_when_level_zero": start_only_zero,
            "commit_physically_commits_only_when_level_one": commit_only_one,
            "rollback_resets_level_to_zero_and_rolls_back_physical_transaction": rollback_to_zero,
            "nested_data_layer_calls_share_static_transaction_state": True,
            "web_concurrency_safety_proven": False,
        },
        "target_contract": {
            "command": "bank_reconciliation.confirm",
            "single_application_service_transaction_owner_required": True,
            "static_connection_transaction_or_nesting_counter_allowed": False,
            "repository_level_commit_allowed": False,
            "repositories_enlist_in_request_scoped_unit_of_work": True,
            "confirm_state_cardex_audit_and_outbox_share_one_local_transaction": True,
            "fault_injection_required_after": [
                "reconcile state write",
                "cardex update",
                "audit append",
                "outbox append",
                "physical commit before response",
            ],
        },
        "source_hash_mismatches": hash_mismatches,
        "method_body_errors": method_errors,
        "validation_errors": errors,
        "limits": [
            "Static fields without ThreadStatic are process-wide metadata evidence; desktop runtime interleaving was not observed.",
            "The target risk is architectural if the pattern is copied into concurrent web requests; no target implementation exists yet.",
            "Stored command SQL text and connection-string values were not read or persisted.",
            "No assembly, database, form, transaction, command or business row was executed.",
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
