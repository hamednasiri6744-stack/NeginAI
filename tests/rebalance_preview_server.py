"""Loopback-only visual fixture. Real transfer logic on disposable SQLite, no ERP routes."""
import sys
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import warehouse_assistant_service as service
from app.routes import warehouse_assistant as routes
from app.business_time import jalali_business_date, tehran_now

temporary = TemporaryDirectory(prefix='negin-transfer-ui-')
settings = SimpleNamespace(sqlite_path=Path(temporary.name)/'isolated.db')
settings.varanegar_transfer_bridge_enabled = True
settings.varanegar_transfer_commit_enabled = True
from app import warehouse_transfer_bridge as credit_bridge
# This fixture has no SQL connection. Only the remote boundary is simulated;
# routes, immutable intent, permissions and document locks remain real.
def fixture_credit_remote(settings, key, username, payload, commit):
    if '--reserve-shortage' in sys.argv:
        blocked=[dict(ProductCode=r['product_code'],RequestedQuantity=float(r['quantity']),
                      OnHandQuantity=0,ReservedQuantity=100,ShortageQuantity=float(r['quantity']))
                 for r in json.loads(payload)['lines'] if r['product_code']=='TEST-2']
        if blocked:
            return dict(BridgeStatus='rejected',ErrorCode=51515,Message='کمبود آزمایشی رزرو',StockIssuesJson=json.dumps(blocked))
    if commit:
        return dict(BridgeStatus='sent',VocherId=1,VocherNo=1,AccYear=1405,Confirmed=True,Message='فقط آزمایشی')
    return dict(BridgeStatus='ready',ValidationToken='fixture-only',Message='آزمایشی')
credit_bridge._remote = fixture_credit_remote
service.init_warehouse_store(settings)
with service.warehouse_connection(settings) as conn:
    conn.execute("INSERT INTO warehouse_snapshots(id,source_filename,source_sheet,content_sha256,product_count,item_count,imported_by,imported_at,period_days) VALUES(1,'synthetic','test','test',1,2,'test','2099-01-01',60)")
    conn.execute("INSERT INTO warehouse_supplier_auto_order_settings(id,warehouse_code,warehouse_name,supplier,created_at,updated_at) VALUES(1,'karaj','انبار کرج','تأمین‌کننده آزمایشی','now','now')")
    conn.execute("""INSERT INTO warehouse_automatic_preorders(id,preorder_number,generation_key,snapshot_id,supplier_setting_id,
        warehouse_code,warehouse_name,supplier,status,reorder_coverage_days,target_days,item_count,total_quantity,total_cartons,
        created_by,created_at,business_date) VALUES(1,'AUTO-TEST','fixture',1,1,'karaj','انبار کرج','تأمین‌کننده آزمایشی',
        'awaiting_approval',10,20,1,24,2,'tester','now',?)""", (jalali_business_date(tehran_now()),))
    conn.execute("""INSERT INTO warehouse_automatic_preorder_lines(preorder_id,warehouse_code,warehouse_name,product_code,
        product_name,brand,conversion_rate,order_quantity,cartons,manufacturer_price,consumer_price,buy_price,estimated_value)
        VALUES(1,'karaj','انبار کرج','TEST-1','کالای آزمایشی جابه‌جایی','آزمایشی',12,24,2,80,100,70,1680)""")
    for index, warehouse, stock in [(1,'karaj',0),(2,'tehran',112),(3,'gilan',0)]:
        conn.execute('''INSERT INTO warehouse_snapshot_items(snapshot_id,source_row,warehouse_code,warehouse_name,product_code,
            product_name,manufacturer,brand,conversion_rate,stock,period_out,consumer_price) VALUES(1,?,?,?,'TEST-1',
            'کالای آزمایشی جابه‌جایی','تأمین‌کننده آزمایشی','آزمایشی',12,?,120,100)''', (index, warehouse, warehouse, stock))
manual = service.create_supplier_orders(settings,'tester',snapshot_id=1,warehouse='karaj',
    lines=[{'product_code':'TEST-1','quantity':24}],note='synthetic')[0]
