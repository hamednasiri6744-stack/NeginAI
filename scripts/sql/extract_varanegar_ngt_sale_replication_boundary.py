"""Extract NGT order-to-sale replication and Type=8 crosswalk evidence safely."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_ngt_return_replication_boundary import (
    _definition,
    _index_contract,
    _profile,
)
from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


PROCEDURES = (
    "dbo.NGT_DoReplicateTour",
    "dbo.NGT_ReplicateTour",
    "dbo.NGT_CreateOrderAndSale",
    "dbo.NGT_CreateSale_ForDistInfo",
)


def _sale_indexes(cursor: Any) -> list[dict[str, Any]]:
    rows = _index_contract(cursor)
    rows.extend(
        _rows(
            cursor,
            """
            SELECT s.name schema_name,t.name table_name,i.name index_name,i.is_unique,
                   i.is_primary_key,i.is_disabled,i.has_filter,i.filter_definition,
                   ic.key_ordinal,ic.is_included_column,c.name column_name
            FROM sys.indexes i
            JOIN sys.tables t ON t.object_id=i.object_id
            JOIN sys.schemas s ON s.schema_id=t.schema_id
            JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
            JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
            WHERE s.name='NGT' AND t.name='CustomerCallOrders'
            ORDER BY i.index_id,ic.key_ordinal,ic.index_column_id
            """,
        )
    )
    return rows


def _history_crosswalk(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH h AS (
          SELECT EntityUniqueId,COUNT_BIG(*) history_count,
                 COUNT(DISTINCT BackOfficeUniqueId) distinct_target_uuid_count,
                 COUNT(DISTINCT BackOfficeRef) distinct_target_ref_count,
                 COUNT(DISTINCT BackOfficeNo) distinct_target_no_count,
                 COUNT(DISTINCT Date) distinct_timestamp_count,
                 MIN(BackOfficeUniqueId) target_uuid,MIN(BackOfficeRef) target_ref
          FROM dbo.TourHistory WHERE Type=8 GROUP BY EntityUniqueId
        )
        SELECT COUNT_BIG(*) entity_count,SUM(history_count) history_count,
          SUM(CASE WHEN history_count>1 THEN 1 ELSE 0 END) multi_history_entity_count,
          SUM(CASE WHEN history_count>1 THEN history_count ELSE 0 END) history_in_multi_group_count,
          MAX(history_count) max_history_per_entity,
          SUM(CASE WHEN distinct_target_uuid_count>1 OR distinct_target_ref_count>1
                   THEN 1 ELSE 0 END) multi_target_entity_count,
          SUM(CASE WHEN history_count>1 AND distinct_target_uuid_count=1
                    AND distinct_target_ref_count=1 AND distinct_target_no_count=1
                   THEN 1 ELSE 0 END) duplicate_same_target_entity_count,
          SUM(CASE WHEN history_count>1 AND distinct_timestamp_count=1
                   THEN 1 ELSE 0 END) duplicate_same_timestamp_entity_count,
          SUM(CASE WHEN o.Id IS NULL THEN 1 ELSE 0 END) missing_ngt_order_count,
          SUM(CASE WHEN o.BackOfficeInvoiceUniqueId IS NULL THEN 1 ELSE 0 END)
            missing_header_invoice_uuid_count,
          SUM(CASE WHEN o.BackOfficeInvoiceUniqueId<>h.target_uuid THEN 1 ELSE 0 END)
            header_invoice_uuid_mismatch_count,
          SUM(CASE WHEN TRY_CONVERT(bigint,o.BackOfficeInvoiceId)<>h.target_ref THEN 1 ELSE 0 END)
            header_invoice_ref_mismatch_count,
          SUM(CASE WHEN s.ID IS NULL THEN 1 ELSE 0 END) missing_current_sale_target_count
        FROM h
        LEFT JOIN NGT.CustomerCallOrders o ON o.Id=h.EntityUniqueId
        LEFT JOIN SLE.tblSaleHdr s ON s.UniqueId=h.target_uuid AND s.ID=h.target_ref
        """,
    )[0]


