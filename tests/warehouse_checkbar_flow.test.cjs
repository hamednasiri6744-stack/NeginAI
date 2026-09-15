const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
function setup(){
  const nodes={};const ctx=vm.createContext({document:{addEventListener(){},querySelectorAll:()=>[]},window:{addEventListener(){}},
    $:key=>nodes[key]??=({value:'',hidden:false,disabled:false,textContent:'',dataset:{},open:true,showModal(){this.open=true},close(){this.open=false}}),
    checkbarState:{source:null,lines:[],saved:null,pending:null,submitting:false,sequence:1},orderMatchingState:{plan:null,loading:false},receiptBridge:{},
    checkbarImportPending:()=>false,matchingDraftSignature:()=> 'current',matchingAmounts:()=>[],matchingRemainders:()=>[],checkbarNotice(){}});
  vm.runInContext(readFileSync('app/static/warehouse-checkbar-flow.js','utf8'),ctx);
  return{ctx,nodes,run:code=>vm.runInContext(code,ctx)};
}
test('draft goes from counting to matching then save only after explicit confirmation',()=>{
  const s=setup();assert.equal(s.run('checkbarFlowModel().step'),1);
  s.run("checkbarState.source={};checkbarState.lines=[{cartons:'2'}]");
  assert.equal(s.run('checkbarFlowModel().target'),'checkbarMatchingPrepare');
  s.run("orderMatchingState.plan={};orderMatchingState.draftSignature='current'");
  assert.equal(s.run('checkbarFlowModel().step'),3);assert.equal(s.run('checkbarFlowModel().blocked'),true);
  s.run("$('#checkbarMatchingConfirmed').checked=true");
  assert.equal(s.run('checkbarFlowModel().target'),'checkbarIssue');assert.equal(s.run('checkbarFlowModel().blocked'),false);
  s.run("orderMatchingState.draftSignature='stale'");
  assert.equal(s.run('checkbarFlowModel().target'),'checkbarMatchingPrepare');
});

test('optional matching proceeds straight to counting save and returns to matching when enabled',()=>{
  const s=setup();s.ctx.checkbarSkipMatching=()=>true;
  s.run('checkbarState.source={};checkbarState.lines=[{cartons:2}]');
  assert.equal(s.run('checkbarFlowModel().target'),'checkbarIssue');
  assert.match(s.run('checkbarFlowModel().label'),/بدون تطبیق/);
  s.ctx.checkbarSkipMatching=()=>false;
  assert.equal(s.run('checkbarFlowModel().target'),'checkbarMatchingPrepare');
});
test('extra quantity needs its own acceptance; invalid allocation cannot enable save',()=>{
  const s=setup();s.run("checkbarState.source={};checkbarState.lines=[{}];orderMatchingState.plan={};orderMatchingState.draftSignature='current';$('#checkbarMatchingConfirmed').checked=true;matchingRemainders=()=>[{unallocated_qty:2}]");
  assert.equal(s.run('checkbarFlowModel().blocked'),true);
  s.run("$('#checkbarMatchingExtra').checked=true");assert.equal(s.run('checkbarFlowModel().blocked'),false);
  s.run('matchingRemainders=()=>[{unallocated_qty:-1}]');assert.equal(s.run('checkbarFlowModel().blocked'),true);
});
test('pending save remains the original retry action; never starts another document',()=>{
  const s=setup();s.run('checkbarState.pending={request_id:"same"}');
  assert.equal(s.run('checkbarFlowModel().target'),'checkbarIssue');
  assert.match(s.run('checkbarFlowModel().label'),/پیگیری/);
  s.run('checkbarState.submitting=true');assert.equal(s.run('checkbarFlowModel().blocked'),true);
});
test('saved receipt states select read/reconcile/transfer without bypassing existing controls',()=>{
  const s=setup();s.run('checkbarState.saved={id:1};receiptBridge.locked=true');
  assert.equal(s.run('checkbarFlowModel().target'),'checkbarReceiptRefresh');
  s.run('receiptBridge.pending=true');assert.equal(s.run('checkbarFlowModel().target'),'checkbarReceiptReconcile');
  s.run('receiptBridge.pending=false;receiptBridge.locked=false');assert.equal(s.run('checkbarFlowModel().target'),'checkbarTransfer');
  s.run('receiptBridge.completed=true');assert.equal(s.run('checkbarFlowModel().blocked'),true);
});
test('close preserves drafts unless discarded and refuses an unresolved write',()=>{
  const s=setup();s.run("checkbarState.lines=[{cartons:'2'}];requestCheckbarClose()");
  assert.equal(s.nodes['#checkbarExitDialog'].open,true);assert.equal(s.run('checkbarState.sequence'),1);
  s.run("resolveCheckbarExit(false)");assert.equal(s.run('checkbarState.lines[0].cartons'),'2');
  s.run('requestCheckbarClose();resolveCheckbarExit(true)');assert.equal(s.nodes['#checkbarDialog'].open,false);assert.equal(s.run('checkbarState.sequence'),2);
  s.run("$('#checkbarDialog').open=true;checkbarState.pending={};requestCheckbarClose()");assert.equal(s.nodes['#checkbarDialog'].open,true);
});
test('guided action respects disabled and hidden original capability controls',()=>{
  const s=setup();s.run('checkbarState.saved={id:1};receiptBridge.locked=true;renderCheckbarFlow()');
  assert.equal(s.nodes['#checkbarNextAction'].disabled,false);
  s.run("$('#checkbarReceiptRefresh').disabled=true;renderCheckbarFlow()");
  assert.equal(s.nodes['#checkbarNextAction'].disabled,true);
  s.run("$('#checkbarReceiptRefresh').disabled=false;$('#checkbarReceiptRefresh').hidden=true;renderCheckbarFlow()");
  assert.equal(s.nodes['#checkbarNextAction'].disabled,true);
});
