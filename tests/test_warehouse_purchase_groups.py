from types import SimpleNamespace
import pytest
from app import warehouse_purchase_contracts as pc


@pytest.fixture
def store(tmp_path):
    settings = SimpleNamespace(sqlite_path=tmp_path/'state.db')
    pc.replace_catalog(settings, [dict(product_code=code, product_name=code, goods_id=i,
        manufacturer_id=1, manufacturer='Maker', brand_id=brand, brand=str(brand),
        group_id=group, group_name=str(group), supplier_id=17, supplier='Supplier',
        tax_rate=10, tax_status='known') for i, (code, brand, group) in
        enumerate([('A', 1, 10), ('B', 1, 20), ('C', 2, 20)], 1)])
    return settings


def rule(codes, **changes):
    return dict(dict(supplier_id=17, scope='collection', product_codes=codes,
        title='Agreement', start_date='1405/06/01', end_date='1405/06/15', status='active',
        basis='manufacturer', includes_tax=True, adjustment_percent='0',
        discount_percent='18', tail_discount_percent='8.95'), **changes)


def test_one_contract_owns_multiple_products_and_resolves_same_identity(store):
    r=pc.save_contract(store,'tester',rule(['A','B']))
    assert r['product_codes']==['A','B']
    items=pc.resolve_products(store,17,'1405/06/10')['items']
    assert [i['contract']['id'] if i['contract'] else None for i in items]==[r['id'],r['id'],None]
    assert len(pc.list_contracts(store))==1


def test_cross_brand_group_intersection_is_rejected_atomically(store):
    pc.save_contract(store,'tester',rule(['A','B']))
    with pytest.raises(pc.ContractError,match='B'):
        pc.save_contract(store,'tester',rule(['B','C'],title='Group 20'))
    assert len(pc.list_contracts(store))==1
    next_period=pc.save_contract(store,'tester',rule(['B','C'],start_date='1405/06/16',end_date=''))
    assert pc.resolve_products(store,17,'1405/06/16')['items'][1]['contract']['id']==next_period['id']


def test_edit_members_dates_history_and_concurrency(store):
    r=pc.save_contract(store,'tester',rule(['A','B']))
    updated=pc.update_members(store,'tester',r['id'],r['revision'],['A','B','C'],{'A':'1405/06/09'})
    assert updated['revision']==2
    assert pc.resolve_products(store,17,'1405/06/10')['items'][0]['contract'] is None
    assert pc.history(store,r['id'])[1]['contract']['product_codes']==['A','B']
    with pytest.raises(pc.ContractError,match='هم‌زمان'):
        pc.save_contract(store,'tester',rule(['A']),r['id'],1)


@pytest.mark.parametrize('codes',[[],['A','A'],['other-supplier'],[1]])
def test_invalid_members_are_rejected(store,codes):
    with pytest.raises(pc.ContractError):pc.save_contract(store,'tester',rule(codes))


def test_draft_cannot_activate_overlapping_members(store):
    draft=pc.save_contract(store,'tester',rule(['A','C'],status='draft'))
    pc.save_contract(store,'tester',rule(['A']))
    with pytest.raises(pc.ContractError):pc.save_contract(store,'tester',rule(['A','C']),draft['id'],1)
    assert pc.list_contracts(store)[0]['status'] in ('draft','active')
    assert next(r for r in pc.list_contracts(store) if r['id']==draft['id'])['status']=='draft'


def test_group_migration_preserves_calculation_and_original_history(store):
    old=[]
    for code in ['A','B']:
        old.append(pc.save_contract(store,'original',dict(rule([code]),scope='item',product_code=code)))
    before=[pc.calculate(i['contract'],price='1100000',quantity='1',tax_rate=10)
            for i in pc.resolve_products(store,17,'1405/06/10')['items'] if i['contract']]
    result=pc.migrate_supplier_contracts(store)
    assert result['migrated_rules']==2
    groups=[r for r in pc.list_contracts(store) if not r.get('materialized')]
    assert sum(len(r['product_codes']) for r in groups)==2
    after=[pc.calculate(i['contract'],price='1100000',quantity='1',tax_rate=10)
           for i in pc.resolve_products(store,17,'1405/06/10')['items'] if i['contract']]
    assert before==after
    for r in old:assert pc.history(store,r['id'])[-1]['contract']==r
    assert pc.migrate_supplier_contracts(store)['migrated_rules']==0
    with pytest.raises(pc.ContractError):
        pc.save_contract(store,'stale-client',dict(rule(['C']),scope='item',product_code='C'))


