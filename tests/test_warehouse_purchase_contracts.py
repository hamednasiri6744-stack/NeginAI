from types import SimpleNamespace
from decimal import Decimal
import json
import pytest

from app import warehouse_purchase_contracts as pc


@pytest.fixture
def store(tmp_path):
    settings=SimpleNamespace(sqlite_path=tmp_path/'state.db')
    pc.initialize(settings)
    pc.replace_catalog(settings, [
        dict(product_code='A',product_name='قلم اول',goods_id=1,brand_id=4,brand='برند یک',supplier_id=17,supplier='شرکت کامان',tax_rate=10,tax_status='known'),
        dict(product_code='B',product_name='قلم دوم',goods_id=2,brand_id=5,brand='برند دو',supplier_id=17,supplier='شرکت کامان',tax_rate=16,tax_status='known'),
        dict(product_code='C',product_name='معاف',goods_id=3,brand_id=4,brand='برند یک',supplier_id=15,supplier='سیلانه سبز',tax_rate=0,tax_status='known'),
    ])
    return settings


def rule(**kw):
    return dict(supplier_id=17,scope='supplier',brand_id=None,product_code='',title='قرارداد نمونه',start_date='1405/06/01',end_date='',status='active',basis='manufacturer',includes_tax=True,adjustment_percent='0',discount_percent='18',tail_discount_percent='8.95',note='',**kw)


def test_confirmed_calculation_and_zero_tax():
    result=pc.calculate(rule(),price='1100000',quantity='1',tax_rate=10)
    assert result['net_before_tax']=='820000'
    assert result['tax']=='82000'
    assert result['tail_discount']=='73390'
    assert result['total']=='828610'
    assert pc.calculate(rule(),price='1160000',quantity='1',tax_rate=16)['total']=='877810'
    assert pc.calculate(rule(),price='1000000',quantity='1',tax_rate=0)['total']=='746610'


def test_item_brand_supplier_precedence_and_dates(store):
    base=pc.save_contract(store,'tester',rule())
    b=rule();b.update(scope='brand',brand_id=4,discount_percent='20')
    brand=pc.save_contract(store,'tester',b)
    i=rule();i.update(scope='item',product_code='A',discount_percent='25',start_date='1405/06/10')
    item=pc.save_contract(store,'tester',i)
    assert pc.resolve_products(store,17,'1405/06/09')['items'][0]['contract']['id']==brand['id']
    assert pc.resolve_products(store,17,'1405/06/10')['items'][0]['contract']['id']==item['id']
    assert pc.resolve_products(store,17,'1405/06/10')['items'][1]['contract']['id']==base['id']
    assert all(r['contract'] is None for r in pc.resolve_products(store,17,'1405/05/31')['items'])


def test_resolved_products_can_check_actual_inventory_price(store,monkeypatch):
    from app import warehouse_purchase_prices as prices
    pc.save_contract(store,'tester',rule())
    calls=[]
    def resolve(settings,ids,on_date,stock_id):
        calls.append((ids,on_date,stock_id))
        return {g:dict(goods_id=g,on_date=on_date,price_id='x',start_date='1405/06/01',end_date='',
                       source_count=1,manufacturer_price='0' if g==1 else '820000',consumer_price='1000000') for g in ids}
    monkeypatch.setattr(prices,'resolve_source_prices',resolve)
    data=pc.resolve_products(store,17,'1405/06/18',stock_id=1)
    assert calls==[([1,2],'1405/06/18',1)]
    assert data['items'][0]['price_validation']['status']=='missing'
    assert 'A' in data['items'][0]['price_validation']['message']
    assert data['items'][1]['price_validation']['price']=='820000'


def test_product_lists_include_latest_manufacturer_code_barcode_and_group(store):
    from app import warehouse_assistant_service as service
    with pc.connect(store) as conn:
        catalog=[json.loads(row[0]) for row in conn.execute('SELECT payload FROM warehouse_purchase_catalog')]
    for item in catalog:
        item['manufacturer_id']=17
        item['manufacturer']='تولیدکننده'
    pc.replace_catalog(store,catalog)
    service.init_warehouse_store(store)
    with service.warehouse_connection(store) as conn:
        snapshot=conn.execute("""INSERT INTO warehouse_snapshots
            (source_filename,source_sheet,content_sha256,product_count,item_count,imported_by,imported_at,period_days)
            VALUES ('x','x','identity',1,1,'test','2026-09-09',60)""").lastrowid
        conn.execute("""INSERT INTO warehouse_snapshot_items
            (snapshot_id,source_row,warehouse_code,warehouse_name,product_code,product_name,conversion_rate,
             manufacturer_product_code,barcode,group_level3)
            VALUES (?,1,'karaj','کرج','A','قلم اول',1,'M-A','6260000000001','گروه سه')""",(snapshot,))
    resolved=pc.resolve_products(store,17,'1405/06/18')['items'][0]
    selected=pc.selection(store,17)['items'][0]
    for item in (resolved,selected):
        assert (item['manufacturer_product_code'],item['barcode'],item['group_level3']) == ('M-A','6260000000001','گروه سه')


