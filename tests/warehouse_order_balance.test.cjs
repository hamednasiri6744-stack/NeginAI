const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
function setup(){
  const elements={},inputs=[],calls=[],confirms=[],notices=[];
  const context=vm.createContext({
    document:{addEventListener(){},querySelectorAll(selector){return selector==='[data-balance-product]'?inputs:[]}},
    $:key=>elements[key]??={value:'',textContent:'',disabled:false,open:false,setAttribute(key,value){this[key]=value},close(){this.open=false},showModal(){this.open=true}},
    normalizeSearchText:value=>String(value??'').replace(/[۰-۹]/g,c=>String(c.charCodeAt(0)-1776)).trim(),
    esc:value=>String(value??'').replaceAll('<','&lt;'),fa:value=>String(value),formatRefreshDate:value=>value,
    replaceTableRows:(element,value)=>element.html=value,
    toast:(...args)=>notices.push(args),state:{bootstrap:{delivery_completion_supported:true},suggestions:{old:true},automaticPreview:{old:true}},
    checkbarRequestId:()=>`synthetic-${calls.length}`,
    confirm:message=>{confirms.push(message);return context.confirmAnswer},confirmAnswer:true,
    api:async(...args)=>{calls.push(args);if(context.fail)throw context.fail;return {}},
  });
  vm.runInContext(readFileSync('app/static/warehouse-fulfillment.js','utf8'),context);
  vm.runInContext(readFileSync('app/static/warehouse-balance.js','utf8'),context);
  context.order={id:7,preorder_number:'PO-7',supplier:'Synthetic',warehouse_code:'karaj',fulfillment:{revision:3,status:'awaiting_supply',remaining_qty:80,received_qty:120,closed_qty:0,lines:[{product_code:'001',product_name:'Fixture',order_quantity:200,received_qty:120,remaining_qty:80,closed_qty:0}]}};
  vm.runInContext('fulfillmentBalanceState.order=order;fulfillmentState.orders=[order];loadFulfillmentOrders=async()=>{}',context);
  context.$('#fulfillmentBalanceReason').value='Supplier will not send remainder';
  context.$('#fulfillmentBalanceMode').value='close';
  inputs.push({dataset:{balanceProduct:'001'},value:'80'});
  return {context,elements,inputs,calls,confirms,notices};
}
test('closing 80 of a 200 ordered / 120 received balance confirms then posts exact revision and base units',async()=>{
  const {context,calls,confirms}=setup();
  await vm.runInContext('saveFulfillmentBalance()',context);
  assert.equal(calls.length,1);assert.match(confirms[0],/80/);
  assert.deepEqual(JSON.parse(calls[0][1].body),{expected_revision:3,request_id:'synthetic-0',reason:'Supplier will not send remainder',lines:[{product_code:'001',quantity:80}],reopen:false,confirmed:true});
  assert.equal(context.state.suggestions,null);assert.equal(context.state.automaticPreview,null);
});
test('cancel, empty quantities, excess amount and precision violations do not write',async()=>{
  for(const scenario of ['cancel','empty','over','precision','negative']){
    const {context,inputs,calls}=setup();
    if(scenario==='cancel')context.confirmAnswer=false;
    if(scenario==='empty')inputs[0].value='';
    if(scenario==='over')inputs[0].value='81';
    if(scenario==='precision')inputs[0].value='0.0001';
    if(scenario==='negative')inputs[0].value='-1';
    await vm.runInContext('saveFulfillmentBalance()',context);assert.equal(calls.length,0,scenario);
  }
});

test('reason is optional and the neutral marker works with already-running servers',async()=>{
  const {context,calls}=setup();context.$('#fulfillmentBalanceReason').value='  ';
  await vm.runInContext('saveFulfillmentBalance()',context);
  assert.equal(calls.length,1);assert.equal(JSON.parse(calls[0][1].body).reason,'بدون توضیح');
});

