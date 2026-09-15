"""No production database or real AI calls. Exercise extraction at its external seam."""
import base64
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app import warehouse_checkbar as checkbar
from app import warehouse_checkbar_image as vision
from app.routes import warehouse_assistant as routes
from app.routes.dependencies import require_session_user
from app.warehouse_assistant_service import WarehouseAssistantError, warehouse_connection
from test_warehouse_checkbar import case, active_scope

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9WQAAAAASUVORK5CYII=')


def line(**changes):
    return dict(source_page=1, description='شامپو 250', supplier_code='۰۰۱۲', barcode=None, cartons='۲',
                units='۰', quantity_text='۲ کارتن', uncertain=False, **changes) if not changes else {
        **line(), **changes}


def extracted(rows=None, **changes):
    return vision.ImageExtraction.model_validate({**dict(supplier='supplier', reference_no='۲۲۲۲', date='۱۴۰۵/۰۶/۱۵',
        pages=[dict(page_number=1,complete=True)], warnings=[], lines=rows or [line()]), **changes})


def source():
    return dict(supplier='supplier', expected_token='a'*64, lines=[], catalog=[
        dict(product_code='A', manufacturer_product_code='0012', barcode='00099', product_name='شامپو 250'),
        dict(product_code='B', manufacturer_product_code='0013', barcode='00100', product_name='شامپو 500')])


def test_exact_code_keeps_leading_zeros_and_blank_distinct_from_zero():
    result=vision.match_rows(extracted(),source())
    assert result['rows'][0]['selected']==0
    assert result['rows'][0]['cartons']==2 and result['rows'][0]['units']==0
    assert result['metadata']['reference_no']=='2222'
    row=vision.match_rows(extracted([line(cartons=None,units=None)]),source())['rows'][0]
    assert row['cartons'] is None and row['units'] is None
    row=vision.match_rows(extracted([line(supplier_code='12')]),source())['rows'][0]
    assert row['selected'] == 0  # Description match; leading zeros remain significant.
    assert 'supplier_code' not in row['match_signals']


@pytest.mark.parametrize('changes',[
    {'supplier_code':None}, {'barcode':'different'}, {'uncertain':True},
    {'supplier_code':None,'description':'نام حدسی'},
])
def test_ranked_evidence_can_select_without_all_identifiers(changes):
    expected = None if 'description' in changes else 0
    assert vision.match_rows(extracted([line(**changes)]),source())['rows'][0]['selected'] == expected


def test_duplicate_catalog_and_invoice_rows_are_not_silently_assigned_or_combined():
    src=source();src['catalog'].append(dict(src['catalog'][0],product_code='C'))
    assert vision.match_rows(extracted(),src)['rows'][0]['selected'] is None
    rows=vision.match_rows(extracted([line(),line()]),source())['rows']
    assert len(rows)==2 and all(row['selected'] is None for row in rows)


@pytest.mark.parametrize('value,integer,expected',[
    ('۱٬۲۰۰',True,1200),('١٢٫٥',False,12.5),('0',True,0),(None,False,None),
    ('1,2',False,None),('-1',False,None),('NaN',False,None),('3 packs',False,None),
    ('1.2',True,None),('1000000001',False,None),('1000001',True,None),
])
def test_quantities_do_not_guess_units_or_decimal_separators(value,integer,expected):
    assert vision.quantity(value,integer)==expected


