"""Atomic receipt/reservation SQL tests, same disposable loopback database as v1."""
import json
from uuid import uuid4
import pytest
from test_checkbar_receipt_sql import db, seed, connection, batches, payload, line, empty, pytestmark


@pytest.fixture(autouse=True)
def price_schema(seed):
    with connection() as c:
        if c.execute("SELECT SCHEMA_ID('FRU')").fetchone()[0] is None:
            c.execute('CREATE SCHEMA FRU')
            c.execute('CREATE TABLE gnr.tblGeneralConfig(KeyName varchar(100),KeyValue varchar(100))')
            c.execute('CREATE TABLE gnr.tblServerConfig(KeyName varchar(100),KeyValue varchar(100))')
            c.execute("INSERT gnr.tblGeneralConfig VALUES('ConfirmVochersBeforeCloseDate','1'); INSERT gnr.tblServerConfig VALUES('IsConfirmVchEffectiveonOnHandQty','1')")
            c.execute('CREATE TABLE dbo.PriceTestSwitch(FailReserve bit); INSERT dbo.PriceTestSwitch VALUES(0)')
            # Native confirmation is separately tested in the retained native clone.
            c.execute('''CREATE PROCEDURE FRU.usp_VocherConfirmation @AccYear int,@DCRef int,@UserRef int,
                @VocherHdrRef int,@IsConfirm bit,@ErrMsg nvarchar(max) OUTPUT,@ResultMsg varchar(max) OUTPUT AS
                BEGIN
                  SET NOCOUNT ON;
                  IF EXISTS(SELECT 1 FROM inv.tblVocherHdr WHERE ID=@VocherHdrRef AND VocherTypeCode=76)
                    AND EXISTS(SELECT 1 FROM dbo.PriceTestSwitch WHERE FailReserve=1)
                  BEGIN SET @ErrMsg='reserve failed';RETURN;END;
                  UPDATE S SET OnHandQty=OnHandQty+Q.Qty*CASE H.VocherTypeCode WHEN 76 THEN -1 ELSE 1 END,
                    ReservedQty=ReservedQty+CASE H.VocherTypeCode WHEN 76 THEN Q.Qty ELSE 0 END
                  FROM gnr.tblStockGoods S JOIN inv.tblVocherHdr H ON H.ID=@VocherHdrRef AND H.StockDCRef=S.StockDCRef AND H.AccYear=S.AccYear
                  CROSS APPLY(SELECT SUM(TotalQty) Qty FROM inv.tblVocherItm WHERE HdrRef=H.ID AND GoodsRef=S.GoodsRef) Q
                  WHERE Q.Qty IS NOT NULL;
                  UPDATE inv.tblVocherHdr SET ConfirmedBy=@UserRef,ConfirmDate=GETDATE() WHERE ID=@VocherHdrRef;
                  SET @ErrMsg=N'';SET @ResultMsg='';
                END''')
        batches(c,'scripts/sql/install_checkbar_receipt_price_bridge.sql')
        c.execute('DELETE NeginAI.CheckbarReceiptBundleAudit; DELETE NeginAI.ReceiptPricePolicy; UPDATE dbo.PriceTestSwitch SET FailReserve=0')
        c.execute('INSERT NeginAI.ReceiptPricePolicy VALUES(ORIGINAL_LOGIN(),1,1)')


def priced(mode='changed',qty='15'):
    old=('0','0') if mode=='unpriced' else ('200','100')
    new=('300','150') if mode=='changed' else old
    return dict(line(qty,'-'.join(new)),price_mode=mode,consumer_price_current=old[0],manufacturer_price_current=old[1],
                consumer_price_effective=new[0],manufacturer_price_effective=new[1])


def call(data,commit=False,key=None):
    with connection() as c:
        q=c.cursor();q.execute('EXEC NeginAI.usp_CreateCheckbarReceiptV2 @TransferKey=?,@RequestedBy=?,@PayloadJson=?,@Commit=?',
            str(key or uuid4()),'tester',json.dumps(data,ensure_ascii=False),commit)
        while True:
            if q.description and 'BridgeStatus' in [r[0] for r in q.description]:
                return dict(zip([r[0] for r in q.description],q.fetchone()))
            if not q.nextset():raise AssertionError('missing response')


def ready(lines):
    data=payload(price_workflow_version=2,checkbar_number='CB-PRICE-TEST',lines=lines)
    result=call(data)
    assert result['BridgeStatus']=='ready',result
    return dict(data,validation_token=result['ValidationToken'])


