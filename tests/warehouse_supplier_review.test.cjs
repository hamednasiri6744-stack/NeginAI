const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
test('warehouse sent-order action reviews in the warehouse instead of navigating to admin cartable',()=>{
  const ctx=vm.createContext({document:{addEventListener(){}},esc:String});
  vm.runInContext(readFileSync('app/static/warehouse-fulfillment.js','utf8'),ctx);
  ctx.order={id:2,order_stage:'sent',supplier_portal:{id:9,workflow_status:'awaiting_negin'}};
  const html=vm.runInContext('fulfillmentActions(order)',ctx);
  assert.match(html,/data-supplier-review="9"/);
  assert.doesNotMatch(html,/supplier-portal-admin/);
});
function setup(){
  const nodes={};
  const ctx=vm.createContext({document:{addEventListener(){},querySelectorAll:()=>[],createElement:()=>({})},
    $:id=>nodes[id]??=({textContent:'',innerHTML:'',value:'',checked:false,hidden:false,append(){}}),
    esc:v=>String(v??'').replaceAll('<','&lt;'),fa:String});
  vm.runInContext(readFileSync('app/static/warehouse-supplier-review.js','utf8'),ctx);
  ctx.order={id:9,revision:7,status:'submitted',requested_delivery_date:'1405/06/25',delivery_date:'1405/06/25',proposed_delivery_date:'1405/06/27',supplier_comment:'<script>',document:{number:'SUP-9',supplier:'fixture',warehouse_name:'karaj'},lines:[{product_code:'001',product_name:'کالا',conversion_rate:12,original_cartons:2,proposed_cartons:3}]};
  const calls=[];ctx.capture=async(url,options)=>{calls.push([url,JSON.parse(options.body)]);return {...ctx.order,status:'accepted'}};
  vm.runInContext('api=capture;toast=()=>{};loadFulfillmentOrders=async()=>{};loadOrders=async()=>{};loadAutomaticPreorders=async()=>{};renderSupplierReview(order)',ctx);
  nodes['#supplierReviewDialog']={open:true,close(){this.open=false}};
  return{ctx,nodes,calls,run:s=>vm.runInContext(s,ctx)};
}
test('review shows original and proposed date, cartons, units, delta, and escapes supplier text',()=>{
  const s=setup(),html=s.nodes['#supplierReviewContent'].innerHTML;
  assert.match(html,/1405\/06\/25/);assert.match(html,/1405\/06\/27/);
  assert.match(html,/<td>24<\/td><td>36<\/td>/);assert.match(html,/افزایش 1/);
  assert.match(html,/منتظر تأیید شما/);assert.doesNotMatch(html,/<script>/);
});
test('review shows changed lines only and no goods table for date-only proposals',()=>{
  const s=setup();s.ctx.order.lines.push({product_code:'UNCHANGED',product_name:'بدون تغییر',conversion_rate:12,original_cartons:1,proposed_cartons:1});
  let html=s.run('supplierReviewContent(order)');assert.doesNotMatch(html,/UNCHANGED/);
  s.ctx.order.lines[0].proposed_cartons=2;
  html=s.run('supplierReviewContent(order)');assert.doesNotMatch(html,/<table/);assert.match(html,/1405\/06\/27/);
  s.ctx.order.lines[0].proposed_cartons=3;s.ctx.order.proposed_delivery_date=s.ctx.order.requested_delivery_date;
  html=s.run('supplierReviewContent(order)');assert.doesNotMatch(html,/supplier-review-dates/);assert.match(html,/افزایش 1/);
});
test('accept requires explicit confirmation then uses exact reviewed revision',async()=>{
  const s=setup();await s.run("decideSupplierReview('accept')");assert.equal(s.calls.length,0);
  s.nodes['#supplierReviewConfirm'].checked=true;
  await s.run("decideSupplierReview('accept')");
  assert.equal(s.calls[0][0],'/warehouse-assistant/api/supplier-portal/orders/9/decision');
  assert.equal(s.calls[0][1].expected_revision,7);assert.equal(s.nodes['#supplierReviewDecision'].hidden,true);
  assert.equal(s.nodes['#supplierReviewDialog'].open,false);
  await s.run("decideSupplierReview('accept')");assert.equal(s.calls.length,1);
});

test('failed decision keeps review open; successful decision closes even if refresh fails',async()=>{
  const s=setup();s.nodes['#supplierReviewConfirm'].checked=true;
  s.run("api=async()=>{throw Error('registration failed')}");
  await s.run("decideSupplierReview('accept')");
  assert.equal(s.nodes['#supplierReviewDialog'].open,true);
  assert.match(s.nodes['#supplierReviewError'].textContent,/registration failed/);
  s.run("api=capture;renderSupplierReview(order);loadFulfillmentOrders=async()=>{throw Error('refresh failed')};toast=(message)=>globalThis.lastToast=message");
  s.nodes['#supplierReviewConfirm'].checked=true;
  await s.run("decideSupplierReview('accept')");
  assert.equal(s.nodes['#supplierReviewDialog'].open,false);
  assert.match(s.ctx.lastToast,/تصمیم ثبت شد/);
  assert.equal(s.calls.length,1);
});
test('return for correction needs a reason and never applies acceptance',async()=>{
  const s=setup();await s.run("decideSupplierReview('changes_requested')");assert.equal(s.calls.length,0);
  s.nodes['#supplierReviewComment'].value='تاریخ قابل قبول نیست';
  await s.run("decideSupplierReview('changes_requested')");
  assert.equal(s.calls[0][1].decision,'changes_requested');
  assert.equal(s.calls[0][1].manager_comment,'تاریخ قابل قبول نیست');
});
