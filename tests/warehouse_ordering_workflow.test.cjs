const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const source=readFileSync('app/static/warehouse-assistant.js','utf8');
const html=readFileSync('app/static/warehouse-assistant.html','utf8');

test('calculate is the form submit action, with no duplicate click handler',()=>{
  assert.match(html,/<button id="calculateButton"[^>]+type="submit"[^>]+form="filterForm"/);
  assert.doesNotMatch(source,/#calculateButton"\)\.addEventListener\("click",calculate\)/);
});

test('inventory cycle selector displays manual exclusion and keeps it selected',()=>{
  const s=setup();s.run('state.bootstrap={inventory_cycle_override_supported:true,inventory_cycle_manual_exclusion_supported:true};expandableCellText=esc;demandAuditNote=()=>""');
  const rendered=s.run('inventoryRow({warehouse:"karaj",product_code:"00123",system_ordering_cycle_active:true,order_cycle_forced_inactive:true,ordering_cycle_active:false})');
  assert.match(rendered,/<option value="force_inactive" selected>خارج از چرخه دستی<\/option>/);
  assert.match(rendered,/<option value="system" >فعال \(سیستم\)<\/option>/);
  assert.match(rendered,/data-warehouse="karaj"/);
});

test('manual exclusion explains the old server and cannot be selected before its API is loaded',()=>{
  const s=setup();s.run('state.bootstrap={inventory_cycle_override_supported:true};expandableCellText=esc;demandAuditNote=()=>""');
  const rendered=s.run('inventoryRow({warehouse:"karaj",product_code:"00123",system_ordering_cycle_active:true})');
  assert.match(rendered,/<option value="force_inactive"[^>]*disabled>خارج از چرخه دستی · نیازمند به‌روزرسانی سرویس<\/option>/);
});

function setup(){
  const nodes={};
  for(const [id,value] of Object.entries({warehouseSelect:'karaj',manufacturerFilter:'',brandFilter:'',productSearch:'',reorderCoverageDays:'15',targetDays:'30',periodDays:'60'}))nodes['#'+id]={value};
  for(const id of ['calculateButton','createOrderButton','orderingStatus'])nodes['#'+id]={disabled:false,textContent:'',hidden:true};
  nodes['#onlyNeeded']={checked:true};
  nodes['#filterForm']={reportValidity:()=>true};
  const calls=[],messages=[],rendered=[];
  const context=vm.createContext({Intl,URLSearchParams,sessionStorage:{getItem(){}},document:{addEventListener(){},querySelector:s=>nodes[s],querySelectorAll:()=>[]},
    location:{hash:'#inventory'},history:{pushState(_a,_b,url){context.location.hash=url;calls.push(url)}},requestAnimationFrame(){},cancelAnimationFrame(){},
    capture:async()=>({orders:[{id:1}]}),message:(...args)=>messages.push(args),render:data=>rendered.push(data)});
  vm.runInContext(source,context);
  vm.runInContext('api=capture;toast=message;has=()=>true;renderSuggestions=data=>{state.suggestions=data;render(data)};loadOrders=async()=>{};selectPreparedOrderKind=()=>{}',context);
  return{context,nodes,calls,messages,rendered,run:code=>vm.runInContext(code,context)};
}
const response=warehouse=>({warehouse:{code:warehouse},snapshot:{id:1},items:[{product_code:'001',conversion_rate:12}]});
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return{promise,resolve,reject}}

test('calculation ignores a response for a warehouse changed while awaiting it',async()=>{
  const s=setup(),pending=deferred();s.context.capture=()=>pending.promise;s.run('api=capture');
  const work=s.run('calculate()');s.nodes['#warehouseSelect'].value='tehran';s.run('invalidateOrderingSuggestions()');
  pending.resolve(response('karaj'));await work;
  assert.equal(s.rendered.length,0);assert.equal(s.nodes['#createOrderButton'].disabled,true);
});

test('changing filters away and back still invalidates the in-flight calculation',async()=>{
  const s=setup(),pending=deferred();s.context.capture=()=>pending.promise;s.run('api=capture');
  const work=s.run('calculate()');s.nodes['#productSearch'].value='changed';s.run('invalidateOrderingSuggestions()');
  s.nodes['#productSearch'].value='';s.run('invalidateOrderingSuggestions()');pending.resolve(response('karaj'));await work;
  assert.equal(s.rendered.length,0);
});

test('only the newest calculation can render and end the busy state',async()=>{
  const s=setup(),first=deferred(),second=deferred();let count=0;
  s.context.capture=()=>++count===1?first.promise:second.promise;s.run('api=capture');
  const a=s.run('calculate()'),b=s.run('calculate()');first.resolve(response('karaj'));await a;
  assert.equal(s.rendered.length,0);assert.equal(s.nodes['#calculateButton'].disabled,true);
  second.resolve(response('karaj'));await b;assert.equal(s.rendered.length,1);assert.equal(s.nodes['#calculateButton'].disabled,false);
});

test('stale filters prevent POST even if a caller invokes prepare directly',async()=>{
  const s=setup();s.context.capture=async()=>response('karaj');s.run('api=capture');await s.run('calculate()');
  const writes=[];s.context.capture=async(...args)=>writes.push(args);s.run('api=capture;selectedLines=()=>[{product_code:"001",cartons:2,quantity:24}]');
  s.nodes['#warehouseSelect'].value='tehran';await s.run('createSupplierDocuments()');
  assert.equal(writes.length,0);assert.equal(s.nodes['#createOrderButton'].disabled,true);
});