def test_supplier_selection_does_not_require_manufacturer(store):
    selection=pc.selection(store,None,supplier_id=17)
    assert [i['product_code'] for i in selection['items']]==['A','B','C']


def add_supply_scope(store):
    with pc.connect(store) as c:
        c.execute('CREATE TABLE warehouse_supply_scope (warehouse_code TEXT,supplier TEXT,brand TEXT,enabled INTEGER,source_supplier_refs_json TEXT)')
        c.executemany('INSERT INTO warehouse_supply_scope VALUES (?,?,?,?,?)',[
            ('karaj','Maker','1',1,'["17"]'),('tehran','Maker','2',1,'["17"]'),
            ('gilan','Maker','1',0,'["17"]'),('tehran','Maker','1',1,'["99"]')])


def test_supplier_overview_counts_only_enabled_brand_and_supplier_scope(store,monkeypatch):
    monkeypatch.setattr(pc,'jalali_business_date',lambda:'1405/06/10')
    pc.save_contract(store,'tester',rule(['A']))
    add_supply_scope(store)
    supplier=pc.catalog(store)['suppliers'][0]
    assert supplier['active_warehouse_count']==2
    assert [(w['active'],w['product_count'],w['uncovered_product_count']) for w in supplier['warehouses']]==[(True,2,1),(True,1,1),(False,0,0)]
    for stock,codes in [(1,['A','B']),(2,['C']),(9,[])]:
        data=pc.resolve_products(store,17,'1405/06/10',stock_id=stock,include_prices=False,supply_only=True)
        assert [i['product_code'] for i in data['items']]==codes
        summary=next(w for w in supplier['warehouses'] if w['id']==stock)
        assert sum(i['contract'] is None for i in data['items'])==summary['uncovered_product_count']
    selection=pc.selection(store,None,supplier_id=17)['items']
    assert [i['eligible_stock_ids'] for i in selection]==[[1],[1],[2]]
    with pytest.raises(pc.ContractError,match='تأمین مجاز'):
        pc.save_contract(store,'tester',rule(['B'],stock_id=2))
    pc.save_contract(store,'tester',rule(['B'],stock_id=1))


def test_missing_supply_scope_is_unknown_not_three_active_warehouses(store):
    catalog=pc.catalog(store)
    assert catalog['supply_scope_known'] is False
    assert catalog['suppliers'][0]['active_warehouse_count']==0
    with pytest.raises(pc.ContractError,match='دامنه'):
        pc.resolve_products(store,17,'1405/06/10',stock_id=1,include_prices=False,supply_only=True)


def test_same_goods_have_independent_warehouse_contracts_and_coverage(store,monkeypatch):
    monkeypatch.setattr(pc,'jalali_business_date',lambda:'1405/06/10')
    first=pc.save_contract(store,'tester',rule(['A','B'],stock_id=1,discount_percent='10'))
    second=pc.save_contract(store,'tester',rule(['A'],stock_id=2,discount_percent='25'))
    for stock,expected,missing in [(1,first,1),(2,second,2),(9,None,3)]:
        items=pc.resolve_products(store,17,'1405/06/10',stock_id=stock,include_prices=False)['items']
        assert items[0]['contract']==expected
        assert pc.catalog(store,stock)['suppliers'][0]['uncovered_product_count']==missing
    with pytest.raises(pc.ContractError,match='انبار'):
        pc.resolve_products(store,17,'1405/06/10')
    with pytest.raises(pc.ContractError,match='انبار'):
        pc.save_contract(store,'tester',rule(['A'],stock_id=1))
    with pytest.raises(pc.ContractError,match='انبار'):
        pc.save_contract(store,'tester',rule(['A'],stock_id=None))
    pc.save_contract(store,'tester',rule(['A'],stock_id=1,start_date='1405/06/16',end_date=''))


def test_existing_common_contract_remains_shared_and_scope_edits_keep_history(store):
    common=pc.save_contract(store,'tester',rule(['A']))
    for stock in (1,2,9):
        assert pc.resolve_products(store,17,'1405/06/10',stock_id=stock,include_prices=False)['items'][0]['contract']['id']==common['id']
    with pytest.raises(pc.ContractError):pc.save_contract(store,'tester',rule(['A'],stock_id=2))
    scoped=pc.save_contract(store,'tester',rule(['A'],stock_id=1),common['id'],1)
    pc.save_contract(store,'tester',rule(['A'],stock_id=2))
    assert pc.history(store,common['id'])[-1]['contract'].get('stock_id') is None
    with pytest.raises(pc.ContractError):pc.save_contract(store,'tester',rule(['A']),scoped['id'],2)
    with pytest.raises(pc.ContractError):pc.save_contract(store,'tester',rule(['A'],stock_id=None),scoped['id'],2)
    assert pc.list_contracts(store)[0]['revision'] in (1,2)


