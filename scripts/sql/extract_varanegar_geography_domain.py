"""Extract Varanegar geography and route-master evidence from the local clone.

This second information-base slice distinguishes geographic masters from the
separate sales, distribution, collection, telephone-sales, FRU, and NGT route
models.  It reuses the safety gate from the organization-domain extractor and
never connects to the live operational database.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    _assert_safe_target,
    _connect,
    _decode_fields,
    _json_default,
    _rows,
    _table_metadata,
)


DOMAIN_TABLES: tuple[dict[str, str], ...] = (
    {"object": "GNR.tblState", "role": "state_master"},
    {"object": "GNR.tblCounty", "role": "county_master"},
    {"object": "GNR.tblArea", "role": "city_or_area_master"},
    {"object": "GNR.tblDCDependency", "role": "center_area_bridge"},
    {"object": "GNR.tblSaleZone", "role": "sales_zone"},
    {"object": "GNR.tblSaleArea", "role": "sales_area"},
    {"object": "GNR.tblSalePath", "role": "sales_path"},
    {"object": "GNR.tblDistZone", "role": "distribution_zone"},
    {"object": "GNR.tblDistArea", "role": "distribution_area"},
    {"object": "GNR.tblDistPath", "role": "distribution_path"},
    {"object": "GNR.tblRcptZone", "role": "collection_zone"},
    {"object": "GNR.tblRcptArea", "role": "collection_area"},
    {"object": "GNR.tblRcptPath", "role": "collection_path"},
    {"object": "GNR.tblTeleZone", "role": "telephone_sales_zone"},
    {"object": "GNR.tblTeleArea", "role": "telephone_sales_area"},
    {"object": "GNR.tblTelePath", "role": "telephone_sales_path"},
    {"object": "FRU.Path", "role": "fru_field_path"},
    {"object": "FRU.DayPath", "role": "fru_daily_path"},
    {"object": "NGT.VisitTemplates", "role": "ngt_visit_template"},
    {"object": "NGT.VisitTemplatePaths", "role": "ngt_visit_template_path"},
    {"object": "NGT.VisitTemplatePathCustomers", "role": "ngt_path_customer_bridge"},
    {"object": "NGT.DayPaths", "role": "ngt_daily_path"},
)


def _object_ids_sql() -> str:
    return ",".join(f"OBJECT_ID(N'{item['object']}', 'U')" for item in DOMAIN_TABLES)


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    object_ids = _object_ids_sql()
    return _rows(
        cursor,
        f"""
        SELECT fk.name AS constraint_name,
               OBJECT_SCHEMA_NAME(fk.parent_object_id) AS parent_schema,
               OBJECT_NAME(fk.parent_object_id) AS parent_table,
               pc.name AS parent_column,
               OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS referenced_schema,
               OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
               rc.name AS referenced_column,
               fk.delete_referential_action_desc AS on_delete,
               fk.update_referential_action_desc AS on_update,
               fk.is_disabled,fk.is_not_trusted
        FROM sys.foreign_keys AS fk
        JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.columns AS pc
          ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns AS rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE fk.parent_object_id IN ({object_ids})
           OR fk.referenced_object_id IN ({object_ids})
        ORDER BY referenced_schema,referenced_table,parent_schema,parent_table,
                 fk.name,fkc.constraint_column_id
        """,
    )


def _module_consumers(cursor: Any) -> list[dict[str, Any]]:
    object_ids = _object_ids_sql()
    return _rows(
        cursor,
        f"""
        SELECT DISTINCT
               OBJECT_SCHEMA_NAME(d.referencing_id) AS consumer_schema,
               OBJECT_NAME(d.referencing_id) AS consumer_name,
               o.type_desc AS consumer_type,
               OBJECT_SCHEMA_NAME(d.referenced_id) AS source_schema,
               OBJECT_NAME(d.referenced_id) AS source_table,
               d.is_schema_bound_reference,
               o.modify_date AS consumer_modify_date
        FROM sys.sql_expression_dependencies AS d
        JOIN sys.objects AS o ON o.object_id=d.referencing_id
        WHERE d.referenced_id IN ({object_ids})
        ORDER BY source_schema,source_table,consumer_schema,consumer_name
        """,
    )


def _implicit_link_candidates(cursor: Any) -> list[dict[str, Any]]:
    object_ids = _object_ids_sql()
    return _rows(
        cursor,
        f"""
        WITH candidates AS (
            SELECT c.object_id,c.column_id,s.name AS schema_name,t.name AS table_name,
                   c.name AS column_name,TYPE_NAME(c.user_type_id) AS data_type
            FROM sys.columns AS c
            JOIN sys.tables AS t ON t.object_id=c.object_id
            JOIN sys.schemas AS s ON s.schema_id=t.schema_id
            WHERE LOWER(c.name) LIKE '%state%'
               OR LOWER(c.name) LIKE '%county%'
               OR LOWER(c.name) LIKE '%area%'
               OR LOWER(c.name) LIKE '%zone%'
               OR LOWER(c.name) LIKE '%path%'
               OR LOWER(c.name) LIKE '%route%'
        )
        SELECT cc.schema_name,cc.table_name,cc.column_name,cc.data_type,
               CASE WHEN fkc.constraint_object_id IS NULL THEN 0 ELSE 1 END AS has_formal_fk,
               OBJECT_SCHEMA_NAME(fkc.referenced_object_id) AS formal_target_schema,
               OBJECT_NAME(fkc.referenced_object_id) AS formal_target_table,
               rc.name AS formal_target_column
        FROM candidates AS cc
        LEFT JOIN sys.foreign_key_columns AS fkc
          ON fkc.parent_object_id=cc.object_id AND fkc.parent_column_id=cc.column_id
        LEFT JOIN sys.columns AS rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE cc.object_id NOT IN ({object_ids})
        ORDER BY has_formal_fk,cc.schema_name,cc.table_name,cc.column_name
        """,
    )


def _geography_snapshot(cursor: Any) -> dict[str, Any]:
    states = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,StateCode,CONVERT(varbinary(max),StateName) AS StateName,
                   ModifiedDateBeforeSend,UniqueId,StateGuid
            FROM GNR.tblState ORDER BY ID
            """,
        ),
        ("StateName",),
    )
    counties = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,StateRef,CountyCode,
                   CONVERT(varbinary(max),CountyName) AS CountyName,
                   CountyCode2,UniqueId,CountyGuid
            FROM GNR.tblCounty ORDER BY StateRef,ID
            """,
        ),
        ("CountyName",),
    )
    areas = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,CountyRef,AreaCode,CONVERT(varbinary(max),AreaName) AS AreaName,
                   AreaCode2,ModifiedDateBeforeSend,UniqueId,AreaGuid
            FROM GNR.tblArea ORDER BY CountyRef,ID
            """,
        ),
        ("AreaName",),
    )
    hierarchy = _decode_fields(
        _rows(
            cursor,
            """
            SELECT s.ID AS StateId,s.StateCode,
                   CONVERT(varbinary(max),s.StateName) AS StateName,
                   c.ID AS CountyId,c.CountyCode,
                   CONVERT(varbinary(max),c.CountyName) AS CountyName,
                   a.ID AS AreaId,a.AreaCode,
                   CONVERT(varbinary(max),a.AreaName) AS AreaName
            FROM GNR.tblArea AS a
            JOIN GNR.tblCounty AS c ON c.ID=a.CountyRef
            JOIN GNR.tblState AS s ON s.ID=c.StateRef
            ORDER BY s.ID,c.ID,a.ID
            """,
        ),
        ("StateName", "CountyName", "AreaName"),
    )
    center_areas = _decode_fields(
        _rows(
            cursor,
            """
            SELECT d.ID AS DependencyId,d.DCRef,
                   CONVERT(varbinary(max),dc.DCName) AS DCName,
                   d.AreaRef,CONVERT(varbinary(max),a.AreaName) AS AreaName,
                   c.ID AS CountyId,CONVERT(varbinary(max),c.CountyName) AS CountyName,
                   s.ID AS StateId,CONVERT(varbinary(max),s.StateName) AS StateName,
                   d.Distance,d.Status
            FROM GNR.tblDCDependency AS d
            JOIN GNR.tblDC AS dc ON dc.ID=d.DCRef
            JOIN GNR.tblArea AS a ON a.ID=d.AreaRef
            JOIN GNR.tblCounty AS c ON c.ID=a.CountyRef
            JOIN GNR.tblState AS s ON s.ID=c.StateRef
            ORDER BY s.ID,c.ID,a.ID
            """,
        ),
        ("DCName", "AreaName", "CountyName", "StateName"),
    )
    return {
        "states": states,
        "counties": counties,
        "areas": areas,
        "area_hierarchy": hierarchy,
        "center_area_assignments": center_areas,
    }


