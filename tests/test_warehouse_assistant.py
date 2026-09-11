from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from io import BytesIO
import sqlite3
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from openpyxl import Workbook, load_workbook

from app.auth_service import create_session, create_user
from app.control_service import control_snapshot
from app.database import sqlite_connection
import app.warehouse_assistant_service as warehouse_service
import app.routes.warehouse_assistant as warehouse_routes


def _session(settings, username: str, role: str = "کارمند انبار") -> dict[str, str]:
    create_user(settings, username, "StrongPass9")
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            "UPDATE users SET role=?, full_name=? WHERE username=?",
            (role, username, username),
        )
    return {"Cookie": f"negin_session={create_session(settings, username)}"}


def _inventory_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "فایل انبار"
    sheet.append(
        [
            "کد کالا",
            "item name",
            "conversion  rate",
            "Manufacturer",
            "Brand",
            "stock karaj",
            "reserved karaj",
            "two month out karaj",
            "sale price karaj",
            "manufacturer price karaj",
            "consumer price karaj",
            "karaj 30 days stock",
            "Buy Price Karaj",
            "stock tehran",
            "reserved tehran",
            "two month out tehran",
            "sale price tehran",
            "manufacturer price tehran",
            "consumer price tehran",
            "tehran 30 days stock",
            "Buy Price Tehran",
            "Stock Gilan",
            "Reserved Gilan",
            "Two Month Out Gilan",
            "gilan 30 days stock",
            "sale price gilan",
            "manufacturer price gilan",
            "consumer price gilan",
            "Buy Price gilan",
        ]
    )
    sheet.append(
        [
            4014,
            "خمیر دندان آزمایشی",
            12,
            "تامین‌کننده نمونه",
            "میسویک",
            10,
            2,
            60,
            100,
            90,
            120,
            8,
            70,
            30,
            0,
            30,
            100,
            90,
            120,
            30,
            70,
            0,
            0,
            0,
            0,
            100,
            90,
            120,
            70,
        ]
    )
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_warehouse_assistant_page_is_separate_from_main_assistant(client):
    page = client.get("/warehouse-assistant")
    script = client.get("/static/warehouse-assistant.js?v=3")
    stylesheet = client.get("/static/warehouse-assistant.css?v=3")
    assistant = client.get("/assistant")

    assert page.status_code == 200
    assert 'id="warehouseAssistantApp"' in page.text
    assert "/static/warehouse-assistant.js?v=3" in page.text
    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert "/warehouse-assistant/api/bootstrap" in script.text
    assert 'id="loginDialog"' in page.text
    assert "/auth/login" in script.text
    assert "/warehouse-assistant/api/sync/varanegar" in script.text
    assert "warehouse-assistant.js" not in assistant.text
    assert "warehouseAssistantApp" not in assistant.text


def test_warehouse_assistant_api_requires_explicit_permission(client, settings):
    assert client.get("/warehouse-assistant/api/bootstrap").status_code == 401

    denied_headers = _session(settings, "warehouse.denied")
    denied = client.get(
        "/warehouse-assistant/api/bootstrap", headers=denied_headers
    )
    assert denied.status_code == 403

    admin_headers = _session(settings, "Admin", "Admin")
    allowed = client.get(
        "/warehouse-assistant/api/bootstrap", headers=admin_headers
    )
    assert allowed.status_code == 200
    assert allowed.json()["separated_from_assistant"] is True
    assert allowed.json()["commit_enabled"] is False
    assert allowed.json()["output_mode"] == "supplier_documents"
    assert allowed.json()["varanegar_integration"] == "not_applicable"


def test_permission_catalog_contains_warehouse_capabilities(settings):
    create_user(settings, "Admin", "StrongPass9")
    snapshot = control_snapshot(settings, "Admin")
    keys = {item["key"] for item in snapshot["permissions"]}

    assert {
        "warehouse.assistant.view",
        "warehouse.order.suggest",
        "warehouse.order.draft",
        "warehouse.data.refresh",
    } <= keys


