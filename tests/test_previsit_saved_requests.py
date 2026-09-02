import json
import sqlite3
import time
from contextlib import contextmanager
from threading import Thread
from types import SimpleNamespace

import pytest

from app.auth_service import create_session, create_user
from app.database import sqlite_connection
from app.models import PrevisitOutcomeRequest, PrevisitSavedRequestUpsert
from app.previsit_service import (
    PrevisitError,
    complete_visit,
    create_saved_request,
    get_saved_request,
    list_route_saved_requests,
    list_saved_requests,
    update_saved_request,
)
from app.routes.seller_workspace import complete_my_previsit


def _seed_active_visit(settings):
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            """INSERT INTO previsit_visits
               (id, username, route_id, customer_id, status, started_at, created_at, updated_at)
               VALUES ('visit-1', 'seller', 'route-1', 'customer-1', 'active', '2026-08-27T08:00:00+00:00',
                       '2026-08-27T08:00:00+00:00', '2026-08-27T08:00:00+00:00')"""
        )
        connection.execute(
            """INSERT INTO previsit_drafts
               (id, visit_id, username, idempotency_key, cart_json, payment_type, order_type, outcome,
                outcome_reason, updated_at)
               VALUES ('draft-1', 'visit-1', 'seller', 'idem-1', '[{"product_id":"old","quantity":1}]',
                       '', '', 'draft', '', '2026-08-27T08:00:00+00:00')"""
        )


def _payload(quantity=71):
    return PrevisitSavedRequestUpsert(
        lines=[{
            "product_id": "3626227101",
            "title": "محلول پاک‌کننده",
            "quantity": quantity,
            "unit_price": 2_744_628,
            "discount_amount": 0,
        }],
        payment_type="رزروی",
        order_type="پیش ویزیت",
        warehouse_ref=1,
        warehouse_name="انبار مرکزی",
        preview={"totals": {"gross": quantity * 2_744_628, "net": quantity * 2_744_628}},
    )


def test_customer_can_keep_multiple_saved_requests_and_working_cart_is_cleared(settings):
    _seed_active_visit(settings)

    first = create_saved_request(settings, "seller", "visit-1", _payload())
    second = create_saved_request(settings, "seller", "visit-1", _payload(24))

    assert first["request_number"] == 1
    assert second["request_number"] == 2
    assert first["customer_id"] == "customer-1"
    assert first["lines"][0]["quantity"] == 71
    assert [item["request_number"] for item in list_saved_requests(settings, "seller", "visit-1")] == [2, 1]
    with sqlite_connection(settings.sqlite_path) as connection:
        working = connection.execute("SELECT cart_json FROM previsit_drafts WHERE visit_id = 'visit-1'").fetchone()
    assert json.loads(working["cart_json"]) == []


def test_visit_can_finish_after_a_validated_request_was_saved_and_cart_was_cleared(settings):
    _seed_active_visit(settings)
    create_saved_request(settings, "seller", "visit-1", _payload())

    result = complete_visit(
        settings,
        "seller",
        "visit-1",
        PrevisitOutcomeRequest(outcome="order"),
    )

    assert result["visit_status"] == "completed"
    assert result["outcome"] == "order"
    assert result["line_count"] == 0


def test_visit_tour_can_list_all_saved_requests_for_its_customers_today(settings):
    _seed_active_visit(settings)
    created = create_saved_request(settings, "seller", "visit-1", _payload())

    requests = list_route_saved_requests(settings, "seller", "route-1")

    assert [item["id"] for item in requests] == [created["id"]]
    assert requests[0]["customer_id"] == "customer-1"
    assert list_route_saved_requests(settings, "seller", "route-2") == []


def test_saved_request_waits_for_a_short_sqlite_write_lock(settings, monkeypatch):
    _seed_active_visit(settings)
    holder = sqlite3.connect(settings.sqlite_path, check_same_thread=False)
    holder.execute("PRAGMA journal_mode=WAL")
    holder.execute("BEGIN IMMEDIATE")

    def release_lock():
        time.sleep(0.15)
        holder.rollback()
        holder.close()

    release_thread = Thread(target=release_lock)
    release_thread.start()

    @contextmanager
    def short_busy_timeout(path):
        with sqlite_connection(path) as connection:
            connection.execute("PRAGMA busy_timeout=25")
            yield connection

    monkeypatch.setattr("app.previsit_service.sqlite_connection", short_busy_timeout)
    try:
        created = create_saved_request(settings, "seller", "visit-1", _payload())
    finally:
        release_thread.join(timeout=2)

    assert created["request_number"] == 1
    assert created["lines"][0]["quantity"] == 71


def test_saved_request_can_be_opened_and_updated_without_changing_its_number(settings):
    _seed_active_visit(settings)
    created = create_saved_request(settings, "seller", "visit-1", _payload())

    updated = update_saved_request(settings, "seller", "visit-1", created["id"], _payload(96))

    assert updated["id"] == created["id"]
    assert updated["request_number"] == 1
    assert get_saved_request(settings, "seller", "visit-1", created["id"])["lines"][0]["quantity"] == 96
    with pytest.raises(PrevisitError):
        get_saved_request(settings, "another-seller", "visit-1", created["id"])