test('failed recalculation cannot reuse the previous proposal',async()=>{
  const s=setup();s.context.capture=async()=>response('karaj');s.run('api=capture');await s.run('calculate()');
  s.context.capture=async()=>{throw Error('offline')};s.run('api=capture');await s.run('calculate()');
  const writes=[];s.context.capture=async(...args)=>writes.push(args);s.run('api=capture;selectedLines=()=>[{product_code:"001",cartons:2,quantity:24}]');
  await s.run('createSupplierDocuments()');assert.equal(writes.length,0);assert.equal(s.nodes['#createOrderButton'].disabled,true);
});

test('mismatched response warehouse is rejected before rendering',async()=>{
  const s=setup();s.context.capture=async()=>response('tehran');s.run('api=capture');await s.run('calculate()');
  assert.equal(s.rendered.length,0);assert.equal(s.nodes['#createOrderButton'].disabled,true);assert.equal(s.messages.length,1);
});

test('invalid form cannot start a request',async()=>{
  const s=setup();let count=0;s.nodes['#filterForm'].reportValidity=()=>false;
  s.context.capture=async()=>{count++};s.run('api=capture');await s.run('calculate()');assert.equal(count,0);
});

test('prepare captures proposal warehouse, blocks double click and consumes proposal on success',async()=>{
  const s=setup();s.context.capture=async()=>response('karaj');s.run('api=capture');await s.run('calculate()');
  const pending=deferred(),writes=[];s.context.capture=(path,opts)=>{writes.push({path,body:JSON.parse(opts.body)});return pending.promise};
  s.run('api=capture;switchView=()=>{};selectedLines=()=>[{product_code:"001",cartons:2,quantity:24}]');
  const work=s.run('createSupplierDocuments()'),duplicate=s.run('createSupplierDocuments()');
  s.nodes['#warehouseSelect'].value='tehran';pending.resolve({orders:[{id:1}]});await Promise.all([work,duplicate]);
  assert.equal(writes.length,1);assert.equal(writes[0].body.warehouse,'karaj');assert.equal(writes[0].body.snapshot_id,1);
  assert.equal(s.nodes['#createOrderButton'].disabled,true);assert.equal(s.run('state.orderingSubmitting'),false);
});

test('failed prepare can be retried when the proposal is still current',async()=>{
  const s=setup();s.context.capture=async()=>response('karaj');s.run('api=capture');await s.run('calculate()');
  s.context.capture=async()=>{throw Error('failed')};s.run('api=capture;selectedLines=()=>[{product_code:"001",cartons:2,quantity:24}]');
  await s.run('createSupplierDocuments()');assert.equal(s.nodes['#createOrderButton'].disabled,false);
});

test('catalog responses cannot replace the selected warehouse catalog out of order',async()=>{
  const s=setup(),first=deferred(),second=deferred();let count=0;
  s.context.capture=()=>++count===1?first.promise:second.promise;s.run('api=capture;renderOrderingBrands=()=>{}');
  const a=s.run('loadOrderingCatalog()');s.nodes['#warehouseSelect'].value='tehran';const b=s.run('loadOrderingCatalog()');
  second.resolve({manufacturers:[{name:'Tehran'}]});await b;first.resolve({manufacturers:[{name:'Karaj'}]});await a;
  assert.equal(s.run('state.orderingCatalog[0].name'),'Tehran');
});

test('navigation adds history once and restores sale pricing without replacing form values',()=>{
  const s=setup();for(const v of ['inventory','supply','ordering','automatic','preorders','fulfillment','checkbar','purchase','unbilled','salePrice'])s.nodes['#'+v+'View']={hidden:true};
  s.run('fitTableWrapsToViewport=()=>{};switchView("ordering");switchView("ordering");switchView("preorders")');
  assert.deepEqual(s.calls,['#ordering','#preorders/manual']);s.context.location.hash='#ordering';s.run('restoreWorkspaceView()');
  assert.equal(s.nodes['#orderingView'].hidden,false);assert.equal(s.nodes['#preordersView'].hidden,true);
  assert.equal(s.nodes['#targetDays'].value,'30');assert.equal(s.calls.length,2);
  s.context.location.hash='#sale-pricing';s.run('restoreWorkspaceView()');assert.equal(s.nodes['#salePriceView'].hidden,false);
});

test('inventory-to-ordering requires a single warehouse and never creates an order',async()=>{
  const s=setup(),calls=[];s.nodes['#inventoryWarehouseSelect']={value:''};
  s.context.capture=async path=>{calls.push(path);return{manufacturers:[]}};s.context.confirm=()=>true;
  s.run('api=capture;renderOrderingBrands=()=>{};switchView=()=>{};state.bootstrap={warehouses:[{code:"tehran",name:"انبار تهران"}]}');
  await s.run('orderFromInventory()');assert.equal(calls.length,0);assert.equal(s.nodes['#warehouseSelect'].value,'karaj');
  s.nodes['#inventoryWarehouseSelect'].value='انبار تهران';await s.run('orderFromInventory()');
  assert.equal(s.nodes['#warehouseSelect'].value,'tehran');assert.equal(s.nodes['#targetDays'].value,'30');
  assert.deepEqual(calls,['/warehouse-assistant/api/catalog?warehouse=tehran']);
});

test('declining warehouse switch preserves the existing ordering draft',async()=>{
  const s=setup();s.nodes['#inventoryWarehouseSelect']={value:'انبار تهران'};s.context.confirm=()=>false;
  s.run('state.bootstrap={warehouses:[{code:"tehran",name:"انبار تهران"}]};state.suggestions={items:[{product_code:"001"}]}');
  await s.run('orderFromInventory()');assert.equal(s.nodes['#warehouseSelect'].value,'karaj');assert.equal(s.run('state.suggestions.items[0].product_code'),'001');
});
