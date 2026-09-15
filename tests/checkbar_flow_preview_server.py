"""Isolated UI fixture; no database, save endpoint or ERP connection."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
root = Path(__file__).resolve().parents[1] / 'app/static'

@app.get('/')
@app.get('/archive')
def page():
    return HTMLResponse((root / 'warehouse-assistant.html').read_text(encoding='utf-8').replace('</body>', '<script src="/fixture.js" defer></script></body>'))

@app.get('/static/warehouse-assistant.js')
def main_script():
    source = (root / 'warehouse-assistant.js').read_text(encoding='utf-8')
    assert source.count('  start();') == 1
    return Response(source.replace('  start();', '  startCheckbarFlowFixture();'), media_type='text/javascript')

@app.get('/fixture.js')
def fixture_script():
    return Response('''function startCheckbarFlowFixture(){
      state.bootstrap={capabilities:['warehouse.order.draft'],warehouses:[]};
      if(location.pathname==='/archive'){switchView('checkbar');return}
      checkbarClear();
      checkbarState.source={warehouse:'karaj',supplier:'آزمایشی',expected_token:'fixture',order_ids:[],catalog:[],outstanding_orders:[{number:'TEST-ORDER'}]};
      checkbarState.lines=Array.from({length:12},(_,i)=>({product_code:`TEST-${i+1}`,product_name:`کالای آزمایشی ${i+1}`,brand:'برند آزمایشی',group_level3:'آزمایشی',conversion_rate:12,preorder_id:1,preorder_number:'TEST-ORDER',order_quantity:120,received_qty:0,remaining_qty:120,cartons:'2',units:'0',manufacturer_price_new:'',consumer_price_new:'',manufacturer_price:100,consumer_price:200}));
      $('#checkbarReference').value='123';
      $('#checkbarOrderPicker').hidden=true;$('#checkbarEditor').hidden=false;
      $('#checkbarDialog').showModal();renderCheckbarLines();
    }''', media_type='text/javascript')

@app.post('/warehouse-assistant/api/checkbars/matching-preview')
async def matching(request: Request):
    payload = await request.json()
    lines = payload.get('lines', [])
    rows = [{'source_row': i+1, 'product_code': line['product_code'], 'product_name': f'کالای آزمایشی {i+1}', 'actual_qty': 24,
             'orders': [{'preorder_id': 1, 'number': 'TEST-ORDER', 'remaining_qty': 120}]} for i, line in enumerate(lines)]
    return {'revision': 'fixture', 'rows': rows, 'allocations': [{'source_row': row['source_row'], 'preorder_id': 1, 'quantity': 24} for row in rows]}

@app.get('/warehouse-assistant/api/table-layouts')
def layouts():
    return {'layouts': []}

@app.get('/warehouse-assistant/api/checkbars')
def archive(include_deleted: bool = False):
    states = ['not_sent', 'pending', 'sent', 'unknown', 'deleted']
    docs = [dict(id=i+1, number=f'TEST-CB-{i+1:03d}', warehouse_name=['انبار تهران', 'انبار کرج', 'انبار گیلان'][i % 3],
                 supplier='تأمین‌کننده آزمایشی', created_at='2026-09-13T12:00:00', receipt_state=states[i % 5],
                 receipt_number=100+i if i % 5 == 2 else None, deleted=i % 7 == 6) for i in range(36)]
    return {'documents': [doc for doc in docs if include_deleted or not doc['deleted']]}

app.mount('/static', StaticFiles(directory=root), name='static')
if __name__ == '__main__':
    import os
    print(f'CHECKBAR_FIXTURE_PID={os.getpid()}', flush=True)
    uvicorn.run(app, host='127.0.0.1', port=0)
