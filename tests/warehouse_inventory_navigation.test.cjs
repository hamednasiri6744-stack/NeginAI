const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const vm=require('node:vm');

function setup(loaded){
  const nodes=new Map();
  const document={addEventListener(){},querySelector:s=>{if(!nodes.has(s))nodes.set(s,{hidden:false});return nodes.get(s)},querySelectorAll:()=>[]};
  const context=vm.createContext({document,Intl,URLSearchParams,location:{hash:'#supply'},history:{pushState(){}},requestAnimationFrame(){},calls:[]});
  vm.runInContext(readFileSync('app/static/warehouse-assistant.js','utf8'),context);
  vm.runInContext(`state.bootstrap={latest_snapshot:{id:1},capabilities:['warehouse.inventory.view']};state.inventory.loaded=${loaded};state.inventory.items=Array.from({length:750},(_,i)=>({product_code:String(i)}));state.inventory.offset=750;fitTableWrapsToViewport=()=>{};loadInventory=async reset=>calls.push(reset);`,context);
  return context;
}
test('returning to loaded inventory preserves all fetched pages instead of resetting to first 250',()=>{
  const context=setup(true);
  vm.runInContext("switchView('supply');switchView('inventory');switchView('inventory')",context);
  assert.deepEqual(context.calls,[]);
  assert.equal(vm.runInContext('state.inventory.offset',context),750);
  assert.equal(vm.runInContext('state.inventory.items.length',context),750);
});
test('first inventory visit still requests data',()=>{
  const context=setup(false);
  vm.runInContext("switchView('inventory')",context);
  assert.deepEqual(context.calls,[true]);
});