# Twelve realistic rows expose layout starvation hidden by a one-row fixture.
with service.warehouse_connection(settings) as conn:
    for index in range(2,13):
        for warehouse,stock in [('karaj',12),('tehran',112),('gilan',0)]:
            conn.execute('''INSERT INTO warehouse_snapshot_items(snapshot_id,source_row,warehouse_code,warehouse_name,product_code,
                product_name,manufacturer,brand,conversion_rate,stock,period_out,consumer_price) VALUES(1,?,?,?,?,
                ?,'تأمین‌کننده آزمایشی','آزمایشی',12,?,120,100)''',(index*2,warehouse,warehouse,f'TEST-{index}',f'کالای آزمایشی {index} برای بررسی فضای عملیاتی جدول',stock))
    for table, parent_column, parent_id in [('warehouse_automatic_preorder_lines','preorder_id',1),('supplier_order_lines','order_id',manual['id'])]:
        original = dict(conn.execute(f'SELECT * FROM {table} WHERE {parent_column}=?', (parent_id,)).fetchone())
        original.pop('id', None)
        for index in range(2,13):
            row = {**original, 'product_code':f'TEST-{index}', 'product_name':f'کالای آزمایشی {index} برای بررسی فضای عملیاتی جدول'}
            conn.execute(f'INSERT INTO {table} ({",".join(row)}) VALUES ({",".join("?" for _ in row)})',tuple(row.values()))
    conn.execute('UPDATE warehouse_automatic_preorders SET item_count=12,total_quantity=288,total_cartons=24 WHERE id=1')
    conn.execute('UPDATE supplier_orders SET total_quantity=288 WHERE id=?',(manual['id'],))
    # Mixed eligibility exercises the distant-route guard without live data.
    conn.execute("UPDATE warehouse_snapshot_items SET stock=60 WHERE warehouse_code='karaj' AND product_code IN ('TEST-1','TEST-10')")
    conn.execute("UPDATE warehouse_snapshot_items SET stock=180 WHERE warehouse_code='tehran' AND product_code IN ('TEST-1','TEST-10')")
    conn.execute("UPDATE warehouse_snapshot_items SET buy_price=70 WHERE warehouse_code='tehran'")
if '--reserve-shortage' in sys.argv:
    from app import warehouse_balance_proposals as proposals, warehouse_transfer_documents as documents
    from app.warehouse_rebalancing import list_requests
    p=proposals.preview(settings,'tester','tehran',destination='karaj',include_all=True)
    proposals.accept(settings,'tester','tehran',[dict(product_code=code,cartons=1) for code in ('TEST-2','TEST-3')],
                     destination='karaj',expected_token=p['expected_token'],request_id='reserve-ui',include_all=True)
    documents.create_documents(settings,'tester',[r['id'] for r in list_requests(settings,'tester')],request_id='reserve-ui-doc')
if '--lifecycle' in sys.argv:
    from app import warehouse_balance_proposals as proposals, warehouse_transfer_documents as documents
    from app import warehouse_transfer_lifecycle as lifecycle
    from app.warehouse_rebalancing import list_requests
    for index in range(2,8):
        p=proposals.preview(settings,'tester','tehran',destination='karaj',include_all=True)
        proposals.accept(settings,'tester','tehran',[dict(product_code=f'TEST-{index}',cartons=1)],
                         destination='karaj',expected_token=p['expected_token'],request_id=f'life-{index}',include_all=True)
        staged=[r['id'] for r in list_requests(settings,'tester') if not r['issued_document_id']]
        result=documents.create_documents(settings,'tester',staged,request_id=f'life-doc-{index}')
        if index<7:
            docid=result['documents'][0]['id']
            ready=credit_bridge.preview(settings,'tester',docid)
            credit_bridge.submit(settings,'tester',docid,credit_bridge.SubmitCredit(
                preview_token=ready['preview_token'],validation_token=ready['validation_token'],confirmed=True))
    def fixture_lifecycle(settings, captured):
        details={}
        for row in captured:
            p,r,key=lifecycle._identity(row)
            detail=dict(headers=[dict(ID=r['VocherId'],UniqueId=key,VocherNo=r['VocherNo'],AccYear=r['AccYear'],
                StockDCRef=p['source_stock_ref'],TStockDCRef=p['destination_stock_ref'],VocherTypeCode=65,
                HealthCodeType=1047,HealthCode=1,VocherDate=p['voucher_date'],ConfirmedBy=2,ConfirmDate='fixture')],
                items=[dict(GoodsCode=line['product_code'],UnitRef=1,BasicUnitRef=1,UnitCapacity=1,
                            UnitQty=line['quantity'],TotalQty=line['quantity']) for line in p['lines']])
            if row['document_id']==2:detail['headers'][0]['ConfirmedBy']=None
            if row['document_id']==3:detail['headers']=[]
            if row['document_id']==4:detail['items'][0]['TotalQty']=999
            if row['document_id']==5:detail=None
            details[row['document_id']]=detail
        return details
    lifecycle._read_many=fixture_lifecycle
