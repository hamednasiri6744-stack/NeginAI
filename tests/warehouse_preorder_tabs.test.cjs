const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const source=readFileSync('app/static/warehouse-assistant.js','utf8');
function setup(){
  const nodes={},changes=[];
  const node=id=>nodes[id]??={hidden:false,textContent:'',value:'',dataset:{},setAttribute(k,v){this[k]=v},focus(){this.focused=true}};
  const tabs=['manual','system'].map(kind=>Object.assign(node(kind),{dataset:{preparedKind:kind}}));
  const context=vm.createContext({Intl,location:{hash:'#inventory'},history:{pushState(a,b,url){context.location.hash=url;changes.push(url)}},
    document:{addEventListener(){},querySelector(selector){if(selector.startsWith('[data-prepared-kind='))return tabs.find(t=>selector.includes(t.dataset.preparedKind));return node(selector)},querySelectorAll(selector){return selector==='[data-prepared-kind]'?tabs:[]}},requestAnimationFrame(){}});
  vm.runInContext(source,context);vm.runInContext('fitTableWrapsToViewport=()=>{}',context);
  return {nodes,tabs,changes,context,run:s=>vm.runInContext(s,context)};
}
test('manual and system tabs switch panels, deep links, and selected keyboard target',()=>{
  const s=setup();s.run("selectPreparedOrderKind('system')");
  assert.equal(s.context.location.hash,'#preorders/system');
  assert.equal(s.nodes['#manualPreparedPanel'].hidden,true);assert.equal(s.nodes['#systemPreparedPanel'].hidden,false);
  assert.equal(s.tabs[1]['aria-selected'],'true');assert.equal(s.tabs[0].tabIndex,-1);
  s.context.location.hash='#preorders/manual';s.run('restoreWorkspaceView()');
  assert.equal(s.nodes['#manualPreparedPanel'].hidden,false);assert.equal(s.nodes['#systemPreparedPanel'].hidden,true);
  assert.equal(s.changes.length,1);
  s.run("preparedOrderTabKey({key:'End',preventDefault(){}})");assert.equal(s.tabs[1].focused,true);
  s.run("preparedOrderTabKey({key:'Home',preventDefault(){}})");assert.equal(s.tabs[0].focused,true);
});
test('counts combine only active unsent manual and system orders',()=>{
  const s=setup();s.run("state.manualPreorders=[{order_stage:'draft'},{deleted:true},{order_stage:'sent'}];state.automaticPreorders=[{order_stage:'draft'},{order_stage:'delivery'}];updatePreparedOrderCounts()");
  assert.equal(s.nodes['#preorderMenuBadge'].textContent,'۲');
  assert.equal(s.nodes['#manualPreparedCount'].textContent,'۱');assert.equal(s.nodes['#systemPreparedCount'].textContent,'۱');
});
test('legacy preorder link opens manual tab and ordering only shows the creation form',()=>{
  const s=setup();s.context.location.hash='#preorders';s.run('restoreWorkspaceView()');
  assert.equal(s.run('state.preparedOrderKind'),'manual');
  s.run("switchView('ordering')");assert.equal(s.nodes['#orderingView'].hidden,false);assert.equal(s.nodes['#preordersView'].hidden,true);
  assert.match(source,/await loadOrders\(\);selectPreparedOrderKind\('manual'\)/);
  assert.doesNotMatch(source,/selected==='ordering'.*loadOrders\(\)/);
});
test('cancelling approval sends no write request for either kind',async()=>{
  const s=setup();const calls=[];
  s.context.confirm=()=>false;s.context.window={confirm:()=>false};
  s.context.capture=async(path,options)=>{calls.push({path,options});return {id:3}};
  s.context.button={dataset:{preorderId:'3',preorderAction:'approve',manualId:'3',manualAction:'approve'}};
  s.run('api=capture;state.automaticPreorders=[{id:3}]');
  await s.run('automaticPreorderAction(button)');await s.run('manualOrderAction(button)');
  assert.ok(calls.every(call=>!call.options?.method));
  assert.equal(s.context.button.disabled,false);
});