def test_inventory_price_status_uses_snapshot_date_and_specific_rule(store):
    pc.save_contract(store,'tester',rule())
    special=rule();special.update(scope='item',product_code='A',basis='consumer',start_date='1405/06/10')
    pc.save_contract(store,'tester',special)
    rows=[dict(warehouse_code='karaj',product_code='A',product_name='اول',manufacturer_price=0,consumer_price=1100),
          dict(warehouse_code='gilan',product_code='A',product_name='اول',manufacturer_price=1100,consumer_price=0),
          dict(warehouse_code='karaj',product_code='B',product_name='دوم',manufacturer_price=None,consumer_price=1100)]
    with pc.connect(store) as conn:
        current=pc.inventory_contract_price_status(conn,rows,'1405/06/18')
        before=pc.inventory_contract_price_status(conn,rows,'1405/06/09')
        expired=pc.inventory_contract_price_status(conn,rows,'1405/05/31')
    assert current[('karaj','A')]['status']=='ready'
    assert current[('karaj','A')]['required_bases']==['consumer']
    assert current[('gilan','A')]['status']=='missing'
    assert 'قیمت مصرف‌کننده' in current[('gilan','A')]['message']
    assert current[('karaj','B')]['status']=='missing'
    assert before[('karaj','A')]['status']=='missing'
    assert expired[('karaj','A')]['status']=='not_required'


def test_inventory_price_status_without_date_never_claims_valid_prices(store):
    pc.save_contract(store,'tester',rule())
    with pc.connect(store) as conn:
        status=pc.inventory_contract_price_status(conn,[dict(warehouse='karaj',product_code='A',manufacturer_price=100)],None)
    assert status[('karaj','A')]['status']=='unverified'


def test_overlap_conflict_history_and_optimistic_lock(store):
    first=pc.save_contract(store,'tester',rule())
    with pytest.raises(pc.ContractError):pc.save_contract(store,'tester',rule())
    edited=dict(first,discount_percent='19')
    saved=pc.save_contract(store,'tester2',edited,first['id'],first['revision'])
    assert saved['revision']==2
    with pytest.raises(pc.ContractError):pc.save_contract(store,'stale',edited,first['id'],1)
    history=pc.history(store,first['id'])
    assert [h['contract']['discount_percent'] for h in history]==['19','18']
    assert history[1]['actor']=='tester'


def test_archive_restores_fallback_and_keeps_history(store):
    base=pc.save_contract(store,'tester',rule())
    special=rule();special.update(scope='item',product_code='A')
    item=pc.save_contract(store,'tester',special)
    pc.archive(store,'tester',item['id'],item['revision'],True)
    assert pc.resolve_products(store,17,'1405/06/02')['items'][0]['contract']['id']==base['id']
    assert pc.history(store,item['id'])[0]['contract']['status']=='archived'


@pytest.mark.parametrize('change',[
    {'start_date':'1405/07/31'}, {'start_date':'1405/12/30'}, {'end_date':'1405/05/31'},
    {'discount_percent':'NaN'}, {'tail_discount_percent':'101'}, {'includes_tax':'false'},
    {'scope':'brand','brand_id':999}, {'scope':'item','product_code':'C'}, {'supplier_id':999},
])
def test_invalid_rules_are_rejected(store,change):
    payload=rule();payload.update(change)
    with pytest.raises(pc.ContractError):pc.save_contract(store,'tester',payload)


def test_dates_persian_and_inclusive_end(store):
    p=rule();p.update(start_date='۱۴۰۵/۰۶/۰۱',end_date='1405/06/02')
    pc.save_contract(store,'tester',p)
    assert pc.resolve_products(store,17,'1405/06/02')['items'][0]['contract']
    assert pc.resolve_products(store,17,'1405/06/03')['items'][0]['contract'] is None


