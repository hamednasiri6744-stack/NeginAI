const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const source=name=>readFileSync(`app/static/${name}.js`,'utf8');
function setup(){
  const nodes={'#fulfillmentSearch':{value:''},'#fulfillmentStatusFilter':{value:'open'}};
  const inputs=[{dataset:{sharedColumnFilter:'warehouse'},value:''}];
  const wrap={scrollLeft:0,scrollTop:0};
  const table={querySelectorAll:()=>inputs,closest:()=>wrap};nodes['#fulfillmentTable']=table;
  const ctx=vm.createContext({document:{addEventListener(){},querySelectorAll:()=>[]},window:{addEventListener(){}},
    $:key=>nodes[key],esc:v=>String(v??''),state:{activeView:'sent'},requestAnimationFrame:fn=>fn(),sharedTableSorts:new WeakMap()});
  vm.runInContext(source('warehouse-order-workflow'),ctx);vm.runInContext(source('warehouse-fulfillment'),ctx);
  return {ctx,nodes,inputs,wrap,run:code=>vm.runInContext(code,ctx)};
}
for(const kind of ['supplier_order','automatic_preorder'])test(`${kind}: primary action follows approval; disabled reasons do not prescribe restart`,()=>{
  const s=setup();s.ctx.order={id:4,dispatch_locked:false,can_approve:true,can_edit:true,can_delete:true};
  let html=s.run(`draftOrderActions(order,'${kind}')`);
  assert.match(html,/<button[^>]*data-workflow-primary="true"[^>]*>تأیید<\/button>/);
  assert.doesNotMatch(html,/راه‌اندازی مجدد/);
  Object.assign(s.ctx.order,{is_approved:true,status:'approved',can_approve:false,can_edit:false,can_revoke_approval:true,can_send_portal:true});
  html=s.run(`draftOrderActions(order,'${kind}')`);
  assert.match(html,/<button[^>]*data-workflow-primary="true"[^>]*>قرار دادن در کارتابل تأمین‌کننده<\/button>/);
  assert.equal((html.match(/data-workflow-primary="true"/g)||[]).length,1);
  s.ctx.order.dispatch_locked=true;
  html=s.run(`draftOrderActions(order,'${kind}')`);
  assert.doesNotMatch(html,/data-workflow-primary="true"/);
  assert.match(html,/نتیجه.*ارسال|شروع ارسال/);
});
test('missing workflow metadata is not mislabelled as already approved',()=>{
  const s=setup();const html=s.run("draftOrderActions({id:1},'supplier_order')");
  assert.match(html,/وضعیت.*دریافت نشده/);assert.doesNotMatch(html,/راه‌اندازی مجدد/);
});
test('tracking stages retain separate search, status, workflow, column filters and scroll',()=>{
  const s=setup();s.nodes['#fulfillmentSearch'].value='کامان';s.nodes['#fulfillmentStatusFilter'].value='all';
  s.inputs[0].value='تهران';s.wrap.scrollTop=180;s.wrap.scrollLeft=-200;s.run("fulfillmentState.workflowFilter='awaiting_negin';prepareFulfillmentNavigation('sent','fulfillment')");
  assert.equal(s.nodes['#fulfillmentSearch'].value,'');assert.equal(s.inputs[0].value,'');
  s.run("state.activeView='fulfillment';restoreFulfillmentNavigationScroll()");
  s.nodes['#fulfillmentSearch'].value='تکین';s.nodes['#fulfillmentStatusFilter'].value='partial';s.inputs[0].value='کرج';s.wrap.scrollTop=250;
  s.run("fulfillmentState.workflowFilter='awaiting_delivery';prepareFulfillmentNavigation('fulfillment','inventory');state.activeView='inventory';prepareFulfillmentNavigation('inventory','sent');state.activeView='sent';restoreFulfillmentNavigationScroll()");
  assert.equal(s.nodes['#fulfillmentSearch'].value,'کامان');assert.equal(s.inputs[0].value,'تهران');assert.equal(s.wrap.scrollTop,180);assert.equal(s.wrap.scrollLeft,-200);
  assert.equal(s.run('fulfillmentState.workflowFilter'),'awaiting_negin');
  s.run("prepareFulfillmentNavigation('sent','fulfillment');state.activeView='fulfillment';restoreFulfillmentNavigationScroll()");
  assert.equal(s.nodes['#fulfillmentSearch'].value,'تکین');assert.equal(s.nodes['#fulfillmentStatusFilter'].value,'partial');assert.equal(s.inputs[0].value,'کرج');assert.equal(s.wrap.scrollTop,250);
  assert.equal(s.run('fulfillmentState.workflowFilter'),'awaiting_delivery');
});
test('account admin has no second publication, notification or approval implementation',()=>{
  const js=source('supplier-portal-admin'),html=readFileSync('app/static/supplier-portal-admin.html','utf8');
  assert.doesNotMatch(js,/\/decision|\/send-sms|\/send-email|\/withdraw|assignmentForm/);
  assert.doesNotMatch(html,/id="assignmentForm"|id="adminReview"/);
  assert.match(html,/\/warehouse-assistant#sent/);assert.match(html,/id="accountForm"/);assert.match(html,/id="cartableAccessPanel"/);
});
test('navigation keeps per-stage sort and does not reset a same-view refresh',()=>{
  const s=setup();s.run("sharedTableSorts.set($('#fulfillmentTable'),{key:'number',direction:'asc'});prepareFulfillmentNavigation('sent','fulfillment');state.activeView='fulfillment'");
  assert.equal(s.run("sharedTableSorts.get($('#fulfillmentTable'))"),undefined);
  s.run("sharedTableSorts.set($('#fulfillmentTable'),{key:'supplier',direction:'desc'});prepareFulfillmentNavigation('fulfillment','sent');state.activeView='sent'");
  assert.equal(s.run("sharedTableSorts.get($('#fulfillmentTable')).key"),'number');
  s.nodes['#fulfillmentSearch'].value='تازه';s.run("prepareFulfillmentNavigation('sent','sent')");
  assert.equal(s.nodes['#fulfillmentSearch'].value,'تازه');
});
test('review is primary only for a pending supplier response; receipt is primary in delivery',()=>{
  const s=setup();s.ctx.order={id:7,order_stage:'sent',supplier_portal:{id:5,workflow_status:'awaiting_negin'}};
  assert.match(s.run('fulfillmentActions(order)'),/class="primary"[^>]*data-supplier-review="5"/);
  s.ctx.order={id:7,order_stage:'delivery',fulfillment:{status:'awaiting_supply'}};
  assert.match(s.run('fulfillmentActions(order)'),/class="primary"[^>]*data-fulfillment-checkbar="7"/);
  assert.match(s.run('fulfillmentActions(order)'),/class="secondary-action"[^>]*data-fulfillment-finish="7"/);
});
