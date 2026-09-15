import pytest
from app import warehouse_purchase_contracts as pc
from test_warehouse_purchase_groups import store, rule


def test_new_draft_can_only_add_uncovered_goods_in_its_warehouse(store):
    pc.save_contract(store,'tester',rule(['A'],stock_id=1))
    with pytest.raises(pc.ContractError,match='A'):
        pc.save_contract(store,'tester',rule(['A','B'],stock_id=1,status='draft'))
    other=pc.save_contract(store,'tester',rule(['A'],stock_id=2,status='draft'))
    assert other['stock_id']==2


def test_membership_edit_preserves_terms_and_releases_removed_goods(store):
    original=pc.save_contract(store,'tester',rule(['A','B'],stock_id=1))
    updated=pc.update_members(store,'tester',original['id'],1,['A','B','C'],{'A':'1405/06/10'})
    assert updated['product_codes']==['A','B','C'] and updated['revision']==2
    assert updated['product_end_dates']=={'A':'1405/06/10'}
    for key in ['supplier_id','stock_id','start_date','end_date','discount_percent','tail_discount','deduction_group']:
        assert updated[key]==original[key]
    assert pc.save_contract(store,'tester',rule(['A'],stock_id=1,start_date='1405/06/11'))
    with pytest.raises(pc.ContractError,match='هم‌زمان'):
        pc.update_members(store,'tester',original['id'],1,['B'])


def test_concurrent_assignment_is_rechecked_at_membership_save(store):
    first=pc.save_contract(store,'tester',rule(['A'],stock_id=1))
    pc.save_contract(store,'tester',rule(['B'],stock_id=1))
    with pytest.raises(pc.ContractError,match='B'):
        pc.update_members(store,'tester',first['id'],1,['A','B'])
    assert next(r for r in pc.list_contracts(store) if r['id']==first['id'])['product_codes']==['A']


def test_shared_contract_blocks_adding_product_in_other_warehouse(store):
    pc.save_contract(store,'tester',rule(['A'],stock_id=None))
    with pytest.raises(pc.ContractError,match='A'):
        pc.save_contract(store,'tester',rule(['A'],stock_id=2,status='draft'))


def test_expired_contract_does_not_prevent_next_period(store):
    pc.save_contract(store,'tester',rule(['A'],stock_id=1))
    assert pc.save_contract(store,'tester',rule(['A'],stock_id=1,start_date='1405/06/16',end_date=''))


def test_members_api_protects_permissions_revision_and_commercial_terms(store,monkeypatch):
    from test_warehouse_purchase_contracts import HEADERS
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI(); app.state.settings=store
    async def identity(request:Request):request.state.username=request.headers.get('X-Test-User','editor')
    app.dependency_overrides[routes.require_session_user]=identity
    monkeypatch.setattr(routes,'_capabilities',lambda request,username: {'warehouse.assistant.view'} | ({'warehouse.order.draft'} if username=='editor' else set()))
    app.include_router(routes.router)
    original=pc.save_contract(store,'tester',rule(['A'],stock_id=1))
    url='/warehouse-assistant/api/purchase-contracts/'+original['id']+'/members'
    payload=dict(expected_revision=1,product_codes=['A','B'])
    with TestClient(app) as client:
        for headers in [{},dict(HEADERS,Origin='https://untrusted.example'),dict(HEADERS,**{'X-Test-User':'viewer'})]:
            assert client.put(url,headers=headers,json=payload).status_code==403
        assert client.put(url,headers=HEADERS,json=dict(payload,discount_percent='90')).status_code==422
        result=client.put(url,headers=HEADERS,json=payload)
        assert result.status_code==200
        assert result.json()['product_codes']==['A','B']
        assert result.json()['discount_percent']==original['discount_percent']
        assert client.put(url,headers=HEADERS,json=payload).status_code==409
        ended=client.put(url,headers=HEADERS,json=dict(expected_revision=2,product_codes=['A','B'],product_end_dates={'A':'1405/06/10'}))
        assert ended.status_code==200 and ended.json()['product_end_dates']=={'A':'1405/06/10'}
        history=client.get(url+'/A/history').json()['history']
        assert history[0]['member_end_date']=='1405/06/10' and history[0]['actor']=='editor'


def test_end_contract_api_checks_permissions_and_history(store,monkeypatch):
    from fastapi import FastAPI,Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    from test_warehouse_purchase_contracts import HEADERS
    app=FastAPI();app.state.settings=store
    async def identity(request:Request):request.state.username=request.headers.get('X-Test-User','editor')
    app.dependency_overrides[routes.require_session_user]=identity
    monkeypatch.setattr(routes,'_capabilities',lambda request,username: {'warehouse.assistant.view'} | ({'warehouse.order.draft'} if username=='editor' else set()))
    app.include_router(routes.router)
    r=pc.save_contract(store,'tester',rule(['A','B']))
    url='/warehouse-assistant/api/purchase-contracts/'+r['id']+'/end'
    payload=dict(expected_revision=1,end_date='1405/06/10')
    with TestClient(app) as client:
        assert client.put(url,json=payload).status_code==403
        assert client.put(url,headers=dict(HEADERS,**{'X-Test-User':'viewer'}),json=payload).status_code==403
        assert client.put(url,headers=HEADERS,json=dict(payload,discount_percent='50')).status_code==422
        assert client.put(url,headers=HEADERS,json=dict(payload,end_date='1405/05/31')).status_code==422
        ended=client.put(url,headers=HEADERS,json=payload)
        assert ended.status_code==200 and ended.json()['end_date']=='1405/06/10'
        assert client.put(url,headers=HEADERS,json=payload).status_code==409
        assert len(pc.history(store,r['id']))==2
