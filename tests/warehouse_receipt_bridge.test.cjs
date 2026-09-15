const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
function setup(){
  const nodes={},events={};
  const context=vm.createContext({document:{addEventListener:(event,fn)=>events[event]=fn},
    $:key=>nodes[key]??={value:'',innerHTML:'',hidden:false,disabled:false,textContent:'',focus(){},addEventListener(event,fn){this[event]=fn}},
    state:{},checkbarState:{submitting:false},has:()=>true,fa:String,confirm:()=>true,
    normalizeSearchText:String,esc:v=>String(v??'').replaceAll('<','&lt;').replaceAll('"','&quot;')});
  vm.runInContext(readFileSync('app/static/warehouse-receipt-bridge.js','utf8'),context);
  events.DOMContentLoaded();
  nodes['#checkbarReceiptReference'].value='1490';
  vm.runInContext("receiptBridge.doc={id:1,revision:0,number:'CB-000001',supplier:'supplier',warehouse_name:'warehouse'}",context);
  return {context,nodes,run:s=>vm.runInContext(s,context)};
}
const ready={status:'ready',commit_enabled:true,preview_token:'a'.repeat(64),
  result:{ValidationToken:'b'.repeat(64),AccYear:1405,SupplierRef:7,Message:'ready'},
  payload:{zero_rows:[2],lines:[{source_row:1,product_code:'<bad>',quantity:'15',item_comment:'180000-120000'}]}};

test('existing receipt stays locked after busy ends and shows ERP number',()=>{
  const {context,nodes,run}=setup();
  context.result={status:'sent',revision:0,result:{VocherNo:71},receipt:{state:'exists',number:72,locked:true}};
  run('receiptBridgeState(result);receiptBusy(false)');
  assert.equal(nodes['#checkbarEdit'].disabled,true);assert.equal(nodes['#checkbarDelete'].disabled,true);
  assert.match(nodes['#checkbarReceiptStatus'].textContent,/72/);
});

test('price workflow result shows every receipt and reservation number',()=>{
  const {context,nodes,run}=setup();
  context.result={status:'sent',revision:2,result:{VocherNo:71,PriceWorkflowVersion:2,DocumentsJson:JSON.stringify([
    {Role:'confirmed_receipt',VocherNo:71},{Role:'price_reserve',VocherNo:9},{Role:'unpriced_receipt',VocherNo:72}])}};
  run('receiptBridgeState(result)');
  for(const label of ['رسید تأییدشده: 71','رزرو بابت تغییر قیمت: 9','رسید فاقد قیمت، تأییدنشده: 72'])assert.ok(nodes['#checkbarReceiptStatus'].textContent.includes(label));
  assert.equal(nodes['#checkbarEdit'].disabled,true);
});

test('price routing is shown before submit and confirmation explains reservation',async()=>{
  const {context,nodes,run}=setup();let confirmation='';
  context.api=async()=>({...ready,payload:{...ready.payload,price_workflow_version:2,lines:[{...ready.payload.lines[0],price_mode:'changed'}]}});
  context.confirm=text=>{confirmation=text;return false};
  await run('previewCheckbarReceipt()');
  assert.match(nodes['#checkbarReceiptLines'].innerHTML,/رزرو تغییر قیمت/);
  await run('submitCheckbarReceipt()');assert.match(confirmation,/رزرو/);assert.match(confirmation,/فاقد قیمت/);
});

test('proven deletion unlocks editing and deletion and retains prior receipt number',()=>{
  const {context,nodes,run}=setup();
  context.result={status:'not_sent',receipt:{state:'deleted',number:71,locked:false},transfer_history:[{revision:0,result:{VocherNo:71}}]};
  run('receiptBridgeState(result);receiptBusy(false)');
  assert.equal(nodes['#checkbarEdit'].disabled,false);assert.equal(nodes['#checkbarDelete'].disabled,false);
  assert.equal(nodes['#checkbarTransfer'].hidden,false);assert.match(nodes['#checkbarReceiptHistory'].textContent,/71/);
});

