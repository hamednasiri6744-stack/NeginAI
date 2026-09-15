"""ERP handover uses the same stock snapshot; no native writes in these tests."""
from contextlib import contextmanager
from dataclasses import replace
import sqlite3
import pytest
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_transfer_bridge import credit, request, sent
from test_warehouse_transfer_reflection import snapshot
from app import warehouse_assistant_service as service
from app import warehouse_transfer_bridge as bridge
from app import warehouse_transfer_reflection as reflection
from app import warehouse_rebalancing as ledger
from app import warehouse_native_transit as native
from app.warehouse_fulfillment import supply_position


def line(**changes):
    return dict(voucher_id=501,transfer_key='native',voucher_no=71,source_ref=2,
                destination_ref=1,product_code='00123',quantity=12,confirmed=1,
                received=0,pending_receipt=0,**changes)


def publish(credit, rows, *, posted=True):
    b,doc,_,remote=credit
    if posted:
        req=request(credit);remote.return_value=sent();bridge.submit(b.settings,'test-user',doc,req)
    snapshot(b)
    with service.warehouse_connection(b.settings) as c:
        captured=reflection.capture(c)
        if captured:
            for r in rows:
                if r['voucher_id']==501:r['transfer_key']=captured[0]['transfer_key']
        native.apply(c,rows,captured,2)
    return b,doc


def test_internal_before_snapshot_then_native_once(credit):
    b,doc,_,remote=credit
    with service.warehouse_connection(b.settings) as c:
        assert ledger.reservations(c,'tehran')[1]=={'00123':12}
        assert supply_position(c,'karaj')[0]=={'00123':12}
    req=request(credit);remote.return_value=sent();bridge.submit(b.settings,'test-user',doc,req)
    with service.warehouse_connection(b.settings) as c:
        # Old stock still needs the old overlay until the coherent refresh publishes.
        assert supply_position(c,'karaj')[0]=={'00123':12}
    publish(credit,[line()],posted=False)
    with service.warehouse_connection(b.settings) as c:
        assert ledger.reservations(c,'tehran')[1]=={}
        assert ledger.reservations(c,'karaj')[0]=={}
        assert supply_position(c,'karaj')[0]=={'00123':12}


@pytest.mark.parametrize('received,pending,expected',[(0,12,12),(5,7,7),(12,0,0)])
def test_receipts_reduce_only_confirmed_quantity(credit,received,pending,expected):
    row=line();row.update(received=received,pending_receipt=pending)
    b,_=publish(credit,[row])
    with service.warehouse_connection(b.settings) as c:
        assert supply_position(c,'karaj')[0].get('00123',0)==expected


def test_external_erp_transfer_is_included_and_source_not_subtracted_twice(credit):
    extra=line();extra.update(voucher_id=900,transfer_key='external',quantity=24)
    b,_=publish(credit,[line(),extra])
    with service.warehouse_connection(b.settings) as c:
        assert supply_position(c,'karaj')[0]=={'00123':36}
        assert ledger.reservations(c,'tehran')[1]=={}


@pytest.mark.parametrize('rows',[[],[dict(line(),confirmed=0)]])
def test_deleted_or_unconfirmed_credit_does_not_restore_internal_overlay(credit,rows):
    b,_=publish(credit,rows)
    with service.warehouse_connection(b.settings) as c:
        assert ledger.reservations(c,'tehran')[1]=={}
        assert supply_position(c,'karaj')[0].get('00123',0)==0


def test_unknown_result_but_native_key_exists_never_double_counts(credit):
    b,doc,_,remote=credit;req=request(credit);remote.side_effect=TimeoutError()
    bridge.submit(b.settings,'test-user',doc,req)
    publish(credit,[line()],posted=False)
    with service.warehouse_connection(b.settings) as c:
        assert ledger.reservations(c,'karaj')[0]=={}
        assert supply_position(c,'karaj')[0]=={'00123':12}


def test_new_snapshot_without_native_evidence_never_reuses_old_erp_counts(credit):
    b,_=publish(credit,[line()])
    with service.warehouse_connection(b.settings) as c:
        row=dict(c.execute('SELECT * FROM warehouse_snapshots WHERE id=2').fetchone())
        row.update(id=3,content_sha256='new-without-native')
        c.execute(f'INSERT INTO warehouse_snapshots({",".join(row)}) VALUES({",".join("?" for _ in row)})',tuple(row.values()))
        assert native.position(c,'karaj')[0]=={}
        assert ledger.reservations(c,'karaj')[0]=={'00123':12}


def test_invalid_native_quantity_rolls_back_instead_of_publishing_partial_state(credit):
    b,doc,_,_=credit;snapshot(b)
    with service.warehouse_connection(b.settings) as c:
        c.execute('BEGIN IMMEDIATE')
        row=line();row['received']=-1
        with pytest.raises(service.WarehouseAssistantError):native.apply(c,[row],[],2)
        assert native.position(c,'karaj')[0]=={}


def test_overreceipt_blocks_ordering_for_affected_item(credit):
    row=line();row['received']=13;b,_=publish(credit,[row])
    with service.warehouse_connection(b.settings) as c:
        assert native.position(c,'karaj')[1]=={'00123'}


def test_snapshot_change_invalidates_supply_revision_even_without_internal_orders(credit):
    b,_=publish(credit,[line()])
    with service.warehouse_connection(b.settings) as c:
        before=supply_position(c,'karaj')[1]
        row=line();row.update(voucher_id=900,transfer_key='external',quantity=24)
        native.apply(c,[row],reflection.capture(c),2)
        assert supply_position(c,'karaj')[1]!=before


