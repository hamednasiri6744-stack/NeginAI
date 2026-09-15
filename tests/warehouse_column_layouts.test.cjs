const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('app/static/warehouse-column-layouts.js','utf8');
function context(){const ctx=vm.createContext({});vm.runInContext(source,ctx);return ctx}
const plain=value=>JSON.parse(JSON.stringify(value));

test('new transfer column is visible in old layouts and placed next to product name',()=>{
  const ctx=context();const shown=[];let order;
  ctx.applyColumnWidths=()=>{};ctx.setColumnOrder=(key,value)=>order=plain(value);ctx.restoreLayoutFilters=()=>{};ctx.renderLayoutColumns=()=>{};
  ctx.layoutVisibility=(key,columns)=>shown.push(plain(columns));ctx.panel={querySelector:()=>({})};
  vm.runInContext("columnLayouts.tables.preview={available:['product_name','consumer_price','transfer_supply'],panel};",ctx);
  vm.runInContext("useColumnLayout('preview',{column_order:['product_name','consumer_price'],visible_columns:['product_name']})",ctx);
  assert.deepEqual(order,['product_name','transfer_supply','consumer_price']);
  assert.deepEqual(shown.at(-1),['product_name','transfer_supply']);
  assert.deepEqual(plain(vm.runInContext("standardColumnOrder(['product_code','product_name','consumer_price','transfer_supply'])",ctx)),['product_code','product_name','transfer_supply','consumer_price']);
});

test('old order layouts gain delivery date while newer deliberate hiding is respected',()=>{
  const ctx=context();const shown=[];
  ctx.applyColumnWidths=()=>{};ctx.setColumnOrder=()=>{};ctx.restoreLayoutFilters=()=>{};ctx.renderLayoutColumns=()=>{};
  ctx.layoutVisibility=(key,columns)=>shown.push(plain(columns));
  ctx.panel={querySelector:()=>({})};
  vm.runInContext("columnLayouts.tables.preorders={available:['supplier','delivery_date'],panel};",ctx);
  vm.runInContext("useColumnLayout('preorders',{column_order:['supplier'],visible_columns:['supplier'],widths:{},filters:{}})",ctx);
  assert.deepEqual(shown.at(-1),['supplier','delivery_date']);
  vm.runInContext("useColumnLayout('preorders',{column_order:['supplier','delivery_date'],visible_columns:['supplier'],widths:{},filters:{}})",ctx);
  assert.deepEqual(shown.at(-1),['supplier']);
});
test('resize follows RTL and LTR pointer direction and stays in safe limits',()=>{
  const ctx=context();
  assert.equal(vm.runInContext(`resizedColumnWidth(220,400,320,true)`,ctx),300);
  assert.equal(vm.runInContext(`resizedColumnWidth(220,400,480,true)`,ctx),140);
  assert.equal(vm.runInContext(`resizedColumnWidth(220,400,480,false)`,ctx),300);
  assert.equal(vm.runInContext(`resizedColumnWidth(220,400,2000,true)`,ctx),56);
  assert.equal(vm.runInContext(`resizedColumnWidth(220,400,-2000,true)`,ctx),640);
});
test('resize pointer cancellation restores original width, and Home/double-click reset it',()=>{
  const ctx=context(),events={},handleEvents={},changes=[];
  const handle={dataset:{},setAttribute(){},addEventListener:(name,fn)=>handleEvents[name]=fn,setPointerCapture(){},hasPointerCapture(){return true},releasePointerCapture(){}};
  const header={dataset:{column:'name'},textContent:'نام کالا',style:{width:'220px'},append(){},getBoundingClientRect:()=>({width:220})};
  ctx.document={createElement:()=>handle,body:{classList:{add(){},remove(){}}},addEventListener:(name,fn)=>events[name]=fn};
  ctx.window={addEventListener(){}};ctx.getComputedStyle=()=>({direction:'rtl',position:'relative'});
  ctx.layoutHeaders=()=>[header];ctx.workViews={inventory:{attribute:'column'}};
  ctx.table={};ctx.setColumnWidth=(...args)=>changes.push(args);
  vm.runInContext(`columnLayouts.tables.inventory={widths:{name:220}};bindColumnResizing('inventory',table)`,ctx);
  const event={button:0,pointerId:1,clientX:400,preventDefault(){},stopPropagation(){}};
  handleEvents.pointerdown(event);events.pointermove({...event,clientX:300});
  assert.deepEqual(changes.at(-1),['inventory','name',320]);
  events.keydown({...event,key:'Escape'});
  assert.deepEqual(changes.at(-1),['inventory','name',220]);
  assert.equal(vm.runInContext('activeColumnResize',ctx),null);
  handleEvents.keydown({...event,key:'Home'});assert.deepEqual(changes.at(-1),['inventory','name',null]);
  handleEvents.dblclick(event);assert.deepEqual(changes.at(-1),['inventory','name',null]);
  handleEvents.keydown({...event,key:'ArrowLeft'});assert.deepEqual(changes.at(-1),['inventory','name',230]);
});
test('identity order is stable, applicable only to product tables, unknown/duplicate preferences ignored',()=>{
  const ctx=context();
  assert.deepEqual(plain(vm.runInContext(`standardColumnOrder(['warehouse','brand','product_name','conversion_rate','barcode','manufacturer','product_code','manufacturer_product_code'])`,ctx)),
    ['product_code','manufacturer_product_code','barcode','product_name','brand','manufacturer','conversion_rate','warehouse']);
  assert.deepEqual(plain(vm.runInContext(`standardColumnOrder(['enabled','supplier','brand'])`,ctx)),['enabled','supplier','brand']);
  assert.deepEqual(plain(vm.runInContext(`completeColumnOrder(['b','a','c'],['c','c','invalid'])`,ctx)),['c','b','a']);
});
test('legacy preview basis column expands to the explicit warehouse and in-transit breakdown',()=>{
  const ctx=context();
  assert.deepEqual(plain(vm.runInContext(`upgradePreviewLayoutColumns(['product_code','effective_procurement_qty','average_daily_out'])`,ctx)),[
    'product_code','physical_procurement_qty','in_transit_qty','pending_receipt_qty','inventory_position_qty','average_daily_out'
  ]);
});
test('reordering moves original nodes once, preserving unkeyed selection and input drafts',()=>{
  const ctx=context();
  const selection={dataset:{}};
  const code={dataset:{column:'product_code'},input:{value:'77'}};
  const name={dataset:{column:'product_name'}};
  let moves=0;
  const row={children:[selection,name,code],insertBefore(node,before){moves++;this.children.splice(this.children.indexOf(node),1);const at=before?this.children.indexOf(before):this.children.length;this.children.splice(at,0,node)}};
  ctx.row=row;
  vm.runInContext(`moveColumnCells(row,['product_code','product_name'],cell=>cell.dataset.column)`,ctx);
  assert.deepEqual(row.children,[selection,code,name]);
  assert.equal(code.input.value,'77');
  assert.equal(moves,1);
  vm.runInContext(`moveColumnCells(row,['product_code','product_name'],cell=>cell.dataset.column)`,ctx);
  assert.equal(moves,1,'idempotent under MutationObserver');
});