def test_saved_request_api_exposes_create_list_get_and_update(client, settings):
    create_user(settings, "seller", "test-password")
    _seed_active_visit(settings)
    headers = {"Cookie": f"negin_session={create_session(settings, 'seller')}"}
    payload = _payload().model_dump()

    created = client.post(
        "/seller-workspace/previsit/visits/visit-1/saved-requests", json=payload, headers=headers,
    )
    assert created.status_code == 200
    request_id = created.json()["id"]
    assert client.get(
        "/seller-workspace/previsit/visits/visit-1/saved-requests", headers=headers,
    ).json()["requests"][0]["id"] == request_id
    assert client.get(
        f"/seller-workspace/previsit/visits/visit-1/saved-requests/{request_id}", headers=headers,
    ).status_code == 200
    payload["lines"][0]["quantity"] = 96
    updated = client.put(
        f"/seller-workspace/previsit/visits/visit-1/saved-requests/{request_id}",
        json=payload,
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["lines"][0]["quantity"] == 96


def test_saved_request_can_end_visit_without_revalidating_empty_cart(settings, monkeypatch):
    _seed_active_visit(settings)
    create_saved_request(settings, "seller", "visit-1", _payload())
    monkeypatch.setattr(
        "app.routes.seller_workspace.validate_order_draft",
        lambda *_args: (_ for _ in ()).throw(AssertionError("empty working cart must not be revalidated")),
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings)),
        state=SimpleNamespace(username="seller"),
    )

    response = complete_my_previsit(
        "visit-1",
        PrevisitOutcomeRequest(outcome="order"),
        request,
    )

    assert response["visit_status"] == "completed"
    assert response["outcome"] == "order"


def test_visit_tour_saved_request_api_is_route_scoped(client, settings, monkeypatch):
    create_user(settings, "seller", "test-password")
    headers = {"Cookie": f"negin_session={create_session(settings, 'seller')}"}
    monkeypatch.setattr(
        "app.routes.seller_workspace.seller_route_customers",
        lambda *_args: {"route": {"id": "route-1"}, "customers": []},
    )
    monkeypatch.setattr(
        "app.routes.seller_workspace.list_route_saved_requests",
        lambda *_args: [{"id": "saved-1", "customer_id": "customer-1"}],
    )

    response = client.get("/seller-workspace/routes/route-1/saved-requests", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"requests": [{"id": "saved-1", "customer_id": "customer-1"}]}


def test_saved_request_ui_has_customer_menu_readonly_invoice_edit_and_pdf_actions():
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    assert 'data-previsit-section="saved-requests"' in script
    assert 'data-previsit-finish-visit' in script
    assert 'id="previsitFinishVisitRailBadge"' in script
    assert "function returnToRouteCustomerList" in script
    assert "function updateRouteCustomerResolution" in script
    assert "previsitSavedRequests.length" in script
    assert "route-customer-resolution" in script
    assert 'id="savePrevisitDraft"' in script
    assert 'data-previsit-saved-request-open' in script
    assert 'data-previsit-saved-request-edit' in script
    assert 'data-previsit-saved-request-pdf' in script
    assert 'مشاهده پیش\u200cفاکتور' in script
    assert 'بازکردن در صفحه سفارش' not in script
    review_start = script.index("function showPrevisitSavedRequestReview")
    review_end = script.index("function closePrevisitSavedRequestReview", review_start)
    review = script[review_start:review_end]
    assert "savedRoot.hidden = true" in review
    assert "section: 'order'" not in review
    edit_start = script.index("function editPrevisitSavedRequest")
    edit_end = script.index("function printPrevisitSavedRequest", edit_start)
    edit = script[edit_start:edit_end]
    assert "clearPrevisitWorkingCart()" in edit
    assert "navigatePrevisitState({section: 'order', activeView: 'cart'})" in edit
    assert "printWindow.print()" in script
    assert "window.NeginAndroid.printHtml" in script
    assert "clearPrevisitWorkingCart" in script
    assert 'class="previsit-save-request-bar"' in script
    assert script.index('id="previsitPreviewResult"', script.index('class="previsit-save-request-bar"') - 2000) < script.index('class="previsit-save-request-bar"')
    assert "previsitSaveRequestSlot" not in script
    assert 'id="previsitSavedRequestReview"' in script
    saved_panel_start = script.index('data-previsit-section-panel="saved-requests"')
    saved_panel_end = script.index('data-previsit-section-panel="invoices"', saved_panel_start)
    assert 'id="previsitSavedRequestReview"' in script[saved_panel_start:saved_panel_end]
    assert "showPrevisitSavedRequestReview" in script
    assert ".previsit-saved-requests" in styles
    assert ".previsit-cart-view.is-reviewing-saved-request" not in styles


def test_saved_request_pdf_matches_invoice_columns_and_can_close_print_window():
    script = open("app/static/assistant.js", encoding="utf-8").read()
    start = script.index("function savedRequestInvoiceTable")
    end = script.index("function renderPrevisitSavedRequests", start)
    invoice = script[start:end]

    for column in (
        "تعداد نهایی", "کارتن", "عدد", "تعداد در کارتن", "قیمت پایه / نهایی",
        "قیمت تولیدکننده", "قیمت مصرف‌کننده", "تخفیف کالایی", "تخفیف حجمی",
        "تخفیف نقدی", "مالیات و عوارض", "خالص",
    ):
        assert column in invoice
    assert "officialPrevisitGiftLines" in invoice
    assert "printClose" in script
    assert "printPdf" in script
    assert "afterprint" in script
    assert "printWindow.close()" in script
    print_start = script.index("function printPrevisitSavedRequest")
    print_end = script.index("async function completePrevisit", print_start)
    printable = script[print_start:print_end]
    assert "printWindow.document.getElementById('printPdf')" in printable
    assert "setTimeout(() => printWindow.window.print()" not in printable
