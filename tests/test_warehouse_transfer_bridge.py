import json
from unittest.mock import Mock
import pytest
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_balance_proposals import preview, accept
from app import warehouse_rebalancing as ledger
from app import warehouse_transfer_documents as documents
from app import warehouse_transfer_bridge as bridge
from app import warehouse_assistant_service as service


@pytest.fixture
def credit(balance,monkeypatch):
    accept(balance,preview(balance),1)
    ident=ledger.list_requests(balance.settings,'test-user')[0]['id']
    doc=documents.create_documents(balance.settings,'test-user',[ident],request_id='credit-fixture')['documents'][0]['id']
    balance.settings.varanegar_transfer_bridge_enabled=True
    balance.settings.varanegar_transfer_commit_enabled=True
    remote=Mock(return_value=dict(BridgeStatus='ready',ValidationToken='sql-token'))
    monkeypatch.setattr(bridge,'_remote',remote)
    return balance,doc,ident,remote


def request(credit):
    b,doc,_,remote=credit
    p=bridge.preview(b.settings,'test-user',doc)
    return bridge.SubmitCredit(preview_token=p['preview_token'],validation_token=p['validation_token'],confirmed=True)


def sent():return dict(BridgeStatus='sent',VocherId=501,VocherNo=71,AccYear=1405,Confirmed=1)


def test_preview_readonly_uses_persisted_route_date_quantity(credit):
    b,doc,_,remote=credit
    p=bridge.preview(b.settings,'test-user',doc)
    assert p['payload']['source_stock_ref']==2 and p['payload']['destination_stock_ref']==1
    assert p['payload']['lines']==[dict(product_code='00123',quantity='12.0')]
    assert remote.call_args.args[-1] is False
    with service.warehouse_connection(b.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM warehouse_transfer_bridge_intents').fetchone()[0]==0


def test_confirmed_submission_persists_intent_before_network_and_retries_same_bytes(credit):
    b,doc,ident,remote=credit;req=request(credit)
    def lost(*args):
        with service.warehouse_connection(b.settings) as c:
            assert c.execute('SELECT status FROM warehouse_transfer_bridge_intents').fetchone()[0]=='pending'
        with pytest.raises(service.WarehouseAssistantError):documents.delete_document(b.settings,'test-user',doc)
        raise OSError('secret connection details must not leak')
    remote.side_effect=lost
    result=bridge.submit(b.settings,'test-user',doc,req)
    assert result['status']=='pending' and 'secret' not in str(result)
    original=remote.call_args.args
    bridge.submit(b.settings,'test-user',doc,req)
    assert remote.call_count==2  # preview plus one initial submit
    remote.side_effect=None;remote.return_value=sent()
    assert bridge.retry(b.settings,'test-user',doc)['status']=='sent'
    assert original==remote.call_args.args
    assert bridge.submit(b.settings,'test-user',doc,req)['status']=='sent'
    with service.warehouse_connection(b.settings) as c:
        assert ledger.reservations(c,'tehran')[1]=={'00123':12}
        assert ledger.reservations(c,'karaj')[0]=={'00123':12}


def test_unconfirmed_remote_result_stays_unknown_and_locked(credit):
    b,doc,_,remote=credit;req=request(credit)
    remote.return_value=dict(sent(),Confirmed=0)
    assert bridge.submit(b.settings,'test-user',doc,req)['status']=='pending'
    with pytest.raises(service.WarehouseAssistantError):documents.delete_document(b.settings,'test-user',doc)


def test_rejected_attempt_can_be_rechecked_and_archived(credit):
    b,doc,_,remote=credit;req=request(credit)
    remote.return_value=dict(BridgeStatus='rejected',Message='native rollback')
    assert bridge.submit(b.settings,'test-user',doc,req)['status']=='rejected'
    remote.return_value=dict(BridgeStatus='ready',ValidationToken='new-token')
    new=request(credit);remote.return_value=sent()
    assert bridge.submit(b.settings,'test-user',doc,new)['status']=='sent'
    with service.warehouse_connection(b.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM warehouse_transfer_bridge_attempts').fetchone()[0]==1
    with pytest.raises(service.WarehouseAssistantError):documents.delete_document(b.settings,'test-user',doc)


def test_rejected_document_can_be_deleted_without_releasing_staging_reservations(credit):
    b,doc,_,remote=credit;req=request(credit);remote.return_value=dict(BridgeStatus='rejected')
    bridge.submit(b.settings,'test-user',doc,req)
    documents.delete_document(b.settings,'test-user',doc)
    assert ledger.list_requests(b.settings,'test-user')[0]['issued_document_id'] is None


def test_auth_flags_confirmation_and_stale_preview_block_writes(credit):
    b,doc,_,remote=credit;req=request(credit)
    with pytest.raises(service.WarehouseAssistantError):bridge.status(b.settings,'other',doc)
    with pytest.raises(service.WarehouseAssistantError):bridge.submit(b.settings,'other',doc,req)
    req.confirmed=False
    with pytest.raises(service.WarehouseAssistantError):bridge.submit(b.settings,'test-user',doc,req)
    req.confirmed=True;req.preview_token='0'*64
    with pytest.raises(service.WarehouseAssistantError):bridge.submit(b.settings,'test-user',doc,req)
    b.settings.varanegar_transfer_commit_enabled=False
    with pytest.raises(service.WarehouseAssistantError):bridge.submit(b.settings,'test-user',doc,req)
    assert remote.call_count==1


def test_pending_and_sent_forbid_preview_or_reflection_override(credit):
    b,doc,ident,remote=credit;req=request(credit);remote.side_effect=TimeoutError()
    bridge.submit(b.settings,'test-user',doc,req)
    with pytest.raises(service.WarehouseAssistantError):bridge.preview(b.settings,'test-user',doc)
    with pytest.raises(service.WarehouseAssistantError):
        ledger.reflect_in_stock(b.settings,'test-user',ident,snapshot_id=2,source_document='1',destination_document='2',confirmed=True)


def test_credit_endpoints_require_both_capabilities(credit):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    from unittest.mock import patch
    b,doc,_,remote=credit
    app=FastAPI();app.state.settings=b.settings;app.include_router(routes.router)
    with TestClient(app) as client:
        root=f'/warehouse-assistant/api/interwarehouse/documents/{doc}/credit'
        assert client.get(root).status_code==401
        assert client.post(root+'/preview').status_code==401
        app.dependency_overrides[routes.require_session_user]=lambda:'test-user'
        with patch.object(routes,'_require',return_value='test-user') as permissions,patch.object(routes,'_is_admin',return_value=False):
            assert client.post(root+'/preview').status_code==200
            assert [call.args[1] for call in permissions.call_args_list]==['warehouse.order.draft','warehouse.receipt.transfer']
