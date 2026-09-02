"""Extract catalog-only source model for three treasury edit command paths."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows


TARGETS = (
    ("dbo", "RCash"),
    ("dbo", "RCashDetail"),
    ("dbo", "Receipt"),
    ("dbo", "RCheque"),
    ("dbo", "tblRChequeLog"),
    ("Acc", "TblCheque"),
    ("dbo", "RCashDraft"),
    ("Acc", "TblBankOrders"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    objects: list[dict[str, Any]] = []
    with _connect() as connection:
        with connection.cursor() as cursor:
            context = _assert_safe_target(cursor)
            for schema, name in TARGETS:
                found = _rows(
                    cursor,
                    """
                    SELECT o.object_id,s.name AS schema_name,o.name,o.type,o.type_desc,
                           o.create_date,o.modify_date,
                           COALESCE(p.approximate_row_count,0) AS approximate_row_count
                    FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
                    LEFT JOIN (
                        SELECT object_id,SUM(row_count) AS approximate_row_count
                        FROM sys.dm_db_partition_stats WHERE index_id IN (0,1)
                        GROUP BY object_id
                    ) p ON p.object_id=o.object_id
                    WHERE s.name=%s AND o.name=%s AND o.is_ms_shipped=0
                    """,
                    (schema, name),
                )
                if not found:
                    errors.append(f"missing object: {schema}.{name}")
                    continue
                base = found[0]
                object_id = int(base["object_id"])
                columns = _rows(
                    cursor,
                    """
                    SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS data_type,
                           c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,c.is_computed,
                           CASE WHEN pk.column_id IS NULL THEN 0 ELSE 1 END AS is_primary_key
                    FROM sys.columns c
                    LEFT JOIN (
                        SELECT ic.object_id,ic.column_id FROM sys.indexes i
                        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
                        WHERE i.is_primary_key=1
                    ) pk ON pk.object_id=c.object_id AND pk.column_id=c.column_id
                    WHERE c.object_id=%s ORDER BY c.column_id
                    """,
                    (object_id,),
                )
                fks = _rows(
                    cursor,
                    """
                    SELECT fk.name AS fk_name,
                           ss.name+'.'+so.name AS source_object,sc.name AS source_column,
                           ts.name+'.'+to1.name AS target_object,tc.name AS target_column,
                           fk.delete_referential_action_desc,fk.update_referential_action_desc,
                           fk.is_disabled,fk.is_not_trusted
                    FROM sys.foreign_key_columns fkc
                    JOIN sys.foreign_keys fk ON fk.object_id=fkc.constraint_object_id
                    JOIN sys.objects so ON so.object_id=fkc.parent_object_id
                    JOIN sys.schemas ss ON ss.schema_id=so.schema_id
                    JOIN sys.columns sc ON sc.object_id=so.object_id AND sc.column_id=fkc.parent_column_id
                    JOIN sys.objects to1 ON to1.object_id=fkc.referenced_object_id
                    JOIN sys.schemas ts ON ts.schema_id=to1.schema_id
                    JOIN sys.columns tc ON tc.object_id=to1.object_id AND tc.column_id=fkc.referenced_column_id
                    WHERE fkc.parent_object_id=%s OR fkc.referenced_object_id=%s
                    ORDER BY fk.name,fkc.constraint_column_id
                    """,
                    (object_id, object_id),
                )
                triggers = _rows(
                    cursor,
                    """
                    SELECT tr.name,tr.is_disabled,tr.is_instead_of_trigger,
                           OBJECTPROPERTYEX(tr.object_id,'ExecIsInsertTrigger') AS is_insert,
                           OBJECTPROPERTYEX(tr.object_id,'ExecIsUpdateTrigger') AS is_update,
                           OBJECTPROPERTYEX(tr.object_id,'ExecIsDeleteTrigger') AS is_delete
                    FROM sys.triggers tr WHERE tr.parent_id=%s ORDER BY tr.name
                    """,
                    (object_id,),
                )
                referenced_by = _rows(
                    cursor,
                    """
                    SELECT DISTINCT rs.name+'.'+ro.name AS referencing_object,ro.type_desc
                    FROM sys.sql_expression_dependencies d
                    JOIN sys.objects ro ON ro.object_id=d.referencing_id
                    JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
                    WHERE d.referenced_id=%s
                    ORDER BY referencing_object
                    """,
                    (object_id,),
                )
                objects.append({
                    "object": f"{base['schema_name']}.{base['name']}",
                    "object_type": str(base["type"]).strip(),
                    "object_type_desc": base["type_desc"],
                    "create_date": base["create_date"],
                    "modify_date": base["modify_date"],
                    "approximate_row_count": int(base["approximate_row_count"]),
                    "columns": [{
                        "ordinal": int(row["column_id"]),
                        "name": row["name"],
                        "data_type": row["data_type"],
                        "max_length": int(row["max_length"]),
                        "precision": int(row["precision"]),
                        "scale": int(row["scale"]),
                        "is_nullable": bool(row["is_nullable"]),
                        "is_identity": bool(row["is_identity"]),
                        "is_computed": bool(row["is_computed"]),
                        "is_primary_key": bool(row["is_primary_key"]),
                    } for row in columns],
                    "foreign_key_edges": [{
                        "fk_name": row["fk_name"],
                        "source_object": row["source_object"],
                        "source_column": row["source_column"],
                        "target_object": row["target_object"],
                        "target_column": row["target_column"],
                        "delete_action": row["delete_referential_action_desc"],
                        "update_action": row["update_referential_action_desc"],
                        "is_disabled": bool(row["is_disabled"]),
                        "is_not_trusted": bool(row["is_not_trusted"]),
                    } for row in fks],
                    "triggers": [{
                        "name": row["name"],
                        "is_disabled": bool(row["is_disabled"]),
                        "is_instead_of": bool(row["is_instead_of_trigger"]),
                        "events": [event for event, key in (("INSERT", "is_insert"), ("UPDATE", "is_update"), ("DELETE", "is_delete")) if row[key]],
                    } for row in triggers],
                    "referencing_modules": referenced_by,
                })

    summary = {
        "target_object_count": len(TARGETS),
        "resolved_object_count": len(objects),
        "table_count": sum(row["object_type"] == "U" for row in objects),
        "column_count": sum(len(row["columns"]) for row in objects),
        "primary_key_column_count": sum(sum(col["is_primary_key"] for col in row["columns"]) for row in objects),
        "foreign_key_edge_observation_count": sum(len(row["foreign_key_edges"]) for row in objects),
        "trigger_count": sum(len(row["triggers"]) for row in objects),
        "enabled_trigger_count": sum(sum(not tr["is_disabled"] for tr in row["triggers"]) for row in objects),
        "referencing_module_observation_count": sum(len(row["referencing_modules"]) for row in objects),
        "business_row_values_or_module_definitions_persisted_count": 0,
        "application_or_sql_module_execution_count": 0,
        "validation_error_count": len(errors),
    }
    artifact = {
        "artifact": "varanegar_treasury_edit_clone_catalog_source_model",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "validation": "PASS" if not errors else "FAIL",
        "scope": {"server": SERVER, "database": DATABASE, "snapshot_kind": "READ_ONLY_CLONE"},
        "safety": {
            "mode": "READ_ONLY_CLONE_SYSTEM_CATALOG_AND_AGGREGATE_PARTITION_COUNT_ONLY",
            "database_updateability": context["updateability"],
            "can_update": context["can_update"],
            "denies_data_writes": bool(context["denies_data_writes"]),
            "business_row_values_module_definitions_or_literals_read_or_persisted": 0,
            "procedures_functions_views_triggers_or_application_commands_executed": 0,
            "live_ui_actions": 0,
        },
        "summary": summary,
        "objects": objects,
        "validation_errors": errors,
        "limits": [
            "Partition row counts are approximate clone metadata, not a live operational reconciliation.",
            "Catalog FK and trigger presence does not prove runtime branch execution or business semantics.",
            "Module definitions and business row values were intentionally not read or persisted.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    print(args.output.resolve())
    print(json.dumps({"validation": artifact["validation"], **summary}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
