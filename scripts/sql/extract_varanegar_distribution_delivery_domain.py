"""Extract Varanegar distribution, assignment, exit, and delivery evidence.

Only aggregate operational evidence, safe reference labels, schema metadata,
and selected SQL contracts are persisted.  Personnel/customer rows, comments,
host/user names, coordinates, credentials, and raw collection values are
intentionally excluded.
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
    _decode_fields,
    _json_default,
    _rows,
    _table_metadata,
)


DOMAIN_TABLES: tuple[dict[str, str], ...] = (
    {"object": "SLE.tblDist", "role": "distribution_header"},
    {"object": "SLE.tblDistTeam", "role": "distribution_team_template"},
    {"object": "GNR.tblTruck", "role": "distribution_vehicle_master"},
    {"object": "inv.tblExit", "role": "warehouse_exit_header"},
    {"object": "SLE.tblSaleHdr", "role": "current_sale_distribution_pointer"},
    {"object": "SLE.tblSaleDistHist", "role": "sale_distribution_assignment_history"},
    {"object": "SLE.tblSaleDistHistFull", "role": "full_sale_distribution_event_snapshot"},
    {"object": "SLE.tblDistLog", "role": "distribution_status_event_log"},
    {"object": "SLE.tblUndeliveredReason", "role": "undelivered_reason_master"},
    {"object": "inv.tblRetDistHdr", "role": "legacy_distribution_return_header"},
    {"object": "inv.tblRetDistItm", "role": "legacy_distribution_return_line"},
    {"object": "NGT.Tours", "role": "ngt_tour_state_snapshot"},
    {"object": "NGT.CustomerCalls", "role": "ngt_customer_call_distribution_crosswalk"},
    {"object": "SLE.tblOrderDeliveryTime", "role": "configured_order_delivery_time_window"},
)

BUSINESS_DATE_FROM = "1405/03/01"
BUSINESS_DATE_TO = "1405/05/31"


def _object_ids_sql() -> str:
    return ",".join(f"OBJECT_ID(N'{item['object']}', 'U')" for item in DOMAIN_TABLES)


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    ids = _object_ids_sql()
    return _rows(cursor, f"""
        SELECT fk.name constraint_name,
               OBJECT_SCHEMA_NAME(fk.parent_object_id) parent_schema,
               OBJECT_NAME(fk.parent_object_id) parent_table,pc.name parent_column,
               OBJECT_SCHEMA_NAME(fk.referenced_object_id) referenced_schema,
               OBJECT_NAME(fk.referenced_object_id) referenced_table,rc.name referenced_column,
               fk.delete_referential_action_desc on_delete,
               fk.update_referential_action_desc on_update,
               fk.is_disabled,fk.is_not_trusted
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE fk.parent_object_id IN ({ids}) OR fk.referenced_object_id IN ({ids})
        ORDER BY referenced_schema,referenced_table,parent_schema,parent_table,
                 fk.name,fkc.constraint_column_id
    """)


def _module_consumers(cursor: Any) -> list[dict[str, Any]]:
    ids = _object_ids_sql()
    return _rows(cursor, f"""
        SELECT DISTINCT OBJECT_SCHEMA_NAME(d.referencing_id) consumer_schema,
               OBJECT_NAME(d.referencing_id) consumer_name,o.type_desc consumer_type,
               OBJECT_SCHEMA_NAME(d.referenced_id) source_schema,
               OBJECT_NAME(d.referenced_id) source_table,
               d.is_schema_bound_reference,o.modify_date consumer_modify_date
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects o ON o.object_id=d.referencing_id
        WHERE d.referenced_id IN ({ids})
        ORDER BY source_schema,source_table,consumer_schema,consumer_name
    """)


def _implicit_link_candidates(cursor: Any) -> list[dict[str, Any]]:
    ids = _object_ids_sql()
    return _rows(cursor, f"""
        WITH candidates AS (
          SELECT c.object_id,c.column_id,s.name schema_name,t.name table_name,
                 c.name column_name,TYPE_NAME(c.user_type_id) data_type
          FROM sys.columns c
          JOIN sys.tables t ON t.object_id=c.object_id
          JOIN sys.schemas s ON s.schema_id=t.schema_id
          WHERE LOWER(c.name) LIKE '%distref%'
             OR LOWER(c.name) LIKE '%distributionref%'
             OR LOWER(c.name) LIKE '%distributionuniqueid%'
             OR LOWER(c.name) LIKE '%exitref%'
             OR LOWER(c.name) LIKE '%driverref%'
             OR LOWER(c.name) LIKE '%truckref%'
             OR LOWER(c.name) LIKE '%vehicleuniqueid%'
             OR LOWER(c.name) LIKE '%touruniqueid%'
        )
        SELECT c.schema_name,c.table_name,c.column_name,c.data_type,
               CASE WHEN fkc.constraint_object_id IS NULL THEN 0 ELSE 1 END has_formal_fk,
               OBJECT_SCHEMA_NAME(fkc.referenced_object_id) formal_target_schema,
               OBJECT_NAME(fkc.referenced_object_id) formal_target_table,
               rc.name formal_target_column
        FROM candidates c
        LEFT JOIN sys.foreign_key_columns fkc
          ON fkc.parent_object_id=c.object_id AND fkc.parent_column_id=c.column_id
        LEFT JOIN sys.columns rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE c.object_id NOT IN ({ids})
        ORDER BY has_formal_fk,c.schema_name,c.table_name,c.column_name
    """)


def _reference_masters(cursor: Any) -> dict[str, Any]:
    dist_statuses = _decode_fields(_rows(cursor, """
        SELECT Code,CONVERT(varbinary(max),Title) Title,Value1,Value2
        FROM GNR.tblLookup WHERE CodeType=44 ORDER BY Code
    """), ("Title",))
    undelivered = _decode_fields(_rows(cursor, """
        SELECT ID,UndeliveredCode,
               CONVERT(varbinary(max),UndeliveredName) UndeliveredName,UniqueId
        FROM SLE.tblUndeliveredReason ORDER BY ID
    """), ("UndeliveredName",))
    delivery_window = _rows(cursor, """
        SELECT Id,FromTime,ToTime,Status FROM SLE.tblOrderDeliveryTime ORDER BY Id
    """)
    ngt_tour_statuses = _rows(cursor, """
        SELECT b.Id,b.BaseValueName,b.Number_ID,COUNT_BIG(*) distribution_tours
        FROM NGT.Tours t JOIN NGT.BaseValues b ON b.Id=t.TourStatusUniqueId
        WHERE t.HasDistribution=1
        GROUP BY b.Id,b.BaseValueName,b.Number_ID ORDER BY distribution_tours DESC
    """)
    return {"distribution_statuses": dist_statuses,
            "undelivered_reasons": undelivered,
            "configured_delivery_windows": delivery_window,
            "ngt_distribution_tour_statuses": ngt_tour_statuses}


def _distribution_profile(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) distributions,COUNT(DISTINCT UniqueId) distinct_uuids,
               SUM(CASE WHEN UniqueId IS NULL THEN 1 ELSE 0 END) null_uuids,
               SUM(CASE WHEN SendDate IS NOT NULL THEN 1 ELSE 0 END) has_send_date,
               SUM(CASE WHEN ReturnDate IS NOT NULL THEN 1 ELSE 0 END) has_return_date,
               SUM(CASE WHEN TruckRef IS NOT NULL THEN 1 ELSE 0 END) truck_links,
               SUM(CASE WHEN DriverRef IS NOT NULL THEN 1 ELSE 0 END) driver_links,
               SUM(CASE WHEN DistributerRef IS NOT NULL THEN 1 ELSE 0 END) distributor_links,
               SUM(CASE WHEN RealDistributerRef IS NOT NULL THEN 1 ELSE 0 END) real_distributor_links,
               COUNT(DISTINCT DistPath) distinct_legacy_path_codes,
               SUM(CASE WHEN TourId IS NOT NULL AND TourId<>0 THEN 1 ELSE 0 END) nonzero_tour_id,
               SUM(CASE WHEN TourNo=1 THEN 1 ELSE 0 END) tour_flag,
               MIN(DistDate) minimum_business_date,MAX(DistDate) maximum_business_date
        FROM SLE.tblDist
    """)[0]
    statuses = _decode_fields(_rows(cursor, """
        SELECT d.Status,CONVERT(varbinary(max),l.Title) status_title,
               COUNT_BIG(*) distributions,
               SUM(CASE WHEN d.SendDate IS NOT NULL THEN 1 ELSE 0 END) has_send_date,
               SUM(CASE WHEN d.ReturnDate IS NOT NULL THEN 1 ELSE 0 END) has_return_date
        FROM SLE.tblDist d
        LEFT JOIN GNR.tblLookup l ON l.CodeType=44 AND l.Code=d.Status
        GROUP BY d.Status,l.Title ORDER BY distributions DESC
    """), ("status_title",))
    business_window = _decode_fields(_rows(cursor, f"""
        SELECT d.Status,CONVERT(varbinary(max),l.Title) status_title,
               COUNT_BIG(*) distributions,
               SUM(CASE WHEN d.SendDate IS NOT NULL THEN 1 ELSE 0 END) has_send_date,
               SUM(CASE WHEN d.ReturnDate IS NOT NULL THEN 1 ELSE 0 END) has_return_date,
               COUNT(DISTINCT d.DriverRef) drivers,
               COUNT(DISTINCT d.DistributerRef) distributors,
               COUNT(DISTINCT d.TruckRef) trucks
        FROM SLE.tblDist d
        LEFT JOIN GNR.tblLookup l ON l.CodeType=44 AND l.Code=d.Status
        WHERE d.DistDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
        GROUP BY d.Status,l.Title ORDER BY distributions DESC
    """), ("status_title",))
    business_summary = _rows(cursor, f"""
        SELECT COUNT_BIG(*) distributions,COUNT(DISTINCT DriverRef) drivers,
               COUNT(DISTINCT DistributerRef) distributors,
               COUNT(DISTINCT RealDistributerRef) real_distributors,
               COUNT(DISTINCT TruckRef) vehicles,COUNT(DISTINCT DistPath) legacy_path_codes,
               SUM(CASE WHEN Status=7 THEN 1 ELSE 0 END) finished,
               SUM(CASE WHEN Status=0 THEN 1 ELSE 0 END) cancelled
        FROM SLE.tblDist WHERE DistDate BETWEEN '{BUSINESS_DATE_FROM}' AND '{BUSINESS_DATE_TO}'
    """)[0]
    return {"population": population, "status_distribution": statuses,
            "business_window": {"from": BUSINESS_DATE_FROM, "to": BUSINESS_DATE_TO,
                                "summary": business_summary,
                                "status_distribution": business_window}}


