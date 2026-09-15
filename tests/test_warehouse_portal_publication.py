import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from test_warehouse_supplier_portal import store
from test_warehouse_order_stages import doc
from app import warehouse_supplier_portal as portal, warehouse_assistant_service as service
from app import warehouse_portal_publication as publication, warehouse_order_sms as sms
from app.warehouse_order_delivery import update_delivery_date
from app.warehouse_portal_account_reset import reset_all


def publish(store,kind='supplier_order'):
    if kind=='automatic_preorder':
        with service.warehouse_connection(store) as conn:
            conn.execute('UPDATE warehouse_automatic_preorders SET source_supplier_order_id=NULL WHERE id=1')
    return portal.create_assignment(store,'buyer',document_kind=kind,document_id=1,
        requested_delivery_date='1405/06/25',expected_token=doc(store,kind)['email_send_token'],publish=True,portal_username='09120000000')


@pytest.mark.parametrize('kind',['supplier_order','automatic_preorder'])
def test_place_without_notification_then_withdraw_and_republish(store,kind):
    assignment=publish(store,kind)
    order=doc(store,kind)
    assert order['order_stage']=='sent' and order['dispatch_locked']
    assert assignment['can_withdraw'] and assignment['notification_status']=='not_sent'
    assert assignment['workflow_status']=='awaiting_supplier'
    assert portal.authenticate(store,'09120000000','1')[1]['must_change_password'] is False
    assert len(portal.list_assignments(store,supplier_key=assignment['supplier_key']))==1
    publication.withdraw(store,'buyer',assignment['id'],assignment['revision'])
    assert doc(store,kind)['order_stage']=='draft'
    assert portal.list_assignments(store,supplier_key=assignment['supplier_key'])==[]
    with pytest.raises(service.WarehouseAssistantError):
        publication.mark_viewed(store,assignment['id'],assignment['supplier_key'])
    second=publish(store,kind)
    assert second['publication_epoch']==2 and second['can_withdraw']
    with service.warehouse_connection(store) as conn:
        assert [r[0] for r in conn.execute('SELECT event FROM warehouse_portal_publication_events ORDER BY id')]==['published','withdrawn','published']


@pytest.mark.parametrize('kind',['supplier_order','automatic_preorder'])
def test_first_view_blocks_withdraw_and_cannot_be_spoofed_by_other_supplier(store,kind):
    assignment=publish(store,kind)
    with pytest.raises(service.WarehouseAssistantError):
        publication.mark_viewed(store,assignment['id'],'wrong-supplier')
    assert portal.get_assignment(store,assignment['id'],staff=True)['can_withdraw']
    publication.mark_viewed(store,assignment['id'],assignment['supplier_key'])
    seen=portal.get_assignment(store,assignment['id'],staff=True)
    assert seen['first_viewed_at'] and not seen['can_withdraw']
    with pytest.raises(service.WarehouseAssistantError):
        publication.withdraw(store,'buyer',assignment['id'],assignment['revision'])


def test_first_view_and_withdraw_are_mutually_exclusive(store):
    assignment=publish(store);barrier=Barrier(2)
    def run(view):
        barrier.wait()
        try:
            if view: publication.mark_viewed(store,assignment['id'],assignment['supplier_key'])
            else: publication.withdraw(store,'buyer',assignment['id'],assignment['revision'])
            return True
        except service.WarehouseAssistantError:return False
    with ThreadPoolExecutor(2) as pool:
        a=pool.submit(run,True);b=pool.submit(run,False)
        assert sorted([a.result(),b.result()])==[False,True]


def test_notification_failure_does_not_unpublish_and_new_epoch_can_notify_again(store,monkeypatch):
    assignment=publish(store)
    monkeypatch.setattr(sms,'_provider_config',lambda:{})
    def failed(*args):raise sms.SmsDeliveryFailure('failed','fixture')
    monkeypatch.setattr(sms,'_send_provider',failed)
    with pytest.raises(service.WarehouseAssistantError):portal.send_invitation(store,'buyer',assignment['id'],'09120000000')
    assert doc(store,'supplier_order')['order_stage']=='sent'
    monkeypatch.setattr(sms,'_send_provider',lambda *args:'fake-only')
    assert portal.send_invitation(store,'buyer',assignment['id'],'09120000000')['send_status']=='sent'
    publication.withdraw(store,'buyer',assignment['id'],assignment['revision'])
    second=publish(store)
    result=portal.send_invitation(store,'buyer',second['id'],'09120000000')
    assert result['external_delivery_performed'] and not result.get('already_sent')


def test_inflight_notification_blocks_withdraw(store,monkeypatch):
    assignment=publish(store)
    monkeypatch.setattr(sms,'_provider_config',lambda:{})
    def sending(*args):
        with pytest.raises(service.WarehouseAssistantError,match='در جریان'):
            publication.withdraw(store,'buyer',assignment['id'],assignment['revision'])
        return 'fake'
    monkeypatch.setattr(sms,'_send_provider',sending)
    portal.send_invitation(store,'buyer',assignment['id'],'09120000000')
    assert publication.withdraw(store,'buyer',assignment['id'],assignment['revision'])['withdrawn']


