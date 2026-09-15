import json
from copy import deepcopy
from uuid import uuid4
import pytest
from app import warehouse_receipt_prices as prices,warehouse_receipt_bridge as bridge,warehouse_receipt_reflection as reflection
from app.warehouse_assistant_service import WarehouseAssistantError,warehouse_connection
from test_warehouse_fulfillment import case
from test_warehouse_receipt_bridge import saved,Remote,prepared


@pytest.mark.parametrize('changes,mode,comment',[
    ({},'unchanged','200-100'),
    ({'consumer_price_new':200},'unchanged','200-100'),
    ({'consumer_price_new':300},'changed','300-100'),
    ({'manufacturer_price_new':150},'changed','200-150'),
    ({'consumer_price_new':300,'manufacturer_price_new':150},'changed','300-150'),
    ({'consumer_price':0,'manufacturer_price':0},'unpriced','0-0'),
    ({'consumer_price_new':0},'changed','0-100'),
])
def test_price_categories(changes,mode,comment):
    line=dict(consumer_price=200,manufacturer_price=100,**{})
    line.update(changes)
    result=prices.price_fields(line,bridge._number,bridge._text,'row')
    assert (result['price_mode'],result['item_comment'])==(mode,comment)


def test_unknown_current_prices_are_not_mislabeled_intrinsically_unpriced():
    with pytest.raises(WarehouseAssistantError):
        prices.price_fields(dict(consumer_price=None,manufacturer_price=None),bridge._number,bridge._text,'row')


def bundle():
    lines=[]
    for code,mode in [('a','changed'),('b','unchanged'),('c','unpriced')]:
        lines.append(dict(product_code=code,quantity='12',price_mode=mode,item_comment='200-100' if mode!='unpriced' else '0-0'))
    payload=dict(price_workflow_version=2,lines=lines,stock_dc_ref=1,comment='test')
    docs=[dict(Role=role,VocherId=501+i,VocherNo=71+i,UniqueId=str(uuid4()),StockDCRef=1,
               VocherTypeCode=76 if role=='price_reserve' else 20,Confirmed=role!='unpriced_receipt',AccYear=1405)
          for i,role in enumerate(['confirmed_receipt','price_reserve','unpriced_receipt'])]
    result=dict(PriceWorkflowVersion=2,BridgeStatus='sent',VocherId=501,VocherNo=71,Confirmed=True,DocumentsJson=json.dumps(docs))
    return payload,result,docs


def test_bundle_reply_requires_all_documents_and_expected_warehouse_and_states():
    payload,result,docs=bundle();prices.validate_result(payload,result,True)
    for changed in [docs[:1],docs+[docs[0]],[dict(d,StockDCRef=2) for d in docs],[dict(d,Confirmed=False) for d in docs]]:
        with pytest.raises(ValueError):prices.validate_result(payload,dict(result,DocumentsJson=json.dumps(changed)),True)
    with pytest.raises(ValueError):prices.validate_result(payload,result,False)


def test_mixed_bundle_reflection_keeps_only_unconfirmed_receipt_pending(monkeypatch):
    payload,result,docs=bundle()
    monkeypatch.setattr(reflection,'_rows',lambda *_:[dict(CardexType=1,EffectOnHandQty=True,EffectType=-1),dict(CardexType=4,EffectOnHandQty=True,EffectType=1)])
    monkeypatch.setattr(reflection,'_receipt',lambda cursor,row:dict(headers=[dict(AccYear=1405)],items=[]))
    monkeypatch.setattr(reflection,'_classify',lambda row,*_:('waiting' if json.loads(row['result_json'])['Role']=='unpriced_receipt' else 'reflected',''))
    row=dict(payload_json=json.dumps(payload),result_json=json.dumps(result))
    evidence=reflection._bundle(None,row,{'valid':True})
    assert evidence['status']=='waiting'
    assert [l['product_code'] for l in evidence['pending_lines']]==['c']
    monkeypatch.setattr(reflection,'_classify',lambda *_:('waiting',''))
    assert reflection._bundle(None,row,{'valid':True})['status']=='review'


def test_confirmed_price_reserve_is_not_added_back_to_available_pending_stock(case,saved,monkeypatch):
    remote=Remote();monkeypatch.setattr(bridge,'_remote',remote)
    request=prepared(case,saved,remote)
    result=bridge.submit(case.settings,'tester',saved['id'],request)
    assert result['status']=='sent'
    from app.warehouse_order_receipts import pending_stock
    with warehouse_connection(case.settings) as conn:
        assert pending_stock(conn,'karaj')[0].get('00123',0)==0


def test_missing_v2_capability_blocks_new_submission(case,saved,monkeypatch):
    monkeypatch.setattr(bridge,'_remote',lambda *_:dict(BridgeStatus='ready',ValidationToken='A'*64))
    result=bridge.preview(case.settings,'tester',saved['id'],bridge.ReceiptRequest(expected_revision=0,voucher_date='1405/06/15',reference_no='123'))
    assert result['status']=='invalid'
    assert 'نصب' in result['result']['Message']


def test_lifecycle_missing_one_component_cannot_unlock_the_checkbar(monkeypatch):
    from contextlib import contextmanager
    from app import database,warehouse_receipt_lifecycle as lifecycle
    payload,result,docs=bundle()
    class Cursor:
        def execute(self,sql):
            rows=[]
            if 'VocherHdr' in sql:
                d=next(d for d in docs if str(d['VocherId']) in sql)
                if d['Role']!='price_reserve':
                    rows=[dict(ID=d['VocherId'],UniqueId=d['UniqueId'],VocherNo=d['VocherNo'],
                        ConfirmDate='now' if d['Confirmed'] else None,ConfirmedBy=1 if d['Confirmed'] else None,
                        StockDCRef=1,VocherTypeCode=d['VocherTypeCode'])]
            self.description=[(k,) for k in rows[0]] if rows else []
            self.data=[tuple(r.values()) for r in rows]
        def fetchall(self):return self.data
    @contextmanager
    def connect(_):yield object()
    monkeypatch.setattr(database,'sql_connection',connect)
    monkeypatch.setattr(reflection,'snapshot_cursor',lambda _:Cursor())
    status=lifecycle.probe(None,dict(result_json=json.dumps(result),transfer_key=str(uuid4())))
    assert status['state']=='review'
    assert len(status['documents'])==3