def test_inventory_snapshot_import_and_deterministic_suggestion_are_isolated(
    client, settings
):
    headers = _session(settings, "Admin", "Admin")
    content = _inventory_workbook()

    imported = client.post(
        "/warehouse-assistant/api/snapshots/import",
        headers=headers,
        files={
            "file": (
                "inventory.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert imported.status_code == 201
    body = imported.json()
    assert body["product_count"] == 1
    assert body["item_count"] == 3
    assert body["duplicate"] is False
    assert body["source_sheet"] == "فایل انبار"

    duplicate = client.post(
        "/warehouse-assistant/api/snapshots/import",
        headers=headers,
        files={"file": ("inventory.xlsx", content)},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["id"] == body["id"]

    response = client.get(
        "/warehouse-assistant/api/suggestions",
        headers=headers,
        params={
            "warehouse": "karaj",
            "brand": "میسویک",
            "target_days": 30,
            "safety_days": 0,
            "period_days": 60,
        },
    )

    assert response.status_code == 200
    suggestion = response.json()["items"][0]
    assert suggestion["product_code"] == "4014"
    assert suggestion["available_quantity"] == 8
    assert suggestion["average_daily_out"] == 1
    assert suggestion["suggested_quantity"] == 24
    assert suggestion["suggested_cartons"] == 2
    assert suggestion["calculation"] == {
        "target_quantity": 30,
        "raw_requirement": 22,
        "rounded_to_conversion_rate": 12,
    }

    warehouse_db = settings.sqlite_path.with_name("warehouse-assistant.db")
    assert warehouse_db.exists()
    with sqlite3.connect(settings.sqlite_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='warehouse_snapshots'"
        ).fetchone()[0] == 0


def test_inventory_import_rejects_non_excel_files(client, settings):
    headers = _session(settings, "Admin", "Admin")
    response = client.post(
        "/warehouse-assistant/api/snapshots/import",
        headers=headers,
        files={"file": ("inventory.txt", b"not an excel workbook", "text/plain")},
    )

    assert response.status_code == 415


def test_inventory_upload_rejects_oversized_body(client, settings, monkeypatch):
    headers = _session(settings, "Admin", "Admin")
    monkeypatch.setattr(warehouse_routes, "MAX_UPLOAD_BYTES", 8)

    response = client.post(
        "/warehouse-assistant/api/snapshots/import",
        headers=headers,
        files={"file": ("inventory.xlsx", b"123456789")},
    )

    assert response.status_code == 413


def _minimal_excel_archive(path, payload: bytes) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
        archive.writestr("xl/worksheets/sheet1.xml", payload)


def test_excel_archive_rejects_high_compression_ratio(tmp_path, monkeypatch):
    path = tmp_path / "bomb.xlsx"
    _minimal_excel_archive(path, b"A" * 100_000)
    monkeypatch.setattr(warehouse_service, "MAX_ARCHIVE_ENTRY_BYTES", 200_000)
    monkeypatch.setattr(warehouse_service, "MAX_COMPRESSION_RATIO", 10)

    with pytest.raises(warehouse_service.WarehouseAssistantError, match="فشرده"):
        warehouse_service._validate_archive(path)


def test_excel_archive_rejects_oversized_single_entry(tmp_path, monkeypatch):
    path = tmp_path / "large-entry.xlsx"
    _minimal_excel_archive(path, b"not-compressible-enough")
    monkeypatch.setattr(warehouse_service, "MAX_ARCHIVE_ENTRY_BYTES", 8)

    with pytest.raises(warehouse_service.WarehouseAssistantError, match="بخش"):
        warehouse_service._validate_archive(path)


def test_excel_archive_rejects_excessive_total_expansion(tmp_path, monkeypatch):
    path = tmp_path / "large-total.xlsx"
    _minimal_excel_archive(path, b"0123456789")
    monkeypatch.setattr(warehouse_service, "MAX_ARCHIVE_ENTRY_BYTES", 100)
    monkeypatch.setattr(warehouse_service, "MAX_UNCOMPRESSED_BYTES", 20)

    with pytest.raises(warehouse_service.WarehouseAssistantError, match="بازشده"):
        warehouse_service._validate_archive(path)


def test_inventory_import_rejects_excessive_dimensions(settings, tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = warehouse_service.SOURCE_SHEET
    sheet.cell(row=2, column=warehouse_service.MAX_SHEET_COLUMNS + 1, value="x")
    path = tmp_path / "wide.xlsx"
    workbook.save(path)

    with pytest.raises(warehouse_service.WarehouseAssistantError, match="ابعاد"):
        warehouse_service.import_inventory_snapshot(settings, path, path.name, "Admin")


def test_inventory_import_rejects_oversized_cell_text(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(warehouse_service, "MAX_CELL_TEXT_CHARS", 8)
    content = _inventory_workbook()
    path = tmp_path / "long-cell.xlsx"
    path.write_bytes(content)

    with pytest.raises(warehouse_service.WarehouseAssistantError, match="سلول"):
        warehouse_service.import_inventory_snapshot(settings, path, path.name, "Admin")


def test_inventory_import_rejects_excessive_materialized_items(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(warehouse_service, "MAX_IMPORT_ITEMS", 2)
    path = tmp_path / "too-many-items.xlsx"
    path.write_bytes(_inventory_workbook())

    with pytest.raises(warehouse_service.WarehouseAssistantError, match="اقلام"):
        warehouse_service.import_inventory_snapshot(settings, path, path.name, "Admin")


def test_admin_creates_supplier_order_and_downloads_ready_documents(client, settings):
    headers = _session(settings, "Admin", "Admin")
    imported = client.post(
        "/warehouse-assistant/api/snapshots/import",
        headers=headers,
        files={"file": ("inventory.xlsx", _inventory_workbook())},
    ).json()

    created = client.post(
        "/warehouse-assistant/api/supplier-orders",
        headers=headers,
        json={
            "snapshot_id": imported["id"],
            "warehouse": "karaj",
            "note": "تحویل در انبار مرکزی",
            "lines": [
                {
                    "product_code": "4014",
                    "quantity": 22,
                    "note": "مقدار پیشنهادی سیستم",
                }
            ],
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert len(body["orders"]) == 1
    order = body["orders"][0]
    assert order["supplier"] == "تامین‌کننده نمونه"
    assert order["warehouse_code"] == "karaj"
    assert order["status"] == "prepared"
    assert order["delivery_mode"] == "supplier_document"
    assert order["lines"][0]["requested_quantity"] == 22
    assert order["lines"][0]["order_quantity"] == 24
    assert order["lines"][0]["cartons"] == 2

    listing = client.get(
        "/warehouse-assistant/api/supplier-orders", headers=headers
    )
    assert listing.status_code == 200
    assert listing.json()["orders"][0]["order_number"] == order["order_number"]

    text_document = client.get(
        f"/warehouse-assistant/api/supplier-orders/{order['id']}/document.txt",
        headers=headers,
    )
    assert text_document.status_code == 200
    assert "سفارش خرید نگین پخش" in text_document.text
    assert "تامین‌کننده نمونه" in text_document.text
    assert "خمیر دندان آزمایشی" in text_document.text
    assert "24" in text_document.text

    excel_document = client.get(
        f"/warehouse-assistant/api/supplier-orders/{order['id']}/document.xlsx",
        headers=headers,
    )
    assert excel_document.status_code == 200
    workbook = load_workbook(BytesIO(excel_document.content), read_only=True)
    assert workbook["گزارش"]["A2"].value == order["order_number"]
    assert workbook["گزارش"]["D2"].value == "4014"
    assert workbook["گزارش"]["H2"].value == 24
    assert workbook["اطلاعات"]["B1"].value.startswith("سفارش خرید")


def test_supplier_order_rejects_unknown_product(client, settings):
    headers = _session(settings, "Admin", "Admin")
    imported = client.post(
        "/warehouse-assistant/api/snapshots/import",
        headers=headers,
        files={"file": ("inventory.xlsx", _inventory_workbook())},
    ).json()

    response = client.post(
        "/warehouse-assistant/api/supplier-orders",
        headers=headers,
        json={
            "snapshot_id": imported["id"],
            "warehouse": "karaj",
            "lines": [{"product_code": "UNKNOWN", "quantity": 12}],
        },
    )

    assert response.status_code == 422
    assert "UNKNOWN" in response.json()["detail"]


class _FakeWarehouseCursor:
    def __init__(self, queries: list[str]):
        self.queries = queries
        self.description = []
        self._rows: list[tuple[object, ...]] = []

    def execute(self, sql: str):
        self.queries.append(sql)
        if "GNR.tblStockGoods" in sql:
            columns = [
                "GoodsRef", "GoodsCode", "GoodsName", "ConversionRate",
                "ManufacturerName", "BrandName", "StockDCRef", "StockDCName",
                "OnHandQty", "ReservedQty",
            ]
            self._rows = [
                (1, "4014", "خمیر دندان آزمایشی", 12, "تامین‌کننده نمونه", "میسویک", 1, "انبار مرکزي", 10, 2),
            ]
        else:
            columns = ["GoodsRef", "StockDCRef", "GrossOutQty", "ReturnQty", "NetOutQty"]
            self._rows = [(1, 1, 60, 6, 54)]
        self.description = [(column,) for column in columns]
        return self

    def fetchall(self):
        return self._rows


class _FakeWarehouseConnection:
    def __init__(self, queries: list[str]):
        self.queries = queries

    def cursor(self):
        return _FakeWarehouseCursor(self.queries)


def test_admin_syncs_inventory_and_outflow_from_varanegar_read_only(
    client, settings, monkeypatch
):
    headers = _session(settings, "Admin", "Admin")
    configured = replace(
        settings,
        sql_server="read-only-host",
        sql_username="warehouse_reader",
        sql_password="secret",
    )
    client.app.state.settings = configured
    queries: list[str] = []

    @contextmanager
    def fake_sql_connection(_settings):
        yield _FakeWarehouseConnection(queries)

    monkeypatch.setattr(warehouse_service, "sql_connection", fake_sql_connection)

    synced = client.post(
        "/warehouse-assistant/api/sync/varanegar",
        headers=headers,
        json={"period_days": 60},
    )

    assert synced.status_code == 201
    snapshot = synced.json()
    assert snapshot["source_kind"] == "varanegar"
    assert snapshot["period_days"] == 60
    assert snapshot["product_count"] == 1
    assert snapshot["item_count"] == 1
    assert snapshot["varanegar_write"] is False

    suggestions = client.get(
        "/warehouse-assistant/api/suggestions",
        headers=headers,
        params={
            "warehouse": "karaj",
            "target_days": 30,
            "safety_days": 0,
            "period_days": 60,
        },
    )
    assert suggestions.status_code == 200
    item = suggestions.json()["items"][0]
    assert item["stock"] == 10
    assert item["reserved"] == 2
    assert item["period_out"] == 54
    assert item["gross_out"] == 60
    assert item["period_return"] == 6

    assert len(queries) == 2
    assert all(query.lstrip().upper().startswith(("SELECT", "WITH")) for query in queries)
    forbidden = ("INSERT ", "UPDATE ", "DELETE ", "MERGE ", "EXEC ", "CREATE ", "ALTER ", "DROP ")
    assert all(not any(token in query.upper() for token in forbidden) for query in queries)