@pytest.mark.parametrize('stock',[0,3,-1,True,'2',2.0,[],{}])
def test_invalid_warehouse_scope_rejected(store,stock):
    with pytest.raises(pc.ContractError):pc.save_contract(store,'tester',rule(['A'],stock_id=stock))
    assert pc.list_contracts(store)==[]


def test_inventory_price_requirements_follow_each_warehouse(store):
    pc.save_contract(store,'tester',rule(['A'],stock_id=1,basis='manufacturer'))
    pc.save_contract(store,'tester',rule(['A'],stock_id=2,basis='consumer'))
    rows=[dict(product_code='A',warehouse_code=code,manufacturer_price=0,consumer_price=100) for code in ('karaj','tehran','gilan')]
    with pc.connect(store) as c:result=pc.inventory_contract_price_status(c,rows,'1405/06/10')
    assert result[('karaj','A')]['status']=='missing'
    assert result[('karaj','A')]['required_bases']==['manufacturer']
    assert result[('tehran','A')]['status']=='ready'
    assert result[('tehran','A')]['required_bases']==['consumer']
    assert result[('gilan','A')]['status']=='not_required'


@pytest.mark.parametrize('today,covered',[
    ('1405/05/31',0),('1405/06/01',1),('1405/06/15',1),('1405/06/16',1),('1405/07/01',1)])
def test_supplier_coverage_uses_current_validity_and_includes_announcement(store,monkeypatch,today,covered):
    monkeypatch.setattr(pc,'jalali_business_date',lambda:today)
    pc.save_contract(store,'tester',rule(['A'],basis='announcement'))
    pc.save_contract(store,'tester',rule(['B'],status='draft'))
    pc.save_contract(store,'tester',rule(['C'],start_date='1405/06/16',end_date=''))
    data=pc.catalog(store);supplier=data['suppliers'][0]
    assert data['today']==today
    assert supplier['covered_product_count']==covered
    assert supplier['uncovered_product_count']==3-covered
    assert sum(i['contract'] is None for i in pc.resolve_products(store,17,today)['items'])==supplier['uncovered_product_count']


def test_coverage_excludes_archived_contracts_and_removed_catalog_members(store,monkeypatch):
    monkeypatch.setattr(pc,'jalali_business_date',lambda:'1405/06/10')
    r=pc.save_contract(store,'tester',rule(['A','B']))
    with pc.connect(store) as c:c.execute("DELETE FROM warehouse_purchase_catalog WHERE product_code='B'")
    supplier=pc.catalog(store)['suppliers'][0]
    assert (supplier['product_count'],supplier['covered_product_count'],supplier['uncovered_product_count'])==(2,1,1)
    pc.archive(store,'tester',r['id'],1,True)
    assert pc.catalog(store)['suppliers'][0]['uncovered_product_count']==2