test('select whole remaining order fills quantities without writing or confirming',()=>{
  const {context,inputs,calls,confirms}=setup();inputs[0].value='';
  vm.runInContext('fillAllFulfillmentBalance()',context);
  assert.equal(inputs[0].value,'80');assert.equal(calls.length,0);assert.equal(confirms.length,0);
  context.$('#fulfillmentBalanceMode').value='reopen';context.order.fulfillment.lines[0].closed_qty=12;
  vm.runInContext('fillAllFulfillmentBalance()',context);assert.equal(inputs[0].value,'12');
});

test('validation and server rejection are visible inside the dialog; rejected draft is retained',async()=>{
  const {context,inputs}=setup();inputs[0].value='';
  await vm.runInContext('saveFulfillmentBalance()',context);
  assert.match(context.$('#fulfillmentBalanceNotice').textContent,/مقدار حداقل/);
  assert.equal(context.$('#fulfillmentBalanceNotice').role,'alert');
  inputs[0].value='80';context.fail={message:'مانده تغییر کرده است',status:409};
  await vm.runInContext('saveFulfillmentBalance()',context);
  assert.equal(context.$('#fulfillmentBalanceNotice').textContent,'مانده تغییر کرده است');
  assert.match(context.$('#fulfillmentBalanceLines').html,/value="80"/);
});
test('reopening checks the closed quantity, with localized numbers and three decimal places',async()=>{
  const {context,inputs,calls}=setup();
  context.order.fulfillment.lines[0].closed_qty=7.125;
  context.$('#fulfillmentBalanceMode').value='reopen';inputs[0].value='۷.۱۲۵';
  await vm.runInContext('saveFulfillmentBalance()',context);
  const payload=JSON.parse(calls[0][1].body);assert.equal(payload.reopen,true);assert.equal(payload.lines[0].quantity,7.125);
});
test('uncertain response freezes the payload and retries unchanged even after close/reopen and attempted edits',async()=>{
  const {context,inputs,calls,confirms}=setup();context.fail=new Error('timeout');
  await vm.runInContext('saveFulfillmentBalance()',context);
  assert.equal(context.$('#fulfillmentBalanceReason').disabled,true);
  await vm.runInContext('openFulfillmentBalance(7)',context);
  inputs[0].value='1';context.$('#fulfillmentBalanceMode').value='reopen';context.$('#fulfillmentBalanceReason').value='changed';context.fail=null;
  await vm.runInContext('saveFulfillmentBalance()',context);
  assert.equal(calls.length,2);assert.equal(calls[0][1].body,calls[1][1].body);assert.equal(confirms.length,1);
});
test('definite stale-revision rejection can be refreshed; concurrent clicks make one request',async()=>{
  const {context,calls}=setup();context.fail={message:'stale',status:409};
  await vm.runInContext('saveFulfillmentBalance()',context);
  assert.equal(vm.runInContext('fulfillmentBalanceState.pending.size',context),0);
  context.fail=null;
  await Promise.all([vm.runInContext('saveFulfillmentBalance()',context),vm.runInContext('saveFulfillmentBalance()',context)]);
  assert.equal(calls.length,2);
});
test('status filters distinguish partial, closed and complete without losing all open orders',()=>{
  const {context}=setup();
  assert.equal(vm.runInContext("fulfillmentMatchesStatus(order.fulfillment,'partial')",context),true);
  assert.match(vm.runInContext('fulfillmentStatusLabel(order.fulfillment)',context),/دریافت ناقص/);
  context.order.fulfillment.status='closed';
  assert.equal(vm.runInContext("fulfillmentMatchesStatus(order.fulfillment,'open')",context),false);
  assert.equal(vm.runInContext("fulfillmentMatchesStatus(order.fulfillment,'closed')",context),true);
  assert.equal(vm.runInContext("fulfillmentMatchesStatus(order.fulfillment,'all')",context),true);
  context.order.fulfillment.status='received';
  assert.equal(vm.runInContext("fulfillmentMatchesStatus(order.fulfillment,'received')",context),true);
});
test('manual receipt cannot double-count quantities already linked to checkbar receipt',async()=>{
  const {context,calls}=setup();context.order.fulfillment.manual_receive_allowed=false;
  vm.runInContext('fulfillmentState.editing=order',context);
  await vm.runInContext('saveFulfillmentReceipt()',context);assert.equal(calls.length,0);
});
test('linked receipt detail disables all legacy manual receipt controls',async()=>{
  const {context}=setup();context.order.fulfillment.manual_receive_allowed=false;
  await vm.runInContext('openFulfillmentReceipt(7)',context);
  for(const id of ['#saveFulfillmentReceipt','#fulfillmentReceiptReference','#fulfillmentInventoryReflected','#fillAllFulfillmentReceipt'])assert.equal(context.$(id).disabled,true,id);
  assert.match(context.$('#fulfillmentReceiptLines').html,/data-received-product="001"[^>]+disabled/);
});
test('order shortcut loads remaining items of the selected order without saving',async()=>{
  const {context,calls}=setup();const loads=[];
  const boxes=[{dataset:{checkbarOrder:'7'},checked:false},{dataset:{checkbarOrder:'8'},checked:true}];
  context.document.querySelectorAll=()=>boxes;
  context.openCheckbar=async()=>{context.$('#checkbarDialog').open=true};
  context.checkbarLoadContext=async reset=>{loads.push([reset,context.$('#checkbarWarehouse').value,context.$('#checkbarSupplier').value])};
  context.checkbarState={};let prepared=false;context.checkbarPrepare=async()=>{prepared=true};
  await vm.runInContext('openCheckbarForOrder(7)',context);
  assert.deepEqual(loads,[[true,'karaj',''],[undefined,'karaj','Synthetic']]);
  assert.match(context.$('#checkbarSourceStatus').textContent,/ماندهٔ PO-7/);assert.equal(calls.length,0);
  assert.equal(context.checkbarState.remainingOrderId,7);assert.equal(prepared,true);
  assert.equal(context.$('#checkbarIncludeOrderItems').checked,true);
});

