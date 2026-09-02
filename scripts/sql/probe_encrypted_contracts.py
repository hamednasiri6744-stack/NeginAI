"""Probe safe observable behavior of encrypted Varanegar functions.

Only SELECT statements are issued against the verified read-only local clone.
The mutating maintenance procedure ``dbo.ChangeDatabaseToDBOne`` is
intentionally never executed.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import analyze_varanegar_clone as catalog


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(type(value).__name__)


def _probe(cursor: Any, name: str, sql: str) -> dict[str, Any]:
    try:
        cursor.execute(sql)
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        return {
            "name": name,
            "status": "ok",
            "result": None if row is None else dict(zip(columns, row)),
            "error": None,
        }
    except Exception as exc:
        return {"name": name, "status": "error", "result": None, "error": str(exc)}


def collect() -> dict[str, Any]:
    connection = catalog._connect()
    try:
        cursor = connection.cursor()
        context = catalog._assert_safe_target(cursor)
        probes = [
            _probe(
                cursor,
                "DateTimeToSolarX_2026_08_26",
                "SELECT GNR.DateTimeToSolarX(CONVERT(datetime,'2026-08-26',120),"
                "'yyyy/mm/dd') AS value",
            ),
            _probe(
                cursor,
                "SolarToDateTime_1405_06_04",
                "SELECT GNR.SolarToDateTime('1405/06/04') AS value",
            ),
            _probe(
                cursor,
                "SolarDateADD_plus_one",
                "SELECT GNR.SolarDateADD('1405/06/04',1) AS value",
            ),
            _probe(
                cursor,
                "SolarDateAddX_minus_one",
                "SELECT GNR.SolarDateAddX('1405/06/04',-1) AS value",
            ),
            _probe(
                cursor,
                "SolarDateDiffX_one_day",
                "SELECT GNR.SolarDateDiffX('1405/06/04','1405/06/05') AS value",
            ),
            _probe(
                cursor,
                "SolarDateFormatIsValidX_valid",
                "SELECT GNR.SolarDateFormatIsValidX('1405/06/04') AS value",
            ),
            _probe(
                cursor,
                "SolarDateFormatIsValidX_invalid",
                "SELECT GNR.SolarDateFormatIsValidX('1405-06-04') AS value",
            ),
            _probe(
                cursor,
                "SolarDateIsValidX_valid",
                "SELECT GNR.SolarDateIsValidX('1405/06/04') AS value",
            ),
            _probe(
                cursor,
                "SolarDateIsValidX_invalid",
                "SELECT GNR.SolarDateIsValidX('1405/13/40') AS value",
            ),
            _probe(
                cursor,
                "SolarDatePart_year",
                "SELECT GNR.SolarDatePart('yyyy','1405/06/04') AS value",
            ),
            _probe(
                cursor,
                "SolarDatePart_month",
                "SELECT GNR.SolarDatePart('mm','1405/06/04') AS value",
            ),
            _probe(
                cursor,
                "SolarDatePart_day",
                "SELECT GNR.SolarDatePart('dd','1405/06/04') AS value",
            ),
            _probe(
                cursor,
                "SolarToDateTimeX_1405_06_04",
                "SELECT GNR.SolarToDateTimeX('1405/06/04') AS value",
            ),
            _probe(
                cursor,
                "GetNumberStr_123456",
                "SELECT GNR.GetNumberStr('123456') AS value",
            ),
            _probe(
                cursor,
                "ufn_GetInvoiceGLId_recent_order",
                "SELECT TOP (1) dbo.ufn_GetInvoiceGLId(ID,OrderDate,CustRef) AS value "
                "FROM SLE.tblOrderHdr WHERE ID IS NOT NULL ORDER BY ID DESC",
            ),
            _probe(
                cursor,
                "vwSaleSokan_reachable",
                "SELECT TOP (1) CONVERT(bit,1) AS reachable FROM dbo.vwSaleSokan",
            ),
        ]
        return {
            "generated_at": datetime.now().astimezone(),
            "connection": context,
            "safety": {
                "statements": "SELECT only",
                "not_executed": ["dbo.ChangeDatabaseToDBOne"],
            },
            "probes": probes,
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
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
