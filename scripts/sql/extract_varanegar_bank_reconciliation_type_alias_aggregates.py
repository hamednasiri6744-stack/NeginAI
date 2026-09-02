"""Extract privacy-safe aggregate evidence for reconciliation Type aliases.

Only counts for four pre-allowlisted literals are persisted. No row identifier,
date, amount, account, user value, free text, or non-allowlisted Type is read.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


ALIASES = (
    ("RBANKDARFT", "RBANKDRAFT", 1),
    ("RCASHDRAF", "RCASHDRAFT", None),
)
SUMMARY_PREDICATES = (
    ("RCHEQUE", 3),
    ("RBANKDARFT", 1),
    ("PCHEQUE", 3),
    ("TRANSFER", None),
    ("PWITHDRAW", None),
    ("RCASHDRAF", None),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            row = _rows(
                cursor,
                """
                SELECT
                  COUNT_BIG(*) AS total_count,
                  SUM(CASE WHEN [Type]='RCHEQUE' THEN 1 ELSE 0 END) AS rcheque_count,
                  SUM(CASE WHEN [Type]='RCHEQUE' AND StatusID=3 THEN 1 ELSE 0 END) AS rcheque_status_3_count,
                  SUM(CASE WHEN [Type]='PCHEQUE' THEN 1 ELSE 0 END) AS pcheque_count,
                  SUM(CASE WHEN [Type]='PCHEQUE' AND StatusID=3 THEN 1 ELSE 0 END) AS pcheque_status_3_count,
                  SUM(CASE WHEN [Type]='TRANSFER' THEN 1 ELSE 0 END) AS transfer_count,
                  SUM(CASE WHEN [Type]='PWITHDRAW' THEN 1 ELSE 0 END) AS pwithdraw_count,
                  SUM(CASE WHEN [Type]='RBANKDARFT' THEN 1 ELSE 0 END) AS rbankdarft_count,
                  SUM(CASE WHEN [Type]='RBANKDARFT' AND StatusID=1 THEN 1 ELSE 0 END) AS rbankdarft_status_1_count,
                  SUM(CASE WHEN [Type]='RBANKDRAFT' THEN 1 ELSE 0 END) AS rbankdraft_count,
                  SUM(CASE WHEN [Type]='RBANKDRAFT' AND StatusID=1 THEN 1 ELSE 0 END) AS rbankdraft_status_1_count,
                  SUM(CASE WHEN [Type]='RCASHDRAF' THEN 1 ELSE 0 END) AS rcashdraf_count,
                  SUM(CASE WHEN [Type]='RCASHDRAFT' THEN 1 ELSE 0 END) AS rcashdraft_count
                FROM dbo.BankAccountCardex
                """,
            )[0]
            catalog_consumers = _rows(
                cursor,
                """
                SELECT 'RCASH_DRAFT' AS alias_family,s.name AS schema_name,o.name AS object_name,o.type_desc,
                  CASE WHEN m.definition LIKE '%''RCASHDRAF''%' THEN 1 ELSE 0 END AS short_literal,
                  CASE WHEN m.definition LIKE '%''RCASHDRAFT''%' THEN 1 ELSE 0 END AS canonical_literal
                FROM sys.sql_modules m
                JOIN sys.objects o ON o.object_id=m.object_id
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE m.definition LIKE '%''RCASHDRAF''%'
                   OR m.definition LIKE '%''RCASHDRAFT''%'
                ORDER BY s.name,o.name
                """,
            )
            bank_catalog_consumers = _rows(
                cursor,
                """
                SELECT 'RBANK_DRAFT' AS alias_family,s.name AS schema_name,o.name AS object_name,o.type_desc,
                  CASE WHEN m.definition LIKE '%''RBANKDARFT''%' THEN 1 ELSE 0 END AS short_literal,
                  CASE WHEN m.definition LIKE '%''RBANKDRAFT''%' THEN 1 ELSE 0 END AS canonical_literal
                FROM sys.sql_modules m
                JOIN sys.objects o ON o.object_id=m.object_id
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                WHERE m.definition LIKE '%''RBANKDARFT''%'
                   OR m.definition LIKE '%''RBANKDRAFT''%'
                ORDER BY s.name,o.name
                """,
            )

    counts = {key: int(value or 0) for key, value in row.items()}
    alias_rows = []
    for summary_literal, matching_literal, status_id in ALIASES:
        prefix_summary = summary_literal.lower()
        prefix_matching = matching_literal.lower()
        summary_count = counts[f"{prefix_summary}_count"]
        matching_count = counts[f"{prefix_matching}_count"]
        alias_rows.append(
            {
                "summary_literal": summary_literal,
                "matching_literal": matching_literal,
                "summary_literal_count": summary_count,
                "matching_literal_count": matching_count,
                "summary_status_filter": status_id,
                "summary_literal_status_match_count": (
                    counts[f"{prefix_summary}_status_1_count"] if status_id == 1 else None
                ),
                "matching_literal_status_match_count": (
                    counts[f"{prefix_matching}_status_1_count"] if status_id == 1 else None
                ),
                "observed_literal_mismatch_count": abs(matching_count - summary_count),
            }
        )

    predicate_rows = []
    for literal, status_id in SUMMARY_PREDICATES:
        prefix = literal.lower()
        total = counts[f"{prefix}_count"]
        eligible = counts[f"{prefix}_status_{status_id}_count"] if status_id is not None else total
        predicate_rows.append(
            {
                "summary_literal": literal,
                "required_status_id": status_id,
                "literal_row_count": total,
                "predicate_eligible_row_count": eligible,
                "status_excluded_row_count": total - eligible,
            }
        )

    alias_pair_literal_count = sum(
        counts[f"{literal.lower()}_count"]
        for pair in ALIASES
        for literal in pair[:2]
    )
    known_literal_count = sum(
        counts[f"{literal.lower()}_count"]
        for literal in {row[0] for row in SUMMARY_PREDICATES} | {row[1] for row in ALIASES}
    )
    summary_eligible_count = sum(row["predicate_eligible_row_count"] for row in predicate_rows)
    canonical_alias_alternative_count = (
        counts["rbankdraft_status_1_count"] + counts["rcashdraft_count"]
    )
    normalized_consumers = [
        {
            "alias_family": row["alias_family"],
            "schema_name": row["schema_name"],
            "object_name": row["object_name"],
            "object_type": row["type_desc"],
            "uses_short_summary_literal": int(row["short_literal"]),
            "uses_canonical_literal": int(row["canonical_literal"]),
        }
        for row in catalog_consumers + bank_catalog_consumers
    ]
    errors: list[str] = []
    if known_literal_count > counts["total_count"]:
        errors.append("known literal count exceeds table count")
    if summary_eligible_count > known_literal_count:
        errors.append("Summary-eligible count exceeds known literal count")
    if any(row["summary_literal_count"] > row["matching_literal_count"] + counts["total_count"] for row in alias_rows):
        errors.append("invalid alias aggregate")
    summary_consumers = [
        row for row in normalized_consumers if row["object_name"] == "DoReconcile_GetSummary"
    ]
    if (
        len(summary_consumers) != len(ALIASES)
        or {row["alias_family"] for row in summary_consumers} != {"RCASH_DRAFT", "RBANK_DRAFT"}
        or any(row["uses_short_summary_literal"] != 1 for row in summary_consumers)
    ):
        errors.append("Summary short-literal catalog consumers not found for both alias families")

    summary = {
        "bank_account_cardex_row_count": counts["total_count"],
        "alias_pair_literal_row_count": alias_pair_literal_count,
        "known_summary_or_matching_literal_row_count": known_literal_count,
        "other_type_row_count": counts["total_count"] - known_literal_count,
        "summary_predicate_eligible_row_count": summary_eligible_count,
        "canonical_alias_alternative_eligible_row_count": canonical_alias_alternative_count,
        "status_excluded_known_literal_row_count": sum(row["status_excluded_row_count"] for row in predicate_rows),
        "summary_predicate_eligible_share_basis_points": round(summary_eligible_count * 10000 / counts["total_count"]),
        "canonical_alias_alternative_share_basis_points": round(canonical_alias_alternative_count * 10000 / counts["total_count"]),
        "short_literal_catalog_consumer_count": sum(row["uses_short_summary_literal"] for row in normalized_consumers),
        "canonical_literal_catalog_consumer_count": sum(row["uses_canonical_literal"] for row in normalized_consumers),
        "catalog_consumer_with_both_literals_count": sum(
            row["uses_short_summary_literal"] and row["uses_canonical_literal"]
            for row in normalized_consumers
        ),
        "alias_family_with_short_summary_outlier_count": len(summary_consumers),
        "alias_pair_count": len(alias_rows),
        "pair_with_observed_count_difference_count": sum(
            row["summary_literal_count"] != row["matching_literal_count"] for row in alias_rows
        ),
        "summary_literal_total_count": sum(row["summary_literal_count"] for row in alias_rows),
        "matching_literal_total_count": sum(row["matching_literal_count"] for row in alias_rows),
        "row_identifier_or_business_value_persisted_count": 0,
        "source_command_execution_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_bank_reconciliation_privacy_safe_type_alias_aggregate_snapshot",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "status": "OBSERVED_CLONE_ALIAS_DIVERGENCE_REQUIRES_EXPLICIT_TARGET_DECISION",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_PRE_ALLOWLISTED_LITERAL_COUNTS_AND_CATALOG_CONSUMERS",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "row_identifiers_dates_amounts_accounts_users_or_free_text_persisted": 0,
            "non_allowlisted_type_values_selected_or_persisted": 0,
            "raw_sql_module_definitions_persisted": 0,
            "procedures_or_application_commands_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": summary,
        "summary_predicate_aggregates": predicate_rows,
        "alias_aggregates": alias_rows,
        "catalog_literal_consumers": normalized_consumers,
        "interpretation": {
            "clone_proves_summary_runtime_result_parity": False,
            "clone_proves_production_frequency": False,
            "observed_counts_make_silent_normalization_safe": False,
            "short_literal_isolated_to_summary_in_clone_catalog": (
                summary["short_literal_catalog_consumer_count"] == len(ALIASES)
                and summary["alias_family_with_short_summary_outlier_count"] == len(ALIASES)
                and summary["canonical_literal_catalog_consumer_count"] > len(ALIASES)
            ),
            "owner_decision_and_redacted_summary_parity_fixture_still_required": True,
            "canonical_matching_literal_can_be_assumed_equivalent_to_summary_literal": False,
        },
        "target_contract": {
            "preserve_legacy_summary_literals_until_owner_decision": True,
            "add_explicit_alias_compatibility_tests": True,
            "measure_both_spellings_on_fresh_read_only_snapshot": True,
            "do_not_rewrite_source_rows": True,
        },
        "validation_errors": errors,
        "limits": [
            "Counts come from the current read-only clone, not production.",
            "Only the six observed Summary literals and two matching aliases were counted; other Type values were not selected.",
            "Catalog consumer names and object types are metadata; raw SQL definitions are not persisted.",
            "A count difference shows data/SQL vocabulary divergence but does not authorize target normalization.",
            "Summary was not executed, so result parity remains unproven.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"validation": artifact["validation"], "summary": summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