def test_native_response_contract_and_incomplete_failure(monkeypatch):
    mock=MagicMock();client=mock.return_value.__enter__.return_value
    client.responses.parse.return_value=SimpleNamespace(status='completed',output_parsed=extracted())
    monkeypatch.setattr(vision,'OpenAI',mock)
    settings=SimpleNamespace(openai_api_key='fake-test-key',openai_model='configured-model')
    assert vision.extract(settings,PNG).reference_no=='۲۲۲۲'
    args=client.responses.parse.call_args.kwargs
    assert args['model']=='configured-model' and args['store'] is False
    assert 'tools' not in args
    prompt=args['input'][0]['content']
    assert 'Accept delivery notes, dispatch notes, invoices AND pro-forma invoices' in prompt
    assert 'do not reject it for its title' in prompt
    assert args['input'][1]['content'][1]['image_url'].startswith('data:image/png;base64,')
    client.responses.parse.return_value.status='incomplete'
    with pytest.raises(WarehouseAssistantError,match='کامل نشد'):vision.extract(settings,PNG)
    client.responses.parse.side_effect=RuntimeError('provider secret details')
    with pytest.raises(WarehouseAssistantError) as error:vision.extract(settings,PNG)
    assert 'secret' not in str(error.value)


@pytest.mark.parametrize('content',[b'',b'<svg onload="evil">',b'not an image',b'x'*(vision.MAX_IMAGE_BYTES+1)],
                         ids=['empty','svg','fake','oversize'])
def test_bad_images_fail_before_provider(content,monkeypatch):
    mock=MagicMock();monkeypatch.setattr(vision,'OpenAI',mock)
    with pytest.raises(WarehouseAssistantError):vision.extract(SimpleNamespace(openai_api_key='fake'),content)
    mock.assert_not_called()


def test_image_api_returns_draft_without_business_writes_and_checks_permission(case,monkeypatch):
    app=FastAPI();app.state.settings=case.settings;app.include_router(routes.router)
    def signed_in(request:Request):request.state.username='tester'
    app.dependency_overrides[require_session_user]=signed_in
    monkeypatch.setattr(routes,'_capabilities',lambda *_:{'warehouse.order.draft'})
    mock=MagicMock(return_value=extracted());monkeypatch.setattr(vision,'extract',mock)
    scope=dict(warehouse='karaj',supplier='supplier',order_ids=[])
    preview=checkbar.prepare(case.settings,**scope)
    def snapshot():
        with warehouse_connection(case.settings) as conn:
            tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            return {t:[tuple(r) for r in conn.execute(f'SELECT * FROM "{t}"')] for t in tables}
    before=snapshot()
    with TestClient(app) as client:
        url='/warehouse-assistant/api/checkbars/image-draft'
        data={'selection':json.dumps(scope),'expected_token':preview['expected_token']}
        response=client.post(url,data=data,files={'file':('note.png',PNG,'image/png')})
        assert response.status_code==200,response.text
        assert response.json()['document_created'] is False
        assert response.json()['varanegar_write'] is False
        assert response.json()['receipt_recorded'] is False
        assert snapshot()==before
        response=client.post(url,data=data,files=[('file',('one.png',PNG,'image/png')),
                                                 ('file',('two.png',PNG+b'page2','image/png'))])
        assert response.status_code==200,response.text
        assert mock.call_args.args[1]==[PNG,PNG+b'page2']
        assert snapshot()==before
        mock.reset_mock()
        assert client.post(url,data=data,files=[('file',('note.png',PNG))]*11).status_code==422
        monkeypatch.setattr(vision,'MAX_TOTAL_IMAGE_BYTES',len(PNG))
        assert client.post(url,data=data,files=[('file',('note.png',PNG))]*2).status_code==422
        assert client.post(url,data={**data,'expected_token':'b'*64},files={'file':('note.png',PNG)}).status_code==422
        assert client.post(url,data=data,files={'file':('fake.png',b'not image','image/png')}).status_code==422
        monkeypatch.setattr(routes,'_capabilities',lambda *_:set())
        assert client.post(url,data=data,files={'file':('note.png',PNG)}).status_code==403
        app.dependency_overrides.clear()
        assert client.post(url,data=data,files={'file':('note.png',PNG)}).status_code==401
        mock.assert_not_called()