def _team_and_vehicle_profile(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM GNR.tblTruck) vehicle_master_rows,
          (SELECT SUM(CASE WHEN Status=1 THEN 1 ELSE 0 END) FROM GNR.tblTruck) active_vehicles,
          (SELECT COUNT(DISTINCT TruckRef) FROM SLE.tblDist) vehicles_used,
          (SELECT COUNT_BIG(*) FROM SLE.tblDistTeam) team_templates,
          (SELECT COUNT(DISTINCT DistributerRef) FROM SLE.tblDistTeam) template_distributors,
          (SELECT COUNT(DISTINCT DriverRef) FROM SLE.tblDistTeam) template_drivers,
          (SELECT COUNT(DISTINCT TruckRef) FROM SLE.tblDistTeam) template_vehicles,
          (SELECT COUNT_BIG(*) FROM SLE.tblDist d LEFT JOIN GNR.tblTruck t
             ON t.ID=d.TruckRef WHERE t.ID IS NULL) orphan_vehicles,
          (SELECT COUNT_BIG(*) FROM SLE.tblDist d LEFT JOIN dbo.Personnel p
             ON p.PersonnelId=d.DriverRef WHERE p.PersonnelId IS NULL) orphan_drivers,
          (SELECT COUNT_BIG(*) FROM SLE.tblDist d LEFT JOIN dbo.Personnel p
             ON p.PersonnelId=d.DistributerRef WHERE p.PersonnelId IS NULL) orphan_distributors
    """)[0]


def _status_event_log(cursor: Any) -> dict[str, Any]:
    population = _rows(cursor, """
        SELECT COUNT_BIG(*) events,COUNT(DISTINCT DistRef) distributions,
               SUM(CASE WHEN ExitRef IS NOT NULL THEN 1 ELSE 0 END) exit_links,
               COUNT(DISTINCT OperationType) operation_types,
               (SELECT COUNT_BIG(*) FROM SLE.tblDistLog l LEFT JOIN SLE.tblDist d
                  ON d.ID=l.DistRef WHERE d.ID IS NULL) orphan_distribution_events,
               (SELECT COUNT(DISTINCT l.DistRef) FROM SLE.tblDistLog l LEFT JOIN SLE.tblDist d
                  ON d.ID=l.DistRef WHERE d.ID IS NULL) orphan_distribution_ids
        FROM SLE.tblDistLog
    """)[0]
    transitions = _rows(cursor, """
        SELECT OldStatus,Status,COUNT_BIG(*) events,COUNT(DISTINCT DistRef) distributions
        FROM SLE.tblDistLog GROUP BY OldStatus,Status ORDER BY events DESC
    """)
    operations = _rows(cursor, """
        SELECT OperationType,COUNT_BIG(*) events,COUNT(DISTINCT DistRef) distributions
        FROM SLE.tblDistLog GROUP BY OperationType ORDER BY events DESC
    """)
    return {"population": population, "status_transitions": transitions,
            "operation_types": operations}


def _sale_assignment_history(cursor: Any) -> dict[str, Any]:
    current = _rows(cursor, """
        SELECT COUNT_BIG(*) sales_with_distribution,COUNT(DISTINCT s.DistRef) distributions,
               SUM(CASE WHEN d.ID IS NULL THEN 1 ELSE 0 END) orphan_distribution,
               SUM(CASE WHEN s.ExitRef IS NOT NULL THEN 1 ELSE 0 END) has_exit,
               SUM(CASE WHEN s.ExitRef IS NULL THEN 1 ELSE 0 END) without_exit,
               SUM(CASE WHEN s.CancelFlag<>0 THEN 1 ELSE 0 END) cancelled_sales,
               SUM(CASE WHEN d.Status=7 THEN 1 ELSE 0 END) linked_finished_distribution,
               SUM(CASE WHEN d.Status=0 THEN 1 ELSE 0 END) linked_cancelled_distribution
        FROM SLE.tblSaleHdr s LEFT JOIN SLE.tblDist d ON d.ID=s.DistRef
        WHERE s.DistRef IS NOT NULL
    """)[0]
    per_distribution = _rows(cursor, """
        SELECT COUNT_BIG(*) distributions,MIN(sales) minimum_sales,MAX(sales) maximum_sales,
               AVG(CONVERT(float,sales)) average_sales,
               SUM(CASE WHEN sales=1 THEN 1 ELSE 0 END) one_sale,
               SUM(CASE WHEN sales>1 THEN 1 ELSE 0 END) multiple_sales
        FROM (SELECT DistRef,COUNT_BIG(*) sales FROM SLE.tblSaleHdr
              WHERE DistRef IS NOT NULL GROUP BY DistRef)x
    """)[0]
    history = _rows(cursor, """
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT SaleRef) sales,
               COUNT(DISTINCT DistRef) distributions,
               SUM(CASE WHEN UndeliveredReasonRef IS NOT NULL THEN 1 ELSE 0 END)
                    undelivered_reason_rows,
               (SELECT COUNT_BIG(*) FROM (SELECT SaleRef FROM SLE.tblSaleDistHist
                  GROUP BY SaleRef HAVING COUNT_BIG(*)>1)x) sales_with_multiple_rows,
               (SELECT COUNT_BIG(*) FROM SLE.tblSaleDistHist h LEFT JOIN SLE.tblSaleHdr s
                  ON s.ID=h.SaleRef WHERE s.ID IS NULL) orphan_sales,
               (SELECT COUNT_BIG(*) FROM SLE.tblSaleDistHist h LEFT JOIN SLE.tblDist d
                  ON d.ID=h.DistRef WHERE d.ID IS NULL) orphan_distributions,
               (SELECT COUNT_BIG(*) FROM SLE.tblSaleDistHist h
                  LEFT JOIN SLE.tblUndeliveredReason r ON r.ID=h.UndeliveredReasonRef
                  WHERE h.UndeliveredReasonRef IS NOT NULL AND r.ID IS NULL) orphan_reasons
        FROM SLE.tblSaleDistHist
    """)[0]
    latest = _rows(cursor, """
        WITH h AS (
          SELECT *,ROW_NUMBER() OVER(PARTITION BY SaleRef
            ORDER BY ISNULL(ModifiedDate,InsDate) DESC,ID DESC) rn
          FROM SLE.tblSaleDistHist
        )
        SELECT COUNT_BIG(*) history_sales,
               SUM(CASE WHEN h.DistRef=s.DistRef THEN 1 ELSE 0 END) latest_agrees_current,
               SUM(CASE WHEN h.DistRef<>s.DistRef THEN 1 ELSE 0 END) latest_differs_current,
               SUM(CASE WHEN s.DistRef IS NULL THEN 1 ELSE 0 END) current_pointer_removed,
               SUM(CASE WHEN h.UndeliveredReasonRef IS NOT NULL THEN 1 ELSE 0 END)
                    latest_undelivered_reason
        FROM h JOIN SLE.tblSaleHdr s ON s.ID=h.SaleRef WHERE h.rn=1
    """)[0]
    full = _rows(cursor, """
        SELECT COUNT_BIG(*) rows,COUNT(DISTINCT ID) distinct_ids,
               COUNT(DISTINCT SaleRef) sales,COUNT(DISTINCT DistRef) distributions,
               COUNT(DISTINCT ExitRef) exits,
               SUM(CASE WHEN PreviousId IS NULL THEN 1 ELSE 0 END) null_previous_id,
               SUM(CASE WHEN UndeliveredReasonRef IS NOT NULL THEN 1 ELSE 0 END)
                    undelivered_reason_rows,
               (SELECT COUNT_BIG(*) FROM (SELECT SaleRef FROM SLE.tblSaleDistHistFull
                  GROUP BY SaleRef HAVING COUNT_BIG(*)>1)x) sales_with_multiple_events
        FROM SLE.tblSaleDistHistFull
    """)[0]
    return {"current_assignments": current, "sales_per_distribution": per_distribution,
            "assignment_history": history, "latest_history_vs_current": latest,
            "full_event_snapshot": full}


def _exit_integration(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        SELECT COUNT_BIG(*) exits,COUNT(DISTINCT e.DistRef) distributions,
               SUM(CASE WHEN e.IsCanceled=0 THEN 1 ELSE 0 END) active_exits,
               SUM(CASE WHEN e.IsCanceled<>0 THEN 1 ELSE 0 END) cancelled_exits,
               COUNT(DISTINCT CASE WHEN e.IsCanceled=0 THEN e.DistRef END)
                    active_exit_distributions,
               SUM(CASE WHEN d.ID IS NULL THEN 1 ELSE 0 END) orphan_distributions,
               (SELECT COUNT_BIG(*) FROM (SELECT DistRef FROM inv.tblExit
                  WHERE IsCanceled=0 GROUP BY DistRef HAVING COUNT_BIG(*)>1)x)
                    distributions_with_multiple_active_exits,
               (SELECT COUNT_BIG(*) FROM SLE.tblDist d WHERE NOT EXISTS
                  (SELECT 1 FROM inv.tblExit e WHERE e.DistRef=d.ID)) distributions_without_any_exit,
               (SELECT COUNT_BIG(*) FROM SLE.tblDist d WHERE NOT EXISTS
                  (SELECT 1 FROM inv.tblExit e WHERE e.DistRef=d.ID AND e.IsCanceled=0))
                    distributions_without_active_exit,
               (SELECT MAX(active_exits) FROM (SELECT DistRef,COUNT_BIG(*) active_exits
                  FROM inv.tblExit WHERE IsCanceled=0 GROUP BY DistRef)x)
                    maximum_active_exits_per_distribution,
               (SELECT COUNT_BIG(*) FROM SLE.tblSaleHdr s JOIN inv.tblExit e
                  ON e.ID=s.ExitRef WHERE s.DistRef IS NOT NULL AND s.DistRef<>e.DistRef)
                    sale_exit_distribution_mismatches
        FROM inv.tblExit e LEFT JOIN SLE.tblDist d ON d.ID=e.DistRef
    """)[0]