def _legacy_route_snapshot(cursor: Any) -> dict[str, Any]:
    sales_routes = _decode_fields(
        _rows(
            cursor,
            """
            SELECT z.ID AS SaleZoneId,z.SaleZoneNo,
                   CONVERT(varbinary(max),z.SaleZoneName) AS SaleZoneName,
                   z.DCRef,z.AreaRef,z.SaleOfficeRef,
                   a.ID AS SaleAreaId,a.SaleAreaNo,
                   CONVERT(varbinary(max),a.SaleAreaName) AS SaleAreaName,a.DealerRef,
                   p.ID AS SalePathId,p.SalePathNo,
                   CONVERT(varbinary(max),p.SalePathName) AS SalePathName
            FROM GNR.tblSaleZone AS z
            LEFT JOIN GNR.tblSaleArea AS a ON a.SaleZoneRef=z.ID
            LEFT JOIN GNR.tblSalePath AS p ON p.SaleAreaRef=a.ID
            ORDER BY z.ID,a.ID,p.ID
            """,
        ),
        ("SaleZoneName", "SaleAreaName", "SalePathName"),
    )
    return {
        "sales_route_hierarchy": sales_routes,
        "route_family_counts": _rows(
            cursor,
            """
            SELECT 'sales' AS route_family,
                   (SELECT COUNT_BIG(*) FROM GNR.tblSaleZone) AS zone_count,
                   (SELECT COUNT_BIG(*) FROM GNR.tblSaleArea) AS area_count,
                   (SELECT COUNT_BIG(*) FROM GNR.tblSalePath) AS path_count
            UNION ALL SELECT 'distribution',
                   (SELECT COUNT_BIG(*) FROM GNR.tblDistZone),
                   (SELECT COUNT_BIG(*) FROM GNR.tblDistArea),
                   (SELECT COUNT_BIG(*) FROM GNR.tblDistPath)
            UNION ALL SELECT 'collection',
                   (SELECT COUNT_BIG(*) FROM GNR.tblRcptZone),
                   (SELECT COUNT_BIG(*) FROM GNR.tblRcptArea),
                   (SELECT COUNT_BIG(*) FROM GNR.tblRcptPath)
            UNION ALL SELECT 'telephone_sales',
                   (SELECT COUNT_BIG(*) FROM GNR.tblTeleZone),
                   (SELECT COUNT_BIG(*) FROM GNR.tblTeleArea),
                   (SELECT COUNT_BIG(*) FROM GNR.tblTelePath)
            """,
        ),
    }