test('standard product layouts place level-three group immediately after manufacturer, preserving saved custom order',()=>{
  const ctx=context();
  const order=plain(vm.runInContext(`standardColumnOrder(['product_code','group_level3','conversion_rate','manufacturer','brand','product_name'])`,ctx));
  assert.equal(order[order.indexOf('manufacturer')+1],'group_level3');
  assert.equal(new Set(order).size,6);
  assert.deepEqual(plain(vm.runInContext(`completeColumnOrder(['product_code','manufacturer','group_level3'],['group_level3','product_code','manufacturer'])`,ctx)),
    ['group_level3','product_code','manufacturer']);
});

test('saved visibility follows column identity after reordering, including preview inputs',()=>{
  const ctx=context();
  const quantity={dataset:{previewColumn:'final_order_cartons'},hidden:false,input:{value:'77'}};
  const code={dataset:{previewColumn:'product_code'},hidden:false};
  const row={children:[code,quantity],insertBefore(node,before){this.children.splice(this.children.indexOf(node),1);this.children.splice(before?this.children.indexOf(before):this.children.length,0,node)}};
  ctx.workViews={preview:{table:'.preview'}};
  ctx.$=()=>({querySelectorAll:selector=>selector==='tr'?[row]:row.children});
  vm.runInContext(`columnLayouts.tables.preview={order:['final_order_cartons','product_code'],visible:['final_order_cartons']};applyColumnOrder('preview')`,ctx);
  assert.equal(row.children[0],quantity);
  assert.equal(quantity.hidden,false);
  assert.equal(code.hidden,true);
  assert.equal(quantity.input.value,'77');
});

test('table order is restored to new rows without changing hidden state',()=>{
  const ctx=context();
  const keys=['product_name','product_code','barcode'];
  const row={children:keys.map(key=>({dataset:{column:key},hidden:key==='barcode'})),insertBefore(node,before){this.children.splice(this.children.indexOf(node),1);this.children.splice(before?this.children.indexOf(before):this.children.length,0,node)}};
  ctx.row=row;
  vm.runInContext(`moveColumnCells(row,['product_code','barcode','product_name'],cell=>cell.dataset.column)`,ctx);
  assert.deepEqual(row.children.map(cell=>cell.dataset.column),['product_code','barcode','product_name']);
  assert.equal(row.children[1].hidden,true);
});

