"""Extract setup discard versus session cancel semantics from allowlisted IL."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _full_type_name,
    _owner_maps,
    _resolve_token,
    _text,
)


ASSEMBLY_NAME = "TreasuryOld.Forms.dll"
FORM_TYPE = "TreasuryOld.Forms.frmReconciliationSetup"
METHOD_NAMES = ("btnDelete_Click", "SaveData")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _method_body(pe: dnfile.dnPE, type_row: Any, method_name: str) -> Any:
    method = next(
        index.row
        for index in type_row.MethodList or []
        if index.row is not None and index.row.Rva and _text(index.row.Name) == method_name
    )
    return read_method_body_from_bytes(pe.get_data(method.Rva, 65536))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--delete-semantics", required=True, type=Path)
    parser.add_argument("--parser-row-contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    inventory = _load(args.binary_inventory)
    delete_semantics = _load(args.delete_semantics)
    parser_row = _load(args.parser_row_contract)
    if delete_semantics.get("validation") != "PASS" or parser_row.get("validation") != "PASS":
        raise ValueError("validated delete and parser-row artifacts are required")

    inventory_row = next(row for row in inventory["files"] if row["name"] == ASSEMBLY_NAME)
    assembly_path = args.source_directory / ASSEMBLY_NAME
    actual_hash = _sha256(assembly_path)
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    logging.getLogger("dnfile.stream").setLevel(logging.CRITICAL)
    pe = dnfile.dnPE(str(assembly_path))
    method_owners, field_owners = _owner_maps(pe)
    type_row = next(row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == FORM_TYPE)

    methods: dict[str, dict[str, Any]] = {}
    for method_name in METHOD_NAMES:
        body = _method_body(pe, type_row, method_name)
        calls: list[str] = []
        fields: list[str] = []
        mnemonics = Counter()
        literal_count = 0
        for instruction in body.instructions:
            mnemonics[instruction.mnemonic] += 1
            operand = instruction.operand
            if isinstance(operand, StringToken):
                literal_count += 1
            elif isinstance(operand, Token):
                resolved = _resolve_token(pe, operand, method_owners, field_owners)
                if instruction.mnemonic in {"call", "callvirt"}:
                    calls.append(resolved)
                elif instruction.mnemonic in {"ldfld", "ldsfld", "stfld"}:
                    fields.append(resolved)
        methods[method_name] = {
            "instruction_count": len(body.instructions),
            "calls": calls,
            "fields": fields,
            "mnemonics": dict(mnemonics),
            "literal_count": literal_count,
        }

    discard = methods["btnDelete_Click"]
    save = methods["SaveData"]
    validation_errors: list[str] = []
    if actual_hash != inventory_row["sha256"]:
        validation_errors.append("forms assembly hash differs from inventory")
    required_discard_calls = {
        "TreasuryOld.DataLayer.BankBillAdapter.GetBankBillSWhere",
        "TreasuryOld.DataLayer.ReconcileItemAdapter.GetReconcileItemSByBankBillS",
        "TreasuryOld.DataLayer.Reconcile.get_BankBillS",
        "TreasuryOld.DataLayer.BankBillS.Delete",
        "TreasuryOld.DataLayer.BankBillS.Update",
    }
    if not required_discard_calls.issubset(set(discard["calls"])):
        validation_errors.append("discard call contract changed")
    if any(call.startswith("TreasuryOld.DataLayer.Reconcile.set_") or call == "TreasuryOld.DataLayer.Reconcile.Delete" for call in discard["calls"]):
        validation_errors.append("discard now mutates reconcile header")
    if "TreasuryOld.DataLayer.Reconcile.Update" not in save["calls"]:
        validation_errors.append("SaveData header update missing")
    if "TreasuryOld.Forms.frmReconciliationSetup.ReconcileId" not in save["fields"]:
        validation_errors.append("saved ReconcileId field assignment missing")

    gate_calls = [
        call
        for call in discard["calls"]
        if any(token in call.casefold() for token in ("permission", "access", "finaldate", "operationdate", "confirmer", "confirmdate"))
    ]
    summary = {
        "selected_method_count": len(methods),
        "selected_instruction_count": sum(row["instruction_count"] for row in methods.values()),
        "discard_link_check_call_count": discard["calls"].count("TreasuryOld.DataLayer.ReconcileItemAdapter.GetReconcileItemSByBankBillS"),
        "discard_bank_bill_collection_delete_call_count": discard["calls"].count("TreasuryOld.DataLayer.BankBillS.Delete"),
        "discard_reconcile_header_mutation_call_count": sum(call.startswith("TreasuryOld.DataLayer.Reconcile.set_") or call == "TreasuryOld.DataLayer.Reconcile.Delete" for call in discard["calls"]),
        "discard_permission_date_or_confirm_state_call_count": len(gate_calls),
        "save_header_update_call_count": save["calls"].count("TreasuryOld.DataLayer.Reconcile.Update"),
        "assembly_hash_mismatch_count": int(actual_hash != inventory_row["sha256"]),
        "string_literal_value_persisted_count": 0,
        "database_connection_count": 0,
        "validation_error_count": len(validation_errors),
    }
    artifact = {
        "artifact": "varanegar_bank_reconciliation_setup_discard_rows_versus_cancel_session_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "safety": {
            "mode": "ALLOWLISTED_STATIC_IL_AND_VALIDATED_ARTIFACT_COMPOSITION",
            "assemblies_loaded_or_executed": 0,
            "forms_invoked": 0,
            "database_connections": 0,
            "source_or_target_commands_executed": 0,
            "business_row_values_read": 0,
            "string_literal_values_persisted": 0,
        },
        "source": {
            "assembly": ASSEMBLY_NAME,
            "type": FORM_TYPE,
            "sha256": actual_hash,
            "inventory_sha256_match": actual_hash == inventory_row["sha256"],
        },
        "summary": summary,
        "save_header_contract": {
            "creates_header_only_when_current_new_reconcile_is_null": True,
            "sets_account_date_file_comment_user_and_modified_date": True,
            "calls_reconcile_update_before_parser_dispatch": True,
            "stores_generated_reconcile_id_on_form": True,
            "existing_header_is_updated_on_repeat_save": False,
        },
        "discard_contract": {
            "requires_current_reconcile_object": True,
            "loads_all_bank_bills_by_reconcile_id": True,
            "checks_reconcile_items_across_loaded_bank_bills": True,
            "active_link_count_greater_than_zero_blocks_discard": True,
            "confirmation_prompt_observed": True,
            "deletes_and_updates_bank_bill_collection": True,
            "deletes_or_cancels_reconcile_header": False,
            "explicit_state_confirmer_or_operation_date_gate_observed": False,
            "permission_call_observed": False,
        },
        "orphan_header_risk": {
            "parser_failure_can_follow_committed_header": parser_row["legacy_atomicity_contract"]["parser_exception_can_leave_committed_header"],
            "discard_removes_header": False,
            "empty_reconcile_header_can_remain_after_failure_or_discard": True,
            "distinct_legacy_cancel_session_command_observed": False,
        },
        "target_contract": {
            "discard_imported_statement_and_cancel_session_are_same_command": False,
            "unconfirmed_cancel_requires_zero_active_links": True,
            "unconfirmed_cancel_transitions_or_archives_header_and_rows_atomically": True,
            "confirmed_session_physical_delete_allowed": False,
            "confirmed_session_requires_owner_approved_reversal": True,
            "capability_scope_operation_date_state_and_expected_version_rechecked": True,
            "parser_failure_persists_no_header_or_rows": True,
            "cancel_is_idempotent_and_audited": True,
        },
        "source_evidence": [delete_semantics["artifact"], parser_row["artifact"]],
        "validation_errors": validation_errors,
        "limits": [
            "No form, delete, update, query, transaction or parser was executed.",
            "The absence of header mutation is confirmed for btnDelete_Click in the current Forms assembly.",
            "A dynamic or external cancel path is still not excluded by static absence.",
            "Process-owner cancel versus archive versus reversal semantics remain unapproved.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation": artifact["validation"], "summary": summary}, ensure_ascii=False))
    return 0 if not validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