def _ngt_crosswalk(cursor: Any) -> dict[str, Any]:
    calls = _rows(cursor, """
        SELECT COUNT_BIG(*) calls,
               SUM(CASE WHEN n.DistributionUniqueId IS NOT NULL THEN 1 ELSE 0 END)
                    distribution_linked_calls,
               SUM(CASE WHEN n.DistributionUniqueId IS NOT NULL THEN 1 ELSE 0 END) uuid_present,
               SUM(CASE WHEN d1.ID IS NOT NULL THEN 1 ELSE 0 END) uuid_matches,
               SUM(CASE WHEN NULLIF(LTRIM(RTRIM(n.DistributionRef)),'') IS NOT NULL
                        THEN 1 ELSE 0 END) numeric_ref_present,
               SUM(CASE WHEN d2.ID IS NOT NULL THEN 1 ELSE 0 END) numeric_ref_matches,
               SUM(CASE WHEN d1.ID=d2.ID THEN 1 ELSE 0 END) id_uuid_agree,
               SUM(CASE WHEN n.DistributionNo IS NOT NULL AND LTRIM(RTRIM(n.DistributionNo))<>''
                        THEN 1 ELSE 0 END) number_present,
               SUM(CASE WHEN n.DistributionDate IS NOT NULL THEN 1 ELSE 0 END)
                    distribution_date_present,
               SUM(CASE WHEN n.DistributionUniqueId IS NOT NULL AND n.DeliveryDate IS NOT NULL
                        THEN 1 ELSE 0 END) linked_delivery_date_present,
               SUM(CASE WHEN n.DistributionUniqueId IS NOT NULL AND n.SaleDate IS NOT NULL
                        THEN 1 ELSE 0 END) linked_sale_date_present,
               SUM(CASE WHEN n.DistributionUniqueId IS NOT NULL AND n.SendDate IS NOT NULL
                        THEN 1 ELSE 0 END) linked_send_date_present,
               COUNT(DISTINCT CASE WHEN d1.ID IS NOT NULL THEN d1.ID END) matched_distributions,
               MIN(n.DistributionDate) minimum_distribution_date,
               MAX(n.DistributionDate) maximum_distribution_date
        FROM NGT.CustomerCalls n
        LEFT JOIN SLE.tblDist d1 ON d1.UniqueId=n.DistributionUniqueId
        LEFT JOIN SLE.tblDist d2 ON d2.ID=TRY_CONVERT(int,n.DistributionRef)
    """)[0]
    tours = _rows(cursor, """
        SELECT COUNT_BIG(*) tours,
               SUM(CASE WHEN n.HasDistribution=1 THEN 1 ELSE 0 END) has_distribution,
               SUM(CASE WHEN n.HasDistribution=1 AND tr.ID IS NOT NULL THEN 1 ELSE 0 END)
                    distribution_tour_vehicle_matches,
               COUNT(DISTINCT CASE WHEN n.HasDistribution=1 THEN n.AgentUniqueId END)
                    distribution_agents,
               COUNT(DISTINCT CASE WHEN n.HasDistribution=1 THEN n.DriverUniqueId END)
                    distribution_drivers,
               COUNT(DISTINCT CASE WHEN n.HasDistribution=1 THEN n.VehicleUniqueId END)
                    distribution_vehicles,
               COUNT(DISTINCT CASE WHEN n.HasDistribution=1 THEN n.TourStatusUniqueId END)
                    distribution_statuses,
               SUM(CASE WHEN n.DistributionNoCollection IS NOT NULL
                         AND LTRIM(RTRIM(n.DistributionNoCollection))<>'' THEN 1 ELSE 0 END)
                    distribution_collection_present,
               MIN(CASE WHEN n.HasDistribution=1 THEN n.TourDate END) minimum_distribution_tour_date,
               MAX(CASE WHEN n.HasDistribution=1 THEN n.TourDate END) maximum_distribution_tour_date
        FROM NGT.Tours n LEFT JOIN GNR.tblTruck tr ON tr.UniqueId=n.VehicleUniqueId
    """)[0]
    return {"customer_call_crosswalk": calls, "tour_profile": tours}


