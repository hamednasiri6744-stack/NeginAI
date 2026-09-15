const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const source=readFileSync('app/static/supplier-portal.js','utf8').replace(/boot\(\);\s*$/,'');
function setup(){
  const nodes={};
  const node=()=>({value:'',textContent:'',innerHTML:'',disabled:false,attrs:{},classList:{toggle(){}},addEventListener(){},setAttribute(k,v){this.attrs[k]=v},querySelectorAll:()=>[]});
  for(const id of ['changePasswordButton','cancelPasswordChange','loginForm','passwordForm','logoutButton','orderStats','orderList','orderDetail','loginError','orderStageNav','orderSectionSummary','retryOrderDetail'])nodes['#'+id]=node();
  nodes['#orderStats'].after=()=>{for(const id of ['cartableFilters','cartableSupplierFilter','cartableWarehouseFilter','cartableRefresh','cartableFeedback'])nodes['#'+id]=node()};
  const context=vm.createContext({document:{querySelector:s=>nodes[s]||null,createElement:node},AbortController,setTimeout,clearTimeout});
  vm.runInContext(source,context);
  return {nodes,context,run:s=>vm.runInContext(s,context)};
}
test('loading feedback and retry are present before the response, then all authorized suppliers render',async()=>{
  const s=setup();let resolve;
  s.context.request=()=>new Promise(r=>{resolve=r});s.run('api=request');
  const pending=s.run('loadOrders()');
  assert.match(s.nodes['#cartableFeedback'].textContent,/در حال دریافت/);
  assert.equal(s.nodes['#cartableRefresh'].disabled,true);
  assert.equal(s.nodes['#orderList'].attrs['aria-busy'],'true');
  resolve({orders:[1,2,3].map(id=>({id,status:'awaiting_supplier',document:{number:`SUP-${id}`,supplier:`Supplier ${id}`,warehouse_name:'Karaj'},requested_delivery_date:'1405/06/22'}))});
  assert.equal(await pending,true);
  assert.match(s.nodes['#orderList'].innerHTML,/SUP-1/);assert.match(s.nodes['#orderList'].innerHTML,/SUP-3/);
  assert.equal(s.nodes['#cartableRefresh'].disabled,false);
  assert.equal(s.nodes['#orderList'].attrs['aria-busy'],'false');
});
test('supplier menu separates action, pending Negin approval, and approved orders',async()=>{
  const s=setup();s.context.request=async()=>({orders:['awaiting_supplier','draft','changes_requested','submitted','accepted','rejected'].map((status,id)=>({id:id+1,status,document:{number:`SUP-${id+1}`,supplier:'Supplier',warehouse_name:'Karaj'}}))});s.run('api=request');
  await s.run('loadOrders()');
  assert.match(s.nodes['#orderList'].innerHTML,/SUP-1/);assert.match(s.nodes['#orderList'].innerHTML,/SUP-3/);
  assert.doesNotMatch(s.nodes['#orderList'].innerHTML,/SUP-4|SUP-5|SUP-6/);
  s.run("selectOrderStage('negin')");assert.match(s.nodes['#orderList'].innerHTML,/SUP-4/);assert.doesNotMatch(s.nodes['#orderList'].innerHTML,/SUP-1|SUP-5/);
  s.run("selectOrderStage('approved')");assert.match(s.nodes['#orderList'].innerHTML,/SUP-5/);
  s.run("selectOrderStage('history')");assert.match(s.nodes['#orderList'].innerHTML,/SUP-6/);
});
test('status changes move an active order to its destination menu on refresh',async()=>{
  for(const [status,stage] of [['submitted','negin'],['accepted','approved'],['changes_requested','action']]){
    const s=setup();s.context.request=async()=>({orders:[{id:1,status,document:{number:'SUP-1',supplier:'Supplier',warehouse_name:'Karaj'}}]});
    s.run("api=request;active={id:1,status:'awaiting_supplier'};openOrder=async()=>{};");
    await s.run('loadOrders()');assert.equal(s.run('selectedOrderStage'),stage);
    assert.match(s.nodes['#orderList'].innerHTML,/SUP-1/);
  }
});
test('failed list stays visible and can recover without logging in again',async()=>{
  const s=setup();s.context.request=async()=>{throw new Error('offline')};s.run('api=request');
  assert.equal(await s.run('loadOrders()'),false);
  assert.match(s.nodes['#cartableFeedback'].textContent,/offline/);
  assert.equal(s.nodes['#cartableFeedback'].className,'error');
  assert.equal(s.nodes['#cartableRefresh'].disabled,false);
  s.context.request=async()=>({orders:[]});s.run('api=request');
  assert.equal(await s.nodes['#cartableRefresh'].onclick(),true);
  assert.match(s.nodes['#orderList'].innerHTML,/سفارشی در این محدوده/);
});
test('malformed successful responses are errors, not empty orders',async()=>{
  const s=setup();s.context.request=async()=>({});s.run('api=request');
  assert.equal(await s.run('loadOrders()'),false);
  assert.match(s.nodes['#cartableFeedback'].textContent,/معتبر نیست/);
});

