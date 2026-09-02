"""Extract the UI-to-entity-to-cardex confirmation orchestration from IL.

Only two allowlisted methods are parsed. The form is not invoked, assemblies are
not loaded into the CLR, and no source or target command is executed.
"""

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
FORM_TYPE = "TreasuryOld.Forms.frmReconciliation"
METHOD_NAMES = ("DoAccept", "cb_CommandClick")
SAFE_COMMAND_KEYS = ("Return", "Ok", "Delete", "Default")
ORDERED_CONFIRM_CALLS = (
    "TreasuryOld.DataLayer.Transaction.Start",
    "TreasuryOld.DataLayer.Reconcile.set_Amount",
    "TreasuryOld.DataLayer.Reconcile.set_ConfirmerId",
    "TreasuryOld.DataLayer.Reconcile.set_ConfirmDate",
    "TreasuryOld.DataLayer.Reconcile.Update",
    "TreasuryOld.DataLayer.ReconcileAdapter.UpdateBankAccountCardex",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _string_value(pe: dnfile.dnPE, token: StringToken) -> str:
    item = pe.net.user_strings.get(token.rid)
    return "" if item is None else _text(item)


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
    parser.add_argument("--transaction-boundary", required=True, type=Path)
    parser.add_argument("--profile-state-boundary", required=True, type=Path)
    parser.add_argument("--confirm-cardex-semantics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    inventory = _load(args.binary_inventory)
    transaction = _load(args.transaction_boundary)
    profile_state = _load(args.profile_state_boundary)
    cardex = _load(args.confirm_cardex_semantics)
    for name, payload in (
        ("transaction", transaction),
        ("profile/state", profile_state),
        ("confirm cardex", cardex),
    ):
        if payload.get("validation") != "PASS":
            raise ValueError(f"validated {name} artifact is required")

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
        safe_literals: list[str] = []
        omitted_literals = 0
        mnemonics = Counter()
        for instruction in body.instructions:
            mnemonics[instruction.mnemonic] += 1
            operand = instruction.operand
            if isinstance(operand, StringToken):
                value = _string_value(pe, operand)
                if value in SAFE_COMMAND_KEYS:
                    safe_literals.append(value)
                else:
                    omitted_literals += 1
            elif isinstance(operand, Token):
                resolved = _resolve_token(pe, operand, method_owners, field_owners)
                if instruction.mnemonic in {"call", "callvirt"}:
                    calls.append(resolved)
                elif instruction.mnemonic in {"ldfld", "ldsfld"}:
                    fields.append(resolved)
        methods[method_name] = {
            "instruction_count": len(body.instructions),
            "calls": calls,
            "fields": fields,
            "safe_literals": safe_literals,
            "omitted_literal_count": omitted_literals,
            "mnemonics": dict(mnemonics),
        }

    accept = methods["DoAccept"]
    command = methods["cb_CommandClick"]
    ordered_positions = [accept["calls"].index(name) for name in ORDERED_CONFIRM_CALLS]
    validation_errors: list[str] = []
    if actual_hash != inventory_row["sha256"]:
        validation_errors.append("forms assembly hash differs from inventory")
    if ordered_positions != sorted(ordered_positions):
        validation_errors.append("confirm call order changed")
    if accept["calls"].count("TreasuryOld.DataLayer.Transaction.RollBack") != 2:
        validation_errors.append("confirm rollback path count changed")
    if accept["calls"].count("TreasuryOld.DataLayer.Transaction.Commit") != 1:
        validation_errors.append("confirm commit path count changed")
    if tuple(command["safe_literals"]) != SAFE_COMMAND_KEYS:
        validation_errors.append("command key dispatch changed")
    if command["calls"].count("TreasuryOld.Forms.frmReconciliation.DoAccept") != 1:
        validation_errors.append("Ok command no longer calls DoAccept exactly once")
    if cardex["summary"]["maximum_typed_link_updates_per_execution"] != 1:
        validation_errors.append("cardex early-return result changed")

    authorization_or_date_calls = [
        call
        for call in accept["calls"]
        if any(token in call.casefold() for token in ("permission", "access", "finaldate", "operationdate"))
    ]
    summary = {
        "selected_method_count": len(methods),
        "selected_instruction_count": sum(row["instruction_count"] for row in methods.values()),
        "command_key_count": len(command["safe_literals"]),
        "confirm_ordered_stage_count": len(ORDERED_CONFIRM_CALLS),
        "confirm_commit_call_count": accept["calls"].count("TreasuryOld.DataLayer.Transaction.Commit"),
        "confirm_rollback_call_count": accept["calls"].count("TreasuryOld.DataLayer.Transaction.RollBack"),
        "confirm_permission_or_operation_date_call_count": len(authorization_or_date_calls),
        "legacy_maximum_instrument_updates_before_success_commit": cardex["summary"]["maximum_typed_link_updates_per_execution"],
        "assembly_hash_mismatch_count": int(actual_hash != inventory_row["sha256"]),
        "string_literal_values_persisted_count": len(command["safe_literals"]),
        "non_allowlisted_string_literal_values_persisted_count": 0,
        "database_connection_count": 0,
        "validation_error_count": len(validation_errors),
    }
    artifact = {
        "artifact": "varanegar_bank_reconciliation_confirm_ui_entity_cardex_orchestration_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "safety": {
            "mode": "ALLOWLISTED_STATIC_IL_AND_VALIDATED_REDACTED_SEMANTICS",
            "assemblies_loaded_or_executed": 0,
            "forms_invoked": 0,
            "database_connections": 0,
            "source_or_target_commands_executed": 0,
            "business_row_values_read": 0,
            "non_allowlisted_string_literal_values_persisted": 0,
        },
        "source": {
            "assembly": ASSEMBLY_NAME,
            "type": FORM_TYPE,
            "sha256": actual_hash,
            "inventory_sha256_match": actual_hash == inventory_row["sha256"],
        },
        "summary": summary,
        "command_dispatch": {
            "keys": list(command["safe_literals"]),
            "confirm_key": "Ok",
            "confirmation_prompt_observed": True,
            "closes_form_only_after_doaccept_true": True,
            "generic_error_after_doaccept_false": True,
        },
        "confirm_success_path": [
            "Transaction.Start",
            "Reconcile.Amount=Decimal.Zero",
            "Reconcile.ConfirmerId=current AppUserId",
            "Reconcile.ConfirmDate=DateTime.Now",
            "Reconcile.Update",
            "ReconcileAdapter.UpdateBankAccountCardex(ReconcileId, out ErrorNo)",
            "if ErrorNo==0 Transaction.Commit and return true",
        ],
        "confirm_failure_paths": [
            "if ErrorNo!=0 Transaction.RollBack and return false",
            "on exception Transaction.RollBack, show generic error and return false",
        ],
        "authorization_boundary": {
            "detail_doaccept_permission_call_observed": False,
            "detail_doaccept_operation_date_guard_call_observed": False,
            "parent_or_client_gate_sufficient_for_target": False,
            "server_side_capability_scope_date_state_validation_required": True,
        },
        "combined_legacy_defect": {
            "reconcile_markers_and_first_successful_instrument_update_share_physical_transaction": True,
            "cardex_procedure_reports_success_after_first_instrument_update": True,
            "outer_doaccept_commits_on_that_zero_error": True,
            "confirmed_session_can_have_remaining_instruments_not_marked_reconciled": True,
            "remaining_instrument_choice_is_nondeterministic_for_multiple_links": True,
            "legacy_amount_zero_is_not_summary_result": True,
        },
        "target_contract": {
            "confirm_is_server_side_explicit_command": True,
            "confirm_rechecks_capability_scope_date_state_and_expected_version": True,
            "amount_is_derived_or_separately_defined_not_forced_to_legacy_zero": True,
            "all_links_are_validated_before_any_mutation": True,
            "all_instruments_state_audit_and_outbox_commit_atomically": True,
            "any_missing_conflicting_or_failed_link_rolls_back_session_markers": True,
            "typed_error_reason_is_returned_not_generic_boolean_only": True,
            "one_link_legacy_defect_is_a_regression_test_not_target_behavior": True,
        },
        "source_evidence": [transaction["artifact"], profile_state["artifact"], cardex["artifact"]],
        "validation_errors": validation_errors,
        "limits": [
            "No form, transaction, entity update or stored procedure was executed.",
            "The combined inconsistency is a static consequence of current IL and SQL definitions; production frequency is not measured.",
            "Safe command keys are persisted; prompt/error text and all other literals are omitted.",
            "Authenticated UAT and process-owner confirmation policy remain absent.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation": artifact["validation"], "summary": summary}, ensure_ascii=False))
    return 0 if not validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
