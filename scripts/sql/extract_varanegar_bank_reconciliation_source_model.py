"""Extract the clone catalog model behind legacy bank reconciliation.

Read-only by design. The extractor persists schema metadata, aggregate row
counts, aggregate link-shape counts, and redacted static UI call evidence. It
does not persist bank statement rows, account/cheque identifiers, comments,
file contents, users, credentials, or SQL/trigger definitions.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


TABLES = (
    "Reconcile",
    "ReconcileItem",
    "ReconcileDetail",
    "BankBill",
    "BankBillFormat",
    "BankBillFormatItem",
    "BankBillFormatType",
    "ReconciliationColumn",
    "BankAccount",
    "PCheque",
    "PWithdraw",
    "RBankDraft",
    "RCashDraft",
    "RCheque",
    "Transfer",
)

CORE_TABLES = {
    "Reconcile",
    "ReconcileItem",
    "ReconcileDetail",
    "BankBill",
    "BankBillFormat",
    "BankBillFormatItem",
    "BankBillFormatType",
    "ReconciliationColumn",
}

MATCHING_REFERENCE_COLUMNS = (
    "BankBillId",
    "PChequeId",
    "PWithdrawId",
    "RBankDraftId",
    "RCashDraftId",
    "RChequeId",
    "TransferId",
)

TARGET_FORMS = (
    "TreasuryOld.Forms.frmBankReconciliationList",
    "TreasuryOld.Forms.frmBankReconciliation",
    "TreasuryOld.Forms.frmReconciliationSetup",
    "TreasuryOld.Forms.frmReconciliation",
)

DATA_LAYER_TYPES = (
    "TreasuryOld.DataLayer.Reconcile",
    "TreasuryOld.DataLayer.ReconcileAdapter",
    "TreasuryOld.DataLayer.ReconcileItemAdapter",
    "TreasuryOld.DataLayer.BankBill",
    "TreasuryOld.DataLayer.BankBillAdapter",
    "TreasuryOld.DataLayer.BankAccountAdapter",
)


def _load_call_graph(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if payload.get("summary", {}).get("source_hash_mismatch_count") != 0:
        raise RuntimeError("Priority-gap call graph has source hash mismatches.")
    return payload


def _ui_contracts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    by_type = {
        row["type"]: row
        for row in payload.get("priority_form_contracts", [])
        if row.get("type") in TARGET_FORMS
    }
    return [
        {
            "type": form_type,
            "page_shape": by_type[form_type]["page_shape"],
            "write_like_methods": by_type[form_type]["contract"]["write_like_methods"],
            "destructive_or_reversing_methods": by_type[form_type]["contract"]["destructive_or_reversing_methods"],
            "validation_methods": by_type[form_type]["contract"]["validation_methods"],
            "permission_methods": by_type[form_type]["contract"]["permission_methods"],
            "external_contract_calls": by_type[form_type]["contract"]["external_contract_calls"],
        }
        for form_type in TARGET_FORMS
        if form_type in by_type
    ]


def _data_layer_contracts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    by_type = {
        row["type"]: row
        for row in payload.get("treasury_data_layer_contracts", [])
        if row.get("type") in DATA_LAYER_TYPES and row.get("found")
    }
    return [
        {
            "type": type_name,
            "definition_assembly": by_type[type_name]["definition_assembly"],
            "write_like_methods": by_type[type_name]["contract"]["write_like_methods"],
            "destructive_or_reversing_methods": by_type[type_name]["contract"]["destructive_or_reversing_methods"],
            "permission_methods": by_type[type_name]["contract"]["permission_methods"],
            "external_contract_calls": by_type[type_name]["contract"]["external_contract_calls"],
        }
        for type_name in DATA_LAYER_TYPES
        if type_name in by_type
    ]


def _link_shape_summary(cursor: Any, available_columns: set[str]) -> dict[str, Any]:
    source_columns = [
        name for name in MATCHING_REFERENCE_COLUMNS[1:] if name.casefold() in available_columns
    ]
    if not source_columns:
        return {
            "total_link_rows": 0,
            "zero_source_reference_rows": 0,
            "exactly_one_source_reference_rows": 0,
            "multiple_source_reference_rows": 0,
            "source_reference_columns": [],
        }
    terms = " + ".join(f"CASE WHEN [{name}] IS NULL THEN 0 ELSE 1 END" for name in source_columns)
    row = _rows(
        cursor,
        f"""
        SELECT COUNT_BIG(*) AS total_link_rows,
               SUM(CASE WHEN ({terms})=0 THEN 1 ELSE 0 END) AS zero_source_reference_rows,
               SUM(CASE WHEN ({terms})=1 THEN 1 ELSE 0 END) AS exactly_one_source_reference_rows,
               SUM(CASE WHEN ({terms})>1 THEN 1 ELSE 0 END) AS multiple_source_reference_rows
        FROM dbo.ReconcileItem
        """,
    )[0]
    return {
        "total_link_rows": int(row["total_link_rows"] or 0),
        "zero_source_reference_rows": int(row["zero_source_reference_rows"] or 0),
        "exactly_one_source_reference_rows": int(row["exactly_one_source_reference_rows"] or 0),
        "multiple_source_reference_rows": int(row["multiple_source_reference_rows"] or 0),
        "source_reference_columns": source_columns,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--call-graph", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    call_graph = _load_call_graph(args.call_graph)
    ui_contracts = _ui_contracts(call_graph)
    data_layer_contracts = _data_layer_contracts(call_graph)
    placeholders = ",".join("%s" for _ in TABLES)

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            table_rows = _rows(
                cursor,
                f"""
                SELECT o.object_id,s.name AS schema_name,o.name AS table_name,o.type_desc,
                       SUM(CASE WHEN o.type='U' AND p.index_id IN (0,1) THEN p.rows ELSE 0 END) AS row_count
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                LEFT JOIN sys.partitions p ON p.object_id=o.object_id
                WHERE o.type IN ('U','V') AND s.name='dbo' AND o.name IN ({placeholders})
                GROUP BY o.object_id,s.name,o.name,o.type_desc
                """,
                TABLES,
            )
            object_ids = [int(row["object_id"]) for row in table_rows]
            if object_ids:
                id_marks = ",".join("%s" for _ in object_ids)
                column_rows = _rows(
                    cursor,
                    f"""
                    SELECT c.object_id,c.column_id,c.name AS column_name,t.name AS data_type,
                           c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,c.is_computed
                    FROM sys.columns c
                    JOIN sys.types t ON t.user_type_id=c.user_type_id
                    WHERE c.object_id IN ({id_marks})
                    ORDER BY c.object_id,c.column_id
                    """,
                    object_ids,
                )
                key_rows = _rows(
                    cursor,
                    f"""
                    SELECT i.object_id,i.name AS index_name,i.is_primary_key,i.is_unique,
                           ic.key_ordinal,c.name AS column_name
                    FROM sys.indexes i
                    JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
                    JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
                    WHERE i.object_id IN ({id_marks}) AND (i.is_primary_key=1 OR i.is_unique=1)
                      AND ic.is_included_column=0
                    ORDER BY i.object_id,i.name,ic.key_ordinal
                    """,
                    object_ids,
                )
                fk_rows = _rows(
                    cursor,
                    f"""
                    SELECT fk.name AS foreign_key_name,
                           ps.name AS parent_schema,po.name AS parent_table,pc.name AS parent_column,
                           rs.name AS referenced_schema,ro.name AS referenced_table,rc.name AS referenced_column,
                           fkc.constraint_column_id,fk.is_disabled,fk.is_not_trusted,
                           CASE WHEN po.object_id IN ({id_marks}) THEN 1 ELSE 0 END AS parent_in_scope,
                           CASE WHEN ro.object_id IN ({id_marks}) THEN 1 ELSE 0 END AS referenced_in_scope
                    FROM sys.foreign_keys fk
                    JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
                    JOIN sys.objects po ON po.object_id=fk.parent_object_id
                    JOIN sys.schemas ps ON ps.schema_id=po.schema_id
                    JOIN sys.columns pc ON pc.object_id=po.object_id AND pc.column_id=fkc.parent_column_id
                    JOIN sys.objects ro ON ro.object_id=fk.referenced_object_id
                    JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
                    JOIN sys.columns rc ON rc.object_id=ro.object_id AND rc.column_id=fkc.referenced_column_id
                    WHERE po.object_id IN ({id_marks}) OR ro.object_id IN ({id_marks})
                    ORDER BY fk.name,fkc.constraint_column_id
                    """,
                    object_ids + object_ids + object_ids + object_ids,
                )
                trigger_rows = _rows(
                    cursor,
                    f"""
                    SELECT tr.parent_id AS object_id,tr.name AS trigger_name,tr.is_disabled,
                           OBJECTPROPERTY(tr.object_id,'ExecIsInsertTrigger') AS is_insert_trigger,
                           OBJECTPROPERTY(tr.object_id,'ExecIsUpdateTrigger') AS is_update_trigger,
                           OBJECTPROPERTY(tr.object_id,'ExecIsDeleteTrigger') AS is_delete_trigger,
                           CASE WHEN m.object_id IS NULL THEN 0 ELSE 1 END AS definition_present
                    FROM sys.triggers tr
                    LEFT JOIN sys.sql_modules m ON m.object_id=tr.object_id
                    WHERE tr.parent_id IN ({id_marks})
                    ORDER BY tr.parent_id,tr.name
                    """,
                    object_ids,
                )
            else:
                column_rows, key_rows, fk_rows, trigger_rows = [], [], [], []

            reconcile_item_id = next(
                (int(row["object_id"]) for row in table_rows if row["table_name"].casefold() == "reconcileitem"),
                None,
            )
            reconcile_item_columns = {
                row["column_name"].casefold()
                for row in column_rows
                if reconcile_item_id is not None and int(row["object_id"]) == reconcile_item_id
            }
            link_shape = _link_shape_summary(cursor, reconcile_item_columns)

    table_name_by_id = {
        int(row["object_id"]): f"{row['schema_name']}.{row['table_name']}" for row in table_rows
    }
    columns_by_id: dict[int, list[dict[str, Any]]] = {object_id: [] for object_id in object_ids}
    for row in column_rows:
        columns_by_id[int(row["object_id"])].append(
            {
                "ordinal": int(row["column_id"]),
                "name": row["column_name"],
                "data_type": row["data_type"],
                "max_length": int(row["max_length"]),
                "precision": int(row["precision"]),
                "scale": int(row["scale"]),
                "nullable": bool(row["is_nullable"]),
                "identity": bool(row["is_identity"]),
                "computed": bool(row["is_computed"]),
            }
        )

    keys_by_id: dict[int, dict[str, dict[str, Any]]] = {object_id: {} for object_id in object_ids}
    for row in key_rows:
        key = keys_by_id[int(row["object_id"])].setdefault(
            row["index_name"],
            {
                "name": row["index_name"],
                "primary_key": bool(row["is_primary_key"]),
                "unique": bool(row["is_unique"]),
                "columns": [],
            },
        )
        key["columns"].append(row["column_name"])

    triggers_by_id: dict[int, list[dict[str, Any]]] = {object_id: [] for object_id in object_ids}
    for row in trigger_rows:
        triggers_by_id[int(row["object_id"])].append(
            {
                "name": row["trigger_name"],
                "disabled": bool(row["is_disabled"]),
                "events": [
                    event
                    for event, flag in (
                        ("INSERT", row["is_insert_trigger"]),
                        ("UPDATE", row["is_update_trigger"]),
                        ("DELETE", row["is_delete_trigger"]),
                    )
                    if flag
                ],
                "definition_present": bool(row["definition_present"]),
                "definition_persisted": False,
            }
        )

    tables = []
    for row in sorted(table_rows, key=lambda value: value["table_name"].casefold()):
        object_id = int(row["object_id"])
        table_columns = columns_by_id[object_id]
        column_names = {column["name"].casefold() for column in table_columns}
        tables.append(
            {
                "object": table_name_by_id[object_id],
                "object_type": row["type_desc"],
                "aggregate_role": (
                    "bank_reconciliation_core" if row["table_name"] in CORE_TABLES else "typed_matching_source"
                ),
                "row_count_snapshot": int(row["row_count"] or 0),
                "column_count": len(table_columns),
                "columns": table_columns,
                "keys": list(keys_by_id[object_id].values()),
                "triggers": triggers_by_id[object_id],
                "candidate_role_signals": {
                    "reconciliation_header": "reconcileid" in column_names,
                    "bank_statement_row": "bankbillid" in column_names,
                    "bank_account_scope": "bankaccountid" in column_names,
                    "business_date_signal": any("date" in name for name in column_names),
                    "amount_or_balance_signal": any(
                        token in name for name in column_names for token in ("amount", "balance", "debit", "credit")
                    ),
                    "source_version_signal": any(
                        name in column_names for name in ("rowversion", "timestamp", "version")
                    ),
                },
            }
        )

    foreign_keys = [
        {
            "name": row["foreign_key_name"],
            "from": f"{row['parent_schema']}.{row['parent_table']}.{row['parent_column']}",
            "to": f"{row['referenced_schema']}.{row['referenced_table']}.{row['referenced_column']}",
            "ordinal": int(row["constraint_column_id"]),
            "from_in_scope": bool(row["parent_in_scope"]),
            "to_in_scope": bool(row["referenced_in_scope"]),
            "disabled": bool(row["is_disabled"]),
            "not_trusted": bool(row["is_not_trusted"]),
        }
        for row in fk_rows
    ]
    found = {row["object"].split(".", 1)[1].casefold() for row in tables}
    missing = sorted(name for name in TABLES if name.casefold() not in found)
    all_columns = [column for table in tables for column in table["columns"]]
    matching_columns = [
        column
        for column in MATCHING_REFERENCE_COLUMNS
        if column.casefold() in reconcile_item_columns
    ]

    required_ui_calls = {
        "TreasuryOld.DataLayer.Transaction.Start",
        "TreasuryOld.DataLayer.Transaction.Commit",
        "TreasuryOld.DataLayer.Transaction.RollBack",
        "TreasuryOld.DataLayer.ReconcileAdapter.UpdateBankAccountCardex",
        "TreasuryOld.DataLayer.ReconcileItemAdapter.NewReconcileItem",
        "TreasuryOld.DataLayer.BankBillAdapter.NewBankBill",
    }
    observed_ui_calls = {
        call for form in ui_contracts for call in form["external_contract_calls"]
    }
    missing_ui_calls = sorted(required_ui_calls - observed_ui_calls)
    errors = []
    if missing:
        errors.append("requested bank-reconciliation tables missing")
    if len(ui_contracts) != len(TARGET_FORMS):
        errors.append("priority form contracts incomplete")
    if len(data_layer_contracts) != len(DATA_LAYER_TYPES):
        errors.append("bank-reconciliation data-layer contracts incomplete")
    if missing_ui_calls:
        errors.append("required static reconciliation call signals missing")
    if len(matching_columns) < 6:
        errors.append("polymorphic reconciliation reference columns incomplete")

    summary = {
        "requested_table_count": len(TABLES),
        "found_table_count": len(tables),
        "missing_table_count": len(missing),
        "core_table_count": sum(table["aggregate_role"] == "bank_reconciliation_core" for table in tables),
        "typed_matching_source_table_count": sum(table["aggregate_role"] == "typed_matching_source" for table in tables),
        "row_count_snapshot_total": sum(table["row_count_snapshot"] for table in tables),
        "column_count": len(all_columns),
        "primary_or_unique_key_count": sum(len(table["keys"]) for table in tables),
        "foreign_key_column_edge_count": len(foreign_keys),
        "foreign_key_constraint_count": len({row["name"] for row in foreign_keys}),
        "foreign_key_not_trusted_count": len({row["name"] for row in foreign_keys if row["not_trusted"]}),
        "in_scope_foreign_key_constraint_count": len(
            {row["name"] for row in foreign_keys if row["from_in_scope"] and row["to_in_scope"]}
        ),
        "trigger_count": sum(len(table["triggers"]) for table in tables),
        "disabled_trigger_count": sum(
            trigger["disabled"] for table in tables for trigger in table["triggers"]
        ),
        "matching_instrument_column_count": len(matching_columns),
        "ui_contract_count": len(ui_contracts),
        "data_layer_contract_count": len(data_layer_contracts),
        "required_static_ui_call_count": len(required_ui_calls),
        "missing_required_static_ui_call_count": len(missing_ui_calls),
        "data_type_counts": dict(sorted(Counter(column["data_type"] for column in all_columns).items())),
        "definition_persisted_count": 0,
        "business_row_value_persisted_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_bank_reconciliation_clone_source_catalog_model",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {
            "server": SERVER,
            "database": DATABASE,
            "requested_tables": list(TABLES),
            "ui_call_graph": args.call_graph.as_posix(),
        },
        "safety": {
            "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_AND_AGGREGATE_ROW_COUNTS",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_or_trigger_definitions_persisted": 0,
            "procedures_or_triggers_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": summary,
        "tables": tables,
        "foreign_keys": foreign_keys,
        "matching_reference_columns": matching_columns,
        "matching_link_shape_aggregate": link_shape,
        "ui_contracts": ui_contracts,
        "data_layer_contracts": data_layer_contracts,
        "required_static_ui_calls": sorted(required_ui_calls),
        "missing_required_static_ui_calls": missing_ui_calls,
        "target_contract": {
            "aggregate": "BankReconciliationSession",
            "owned_entities": ["ImportedBankStatement", "BankStatementRow", "TypedReconciliationLink"],
            "matching_cardinality": "one bank statement row to zero or more typed reconciliation links",
            "source_reference_policy": "a link identifies its source by an explicit typed reference; multiple populated source references require quarantine",
            "commands": [
                "bank_reconciliation.import_statement",
                "bank_reconciliation.match_instrument",
                "bank_reconciliation.unmatch_instrument",
                "bank_reconciliation.confirm",
                "bank_reconciliation.cancel",
            ],
            "provisional_command_names": ["bank_reconciliation.cancel"],
            "additional_required_command_boundaries": [
                "bank_reconciliation.discard_imported_statement",
                "bank_reconciliation.cancel_session",
                "bank_reconciliation.reverse_confirmed_session",
            ],
            "cancel_legacy_parity_status": "UNPROVEN_NO_DISTINCT_LEGACY_COMMAND_OBSERVED",
            "query_contracts": [
                "bank_reconciliation.sessions",
                "bank_reconciliation.unmatched_statement_rows",
                "bank_reconciliation.match_candidates",
                "bank_reconciliation.summary",
            ],
            "direct_table_crud_allowed": False,
            "required_controls": [
                "deny-first account and command authorization",
                "immutable imported-file identity and row hash",
                "idempotent import and match command ids",
                "single target transaction plus audit/outbox",
                "typed-source and amount/date validation before match",
                "bank-account cardex reconciliation before confirmation",
                "quarantine for zero-source, multi-source, duplicate or ambiguous links",
            ],
        },
        "missing_tables": missing,
        "validation_errors": errors,
        "evidence_limits": [
            "Static call evidence establishes command candidates, not runtime branch or result parity.",
            "Aggregate link-shape counts do not expose statement, account, cheque, amount, comment or user values.",
            "The menu or plugin entrypoint for the setup/list roots remains unresolved after complete active-assembly and deployment exact-reference scans.",
            "Parser, permission catalog, transaction, cardex and delete semantics are statically bounded; real profiles, effective-user UAT, target implementation and runtime parity remain unresolved.",
            "No distinct legacy cancel-session command was observed; cancel remains provisional and separate from unmatch, imported-row discard and confirmed-session reversal.",
            "Clone row counts can be stale relative to operational Varanegar.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
