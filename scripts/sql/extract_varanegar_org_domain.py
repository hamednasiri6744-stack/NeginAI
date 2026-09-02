"""Extract the first Varanegar information-base domain from the local clone.

The extractor is intentionally pinned to the local ``NeginPakhsh_WebDev``
database.  It refuses to run unless the database is read-only and the analysis
login has no database-level UPDATE permission.  Passwords are loaded from the
repository ``.env`` and are never written to the output.

Scope: company/organizational centers, sale offices, stock centers, their
bridges, and the two observed fiscal-year models.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytds
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
SERVER = "127.0.0.1"
DATABASE = "NeginPakhsh_WebDev"
EXPECTED_LOGIN = "Negin_Report_ReadOnly"

DOMAIN_TABLES: tuple[dict[str, str], ...] = (
    {"object": "GNR.tblDC", "role": "distribution_center_or_operational_area"},
    {"object": "GNR.tblSaleOffice", "role": "sale_office"},
    {"object": "GNR.tblStockDC", "role": "stock_center"},
    {"object": "GNR.tblDCSaleOffice", "role": "dc_sale_office_stock_bridge"},
    {"object": "GNR.tblDCDependency", "role": "dc_area_dependency"},
    {"object": "GNR.tblAccYear", "role": "operational_accounting_year"},
    {"object": "dbo.FiscalYear", "role": "general_ledger_fiscal_year"},
    {"object": "dbo.DCFiscalYear", "role": "dc_general_ledger_fiscal_year_bridge"},
)


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return "0x" + value.hex()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _rows(cursor: Any, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _decode_cp1256(value: bytes | bytearray | memoryview | None) -> str | None:
    if value is None:
        return None
    return bytes(value).decode("cp1256")


def _decode_fields(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    for row in rows:
        for field in fields:
            row[field] = _decode_cp1256(row[field])
    return rows


def _connect() -> Any:
    load_dotenv(ENV_PATH, override=True)
    user = os.environ.get("SQL_USERNAME", "")
    password = os.environ.get("SQL_PASSWORD", "")
    if user != EXPECTED_LOGIN or not password:
        raise RuntimeError("Expected read-only analysis credentials are missing from .env.")
    return pytds.connect(
        dsn=SERVER,
        database=DATABASE,
        user=user,
        password=password,
        login_timeout=6,
        timeout=180,
        readonly=True,
        autocommit=True,
    )


def _assert_safe_target(cursor: Any) -> dict[str, Any]:
    context = _rows(
        cursor,
        """
        SELECT
            CONVERT(nvarchar(128), SERVERPROPERTY('MachineName')) AS machine_name,
            CONVERT(nvarchar(128), @@SERVERNAME) AS server_name,
            DB_NAME() AS database_name,
            SUSER_SNAME() AS login_name,
            USER_NAME() AS database_user,
            DATABASEPROPERTYEX(DB_NAME(), 'Updateability') AS updateability,
            HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'SELECT') AS can_select,
            HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION') AS can_view_definition,
            HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'UPDATE') AS can_update,
            IS_MEMBER('db_denydatawriter') AS denies_data_writes
        """,
    )[0]
    local_names = {
        socket.gethostname().casefold(),
        os.environ.get("COMPUTERNAME", "").casefold(),
        "localhost",
    }
    if str(context["machine_name"]).casefold() not in local_names:
        raise RuntimeError(f"Safety stop: SQL target is not local: {context!r}")
    if context["database_name"] != DATABASE:
        raise RuntimeError(f"Safety stop: unexpected database: {context!r}")
    if context["login_name"] != EXPECTED_LOGIN:
        raise RuntimeError(f"Safety stop: unexpected login: {context!r}")
    if context["updateability"] != "READ_ONLY":
        raise RuntimeError(f"Safety stop: clone is not read-only: {context!r}")
    if context["can_select"] != 1 or context["can_view_definition"] != 1:
        raise RuntimeError(f"Safety stop: required analysis permissions are missing: {context!r}")
    if context["can_update"] != 0 or context["denies_data_writes"] != 1:
        raise RuntimeError(f"Safety stop: analysis login is not write-denied: {context!r}")
    return context


def _table_metadata(cursor: Any, object_name: str, role: str) -> dict[str, Any]:
    identity = _rows(
        cursor,
        """
        SELECT s.name AS schema_name, t.name AS table_name, t.object_id,
               t.create_date, t.modify_date,
               SUM(CASE WHEN ps.index_id IN (0,1) THEN ps.row_count ELSE 0 END) AS row_count,
               SUM(CASE WHEN ps.index_id IN (0,1) THEN ps.reserved_page_count ELSE 0 END) * 8 AS reserved_kb
        FROM sys.tables AS t
        JOIN sys.schemas AS s ON s.schema_id=t.schema_id
        LEFT JOIN sys.dm_db_partition_stats AS ps ON ps.object_id=t.object_id
        WHERE t.object_id=OBJECT_ID(%s, 'U')
        GROUP BY s.name,t.name,t.object_id,t.create_date,t.modify_date
        """,
        (object_name,),
    )
    if not identity:
        raise RuntimeError(f"Required domain table is missing: {object_name}")
    info = identity[0]
    info["role"] = role
    info["columns"] = _rows(
        cursor,
        """
        SELECT c.column_id, c.name AS column_name, TYPE_NAME(c.user_type_id) AS data_type,
               c.max_length, c.precision, c.scale, c.is_nullable, c.is_identity,
               dc.definition AS default_definition, cc.definition AS computed_definition
        FROM sys.columns AS c
        LEFT JOIN sys.default_constraints AS dc
          ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
        LEFT JOIN sys.computed_columns AS cc
          ON cc.object_id=c.object_id AND cc.column_id=c.column_id
        WHERE c.object_id=OBJECT_ID(%s, 'U')
        ORDER BY c.column_id
        """,
        (object_name,),
    )
    info["primary_key"] = _rows(
        cursor,
        """
        SELECT i.name AS constraint_name, ic.key_ordinal, c.name AS column_name,
               i.is_unique, i.type_desc AS index_type
        FROM sys.indexes AS i
        JOIN sys.index_columns AS ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns AS c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID(%s, 'U') AND i.is_primary_key=1
        ORDER BY ic.key_ordinal
        """,
        (object_name,),
    )
    info["unique_keys"] = _rows(
        cursor,
        """
        SELECT i.name AS index_name, ic.key_ordinal, c.name AS column_name,
               i.is_unique_constraint, i.has_filter, i.filter_definition
        FROM sys.indexes AS i
        JOIN sys.index_columns AS ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns AS c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.object_id=OBJECT_ID(%s, 'U') AND i.is_unique=1 AND i.is_primary_key=0
          AND ic.is_included_column=0
        ORDER BY i.name,ic.key_ordinal
        """,
        (object_name,),
    )
    info["triggers"] = _rows(
        cursor,
        """
        SELECT OBJECT_SCHEMA_NAME(tr.object_id) AS schema_name, tr.name AS trigger_name,
               tr.is_disabled, tr.is_instead_of_trigger, tr.create_date, tr.modify_date
        FROM sys.triggers AS tr
        WHERE tr.parent_id=OBJECT_ID(%s, 'U')
        ORDER BY tr.name
        """,
        (object_name,),
    )
    return info


def _foreign_keys(cursor: Any) -> list[dict[str, Any]]:
    object_ids = ",".join(f"OBJECT_ID(N'{item['object']}', 'U')" for item in DOMAIN_TABLES)
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
               fk.is_disabled, fk.is_not_trusted
        FROM sys.foreign_keys AS fk
        JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id=fk.object_id
        JOIN sys.columns AS pc
          ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns AS rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE fk.parent_object_id IN ({object_ids})
           OR fk.referenced_object_id IN ({object_ids})
        ORDER BY referenced_schema,referenced_table,parent_schema,parent_table,fk.name,fkc.constraint_column_id
        """,
    )