test('finish delivery confirms once, preserves uncertain retry and clears previews on success',async()=>{
  const {context:c,calls,confirms}=setup();c.renderFulfillmentOrders=()=>{};
  c.confirmAnswer=false;await vm.runInContext('finishFulfillmentDelivery(7)',c);assert.equal(calls.length,0);
  c.confirmAnswer=true;c.fail=new Error('timeout');await vm.runInContext('finishFulfillmentDelivery(7)',c);
  assert.equal(calls.length,1);assert.match(confirms[1],/حذف یا اصلاح چک‌بار/);
  c.fail=null;await vm.runInContext('finishFulfillmentDelivery(7)',c);
  assert.equal(calls[0][1].body,calls[1][1].body);assert.equal(confirms.length,2);
  assert.equal(c.state.suggestions,null);assert.equal(vm.runInContext('deliveryFinishState.pending.size',c),0);
});

test('ended delivery disables reopening and is labeled explicitly',async()=>{
  const {context:c,calls}=setup();c.order.fulfillment.delivery_ended=true;
  vm.runInContext('renderFulfillmentBalance()',c);
  assert.equal(c.$('#saveFulfillmentBalance').disabled,true);
  await vm.runInContext('saveFulfillmentBalance()',c);assert.equal(calls.length,0);
  assert.match(vm.runInContext('fulfillmentStatusLabel(order.fulfillment)',c),/پایان تحویل/);
});
test('audit rows escape supplier input and show receipt reflection state',()=>{
  const {context,elements}=setup();
  context.order.fulfillment.history=[{product_code:'001',quantity:-2,reason:'<img>',recorded_by:'<user>',recorded_at:'2026-01-01'}];
  context.order.fulfillment.linked_receipts=[{document_id:9,product_code:'001',quantity:120,status:'sent',stock_status:'waiting'}];
  vm.runInContext('renderFulfillmentBalance()',context);
  assert.match(elements['#fulfillmentBalanceHistory'].html,/&lt;img>/);assert.match(elements['#fulfillmentBalanceHistory'].html,/بازگشایی 2/);
  assert.match(elements['#fulfillmentLinkedReceipts'].html,/در انتظار انعکاس موجودی/);
});
