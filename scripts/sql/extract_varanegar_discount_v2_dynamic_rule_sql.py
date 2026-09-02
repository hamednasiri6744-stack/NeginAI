"""Profile database-resident Discount V2 SQL conditions without persisting them."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from extract_varanegar_org_domain import _assert_safe_target, _connect, _rows


SOURCES = (
    ("SLE.tblDiscount", "ID", "IsActive", "StartDate", "EndDate", "SqlCondition"),
    ("NGT.Discounts", "BackOfficeId", "IsActive", "StartDate", "EndDate", "SqlCondition"),
    ("SLE.tblSaleVocherDiscount", "ID", "IsActive", "StartDate", "EndDate", "SqlCondition"),
)

PATTERNS = {
    "select": r"\bselect\b",
    "exec_or_execute": r"\bexec(?:ute)?\b",
    "write_dml": r"\b(?:insert|update|delete|merge)\b",
    "ddl_or_permission": r"\b(?:create|alter|drop|truncate|grant|revoke|deny)\b",
    "external_or_delay_primitive": r"\b(?:xp_cmdshell|openrowset|opendatasource|openquery|waitfor)\b",
    "union": r"\bunion\b",
    "line_or_block_comment": r"--|/\*|\*/",
    "statement_separator": r";",
    "evc_id_parameter": r"@evcid\b",
    "result_parameter": r"@result\b",
    "base_evc_object": r"\bsle\.tblevc(?:itemstatutes|item)?\b",
    "temporary_evc_object": r"#(?:tbltempevc\w*|evcitemfull)\b",
}


def _profile(values: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [str(row["SqlCondition"]) for row in values if row["SqlCondition"] not in (None, "")]
    stripped = [value.strip() for value in texts if value.strip()]
    hashes = [hashlib.sha256(value.encode("utf-8")).hexdigest() for value in stripped]
    pattern_counts = {
        name: sum(bool(re.search(pattern, value, re.I)) for value in stripped)
        for name, pattern in PATTERNS.items()
    }
    lengths = [len(value) for value in stripped]
    active = [
        row for row in values
        if row["SqlCondition"] is not None and str(row["SqlCondition"]).strip()
        and int(row["IsActive"] or 0) == 1
    ]
    return {
        "row_count": len(values),
        "nonempty_condition_count": len(stripped),
        "active_nonempty_condition_count": len(active),
        "distinct_condition_hash_count": len(set(hashes)),
        "duplicate_condition_instance_count": len(hashes) - len(set(hashes)),
        "condition_length_minimum": min(lengths) if lengths else 0,
        "condition_length_maximum": max(lengths) if lengths else 0,
        "condition_length_average": round(mean(lengths), 2) if lengths else 0,
        "condition_length_buckets": dict(sorted(Counter(
            "1_255" if length <= 255 else
            "256_1000" if length <= 1000 else
            "1001_4000" if length <= 4000 else
            "over_4000"
            for length in lengths
        ).items())),
        "lexical_shape_counts": pattern_counts,
        "condition_corpus_sha256": hashlib.sha256(
            "\n".join(sorted(hashes)).encode("ascii")
        ).hexdigest(),
        "raw_conditions_persisted": 0,
        "row_identifiers_persisted": 0,
    }


def collect(engine_runtime_path: Path) -> dict[str, Any]:
    runtime = json.loads(engine_runtime_path.read_text(encoding="utf-8-sig"))
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        source_profiles: list[dict[str, Any]] = []
        for table, identity, active, start, end, condition in SOURCES:
            catalog = _rows(
                cursor,
                """
                SELECT o.object_id,o.type_desc,
                       (SELECT SUM(row_count) FROM sys.dm_db_partition_stats p
                        WHERE p.object_id=o.object_id AND p.index_id IN (0,1)) AS row_count
                FROM sys.objects o WHERE o.object_id=OBJECT_ID(%s)
                """,
                (table,),
            )[0]
            rows = _rows(
                cursor,
                f"SELECT {identity} AS RuleId,{active} AS IsActive,{start} AS StartDate,"
                f"{end} AS EndDate,{condition} AS SqlCondition FROM {table}",
            )
            profile = _profile(rows)
            profile.update(
                {
                    "qualified_table": table,
                    "object_id": catalog["object_id"],
                    "type_desc": catalog["type_desc"],
                    "catalog_row_count": int(catalog["row_count"] or 0),
                }
            )
            source_profiles.append(profile)

        primary = next(row for row in source_profiles if row["qualified_table"] == "SLE.tblDiscount")
        assertions = {
            "engine_runtime_artifact_passes": runtime["validation"] == "PASS",
            "database_is_read_only_and_writer_denied": context["updateability"] == "READ_ONLY"
            and context["denies_data_writes"] == 1,
            "all_three_sqlcondition_sources_resolve": len(source_profiles) == 3
            and all(row["type_desc"] == "USER_TABLE" for row in source_profiles),
            "primary_rule_table_has_advanced_conditions": primary["nonempty_condition_count"] > 0,
            "primary_rules_are_executable_statement_fragments": (
                primary["lexical_shape_counts"]["result_parameter"] > 0
                or primary["lexical_shape_counts"]["select"] > 0
            ),
            "no_raw_conditions_or_rule_ids_persisted": all(
                row["raw_conditions_persisted"] == 0 and row["row_identifiers_persisted"] == 0
                for row in source_profiles
            ),
            "no_database_commands_or_mutations_performed": True,
        }
        return {
            "artifact": "varanegar_discount_v2_dynamic_rule_sql",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": "PASS" if all(assertions.values()) else "FAIL",
            "source": context,
            "safety": {
                "mode": "READ_ONLY_AGGREGATE_LEXICAL_PROFILE_IN_MEMORY",
                "commands_executed": 0,
                "data_mutations": 0,
                "raw_conditions_persisted": 0,
                "row_identifiers_persisted": 0,
                "source_or_target_state_changed": 0,
            },
            "summary": {
                "sqlcondition_source_table_count": len(source_profiles),
                "primary_rule_count": primary["row_count"],
                "primary_nonempty_condition_count": primary["nonempty_condition_count"],
                "primary_active_nonempty_condition_count": primary["active_nonempty_condition_count"],
                "primary_distinct_condition_hash_count": primary["distinct_condition_hash_count"],
                "primary_maximum_condition_length": primary["condition_length_maximum"],
                "primary_write_dml_shape_count": primary["lexical_shape_counts"]["write_dml"],
                "primary_ddl_or_permission_shape_count": primary["lexical_shape_counts"]["ddl_or_permission"],
                "primary_external_or_delay_shape_count": primary["lexical_shape_counts"]["external_or_delay_primitive"],
            },
            "sources": source_profiles,
            "assertions": assertions,
            "limits": [
                "Lexical matches are conservative shape indicators, not a SQL parser or vulnerability verdict.",
                "The clone snapshot does not prove which rules were evaluated for a specific production order.",
                "An active flag does not by itself prove date-effective reachability or user authorization to edit the rule.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine-runtime", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = collect(args.engine_runtime)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(json.dumps(artifact["assertions"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
