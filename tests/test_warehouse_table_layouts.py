from app.auth_service import create_session, create_user
from app.database import sqlite_connection
from app.routes.warehouse_assistant import router
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client(settings):
    # API tests must not start the production ERP/background synchronization loops.
    app = FastAPI()
    app.state.settings = settings
    app.include_router(router)
    with TestClient(app) as value:
        yield value


def session(settings, username):
    create_user(settings, username, "StrongPass9")
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute("UPDATE users SET role='Admin' WHERE username=?", (username,))
    return {"Cookie": f"negin_session={create_session(settings, username)}"}


def test_layout_roundtrip_is_user_and_table_scoped(client, settings):
    one, two = session(settings, "layout.one"), session(settings, "layout.two")
    root = "/warehouse-assistant/api/table-layouts"
    payload = dict(name="خرید", is_default=True,
                   column_order=["product_name", "product_code", "barcode"],
                   visible_columns=["product_name", "product_code"],
                   filters={"product_code": "۱۲۳"}, widths={"product_name": 320, "barcode": 180})
    saved = client.post(root + "/inventory", headers=one, json=payload)
    assert saved.status_code == 201, saved.text
    record = saved.json()
    assert record["column_order"][:3] == payload["column_order"]
    assert record["visible_columns"] == payload["visible_columns"]
    assert record["filters"] == payload["filters"]
    assert record["widths"] == payload["widths"]
    assert client.get(root, headers=two).json()["layouts"] == []
    other_table = client.post(root + "/ordering", headers=one, json=payload)
    assert other_table.status_code == 201
    second = client.post(root + "/inventory", headers=one,
                         json={**payload, "name": "کنترل"}).json()
    records = client.get(root, headers=one).json()["layouts"]
    assert len(records) == 3
    assert next(r for r in records if r["id"] == record["id"])["widths"] == payload["widths"]
    assert sum(r["is_default"] for r in records) == 2
    assert not next(r for r in records if r["id"] == record["id"])["is_default"]
    updated = client.post(root + "/inventory", headers=one,
                          json={**payload, "name": "کنترل", "is_default": False})
    assert updated.status_code == 200
    assert updated.json()["id"] == second["id"]
    assert client.delete(root + "/inventory/" + record["id"], headers=two).status_code == 404
    assert client.delete(root + "/ordering/" + record["id"], headers=one).status_code == 404
    assert client.delete(root + "/inventory/" + record["id"], headers=one).status_code == 200
    assert len(client.get(root, headers=one).json()["layouts"]) == 2


def test_layout_validation_and_auth(client, settings):
    root = "/warehouse-assistant/api/table-layouts"
    assert client.get(root).status_code in (401, 403)
    headers = session(settings, "layout.validation")
    payload = dict(name="طرح", column_order=["product_code"],
                   visible_columns=["product_code"], filters={})
    for change in ({"name": "   "}, {"visible_columns": []},
                   {"column_order": ["unknown"]}, {"visible_columns": ["unknown"]},
                   {"filters": {"unknown": "x"}}, {"filters": {"product_code": "x" * 201}},
                   {"widths": {"unknown": 100}}, {"widths": {"product_code": 55}},
                   {"widths": {"product_code": 641}}, {"widths": {"product_code": True}}):
        assert client.post(root + "/inventory", headers=headers,
                           json={**payload, **change}).status_code == 422
    assert client.post(root + "/unknown", headers=headers, json=payload).status_code == 422
    for table, column in (("inventory", "product_code"), ("ordering", "product_code"),
                          ("preorder_preview", "barcode"), ("automatic_settings", "supplier"),
                          ("automatic_preorders", "supplier"), ("supply_scope", "brand")):
        response = client.post(root + "/" + table, headers=headers,
                               json={**payload, "column_order": [column], "visible_columns": [column]})
        assert response.status_code == 201, response.text
        assert response.json()["widths"] == {}


