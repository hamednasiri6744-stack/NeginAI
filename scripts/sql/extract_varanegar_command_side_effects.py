"""Extract read-only command-to-SQL side-effect evidence for active pages.

No application procedure is executed. Module definitions are inspected in the
read-only clone, reduced to hashes, statement-kind counts and safe dependency
metadata, then discarded. Raw SQL, literals and business rows are not persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
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


COMMANDS: tuple[dict[str, Any], ...] = (
    {
        "command": "inventory.stock_goods.read",
        "ui_chain": ["FormStockGoods.LoadInitData", "StockGoodsUIHelper.StockGoodsGridServerModeDC"],
        "sql_objects": ["GNR.vwStockGoods_serverMode"],
        "mutation_expected": False,
    },
    {
        "command": "distribution.create_or_update",
        "ui_chain": ["FormDistManagementDataEntry.SaveCommand", "DistHandler.CreateDist", "DistAdapter.CreateDist"],
        "sql_objects": ["SLE.usp_sdsnet_CreateDist", "dbo.GetMaxDistNo"],
        "mutation_expected": True,
    },
    {
        "command": "distribution.issue_exit",
        "ui_chain": ["FormDistManagementList.SetExitexportation", "DistHandler.CreateExitVocherByDist", "DistAdapter.CreateExitVocherByDist"],
        "sql_objects": ["dbo.usp_CreateExitVocherByDist"],
        "mutation_expected": True,
    },
    {
        "command": "distribution.merge_or_adjust_exit",
        "ui_chain": ["FormDistManagementList.MergeGoodsExitData", "DistHandler.MergeGoodsExit", "DistAdapter.MergeGoodsExit"],
        "sql_objects": ["inv.Usp_InsertGoodsExit_RD"],
        "mutation_expected": True,
    },
    {
        "command": "distribution.remove_exit",
        "ui_chain": ["FormDistManagementList.RemoveExitFromDist", "DistHandler.RemoveExitFromDist", "DistAdapter.RemoveExitFromDist"],
        "sql_objects": ["inv.Usp_RemoveExitFromDist"],
        "mutation_expected": True,
    },
    {
        "command": "received_cheque.validate_transition",
        "ui_chain": ["frmRChequeTracking workflow lookup", "RChequeAdapter.RchequeWorkFlow_IsValid"],
        "sql_objects": ["dbo.RchequeWorkFlow_IsValid"],
        "mutation_expected": False,
    },
    {
        "command": "received_cheque.change_status",
        "ui_chain": ["frmRChequeTracking.ChangeStatus", "RChequeAdapter.DoRCheque_AddRChequeHistory"],
        "sql_objects": ["dbo.DoRCheque_AddRChequeHistory"],
        "mutation_expected": True,
    },
    {
        "command": "received_cheque.undo",
        "ui_chain": ["frmRChequeTracking.DoUndo", "RChequeAdapter.DoRCheque_DeleteLastRChequeHistory"],
        "sql_objects": ["dbo.DoRCheque_DeleteLastRChequeHistory"],
        "mutation_expected": True,
    },
    {
        "command": "payable_cheque.validate_transition",
        "ui_chain": ["frmPChequeTracking workflow lookup", "PChequeAdapter.PChequeWorkFlow_IsValid"],
        "sql_objects": ["dbo.PChequeWorkFlow_IsValid"],
        "mutation_expected": False,
    },
    {
        "command": "payable_cheque.change_status",
        "ui_chain": ["frmPChequeTracking.ChangeStatus", "PChequeAdapter.DoPCheque_AddPChequeHistory"],
        "sql_objects": ["dbo.DoPCheque_AddPChequeHistory"],
        "mutation_expected": True,
    },
    {
        "command": "payable_cheque.undo",
        "ui_chain": ["frmPChequeTracking.DoUndo", "PChequeAdapter.DoPCheque_DeleteLastPChequeHistory"],
        "sql_objects": ["dbo.DoPCheque_DeleteLastPChequeHistory"],
        "mutation_expected": True,
    },
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_comments_and_literals(definition: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", " ", definition, flags=re.DOTALL)
    without_line = re.sub(r"--[^\r\n]*", " ", without_block)
    return re.sub(r"N?'(?:''|[^'])*'", "''", without_line)


def _statement_counts(definition: str) -> dict[str, int]:
    clean = _strip_comments_and_literals(definition)
    patterns = {
        "select": r"\bselect\b",
        "insert": r"\binsert\b",
        "update": r"\bupdate\b",
        "delete": r"\bdelete\b",
        "merge": r"\bmerge\b",
        "execute": r"\bexec(?:ute)?\b",
        "begin_transaction": r"\bbegin\s+tran(?:saction)?\b",
        "commit": r"\bcommit(?:\s+tran(?:saction)?)?\b",
        "rollback": r"\brollback(?:\s+tran(?:saction)?)?\b",
        "try": r"\bbegin\s+try\b",
        "catch": r"\bbegin\s+catch\b",
        "raiserror": r"\braiserror\b",
        "throw": r"\bthrow\b",
    }
    return {name: len(re.findall(pattern, clean, flags=re.IGNORECASE)) for name, pattern in patterns.items()}


def _definition(cursor: Any, object_name: str) -> str:
    rows = _rows(
        cursor,
        f"""
        SELECT sm.definition
        FROM sys.sql_modules sm
        WHERE sm.object_id=OBJECT_ID(N'{object_name}')
        """,
    )
    if not rows or rows[0]["definition"] is None:
        return ""
    value = rows[0]["definition"]
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode("cp1256")
    return str(value)


def _references(cursor: Any, object_name: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        rows = _rows(
            cursor,
            f"""
            SELECT r.referenced_id,r.referenced_schema_name,r.referenced_entity_name,
                   r.referenced_minor_name,r.is_selected,r.is_updated,r.is_select_all,
                   r.is_insert_all,o.type_desc,OBJECT_SCHEMA_NAME(r.referenced_id) resolved_schema_name,
                   OBJECT_NAME(r.referenced_id) resolved_object_name
            FROM sys.dm_sql_referenced_entities(N'{object_name}',N'OBJECT') r
            LEFT JOIN sys.objects o ON o.object_id=r.referenced_id
            WHERE r.referenced_entity_name IS NOT NULL
            ORDER BY r.referenced_schema_name,r.referenced_entity_name,r.referenced_minor_name
            """,
        )
        return rows, None
    except Exception as exc:  # system dependency inspection can fail on dynamic/temp SQL
        return [], f"{type(exc).__name__}:{hashlib.sha256(str(exc).encode('utf-8')).hexdigest()}"


def _aggregate_references(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        schema_name = row.get("resolved_schema_name") or row.get("referenced_schema_name") or "dbo"
        object_name = row.get("resolved_object_name") or row["referenced_entity_name"]
        key = (
            row.get("referenced_id"),
            schema_name.casefold(),
            object_name.casefold(),
        )
        item = grouped.setdefault(
            key,
            {
                "referenced_id": row.get("referenced_id"),
                "schema_name": schema_name,
                "object_name": object_name,
                "type_desc": row.get("type_desc") or "UNRESOLVED_OR_LOCAL_REFERENCE",
                "is_selected": False,
                "is_updated": False,
                "is_select_all": False,
                "is_insert_all": False,
                "selected_columns": set(),
                "updated_columns": set(),
            },
        )
        item["is_selected"] = item["is_selected"] or bool(row.get("is_selected"))
        item["is_updated"] = item["is_updated"] or bool(row.get("is_updated"))
        item["is_select_all"] = item["is_select_all"] or bool(row.get("is_select_all"))
        item["is_insert_all"] = item["is_insert_all"] or bool(row.get("is_insert_all"))
        column = row.get("referenced_minor_name")
        if column and row.get("is_selected"):
            item["selected_columns"].add(column)
        if column and row.get("is_updated"):
            item["updated_columns"].add(column)
    result = []
    for item in grouped.values():
        item["selected_columns"] = sorted(item["selected_columns"])
        item["updated_columns"] = sorted(item["updated_columns"])
        result.append(item)
    return sorted(result, key=lambda row: (row["schema_name"].casefold(), row["object_name"].casefold()))


def _role_hint(reference: dict[str, Any]) -> str:
    name = f"{reference['schema_name']}.{reference['object_name']}".casefold()
    simple_name = reference["object_name"].casefold()
    if reference["type_desc"] in {"SQL_STORED_PROCEDURE", "SQL_SCALAR_FUNCTION", "SQL_TABLE_VALUED_FUNCTION"}:
        return "nested_rule_or_command"
    if simple_name.startswith(("usp", "sp_", "ufn", "fn_")):
        return "nested_rule_or_command"
    if reference["type_desc"] == "SEQUENCE_OBJECT":
        return "key_generator"
    if any(token in name for token in ("hist", "history", "audit", "log")):
        return "event_or_audit_history"
    if any(token in name for token in ("vocher", "voucher", "cardex", "payment", "settlement")):
        return "financial_or_stock_ledger"
    if "exit" in name:
        return "stock_exit_or_distribution_link"
    if any(token in name for token in ("cheque", "dist", "salehdr", "orderhdr")):
        return "aggregate_or_current_state"
    return "reference_or_configuration"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    contract_payload = _load(args.sql_contracts)
    contract_by_name = {row["object"]: row for row in contract_payload["contracts"]}
    object_names = sorted({name for command in COMMANDS for name in command["sql_objects"]})
    sql_objects = []
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            for object_name in object_names:
                definition = _definition(cursor, object_name)
                rows, reference_error = _references(cursor, object_name)
                references = _aggregate_references(rows)
                for reference in references:
                    reference["role_hint"] = _role_hint(reference)
                contract = contract_by_name[object_name]
                statement_counts = _statement_counts(definition)
                sql_objects.append(
                    {
                        "object": object_name,
                        "type_desc": contract["type_desc"],
                        "modify_date": contract["modify_date"],
                        "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest(),
                        "definition_persisted": False,
                        "parameters": contract["parameters"],
                        "statement_kind_counts": statement_counts,
                        "formal_reference_count": len(references),
                        "mutated_reference_count": sum(row["is_updated"] for row in references),
                        "selected_reference_count": sum(row["is_selected"] for row in references),
                        "formal_references": references,
                        "dependency_inspection_error": reference_error,
                        "transaction_evidence": {
                            "begin_transaction_count": statement_counts["begin_transaction"],
                            "commit_count": statement_counts["commit"],
                            "rollback_count": statement_counts["rollback"],
                            "try_count": statement_counts["try"],
                            "catch_count": statement_counts["catch"],
                        },
                    }
                )

    object_by_name = {row["object"]: row for row in sql_objects}
    command_traces = []
    for command in COMMANDS:
        objects = [object_by_name[name] for name in command["sql_objects"]]
        mutation_evidence = sum(
            row["statement_kind_counts"][verb]
            for row in objects
            for verb in ("insert", "update", "delete", "merge")
        )
        parameter_names = {
            row["parameter_name"].casefold()
            for obj in objects
            for row in obj["parameters"]
        }
        has_idempotency_token = any(
            token in name for name in parameter_names
            for token in ("idempot", "requestid", "commandid", "correlation")
        )
        command_traces.append(
            {
                "command": command["command"],
                "ui_to_business_chain": command["ui_chain"],
                "sql_objects": command["sql_objects"],
                "mutation_expected": command["mutation_expected"],
                "mutation_statement_evidence_count": mutation_evidence,
                "mutated_references": sorted(
                    {
                        f"{ref['schema_name']}.{ref['object_name']}".casefold()
                        for obj in objects for ref in obj["formal_references"]
                        if ref["is_updated"]
                    }
                ),
                "ledger_and_history_references": sorted(
                    {
                        f"{ref['schema_name']}.{ref['object_name']}".casefold()
                        for obj in objects for ref in obj["formal_references"]
                        if ref["role_hint"] in {"event_or_audit_history", "financial_or_stock_ledger"}
                    }
                ),
                "explicit_idempotency_parameter_observed": has_idempotency_token,
                "target_contract": (
                    "Server-authorized idempotent command with expected aggregate version, "
                    "single transaction, immutable audit event and post-condition reconciliation."
                    if command["mutation_expected"] else
                    "Side-effect-free query or validation; result must be scoped and version-aware."
                ),
            }
        )

    artifact = {
        "artifact": "varanegar_active_command_side_effect_contracts",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_MODULE_DEPENDENCY_INSPECTION",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "application_procedures_executed": 0,
            "write_statements_executed": 0,
            "raw_module_definitions_persisted": 0,
            "business_rows_read_or_persisted": 0,
            "credentials_or_literal_values_persisted": 0,
            "live_ui_actions": 0,
        },
        "summary": {
            "command_trace_count": len(command_traces),
            "sql_object_count": len(sql_objects),
            "module_dependency_error_count": sum(row["dependency_inspection_error"] is not None for row in sql_objects),
            "mutation_command_count": sum(row["mutation_expected"] for row in command_traces),
            "mutation_command_without_explicit_idempotency_parameter_count": sum(
                row["mutation_expected"] and not row["explicit_idempotency_parameter_observed"]
                for row in command_traces
            ),
            "formal_reference_count": sum(row["formal_reference_count"] for row in sql_objects),
            "mutated_reference_count": sum(row["mutated_reference_count"] for row in sql_objects),
        },
        "interpretation": [
            "Formal is_updated flags and statement counts prove mutation intent but may miss dynamic SQL and alias-specific delete targets.",
            "No explicit request/command/correlation id parameter was observed on the mutating contracts; target idempotency must be designed explicitly.",
            "Stored-procedure transaction evidence is local to each module; nested procedure atomicity and caller transaction behavior require separate verification.",
            "Role hints classify object purpose conservatively from names/type and are not schema truth.",
        ],
        "erp_command_contract": [
            "Accept a client-generated command_id and enforce a uniqueness key per tenant/context.",
            "Require expected_version/current_state and reject stale commands.",
            "Execute state, ledger, current pointer and audit writes in one server-side transaction.",
            "Persist actor, permission decision, scope, reason, source version and before/after state without copying credentials.",
            "Return a deterministic result for duplicate command_id and expose reconciliation status.",
            "Never expose direct table-write capabilities to the web client.",
        ],
        "command_traces": command_traces,
        "sql_objects": sql_objects,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
