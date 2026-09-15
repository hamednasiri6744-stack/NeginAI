"""Synthetic receipts only; ERP I/O boundaries are replaced, local ledger is real."""
from copy import deepcopy
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from app import warehouse_purchase_contracts as contracts
from app import warehouse_purchase_invoice_bridge as bridge
from app.sql_guard import validate_read_only_sql
from app.warehouse_assistant_service import warehouse_connection, warehouse_database_path


def request(**changes):
    return dict(supplier_invoice_no='2222',supplier_invoice_date='1405/06/18',voucher_date='1405/06/18',**changes)


@pytest.fixture
def case(tmp_path,monkeypatch):
    settings=SimpleNamespace(sqlite_path=tmp_path/'state.db',varanegar_purchase_bridge_enabled=True,
                             varanegar_purchase_commit_enabled=True)
    contracts.initialize(settings)
    catalog=[dict(goods_id=g,product_code=f'G{g}',product_name=f'کالای {g}',brand_id=4,brand='برند',
                  supplier_id=17,supplier='کامان',tax_rate=10,tax_status='known') for g in (1,2)]
    contracts.replace_catalog(settings,catalog)
    rule=contracts.save_contract(settings,'tester',dict(supplier_id=17,scope='supplier',brand_id=None,
        product_code='',title='آزمون مستقل',start_date='1405/06/01',end_date='',status='active',basis='manufacturer',
        includes_tax=True,adjustment_percent='0',discount_percent='18',tail_discount_percent='8.95',note=''))
    rows=[dict(receipt_id=100,receipt_no=700,fiscal_year=1405,receipt_date='1405/06/18',receipt_type=20,
        supplier_id=17,stock_id=1,dc_id=4,confirmed_at='2026-09-08',supplier_reference=2222,
        comment='fixture',supplier_name='کامان',stock_name='کرج',linked=0,receipt_item_id=1000+g,
        goods_id=g,unit_ref=1,unit_capacity='1',quantity='1',unit_quantity='1',product_code=f'G{g}',
        product_name=f'کالای {g}',item_comment='fixture') for g in (1,2)]
    sources={g:dict(goods_id=g,stock_id=1,stock_name='کرج',on_date='1405/06/18',price_id=f'P{g}',
        start_date='1405/06/01',end_date='',source_count=1,manufacturer_price='1100000',
        consumer_price='2000000') for g in (1,2)}
    calls=[]
    def read(settings,receipt_id):
        assert receipt_id==100
        return deepcopy(rows)
    def prices(settings,goods_ids,on_date,stock_id):
        calls.append((list(goods_ids),on_date,stock_id))
        return {g:dict(sources[g],on_date=on_date,stock_id=stock_id) for g in goods_ids}
    monkeypatch.setattr(bridge,'preflight',lambda *args:dict(ready=True,message='fixture ready'))
    monkeypatch.setattr(bridge,'read_receipt',read)
    monkeypatch.setattr(bridge,'resolve_source_prices',prices)
    return SimpleNamespace(settings=settings,rows=rows,sources=sources,price_calls=calls,rule=rule)


def test_prepare_uses_receipt_quantity_live_price_and_effective_contract(case):
    supplied=request(price=1,quantity=999,tax_rate=0,lines=[{'goods_id':999}],supplier_id=15,stock_id=9)
    result=bridge.prepare(case.settings,100,supplied)
    assert result['ready'] and not result['varanegar_write']
    assert result['total']=='1657220'
    assert case.price_calls==[([1,2],'1405/06/18',1)]
    assert len(result['payload']['lines'])==2
    first=result['payload']['lines'][0]
    assert first['goods_id']==1 and first['quantity']=='1'
    assert first['unit_price']=='1000000' and first['tax_amount']=='82000'
    assert first['column_discount']=='180000' and first['tail_discount']=='73390'
    assert result['items'][0]['contract_revision']==1
    with warehouse_connection(case.settings) as c:
        assert not c.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_purchase_invoice_attempts'").fetchone()


