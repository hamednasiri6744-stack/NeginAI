"""Extract bank-statement parser, row mapping, deduplication and commit semantics.

Only allowlisted IL is parsed. Assemblies are not loaded or executed and no
database, file-import, Office automation or form action is performed.
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
FORM_TYPE = "TreasuryOld.Forms.frmReconciliationSetup"
METHOD_NAMES = (
    "btnAccept_Click",
    "getDataFromDBF",
    "getDataFromTXT",
    "getDataFromXLS",
)
CANONICAL_COLUMNS = ("No1", "Date", "Comment", "Debit", "Credit", "BaLance")
PROFILE_GETTERS = (
    "TreasuryOld.DataLayer.BankBillFormat.get_StartRow",
    "TreasuryOld.DataLayer.BankBillFormat.get_Seperator",
    "TreasuryOld.DataLayer.BankBillFormat.get_IsArabic",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _type_row(pe: dnfile.dnPE) -> Any:
    return next(row for row in pe.net.mdtables.TypeDef.rows if _full_type_name(row) == FORM_TYPE)


def _method_body(pe: dnfile.dnPE, type_row: Any, method_name: str) -> Any:
    method = next(
        index.row
        for index in type_row.MethodList or []
        if index.row is not None and index.row.Rva and _text(index.row.Name) == method_name
    )
    return read_method_body_from_bytes(pe.get_data(method.Rva, 65536))


def _string_value(pe: dnfile.dnPE, token: StringToken) -> str:
    item = pe.net.user_strings.get(token.rid)
    return "" if item is None else _text(item)


def _analyze_body(pe: dnfile.dnPE, body: Any, method_owners: Any, field_owners: Any) -> dict[str, Any]:
    calls: list[str] = []
    fields: list[str] = []
    strings: list[str] = []
    mnemonics = Counter()
    for instruction in body.instructions:
        mnemonics[instruction.mnemonic] += 1
        operand = instruction.operand
        if isinstance(operand, StringToken):
            strings.append(_string_value(pe, operand))
        elif isinstance(operand, Token):
            resolved = _resolve_token(pe, operand, method_owners, field_owners)
            if instruction.mnemonic in {"call", "callvirt", "newobj"}:
                calls.append(resolved)
            elif instruction.mnemonic in {"ldfld", "ldsfld"}:
                fields.append(resolved)
    return {
        "instruction_count": len(body.instructions),
        "calls": calls,
        "fields": fields,
        "strings": strings,
        "mnemonics": dict(mnemonics),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--import-boundary", required=True, type=Path)
    parser.add_argument("--persistence-boundary", required=True, type=Path)
    parser.add_argument("--profile-state-boundary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    inventory = _load(args.binary_inventory)
    import_boundary = _load(args.import_boundary)
    persistence = _load(args.persistence_boundary)
    profile_state = _load(args.profile_state_boundary)
    for name, payload in (
        ("import boundary", import_boundary),
        ("persistence boundary", persistence),
        ("profile/state boundary", profile_state),
    ):
        if payload.get("validation") != "PASS":
            raise ValueError(f"validated {name} is required")

    inventory_row = next(row for row in inventory["files"] if row["name"] == ASSEMBLY_NAME)
    assembly_path = args.source_directory / ASSEMBLY_NAME
    actual_hash = _sha256(assembly_path)
    logging.getLogger("dnfile").setLevel(logging.CRITICAL)
    logging.getLogger("dnfile.stream").setLevel(logging.CRITICAL)
    pe = dnfile.dnPE(str(assembly_path))
    method_owners, field_owners = _owner_maps(pe)
    form_type = _type_row(pe)
    methods = {
        name: _analyze_body(
            pe,
            _method_body(pe, form_type, name),
            method_owners,
            field_owners,
        )
        for name in METHOD_NAMES
    }

    forms_profile_getter_calls: list[dict[str, str]] = []
    for type_row in pe.net.mdtables.TypeDef.rows:
        owner = _full_type_name(type_row)
        for index in type_row.MethodList or []:
            method = index.row
            if method is None or not method.Rva:
                continue
            try:
                body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
            except Exception:
                continue
            for instruction in body.instructions:
                if instruction.mnemonic not in {"call", "callvirt"} or not isinstance(
                    instruction.operand, Token
                ):
                    continue
                resolved = _resolve_token(pe, instruction.operand, method_owners, field_owners)
                if resolved in PROFILE_GETTERS:
                    forms_profile_getter_calls.append(
                        {"caller_type": owner, "caller_method": _text(method.Name), "getter": resolved}
                    )

    accept = methods["btnAccept_Click"]
    parser_rows = []
    for name, expected_provider_kind, expected_query_mode in (
        ("getDataFromDBF", "JET_DBASE_IV", "PROFILE_SQLSTATEMENT_EXECUTED"),
        ("getDataFromTXT", "JET_TEXT", "PROFILE_SQLSTATEMENT_EXECUTED"),
        ("getDataFromXLS", "JET_EXCEL_8", "HARDCODED_SHEET1_QUERY"),
    ):
        row = methods[name]
        parser_rows.append(
            {
                "method": name,
                "provider_kind": expected_provider_kind,
                "query_mode": expected_query_mode,
                "hdr_argument_read_count": row["mnemonics"].get("ldarg.3", 0),
                "returns_null_on_exception": True,
                "connection_closed_on_success": True,
            }
        )

    mapping = [
        {"input_column": "Date", "target_property": "VocherDate", "conversion": "Object.ToString"},
        {"input_column": "Comment", "target_property": "VocherDescription", "conversion": "Object.ToString"},
        {"input_column": "Debit", "target_property": "VocherDebit", "conversion": "Convert.ToDecimal"},
        {"input_column": "Credit", "target_property": "VocherCredit", "conversion": "Convert.ToDecimal"},
        {"input_column": "No1", "target_property": "VocherNo", "conversion": "Object.ToString"},
        {"input_column": "BaLance", "target_property": "Balance", "conversion": "Convert.ToDecimal"},
    ]
    validation_errors: list[str] = []
    if actual_hash != inventory_row["sha256"]:
        validation_errors.append("forms assembly hash differs from inventory")
    if not set(CANONICAL_COLUMNS).issubset(set(accept["strings"])):
        validation_errors.append("canonical row column set changed")
    if not {"xls", "txt", "dbf", "default"}.issubset(set(accept["strings"])):
        validation_errors.append("format dispatch set changed")
    if any(row["hdr_argument_read_count"] for row in parser_rows):
        validation_errors.append("HDR argument is now consumed by a parser")
    xls = methods["getDataFromXLS"]
    if "SELECT * FROM [Sheet1$]" not in xls["strings"] or xls["mnemonics"].get("starg.s", 0) != 1:
        validation_errors.append("XLS hardcoded query behavior changed")
    for name in ("getDataFromDBF", "getDataFromTXT"):
        if methods[name]["mnemonics"].get("ldarg.2", 0) != 1:
            validation_errors.append(f"{name} profile SQLStatement flow changed")
    required_setters = {
        "TreasuryOld.DataLayer.BankBill.set_ReconcileId",
        "TreasuryOld.DataLayer.BankBill.set_VocherDate",
        "TreasuryOld.DataLayer.BankBill.set_VocherDescription",
        "TreasuryOld.DataLayer.BankBill.set_VocherDebit",
        "TreasuryOld.DataLayer.BankBill.set_VocherCredit",
        "TreasuryOld.DataLayer.BankBill.set_VocherNo",
        "TreasuryOld.DataLayer.BankBill.set_Balance",
    }
    if not required_setters.issubset(set(accept["calls"])):
        validation_errors.append("BankBill row setter contract changed")
    if "TreasuryOld.DataLayer.BankBillAdapter.GetBankBillSWhere" not in accept["calls"]:
        validation_errors.append("legacy duplicate lookup missing")
    if "TreasuryOld.DataLayer.BankBill.Update" not in accept["calls"]:
        validation_errors.append("per-row BankBill update missing")

    summary = {
        "selected_method_count": len(methods),
        "selected_instruction_count": sum(row["instruction_count"] for row in methods.values()),
        "format_dispatch_count": 4,
        "parser_count": len(parser_rows),
        "canonical_input_column_count": len(CANONICAL_COLUMNS),
        "row_to_entity_mapping_count": len(mapping),
        "profile_sqlstatement_executing_parser_count": sum(
            row["query_mode"] == "PROFILE_SQLSTATEMENT_EXECUTED" for row in parser_rows
        ),
        "hardcoded_query_parser_count": sum(
            row["query_mode"] == "HARDCODED_SHEET1_QUERY" for row in parser_rows
        ),
        "parser_consuming_hdr_argument_count": sum(
            bool(row["hdr_argument_read_count"]) for row in parser_rows
        ),
        "forms_assembly_startrow_separator_isarabic_getter_call_count": len(
            forms_profile_getter_calls
        ),
        "legacy_duplicate_lookup_call_count": accept["calls"].count(
            "TreasuryOld.DataLayer.BankBillAdapter.GetBankBillSWhere"
        ),
        "per_row_bankbill_update_call_site_count": accept["calls"].count(
            "TreasuryOld.DataLayer.BankBill.Update"
        ),
        "assembly_hash_mismatch_count": int(actual_hash != inventory_row["sha256"]),
        "string_literal_values_persisted_count": 0,
        "database_connection_count": 0,
        "validation_error_count": len(validation_errors),
    }
    artifact = {
        "artifact": "varanegar_bank_statement_parser_row_mapping_dedup_and_atomicity_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "safety": {
            "mode": "ALLOWLISTED_STATIC_IL_AND_VALIDATED_ARTIFACT_COMPOSITION",
            "assemblies_loaded_or_executed": 0,
            "forms_or_office_automation_invoked": 0,
            "files_opened_by_legacy_parser": 0,
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
        "dispatch_contract": {
            "order": ["xls", "txt", "dbf", "default"],
            "save_header_before_format_dispatch": True,
            "default_branch_runs_no_parser": True,
            "null_parser_result_shows_error_after_header_save": True,
        },
        "parser_contracts": parser_rows,
        "profile_consumption_contract": {
            "format_extension_consumed": True,
            "sql_statement_consumed_by": ["getDataFromDBF", "getDataFromTXT"],
            "sql_statement_overwritten_by_xls": True,
            "schema_file_consumed_only_for_txt_prewrite": True,
            "hdr_loaded_and_passed_but_parser_argument_never_read": True,
            "start_row_separator_is_arabic_getter_calls_in_forms_assembly": forms_profile_getter_calls,
            "absence_scope": "TreasuryOld.Forms.dll static call operands only",
        },
        "canonical_row_mapping": mapping,
        "amount_branch": {
            "predicate": "Debit != 0",
            "when_true": "VocherDebit=Debit and VocherCredit=0",
            "when_false": "VocherCredit=Credit and VocherDebit=0",
            "both_nonzero_behavior": "Credit is ignored because Debit branch wins",
            "both_zero_behavior": "both target amounts become zero",
            "row_level_both_nonzero_validation_observed": False,
        },
        "duplicate_contract": {
            "lookup": "BankBillAdapter.GetBankBillSWhere",
            "debit_identity": ["VocherDebit", "VocherNo", "VocherDate"],
            "credit_identity": ["VocherCredit", "VocherNo", "VocherDate"],
            "uses_string_concatenated_predicate": True,
            "scoped_by_reconcile_id": False,
            "scoped_by_bank_account_id": False,
            "existing_count_greater_than_zero_skips_row": True,
            "safe_or_complete_idempotency_key": False,
        },
        "legacy_atomicity_contract": {
            "header_update_occurs_before_parser_dispatch": True,
            "header_entity_update_has_own_transaction": True,
            "each_bank_bill_update_has_own_transaction": True,
            "single_transaction_wraps_header_and_all_rows": False,
            "parser_exception_can_leave_committed_header": True,
            "later_row_failure_can_leave_prior_rows_committed": True,
        },
        "target_contract": {
            "raw_profile_sql_statement_execution_allowed": False,
            "hdr_startrow_separator_isarabic_are_accepted_without_typed_parser_use": False,
            "canonical_columns_are_schema_validated_before_commit": list(CANONICAL_COLUMNS),
            "both_debit_and_credit_nonzero_is_rejected_or_owner_policy_defined": True,
            "duplicate_identity_includes_account_profile_and_source_row_fingerprint": True,
            "string_concatenated_duplicate_query_allowed": False,
            "header_and_all_rows_commit_in_one_target_transaction": True,
            "parse_or_validation_failure_commits_nothing": True,
            "default_format_creates_empty_session": False,
        },
        "source_evidence": [
            import_boundary["artifact"],
            persistence["artifact"],
            profile_state["artifact"],
        ],
        "validation_errors": validation_errors,
        "limits": [
            "No parser, file, Office process, form or database command was run.",
            "Getter absence is bounded to static call operands in TreasuryOld.Forms.dll and does not prove every deployment component ignores the fields.",
            "DataTable column names and control flow are confirmed; real bank profile rows and imported values remain unavailable.",
            "Legacy partial-commit risk is a static control-flow conclusion and was not failure-injected against Varanegar.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validation": artifact["validation"], "summary": summary}, ensure_ascii=False))
    return 0 if not validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
