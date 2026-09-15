"""Opt-in real SQL tests with synthetic data, never a restored business database.

NEGIN_RECEIPT_SQL_TEST=1 creates precisely NeginAI_CheckbarBridge_Test locally,
refuses to reuse an existing database, and drops only the database it created.
No SQL login, server grant, production schema, or real document is changed.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
from uuid import uuid4
import pytest
import pyodbc

NAME='NeginAI_CheckbarBridge_Test'
BASE='DRIVER={ODBC Driver 18 for SQL Server};SERVER=127.0.0.1;Trusted_Connection=yes;TrustServerCertificate=yes;'
pytestmark=pytest.mark.skipif(os.getenv('NEGIN_RECEIPT_SQL_TEST')!='1',reason='opt-in isolated SQL fixture')


def batches(conn,path):
    for batch in re.split(r'^GO\s*$',Path(path).read_text(encoding='utf-8'),flags=re.M|re.I):
        if batch.strip():conn.cursor().execute(batch)


@pytest.fixture(scope='module')
def db():
    master=pyodbc.connect(BASE+'DATABASE=master;',autocommit=True,timeout=5)
    assert master.cursor().execute('SELECT DB_ID(?)',NAME).fetchone()[0] is None, 'Refuse to touch an existing database'
    master.cursor().execute(f'CREATE DATABASE [{NAME}] COLLATE Persian_100_CI_AS')
    try:
        c=pyodbc.connect(BASE+f'DATABASE={NAME};',autocommit=True,timeout=5)
        try:
            assert c.cursor().execute('SELECT DB_NAME()').fetchone()[0]==NAME
            batches(c,'tests/fixtures/checkbar_receipt/synthetic_schema.sql')
            batches(c,'scripts/sql/install_checkbar_receipt_bridge.sql')
        finally:c.close()
        yield
    finally:
        # Constant literal target and verified creation above; never use discovered DB names.
        master.cursor().execute(f'ALTER DATABASE [{NAME}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE')
        master.cursor().execute(f'DROP DATABASE [{NAME}]')
        master.close()


@contextmanager
def connection():
    c=pyodbc.connect(BASE+f'DATABASE={NAME};',autocommit=True,timeout=10)
    try:yield c
    finally:c.close()


@pytest.fixture(autouse=True)
def seed(db):
    with connection() as c:
        for table in ['NeginAI.CheckbarReceiptAudit','inv.tblVocherItm','inv.tblVocherHdr','dbo.tblVocherNo',
                      'NeginAI.ReceiptBridgePolicy','dbo.AppUser','gnr.tblAccYear','gnr.tblStockDC',
                      'gnr.tblOprDate','inv.tblStCountHdr','gnr.tblGoods','gnr.tblSupplier','gnr.tblGoodsSupplier',
                      'gnr.tblStockGoods','gnr.tblPackage','SLE.tblGoodsNoSale']:
            c.execute(f'DELETE FROM {table}')
        c.execute('''INSERT dbo.AppUser VALUES(10,1,0);
            INSERT NeginAI.ReceiptBridgePolicy VALUES(ORIGINAL_LOGIN(),1,10,1);
            INSERT gnr.tblAccYear VALUES(1405,'1405/01/01','1405/12/29');
            INSERT gnr.tblStockDC VALUES(1,1,NULL);
            INSERT gnr.tblOprDate VALUES(1405,1,1,0,'1405/01/01','1405/06/15');
            INSERT gnr.tblGoods VALUES(100,'00123',1,1,0,0);
            INSERT gnr.tblSupplier VALUES(7,N'supplier',1);
            INSERT gnr.tblGoodsSupplier VALUES(100,7);
            INSERT gnr.tblStockGoods(GoodsRef,StockDCRef,AccYear,IsBatch,OnHandQty) VALUES(100,1,1405,0,999);
            INSERT gnr.tblPackage VALUES(100,1,1,1,1);
            UPDATE dbo.TestSwitch SET ValidationError=0,ForceConfirmed=0,CorruptItem=0,ChangeStock=0;''')


def payload(**updates):
    return dict(stock_dc_ref=1,supplier_name='supplier',supplier_refs=[7],voucher_date='1405/06/15',
                reference_no='1490',comment='CB-000001 / v0',**updates)


@pytest.mark.parametrize('reference',[None,'','0','-1','INV-12','1.5','2147483648'])
def test_reference_required_for_editable_healthy_receipt(reference):
    data=payload(lines=[line()]);data['reference_no']=reference
    result=call(data)
    assert result['BridgeStatus']=='rejected' and result['ErrorCode']==51123
    empty()


def test_supplier_reference_reaches_native_editor_field():
    data=ready(payload(lines=[line()]));result=call(data,True)
    assert result['BridgeStatus']=='sent'
    with connection() as c:
        # Vocher20Helper.SetItemEnable requires StockDCRef, SupplierRef and
        # TVocherNo for a healthy receipt with no PurchaseOrderRef.
        assert tuple(c.execute('SELECT StockDCRef,SupplierRef,TVocherNo,PurchaseOrderRef,HealthCode,ConfirmedBy,ConfirmDate FROM inv.tblVocherHdr').fetchone())==(1,7,1490,None,1,None,None)


def test_changing_supplier_reference_requires_fresh_sql_preflight():
    data=ready(payload(lines=[line()]));data['reference_no']='1491'
    result=call(data,True)
    assert result['BridgeStatus']=='rejected' and result['ErrorCode']==51121
    empty()


def line(qty='15',comment='180000-120000'):
    return dict(product_code='00123',quantity=qty,item_comment=comment)


def call(data,commit=False,key=None):
    with connection() as c:
        q=c.cursor();q.execute('EXEC NeginAI.usp_CreateCheckbarReceipt @TransferKey=?,@RequestedBy=?,@PayloadJson=?,@Commit=?',
            str(key or uuid4()),'tester',json.dumps(data,ensure_ascii=False),commit)
        while True:
            if q.description and 'BridgeStatus' in [r[0] for r in q.description]:
                return dict(zip([r[0] for r in q.description],q.fetchone()))
            if not q.nextset():raise AssertionError('missing bridge response')


def ready(data):
    result=call(data)
    assert result['BridgeStatus']=='ready',result
    return dict(data,validation_token=result['ValidationToken'])


def empty():
    with connection() as c:
        assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM inv.tblVocherItm').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM dbo.tblVocherNo').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM NeginAI.CheckbarReceiptAudit').fetchone()[0]==0
        assert c.execute('SELECT OnHandQty FROM gnr.tblStockGoods').fetchone()[0]==999


def test_preflight_does_not_allocate_or_create():
    assert ready(payload(lines=[line()]))['validation_token']
    empty()


def test_official_allocator_unconfirmed_header_item_comments_and_duplicate_replay():
    data=ready(payload(lines=[line(),line('3'),line('2','200000-130000')]))
    key=uuid4();a=call(data,True,key);b=call(data,True,key)
    assert a['BridgeStatus']=='sent',a
    assert a['VocherNo']==1 and b['VocherId']==a['VocherId'] and b['Replayed']
    with connection() as c:
        assert tuple(c.execute('SELECT VocherTypeCode,HealthCodeType,HealthCode,ConfirmedBy,ConfirmDate,DocRef,PurchaseOrderRef FROM inv.tblVocherHdr').fetchone())==(20,12,1,None,None,None,None)
        items=c.execute('SELECT TotalQty,UnitQty,UnitCapacity,Comment,ValuePrice FROM inv.tblVocherItm ORDER BY TotalQty').fetchall()
        assert [tuple(r) for r in items]==[(2,2,1,'200000-130000',None),(18,18,1,'180000-120000',None)]
        assert c.execute('SELECT OnHandQty FROM gnr.tblStockGoods').fetchone()[0]==999
        assert c.execute('SELECT COUNT(*) FROM NeginAI.CheckbarReceiptAudit').fetchone()[0]==1


@pytest.mark.parametrize('sql,code',[
    ('UPDATE NeginAI.ReceiptBridgePolicy SET Enabled=0',51103),
    ('UPDATE dbo.AppUser SET IsActive=0',51103),
    ('UPDATE gnr.tblOprDate SET IsClosed=1',51106),
    ('UPDATE gnr.tblOprDate SET LastDate=\'1405/06/15\'',51106),
    ('INSERT inv.tblStCountHdr VALUES(1,1405,0)',51107),
    ('UPDATE gnr.tblGoods SET GoodsCode=\'OTHER\'',51110),
    ('DELETE FROM gnr.tblGoodsSupplier',51111),
    ('UPDATE gnr.tblSupplier SET Active=0',51111),
    ('UPDATE gnr.tblStockGoods SET IsBatch=1',51113),
    ('UPDATE gnr.tblGoods SET SerialNo=1',51114),
    ('UPDATE gnr.tblGoods SET GoodsTypeRef=2',51114),
    ('UPDATE gnr.tblPackage SET ForInv=0',51115),
    ("INSERT SLE.tblGoodsNoSale VALUES(100,NULL,4,'1405/01/01',NULL)",51116),
])
def test_mandatory_business_validation(sql,code):
    with connection() as c:c.execute(sql)
    result=call(payload(lines=[line()]),True)
    assert result['BridgeStatus']=='rejected' and result['ErrorCode']==code,result
    empty()


@pytest.mark.parametrize('qty',['0','-1',None,'0.0001','2.5'])
def test_bad_quantity_is_never_silently_removed_or_rounded(qty):
    assert call(payload(lines=[line(qty)]),True)['BridgeStatus']=='rejected'
    empty()


@pytest.mark.parametrize('switch,code',[('ValidationError',51120),('ForceConfirmed',51118),('CorruptItem',51119),('ChangeStock',51122)])
def test_failure_after_native_insert_rolls_back_receipt_audit_and_number(switch,code):
    data=ready(payload(lines=[line()]))
    with connection() as c:c.execute(f'UPDATE dbo.TestSwitch SET {switch}=1')
    result=call(data,True)
    assert result['BridgeStatus']=='rejected' and result['ErrorCode']==code,result
    empty()


def test_mapping_change_between_preview_and_send_requires_new_preview():
    data=ready(payload(lines=[line()]))
    with connection() as c:c.execute('UPDATE dbo.AppUser SET AppUserId=11; UPDATE NeginAI.ReceiptBridgePolicy SET AppUserId=11;')
    result=call(data,True)
    assert result['ErrorCode']==51121,result
    empty()


def test_parallel_duplicate_and_first_number_requests():
    data=ready(payload(lines=[line()]));key=uuid4()
    with ThreadPoolExecutor(4) as pool:results=list(pool.map(lambda _:call(data,True,key),range(4)))
    assert all(r['BridgeStatus']=='sent' for r in results),results
    assert len({r['VocherId'] for r in results})==1
    with ThreadPoolExecutor(4) as pool:results=list(pool.map(lambda _:call(data,True),range(4)))
    assert all(r['BridgeStatus']=='sent' for r in results),results
    assert sorted(r['VocherNo'] for r in results)==[2,3,4,5]


def test_parallel_first_use_of_missing_counter():
    data=ready(payload(lines=[line()]))
    with ThreadPoolExecutor(4) as pool:results=list(pool.map(lambda _:call(data,True),range(4)))
    assert all(r['BridgeStatus']=='sent' for r in results),results
    assert sorted(r['VocherNo'] for r in results)==[1,2,3,4]


def test_missing_counter_initializes_from_existing_receipts():
    data=ready(payload(lines=[line()]));assert call(data,True)['BridgeStatus']=='sent'
    with connection() as c:c.execute('DELETE FROM dbo.tblVocherNo; UPDATE inv.tblVocherHdr SET VocherNo=45;')
    result=call(data,True)
    assert result['BridgeStatus']=='sent' and result['VocherNo']==46,result


def test_confirmed_or_deleted_existing_receipt_cannot_be_recreated():
    data=ready(payload(lines=[line()]));key=uuid4();a=call(data,True,key)
    with connection() as c:c.execute('UPDATE inv.tblVocherHdr SET ConfirmedBy=10,ConfirmDate=GETDATE()')
    assert call(data,True,key)['BridgeStatus']=='blocked'
    with connection() as c:c.execute('DELETE FROM inv.tblVocherItm;DELETE FROM inv.tblVocherHdr;')
    assert call(data,True,key)['BridgeStatus']=='blocked'
    with connection() as c:assert c.execute('SELECT VocherNo FROM dbo.tblVocherNo').fetchone()[0]==a['VocherNo']


def replacement(data,key,result):
    return dict(data,root_transfer_key=str(key),replaces_receipts=[dict(transfer_key=str(key),vocher_id=result['VocherId'])])


def test_deleted_receipt_replacement_new_number_and_idempotent_recovery():
    data=ready(payload(checkbar_number='CB-000001',lines=[line()]));key=uuid4()
    first=call(data,True,key)
    next_data=replacement(data,key,first)
    assert call(next_data)['ErrorCode']==51125  # Even an unconfirmed receipt locks replacement.
    with connection() as c:c.execute('DELETE FROM inv.tblVocherItm;DELETE FROM inv.tblVocherHdr;')
    next_data=ready(next_data);new_key=uuid4();second=call(next_data,True,new_key)
    assert second['BridgeStatus']=='sent' and second['VocherNo']==first['VocherNo']+1
    assert call(next_data,False,new_key)['ReplacementSupported']==1
    assert call(next_data,True,new_key)['VocherId']==second['VocherId']
    with connection() as c:
        assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM NeginAI.CheckbarReceiptAudit').fetchone()[0]==2
        assert c.execute('SELECT OnHandQty FROM gnr.tblStockGoods').fetchone()[0]==999


@pytest.mark.parametrize('change',['wrong_number','missing_number','unknown_key','wrong_id','orphan_items'])
def test_replacement_rejects_invalid_history_and_orphan_items(change):
    data=ready(payload(checkbar_number='CB-000001',lines=[line()]));key=uuid4();first=call(data,True,key)
    new_data=replacement(data,key,first)
    with connection() as c:
        if change!='orphan_items':c.execute('DELETE FROM inv.tblVocherItm')
        c.execute('DELETE FROM inv.tblVocherHdr')
    if change=='wrong_number':new_data['checkbar_number']='CB-OTHER'
    if change=='missing_number':new_data.pop('checkbar_number')
    if change=='unknown_key':new_data['replaces_receipts'][0]['transfer_key']=str(uuid4())
    if change=='wrong_id':new_data['replaces_receipts'][0]['vocher_id']=99999
    result=call(new_data,True)
    assert result['BridgeStatus']=='rejected' and result['ErrorCode']==(51125 if change=='orphan_items' else 51124),result
    with connection() as c:assert c.execute('SELECT COUNT(*) FROM NeginAI.CheckbarReceiptAudit').fetchone()[0]==1


def test_two_competing_replacements_create_only_one_receipt_and_require_complete_history():
    data=ready(payload(checkbar_number='CB-000001',lines=[line()]));key=uuid4();first=call(data,True,key)
    with connection() as c:c.execute('DELETE FROM inv.tblVocherItm;DELETE FROM inv.tblVocherHdr;')
    data=ready(replacement(data,key,first))
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:call(data,True),range(2)))
    assert sorted(r['BridgeStatus'] for r in results)==['rejected','sent'],results
    with connection() as c:
        assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==1
        c.execute('DELETE FROM inv.tblVocherItm;DELETE FROM inv.tblVocherHdr;')
    # Omitting the second generation is forbidden even once it too is absent.
    assert call(data,True)['ErrorCode']==51124