def test_grouped_contract_migration_keeps_invoice_amounts_and_shared_identity(case):
    before=bridge.prepare(case.settings,100,request())
    contracts.migrate_supplier_contracts(case.settings)
    after=bridge.prepare(case.settings,100,request())
    assert after['ready'] and after['total']==before['total']
    assert after['payload']==before['payload']
    assert len({item['contract_id'] for item in after['items']})==1
    assert after['preview_token']!=before['preview_token']


def test_legacy_desktop_era_dates_match_canonical_preview(case):
    canonical=bridge.prepare(case.settings,100,request())
    legacy=request()
    legacy.update(supplier_invoice_date='۱۴۰۵/۰۶/۱۸ AP',voucher_date='1405/06/18 AP')
    result=bridge.prepare(case.settings,100,legacy)
    assert result['payload']==canonical['payload']
    assert result['preview_token']==canonical['preview_token']


def test_invoice_uses_receipt_warehouse_even_when_same_supplier_and_goods(case):
    old=case.rule
    first=contracts.save_contract(case.settings,'tester',dict(old,stock_id=1),old['id'],old['revision'])
    second=contracts.save_contract(case.settings,'tester',dict(old,stock_id=2,discount_percent='25'))
    karaj=bridge.prepare(case.settings,100,request())
    assert karaj['summary']['discount']=='360000'
    for row in case.rows:row['stock_id']=2
    tehran=bridge.prepare(case.settings,100,request())
    assert tehran['summary']['discount']=='500000'
    assert all(item['contract_id']==second['id'] for item in tehran['items'])
    assert karaj['preview_token']!=tehran['preview_token']
    for row in case.rows:row['stock_id']=9
    gilan=bridge.prepare(case.settings,100,request())
    assert gilan['payload'] is None and gilan['errors']


def test_invoice_summary_shows_tax_then_tail_using_exact_payload_amounts(case):
    result=bridge.prepare(case.settings,100,request())
    s=result['summary']
    assert s==dict(gross='2000000',discount='360000',net_before_tax='1640000',tax='164000',
                  after_tax='1804000',tail_discount='146780',total='1657220',
                  tail_discounts=[dict(kind='percent',basis='net_before_tax',value='8.95',base='1640000',amount='146780')])
    assert result['items'][0]['pricing']['discount_steps']==[dict(percent='18')]
    assert result['items'][0]['amounts']['after_tax']=='902000'
    assert sum(Decimal(r['tail_discount']) for r in result['payload']['lines'])==Decimal(s['tail_discount'])
    assert 'pricing' not in result['payload']['lines'][0]


@pytest.mark.parametrize('bad',['1405/06/18 AD','1405/06/18 AP junk','1405/12/31 AP'])
def test_legacy_date_normalization_keeps_strict_calendar_validation(case,bad):
    data=request();data['supplier_invoice_date']=bad
    with pytest.raises(bridge.InvoiceError):bridge.prepare(case.settings,100,data)


def test_legacy_date_with_missing_invoice_number_reports_required_number(case):
    data=request();data.update(supplier_invoice_date='1405/06/18 AP',voucher_date='1405/06/18 AP',supplier_invoice_no='')
    with pytest.raises(bridge.InvoiceError,match='شماره فاکتور تأمین‌کننده'):
        bridge.prepare(case.settings,100,data)


def test_invoice_tail_rounds_once_and_allocates_exact_rials(case):
    for source in case.sources.values():source['manufacturer_price']='1100'
    result=bridge.prepare(case.settings,100,request())
    assert result['ready']
    # 2 * (820 + 82) - round(1640 * 8.95%) = 1657, not 1658.
    assert result['total']=='1657'
    assert sum(Decimal(r['tail_discount']) for r in result['payload']['lines'])==147
    assert sorted(Decimal(r['tail_discount']) for r in result['payload']['lines'])==[73,74]


@pytest.mark.parametrize('field,value', [('receipt_type',10),('confirmed_at',None),('linked',1),
    ('stock_id',7),('fiscal_year',1404)])
def test_receipt_header_prohibitions_stop_before_price_read(case,field,value):
    for row in case.rows:row[field]=value
    with pytest.raises(bridge.InvoiceError):bridge.prepare(case.settings,100,request())
    assert not case.price_calls