def test_dynamic_form_and_preview_table_layout_is_user_scoped(client, settings):
    one, two = session(settings, "layout.forms.one"), session(settings, "layout.forms.two")
    root = "/warehouse-assistant/api/table-layouts/ui_purchase_invoice_preview_table"
    payload = dict(name="پیش‌نمایش من", is_default=True,
                   column_order=["product_code", "barcode", "column_4"],
                   visible_columns=["product_code", "barcode"], filters={},
                   widths={"barcode": 170})
    saved = client.post(root, headers=one, json=payload)
    assert saved.status_code == 201, saved.text
    assert saved.json()["table_key"] == "ui_purchase_invoice_preview_table"
    assert client.get("/warehouse-assistant/api/table-layouts", headers=two).json()["layouts"] == []
    assert client.post(root.replace("preview_table", "bad-key"), headers=one, json=payload).status_code == 422


def test_old_layout_schema_migrates_without_losing_saved_choices(settings):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection
    from app.warehouse_table_layouts import list_layouts
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('''CREATE TABLE warehouse_table_layouts (
            id TEXT PRIMARY KEY, username TEXT, table_key TEXT, name TEXT, is_default INTEGER,
            column_order_json TEXT, visible_columns_json TEXT, filters_json TEXT,
            created_at TEXT, updated_at TEXT, UNIQUE(username,table_key,name))''')
        conn.execute('''INSERT INTO warehouse_table_layouts VALUES
            ('legacy','owner','inventory','old',1,'["product_code"]','["product_code"]','{}','now','now')''')
    for _ in range(2):
        record = list_layouts(settings, "owner")[0]
        assert record["widths"] == {}
        assert record["column_order"] == ["product_code"]
        assert record["is_default"] is True


def test_preview_identity_uses_local_order_snapshot_without_changing_amounts(client, settings):
    from test_warehouse_assistant import _inventory_workbook
    from app.warehouse_assistant_service import warehouse_connection
    headers = session(settings, "layout.preview")
    root = "/warehouse-assistant/api"
    imported = client.post(root + "/snapshots/import", headers=headers,
                           files={"file": ("inventory.xlsx", _inventory_workbook())})
    assert imported.status_code == 201
    with warehouse_connection(settings) as conn:
        conn.execute("UPDATE warehouse_snapshot_items SET barcode='6261234567890', manufacturer_product_code='SUP-42'")
    config = next(item for item in client.get(root + "/automatic-settings", headers=headers).json()["settings"]
                  if item["warehouse_code"] == "karaj")
    assert client.put(root + f"/automatic-settings/{config['id']}", headers=headers,
                      json=dict(enabled=True, reorder_coverage_days=15, target_days=20)).status_code == 200
    result = client.post(root + "/automatic-preorders/run", headers=headers)
    assert result.status_code == 200, result.text
    line = result.json()["preorders"][0]["lines"][0]
    assert line["barcode"] == "6261234567890"
    assert line["manufacturer_product_code"] == "SUP-42"
    assert line["manufacturer"] == "تامین‌کننده نمونه"
    assert line["cartons"] == 1
    assert line["estimated_value"] == 840
    assert line["average_daily_out"] == 1


def test_restart_guard_defers_when_refresh_is_running(settings, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from pathlib import Path
    import re
    import app.config
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection
    init_warehouse_store(settings)
    monkeypatch.setattr(app.config, "get_settings", lambda: settings)
    script = (Path(__file__).resolve().parents[1] / "scripts/start_public_service.ps1").read_text(encoding="utf-8")
    guard = re.search(r'& \$python -c "([^"]+)"', script).group(1)
    assert script.index("if ($LASTEXITCODE -ne 0)") < script.index("Stop-Process")
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with warehouse_connection(settings) as conn:
        conn.execute("INSERT OR REPLACE INTO warehouse_automatic_refresh_state (id,lock_token,lock_expires_at) VALUES (1,'test-lock',?)", (future,))
    scope = {}
    with pytest.raises(SystemExit) as error:
        exec(guard, scope)
    scope["c"].close()
    assert error.value.code == 2
    with warehouse_connection(settings) as conn:
        conn.execute("UPDATE warehouse_automatic_refresh_state SET lock_token=NULL WHERE id=1")
    with pytest.raises(SystemExit) as error:
        exec(guard, scope)
    scope["c"].close()
    assert error.value.code == 0