def test_initial_drafts_once_and_unknown_is_not_exempt(store):
    pc.seed_defaults(store)
    pc.seed_defaults(store)
    drafts=[c for c in pc.list_contracts(store) if c['seed_key']]
    assert len(drafts)==2 and all(c['status']=='draft' for c in drafts)
    with pytest.raises(pc.ContractError):pc.calculate(rule(),price=100,quantity=1,tax_rate=None)
    with pytest.raises(pc.ContractError):pc.calculate(rule(),price='',quantity=1,tax_rate=0)
    assert pc.calculate(rule(),price=0,quantity=1,tax_rate=0)['total']=='0'


def test_conflicting_tax_groups_are_not_silently_selected():
    rows=[dict(GoodsCode='A',GoodsRef=1,GoodsName='a',BrandRef=4,BrandName='b',SupplierRef=17,SupplierName='s',TaxLabel='10'),
          dict(GoodsCode='A',GoodsRef=1,GoodsName='a',BrandRef=4,BrandName='b',SupplierRef=17,SupplierName='s',TaxLabel='16')]
    for row in rows:row['TaxGroupName']='وضعیت مالیات'
    assert pc.normalize_catalog(rows)[0]['tax_status']=='conflict'
    assert pc.normalize_catalog(rows)[0]['tax_rate'] is None


def test_adjacent_contracts_are_allowed(store):
    p=rule();p.update(end_date='1405/06/10');pc.save_contract(store,'tester',p)
    p=rule();p.update(start_date='1405/06/11');pc.save_contract(store,'tester',p)
    assert len(pc.list_contracts(store))==2


def test_failed_refresh_preserves_catalog_and_tax(store,monkeypatch):
    from contextlib import contextmanager
    before=pc.resolve_products(store,17,'1405/06/10')
    @contextmanager
    def unavailable(_settings):
        raise RuntimeError('private connection details')
        yield
    monkeypatch.setattr(pc,'sql_connection',unavailable)
    with pytest.raises(pc.ContractError,match='اطلاعات قبلی حفظ شد') as error:pc.refresh_catalog(store)
    assert 'private' not in str(error.value)
    assert pc.resolve_products(store,17,'1405/06/10')==before
    with pytest.raises(pc.ContractError):pc.replace_catalog(store,[])
    assert pc.resolve_products(store,17,'1405/06/10')==before


def test_missing_tax_membership_is_unknown_and_zero_is_known():
    base=dict(GoodsCode='A',GoodsRef=1,GoodsName='a',SupplierRef=17,TaxLabel='0')
    assert pc.normalize_catalog([base])[0]['tax_status']=='unknown'
    assert pc.normalize_catalog([dict(base,TaxGroupName='وضعيت ماليات')])[0]['tax_rate']==0


@pytest.fixture
def api_client(store,monkeypatch):
    from fastapi import FastAPI,Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=store
    async def identity(request:Request):request.state.username=request.headers.get('X-Test-User','editor')
    app.dependency_overrides[routes.require_session_user]=identity
    monkeypatch.setattr(routes,'_capabilities',lambda request,username: {'warehouse.assistant.view'} | ({'warehouse.order.draft','warehouse.data.refresh'} if username=='editor' else set()))
    app.include_router(routes.router)
    with TestClient(app) as client:yield client


HEADERS={'X-Warehouse-Settings':'1','Origin':'http://testserver'}
URL='/warehouse-assistant/api/purchase-contracts'


def test_api_lifecycle_version_conflict_and_fallback(api_client):
    assert len(api_client.get(URL).json()['contracts'])==2
    response=api_client.post(URL,headers=HEADERS,json=rule())
    assert response.status_code==200
    r=response.json()
    edit=api_client.put(URL+'/'+r['id'],headers=HEADERS,json=dict(r,expected_revision=1,discount_percent='19'))
    assert edit.status_code==200 and edit.json()['revision']==2
    assert api_client.put(URL+'/'+r['id'],headers=HEADERS,json=dict(r,expected_revision=1)).status_code==409
    products=api_client.get(URL+'/products',params={'supplier_id':17,'on_date':'1405/06/10','limit':1}).json()
    assert products['total']==2 and products['items'][0]['contract']['discount_percent']=='19'
    assert api_client.post(URL+'/'+r['id']+'/archive',headers=HEADERS,json={'expected_revision':2}).status_code==422
    archived=api_client.post(URL+'/'+r['id']+'/archive',headers=HEADERS,json={'expected_revision':2,'confirmed':True})
    assert archived.status_code==200
    versions=api_client.get(URL+'/'+r['id']+'/history').json()['history']
    assert [h['contract']['revision'] for h in versions]==[3,2,1]