@pytest.mark.parametrize('field,value',[('quantity','0'),('quantity','-1'),('unit_capacity','12'),('unit_ref',None)])
def test_invalid_quantity_or_nonbase_unit_prevents_payload(case,field,value):
    case.rows[0][field]=value
    result=bridge.prepare(case.settings,100,request())
    assert not result['ready'] and result['errors'] and result['payload'] is None
    assert result['preview_token']==''


@pytest.mark.parametrize('missing',[None,0,'NaN'])
def test_missing_required_price_stops_invoice_with_specific_product(case,missing):
    case.sources[1]['manufacturer_price']=missing
    result=bridge.prepare(case.settings,100,request(price=1100000))
    assert not result['ready'] and result['payload'] is None
    assert any('G1' in error and 'قیمت تولیدکننده' in error for error in result['errors'])


def test_expired_price_or_uncovered_contract_date_stops_invoice(case):
    case.sources[1]['end_date']='1405/06/17'
    assert not bridge.prepare(case.settings,100,request())['ready']
    query=request();query['supplier_invoice_date']='1405/05/31'
    result=bridge.prepare(case.settings,100,query)
    assert not result['ready'] and any('قرارداد' in error for error in result['errors'])


def test_duplicate_goods_not_silently_merged(case):
    case.rows[1]['goods_id']=1
    with pytest.raises(bridge.InvoiceError,match='چند ردیف'):bridge.prepare(case.settings,100,request())
    assert not case.price_calls


def test_unknown_tax_fails_but_mixed_valid_rates_are_supported(case):
    with contracts.connect(case.settings) as c:
        row=json.loads(c.execute("SELECT payload FROM warehouse_purchase_catalog WHERE product_code='G2'").fetchone()[0])
        row.update(tax_status='unknown',tax_rate=None)
        c.execute("UPDATE warehouse_purchase_catalog SET payload=? WHERE product_code='G2'",(json.dumps(row),))
    assert any('مالیات' in e for e in bridge.prepare(case.settings,100,request())['errors'])
    with contracts.connect(case.settings) as c:
        row.update(tax_status='known',tax_rate=16)
        c.execute("UPDATE warehouse_purchase_catalog SET payload=? WHERE product_code='G2'",(json.dumps(row),))
    mixed=bridge.prepare(case.settings,100,request())
    assert mixed['ready'] and {line['tax_rate'] for line in mixed['payload']['lines']}=={10,16}


@pytest.mark.parametrize('supplier_id,supplier,adjustment,steps,tail',[
    (67,'بازرگانی افق پاک تکین','0',['0'],'0'),
    (5,'آوین پلاست پارس','-60',['20','5'],'0'),
    (4,'آوامهرخاورمیانه','-15',['16.666','23.56'],'0'),
])
def test_every_supplier_with_an_active_contract_uses_its_own_terms(case,supplier_id,supplier,adjustment,steps,tail):
    catalog=[dict(goods_id=g,product_code=f'G{g}',product_name=f'کالای {g}',brand_id=4,brand='برند',
                  supplier_id=supplier_id,supplier=supplier,tax_rate=10,tax_status='known') for g in (1,2)]
    contracts.replace_catalog(case.settings,catalog)
    rule=contracts.save_contract(case.settings,'tester',dict(supplier_id=supplier_id,scope='supplier',brand_id=None,
        product_code='',title='قرارداد عمومی',start_date='1405/06/01',end_date='',status='active',basis='manufacturer',
        includes_tax=True,adjustment_percent=adjustment,discount_percent=steps[0],
        discount_steps=[{'percent':value} for value in steps],tail_discount_percent=tail,note=''))
    for row in case.rows:
        row.update(supplier_id=supplier_id,supplier_name=supplier)
    result=bridge.prepare(case.settings,100,request())
    assert result['ready'],result['errors']
    assert result['items'][0]['contract_id']==rule['id']
    assert result['payload']['lines'][0]['discount_steps']==[{'percent':value} for value in steps]


def test_changed_source_or_contract_changes_preview_token(case):
    first=bridge.prepare(case.settings,100,request())['preview_token']
    case.sources[1]['price_id']='replacement-same-price'
    second=bridge.prepare(case.settings,100,request())['preview_token']
    assert first!=second
    contracts.save_contract(case.settings,'editor',dict(case.rule,note='reviewed'),case.rule['id'],case.rule['revision'])
    assert second!=bridge.prepare(case.settings,100,request())['preview_token']


