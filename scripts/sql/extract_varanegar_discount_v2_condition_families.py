"""Build sanitized structural/usage profiles for Discount V2 condition families."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import _assert_safe_target, _connect, _rows


DATE_FROM = "1405/03/01"
DATE_TO = "1405/05/31"
KEYWORDS = {
    "select", "from", "where", "join", "inner", "left", "right", "full", "on",
    "and", "or", "not", "null", "is", "in", "exists", "case", "when", "then",
    "else", "end", "as", "distinct", "group", "by", "having", "order", "asc",
    "desc", "top", "set", "declare", "int", "bigint", "money", "varchar",
    "nvarchar", "float", "real", "bit", "output", "with", "nolock", "like",
    "between", "true", "false", "convert", "cast", "date", "datetime",
}
FUNCTIONS = {
    "isnull", "coalesce", "count", "sum", "min", "max", "avg", "abs", "round",
    "convert", "cast", "len", "ltrim", "rtrim", "substring", "charindex",
    "dateadd", "datediff", "getdate", "row_number", "rank", "dense_rank",
}


def _mask_literals_and_comments(sql: str) -> str:
    sql = re.sub(r"N?'(?:''|[^'])*'", "''", sql, flags=re.S | re.I)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\r\n]*", " ", sql)
    return sql


def _shape(sql: str, catalog_columns: set[str]) -> dict[str, Any]:
    code = _mask_literals_and_comments(sql).casefold()
    parameters = sorted(set(re.findall(r"@[a-z_][a-z0-9_]*", code)))
    schema_objects = sorted(set(
        value.replace("[", "").replace("]", "")
        for value in re.findall(r"\b[a-z_][a-z0-9_]*\s*\.\s*[a-z_][a-z0-9_]*\b", code)
        if value.split(".", 1)[0].strip(" []") in {"sle", "gnr", "inv", "acc", "gnm", "dbo"}
    ))
    temp_objects = sorted(set(re.findall(r"#[a-z_][a-z0-9_]*", code)))
    from_join_objects = sorted(set(
        value.replace("[", "").replace("]", "").strip(".;")
        for value in re.findall(
            r"\b(?:from|join)\s+([#\[\]a-z_][#\[\]a-z0-9_.]*)",
            code,
        )
        if not value.startswith("(")
    ))
    identifier_tokens = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", code))
    column_candidates = sorted(identifier_tokens & catalog_columns)
    function_calls = sorted(set(
        name for name in re.findall(r"\b([a-z_][a-z0-9_]*)\s*\(", code)
        if name in FUNCTIONS
    ))
    return {
        "parameters": parameters,
        "schema_object_refs": schema_objects,
        "temporary_object_refs": temp_objects,
        "from_join_object_refs": from_join_objects,
        "column_candidates": column_candidates,
        "function_calls": function_calls,
        "boolean_and_count": len(re.findall(r"\band\b", code)),
        "boolean_or_count": len(re.findall(r"\bor\b", code)),
        "exists_count": len(re.findall(r"\bexists\b", code)),
        "not_exists_count": len(re.findall(r"\bnot\s+exists\b", code)),
        "in_operator_count": len(re.findall(r"\bin\s*\(", code)),
        "comparison_operator_count": len(re.findall(r"(?:<>|!=|<=|>=|(?<![<>=])=(?!=)|<|>)", code)),
        "select_count": len(re.findall(r"\bselect\b", code)),
        "subquery_indicator": len(re.findall(r"\(\s*select\b", code)),
    }


def collect(previous_profile_path: Path) -> dict[str, Any]:
    previous = json.loads(previous_profile_path.read_text(encoding="utf-8-sig"))
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        rules = _rows(
            cursor,
            """
            SELECT d.ID,d.IsActive,d.StartDate,d.EndDate,d.SqlCondition,
                   l.ChangeDate AS DeactivationDate,l.IsActiveChangedTo
            FROM SLE.tblDiscount d
            LEFT JOIN SLE.tblDiscount_DeactivationLog l ON l.DiscountID=d.ID
            WHERE d.SqlCondition IS NOT NULL AND LTRIM(RTRIM(d.SqlCondition))<>''
            """,
        )
        deactivation_log = _rows(
            cursor,
            """
            SELECT COUNT_BIG(*) AS rows,COUNT(DISTINCT DiscountID) AS rules,
                   SUM(CASE WHEN IsActiveChangedTo=1 THEN 1 ELSE 0 END) AS to_active,
                   SUM(CASE WHEN IsActiveChangedTo=0 THEN 1 ELSE 0 END) AS to_inactive,
                   SUM(CASE WHEN ChangeDate IS NULL THEN 1 ELSE 0 END) AS missing_change_date
            FROM SLE.tblDiscount_DeactivationLog
            """,
        )[0]
        current_solar_date = str(_rows(
            cursor,
            "SELECT SolarDate FROM dbo.Calendar WHERE Date=CAST(GETDATE() AS date)",
        )[0]["SolarDate"])
        catalog_columns = {
            str(row["name"]).casefold()
            for row in _rows(cursor, "SELECT DISTINCT name FROM sys.columns")
        }
        usage_rows = _rows(
            cursor,
            f"""
            SELECT ds.DisRef,COUNT_BIG(*) AS applied_rows,
                   COUNT(DISTINCT ds.HdrRef) AS sales,
                   SUM(CASE WHEN ISNULL(ds.Discount,0)<>0 THEN 1 ELSE 0 END) AS discount_rows,
                   SUM(CASE WHEN ISNULL(ds.AddAmount,0)<>0 THEN 1 ELSE 0 END) AS addition_rows
            FROM SLE.tblDisSale ds
            JOIN SLE.tblSaleHdr h ON h.ID=ds.HdrRef
            WHERE h.SaleDate BETWEEN '{DATE_FROM}' AND '{DATE_TO}'
              AND ISNULL(h.CancelFlag,0)=0
            GROUP BY ds.DisRef
            """,
        )
        usage_totals = _rows(
            cursor,
            f"""
            SELECT COUNT_BIG(*) AS all_applied_rows,
                   COUNT(DISTINCT ds.HdrRef) AS all_sales,
                   COUNT(DISTINCT ds.DisRef) AS all_rules,
                   SUM(CASE WHEN d.SqlCondition IS NOT NULL
                                  AND LTRIM(RTRIM(d.SqlCondition))<>'' THEN 1 ELSE 0 END)
                       AS advanced_applied_rows,
                   COUNT(DISTINCT CASE WHEN d.SqlCondition IS NOT NULL
                                             AND LTRIM(RTRIM(d.SqlCondition))<>''
                                       THEN ds.HdrRef END) AS advanced_sales,
                   COUNT(DISTINCT CASE WHEN d.SqlCondition IS NOT NULL
                                             AND LTRIM(RTRIM(d.SqlCondition))<>''
                                       THEN ds.DisRef END) AS advanced_rules
            FROM SLE.tblDisSale ds
            JOIN SLE.tblSaleHdr h ON h.ID=ds.HdrRef
            LEFT JOIN SLE.tblDiscount d ON d.ID=ds.DisRef
            WHERE h.SaleDate BETWEEN '{DATE_FROM}' AND '{DATE_TO}'
              AND ISNULL(h.CancelFlag,0)=0
            """,
        )[0]
        usage_by_rule = {int(row["DisRef"]): row for row in usage_rows}
        grouped: dict[str, dict[str, Any]] = {}
        for row in rules:
            text = str(row["SqlCondition"]).strip()
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest not in grouped:
                grouped[digest] = {
                    "condition_sha256": digest,
                    "condition_length": len(text),
                    "rule_instance_count": 0,
                    "active_rule_instance_count": 0,
                    "current_effective_rule_instance_count": 0,
                    "business_window_date_overlap_rule_instance_count": 0,
                    "deactivated_before_window_rule_instance_count": 0,
                    "deactivated_inside_window_rule_instance_count": 0,
                    "deactivated_after_window_rule_instance_count": 0,
                    "current_active_with_deactivation_log_count": 0,
                    "three_month_used_rule_instance_count": 0,
                    "three_month_used_current_active_rule_instance_count": 0,
                    "three_month_used_deactivated_inside_window_rule_instance_count": 0,
                    "three_month_applied_row_count": 0,
                    "three_month_sale_count_sum": 0,
                    "three_month_discount_row_count": 0,
                    "three_month_addition_row_count": 0,
                    "structure": _shape(text, catalog_columns),
                    "raw_condition_persisted": False,
                    "rule_identifier_persisted": False,
                }
            family = grouped[digest]
            family["rule_instance_count"] += 1
            family["active_rule_instance_count"] += int(row["IsActive"] or 0) == 1
            start_date = str(row["StartDate"] or "")
            end_date = str(row["EndDate"] or "")
            family["current_effective_rule_instance_count"] += (
                int(row["IsActive"] or 0) == 1
                and (not start_date or start_date <= current_solar_date)
                and (not end_date or end_date >= current_solar_date)
            )
            family["business_window_date_overlap_rule_instance_count"] += (
                (not start_date or start_date <= DATE_TO)
                and (not end_date or end_date >= DATE_FROM)
            )
            deactivation = row["DeactivationDate"]
            if deactivation is not None:
                deactivation_day = deactivation.date().isoformat()
                family["deactivated_before_window_rule_instance_count"] += deactivation_day < "2026-05-22"
                family["deactivated_inside_window_rule_instance_count"] += "2026-05-22" <= deactivation_day <= "2026-08-22"
                family["deactivated_after_window_rule_instance_count"] += deactivation_day > "2026-08-22"
                family["current_active_with_deactivation_log_count"] += int(row["IsActive"] or 0) == 1
            usage = usage_by_rule.get(int(row["ID"]))
            if usage:
                family["three_month_used_rule_instance_count"] += 1
                family["three_month_used_current_active_rule_instance_count"] += int(row["IsActive"] or 0) == 1
                if deactivation is not None:
                    family["three_month_used_deactivated_inside_window_rule_instance_count"] += (
                        "2026-05-22" <= deactivation.date().isoformat() <= "2026-08-22"
                    )
                family["three_month_applied_row_count"] += int(usage["applied_rows"] or 0)
                family["three_month_sale_count_sum"] += int(usage["sales"] or 0)
                family["three_month_discount_row_count"] += int(usage["discount_rows"] or 0)
                family["three_month_addition_row_count"] += int(usage["addition_rows"] or 0)

        families = sorted(
            grouped.values(),
            key=lambda row: (-row["three_month_applied_row_count"], -row["rule_instance_count"], row["condition_sha256"]),
        )
        all_objects = sorted({value for row in families for value in row["structure"]["schema_object_refs"]})
        all_temps = sorted({value for row in families for value in row["structure"]["temporary_object_refs"]})
        all_from_join = sorted({value for row in families for value in row["structure"]["from_join_object_refs"]})
        all_columns = sorted({value for row in families for value in row["structure"]["column_candidates"]})

        def aggregate_vocabulary(key: str) -> list[dict[str, Any]]:
            profiles: list[dict[str, Any]] = []
            values = sorted({value for row in families for value in row["structure"][key]})
            for value in values:
                selected = [row for row in families if value in row["structure"][key]]
                profiles.append(
                    {
                        "name": value,
                        "condition_family_count": len(selected),
                        "rule_instance_count": sum(row["rule_instance_count"] for row in selected),
                        "current_effective_rule_instance_count": sum(
                            row["current_effective_rule_instance_count"] for row in selected
                        ),
                        "three_month_used_rule_instance_count": sum(
                            row["three_month_used_rule_instance_count"] for row in selected
                        ),
                        "three_month_applied_row_count": sum(
                            row["three_month_applied_row_count"] for row in selected
                        ),
                    }
                )
            return sorted(
                profiles,
                key=lambda row: (-row["rule_instance_count"], -row["condition_family_count"], row["name"]),
            )

        column_profiles = aggregate_vocabulary("column_candidates")
        object_profiles = aggregate_vocabulary("from_join_object_refs")
        assertions = {
            "previous_rule_profile_passes": previous["validation"] == "PASS",
            "all_845_nonempty_rules_grouped": len(rules) == 845
            and sum(row["rule_instance_count"] for row in families) == 845,
            "exactly_44_condition_families": len(families) == 44,
            "family_count_matches_previous_profile": len(families)
            == previous["summary"]["primary_distinct_condition_hash_count"],
            "deactivation_log_is_one_way_and_one_row_per_rule": int(deactivation_log["rows"] or 0) == 1313
            and int(deactivation_log["rules"] or 0) == 1313
            and int(deactivation_log["to_active"] or 0) == 0
            and int(deactivation_log["to_inactive"] or 0) == 1313
            and int(deactivation_log["missing_change_date"] or 0) == 0,
            "database_is_read_only_and_writer_denied": context["updateability"] == "READ_ONLY"
            and context["denies_data_writes"] == 1,
            "no_raw_conditions_or_rule_ids_persisted": all(
                not row["raw_condition_persisted"] and not row["rule_identifier_persisted"]
                for row in families
            ),
            "no_database_commands_or_mutations_performed": True,
        }
        return {
            "artifact": "varanegar_discount_v2_condition_families",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": "PASS" if all(assertions.values()) else "FAIL",
            "source": context,
            "safety": {
                "mode": "READ_ONLY_IN_MEMORY_SANITIZED_STRUCTURE_AND_AGGREGATE_USAGE",
                "commands_executed": 0,
                "data_mutations": 0,
                "raw_conditions_persisted": 0,
                "rule_identifiers_persisted": 0,
                "business_scalar_values_persisted": 0,
            },
            "business_window": {
                "from": DATE_FROM,
                "to": DATE_TO,
                "basis": "non-cancelled sale headers; applied rows grouped by rule then condition hash",
            },
            "summary": {
                "condition_family_count": len(families),
                "rule_instance_count": sum(row["rule_instance_count"] for row in families),
                "active_rule_instance_count": sum(row["active_rule_instance_count"] for row in families),
                "current_effective_rule_instance_count": sum(row["current_effective_rule_instance_count"] for row in families),
                "current_effective_condition_family_count": sum(row["current_effective_rule_instance_count"] > 0 for row in families),
                "business_window_date_overlap_rule_instance_count": sum(row["business_window_date_overlap_rule_instance_count"] for row in families),
                "business_window_date_overlap_condition_family_count": sum(row["business_window_date_overlap_rule_instance_count"] > 0 for row in families),
                "advanced_deactivated_before_window_rule_count": sum(row["deactivated_before_window_rule_instance_count"] for row in families),
                "advanced_deactivated_inside_window_rule_count": sum(row["deactivated_inside_window_rule_instance_count"] for row in families),
                "advanced_deactivated_after_window_rule_count": sum(row["deactivated_after_window_rule_instance_count"] for row in families),
                "advanced_current_active_with_deactivation_log_count": sum(row["current_active_with_deactivation_log_count"] for row in families),
                "three_month_used_condition_family_count": sum(row["three_month_applied_row_count"] > 0 for row in families),
                "three_month_used_advanced_rule_count": sum(row["three_month_used_rule_instance_count"] for row in families),
                "three_month_advanced_condition_applied_row_count": sum(row["three_month_applied_row_count"] for row in families),
                "three_month_advanced_condition_discount_row_count": sum(row["three_month_discount_row_count"] for row in families),
                "three_month_advanced_condition_addition_row_count": sum(row["three_month_addition_row_count"] for row in families),
                "three_month_advanced_condition_distinct_sale_count": int(usage_totals["advanced_sales"] or 0),
                "three_month_all_applied_rule_row_count": int(usage_totals["all_applied_rows"] or 0),
                "three_month_all_applied_rule_count": int(usage_totals["all_rules"] or 0),
                "three_month_advanced_applied_row_share_percent": round(
                    100 * int(usage_totals["advanced_applied_rows"] or 0)
                    / max(1, int(usage_totals["all_applied_rows"] or 0)),
                    4,
                ),
                "schema_object_reference_count": len(all_objects),
                "temporary_object_reference_count": len(all_temps),
                "from_join_object_reference_count": len(all_from_join),
                "column_candidate_count": len(all_columns),
            },
            "families": families,
            "vocabulary": {
                "schema_object_refs": all_objects,
                "temporary_object_refs": all_temps,
                "from_join_object_refs": all_from_join,
                "column_candidates": all_columns,
                "column_profiles": column_profiles,
                "from_join_object_profiles": object_profiles,
            },
            "assertions": assertions,
            "limits": [
                "Regex structure extraction is a sanitized inventory, not a complete T-SQL parser.",
                "Summing distinct sales per rule can double-count one sale across multiple rules/families.",
                "Applied tblDisSale rows prove retained effects, not every evaluated or rejected advanced rule.",
                "Family hashes identify code shapes but do not define their approved target business meaning.",
                "Current IsActive is not reconstructed historically; date-overlap counts do not prove a rule was active during the past window.",
                "The retained log records deactivation only; one currently active advanced rule has an older deactivation row, proving reactivation is not completely represented by this log.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-profile", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = collect(args.previous_profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(json.dumps(artifact["assertions"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
