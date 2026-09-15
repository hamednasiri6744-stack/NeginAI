const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const source = readFileSync('app/static/warehouse-assistant.js', 'utf8');
const fulfillmentSource = readFileSync('app/static/warehouse-fulfillment.js', 'utf8');
const html = readFileSync('app/static/warehouse-assistant.html', 'utf8');
  const views = ['inventory','supply','ordering','automatic','preorders','fulfillment','checkbar','purchase','unbilled'];

test('Fluent theme is opt-in, local and loaded after the existing layout',()=>{
  assert.match(html,/<body class="wa-fluent">/);
  assert.match(html,/warehouse-assistant-fluent\.css\?v=1/);
  assert.ok(html.indexOf('warehouse-assistant-fluent.css')>html.indexOf('warehouse-assistant.css'));
  const theme=readFileSync('app/static/warehouse-assistant-fluent.css','utf8');
  assert.match(theme,/--fluent-brand:\s*#126d50/);
  assert.match(theme,/:focus-visible/);
  assert.match(theme,/auto-dirty/);
  assert.match(theme,/is-negative/);
  assert.match(theme,/@media\s*\(forced-colors:\s*active\)/);
  assert.doesNotMatch(theme,/@import|https?:|linear-gradient|radial-gradient|font-size:\s*(?:1[6-9]|[2-9]\d)px|table-layout:/);
});

test('Persian, Arabic and English digits compare identically, including decimals and grouping',()=>{
  const {context}=setup();
  for(const value of ['۱۲٬۳۴۵٫۶','١٢٬٣٤٥٫٦','12,345.6']){
    assert.equal(vm.runInContext(`normalizeSearchText(${JSON.stringify(value)})`,context),'12345.6');
  }
  assert.equal(vm.runInContext("normalizeSearchText('۱۴۰۵/۰۶/۱۴')",context),'1405/06/14');
  assert.equal(vm.runInContext('normalizeSearchText(0)',context),'0');
  assert.equal(vm.runInContext('normalizeSearchText(null)',context),'');
});

test('automatic filters normalize both stored values and typed text without changing drafts',()=>{
  const {context}=setup();
  context.filter={value:'۲۰',dataset:{autoFilter:'product_count'}};
  context.document.querySelectorAll=()=>[context.filter];
  assert.equal(vm.runInContext('automaticFilterMatches({id:1,product_count:20})',context),true);
  context.filter.value='20';
  assert.equal(vm.runInContext("automaticFilterMatches({id:1,product_count:'٢٠'})",context),true);
  context.filter.value='21';
  assert.equal(vm.runInContext('automaticFilterMatches({id:1,product_count:20})',context),false);
});

test('fixed widths ignore contents and hidden columns do not leave width behind',()=>{
  const {context}=setup();
  const headers=['supplier','contact_email','product_count'].map(key=>({dataset:{autoColumn:key},style:{},hidden:false}));
  const table={style:{},classList:{contains(){return false},add(){}},querySelectorAll(){return headers}};
  context.table=table;
  vm.runInContext('fitFixedTableColumns(table)',context);
  assert.equal(table.style.width,'467px');
  headers[0].textContent='very long name '.repeat(100);
  headers[1].hidden=true;
  vm.runInContext('fitFixedTableColumns(table)',context);
  assert.equal(table.style.width,'292px');assert.equal(headers[0].style.width,'180px');
});

test('balance and history tables do not collapse to checkbox-width columns',()=>{
  const {context}=setup();
  for(const id of ['fulfillmentBalanceTable','fulfillmentBalanceHistoryTable','fulfillmentLinkedReceiptsTable']){
    const markup=html.match(new RegExp(`<table id="${id}">([\\s\\S]*?)</thead>`))?.[1];
    assert.ok(markup,`${id} must have a stable table id`);
    const headers=[...markup.matchAll(/<th\b([^>]*)>/g)].map(([,attrs])=>({
      dataset:{column:attrs.match(/data-column="([^"]+)"/)?.[1],userColumnWidth:attrs.match(/data-user-column-width="([^"]+)"/)?.[1]},
      style:{},hidden:false
    }));
    assert.ok(headers.every(h=>h.dataset.column),`${id} needs semantic column roles`);
    context.table={id,style:{},classList:{contains:()=>false,add(){}},querySelectorAll:()=>headers};
    vm.runInContext('fitFixedTableColumns(table)',context);
    assert.ok(headers.every(h=>parseFloat(h.style.width)>=100),`${id} columns must remain readable`);
    assert.ok(parseFloat(context.table.style.width)>=800,`${id} must not shrink into the corner`);
    const name=headers.find(h=>h.dataset.column==='product_name');
    if(name)assert.ok(parseFloat(name.style.width)>=250);
  }
});

test('fulfillment and receipt columns have explicit role widths, independent of long data',()=>{
  const {context}=setup();
  for(const [id,attr,keys,expected] of [
    ['fulfillmentTable','fulfillmentColumn',['number','supplier','supplier-confirmation','warehouse','sent','delivery_date','viewed','notification','remaining','status','actions'],[130,160,170,90,150,110,170,150,120,120,196]],
    ['fulfillmentReceiptTable','receiptColumn',['code','name','ordered','previous','cumulative','units','complete'],[104,248,96,116,100,88,108]],
    ['preorderCatalogTable','catalogColumn',['code','manufacturer_code','barcode','name','stock','incoming','basis','daily','coverage','price','cartons','action'],[90,100,140,220,80,80,90,90,90,150,80,96]],
  ]){
    const headers=keys.map(key=>({dataset:{[attr]:key},style:{},hidden:false,textContent:'very long content'.repeat(20)}));
    context.table={id,style:{},classList:{contains(){return false},add(){}},querySelectorAll(){return headers}};
    vm.runInContext('fitFixedTableColumns(table)',context);
    assert.deepEqual(headers.map(h=>h.style.width),expected.map(n=>`${n}px`));
    assert.equal(context.table.style.width,`${expected.reduce((a,b)=>a+b,0)}px`);
  }
});

test('receipt status distinguishes partial, pending and complete without color alone',()=>{
  const context=vm.createContext({document:{addEventListener(){}}});
  vm.runInContext(readFileSync('app/static/warehouse-fulfillment.js','utf8'),context);
  assert.match(vm.runInContext("fulfillmentStatusLabel({status:'awaiting_supply',received_qty:0})",context),/در انتظار دریافت/);
  assert.match(vm.runInContext("fulfillmentStatusLabel({status:'awaiting_supply',received_qty:12})",context),/دریافت ناقص/);
  assert.match(vm.runInContext("fulfillmentStatusLabel({status:'received',received_qty:24})",context),/دریافت کامل/);
});

test('inventory uses compact role-based widths without shrinking other forms',()=>{
  const {context}=setup();
  const keys=['manufacturer','brand','warehouse_name','conversion_rate','on_hand_qty','reserved_qty','barcode','product_name'];
  const headers=keys.map(column=>({dataset:{column},style:{},hidden:false}));
  const cell={textContent:'تولیدکننده با نام کامل',title:''};
  context.table={style:{},classList:{contains(name){return name==='inventory-table'},add(){}},
    querySelectorAll(selector){return selector.startsWith('thead')?headers:[cell]}};
  vm.runInContext('fitFixedTableColumns(table)',context);
  assert.deepEqual(headers.map(h=>h.style.width),['110px','84px','96px','60px','88px','88px','116px','220px']);
  assert.equal(context.table.style.width,'862px');
  assert.equal(cell.title,cell.textContent);
  headers[0].hidden=true;
  vm.runInContext('fitFixedTableColumns(table)',context);
  assert.equal(context.table.style.width,'752px');
  assert.equal(vm.runInContext("fixedColumnWidth('manufacturer')",context),160);
});

test('explicit resized width survives repeated fitting and hidden columns retain their width',()=>{
  const {context}=setup();
  const headers=[{dataset:{column:'product_name',userColumnWidth:'320'},style:{},hidden:false},
    {dataset:{column:'barcode',userColumnWidth:'180'},style:{},hidden:true}];
  context.table={style:{},classList:{contains(){return false},add(){}},querySelectorAll(){return headers}};
  for(let i=0;i<3;i++)vm.runInContext('fitFixedTableColumns(table)',context);
  assert.equal(headers[0].style.width,'320px');assert.equal(context.table.style.width,'320px');
  headers[1].hidden=false;vm.runInContext('fitFixedTableColumns(table)',context);
  assert.equal(context.table.style.width,'500px');
  delete headers[0].dataset.userColumnWidth;vm.runInContext('fitFixedTableColumns(table)',context);
  assert.equal(headers[0].style.width,'220px');
});

function setup() {
  const nodes = Object.fromEntries(views.map(v=>['#'+v+'View',{hidden:false}]));
  const buttons = views.map(view=>({dataset:{view},attributes:{},classList:{toggle(){}},
    setAttribute(k,v){this.attributes[k]=v},removeAttribute(k){delete this.attributes[k]}}));
  const context = vm.createContext({Intl,URLSearchParams,sessionStorage:{getItem(){return null}},
    document:{addEventListener(){},querySelector:s=>nodes[s],querySelectorAll:()=>buttons},
    location:{hash:'#inventory'},history:{replaceState(){},pushState(){}},requestAnimationFrame(){return 1},cancelAnimationFrame(){}});
  vm.runInContext(source,context);
  vm.runInContext(readFileSync('app/static/warehouse-order-workflow.js','utf8'),context);
  vm.runInContext('loadFulfillmentOrders=async()=>{}',context);
  return {context,nodes,buttons};
}

test('manual orders use compact rows, real ordered quantity, retained deleted history',()=>{
  const {context,nodes}=setup();nodes['#ordersList']={innerHTML:''};
  context.orders=[{id:1,order_number:'MAN-1',supplier:'<supplier>',warehouse_name:'warehouse',created_at:'2026-09-08',created_by:'worker',total_quantity:24,lines:[{product_code:'00123',product_name:'toothpaste',brand:'brand',order_quantity:24}]}];
  vm.runInContext('fitTableWrapsToViewport=()=>{};renderOrders(orders)',context);
  assert.match(nodes['#ordersList'].innerHTML,/manualOrdersTable/);
  assert.match(nodes['#ordersList'].innerHTML,/data-manual-delete="1"/);
  assert.match(nodes['#ordersList'].innerHTML,/۲۴ عدد/);
  assert.match(nodes['#ordersList'].innerHTML,/&lt;supplier&gt;/);
  context.orders[0].deleted=true;vm.runInContext('renderOrders(orders)',context);
  assert.doesNotMatch(nodes['#ordersList'].innerHTML,/data-manual-delete/);
  assert.match(nodes['#ordersList'].innerHTML,/حذف‌شده/);
});

test('manual order delete requires confirmation and only targets the chosen order',async()=>{
  const {context}=setup(),calls=[];context.confirm=()=>false;
  context.capture=async(path,options)=>{calls.push({path,options})};
  context.button={dataset:{manualNumber:'MAN-1',manualDelete:'1'}};
  vm.runInContext('api=capture;loadOrders=async()=>{};toast=()=>{}',context);
  await vm.runInContext('deleteManualOrder(button)',context);assert.equal(calls.length,0);
  context.confirm=()=>true;await vm.runInContext('deleteManualOrder(button)',context);
  assert.equal(calls.length,1);assert.equal(calls[0].path,'/warehouse-assistant/api/supplier-orders/1');
  assert.equal(calls[0].options.method,'DELETE');assert.deepEqual(JSON.parse(calls[0].options.body),{confirmed:true});
});

test('email requires confirmation and posts the displayed snapshot as JSON',async()=>{
  const {context}=setup();let calls=0,prompt='';
  context.window={confirm(text){prompt=text;return false}};
  context.capture=async(path,options)=>{calls++;context.request={path,options};return {preorder:{id:1,preorder_number:'AUTO-TEST',supplier:'supplier',contact_email:'current@example.com',contact_mobile:'09121112233',total_cartons:2,email_send_token:'fresh-snapshot'},send_status:'sent'}};
  context.button={dataset:{preorderId:'1',preorderAction:'send-email'},disabled:false};
  vm.runInContext("state.automaticPreorders=[{id:1,preorder_number:'AUTO-TEST',supplier:'supplier',contact_email:'buyer@example.com',total_cartons:2,email_send_token:'confirmed-snapshot'}]; api=capture;renderAutomaticPreorders=()=>{};toast=()=>{};",context);
  await vm.runInContext('automaticPreorderAction(button)',context);
  assert.equal(calls,1);assert.equal(context.button.disabled,false);
  assert.match(prompt,/current@example.com/);assert.match(prompt,/09121112233/);assert.match(prompt,/AUTO-TEST/);
  context.window.confirm=()=>true;
  await vm.runInContext('automaticPreorderAction(button)',context);
  assert.equal(calls,3);assert.match(context.request.path,/\/1\/send-email$/);
  assert.equal(context.request.options.headers['Content-Type'],'application/json');
  assert.equal(JSON.parse(context.request.options.body).expected_token,'fresh-snapshot');
});

test('revoking approval requires confirmation and never calls send',async()=>{
  const {context}=setup();const calls=[];
  context.window={confirm(){return false}};
  context.capture=async(path,options)=>{calls.push(path);return {preorder:{id:1,status:'awaiting_approval'}}};
  context.button={dataset:{preorderId:'1',preorderAction:'revoke-approval'},disabled:false};
  vm.runInContext("state.automaticPreorders=[{id:1,preorder_number:'AUTO-TEST',status:'approved'}];api=capture;renderAutomaticPreorders=()=>{};toast=()=>{};",context);
  await vm.runInContext('automaticPreorderAction(button)',context);
  assert.equal(calls.length,0);assert.equal(context.button.disabled,false);
  context.window.confirm=()=>true;
  await vm.runInContext('automaticPreorderAction(button)',context);
  assert.deepEqual(calls,['/warehouse-assistant/api/automatic-preorders/1/revoke-approval']);
  assert.equal(vm.runInContext('state.automaticPreorders[0].status',context),'awaiting_approval');
  const status=vm.runInContext("preorderStatus({status:'awaiting_approval',email_delivery:{status:'failed',recipient:'old@example.com'}})",context);
  assert.match(status,/منتظر تأیید کاربر/);
  assert.doesNotMatch(status,/تلاش مجدد/);
});

test('saving contacts reloads ready orders without running their calculation',async()=>{
  const {context,nodes}=setup();const paths=[];let reloaded=0;
  nodes['#saveAutomaticSettingsButton']={};
  context.capture=async(path)=>{paths.push(path);return {id:1,contact_email:'new@example.com'}};
  context.reload=async()=>{reloaded++};
  vm.runInContext("state.automaticDrafts={1:{contact_email:'new@example.com'}};state.automaticSettings=[{id:1}];api=capture;validateAutomaticPayload=()=>true;loadAutomaticPreorders=reload;renderAutomaticSettings=()=>{};toast=()=>{};",context);
  await vm.runInContext('saveAutomaticSettings()',context);
  assert.deepEqual(paths,['/warehouse-assistant/api/automatic-settings/1']);
  assert.equal(reloaded,1);
  assert.equal(vm.runInContext('Object.keys(state.automaticDrafts).length',context),0);
});

test('uncertain HTTP result cannot be retried immediately and status text is escaped',async()=>{
  const {context}=setup();
  context.window={confirm(){return true}};
  context.capture=async()=>{throw Error('network')};
  context.button={dataset:{preorderId:'1',preorderAction:'send-email'},disabled:false};
  vm.runInContext("state.automaticPreorders=[{id:1,preorder_number:'test',supplier:'supplier',contact_email:'buyer@example.com',total_cartons:2}];api=capture;toast=()=>{};",context);
  await vm.runInContext('automaticPreorderAction(button)',context);
  assert.equal(context.button.disabled,true);
  context.order={email_delivery:{status:'unknown',recipient:'buyer@example.com',error:'<img src=x>'}};
  const status=vm.runInContext('preorderStatus(order)',context);
  assert.match(status,/نیازمند بررسی/);assert.doesNotMatch(status,/<img/);
});

test('every page has exactly one current accessible navigation item',()=>{
  const {context,nodes,buttons}=setup();
  for(const view of views){
    vm.runInContext(`switchView('${view}')`,context);
    assert.equal(nodes['#'+view+'View'].hidden,false);
    assert.equal(Object.values(nodes).filter(n=>!n.hidden).length,1);
    assert.deepEqual(buttons.filter(b=>b.attributes['aria-current']==='page').map(b=>b.dataset.view),[view]);
  }
});
test('unknown navigation falls back to inventory',()=>{
  const {context,buttons}=setup();vm.runInContext("switchView('bad-view')",context);
  assert.equal(buttons[0].attributes['aria-current'],'page');
});
test('table controls and business inputs retain their stable IDs',()=>{
  for(const id of ['inventoryDisplayOptions','inventoryViewSelect','inventoryViewName','inventoryViewDefault',
    'saveInventoryViewButton','deleteInventoryViewButton','manualRefreshPreordersButton','saveAutomaticSettingsButton']){
    assert.equal((html.match(new RegExp(`id="${id}"`,'g'))||[]).length,1);
  }
  assert.match(html, /<details class="workspace-options" id="inventoryDisplayOptions">/);
  assert.match(html, /aria-labelledby="previewPreorderTitle"/);
  for(const view of views) assert.match(html,new RegExp(`data-view="${view}" aria-label="[^"]+" title="[^"]+"`));
});
test('preview keeps baseline demand, prices, coverage and escaped product names',()=>{
  const {context}=setup();
  const markup=vm.runInContext(`previewPreorderLine({product_code:'T',product_name:'<test>',conversion_rate:12,cartons:3,
    physical_procurement_qty:24,in_transit_qty:30,pending_receipt_qty:6,inventory_position_qty:60,
    average_daily_out:10,coverage_days:6,sales_rate_days:6,raw_period_out:72,adjusted_period_out:60,
    exceptional_period_out:12,demand_anomaly_days:1,system_suggested_cartons:3,
    unadjusted_suggested_cartons:7,manufacturer_price:120,consumer_price:150,approximate_price:90,order_quantity:36},true)`,context);
  assert.ok(markup.includes('&lt;test&gt;'));assert.ok(!markup.includes('<test>'));
  assert.match(markup,/unadjusted-suggestion/);assert.match(markup,/۷ کارتن/);
  assert.match(markup,/data-approximate-price="90"/);assert.match(markup,/value="3"/);
  assert.match(markup,/۶<small>روز/);
  for(const key of ['physical_procurement_qty','in_transit_qty','pending_receipt_qty','inventory_position_qty'])assert.match(markup,new RegExp(`data-preview-column="${key}"`));
  assert.match(markup,/data-export-value="روزانه ۱۰ عدد؛ ۶ روز موجود؛ فروش ۷۲ عدد؛ حذف هیجانی ۱۲ عدد؛ مبنا ۶۰ عدد"/);
});

test('matching table has readable defaults even after user widths are cleared',()=>{
  const {context}=setup();
  const markup=html.split('id="checkbarMatchingTable"')[1].split('</thead>')[0];
  const headers=[...markup.matchAll(/<th\b([^>]*)>/g)].map(([,attrs])=>({dataset:{defaultColumnWidth:attrs.match(/data-default-column-width="([^"]+)"/)?.[1]},style:{},hidden:false}));
  context.table={id:'checkbarMatchingTable',style:{},classList:{contains:()=>false,add(){}},querySelectorAll:()=>headers};
  vm.runInContext('fitFixedTableColumns(table)',context);
  assert.equal(headers.length,10);
  assert.ok(parseFloat(context.table.style.width)>=1300);
  assert.ok(parseFloat(headers[4].style.width)>=240);
  assert.ok(parseFloat(headers[9].style.width)>=160);
  headers[4].dataset.userColumnWidth='300';vm.runInContext('fitFixedTableColumns(table)',context);
  assert.equal(headers[4].style.width,'300px');
  delete headers[4].dataset.userColumnWidth;vm.runInContext('fitFixedTableColumns(table)',context);
  assert.equal(headers[4].style.width,'260px');
});

test('all warehouses shows separate settings and retains the warehouse column filter',()=>{
  const {context,nodes}=setup();
  nodes['#automaticWarehouseSelect']={value:''};nodes['#automaticRows']={};nodes['#automaticSummary']={};
  context.document.querySelectorAll=()=>[];
  vm.runInContext("state.automaticSettings=[{id:1,warehouse_code:'karaj',warehouse_name:'کرج'},{id:2,warehouse_code:'tehran',warehouse_name:'تهران'}];replaceTableRows=(node,html)=>node.innerHTML=html;automaticRow=row=>String(row.id);applyAutomaticColumnVisibility=()=>{};updateAutomaticSaveState=()=>{}",context);
  vm.runInContext('renderAutomaticSettings()',context);
  assert.equal(nodes['#automaticRows'].innerHTML,'12');
  nodes['#automaticWarehouseSelect'].value='tehran';
  vm.runInContext('renderAutomaticSettings()',context);
  assert.equal(nodes['#automaticRows'].innerHTML,'2');
  context.document.querySelectorAll=()=>[{dataset:{autoFilter:'warehouse'},value:'تهران'}];
  assert.equal(vm.runInContext("automaticFilterMatches({id:2,warehouse_name:'تهران'})",context),true);
});

test('all warehouse preview requests each warehouse and does not create orders',async()=>{
  const {context,nodes}=setup();const paths=[];
  nodes['#automaticWarehouseSelect']={value:''};nodes['#previewAutomaticButton']={};
  context.capture=async path=>{paths.push(path);return {warehouse:{name:path},ready_suppliers:1,suppliers:[{id:paths.length,enabled:true}]}};
  vm.runInContext("state.bootstrap={warehouses:[{code:'karaj'},{code:'tehran'},{code:'gilan'}]};api=capture;renderAutomaticSettings=()=>{};updateAutomaticSaveState=()=>{};toast=()=>{}",context);
  await vm.runInContext('previewAutomaticOrders()',context);
  assert.deepEqual(paths,['karaj','tehran','gilan'].map(w=>'/warehouse-assistant/api/automatic-settings/preview/'+w));
  assert.equal(vm.runInContext('state.automaticPreview.suppliers.length',context),3);
  assert.equal(vm.runInContext('state.automaticPreview.ready_suppliers',context),3);
  assert.equal(nodes['#automaticWarehouseSelect'].disabled,false);
  paths.length=0;nodes['#automaticWarehouseSelect'].value='karaj';
  await vm.runInContext('previewAutomaticOrders()',context);
  assert.deepEqual(paths,['/warehouse-assistant/api/automatic-settings/preview/karaj']);
});
test('approved previews remain noneditable',()=>{
  const {context}=setup();
  assert.match(vm.runInContext("previewPreorderLine({product_name:'test',cartons:3},false)",context),/disabled/);
});
test('daily demand explanation is compact, visible and states days, sales and excluded surge',()=>{
  const {context}=setup();
  const normal=vm.runInContext("demandAuditNote({sales_rate_days:30,raw_period_out_qty:240,period_out_qty:228,gross_out_qty:240,period_return_qty:12},{inventory:true})",context);
  assert.match(normal,/<span class="demand-audit-note/);
  assert.match(normal,/۳۰ روز موجود/);
  assert.match(normal,/فروش ۲۴۰ عدد/);
  assert.match(normal,/مبنای محاسبه ۲۲۸ عدد/);
  const surge=vm.runInContext("demandAuditNote({sales_rate_days:30,exceptional_period_out_qty:1000,raw_period_out_qty:1240,period_out_qty:240,demand_anomaly_days:1,amiran_period_out_qty:120,online_transfer_out_qty:48},{inventory:true})",context);
  assert.match(surge,/حذف هیجانی ۱٬۰۰۰ عدد/);
  assert.match(surge,/مبنای محاسبه ۲۴۰ عدد/);
  assert.match(surge,/۱ روز هیجانی/);
  assert.match(surge,/امیران ۱۲۰ کامل لحاظ شد/);
  assert.match(surge,/انتقال آنلاین ۴۸ کامل لحاظ شد/);
  const preview=vm.runInContext("demandAuditNote({exceptional_period_out_qty:100})",context);
  assert.match(preview,/<span class="demand-audit-note/);
});
test('editable preorder rows expose removal and zero is a valid removal value',()=>{
  const {context}=setup();
  const markup=vm.runInContext("previewPreorderLine({product_code:'T',product_name:'test',conversion_rate:12,cartons:3},true)",context);
  assert.match(markup,/min="0"/);
  assert.match(markup,/data-preview-remove/);
  assert.match(markup,/حذف قلم/);
  assert.match(source,/line\.cartons<0/);
});
test('versioned HTML requests matching UI assets',()=>{
  assert.match(html,/warehouse-assistant\.css\?v=37/);assert.match(html,/warehouse-assistant\.js\?v=84/);
  assert.match(html,/warehouse-fulfillment\.js\?v=24/);
  assert.match(html,/warehouse-fulfillment\.css\?v=5/);
  assert.match(html,/warehouse-column-layouts\.js\?v=15/);
});

test('in-transit page exposes the complete supplier coordination workflow',()=>{
  for(const state of ['all','unviewed','awaiting_supplier','changes_requested','awaiting_negin','supplier_confirmed','awaiting_delivery']){
    assert.match(html,new RegExp(`data-workflow-filter="${state}"`));
  }
  assert.match(fulfillmentSource,/workflowFilter:'all'/);
  assert.match(fulfillmentSource,/قرار دادن در کارتابل تأمین‌کننده/);
  assert.match(fulfillmentSource,/بررسی تغییرات/);
  assert.match(fulfillmentSource,/data-supplier-review=/);
  assert.doesNotMatch(fulfillmentSource,/supplier-portal-admin/);
});

test('in-transit table keeps headers and rendered cells in one semantic order',()=>{
  const table=html.match(/<table id="fulfillmentTable"[\s\S]*?<\/table>/)?.[0]||'';
  const headers=[...table.matchAll(/<th data-fulfillment-column="([^"]+)"/g)].map(match=>match[1]);
  assert.deepEqual(headers,['number','supplier','supplier-confirmation','warehouse','sent','delivery_date','viewed','notification','remaining','status','actions']);
  const rowTemplate=fulfillmentSource.match(/rows\.map\(order=>`<tr>([\s\S]*?)<\/tr>`\)/)?.[1]||'';
  const cells=[...rowTemplate.matchAll(/<td data-fulfillment-column="([^"]+)"/g)].map(match=>match[1]);
  assert.deepEqual(cells,headers);
  assert.doesNotMatch(fulfillmentSource,/prioritizeSupplierConfirmationColumn/);
});

test('delivery rows expose remaining checkbar and finish above the overflow menu',()=>{
  const context=vm.createContext({document:{addEventListener(){}},esc:value=>String(value??'')});
  vm.runInContext(fulfillmentSource,context);
  context.order={id:7,preorder_number:'AUTO-7',source_kind:'automatic',fulfillment:{status:'awaiting_supply'},supplier_portal:{id:9,workflow_status:'awaiting_link'}};
  const withPortal=vm.runInContext('fulfillmentActions(order)',context);
  const beforeMenu=withPortal.split('<details')[0];
  assert.match(beforeMenu,/قرار دادن در کارتابل تأمین‌کننده/);
  assert.doesNotMatch(beforeMenu,/چک‌بار مانده/);
  assert.equal((withPortal.match(/data-fulfillment-checkbar/g)||[]).length,1);
  context.order.supplier_portal.workflow_status='supplier_confirmed';
  const withoutPortal=vm.runInContext('fulfillmentActions(order)',context);
  assert.match(withoutPortal.split('<details')[0],/چک‌بار مانده/);
  assert.match(withoutPortal.split('<details')[0],/پایان تحویل/);
  assert.equal((withoutPortal.match(/data-fulfillment-checkbar/g)||[]).length,1);
});

test('refresh controls live only in inventory and retain the data-refresh permission',()=>{
  const inventory=html.slice(html.indexOf('id="inventoryView"'),html.indexOf('id="supplyView"'));
  const ordering=html.slice(html.indexOf('id="orderingView"'),html.indexOf('id="loginDialog"'));
  for(const id of ['inventoryDataTools','varanegarSyncForm','snapshotForm','syncPeriodDays','syncButton','snapshotFileInput','importButton']){
    assert.equal(html.split(`id="${id}"`).length-1,1);
    assert.ok(inventory.includes(`id="${id}"`));
    assert.ok(!ordering.includes(`id="${id}"`));
  }
  assert.match(inventory,/<details id="inventoryDataTools"[^>]* hidden>/);
  const {context}=setup();
  const nodes={};
  context.document.querySelector=id=>nodes[id]??=( {value:'',hidden:false} );
  context.payload={username:'Test',warehouses:[],capabilities:[],latest_snapshot:null};
  for(const allowed of [false,true,false]){
    context.payload.capabilities=allowed?['warehouse.data.refresh']:[];
    vm.runInContext('renderBootstrap(payload)',context);
    for(const id of ['inventoryDataTools','varanegarSyncForm','snapshotForm'])assert.equal(nodes['#'+id].hidden,!allowed);
  }
});

test('compact quantity view has eight decision columns; full view retains demand detail',()=>{
  const {context}=setup();
  const keys=vm.runInContext("workViewColumns('preview','quantity',previewColumnKeys)",context);
  assert.deepEqual(Array.from(keys),['product_code','product_name','inventory_position_qty','coverage_days','system_suggested_cartons','final_order_cartons','order_quantity','estimated_value']);
  const full=vm.runInContext("workViewColumns('preview','all',previewColumnKeys)",context);
  for(const key of ['physical_procurement_qty','in_transit_qty','pending_receipt_qty','unadjusted_suggested_cartons','average_daily_out'])assert.ok(full.includes(key));
  assert.ok(!keys.includes('approximate_price'));
  assert.equal(vm.runInContext("workViewColumns('inventory','prices',['product_name','sale_price','unknown']).join(',')",context),'product_name,sale_price');
});

test('changing a work view preserves draft objects and never persists a preference',()=>{
  const {context}=setup();
  context.choices=['supplier','minimum_cartons','contact_email'].map(value=>({value,checked:true}));
  context.table={closest(){return null}};
  context.document.querySelector=selector=>selector==='#automaticTable'?context.table:null;
  context.document.querySelectorAll=()=>context.choices;
  vm.runInContext("state.automaticDrafts={7:{minimum_cartons:200,contact_email:'sample@example.test'}};state.tablePreferences={automatic_settings:['supplier']};refreshWorkViewState=()=>{};fitTableWrapsToViewport=()=>{};workViews.automatic.apply=()=>{};",context);
  const before=vm.runInContext('JSON.stringify([state.automaticDrafts,state.tablePreferences])',context);
  vm.runInContext("applyWorkView('automatic','contacts')",context);
  assert.deepEqual(context.choices.map(c=>c.checked),[true,false,true]);
  vm.runInContext("applyWorkView('automatic','rules')",context);
  assert.deepEqual(context.choices.map(c=>c.checked),[true,true,false]);
  assert.equal(vm.runInContext('JSON.stringify([state.automaticDrafts,state.tablePreferences])',context),before);
});

test('inventory, ordering and preview work views expose manufacturer and the actual level-three group',()=>{
  const {context}=setup();
  for(const [table,views] of [['inventory',['stock','demand','prices','identity']],['ordering',['quantity']],['preview',['all','prices']]]){
    for(const view of views){
      const keys=vm.runInContext(`workViewColumns('${table}','${view}',['product_code','manufacturer','group_level3','sale_price'])`,context);
      assert.ok(keys.includes('manufacturer'),`${table}/${view}`);
      assert.ok(keys.includes('group_level3'),`${table}/${view}`);
    }
  }
  assert.match(vm.runInContext('groupLevel3Cell(null)',context),/مشخص نشده/);
  assert.match(vm.runInContext("groupLevel3Cell('  ')",context),/مشخص نشده/);
  assert.equal(vm.runInContext("groupLevel3Cell('شوینده')",context),'شوینده');
  assert.equal(vm.runInContext("groupLevel3Cell('<img>')",context),'&lt;img&gt;');
});

test('preview view switching hides cells without recreating quantity inputs',()=>{
  const {context}=setup();
  const keys=Array.from(vm.runInContext('previewColumnKeys',context));
  const cells=keys.map(()=>({hidden:false}));
  const final=keys.indexOf('final_order_cartons'),inventory=keys.indexOf('inventory_position_qty'),price=keys.indexOf('approximate_price');
  const input={value:'235',disabled:false};cells[final].input=input;
  context.table={closest(){return null},querySelectorAll(){return [{children:cells}]}};
  context.document.querySelector=()=>context.table;
  vm.runInContext('refreshWorkViewState=()=>{};fitTableWrapsToViewport=()=>{};',context);
  vm.runInContext("applyWorkView('preview','prices')",context);
  assert.equal(cells[final].input,input);assert.equal(input.value,'235');assert.equal(input.disabled,false);
  assert.equal(cells[price].hidden,false);assert.equal(cells[inventory].hidden,true);
  vm.runInContext("applyWorkView('preview','quantity')",context);
  assert.equal(cells[inventory].hidden,false);assert.equal(cells[price].hidden,true);assert.equal(input.value,'235');
});

test('hidden active filters include zero and leave visible filters alone',()=>{
  const {context}=setup();
  context.table={querySelectorAll(){return [['۰',true],['',true],['20',false]].map(([value,hidden])=>({value,closest(){return {hidden}}}))}};
  assert.equal(vm.runInContext('hiddenWorkViewFilters(table).length',context),1);
});

test('long cell text has safe keyboard-accessible expansion and short text stays simple',()=>{
  const {context}=setup();
  context.name='<img src=x onerror=alert(1)> '+ 'نام کامل '.repeat(12);
  const markup=vm.runInContext('expandableCellText(name)',context);
  assert.match(markup,/<details class="cell-text-details"><summary/);
  assert.match(markup,/aria-label="نمایش متن کامل:/);assert.match(markup,/&lt;img/);
  assert.doesNotMatch(markup,/<img/);
  assert.equal(markup.match(/<summary[^>]*>(.*?)<\/summary>/s)[1],vm.runInContext('esc(name)',context));
  assert.equal(vm.runInContext("expandableCellText('برند')",context),'برند');
});

test('Persian search matches Arabic letter variants, spaces and half-spaces',()=>{
  const {context}=setup();
  assert.equal(vm.runInContext("normalizeSearchText('  کم‌چرب   كيسه ۲۰  ')",context),'کم چرب کیسه 20');
});

test('Vazirmatn is locally served with its license and no runtime CDN',()=>{
  const css=readFileSync('app/static/warehouse-assistant-workspace.css','utf8');
  assert.match(html,/warehouse-assistant-workspace\.css\?v=1/);
  assert.doesNotMatch(css,/@import|https?:|zoom:|transform:\s*scale/);
  for(const weight of ['Regular','Medium','SemiBold','Bold']){
    assert.equal(readFileSync(`app/static/fonts/vazirmatn/Vazirmatn-${weight}.woff2`).subarray(0,4).toString(),'wOF2');
  }
  assert.match(readFileSync('app/static/fonts/vazirmatn/OFL.txt','utf8'),/SIL OPEN FONT LICENSE/);
});
test('compact table type uses 11px font and 16px line height without scaling the page',()=>{
  const css=readFileSync('app/static/warehouse-assistant.css','utf8').split('/* V33: shared compact density')[1];
  assert.match(css,/--wa-font-ui:11px/);
  assert.match(css,/--wa-line-ui:16px/);
  assert.match(css,/--wa-font-table:var\(--wa-font-ui\)/);
  assert.doesNotMatch(css,/\bzoom\s*:|transform\s*:\s*scale/);
});
test('shared density covers every table, controls and touch targets',()=>{
  const css=readFileSync('app/static/warehouse-assistant.css','utf8').split('/* V33: shared compact density')[1];
  assert.ok(css,'one shared compact density contract is present');
  assert.match(css,/--wa-control-size:28px/);
  assert.match(css,/--wa-line-ui:16px/);
  assert.match(css,/\.warehouse-shell \.table-wrap table/);
  assert.match(css,/\.preorder-preview-dialog/);
  assert.match(css,/@media\(pointer:coarse\)/);
  assert.doesNotMatch(css,/\bzoom\s*:|transform\s*:\s*scale/);
});