def test_all_pages_sent_in_order_and_duplicate_rows_retained(monkeypatch):
    mock=MagicMock();client=mock.return_value.__enter__.return_value
    pages=[dict(page_number=1,complete=True),dict(page_number=2,complete=True)]
    client.responses.parse.return_value=SimpleNamespace(status='completed',output_parsed=extracted(
        [line(),line(source_page=2,cartons='0',units=None)],pages=pages))
    monkeypatch.setattr(vision,'OpenAI',mock)
    output=vision.extract(SimpleNamespace(openai_api_key='fake',openai_model='test'),[PNG,PNG+b'page2'])
    content=client.responses.parse.call_args.kwargs['input'][1]['content']
    assert content[0]['text']=='Source page 1 of 2' and content[2]['text']=='Source page 2 of 2'
    assert base64.b64decode(content[1]['image_url'].split(',')[1])==PNG
    assert base64.b64decode(content[3]['image_url'].split(',')[1])==PNG+b'page2'
    result=vision.match_rows(output,source())
    assert result['page_count']==2
    assert [row['source_page'] for row in result['rows']]==[1,2]
    assert all(row['selected'] is None for row in result['rows'])
    assert result['rows'][1]['cartons']==0 and result['rows'][1]['units'] is None


@pytest.mark.parametrize('pages,source_page',[
    ([dict(page_number=1,complete=True)],1),
    ([dict(page_number=1,complete=True),dict(page_number=1,complete=True)],1),
    ([dict(page_number=1,complete=True),dict(page_number=2,complete=False)],1),
    ([dict(page_number=1,complete=True),dict(page_number=2,complete=True)],3),
])
def test_incomplete_missing_duplicate_or_out_of_range_pages_rejected(monkeypatch,pages,source_page):
    mock=MagicMock();client=mock.return_value.__enter__.return_value
    client.responses.parse.return_value=SimpleNamespace(status='completed',output_parsed=extracted(
        [line(source_page=source_page)],pages=pages))
    monkeypatch.setattr(vision,'OpenAI',mock)
    with pytest.raises(WarehouseAssistantError,match='کامل نشد'):
        vision.extract(SimpleNamespace(openai_api_key='fake',openai_model='test'),[PNG,PNG])


def test_page_count_total_size_and_later_bad_image_fail_before_provider(monkeypatch):
    mock=MagicMock();monkeypatch.setattr(vision,'OpenAI',mock)
    monkeypatch.setattr(vision,'MAX_TOTAL_IMAGE_BYTES',len(PNG)*2)
    for pages in [[],[PNG]*11,[PNG]*3,[PNG,b'not image']]:
        with pytest.raises(WarehouseAssistantError):
            vision.extract(SimpleNamespace(openai_api_key='fake'),pages)
    mock.assert_not_called()


@pytest.mark.parametrize('status,message',[(401,'کلید'),(429,'ظرفیت'),(500,'نپذیرفت')])
def test_provider_failure_is_actionable_and_never_leaks_body(monkeypatch,status,message,caplog):
    mock=MagicMock();client=mock.return_value.__enter__.return_value
    response=httpx.Response(status,request=httpx.Request('POST','https://example.test'))
    client.responses.parse.side_effect=vision.APIStatusError('secret provider body',response=response,body={})
    monkeypatch.setattr(vision,'OpenAI',mock)
    with pytest.raises(WarehouseAssistantError,match=message) as error:
        vision.extract(SimpleNamespace(openai_api_key='fake',openai_model='test'),PNG)
    assert 'secret' not in str(error.value) and 'secret' not in caplog.text
    assert f'status={status}' in caplog.text


def test_incomplete_document_reports_actual_reason_without_claiming_blur(monkeypatch):
    mock=MagicMock();client=mock.return_value.__enter__.return_value
    client.responses.parse.return_value=SimpleNamespace(status='completed',output_parsed=extracted(
        pages=[dict(page_number=1,complete=False)],warnings=['سند انتخاب‌شده فهرست کالا ندارد.']))
    monkeypatch.setattr(vision,'OpenAI',mock)
    with pytest.raises(WarehouseAssistantError,match='فهرست کالا ندارد') as error:
        vision.extract(SimpleNamespace(openai_api_key='fake',openai_model='test'),PNG)
    assert 'خوانا نیست' not in str(error.value)