def test_disabled_commit_has_no_local_or_remote_effect(tmp_path,monkeypatch):
    settings=SimpleNamespace(sqlite_path=tmp_path/'state.db',varanegar_purchase_bridge_enabled=True,
                             varanegar_purchase_commit_enabled=False)
    def forbidden(*args):pytest.fail('Disabled commit crossed an I/O boundary')
    for name in ('initialize','prepare','remote'):monkeypatch.setattr(bridge,name,forbidden)
    with pytest.raises(bridge.InvoiceError,match='فعال نشده'):bridge.commit(settings,'tester',100,request())
    assert not warehouse_database_path(settings).exists()


class Remote:
    """One fake ERP insertion per transfer key; can lose its committed reply."""
    def __init__(self):self.calls=[];self.documents={};self.lose_once=False
    def __call__(self,settings,key,actor,payload):
        self.calls.append((key,actor,payload))
        result=self.documents.setdefault(key,dict(BridgeStatus='sent',InvoiceId=901,InvoiceNo=701,Confirmed=False))
        if self.lose_once:
            self.lose_once=False
            raise TimeoutError('reply lost after remote commit')
        return result


def confirmed(case):
    preview=bridge.prepare(case.settings,100,request())
    return request(confirmed=True,preview_token=preview['preview_token'])