def _shape(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        WITH g AS (
          SELECT EntityUniqueId,COUNT_BIG(*) histories_per_entity,
                 COUNT(DISTINCT BackOfficeUniqueId) distinct_target_uuid_count,
                 COUNT(DISTINCT BackOfficeRef) distinct_target_ref_count,
                 COUNT(DISTINCT Date) distinct_timestamp_count
          FROM dbo.TourHistory WHERE Type=8 GROUP BY EntityUniqueId
        )
        SELECT histories_per_entity,distinct_target_uuid_count,
               distinct_target_ref_count,distinct_timestamp_count,
               COUNT_BIG(*) entity_count
        FROM g
        GROUP BY histories_per_entity,distinct_target_uuid_count,
                 distinct_target_ref_count,distinct_timestamp_count
        ORDER BY histories_per_entity,distinct_target_uuid_count,
                 distinct_target_ref_count,distinct_timestamp_count
        """,
    )


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        definitions = {name: _definition(cursor, name) for name in PROCEDURES}
        profiles = [_profile(name, definitions[name]) for name in PROCEDURES]
        indexes = _sale_indexes(cursor)
        crosswalk = _history_crosswalk(cursor)
        shape = _shape(cursor)
    finally:
        connection.close()
    history_unique = any(
        row["schema_name"] == "dbo"
        and row["table_name"] == "TourHistory"
        and row["is_unique"]
        and not row["is_disabled"]
        and not row["has_filter"]
        and row["key_ordinal"] == 1
        and row["column_name"] == "EntityUniqueId"
        for row in indexes
    )
    invoice_crosswalk_unique = any(
        row["schema_name"] == "NGT"
        and row["table_name"] == "CustomerCallOrders"
        and row["is_unique"]
        and not row["is_disabled"]
        and row["column_name"] in {"BackOfficeInvoiceUniqueId", "BackOfficeInvoiceId"}
        for row in indexes
    )
    contract = {
        "history_type": 8,
        "history_count": int(crosswalk["history_count"] or 0),
        "entity_count": int(crosswalk["entity_count"] or 0),
        "multi_history_entity_count": int(crosswalk["multi_history_entity_count"] or 0),
        "history_in_multi_group_count": int(crosswalk["history_in_multi_group_count"] or 0),
        "max_history_per_entity": int(crosswalk["max_history_per_entity"] or 0),
        "multi_target_entity_count": int(crosswalk["multi_target_entity_count"] or 0),
        "duplicate_same_target_entity_count": int(
            crosswalk["duplicate_same_target_entity_count"] or 0
        ),
        "duplicate_same_timestamp_entity_count": int(
            crosswalk["duplicate_same_timestamp_entity_count"] or 0
        ),
        "missing_ngt_order_count": int(crosswalk["missing_ngt_order_count"] or 0),
        "header_invoice_uuid_mismatch_count": int(
            crosswalk["header_invoice_uuid_mismatch_count"] or 0
        ),
        "header_invoice_ref_mismatch_count": int(
            crosswalk["header_invoice_ref_mismatch_count"] or 0
        ),
        "missing_current_sale_target_count": int(
            crosswalk["missing_current_sale_target_count"] or 0
        ),
        "type_8_history_unique_guard_present": history_unique,
        "order_invoice_crosswalk_unique_guard_present": invoice_crosswalk_unique,
    }
    return {
        "artifact": "varanegar_ngt_sale_replication_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": safety["updateability"],
            "can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "business_rows_or_identifiers_persisted": 0,
            "sql_definitions_persisted": 0,
            "guid_literals_persisted": 0,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "procedure_count": len(profiles),
            "type_8_history_count": contract["history_count"],
            "type_8_entity_count": contract["entity_count"],
            "multi_history_entity_count": contract["multi_history_entity_count"],
            "duplicate_same_target_entity_count": contract[
                "duplicate_same_target_entity_count"
            ],
            "multi_target_entity_count": contract["multi_target_entity_count"],
            "missing_current_sale_target_count": contract[
                "missing_current_sale_target_count"
            ],
        },
        "sale_replication_contract": contract,
        "history_shape": shape,
        "index_contract": indexes,
        "procedure_profiles": profiles,
        "evidence_limits": [
            "Duplicate same-target same-timestamp history proves duplicate ledger rows, not duplicate Sale effects.",
            "Current target consistency cannot establish which SQL branch inserted each duplicate history row.",
            "No procedure or endpoint was executed and no raw identifier, amount or SQL definition was persisted.",
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
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
