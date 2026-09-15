"""Opt-in SQL transaction tests on a newly created, strictly isolated database.

Native create/allocator are exercised against synthetic tables; confirmation is
an explicit double, NOT a substitute for full native clone validation.
NEGIN_INTERWAREHOUSE_SQL_TEST=1 enables this suite. No production SQL is used.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
from uuid import uuid4

import pyodbc
import pytest

NAME = 'NeginAI_InterwarehouseBridge_SyntheticTest'
BASE = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=127.0.0.1;Trusted_Connection=yes;TrustServerCertificate=yes;'
pytestmark = pytest.mark.skipif(os.getenv('NEGIN_INTERWAREHOUSE_SQL_TEST') != '1', reason='isolated SQL opt-in')


def batches(conn, path):
    sql=Path(path).read_text(encoding='utf-8')
    if path.endswith('install_interwarehouse_credit_bridge.sql'):
        assert conn.execute('SELECT DB_NAME()').fetchone()[0]==NAME
        assert sql.count('USE [NeginPakhsh];')==1
        sql=sql.replace('USE [NeginPakhsh];',f'USE [{NAME}];')
    for batch in re.split(r'^GO\s*$', sql, flags=re.M | re.I):
        if batch.strip():
            conn.cursor().execute(batch)


@pytest.fixture(scope='module')
def db():
    master = pyodbc.connect(BASE + 'DATABASE=master;', autocommit=True, timeout=5)
    assert master.execute('SELECT DB_ID(?)', NAME).fetchone()[0] is None, 'Never reuse an existing database'
    master.execute(f'CREATE DATABASE [{NAME}] COLLATE Persian_100_CI_AS')
    try:
        with connection() as c:
            assert c.execute('SELECT DB_NAME()').fetchone()[0] == NAME
            batches(c, 'tests/fixtures/checkbar_receipt/synthetic_schema.sql')
            batches(c, 'tests/fixtures/interwarehouse_credit/synthetic_confirmation.sql')
            batches(c, 'scripts/sql/install_interwarehouse_credit_bridge.sql')
        yield
    finally:
        # Only the constant database whose absence and successful creation we verified.
        master.execute(f'ALTER DATABASE [{NAME}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE')
        master.execute(f'DROP DATABASE [{NAME}]')
        master.close()


@contextmanager
def connection():
    c = pyodbc.connect(BASE + f'DATABASE={NAME};', autocommit=True, timeout=10)
    try:
        yield c
    finally:
        c.close()


@pytest.fixture(autouse=True)
def seed(db):
    with connection() as c:
        for table in ['NeginAI.InterwarehouseCreditAudit', 'inv.tblVocherItm', 'inv.tblVocherHdr', 'dbo.tblVocherNo',
                      'NeginAI.InterwarehouseCreditPolicy', 'dbo.AppUser', 'gnr.tblAccYear', 'gnr.tblStockDC',
                      'gnr.tblOprDate', 'inv.tblStCountHdr', 'gnr.tblGoods', 'gnr.tblStockGoods',
                      'gnr.tblPackage', 'SLE.tblGoodsNoSale', 'gnr.tblGeneralConfig', 'gnr.tblServerConfig']:
            c.execute(f'DELETE FROM {table}')
        c.execute("""INSERT dbo.AppUser VALUES(10,1,0);
            INSERT NeginAI.InterwarehouseCreditPolicy VALUES(ORIGINAL_LOGIN(),2,1,10,1,1);
            INSERT gnr.tblAccYear VALUES(1405,'1405/01/01','1405/12/29');
            INSERT gnr.tblStockDC VALUES(1,1,NULL),(2,1,NULL),(9,1,NULL);
            INSERT gnr.tblOprDate VALUES(1405,1,1,0,'1405/01/01','1405/06/22');
            INSERT gnr.tblGoods VALUES(100,'00123',1,1,0,0);
            INSERT gnr.tblStockGoods(GoodsRef,StockDCRef,AccYear,IsBatch,OnHandQty) VALUES(100,2,1405,0,999),(100,1,1405,0,20);
            INSERT gnr.tblPackage VALUES(100,1,1,1,1);
            INSERT gnr.tblGeneralConfig VALUES('CreateVocher15','0'),('ConfirmVochersBeforeCloseDate','1');
            INSERT gnr.tblServerConfig VALUES('IsConfirmVchEffectiveonOnHandQty','1'),('InsertManualBedVoucher','0');
            UPDATE dbo.TestSwitch SET ValidationError=0,ForceConfirmed=0,CorruptItem=0,ChangeStock=0;
            UPDATE dbo.CreditTestSwitch SET ConfirmError=0,WrongSourceDelta=0,DestinationChanged=0,CreateDebit=0,MissingConfirmation=0;""")


def payload(**updates):
    data = dict(version=1, document_number='TR-000001', source_stock_ref=2, destination_stock_ref=1,
                voucher_date='1405/06/22', lines=[dict(product_code='00123', quantity=15)])
    data.update(updates)
    return data


def call(data, commit=False, key=None):
    with connection() as c:
        q = c.cursor()
        q.execute('EXEC NeginAI.usp_CreateInterwarehouseCredit @TransferKey=?,@RequestedBy=?,@PayloadJson=?,@Commit=?',
                  str(key or uuid4()), 'tester', json.dumps(data, ensure_ascii=False), commit)
        while True:
            if q.description and 'BridgeStatus' in [r[0] for r in q.description]:
                return dict(zip([r[0] for r in q.description], q.fetchone()))
            if not q.nextset():
                raise AssertionError('Missing bridge result')


def ready(data=None):
    data = data or payload()
    result = call(data)
    assert result['BridgeStatus'] == 'ready', result
    return dict(data, validation_token=result['ValidationToken'])


def unchanged():
    with connection() as c:
        for table in ['inv.tblVocherHdr', 'inv.tblVocherItm', 'dbo.tblVocherNo', 'NeginAI.InterwarehouseCreditAudit']:
            assert c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
        assert [tuple(r) for r in c.execute('SELECT StockDCRef,OnHandQty FROM gnr.tblStockGoods ORDER BY StockDCRef')] == [(1,20),(2,999)]


def test_preflight_is_read_only():
    assert ready()['validation_token']
    unchanged()


def test_confirmed_credit_changes_source_only_and_replays_once():
    data = ready(); key = uuid4()
    first = call(data, True, key); again = call(data, True, key)
    assert first['BridgeStatus'] == 'sent' and first['Confirmed'] == 1, first
    assert again['VocherId'] == first['VocherId'] and again['Replayed'] == 1
    with connection() as c:
        assert tuple(c.execute('SELECT VocherTypeCode,HealthCodeType,HealthCode,StockDCRef,TStockDCRef,ConfirmedBy FROM inv.tblVocherHdr').fetchone()) == (65,1047,1,2,1,10)
        assert [tuple(r) for r in c.execute('SELECT StockDCRef,OnHandQty FROM gnr.tblStockGoods ORDER BY StockDCRef')] == [(1,20),(2,984)]
        assert c.execute('SELECT COUNT(*) FROM NeginAI.InterwarehouseCreditAudit').fetchone()[0] == 1


@pytest.mark.parametrize('switch,code', [('ConfirmError',51518),('WrongSourceDelta',51521),('DestinationChanged',51521),('CreateDebit',51521),('MissingConfirmation',51519)])
def test_native_confirmation_error_rolls_back_header_items_stock_audit_and_counter(switch, code):
    data = ready()
    with connection() as c:
        c.execute(f'UPDATE dbo.CreditTestSwitch SET {switch}=1')
    result = call(data, True)
    assert result['BridgeStatus'] == 'rejected' and result['ErrorCode'] == code, result
    unchanged()


@pytest.mark.parametrize('change', ['UPDATE NeginAI.InterwarehouseCreditPolicy SET Enabled=0',
                                   'UPDATE NeginAI.InterwarehouseCreditPolicy SET IsolatedValidationComplete=0',
                                   'UPDATE dbo.AppUser SET IsActive=0'])
def test_disabled_policy_cannot_commit(change):
    data = ready()
    with connection() as c:
        c.execute(change)
    assert call(data, True)['BridgeStatus'] == 'blocked'
    unchanged()


@pytest.mark.parametrize('sql,code', [
    ("UPDATE gnr.tblGeneralConfig SET KeyValue='1' WHERE KeyName='CreateVocher15'",51504),
    ("DELETE FROM gnr.tblGeneralConfig WHERE KeyName='CreateVocher15'",51504),
    ("UPDATE gnr.tblServerConfig SET KeyValue='0' WHERE KeyName='IsConfirmVchEffectiveonOnHandQty'",51504),
    ('UPDATE gnr.tblOprDate SET IsClosed=1',51507),
    ('INSERT inv.tblStCountHdr VALUES(1,1405,0)',51508),
    ('UPDATE gnr.tblStockGoods SET IsBatch=1',51514),
    ('UPDATE gnr.tblGoods SET SerialNo=1',51511),
    ('UPDATE gnr.tblPackage SET ForInv=0',51512),
    ('UPDATE gnr.tblStockGoods SET OnHandQty=10 WHERE StockDCRef=2',51515),
])
def test_native_business_guards(sql,code):
    with connection() as c:
        c.execute(sql)
    result=call(payload(),True)
    assert result['BridgeStatus']=='rejected' and result['ErrorCode']==code,result
    with connection() as c:
        assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==0


@pytest.mark.parametrize('quantity',[0,-1,0.0001,2.5,None,'n/a',1000000001])
def test_invalid_quantities_never_round_or_disappear(quantity):
    assert call(payload(lines=[dict(product_code='00123',quantity=quantity)]),True)['BridgeStatus']=='rejected'
    unchanged()


def test_changed_mapping_requires_new_validation():
    data=ready();data['voucher_date']='1405/06/21'
    assert call(data,True)['ErrorCode']==51516
    unchanged()


@pytest.mark.parametrize('lines',[[],{'0':dict(product_code='00123',quantity=1)},[dict(product_code='00123',quantity=1)]*2,[dict(product_code='x'*81,quantity=1)]])
def test_malformed_or_duplicate_lines_fail_closed(lines):
    assert call(payload(lines=lines),True)['BridgeStatus']=='rejected'
    unchanged()


@pytest.mark.parametrize('change',['item','header','delete','payload','unit_ref','unit_capacity','unit_quantity'])
def test_changed_existing_document_is_blocked_without_reposting(change):
    data=ready();key=uuid4();first=call(data,True,key)
    with connection() as c:
        if change=='item':c.execute('UPDATE inv.tblVocherItm SET TotalQty=TotalQty+1')
        if change=='header':c.execute('UPDATE inv.tblVocherHdr SET ConfirmedBy=NULL,ConfirmDate=NULL')
        if change=='delete':c.execute('DELETE FROM inv.tblVocherItm;DELETE FROM inv.tblVocherHdr')
        if change=='unit_ref':c.execute('UPDATE inv.tblVocherItm SET UnitRef=999')
        if change=='unit_capacity':c.execute('UPDATE inv.tblVocherItm SET UnitCapacity=12')
        if change=='unit_quantity':c.execute('UPDATE inv.tblVocherItm SET UnitQty=0')
    if change=='payload':data['lines'][0]['quantity']=16
    assert call(data,True,key)['BridgeStatus']=='blocked'
    with connection() as c:
        assert c.execute('SELECT VocherNo FROM dbo.tblVocherNo').fetchone()[0]==first['VocherNo']
        assert c.execute('SELECT COUNT(*) FROM NeginAI.InterwarehouseCreditAudit').fetchone()[0]==1


def test_concurrent_same_key_and_different_key_same_document_cannot_duplicate():
    data=ready();key=uuid4()
    with ThreadPoolExecutor(4) as pool:
        results=list(pool.map(lambda _:call(data,True,key),range(4)))
    assert all(r['BridgeStatus']=='sent' for r in results),results
    assert len({r['VocherId'] for r in results})==1
    assert call(data,True)['BridgeStatus']=='blocked'
