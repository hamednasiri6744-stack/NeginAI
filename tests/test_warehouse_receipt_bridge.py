import json
from contextlib import contextmanager
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from test_warehouse_fulfillment import case
from test_warehouse_checkbar import activate
from app import warehouse_checkbar as checkbar, warehouse_receipt_bridge as bridge
from app.warehouse_assistant_service import WarehouseAssistantError, warehouse_connection


@pytest.fixture
def saved(case):
    activate(case);case.send()
    p=checkbar.prepare(case.settings,'karaj','supplier',[1])
    doc=checkbar.issue(case.settings,'tester',dict(warehouse='karaj',supplier='supplier',order_ids=[1],
        expected_token=p['expected_token'],request_id='receipt-fixture',metadata={'reference_no':'2222'},
        lines=[dict(preorder_id=1,product_code='00123',cartons=1,units=3,
                    consumer_price_new=180000,manufacturer_price_new=120000)]))
    case.settings.varanegar_receipt_bridge_enabled=True
    case.settings.varanegar_receipt_commit_enabled=True
    return doc


def req(**kwargs):
    kwargs.setdefault('reference_no','1490')
    kwargs.setdefault('matching_confirmed',True)
    return bridge.ReceiptRequest(expected_revision=0,voucher_date='۱۴۰۵/۰۶/۱۵',**kwargs)


@pytest.mark.parametrize('reference',['','0','-1','INV-12','1.5','2147483648'])
def test_supplier_document_number_required_before_any_sql(case,saved,monkeypatch,reference):
    remote=Remote();monkeypatch.setattr(bridge,'_remote',remote)
    with pytest.raises(WarehouseAssistantError,match='شماره.*عطف'):
        bridge.preview(case.settings,'tester',saved['id'],req(reference_no=reference))
    assert not remote.calls


def test_supplier_document_number_normalizes_persian_digits(case,saved,monkeypatch):
    remote=Remote();monkeypatch.setattr(bridge,'_remote',remote)
    result=bridge.preview(case.settings,'tester',saved['id'],req(reference_no='۱۴۹۰'))
    assert result['payload']['reference_no']=='1490'


class Remote:
    """Network boundary double; local database and application collaboration are real."""
    def __init__(self):self.commits={};self.calls=[];self.lose=False;self.reject=False
    def __call__(self,settings,key,user,encoded,commit):
        self.calls.append((key,user,encoded,commit))
        payload=json.loads(encoded)
        modern=payload.get('price_workflow_version')==2
        if not commit:return dict(BridgeStatus='ready',ValidationToken='A'*64,AccYear=1405,SupplierRef=7,**({'PriceWorkflowVersion':2} if modern else {}))
        if self.reject:return dict(BridgeStatus='rejected',Message='closed period')
        result=self.commits.setdefault(key,dict(BridgeStatus='sent',VocherNo=71,VocherId=501,Confirmed=False))
        if modern:
            from app.warehouse_receipt_prices import expected_roles
            from uuid import uuid5,NAMESPACE_URL
            docs=[dict(Role=role,VocherId=501+i,VocherNo=71+i,UniqueId=str(uuid5(NAMESPACE_URL,key+role)),
                       StockDCRef=payload['stock_dc_ref'],VocherTypeCode=76 if role=='price_reserve' else 20,
                       Confirmed=role!='unpriced_receipt',AccYear=1405) for i,role in enumerate(sorted(expected_roles(payload)))]
            primary=next(d for d in docs if d['Role']!='price_reserve')
            result.update(PriceWorkflowVersion=2,DocumentsJson=json.dumps(docs),**{k:primary[k] for k in ('VocherId','VocherNo','Confirmed')})
        if self.lose:self.lose=False;raise TimeoutError('lost reply after SQL commit')
        return result


def prepared(case,saved,remote):
    response=bridge.preview(case.settings,'tester',saved['id'],req())
    return req(preview_token=response['preview_token'],validation_token=response['result']['ValidationToken'])


def test_saved_prices_comment_and_original_are_preserved(case,saved,monkeypatch):
    remote=Remote();monkeypatch.setattr(bridge,'_remote',remote)
    preview=bridge.preview(case.settings,'tester',saved['id'],req())
    assert preview['payload']['lines']==[dict(product_code='00123',quantity='15',item_comment='180000-120000',source_row=1,
        price_mode='changed',consumer_price_current='120',manufacturer_price_current='90',
        consumer_price_effective='180000',manufacturer_price_effective='120000')]
    assert preview['payload']['voucher_date']=='1405/06/15'
    assert not remote.commits
    assert checkbar.get_document(case.settings,saved['id'])==saved


