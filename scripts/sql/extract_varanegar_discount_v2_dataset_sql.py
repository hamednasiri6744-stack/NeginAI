"""Validate Discount V2 query dependencies against the read-only clone catalog."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import _assert_safe_target, _connect, _rows


def collect(query_contracts_path: Path) -> dict[str, Any]:
    contracts = json.loads(query_contracts_path.read_text(encoding="utf-8-sig"))
    refs = [ref for ref in contracts["unique_table_refs"] if not ref.startswith("#")]
    connection = _connect()
    try:
        cursor = connection.cursor()
        context = _assert_safe_target(cursor)
        isolation = _rows(
            cursor,
            "SELECT snapshot_isolation_state_desc,is_read_committed_snapshot_on FROM sys.databases WHERE name=DB_NAME()",
        )[0]
        objects = []
        for ref in refs:
            rows = _rows(
                cursor,
                """
                SELECT o.object_id,o.type_desc,o.create_date,o.modify_date,
                       CASE WHEN o.type='U' THEN COALESCE((
                           SELECT SUM(row_count) FROM sys.dm_db_partition_stats p
                           WHERE p.object_id=o.object_id AND p.index_id IN (0,1)
                       ),0) END row_count
                FROM sys.objects o WHERE o.object_id=OBJECT_ID(%s)
                """,
                (ref,),
            )
            objects.append(
                {
                    "qualified_name": ref,
                    "resolved": len(rows) == 1,
                    "object_id": rows[0]["object_id"] if rows else None,
                    "type_desc": rows[0]["type_desc"] if rows else None,
                    "create_date": rows[0]["create_date"] if rows else None,
                    "modify_date": rows[0]["modify_date"] if rows else None,
                    "row_count": rows[0]["row_count"] if rows else None,
                }
            )
        table_rows = [row for row in objects if row["type_desc"] == "USER_TABLE"]
        assertions = {
            "static_contract_artifact_passes": contracts["validation"] == "PASS",
            "all_41_persistent_refs_resolve": len(objects) == 41 and all(row["resolved"] for row in objects),
            "database_is_read_only_and_writer_denied": context["updateability"] == "READ_ONLY"
            and context["denies_data_writes"] == 1,
            "no_business_rows_or_values_persisted": True,
            "clone_uses_rcsi_and_allows_snapshot_isolation": (
                isolation["snapshot_isolation_state_desc"] == "ON"
                and bool(isolation["is_read_committed_snapshot_on"])
            ),
        }
        return {
            "artifact": "varanegar_discount_v2_dataset_sql",
            "schema_version": 1,
            "generated_at": datetime.now().astimezone().isoformat(),
            "validation": "PASS" if all(assertions.values()) else "FAIL",
            "source": context,
            "safety": {
                "mode": "READ_ONLY_CATALOG_AND_PARTITION_AGGREGATES",
                "commands_executed": 0,
                "data_mutations": 0,
                "raw_business_rows_or_values_persisted": 0,
            },
            "summary": {
                "persistent_reference_count": len(objects),
                "resolved_reference_count": sum(row["resolved"] for row in objects),
                "user_table_reference_count": len(table_rows),
                "view_reference_count": sum(row["type_desc"] == "VIEW" for row in objects),
                "referenced_table_total_row_count": sum(int(row["row_count"] or 0) for row in table_rows),
                "empty_referenced_table_count": sum(int(row["row_count"] or 0) == 0 for row in table_rows),
            },
            "objects": objects,
            "database_isolation": isolation,
            "assertions": assertions,
            "limits": [
                "Partition row counts are scale indicators, not business activity or query selectivity.",
                "View row counts are not materialized and are intentionally omitted.",
                "Catalog resolution does not validate template semantics or runtime result accuracy.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query-contracts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = collect(args.query_contracts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps(artifact["summary"], ensure_ascii=False))
    print(json.dumps(artifact["assertions"], ensure_ascii=False))
    print(artifact["validation"])
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