def _customer_assignment_summary(cursor: Any) -> dict[str, Any]:
    summary = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS total_customers,
               SUM(CASE WHEN StateRef IS NOT NULL THEN 1 ELSE 0 END) AS state_assigned,
               SUM(CASE WHEN AreaRef IS NOT NULL THEN 1 ELSE 0 END) AS area_assigned,
               SUM(CASE WHEN SalePathRef IS NOT NULL THEN 1 ELSE 0 END) AS sale_path_assigned,
               SUM(CASE WHEN DistPathRef IS NOT NULL THEN 1 ELSE 0 END) AS dist_path_assigned,
               SUM(CASE WHEN RcptPathRef IS NOT NULL THEN 1 ELSE 0 END) AS collection_path_assigned,
               SUM(CASE WHEN TelePathRef IS NOT NULL THEN 1 ELSE 0 END) AS telephone_path_assigned,
               SUM(CASE WHEN CityZone IS NOT NULL THEN 1 ELSE 0 END) AS city_zone_populated,
               SUM(CASE WHEN CityArea IS NOT NULL THEN 1 ELSE 0 END) AS city_area_populated,
               COUNT(DISTINCT StateRef) AS distinct_state_refs,
               COUNT(DISTINCT AreaRef) AS distinct_area_refs,
               COUNT(DISTINCT SalePathRef) AS distinct_sale_path_refs,
               COUNT(DISTINCT CityZone) AS distinct_city_zone_values
        FROM GNR.tblCust
        """,
    )[0]
    city_zone_values = _rows(
        cursor,
        """
        SELECT TOP (50) CityZone,COUNT_BIG(*) AS customer_count
        FROM GNR.tblCust WHERE CityZone IS NOT NULL
        GROUP BY CityZone ORDER BY customer_count DESC,CityZone
        """,
    )
    return {"summary": summary, "city_zone_value_distribution": city_zone_values}


def _data_quality(cursor: Any) -> dict[str, Any]:
    referential = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM GNR.tblCounty c LEFT JOIN GNR.tblState s
             ON s.ID=c.StateRef WHERE s.ID IS NULL) AS orphan_counties,
          (SELECT COUNT_BIG(*) FROM GNR.tblArea a LEFT JOIN GNR.tblCounty c
             ON c.ID=a.CountyRef WHERE c.ID IS NULL) AS orphan_areas,
          (SELECT COUNT_BIG(*) FROM GNR.tblDCDependency d LEFT JOIN GNR.tblArea a
             ON a.ID=d.AreaRef WHERE a.ID IS NULL) AS orphan_center_areas,
          (SELECT COUNT_BIG(*) FROM GNR.tblSaleZone z LEFT JOIN GNR.tblDC d
             ON d.ID=z.DCRef WHERE d.ID IS NULL) AS orphan_sales_zone_centers,
          (SELECT COUNT_BIG(*) FROM GNR.tblSaleArea a LEFT JOIN GNR.tblSaleZone z
             ON z.ID=a.SaleZoneRef WHERE z.ID IS NULL) AS orphan_sales_areas,
          (SELECT COUNT_BIG(*) FROM GNR.tblSalePath p LEFT JOIN GNR.tblSaleArea a
             ON a.ID=p.SaleAreaRef WHERE a.ID IS NULL) AS orphan_sales_paths,
          (SELECT COUNT_BIG(*) FROM GNR.tblCust c LEFT JOIN GNR.tblState s
             ON s.ID=c.StateRef WHERE c.StateRef IS NOT NULL AND s.ID IS NULL) AS customer_orphan_states,
          (SELECT COUNT_BIG(*) FROM GNR.tblCust c LEFT JOIN GNR.tblArea a
             ON a.ID=c.AreaRef WHERE c.AreaRef IS NOT NULL AND a.ID IS NULL) AS customer_orphan_areas,
          (SELECT COUNT_BIG(*) FROM GNR.tblCust c LEFT JOIN GNR.tblSalePath p
             ON p.ID=c.SalePathRef WHERE c.SalePathRef IS NOT NULL AND p.ID IS NULL) AS customer_orphan_sales_paths
        """,
    )[0]
    duplicates = _rows(
        cursor,
        """
        SELECT 'state_code' AS check_name,COUNT_BIG(*) AS duplicate_groups FROM (
          SELECT StateCode FROM GNR.tblState GROUP BY StateCode HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'county_code_within_state',COUNT_BIG(*) FROM (
          SELECT StateRef,CountyCode FROM GNR.tblCounty GROUP BY StateRef,CountyCode HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'area_code_within_county',COUNT_BIG(*) FROM (
          SELECT CountyRef,AreaCode FROM GNR.tblArea GROUP BY CountyRef,AreaCode HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'sale_zone_no_within_center',COUNT_BIG(*) FROM (
          SELECT DCRef,SaleZoneNo FROM GNR.tblSaleZone GROUP BY DCRef,SaleZoneNo HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'sale_area_no_within_zone',COUNT_BIG(*) FROM (
          SELECT SaleZoneRef,SaleAreaNo FROM GNR.tblSaleArea GROUP BY SaleZoneRef,SaleAreaNo HAVING COUNT_BIG(*)>1
        ) d
        UNION ALL SELECT 'sale_path_no_within_area',COUNT_BIG(*) FROM (
          SELECT SaleAreaRef,SalePathNo FROM GNR.tblSalePath GROUP BY SaleAreaRef,SalePathNo HAVING COUNT_BIG(*)>1
        ) d
        """,
    )
    return {"referential_integrity": referential, "duplicate_key_groups": duplicates}


