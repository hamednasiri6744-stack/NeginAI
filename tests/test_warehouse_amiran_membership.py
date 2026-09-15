"""Exercise generated sales SQL against customer membership, without live jobs."""
from contextlib import contextmanager
from dataclasses import replace
import re
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.warehouse_assistant import router
from app import warehouse_assistant_service as service
import test_warehouse_assistant as existing


@pytest.fixture
def client(settings):
    isolated = FastAPI()
    isolated.state.settings = settings
    isolated.include_router(router)
    with TestClient(isolated) as client:
        yield client


def test_existing_sync_contract(client, settings, monkeypatch):
    existing.test_admin_syncs_inventory_and_outflow_from_varanegar_read_only(
        client, settings, monkeypatch
    )


def test_sales_sql_uses_real_membership_not_chain_category(settings, monkeypatch):
    queries = []

    @contextmanager
    def fake_connection(_settings):
        yield existing._FakeWarehouseConnection(queries)

    monkeypatch.setattr(service, "sql_connection", fake_connection)
    configured = replace(settings, sql_server="test", sql_username="reader", sql_password="test")
    service.sync_varanegar_snapshot(configured, "Admin", period_days=60)
    sql = next(q for q in queries if "WITH sales_demand AS" in q)
    # Execute the production CTE; only adapt SQL Server's Unicode literals and
    # ISNULL spelling to SQLite. No substitute membership/calculation logic.
    sales_sql = sql.split(",\nonline_transfer_demand AS", 1)[0]
    sales_sql = sales_sql.replace("ISNULL(", "IFNULL(").replace("N'", "'")
    report_date = re.search(r"BETWEEN '([^']+)'", sales_sql).group(1)
    with sqlite3.connect(":memory:") as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("ATTACH DATABASE ':memory:' AS dbo")
        conn.execute("ATTACH DATABASE ':memory:' AS GNR")
        conn.execute("CREATE TABLE GNR.tblCust (ID INTEGER PRIMARY KEY, CustGroupRef INTEGER)")
        conn.execute("CREATE TABLE dbo.SalesReviewFast (GoodsId, StockDcID, ReportDate, CustomerId, CustomerCategoryId, DealerId, SellQty, SellReturnQty)")
        conn.executemany("INSERT INTO GNR.tblCust VALUES (?, ?)", [(28002, None), (2, 2), (3, 2), (4, 5)])
        conn.executemany("INSERT INTO dbo.SalesReviewFast VALUES (2866, 1, ?, ?, ?, ?, ?, ?)", [
            (report_date, 28002, 3, 258, 5, 0),  # Iranian: category 3, not Amiran.
            (report_date, 2, 4, 258, 12, 0),    # Amiran even outside category 3.
            (report_date, 3, 3, 258, 0, 2),     # Member returns remain protected.
            (report_date, 4, 3, 258, 7, 0),     # Another group is not exempt.
            (report_date, 99, 3, 258, 9, 0),    # Missing master stays ordinary.
            (report_date, 2, 4, 7, 100, 0),     # Excluded dealer stays excluded.
        ])
        rows = {r["CustomerId"]: r for r in conn.execute(sales_sql + " SELECT * FROM sales_demand")}
    assert (rows[28002]["AmiranNetOutQty"], rows[28002]["OtherCustomerNetOutQty"]) == (0, 5)
    assert (rows[2]["AmiranNetOutQty"], rows[2]["OtherCustomerNetOutQty"]) == (12, 0)
    assert rows[3]["AmiranNetOutQty"] == -2
    assert rows[4]["OtherCustomerNetOutQty"] == 7
    assert rows[99]["OtherCustomerNetOutQty"] == 9
    assert rows[2]["ExcludedSellerNetQty"] == 100
    assert sum(r["NetOutQty"] for r in rows.values()) == 31
    assert all(r["AmiranNetOutQty"] + r["OtherCustomerNetOutQty"] == r["NetOutQty"] for r in rows.values())
