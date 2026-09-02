"""Classify active Voucher headers without active lines on the read-only clone."""

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
    "DoVoucher_SetVoucherNo",
    "DoVoucherStatusHistory_GetVoucherStatus",
    "Usp_Sdsnet_Voucher_Save",
    "Voucher2",
    "Get_GLBook",
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
                "references_voucher_item": "voucheritem" in definition.casefold(),
            }
        )
    return public, definitions


def _aggregates(cursor: Any) -> dict[str, Any]:
    profile = _rows(
        cursor,
        """
        SELECT v.VoucherTypeId,vt.VoucherTypeName,v.IsManual,
               CASE WHEN v.ExternalVoucherHeaderId IS NULL THEN 0 ELSE 1 END external_linked,
               h.VoucherStatusId,vs.VoucherStatusName,
               CASE WHEN v.VoucherNo IS NULL THEN 1 ELSE 0 END voucher_no_null,
               v.FiscalYearId,v.DCId,COUNT_BIG(*) headers
        FROM dbo.Voucher v
        JOIN dbo.VoucherType vt ON vt.VoucherTypeId=v.VoucherTypeId
        JOIN dbo.VoucherStatusHistory h
          ON h.VoucherStatusHistoryId=v.VoucherStatusHistoryId
        JOIN dbo.VoucherStatus vs ON vs.VoucherStatusId=h.VoucherStatusId
        WHERE v.IsDeleted=0
          AND NOT EXISTS(SELECT 1 FROM dbo.VoucherItem i
                         WHERE i.VoucherId=v.VoucherId AND i.IsDeleted=0)
        GROUP BY v.VoucherTypeId,vt.VoucherTypeName,v.IsManual,
                 CASE WHEN v.ExternalVoucherHeaderId IS NULL THEN 0 ELSE 1 END,
                 h.VoucherStatusId,vs.VoucherStatusName,
                 CASE WHEN v.VoucherNo IS NULL THEN 1 ELSE 0 END,
                 v.FiscalYearId,v.DCId
        """,
    )
    history = _rows(
        cursor,
        """
        WITH e AS (
          SELECT v.VoucherId,v.VoucherStatusHistoryId
          FROM dbo.Voucher v
          WHERE v.IsDeleted=0
            AND NOT EXISTS(SELECT 1 FROM dbo.VoucherItem i
                           WHERE i.VoucherId=v.VoucherId AND i.IsDeleted=0)
        )
        SELECT h.VoucherStatusId,COUNT_BIG(*) events,
               SUM(CASE WHEN h.VoucherStatusHistoryId=e.VoucherStatusHistoryId
                        THEN 1 ELSE 0 END) current_events
        FROM e JOIN dbo.VoucherStatusHistory h ON h.VoucherId=e.VoucherId
        GROUP BY h.VoucherStatusId
        """,
    )
    impact = _rows(
        cursor,
        """
        WITH e AS (
          SELECT v.VoucherId,v.ExternalVoucherHeaderId
          FROM dbo.Voucher v
          WHERE v.IsDeleted=0
            AND NOT EXISTS(SELECT 1 FROM dbo.VoucherItem i
                           WHERE i.VoucherId=v.VoucherId AND i.IsDeleted=0)
        )
        SELECT COUNT_BIG(*) shell_count,
               SUM(CASE WHEN e.ExternalVoucherHeaderId IS NOT NULL THEN 1 ELSE 0 END)
                 external_link_count,
               (SELECT COUNT_BIG(*) FROM dbo.VoucherItem i JOIN e ON e.VoucherId=i.VoucherId)
                 any_line_count,
               (SELECT COUNT_BIG(*) FROM dbo.VoucherItem i JOIN e ON e.VoucherId=i.VoucherId
                 WHERE i.IsDeleted=1) deleted_line_count,
               (SELECT COALESCE(SUM(i.DebitAmount),0) FROM dbo.VoucherItem i
                 JOIN e ON e.VoucherId=i.VoucherId) debit_amount,
               (SELECT COALESCE(SUM(i.CreditAmount),0) FROM dbo.VoucherItem i
                 JOIN e ON e.VoucherId=i.VoucherId) credit_amount
        FROM e
        """,
    )[0]
    return {"shell_profile": profile, "status_history": history, "financial_impact": impact}


def _contracts(definitions: dict[str, str]) -> dict[str, bool]:
    normalized = {name: _normalize(value) for name, value in definitions.items()}
    numbering = normalized["DoVoucher_SetVoucherNo"]
    validate = normalized["DoVoucherStatusHistory_GetVoucherStatus"]
    save = normalized["Usp_Sdsnet_Voucher_Save"]
    book = normalized["Get_GLBook"]
    return {
        "numbering_rejects_voucher_without_item": (
            "not exists(select 1 from voucheritem where voucherid=@voucherid)" in numbering
            and "raiserror" in numbering
        ),
        "status_validator_iterates_active_items": (
            "from voucheritem vi" in validate and "vi.isdeleted = 0" in validate
        ),
        "save_can_delete_items_absent_from_request": (
            "delete vi" in save
            and "not exists (select 1 from #voucheritems" in save
        ),
        "save_can_downgrade_invalid_temporary_voucher_to_draft": (
            "if @voucherstatusid = 2" in save
            and "1 as voucherstatusid" in save
        ),
        "save_numbering_recheck_is_commented_in_manual_insert_path": (
            "--exec dovoucher_setvoucherno" in save
        ),
        "general_ledger_book_requires_voucher_items": (
            "voucheritem" in book and "voucherstatushistory" in book
        ),
    }


