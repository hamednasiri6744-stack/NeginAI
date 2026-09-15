"""Synthetic in-memory attachments only; no production database or provider calls."""
import base64
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from openpyxl import Workbook
from pypdf import PdfReader, PdfWriter
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app import warehouse_checkbar_files as files
from app import warehouse_checkbar_image as vision
from app import warehouse_checkbar as checkbar
from app.routes import warehouse_assistant as routes
from app.routes.dependencies import require_session_user
from app.warehouse_assistant_service import WarehouseAssistantError, warehouse_connection
from test_warehouse_checkbar import case, active_scope
from test_warehouse_checkbar_image import PNG, extracted, line, source


def pdf(pages=2, encrypted=False):
    writer = PdfWriter()
    for index in range(pages):
        writer.add_blank_page(width=200+index, height=300)
    if encrypted:
        writer.encrypt('synthetic-password')
    output = BytesIO();writer.write(output)
    return output.getvalue()


def workbook(sheets=2, formula=False):
    book = Workbook()
    for index in range(sheets):
        sheet = book.active if index == 0 else book.create_sheet()
        sheet.title = f'حواله {index+1}'
        sheet.append(['کد کالا','شرح','کارتن','عدد جزء'])
        sheet.append(['0012','شامپو',0,None])
        sheet.append([13,'صابون',None,5])
        sheet['A3'].number_format='0000'
        if formula:
            sheet['C2']='=1+1'
    output=BytesIO();book.save(output);book.close()
    return output.getvalue()


def test_pdf_is_split_in_order_and_each_page_remains_a_pdf():
    pages=files.prepare_files([pdf()],['note.pdf'])
    assert [label for label,_ in pages]==['note.pdf · صفحه 1','note.pdf · صفحه 2']
    for index,(_,part) in enumerate(pages):
        assert part['type']=='input_file'
        page=PdfReader(BytesIO(base64.b64decode(part['file_data'].split(',')[1])))
        assert len(page.pages)==1 and page.pages[0].mediabox.width==200+index


def test_excel_all_sheets_leading_zeros_zero_and_blank():
    pages=files.prepare_files([workbook()],['note.xlsx'])
    assert len(pages)==2
    for index,(label,part) in enumerate(pages):
        assert label==f'note.xlsx · برگه حواله {index+1}'
        rows=json.loads(part['text'])['cells']
        assert rows[1]=={'A2':'0012','B2':'شامپو','C2':0}
        assert rows[2]=={'A3':'0013','B3':'صابون','D3':5}


def test_legacy_xls_real_binary_fixture():
    pages=files.prepare_files([(Path(__file__).parent/'fixtures/checkbar/synthetic.xls').read_bytes()],['note.xls'])
    assert len(pages)==1 and 'حواله قدیمی' in pages[0][0]
    rows=json.loads(pages[0][1]['text'])['cells']
    assert rows[4]['A5']=='0012' and rows[4]['D5']==0
    assert rows[5]['A6']=='0013' and rows[5]['C6']==0 and rows[5]['D6']==5


@pytest.mark.parametrize('content,name,message',[
    (b'%PDF-broken','bad.pdf','قابل خواندن نیست'),
    (b'PK\x03\x04broken','bad.xlsx','قابل خواندن نیست'),
    (b'not document','fake.pdf','فقط'),
    (pdf(encrypted=True),'locked.pdf','رمزدار'),
    (pdf(11),'many.pdf','۱۰'),
    (workbook(formula=True),'formula.xlsx','فرمول'),
],ids=['broken-pdf','broken-xlsx','wrong-signature','locked-pdf','many-pages','uncached-formula'])
def test_rejects_before_provider(monkeypatch,content,name,message):
    provider=MagicMock();monkeypatch.setattr(vision,'OpenAI',provider)
    with pytest.raises(WarehouseAssistantError,match=message):
        vision.extract(SimpleNamespace(openai_api_key='test'),[content],filenames=[name])
    provider.assert_not_called()


def test_mixed_page_limit_and_unpacked_excel_size(monkeypatch):
    with pytest.raises(WarehouseAssistantError,match='۱۰'):
        files.prepare_files([pdf(9),workbook(2)],['note.pdf','note.xlsx'])
    monkeypatch.setattr(files,'MAX_TOTAL_BYTES',10000)
    archive=BytesIO()
    with ZipFile(archive,'w',ZIP_DEFLATED) as zipped:
        zipped.writestr('xl/workbook.xml','x'*10001)
    with pytest.raises(WarehouseAssistantError,match='بزرگ'):
        files.prepare_files([archive.getvalue()],['large.xlsx'])