test('unknown receipt cannot be edited, deleted or sent even through a stale button',async()=>{
  const {context,nodes,run}=setup();let calls=0;context.api=async()=>{calls++};
  context.result={status:'sent',revision:0,result:{VocherNo:71},receipt:{state:'unknown',number:71,locked:true}};
  run('receiptBridgeState(result);receiptBusy(false)');
  await run('advanceCheckbarReceipt();previewCheckbarReceipt()');
  assert.equal(calls,0);assert.equal(nodes['#checkbarDelete'].disabled,true);
  assert.equal(nodes['#checkbarReceiptRefresh'].hidden,false);
});

test('footer action opens then checks then submits with explicit confirmation',async()=>{
  const {context,nodes,run}=setup(),calls=[];
  context.$('#checkbarReceiptPanel').hidden=true;
  context.api=async(path,options)=>{calls.push({path,options});return path.endsWith('receipt-preview')?ready:{status:'sent',revision:0,result:{VocherNo:71}}};
  await nodes['#checkbarTransfer'].click();
  assert.equal(calls.length,0);assert.match(nodes['#checkbarTransfer'].textContent,/بررسی آمادگی/);
  await nodes['#checkbarTransfer'].click();
  assert.equal(calls.length,1);assert.match(calls[0].path,/receipt-preview$/);
  assert.match(nodes['#checkbarTransfer'].textContent,/تأیید و ارسال/);
  assert.match(nodes['#checkbarReceiptProgress'].textContent,/آمادهٔ ارسال/);
  context.confirm=()=>false;await nodes['#checkbarTransfer'].click();assert.equal(calls.length,1);
  context.confirm=()=>true;await nodes['#checkbarTransfer'].click();
  assert.equal(calls.length,2);assert.match(calls[1].path,/receipt-transfer$/);
  assert.match(nodes['#checkbarReceiptProgress'].textContent,/71/);
});

test('preview failure stays visible next to buttons and never exposes commit',async()=>{
  const {context,nodes,run}=setup();context.api=async()=>({status:'invalid',result:{Message:'کد کالا نامعتبر است'}});
  await run('previewCheckbarReceipt()');
  assert.equal(nodes['#checkbarReceiptProgress'].hidden,false);
  assert.match(nodes['#checkbarReceiptProgress'].textContent,/کد کالا/);
  assert.equal(run('receiptBridge.preview'),null);
  assert.match(nodes['#checkbarTransfer'].textContent,/بررسی/);
});

test('read-only successful preflight cannot turn footer action into a commit',async()=>{
  const {context,nodes,run}=setup(),paths=[];
  context.api=async path=>{paths.push(path);return {...ready,commit_enabled:false}};
  await run('previewCheckbarReceipt()');await nodes['#checkbarTransfer'].click();
  assert.ok(paths.every(path=>path.endsWith('receipt-preview')));
  assert.equal(run('receiptBridge.preview'),null);
  assert.equal(nodes['#checkbarReceiptSubmit'].hidden,true);
});

test('preview escapes identifiers, preserves consumer-producer format and warns about zero',async()=>{
  const {context,nodes,run}=setup();context.api=async()=>ready;
  await run('previewCheckbarReceipt()');
  assert.match(nodes['#checkbarReceiptLines'].innerHTML,/&lt;bad>/);
  assert.match(nodes['#checkbarReceiptLines'].innerHTML,/180000-120000/);
  assert.match(nodes['#checkbarReceiptStatus'].textContent,/صفر/);
  assert.equal(nodes['#checkbarReceiptSubmit'].hidden,false);
});

test('changing header invalidates preview and prevents submit',async()=>{
  const {context,nodes,run}=setup();let calls=0;context.api=async()=>{calls++;return ready};
  await run('previewCheckbarReceipt()');nodes['#checkbarReceiptDate'].input();
  await run('submitCheckbarReceipt()');assert.equal(calls,1);
  assert.equal(nodes['#checkbarReceiptSubmit'].hidden,true);
});

test('canceling final confirmation cannot send',async()=>{
  const {context,run}=setup();let calls=0;context.api=async()=>{calls++;return ready};context.confirm=()=>false;
  await run('previewCheckbarReceipt()');await run('submitCheckbarReceipt()');assert.equal(calls,1);
});

