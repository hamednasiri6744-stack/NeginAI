const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const plan={version:1,revision:'a'.repeat(64),allocations:[{source_row:1,preorder_id:1,quantity:100},{source_row:1,preorder_id:2,quantity:20}],rows:[{source_row:1,product_code:'X',product_name:'<script>',actual_qty:120,unallocated_qty:0,orders:[{preorder_id:1,number:'old',remaining_qty:100},{preorder_id:2,number:'new',remaining_qty:100}]}],unallocated_qty:0};
function setup(){
 const nodes={},events=[],inputs=[{value:'100',dataset:{matchingRow:'1',matchingOrder:'1'}},{value:'20',dataset:{matchingRow:'1',matchingOrder:'2'}}];
 const $=key=>nodes[key]??={hidden:false,disabled:false,checked:false,value:'',innerHTML:'',textContent:'',focus(){},setAttribute(){},addEventListener(name,fn){this[name]=fn}};
 const ctx=vm.createContext({$,state:{},checkbarState:{},document:{addEventListener(name,fn){events.push(fn)},querySelectorAll(){return inputs}},
  has:()=>true,fa:String,confirm:()=>true,normalizeSearchText:String,esc:v=>String(v??'').replaceAll('<','&lt;').replaceAll('"','&quot;')});
 for(const file of ['warehouse-receipt-bridge.js','warehouse-order-matching.js'])vm.runInContext(readFileSync('app/static/'+file,'utf8'),ctx);
 events.forEach(fn=>fn());
 vm.runInContext("receiptBridge.doc={id:1,revision:0,number:'CB-1',supplier:'s',warehouse_name:'w'}",ctx);
 ctx.plan=structuredClone(plan);
 $('#checkbarReceiptReference').value='2222';
 return {ctx,nodes,inputs,run:s=>vm.runInContext(s,ctx)};
}
test('matching is explicitly confirmed before any ERP preview, with exact editable allocation',async()=>{
 const t=setup(),calls=[];t.ctx.api=async(path,options)=>{calls.push({path,options});return path.endsWith('order-matching')?plan:{status:'ready',commit_enabled:true,preview_token:'p',result:{ValidationToken:'v'},payload:{}}};
 await t.run('loadOrderMatching()');await t.run('previewCheckbarReceipt()');assert.equal(calls.length,1);
 t.nodes['#checkbarMatchingConfirmed'].checked=true;
 await t.run('previewCheckbarReceipt()');
 const request=JSON.parse(calls[1].options.body);
 assert.deepEqual(request.allocations,plan.allocations);assert.equal(request.matching_confirmed,true);
 assert.equal(request.allocation_revision,plan.revision);
});
test('manual split remains in base units and excess receipt needs its own acceptance',()=>{
 const t=setup();t.run('renderOrderMatching(plan);orderMatchingState.documentId=1');
 t.inputs[0].value='40';t.inputs[1].value='80';t.nodes['#checkbarMatchingConfirmed'].checked=true;
 assert.deepEqual(JSON.parse(t.run('JSON.stringify(orderMatchingRequest().allocations)')).map(a=>a.quantity),[40,80]);
 t.inputs[1].value='50';assert.throws(()=>t.run('orderMatchingRequest()'),/اضافه/);
 t.nodes['#checkbarMatchingExtra'].checked=true;assert.equal(t.run('orderMatchingRequest().accept_unallocated'),true);
 t.inputs[1].value='100';assert.throws(()=>t.run('orderMatchingRequest()'),/اصلاح/);
});
test('allocation edits invalidate both preview and quantity confirmation',()=>{
 const t=setup();t.run('renderOrderMatching(plan);receiptBridge.preview={frozen:true}');
 t.nodes['#checkbarMatchingConfirmed'].checked=true;t.nodes['#checkbarMatchingRows'].input();
 assert.equal(t.run('receiptBridge.preview'),null);assert.equal(t.nodes['#checkbarMatchingConfirmed'].checked,false);
 assert.equal(t.nodes['#checkbarReceiptSubmit'].hidden,true);
});
test('late proposal cannot cross a document reset',async()=>{
 const t=setup();let resolve;t.ctx.api=()=>new Promise(r=>resolve=r);
 const pending=t.run('loadOrderMatching()');t.run('resetCheckbarReceipt();receiptBridge.doc={id:2}');resolve(plan);await pending;
 assert.equal(t.run('orderMatchingState.plan'),null);
});
test('blank or excessive precision is rejected, zero and three decimals are preserved',()=>{
 const t=setup();for(const bad of ['','-1','1.0001','Infinity']){t.inputs[0].value=bad;assert.throws(()=>t.run('matchingAmounts()'))}
 t.inputs[0].value='0';t.inputs[1].value='0.125';assert.deepEqual(JSON.parse(t.run('JSON.stringify(matchingAmounts())')).map(a=>a.quantity),[0,.125]);
});
test('rendering escapes external product text and sent allocation remains locked after request ends',()=>{
 const t=setup();t.run('renderOrderMatching(plan)');assert.ok(t.nodes['#checkbarMatchingRows'].innerHTML.includes('&lt;script>'));
 assert.ok(!t.nodes['#checkbarMatchingRows'].innerHTML.includes('<script>'));
 t.run("receiptBridgeState({status:'sent',order_matching:plan,result:{VocherNo:71}});receiptBusy(false)");
 assert.ok(t.inputs.every(input=>input.disabled));assert.ok(t.nodes['#checkbarMatchingConfirmed'].disabled);
});
test('milliunit arithmetic does not invent tiny overages from decimal addition',()=>{
 const t=setup();t.ctx.decimalPlan={rows:[{source_row:1,actual_qty:.3}]};
 assert.equal(t.run('matchingRemainders(decimalPlan,[{source_row:1,quantity:.1},{source_row:1,quantity:.2}])[0].unallocated_qty'),0);
});

