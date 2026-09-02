"""Extract the clone catalog model behind POS session receipt replication."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows


TABLES = (
    "BaseChargeDevice",
    "InstalmentMethodThirdParty",
    "PCredit",
    "POrder",
    "POrderLine",
    "POrderRetLine",
    "POrderXBO",
    "PPayment",
    "PRetSaleXBO",
    "PSession",
    "safe",
    "Subscriber",
    "TblPayWithPaymentRelation",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    placeholders = ",".join("%s" for _ in TABLES)
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            table_rows = _rows(
                cursor,
                f"""
                SELECT o.object_id,s.name AS schema_name,o.name AS table_name,
                       SUM(CASE WHEN p.index_id IN (0,1) THEN p.rows ELSE 0 END) AS row_count
                FROM sys.objects o
                JOIN sys.schemas s ON s.schema_id=o.schema_id
                LEFT JOIN sys.partitions p ON p.object_id=o.object_id
                WHERE o.type='U' AND s.name='dbo' AND o.name IN ({placeholders})
                GROUP BY o.object_id,s.name,o.name
                """,
                TABLES,
            )
            object_ids = [int(row["object_id"]) for row in table_rows]
            if object_ids:
                id_marks = ",".join("%s" for _ in object_ids)
                column_rows = _rows(
                    cursor,
                    f"""
                    SELECT c.object_id,c.column_id,c.name AS column_name,t.name AS data_type,
                           c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,c.is_computed
                    FROM sys.columns c
                    JOIN sys.types t ON t.user_type_id=c.user_type_id
                    WHERE c.object_id IN ({id_marks})
                    ORDER BY c.object_id,c.column_id
                    """,
                    object_ids,
                )
                key_rows = _rows(
                    cursor,
                    f"""
                    SELECT i.object_id,i.name AS index_name,i.is_primary_key,i.is_unique,
                           ic.key_ordinal,c.name AS column_name
                    FROM sys.indexes i
                    JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
                    JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
                    WHERE i.object_id IN ({id_marks}) AND (i.is_primary_key=1 OR i.is_unique=1)
                      AND ic.is_included_column=0
                    ORDER BY i.object_id,i.name,ic.key_ordinal
                    """,
                    object_ids,
                )
                fk_rows = _rows(
                    cursor,
                    f"""
                    SELECT fk.name AS foreign_key_name,
                           ps.name AS parent_schema,po.name AS parent_table,pc.name AS parent_column,
                           rs.name AS referenced_schema,ro.name AS referenced_table,rc.name AS referenced_column,
                           fkc.constraint_column_id,fk.is_disabled,fk.is_not_trusted,
                           CASE WHEN po.object_id IN ({id_marks}) THEN 1 ELSE 0 END AS parent_in_scope,
                           CASE WHEN ro.object_id IN ({id_marks}) THEN 1 ELSE 0 END AS referenced_in_scope
                    FROM sys.foreign_keys fk
                    JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
                    JOIN sys.objects po ON po.object_id=fk.parent_object_id
                    JOIN sys.schemas ps ON ps.schema_id=po.schema_id
                    JOIN sys.columns pc ON pc.object_id=po.object_id AND pc.column_id=fkc.parent_column_id
                    JOIN sys.objects ro ON ro.object_id=fk.referenced_object_id
                    JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
                    JOIN sys.columns rc ON rc.object_id=ro.object_id AND rc.column_id=fkc.referenced_column_id
                    WHERE po.object_id IN ({id_marks}) OR ro.object_id IN ({id_marks})
                    ORDER BY fk.name,fkc.constraint_column_id
                    """,
                    object_ids + object_ids + object_ids + object_ids,
                )
                trigger_rows = _rows(
                    cursor,
                    f"""
                    SELECT tr.parent_id AS object_id,tr.name AS trigger_name,tr.is_disabled,
                           OBJECTPROPERTY(tr.object_id,'ExecIsInsertTrigger') AS is_insert_trigger,
                           OBJECTPROPERTY(tr.object_id,'ExecIsUpdateTrigger') AS is_update_trigger,
                           OBJECTPROPERTY(tr.object_id,'ExecIsDeleteTrigger') AS is_delete_trigger,
                           m.definition
                    FROM sys.triggers tr
                    LEFT JOIN sys.sql_modules m ON m.object_id=tr.object_id
                    WHERE tr.parent_id IN ({id_marks})
                    ORDER BY tr.parent_id,tr.name
                    """,
                    object_ids,
                )
            else:
                column_rows, key_rows, fk_rows, trigger_rows = [], [], [], []

    table_name_by_id = {int(row["object_id"]): f"{row['schema_name']}.{row['table_name']}" for row in table_rows}
    columns_by_id: dict[int, list[dict[str, Any]]] = {object_id: [] for object_id in object_ids}
    for row in column_rows:
        columns_by_id[int(row["object_id"])].append(
            {
                "ordinal": int(row["column_id"]),
                "name": row["column_name"],
                "data_type": row["data_type"],
                "max_length": int(row["max_length"]),
                "precision": int(row["precision"]),
                "scale": int(row["scale"]),
                "nullable": bool(row["is_nullable"]),
                "identity": bool(row["is_identity"]),
                "computed": bool(row["is_computed"]),
            }
        )

    keys_by_id: dict[int, dict[str, dict[str, Any]]] = {object_id: {} for object_id in object_ids}
    for row in key_rows:
        bucket = keys_by_id[int(row["object_id"])]
        key = bucket.setdefault(
            row["index_name"],
            {"name": row["index_name"], "primary_key": bool(row["is_primary_key"]), "unique": bool(row["is_unique"]), "columns": []},
        )
        key["columns"].append(row["column_name"])

    triggers_by_id: dict[int, list[dict[str, Any]]] = {object_id: [] for object_id in object_ids}
    for row in trigger_rows:
        definition = row.pop("definition") or ""
        triggers_by_id[int(row["object_id"])].append(
            {
                "name": row["trigger_name"],
                "disabled": bool(row["is_disabled"]),
                "events": [
                    event
                    for event, flag in (("INSERT", row["is_insert_trigger"]), ("UPDATE", row["is_update_trigger"]), ("DELETE", row["is_delete_trigger"]))
                    if flag
                ],
                "definition_present": bool(definition),
                "definition_persisted": False,
            }
        )

    tables = []
    for row in sorted(table_rows, key=lambda value: value["table_name"].casefold()):
        object_id = int(row["object_id"])
        table_columns = columns_by_id[object_id]
        names = {column["name"].casefold() for column in table_columns}
        tables.append(
            {
                "object": table_name_by_id[object_id],
                "row_count_snapshot": int(row["row_count"] or 0),
                "column_count": len(table_columns),
                "columns": table_columns,
                "keys": list(keys_by_id[object_id].values()),
                "triggers": triggers_by_id[object_id],
                "candidate_role_signals": {
                    "session_key": any(name in names for name in ("psessionid", "sessionid")),
                    "order_key": any(name in names for name in ("porderid", "orderid")),
                    "receipt_or_payment_key": any("receipt" in name or "payment" in name for name in names),
                    "source_version_signal": any(name in names for name in ("rowversion", "timestamp", "version")),
                    "business_date_signal": any("date" in name for name in names),
                    "amount_signal": any("amount" in name or "price" in name for name in names),
                },
            }
        )

    foreign_keys = [
        {
            "name": row["foreign_key_name"],
            "from": f"{row['parent_schema']}.{row['parent_table']}.{row['parent_column']}",
            "to": f"{row['referenced_schema']}.{row['referenced_table']}.{row['referenced_column']}",
            "ordinal": int(row["constraint_column_id"]),
            "from_in_scope": bool(row["parent_in_scope"]),
            "to_in_scope": bool(row["referenced_in_scope"]),
            "disabled": bool(row["is_disabled"]),
            "not_trusted": bool(row["is_not_trusted"]),
        }
        for row in fk_rows
    ]
    found = {row["object"].split(".", 1)[1].casefold() for row in tables}
    missing = sorted(name for name in TABLES if name.casefold() not in found)
    all_columns = [column for table in tables for column in table["columns"]]
    summary = {
        "requested_table_count": len(TABLES),
        "found_table_count": len(tables),
        "missing_table_count": len(missing),
        "row_count_snapshot_total": sum(table["row_count_snapshot"] for table in tables),
        "column_count": len(all_columns),
        "primary_or_unique_key_count": sum(len(table["keys"]) for table in tables),
        "foreign_key_column_edge_count": len(foreign_keys),
        "foreign_key_constraint_count": len({row["name"] for row in foreign_keys}),
        "foreign_key_not_trusted_count": len({row["name"] for row in foreign_keys if row["not_trusted"]}),
        "in_scope_foreign_key_constraint_count": len({row["name"] for row in foreign_keys if row["from_in_scope"] and row["to_in_scope"]}),
        "in_scope_foreign_key_not_trusted_count": len({row["name"] for row in foreign_keys if row["from_in_scope"] and row["to_in_scope"] and row["not_trusted"]}),
        "trigger_count": sum(len(table["triggers"]) for table in tables),
        "disabled_trigger_count": sum(trigger["disabled"] for table in tables for trigger in table["triggers"]),
        "data_type_counts": dict(sorted(Counter(column["data_type"] for column in all_columns).items())),
        "table_with_source_version_signal_count": sum(table["candidate_role_signals"]["source_version_signal"] for table in tables),
        "definition_persisted_count": 0,
        "business_row_value_persisted_count": 0,
        "validation_error_count": 0 if not missing else 1,
    }
    artifact = {
        "artifact": "varanegar_pos_receipt_replication_clone_source_catalog_model",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not missing else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "root_parameter": "@PSessionId", "requested_tables": list(TABLES)},
        "safety": {
            "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_AND_AGGREGATE_ROW_COUNTS",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": context["denies_data_writes"],
            "business_row_values_read_or_persisted": 0,
            "module_or_trigger_definitions_persisted": 0,
            "procedures_or_triggers_executed": 0,
            "application_or_live_ui_actions": 0,
        },
        "summary": summary,
        "tables": tables,
        "foreign_keys": foreign_keys,
        "missing_tables": missing,
        "migration_implications": [
            "PSessionId is a legacy lookup key, not a sufficient target idempotency key.",
            "A source snapshot must preserve session, order, return, payment and credit provenance before target commands run.",
            "Row counts are clone snapshot aggregates and do not establish operational completeness or freshness.",
            "Missing rowversion/version signals require payload hashing plus extraction-watermark and source snapshot identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if artifact["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
