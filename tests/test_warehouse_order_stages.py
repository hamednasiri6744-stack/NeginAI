"""Local-only workflow tests: all delivery providers are fakes."""
import pytest
from test_warehouse_supplier_portal import store
from app import warehouse_supplier_portal as portal, warehouse_assistant_service as service
from app import warehouse_order_sms as sms, warehouse_email as mail
from app.warehouse_manual_order_edit import update_lines
from app.warehouse_fulfillment import list_fulfillment_orders, supply_position


def setup_order(store, kind):
    if kind == 'automatic_preorder':
        with service.warehouse_connection(store) as conn:
            conn.execute('UPDATE warehouse_automatic_preorders SET source_supplier_order_id=NULL WHERE id=1')
    portal.create_account(store, 'buyer', username='supplier.workflow', password='Fixture-only-123',
                          supplier_name='تأمین‌کننده نمونه', mobile='09120000000')
    assignment = portal.create_assignment(store, 'buyer', document_kind=kind, document_id=1, requested_delivery_date='1405/06/25')
    return assignment


def doc(store, kind):
    return (service.get_supplier_order(store, 1, 'buyer', include_all=True) if kind == 'supplier_order'
            else service.get_automatic_preorder(store, 1))


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
@pytest.mark.parametrize('channel', ['sms', 'email'])
def test_approval_dispatch_and_confirmation_are_distinct_stages(store, monkeypatch, kind, channel):
    assignment = setup_order(store, kind)
    before = doc(store, kind)
    assert before['order_stage'] == 'draft' and before['can_revoke_approval']
    assert before['can_send_portal'] and not before['can_edit']
    with service.warehouse_connection(store) as conn:
        stock_before = supply_position(conn, 'karaj')[0]
    sent = []
    def provider(*args):
        claimed = doc(store, kind)
        assert claimed['dispatch_locked'] and not claimed['can_revoke_approval']
        assert claimed['order_stage'] == 'draft'  # Claim is not proof of delivery.
        with pytest.raises(service.WarehouseAssistantError):
            if kind == 'supplier_order':
                service.transition_supplier_order(store, 'buyer', 1, 'revoke_approval', include_all=True)
            else:
                service.transition_automatic_preorder(store, 'buyer', 1, 'revoke_approval')
        sent.append(args[-1])
        return 'fake-id'
    monkeypatch.setattr(sms, '_provider_config', lambda: {})
    monkeypatch.setattr(sms, '_send_provider', provider)
    monkeypatch.setattr(mail, '_config', lambda: {'username': 'sender@example.test'})
    monkeypatch.setattr(mail, '_smtp_send', provider)
    send = portal.send_invitation if channel == 'sms' else portal.send_email_invitation
    recipient = '09120000000' if channel == 'sms' else 'supplier@example.test'
    send(store, 'buyer', assignment['id'], recipient, expected_token=before['email_send_token'], expected_revision=assignment['revision'])
    assert len(sent) == 1
    content = sent[0] if channel == 'sms' else sent[0].get_content()
    assert '/supplier-portal' in content and '/warehouse-download/' not in content
    assert 'Fixture-only-123' not in content
    assert send(store, 'buyer', assignment['id'], recipient)['already_sent']
    assert len(sent) == 1
    current = doc(store, kind)
    assert current['order_stage'] == 'sent'
    assert not any(current[k] for k in ('can_edit','can_revoke_approval','can_delete','can_send_portal'))
    if kind == 'automatic_preorder':
        assert service.list_automatic_preorders(store) == []
    else:
        assert service.list_supplier_orders(store, 'buyer', stage='draft') == []
    assert list_fulfillment_orders(store, include_completed=True)[0]['order_stage'] == 'sent'
    profile = portal.authenticate(store, 'supplier.workflow', 'Fixture-only-123')[1]
    portal.save_response(store, profile, assignment['id'], expected_revision=assignment['revision'],
        proposed_delivery_date='1405/06/25', supplier_comment='', submit=True, confirmation_mode='confirm',
        lines=[{'product_code':'00123','proposed_cartons':2},{'product_code':'00456','proposed_cartons':1}])
    assert doc(store, kind)['order_stage'] == 'delivery'
    with service.warehouse_connection(store) as conn:
        assert supply_position(conn, 'karaj')[0] == stock_before


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
def test_supplier_changes_stay_sent_until_staff_accepts(store, kind):
    assignment = setup_order(store, kind)
    profile = portal.authenticate(store, 'supplier.workflow', 'Fixture-only-123')[1]
    proposal = portal.save_response(store, profile, assignment['id'], expected_revision=0,
        proposed_delivery_date='1405/06/27', supplier_comment='', submit=True,
        lines=[{'product_code':'00123','proposed_cartons':3},{'product_code':'00456','proposed_cartons':1}])
    assert doc(store, kind)['order_stage'] == 'sent'
    assert doc(store, kind)['lines'][0]['cartons'] == 2
    portal.decide(store, 'buyer', assignment['id'], decision='accept', expected_revision=proposal['revision'], manager_comment='test')
    assert doc(store, kind)['order_stage'] == 'delivery'


