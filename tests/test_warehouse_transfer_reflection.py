import json
from unittest.mock import Mock
import pytest
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_transfer_bridge import credit, request, sent
from app import warehouse_transfer_bridge as bridge
from app import warehouse_transfer_reflection as reflection
from app import warehouse_transfer_lifecycle as lifecycle
from app import warehouse_rebalancing as ledger
from app import warehouse_assistant_service as service
from app.warehouse_order_receipts import pending_stock


def snapshot(b):
    with service.warehouse_connection(b.settings) as c:
        row=dict(c.execute('SELECT * FROM warehouse_snapshots WHERE id=1').fetchone())
        row.update(id=2,source_kind='varanegar',period_end='1405/06/22',content_sha256='credit-reflection')
        c.execute(f'INSERT INTO warehouse_snapshots({",".join(row)}) VALUES({",".join("?" for _ in row)})',tuple(row.values()))
        for item in c.execute('SELECT * FROM warehouse_snapshot_items WHERE snapshot_id=1').fetchall():
            d=dict(item);d.pop('id',None);d['snapshot_id']=2
            if d['warehouse_code']=='tehran':d['stock']-=12
            c.execute(f'INSERT INTO warehouse_snapshot_items({",".join(d)}) VALUES({",".join("?" for _ in d)})',tuple(d.values()))


def evidence(row):
    p=json.loads(row['payload_json'])
    return dict(headers=[dict(ID=501,UniqueId=row['transfer_key'],VocherNo=71,StockDCRef=2,TStockDCRef=1,
        AccYear=1405,VocherTypeCode=65,HealthCodeType=1047,HealthCode=1,VocherDate=p['voucher_date'],ConfirmedBy=2,ConfirmDate='now')],
        items=[dict(GoodsCode='00123',UnitRef=1,BasicUnitRef=1,UnitCapacity=1,UnitQty=12,TotalQty=12)])


def test_source_leg_stops_double_subtraction_destination_remains_inbound(credit):
    b,doc,_,remote=credit;req=request(credit);remote.return_value=sent();bridge.submit(b.settings,'test-user',doc,req)
    with service.warehouse_connection(b.settings) as c:
        assert pending_stock(c,'tehran')[1]=={'00123'}
        assert pending_stock(c,'karaj')[1]=={'00123'}
    snapshot(b)
    with service.warehouse_connection(b.settings) as c:
        captured=reflection.capture(c);detail=evidence(captured[0])
        status,message=reflection._classify(captured[0],detail,True)
        assert status=='reflected'
        reflection.apply(c,captured,{doc:dict(detail,status=status,message=message)},2)
        assert ledger.reservations(c,'tehran')[1]=={}
        assert ledger.reservations(c,'karaj')[0]=={'00123':12}
        assert pending_stock(c,'tehran')[1]==set()
        assert pending_stock(c,'karaj')[1]==set()
        # A later native unconfirmation is not inferred away from unrelated stock.
        detail['headers'][0]['ConfirmedBy']=None
        state,message=reflection._classify(captured[0],detail,True)
        reflection.apply(c,captured,{doc:dict(detail,status=state,message=message)},2)
        assert ledger.reservations(c,'tehran')[1]=={'00123':12}
        assert pending_stock(c,'tehran')[1]=={'00123'}


@pytest.mark.parametrize('change',[lambda d:d['headers'].clear(),lambda d:d['headers'][0].update(TStockDCRef=9),
    lambda d:d['items'][0].update(TotalQty=13),lambda d:d['items'][0].update(UnitCapacity=12),
    lambda d:d['headers'][0].update(ConfirmedBy=None),lambda d:d['headers'][0].update(VocherTypeCode=15)])
def test_changed_or_missing_credit_needs_review(credit,change):
    b,doc,_,remote=credit;req=request(credit);remote.return_value=sent();bridge.submit(b.settings,'test-user',doc,req)
    with service.warehouse_connection(b.settings) as c:row=reflection.capture(c)[0]
    detail=evidence(row);change(detail)
    assert reflection._classify(row,detail,True)[0]=='review'


def test_new_intent_during_snapshot_invalidates_import_even_if_capture_was_empty(credit):
    b,doc,_,remote=credit;req=request(credit)
    with service.warehouse_connection(b.settings) as c:before=reflection.capture(c)
    assert before==[]
    remote.return_value=sent();bridge.submit(b.settings,'test-user',doc,req)
    with service.warehouse_connection(b.settings) as c:
        with pytest.raises(service.WarehouseAssistantError):reflection.verify_current(c,before)


def test_pending_cannot_manually_bypass_source_reconciliation(credit):
    b,doc,ident,remote=credit;req=request(credit);remote.side_effect=TimeoutError();bridge.submit(b.settings,'test-user',doc,req)
    snapshot(b)
    with pytest.raises(service.WarehouseAssistantError,match='بستانکار'):
        ledger.reflect_in_stock(b.settings,'test-user',ident,snapshot_id=2,source_document='71',destination_document='99',confirmed=True)


def test_source_reconciliation_and_explicit_destination_receipt_clear_both_legs(credit,monkeypatch):
    b,doc,ident,remote=credit;req=request(credit);remote.return_value=sent();bridge.submit(b.settings,'test-user',doc,req);snapshot(b)
    with service.warehouse_connection(b.settings) as c:
        captured=reflection.capture(c)
        reflection.apply(c,captured,{doc:dict(evidence(captured[0]),status='reflected')},2)
    monkeypatch.setattr(lifecycle,'_read_many',Mock(return_value={doc:evidence(captured[0])}))
    with pytest.raises(service.WarehouseAssistantError,match='شماره'):
        ledger.reflect_in_stock(b.settings,'test-user',ident,snapshot_id=2,source_document='wrong',destination_document='99',confirmed=True)
    ledger.reflect_in_stock(b.settings,'test-user',ident,snapshot_id=2,source_document='71',destination_document='99',confirmed=True)
    with service.warehouse_connection(b.settings) as c:
        assert ledger.reservations(c,'tehran')[1]=={}
        assert ledger.reservations(c,'karaj')[0]=={}
