"""Presentation-only fixture: no production settings, database or write routes."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
root = Path(__file__).resolve().parents[1] / 'app/static'

@app.get('/')
def page():
    return HTMLResponse((root / 'warehouse-assistant.html').read_text(encoding='utf-8').replace('</body>', '<script src="/fixture.js" defer></script></body>'))

@app.get('/static/warehouse-assistant.js')
def main_script():
    source = (root / 'warehouse-assistant.js').read_text(encoding='utf-8')
    assert source.count('  start();') == 1
    return Response(source.replace('  start();', '  startWorkflowFixture();'), media_type='text/javascript')

@app.get('/fixture.js')
def fixture_script():
    return Response('''async function startWorkflowFixture(){
      state.bootstrap={capabilities:['warehouse.order.draft'],warehouses:[]};
      $('#userBadge').hidden=false;$('#userBadge').textContent='آزمایشی — بدون سفارش واقعی';
      loadOrders=async()=>{};loadAutomaticPreorders=async()=>{};loadFulfillmentOrders=async()=>{};
      const base={id:1,order_number:'TEST-M1',preorder_number:'TEST-A1',supplier:'تأمین‌کننده آزمایشی',warehouse_name:'انبار تهران',
        status:'awaiting_approval',dispatch_locked:false,can_approve:true,can_edit:true,can_edit_delivery_date:true,can_delete:true,
        total_cartons:2,total_quantity:24,lines:[{product_code:'TEST1',product_name:'کالای آزمایشی',cartons:2,order_quantity:24}],fulfillment:{status:'awaiting_supply',remaining_cartons:2},order_stage:'draft'};
      renderOrders([base,{...base,id:2,order_number:'TEST-M2',status:'approved',is_approved:true,can_approve:false,can_edit:false,can_revoke_approval:true,can_send_portal:true}]);
      state.automaticPreorders=[{...base,item_count:1},{...base,id:2,preorder_number:'TEST-A2',item_count:1,status:'approved',can_approve:false,can_edit:false,can_revoke_approval:true,can_send_portal:true}];
      fulfillmentState.orders=Array.from({length:48},(_,i)=>({...base,id:i+1,preorder_number:`TEST-${i+1}`,supplier:i%2?'کامان آزمایشی':'تکین آزمایشی',
        order_stage:i<24?'sent':'delivery',fulfillment:{status:'awaiting_supply',remaining_cartons:2,received_qty:i%2?12:0},
        supplier_portal:{id:i+1,publication_state:'published',first_viewed_at:i%2?'2026-09-13T12:00:00':null,workflow_status:i<24?(i%2?'awaiting_negin':'awaiting_supplier'):'awaiting_delivery'}}));
      initializePreorderColumns();renderAutomaticPreorders();switchView('preorders');
    }''', media_type='text/javascript')

@app.get('/warehouse-assistant/api/supplier-portal/accounts')
def accounts():
    return {'accounts': []}

@app.get('/warehouse-assistant/api/supplier-portal/cartables')
def cartables():
    return {'cartables': [], 'suppliers': [], 'warehouses': []}

@app.get('/warehouse-assistant/api/table-layouts')
def layouts():
    return {'layouts': []}

app.mount('/static', StaticFiles(directory=root), name='static')
if __name__ == '__main__':
    import os
    print(f'WORKFLOW_FIXTURE_PID={os.getpid()}', flush=True)
    uvicorn.run(app, host='127.0.0.1', port=0)