def _module_consumers(cursor: Any) -> list[dict[str, Any]]:
    object_ids = ",".join(f"OBJECT_ID(N'{item['object']}', 'U')" for item in DOMAIN_TABLES)
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
    return _rows(
        cursor,
        """
        WITH candidate_columns AS (
            SELECT c.object_id,c.column_id,s.name AS schema_name,t.name AS table_name,
                   c.name AS column_name,TYPE_NAME(c.user_type_id) AS data_type
            FROM sys.columns AS c
            JOIN sys.tables AS t ON t.object_id=c.object_id
            JOIN sys.schemas AS s ON s.schema_id=t.schema_id
            WHERE LOWER(c.name) IN (
                'dcref','dcid','todcid','fromdcid','saleofficeref','saleofficeid',
                'fromsaleofficeid','tosaleofficeid','stockdcref','stockdcid','stockid',
                'dcsaleofficeref','dcsaleofficeid','accyear','accyearid','fiscalyearid'
            )
        )
        SELECT cc.schema_name,cc.table_name,cc.column_name,cc.data_type,
               CASE WHEN fkc.constraint_object_id IS NULL THEN 0 ELSE 1 END AS has_formal_fk,
               OBJECT_SCHEMA_NAME(fkc.referenced_object_id) AS formal_target_schema,
               OBJECT_NAME(fkc.referenced_object_id) AS formal_target_table,
               rc.name AS formal_target_column
        FROM candidate_columns AS cc
        LEFT JOIN sys.foreign_key_columns AS fkc
          ON fkc.parent_object_id=cc.object_id AND fkc.parent_column_id=cc.column_id
        LEFT JOIN sys.columns AS rc
          ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE cc.object_id NOT IN (
            OBJECT_ID(N'GNR.tblDC','U'),OBJECT_ID(N'GNR.tblSaleOffice','U'),
            OBJECT_ID(N'GNR.tblStockDC','U'),OBJECT_ID(N'GNR.tblDCSaleOffice','U'),
            OBJECT_ID(N'GNR.tblDCDependency','U'),OBJECT_ID(N'GNR.tblAccYear','U'),
            OBJECT_ID(N'dbo.FiscalYear','U'),OBJECT_ID(N'dbo.DCFiscalYear','U')
        )
        ORDER BY has_formal_fk,schema_name,table_name,column_name
        """,
    )