def test_understated_dimensions_do_not_hide_out_of_bounds_cells():
    original=workbook(1);output=BytesIO()
    with ZipFile(BytesIO(original)) as src, ZipFile(output,'w',ZIP_DEFLATED) as dst:
        for item in src.infolist():
            value=src.read(item.filename)
            if item.filename=='xl/worksheets/sheet1.xml':
                value=value.replace(b'r="D3"',b'r="ZZ3"')
            dst.writestr(item.filename,value)
    with pytest.raises(WarehouseAssistantError,match='محدوده'):
        files.prepare_files([output.getvalue()],['hidden.xlsx'])


def test_cached_formula_zero_is_read_without_executing_formula():
    output=BytesIO()
    with ZipFile(BytesIO(workbook(1,formula=True))) as src, ZipFile(output,'w',ZIP_DEFLATED) as dst:
        for item in src.infolist():
            value=src.read(item.filename)
            if item.filename=='xl/worksheets/sheet1.xml':
                xml=ET.fromstring(value)
                ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                target=xml.find('.//s:c[@r="C2"]/s:v',ns)
                assert target is not None
                target.text='0'
                value=ET.tostring(xml)
            dst.writestr(item.filename,value)
    page=files.prepare_files([output.getvalue()],['cached.xlsx'])[0][1]
    assert json.loads(page['text'])['cells'][1]['C2']==0
    assert '1+1' not in page['text']


@pytest.mark.parametrize('attachment',['xl/vbaProject.bin','xl/media/image1.png'])
def test_embedded_content_is_not_silently_ignored(attachment):
    output=BytesIO()
    with ZipFile(BytesIO(workbook(1))) as src, ZipFile(output,'w',ZIP_DEFLATED) as dst:
        for item in src.infolist():dst.writestr(item.filename,src.read(item.filename))
        dst.writestr(attachment,b'synthetic content')
    with pytest.raises(WarehouseAssistantError,match='PDF'):
        files.prepare_files([output.getvalue()],['embedded.xlsx'])


def test_pdf_excel_image_share_one_provider_call_and_keep_origin(monkeypatch):
    provider=MagicMock();client=provider.return_value.__enter__.return_value
    client.responses.parse.return_value=SimpleNamespace(status='completed',output_parsed=extracted(
        [line(source_page=1),line(source_page=3),line(source_page=4)],
        pages=[dict(page_number=i,complete=True) for i in range(1,5)]))
    monkeypatch.setattr(vision,'OpenAI',provider)
    output=vision.extract(SimpleNamespace(openai_api_key='test',openai_model='configured'),
                          [pdf(),workbook(1),PNG],filenames=['note.pdf','note.xlsx','photo.png'])
    content=client.responses.parse.call_args.kwargs['input'][1]['content']
    assert [part['type'] for part in content[1::2]]==['input_file','input_file','input_text','input_image']
    assert client.responses.parse.call_count==1
    result=vision.match_rows(output,source())
    assert result['file_count']==3 and result['page_count']==4
    assert [row['source_label'] for row in result['rows']]==[
        'note.pdf · صفحه 1','note.xlsx · برگه حواله 1','photo.png · عکس']


def test_multipart_pdf_excel_api_is_unsaved_and_no_business_writes(case,monkeypatch):
    app=FastAPI();app.state.settings=case.settings;app.include_router(routes.router)
    def signed_in(request:Request):request.state.username='tester'
    app.dependency_overrides[require_session_user]=signed_in
    monkeypatch.setattr(routes,'_capabilities',lambda *_:{'warehouse.order.draft'})
    case.settings.openai_api_key='fake'
    case.settings.openai_model='fake-model'
    provider=MagicMock();monkeypatch.setattr(vision,'OpenAI',provider)
    provider.return_value.__enter__.return_value.responses.parse.return_value=SimpleNamespace(
        status='completed',output_parsed=extracted([line(source_page=1),line(source_page=3)],
        pages=[dict(page_number=i,complete=True) for i in range(1,4)]))
    scope=dict(warehouse='karaj',supplier='supplier',order_ids=[])
    preview=checkbar.prepare(case.settings,**scope)
    def snapshot():
        with warehouse_connection(case.settings) as conn:
            tables=[row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            return {t:[tuple(row) for row in conn.execute(f'SELECT * FROM "{t}"')] for t in tables}
    before=snapshot()
    with TestClient(app) as client:
        response=client.post('/warehouse-assistant/api/checkbars/image-draft',
            data={'selection':json.dumps(scope),'expected_token':preview['expected_token']},
            files=[('file',('invoice.pdf',pdf(),'application/pdf')),
                   ('file',('invoice.xlsx',workbook(1),'application/octet-stream'))])
        assert response.status_code==200,response.text
        assert response.json()['file_count']==2 and response.json()['page_count']==3
        assert response.json()['document_created'] is False and response.json()['varanegar_write'] is False
    assert snapshot()==before
