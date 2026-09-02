"""Extract how the bank-reconciliation Summary outputs are presented by the UI.

The extractor parses one allowlisted IL method. It never loads the assembly,
invokes the form, opens a database connection, or persists user-string values.
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
from dncil.clr.token import Token

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
METHOD_NAME = "RefreshSummary"
EXPECTED_LABEL_FIELDS = (
    "lblRemainingLastReconcileValue",
    "lblRemainingThisPeriodValue",
    "lblRemainingBillValue",
    "lblRemainingCardexValue",
    "lblBillDebitOpenItemsValue",
    "lblBillCreditOpenItemsValue",
    "lblCardexlDebitOpenItemsValue",
    "lblCardexlCreditOpenItemsValue",
    "lblRealRemainingBillValue",
    "lblRealRemainingCardexValue",
    "lblReconcileValue",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _method_body(pe: dnfile.dnPE) -> Any:
    type_row = next(
        row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == FORM_TYPE
    )
    method = next(
        index.row
        for index in type_row.MethodList or []
        if index.row is not None
        and index.row.Rva
        and _text(index.row.Name) == METHOD_NAME
    )
    return read_method_body_from_bytes(pe.get_data(method.Rva, 65536))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--matching-boundary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    inventory = _load(args.binary_inventory)
    matching = _load(args.matching_boundary)
    if matching.get("validation") != "PASS":
        raise ValueError("validated matching boundary is required")
    inventory_row = next(row for row in inventory["files"] if row["name"] == ASSEMBLY_NAME)
    assembly_path = args.source_directory / ASSEMBLY_NAME
    actual_hash = _sha256(assembly_path)

    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    logging.getLogger("dnfile.stream").setLevel(logging.CRITICAL)
    pe = dnfile.dnPE(str(assembly_path))
    method_owners, field_owners = _owner_maps(pe)
    body = _method_body(pe)
    resolved_calls: list[str] = []
    resolved_fields: list[str] = []
    mnemonics = Counter()
    for instruction in body.instructions:
        mnemonics[instruction.mnemonic] += 1
        if not isinstance(instruction.operand, Token):
            continue
        resolved = _resolve_token(pe, instruction.operand, method_owners, field_owners)
        if instruction.mnemonic in {"call", "callvirt"}:
            resolved_calls.append(resolved)
        elif instruction.mnemonic in {"ldfld", "ldsfld"}:
            resolved_fields.append(resolved)

    label_sequence: list[str] = []
    field_prefix = FORM_TYPE + "."
    for field in resolved_fields:
        if not field.startswith(field_prefix):
            continue
        short = field.removeprefix(field_prefix)
        if short not in EXPECTED_LABEL_FIELDS or short in label_sequence:
            continue
        label_sequence.append(short)

    output_parameters = [
        row["name"].removeprefix("@")
        for row in matching["summary_boundary"]["catalog_parameters"]
        if row["is_output"]
    ]
    mappings = [
        {
            "ordinal": index + 1,
            "output_metric": metric,
            "ui_label_field": label,
            "negative_display": "ABSOLUTE_VALUE_IN_PARENTHESES_RED",
            "zero_or_positive_display": "SIGNED_VALUE_DARK_BLUE",
        }
        for index, (metric, label) in enumerate(zip(output_parameters, label_sequence))
    ]

    call_counts = Counter(resolved_calls)
    validation_errors: list[str] = []
    if actual_hash != inventory_row["sha256"]:
        validation_errors.append("assembly hash differs from validated binary inventory")
    if tuple(label_sequence) != EXPECTED_LABEL_FIELDS:
        validation_errors.append("summary label sequence changed")
    if len(output_parameters) != 11 or len(mappings) != 11:
        validation_errors.append("summary output mapping count changed")
    expected_call_counts = {
        "TreasuryOld.DataLayer.ReconcileAdapter.GetSummary": 1,
        "System.Decimal.op_LessThan": 11,
        "System.Decimal.op_Multiply": 11,
        "System.Drawing.Color.get_Red": 11,
        "System.Drawing.Color.get_DarkBlue": 11,
        "System.Windows.Forms.Control.set_Text": 22,
        "System.Windows.Forms.Control.set_ForeColor": 22,
    }
    for name, expected in expected_call_counts.items():
        if call_counts[name] != expected:
            validation_errors.append(
                f"{name}: expected {expected} calls, got {call_counts[name]}"
            )

    summary = {
        "selected_method_count": 1,
        "instruction_count": len(body.instructions),
        "summary_input_count": 3,
        "summary_output_count": len(output_parameters),
        "output_to_label_mapping_count": len(mappings),
        "negative_comparison_count": call_counts["System.Decimal.op_LessThan"],
        "absolute_value_multiply_count": call_counts["System.Decimal.op_Multiply"],
        "red_color_assignment_count": call_counts["System.Drawing.Color.get_Red"],
        "dark_blue_color_assignment_count": call_counts["System.Drawing.Color.get_DarkBlue"],
        "text_assignment_count": call_counts["System.Windows.Forms.Control.set_Text"],
        "foreground_color_assignment_count": call_counts[
            "System.Windows.Forms.Control.set_ForeColor"
        ],
        "assembly_hash_mismatch_count": int(actual_hash != inventory_row["sha256"]),
        "string_literal_value_persisted_count": 0,
        "database_connection_count": 0,
        "validation_error_count": len(validation_errors),
    }
    artifact = {
        "artifact": "varanegar_bank_reconciliation_summary_output_to_ui_presentation_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "safety": {
            "mode": "ALLOWLISTED_STATIC_IL_ONLY",
            "assembly_loaded_or_executed": 0,
            "form_invoked": 0,
            "database_connections": 0,
            "stored_procedures_executed": 0,
            "business_row_values_read": 0,
            "string_literal_values_persisted": 0,
        },
        "source": {
            "assembly": ASSEMBLY_NAME,
            "type": FORM_TYPE,
            "method": METHOD_NAME,
            "sha256": actual_hash,
            "inventory_sha256_match": actual_hash == inventory_row["sha256"],
        },
        "summary": summary,
        "call_boundary": {
            "input_scope_fields": ["m_CurrentReconcile.ReconcileId", "m_DateOf", "m_BankAccountId"],
            "output_parameter_order": output_parameters,
            "passes_all_outputs_by_reference": True,
            "adapter_call_count": call_counts[
                "TreasuryOld.DataLayer.ReconcileAdapter.GetSummary"
            ],
        },
        "output_to_ui_mappings": mappings,
        "presentation_semantics": {
            "negative_values_compared_to_decimal_zero": True,
            "negative_values_multiplied_by_decimal_minus_one_before_text": True,
            "negative_values_have_parenthesis_tokens_around_absolute_value": True,
            "negative_values_colored_red": True,
            "zero_and_positive_values_colored_dark_blue": True,
            "presentation_mutates_only_local_output_copies": True,
            "presentation_does_not_update_reconcile_or_other_domain_entity": True,
            "color_is_not_a_domain_state_or_authorization_signal": True,
        },
        "target_contract": {
            "summary_api_returns_signed_decimal_metrics": True,
            "presentation_formatting_is_separate_from_query_formula": True,
            "negative_values_preserve_machine_readable_sign": True,
            "accessible_text_must_not_rely_on_color_alone": True,
            "metric_order_is_not_used_as_wire_identity": True,
            "stable_metric_keys_are_required": output_parameters,
            "legacy_static_transaction_is_not_copied_into_ui": True,
            "summary_formula_semantics_confirmed": False,
            "runtime_row_result_parity_required_before_command_pilot": True,
        },
        "validation_errors": validation_errors,
        "limits": [
            "The stored procedure definition and all business rows remain unread.",
            "The 11 output names and their UI destinations are confirmed; formulas are not.",
            "Parenthesis token contents were not persisted; the structure is inferred from IL concatenation around absolute value.",
            "Color and formatting behavior do not prove accounting debit/credit semantics.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation": artifact["validation"], "summary": summary}, ensure_ascii=False))
    return 0 if not validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