def _business_snapshot(cursor: Any) -> dict[str, Any]:
    centers = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,DCCode,CONVERT(varbinary(max),DCName) AS DCName,DCCategory,
                   Status,IsCentralize,StartAccYear
            FROM GNR.tblDC ORDER BY ID
            """,
        ),
        ("DCName",),
    )
    sale_offices = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,CONVERT(varbinary(max),Name) AS Name,AccPriority,
                   IsSaleActive,IsAccActive,IgnoreDistributeRetOrderHdr,IgnoreForReceipt
            FROM GNR.tblSaleOffice ORDER BY ID
            """,
        ),
        ("Name",),
    )
    stock_centers = _decode_fields(
        _rows(
            cursor,
            """
            SELECT ID,DCRef,StockDCCode,CONVERT(varbinary(max),StockDCName) AS StockDCName,
                   StockType,ShipTypeRef,InActiveAccYear,
                   AllowNegativeOnHandQty,AllowNegativeCardexQty
            FROM GNR.tblStockDC ORDER BY ID
            """,
        ),
        ("StockDCName",),
    )
    return {
        "distribution_centers": centers,
        "sale_offices": sale_offices,
        "stock_centers": stock_centers,
        "dc_sale_office_stock_links": _rows(
            cursor,
            "SELECT ID,DCRef,SaleOfficeRef,StockDcRef,DLCode FROM GNR.tblDCSaleOffice ORDER BY ID",
        ),
        "dc_area_dependency_summary": _rows(
            cursor,
            """
            SELECT DCRef,COUNT_BIG(*) AS area_count,
                   SUM(CASE WHEN Status=1 THEN 1 ELSE 0 END) AS active_area_count,
                   MIN(Distance) AS min_distance,MAX(Distance) AS max_distance
            FROM GNR.tblDCDependency GROUP BY DCRef ORDER BY DCRef
            """,
        ),
        "operational_accounting_years": _rows(
            cursor,
            """
            SELECT ID,StartDate,EndDate,AccYear,CreatedAt,ModifiedAt
            FROM GNR.tblAccYear ORDER BY ID
            """,
        ),
        "general_ledger_fiscal_years": _rows(
            cursor,
            """
            SELECT FiscalYearId,FiscalYearName,StartDate,EndDate,VoucherStartNo,
                   ModifiedDate,CreatedDate
            FROM dbo.FiscalYear ORDER BY FiscalYearId
            """,
        ),
        "dc_general_ledger_fiscal_year_links": _rows(
            cursor,
            """
            SELECT DCFiscalYearId,FiscalYearId,DCId,LastFinalNo,LastFinalDate,
                   IsLocked,IsClosed,IsClosingVoucher,HasInitialVoucher,
                   HasConclusiveVoucher,CenterIsLocked
            FROM dbo.DCFiscalYear ORDER BY DCFiscalYearId
            """,
        ),
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
        foreign_keys = _foreign_keys(cursor)
        module_consumers = _module_consumers(cursor)
        implicit_links = _implicit_link_candidates(cursor)
        return {
            "generated_at": datetime.now().astimezone(),
            "domain": "organization_and_fiscal_year",
            "scope": {
                "server": SERVER,
                "database": DATABASE,
                "mode": "read-only metadata and small information-base snapshots",
                "company_master_status": "not_established",
            },
            "safety": safety,
            "tables": tables,
            "formal_foreign_keys": foreign_keys,
            "module_consumers": module_consumers,
            "implicit_link_candidates": implicit_links,
            "business_snapshot": _business_snapshot(cursor),
            "evidence_limits": [
                "Formal foreign keys do not cover dynamic SQL or every Ref/Id convention.",
                "Index usage on the restored clone is not evidence of three-month production activity.",
                "No populated canonical company master table has been established in this slice.",
                "Persian varchar labels are decoded from their stored Windows-1256 bytes.",
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON output path")
    args = parser.parse_args()
    result = collect()
    payload = json.dumps(result, ensure_ascii=False, indent=2, default=_json_default)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(args.output.resolve())
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