@pytest.mark.parametrize('headers',[{},dict(HEADERS,Origin='https://untrusted.example'),dict(HEADERS,**{'X-Test-User':'viewer'})])
def test_api_write_requires_capability_and_same_origin(api_client,store,headers):
    before=pc.list_contracts(store)
    assert api_client.post(URL,headers=headers,json=rule()).status_code==403
    assert pc.list_contracts(store)==before


def test_api_preview_uses_product_tax_and_does_not_save(api_client,store,monkeypatch):
    from app import warehouse_purchase_prices as prices
    def resolve(settings,ids,on_date,stock_id):
        assert ids==[2] and on_date=='1405/06/18' and stock_id==1
        return {2:dict(goods_id=2,on_date=on_date,price_id='x',start_date='1405/06/01',end_date='',
                       source_count=1,manufacturer_price='1160000',consumer_price='2000000')}
    monkeypatch.setattr(prices,'resolve_source_prices',resolve)
    before=pc.list_contracts(store)
    r=api_client.post(URL+'/preview',headers=HEADERS,json={'contract':rule(),'product_code':'B','price':'999','quantity':1,'stock_id':1,'on_date':'1405/06/18'})
    assert r.status_code==200 and r.json()['tax_rate']==16 and r.json()['total']=='877810'
    assert pc.list_contracts(store)==before
    p=rule();p.update(scope='brand',brand_id=4)
    assert api_client.post(URL+'/preview',headers=HEADERS,json={'contract':p,'product_code':'B','price':100,'quantity':1}).status_code==422
    with pc.connect(store) as c:
        row=json.loads(c.execute("SELECT payload FROM warehouse_purchase_catalog WHERE product_code='B'").fetchone()[0])
        row.update(tax_status='unknown',tax_rate=None)
        c.execute("UPDATE warehouse_purchase_catalog SET payload=? WHERE product_code='B'",(json.dumps(row),))
    assert api_client.post(URL+'/preview',headers=HEADERS,json={'contract':rule(),'product_code':'B','price':100,'quantity':1}).status_code==422


@pytest.mark.parametrize('source_price',[None,0])
def test_api_sample_price_cannot_bypass_missing_inventory_basis(api_client,monkeypatch,source_price):
    from app import warehouse_purchase_prices as prices
    monkeypatch.setattr(prices,'resolve_source_prices',lambda *args:{2:dict(goods_id=2,on_date='1405/06/18',
        price_id='x',start_date='1405/06/01',end_date='',source_count=1,
        manufacturer_price=source_price,consumer_price='2000000')})
    response=api_client.post(URL+'/preview',headers=HEADERS,json={'contract':rule(),'product_code':'B',
        'price':'1160000','quantity':1,'stock_id':1,'on_date':'1405/06/18'})
    assert response.status_code==422
    assert 'قیمت تولیدکننده' in response.json()['detail'] and 'B' in response.json()['detail']


def test_api_basis_preview_requires_context_but_announcement_uses_input(api_client):
    payload={'contract':rule(),'product_code':'B','price':'1160000','quantity':1}
    assert api_client.post(URL+'/preview',headers=HEADERS,json=payload).status_code==422
    payload['on_date']='1405/06/18'
    assert api_client.post(URL+'/preview',headers=HEADERS,json=payload).status_code==422
    payload['contract']['basis']='announcement'
    response=api_client.post(URL+'/preview',headers=HEADERS,json=payload)
    assert response.status_code==200 and response.json()['total']=='877810'


def test_api_preview_rejects_price_outside_its_period(api_client,monkeypatch):
    from app import warehouse_purchase_prices as prices
    monkeypatch.setattr(prices,'resolve_source_prices',lambda *args:{2:dict(goods_id=2,on_date='1405/06/18',
        price_id='old',start_date='1405/05/01',end_date='1405/06/17',source_count=1,
        manufacturer_price='1160000',consumer_price='2000000')})
    response=api_client.post(URL+'/preview',headers=HEADERS,json={'contract':rule(),'product_code':'B',
        'price':'1160000','quantity':1,'stock_id':1,'on_date':'1405/06/18'})
    assert response.status_code==422 and 'قیمت تولیدکننده' in response.json()['detail']


