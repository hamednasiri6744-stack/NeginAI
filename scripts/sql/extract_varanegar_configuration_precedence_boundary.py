"""Extract privacy-safe configuration scope, resolver, and null boundaries.

Only catalog metadata, SQL-definition fingerprints, identifier-level contracts,
and anonymous aggregates are persisted. Configuration values, secrets, hosts,
paths, identities, raw history rows, and SQL definitions are not persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from extract_varanegar_org_domain import (
    DATABASE,
    SERVER,
    _assert_safe_target,
    _connect,
    _json_default,
    _rows,
)


TABLES = (
    ("GNR", "tblGeneralConfig"),
    ("GNR", "tblServerConfig"),
    ("GNR", "tblServerConfigDC"),
    ("GNR", "tblCustConfig"),
    ("GNR", "tblCustConfigDC"),
    ("NGT", "AppSettings"),
    ("NGT", "DeviceSettings"),
    ("NGT", "DeviceSettingKeyTypes"),
)

HIGH_IMPACT_DC_FIELDS = (
    "MaxDay4OpenSale",
    "ValidPeriodOfSales",
    "ValidPeriodOfFinancial",
    "ControlSaleCloseOprDate",
    "AutoOrderConfirm",
    "CheckSaleItmStock",
    "DiscountControl",
    "OrderRowLimit",
    "MinOrderAmount",
    "MaxOrderAmount",
    "RChequePayControl",
    "PayDateControl",
    "AllowFreeReason",
    "CreateExitWithConfirmStockMan",
    "AutoGenRetSaleVocher",
)

HIGH_IMPACT_NGT_FIELDS = (
    "MandatoryCustomerVisit",
    "InventoryControl",
    "ReturnWithReference",
    "ReturnWithoutReference",
    "DistanceCheck",
    "MaxDistance",
    "ShowStock",
    "AllowEditCustomer",
    "OnlineEvc",
    "CustomerCallDateBasedOnUniqueId",
    "DisReturnDateCannotBeOlderThanNow",
    "OrderValidationErrorTypeUniqueId",
    "ReturnValidationErrorTypeUniqueId",
    "CanRemoveCustomerWhenExistOpenTour",
)

BACK_OFFICE_SOURCE_TO_DELIVERY_NAME = (
    ("DiscountControl", "SettlementDiscountPercent"),
    ("ShowNormalItmDetail", "ShowNormalItmDetail"),
    ("MaxSaleAmount", "MaximumFactorAmount"),
    ("MinSaleAmount", "MinimumFactorAmount"),
    ("MaxOrderAmount", "MaximumOrderAmount"),
    ("MinOrderAmount", "MinimumOrderAmount"),
    ("OrderRowLimit", "MaximumOrderItemCount"),
    ("OrderRowLimitMin", "MinimumOrderItemCount"),
    ("RefRetOrder", "RefRetOrder"),
    ("OrderAsnLimit", "OrderAsnLimit"),
    ("OrderBedLimit", "OrderBedLimit"),
    ("IsUndeliveredEnabled", "IsUndeliveredEnabled"),
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _qualified(schema: str, table: str) -> str:
    return f"{schema}.{table}"


def _table_columns(cursor: Any) -> list[dict[str, Any]]:
    predicates = " OR ".join(
        f"(s.name=N'{schema}' AND t.name=N'{table}')" for schema, table in TABLES
    )
    return _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,c.column_id,c.name column_name,
               ty.name data_type,c.is_nullable,dc.definition default_definition
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        LEFT JOIN sys.default_constraints dc
          ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
        WHERE {predicates}
        ORDER BY s.name,t.name,c.column_id
        """,
    )


