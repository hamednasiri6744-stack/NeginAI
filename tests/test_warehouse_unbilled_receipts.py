from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app import warehouse_unbilled_receipts as receipts
from app.sql_guard import validate_read_only_sql


def row(**changes):
    return dict(receipt_id=11, fiscal_year=1405, receipt_no=650, receipt_date='1405/06/16',
                stock_id=1, stock_name='انبار', supplier_id=17, supplier_name='طرف خرید',
                supplier_reference=2222, confirmed=1, comment='شرح\nرسید <نام>',
                manufacturer_id=15, manufacturer_name='توليد كننده'.encode('cp1256'), **changes)


def test_distinct_manufacturers_share_one_receipt_and_are_not_supplier():
    first=row();other={**first,'manufacturer_id':17,'manufacturer_name':'سازنده دوم'}
    missing={**first,'receipt_id':12,'confirmed':0,'manufacturer_id':None,'manufacturer_name':None,'comment':None}
    result=receipts.normalize_rows([first,first,other,missing])
    assert len(result)==2
    assert result[0]['supplier_name']=='طرف خرید'
    assert result[0]['manufacturers']==[{'id':15,'name':'تولید کننده'},{'id':17,'name':'سازنده دوم'}]
    assert result[0]['comment']=='شرح\nرسید <نام>'
    assert not result[1]['confirmed'] and result[1]['comment']==''
    assert result[1]['manufacturers']==[{'id':None,'name':'مشخص نشده'}]


@pytest.mark.parametrize('year',['1405; DROP TABLE x',True,1299,1501])
def test_year_rejected_before_sql(year):
    with pytest.raises(receipts.ReceiptListError):receipts.receipt_query(year)


def test_query_reserves_any_invoice_relation_and_is_select_only():
    sql=validate_read_only_sql(receipts.receipt_query(1405)).sql.lower()
    assert 'not exists' in sql and 'tblsupinvinvoicerelation' in sql
    assert 'supinvoicehdr' not in sql  # Draft and orphan links also reserve receipts.
    compact=''.join(sql.split())
    assert 'vochertypecode=20' in compact and 'accyear=1405' in compact
    assert 'manufacturerref' in sql and 'comment' in sql


def test_reader_uses_one_select_and_does_not_initialize_or_commit(monkeypatch,tmp_path):
    rows=[row()];calls=[]
    class Cursor:
        description=[(key,) for key in rows[0]]
        def execute(self,sql):calls.append(sql)
        def fetchmany(self,n):return [tuple(r.values()) for r in rows]
    @contextmanager
    def connection(settings):yield SimpleNamespace(cursor=lambda:Cursor())
    monkeypatch.setattr(receipts,'sql_connection',connection)
    settings=SimpleNamespace(sqlite_path=tmp_path/'must-not-exist.db')
    result=receipts.list_receipts(settings,1405)
    assert result['total']==1 and result['confirmed']==1 and result['varanegar_write'] is False
    assert len(calls)==1 and not settings.sqlite_path.exists()


def test_api_permission_validation_and_failure_do_not_misreport_empty_list(monkeypatch):
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=SimpleNamespace()
    async def identity(request:Request):request.state.username=request.headers.get('X-Test-User','reader')
    app.dependency_overrides[routes.require_session_user]=identity
    monkeypatch.setattr(routes,'_capabilities',lambda request,user:{'warehouse.assistant.view'} if user=='reader' else set())
    calls=[]
    def result(settings,year):calls.append(year);return {'items':[],'year':year,'total':0,'varanegar_write':False}
    monkeypatch.setattr(receipts,'list_receipts',result)
    app.include_router(routes.router)
    url='/warehouse-assistant/api/unbilled-receipts'
    with TestClient(app) as client:
        assert client.get(url,params={'year':1405}).json()['total']==0
        assert calls==[1405]
        assert client.get(url,headers={'X-Test-User':'blocked'}).status_code==403
        assert client.get(url,params={'year':1}).status_code==422
        assert calls==[1405]
        def fail(*args):raise receipts.ReceiptListError('خواندن انجام نشد')
        monkeypatch.setattr(receipts,'list_receipts',fail)
        response=client.get(url)
        assert response.status_code==502 and 'items' not in response.json()