def test_changed_source_after_preview_never_calls_remote(case,monkeypatch):
    data=confirmed(case);case.sources[1]['manufacturer_price']='2200000'
    remote=Remote();monkeypatch.setattr(bridge,'remote',remote)
    with pytest.raises(bridge.InvoiceError,match='تغییر کرده'):bridge.commit(case.settings,'tester',100,data)
    assert not remote.calls
    with warehouse_connection(case.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM warehouse_purchase_invoice_attempts').fetchone()[0]==0


def test_uncertain_remote_result_replays_same_key_and_bytes_then_caches_success(case,monkeypatch):
    data=confirmed(case);remote=Remote();remote.lose_once=True
    monkeypatch.setattr(bridge,'remote',remote)
    with pytest.raises(bridge.InvoiceError,match='درخواست محفوظ'):bridge.commit(case.settings,'tester',100,data)
    with warehouse_connection(case.settings) as c:
        stored=dict(c.execute('SELECT * FROM warehouse_purchase_invoice_attempts').fetchone())
    assert stored['status']=='pending' and len(remote.documents)==1
    case.sources[1]['manufacturer_price']='2200000'
    retry=dict(data,price='1',quantity=999,supplier_invoice_no='3333')
    result=bridge.commit(case.settings,'tester',100,retry)
    assert result['BridgeStatus']=='sent' and len(remote.documents)==1
    assert remote.calls[0]==remote.calls[1]
    assert remote.calls[0][2]==stored['payload_json']
    assert json.loads(remote.calls[0][2])['supplier_invoice_no']==2222
    assert bridge.commit(case.settings,'tester',100,retry)==result
    assert len(remote.calls)==2


def test_pending_attempt_cannot_change_actor_or_preview_token(case,monkeypatch):
    data=confirmed(case);remote=Remote();remote.lose_once=True
    monkeypatch.setattr(bridge,'remote',remote)
    with pytest.raises(bridge.InvoiceError):bridge.commit(case.settings,'tester',100,data)
    with pytest.raises(bridge.InvoiceError):bridge.commit(case.settings,'other',100,data)
    with pytest.raises(bridge.InvoiceError):bridge.commit(case.settings,'tester',100,dict(data,preview_token='different'))
    assert len(remote.calls)==1


def test_known_blocked_attempt_can_be_corrected_without_erasing_history(case,monkeypatch):
    first=confirmed(case);calls=[]
    def blocked(settings,key,actor,payload):
        calls.append((key,payload))
        return dict(BridgeStatus='blocked',Message='closed period')
    monkeypatch.setattr(bridge,'remote',blocked)
    assert bridge.commit(case.settings,'tester',100,first)['BridgeStatus']=='blocked'
    revised=request();revised['voucher_date']='1405/06/19'
    preview=bridge.prepare(case.settings,100,revised)
    revised.update(confirmed=True,preview_token=preview['preview_token'])
    remote=Remote();monkeypatch.setattr(bridge,'remote',remote)
    assert bridge.commit(case.settings,'tester',100,revised)['BridgeStatus']=='sent'
    assert calls[0][0]!=remote.calls[0][0]
    with warehouse_connection(case.settings) as c:
        states=[row[0] for row in c.execute('SELECT status FROM warehouse_purchase_invoice_attempts ORDER BY created_at,rowid')]
    assert states==['blocked','sent']


@pytest.mark.parametrize('result',[
    {'BridgeStatus':'sent','InvoiceId':0,'InvoiceNo':701,'Confirmed':False},
    {'BridgeStatus':'sent','InvoiceId':901,'InvoiceNo':701,'Confirmed':True},
    {'BridgeStatus':'sent','InvoiceId':901,'InvoiceNo':701,'Confirmed':None},
    {'BridgeStatus':'unknown','InvoiceId':901,'InvoiceNo':701,'Confirmed':False},
])
def test_remote_never_accepts_unverified_or_confirmed_invoice(case,monkeypatch,result):
    from app import warehouse_receipt_bridge
    columns=list(result)
    class Cursor:
        description=[(name,) for name in columns]
        def execute(self,sql,params):
            assert 'EXEC NeginAI.usp_CreatePurchaseInvoiceFromReceipt' in sql
            assert params==('key','tester','{}',True)
        def fetchone(self):return tuple(result.values())
    @contextmanager
    def connection(settings):yield SimpleNamespace(cursor=lambda:Cursor())
    monkeypatch.setattr(warehouse_receipt_bridge,'_connection',connection)
    with pytest.raises(bridge.InvoiceError):bridge.remote(case.settings,'key','tester','{}')


def test_unconfirmed_request_never_opens_ledger(case,monkeypatch):
    monkeypatch.setattr(bridge,'initialize',lambda *args:pytest.fail('Unconfirmed request opened ledger'))
    with pytest.raises(bridge.InvoiceError):bridge.commit(case.settings,'tester',100,request(confirmed='true',preview_token='x'))


def test_receipt_query_is_read_only_and_exactly_scoped():
    sql=bridge.source_query(100)
    assert 'WHERE h.ID=100' in sql
    assert 'ICA.tblSupInvInvoiceRelation' in validate_read_only_sql(sql).sources
    for invalid in (True,'100',-1,0):
        with pytest.raises(bridge.InvoiceError):bridge.source_query(invalid)


def test_sql_bridge_is_supplier_agnostic_and_builds_contract_factors_dynamically():
    sql=(Path(__file__).parents[1]/'scripts/sql/install_purchase_invoice_bridge.sql').read_text(encoding='utf-8-sig')
    assert 'SupplierRef IN(15,17)' not in sql
    assert 'Rate NOT IN(10,16)' not in sql
    assert 'Gross*0.18' not in sql and '*0.0895' not in sql
    assert "OPENJSON(L.RawJson,'$.discount_steps')" in sql
    assert "CASE StageNo WHEN 1 THEN 2 ELSE 3 END" in sql
    assert "N'V|'" in sql and 'GROUP BY Rate' in sql
    assert 'SELECT @FactorCount=COUNT(*) FROM #F' in sql


@pytest.fixture
def api(case,monkeypatch):
    from fastapi import FastAPI,Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=case.settings
    async def identity(request:Request):request.state.username=request.headers.get('X-Test-User','editor')
    app.dependency_overrides[routes.require_session_user]=identity
    monkeypatch.setattr(routes,'_capabilities',lambda req,user:{'warehouse.assistant.view'} | (
        {'warehouse.order.draft','warehouse.receipt.transfer'} if user=='editor' else set()))
    app.include_router(routes.router)
    with TestClient(app) as client:yield client


HEADERS={'X-Warehouse-Settings':'1','Origin':'http://testserver'}
URL='/warehouse-assistant/api/purchase-invoices/100'


def test_invoice_routes_preview_uses_source_then_commit_requires_capability(api,case,monkeypatch):
    remote=Remote();monkeypatch.setattr(bridge,'remote',remote)
    response=api.post(URL+'/preview',headers=HEADERS,json=request(price=1))
    assert response.status_code==200 and response.json()['total']=='1657220'
    data=request(confirmed=True,preview_token=response.json()['preview_token'])
    assert api.post(URL+'/transfer',headers=dict(HEADERS,**{'X-Test-User':'viewer'}),json=data).status_code==403
    assert api.post(URL+'/transfer',headers=dict(HEADERS,Origin='https://other.example'),json=data).status_code==403
    assert not remote.calls
    response=api.post(URL+'/transfer',headers=HEADERS,json=data)
    assert response.status_code==200 and response.json()['InvoiceNo']==701
    assert len(remote.documents)==1


def test_enabled_flags_do_not_enable_unready_database(case,monkeypatch):
    monkeypatch.setattr(bridge,'preflight',lambda *args:dict(ready=False,message='not approved'))
    preview=bridge.prepare(case.settings,100,request())
    assert preview['ready'] and not preview['commit_enabled'] and not preview['bridge_ready']
    monkeypatch.setattr(bridge,'remote',lambda *args:pytest.fail('unready transfer wrote to ERP'))
    with pytest.raises(bridge.InvoiceError,match='not approved'):
        bridge.commit(case.settings,'tester',100,request(confirmed=True,preview_token=preview['preview_token']))
    with warehouse_connection(case.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM warehouse_purchase_invoice_attempts').fetchone()[0]==0


@pytest.mark.parametrize('code',[51217,51204,51210])
def test_preflight_uses_validation_only_and_explains_rejection(monkeypatch,code):
    def remote(settings,key,actor,payload,commit=True):
        assert commit is False and json.loads(payload)=={'receipt_id':100}
        return dict(BridgeStatus='blocked',ErrorCode=code,Message='changed receipt')
    monkeypatch.setattr(bridge,'remote',remote)
    result=bridge.preflight(None,{'receipt_id':100})
    assert not result['ready'] and result['message']


def test_preflight_permission_failure_stays_disabled(monkeypatch):
    def denied(*args,**kwargs):raise PermissionError('database permission denied')
    monkeypatch.setattr(bridge,'remote',denied)
    assert not bridge.preflight(None,{})['ready']


@pytest.fixture
def multi(case,monkeypatch):
    groups={100:deepcopy(case.rows),200:deepcopy(case.rows),300:deepcopy(case.rows)}
    for rid,rows in groups.items():
        for row in rows:
            row.update(receipt_id=rid,receipt_no=rid+600,receipt_item_id=rid*10+row['goods_id'])
    monkeypatch.setattr(bridge,'read_receipt',lambda settings,rid:deepcopy(groups[rid]))
    return case,groups


def test_multiple_receipts_merge_goods_and_retain_sources(multi):
    case,groups=multi
    groups[200][0]['quantity']='3'
    p=bridge.prepare(case.settings,[200,100],request())
    assert p['ready'] and p['receipt_ids']==[100,200] and p['receipt_nos']==[700,800]
    assert p['payload']['receipt_ids']==[100,200] and p['payload']['receipt_id']==100
    assert len(p['items'])==2 and p['items'][0]['quantity']=='4'
    assert p['items'][0]['receipt_sources']==[dict(receipt_id=100,receipt_no=700,quantity='1'),dict(receipt_id=200,receipt_no=800,quantity='3')]
    assert p['preview_token']==bridge.prepare(case.settings,[100,200],request())['preview_token']
    assert p['total']=='4971660'  # six units * 828610 per unit


@pytest.mark.parametrize('ids',[[],[100,100],[True],[0],[-1],['100'],[2147483648],list(range(1,22)),None])
def test_invalid_receipt_sets_fail_before_source_read(case,monkeypatch,ids):
    monkeypatch.setattr(bridge,'read_receipt',lambda *args:pytest.fail('invalid selection reached ERP'))
    with pytest.raises(bridge.InvoiceError):bridge.prepare(case.settings,ids,request())


@pytest.mark.parametrize('field,value',[('stock_id',9),('supplier_id',15),('fiscal_year',1404),('dc_id',99),('confirmed_at',None),('linked',1)])
def test_incompatible_receipt_sets_rejected_before_price_lookup(multi,field,value):
    case,groups=multi
    for row in groups[200]:row[field]=value
    with pytest.raises(bridge.InvoiceError):bridge.prepare(case.settings,[100,200],request())
    assert not case.price_calls


def test_mixed_unit_or_empty_quantity_cannot_be_hidden_by_merge(multi):
    case,groups=multi
    groups[200][0]['unit_ref']=2
    with pytest.raises(bridge.InvoiceError,match='واحد'):bridge.prepare(case.settings,[100,200],request())
    groups[200][0]['unit_ref']=1;groups[200][0]['quantity']='0'
    with pytest.raises(contracts.ContractError):bridge.selected_receipts(case.settings,[100,200])


def test_overlap_blocks_single_subset_and_other_group_then_exact_retry_works(multi,monkeypatch):
    case,groups=multi
    p=bridge.prepare(case.settings,[100,200],request());data=request(confirmed=True,preview_token=p['preview_token'])
    remote=Remote();remote.lose_once=True;monkeypatch.setattr(bridge,'remote',remote)
    with pytest.raises(bridge.InvoiceError):bridge.commit(case.settings,'tester',[100,200],data)
    for ids in ([200],[200,300],[100]):
        with pytest.raises(bridge.InvoiceError):bridge.commit(case.settings,'tester',ids,data)
    assert len(remote.calls)==1
    result=bridge.commit(case.settings,'tester',[200,100],data)
    assert result['BridgeStatus']=='sent' and remote.calls[0]==remote.calls[1]
    with warehouse_connection(case.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM warehouse_purchase_invoice_receipts').fetchone()[0]==2
        assert c.execute('SELECT COUNT(*) FROM warehouse_purchase_invoice_attempts').fetchone()[0]==1


def test_known_rejection_releases_all_receipts_but_preserves_attempt(multi,monkeypatch):
    case,groups=multi;p=bridge.prepare(case.settings,[100,200],request())
    monkeypatch.setattr(bridge,'remote',lambda *args:dict(BridgeStatus='blocked',Message='changed receipt'))
    result=bridge.commit(case.settings,'tester',[100,200],request(confirmed=True,preview_token=p['preview_token']))
    assert result['BridgeStatus']=='blocked'
    with warehouse_connection(case.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM warehouse_purchase_invoice_receipts').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM warehouse_purchase_invoice_attempts').fetchone()[0]==1


def test_legacy_single_attempt_migrates_to_shared_receipt_reservation(case,monkeypatch):
    data=confirmed(case);remote=Remote();remote.lose_once=True;monkeypatch.setattr(bridge,'remote',remote)
    with pytest.raises(bridge.InvoiceError):bridge.commit(case.settings,'tester',100,data)
    with warehouse_connection(case.settings) as c:c.execute('DROP TABLE warehouse_purchase_invoice_receipts')
    bridge.initialize(case.settings)
    with warehouse_connection(case.settings) as c:
        assert c.execute('SELECT receipt_id FROM warehouse_purchase_invoice_receipts').fetchone()[0]==100


def test_multi_routes_use_same_permissions_and_source_quantities(api,multi,monkeypatch):
    case,groups=multi;remote=Remote();monkeypatch.setattr(bridge,'remote',remote)
    url='/warehouse-assistant/api/purchase-invoices'
    response=api.post(url+'/preview',headers=HEADERS,json=dict(request(),receipt_ids=[200,100],lines=[dict(quantity=999)]))
    assert response.status_code==200,response.text
    p=response.json();assert len(p['items'])==2 and p['items'][0]['quantity']=='2'
    data=dict(request(),receipt_ids=[100,200],confirmed=True,preview_token=p['preview_token'])
    assert api.post(url+'/transfer',headers=dict(HEADERS,**{'X-Test-User':'viewer'}),json=data).status_code==403
    assert api.post(url+'/transfer',headers=HEADERS,json=data).json()['BridgeStatus']=='sent'
    assert json.loads(remote.calls[0][2])['receipt_ids']==[100,200]
