import pytest
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_balance_proposals import preview, accept
from app import warehouse_transfer_documents as documents, warehouse_rebalancing as ledger
from app import warehouse_assistant_service as service


def staged(b):
    b.change("UPDATE warehouse_snapshot_items SET stock=240 WHERE warehouse_code='tehran'")
    accept(b,preview(b),1,key='bulk-one')
    accept(b,preview(b),1,key='bulk-two')
    return sorted(r['id'] for r in ledger.list_requests(b.settings,'test-user'))


@pytest.mark.parametrize('action,table',[('delete','warehouse_rebalance_deletions'),('revoke','warehouse_rebalance_revocations')])
def test_bulk_atomic_idempotent_and_releases_selected_reservations(balance,action,table):
    ids=staged(balance)
    result=documents.mutate_pending_batch(balance.settings,'test-user',ids,action=action)
    assert result['affected_count']==2
    assert documents.mutate_pending_batch(balance.settings,'test-user',ids,action=action)['affected_count']==0
    assert ledger.list_requests(balance.settings,'test-user')==[]
    with service.warehouse_connection(balance.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==2
        assert ledger.reservations(c,'tehran')[1]=={}
        assert ledger.reservations(c,'karaj')[0]=={}
        assert c.execute('SELECT COUNT(*) FROM warehouse_rebalance_requests').fetchone()[0]==2
    balance.transport.assert_not_called()


@pytest.mark.parametrize('action',['delete','revoke'])
def test_issued_selection_blocks_whole_batch(balance,action):
    ids=staged(balance)
    documents.create_documents(balance.settings,'test-user',[ids[-1]],request_id='issued')
    with pytest.raises(service.WarehouseAssistantError):
        documents.mutate_pending_batch(balance.settings,'test-user',ids,action=action)
    assert len(ledger.list_requests(balance.settings,'test-user'))==2


@pytest.mark.parametrize('invalid',[[],[True],[0],[1,1],[1.5],[999],list(range(1,502))])
def test_bulk_invalid_selection_does_not_mutate(balance,invalid):
    staged(balance)
    with pytest.raises(service.WarehouseAssistantError):
        documents.mutate_pending_batch(balance.settings,'test-user',invalid,action='delete')
    assert len(ledger.list_requests(balance.settings,'test-user'))==2


def test_bulk_owner_and_action_validation(balance):
    ids=staged(balance)
    for who,action in [('another-user','delete'),('test-user','invalid')]:
        with pytest.raises(service.WarehouseAssistantError):
            documents.mutate_pending_batch(balance.settings,who,ids,action=action)
    assert documents.mutate_pending_batch(balance.settings,'Admin',ids,action='revoke',include_all=True)['affected_count']==2


def test_approval_keeps_actual_selected_coverage_not_maximum_proposal(balance):
    p=preview(balance);o=p['lines'][0]
    accept(balance,p,1)
    row=ledger.list_requests(balance.settings,'test-user')[0]
    context=row['approval_context']
    assert context['source_position']==o['source_position']
    assert context['destination_position']==o['destination_position']
    assert context['source_after_days']==pytest.approx((o['source_position']-row['quantity'])/o['source_daily_demand'])
    assert context['destination_after_days']==pytest.approx((o['destination_position']+row['quantity'])/o['destination_daily_demand'])
    balance.change('UPDATE warehouse_snapshot_items SET stock=999,period_out=1')
    assert ledger.list_requests(balance.settings,'test-user')[0]['approval_context']==context
    with service.warehouse_connection(balance.settings) as c:
        c.execute('DELETE FROM warehouse_rebalance_approval_context')
    assert ledger.list_requests(balance.settings,'test-user')[0]['approval_context'] is None


def test_bulk_route_auth_schema_and_real_transaction(balance):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from app.routes import warehouse_assistant as routes
    ids=staged(balance)
    app=FastAPI();app.state.settings=balance.settings;app.include_router(routes.router)
    endpoint='/warehouse-assistant/api/interwarehouse/requests/batch'
    with TestClient(app) as client:
        assert client.post(endpoint,json={'request_ids':ids,'action':'delete'}).status_code==401
        app.dependency_overrides[routes.require_session_user]=lambda:'test-user'
        with patch.object(routes,'_require',return_value='test-user') as permission,patch.object(routes,'_is_admin',return_value=False):
            for payload in [{'request_ids':[True],'action':'delete'},{'request_ids':ids,'action':'wrong'}]:
                assert client.post(endpoint,json=payload).status_code==422
            response=client.post(endpoint,json={'request_ids':ids,'action':'delete'})
            assert response.status_code==200 and response.json()['affected_count']==2
            assert permission.call_args.args[1]=='warehouse.order.draft'
