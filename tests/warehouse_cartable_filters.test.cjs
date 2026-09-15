const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
function context(){
  const ctx=vm.createContext({document:{addEventListener(){}}});
  vm.runInContext(readFileSync('app/static/warehouse-fulfillment.js','utf8'),ctx);
  return ctx;
}
test('cartable filters describe published-order steps, not preparation or receipt steps',()=>{
  const ctx=context();
  assert.deepEqual(Array.from(vm.runInContext("fulfillmentFilterKeys('sent')",ctx)),['all','unviewed','awaiting_supplier','changes_requested','awaiting_negin']);
  assert.deepEqual(Array.from(vm.runInContext("fulfillmentFilterKeys('delivery')",ctx)),['all','supplier_confirmed','awaiting_delivery']);
});
test('first view, draft reply, correction and Negin decision get distinct cartable filters',()=>{
  const ctx=context();
  for(const [status,viewed,expected] of [['awaiting_supplier',null,'unviewed'],['awaiting_supplier','now','awaiting_supplier'],['draft','now','awaiting_supplier'],['changes_requested','now','changes_requested'],['awaiting_negin','now','awaiting_negin']]){
    ctx.order={supplier_portal:{workflow_status:status,publication_state:'published',first_viewed_at:viewed}};
    assert.equal(vm.runInContext(`fulfillmentMatchesWorkflow(order,'${expected}')`,ctx),true);
    const matches=vm.runInContext("fulfillmentFilterKeys('sent').filter(key=>key!=='all'&&fulfillmentMatchesWorkflow(order,key))",ctx);
    assert.deepEqual(Array.from(matches),[expected]);
  }
});
