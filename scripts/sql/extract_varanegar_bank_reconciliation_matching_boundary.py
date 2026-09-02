"""Extract the bank-reconciliation matching boundary without executing legacy code.

The extractor parses allowlisted IL and reads only SQL Server system catalogs on
the read-only clone. It never loads an assembly, invokes a form, executes a
stored procedure, or reads a business row.
"""

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
if str(WINDOWS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SCRIPTS))

from extract_varanegar_targeted_il_contracts import (  # noqa: E402
    _analyze_assembly,
    _full_type_name,
    _owner_maps,
    _resolve_token,
    _text,
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
FORM_TYPE = "TreasuryOld.Forms.frmReconciliation"
DATA_TYPES = {
    "TreasuryOld.DataLayer.ReconcileItem",
    "TreasuryOld.DataLayer.ReconcileItemAdapter",
    "TreasuryOld.DataLayer.ReconcileAdapter",
}
SUMMARY_ADAPTER_TYPE = "TreasuryOld.DataLayer.ReconcileAdapter"
SUMMARY_COMMAND = "DoReconcile_GetSummary"
SUMMARY_PARAMETER_CONTRACT = (
    ("@ReconcileId", "int", False),
    ("@VocherDate", "varchar", False),
    ("@BankAccountId", "int", False),
    ("@RemainingLastReconcile", "money", True),
    ("@RemainingThisPeriod", "money", True),
    ("@RemainingBill", "money", True),
    ("@RemainingCardex", "money", True),
    ("@BillDebitOpenItems", "money", True),
    ("@BillCreditOpenItems", "money", True),
    ("@CardexDebitOpenItems", "money", True),
    ("@CardexCreditOpenItems", "money", True),
    ("@RealRemainingBill", "money", True),
    ("@RealRemainingCardex", "money", True),
    ("@Reconcile", "money", True),
)
FORM_METHODS = (
    "DoVocherPass",
    "LoadData",
    "LoadForm",
    "RefreshGrids",
    "RefreshSummary",
    "cb_CommandClick",
    "grdBankAccountCardex_CellValueChanged",
    "grdBankBill_SelectionChanged",
    "vGrid_DeletingRecords",
    "vGrid_RecordsDeleted",
)
DISCRIMINATOR_TO_SETTER = {
    "PCHEQUE": "PChequeId",
    "PWITHDRAW": "PWithdrawId",
    "RBANKDRAFT": "RBankDraftId",
    "RCASHDRAFT": "RCashDraftId",
    "RCHEQUE": "RChequeId",
    "TRANSFER": "TransferId",
}
AMOUNT_COLUMNS = {"Credit", "Debit", "VocherCredit", "VocherDebit"}
SAFE_FILTER_LITERALS = {
    "BankAccountId=",
    " And DateOf<='",
    "VocherDate<='",
    "BankBillId IN (SELECT BankBillId FROM ReconcileItem)",
    "relationBankBillReconcileItem",
    "ReconcileItem",
}
HOOK_NAMES = ("BeforeReconcileItem", "AfterReconcileItem")
HOOK_PROBE_LITERAL_TO_NAME = {
    "select COUNT(*) from dbo.sysobjects where id = object_id(N'BeforeReconcileItem')": "BeforeReconcileItem",
    "select COUNT(*) from dbo.sysobjects where id = object_id(N'AfterReconcileItem')": "AfterReconcileItem",
}
CATALOG_NAMES = (
    "FreeBankAccountCardex",
    "FreeBankBill",
    "BankBill2",
    "ReconcileItem",
    SUMMARY_COMMAND,
    *HOOK_NAMES,
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _has_call(row: dict[str, Any], suffix: str) -> bool:
    return any(call.endswith(suffix) for call in row["calls"])


def _contract(type_name: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": type_name,
        "method": row["method"],
        "instruction_count": row["instruction_count"],
        "calls": row["calls"],
        "referenced_fields": row["referenced_fields"],
        "string_literal_values_persisted": 0,
    }


def _type_row(pe: dnfile.dnPE, type_name: str) -> Any:
    return next(
        row
        for row in pe.net.mdtables.TypeDef.rows
        if _full_type_name(row) == type_name
    )


def _method_body(pe: dnfile.dnPE, type_name: str, method_name: str) -> Any:
    type_row = _type_row(pe, type_name)
    method = next(
        index.row
        for index in type_row.MethodList or []
        if index.row is not None
        and index.row.Rva
        and _text(index.row.Name) == method_name
    )
    return read_method_body_from_bytes(pe.get_data(method.Rva, 65536))


def _string_value(pe: dnfile.dnPE, token: StringToken) -> str:
    item = pe.net.user_strings.get(token.rid)
    return "" if item is None else _text(item)


def _safe_literals_for_method(
    pe: dnfile.dnPE, method_name: str, allowlist: set[str]
) -> list[str]:
    body = _method_body(pe, FORM_TYPE, method_name)
    values = []
    for instruction in body.instructions:
        if not isinstance(instruction.operand, StringToken):
            continue
        value = _string_value(pe, instruction.operand)
        if value in allowlist:
            values.append(value)
    return values


def _dispatch_contract(pe: dnfile.dnPE) -> dict[str, Any]:
    body = _method_body(pe, FORM_TYPE, "DoVocherPass")
    method_owners, field_owners = _owner_maps(pe)
    instructions = list(body.instructions)
    offsets = {int(instruction.offset): index for index, instruction in enumerate(instructions)}
    mappings: list[dict[str, Any]] = []
    safe_literal_count = 0
    omitted_literal_count = 0
    for index, instruction in enumerate(instructions):
        operand = instruction.operand
        if not isinstance(operand, StringToken):
            continue
        value = _string_value(pe, operand)
        if value in set(DISCRIMINATOR_TO_SETTER) | {"Type", "BankBillId", "BankAccountCardexId"}:
            safe_literal_count += 1
        else:
            omitted_literal_count += 1
        if value not in DISCRIMINATOR_TO_SETTER:
            continue
        branch = next(
            (
                candidate
                for candidate in instructions[index + 1 : index + 5]
                if candidate.mnemonic.startswith("brtrue")
            ),
            None,
        )
        target_offset = int(branch.operand) if branch is not None else -1
        target_index = offsets.get(target_offset, -1)
        setter = ""
        if target_index >= 0:
            for candidate in instructions[target_index : target_index + 15]:
                if candidate.mnemonic not in {"call", "callvirt"} or not isinstance(
                    candidate.operand, Token
                ):
                    continue
                resolved = _resolve_token(
                    pe, candidate.operand, method_owners, field_owners
                )
                prefix = "TreasuryOld.DataLayer.ReconcileItem.set_"
                if resolved.startswith(prefix):
                    setter = resolved.removeprefix(prefix)
                    break
        mappings.append(
            {
                "type_discriminator": value,
                "typed_reference_property": setter,
                "source_grid_reference_column": "BankAccountCardexId",
                "branch_target_il_offset": target_offset,
            }
        )
    return {
        "form_type": FORM_TYPE,
        "method": "DoVocherPass",
        "instruction_count": len(instructions),
        "typed_reference_mappings": mappings,
        "safe_literal_occurrence_count": safe_literal_count,
        "omitted_literal_count": omitted_literal_count,
        "omitted_literal_values_persisted_count": 0,
    }


def _hook_names(pe: dnfile.dnPE) -> list[str]:
    observed: set[str] = set()
    for method_name in ("PreUpdate", "PostUpdate"):
        body = _method_body(
            pe, "TreasuryOld.DataLayer.ReconcileItemAdapter", method_name
        )
        for instruction in body.instructions:
            if isinstance(instruction.operand, StringToken):
                value = _string_value(pe, instruction.operand)
                hook_name = HOOK_PROBE_LITERAL_TO_NAME.get(value)
                if hook_name is not None:
                    observed.add(hook_name)
    return sorted(observed)


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
    paths = {
        FORM_ASSEMBLY: args.source_directory / FORM_ASSEMBLY,
        DATA_ASSEMBLY: args.source_directory / DATA_ASSEMBLY,
    }
    source_hashes = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in paths.items()
    }
    hash_mismatches = [
        name
        for name, digest in source_hashes.items()
        if digest != expected_hash.get(name)
    ]

    form_analysis = _analyze_assembly(paths[FORM_ASSEMBLY], {FORM_TYPE})
    data_analysis = _analyze_assembly(paths[DATA_ASSEMBLY], DATA_TYPES)
    form_rows = form_analysis["target_types"][0]["methods"]
    form_by_name = {row["method"]: row for row in form_rows}
    data_by_type = {
        row["type"]: row["methods"] for row in data_analysis["target_types"]
    }
    method_contracts = [
        _contract(FORM_TYPE, form_by_name[name]) for name in FORM_METHODS
    ]
    reconcile_item_methods = data_by_type["TreasuryOld.DataLayer.ReconcileItem"]
    adapter_methods = data_by_type["TreasuryOld.DataLayer.ReconcileItemAdapter"]
    summary_adapter_methods = data_by_type[SUMMARY_ADAPTER_TYPE]
    method_contracts.append(
        _contract(
            "TreasuryOld.DataLayer.ReconcileItem",
            next(
                row
                for row in reconcile_item_methods
                if row["method"] == "Update" and _has_call(row, "Transaction.Start")
            ),
        )
    )
    summary_method = next(
        row
        for row in summary_adapter_methods
        if row["method"] == "GetSummary"
        and _has_call(row, "get_DoReconcile_GetSummarycommand")
    )
    method_contracts.append(_contract(SUMMARY_ADAPTER_TYPE, summary_method))
    for name in ("PreUpdate", "PostUpdate"):
        method_contracts.append(
            _contract(
                "TreasuryOld.DataLayer.ReconcileItemAdapter",
                next(row for row in adapter_methods if row["method"] == name),
            )
        )
    method_contracts.append(
        _contract(
            "TreasuryOld.DataLayer.ReconcileItemAdapter",
            next(
                row
                for row in adapter_methods
                if row["method"] == "Update"
                and _has_call(row, "DbCommand.ExecuteNonQuery")
            ),
        )
    )

    form_pe = dnfile.dnPE(str(paths[FORM_ASSEMBLY]))
    data_pe = dnfile.dnPE(str(paths[DATA_ASSEMBLY]))
    dispatch = _dispatch_contract(form_pe)
    amount_columns_by_event = {
        name: sorted(
            set(_safe_literals_for_method(form_pe, name, AMOUNT_COLUMNS))
        )
        for name in (
            "grdBankAccountCardex_CellValueChanged",
            "grdBankBill_SelectionChanged",
        )
    }
    refresh_filter_literals = sorted(
        set(_safe_literals_for_method(form_pe, "RefreshGrids", SAFE_FILTER_LITERALS))
    )
    observed_hook_names = _hook_names(data_pe)

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            placeholders = ",".join("%s" for _ in CATALOG_NAMES)
            catalog_objects = _rows(
                cursor,
                f"""
                SELECT o.object_id,s.name AS schema_name,o.name,o.type_desc
                FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE o.name IN ({placeholders}) AND o.is_ms_shipped=0
                ORDER BY o.name
                """,
                CATALOG_NAMES,
            )
            view_names = ("FreeBankAccountCardex", "FreeBankBill", "BankBill2")
            view_placeholders = ",".join("%s" for _ in view_names)
            catalog_columns = _rows(
                cursor,
                f"""
                SELECT s.name AS schema_name,o.name AS object_name,c.column_id,
                       c.name AS column_name,TYPE_NAME(c.user_type_id) AS data_type,
                       c.is_nullable
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                JOIN sys.columns c ON c.object_id=o.object_id
                WHERE o.name IN ({view_placeholders})
                ORDER BY o.name,c.column_id
                """,
                view_names,
            )
            catalog_dependencies = _rows(
                cursor,
                f"""
                SELECT DISTINCT rs.name AS referencing_schema,ro.name AS referencing_object,
                       COALESCE(ds.name,d.referenced_schema_name) AS referenced_schema,
                       COALESCE(do.name,d.referenced_entity_name) AS referenced_object
                FROM sys.sql_expression_dependencies d
                JOIN sys.objects ro ON ro.object_id=d.referencing_id
                JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
                LEFT JOIN sys.objects do ON do.object_id=d.referenced_id
                LEFT JOIN sys.schemas ds ON ds.schema_id=do.schema_id
                WHERE ro.name IN ({view_placeholders})
                ORDER BY ro.name,referenced_schema,referenced_object
                """,
                view_names,
            )
            summary_object = next(
                (row for row in catalog_objects if row["name"] == SUMMARY_COMMAND),
                None,
            )
            summary_object_id = (
                int(summary_object["object_id"])
                if summary_object is not None
                else -1
            )
            summary_parameters = [] if summary_object_id < 0 else _rows(
                cursor,
                """
                SELECT parameter_id,name,TYPE_NAME(user_type_id) AS data_type,
                       max_length,precision,scale,is_output
                FROM sys.parameters
                WHERE object_id=%s
                ORDER BY parameter_id
                """,
                (summary_object_id,),
            )
            summary_dependencies = [] if summary_object_id < 0 else _rows(
                cursor,
                """
                SELECT DISTINCT
                       COALESCE(ds.name,d.referenced_schema_name) AS referenced_schema,
                       COALESCE(do.name,d.referenced_entity_name) AS referenced_object,
                       do.type_desc AS referenced_type_desc,
                       d.is_ambiguous
                FROM sys.sql_expression_dependencies d
                LEFT JOIN sys.objects do ON do.object_id=d.referenced_id
                LEFT JOIN sys.schemas ds ON ds.schema_id=do.schema_id
                WHERE d.referencing_id=%s
                ORDER BY referenced_schema,referenced_object
                """,
                (summary_object_id,),
            )

    expected_mappings = [
        {
            "type_discriminator": discriminator,
            "typed_reference_property": property_name,
        }
        for discriminator, property_name in DISCRIMINATOR_TO_SETTER.items()
    ]
    actual_mappings = [
        {
            "type_discriminator": row["type_discriminator"],
            "typed_reference_property": row["typed_reference_property"],
        }
        for row in dispatch["typed_reference_mappings"]
    ]
    form_errors = form_analysis["method_body_errors"]
    data_errors = data_analysis["method_body_errors"]
    catalog_names = {row["name"] for row in catalog_objects}
    errors: list[str] = []
    if hash_mismatches:
        errors.append("source package hash mismatch")
    if len(method_contracts) != 15:
        errors.append("matching method coverage incomplete")
    if actual_mappings != expected_mappings:
        errors.append("typed discriminator mapping changed")
    if any(set(columns) != AMOUNT_COLUMNS for columns in amount_columns_by_event.values()):
        errors.append("matching amount column contract changed")
    for event_name in amount_columns_by_event:
        calls = form_by_name[event_name]["calls"]
        if not all(
            any(call.endswith(suffix) for call in calls)
            for suffix in (
                "DoVocherPass",
                "RefreshGrids",
                "RefreshSummary",
                "Decimal.op_Equality",
                "Math.Abs",
            )
        ):
            errors.append(f"matching event call contract changed: {event_name}")
    if set(observed_hook_names) != set(HOOK_NAMES):
        errors.append("ReconcileItem hook name contract changed")
    if not {"FreeBankAccountCardex", "FreeBankBill", "BankBill2", "ReconcileItem"}.issubset(catalog_names):
        errors.append("matching catalog object coverage incomplete")
    actual_summary_parameters = [
        (row["name"], row["data_type"], bool(row["is_output"]))
        for row in summary_parameters
    ]
    if actual_summary_parameters != list(SUMMARY_PARAMETER_CONTRACT):
        errors.append("summary procedure parameter contract changed")
    if not _has_call(summary_method, "DbCommand.ExecuteNonQuery"):
        errors.append("summary execution method contract changed")
    if context["updateability"] != "READ_ONLY" or context["can_update"] != 0:
        errors.append("unsafe clone target")
    if form_errors or data_errors:
        errors.append("target method body parse failure")

    empty_grid_delete_handlers = [
        name
        for name in ("vGrid_DeletingRecords", "vGrid_RecordsDeleted")
        if form_by_name[name]["instruction_count"] == 1
        and not form_by_name[name]["calls"]
    ]
    artifact = {
        "artifact": "varanegar_bank_reconciliation_matching_ui_dataaccess_catalog_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {
            "server": SERVER,
            "database": DATABASE,
            "snapshot_kind": "READ_ONLY_CLONE_AND_STATIC_IL",
        },
        "safety": {
            "mode": "READ_ONLY_ALLOWLISTED_IL_AND_SQL_SYSTEM_CATALOG_METADATA",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "assemblies_loaded_or_executed": 0,
            "forms_or_application_commands_executed": 0,
            "procedures_hooks_or_triggers_executed": 0,
            "business_rows_or_values_read_or_persisted": 0,
            "sql_module_definitions_persisted": 0,
            "unknown_string_literal_values_persisted": 0,
        },
        "summary": {
            "selected_method_contract_count": len(method_contracts),
            "typed_reference_mapping_count": len(actual_mappings),
            "matching_event_count": len(amount_columns_by_event),
            "matching_amount_column_count": len(AMOUNT_COLUMNS),
            "empty_grid_delete_handler_count": len(empty_grid_delete_handlers),
            "allowlisted_hook_name_count": len(observed_hook_names),
            "clone_present_hook_count": len(set(HOOK_NAMES) & catalog_names),
            "catalog_object_count": len(catalog_objects),
            "catalog_view_column_count": len(catalog_columns),
            "catalog_dependency_count": len(catalog_dependencies),
            "summary_parameter_count": len(summary_parameters),
            "summary_dependency_count": len(summary_dependencies),
            "source_hash_mismatch_count": len(hash_mismatches),
            "method_body_error_count": len(form_errors) + len(data_errors),
            "validation_error_count": len(errors),
        },
        "source_hashes": [
            {
                "assembly": name,
                "sha256": digest,
                "inventory_sha256_match": name not in hash_mismatches,
            }
            for name, digest in sorted(source_hashes.items())
        ],
        "method_contracts": method_contracts,
        "matching_dispatch": dispatch,
        "matching_event_contracts": [
            {
                "event": event_name,
                "amount_columns": columns,
                "exact_decimal_equality_signal_observed": True,
                "absolute_difference_signal_observed": True,
                "confirmation_prompt_call_observed": _has_call(
                    form_by_name[event_name], "Question.Default"
                ),
                "immediate_link_persistence_call_observed": _has_call(
                    form_by_name[event_name], "DoVocherPass"
                ),
                "refresh_after_match_calls_observed": all(
                    _has_call(form_by_name[event_name], suffix)
                    for suffix in ("RefreshGrids", "RefreshSummary")
                ),
            }
            for event_name, columns in amount_columns_by_event.items()
        ],
        "read_model_contract": {
            "refresh_method": "frmReconciliation.RefreshGrids",
            "adapter_calls": sorted(
                call
                for call in form_by_name["RefreshGrids"]["calls"]
                if call.startswith("TreasuryOld.DataLayer.")
            ),
            "allowlisted_filter_literals": refresh_filter_literals,
            "catalog_views": [
                row for row in catalog_objects if row["name"] in {"FreeBankAccountCardex", "FreeBankBill", "BankBill2"}
            ],
            "catalog_view_columns": catalog_columns,
            "catalog_dependencies": catalog_dependencies,
            "summary_call": "TreasuryOld.DataLayer.ReconcileAdapter.GetSummary",
        },
        "summary_boundary": {
            "legacy_command": f"dbo.{SUMMARY_COMMAND}",
            "method_contract": _contract(SUMMARY_ADAPTER_TYPE, summary_method),
            "catalog_object": summary_object,
            "catalog_parameters": [
                {
                    "ordinal": int(row["parameter_id"]),
                    "name": row["name"],
                    "data_type": row["data_type"],
                    "max_length": int(row["max_length"]),
                    "precision": int(row["precision"]),
                    "scale": int(row["scale"]),
                    "is_output": bool(row["is_output"]),
                }
                for row in summary_parameters
            ],
            "catalog_dependencies": [
                {
                    **row,
                    "is_ambiguous": bool(row["is_ambiguous"]),
                }
                for row in summary_dependencies
            ],
            "input_scope": ["ReconcileId", "VocherDate", "BankAccountId"],
            "output_metric_names_are_catalog_confirmed": True,
            "output_formula_semantics_confirmed": False,
            "module_definition_read_or_persisted": False,
        },
        "persistence_contract": {
            "legacy_ui_event_calls_link_update_immediately": True,
            "reconcile_item_update_owns_nested_static_transaction": True,
            "optional_hook_names_observed_in_il": observed_hook_names,
            "optional_hooks_present_in_clone": sorted(set(HOOK_NAMES) & catalog_names),
            "empty_grid_delete_handlers": empty_grid_delete_handlers,
            "unmatch_surface": "btnDelete_Click -> BankBillAdapter.DeleteReconcileItem",
        },
        "target_contract": {
            "command": "bank_reconciliation.match_instrument",
            "queries": [
                "bank_reconciliation.unmatched_statement_rows",
                "bank_reconciliation.match_candidates",
                "bank_reconciliation.summary",
            ],
            "summary_query_returns_named_money_metrics_without_exposing_legacy_procedure": True,
            "summary_formula_parity_requires_fixture_or_owner_validation": True,
            "typed_source_mapping": DISCRIMINATOR_TO_SETTER,
            "direct_grid_event_persistence_allowed": False,
            "explicit_user_command_required": True,
            "exactly_one_typed_source_reference_required": True,
            "account_and_as_of_date_scope_required": True,
            "amount_parity_rule_requires_owner_review_and_golden_cases": True,
            "single_application_service_transaction_owner_required": True,
            "repository_level_commit_allowed": False,
            "idempotency_and_optimistic_version_required": True,
            "audit_and_outbox_in_same_local_transaction": True,
            "optional_runtime_hook_discovery_allowed": False,
            "unmatch_is_separate_command": True,
        },
        "source_hash_mismatches": hash_mismatches,
        "method_body_errors": form_errors + data_errors,
        "validation_errors": errors,
        "limits": [
            "Static IL proves the legacy call and branch shape, not an authenticated UI outcome or successful commit.",
            "Exact decimal comparison signals are observed, but owner-approved tolerance and currency policy remain target decisions.",
            "Catalog dependencies and columns do not prove row-level parity, selectivity, performance, or current operational data.",
            "No raw unknown literal, SQL definition, business value, identity, connection string, or credential is persisted.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], "summary": artifact["summary"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