def _exact_column_overlap(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in columns:
        by_name[row["column_name"].casefold()].append(row)
    ignored = {
        "id", "number_id", "createddate", "lastupdate", "isremoved",
        "applicationownerid", "dataownerid", "dataownercenterid", "addedbyid",
        "lastmodifiedbyid", "datageneratedownercenterid", "concurrencycheckfield",
        "rowindex", "dcref",
    }
    result = []
    for normalized, rows in sorted(by_name.items()):
        tables = sorted({_qualified(row["schema_name"], row["table_name"]) for row in rows})
        if len(tables) < 2 or normalized in ignored:
            continue
        result.append(
            {
                "column_name": rows[0]["column_name"],
                "tables": tables,
                "nullable_by_table": {
                    _qualified(row["schema_name"], row["table_name"]): bool(row["is_nullable"])
                    for row in rows
                },
            }
        )
    return result


def _table_catalog_profiles(cursor: Any, columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Persist identifier-level shape and anonymous scope/state counts only."""
    columns_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in columns:
        columns_by_table[_qualified(row["schema_name"], row["table_name"])].append(row)

    profiles: list[dict[str, Any]] = []
    for schema, table in TABLES:
        qualified = _qualified(schema, table)
        table_columns = columns_by_table[qualified]
        names = {row["column_name"] for row in table_columns}
        aggregates = ["COUNT_BIG(*) row_count"]
        if "IsRemoved" in names:
            aggregates.extend(
                [
                    "SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed_count",
                    "SUM(CASE WHEN ISNULL(IsRemoved,0)=0 THEN 1 ELSE 0 END) active_count",
                ]
            )
        for scope_name in ("DCRef", "DataOwnerCenterId", "DataOwnerId", "ApplicationOwnerId"):
            if scope_name in names:
                safe = scope_name.replace("]", "]]" )
                aggregates.append(
                    f"COUNT_BIG(DISTINCT [{safe}]) distinct_{scope_name.casefold()}_count"
                )
                aggregates.append(
                    f"SUM(CASE WHEN [{safe}] IS NULL THEN 1 ELSE 0 END) null_{scope_name.casefold()}_count"
                )
        counts = _rows(
            cursor,
            f"SELECT {','.join(aggregates)} FROM [{schema}].[{table}]",
        )[0]
        profiles.append(
            {
                "qualified_name": qualified,
                "column_count": len(table_columns),
                "column_names": [row["column_name"] for row in table_columns],
                "anonymous_counts": counts,
            }
        )
    return profiles


def _target_unique_index_contracts(cursor: Any) -> list[dict[str, Any]]:
    predicates = " OR ".join(
        f"(s.name=N'{schema}' AND t.name=N'{table}')" for schema, table in TABLES
    )
    rows = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,t.name table_name,i.name index_name,
               i.is_unique,i.is_primary_key,i.has_filter,i.filter_definition,
               ic.key_ordinal,ic.is_included_column,c.name column_name
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.indexes i ON i.object_id=t.object_id AND i.index_id>0
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE ({predicates}) AND (i.is_unique=1 OR i.is_primary_key=1)
        ORDER BY s.name,t.name,i.index_id,ic.key_ordinal,ic.index_column_id
        """,
    )
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        qualified = _qualified(row["schema_name"], row["table_name"])
        key = (qualified, row["index_name"])
        contract = grouped.setdefault(
            key,
            {
                "qualified_table": qualified,
                "index_name": row["index_name"],
                "is_unique": bool(row["is_unique"]),
                "is_primary_key": bool(row["is_primary_key"]),
                "has_filter": bool(row["has_filter"]),
                "filter_uses_removed_state": "isremoved" in (row["filter_definition"] or "").casefold(),
                "key_columns": [],
                "included_columns": [],
            },
        )
        destination = "included_columns" if row["is_included_column"] else "key_columns"
        contract[destination].append(row["column_name"])
    return list(grouped.values())


def _target_foreign_key_contracts(cursor: Any) -> list[dict[str, Any]]:
    target_names = {_qualified(schema, table).casefold() for schema, table in TABLES}
    rows = _rows(
        cursor,
        """
        SELECT fk.name constraint_name,
               ps.name parent_schema,pt.name parent_table,pc.name parent_column,
               rs.name referenced_schema,rt.name referenced_table,rc.name referenced_column,
               fkc.constraint_column_id
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.tables pt ON pt.object_id=fk.parent_object_id
        JOIN sys.schemas ps ON ps.schema_id=pt.schema_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.tables rt ON rt.object_id=fk.referenced_object_id
        JOIN sys.schemas rs ON rs.schema_id=rt.schema_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        ORDER BY ps.name,pt.name,fk.name,fkc.constraint_column_id
        """,
    )
    return [
        {
            "constraint_name": row["constraint_name"],
            "parent_table": _qualified(row["parent_schema"], row["parent_table"]),
            "parent_column": row["parent_column"],
            "referenced_table": _qualified(row["referenced_schema"], row["referenced_table"]),
            "referenced_column": row["referenced_column"],
            "constraint_column_id": row["constraint_column_id"],
        }
        for row in rows
        if _qualified(row["parent_schema"], row["parent_table"]).casefold() in target_names
        or _qualified(row["referenced_schema"], row["referenced_table"]).casefold() in target_names
    ]


def _key_scope_overlap(cursor: Any) -> dict[str, Any]:
    summary = _rows(
        cursor,
        """
        SELECT
          (SELECT COUNT_BIG(*) FROM GNR.tblGeneralConfig) general_key_count,
          (SELECT COUNT_BIG(*) FROM GNR.tblServerConfig) server_key_count,
          (SELECT COUNT_BIG(*) FROM GNR.tblGeneralConfig g JOIN GNR.tblServerConfig s
             ON LOWER(LTRIM(RTRIM(g.KeyName)))=LOWER(LTRIM(RTRIM(s.KeyName)))) exact_normalized_overlap_count,
          (SELECT COUNT_BIG(*) FROM GNR.tblServerConfig WHERE KeyValue IS NULL) server_null_value_count,
          (SELECT COUNT_BIG(*) FROM GNR.tblGeneralConfig WHERE KeyValue IS NULL) general_null_value_count
        """,
    )[0]
    overlap = _rows(
        cursor,
        """
        SELECT g.KeyName key_name
        FROM GNR.tblGeneralConfig g
        JOIN GNR.tblServerConfig s
          ON LOWER(LTRIM(RTRIM(g.KeyName)))=LOWER(LTRIM(RTRIM(s.KeyName)))
        ORDER BY g.KeyName
        """,
    )
    null_names = _rows(
        cursor,
        """
        SELECT KeyName key_name FROM GNR.tblServerConfig WHERE KeyValue IS NULL ORDER BY KeyName
        """,
    )
    return {
        "summary": summary,
        "exact_normalized_overlap_key_names": [row["key_name"] for row in overlap],
        "server_null_key_names": [row["key_name"] for row in null_names],
    }


def _null_profile(cursor: Any, schema: str, table: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    available = {
        row["column_name"]
        for row in _rows(
            cursor,
            """
            SELECT c.name column_name
            FROM sys.columns c
            WHERE c.object_id=OBJECT_ID(%s)
            """,
            (_qualified(schema, table),),
        )
    }
    selected = [field for field in fields if field in available]
    if not selected:
        return []
    clauses = []
    for field in selected:
        safe = field.replace("]", "]]")
        clauses.append(
            f"SELECT N'{field}' field_name,COUNT_BIG(*) row_count,"
            f"SUM(CASE WHEN [{safe}] IS NULL THEN 1 ELSE 0 END) null_count "
            f"FROM [{schema}].[{table}]"
        )
    return _rows(cursor, " UNION ALL ".join(clauses))


def _resolver_modules(cursor: Any) -> list[dict[str, Any]]:
    targets = {_qualified(schema, table).casefold() for schema, table in TABLES}
    dependencies = _rows(
        cursor,
        """
        SELECT d.referencing_id,rs.name referenced_schema,ro.name referenced_object
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects ro ON ro.object_id=d.referenced_id
        JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
        WHERE d.referenced_id IS NOT NULL
        """,
    )
    refs_by_id: dict[int, set[str]] = defaultdict(set)
    for row in dependencies:
        qualified = _qualified(row["referenced_schema"], row["referenced_object"])
        if qualified.casefold() in targets:
            refs_by_id[int(row["referencing_id"])].add(qualified)
    ids = sorted(object_id for object_id, refs in refs_by_id.items() if len(refs) >= 2)
    if not ids:
        return []
    placeholders = ",".join("%s" for _ in ids)
    modules = _rows(
        cursor,
        f"""
        SELECT o.object_id,s.name schema_name,o.name object_name,o.type_desc,
               o.modify_date,DATALENGTH(m.definition) definition_bytes,m.definition
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE o.object_id IN ({placeholders})
        ORDER BY s.name,o.name
        """,
        tuple(ids),
    )
    result = []
    for row in modules:
        definition = row.pop("definition")
        object_id = int(row.pop("object_id"))
        normalized = re.sub(r"\s+", " ", definition).casefold()
        refs = sorted(refs_by_id[object_id], key=str.casefold)
        result.append(
            {
                **row,
                "qualified_name": _qualified(row["schema_name"], row["object_name"]),
                "definition_sha256": _sha256(definition),
                "referenced_configuration_tables": refs,
                "reference_count": len(refs),
                "has_inner_join": " inner join " in f" {normalized} ",
                "has_left_join": " left join " in f" {normalized} ",
                "has_cross_join": " cross join " in f" {normalized} ",
                "has_union": bool(re.search(r"\bunion(?:\s+all)?\b", normalized)),
                "has_isnull": "isnull(" in normalized,
                "has_coalesce": "coalesce(" in normalized,
                "has_case": bool(re.search(r"\bcase\b", normalized)),
                "has_null_predicate": " is null" in normalized or " is not null" in normalized,
                "has_top_one": bool(re.search(r"\btop\s*\(?\s*1\s*\)?", normalized)),
                "has_order_by": " order by " in f" {normalized} ",
                "has_dynamic_execution": bool(re.search(r"\bexec(?:ute)?\s*\(", normalized)),
                "references_removed_filter": "isremoved" in normalized,
                "references_owner_scope": any(
                    name in normalized
                    for name in ("applicationowner", "dataowner", "dataownercenter")
                ),
            }
        )
    return result


def _target_module_profiles(cursor: Any) -> list[dict[str, Any]]:
    names = (
        "NGT_GetBackOfficeSettings",
        "SdsNet_serverConfig",
        "SdsNet_CustConfig",
        "NGT_TourBackOfficeSettingModel",
        "NGT_TourAppSettingModel",
        "NGT_TourDeviceSettingModel",
        "TourDeviceSettingModel",
    )
    placeholders = ",".join("%s" for _ in names)
    rows = _rows(
        cursor,
        f"""
        SELECT s.name schema_name,o.name object_name,o.type_desc,o.modify_date,
               DATALENGTH(m.definition) definition_bytes,m.definition
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE o.name IN ({placeholders})
        ORDER BY s.name,o.name
        """,
        names,
    )
    result = []
    table_tokens = {
        _qualified(schema, table): re.compile(
            rf"(?:\[?{re.escape(schema)}\]?\.)?\[?{re.escape(table)}\]?\b",
            re.IGNORECASE,
        )
        for schema, table in TABLES
    }
    for row in rows:
        definition = row.pop("definition")
        normalized = re.sub(r"\s+", " ", definition)
        result.append(
            {
                **row,
                "qualified_name": _qualified(row["schema_name"], row["object_name"]),
                "definition_sha256": _sha256(definition),
                "referenced_configuration_tables_by_text": sorted(
                    name for name, pattern in table_tokens.items() if pattern.search(normalized)
                ),
                "high_impact_fields_referenced": sorted(
                    field
                    for field in set(HIGH_IMPACT_DC_FIELDS + HIGH_IMPACT_NGT_FIELDS)
                    if re.search(rf"\b{re.escape(field)}\b", normalized, re.IGNORECASE)
                ),
                "has_isnull": bool(re.search(r"\bisnull\s*\(", normalized, re.IGNORECASE)),
                "has_coalesce": bool(re.search(r"\bcoalesce\s*\(", normalized, re.IGNORECASE)),
                "has_case": bool(re.search(r"\bcase\b", normalized, re.IGNORECASE)),
                "has_union": bool(re.search(r"\bunion(?:\s+all)?\b", normalized, re.IGNORECASE)),
                "has_top_one": bool(re.search(r"\btop\s*\(?\s*1\s*\)?", normalized, re.IGNORECASE)),
                "has_order_by": bool(re.search(r"\border\s+by\b", normalized, re.IGNORECASE)),
                "references_is_removed": bool(re.search(r"\bIsRemoved\b", normalized, re.IGNORECASE)),
                "references_dc_scope": bool(re.search(r"\bDCRef\b", normalized, re.IGNORECASE)),
                "references_owner_scope": bool(
                    re.search(r"\b(?:ApplicationOwner|DataOwner|DataOwnerCenter)", normalized, re.IGNORECASE)
                ),
            }
        )
    return result


def _target_module_lineage(cursor: Any) -> list[dict[str, Any]]:
    """Return catalog-derived column lineage, without persisting module SQL."""
    names = (
        "NGT_GetBackOfficeSettings",
        "SdsNet_serverConfig",
        "SdsNet_CustConfig",
        "NGT_TourBackOfficeSettingModel",
        "NGT_TourAppSettingModel",
        "NGT_TourDeviceSettingModel",
        "TourDeviceSettingModel",
    )
    placeholders = ",".join("%s" for _ in names)
    rows = _rows(
        cursor,
        f"""
        SELECT s.name module_schema,o.name module_name,
               rs.name referenced_schema,ro.name referenced_object,
               rc.name referenced_column
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_expression_dependencies d ON d.referencing_id=o.object_id
        LEFT JOIN sys.objects ro ON ro.object_id=d.referenced_id
        LEFT JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
        LEFT JOIN sys.columns rc
          ON rc.object_id=d.referenced_id AND rc.column_id=d.referenced_minor_id
        WHERE o.name IN ({placeholders}) AND d.referenced_id IS NOT NULL
        ORDER BY s.name,o.name,rs.name,ro.name,rc.column_id
        """,
        names,
    )
    return [
        {
            "module": _qualified(row["module_schema"], row["module_name"]),
            "referenced_table_or_module": _qualified(
                row["referenced_schema"], row["referenced_object"]
            ),
            "referenced_column": row["referenced_column"],
        }
        for row in rows
    ]


def _target_result_set_contracts(cursor: Any) -> list[dict[str, Any]]:
    """Use SQL Server metadata to describe output names and source columns."""
    names = (
        "NGT_GetBackOfficeSettings",
        "SdsNet_serverConfig",
        "SdsNet_CustConfig",
        "NGT_TourBackOfficeSettingModel",
        "NGT_TourAppSettingModel",
        "NGT_TourDeviceSettingModel",
        "TourDeviceSettingModel",
    )
    placeholders = ",".join("%s" for _ in names)
    objects = _rows(
        cursor,
        f"""
        SELECT o.object_id,s.name schema_name,o.name object_name,o.type_desc
        FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE o.name IN ({placeholders})
        ORDER BY s.name,o.name
        """,
        names,
    )
    contracts: list[dict[str, Any]] = []
    for obj in objects:
        if obj["type_desc"] == "VIEW":
            output_rows = _rows(
                cursor,
                """
                SELECT c.column_id column_ordinal,c.name output_column_name,c.is_nullable,
                       ty.name system_type_name
                FROM sys.columns c JOIN sys.types ty ON ty.user_type_id=c.user_type_id
                WHERE c.object_id=%s ORDER BY c.column_id
                """,
                (obj["object_id"],),
            )
            contracts.append(
                {
                    "module": _qualified(obj["schema_name"], obj["object_name"]),
                    "type_desc": obj["type_desc"],
                    "metadata_status": "CATALOG_VIEW_COLUMNS",
                    "metadata_error_number": None,
                    "output_columns": [
                        {
                            "ordinal": row["column_ordinal"],
                            "name": row["output_column_name"],
                            "is_nullable": row["is_nullable"],
                            "system_type_name": row["system_type_name"],
                            "source_table": None,
                            "source_column": None,
                            "is_hidden": False,
                        }
                        for row in output_rows
                    ],
                }
            )
            continue
        try:
            output_rows = _rows(
                cursor,
                """
                SELECT column_ordinal,name output_column_name,is_nullable,system_type_name,
                       source_schema,source_table,source_column,is_hidden,error_number,error_message
                FROM sys.dm_exec_describe_first_result_set_for_object(%s,1)
                ORDER BY column_ordinal
                """,
                (obj["object_id"],),
            )
            error = next((row for row in output_rows if row["error_number"] is not None), None)
            contracts.append(
                {
                    "module": _qualified(obj["schema_name"], obj["object_name"]),
                    "type_desc": obj["type_desc"],
                    "metadata_status": "ERROR" if error else "AVAILABLE",
                    "metadata_error_number": error["error_number"] if error else None,
                    "output_columns": [
                        {
                            "ordinal": row["column_ordinal"],
                            "name": row["output_column_name"],
                            "is_nullable": row["is_nullable"],
                            "system_type_name": row["system_type_name"],
                            "source_table": (
                                _qualified(row["source_schema"], row["source_table"])
                                if row["source_schema"] and row["source_table"]
                                else None
                            ),
                            "source_column": row["source_column"],
                            "is_hidden": bool(row["is_hidden"]),
                        }
                        for row in ([] if error else output_rows)
                        if row["column_ordinal"] is not None
                    ],
                }
            )
        except Exception as exc:  # catalog metadata can reject dynamic/temp-table procedures
            contracts.append(
                {
                    "module": _qualified(obj["schema_name"], obj["object_name"]),
                    "type_desc": obj["type_desc"],
                    "metadata_status": "UNAVAILABLE",
                    "metadata_error_class": type(exc).__name__,
                    "output_columns": [],
                }
            )
    return contracts


def _configuration_delivery_parity(cursor: Any) -> list[dict[str, Any]]:
    """Compare DC-effective and replication-delivered settings without values."""
    view_columns = {
        row["column_name"]
        for row in _rows(
            cursor,
            """
            SELECT c.name column_name
            FROM sys.columns c WHERE c.object_id=OBJECT_ID('GNR.SdsNet_serverConfig')
            """,
        )
    }
    server_keys = {
        row["key_name"].casefold(): row["key_name"]
        for row in _rows(cursor, "SELECT KeyName key_name FROM GNR.tblServerConfig")
    }
    definition = _rows(
        cursor,
        "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID('FRU.NGT_TourBackOfficeSettingModel')",
    )[0]["definition"]
    unpivot_match = re.search(
        r"UNPIVOT\s*\(\s*Value\s+FOR\s+Name\s+IN\s*\((.*?)\)\s*\)",
        definition or "",
        re.IGNORECASE | re.DOTALL,
    )
    delivery_identifiers = {
        token.casefold()
        for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", unpivot_match.group(1))
    } if unpivot_match else set()
    fields = [
        (field, delivery_name)
        for field, delivery_name in BACK_OFFICE_SOURCE_TO_DELIVERY_NAME
        if field in view_columns
    ]
    contracts: list[dict[str, Any]] = []
    for field, delivery_name in fields:
        safe = field.replace("]", "]]" )
        key_name = server_keys.get(field.casefold(), field)
        row = _rows(
            cursor,
            f"""
            SELECT
              COUNT_BIG(*) effective_dc_row_count,
              COUNT_BIG(DISTINCT CONVERT(nvarchar(4000),V.[{safe}])) effective_distinct_nonnull_count,
              SUM(CASE WHEN V.[{safe}] IS NULL THEN 1 ELSE 0 END) effective_null_count,
              SUM(CASE WHEN R.Value IS NULL THEN 1 ELSE 0 END) replication_null_or_absent_count,
              SUM(CASE WHEN
                    (V.[{safe}] IS NULL AND R.Value IS NULL)
                    OR LTRIM(RTRIM(CONVERT(nvarchar(4000),V.[{safe}])))=LTRIM(RTRIM(CONVERT(nvarchar(4000),R.Value)))
                  THEN 1 ELSE 0 END) exact_or_both_null_match_count,
              SUM(CASE WHEN
                    TRY_CONVERT(decimal(38,10),V.[{safe}]) IS NOT NULL
                    AND TRY_CONVERT(decimal(38,10),R.Value) IS NOT NULL
                    AND TRY_CONVERT(decimal(38,10),V.[{safe}])=TRY_CONVERT(decimal(38,10),R.Value)
                  THEN 1 ELSE 0 END) numeric_equivalent_count,
              SUM(CASE WHEN
                    (V.[{safe}] IS NULL AND R.Value IS NULL)
                    OR LTRIM(RTRIM(CONVERT(nvarchar(4000),V.[{safe}])))=LTRIM(RTRIM(CONVERT(nvarchar(4000),R.Value)))
                    OR (
                      TRY_CONVERT(decimal(38,10),V.[{safe}]) IS NOT NULL
                      AND TRY_CONVERT(decimal(38,10),R.Value) IS NOT NULL
                      AND TRY_CONVERT(decimal(38,10),V.[{safe}])=TRY_CONVERT(decimal(38,10),R.Value)
                    )
                  THEN 0 ELSE 1 END) semantic_mismatch_count,
              (SELECT COUNT_BIG(*) FROM FRU.NGT_TourBackOfficeSettingModel WHERE Name=%s) replication_row_count,
              (SELECT COUNT_BIG(*) FROM GNR.tblServerConfig WHERE KeyName=%s) global_server_key_row_count
            FROM GNR.SdsNet_serverConfig V
            OUTER APPLY (
              SELECT TOP (1) Value FROM FRU.NGT_TourBackOfficeSettingModel WHERE Name=%s
            ) R
            """,
            (delivery_name, key_name, delivery_name),
        )[0]
        contracts.append(
            {
                "source_field_name": field,
                "delivery_name": delivery_name,
                "delivery_declared_in_unpivot_contract": delivery_name.casefold() in delivery_identifiers,
                **row,
            }
        )
    return contracts


def _back_office_output_identifier_contract(cursor: Any) -> dict[str, Any]:
    rows = _rows(
        cursor,
        """
        SELECT s.name schema_name,o.name object_name,m.definition
        FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules m ON m.object_id=o.object_id
        WHERE (s.name='dbo' AND o.name='NGT_GetBackOfficeSettings')
           OR (s.name='FRU' AND o.name='NGT_TourBackOfficeSettingModel')
        """,
    )
    by_name = {
        _qualified(row["schema_name"], row["object_name"]): row["definition"] or ""
        for row in rows
    }
    procedure = by_name.get("dbo.NGT_GetBackOfficeSettings", "")
    final_select_anchor = re.search(
        r"SELECT\s+@CustName\s+AS\s+CompanyName\b(.*?)(?:\bEND\s*;?\s*$)",
        procedure,
        re.IGNORECASE | re.DOTALL,
    )
    sql_type_aliases = {
        "bigint", "binary", "bit", "char", "date", "datetime", "decimal",
        "float", "int", "money", "nchar", "numeric", "nvarchar", "real",
        "smallint", "time", "tinyint", "uniqueidentifier", "varbinary", "varchar",
    }
    procedure_outputs = []
    if final_select_anchor:
        segment = "SELECT @CustName AS CompanyName " + final_select_anchor.group(1)
        procedure_outputs = [
            alias
            for alias in re.findall(r"\bAS\s+\[?([A-Za-z_][A-Za-z0-9_]*)\]?", segment, re.IGNORECASE)
            if alias.casefold() not in sql_type_aliases
        ]
    replication = by_name.get("FRU.NGT_TourBackOfficeSettingModel", "")
    unpivot_match = re.search(
        r"UNPIVOT\s*\(\s*Value\s+FOR\s+Name\s+IN\s*\((.*?)\)\s*\)",
        replication,
        re.IGNORECASE | re.DOTALL,
    )
    replication_outputs = (
        re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", unpivot_match.group(1))
        if unpivot_match else []
    )
    proc_set = {name.casefold(): name for name in procedure_outputs}
    repl_set = {name.casefold(): name for name in replication_outputs}
    return {
        "procedure_output_names": list(dict.fromkeys(procedure_outputs)),
        "replication_unpivot_output_names": list(dict.fromkeys(replication_outputs)),
        "procedure_only_exact_name_outputs": sorted(
            (name for key, name in proc_set.items() if key not in repl_set), key=str.casefold
        ),
        "replication_only_exact_name_outputs": sorted(
            (name for key, name in repl_set.items() if key not in proc_set), key=str.casefold
        ),
        "known_semantic_rename": {"DCName": "DistributionCenterName"},
        "source_to_delivery_name": [
            {"source_field_name": source, "delivery_name": delivery}
            for source, delivery in BACK_OFFICE_SOURCE_TO_DELIVERY_NAME
        ],
    }


def _device_setting_state_and_reference_contract(cursor: Any) -> dict[str, Any]:
    cardinality = _rows(
        cursor,
        """
        WITH G AS (
          SELECT DeviceSettingNo,
                 COUNT_BIG(*) total_count,
                 SUM(CASE WHEN ISNULL(IsRemoved,0)=0 THEN 1 ELSE 0 END) active_count,
                 SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed_count
          FROM NGT.DeviceSettings GROUP BY DeviceSettingNo
        )
        SELECT
          (SELECT COUNT_BIG(*) FROM NGT.DeviceSettings) row_count,
          (SELECT COUNT_BIG(DISTINCT DeviceSettingNo) FROM NGT.DeviceSettings) distinct_number_count,
          (SELECT COUNT_BIG(*) FROM NGT.DeviceSettings WHERE DeviceSettingNo IS NULL) null_number_count,
          SUM(CASE WHEN total_count>1 THEN 1 ELSE 0 END) duplicate_number_group_count,
          MAX(total_count) maximum_rows_per_number,
          SUM(CASE WHEN active_count>1 THEN 1 ELSE 0 END) duplicate_active_number_group_count,
          SUM(CASE WHEN active_count>0 AND removed_count>0 THEN 1 ELSE 0 END) mixed_active_removed_number_group_count,
          SUM(CASE WHEN active_count=0 AND removed_count>0 THEN 1 ELSE 0 END) removed_only_number_group_count
        FROM G
        """,
    )[0]
    transport = _rows(
        cursor,
        """
        WITH G AS (
          SELECT DeviceSettingNo,
                 SUM(CASE WHEN ISNULL(IsRemoved,0)=0 THEN 1 ELSE 0 END) active_count,
                 SUM(CASE WHEN IsRemoved=1 THEN 1 ELSE 0 END) removed_count
          FROM NGT.DeviceSettings GROUP BY DeviceSettingNo
        ), T AS (
          SELECT DeviceSettingNo,COUNT_BIG(*) output_row_count
          FROM FRU.NGT_TourDeviceSettingModel
          WHERE DeviceSettingNo IS NOT NULL
          GROUP BY DeviceSettingNo
        )
        SELECT
          COUNT_BIG(*) emitted_device_number_count,
          SUM(T.output_row_count) emitted_output_row_count,
          SUM(CASE WHEN G.active_count=0 AND G.removed_count>0 THEN 1 ELSE 0 END) emitted_removed_only_number_count,
          SUM(CASE WHEN G.active_count=0 AND G.removed_count>0 THEN T.output_row_count ELSE 0 END) emitted_removed_only_output_row_count,
          SUM(CASE WHEN G.active_count>0 AND G.removed_count>0 THEN 1 ELSE 0 END) emitted_mixed_state_number_count,
          SUM(CASE WHEN G.active_count>0 AND G.removed_count>0 THEN T.output_row_count ELSE 0 END) emitted_mixed_state_output_row_count
        FROM T LEFT JOIN G ON G.DeviceSettingNo=T.DeviceSettingNo
        """,
    )[0]
    inbound_fks = _rows(
        cursor,
        """
        SELECT ps.name parent_schema,pt.name parent_table,pc.name parent_column
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.tables pt ON pt.object_id=fk.parent_object_id
        JOIN sys.schemas ps ON ps.schema_id=pt.schema_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        WHERE fk.referenced_object_id=OBJECT_ID('NGT.DeviceSettings')
        ORDER BY ps.name,pt.name
        """,
    )
    references = []
    for fk in inbound_fks:
        schema = fk["parent_schema"].replace("]", "]]" )
        table = fk["parent_table"].replace("]", "]]" )
        column = fk["parent_column"].replace("]", "]]" )
        has_child_removed = bool(
            _rows(
                cursor,
                """
                SELECT COUNT_BIG(*) match_count FROM sys.columns
                WHERE object_id=OBJECT_ID(%s) AND name='IsRemoved'
                """,
                (_qualified(fk["parent_schema"], fk["parent_table"]),),
            )[0]["match_count"]
        )
        child_active = "ISNULL(R.IsRemoved,0)=0" if has_child_removed else "1=1"
        counts = _rows(
            cursor,
            f"""
            SELECT COUNT_BIG(*) referencing_row_count,
                   SUM(CASE WHEN {child_active} THEN 1 ELSE 0 END) active_referencing_row_count,
                   SUM(CASE WHEN ISNULL(D.IsRemoved,0)=0 THEN 1 ELSE 0 END) active_setting_reference_count,
                   SUM(CASE WHEN D.IsRemoved=1 THEN 1 ELSE 0 END) removed_setting_reference_count,
                   SUM(CASE WHEN D.IsRemoved=1 AND {child_active} THEN 1 ELSE 0 END) active_child_to_removed_setting_reference_count
            FROM [{schema}].[{table}] R
            JOIN NGT.DeviceSettings D ON D.Id=R.[{column}]
            """,
        )[0]
        references.append(
            {
                "referencing_table": _qualified(fk["parent_schema"], fk["parent_table"]),
                "referencing_column": fk["parent_column"],
                **counts,
            }
        )
    return {
        "device_setting_number_cardinality": cardinality,
        "transport_emission_state": transport,
        "inbound_reference_state": references,
    }


def _configuration_transport_sql_consumers(cursor: Any) -> list[dict[str, Any]]:
    targets = (
        "FRU.NGT_TourAppSettingModel",
        "FRU.NGT_TourBackOfficeSettingModel",
        "FRU.NGT_TourDeviceSettingModel",
        "FRU.TourDeviceSettingModel",
    )
    placeholders = ",".join("OBJECT_ID(%s)" for _ in targets)
    rows = _rows(
        cursor,
        f"""
        SELECT DISTINCT rs.name referenced_schema,ro.name referenced_object,
               cs.name consumer_schema,co.name consumer_object,co.type_desc,m.definition
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects ro ON ro.object_id=d.referenced_id
        JOIN sys.schemas rs ON rs.schema_id=ro.schema_id
        JOIN sys.objects co ON co.object_id=d.referencing_id
        JOIN sys.schemas cs ON cs.schema_id=co.schema_id
        LEFT JOIN sys.sql_modules m ON m.object_id=co.object_id
        WHERE d.referenced_id IN ({placeholders}) AND d.referencing_id<>d.referenced_id
        ORDER BY cs.name,co.name,rs.name,ro.name
        """,
        targets,
    )
    result = []
    for row in rows:
        definition = row.pop("definition") or ""
        normalized = re.sub(r"\s+", " ", definition).casefold()
        result.append(
            {
                **row,
                "referenced_module": _qualified(row["referenced_schema"], row["referenced_object"]),
                "consumer_module": _qualified(row["consumer_schema"], row["consumer_object"]),
                "definition_sha256": _sha256(definition),
                "references_device_setting_number": "devicesettingno" in normalized,
                "references_removed_state": "isremoved" in normalized,
                "references_owner_scope": any(
                    token in normalized
                    for token in ("applicationowner", "dataowner", "dataownercenter")
                ),
            }
        )
    return result


def _app_device_same_name_parity(cursor: Any) -> list[dict[str, Any]]:
    fields = ("MandatoryCustomerVisit", "DisplayunitbyBasedOnUniqueId")
    definitions = {
        row["module_name"]: (row["definition"] or "")
        for row in _rows(
            cursor,
            """
            SELECT o.name module_name,m.definition FROM sys.objects o
            JOIN sys.schemas s ON s.schema_id=o.schema_id
            JOIN sys.sql_modules m ON m.object_id=o.object_id
            WHERE s.name='FRU' AND o.name IN ('NGT_TourAppSettingModel','NGT_TourDeviceSettingModel')
            """,
        )
    }
    result = []
    for field in fields:
        safe = field.replace("]", "]]" )
        row = _rows(
            cursor,
            f"""
            SELECT COUNT_BIG(*) active_device_count,
                   SUM(CASE WHEN D.[{safe}] IS NULL THEN 1 ELSE 0 END) device_null_count,
                   SUM(CASE WHEN A.[{safe}] IS NULL THEN 1 ELSE 0 END) app_null_projection_count,
                   SUM(CASE WHEN D.[{safe}]=A.[{safe}]
                                  OR (D.[{safe}] IS NULL AND A.[{safe}] IS NULL)
                            THEN 1 ELSE 0 END) exact_or_both_null_match_count,
                   SUM(CASE WHEN D.[{safe}]=A.[{safe}]
                                  OR (D.[{safe}] IS NULL AND A.[{safe}] IS NULL)
                            THEN 0 ELSE 1 END) mismatch_count
            FROM NGT.DeviceSettings D CROSS JOIN NGT.AppSettings A
            WHERE ISNULL(D.IsRemoved,0)=0 AND ISNULL(A.IsRemoved,0)=0
            """,
        )[0]
        result.append(
            {
                "field_name": field,
                "app_transport_view_references_field": field.casefold() in definitions.get(
                    "NGT_TourAppSettingModel", ""
                ).casefold(),
                "device_transport_view_references_field": field.casefold() in definitions.get(
                    "NGT_TourDeviceSettingModel", ""
                ).casefold(),
                **row,
            }
        )
    return result


def collect() -> dict[str, Any]:
    connection = _connect()
    try:
        cursor = connection.cursor()
        safety = _assert_safe_target(cursor)
        columns = _table_columns(cursor)
        table_profiles = _table_catalog_profiles(cursor, columns)
        unique_indexes = _target_unique_index_contracts(cursor)
        foreign_keys = _target_foreign_key_contracts(cursor)
        overlap = _exact_column_overlap(columns)
        key_overlap = _key_scope_overlap(cursor)
        null_profiles = {
            "GNR.tblServerConfigDC": _null_profile(
                cursor, "GNR", "tblServerConfigDC", HIGH_IMPACT_DC_FIELDS
            ),
            "NGT.AppSettings": _null_profile(
                cursor, "NGT", "AppSettings", HIGH_IMPACT_NGT_FIELDS
            ),
            "NGT.DeviceSettings": _null_profile(
                cursor, "NGT", "DeviceSettings", HIGH_IMPACT_NGT_FIELDS
            ),
        }
        resolvers = _resolver_modules(cursor)
        targets = _target_module_profiles(cursor)
        target_lineage = _target_module_lineage(cursor)
        target_result_sets = _target_result_set_contracts(cursor)
        delivery_parity = _configuration_delivery_parity(cursor)
        output_identifiers = _back_office_output_identifier_contract(cursor)
        device_state = _device_setting_state_and_reference_contract(cursor)
        transport_consumers = _configuration_transport_sql_consumers(cursor)
        app_device_parity = _app_device_same_name_parity(cursor)
    finally:
        connection.close()

    resolver_with_ambiguous_first_row = [
        row
        for row in resolvers
        if row["has_top_one"] and not row["has_order_by"]
    ]
    return {
        "artifact": "varanegar_configuration_precedence_boundary",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone(),
        "validation": "PASS",
        "scope": {"server": SERVER, "database": DATABASE},
        "safety": {
            "mode": "READ_ONLY_CLONE_CATALOG_DEFINITION_FINGERPRINTS_AND_ANONYMOUS_NULL_AGGREGATES",
            "database_updateability": safety["updateability"],
            "can_update": safety["can_update"],
            "denies_data_writes": safety["denies_data_writes"],
            "stored_procedure_or_application_command_executions": 0,
            "configuration_values_old_values_secrets_hosts_paths_or_identities_persisted": 0,
            "raw_configuration_or_history_rows_persisted": 0,
            "sql_definitions_persisted": 0,
            "safe_configuration_key_or_column_identifiers_persisted": True,
            "source_or_target_state_changed": 0,
        },
        "summary": {
            "target_table_count": len(TABLES),
            "catalog_column_count": len(columns),
            "exact_cross_table_business_column_overlap_count": len(overlap),
            "general_server_exact_key_overlap_count": int(
                key_overlap["summary"]["exact_normalized_overlap_count"] or 0
            ),
            "server_null_value_count": int(key_overlap["summary"]["server_null_value_count"] or 0),
            "multi_configuration_table_resolver_module_count": len(resolvers),
            "resolver_with_top_one_without_order_count": len(resolver_with_ambiguous_first_row),
            "target_module_profile_count": len(targets),
            "target_module_lineage_edge_count": len(target_lineage),
            "target_result_set_contract_count": len(target_result_sets),
            "target_unique_or_primary_index_count": len(unique_indexes),
            "target_related_foreign_key_edge_count": len(foreign_keys),
            "configuration_delivery_parity_field_count": len(delivery_parity),
            "configuration_delivery_static_omission_count": sum(
                1 for row in delivery_parity if not row["delivery_declared_in_unpivot_contract"]
            ),
            "configuration_delivery_current_absence_count": sum(
                1 for row in delivery_parity if int(row["replication_row_count"] or 0) == 0
            ),
            "configuration_delivery_semantic_mismatch_count": sum(
                int(row["semantic_mismatch_count"] or 0) for row in delivery_parity
                if row["delivery_declared_in_unpivot_contract"]
            ),
            "back_office_procedure_output_count": len(output_identifiers["procedure_output_names"]),
            "back_office_replication_output_count": len(
                output_identifiers["replication_unpivot_output_names"]
            ),
            "device_setting_removed_reference_count": sum(
                int(row["removed_setting_reference_count"] or 0)
                for row in device_state["inbound_reference_state"]
            ),
            "active_child_to_removed_device_setting_reference_count": sum(
                int(row["active_child_to_removed_setting_reference_count"] or 0)
                for row in device_state["inbound_reference_state"]
            ),
            "configuration_transport_direct_sql_consumer_count": len(transport_consumers),
            "app_device_same_name_current_mismatch_count": sum(
                int(row["mismatch_count"] or 0) for row in app_device_parity
            ),
        },
        "table_catalog_profiles": table_profiles,
        "target_unique_index_contracts": unique_indexes,
        "target_related_foreign_key_contracts": foreign_keys,
        "general_server_key_scope": key_overlap,
        "exact_business_column_overlap": overlap,
        "high_impact_null_profiles": null_profiles,
        "multi_table_resolver_modules": resolvers,
        "target_module_profiles": targets,
        "target_module_column_lineage": target_lineage,
        "target_result_set_contracts": target_result_sets,
        "configuration_delivery_parity": delivery_parity,
        "back_office_output_identifier_contract": output_identifiers,
        "device_setting_state_and_reference_contract": device_state,
        "configuration_transport_direct_sql_consumers": transport_consumers,
        "app_device_same_name_parity": app_device_parity,
        "evidence_limits": [
            "Exact key or column-name overlap does not by itself prove override precedence or semantic equivalence.",
            "Null counts prove stored absence, not the runtime default selected by every client or SQL path.",
            "Static SQL references prove reachable resolver shapes, not the active production request path.",
            "Desktop/mobile code may apply additional defaults or precedence outside these SQL modules.",
            "No configuration value or historical value was persisted, so current enabled/disabled policy is not asserted here.",
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
    print(json.dumps(payload["summary"], ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