def _data_quality(cursor: Any) -> dict[str, Any]:
    return _rows(cursor, """
        SELECT
          (SELECT COUNT_BIG(*) FROM (SELECT AccYear,DCRef,DistNo FROM SLE.tblDist
             GROUP BY AccYear,DCRef,DistNo HAVING COUNT_BIG(*)>1)x)
                duplicate_composite_distribution_number_groups,
          (SELECT COUNT_BIG(*) FROM (SELECT UniqueId FROM SLE.tblDist
             GROUP BY UniqueId HAVING COUNT_BIG(*)>1)x) duplicate_distribution_uuid_groups,
          (SELECT COUNT_BIG(*) FROM SLE.tblDist d LEFT JOIN GNR.tblDistPath p
             ON p.ID=d.DistPath WHERE p.ID IS NULL)
                distribution_rows_without_legacy_path_id_match_not_an_fk_error,
          (SELECT COUNT_BIG(*) FROM sys.foreign_key_columns fkc
             JOIN sys.columns c ON c.object_id=fkc.parent_object_id
               AND c.column_id=fkc.parent_column_id
             WHERE fkc.parent_object_id=OBJECT_ID(N'SLE.tblDist')
               AND c.name='DistPath') dist_path_formal_fk_count,
          (SELECT COUNT_BIG(*) FROM GNR.tblDistPath) legacy_distribution_path_master_rows,
          (SELECT COUNT_BIG(*) FROM inv.tblRetDistHdr) legacy_return_distribution_headers,
          (SELECT COUNT_BIG(*) FROM inv.tblRetDistItm) legacy_return_distribution_lines,
          (SELECT COUNT_BIG(*) FROM SLE.tblSaleDistHist
             WHERE UndeliveredReasonRef IS NOT NULL) used_undelivered_reason_rows,
          (SELECT COUNT_BIG(*) FROM SLE.tblUndeliveredReason) undelivered_reason_master_rows
    """)[0]


