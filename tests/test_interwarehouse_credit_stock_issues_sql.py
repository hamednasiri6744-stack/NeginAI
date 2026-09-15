"""Regression tests for separate price-reserve stock and structured shortages.

Uses the existing opt-in synthetic SQL fixture; native confirmation is verified
separately in native_price_reserve_proof.py. Never connects to production.
"""
import json
import os
import pytest
from test_interwarehouse_credit_sql import db,seed,connection,payload,call,ready

pytestmark=pytest.mark.skipif(os.getenv('NEGIN_INTERWAREHOUSE_SQL_TEST')!='1',reason='isolated SQL opt-in')


def balances():
    with connection() as c:
        return [tuple(r) for r in c.execute('SELECT GoodsRef,StockDCRef,OnHandQty,ReservedQty FROM gnr.tblStockGoods ORDER BY GoodsRef,StockDCRef')]


def assert_no_post():
    with connection() as c:
        for table in ['inv.tblVocherHdr','inv.tblVocherItm','NeginAI.InterwarehouseCreditAudit','dbo.tblVocherNo']:
            assert c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]==0


def test_large_price_reserve_does_not_reduce_healthy_availability_twice():
    with connection() as c:
        c.execute('UPDATE gnr.tblStockGoods SET ReservedQty=1000 WHERE StockDCRef=2')
    data=ready()
    assert call(data,True)['BridgeStatus']=='sent'
    assert balances()==[(100,1,20,0),(100,2,984,1000)]


@pytest.mark.parametrize('commit',[False,True])
@pytest.mark.parametrize('reserved',[0,977])
def test_healthy_shortage_is_structured_before_any_native_post(commit,reserved):
    with connection() as c:
        c.execute('UPDATE gnr.tblStockGoods SET OnHandQty=10,ReservedQty=? WHERE StockDCRef=2',reserved)
    before=balances()
    data=payload(lines=[dict(product_code='00123',quantity=402)])
    result=call(data,commit)
    assert result['BridgeStatus']=='rejected' and result['ErrorCode']==51515,result
    assert json.loads(result['StockIssuesJson'])==[dict(ProductCode='00123',RequestedQuantity=402,
         OnHandQuantity=10,ReservedQuantity=reserved,ShortageQuantity=392)]
    assert balances()==before
    assert_no_post()


@pytest.mark.parametrize('commit',[False,True])
def test_returns_all_shortages_not_only_reserved_or_first_item(commit):
    with connection() as c:
        c.execute("""INSERT gnr.tblGoods VALUES(101,'00234',1,1,0,0);
        INSERT gnr.tblPackage VALUES(101,1,1,1,1);
        INSERT gnr.tblStockGoods(GoodsRef,StockDCRef,AccYear,IsBatch,OnHandQty,ReservedQty)
          VALUES(101,2,1405,0,20,100),(101,1,1405,0,5,0);""")
    before=balances()
    result=call(payload(lines=[dict(product_code='00123',quantity=1000),dict(product_code='00234',quantity=35)]),commit)
    assert result['BridgeStatus']=='rejected' and result['ErrorCode']==51515
    assert json.loads(result['StockIssuesJson'])==[
        dict(ProductCode='00123',RequestedQuantity=1000,OnHandQuantity=999,ReservedQuantity=0,ShortageQuantity=1),
        dict(ProductCode='00234',RequestedQuantity=35,OnHandQuantity=20,ReservedQuantity=100,ShortageQuantity=15)]
    assert balances()==before
    assert_no_post()


def test_commit_rechecks_stock_after_a_successful_preflight():
    data=ready()
    with connection() as c:
        c.execute('UPDATE gnr.tblStockGoods SET OnHandQty=10,ReservedQty=977 WHERE StockDCRef=2')
    before=balances()
    result=call(data,True)
    assert result['ErrorCode']==51515 and result['BridgeStatus']=='rejected'
    assert json.loads(result['StockIssuesJson'])==[dict(ProductCode='00123',RequestedQuantity=15,
           OnHandQuantity=10,ReservedQuantity=977,ShortageQuantity=5)]
    assert balances()==before
    assert_no_post()


def test_sufficient_lines_are_not_in_shortage_list_and_no_partial_post_occurs():
    with connection() as c:
        c.execute("""INSERT gnr.tblGoods VALUES(101,'00234',1,1,0,0);
        INSERT gnr.tblPackage VALUES(101,1,1,1,1);
        INSERT gnr.tblStockGoods(GoodsRef,StockDCRef,AccYear,IsBatch,OnHandQty,ReservedQty)
          VALUES(101,2,1405,0,20,100),(101,1,1405,0,5,0);""")
    before=balances()
    result=call(payload(lines=[dict(product_code='00123',quantity=15),dict(product_code='00234',quantity=35)]),True)
    assert json.loads(result['StockIssuesJson'])==[dict(ProductCode='00234',RequestedQuantity=35,
            OnHandQuantity=20,ReservedQuantity=100,ShortageQuantity=15)]
    assert balances()==before
    assert_no_post()