def _finding(fid: str, title: str, severity: str, evidence: list[str], implication: str,
             action: str, confidence: str) -> dict[str, Any]:
    return {
        "finding_id": fid,
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
            aggregates = _aggregates(cursor)
    contracts = _contracts(definitions)
    profile = aggregates["shell_profile"]
    history = aggregates["status_history"]
    impact = aggregates["financial_impact"]
    if not (
        len(modules) == len(MODULE_NAMES)
        and all(contracts.values())
        and len(profile) == 1
        and profile[0]["headers"] == 1
        and profile[0]["VoucherTypeId"] == 59
        and profile[0]["IsManual"] is True
        and profile[0]["external_linked"] == 0
        and profile[0]["VoucherStatusId"] == 1
        and profile[0]["voucher_no_null"] == 0
        and history == [{"VoucherStatusId": 1, "events": 1, "current_events": 1}]
        and impact["any_line_count"] == 0
        and str(impact["debit_amount"]) == "0"
        and str(impact["credit_amount"]) == "0"
    ):
        raise RuntimeError("Empty Voucher shell diagnostic contract drift")

    findings = [
        _finding(
            "EVS-001",
            "The active header without lines is a manual draft shell, not a posted journal",
            "CRITICAL",
            [
                "the only row has current status 1 (draft)",
                "it has no current, deleted or historical VoucherItem rows",
                "it has no ExternalVoucherHeader link and zero debit/credit effect",
                "the official ledger-book path requires VoucherItem rows",
            ],
            "Synthesizing a balancing line or treating IsDeleted=0 as posted would invent a financial event.",
            "Preserve as DRAFT_EMPTY_NUMBERED_SHELL outside the ledger; never synthesize lines or balances.",
            "HIGH_READ_ONLY_AGGREGATE_AND_SQL",
        ),
        _finding(
            "EVS-002",
            "The draft shell has an assigned voucher number that current numbering rules reject",
            "HIGH",
            [
                "VoucherNo is non-null",
                "DoVoucher_SetVoucherNo explicitly rejects a voucher without items",
                "the shell belongs to an older fiscal-year scope",
            ],
            "The row can reserve or confuse a legal sequence even though it has no ledger effect.",
            "Preserve the source number as provenance, exclude it from target posted numbering, and require accountant disposition before number reuse.",
            "HIGH_SQL_AND_AGGREGATE",
        ),
        _finding(
            "EVS-003",
            "The deployed manual-save path can plausibly leave an empty numbered draft",
            "HIGH",
            [
                "update deletes persisted lines absent from #VoucherItems",
                "an invalid temporary voucher can be downgraded to draft",
                "the manual insert numbering recheck call is commented in the deployed save module",
            ],
            "A line-removal edit can separate draft validity from an already assigned source number; the static path is plausible but does not prove this row's history.",
            "The target command must atomically validate at least two balanced lines before assigning a posted number and must release/reserve draft numbers by explicit policy.",
            "HIGH_STATIC_PATH_HISTORICAL_CAUSATION_UNPROVEN",
        ),
        _finding(
            "EVS-004",
            "No event trail explains why the shell was retained",
            "MEDIUM",
            ["the shell has exactly one draft status event", "no raw comment or actor identity was inspected or persisted"],
            "The source snapshot cannot distinguish abandoned work, retained template or failed edit.",
            "Use UNKNOWN_SOURCE provenance and accounting-owner review; do not infer deletion or business meaning.",
            "MEDIUM_CURRENT_STATE_LIMIT",
        ),
    ]
    sev = Counter(row["severity"] for row in findings)
    return {
        "artifact": "varanegar_empty_voucher_shell_diagnostic_contract",
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
            "identities_numbers_comments_or_raw_rows_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "finding_count": len(findings),
            "finding_severity_counts": dict(sorted(sev.items())),
            "active_header_without_line_count": impact["shell_count"],
            "draft_shell_count": profile[0]["headers"],
            "numbered_shell_count": 1 - profile[0]["voucher_no_null"],
            "external_link_count": impact["external_link_count"],
            "any_item_count": impact["any_line_count"],
            "deleted_item_count": impact["deleted_line_count"],
            "ledger_debit_effect": str(impact["debit_amount"]),
            "ledger_credit_effect": str(impact["credit_amount"]),
            "previous_active_journal_corruption_interpretation_valid": False,
            "safe_to_synthesize_lines": False,
            "safe_to_reuse_source_number": False,
            "historical_reason_recoverable": False,
            "stored_procedure_or_application_commands_executed": 0,
        },
        "semantic_correction": {
            "wrong_model": "every IsDeleted=0 Voucher is a posted journal that requires repair when it has no lines",
            "evidenced_model": "the single row is a non-posted manual draft shell with no ledger effect but an unresolved assigned source number",
            "migration_state": "DRAFT_EMPTY_NUMBERED_SHELL with UNKNOWN_SOURCE",
            "prohibition": "never synthesize lines, post the shell or silently reuse its source number",
        },
        "incident_findings": findings,
        "aggregate_contract": aggregates,
        "sql_module_contracts": modules,
        "verified_contracts": contracts,
        "evidence_limits": [
            "Static SQL identifies a plausible save path but does not prove the historical cause of this row.",
            "No voucher number, actor, comment, reference, account or line value was persisted.",
            "No live-role UI execution or accountant UAT was performed.",
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
