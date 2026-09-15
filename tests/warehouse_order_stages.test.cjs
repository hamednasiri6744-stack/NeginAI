const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const fulfillment=readFileSync('app/static/warehouse-fulfillment.js','utf8');
const workflow=readFileSync('app/static/warehouse-order-workflow.js','utf8');
const html=readFileSync('app/static/warehouse-assistant.html','utf8');

test('orders group has a unified preorder workspace and ordering contains no draft list',()=>{
  const group=html.split('class="nav-section-label">سفارش خرید</span>')[1].split('class="nav-section-label">دریافت کالا')[0];
  assert.deepEqual([...group.matchAll(/data-view="([^"]+)"/g)].map(m=>m[1]),['automatic','ordering','preorders','sent','fulfillment']);
  const inventoryGroup=html.split('class="nav-section-label">انبار و کالا</span>')[1].split('class="nav-section-label">سفارش خرید')[0];
  assert.match(inventoryGroup,/data-view="transfers"/);
  const system=html.split('id="preordersView"')[1].split('id="fulfillmentView"')[0];
  assert.match(group,/aria-label="پیش‌سفارش‌ها"/);
  assert.match(system,/manual-orders-block/);
  for(const kind of ['manual','system'])assert.match(system,new RegExp(`data-prepared-kind="${kind}"`));
  assert.match(system,/role="tablist"/);
  assert.match(system,/id="ordersList"/);
  assert.match(system,/id="automaticPreordersList"/);
  const ordering=html.split('id="orderingView"')[1].split('</main>')[0];
  assert.doesNotMatch(ordering,/ordersList|manual-orders-block/);
});

test('both kinds show all four actions; approval determines which actions are enabled',()=>{
  const {ctx,run}=context();
  for(const kind of ['supplier_order','automatic_preorder']){
    ctx.order={id:3,order_number:'M3',status:'awaiting_approval',dispatch_locked:false,can_approve:true,can_edit:true,can_revoke_approval:false,can_delete:true};
    let markup=run(`draftOrderActions(order,'${kind}')`);
    for(const label of ['تأیید','لغو تأیید','ویرایش','حذف'])assert.match(markup,new RegExp('>'+label+'</button>'));
    assert.match(markup,/<button[^>]*disabled[^>]*>لغو تأیید<\/button>/);
    assert.doesNotMatch(markup,/<button[^>]*disabled[^>]*>ویرایش<\/button>/);
    Object.assign(ctx.order,{status:'approved',is_approved:true,can_approve:false,can_edit:false,can_revoke_approval:true});
    markup=run(`draftOrderActions(order,'${kind}')`);
    assert.match(markup,/<button[^>]*disabled[^>]*>تأیید<\/button>/);
    assert.doesNotMatch(markup,/<button[^>]*disabled[^>]*>ویرایش<\/button>/);
    ctx.order.dispatch_locked=true;
    markup=run(`draftOrderActions(order,'${kind}')`);
    assert.match(markup,/<button[^>]*disabled[^>]*>ویرایش<\/button>/);
  }
});

test('editing an approved unsent order requires consent before revoking approval',async()=>{
  const {ctx,run}=context();let calls=0;
  ctx.confirm=()=>false;ctx.capture=async()=>{calls++;return {can_edit:true}};
  run('freshWorkflowOrder=async()=>({can_edit:false,can_revoke_approval:true});api=capture;loadOrders=async()=>{};loadAutomaticPreorders=async()=>{}');
  assert.equal(await run("editableWorkflowOrder('supplier_order',4)"),null);assert.equal(calls,0);
  ctx.confirm=()=>true;
  assert.equal((await run("editableWorkflowOrder('supplier_order',4)")).can_edit,true);assert.equal(calls,1);
});

function context(){
  const nodes={};
  const ctx=vm.createContext({document:{addEventListener(){},querySelectorAll(){return []}},
    state:{activeView:'sent'},$:(id)=>nodes[id]??=( {textContent:'',innerHTML:'',value:'',closest(){return this}}),
    fa:v=>String(v),esc:v=>String(v??''),normalizeSearchText:v=>String(v??''),
    expandableCellText:v=>String(v),formatRefreshDate:v=>String(v??''),
    replaceTableRows:(node,rows)=>node.innerHTML=rows});
  vm.runInContext(fulfillment,ctx);vm.runInContext(workflow,ctx);
  const main=readFileSync('app/static/warehouse-assistant.js','utf8');
  vm.runInContext(main.slice(main.indexOf('function orderDeliveryDateCell('),main.indexOf('function renderOrders(')),ctx);
  return {ctx,nodes,run:code=>vm.runInContext(code,ctx)};
}

test('delivery cell never promotes an unapproved supplier date',()=>{
  const {ctx,run}=context();
  ctx.order={supplier_portal:{status:'submitted',requested_delivery_date:'1405/06/25',proposed_delivery_date:'1405/06/27'}};
  let markup=run('orderDeliveryDateCell(order)');
  assert.match(markup,/dir="ltr">1405\/06\/25/);
  assert.match(markup,/1405\/06\/27.*منتظر تأیید شما/);
  ctx.order.supplier_portal.status='accepted';
  markup=run('orderDeliveryDateCell(order)');
  assert.match(markup,/dir="ltr">1405\/06\/27/);
  assert.doesNotMatch(markup,/منتظر تأیید/);
  ctx.order.supplier_portal.status='rejected';
  assert.match(run('orderDeliveryDateCell(order)'),/dir="ltr">1405\/06\/25/);
});

test('both draft kinds can edit dates before dispatch and cannot edit after dispatch',()=>{
  const {ctx,run}=context();
  ctx.order={id:1,dispatch_locked:false,can_edit:true,can_edit_delivery_date:true};
  for(const kind of ['supplier_order','automatic_preorder']){
    ctx.order.dispatch_locked=false;
    assert.doesNotMatch(run(`draftOrderActions(order,'${kind}')`),/<button[^>]*disabled[^>]*>تاریخ تحویل<\/button>/);
    ctx.order.dispatch_locked=true;
    assert.match(run(`draftOrderActions(order,'${kind}')`),/<button[^>]*disabled[^>]*>تاریخ تحویل<\/button>/);
  }
});

test('delivery date editor uses the correct endpoint and current order token for both kinds',async()=>{
  const {ctx,nodes,run}=context();
  const calls=[];ctx.capture=async(url,options)=>{calls.push([url,JSON.parse(options.body)]);return {}};
  ctx.event={preventDefault(){}};
  run("api=capture;loadOrders=async()=>{};loadAutomaticPreorders=async()=>{};toast=()=>{};$('#orderDateDialog').close=()=>{};");
  for(const [kind,path] of [['supplier_order','supplier-orders'],['automatic_preorder','automatic-preorders']]){
    run(`orderDateState.order={id:5,email_send_token:'current-token'};orderDateState.kind='${kind}';$('#orderDeliveryDate').value='1405/06/25'`);
    await run('saveOrderDate(event)');
    assert.deepEqual(calls.at(-1),[`/warehouse-assistant/api/${path}/5/delivery-date`,{delivery_date:'1405/06/25',expected_token:'current-token'}]);
    assert.equal(nodes['#orderDateSave'].disabled,false);
  }
});

test('only sent orders enter tracking; supplier acceptance enters delivery; historical receipts stay available',()=>{
  const {ctx,run}=context();
  for(const [order,stage] of [
    [{status:'approved'},'draft'],
    [{order_stage:'draft',dispatch_locked:true},'draft'],
    [{order_stage:'sent'},'sent'],
    [{supplier_portal:{workflow_status:'awaiting_negin',dispatch_sent:true}},'sent'],
    [{supplier_portal:{workflow_status:'supplier_confirmed'}},'delivery'],
    [{order_stage:'draft',fulfillment:{received_qty:12,status:'awaiting_supply'}},'delivery'],
    [{order_stage:'draft',fulfillment:{status:'closed'}},'delivery'],
    [{order_stage:'sent',supplier_portal:{id:4,workflow_status:'awaiting_negin'},fulfillment:{received_qty:12,status:'awaiting_supply'}},'sent'],
  ]){ctx.order=order;assert.equal(run('fulfillmentStage(order)'),stage)}
});

test('sent and delivery rows and badge counts are disjoint; sent rows have no receipt actions',()=>{
  const {ctx,nodes,run}=context();
  ctx.orders=['draft','sent','delivery'].map((stage,i)=>({id:i+1,preorder_number:stage,supplier:'S',warehouse_name:'W',order_stage:stage,source_kind:'automatic',fulfillment:{status:'awaiting_supply',remaining_cartons:2},supplier_portal:{id:i+1,workflow_status:stage==='sent'?'awaiting_negin':'supplier_confirmed'}}));
  run('fulfillmentState.orders=orders;renderFulfillmentOrders()');
  assert.match(nodes['#fulfillmentRows'].innerHTML,/>sent</);
  assert.doesNotMatch(nodes['#fulfillmentRows'].innerHTML,/>draft<|>delivery<|data-fulfillment-checkbar|data-fulfillment-receive/);
  assert.equal(nodes['#sentMenuBadge'].textContent,'1');assert.equal(nodes['#fulfillmentMenuBadge'].textContent,'1');
  run("state.activeView='fulfillment';renderFulfillmentOrders()");
  assert.match(nodes['#fulfillmentRows'].innerHTML,/>delivery</);
  assert.doesNotMatch(nodes['#fulfillmentRows'].innerHTML,/>draft<|>sent</);
  assert.match(nodes['#fulfillmentRows'].innerHTML,/data-fulfillment-checkbar/);
});

test('manual and system buttons use the same portal composer and require explicit sendability',()=>{
  const {run}=context();
  for(const kind of ['supplier_order','automatic_preorder']){
    const button=run(`orderPortalButtons({id:1,can_send_portal:true},'${kind}')`);
    assert.match(button,/قرار دادن در کارتابل تأمین‌کننده/);assert.doesNotMatch(button,/disabled|اکسل/);
    assert.match(run(`orderPortalButtons({id:1,can_send_portal:false},'${kind}')`),/disabled/);
  }
  assert.match(workflow,/expected_token:order.email_send_token/);
  assert.match(workflow,/expected_revision:assignment.revision/);
  assert.match(workflow,/confirmed:true/);
  assert.doesNotMatch(workflow,/send-sms-link|document.xlsx/);
});

test('publication without optional notification contacts never calls a sender',async()=>{
  const {run,nodes,ctx}=context();const calls=[];
  ctx.capture=async(url,options)=>{calls.push(url);return {id:7,revision:0}};
  run("api=capture;loadOrders=async()=>{};loadAutomaticPreorders=async()=>{};switchView=()=>{};toast=()=>{};orderPortalState.order={id:1,staff_delivery_date:'1405/06/25',email_send_token:'token'};orderPortalState.kind='supplier_order'");
  nodes['#orderPortalForm']={reportValidity:()=>true,querySelectorAll:()=>[]};
  nodes['#orderPortalUsername']={value:'09120000000'};
  nodes['#orderPortalMobile']={value:''};nodes['#orderPortalEmail']={value:''};
  nodes['#orderPortalDate']={value:'1405/06/25'};nodes['#orderPortalDialog']={close(){}};
  await run('sendOrderPortal({preventDefault(){}})');
  assert.deepEqual(calls,['/warehouse-assistant/api/supplier-portal/orders/publish']);
  assert.equal(run('orderPortalState.busy'),false);
});

test('opening publication prefills current notification phone without sending and permits clearing it',async()=>{
  const {run,nodes,ctx}=context();const calls=[];
  ctx.state.bootstrap={supplier_portal_publication_supported:true,supplier_portal_shared_access_supported:true};
  ctx.capture=async url=>{calls.push(url);return url.includes('order-recipient')?
    {username:'09123333333',mobile:'09123333333'}:{id:1,can_send_portal:true,contact_mobile:'09120000000'}};
  nodes['#orderPortalDialog']={showModal(){}};
  run('api=capture');
  await run("openOrderPortal('supplier_order',1)");
  assert.equal(nodes['#orderPortalUsername'].value,'09123333333');
  assert.equal(nodes['#orderPortalMobile'].value,'09123333333');
  assert.equal(calls.length,2);assert.ok(calls.every(url=>!url.includes('send-')));
  nodes['#orderPortalMobile'].value='';assert.equal(nodes['#orderPortalMobile'].value,'');
});