def test_blank_blocks_zero_is_preserved_and_excluded(case,saved,monkeypatch):
    remote=Remote();monkeypatch.setattr(bridge,'_remote',remote)
    with warehouse_connection(case.settings) as conn:
        payload=bridge._payload(conn,{**saved,'lines':[saved['lines'][0],{**saved['lines'][0],'actual_qty':0}]},req())
        assert payload['zero_rows']==[2] and len(payload['lines'])==1
        for value,text in [(None,'خالی'),(0,'بیشتر از صفر'),(.0001,'سه رقم')]:
            with pytest.raises(WarehouseAssistantError,match=text):
                bridge._payload(conn,{**saved,'lines':[{**saved['lines'][0],'actual_qty':value}]},req())
    assert not remote.calls


def test_zero_price_does_not_fall_back_and_missing_price_blocks(case,saved):
    with warehouse_connection(case.settings) as conn:
        line={**saved['lines'][0],'consumer_price_new':0,'manufacturer_price_new':None,'manufacturer_price':100}
        assert bridge._payload(conn,{**saved,'lines':[line]},req())['lines'][0]['item_comment']=='0-100'
        line['manufacturer_price']=None
        with pytest.raises(WarehouseAssistantError,match='تولیدکننده'):
            bridge._payload(conn,{**saved,'lines':[line]},req())


@pytest.mark.parametrize('bad',['1405/00/10','1405/07/31','1405/06/00','1405/12/30','1405/99/99'])
def test_invalid_calendar_dates(bad):
    with pytest.raises(ValidationError):bridge.ReceiptRequest(expected_revision=0,voucher_date=bad)


def test_unknown_or_confirmation_fields_rejected():
    with pytest.raises(ValidationError):req(confirmed=True)


def test_disabled_bridge_never_opens_sql(case,saved,monkeypatch):
    case.settings.varanegar_receipt_bridge_enabled=False
    monkeypatch.setattr(bridge,'_connection',lambda *_:pytest.fail('SQL must not open'))
    result=bridge.preview(case.settings,'tester',saved['id'],req())
    assert result['status']=='invalid' and result['payload']['lines']
    with pytest.raises(WarehouseAssistantError):bridge.submit(case.settings,'tester',saved['id'],req())
    assert bridge.transfer_status(case.settings,saved['id'])['status']=='not_sent'


def test_commit_requires_fresh_revision_preview_and_live_validation(case,saved,monkeypatch):
    remote=Remote();monkeypatch.setattr(bridge,'_remote',remote)
    request=prepared(case,saved,remote)
    with pytest.raises(WarehouseAssistantError):bridge.submit(case.settings,'tester',saved['id'],req())
    with pytest.raises(WarehouseAssistantError):bridge.submit(case.settings,'tester',saved['id'],request.model_copy(update={'comment':'changed'}))
    with pytest.raises(WarehouseAssistantError):bridge.submit(case.settings,'tester',saved['id'],request.model_copy(update={'expected_revision':2}))
    assert not remote.commits