def test_api_preview_source_outage_does_not_use_numeric_sample(api_client,monkeypatch):
    from app import warehouse_purchase_prices as prices
    def unavailable(*args):raise pc.ContractError('بررسی قیمت تولید و مصرف از ورانگر انجام نشد.')
    monkeypatch.setattr(prices,'resolve_source_prices',unavailable)
    response=api_client.post(URL+'/preview',headers=HEADERS,json={'contract':rule(),'product_code':'B',
        'price':'1160000','quantity':1,'stock_id':1,'on_date':'1405/06/18'})
    assert response.status_code==422 and 'انجام نشد' in response.json()['detail']


def test_inventory_tax_filter_is_exact_and_stock_is_unchanged(settings):
    from app import warehouse_assistant_service as warehouse
    warehouse.init_warehouse_store(settings)
    with warehouse.warehouse_connection(settings) as c:
        c.execute("INSERT INTO warehouse_snapshots (source_filename,source_sheet,content_sha256,product_count,item_count,imported_by,imported_at,period_days) VALUES ('fixture','fixture','fixture',4,4,'tester','2026-09-08',60)")
        snapshot=c.execute('SELECT MAX(id) FROM warehouse_snapshots').fetchone()[0]
        for code in ['zero','ten','sixteen','unknown']:
            c.execute("INSERT INTO warehouse_snapshot_items (snapshot_id,source_row,warehouse_code,warehouse_name,product_code,product_name,conversion_rate,stock) VALUES (?,1,'karaj','fixture',?,?,1,50)",(snapshot,code,code))
    pc.replace_catalog(settings,[dict(product_code=code,product_name=code,goods_id=i,brand_id=4,brand='brand',supplier_id=17,supplier='supplier',tax_rate=rate,tax_status='known' if rate is not None else 'unknown') for i,(code,rate) in enumerate([('zero',0),('ten',10),('sixteen',16),('unknown',None)])])
    for rate,expected in [('0','zero'),('۱۰','ten'),('16','sixteen'),('نامشخص','unknown')]:
        result=warehouse.list_inventory_information(settings,column_filters={'tax_rate':rate})
        assert result['summary']['total_items']==1
        assert result['items'][0]['product_code']==expected and result['items'][0]['on_hand_qty']==50


@pytest.fixture
def item_store(store):
    with pc.connect(store) as c:
        rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog')]
    for r in rows:
        r.update(manufacturer_id=r['supplier_id'],manufacturer=r['supplier'],group_id=r['brand_id'],group_name='گروه '+str(r['brand_id']))
    pc.replace_catalog(store,rows)
    return store


def batch_rule(**changes):
    result=rule();result.update(manufacturer_id=17,filter_brand_id=None,filter_group_id=None,product_codes=['A','B'])
    result.update(changes);return result


def test_cascaded_selection_and_frozen_item_contracts(item_store):
    assert [r['product_code'] for r in pc.selection(item_store,17,brand_id=4,group_id=4)['items']]==['A']
    assert pc.selection(item_store,17,brand_id=4,group_id=5)['items']==[]
    saved=pc.save_batch(item_store,'tester',batch_rule())
    assert saved['count']==2 and {r['scope'] for r in saved['contracts']}=={'item'}
    assert len({r['id'] for r in saved['contracts']})==2
    with pc.connect(item_store) as c:
        rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog')]
    rows.append(dict(rows[0],product_code='NEW',goods_id=9))
    pc.replace_catalog(item_store,rows)
    assert next(r for r in pc.resolve_products(item_store,17,'1405/06/17')['items'] if r['product_code']=='NEW')['contract'] is None


@pytest.mark.parametrize('change',[{'product_codes':['A','C']},{'filter_brand_id':4},{'filter_group_id':5},{'manufacturer_id':15}])
def test_bulk_selection_cannot_escape_filters(item_store,change):
    with pytest.raises(pc.ContractError):pc.save_batch(item_store,'tester',batch_rule(**change))
    assert pc.list_contracts(item_store)==[]


def test_batch_conflict_rolls_back_every_item(item_store):
    special=rule();special.update(scope='item',product_code='B');pc.save_contract(item_store,'tester',special)
    with pytest.raises(pc.ContractError):pc.save_batch(item_store,'tester',batch_rule())
    assert [r['product_code'] for r in pc.list_contracts(item_store)]==['B']


