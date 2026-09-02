"""Extract hash-pinned static IL for received-cheque delete commands."""

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
        "TreasuryOld.Forms.frmRChequeTracking": {"DeleteRCheque"},
        "TreasuryOld.Forms.frmRChequeTrackingNew": {"DeleteRCheque"},
    }
}

SAFE_MEMBERS = {
    "Question.Delete",
    "Error.NotAllowDelete",
    "System.Data.DataRow.Delete",
    "TreasuryOld.DataLayer.RCheque.Update",
    "TreasuryOld.DataLayer.Transaction.Start",
    "BaseClasses.Objects.VNGridEx.GetDataRow",
    "BaseClasses.Objects.VNGridEx.SaveCurRowPosition",
    "BaseClasses.Objects.VNGridEx.GoLastRowPosition",
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
                    methods.append(_method(pe, assembly, owner, index, method_owners, field_owners))
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
    legacy = by_key.get(("TreasuryOld.Forms.frmRChequeTracking", "DeleteRCheque"))
    newer = by_key.get(("TreasuryOld.Forms.frmRChequeTrackingNew", "DeleteRCheque"))
    if not legacy or not newer:
        errors.append({"error": "selected runtime coverage incomplete"})

    legacy_question = _offsets(legacy, "Question.Delete")
    legacy_row_delete = _offsets(legacy, "System.Data.DataRow.Delete")
    legacy_update = _offsets(legacy, "TreasuryOld.DataLayer.RCheque.Update")
    managed = {
        "legacy_delete_has_confirmation": bool(legacy_question),
        "legacy_delete_marks_dataset_row_deleted": bool(legacy_row_delete),
        "legacy_delete_flushes_rcheque_dataset": bool(legacy_update),
        "legacy_confirmation_precedes_row_delete_and_update_in_linear_il": bool(
            legacy_question
            and legacy_row_delete
            and legacy_update
            and min(legacy_question) < min(legacy_row_delete) < min(legacy_update)
        ),
        "legacy_delete_has_explicit_transaction_signal": bool(
            _offsets(legacy, "TreasuryOld.DataLayer.Transaction.Start")
        ),
        "new_delete_has_confirmation": bool(_offsets(newer, "Question.Delete")),
        "new_delete_has_dataset_delete_or_update_signal": bool(
            _offsets(newer, "System.Data.DataRow.Delete")
            or _offsets(newer, "TreasuryOld.DataLayer.RCheque.Update")
        ),
        "runtime_form_selection_proven": False,
        "dataset_update_to_sql_trigger_branch_reachability_proven": False,
    }
    return {
        "artifact": "varanegar_received_cheque_delete_runtime_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "source": sources,
        "safety": {
            "mode": "STATIC_HASH_PINNED_PE_METADATA_AND_IL_ONLY",
            "assembly_loads_or_executions": 0,
            "application_endpoint_form_or_command_executions": 0,
            "database_connections": 0,
            "configuration_cheque_receipt_customer_amount_bank_or_operator_values_read": 0,
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
        "managed_delete_contract": managed,
        "method_contracts": methods,
        "errors": errors,
        "evidence_limits": [
            "Linear IL proves call ordering, not branch-specific execution or database outcome.",
            "The legacy form mutates a dataset row and calls its Update method; this artifact does not independently prove the resulting SQL command or trigger branch.",
            "The new form's selected method contains only confirmation-related evidence; deletion may be delegated elsewhere or intentionally absent.",
            "Both form variants are present, but runtime selection for each user and permission set is not proven.",
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
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(json.dumps(payload["managed_delete_contract"], ensure_ascii=False))
    return 0 if payload["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
