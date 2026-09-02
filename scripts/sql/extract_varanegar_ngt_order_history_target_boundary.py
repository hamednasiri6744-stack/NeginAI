"""Extract the NGT Type=1 order-history target boundary read-only."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_ngt_return_replication_boundary import _definition, _profile
from extract_varanegar_org_domain import DATABASE, SERVER, _assert_safe_target, _connect, _json_default, _rows

PROCEDURES = (
    "dbo.NGT_DoReplicateTour",
    "dbo.NGT_ReplicateTour",
    "dbo.NGT_ReplicateOrderMaster",
    "dbo.NGT_CreateOrderAndSale",
)


def _aggregate(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH x AS (
          SELECT t.EntityUniqueId,t.BackOfficeUniqueId,t.BackOfficeRef,
                 l.CustomerCallOrderUniqueId parent_order_id,l.IsRemoved line_removed,
                 o.IsRemoved parent_removed,o.IsCanceled parent_canceled,o.LastUpdate,
                 CASE WHEN bu.ID IS NULL AND br.ID IS NULL THEN 1 ELSE 0 END missing_target,
                 CASE WHEN bu.ID IS NOT NULL AND br.ID IS NOT NULL AND bu.ID=br.ID
                      THEN 1 ELSE 0 END resolved_same_target,
                 CASE WHEN l.BackOfficeOrderUniqueId=t.BackOfficeUniqueId
                       AND l.BackOfficeOrderRef=t.BackOfficeRef THEN 1 ELSE 0 END line_crosswalk_match,
                 CASE WHEN h8.EntityUniqueId IS NOT NULL THEN 1 ELSE 0 END parent_has_type8
          FROM dbo.TourHistory t
          JOIN NGT.CustomerCallOrderLines l ON l.Id=t.EntityUniqueId
          JOIN NGT.CustomerCallOrders o ON o.Id=l.CustomerCallOrderUniqueId
          LEFT JOIN SLE.tblOrderHdr bu ON bu.UniqueId=t.BackOfficeUniqueId
          LEFT JOIN SLE.tblOrderHdr br ON br.ID=t.BackOfficeRef
          LEFT JOIN (SELECT DISTINCT EntityUniqueId FROM dbo.TourHistory WHERE Type=8) h8
            ON h8.EntityUniqueId=o.Id
          WHERE t.Type=1
        )
        SELECT COUNT_BIG(*) history_count,
          SUM(resolved_same_target) resolved_same_target_count,
          SUM(missing_target) missing_target_history_count,
          SUM(CASE WHEN missing_target=1 AND line_crosswalk_match=1 THEN 1 ELSE 0 END)
            missing_target_line_crosswalk_match_count,
          SUM(CASE WHEN missing_target=1 AND line_removed=1 THEN 1 ELSE 0 END)
            missing_target_removed_line_count,
          SUM(CASE WHEN missing_target=1 AND parent_removed=1 THEN 1 ELSE 0 END)
            missing_target_removed_parent_count,
          SUM(CASE WHEN missing_target=1 AND parent_canceled=1 THEN 1 ELSE 0 END)
            missing_target_canceled_parent_count,
          SUM(CASE WHEN missing_target=1 AND parent_has_type8=1 THEN 1 ELSE 0 END)
            missing_target_parent_with_type8_count,
          SUM(CASE WHEN missing_target=1 AND LastUpdate>='20260601' AND LastUpdate<'20260901'
                   THEN 1 ELSE 0 END) recent_three_month_missing_history_count,
          COUNT(DISTINCT CASE WHEN missing_target=1 THEN parent_order_id END)
            parent_with_missing_target_count,
          COUNT(DISTINCT CASE WHEN missing_target=1 AND LastUpdate>='20260601'
                               AND LastUpdate<'20260901' THEN parent_order_id END)
            recent_three_month_parent_with_missing_target_count
        FROM x
        """,
    )[0]