test('drag outside header is accepted only inside the same workspace, with a safe margin',()=>{
  const ctx=context();
  ctx.heading={left:20,right:900,top:100,bottom:140};
  ctx.scope={left:10,right:920,top:40,bottom:700};
  assert.equal(vm.runInContext(`outsideColumnHeader({x:400,y:210},heading,scope)`,ctx),true);
  assert.equal(vm.runInContext(`outsideColumnHeader({x:400,y:120},heading,scope)`,ctx),false);
  assert.equal(vm.runInContext(`outsideColumnHeader({x:400,y:145},heading,scope)`,ctx),false);
  assert.equal(vm.runInContext(`outsideColumnHeader({x:400,y:720},heading,scope)`,ctx),false);
});

test('hiding is reversible, never hides the last visible column, and keeps original order',()=>{
  const ctx=context();
  const headers=[{dataset:{column:'product_code'},hidden:false,textContent:'کد کالا'},{dataset:{column:'product_name'},hidden:false,textContent:'نام کالا'}];
  ctx.workViews={inventory:{attribute:'column'}};
  ctx.messages=[];
  ctx.toast=message=>ctx.messages.push(message);
  ctx.layoutHeaders=()=>headers;
  ctx.layoutVisibility=(key,visible)=>headers.forEach(header=>header.hidden=!visible.includes(header.dataset.column));
  vm.runInContext(`columnLayouts.tables.inventory={order:['product_code','product_name']};hideDraggedColumn('inventory','product_name')`,ctx);
  assert.equal(headers[1].hidden,true);
  assert.deepEqual(plain(vm.runInContext(`columnLayouts.tables.inventory.order`,ctx)),['product_code','product_name']);
  vm.runInContext(`hideDraggedColumn('inventory','product_code')`,ctx);
  assert.equal(headers[0].hidden,false);
  vm.runInContext(`undoHiddenColumn('inventory','product_name')`,ctx);
  assert.equal(headers[1].hidden,false);
  assert.deepEqual(plain(vm.runInContext(`columnLayouts.tables.inventory.hiddenByDrag`,ctx)),[]);
});

test('each dragged-out column has an independent return action; restoring one keeps the others',()=>{
  const ctx=context(),headers=['code','name','brand','stock'].map(column=>({dataset:{column},hidden:false,textContent:column}));
  ctx.workViews={inventory:{attribute:'column'}};ctx.layoutHeaders=()=>headers;ctx.toast=()=>{};
  ctx.layoutVisibility=(key,visible)=>headers.forEach(header=>header.hidden=!visible.includes(header.dataset.column));
  vm.runInContext(`columnLayouts.tables.inventory={order:['code','name','brand','stock']};hideDraggedColumn('inventory','code');hideDraggedColumn('inventory','name');hideDraggedColumn('inventory','brand');hideDraggedColumn('inventory','code')`,ctx);
  assert.deepEqual(plain(vm.runInContext(`columnLayouts.tables.inventory.hiddenByDrag||[]`,ctx)),['code','name','brand']);
  vm.runInContext(`undoHiddenColumn('inventory','name')`,ctx);
  assert.equal(headers[1].hidden,false);
  assert.equal(headers[0].hidden,true);assert.equal(headers[2].hidden,true);
  assert.deepEqual(plain(vm.runInContext(`columnLayouts.tables.inventory.hiddenByDrag`,ctx)),['code','brand']);
  vm.runInContext(`undoHiddenColumn('inventory','code');undoHiddenColumn('inventory','brand')`,ctx);
  assert.equal(headers.every(header=>!header.hidden),true);
  assert.deepEqual(plain(vm.runInContext(`columnLayouts.tables.inventory.order`,ctx)),['code','name','brand','stock']);
  assert.deepEqual(plain(vm.runInContext(`columnLayouts.tables.inventory.hiddenByDrag`,ctx)),[]);
  vm.runInContext(`hideDraggedColumn('inventory','code')`,ctx);
  headers[0].hidden=false; // Restored through a preset or column checkbox.
  vm.runInContext(`renderHiddenColumns('inventory')`,ctx);
  assert.deepEqual(plain(vm.runInContext(`columnLayouts.tables.inventory.hiddenByDrag`,ctx)),[]);
});

