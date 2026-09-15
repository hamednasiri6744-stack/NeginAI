const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');

function setup(){
  const callbacks=[],events={},nodes={};
  const grid=(top,footer=0,visible=true)=>{
    const values=new Map();
    return {dataset:{},style:{getPropertyValue:key=>values.get(key)||'',setProperty:(key,value)=>values.set(key,value)},
      getClientRects:()=>visible?[{}]:[],getBoundingClientRect:()=>({top}),
      closest:selector=>selector==='dialog'?null:{querySelector:()=>({getClientRects:()=>[{}],getBoundingClientRect:()=>({height:footer})})}};
  };
  const inventory=grid(180,30),nestedTransfer=grid(270),receipts=grid(230,40),hiddenPane=grid(0,0,false);
  const grids=[inventory,nestedTransfer,receipts,hiddenPane];
  const content={querySelectorAll:selector=>selector==='.operation-table'?grids:[],addEventListener:(name,fn)=>events[name]=fn};
  const context=vm.createContext({
    document:{querySelector:()=>content,getElementById:id=>nodes[id],addEventListener(){}},
    window:{innerHeight:720,addEventListener:(name,fn)=>events[name]=fn},
    requestAnimationFrame:fn=>{callbacks.push(fn);return callbacks.length},
    ResizeObserver:class{observe(){}},MutationObserver:class{observe(){}},
  });
  vm.runInContext(readFileSync('app/static/warehouse-pages.js','utf8'),context);
  vm.runInContext('initializeWarehousePages()',context);
  const flush=()=>{for(const fn of callbacks.splice(0))fn()};
  return {context,events,nodes,grids,callbacks,flush};
}
test('each visible main grid fills only the space above its own footer, including nested tabs',()=>{
  const h=setup();h.flush();
  assert.equal(h.grids[0].style.getPropertyValue('--page-table-height'),'500px');
  assert.equal(h.grids[1].style.getPropertyValue('--page-table-height'),'440px');
  assert.equal(h.grids[2].style.getPropertyValue('--page-table-height'),'440px');
  assert.equal(h.grids[3].style.getPropertyValue('--page-table-height'),'');
  assert.equal(h.grids[3].dataset.pageGrid,undefined);
  h.context.window.innerHeight=900;h.events.resize();h.events.resize();
  assert.equal(h.callbacks.length,1);h.flush();
  assert.equal(h.grids[2].style.getPropertyValue('--page-table-height'),'620px');
});
test('collapsing calculation conditions retains and exposes current values in the summary',()=>{
  const h=setup();
  h.nodes.orderingConditionsSummary={textContent:''};
  for(const [id,value] of Object.entries({reorderCoverageDays:'15',targetDays:'30',periodDays:'60',orderingDeliveryDate:'1405/06/25'}))h.nodes[id]={value};
  h.nodes.onlyNeeded={checked:false};h.flush();
  assert.match(h.nodes.orderingConditionsSummary.textContent,/15.*30.*60.*همه اقلام.*1405\/06\/25/);
  h.nodes.targetDays.value='45';h.events.input();h.flush();
  assert.match(h.nodes.orderingConditionsSummary.textContent,/هدف 45 روز/);
  assert.equal(h.nodes.orderingDeliveryDate.value,'1405/06/25');
});
test('native validation reveals a collapsed invalid calculation field',()=>{
  const h=setup(),details={open:false};
  h.events.invalid({target:{closest:()=>details}});
  assert.equal(details.open,true);
});
test('table tools follow a hidden tab without hiding the active tab tools',()=>{
  const h=setup();
  const tools=()=>({hidden:false,classList:{contains:name=>name==='operation-tools'}});
  h.grids[0].hidden=false;h.grids[0].previousElementSibling=tools();
  h.grids[3].hidden=true;h.grids[3].previousElementSibling=tools();h.flush();
  assert.equal(h.grids[0].previousElementSibling.hidden,false);
  assert.equal(h.grids[3].previousElementSibling.hidden,true);
  h.grids[3].hidden=false;h.events.change();h.flush();
  assert.equal(h.grids[3].previousElementSibling.hidden,false);
});
