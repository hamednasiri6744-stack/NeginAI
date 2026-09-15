from types import SimpleNamespace
import json

import pytest

from app import warehouse_purchase_contracts as purchase
from app import warehouse_sale_price_contracts as sale


@pytest.fixture
def store(tmp_path):
    settings = SimpleNamespace(sqlite_path=tmp_path / "state.db")
    purchase.replace_catalog(settings, [
        dict(product_code="A", product_name="قلم اول", goods_id=1, brand_id=4, brand="برند یک",
             supplier_id=67, supplier="افق", manufacturer_id=70, manufacturer="افق پاک تکین",
             group_id=1, group_name="گروه", tax_rate=10, tax_status="known"),
        dict(product_code="B", product_name="کرم اصلاح", goods_id=2, brand_id=5, brand="آرکو",
             supplier_id=67, supplier="افق", manufacturer_id=70, manufacturer="افق پاک تکین",
             group_id=2, group_name="کرم", tax_rate=10, tax_status="known"),
    ])
    sale.initialize(settings)
    return settings


def rule(**changes):
    value = dict(warehouse_code="karaj", manufacturer_id=70, scope="manufacturer", product_code="",
                 title="قیمت فروش افق", start_date="1405/06/17", end_date="", status="active",
                 source_includes_tax=True, markup_percent="11", note="قاعده عمومی")
    value.update(changes)
    return value


def test_calculation_removes_tax_then_adds_markup():
    result = sale.calculate(rule(), "653697", 10)
    assert result == {
        "manufacturer_price": "653697", "net_manufacturer_price": "594270",
        "markup_percent": "11", "markup_amount": "65370", "sale_price": "659640",
        "tax": "65964", "sale_price_with_tax": "725604",
    }
    assert sale.calculate(rule(markup_percent="12"), "699177", 10)["sale_price"] == "711889"
    with pytest.raises(sale.SalePriceError, match="بزرگ‌تر از صفر"):
        sale.calculate(rule(), "0", 10)


def test_warehouse_derives_order_type_and_item_overrides_manufacturer(store):
    general = sale.save_contract(store, "tester", rule())
    special = sale.save_contract(store, "tester", rule(scope="item", product_code="B", markup_percent="12"))
    assert general["stock_id"] == 1 and general["order_type_id"] == 2
    rows = sale.resolve_products(store, 70, "karaj", "1405/06/17")["items"]
    assert next(row for row in rows if row["product_code"] == "A")["contract"]["id"] == general["id"]
    assert next(row for row in rows if row["product_code"] == "B")["contract"]["id"] == special["id"]


def test_warehouse_rules_are_independent_and_overlap_is_rejected(store):
    sale.save_contract(store, "tester", rule())
    tehran = sale.save_contract(store, "tester", rule(warehouse_code="tehran"))
    assert tehran["stock_id"] == 2 and tehran["order_type_id"] == 10
    with pytest.raises(sale.SalePriceError, match="هم‌پوشانی"):
        sale.save_contract(store, "tester", rule())


def test_filtered_batch_freezes_selected_items_atomically(store):
    payload = rule(status="draft")
    payload.update(product_codes=["A"], filter_brand_id=4, filter_group_id=1)
    saved = sale.save_batch(store, "tester", payload)
    assert saved["count"] == 1 and saved["contracts"][0]["product_code"] == "A"
    assert saved["contracts"][0]["scope"] == "item"
    assert saved["contracts"][0]["selection"] == {"manufacturer_id": 70, "brand_id": 4, "group_id": 1}
    with pytest.raises(sale.SalePriceError, match="خارج"):
        sale.save_batch(store, "tester", dict(payload, product_codes=["B"]))
    assert len(sale.list_contracts(store)) == 1


def test_active_batch_conflict_rolls_back_all_items(store):
    sale.save_contract(store, "tester", rule(scope="item", product_code="B"))
    payload = rule(product_codes=["A", "B"], filter_brand_id=None, filter_group_id=None)
    with pytest.raises(sale.SalePriceError, match="هیچ قاعدهٔ جدیدی ذخیره نشد"):
        sale.save_batch(store, "tester", payload)
    assert [row["product_code"] for row in sale.list_contracts(store)] == ["B"]


