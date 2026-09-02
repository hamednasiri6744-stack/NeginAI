"""Extract hash-pinned static IL for received-cheque DoUndo."""

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
        "TreasuryOld.Forms.frmRChequeTracking": {"DoUndo", "CanDoUndo"},
        "TreasuryOld.Forms.frmRChequeTrackingNew": {"DoUndo", "CanDoUndo"},
    },
    "TreasuryOld.DataAccess.dll": {
        "TreasuryOld.DataLayer.RChequeAdapter": {
            "DeleteLastRChequeHistory",
            "DeleteCessionToOther",
        },
    },
}

SAFE_MEMBERS = {
    "TreasuryOld.Forms.frmRChequeTracking.CanDoUndo",
    "TreasuryOld.Forms.frmRChequeTrackingNew.CanDoUndo",
    "TreasuryOld.DataLayer.Transaction.Start",
    "TreasuryOld.DataLayer.Transaction.Commit",
    "TreasuryOld.DataLayer.Transaction.RollBack",
    "TreasuryOld.DataLayer.RChequeAdapter.DeleteLastRChequeHistory",
    "TreasuryOld.DataLayer.RChequeAdapter.DeleteCessionToOther",
    "TreasuryOld.DataLayer.RCheque.Refresh",
    "TreasuryOld.DataLayer.RChequeHistoryS.Refresh",
    "TreasuryOld.DataLayer.RCheque.get_RChequeHistoryS",
    "TreasuryOld.DataLayer.RChequeHistoryS.get_Count",
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
                        _method(pe, assembly, owner, index, method_owners, field_owners)
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
    legacy_undo = by_key.get(("TreasuryOld.Forms.frmRChequeTracking", "DoUndo"))
    legacy_can = by_key.get(("TreasuryOld.Forms.frmRChequeTracking", "CanDoUndo"))
    new_undo = by_key.get(("TreasuryOld.Forms.frmRChequeTrackingNew", "DoUndo"))
    new_can = by_key.get(("TreasuryOld.Forms.frmRChequeTrackingNew", "CanDoUndo"))
    adapter = by_key.get(
        ("TreasuryOld.DataLayer.RChequeAdapter", "DeleteLastRChequeHistory")
    )
    wrapper_adapter = by_key.get(
        ("TreasuryOld.DataLayer.RChequeAdapter", "DeleteCessionToOther")
    )
    if not all((legacy_undo, legacy_can, new_undo, new_can, adapter, wrapper_adapter)):
        errors.append({"error": "selected runtime coverage incomplete"})

    legacy_start = _offsets(legacy_undo, "TreasuryOld.DataLayer.Transaction.Start")
    legacy_delete = _offsets(
        legacy_undo, "TreasuryOld.DataLayer.RChequeAdapter.DeleteCessionToOther"
    )
    legacy_commit = _offsets(legacy_undo, "TreasuryOld.DataLayer.Transaction.Commit")
    new_start = _offsets(new_undo, "TreasuryOld.DataLayer.Transaction.Start")
    new_delete = _offsets(
        new_undo, "TreasuryOld.DataLayer.RChequeAdapter.DeleteCessionToOther"
    )
    new_commit = _offsets(new_undo, "TreasuryOld.DataLayer.Transaction.Commit")
    adapter_start = _offsets(adapter, "TreasuryOld.DataLayer.Transaction.Start")
    adapter_execute = _offsets(adapter, "System.Data.Common.DbCommand.ExecuteNonQuery")
    adapter_commit = _offsets(adapter, "TreasuryOld.DataLayer.Transaction.Commit")
    wrapper_start = _offsets(wrapper_adapter, "TreasuryOld.DataLayer.Transaction.Start")
    wrapper_execute = _offsets(wrapper_adapter, "System.Data.Common.DbCommand.ExecuteNonQuery")
    wrapper_commit = _offsets(wrapper_adapter, "TreasuryOld.DataLayer.Transaction.Commit")
    contract = {
        "legacy_undo_checks_can_do_undo": bool(
            _offsets(legacy_undo, "TreasuryOld.Forms.frmRChequeTracking.CanDoUndo")
        ),
        "legacy_undo_starts_transaction_before_delete_call": bool(
            legacy_start and legacy_delete and min(legacy_start) < min(legacy_delete)
        ),
        "legacy_undo_delete_precedes_commit_in_linear_il": bool(
            legacy_delete and legacy_commit and min(legacy_delete) < min(legacy_commit)
        ),
        "legacy_undo_has_rollback_signal": bool(
            _offsets(legacy_undo, "TreasuryOld.DataLayer.Transaction.RollBack")
        ),
        "legacy_undo_refreshes_cheque_and_history": bool(
            _offsets(legacy_undo, "TreasuryOld.DataLayer.RCheque.Refresh")
            and _offsets(legacy_undo, "TreasuryOld.DataLayer.RChequeHistoryS.Refresh")
        ),
        "legacy_can_undo_reads_history_count": bool(
            _offsets(legacy_can, "TreasuryOld.DataLayer.RChequeHistoryS.get_Count")
        ),
        "new_undo_checks_can_do_undo": bool(
            _offsets(new_undo, "TreasuryOld.Forms.frmRChequeTrackingNew.CanDoUndo")
        ),
        "new_undo_starts_transaction_before_delete_call": bool(
            new_start and new_delete and min(new_start) < min(new_delete)
        ),
        "new_undo_delete_precedes_commit_in_linear_il": bool(
            new_delete and new_commit and min(new_delete) < min(new_commit)
        ),
        "new_undo_has_rollback_signal": bool(
            _offsets(new_undo, "TreasuryOld.DataLayer.Transaction.RollBack")
        ),
        "new_undo_refreshes_cheque_and_history": bool(
            _offsets(new_undo, "TreasuryOld.DataLayer.RCheque.Refresh")
            and _offsets(new_undo, "TreasuryOld.DataLayer.RChequeHistoryS.Refresh")
        ),
        "new_can_undo_reads_history_count": bool(
            _offsets(new_can, "TreasuryOld.DataLayer.RChequeHistoryS.get_Count")
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
        "desktop_forms_call_cession_wrapper_not_direct_delete_adapter": bool(
            legacy_delete
            and new_delete
            and not _offsets(
                legacy_undo,
                "TreasuryOld.DataLayer.RChequeAdapter.DeleteLastRChequeHistory",
            )
            and not _offsets(
                new_undo,
                "TreasuryOld.DataLayer.RChequeAdapter.DeleteLastRChequeHistory",
            )
        ),
        "cession_wrapper_adapter_starts_nested_transaction_before_execute": bool(
            wrapper_start
            and wrapper_execute
            and min(wrapper_start) < min(wrapper_execute)
        ),
        "cession_wrapper_adapter_execute_precedes_nested_commit": bool(
            wrapper_execute
            and wrapper_commit
            and min(wrapper_execute) < min(wrapper_commit)
        ),
        "cession_wrapper_adapter_has_rollback_signal": bool(
            _offsets(wrapper_adapter, "TreasuryOld.DataLayer.Transaction.RollBack")
        ),
        "branch_specific_delete_cession_and_rollback_reachability_proven": False,
        "runtime_form_selection_proven": False,
    }
    return {
        "artifact": "varanegar_received_cheque_undo_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "application_endpoint_form_or_command_executions": 0,
            "database_connections": 0,
            "configuration_cheque_bank_customer_history_or_operator_values_read": 0,
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
            "Linear IL order does not prove branch-specific execution, delete-cession reachability or rollback outcomes.",
            "Both form variants are present, but runtime selection for each user and permission set is not proven.",
            "Nested Transaction calls are static signals; physical transaction enlistment is not re-proven here.",
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