def test_post_refresh_failure_keeps_sent_and_never_retries_erp(credit,monkeypatch):
    b,doc,_,remote=credit
    b.settings.sql_configured=True
    monkeypatch.setattr(service,'sync_varanegar_snapshot',lambda *a,**kw: (_ for _ in ()).throw(OSError('secret')))
    result=native.refresh_after_post(b.settings,'test-user',{'status':'sent','result':sent()})
    assert result['status']=='sent' and result['inventory_sync']=='refresh_required'
    assert 'secret' not in str(result)
    remote.assert_not_called()


def test_post_refresh_uses_inventory_sync_not_automatic_purchase_generation(credit,monkeypatch):
    b,_,_,remote=credit;b.settings.sql_configured=True
    calls=[]
    monkeypatch.setattr(service,'sync_varanegar_snapshot',lambda *a,**kw: calls.append((a,kw)) or {'id':42})
    result=native.refresh_after_post(b.settings,'test-user',{'status':'sent'})
    assert result['inventory_snapshot_id']==42 and len(calls)==1
    assert native.refresh_after_post(b.settings,'test-user',{'status':'pending'})=={'status':'pending'}
    assert len(calls)==1;remote.assert_not_called()


@pytest.mark.parametrize('fail_publish',[False,True])
def test_actual_sync_publishes_stock_and_native_inbound_together(settings,monkeypatch,fail_publish):
    from test_warehouse_assistant import _FakeWarehouseConnection
    configured=replace(settings,sql_server='synthetic',sql_username='reader',sql_password='test')
    queries=[]
    @contextmanager
    def source(_):yield _FakeWarehouseConnection(queries)
    monkeypatch.setattr(service,'sql_connection',source)
    row=line();row.update(product_code='4014',quantity=24)
    def read(cursor,year):
        assert cursor.queries is queries
        assert queries[0]=='SET TRANSACTION ISOLATION LEVEL SNAPSHOT'
        assert 'FRU.StockGoodsModel' in queries[1]
        return [row]
    monkeypatch.setattr(native,'source_queries',read)
    original=native.apply
    def publish(*args):
        original(*args)
        if fail_publish:raise service.WarehouseAssistantError('native publish failure')
    monkeypatch.setattr(native,'apply',publish)
    if fail_publish:
        with pytest.raises(service.WarehouseAssistantError,match='native publish'):
            service.sync_varanegar_snapshot(configured,'tester')
        with service.warehouse_connection(configured) as c:
            assert c.execute('SELECT COUNT(*) FROM warehouse_snapshots').fetchone()[0]==0
            assert c.execute('SELECT COUNT(*) FROM warehouse_native_transit').fetchone()[0]==0
    else:
        service.sync_varanegar_snapshot(configured,'tester')
        item=service.build_suggestions(configured,warehouse='karaj',only_needed=False)['items'][0]
        assert item['in_transit_qty']==24
        assert item['inventory_position_qty']==44  # 10 on hand + 20 reserved - 10 demand + 24 native


def test_native_sql_joins_exact_receipt_and_sums_partial_lines_without_multiplication():
    with sqlite3.connect(':memory:') as c:
        c.execute("ATTACH DATABASE ':memory:' AS inv")
        c.execute("ATTACH DATABASE ':memory:' AS gnr")
        c.execute('CREATE TABLE inv.tblVocherHdr(ID,UniqueId,VocherNo,StockDCRef,TStockDCRef,AccYear,VocherTypeCode,HealthCode,ConfirmedBy,ConfirmDate,DocRef)')
        c.execute('CREATE TABLE inv.tblVocherItm(HdrRef,GoodsRef,TotalQty)')
        c.execute('CREATE TABLE gnr.tblGoods(ID,GoodsCode)')
        c.execute("INSERT INTO gnr.tblGoods VALUES(1,'00123')")
        c.executemany('INSERT INTO inv.tblVocherHdr VALUES(?,?,?,?,?,?,?,?,?,?,?)',[
            (501,'key',71,2,1,1405,65,1,2,'now',None),
            (601,'receipt',90,1,2,1405,15,1,2,'now',501),
            (602,'pending',91,1,2,1405,15,1,None,None,501),
            (603,'wrong destination',92,9,2,1405,15,1,2,'now',501),
            (604,'wrong year',93,1,2,1404,15,1,2,'now',501),
        ])
        c.executemany('INSERT INTO inv.tblVocherItm VALUES(?,?,?)',[(501,1,6),(501,1,6),(601,1,2),(601,1,3),(602,1,7),(603,1,12),(604,1,12)])
        class Cursor:
            def execute(self,sql):
                assert 'NOLOCK' not in sql
                self.cursor=c.execute(sql.replace('ISNULL(','IFNULL('));self.description=self.cursor.description
            def fetchall(self):return self.cursor.fetchall()
        result=native.source_queries(Cursor(),1405)
        assert len(result)==1
        assert (result[0]['quantity'],result[0]['received'],result[0]['pending_receipt'])==(12,5,7)


def test_changed_intent_during_native_snapshot_cannot_publish(credit):
    b,doc,_,remote=credit
    with service.warehouse_connection(b.settings) as c:captured=reflection.capture(c)
    req=request(credit);remote.return_value=sent();bridge.submit(b.settings,'test-user',doc,req)
    with service.warehouse_connection(b.settings) as c:
        with pytest.raises(service.WarehouseAssistantError):reflection.verify_current(c,captured)


def test_empty_native_handover_still_changes_supply_revision(credit):
    b,doc,_,remote=credit;req=request(credit);remote.return_value=sent();bridge.submit(b.settings,'test-user',doc,req)
    with service.warehouse_connection(b.settings) as c:before=supply_position(c,'karaj')[1]
    publish(credit,[],posted=False)
    with service.warehouse_connection(b.settings) as c:
        quantities,revision=supply_position(c,'karaj')
        assert quantities=={} and revision!=before
