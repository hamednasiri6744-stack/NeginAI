"""Atomic draft editing uses disposable SQLite only; no ERP or notification calls."""
import pytest
from test_warehouse_supplier_portal import store
from test_warehouse_order_delivery import date_draft, transition
from test_warehouse_order_stages import doc
from app import warehouse_assistant_service as service
from app import warehouse_order_delivery as dates
from app.warehouse_manual_order_edit import update_lines


def save(store, kind, token, date='۱۴۰۵/۰۶/۲۸', *, user='buyer', lines=None):
    fn = update_lines if kind == 'supplier_order' else service.update_automatic_preorder_lines
    return fn(store, user, 1, lines or [
        {'product_code': '00123', 'cartons': 4},
        {'product_code': '00456', 'cartons': 1},
    ], expected_token=token, delivery_date=date)


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
def test_date_and_lines_commit_together_and_reject_stale_save(store, kind):
    before = date_draft(store, kind)
    result = save(store, kind, before['email_send_token'])
    assert result['delivery_date'] == '1405/06/28'
    assert result['total_quantity'] == 60
    assert result['email_send_token'] != before['email_send_token']
    persisted = doc(store, kind)
    assert persisted['delivery_date'] == result['delivery_date']
    assert persisted['total_quantity'] == 60
    with pytest.raises(service.WarehouseAssistantError, match='تغییر کرده'):
        save(store, kind, before['email_send_token'], '1405/06/29')
    assert doc(store, kind)['delivery_date'] == '1405/06/28'


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
def test_invalid_date_or_late_write_failure_rolls_back_quantities(store, kind, monkeypatch):
    before = date_draft(store, kind)
    with pytest.raises(service.WarehouseAssistantError):
        save(store, kind, before['email_send_token'], '1405/07/31')
    assert doc(store, kind)['total_quantity'] == before['total_quantity']

    def failure(*args):
        raise RuntimeError('fixture disk failure')
    monkeypatch.setattr(dates, 'write_date', failure)
    with pytest.raises(RuntimeError, match='fixture disk failure'):
        save(store, kind, before['email_send_token'])
    after = doc(store, kind)
    assert after['total_quantity'] == before['total_quantity']
    assert after['delivery_date'] == before['delivery_date']


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
def test_approved_order_cannot_use_combined_edit(store, kind):
    date_draft(store, kind)
    transition(store, kind, 'approve')
    before = doc(store, kind)
    with pytest.raises(service.WarehouseAssistantError):
        save(store, kind, before['email_send_token'])
    assert doc(store, kind)['delivery_date'] == before['delivery_date']


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
def test_optional_draft_date_and_missing_token(store, kind):
    before = date_draft(store, kind)
    with pytest.raises(service.WarehouseAssistantError):
        save(store, kind, None)
    result = save(store, kind, before['email_send_token'], '')
    assert result['staff_delivery_date'] == ''
    assert result['total_quantity'] == 60


def test_manual_ownership_preserved(store):
    before = date_draft(store, 'supplier_order')
    with pytest.raises(service.WarehouseAssistantError, match='پیدا نشد'):
        save(store, 'supplier_order', before['email_send_token'], user='someone-else')


def test_http_models_accept_combined_payload():
    from app.routes.warehouse_assistant import AutomaticPreorderLinesRequest, ManualOrderEditRequest
    for model in (AutomaticPreorderLinesRequest, ManualOrderEditRequest):
        payload = model(lines=[{'product_code': '00123', 'cartons': 4}],
                        expected_token='a' * 64, delivery_date='1405/06/28')
        assert payload.delivery_date == '1405/06/28'
