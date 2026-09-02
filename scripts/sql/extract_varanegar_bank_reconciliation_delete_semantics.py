"""Separate legacy unmatch, imported-row discard, and target session cancel."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _rows,
)


PROCEDURE = "DoBankBill_DeleteReconcileItem"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command-guards", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    guards = _load(args.command_guards)
    if guards.get("validation") != "PASS":
        raise ValueError("validated command-guard artifact is required")
    delete_methods = [
        row for row in guards["method_contracts"] if row["method"] == "btnDelete_Click"
    ]
    by_form = {row["form_type"]: row for row in delete_methods}

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            objects = _rows(
                cursor,
                """
                SELECT o.object_id,s.name AS schema_name,o.name,o.type_desc
                FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE s.name=%s AND o.name=%s AND o.is_ms_shipped=0
                """,
                ("dbo", PROCEDURE),
            )
            object_id = int(objects[0]["object_id"]) if objects else -1
            parameters = [] if object_id < 0 else _rows(
                cursor,
                """
                SELECT parameter_id,name,TYPE_NAME(user_type_id) AS data_type,is_output
                FROM sys.parameters WHERE object_id=%s ORDER BY parameter_id
                """,
                (object_id,),
            )
            dependencies = [] if object_id < 0 else _rows(
                cursor,
                """
                SELECT DISTINCT COALESCE(s.name+'.','')+COALESCE(o.name,d.referenced_entity_name)
                       AS referenced_object,o.type_desc
                FROM sys.sql_expression_dependencies d
                LEFT JOIN sys.objects o ON o.object_id=d.referenced_id
                LEFT JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE d.referencing_id=%s ORDER BY referenced_object
                """,
                (object_id,),
            )

    detail = by_form.get("TreasuryOld.Forms.frmReconciliation")
    setup = by_form.get("TreasuryOld.Forms.frmReconciliationSetup")
    detail_calls = set([] if detail is None else detail["business_calls"])
    setup_calls = set([] if setup is None else setup["business_calls"])
    detail_is_unmatch = {
        "TreasuryOld.DataLayer.BankBillAdapter.DeleteReconcileItem",
        "TreasuryOld.DataLayer.Transaction.Start",
        "TreasuryOld.DataLayer.Transaction.Commit",
        "TreasuryOld.DataLayer.Transaction.RollBack",
    }.issubset(detail_calls)
    setup_is_import_discard = {
        "TreasuryOld.DataLayer.BankBillAdapter.GetBankBillSWhere",
        "TreasuryOld.DataLayer.BankBillS.Delete",
        "TreasuryOld.DataLayer.BankBillS.Update",
        "TreasuryOld.DataLayer.ReconcileItemAdapter.GetReconcileItemSByBankBillS",
    }.issubset(setup_calls)
    setup_mutates_reconcile_header = any(
        call in setup_calls
        for call in (
            "TreasuryOld.DataLayer.Reconcile.Delete",
            "TreasuryOld.DataLayer.Reconcile.Update",
        )
    )

    parameter_rows = [
        {
            "ordinal": int(row["parameter_id"]),
            "name": row["name"],
            "data_type": row["data_type"],
            "is_output": bool(row["is_output"]),
        }
        for row in parameters
    ]
    dependency_rows = [
        {"referenced_object": row["referenced_object"], "object_type_desc": row["type_desc"]}
        for row in dependencies
    ]
    errors: list[str] = []
    if len(delete_methods) != 2:
        errors.append("two legacy delete surfaces were not observed")
    if not detail_is_unmatch:
        errors.append("detail delete/unmatch call contract changed")
    if not setup_is_import_discard or setup_mutates_reconcile_header:
        errors.append("setup imported-row discard contract changed")
    if len(objects) != 1:
        errors.append("unmatch procedure missing")
    if [(row["name"], row["data_type"], row["is_output"]) for row in parameter_rows] != [
        ("@BankBillId", "int", False),
        ("@ErrorNo", "tinyint", True),
    ]:
        errors.append("unmatch procedure signature changed")
    if {row["referenced_object"] for row in dependency_rows} != {"dbo.ReconcileItem"}:
        errors.append("unmatch procedure dependency changed")

    artifact = {
        "artifact": "varanegar_bank_reconciliation_delete_unmatch_discard_semantics",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_REDACTED_IL_CONTRACT_AND_SQL_SYSTEM_CATALOG_METADATA",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "module_definitions_or_business_rows_read_or_persisted": 0,
            "application_or_sql_commands_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": {
            "legacy_delete_surface_count": len(delete_methods),
            "unmatch_procedure_count": len(objects),
            "unmatch_parameter_count": len(parameter_rows),
            "unmatch_dependency_count": len(dependency_rows),
            "session_cancel_legacy_command_observed_count": 0,
            "validation_error_count": len(errors),
        },
        "legacy_delete_surfaces": [
            {
                "form_type": "TreasuryOld.Forms.frmReconciliation",
                "semantic_classification": "UNMATCH_ONE_RECONCILIATION_LINK",
                "explicit_ui_transaction_observed": detail_is_unmatch,
                "calls": [] if detail is None else detail["business_calls"],
            },
            {
                "form_type": "TreasuryOld.Forms.frmReconciliationSetup",
                "semantic_classification": "DISCARD_IMPORTED_BANK_STATEMENT_ROWS_AFTER_LINK_CHECK",
                "reconcile_header_mutation_call_observed": setup_mutates_reconcile_header,
                "calls": [] if setup is None else setup["business_calls"],
            },
        ],
        "unmatch_procedure": {
            "object": "dbo.DoBankBill_DeleteReconcileItem",
            "parameters": parameter_rows,
            "dependencies": dependency_rows,
        },
        "target_contract": {
            "commands_must_remain_distinct": [
                "bank_reconciliation.unmatch_instrument",
                "bank_reconciliation.discard_imported_statement",
                "bank_reconciliation.cancel_session",
                "bank_reconciliation.reverse_confirmed_session",
            ],
            "cancel_session_legacy_parity_status": "UNPROVEN_NO_DISTINCT_LEGACY_COMMAND_OBSERVED",
            "golden_cancel_name_is_provisional_until_process_owner_signoff": True,
            "discard_allowed_when_active_links_exist": False,
            "confirmed_session_requires_explicit_reversal_not_delete": True,
            "legacy_procedure_directly_exposed_to_web": False,
        },
        "validation_errors": errors,
        "limits": [
            "Static call absence does not prove that no dynamic or external cancellation path exists.",
            "The setup delete path is classified from calls; live state branches and user decisions were not observed.",
            "No module definition, business row, form, procedure, transaction or command was read or executed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **artifact["summary"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