test('pointer gesture handlers distinguish reorder, hide, click, cancellation and outside-workspace drops',()=>{
  const ctx=context(),listeners={table:{},document:{},window:{}};
  const listen=target=>(name,fn)=>{listeners[target][name]=fn};
  const classList={add(){},remove(){},toggle(){}};
  const header={dataset:{column:'code'},classList,getBoundingClientRect:()=>({bottom:140})};
  const target={closest:selector=>selector==='thead tr:first-child th'?header:null};
  let captured=null,hit=null;
  const table={addEventListener:listen('table'),setPointerCapture:id=>captured=id,hasPointerCapture:id=>captured===id,releasePointerCapture:()=>captured=null,
    closest:()=>({getBoundingClientRect:()=>({left:10,width:900})}),contains:node=>node===header||node===other,
    querySelector:()=>({getBoundingClientRect:()=>({left:20,right:900,top:100,bottom:140})}),querySelectorAll:()=>[header]};
  const other={dataset:{column:'name'}};
  const scope={getBoundingClientRect:()=>({left:10,right:920,top:40,bottom:700})};
  const zone={hidden:true,style:{},classList};
  ctx.document={addEventListener:listen('document'),elementFromPoint:()=>hit?{closest:()=>hit}:null};
  ctx.window={innerHeight:720,innerWidth:1280,addEventListener:listen('window')};
  ctx.workViews={inventory:{table:'table',attribute:'column'}};ctx.$=()=>table;ctx.layoutHeaders=()=>[header];
  ctx.table=table;ctx.scope=scope;ctx.zone=zone;
  const hidden=[],moved=[];
  ctx.hideDraggedColumn=(...args)=>hidden.push(args);ctx.moveColumnTo=(...args)=>moved.push(args);
  vm.runInContext(`columnLayouts.tables.inventory={order:['code','name'],dropZone:zone};bindColumnDragging('inventory',table,scope,zone)`,ctx);
  const event=(x,y,extra={})=>({target,button:0,pointerType:'mouse',pointerId:1,clientX:x,clientY:y,preventDefault(){},...extra});
  const down=()=>listeners.table.pointerdown(event(100,120));
  const move=(x,y)=>listeners.document.pointermove(event(x,y));
  const up=(x,y)=>listeners.document.pointerup(event(x,y));
  down();up(100,120);assert.equal(hidden.length,0,'ordinary click does not hide');
  down();move(100,220);assert.equal(zone.hidden,false);up(100,220);
  assert.deepEqual(hidden,[['inventory','code']]);assert.equal(zone.hidden,true);assert.equal(captured,null);
  down();move(100,220);listeners.document.keydown({key:'Escape',preventDefault(){}});up(100,220);
  assert.equal(hidden.length,1,'Escape cancels without hiding');
  down();move(100,220);listeners.document.pointercancel(event(100,220));up(100,220);
  assert.equal(hidden.length,1,'pointer cancellation does not hide');
  down();move(100,710);up(100,710);assert.equal(hidden.length,1,'outside workspace cancels');
  hit=other;down();move(300,120);up(300,120);assert.deepEqual(moved,[['inventory','code',1]]);
  listeners.table.pointerdown(event(100,120,{pointerType:'touch'}));
  assert.equal(captured,null,'touch scrolling is left alone; dropdown remains available');
});

test('universal tables receive stable server keys and canonical cell identities',()=>{
  const ctx=context();
  const headers=['product_code','barcode','name'].map((key,index)=>({dataset:index<2?{column:key}:{},textContent:key}));
  const cells=[{dataset:{}},{dataset:{}},{dataset:{}}];
  const table={dataset:{},id:'purchaseInvoicePreviewTable',tBodies:[{id:'invoiceRows'}],querySelector:selector=>selector==='thead tr:first-child th'?headers[0]:null,
    querySelectorAll:selector=>selector==='thead tr:first-child th'?headers:selector==='tr'?[{children:cells,parentElement:{tagName:'TBODY'}}]:[],closest:()=>null};
  ctx.table=table;ctx.workViews={};ctx.$=selector=>selector===`[data-layout-table="ui_purchase_invoice_preview_table"]`?table:null;
  vm.runInContext(`workViews.ui_purchase_invoice_preview_table={table:'[data-layout-table="ui_purchase_invoice_preview_table"]',attribute:'layoutColumn',generic:true};columnLayouts.tables.ui_purchase_invoice_preview_table={available:['product_code','barcode','column_3'],order:['product_code','barcode','column_3']};tagUniversalRows('ui_purchase_invoice_preview_table')`,ctx);
  assert.deepEqual(cells.map(cell=>cell.dataset.layoutColumn),['product_code','barcode','column_3']);
  assert.equal(vm.runInContext(`universalTableId(table)`,ctx),'purchase_invoice_preview_table');
});