@pytest.mark.parametrize('outcome', ['failed', 'unknown'])
def test_failed_dispatch_never_moves_to_sent_and_unknown_locks_draft(store, monkeypatch, outcome):
    assignment = setup_order(store, 'supplier_order')
    monkeypatch.setattr(sms, '_provider_config', lambda: {})
    def fail(*args):
        raise sms.SmsDeliveryFailure(outcome, 'fake failure')
    monkeypatch.setattr(sms, '_send_provider', fail)
    with pytest.raises(service.WarehouseAssistantError):
        portal.send_invitation(store, 'buyer', assignment['id'], '09120000000')
    order = doc(store, 'supplier_order')
    assert order['order_stage'] == 'draft'
    assert order['dispatch_locked'] == (outcome == 'unknown')
    assert order['can_revoke_approval'] == (outcome == 'failed')


def test_manual_edit_requires_revoke_and_current_token_and_updates_totals(store):
    before = doc(store, 'supplier_order')
    lines = [{'product_code':'00123','cartons':4},{'product_code':'00456','cartons':0}]
    with pytest.raises(service.WarehouseAssistantError):
        update_lines(store, 'buyer', 1, lines, expected_token=before['email_send_token'])
    current = service.transition_supplier_order(store, 'buyer', 1, 'revoke_approval')
    with pytest.raises(service.WarehouseAssistantError, match='تغییر کرده'):
        update_lines(store, 'buyer', 1, lines, expected_token=before['email_send_token'])
    after = update_lines(store, 'buyer', 1, lines, expected_token=current['email_send_token'])
    assert after['total_quantity'] == 48 and after['estimated_value'] == 3360
    assert len(after['lines']) == 1 and after['can_edit']
    with pytest.raises(service.WarehouseAssistantError):
        update_lines(store, 'another-user', 1, lines, expected_token=after['email_send_token'])


def test_stale_assignment_cannot_send_after_revoke_or_edit(store, monkeypatch):
    assignment = setup_order(store, 'supplier_order')
    monkeypatch.setattr(sms, '_provider_config', lambda: {})
    monkeypatch.setattr(sms, '_send_provider', lambda *a: pytest.fail('stale send reached provider'))
    current = service.transition_supplier_order(store, 'buyer', 1, 'revoke_approval')
    with pytest.raises(service.WarehouseAssistantError, match='ابتدا سفارش'):
        portal.send_invitation(store, 'buyer', assignment['id'], '')
    update_lines(store, 'buyer', 1, [{'product_code':'00123','cartons':4},{'product_code':'00456','cartons':1}], expected_token=current['email_send_token'])
    service.transition_supplier_order(store, 'buyer', 1, 'approve')
    with pytest.raises(service.WarehouseAssistantError, match='یکسان نیست'):
        portal.send_invitation(store, 'buyer', assignment['id'], '')