def test_three_routes_atomic_stock_and_replay():
    with connection() as c:
        for ident,code in [(101,'002'),(102,'003')]:
            c.execute('INSERT gnr.tblGoods VALUES(?,?,1,1,0,0)',ident,code)
            c.execute('INSERT gnr.tblGoodsSupplier VALUES(?,7)',ident)
            c.execute('INSERT gnr.tblStockGoods(GoodsRef,StockDCRef,AccYear,IsBatch,OnHandQty) VALUES(?,1,1405,0,999)',ident)
            c.execute('INSERT gnr.tblPackage VALUES(?,1,1,1,1)',ident)
    data=ready([priced('changed','15'),dict(priced('unchanged','3'),product_code='002'),dict(priced('unpriced','2'),product_code='003')]);empty()
    key=uuid4();result=call(data,True,key)
    assert result['BridgeStatus']=='sent',result
    docs=json.loads(result['DocumentsJson'])
    assert {(d['Role'],d['VocherTypeCode'],d['Confirmed']) for d in docs}=={
        ('confirmed_receipt',20,True),('price_reserve',76,True),('unpriced_receipt',20,False)}
    with connection() as c:
        assert [tuple(r) for r in c.execute('SELECT OnHandQty,ReservedQty FROM gnr.tblStockGoods ORDER BY GoodsRef')]==[(999,15),(1002,0),(999,0)]
        reserve=c.execute("SELECT I.TotalQty,I.Comment,H.Comment FROM inv.tblVocherItm I JOIN inv.tblVocherHdr H ON H.ID=I.HdrRef WHERE H.VocherTypeCode=76").fetchone()
        assert (reserve[0],reserve[1],reserve[2].replace('ي','ی').replace('ك','ک'))==(15,'300-150','بابت تغییر قیمت')
    replay=call(data,True,key)
    assert replay['Replayed'] and replay['DocumentsJson']==result['DocumentsJson']
    with connection() as c:
        assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==3
        assert [tuple(r) for r in c.execute('SELECT OnHandQty,ReservedQty FROM gnr.tblStockGoods ORDER BY GoodsRef')]==[(999,15),(1002,0),(999,0)]


@pytest.mark.parametrize('mode,count,healthy,reserved',[('changed',2,999,15),('unchanged',1,1014,0),('unpriced',1,999,0)])
def test_single_price_category(mode,count,healthy,reserved):
    result=call(ready([priced(mode)]),True)
    assert result['BridgeStatus']=='sent',result
    with connection() as c:
        assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==count
        assert tuple(c.execute('SELECT OnHandQty,ReservedQty FROM gnr.tblStockGoods').fetchone())==(healthy,reserved)


def test_reservation_failure_rolls_back_receipt_confirmation_stock_counter_and_audit():
    data=ready([priced()])
    with connection() as c:c.execute('UPDATE dbo.PriceTestSwitch SET FailReserve=1')
    result=call(data,True)
    assert result['BridgeStatus']=='rejected',result
    empty()
    with connection() as c:assert c.execute('SELECT COUNT(*) FROM NeginAI.CheckbarReceiptBundleAudit').fetchone()[0]==0


def test_price_mode_and_fresh_preflight_cannot_be_forged():
    data=ready([priced()]);data['lines'][0]['price_mode']='unpriced'
    assert call(data,True)['BridgeStatus']=='rejected';empty()
    data=ready([priced()]);data['lines'][0]=priced('unchanged')
    assert call(data,True)['ErrorCode']==51121;empty()


def test_deleted_reserve_never_recreates_receipt_on_retry():
    data=ready([priced()]);key=uuid4();result=call(data,True,key)
    assert result['BridgeStatus']=='sent'
    with connection() as c:c.execute('DELETE inv.tblVocherHdr WHERE VocherTypeCode=76')
    assert call(data,True,key)['BridgeStatus']=='blocked'
    with connection() as c:assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==1


def test_changed_reservation_items_block_retry_without_new_documents():
    data=ready([priced()]);key=uuid4();assert call(data,True,key)['BridgeStatus']=='sent'
    with connection() as c:
        c.execute("UPDATE I SET Comment='altered' FROM inv.tblVocherItm I JOIN inv.tblVocherHdr H ON H.ID=I.HdrRef WHERE H.VocherTypeCode=76")
    assert call(data,True,key)['BridgeStatus']=='blocked'
    with connection() as c:assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==2


def test_changed_reserve_header_blocks_retry():
    data=ready([priced()]);key=uuid4();assert call(data,True,key)['BridgeStatus']=='sent'
    with connection() as c:c.execute("UPDATE inv.tblVocherHdr SET Comment='changed' WHERE VocherTypeCode=76")
    assert call(data,True,key)['BridgeStatus']=='blocked'


def test_concurrent_retries_create_exactly_one_bundle():
    from concurrent.futures import ThreadPoolExecutor
    data=ready([priced()]);key=uuid4()
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda _:call(data,True,key),range(3)))
    assert all(r['BridgeStatus']=='sent' for r in results)
    assert len({r['VocherId'] for r in results})==1
    with connection() as c:
        assert c.execute('SELECT COUNT(*) FROM inv.tblVocherHdr').fetchone()[0]==2
        assert tuple(c.execute('SELECT OnHandQty,ReservedQty FROM gnr.tblStockGoods').fetchone())==(999,15)


def test_replacement_requires_all_prior_receipts_and_reserve_to_be_absent():
    data=ready([priced()]);key=uuid4();old=call(data,True,key)
    new=dict(data,root_transfer_key=str(key),replaces_receipts=[dict(transfer_key=str(key),vocher_id=old['VocherId'])])
    assert call(new)['ErrorCode']==51125
    with connection() as c:
        c.execute('DELETE I FROM inv.tblVocherItm I JOIN inv.tblVocherHdr H ON H.ID=I.HdrRef WHERE H.VocherTypeCode=20')
        c.execute('DELETE inv.tblVocherHdr WHERE VocherTypeCode=20')
    assert call(new)['ErrorCode']==51125
    with connection() as c:c.execute('DELETE inv.tblVocherItm; DELETE inv.tblVocherHdr')
    result=call(new);assert result['BridgeStatus']=='ready',result
    new['validation_token']=result['ValidationToken']
    assert call(new,True)['BridgeStatus']=='sent'
    assert call(new)['ErrorCode']==51124  # The retained chain now has a second generation.
