"""Trace bank-statement import persistence from UI to DataAccess and SQL metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import dnfile
from dncil.cil.body.reader import read_method_body_from_bytes
from dncil.clr.token import StringToken

WINDOWS_SCRIPTS = Path(__file__).resolve().parents[1] / "windows"
if str(WINDOWS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SCRIPTS))

from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _analyze_assembly,
    _full_type_name,
)
from extract_varanegar_org_domain import (  # noqa: E402
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


FORM_ASSEMBLY = "TreasuryOld.Forms.dll"
DATA_ASSEMBLY = "TreasuryOld.DataAccess.dll"
FORM_TYPE = "TreasuryOld.Forms.frmReconciliationSetup"
DATA_TYPES = {
    "TreasuryOld.DataLayer.Reconcile",
    "TreasuryOld.DataLayer.BankBill",
    "TreasuryOld.DataLayer.BankBillAdapter",
}
HOOK_NAMES = ("BeforeBankBill", "AfterBankBill", "DoBankBill_DeleteReconcileItem")
SQL_PATTERN = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE)\b", re.I)
TABLE_PATTERN = re.compile(r"\bBankBill2?\b", re.I)
PARAMETER_PATTERN = re.compile(r"^@[A-Za-z][A-Za-z0-9_]{0,127}$")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _has_call(row: dict[str, Any], suffix: str) -> bool:
    return any(call.endswith(suffix) for call in row["calls"])


def _selected_method(type_name: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": type_name,
        **{key: value for key, value in row.items() if key != "string_literals"},
    }


def _command_literals(path: Path) -> dict[str, Any]:
    pe = dnfile.dnPE(str(path))
    type_row = next(
        row
        for row in pe.net.mdtables.TypeDef.rows
        if _full_type_name(row) == "TreasuryOld.DataLayer.BankBillAdapter"
    )
    method = next(
        index.row
        for index in type_row.MethodList or []
        if index.row is not None
        and index.row.Rva
        and str(index.row.Name) == "InitCommandCollection"
    )
    body = read_method_body_from_bytes(pe.get_data(method.Rva, 65536))
    crud_fingerprints: list[dict[str, Any]] = []
    hooks: set[str] = set()
    parameters: set[str] = set()
    omitted = 0
    for instruction in body.instructions:
        if not isinstance(instruction.operand, StringToken):
            continue
        item = pe.net.user_strings.get(instruction.operand.rid)
        value = "" if item is None else str(item)
        sql_match = SQL_PATTERN.match(value)
        if sql_match and TABLE_PATTERN.search(value):
            crud_fingerprints.append(
                {
                    "verb": sql_match.group(1).upper(),
                    "target_table": (
                        "dbo.BankBill2"
                        if re.search(r"\bBankBill2\b", value, re.I)
                        else "dbo.BankBill"
                    ),
                    "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                    "length": len(value),
                    "raw_sql_persisted": False,
                }
            )
        elif value in HOOK_NAMES:
            hooks.add(value)
        elif PARAMETER_PATTERN.fullmatch(value):
            parameters.add(value)
        else:
            omitted += 1
    unique_fingerprints = {
        (row["verb"], row["sha256"]): row for row in crud_fingerprints
    }
    return {
        "type": "TreasuryOld.DataLayer.BankBillAdapter",
        "method": "InitCommandCollection",
        "instruction_count": len(body.instructions),
        "bank_bill_crud_command_fingerprints": sorted(
            unique_fingerprints.values(), key=lambda row: (row["verb"], row["sha256"])
        ),
        "allowlisted_hook_names": sorted(hooks),
        "allowlisted_parameter_names": sorted(parameters),
        "omitted_literal_count": omitted,
        "omitted_literal_values_persisted_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--binary-inventory", required=True, type=Path)
    parser.add_argument("--source-model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    logging.getLogger("dnfile").setLevel(logging.ERROR)
    logging.getLogger("dnfile.stream").setLevel(logging.ERROR)
    inventory = _load(args.binary_inventory)
    source_model = _load(args.source_model)
    expected_hash = {row["name"]: row["sha256"] for row in inventory["files"]}
    paths = {
        FORM_ASSEMBLY: args.source_directory / FORM_ASSEMBLY,
        DATA_ASSEMBLY: args.source_directory / DATA_ASSEMBLY,
    }
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    mismatches = [name for name, digest in hashes.items() if digest != expected_hash.get(name)]

    form_analysis = _analyze_assembly(paths[FORM_ASSEMBLY], {FORM_TYPE})
    data_analysis = _analyze_assembly(paths[DATA_ASSEMBLY], DATA_TYPES)
    form_methods = form_analysis["target_types"][0]["methods"]
    data_by_type = {row["type"]: row["methods"] for row in data_analysis["target_types"]}
    selected: list[dict[str, Any]] = []
    for name in ("AddNewBankBill", "AddNewReconcile", "SaveData"):
        selected.append(_selected_method(FORM_TYPE, next(row for row in form_methods if row["method"] == name)))
    for type_name in ("TreasuryOld.DataLayer.Reconcile", "TreasuryOld.DataLayer.BankBill"):
        methods = data_by_type[type_name]
        selected.append(_selected_method(type_name, next(row for row in methods if row["method"] == "UpdateDetailTables")))
        selected.append(
            _selected_method(
                type_name,
                next(row for row in methods if row["method"] == "Update" and _has_call(row, "Transaction.Start")),
            )
        )
    adapter_methods = data_by_type["TreasuryOld.DataLayer.BankBillAdapter"]
    for name in ("PreUpdate", "PostUpdate"):
        selected.append(_selected_method("TreasuryOld.DataLayer.BankBillAdapter", next(row for row in adapter_methods if row["method"] == name)))
    selected.append(
        _selected_method(
            "TreasuryOld.DataLayer.BankBillAdapter",
            next(row for row in adapter_methods if row["method"] == "Update" and _has_call(row, "DbCommand.ExecuteNonQuery")),
        )
    )
    literal_boundary = _command_literals(paths[DATA_ASSEMBLY])

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            catalog_hooks = _rows(
                cursor,
                """
                SELECT s.name AS schema_name,o.name,o.type_desc
                FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE o.name IN (%s,%s,%s) AND o.is_ms_shipped=0
                ORDER BY o.name
                """,
                HOOK_NAMES,
            )

    bank_bill_object = next(
        row for row in source_model["tables"] if row["object"] == "dbo.BankBill"
    )
    model_columns = {row["name"] for row in bank_bill_object["columns"]}
    persisted_parameters = {
        name.removeprefix("@")
        for name in literal_boundary["allowlisted_parameter_names"]
    }
    expected_columns = {
        "BankBillId", "ReconcileId", "VocherDate", "VocherDescription",
        "VocherDebit", "VocherCredit", "VocherNo", "Balance",
    }
    errors: list[str] = []
    if mismatches:
        errors.append("source package hash mismatch")
    if len(selected) != 10:
        errors.append("selected persistence method coverage incomplete")
    if not expected_columns.issubset(model_columns & persisted_parameters):
        errors.append("BankBill persistence column or parameter set changed")
    verbs = Counter(row["verb"] for row in literal_boundary["bank_bill_crud_command_fingerprints"])
    if set(verbs) != {"SELECT", "INSERT", "UPDATE", "DELETE"}:
        errors.append("BankBill CRUD command fingerprint set changed")
    if set(literal_boundary["allowlisted_hook_names"]) != set(HOOK_NAMES):
        errors.append("BankBill hook command names changed")
    method_errors = form_analysis["method_body_errors"] + data_analysis["method_body_errors"]
    if method_errors:
        errors.append("target method body parse failure")

    catalog_hook_names = {row["name"] for row in catalog_hooks}
    artifact = {
        "artifact": "varanegar_bank_statement_import_header_detail_persistence_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_TARGETED_IL_ALLOWLISTED_SQL_FINGERPRINT_AND_CATALOG_NAME_CHECK",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "assemblies_loaded_or_executed": 0,
            "raw_sql_module_definitions_or_connection_strings_persisted": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "application_or_sql_commands_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": {
            "selected_method_contract_count": len(selected),
            "bank_bill_crud_fingerprint_count": len(literal_boundary["bank_bill_crud_command_fingerprints"]),
            "bank_bill_crud_verb_counts": dict(sorted(verbs.items())),
            "allowlisted_hook_name_count": len(literal_boundary["allowlisted_hook_names"]),
            "clone_present_hook_count": len(catalog_hook_names),
            "clone_absent_optional_hook_count": len(set(HOOK_NAMES) - catalog_hook_names),
            "source_hash_mismatch_count": len(mismatches),
            "method_body_error_count": len(method_errors),
            "validation_error_count": len(errors),
        },
        "source_hashes": hashes,
        "method_contracts": selected,
        "sql_literal_boundary": literal_boundary,
        "clone_catalog_hooks": [
            {"object": f"{row['schema_name']}.{row['name']}", "object_type_desc": row["type_desc"]}
            for row in catalog_hooks
        ],
        "clone_absent_optional_hooks": sorted(set(HOOK_NAMES) - catalog_hook_names),
        "persistence_chain": [
            "frmReconciliationSetup.SaveData",
            "Reconcile.Update",
            "Reconcile.UpdateDetailTables",
            "BankBillS.Update",
            "BankBill.Update",
            "BankBillAdapter.Update",
            "dbo.BankBill CRUD command",
        ],
        "target_contract": {
            "aggregate": "BankReconciliationSession",
            "header_and_imported_statement_rows_commit_atomically": True,
            "parser_staging_commits_directly_to_ledger": False,
            "repository_level_commit_allowed": False,
            "optional_runtime_procedure_discovery_allowed": False,
            "extension_hooks_are_explicit_versioned_domain_events_or_outbox_handlers": True,
            "bulk_row_validation_and_idempotent_import_identity_required": True,
        },
        "source_hash_mismatches": mismatches,
        "method_body_errors": method_errors,
        "validation_errors": errors,
        "limits": [
            "SQL text is represented only by verb/table fingerprints; raw SQL and module definitions are not persisted.",
            "BeforeBankBill and AfterBankBill names are present in the adapter but absent from the clone catalog; live presence is unproven.",
            "The chain proves static call structure, not successful runtime commit or live row parity.",
            "No form, parser, transaction, SQL command, procedure or business row was executed or read.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