def _ngt_route_summary(cursor: Any) -> dict[str, Any]:
    counts = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM NGT.VisitTemplates) AS visit_templates_total,
          (SELECT COUNT_BIG(*) FROM NGT.VisitTemplates WHERE IsRemoved=0) AS visit_templates_active,
          (SELECT COUNT_BIG(*) FROM NGT.VisitTemplatePaths) AS paths_total,
          (SELECT COUNT_BIG(*) FROM NGT.VisitTemplatePaths WHERE IsRemoved=0) AS paths_active,
          (SELECT COUNT(DISTINCT Number_ID) FROM NGT.VisitTemplatePaths WHERE IsRemoved=0) AS active_distinct_number_ids,
          (SELECT COUNT_BIG(*) FROM NGT.VisitTemplatePathCustomers) AS customer_links_total,
          (SELECT COUNT_BIG(*) FROM NGT.VisitTemplatePathCustomers WHERE IsRemoved=0) AS customer_links_active,
          (SELECT COUNT(DISTINCT CustomerUniqueId) FROM NGT.VisitTemplatePathCustomers WHERE IsRemoved=0) AS active_distinct_customers,
          (SELECT COUNT_BIG(*) FROM NGT.DayPaths) AS day_paths_total,
          (SELECT COUNT_BIG(*) FROM NGT.DayPaths WHERE IsRemoved=0) AS day_paths_active,
          (SELECT COUNT_BIG(*) FROM FRU.Path) AS fru_paths_total,
          (SELECT COUNT_BIG(*) FROM FRU.DayPath) AS fru_day_paths_total
        """,
    )[0]
    recent_changes = _rows(
        cursor,
        """
        SELECT 'VisitTemplates' AS object_name,COUNT_BIG(*) AS changed_90d
          FROM NGT.VisitTemplates WHERE LastUpdate>=DATEADD(day,-90,SYSDATETIME())
        UNION ALL SELECT 'VisitTemplatePaths',COUNT_BIG(*)
          FROM NGT.VisitTemplatePaths WHERE LastUpdate>=DATEADD(day,-90,SYSDATETIME())
        UNION ALL SELECT 'VisitTemplatePathCustomers',COUNT_BIG(*)
          FROM NGT.VisitTemplatePathCustomers WHERE LastUpdate>=DATEADD(day,-90,SYSDATETIME())
        UNION ALL SELECT 'DayPaths',COUNT_BIG(*)
          FROM NGT.DayPaths WHERE LastUpdate>=DATEADD(day,-90,SYSDATETIME())
        """,
    )
    legacy_match = _rows(
        cursor,
        """
        SELECT COUNT_BIG(*) AS active_ngt_path_rows,
               COUNT(DISTINCT n.Number_ID) AS active_ngt_number_ids,
               SUM(CASE WHEN s.ID IS NOT NULL THEN 1 ELSE 0 END) AS rows_matching_legacy_sales_path,
               COUNT(DISTINCT CASE WHEN s.ID IS NOT NULL THEN n.Number_ID END) AS distinct_ids_matching_legacy_sales_path
        FROM NGT.VisitTemplatePaths AS n
        LEFT JOIN GNR.tblSalePath AS s ON s.ID=n.Number_ID
        WHERE n.IsRemoved=0
        """,
    )[0]
    unmatched_number_ids = _rows(
        cursor,
        """
        SELECT n.Number_ID,COUNT_BIG(*) AS active_path_rows
        FROM NGT.VisitTemplatePaths AS n
        LEFT JOIN GNR.tblSalePath AS s ON s.ID=n.Number_ID
        WHERE n.IsRemoved=0 AND s.ID IS NULL
        GROUP BY n.Number_ID ORDER BY n.Number_ID
        """,
    )
    return {
        "counts": counts,
        "master_data_changes_90d": recent_changes,
        "legacy_number_id_match": legacy_match,
        "unmatched_active_number_ids": unmatched_number_ids,
    }


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        tables = [
            _table_metadata(cursor, item["object"], item["role"])
            for item in DOMAIN_TABLES
        ]
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "geography_and_routes",
            "scope": {
                "server": "127.0.0.1",
                "database": "NeginPakhsh_WebDev",
                "mode": "read-only metadata, aggregates, and non-sensitive master labels",
            },
            "safety": safety,
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "geography_snapshot": _geography_snapshot(cursor),
            "legacy_routes": _legacy_route_snapshot(cursor),
            "customer_assignments": _customer_assignment_summary(cursor),
            "data_quality": _data_quality(cursor),
            "ngt_routes": _ngt_route_summary(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() AS captured_at")[0],
            "evidence_limits": [
                "Area is treated as a geographic master, but its exact UI label (city/area) still needs form evidence.",
                "CityZone and CityArea on GNR.tblCust have no discovered master table or formal foreign key.",
                "NGT Number_ID overlap with GNR.tblSalePath is not sufficient to prove one-to-one identity.",
                "LastUpdate changes in 90 days show master-data churn, not completed visits or route execution.",
                "Formal dependencies do not capture dynamic SQL or every implicit reference.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON output path")
    args = parser.parse_args()
    result = collect()
    payload = json.dumps(result, ensure_ascii=False,indent=2,default=_json_default)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(payload+"\n",encoding="utf-8")
        print(args.output.resolve())
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