function draftSetup(){
 const t=setup(),metadata=[{dataset:{checkbarMeta:'reference_no'},value:'2222'}],calls=[];
 t.ctx.document.querySelectorAll=selector=>selector==='[data-checkbar-meta]'?metadata:selector==='[data-matching-row]'?t.inputs:[];
 Object.assign(t.ctx,{AbortController,setTimeout,clearTimeout,toast(){},checkbarRequestId:()=> 'draft-test',confirm:()=>true});
 vm.runInContext(readFileSync('app/static/warehouse-checkbar.js','utf8'),t.ctx);
 t.run("checkbarState.source={warehouse:'karaj',supplier:'s',order_ids:[],expected_token:'token'};checkbarState.lines=[{product_code:'X',preorder_id:null,conversion_rate:1,cartons:'0',units:'120',manufacturer_price_new:'',consumer_price_new:''}];checkbarState.requestId='draft-test';receiptBridge.doc=null;renderCheckbarLines=()=>{};renderCheckbarProducts=()=>{};refreshCheckbarVersions=()=>{};loadCheckbarPage=()=>{};showSavedCheckbar=doc=>{checkbarState.saved=doc}");
 t.ctx.$('#checkbarReference').value='2222';
 t.ctx.api=async(path,options)=>{calls.push({path,options});return path.endsWith('matching-preview')?plan:{document:{id:9,receipt_confirmed:true,order_matching:plan}}};
 return {...t,metadata,calls};
}

test('draft matching reviews all open orders before save; confirmed save consumes via checkbar API and never calls ERP',async()=>{
 const t=draftSetup();
 await t.run('issueCheckbar()');assert.equal(t.calls.length,0);
 await t.run('loadOrderMatching()');assert.equal(t.calls[0].path,'/warehouse-assistant/api/checkbars/matching-preview');
 const preview=JSON.parse(t.calls[0].options.body);assert.deepEqual(preview.order_ids,[]);assert.equal(preview.lines[0].preorder_id,null);
 await t.run('issueCheckbar()');assert.equal(t.calls.length,1);
 t.ctx.$('#checkbarMatchingConfirmed').checked=true;
 await t.run('issueCheckbar()');assert.equal(t.calls.length,2);
 assert.equal(t.calls[1].path,'/warehouse-assistant/api/checkbars');
 const saved=JSON.parse(t.calls[1].options.body);assert.equal(saved.confirm_receipt,true);assert.equal(saved.allocation_revision,plan.revision);assert.deepEqual(saved.allocations,plan.allocations);
});

test('confirmation cancellation performs no save; quantities or metadata changing invalidate draft matching',async()=>{
 const t=draftSetup();await t.run('loadOrderMatching()');t.ctx.$('#checkbarMatchingConfirmed').checked=true;t.ctx.confirm=()=>false;
 await t.run('issueCheckbar()');assert.equal(t.calls.length,1);
 t.run("checkbarState.lines[0].units='121';invalidateDraftOrderMatching()");
 assert.equal(t.run('orderMatchingState.plan'),null);assert.throws(()=>t.run('orderMatchingRequest(true)'),/ابتدا/);
 await t.run('loadOrderMatching()');t.metadata[0].value='3333';t.run('invalidateDraftOrderMatching()');assert.equal(t.run('orderMatchingState.plan'),null);
});

test('edit draft preview carries original identity; edit save carries revision and matching confirmation',async()=>{
 const t=draftSetup();t.run('checkbarState.editing={id:5,revision:2};delete checkbarState.source.expected_token');
 await t.run('loadOrderMatching()');const preview=JSON.parse(t.calls[0].options.body);assert.equal(preview.document_id,5);assert.equal(preview.expected_revision,2);
 t.ctx.$('#checkbarMatchingConfirmed').checked=true;await t.run('issueCheckbar()');
 assert.equal(t.calls[1].path,'/warehouse-assistant/api/checkbars/5');assert.equal(t.calls[1].options.method,'PUT');
 const payload=JSON.parse(t.calls[1].options.body);assert.equal(payload.expected_revision,2);assert.equal(payload.confirm_receipt,true);assert.equal(payload.warehouse,undefined);
});

test('late draft proposal is discarded after quantity edit',async()=>{
 const t=draftSetup();let resolve;t.ctx.api=()=>new Promise(r=>resolve=r);
 const pending=t.run('loadOrderMatching()');t.run("checkbarState.lines[0].units='121';invalidateDraftOrderMatching()");resolve(plan);await pending;
 assert.equal(t.run('orderMatchingState.plan'),null);
});

test('confirmed saved checkbar sends ERP header only and leaves frozen allocation read-only',async()=>{
 const t=setup(),calls=[];t.run('receiptBridge.doc.receipt_confirmed=true;receiptBridge.doc.order_matching=plan');
 t.ctx.api=async(path,options)=>{calls.push({path,options});return {status:'ready',commit_enabled:true,preview_token:'p',result:{ValidationToken:'v'},payload:{}}};
 await t.run('loadOrderMatching()');assert.equal(calls.length,0);await t.run('previewCheckbarReceipt()');
 const request=JSON.parse(calls[0].options.body);assert.equal(request.allocations,undefined);assert.equal(request.allocation_revision,undefined);
 t.run('receiptBusy(false)');assert.ok(t.inputs.every(input=>input.disabled));assert.equal(t.nodes['#checkbarMatchingRemainingHeading'].textContent,'مانده پیش از این دریافت');
});