app=FastAPI(); app.state.settings=settings
routes._require=lambda *args:'tester'
routes._is_admin=lambda *args:True
app.dependency_overrides[routes.require_session_user]=lambda:'tester'
for route in routes.router.routes:
    if route.path.startswith('/warehouse-assistant/api/interwarehouse'):
        app.add_api_route(route.path, route.endpoint, methods=list(route.methods))
root=Path(__file__).resolve().parents[1]/'app/static'

@app.get('/')
def page():
    return HTMLResponse((root/'warehouse-assistant.html').read_text(encoding='utf-8').replace('</body>','<script src="/fixture.js" defer></script></body>'))

@app.get('/static/warehouse-assistant.js')
def main_script():
    return Response((root/'warehouse-assistant.js').read_text(encoding='utf-8').replace('  start();','  startTransferFixture();'),media_type='text/javascript')

@app.get('/fixture.js')
def fixture_script():
    return Response('''async function startTransferFixture(){
      state.bootstrap={capabilities:['warehouse.order.draft','warehouse.receipt.transfer'],warehouses:[],latest_snapshot:{}};
      $('#userBadge').hidden=false;$('#userBadge').textContent='محیط آزمایشی — بدون اطلاعات واقعی';
      loadOrders=async()=>{};loadAutomaticPreorders=async()=>{};loadFulfillmentOrders=async()=>{};
      loadInventory=async()=>{};
      state.automaticPreorders=[await api('/fixture/order')];
      freshWorkflowOrder=async(kind,id)=>api(kind==='supplier_order'?'/fixture/manual':'/fixture/order');
      initializeInventoryColumns();initializeOrderingColumns();initializeAutomaticColumns();initializePreorderColumns();initializeSupplyColumns();
      initializeWorkViews();
      try{await initializeColumnLayouts()}catch(error){const alert=document.createElement('p');alert.textContent='Fixture layout: '+error.message;document.querySelector('main').prepend(alert)}
      const controls=document.createElement('div');controls.className='transfer-actions';
      controls.innerHTML='<button id="fixtureSystem" type="button">تست پیش‌سفارش سیستمی</button><button id="fixtureManual" type="button">تست پیش‌سفارش دستی</button><button id="fixtureCheckbar" type="button">تست چک‌بار</button><button id="fixtureReview" type="button">تست پاسخ تأمین‌کننده</button>';
      document.querySelector('main').prepend(controls);
      $('#fixtureSystem').onclick=async()=>{state.automaticPreorders=[await api('/fixture/order')];openPreorderPreview(1)};
      $('#fixtureManual').onclick=()=>openManualEdit(1);
      $('#fixtureCheckbar').onclick=()=>{
        checkbarClear();checkbarState.source={warehouse:'karaj',supplier:'آزمایشی',products:[],order_ids:[]};
        checkbarState.lines=state.automaticPreorders[0].lines.map(line=>({...line,cartons:2,units:0,remaining_qty:24,received_qty:0,order_quantity:24,manufacturer_price_new:'',consumer_price_new:''}));
        $('#checkbarEditor').hidden=false;$('#checkbarOrderPicker').hidden=true;
        $('#checkbarDialog').showModal();renderCheckbarLines();
      };
      $('#fixtureReview').onclick=()=>{
        const sample={status:'submitted',requested_delivery_date:'1405/06/22',proposed_delivery_date:'1405/06/23',lines:state.automaticPreorders[0].lines.map(line=>({...line,original_cartons:2,proposed_cartons:3}))};
        $('#supplierReviewContent').innerHTML=supplierReviewContent(sample);$('#supplierReviewDecision').hidden=false;$('#supplierReviewDialog').showModal();
      };
      RESERVE_FIXTURE_START
      switchView('transfers');
    }'''.replace('RESERVE_FIXTURE_START',"rebalanceState.stage='documents';rebalanceState.direction='all';" if any(x in sys.argv for x in ('--reserve-shortage','--lifecycle')) else ''),media_type='text/javascript')

@app.get('/fixture/order')
def fixture_order():
    return service.get_automatic_preorder(settings,1)

@app.get('/fixture/manual')
def fixture_manual():
    return service.get_supplier_order(settings,manual['id'],'tester',include_all=True)

@app.get('/warehouse-assistant/api/table-layouts')
def fixture_layouts():
    return {'layouts': []}

app.mount('/static', StaticFiles(directory=root), name='static')
if __name__=='__main__':
    uvicorn.run(app,host='127.0.0.1',port=8027)