def test_edit_archive_and_history(store):
    saved = sale.save_contract(store, "tester", rule())
    edited = sale.save_contract(store, "editor", dict(saved, markup_percent="12"), saved["id"], 1)
    assert edited["revision"] == 2
    with pytest.raises(sale.SalePriceError, match="هم‌زمان"):
        sale.save_contract(store, "stale", edited, saved["id"], 1)
    archived = sale.archive(store, "editor", saved["id"], 2, True)
    assert archived["status"] == "archived" and archived["revision"] == 3
    assert [entry["contract"]["revision"] for entry in sale.history(store, saved["id"])] == [3, 2, 1]


@pytest.mark.parametrize("changes", [
    {"warehouse_code": "wrong"}, {"manufacturer_id": 999}, {"scope": "brand"},
    {"scope": "item", "product_code": "wrong"}, {"markup_percent": "101"},
    {"source_includes_tax": "true"}, {"start_date": "1405/12/30"},
])
def test_invalid_rule_is_rejected(store, changes):
    with pytest.raises(sale.SalePriceError):
        sale.save_contract(store, "tester", rule(**changes))


@pytest.fixture
def api_client(store, monkeypatch):
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app = FastAPI()
    app.state.settings = store
    async def identity(request: Request):
        request.state.username = request.headers.get("X-Test-User", "editor")
    app.dependency_overrides[routes.require_session_user] = identity
    monkeypatch.setattr(routes, "_capabilities", lambda request, username: {"warehouse.assistant.view"} | (
        {"warehouse.order.draft"} if username == "editor" else set()
    ))
    app.include_router(routes.router)
    with TestClient(app) as client:
        yield client


HEADERS = {"X-Warehouse-Settings": "1", "Origin": "http://testserver"}
URL = "/warehouse-assistant/api/sale-price-contracts"


def test_api_lifecycle_and_permissions(api_client):
    assert api_client.get(URL).status_code == 200
    created = api_client.post(URL, headers=HEADERS, json=rule())
    assert created.status_code == 200 and created.json()["order_type_id"] == 2
    contract = created.json()
    edited = api_client.put(URL + "/" + contract["id"], headers=HEADERS,
                            json=dict(contract, expected_revision=1, markup_percent="12"))
    assert edited.status_code == 200 and edited.json()["revision"] == 2
    assert api_client.put(URL + "/" + contract["id"], headers=HEADERS,
                          json=dict(contract, expected_revision=1)).status_code == 409
    assert api_client.post(URL, headers={**HEADERS, "X-Test-User": "viewer"}, json=rule()).status_code == 403


def test_api_selection_filters_and_batch_create(api_client):
    selected = api_client.get(URL + "/selection", params={"manufacturer_id": 70, "brand_id": 4, "group_id": 1})
    assert selected.status_code == 200 and [row["product_code"] for row in selected.json()["items"]] == ["A"]
    payload = rule(status="draft", product_codes=["A"], filter_brand_id=4, filter_group_id=1)
    created = api_client.post(URL + "/batch", headers=HEADERS, json=payload)
    assert created.status_code == 200 and created.json()["count"] == 1


def test_api_preview_manual_and_erp_source(api_client, monkeypatch):
    manual = api_client.post(URL + "/preview", headers=HEADERS, json={
        "contract": rule(), "product_code": "A", "manufacturer_price": "653697", "on_date": "1405/06/17"
    })
    assert manual.status_code == 200
    assert manual.json()["sale_price"] == "659640" and manual.json()["price_source"] == "manual_preview"
    from app import warehouse_purchase_prices as prices
    monkeypatch.setattr(prices, "resolve_source_prices", lambda *args: {1: dict(
        goods_id=1, on_date="1405/06/17", price_id="p", start_date="1405/06/01", end_date="",
        source_count=1, manufacturer_price="653697", consumer_price="834444"
    )})
    live = api_client.post(URL + "/preview", headers=HEADERS, json={
        "contract": rule(), "product_code": "A", "manufacturer_price": "", "on_date": "1405/06/17"
    })
    assert live.status_code == 200 and live.json()["price_source"] == "erp_read_only"
    assert live.json()["erp_write"] is False