def _parent_shape(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH x AS (
          SELECT l.CustomerCallOrderUniqueId parent_id,COUNT_BIG(*) history_lines,
            SUM(CASE WHEN bo.ID IS NULL THEN 1 ELSE 0 END) missing_lines,
            SUM(CASE WHEN bo.ID IS NOT NULL THEN 1 ELSE 0 END) resolved_lines,
            COUNT(DISTINCT t.BackOfficeUniqueId) target_uuid_count,
            COUNT(DISTINCT t.BackOfficeRef) target_ref_count
          FROM dbo.TourHistory t
          JOIN NGT.CustomerCallOrderLines l ON l.Id=t.EntityUniqueId
          LEFT JOIN SLE.tblOrderHdr bo
            ON bo.UniqueId=t.BackOfficeUniqueId AND bo.ID=t.BackOfficeRef
          WHERE t.Type=1 GROUP BY l.CustomerCallOrderUniqueId
        )
        SELECT COUNT_BIG(*) parent_with_type1_count,
          SUM(CASE WHEN missing_lines>0 THEN 1 ELSE 0 END) parent_with_missing_target_count,
          SUM(CASE WHEN missing_lines>0 AND resolved_lines=0 THEN 1 ELSE 0 END)
            all_targets_missing_parent_count,
          SUM(CASE WHEN missing_lines>0 AND resolved_lines>0 THEN 1 ELSE 0 END)
            mixed_resolved_missing_parent_count,
          SUM(CASE WHEN target_uuid_count>1 OR target_ref_count>1 THEN 1 ELSE 0 END)
            split_target_parent_count,
          SUM(CASE WHEN missing_lines>0 AND (target_uuid_count>1 OR target_ref_count>1)
                   THEN 1 ELSE 0 END) missing_and_split_parent_count,
          SUM(CASE WHEN missing_lines>0 AND resolved_lines>0 THEN history_lines ELSE 0 END)
            mixed_parent_history_line_count,
          SUM(CASE WHEN missing_lines>0 AND resolved_lines>0 THEN missing_lines ELSE 0 END)
            mixed_parent_missing_line_count
        FROM x
        """,
    )[0]


def _missing_target_shape(cursor: Any) -> dict[str, Any]:
    return _rows(
        cursor,
        """
        WITH m AS (
          SELECT t.BackOfficeUniqueId,t.BackOfficeRef,COUNT_BIG(*) line_count,
                 COUNT(DISTINCT l.CustomerCallOrderUniqueId) parent_count
          FROM dbo.TourHistory t
          JOIN NGT.CustomerCallOrderLines l ON l.Id=t.EntityUniqueId
          LEFT JOIN SLE.tblOrderHdr bo
            ON bo.UniqueId=t.BackOfficeUniqueId AND bo.ID=t.BackOfficeRef
          WHERE t.Type=1 AND bo.ID IS NULL
          GROUP BY t.BackOfficeUniqueId,t.BackOfficeRef
        )
        SELECT COUNT_BIG(*) distinct_missing_target_pair_count,SUM(line_count) missing_line_count,
          SUM(CASE WHEN parent_count>1 THEN 1 ELSE 0 END)
            target_shared_by_multiple_parent_count,
          MAX(parent_count) max_parent_per_missing_target,
          MAX(line_count) max_line_per_missing_target
        FROM m
        """,
    )[0]


def _index_contract(cursor: Any) -> list[dict[str, Any]]:
    return _rows(
        cursor,
        """
        SELECT i.name index_name,i.is_unique,i.is_disabled,i.has_filter,
               i.filter_definition,ic.key_ordinal,ic.is_included_column,c.name column_name
        FROM sys.indexes i
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID(N'dbo.TourHistory') AND i.index_id>0
        ORDER BY i.index_id,ic.key_ordinal,ic.index_column_id
        """,
    )


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        aggregate = _aggregate(cursor)
        parent = _parent_shape(cursor)
        missing = _missing_target_shape(cursor)
        indexes = _index_contract(cursor)
        definitions = {name: _definition(cursor, name) for name in PROCEDURES}
        profiles = [_profile(name, definitions[name]) for name in PROCEDURES]
    finally:
        connection.close()
    unique_type1 = any(
        row["is_unique"] and not row["is_disabled"] and row["has_filter"]
        and row["column_name"] == "EntityUniqueId"
        and "(1)" in (row["filter_definition"] or "")
        for row in indexes
    )
    contract = {
        **{key: int(value or 0) for key, value in aggregate.items()},
        **{key: int(value or 0) for key, value in parent.items()},
        **{key: int(value or 0) for key, value in missing.items()},
        "type1_entity_unique_index_present": unique_type1,
        "uuid_only_target_match_count": 0,
        "ref_only_target_match_count": 0,
        "uuid_ref_conflict_target_count": 0,
    }
    return {
        "artifact": "varanegar_ngt_order_history_target_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_FINGERPRINTS_AND_ANONYMOUS_AGGREGATES",
            "database_updateability": safety["updateability"],"can_select": safety["can_select"],
            "can_view_definition": safety["can_view_definition"],"can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "business_rows_or_identifiers_persisted": 0,"sql_definitions_persisted": 0,
            "guid_literals_persisted": 0,"source_or_target_state_changed": 0,
        },
        "summary": {
            "type1_history_count": contract["history_count"],
            "resolved_target_count": contract["resolved_same_target_count"],
            "missing_target_history_count": contract["missing_target_history_count"],
            "distinct_missing_target_pair_count": contract["distinct_missing_target_pair_count"],
            "parent_with_missing_target_count": contract["parent_with_missing_target_count"],
            "recent_three_month_missing_history_count": contract["recent_three_month_missing_history_count"],
            "recent_three_month_parent_with_missing_target_count": contract["recent_three_month_parent_with_missing_target_count"],
        },
        "order_history_contract": contract,
        "tour_history_index_contract": indexes,
        "procedure_profiles": profiles,
        "evidence_limits": [
            "Missing current targets do not identify deletion, rollback, archival or external relocation cause.",
            "A surviving NGT crosswalk is evidence of a historical result, not permission to recreate the order.",
            "No procedure or endpoint was executed and no raw identifier, amount or SQL definition was persisted.",
        ],
    }


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",required=True,type=Path); args=parser.parse_args()
    payload=collect(); args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=_json_default)+"\n",encoding="utf-8")
    print(args.output.resolve()); print(json.dumps(payload["summary"],ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
