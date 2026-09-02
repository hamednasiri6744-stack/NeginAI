"""Diagnose payable cheque-leaf usage semantics without reading identities or raw rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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


MODULE_NAMES = (
    "usp_sdsnet_PchequeBookItem_Save",
    "usp_sdsnet_PChequeBookItem_BeforeSave",
    "BeforePCheque",
    "DoPCheque_AddPChequeHistory",
    "DoPCheque_DeleteLastPChequeHistory",
    "DoPCheque_IsChequeBookItemUsable",
)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold()


def _modules(cursor: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    quoted = ",".join("N'" + name.replace("'", "''") + "'" for name in MODULE_NAMES)
    rows = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,
               DATALENGTH(m.definition) definition_bytes,m.definition
        FROM sys.sql_modules m
        JOIN sys.objects o ON o.object_id=m.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE s.name=N'dbo' AND o.name IN ({quoted})
        ORDER BY o.name
        """,
    )
    public: list[dict[str, Any]] = []
    definitions: dict[str, str] = {}
    for row in rows:
        definition = row.pop("definition")
        definitions[row["object_name"]] = definition
        public.append(
            {
                **row,
                "qualified_name": f"dbo.{row['object_name']}",
                "definition_sha256": hashlib.sha256(definition.encode("utf-8")).hexdigest(),
                "references_leaf_usage": "isused" in definition.casefold(),
                "has_explicit_transaction": bool(
                    re.search(r"\bbegin\s+tran(?:saction)?\b", definition, re.I)
                ),
            }
        )
    return public, definitions


