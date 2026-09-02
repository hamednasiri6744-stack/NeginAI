"""Diagnose ledger Voucher current-pointer/history divergence on the read-only clone."""

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
    "Get_ChangeVoucherStatus",
    "DoVoucher_SetVoucherNo",
    "Usp_Sdsnet_Voucher_Save",
    "Voucher2",
    "VoucherFast",
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
                "references_current_pointer": "voucherstatushistoryid" in definition.casefold(),
                "has_explicit_transaction": bool(
                    re.search(r"\bbegin\s+tran(?:saction)?\b", definition, re.I)
                ),
                "has_explicit_rollback": bool(
                    re.search(r"\brollback(?:\s+tran(?:saction)?)?\b", definition, re.I)
                ),
            }
        )
    return public, definitions


def _aggregates(cursor: Any) -> dict[str, Any]:
    status_matrix = _rows(
        cursor,
        """
        WITH x AS (
          SELECT v.VoucherId,cur.VoucherStatusId current_status,
                 mx.VoucherStatusId maximum_status
          FROM dbo.Voucher v
          JOIN dbo.VoucherStatusHistory cur
            ON cur.VoucherStatusHistoryId=v.VoucherStatusHistoryId
          JOIN (SELECT VoucherId,MAX(VoucherStatusHistoryId) maximum_id
                FROM dbo.VoucherStatusHistory GROUP BY VoucherId) m
            ON m.VoucherId=v.VoucherId
          JOIN dbo.VoucherStatusHistory mx
            ON mx.VoucherStatusHistoryId=m.maximum_id
          WHERE v.VoucherStatusHistoryId<>m.maximum_id
        )
        SELECT current_status,maximum_status,COUNT_BIG(*) vouchers
        FROM x GROUP BY current_status,maximum_status ORDER BY vouchers DESC
        """,
    )
    trail_summary = _rows(
        cursor,
        """
        WITH mismatch AS (
          SELECT v.VoucherId,v.VoucherStatusHistoryId current_id
          FROM dbo.Voucher v
          JOIN (SELECT VoucherId,MAX(VoucherStatusHistoryId) maximum_id
                FROM dbo.VoucherStatusHistory GROUP BY VoucherId) m
            ON m.VoucherId=v.VoucherId
          WHERE v.VoucherStatusHistoryId<>m.maximum_id
        ), ranked AS (
          SELECT h.*,
                 ROW_NUMBER() OVER(PARTITION BY VoucherId ORDER BY VoucherStatusHistoryId) rn,
                 COUNT_BIG(*) OVER(PARTITION BY VoucherId) event_count
          FROM dbo.VoucherStatusHistory h
        ), x AS (
          SELECT m.VoucherId,
                 MAX(CASE WHEN h.VoucherStatusHistoryId=m.current_id THEN h.rn END)
                   current_ordinal,
                 SUM(CASE WHEN h.VoucherStatusHistoryId>m.current_id THEN 1 ELSE 0 END)
                   trailing_events,
                 SUM(CASE WHEN h.VoucherStatusHistoryId>m.current_id
                               AND h.VoucherStatusId<>cur.VoucherStatusId THEN 1 ELSE 0 END)
                   trailing_different_status_events,
                 MAX(CASE WHEN h.VoucherStatusHistoryId>m.current_id
                               AND h.VoucherStatusId<>cur.VoucherStatusId THEN 1 ELSE 0 END)
                   has_trailing_different_status,
                 SUM(CASE WHEN h.VoucherStatusHistoryId>m.current_id
                               AND NULLIF(LTRIM(RTRIM(h.VoucherStatusComment)),'') IS NOT NULL
                          THEN 1 ELSE 0 END) trailing_with_comment,
                 MIN(CASE WHEN h.VoucherStatusHistoryId>m.current_id
                          THEN h.ModifiedDate END) first_trailing_date,
                 MAX(CASE WHEN h.VoucherStatusHistoryId>m.current_id
                          THEN h.ModifiedDate END) last_trailing_date
          FROM mismatch m
          JOIN ranked h ON h.VoucherId=m.VoucherId
          JOIN dbo.VoucherStatusHistory cur ON cur.VoucherStatusHistoryId=m.current_id
          GROUP BY m.VoucherId
        )
        SELECT COUNT_BIG(*) vouchers,
               SUM(CASE WHEN current_ordinal=1 THEN 1 ELSE 0 END) pointer_at_first_event,
               SUM(trailing_events) trailing_events,
               SUM(trailing_different_status_events) trailing_different_status_events,
               SUM(has_trailing_different_status) vouchers_with_trailing_different_status,
               MIN(trailing_events) minimum_trailing_events,
               MAX(trailing_events) maximum_trailing_events,
               SUM(trailing_with_comment) trailing_with_comment,
               MIN(first_trailing_date) first_trailing_date,
               MAX(last_trailing_date) last_trailing_date
        FROM x
        """,
    )[0]
    scope_profile = _rows(
        cursor,
        """
        WITH mismatch AS (
          SELECT v.VoucherId,v.IsManual,v.ExternalVoucherHeaderId,
                 cur.VoucherStatusId current_status,
                 mx.VoucherStatusId maximum_status
          FROM dbo.Voucher v
          JOIN dbo.VoucherStatusHistory cur
            ON cur.VoucherStatusHistoryId=v.VoucherStatusHistoryId
          JOIN (SELECT VoucherId,MAX(VoucherStatusHistoryId) maximum_id
                FROM dbo.VoucherStatusHistory GROUP BY VoucherId) m
            ON m.VoucherId=v.VoucherId
          JOIN dbo.VoucherStatusHistory mx ON mx.VoucherStatusHistoryId=m.maximum_id
          WHERE v.VoucherStatusHistoryId<>m.maximum_id
        )
        SELECT IsManual,
               CASE WHEN ExternalVoucherHeaderId IS NULL THEN 0 ELSE 1 END external_linked,
               current_status,maximum_status,COUNT_BIG(*) vouchers
        FROM mismatch
        GROUP BY IsManual,CASE WHEN ExternalVoucherHeaderId IS NULL THEN 0 ELSE 1 END,
                 current_status,maximum_status
        ORDER BY vouchers DESC
        """,
    )
    monthly = _rows(
        cursor,
        """
        WITH mismatch AS (
          SELECT v.VoucherId,m.maximum_id
          FROM dbo.Voucher v
          JOIN (SELECT VoucherId,MAX(VoucherStatusHistoryId) maximum_id
                FROM dbo.VoucherStatusHistory GROUP BY VoucherId) m
            ON m.VoucherId=v.VoucherId
          WHERE v.VoucherStatusHistoryId<>m.maximum_id
        )
        SELECT CONVERT(char(7),h.ModifiedDate,120) maximum_event_month,
               COUNT_BIG(*) vouchers
        FROM mismatch m
        JOIN dbo.VoucherStatusHistory h ON h.VoucherStatusHistoryId=m.maximum_id
        GROUP BY CONVERT(char(7),h.ModifiedDate,120)
        ORDER BY maximum_event_month
        """,
    )
    pointer_integrity = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM dbo.Voucher) vouchers,
          (SELECT COUNT_BIG(*) FROM dbo.VoucherStatusHistory) history_events,
          (SELECT COUNT_BIG(*) FROM dbo.Voucher v LEFT JOIN dbo.VoucherStatusHistory h
             ON h.VoucherStatusHistoryId=v.VoucherStatusHistoryId
           WHERE h.VoucherStatusHistoryId IS NULL OR h.VoucherId<>v.VoucherId)
             invalid_current_pointer,
          (SELECT COUNT_BIG(*) FROM dbo.Voucher v
             JOIN (SELECT VoucherId,MAX(VoucherStatusHistoryId) maximum_id
                   FROM dbo.VoucherStatusHistory GROUP BY VoucherId) m
               ON m.VoucherId=v.VoucherId
           WHERE v.VoucherStatusHistoryId<>m.maximum_id) pointer_not_maximum_history
        """,
    )[0]
    return {
        "pointer_integrity": pointer_integrity,
        "current_vs_maximum_status": status_matrix,
        "detached_trailing_event_summary": trail_summary,
        "affected_voucher_scope": scope_profile,
        "maximum_trailing_event_months": monthly,
    }


def _contracts(definitions: dict[str, str]) -> dict[str, bool]:
    normalized = {name: _normalize(value) for name, value in definitions.items()}
    change = normalized["Get_ChangeVoucherStatus"]
    numbering = normalized["DoVoucher_SetVoucherNo"]
    view2 = normalized["Voucher2"]
    fast = normalized["VoucherFast"]
    return {
        "legacy_change_inserts_history_before_updating_pointer": (
            change.find("insert into voucherstatushistory")
            < change.find("update voucher set voucherstatushistoryid")
            and change.find("insert into voucherstatushistory") >= 0
        ),
        "legacy_change_wraps_insert_and_pointer_update_in_transaction": (
            "begin tran" in change and "commit tran" in change
        ),
        "legacy_change_catch_has_no_explicit_rollback": (
            "begin catch" in change and "rollback" not in change
        ),
        "voucher_numbering_rejects_pointer_not_latest": (
            "voucherstatushistoryid from voucher" in numbering
            and "order by voucherstatushistoryid desc" in numbering
            and "raiserror" in numbering
        ),
        "voucher2_reads_status_through_current_pointer": (
            "inner join voucherstatushistory vsh on vsh.voucherstatushistoryid = vh.voucherstatushistoryid" in view2
        ),
        "voucher_fast_reads_status_through_current_pointer": (
            "voucherstatushistoryid" in fast and "voucherstatushistory" in fast
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
            aggregates = _aggregates(cursor)
    contracts = _contracts(definitions)
    integrity = aggregates["pointer_integrity"]
    trail = aggregates["detached_trailing_event_summary"]
    status = aggregates["current_vs_maximum_status"]
    if not (
        len(modules) == len(MODULE_NAMES)
        and all(contracts.values())
        and integrity["invalid_current_pointer"] == 0
        and integrity["pointer_not_maximum_history"] == 1094
        and trail["trailing_events"] == 14946
        and trail["pointer_at_first_event"] == 1090
        and trail["vouchers_with_trailing_different_status"] == 1091
        and status == [
            {"current_status": 2, "maximum_status": 2, "vouchers": 1083},
            {"current_status": 2, "maximum_status": 1, "vouchers": 11},
        ]
    ):
        raise RuntimeError("Voucher status pointer diagnostic contract drift")

    findings = [
        _finding(
            "VSP-001",
            "1094 vouchers have valid current pointers but detached later status events",
            "CRITICAL",
            [
                "all current pointers resolve to the same voucher",
                "14946 later history events remain after those pointers",
                "1091 vouchers have at least one later event with a different status",
                "1090 current pointers still select the first event",
            ],
            "The history table is not a simple append-only ledger whose maximum identifier is always current, and the divergence is operationally material.",
            "Quarantine the divergence as CURRENT_POINTER_HISTORY_FORK; preserve both branches and require accounting reconciliation before cutover.",
            "HIGH_READ_ONLY_AGGREGATE",
        ),
        _finding(
            "VSP-002",
            "The deployed legacy status-change failure path does not explicitly roll back",
            "CRITICAL",
            [
                "Get_ChangeVoucherStatus inserts VoucherStatusHistory before updating Voucher inside a local transaction",
                "its CATCH branch has no explicit rollback for that transaction",
                "DoVoucher_SetVoucherNo explicitly rejects a pointer that is not the latest history row",
            ],
            "An exception can leave an open transaction whose later disposition is caller/session-dependent; this is a plausible contributor to inconsistent outcomes, not proof for every historical row.",
            "Implement one idempotent transaction for event insertion, current-pointer CAS and numbering side effects; inject a failure between insert and pointer update.",
            "HIGH_STATIC_REACHABLE_PATH_HISTORICAL_CAUSATION_UNPROVEN",
        ),
        _finding(
            "VSP-003",
            "Neither pointer nor MAX(history) may be silently substituted during migration",
            "HIGH",
            [
                "official Voucher2/VoucherFast read current status through the pointer",
                "1083 maximum rows return to status 2 while 11 end in status 1",
                "all 1094 affected vouchers are manual and have no ExternalVoucherHeader link",
            ],
            "Choosing MAX can resurrect attempted transitions; choosing only the pointer can discard evidence of incomplete or rejected transitions.",
            "Import the pointer as current projection, retain every event with branch provenance, and block posting-state enablement until an accountant dispositions each fork class.",
            "HIGH_SQL_AND_AGGREGATE",
        ),
        _finding(
            "VSP-004",
            "The fork is concentrated but historical intent is not recoverable from aggregate evidence",
            "MEDIUM",
            [
                "the affected maximum events span 2024-04 through 2025-05 and cluster strongly in 2025-02",
                "none of the 14946 trailing events has a non-empty status comment",
                "up to 244 trailing events exist behind a single current pointer",
            ],
            "The snapshot cannot tell which transitions were accepted, rejected, retried or repaired by operators.",
            "Preserve UNKNOWN_OUTCOME provenance and obtain owner-approved resolution rules from accounting rather than inferring intent.",
            "MEDIUM_CURRENT_STATE_LIMIT",
        ),
    ]
    severities = Counter(row["severity"] for row in findings)
    return {
        "artifact": "varanegar_voucher_status_pointer_diagnostic_contract",
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
            "identities_comments_or_raw_business_rows_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "finding_count": len(findings),
            "finding_severity_counts": dict(sorted(severities.items())),
            "voucher_count": integrity["vouchers"],
            "history_event_count": integrity["history_events"],
            "invalid_current_pointer_count": integrity["invalid_current_pointer"],
            "current_pointer_not_maximum_count": integrity["pointer_not_maximum_history"],
            "detached_trailing_event_count": trail["trailing_events"],
            "pointer_at_first_event_count": trail["pointer_at_first_event"],
            "fork_with_different_status_count": trail["vouchers_with_trailing_different_status"],
            "maximum_trailing_events_per_voucher": trail["maximum_trailing_events"],
            "trailing_event_with_comment_count": trail["trailing_with_comment"],
            "safe_to_replace_pointer_with_maximum": False,
            "safe_to_discard_trailing_history": False,
            "legacy_change_status_failure_has_explicit_rollback": False,
            "historical_outcome_recoverable": False,
            "stored_procedure_or_application_commands_executed": 0,
        },
        "semantic_correction": {
            "previous_model": "the pointer is authoritative and non-maximum history can be treated as harmless rollback evidence",
            "evidenced_model": "the pointer is the deployed read projection, but later detached events form an unresolved history fork and numbering explicitly rejects the divergence",
            "migration_state": "CURRENT_POINTER_HISTORY_FORK with UNKNOWN_OUTCOME",
            "prohibition": "do not set pointer to MAX, discard trailing events or call them accepted rollbacks without owner evidence",
        },
        "incident_findings": findings,
        "aggregate_contract": aggregates,
        "sql_module_contracts": modules,
        "verified_contracts": contracts,
        "diagnostic_order": [
            "validate pointer existence and voucher ownership",
            "compare pointer ordinal and later status-event branch",
            "use deployed read models to identify current projection semantics",
            "inspect write ordering, transaction and numbering guards",
            "preserve fork and block automatic repair until accounting disposition",
        ],
        "evidence_limits": [
            "The code path is a plausible partial-commit mechanism but does not prove causation for each historical voucher.",
            "Aggregate evidence does not expose actor identities, voucher numbers, comments or line values.",
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