def test_seed_migrates_untouched_templates_once_and_preserves_history(item_store):
    pc.seed_item_defaults(item_store);pc.seed_item_defaults(item_store)
    contracts=pc.list_contracts(item_store)
    items=[r for r in contracts if r['scope']=='item']
    assert len(items)==3 and all(r['status']=='draft' for r in items)
    assert all(r['tail_discount']=={'kind':'percent','basis':'net_before_tax','value':'8.95'} for r in items)
    parents=[r for r in contracts if r.get('materialized')]
    assert len(parents)==2 and all(len(pc.history(item_store,r['id']))==2 for r in parents)
    pc.archive(item_store,'tester',items[0]['id'],1,True)
    pc.seed_item_defaults(item_store)
    assert len(pc.list_contracts(item_store))==5


@pytest.mark.parametrize('basis,tail',[('net_before_tax','82000'),('gross','100000'),('after_tax','90200')])
def test_percent_discount_base_is_explicit(basis,tail):
    r=rule();r['tail_discount']={'kind':'percent','basis':basis,'value':'10'}
    result=pc.calculate(r,price=1100000,quantity=1,tax_rate=10)
    assert result['tail_discount']==tail and result['tax']=='82000'


def test_fixed_invoice_discount_is_applied_once_and_allocated_exactly(item_store):
    saved=pc.save_batch(item_store,'tester',batch_rule(tail_discount={'kind':'fixed','basis':'invoice','value':'10001'}))
    lines=[{'rule':r,'price':1100000 if r['product_code']=='A' else 1160000,'quantity':1,'tax_rate':10 if r['product_code']=='A' else 16} for r in saved['contracts']]
    result=pc.calculate_invoice(lines)
    assert sum(Decimal(r['tail_discount']) for r in result['items'])==10001
    assert Decimal(result['total'])==Decimal(902000+951200-10001)
    r=saved['contracts'][0]
    edited=pc.save_contract(item_store,'tester',dict(r,title='renamed'),r['id'],1)
    assert edited['deduction_group']==r['deduction_group']
    edited2=pc.save_contract(item_store,'tester',dict(edited,tail_discount={'kind':'fixed','basis':'invoice','value':'5000'}),r['id'],2)
    assert edited2['deduction_group']!=r['deduction_group']


def test_fixed_per_unit_discount_and_excess_rejected():
    r=rule();r['tail_discount']={'kind':'fixed','basis':'unit','value':'1000'}
    assert pc.calculate(r,price=1100000,quantity=3,tax_rate=10)['tail_discount']=='3000'
    r['tail_discount']['value']='9999999'
    with pytest.raises(pc.ContractError):pc.calculate(r,price=1100000,quantity=1,tax_rate=10)


def test_group_edit_atomic_versions_and_shared_fixed_discount(item_store):
    saved=pc.save_batch(item_store,'tester',batch_rule(status='draft'))['contracts']
    payload=batch_rule(status='active',tail_discount={'kind':'fixed','basis':'invoice','value':'12000'})
    payload['contract_versions']={r['id']:r['revision'] for r in saved}
    result=pc.update_item_batch(item_store,'tester',payload)['contracts']
    assert len(result)==2 and all(r['revision']==2 for r in result)
    assert len({r['deduction_group'] for r in result})==1
    with pytest.raises(pc.ContractError):pc.update_item_batch(item_store,'tester',payload)
    assert all(r['revision']==2 for r in pc.list_contracts(item_store))
    assert all(len(pc.history(item_store,r['id']))==2 for r in result)


def test_item_api_batch_roundtrip_and_filter_validation(api_client,store):
    with pc.connect(store) as c:
        rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog')]
    for r in rows:r.update(manufacturer_id=r['supplier_id'],manufacturer=r['supplier'],group_id=r['brand_id'],group_name='group')
    pc.replace_catalog(store,rows)
    selection=api_client.get(URL+'/selection',params={'manufacturer_id':17,'brand_id':4}).json()
    assert [r['product_code'] for r in selection['items']]==['A']
    response=api_client.post(URL+'/batch',headers=HEADERS,json=batch_rule(status='draft'))
    assert response.status_code==200 and response.json()['count']==2
    contracts=response.json()['contracts']
    edited=api_client.post(URL+'/batch-edit',headers=HEADERS,json=dict(batch_rule(),contract_versions={r['id']:1 for r in contracts}))
    assert edited.status_code==200 and all(r['status']=='active' for r in edited.json()['contracts'])
    assert api_client.post(URL+'/batch',headers={**HEADERS,'X-Test-User':'viewer'},json=batch_rule()).status_code==403
