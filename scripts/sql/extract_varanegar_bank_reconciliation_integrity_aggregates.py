"""Extract privacy-safe aggregate integrity metrics for bank reconciliation.

Only COUNT/SUM aggregates are returned from the local read-only clone. No row
identifier, date, amount, comment, file name, user value or other business value
is persisted.
"""

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
    _json_default,
    _rows,
)


TABLES = (
    "Reconcile",
    "BankBill",
    "ReconcileItem",
    "BankBillFormat",
    "BankBillFormatItem",
    "BankBillFormatType",
    "ReconciliationColumn",
)
TYPED_LINKS = (
    ("PCheque", "PChequeId", "PChequeId"),
    ("PWithDraw", "PWithDrawId", "PWithDrawId"),
    ("RBankDraft", "RBankDraftId", "RBankDraftId"),
    ("RCashDraft", "RCashDraftId", "RCashDraftId"),
    ("RCheque", "RChequeId", "RChequeId"),
    ("Transfer", "TransferId", "TransferId"),
)


def _scalar(cursor: Any, sql: str) -> int:
    cursor.execute(sql)
    row = cursor.fetchone()
    return 0 if row is None or row[0] is None else int(row[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            table_counts = {
                table: _scalar(cursor, f"SELECT COUNT_BIG(*) FROM dbo.[{table}]")
                for table in TABLES
            }
            state = _rows(
                cursor,
                """
                SELECT
                  COUNT_BIG(*) AS session_count,
                  SUM(CASE WHEN ConfirmerId IS NULL AND ConfirmDate IS NULL THEN 1 ELSE 0 END) AS unconfirmed_marker_count,
                  SUM(CASE WHEN ConfirmerId IS NOT NULL AND ConfirmDate IS NOT NULL THEN 1 ELSE 0 END) AS confirmed_marker_count,
                  SUM(CASE WHEN (ConfirmerId IS NULL AND ConfirmDate IS NOT NULL)
                                OR (ConfirmerId IS NOT NULL AND ConfirmDate IS NULL) THEN 1 ELSE 0 END) AS partial_marker_count,
                  SUM(CASE WHEN ConfirmerId IS NOT NULL AND ConfirmDate IS NOT NULL AND Amount IS NULL THEN 1 ELSE 0 END) AS confirmed_amount_null_count,
                  SUM(CASE WHEN ConfirmerId IS NOT NULL AND ConfirmDate IS NOT NULL AND Amount = 0 THEN 1 ELSE 0 END) AS confirmed_amount_zero_count,
                  SUM(CASE WHEN ConfirmerId IS NOT NULL AND ConfirmDate IS NOT NULL AND Amount <> 0 THEN 1 ELSE 0 END) AS confirmed_amount_nonzero_count
                FROM dbo.Reconcile
                """,
            )[0]
            topology = {
                "session_without_bank_bill_count": _scalar(
                    cursor,
                    "SELECT COUNT_BIG(*) FROM dbo.Reconcile r WHERE NOT EXISTS (SELECT 1 FROM dbo.BankBill b WHERE b.ReconcileId=r.ReconcileId)",
                ),
                "bank_bill_without_link_count": _scalar(
                    cursor,
                    "SELECT COUNT_BIG(*) FROM dbo.BankBill b WHERE NOT EXISTS (SELECT 1 FROM dbo.ReconcileItem ri WHERE ri.BankBillId=b.BankBillId)",
                ),
                "bank_bill_with_multiple_links_count": _scalar(
                    cursor,
                    "SELECT COUNT_BIG(*) FROM (SELECT BankBillId FROM dbo.ReconcileItem GROUP BY BankBillId HAVING COUNT_BIG(*)>1) x",
                ),
                "session_with_multiple_links_count": _scalar(
                    cursor,
                    "SELECT COUNT_BIG(*) FROM (SELECT b.ReconcileId FROM dbo.BankBill b JOIN dbo.ReconcileItem ri ON ri.BankBillId=b.BankBillId GROUP BY b.ReconcileId HAVING COUNT_BIG(*)>1) x",
                ),
                "confirmed_session_with_multiple_links_count": _scalar(
                    cursor,
                    "SELECT COUNT_BIG(*) FROM (SELECT b.ReconcileId FROM dbo.BankBill b JOIN dbo.ReconcileItem ri ON ri.BankBillId=b.BankBillId JOIN dbo.Reconcile r ON r.ReconcileId=b.ReconcileId WHERE r.ConfirmerId IS NOT NULL AND r.ConfirmDate IS NOT NULL GROUP BY b.ReconcileId HAVING COUNT_BIG(*)>1) x",
                ),
            }
            reference_shape = _rows(
                cursor,
                """
                SELECT ref_count,COUNT_BIG(*) AS link_count
                FROM (
                  SELECT (CASE WHEN PChequeId IS NULL THEN 0 ELSE 1 END
                        + CASE WHEN PWithDrawId IS NULL THEN 0 ELSE 1 END
                        + CASE WHEN RBankDraftId IS NULL THEN 0 ELSE 1 END
                        + CASE WHEN RCashDraftId IS NULL THEN 0 ELSE 1 END
                        + CASE WHEN RChequeId IS NULL THEN 0 ELSE 1 END
                        + CASE WHEN TransferId IS NULL THEN 0 ELSE 1 END) AS ref_count
                  FROM dbo.ReconcileItem
                ) x
                GROUP BY ref_count ORDER BY ref_count
                """,
            )
            typed_metrics = []
            for table, reference_column, key_column in TYPED_LINKS:
                rows = _rows(
                    cursor,
                    f"""
                    SELECT
                      COUNT_BIG(*) AS link_count,
                      SUM(CASE WHEN src.[{key_column}] IS NULL THEN 1 ELSE 0 END) AS missing_source_count,
                      SUM(CASE WHEN src.[{key_column}] IS NOT NULL AND ISNULL(src.IsReconciled,0)=1 THEN 1 ELSE 0 END) AS instrument_reconciled_count,
                      SUM(CASE WHEN src.[{key_column}] IS NOT NULL AND ISNULL(src.IsReconciled,0)=0 THEN 1 ELSE 0 END) AS instrument_not_reconciled_count,
                      SUM(CASE WHEN r.ConfirmerId IS NOT NULL AND r.ConfirmDate IS NOT NULL
                                    AND src.[{key_column}] IS NOT NULL AND ISNULL(src.IsReconciled,0)=0 THEN 1 ELSE 0 END) AS confirmed_session_instrument_not_reconciled_count,
                      SUM(CASE WHEN r.ConfirmerId IS NULL AND r.ConfirmDate IS NULL
                                    AND src.[{key_column}] IS NOT NULL AND ISNULL(src.IsReconciled,0)=1 THEN 1 ELSE 0 END) AS unconfirmed_session_instrument_reconciled_count
                    FROM dbo.ReconcileItem ri
                    JOIN dbo.BankBill b ON b.BankBillId=ri.BankBillId
                    JOIN dbo.Reconcile r ON r.ReconcileId=b.ReconcileId
                    LEFT JOIN dbo.[{table}] src ON src.[{key_column}]=ri.[{reference_column}]
                    WHERE ri.[{reference_column}] IS NOT NULL
                    """,
                )[0]
                typed_metrics.append({"instrument_type": table, **rows})

    normalized_state = {key: int(value or 0) for key, value in state.items()}
    normalized_shape = [
        {"typed_reference_count": int(row["ref_count"]), "link_count": int(row["link_count"])}
        for row in reference_shape
    ]
    normalized_typed = [
        {
            "instrument_type": row["instrument_type"],
            **{key: int(value or 0) for key, value in row.items() if key != "instrument_type"},
        }
        for row in typed_metrics
    ]
    errors: list[str] = []
    if normalized_state["session_count"] != table_counts["Reconcile"]:
        errors.append("session aggregate mismatch")
    if sum(row["link_count"] for row in normalized_shape) != table_counts["ReconcileItem"]:
        errors.append("reference shape aggregate mismatch")
    if sum(row["link_count"] for row in normalized_typed) != sum(
        row["typed_reference_count"] * row["link_count"] for row in normalized_shape
    ):
        errors.append("typed-link aggregate mismatch")
    if normalized_state["unconfirmed_marker_count"] + normalized_state["confirmed_marker_count"] + normalized_state["partial_marker_count"] != normalized_state["session_count"]:
        errors.append("state marker partition mismatch")

    runtime_fixture_available = table_counts["Reconcile"] > 0 and table_counts["ReconcileItem"] > 0
    summary = {
        "counted_table_count": len(table_counts),
        "session_count": table_counts["Reconcile"],
        "bank_bill_count": table_counts["BankBill"],
        "reconcile_item_count": table_counts["ReconcileItem"],
        "profile_row_count": sum(table_counts[table] for table in ("BankBillFormat", "BankBillFormatItem", "BankBillFormatType", "ReconciliationColumn")),
        "typed_instrument_family_count": len(normalized_typed),
        "bank_bill_with_multiple_links_count": topology["bank_bill_with_multiple_links_count"],
        "confirmed_session_with_multiple_links_count": topology["confirmed_session_with_multiple_links_count"],
        "partial_marker_count": normalized_state["partial_marker_count"],
        "confirmed_session_instrument_not_reconciled_count": sum(row["confirmed_session_instrument_not_reconciled_count"] for row in normalized_typed),
        "unconfirmed_session_instrument_reconciled_count": sum(row["unconfirmed_session_instrument_reconciled_count"] for row in normalized_typed),
        "runtime_fixture_available_count": int(runtime_fixture_available),
        "row_identifier_or_business_value_persisted_count": 0,
        "source_command_execution_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_bank_reconciliation_privacy_safe_integrity_aggregate_snapshot",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "NO_RUNTIME_PARITY_FIXTURE_IN_CURRENT_CLONE" if not runtime_fixture_available else "AGGREGATE_RUNTIME_FIXTURE_PRESENT",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_PRIVACY_SAFE_COUNT_AND_SUM_AGGREGATES",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "row_identifiers_dates_amounts_comments_files_or_user_values_persisted": 0,
            "aggregate_counts_only": 1,
            "procedures_or_application_commands_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": summary,
        "table_counts": table_counts,
        "state_marker_aggregates": normalized_state,
        "topology_aggregates": topology,
        "typed_reference_shape_aggregates": normalized_shape,
        "instrument_integrity_aggregates": normalized_typed,
        "interpretation": {
            "zero_current_counts_prove_no_production_issue": False,
            "current_clone_can_measure_legacy_defect_frequency": runtime_fixture_available,
            "fresh_owner_approved_redacted_snapshot_required_for_parity": not runtime_fixture_available,
            "aggregate_queries_are_reusable_on_a_future_read_only_snapshot": True,
        },
        "target_contract": {
            "pre_migration_integrity_gate_reuses_these_aggregate_metrics": True,
            "any_partial_marker_or_confirmed_unreconciled_instrument_is_quarantined": True,
            "any_zero_or_multiple_typed_reference_link_is_quarantined": True,
            "empty_headers_are_classified_before_migration": True,
            "no_legacy_row_is_auto_fixed_in_source": True,
        },
        "validation_errors": errors,
        "limits": [
            "Only aggregate counts were read; no row-level value or identifier is present.",
            "An empty clone cannot measure production defect frequency or establish runtime parity.",
            "The snapshot can lag production and must be refreshed under the same read-only controls.",
            "No anomaly is repaired automatically; future nonzero aggregates require quarantine and owner review.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"validation": artifact["validation"], "status": artifact["status"], "summary": summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