def test_notification_uses_selected_phone_account(store):
    portal.create_account(store,'buyer',username='09121111111',password='1',
        supplier_name='تأمین‌کننده نمونه',mobile='09121111111')
    assignment=publish(store)
    assert assignment['portal_account']['username']=='09120000000'
    assert portal.get_assignment(store,assignment['id'],staff=True)['portal_account']['mobile']=='09120000000'


def test_phone_collision_never_reassigns_supplier_account(store):
    portal.create_account(store,'buyer',username='09120000000',password='1',supplier_name='different',mobile='09120000000')
    with pytest.raises(service.WarehouseAssistantError,match='حساب دیگری'):
        publish(store)
    assert doc(store,'supplier_order')['order_stage']=='draft'


@pytest.mark.parametrize('kind',['supplier_order','automatic_preorder'])
def test_approved_date_edit_allowed_until_publication(store,kind):
    if kind=='automatic_preorder':
        with service.warehouse_connection(store) as conn:conn.execute('UPDATE warehouse_automatic_preorders SET source_supplier_order_id=NULL WHERE id=1')
    before=doc(store,kind)
    after=update_delivery_date(store,'buyer',kind,1,'1405/06/25',expected_token=before['email_send_token'])
    assert after['delivery_date']=='1405/06/25' and after['can_send_portal']
    assert after['email_send_token']!=before['email_send_token']
    publish(store,kind)
    with pytest.raises(service.WarehouseAssistantError):
        update_delivery_date(store,'buyer',kind,1,'1405/06/27',expected_token=doc(store,kind)['email_send_token'])


def test_explicit_account_reset_changes_login_revokes_session_and_keeps_orders(store):
    portal.create_account(store,'buyer',username='legacy.user',password='Fixture-only-123',supplier_name='supplier',mobile='09120000000')
    token,_=portal.authenticate(store,'legacy.user','Fixture-only-123')
    before=doc(store,'supplier_order')
    with pytest.raises(service.WarehouseAssistantError):reset_all(store,'buyer')
    assert reset_all(store,'buyer',confirmed=True)['accounts_updated']==1
    assert portal.authenticate(store,'legacy.user','Fixture-only-123') is None
    assert portal.authenticate(store,'09120000000','1')[1]['must_change_password'] is False
    assert portal.session_profile(store,token) is None
    assert doc(store,'supplier_order')['lines']==before['lines']


def test_account_reset_is_all_or_nothing_for_duplicate_phones(store):
    for username in ('first','second'):
        portal.create_account(store,'buyer',username=username,password='Fixture-only-123',supplier_name=username,mobile='09120000000')
    with pytest.raises(service.WarehouseAssistantError):reset_all(store,'buyer',confirmed=True)
    assert portal.authenticate(store,'first','Fixture-only-123')
    assert portal.authenticate(store,'second','Fixture-only-123')


def test_http_listing_is_not_a_view_but_detail_and_download_are(store,monkeypatch):
    from fastapi import FastAPI,Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_supplier_portal as routes
    from app.routes.dependencies import require_session_user
    app=FastAPI();app.state.settings=store
    async def identity(request:Request):request.state.username='buyer'
    app.dependency_overrides[require_session_user]=identity
    monkeypatch.setattr(routes,'_staff',lambda request:'buyer')
    app.include_router(routes.staff_router);app.include_router(routes.public_router)
    assignment=publish(store)
    with TestClient(app) as client:
        assert client.get('/supplier-portal/api/orders').status_code==401
        assert client.post('/supplier-portal/api/login',json={'username':'۰۹۱۲۰۰۰۰۰۰۰','password':'1'}).status_code==200
        listing=client.get('/supplier-portal/api/orders')
        assert listing.status_code==200 and listing.headers['cache-control']=='no-store'
        assert 'lines' not in listing.json()['orders'][0] and 'comments' not in listing.json()['orders'][0]
        assert portal.get_assignment(store,assignment['id'],staff=True)['can_withdraw']
        response=client.post(f"/warehouse-assistant/api/supplier-portal/orders/{assignment['id']}/withdraw",json={'confirmed':True,'expected_revision':assignment['revision']})
        assert response.status_code==200
        assert client.get(f"/supplier-portal/api/orders/{assignment['id']}").status_code==409
        assert client.get('/supplier-portal/api/orders').json()['orders']==[]
        second=publish(store)
        assert client.get(f"/supplier-portal/api/orders/{second['id']}/document.xlsx").status_code==200
        assert portal.get_assignment(store,second['id'],staff=True)['first_viewed_at']
        assert client.post(f"/warehouse-assistant/api/supplier-portal/orders/{second['id']}/withdraw",json={'confirmed':True,'expected_revision':second['revision']}).status_code==409
        assert client.post('/supplier-portal/api/change-password',json={'current_password':'1','new_password':'My-new-fixture-password'}).status_code==200