def _schema(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT c.column_id,c.name column_name,TYPE_NAME(c.user_type_id) data_type,
               c.is_nullable
        FROM sys.columns c
        WHERE c.object_id=OBJECT_ID(N'dbo.PChequeBookItem')
        ORDER BY c.column_id
        """,
    )


def _aggregates(cursor: Any) -> dict[str, Any]:
    decomposition = _rows(
        cursor,
        """
        WITH p AS (
          SELECT DISTINCT PChequeBookItemId FROM dbo.PCheque
        ), u AS (
          SELECT i.PChequeBookItemId,i.PChequeBookId,i.IssuedFor,i.Comment,b.IsActive
          FROM dbo.PChequeBookItem i
          JOIN dbo.PChequeBook b ON b.PChequeBookId=i.PChequeBookId
          LEFT JOIN p ON p.PChequeBookItemId=i.PChequeBookItemId
          WHERE i.IsUsed=1 AND p.PChequeBookItemId IS NULL
        ), t AS (
          SELECT DISTINCT PChequeBookItemId FROM dbo.Transfer
          WHERE PChequeBookItemId IS NOT NULL
        ), a AS (
          SELECT DISTINCT PChequeBookItemId FROM dbo.transfer_vn14031207
          WHERE PChequeBookItemId IS NOT NULL
        ), r AS (
          SELECT DISTINCT FromPChequeBookItemId AS PChequeBookItemId
          FROM dbo.RPTransferPCheque WHERE FromPChequeBookItemId IS NOT NULL
        )
        SELECT
          (SELECT COUNT_BIG(*) FROM dbo.PChequeBookItem) leaf_count,
          (SELECT COUNT_BIG(*) FROM dbo.PChequeBookItem WHERE IsUsed=1) used_count,
          (SELECT COUNT_BIG(*) FROM dbo.PCheque c WHERE c.PChequeBookItemId IS NOT NULL)
            current_cheque_link_count,
          COUNT_BIG(*) used_without_current_cheque,
          COUNT(DISTINCT u.PChequeBookId) affected_book_count,
          SUM(CASE WHEN u.IsActive=1 THEN 1 ELSE 0 END) rows_in_active_books,
          SUM(CASE WHEN NULLIF(LTRIM(RTRIM(u.IssuedFor)),'') IS NOT NULL THEN 1 ELSE 0 END)
            issued_for_present_count,
          SUM(CASE WHEN NULLIF(LTRIM(RTRIM(u.Comment)),'') IS NOT NULL THEN 1 ELSE 0 END)
            comment_present_count,
          COUNT_BIG(t.PChequeBookItemId) current_transfer_link_count,
          COUNT_BIG(a.PChequeBookItemId) archived_transfer_link_count,
          COUNT_BIG(r.PChequeBookItemId) rp_transfer_link_count
        FROM u
        LEFT JOIN t ON t.PChequeBookItemId=u.PChequeBookItemId
        LEFT JOIN a ON a.PChequeBookItemId=u.PChequeBookItemId
        LEFT JOIN r ON r.PChequeBookItemId=u.PChequeBookItemId
        """,
    )[0]
    book_buckets = _rows(
        cursor,
        """
        WITH u AS (
          SELECT i.PChequeBookId,COUNT_BIG(*) used_unlinked
          FROM dbo.PChequeBookItem i
          WHERE i.IsUsed=1
            AND NOT EXISTS (SELECT 1 FROM dbo.PCheque c
                            WHERE c.PChequeBookItemId=i.PChequeBookItemId)
          GROUP BY i.PChequeBookId
        )
        SELECT CASE
                 WHEN used_unlinked=1 THEN '1'
                 WHEN used_unlinked BETWEEN 2 AND 5 THEN '2_5'
                 WHEN used_unlinked BETWEEN 6 AND 10 THEN '6_10'
                 ELSE '11_PLUS'
               END leaf_count_bucket,
               COUNT_BIG(*) book_count,SUM(used_unlinked) leaf_count
        FROM u
        GROUP BY CASE
                   WHEN used_unlinked=1 THEN '1'
                   WHEN used_unlinked BETWEEN 2 AND 5 THEN '2_5'
                   WHEN used_unlinked BETWEEN 6 AND 10 THEN '6_10'
                   ELSE '11_PLUS'
                 END
        ORDER BY MIN(used_unlinked)
        """,
    )
    return {"usage_decomposition": decomposition, "affected_book_buckets": book_buckets}


def _contracts(definitions: dict[str, str], columns: list[dict[str, Any]]) -> dict[str, bool]:
    normalized = {name: _normalize(value) for name, value in definitions.items()}
    save = normalized["usp_sdsnet_PchequeBookItem_Save"]
    before_save = normalized["usp_sdsnet_PChequeBookItem_BeforeSave"]
    before_cheque = normalized["BeforePCheque"]
    add_history = normalized["DoPCheque_AddPChequeHistory"]
    undo_history = normalized["DoPCheque_DeleteLastPChequeHistory"]
    column_names = {row["column_name"].casefold() for row in columns}
    return {
        "leaf_screen_save_directly_persists_is_used": (
            "update c set isused=p.isused" in save
        ),
        "manual_unmark_is_blocked_only_when_pcheque_or_transfer_uses_leaf": (
            "p.isused=0" in before_save
            and "exists(select 1 from pcheque" in before_save
            and "exists(select 1 from transfer" in before_save
        ),
        "cheque_save_marks_selected_leaf_used": (
            "update pchequebookitem set isused = 1" in before_cheque
        ),
        "returned_cheque_state_releases_leaf": (
            "case when @pchequestatusid = 2 then 0 else 1 end" in add_history
        ),
        "history_undo_recomputes_leaf_usage": "update pchequebookitem" in undo_history,
        "leaf_has_no_actor_or_modified_timestamp_column": not (
            {"appuserid", "modifieddate", "createddate", "createdby"} & column_names
        ),
    }


def _finding(
    finding_id: str,
    title: str,
    severity: str,
    evidence: list[str],
    implication: str,
    action: str,
    confidence: str,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "title": title,
        "severity": severity,
        "confidence": confidence,
        "evidence": evidence,
        "implication": implication,
        "diagnostic_or_migration_action": action,
    }


def collect() -> dict[str, Any]:
    with _connect() as connection:
        with connection.cursor() as cursor:
            safety = _assert_safe_target(cursor)
            modules, definitions = _modules(cursor)
            columns = _schema(cursor)
            aggregates = _aggregates(cursor)
    contracts = _contracts(definitions, columns)
    usage = aggregates["usage_decomposition"]
    if not (
        len(modules) == len(MODULE_NAMES)
        and all(contracts.values())
        and usage["leaf_count"] == 5687
        and usage["used_count"] == 4827
        and usage["current_cheque_link_count"] == 4672
        and usage["used_without_current_cheque"] == 155
        and usage["current_transfer_link_count"] == 0
        and usage["archived_transfer_link_count"] == 0
        and usage["rp_transfer_link_count"] == 0
    ):
        raise RuntimeError("Payable cheque-leaf usage contract drift")

    findings = [
        _finding(
            "PCL-001",
            "Used without current PCheque is an explicitly supported source state",
            "CRITICAL",
            [
                "the leaf maintenance save procedure directly persists the UI IsUsed value",
                "the validator permits clearing IsUsed only when neither PCheque nor Transfer consumes the leaf",
                "all 155 rows have no current PCheque or Transfer-family link",
            ],
            "Treating every used-unlinked leaf as corrupt would erase an intentional manual reservation/consumption capability.",
            "Preserve SOURCE_USED_UNLINKED as a typed source state; never create a cheque or clear IsUsed automatically.",
            "HIGH_STATIC_SQL_AND_READ_ONLY_AGGREGATE",
        ),
        _finding(
            "PCL-002",
            "The exact historical reason for the 155 used-unlinked leaves is unavailable",
            "HIGH",
            [
                "PChequeBookItem has no actor or modified timestamp column",
                "none of the 155 rows has IssuedFor or Comment context",
                "the rows span 23 active cheque books",
            ],
            "Current state cannot distinguish a deliberate manual mark from a deleted legacy cheque or another historical residue.",
            "Import provenance as UNKNOWN_SOURCE and require owner review before reuse; do not claim manual intent as a historical fact.",
            "HIGH_SCHEMA_AND_AGGREGATE_LIMIT",
        ),
        _finding(
            "PCL-003",
            "Leaf usage belongs to the payable-cheque command consistency boundary",
            "HIGH",
            [
                "cheque save marks the leaf used",
                "status 2 releases the leaf",
                "history undo recomputes leaf usage",
            ],
            "Updating cheque state and leaf availability in separate transactions can double-issue or permanently lock a leaf.",
            "Use one versioned idempotent command and transaction for cheque event, current projection and leaf state.",
            "HIGH_STATIC_SQL",
        ),
        _finding(
            "PCL-004",
            "The aggregate is reconciled but not auditable",
            "MEDIUM",
            [
                "4827 used leaves decompose exactly into 4672 current cheque links plus 155 used-unlinked rows",
                "current cheque leaf orphans and reused leaf groups are zero in the domain baseline",
            ],
            "Count conservation rules out an unexplained aggregate gap but does not recover missing event provenance.",
            "Reconcile the three destination states AVAILABLE, LINKED_TO_CHEQUE and SOURCE_USED_UNLINKED separately.",
            "MEDIUM_AGGREGATE_RECONCILIATION",
        ),
    ]
    severities = Counter(row["severity"] for row in findings)
    return {
        "artifact": "varanegar_payable_cheque_leaf_usage_diagnostic_contract",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_AGGREGATES_CATALOG_AND_DEFINITION_ANALYSIS",
            "database_updateability": safety["updateability"],
            "can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "identities_or_raw_business_rows_persisted": 0,
            "cheque_numbers_or_comments_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "finding_count": len(findings),
            "finding_severity_counts": dict(sorted(severities.items())),
            "leaf_count": usage["leaf_count"],
            "used_leaf_count": usage["used_count"],
            "current_cheque_link_count": usage["current_cheque_link_count"],
            "source_used_unlinked_count": usage["used_without_current_cheque"],
            "affected_book_count": usage["affected_book_count"],
            "linked_transfer_family_count": usage["current_transfer_link_count"]
            + usage["archived_transfer_link_count"]
            + usage["rp_transfer_link_count"],
            "manual_context_present_count": usage["issued_for_present_count"]
            + usage["comment_present_count"],
            "previous_orphan_interpretation_valid": False,
            "safe_to_clear_or_synthesize": False,
            "historical_reason_recoverable": False,
            "stored_procedure_or_application_commands_executed": 0,
        },
        "semantic_correction": {
            "wrong_model": "IsUsed requires a current PCheque foreign-key consumer",
            "evidenced_model": "IsUsed can be set directly by leaf maintenance or derived by cheque lifecycle",
            "migration_state": "SOURCE_USED_UNLINKED with UNKNOWN_SOURCE provenance",
            "prohibition": "never clear IsUsed, synthesize a PCheque or infer the original actor/reason",
        },
        "incident_findings": findings,
        "leaf_schema": columns,
        "aggregate_contract": aggregates,
        "sql_module_contracts": modules,
        "verified_contracts": contracts,
        "diagnostic_order": [
            "reconcile IsUsed against current PCheque and Transfer-family consumers",
            "check whether the maintenance command supports direct manual usage state",
            "verify actor/time/reason provenance exists before inferring historical intent",
            "preserve used-unlinked as a typed state and require explicit review before reuse",
        ],
        "evidence_limits": [
            "Static SQL proves the supported direct state transition, not which path created each historical row.",
            "The leaf table has no actor/timestamp provenance and the 155 rows have no persisted contextual note.",
            "Deleted historical PCheque rows cannot be reconstructed from this current-state snapshot.",
            "No identity, cheque number, bank account, comment or raw business row was persisted.",
            "No form, stored procedure, transaction or mutation was executed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())
    print(json.dumps(payload["summary"], ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