test('submit uses frozen preview then displays returned ERP number',async()=>{
  const {context,nodes,run}=setup();const calls=[];
  context.api=async(path,options)=>{calls.push({path,options});return calls.length===1?ready:{status:'sent',revision:0,result:{VocherNo:71}}};
  await run('previewCheckbarReceipt()');await run('submitCheckbarReceipt()');
  const sent=JSON.parse(calls[1].options.body);
  assert.equal(sent.reference_no,'1490');
  assert.equal(sent.preview_token,ready.preview_token);assert.equal(sent.validation_token,ready.result.ValidationToken);
  assert.match(nodes['#checkbarReceiptStatus'].textContent,/71/);
  assert.equal(nodes['#checkbarTransfer'].hidden,true);
});

test('missing supplier document number blocks preview before network',async()=>{
  const {context,nodes,run}=setup();let calls=0;context.api=async()=>{calls++;return ready};
  for(const value of ['', '0', '-1', 'INV-12', '1.5', '2147483648']){
    nodes['#checkbarReceiptReference'].value=value;
    await run('previewCheckbarReceipt()');
    assert.equal(nodes['#checkbarReceiptSubmit'].hidden,true);
    assert.match(nodes['#checkbarReceiptStatus'].textContent,/شماره.*عطف/);
  }
  assert.equal(calls,0);
});

test('changing supplier document number invalidates checked transfer',async()=>{
  const {context,nodes,run}=setup();let calls=0;context.api=async()=>{calls++;return ready};
  await run('previewCheckbarReceipt()');
  nodes['#checkbarReceiptReference'].value='1491';nodes['#checkbarReceiptReference'].input();
  await run('submitCheckbarReceipt()');assert.equal(calls,1);
});

test('uncertain response offers recovery without changed payload and blocks local edits',async()=>{
  const {context,nodes,run}=setup();context.api=async()=>ready;await run('previewCheckbarReceipt()');
  context.api=async()=>{throw new Error('offline')};await run('submitCheckbarReceipt()');
  assert.equal(nodes['#checkbarReceiptReconcile'].hidden,false);assert.equal(nodes['#checkbarEdit'].disabled,true);
  let request;context.api=async(path,options)=>{request={path,options};return {status:'sent',revision:0,result:{VocherNo:71}}};
  await run('submitCheckbarReceipt(true)');assert.match(request.path,/receipt-reconcile$/);
  assert.equal(request.options.body,undefined);
});

test('late saved-document status cannot contaminate another document',async()=>{
  const {context,nodes,run}=setup();let resolve;context.api=()=>new Promise(r=>resolve=r);
  const pending=run("refreshCheckbarReceipt({id:1,metadata:{},revision:0})");
  run('resetCheckbarReceipt()');resolve({status:'sent',revision:0,result:{VocherNo:71}});await pending;
  assert.equal(nodes['#checkbarReceiptPanel'].hidden,true);
  assert.equal(nodes['#checkbarReceiptStatus'].textContent,'');
});

test('read-only mode cannot present final submit',async()=>{
  const {context,nodes,run}=setup();context.api=async()=>({...ready,commit_enabled:false});
  await run('previewCheckbarReceipt()');assert.equal(nodes['#checkbarReceiptSubmit'].hidden,true);
});

test('fresh status failure does not offer a new transfer',async()=>{
  const {context,nodes,run}=setup();context.api=async()=>{throw new Error('offline')};
  await run("refreshCheckbarReceipt({id:1,metadata:{},revision:0})");
  assert.equal(nodes['#checkbarTransfer'].disabled,true);
});


test('transfer uses saved supplier reference and clears it for a legacy document',async()=>{
  const {context,nodes,run}=setup();context.api=async()=>({status:'not_sent'});
  await run("refreshCheckbarReceipt({id:1,metadata:{reference_no:'2222'},revision:0})");
  assert.equal(nodes['#checkbarReceiptReference'].value,'2222');
  assert.equal(run('receiptInput().reference_no'),'2222');
  await run("refreshCheckbarReceipt({id:2,metadata:{},revision:0})");
  assert.equal(nodes['#checkbarReceiptReference'].value,'');
});
