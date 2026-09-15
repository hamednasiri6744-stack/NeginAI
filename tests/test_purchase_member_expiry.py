import json
import pytest
from app import warehouse_purchase_contracts as pc
from app import warehouse_purchase_membership as membership
from app import warehouse_purchase_invoice_bridge as bridge
from test_warehouse_purchase_groups import store, rule
from test_warehouse_purchase_invoice_bridge import case, Remote, confirmed


def test_end_date_preserves_history_and_only_expires_one_product(store,monkeypatch):
    r=pc.save_contract(store,'creator',rule(['A','B'],stock_id=1))
    r=pc.update_members(store,'ender',r['id'],1,['A','B'],{'A':'۱۴۰۵/۰۶/۱۰'})
    assert r['product_codes']==['A','B']
    assert r['end_date']=='1405/06/15'
    assert pc.resolve_products(store,17,'1405/06/10',stock_id=1,include_prices=False)['items'][0]['contract']
    after=pc.resolve_products(store,17,'1405/06/11',stock_id=1,include_prices=False)['items']
    assert after[0]['contract'] is None and after[1]['contract']['id']==r['id']
    monkeypatch.setattr(pc,'jalali_business_date',lambda:'1405/06/11')
    assert pc.catalog(store,stock_id=1)['suppliers'][0]['uncovered_product_count']==2
    with pytest.raises(pc.ContractError):pc.save_contract(store,'other',rule(['A'],stock_id=1,start_date='1405/06/10'))
    pc.save_contract(store,'other',rule(['A'],stock_id=1,start_date='1405/06/11'))
    events=membership.member_history(store,r['id'],'A')
    assert [e['actor'] for e in events]==['ender','creator']
    assert events[0]['member_end_date']=='1405/06/10'


@pytest.mark.parametrize('changes',[{'A':''},{'A':'1405/06/31'},{'A':'1405/05/31'},{'A':'1405/06/16'},{'C':'1405/06/10'}])
def test_invalid_expiry_is_atomic(store,changes):
    r=pc.save_contract(store,'tester',rule(['A','B']))
    with pytest.raises(pc.ContractError):pc.update_members(store,'tester',r['id'],1,['A','B'],changes)
    assert pc.list_contracts(store)==[r]


def test_no_physical_removal_and_regular_edit_retains_product_expiry(store):
    r=pc.save_contract(store,'tester',rule(['A','B']))
    with pytest.raises(pc.ContractError,match='تاریخ پایان'):pc.update_members(store,'tester',r['id'],1,['B'])
    r=pc.update_members(store,'tester',r['id'],1,['A','B'],{'A':'1405/06/10','B':'1405/06/10'})
    updated=pc.save_contract(store,'tester',dict(r,discount_percent='20',product_end_dates={}),r['id'],2)
    assert updated['product_end_dates']==r['product_end_dates']
    assert not pc.active_contracts_on([updated],'1405/06/11')


@pytest.mark.parametrize('pending',[False,True])
def test_invoice_usage_blocks_same_day_and_earlier_and_keeps_terms(case,monkeypatch,pending):
    pc.migrate_supplier_contracts(case.settings)
    r=next(x for x in pc.list_contracts(case.settings) if x['scope']=='collection')
    remote=Remote();remote.lose_once=pending
    monkeypatch.setattr(bridge,'remote',remote)
    if pending:
        with pytest.raises(bridge.InvoiceError):bridge.commit(case.settings,'tester',100,confirmed(case))
    else:bridge.commit(case.settings,'tester',100,confirmed(case))
    for end in ['1405/06/18','1405/06/17']:
        with pytest.raises(pc.ContractError,match='فاکتور خرید'):
            pc.update_members(case.settings,'tester',r['id'],r['revision'],r['product_codes'],{'G1':end})
    updated=pc.update_members(case.settings,'tester',r['id'],r['revision'],r['product_codes'],{'G1':'1405/06/19'})
    assert updated['discount_percent']==r['discount_percent']
    with pc.connect(case.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM warehouse_purchase_contract_usage').fetchone()[0]==2
        # Existing installations' payloads are also guarded before usage tracking existed.
        c.execute('DELETE FROM warehouse_purchase_contract_usage')
    with pytest.raises(pc.ContractError,match='فاکتور خرید'):
        pc.update_members(case.settings,'tester',r['id'],updated['revision'],r['product_codes'],{'G1':'1405/06/18'})


def test_contract_change_between_prepare_and_attempt_is_rejected(case,monkeypatch):
    pc.migrate_supplier_contracts(case.settings)
    r=next(x for x in pc.list_contracts(case.settings) if x['scope']=='collection')
    request=confirmed(case)
    original=bridge.prepare
    def racing(*args,**kwargs):
        result=original(*args,**kwargs)
        pc.update_members(case.settings,'ender',r['id'],r['revision'],r['product_codes'],{'G1':'1405/06/17'})
        return result
    monkeypatch.setattr(bridge,'prepare',racing)
    remote=Remote();monkeypatch.setattr(bridge,'remote',remote)
    with pytest.raises(bridge.InvoiceError,match='هم‌زمان'):bridge.commit(case.settings,'tester',100,request)
    assert not remote.calls
    with pc.connect(case.settings) as c:
        assert c.execute('SELECT COUNT(*) FROM warehouse_purchase_invoice_attempts').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM warehouse_purchase_contract_usage').fetchone()[0]==0


def test_end_whole_contract_retains_earlier_member_ends_and_history(store):
    r=pc.save_contract(store,'creator',rule(['A','B'],stock_id=1))
    r=pc.update_members(store,'tester',r['id'],1,r['product_codes'],{'A':'1405/06/05'})
    ended=pc.end_contract(store,'ender',r['id'],2,'1405/06/10')
    assert ended['end_date']=='1405/06/10' and ended['product_end_dates']=={'A':'1405/06/05'}
    assert ended['product_codes']==['A','B'] and ended['status']=='active'
    assert pc.active_contracts_on([ended],'1405/06/10')[0]['product_codes']==['B']
    assert not pc.active_contracts_on([ended],'1405/06/11')
    assert pc.history(store,r['id'])[0]['actor']=='ender'
    with pytest.raises(pc.ContractError,match='هم‌زمان'):pc.end_contract(store,'ender',r['id'],2,'1405/06/09')


def test_end_whole_contract_rejects_invoice_usage_atomically(case,monkeypatch):
    pc.migrate_supplier_contracts(case.settings)
    r=next(x for x in pc.list_contracts(case.settings) if x['scope']=='collection')
    monkeypatch.setattr(bridge,'remote',Remote())
    bridge.commit(case.settings,'tester',100,confirmed(case))
    with pytest.raises(pc.ContractError,match='فاکتور خرید'):pc.end_contract(case.settings,'tester',r['id'],r['revision'],'1405/06/18')
    assert next(x for x in pc.list_contracts(case.settings) if x['id']==r['id'])==r
    assert pc.end_contract(case.settings,'tester',r['id'],r['revision'],'1405/06/19')['end_date']=='1405/06/19'
