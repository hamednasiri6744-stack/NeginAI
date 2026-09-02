"""Extract redacted SQL semantics of the bank-bill unmatch procedure."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from extract_varanegar_extension_sql_semantics import _mask_comments_and_strings
from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


OBJECT_NAME = "dbo.DoBankBill_DeleteReconcileItem"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            identity = _rows(
                cursor,
                """
                SELECT o.object_id,s.name AS schema_name,o.name AS object_name,o.type_desc,
                       OBJECTPROPERTYEX(o.object_id,'IsEncrypted') AS is_encrypted,m.definition
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(%s)
                """,
                (OBJECT_NAME,),
            )
            if not identity:
                raise ValueError(f"required object missing: {OBJECT_NAME}")
            row = identity[0]
            object_id = int(row.pop("object_id"))
            definition = row.pop("definition") or ""
            parameters = _rows(
                cursor,
                """
                SELECT p.parameter_id,p.name AS parameter_name,TYPE_NAME(p.user_type_id) AS data_type,
                       p.max_length,p.precision,p.scale,p.is_output
                FROM sys.parameters p WHERE p.object_id=%s ORDER BY p.parameter_id
                """,
                (object_id,),
            )
            dependencies = _rows(
                cursor,
                """
                SELECT DISTINCT COALESCE(d.referenced_schema_name,OBJECT_SCHEMA_NAME(d.referenced_id)) AS schema_name,
                       COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) AS object_name,
                       COALESCE(o.type_desc,'UNRESOLVED_OR_COLUMN_REFERENCE') AS type_desc
                FROM sys.sql_expression_dependencies d
                LEFT JOIN sys.objects o ON o.object_id=d.referenced_id
                WHERE d.referencing_id=%s
                  AND COALESCE(d.referenced_entity_name,OBJECT_NAME(d.referenced_id)) IS NOT NULL
                ORDER BY schema_name,object_name,type_desc
                """,
                (object_id,),
            )

    masked = _mask_comments_and_strings(definition)
    delete_match = re.search(
        r"DELETE\s+(?:dbo\.)?ReconcileItem\s+WHERE\s+BankBillId\s*=\s*@BankBillId",
        masked,
        re.IGNORECASE,
    )
    error_match = re.search(
        r"IF\s+@@ROWCOUNT\s*=\s*0.*?SET\s+@ErrorNo\s*=\s*1\s+return.*?SET\s+@ErrorNo\s*=\s*0",
        masked,
        re.IGNORECASE | re.DOTALL,
    )
    keyword_counts = {
        name: len(re.findall(rf"\b{name}\b", masked, re.IGNORECASE))
        for name in ("DELETE", "UPDATE", "INSERT", "MERGE", "RETURN")
    }
    validation_errors: list[str] = []
    if row["is_encrypted"]:
        validation_errors.append("unmatch procedure unexpectedly encrypted")
    if not definition:
        validation_errors.append("unmatch procedure definition unavailable")
    if not delete_match:
        validation_errors.append("BankBillId-scoped ReconcileItem delete changed")
    if not error_match:
        validation_errors.append("ErrorNo contract changed")
    if keyword_counts != {"DELETE": 1, "UPDATE": 0, "INSERT": 0, "MERGE": 0, "RETURN": 1}:
        validation_errors.append(f"mutation/return keyword contract changed: {keyword_counts}")

    summary = {
        "catalog_object_count": 1,
        "parameter_count": len(parameters),
        "dependency_count": len(dependencies),
        "delete_statement_count": keyword_counts["DELETE"],
        "instrument_update_statement_count": keyword_counts["UPDATE"],
        "bank_bill_scope_column_count": int(bool(delete_match)),
        "link_id_scope_column_count": 0,
        "reconcile_or_account_scope_column_count": 0,
        "explicit_transaction_statement_count": len(
            re.findall(r"\b(?:BEGIN\s+TRAN(?:SACTION)?|COMMIT|ROLLBACK)\b", masked, re.IGNORECASE)
        ),
        "definition_length": len(definition),
        "definition_persisted_count": 0,
        "business_row_value_read_count": 0,
        "procedure_execution_count": 0,
        "validation_error_count": len(validation_errors),
    }
    artifact = {
        "artifact": "varanegar_bank_reconciliation_unmatch_redacted_sql_delete_semantics",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_CLONE_DEFINITION_IN_MEMORY_REDACTED_DELETE_PARSE",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_definitions_persisted": 0,
            "string_literals_persisted": 0,
            "procedures_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": summary,
        "catalog_object": {
            **row,
            "definition_length": len(definition),
            "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest(),
            "definition_persisted": False,
        },
        "parameters": parameters,
        "dependencies": dependencies,
        "delete_contract": {
            "target": "dbo.ReconcileItem",
            "predicate": "BankBillId=@BankBillId",
            "deletes_one_specific_reconcile_item_by_link_id": False,
            "deletes_all_reconcile_items_for_bank_bill": True,
            "zero_rows_sets_error_no": 1,
            "one_or_more_rows_sets_error_no": 0,
            "affected_row_count_returned": False,
        },
        "missing_side_effects": {
            "instrument_is_reconciled_reset": False,
            "reconcile_header_state_transition": False,
            "audit_append": False,
            "outbox_append": False,
        },
        "confirmed_state_risk": {
            "confirmed_session_unmatch_can_be_proven_safe": False,
            "link_delete_can_leave_instrument_is_reconciled_true": True,
            "reverse_confirmed_session_is_equivalent_to_this_delete": False,
        },
        "target_contract": {
            "unmatch_allowed_state": "IMPORTED_UNCONFIRMED",
            "unmatch_uses_link_id_and_expected_version": True,
            "bank_bill_has_at_most_one_active_link_invariant_required": True,
            "unmatch_returns_typed_not_found_or_conflict_reason": True,
            "confirmed_session_uses_separate_owner_approved_reversal": True,
            "reversal_resets_every_instrument_and_session_state_atomically": True,
            "legacy_procedure_direct_execution_allowed": False,
        },
        "validation_errors": validation_errors,
        "limits": [
            "The procedure definition was parsed but never executed and no affected-row count was observed.",
            "The schema does not prove one link per BankBill; target uniqueness needs an explicit invariant.",
            "No distinct legacy cancel or confirmed-session reversal command is established.",
            "The target must not use link deletion as a confirmed-session reversal.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"validation": artifact["validation"], "summary": summary}, ensure_ascii=False))
    return 0 if not validation_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