function detailSetup(){
  const s=setup();s.run("orders=[1,2].map(id=>({id,status:'awaiting_supplier',document:{number:'SUP-'+id,supplier:'Supplier',warehouse_name:'Karaj'}}));renderOrder=o=>{$('#orderDetail').innerHTML='opened-'+o.id}");
  return s;
}
const detail=id=>({id,status:'awaiting_supplier',document:{number:'SUP-'+id},lines:[],comments:[]});

test('click immediately displays progress and selected order; repeated clicks make one request',async()=>{
  const s=detailSetup();let resolve,calls=0;
  s.context.request=()=>{calls++;return new Promise(r=>resolve=r)};s.run('api=request');
  const pending=s.run('openOrder(1)');
  assert.match(s.nodes['#orderDetail'].innerHTML,/در حال دریافت اقلام/);
  assert.equal(s.nodes['#orderDetail'].attrs['aria-busy'],'true');
  assert.match(s.nodes['#orderList'].innerHTML,/is-active[^>]+data-id="1"[^>]+disabled/);
  await s.run('openOrder(1)');assert.equal(calls,1);
  resolve(detail(1));await pending;
  assert.equal(s.nodes['#orderDetail'].innerHTML,'opened-1');
  assert.equal(s.nodes['#orderDetail'].attrs['aria-busy'],'false');
});

test('switching order aborts old request and ignores a late reply',async()=>{
  const s=detailSetup(),requests=[];
  s.context.request=(url,options)=>new Promise(resolve=>requests.push({resolve,signal:options.signal}));s.run('api=request');
  const first=s.run('openOrder(1)'),second=s.run('openOrder(2)');
  assert.equal(requests[0].signal.aborted,true);
  requests[1].resolve(detail(2));await second;
  requests[0].resolve(detail(1));await first;
  assert.equal(s.nodes['#orderDetail'].innerHTML,'opened-2');
});

test('switching section cancels detail without replacing the new section',async()=>{
  const s=detailSetup();let resolve,signal;
  s.context.request=(url,options)=>{signal=options.signal;return new Promise(r=>resolve=r)};s.run('api=request');
  const pending=s.run('openOrder(1)');s.run("selectOrderStage('approved')");
  const placeholder=s.nodes['#orderDetail'].innerHTML;
  assert.equal(signal.aborted,true);resolve(detail(1));await pending;
  assert.equal(s.nodes['#orderDetail'].innerHTML,placeholder);
  assert.equal(s.nodes['#orderDetail'].attrs['aria-busy'],'false');
});

test('timeout releases loading and retry opens the order',async()=>{
  const s=detailSetup();let timeout;
  s.context.setTimeout=callback=>{timeout=callback;return 1};s.context.clearTimeout=()=>{};
  s.context.request=(url,{signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(new Error('aborted'))));s.run('api=request');
  const pending=s.run('openOrder(1)');timeout();await pending;
  assert.match(s.nodes['#orderDetail'].innerHTML,/دریافت سفارش طول کشید/);
  assert.equal(s.nodes['#orderDetail'].attrs['aria-busy'],'false');
  s.context.request=async()=>detail(1);s.run('api=request');
  await s.nodes['#retryOrderDetail'].onclick();
  assert.equal(s.nodes['#orderDetail'].innerHTML,'opened-1');
});

test('malformed detail shows recoverable error instead of rendering a broken form',async()=>{
  const s=detailSetup();s.context.request=async()=>({});s.run('api=request');
  await s.run('openOrder(1)');
  assert.match(s.nodes['#orderDetail'].innerHTML,/پاسخ جزئیات سفارش معتبر نیست/);
  assert.equal(s.nodes['#orderDetail'].attrs['aria-busy'],'false');
});
