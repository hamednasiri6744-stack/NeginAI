"""Delivery commitments tested against disposable SQLite orders; no real senders."""
import pytest
from test_warehouse_supplier_portal import store
from test_warehouse_order_stages import setup_order, doc
from app import warehouse_assistant_service as service, warehouse_supplier_portal as portal
from app.warehouse_order_delivery import update_delivery_date, clean_delivery_date
from app.warehouse_fulfillment import list_fulfillment_orders


def transition(store, kind, action):
    fn = service.transition_supplier_order if kind == 'supplier_order' else service.transition_automatic_preorder
    return fn(store, 'buyer', 1, action)


def date_draft(store, kind):
    if kind == 'automatic_preorder':
        with service.warehouse_connection(store) as conn:
            conn.execute('UPDATE warehouse_automatic_preorders SET source_supplier_order_id=NULL WHERE id=1')
    current = transition(store, kind, 'revoke_approval')
    return update_delivery_date(store, 'buyer', kind, 1, '۱۴۰۵/۰۶/۲۵', expected_token=current['email_send_token'])


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
def test_draft_date_persists_changes_token_and_is_editable_while_approved(store, kind):
    before = doc(store, kind)
    after = date_draft(store, kind)
    assert after['delivery_date'] == after['staff_delivery_date'] == '1405/06/25'
    assert doc(store, kind)['delivery_date'] == '1405/06/25'
    assert after['email_send_token'] != before['email_send_token']
    changed = update_delivery_date(store, 'buyer', kind, 1, '1405/06/26', expected_token=after['email_send_token'])
    assert changed['email_send_token'] != after['email_send_token']
    with pytest.raises(service.WarehouseAssistantError, match='تغییر کرده'):
        update_delivery_date(store, 'buyer', kind, 1, '1405/06/27', expected_token=after['email_send_token'])
    transition(store, kind, 'approve')
    update_delivery_date(store, 'buyer', kind, 1, '1405/06/28', expected_token=doc(store, kind)['email_send_token'])
    assert doc(store, kind)['delivery_date'] == '1405/06/28'


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
@pytest.mark.parametrize('decision', ['accept', 'reject', 'changes_requested', 'unchanged'])
def test_supplier_date_is_not_effective_before_staff_acceptance(store, kind, decision):
    date_draft(store, kind)
    transition(store, kind, 'approve')
    assignment = setup_order(store, kind)
    profile = portal.authenticate(store, 'supplier.workflow', 'Fixture-only-123')[1]
    proposal = portal.save_response(store, profile, assignment['id'], expected_revision=assignment['revision'],
        proposed_delivery_date='1405/06/25' if decision == 'unchanged' else '1405/06/27',
        supplier_comment='', submit=True,
        lines=[{'product_code':'00123','proposed_cartons':2},{'product_code':'00456','proposed_cartons':1}])
    current = doc(store, kind)
    assert current['delivery_date'] == '1405/06/25'
    if decision == 'unchanged':
        assert current['pending_delivery_date'] == ''
        assert current['order_stage'] == 'delivery'
        return
    assert current['pending_delivery_date'] == '1405/06/27'
    assert current['order_stage'] == 'sent'
    portal.decide(store, 'buyer', assignment['id'], decision=decision, expected_revision=proposal['revision'], manager_comment='fixture')
    expected = '1405/06/27' if decision == 'accept' else '1405/06/25'
    assert doc(store, kind)['delivery_date'] == expected
    assert doc(store, kind)['requested_delivery_date'] == '1405/06/25'
    assert doc(store, kind)['pending_delivery_date'] == ''
    if decision == 'accept':
        assert list_fulfillment_orders(store, include_completed=True)[0]['delivery_date'] == expected
    with pytest.raises(service.WarehouseAssistantError):
        update_delivery_date(store, 'buyer', kind, 1, '1405/06/28', expected_token=doc(store, kind)['email_send_token'])


def test_date_edit_ownership_and_manual_projection(store):
    current = date_draft(store, 'supplier_order')
    with pytest.raises(service.WarehouseAssistantError, match='پیدا نشد'):
        update_delivery_date(store, 'other', 'supplier_order', 1, '1405/06/28', expected_token=current['email_send_token'])
    transition(store, 'supplier_order', 'approve')
    projected = service.get_automatic_preorder(store, 1)
    assert projected['delivery_date'] == '1405/06/25'
    with pytest.raises(service.WarehouseAssistantError):
        update_delivery_date(store, 'buyer', 'automatic_preorder', 1, '1405/06/28', expected_token=projected['email_send_token'])


def test_assignment_date_cannot_override_approved_staff_date(store):
    date_draft(store, 'supplier_order')
    transition(store, 'supplier_order', 'approve')
    with pytest.raises(service.WarehouseAssistantError, match='همان تاریخ'):
        portal.create_assignment(store, 'buyer', document_kind='supplier_order', document_id=1, requested_delivery_date='1405/06/26')


def test_stale_assignment_cannot_send_after_date_edit(store, monkeypatch):
    assignment = setup_order(store, 'supplier_order')
    date_draft(store, 'supplier_order')
    current = doc(store, 'supplier_order')
    update_delivery_date(store, 'buyer', 'supplier_order', 1, '1405/06/28', expected_token=current['email_send_token'])
    transition(store, 'supplier_order', 'approve')
    with pytest.raises(service.WarehouseAssistantError, match='تاریخ کارتابل'):
        portal.send_invitation(store, 'buyer', assignment['id'], '')


@pytest.mark.parametrize('invalid', ['1405/07/31','1405/13/01','1405/00/02','abcd','1405/12/30',''])
def test_invalid_calendar_days_rejected(invalid):
    with pytest.raises(service.WarehouseAssistantError):
        clean_delivery_date(invalid)


def test_normalizes_persian_and_arabic_digits():
    assert clean_delivery_date('۱۴۰۵/۰۶/۲۵') == '1405/06/25'
    assert clean_delivery_date('١٤٠٥/٠٦/٢٥') == '1405/06/25'