def test_lost_reply_replays_exact_intent_and_receives_order_only_once(case,saved,monkeypatch):
    remote=Remote();monkeypatch.setattr(bridge,'_remote',remote)
    request=prepared(case,saved,remote);remote.lose=True
    assert bridge.submit(case.settings,'tester',saved['id'],request)['status']=='pending'
    with pytest.raises(WarehouseAssistantError,match='پیگیری'):
        checkbar.delete_document(case.settings,'tester',saved['id'],dict(expected_revision=0,request_id='delete'))
    result=bridge.submit(case.settings,'another-user',saved['id'])
    assert result['status']=='sent' and result['result']['VocherNo']==71
    assert remote.calls[-1]==remote.calls[-2] and len(remote.commits)==1
    assert bridge.submit(case.settings,'tester',saved['id'],request)==result
    assert len(remote.calls)==3
    with pytest.raises(WarehouseAssistantError):
        checkbar.delete_document(case.settings,'tester',saved['id'],dict(expected_revision=0,request_id='delete'))
    assert bridge.transfer_status(case.settings,saved['id'])['status']=='sent'
    assert bridge.submit(case.settings,'tester',saved['id'])==result
    with warehouse_connection(case.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_fulfillment_receipts').fetchone()[0]==0  # no duplicate manual receipt
        assert conn.execute('SELECT SUM(quantity) FROM warehouse_receipt_allocations').fetchone()[0]==15
        assert conn.execute('SELECT COUNT(*) FROM warehouse_checkbar_transfers').fetchone()[0]==1


def test_definite_rollback_allows_correction_without_new_transfer_key(case,saved,monkeypatch):
    remote=Remote();monkeypatch.setattr(bridge,'_remote',remote)
    request=prepared(case,saved,remote);remote.reject=True
    assert bridge.submit(case.settings,'tester',saved['id'],request)['status']=='rejected'
    firstkey=remote.calls[-1][0];remote.reject=False
    request=prepared(case,saved,remote)
    assert bridge.submit(case.settings,'tester',saved['id'],request)['status']=='sent'
    assert remote.calls[-1][0]==firstkey


def test_reconciliation_without_intent_cannot_create_receipt(case,saved,monkeypatch):
    monkeypatch.setattr(bridge,'_remote',lambda *_:pytest.fail('must not call ERP'))
    with pytest.raises(WarehouseAssistantError):bridge.submit(case.settings,'tester',saved['id'])


def test_restored_pretransfer_backup_keeps_remote_identity(case,saved,monkeypatch):
    remote=Remote();monkeypatch.setattr(bridge,'_remote',remote)
    request=prepared(case,saved,remote)
    assert bridge.submit(case.settings,'tester',saved['id'],request)['status']=='sent'
    key=remote.calls[-1][0]
    # Synthetic restoration to original checkbar state before any transfer ledger.
    with warehouse_connection(case.settings) as conn:conn.execute('DELETE FROM warehouse_checkbar_transfers')
    request=prepared(case,saved,remote)
    assert bridge.submit(case.settings,'tester',saved['id'],request)['status']=='sent'
    assert remote.calls[-1][0]==key and len(remote.commits)==1


def test_api_requires_separate_transfer_permission_and_session(case,saved,monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=case.settings;app.include_router(routes.router)
    base=f'/warehouse-assistant/api/checkbars/{saved["id"]}'
    with TestClient(app) as client:
        assert client.post(base+'/receipt-transfer',json=req().model_dump()).status_code==401
        app.dependency_overrides[routes.require_session_user]=lambda:'tester'
        monkeypatch.setattr(routes,'_capabilities',lambda *_:{'warehouse.order.draft'})
        assert client.get(base+'/receipt-transfer').status_code==200
        for suffix in ('receipt-transfer','receipt-preview','receipt-reconcile'):
            assert client.post(base+'/'+suffix,json=req().model_dump()).status_code==403
        monkeypatch.setattr(routes,'_capabilities',lambda *_:{'warehouse.order.draft','warehouse.receipt.transfer'})
        monkeypatch.setattr(bridge,'_remote',Remote())
        p=client.post(base+'/receipt-preview',json=req().model_dump());assert p.status_code==200,p.text
        request=req(preview_token=p.json()['preview_token'],validation_token=p.json()['result']['ValidationToken'])
        response=client.post(base+'/receipt-transfer',json=request.model_dump())
        assert response.status_code==200 and response.json()['status']=='sent'


@pytest.mark.parametrize('response,commit,accepted',[
    ({'BridgeStatus':'ready','ValidationToken':'A'*64},False,True),
    ({'BridgeStatus':'sent','VocherId':501,'VocherNo':71,'Confirmed':False},True,True),
    ({'BridgeStatus':'sent','VocherId':501,'VocherNo':71,'Confirmed':True},True,False),
    ({'BridgeStatus':'sent','VocherId':501,'VocherNo':0,'Confirmed':False},True,False),
    ({'BridgeStatus':'sent','VocherId':501,'VocherNo':71,'Confirmed':False},False,False),
    ({'BridgeStatus':'unexpected'},True,False),
])
def test_transport_scans_result_sets_and_enforces_unconfirmed_receipt_contract(case,saved,monkeypatch,response,commit,accepted):
    class Cursor:
        description=None
        def execute(self,statement,params):
            assert 'NeginAI.usp_CreateCheckbarReceipt' in statement
            assert params[-1] is commit
        def nextset(self):
            self.description=[(key,) for key in response]
            return True
        def fetchone(self):return list(response.values())
    class Connection:
        def cursor(self):return Cursor()
    @contextmanager
    def connect(*_):yield Connection()
    monkeypatch.setattr(bridge,'_connection',connect)
    if accepted:
        assert bridge._remote(case.settings,'test-key','tester','{}',commit)==response
    else:
        with pytest.raises(WarehouseAssistantError):bridge._remote(case.settings,'test-key','tester','{}',commit)


@pytest.mark.parametrize('capability,expected_commits',[(False,0),(True,1)])
def test_replacement_transport_checks_wrapper_capability_and_recovers_lost_reply(case,saved,monkeypatch,capability,expected_commits):
    calls=[]
    class Cursor:
        description=None
        def execute(self,statement,params):
            calls.append(params[-1])
            self.response=({'BridgeStatus':'sent','VocherId':502,'VocherNo':72,'Confirmed':False}
                if params[-1] else {'BridgeStatus':'blocked',**({'ReplacementSupported':1} if capability else {})})
            self.description=[(k,) for k in self.response]
        def fetchone(self):return list(self.response.values())
    class Connection:
        def cursor(self):return Cursor()
    @contextmanager
    def connect(*_):yield Connection()
    monkeypatch.setattr(bridge,'_connection',connect)
    encoded=json.dumps({'replaces_receipts':[{'transfer_key':'prior'}]})
    if capability:assert bridge._remote(case.settings,'new-key','tester',encoded,True)['VocherNo']==72
    else:
        with pytest.raises(WarehouseAssistantError):bridge._remote(case.settings,'new-key','tester',encoded,True)
    assert calls.count(True)==expected_commits and calls[0] is False
