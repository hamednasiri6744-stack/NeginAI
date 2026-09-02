"""Extract redacted mutation semantics of reconciliation confirmation cardex update.

The definition is read and parsed in memory from the read-only clone. The
procedure is never executed and no business rows are selected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_extension_sql_semantics import _mask_comments_and_strings
from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


OBJECT_NAME = "dbo.DoReconcile_UpdateBankAccountCardex"
EXPECTED_UPDATES = (
    ("PCheque", "PChequeID", "PChequeID", 1),
    ("PWithDraw", "PWithDrawId", "PWithDrawId", 2),
    ("RBankDraft", "RBankDraftId", "RBankDraftId", 3),
    ("RCashDraft", "RCashDraftId", "RCashDraftId", 4),
    ("RCheque", "RChequeId", "RChequeId", 5),
    ("Transfer", "TransferId", "TransferId", 6),
)


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
    update_pattern = re.compile(
        r"UPDATE\s+(\w+)\s+SET\s+IsReconciled\s*=\s*1\s+WHERE\s+(\w+)\s*=\s*@(\w+).*?SET\s+@ErrorNo\s*=\s*(\d+)\s+return.*?SET\s+@ErrorNo\s*=\s*0\s+return",
        re.IGNORECASE | re.DOTALL,
    )
    updates = tuple(
        (match.group(1), match.group(2), match.group(3), int(match.group(4)))
        for match in update_pattern.finditer(masked)
    )
    mutation_contracts = [
        {
            "source_reference": variable,
            "target_table": table,
            "target_key": key,
            "mutation": "IsReconciled=1",
            "zero_row_error_code": error_code,
            "success_error_code": 0,
            "returns_after_zero_row": True,
            "returns_after_success": True,
        }
        for table, key, variable, error_code in updates
    ]

    keyword_counts = {
        "cursor": len(re.findall(r"\bCURSOR\b", masked, re.IGNORECASE)),
        "fetch_next": len(re.findall(r"\bFETCH\s+NEXT\b", masked, re.IGNORECASE)),
        "while": len(re.findall(r"\bWHILE\b", masked, re.IGNORECASE)),
        "update": len(re.findall(r"\bUPDATE\b", masked, re.IGNORECASE)),
        "return": len(re.findall(r"\bRETURN\b", masked, re.IGNORECASE)),
        "rowcount": len(re.findall(r"@@ROWCOUNT", masked, re.IGNORECASE)),
        "order_by": len(re.findall(r"\bORDER\s+BY\b", masked, re.IGNORECASE)),
        "begin_transaction": len(re.findall(r"\bBEGIN\s+TRAN(?:SACTION)?\b", masked, re.IGNORECASE)),
        "commit": len(re.findall(r"\bCOMMIT\b", masked, re.IGNORECASE)),
        "rollback": len(re.findall(r"\bROLLBACK\b", masked, re.IGNORECASE)),
    }
    cursor_scope_confirmed = bool(
        re.search(
            r"FROM\s+BankBill\s+INNER\s+JOIN\s+ReconcileItem\s+ON\s+BankBill\.BankBillId\s*=\s*ReconcileItem\.BankBillId\s+WHERE\s+BankBill\.ReconcileId\s*=\s*@ReconcileId",
            masked,
            re.IGNORECASE | re.DOTALL,
        )
    )
    validation_errors: list[str] = []
    if row["is_encrypted"]:
        validation_errors.append("cardex procedure unexpectedly encrypted")
    if not definition:
        validation_errors.append("cardex procedure definition unavailable")
    if updates != EXPECTED_UPDATES:
        validation_errors.append("typed update/error mapping changed")
    if not cursor_scope_confirmed:
        validation_errors.append("cursor ReconcileId scope changed")
    expected_keywords = {
        "cursor": 1,
        "fetch_next": 2,
        "while": 1,
        "update": 6,
        "return": 12,
        "rowcount": 6,
        "order_by": 0,
        "begin_transaction": 0,
        "commit": 0,
        "rollback": 0,
    }
    for name, expected in expected_keywords.items():
        if keyword_counts[name] != expected:
            validation_errors.append(
                f"{name}: expected {expected}, got {keyword_counts[name]}"
            )

    summary = {
        "catalog_object_count": 1,
        "parameter_count": len(parameters),
        "dependency_count": len(dependencies),
        "typed_update_branch_count": len(mutation_contracts),
        "cursor_count": keyword_counts["cursor"],
        "fetch_next_count": keyword_counts["fetch_next"],
        "return_count": keyword_counts["return"],
        "unordered_cursor_count": int(keyword_counts["cursor"] > 0 and keyword_counts["order_by"] == 0),
        "explicit_transaction_statement_count": keyword_counts["begin_transaction"] + keyword_counts["commit"] + keyword_counts["rollback"],
        "maximum_typed_link_updates_per_execution": 1,
        "definition_length": len(definition),
        "definition_persisted_count": 0,
        "business_row_value_read_count": 0,
        "procedure_execution_count": 0,
        "validation_error_count": len(validation_errors),
    }
    artifact = {
        "artifact": "varanegar_bank_reconciliation_confirm_cardex_redacted_mutation_semantics",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not validation_errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_CLONE_DEFINITION_IN_MEMORY_REDACTED_MUTATION_PARSE",
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
        "cursor_contract": {
            "source": "BankBill INNER JOIN ReconcileItem",
            "scope": "BankBill.ReconcileId=@ReconcileId",
            "typed_reference_order": [row[2] for row in EXPECTED_UPDATES],
            "order_by_present": False,
            "exactly_one_typed_reference_per_link_required_by_target": True,
        },
        "mutation_contracts": mutation_contracts,
        "early_return_defect": {
            "return_in_zero_row_branch_count": len(mutation_contracts),
            "return_in_success_branch_count": len(mutation_contracts),
            "fetch_next_reached_after_any_typed_branch": False,
            "maximum_typed_link_updates_per_execution": 1,
            "which_link_is_processed_is_deterministic_when_multiple_links_exist": False,
            "reason": "the unordered cursor returns from both outcomes of the first non-null typed branch",
        },
        "transaction_contract": {
            "procedure_has_explicit_transaction": False,
            "legacy_caller_static_transaction_wrapper_required": True,
            "procedure_itself_guarantees_atomic_confirm_state_and_all_link_updates": False,
        },
        "target_contract": {
            "copy_cursor_or_early_return_behavior": False,
            "load_all_scoped_typed_links_before_mutation": True,
            "reject_zero_or_multiple_typed_references_per_link": True,
            "update_every_link_or_roll_back_everything": True,
            "expected_affected_count_equals_distinct_link_count": True,
            "missing_or_conflicting_instrument_is_a_stable_domain_error": True,
            "already_reconciled_instrument_policy_requires_owner_approval": True,
            "confirm_state_all_instrument_updates_audit_and_outbox_share_one_transaction": True,
            "failure_injection_after_each_instrument_type_and_before_commit": True,
            "legacy_result_parity_does_not_mean_reproducing_the_one_link_defect": True,
        },
        "validation_errors": validation_errors,
        "limits": [
            "The procedure definition was parsed but never executed; no cursor result or row value was read.",
            "The one-link maximum is a static control-flow result for the current definition.",
            "Actual production impact requires aggregate-only counts or owner-approved fixtures; none are claimed here.",
            "The target must preserve intended all-link reconciliation, not the legacy early-return defect.",
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