def _semantic_contract_sources(cursor: Any) -> list[dict[str, Any]]:
    return _rows(cursor, """
        SELECT s.name schema_name,o.name object_name,o.type_desc,m.definition,o.modify_date
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE (s.name='GNR' AND o.name='vwDistStatus')
           OR (s.name='SLE' AND o.name IN
              ('vwDistFast','usp_sdsnet_CreateDist','usp_FinalizeRetDist',
               'usp_NotDistributedSale','trg_tblSaleHdr_DistDate'))
           OR (s.name='dbo' AND o.name IN
              ('usp_CreateExitVocherByDist','NGT_ConfirmDistributionDelivery',
               'NGT_CancelDistributionDelivery','NGT_GetDistributionTour',
               'NGT_ReturnDistStatus'))
           OR (s.name='inv' AND o.name IN ('Usp_RemoveExitFromDist','trg_tblExit_DistDate'))
        ORDER BY s.name,o.name
    """)


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        tables = [_table_metadata(cursor, x["object"], x["role"]) for x in DOMAIN_TABLES]
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "distribution_and_delivery",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata and aggregate distribution evidence",
                "privacy_policy": "no party rows, comments, coordinates, usernames, hosts, credentials, or raw collections",
            },
            "safety": safety,
            "tables": tables,
            "formal_foreign_keys": _foreign_keys(cursor),
            "module_consumers": _module_consumers(cursor),
            "implicit_link_candidates": _implicit_link_candidates(cursor),
            "reference_masters": _reference_masters(cursor),
            "distributions": _distribution_profile(cursor),
            "team_and_vehicle": _team_and_vehicle_profile(cursor),
            "status_event_log": _status_event_log(cursor),
            "sale_assignment": _sale_assignment_history(cursor),
            "exit_integration": _exit_integration(cursor),
            "ngt_crosswalk": _ngt_crosswalk(cursor),
            "data_quality": _data_quality(cursor),
            "semantic_contract_sources": _semantic_contract_sources(cursor),
            "server_clock": _rows(cursor, "SELECT SYSDATETIMEOFFSET() captured_at")[0],
            "evidence_limits": [
                "Distribution status 4 or 7 is an operational state; it does not by itself prove customer receipt.",
                "NGT CustomerCalls currently contain no DeliveryDate for distribution-linked calls.",
                "DistPath is a mode-dependent integer code, not a foreign key to GNR.tblDistPath.ID; the empty legacy master means labels and hierarchy are unresolved, not that distribution headers are orphaned.",
                "Personnel and customer identities are intentionally excluded from the artifact.",
                "SaleDistHistFull PreviousId is entirely NULL despite its name and must not be assumed to form a chain.",
                "The unused undelivered-reason master and empty return-distribution tables are retained as valid schema, not deleted.",
                "Formal dependencies do not capture dynamic SQL or every Ref/Id/UUID convention.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON output path")
    args = parser.parse_args()
    payload = json.dumps(collect(), ensure_ascii=False, indent=2, default=_json_default)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(args.output.resolve())
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