def test_uncovered_api_uses_today_filters_before_pagination_and_skips_prices(store,monkeypatch):
    from fastapi import FastAPI,Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    from app import warehouse_purchase_prices as prices
    monkeypatch.setattr(pc,'jalali_business_date',lambda:'1405/06/10')
    def forbid_prices(*args,**kwargs):raise AssertionError('Coverage must not fetch ERP prices')
    monkeypatch.setattr(prices,'resolve_source_prices',forbid_prices)
    pc.save_contract(store,'tester',rule(['A']))
    app=FastAPI();app.state.settings=store
    async def identity(request:Request):request.state.username='viewer'
    app.dependency_overrides[routes.require_session_user]=identity
    monkeypatch.setattr(routes,'_capabilities',lambda *args:{'warehouse.assistant.view'})
    app.include_router(routes.router)
    with TestClient(app) as client:
        url='/warehouse-assistant/api/purchase-contracts/products'
        query=dict(supplier_id=17,on_date='1405/08/01',without_contract=True,stock_id=1,limit=1)
        first=client.get(url,params=query);assert first.status_code==200
        data=first.json()
        assert data['on_date']=='1405/06/10' and data['total']==data['uncovered_product_count']==2
        assert [i['product_code'] for i in data['items']]==['B']
        second=client.get(url,params=dict(query,offset=1)).json()
        assert [i['product_code'] for i in second['items']]==['C']
        searched=client.get(url,params=dict(query,search='C')).json()
        assert searched['total']==1 and searched['uncovered_product_count']==2
        common=pc.list_contracts(store)[0]
        pc.save_contract(store,'tester',rule(['A'],stock_id=1),common['id'],common['revision'])
        other=client.get(url,params=dict(query,stock_id=2)).json()
        assert other['uncovered_product_count']==other['total']==3 and other['stock_id']==2
        metadata=client.get('/warehouse-assistant/api/purchase-contracts',params={'stock_id':2}).json()['catalog']
        assert metadata['suppliers'][0]['uncovered_product_count']==3 and metadata['stock_id']==2
        add_supply_scope(store)
        scoped_query=dict(query,supply_only=True,without_contract=False,stock_id=1,coverage='all')
        scoped=client.get(url,params=scoped_query).json()
        assert scoped['coverage_counts']=={'all':2,'covered':1,'uncovered':1}
        assert scoped['total']==2 and scoped['items'][0]['product_code']=='A'
        covered=client.get(url,params=dict(scoped_query,coverage='covered')).json()
        assert covered['total']==1 and covered['items'][0]['product_code']=='A'
        uncovered=client.get(url,params=dict(scoped_query,coverage='uncovered')).json()
        assert uncovered['total']==1 and uncovered['items'][0]['product_code']=='B'
        assert client.get(url,params=dict(scoped_query,stock_id=9)).json()['total']==0


def test_migration_rolls_back_legacy_cross_scope_overlap(store):
    pc.save_contract(store,'tester',dict(rule(['A']),scope='supplier'))
    pc.save_contract(store,'tester',dict(rule(['A']),scope='item',product_code='A',discount_percent='10'))
    before=pc.list_contracts(store)
    with pytest.raises(pc.ContractError):pc.migrate_supplier_contracts(store)
    assert pc.list_contracts(store)==before
    with pc.connect(store) as c:assert not pc.grouped_structure(c)


def test_migration_merges_shared_batch_but_keeps_different_terms(store):
    pc.save_batch(store,'tester',dict(rule(['A','B']),manufacturer_id=1))
    report=pc.migrate_supplier_contracts(store)
    assert len(report['contracts'])==1 and report['contracts'][0]['count']==2
    grouped=[r for r in pc.list_contracts(store) if r['scope']=='collection'][0]
    archived=pc.archive(store,'tester',grouped['id'],1,True)
    assert archived['product_codes']==['A','B']
    assert all(i['contract'] is None for i in pc.resolve_products(store,17,'1405/06/10')['items'])


def test_collection_api_membership_preview_and_auth(store,monkeypatch):
    from fastapi import FastAPI,Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=store
    async def identity(request:Request):request.state.username=request.headers.get('X-Test-User','editor')
    app.dependency_overrides[routes.require_session_user]=identity
    monkeypatch.setattr(routes,'_capabilities',lambda request,username:{'warehouse.assistant.view'}|({'warehouse.order.draft'} if username=='editor' else set()))
    app.include_router(routes.router)
    headers={'Origin':'http://testserver','X-Warehouse-Settings':'1'}
    url='/warehouse-assistant/api/purchase-contracts'
    with TestClient(app) as client:
        assert len(client.get(url+'/selection?supplier_id=17').json()['items'])==3
        saved=client.post(url,headers=headers,json=rule(['A','B']));assert saved.status_code==200
        r=saved.json();assert r['scope']=='collection'
        assert client.post(url,headers=headers,json=rule(['B','C'])).status_code==422
        assert client.put(url+'/'+r['id'],headers={**headers,'X-Test-User':'viewer'},json=dict(rule(['C']),expected_revision=1)).status_code==403
        assert client.put(url+'/'+r['id'],headers=headers,json=dict(rule(['C']),expected_revision=1)).status_code==422
        assert client.put(url+'/'+r['id']+'/members',headers=headers,json=dict(product_codes=['A','B','C'],product_end_dates={'A':'1405/06/09','B':'1405/06/09'},expected_revision=1)).status_code==200
        assert client.put(url+'/'+r['id'],headers=headers,json=dict(rule(['A']),expected_revision=1)).status_code==409
        preview=client.post(url+'/preview',headers=headers,json={'contract':rule(['A'],basis='announcement'),'product_code':'B','price':'100','quantity':'1'})
        assert preview.status_code==422
