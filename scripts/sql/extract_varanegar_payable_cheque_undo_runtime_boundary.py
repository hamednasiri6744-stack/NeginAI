"""Extract hash-pinned static IL for payable-cheque UndoStatus."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken, Token

WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
sys.path.insert(0, str(WINDOWS_SCRIPTS))
from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _full_type_name,
    _owner_maps,
    _resolve_token,
)


TARGETS = {
    "TreasuryOld.Forms.dll": {
        "TreasuryOld.Forms.frmPChequeTracking": {"UndoStatus", "CanDoUndo"},
        "TreasuryOld.Forms.frmPChequeTrackingNew": {"UndoStatus", "CanDoUndo"},
    },
    "TreasuryOld.DataAccess.dll": {
        "TreasuryOld.DataLayer.PChequeAdapter": {"DeleteLastPChequeHistory"},
    },
}

SAFE_MEMBERS = {
    "TreasuryOld.Forms.frmPChequeTracking.CanDoUndo",
    "TreasuryOld.DataLayer.Transaction.Start",
    "TreasuryOld.DataLayer.Transaction.Commit",
    "TreasuryOld.DataLayer.Transaction.RollBack",
    "TreasuryOld.DataLayer.PChequeAdapter.DeleteLastPChequeHistory",
    "TreasuryOld.DataLayer.PayAdapter.CreateApprovePChequeHistory",
    "TreasuryOld.DataLayer.PCheque.Refresh",
    "TreasuryOld.DataLayer.PChequeHistoryS.Refresh",
    "TreasuryOld.DataLayer.PCheque.get_PChequeHistoryS",
    "TreasuryOld.DataLayer.PChequeHistoryS.get_Count",
    "System.Data.Common.DbCommand.ExecuteNonQuery",
    "System.Data.SqlClient.SqlCommand.set_Transaction",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _method(
    pe: dnfile.dnPE,
    assembly: str,
    owner: str,
    index: Any,
    method_owners: dict[int, str],
    field_owners: dict[int, str],
) -> dict[str, Any]:
    row = index.row
    body = read_method_body_from_bytes(pe.get_data(row.Rva, 131072))
    events = []
    literals = []
    for instruction in body.instructions:
        operand = instruction.operand
        if isinstance(operand, StringToken):
            item = pe.net.user_strings.get(operand.rid)
            value = "" if item is None else str(item.value)
            literals.append(
                {
                    "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                    "length": len(value),
                    "raw_value_persisted": False,
                }
            )
        elif isinstance(operand, Token):
            member = _resolve_token(pe, operand, method_owners, field_owners)
            if member in SAFE_MEMBERS:
                events.append(
                    {
                        "offset": int(instruction.offset),
                        "opcode": instruction.mnemonic,
                        "member": member,
                    }
                )
    return {
        "assembly_file": assembly,
        "type": owner,
        "method": str(row.Name),
        "instruction_count": len(body.instructions),
        "has_exception_regions": bool(body.exception_handlers),
        "event_ledger": events,
        "literal_fingerprints": literals,
    }


def _offsets(method: dict[str, Any] | None, member: str) -> list[int]:
    if method is None:
        return []
    return [row["offset"] for row in method["event_ledger"] if row["member"] == member]


def collect(source_directory: Path, binary_inventory: Path) -> dict[str, Any]:
    inventory = _load(binary_inventory)
    expected = {row["name"]: row["sha256"] for row in inventory["files"]}
    sources = []
    methods = []
    errors = []
    for assembly, type_targets in TARGETS.items():
        path = source_directory / assembly
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        match = actual == expected.get(assembly)
        sources.append(
            {
                "assembly_file": assembly,
                "assembly_bytes": path.stat().st_size,
                "assembly_sha256": actual,
                "inventory_sha256_match": match,
            }
        )
        if not match:
            errors.append({"assembly_file": assembly, "error": "inventory hash mismatch"})
        pe = dnfile.dnPE(str(path))
        method_owners, field_owners = _owner_maps(pe)
        types = {_full_type_name(row): row for row in pe.net.mdtables.TypeDef.rows}
        for owner, selected in type_targets.items():
            type_row = types.get(owner)
            if type_row is None:
                errors.append({"assembly_file": assembly, "type": owner, "error": "type absent"})
                continue
            found = set()
            for index in type_row.MethodList or []:
                row = index.row
                if row is None or not row.Rva or str(row.Name) not in selected:
                    continue
                found.add(str(row.Name))
                try:
                    methods.append(
                        _method(
                            pe,
                            assembly,
                            owner,
                            index,
                            method_owners,
                            field_owners,
                        )
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "assembly_file": assembly,
                            "type": owner,
                            "method": str(row.Name),
                            "error": type(exc).__name__,
                        }
                    )
            for missing in selected - found:
                errors.append(
                    {"assembly_file": assembly, "type": owner, "method": missing, "error": "method absent"}
                )
    by_key = {(row["type"], row["method"]): row for row in methods}
    old_undo = by_key.get(("TreasuryOld.Forms.frmPChequeTracking", "UndoStatus"))
    old_can = by_key.get(("TreasuryOld.Forms.frmPChequeTracking", "CanDoUndo"))
    new_undo = by_key.get(("TreasuryOld.Forms.frmPChequeTrackingNew", "UndoStatus"))
    new_can = by_key.get(("TreasuryOld.Forms.frmPChequeTrackingNew", "CanDoUndo"))
    adapter = by_key.get(
        ("TreasuryOld.DataLayer.PChequeAdapter", "DeleteLastPChequeHistory")
    )
    if not all((old_undo, old_can, new_undo, new_can, adapter)):
        errors.append({"error": "selected runtime coverage incomplete"})

    start = _offsets(old_undo, "TreasuryOld.DataLayer.Transaction.Start")
    delete = _offsets(
        old_undo, "TreasuryOld.DataLayer.PChequeAdapter.DeleteLastPChequeHistory"
    )
    approve = _offsets(
        old_undo, "TreasuryOld.DataLayer.PayAdapter.CreateApprovePChequeHistory"
    )
    commit = _offsets(old_undo, "TreasuryOld.DataLayer.Transaction.Commit")
    adapter_start = _offsets(adapter, "TreasuryOld.DataLayer.Transaction.Start")
    adapter_execute = _offsets(adapter, "System.Data.Common.DbCommand.ExecuteNonQuery")
    adapter_commit = _offsets(adapter, "TreasuryOld.DataLayer.Transaction.Commit")
    contract = {
        "legacy_undo_checks_can_do_undo": bool(
            _offsets(old_undo, "TreasuryOld.Forms.frmPChequeTracking.CanDoUndo")
        ),
        "legacy_undo_starts_transaction_before_delete_call": bool(
            start and delete and min(start) < min(delete)
        ),
        "legacy_undo_delete_call_precedes_optional_reapprove_signal": bool(
            delete and approve and min(delete) < min(approve)
        ),
        "legacy_undo_has_rollback_signal": bool(
            _offsets(old_undo, "TreasuryOld.DataLayer.Transaction.RollBack")
        ),
        "legacy_undo_commit_follows_delete_in_linear_il": bool(
            delete and commit and min(delete) < min(commit)
        ),
        "legacy_undo_refreshes_cheque_and_history_after_mutation": bool(
            _offsets(old_undo, "TreasuryOld.DataLayer.PCheque.Refresh")
            and _offsets(old_undo, "TreasuryOld.DataLayer.PChequeHistoryS.Refresh")
        ),
        "legacy_can_undo_reads_history_count": bool(
            _offsets(old_can, "TreasuryOld.DataLayer.PChequeHistoryS.get_Count")
        ),
        "new_tracking_undo_method_is_one_instruction_stub": bool(
            new_undo and new_undo["instruction_count"] == 1
        ),
        "new_can_undo_reads_history_count": bool(
            _offsets(new_can, "TreasuryOld.DataLayer.PChequeHistoryS.get_Count")
        ),
        "adapter_starts_nested_transaction_before_execute": bool(
            adapter_start and adapter_execute and min(adapter_start) < min(adapter_execute)
        ),
        "adapter_execute_precedes_nested_commit": bool(
            adapter_execute and adapter_commit and min(adapter_execute) < min(adapter_commit)
        ),
        "adapter_has_rollback_signal": bool(
            _offsets(adapter, "TreasuryOld.DataLayer.Transaction.RollBack")
        ),
        "branch_specific_reapprove_and_rollback_reachability_proven": False,
        "new_tracking_form_runtime_selection_proven": False,
    }
    return {
        "artifact": "varanegar_payable_cheque_undo_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "application_endpoint_form_or_command_executions": 0,
            "database_connections": 0,
            "configuration_cheque_bank_leaf_history_or_operator_values_read": 0,
            "raw_string_or_sql_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "assembly_count": len(sources),
            "selected_method_count": len(methods),
            "selected_instruction_count": sum(row["instruction_count"] for row in methods),
            "source_hash_mismatch_count": sum(
                not row["inventory_sha256_match"] for row in sources
            ),
            "method_or_coverage_error_count": len(errors),
        },
        "managed_undo_contract": contract,
        "method_contracts": methods,
        "errors": errors,
        "evidence_limits": [
            "Linear IL order does not prove branch-specific execution, optional reapproval or rollback outcomes.",
            "The one-instruction new-form UndoStatus method does not prove which form is selected for every user or permission set.",
            "Nested legacy Transaction calls are static signals; physical transaction enlistment is not re-proven in this artifact.",
            "Assemblies were never loaded or executed and no raw literal or financial identifier was persisted.",
        ],
    }


def main() -> int:
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect(args.source_directory, args.binary_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(json.dumps(payload["managed_undo_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
