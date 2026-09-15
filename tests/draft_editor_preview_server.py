"""Isolated visual/HTTP test: synthetic orders, temporary DB, no ERP endpoints."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_warehouse_supplier_portal import store
from app import warehouse_assistant_service as service
from app.routes import warehouse_assistant as routes
from app.business_time import jalali_business_date, tehran_now

temporary = TemporaryDirectory(prefix='negin-draft-editor-ui-')
settings = store.__wrapped__(Path(temporary.name))
with service.warehouse_connection(settings) as conn:
    conn.execute("UPDATE warehouse_automatic_preorders SET source_supplier_order_id=NULL,status='awaiting_approval',business_date=?", (jalali_business_date(tehran_now()),))
service.transition_supplier_order(settings, 'buyer', 1, 'revoke_approval')
with service.warehouse_connection(settings) as conn:
    for table, parent in [('supplier_order_lines', 'order_id'), ('warehouse_automatic_preorder_lines', 'preorder_id')]:
        original = dict(conn.execute(f'SELECT * FROM {table} WHERE {parent}=1 LIMIT 1').fetchone())
        original.pop('id', None)
        for i in range(3, 31):
            row = {**original, 'product_code': f'TEST-{i:03}',
                   'product_name': f'کالای آزمایشی شماره {i} با نام فارسی بلند برای بررسی خوانایی جدول'}
            conn.execute(f'INSERT INTO {table} ({",".join(row)}) VALUES ({",".join("?" for _ in row)})', tuple(row.values()))
    original = dict(conn.execute('SELECT * FROM warehouse_snapshot_items LIMIT 1').fetchone())
    original.pop('id', None)
    for i in range(3, 31):
        row = {**original, 'source_row': i, 'product_code': f'TEST-{i:03}',
               'product_name': f'کالای آزمایشی شماره {i} با نام فارسی بلند برای بررسی خوانایی جدول'}
        conn.execute(f'INSERT INTO warehouse_snapshot_items ({",".join(row)}) VALUES ({",".join("?" for _ in row)})', tuple(row.values()))

app = FastAPI()
app.state.settings = settings
routes._require = lambda *args: 'buyer'
routes._is_admin = lambda *args: True
app.dependency_overrides[routes.require_session_user] = lambda: 'buyer'
# Only the exact edit endpoints are exposed; no bridge, publish, send or delete.
for route in routes.router.routes:
    if route.name in {'edit_manual_order', 'update_automatic_preorder_lines_route', 'edit_manual_delivery_date', 'edit_system_delivery_date'}:
        app.add_api_route(route.path, route.endpoint, methods=list(route.methods))
root = Path(__file__).resolve().parents[1] / 'app/static'

@app.get('/')
def page():
    html = (root / 'warehouse-assistant.html').read_text(encoding='utf-8')
    return HTMLResponse(html.replace('</body>', '<script src="/fixture.js" defer></script></body>'))

@app.get('/static/warehouse-assistant.js')
def main_script():
    source = (root / 'warehouse-assistant.js').read_text(encoding='utf-8')
    assert source.count('  start();') == 1
    return Response(source.replace('  start();', '  startDraftFixture();'), media_type='text/javascript')

@app.get('/fixture.js')
def fixture_script():
    return Response('''async function startDraftFixture(){
      state.bootstrap={draft_editor_atomic_supported:true,capabilities:['warehouse.order.draft'],warehouses:[],latest_snapshot:{}};
      $('#userBadge').hidden=false;$('#userBadge').textContent='فقط آزمایشی — ۳۰ قلم، بدون اطلاعات واقعی';
      loadOrders=async()=>{};loadAutomaticPreorders=async()=>{};loadFulfillmentOrders=async()=>{};loadInventory=async()=>{};
      freshWorkflowOrder=async(kind,id)=>api(kind==='supplier_order'?'/fixture/manual':'/fixture/system');
      initializeInventoryColumns();initializeOrderingColumns();initializeAutomaticColumns();initializePreorderColumns();initializeSupplyColumns();initializeWorkViews();
      await initializeColumnLayouts();
      const controls=document.createElement('div');controls.className='transfer-actions';
      controls.innerHTML='<button id="fixtureSystem" type="button">آزمون ویرایش سیستمی</button><button id="fixtureManual" type="button">آزمون ویرایش دستی</button>';
      document.querySelector('main').prepend(controls);
      $('#fixtureSystem').onclick=async()=>{state.automaticPreorders=[await api('/fixture/system')];openPreorderPreview(1)};
      $('#fixtureManual').onclick=()=>openManualEdit(1);
    }''', media_type='text/javascript')

@app.get('/fixture/manual')
def manual():
    return service.get_supplier_order(settings, 1, 'buyer', include_all=True)

@app.get('/fixture/system')
def system():
    return service.get_automatic_preorder(settings, 1)

@app.get('/warehouse-assistant/api/table-layouts')
def layouts():
    return {'layouts': []}

app.mount('/static', StaticFiles(directory=root), name='static')
if __name__ == '__main__':
    import os
    print(f'DRAFT_FIXTURE_PID={os.getpid()}', flush=True)
    uvicorn.run(app, host='127.0.0.1', port=0)
