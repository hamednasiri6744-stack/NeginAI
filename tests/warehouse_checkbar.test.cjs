const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
function setup(){
  const nodes={};
  const context=vm.createContext({document:{addEventListener(){},querySelectorAll(){return []}},
    $:key=>nodes[key]??={value:'',innerHTML:'',textContent:'',hidden:false,setAttribute(k,v){this[k]=v},focus(){this.focused=true}},
    normalizeSearchText:v=>String(v??'').replace(/[۰-۹]/g,c=>c.charCodeAt(0)-1776).replace(/[٠-٩]/g,c=>c.charCodeAt(0)-1632).toLowerCase().trim(),
    esc:v=>String(v??'').replaceAll('<','&lt;').replaceAll('"','&quot;'),fa:String,
    receiptQuantityLabel:(n)=>String(n),toast(){},confirm:()=>true,orderMatchingRequest:()=>({allocations:[],allocation_revision:'a'.repeat(64),accept_unallocated:true}),encodeURIComponent,AbortController,setTimeout,clearTimeout,
  });
  vm.runInContext(readFileSync('app/static/warehouse-checkbar.js','utf8'),context);
  return {context,nodes};
}

test('archive shows a dedicated receipt status even without a receipt number',()=>{
  const {context:c,nodes}=setup();c.formatRefreshDate=String;
  for(const [status,label] of [['not_sent','آماده ثبت'],['pending','در انتظار نتیجه'],['sent','ثبت‌شده'],['unknown','نیازمند بررسی']]){
    c.status=status;
    vm.runInContext("checkbarArchive=[{id:8,number:'CB-000008',receipt_state:status}];renderCheckbarArchive()",c);
    assert.match(nodes['#checkbarHistoryRows'].innerHTML,new RegExp(`data-checkbar-status="[^"]+">${label}`));
  }
});

test('archive filters warehouse and status together and keeps filters during receipt refresh',()=>{
  const {context:c,nodes}=setup();c.formatRefreshDate=String;
  c.$('#checkbarArchiveWarehouse').value='تهران';c.$('#checkbarArchiveState').value='pending';
  vm.runInContext("checkbarArchive=[{id:1,number:'CB-1',warehouse_name:'تهران',receipt_state:'pending'},{id:2,number:'CB-2',warehouse_name:'کرج',receipt_state:'pending'},{id:3,number:'CB-3',warehouse_name:'تهران',receipt_state:'sent'}];renderCheckbarArchive()",c);
  assert.match(nodes['#checkbarHistoryRows'].innerHTML,/CB-1/);
  assert.doesNotMatch(nodes['#checkbarHistoryRows'].innerHTML,/CB-2|CB-3/);
  vm.runInContext("updateCheckbarArchiveReceipt(1,{status:'sent',receipt:{state:'exists',number:71}})",c);
  assert.equal(nodes['#checkbarArchiveWarehouse'].value,'تهران');assert.equal(nodes['#checkbarArchiveState'].value,'pending');
  assert.match(nodes['#checkbarHistoryRows'].innerHTML,/فیلتر/);
});

test('archive has one contextual primary and keeps destructive controls in disclosure',()=>{
  const {context:c}=setup();
  for(const [status,label] of [['not_sent','آماده‌سازی رسید'],['pending','پیگیری نتیجه'],['sent','مشاهده سند'],['unknown','بررسی وضعیت']]){
    c.status=status;const html=vm.runInContext("checkbarArchiveActions({id:8,receipt_state:status})",c);
    assert.equal((html.match(/data-workflow-primary="true"/g)||[]).length,1);
    assert.match(html,/href="\/warehouse-assistant\/api\/checkbars\/8\/print" target="_blank" rel="noopener">چاپ<\/a>/);
    assert.match(html,new RegExp(`>${label}</button>`));
    assert.match(html,/<details[\s\S]*data-checkbar-action="delete"[\s\S]*<\/details>/);
  }
  const deleted=vm.runInContext('checkbarArchiveActions({id:8,deleted:true})',c);
  assert.doesNotMatch(deleted,/data-checkbar-action|document.xlsx/);
});

test('archive exposes edit delete and receipt actions and locks transferred or uncertain documents',()=>{
  const {context:c,nodes}=setup();c.formatRefreshDate=String;
  for(const status of ['not_sent','deleted','sent','pending','unknown','review']){
    c.status=status;
    vm.runInContext("checkbarArchive=[{id:8,number:'CB-000008',receipt_state:status}];renderCheckbarArchive()",c);
    const html=nodes['#checkbarHistoryRows'].innerHTML;
    for(const action of ['edit','delete','receipt'])assert.match(html,new RegExp(`data-checkbar-action="${action}"`));
    const edit=html.match(/<button[^>]*data-checkbar-action="edit"[^>]*>/)[0];
    const del=html.match(/<button[^>]*data-checkbar-action="delete"[^>]*>/)[0];
    assert.equal(edit.includes('disabled'),!['not_sent','deleted'].includes(status));
    assert.equal(del.includes('disabled'),!['not_sent','deleted'].includes(status));
  }
});

test('archive shortcut waits for receipt verification and ignores a closed or replaced document',async()=>{
  const {context:c}=setup();let resolve,edits=0,deletes=0;
  c.openCheckbarHistory=async id=>{vm.runInContext(`checkbarState.saved={id:${id}}`,c);return new Promise(r=>resolve=r)};
  c.receiptBridge={locked:true};c.editSavedCheckbar=async()=>edits++;c.deleteSavedCheckbar=async()=>deletes++;
  const pending=vm.runInContext("openCheckbarArchiveAction(8,'edit')",c);
  assert.equal(edits,0);c.receiptBridge.locked=false;resolve(true);await pending;assert.equal(edits,1);
  c.receiptBridge.locked=true;
  const locked=vm.runInContext("openCheckbarArchiveAction(8,'delete')",c);resolve(true);await locked;assert.equal(deletes,0);
  c.receiptBridge.locked=false;
  const closed=vm.runInContext("openCheckbarArchiveAction(8,'delete')",c);resolve(false);await closed;assert.equal(deletes,0);
});

test('receipt verification updates only the matching archive row and proven deletion unlocks it',()=>{
  const {context:c,nodes}=setup();c.formatRefreshDate=String;
  vm.runInContext("checkbarArchive=[{id:8,receipt_state:'sent'},{id:9,receipt_state:'sent'}];updateCheckbarArchiveReceipt(8,{status:'not_sent',receipt:{state:'deleted',number:71,locked:false}})",c);
  assert.equal(vm.runInContext('checkbarArchive[0].receipt_state',c),'deleted');
  assert.equal(vm.runInContext('checkbarArchive[1].receipt_state',c),'sent');
  assert.equal(vm.runInContext('checkbarArchive[0].receipt_number',c),71);
  assert.match(nodes['#checkbarHistoryRows'].innerHTML,/سند ورانگر 71 · حذف‌شده/);
});

test('opening history resolves only after receipt state arrives and rejects stale dialogs',async()=>{
  const {context:c}=setup();let resolve;
  c.checkbarClear=()=>vm.runInContext('checkbarState.sequence++',c);
  c.$('#checkbarDialog').showModal=()=>{};c.checkbarNotice=()=>{};c.renderCheckbarVersions=()=>{};
  c.api=async()=>({document:{id:8},versions:[]});
  c.showSavedCheckbar=doc=>{vm.runInContext('checkbarState.saved={id:8}',c);return new Promise(r=>resolve=r)};
  const pending=vm.runInContext('openCheckbarHistory(8)',c);
  await new Promise(r=>setImmediate(r));
  vm.runInContext('checkbarState.sequence++',c);resolve();assert.equal(await pending,false);
  const current=vm.runInContext('openCheckbarHistory(8)',c);
  await new Promise(r=>setImmediate(r));resolve();assert.equal(await current,true);
});

test('switching checkbar views preserves quantity inputs, zero, blank and draft state',()=>{
  const {context:c}=setup();
  const cells=Array.from({length:19},()=>({hidden:false}));
  const zero={value:'0'},blank={value:''};cells[10].input=zero;cells[9].input=blank;
  const table=c.$('#checkbarTable');table.dataset={};table.querySelectorAll=()=>[{children:cells}];
  c.fitFixedTableColumns=()=>{};
  vm.runInContext("checkbarState.lines=[{units:'0',cartons:'',conversion_rate:12}]",c);
  for(const view of ['prices','all','count']){
    vm.runInContext(`applyCheckbarTableView('${view}')`,c);
    assert.equal(cells[10].input,zero);assert.equal(cells[9].input,blank);
    assert.equal(zero.value,'0');assert.equal(blank.value,'');
    assert.equal(vm.runInContext('checkbarActual(checkbarState.lines[0])',c),0);
  }
  assert.equal(cells[9].hidden,false);assert.equal(cells[10].hidden,false);
});

test('hidden active checkbar filter remains intact and is disclosed to the user',()=>{
  const {context:c}=setup();
  const cells=Array.from({length:19},()=>({hidden:false}));
  const filter={value:'شوینده'};
  const table=c.$('#checkbarTable');table.dataset={};table.querySelectorAll=()=>[{children:cells}];
  c.fitFixedTableColumns=()=>{};
  c.document.querySelectorAll=selector=>selector.includes('th[hidden]')&&cells[18].hidden?[filter]:[];
  vm.runInContext("applyCheckbarTableView('count')",c);
  assert.equal(c.$('#checkbarHiddenFilters').hidden,false);
  vm.runInContext("applyCheckbarTableView('all')",c);
  assert.equal(c.$('#checkbarHiddenFilters').hidden,true);
  assert.equal(filter.value,'شوینده');
});

test('brand split is opt-in, previews real row groups and preserves the retry request',async()=>{
  const {context:c,nodes}=issueSetup();const sent=[];
  vm.runInContext("checkbarState.lines=[{product_code:'A',brand:'Alpha',units:'5',conversion_rate:1},{product_code:'B',brand:'Beta',units:'0',conversion_rate:1},{product_code:'C',brand:'Alpha',units:'7',conversion_rate:1}]",c);
  assert.equal(vm.runInContext('checkbarIssuePayload().split_by_brand',c),undefined);
  c.$('#checkbarSplitByBrand').checked=true;
  vm.runInContext('renderCheckbarBrandSplit()',c);
  assert.match(nodes['#checkbarBrandSplitSummary'].textContent,/2.*Alpha.*2.*Beta.*1/);
  let message;c.confirm=text=>{message=text;return true};
  c.api=async(url,options)=>{sent.push(options.body);throw new TypeError('offline')};
  await vm.runInContext('issueCheckbar()',c);
  assert.match(message,/2.*Alpha.*Beta/);
  assert.equal(JSON.parse(sent[0]).split_by_brand,true);
  assert.equal(JSON.parse(sent[0]).lines[1].units,0);
  assert.equal(nodes['#checkbarSplitByBrand'].disabled,true);
  await vm.runInContext('issueCheckbar()',c);
  assert.equal(sent[0],sent[1]);
});

test('unknown brand and canceled batch confirmation cannot submit',async()=>{
  const {context:c,nodes}=issueSetup();let calls=0;
  c.$('#checkbarSplitByBrand').checked=true;c.api=async()=>{calls++};
  await vm.runInContext('issueCheckbar()',c);
  assert.equal(calls,0);assert.match(nodes['#checkbarNotice'].textContent,/برند/);
  vm.runInContext("checkbarState.lines[0].brand='Alpha'",c);c.confirm=()=>false;
  await vm.runInContext('issueCheckbar()',c);assert.equal(calls,0);
});

test('batch result exposes each independent document and escapes brands',()=>{
  const {context:c,nodes}=setup();
  vm.runInContext("renderCheckbarBrandBatch({id:11,brand_batch:[{id:11,number:'CB-000011',brand:'Alpha'},{id:12,number:'CB-000012',brand:'<Beta>'}]})",c);
  assert.equal(nodes['#checkbarBrandBatch'].hidden,false);
  assert.match(nodes['#checkbarBrandBatch'].innerHTML,/data-checkbar-view="12"/);
  assert.match(nodes['#checkbarBrandBatch'].innerHTML,/&lt;Beta>/);
  vm.runInContext("checkbarState.editing={id:11};checkbarState.source={};renderCheckbarBrandSplit()",c);
  assert.equal(nodes['#checkbarBrandSplitOptions'].hidden,true);
});
test('localized carton and unit input, blank distinct from zero',()=>{
  const {context}=setup();
  assert.equal(vm.runInContext("checkbarActual({cartons:'۲۰',units:'۱۰',conversion_rate:48})",context),970);
  assert.equal(vm.runInContext("checkbarActual({cartons:'۲',units:'٣',conversion_rate:12})",context),27);
  assert.equal(vm.runInContext("checkbarActual({cartons:'',units:'',conversion_rate:12})",context),null);
  assert.equal(vm.runInContext("checkbarActual({cartons:'۰',units:'',conversion_rate:12})",context),0);
  for(const text of ['-1','0.5','NaN','Infinity'])assert.throws(()=>vm.runInContext(`checkbarNumeric('${text}',true)`,context));
});

test('LAN HTTP works without secure-context randomUUID',()=>{
  const {context}=setup();
  context.crypto={getRandomValues:array=>array.fill(15)};
  assert.equal(vm.runInContext('checkbarRequestId()',context),'0f'.repeat(16));
});
test('supplier catalog escapes and excludes existing products',()=>{
  const {context,nodes}=setup();
  vm.runInContext("checkbarState.source={catalog:[{product_code:'001',product_name:'existing'},{product_code:'002',product_name:'<unsafe>',barcode:'123',conversion_rate:6}]};checkbarState.lines=[{product_code:'001'}]",context);
  context.$('#checkbarCatalogSearch').value='۱۲۳';
  vm.runInContext('renderCheckbarProducts();renderCheckbarCatalog()',context);
  assert.match(nodes['#checkbarCatalogRows'].innerHTML,/&lt;unsafe>/);
  assert.doesNotMatch(nodes['#checkbarCatalogRows'].innerHTML,/existing/);
});
test('late scope response cannot overwrite newer warehouse selection',async()=>{
  const {context,nodes}=setup();
  const pending=[];context.api=()=>new Promise(resolve=>pending.push(resolve));
  context.$('#checkbarWarehouse').value='karaj';context.$('#checkbarSupplier').value='';
  const first=vm.runInContext('checkbarLoadContext(true)',context);
  context.$('#checkbarWarehouse').value='tehran';
  const second=vm.runInContext('checkbarLoadContext(true)',context);
  pending[1]({suppliers:['new'],orders:[]});await second;
  pending[0]({suppliers:['old'],orders:[]});await first;
  assert.match(nodes['#checkbarSupplier'].innerHTML,/new/);
  assert.doesNotMatch(nodes['#checkbarSupplier'].innerHTML,/old/);
});

test('supplier with no outstanding orders can continue',async()=>{
  const {context,nodes}=setup();
  context.api=async()=>({suppliers:['new supplier'],orders:[]});
  context.$('#checkbarWarehouse').value='karaj';context.$('#checkbarSupplier').value='new supplier';
  await vm.runInContext('checkbarLoadContext()',context);
  assert.equal(nodes['#checkbarPrepare'].disabled,false);
  assert.match(nodes['#checkbarSourceStatus'].textContent,/بدون سفارش/);
});

test('adding all order items is opt-in and never copies ordered quantity into arrived counts',async()=>{
  for(const selected of [false,true]){
    const {context}=setup();context.crypto={randomUUID:()=> 'synthetic-key'};
    context.$('#checkbarSupplier').value='supplier';context.$('#checkbarWarehouse').value='karaj';
    context.$('#checkbarIncludeOrderItems').checked=selected;
    context.api=async()=>({warehouse:'karaj',supplier:'supplier',order_ids:[],catalog:[],lines:[],aggregate_open_lines:[{product_code:'A',remaining_qty:200,conversion_rate:12}],outstanding_orders:[]});
    vm.runInContext('renderCheckbarProducts=()=>{};renderCheckbarLines=()=>{}',context);
    await vm.runInContext('checkbarPrepare()',context);
    assert.equal(vm.runInContext('checkbarState.lines.length',context),selected?1:0);
    if(selected)assert.equal(vm.runInContext('checkbarActual(checkbarState.lines[0])',context),null);
  }
});

test('aggregate order origin and persistent supplier summary are clear without choosing individual orders',()=>{
  const {context}=setup();
  vm.runInContext("checkbarState.source={outstanding_orders:[{number:'OLD-1'},{number:'NEW-2'}]}",context);
  assert.equal(vm.runInContext("checkbarOriginLabel({aggregate_open_order:true,preorder_id:null})",context),'مجموع سفارش‌های در راه');
  assert.equal(vm.runInContext("checkbarOriginLabel({preorder_id:null})",context),'افزودهٔ دستی');
  assert.match(vm.runInContext('checkbarOutstandingSummary()',context),/2.*OLD-1.*NEW-2/);
  vm.runInContext('checkbarState.saved={id:1}',context);assert.equal(vm.runInContext('checkbarOutstandingSummary()',context),'');
  const html=readFileSync('app/static/warehouse-assistant.html','utf8');
  assert.ok(html.indexOf('id="checkbarOutstandingSummary"')<html.indexOf('id="checkbarTable"'));
  assert.match(html,/class="preview-dialog-footer checkbar-guided-footer"/);
  assert.ok(html.indexOf('id="checkbarSummary"')<html.indexOf('id="checkbarNextAction"'));
});

test('archive search normalizes digits and escapes supplier names',()=>{
  const {context,nodes}=setup();context.formatRefreshDate=v=>v;
  vm.runInContext("checkbarArchive=[{id:1,number:'CB-000001',supplier:'<unsafe>',warehouse_name:'Karaj',created_at:'now'}]",context);
  context.$('#checkbarArchiveSearch').value='۰۰۰۰۰۱';
  vm.runInContext('renderCheckbarArchive()',context);
  assert.match(nodes['#checkbarHistoryRows'].innerHTML,/&lt;unsafe>/);
  context.$('#checkbarArchiveSearch').value='no match';vm.runInContext('renderCheckbarArchive()',context);
  assert.doesNotMatch(nodes['#checkbarHistoryRows'].innerHTML,/CB-000001/);
});

test('removed source lines cannot return as ambiguous manual additions',()=>{
  const {context,nodes}=setup();
  vm.runInContext("checkbarState.source={lines:[{product_code:'001'}],catalog:[{product_code:'001',product_name:'source'}]};checkbarState.lines=[];renderCheckbarProducts()",context);
  assert.equal(vm.runInContext('checkbarFilteredProducts().length',context),0);
});

test('check bar headers retain compact role widths in the shared table fitter',()=>{
  const html=readFileSync('app/static/warehouse-assistant.html','utf8');
  const header=html.split('id="checkbarTable"')[1].split('</thead>')[0];
  assert.doesNotMatch(header,/مالیات/);assert.match(header,/تعداد کل/);
  const widths=[...header.matchAll(/data-user-column-width="(\d+)"/g)].map(m=>Number(m[1]));
  assert.equal(widths.length,19);assert.equal(widths[4],240);assert.equal(widths[5],65);
  assert.equal(widths.reduce((a,b)=>a+b,0),2205);
});

test('brand then level3 narrows catalog and exact localized supplier code adds only one match',()=>{
  const {context}=setup();
  vm.runInContext("checkbarState.source={catalog:[{product_code:'a',manufacturer_product_code:'012',brand:'B',group_level3:'G'},{product_code:'b',manufacturer_product_code:'012',brand:'C',group_level3:'G'},{product_code:'c',manufacturer_product_code:'012',brand:'B',group_level3:'H'}]}",context);
  context.$('#checkbarBrand').value='B';context.$('#checkbarGroup3').value='G';
  assert.equal(vm.runInContext('checkbarFilteredProducts().length',context),1);
  context.$('#checkbarProductSearch').value='۰۱۲';
  vm.runInContext('addCheckbarProducts=codes=>{checkbarState.testCodes=codes};quickAddCheckbar()',context);
  assert.equal(vm.runInContext('checkbarState.testCodes.join()',context),'a');
});

test('ambiguous supplier code opens picker without arbitrary addition',()=>{
  const {context}=setup();context.$('#checkbarCatalogDialog').showModal=()=>{};
  vm.runInContext("checkbarState.source={catalog:[{product_code:'a',manufacturer_product_code:'12'},{product_code:'b',manufacturer_product_code:'12'}]};addCheckbarProducts=()=>{throw Error('must not add')}",context);
  context.$('#checkbarProductSearch').value='۱۲';vm.runInContext('quickAddCheckbar()',context);
  assert.match(context.$('#checkbarCatalogRows').innerHTML,/data-checkbar-catalog-code="a"/);
  assert.match(context.$('#checkbarCatalogRows').innerHTML,/data-checkbar-catalog-code="b"/);
});

test('worksheet stage saves blank rows without matching, confirmation or receipt consumption',async()=>{
  const {context:c}=issueSetup();let body;
  c.confirm=()=>{throw new Error('Initial save must not confirm receipt')};
  c.api=async(url,options)=>{body=JSON.parse(options.body);throw new TypeError('offline')};
  vm.runInContext("checkbarState.worksheetWorkflow=true;checkbarState.lines[0].cartons='';checkbarState.lines[0].units=''",c);
  await vm.runInContext('issueCheckbar()',c);
  assert.equal(body.worksheet_workflow,true);assert.equal(body.confirm_receipt,undefined);
  assert.equal(body.lines[0].cartons,null);assert.equal(body.lines[0].units,null);
});

test('optional matching sends only the explicit skip choice and freezes it for retries',async()=>{
  const {context:c}=issueSetup();const bodies=[];
  c.orderMatchingRequest=()=>{throw Error('No matching request should run')};
  c.api=async(url,o)=>{bodies.push(o.body);throw new TypeError('offline')};
  vm.runInContext("checkbarState.worksheetWorkflow=true;checkbarState.editing={id:7,revision:1,worksheet_approved_at:'now'};checkbarState.skipOrderMatching=true",c);
  await vm.runInContext('issueCheckbar()',c);
  vm.runInContext('checkbarState.skipOrderMatching=false',c);
  await vm.runInContext('issueCheckbar()',c);
  assert.equal(bodies.length,2);assert.equal(bodies[0],bodies[1]);
  const body=JSON.parse(bodies[0]);
  assert.equal(body.skip_order_matching,true);assert.equal(body.confirm_receipt,true);
  assert.equal(body.allocations,undefined);assert.equal(body.allocation_revision,undefined);
  assert.equal(c.$('#checkbarMatchOrders').disabled,true);
});

test('worksheet approval retries the same revision and request without repeating a new action',async()=>{
  const {context:c}=issueSetup();const calls=[];
  c.crypto={randomUUID:()=> 'approve-fixed'};
  c.api=async(url,options)=>{calls.push({url,body:options.body});throw new TypeError('offline')};
  vm.runInContext("checkbarState.saved={id:7,revision:2,worksheet_workflow:true}",c);
  await vm.runInContext('approveCheckbarWorksheet()',c);await vm.runInContext('approveCheckbarWorksheet()',c);
  assert.equal(calls.length,2);assert.equal(calls[0].url,'/warehouse-assistant/api/checkbars/7/approve-worksheet');
  assert.equal(calls[0].body,calls[1].body);assert.equal(JSON.parse(calls[0].body).expected_revision,2);
});

test('worksheet archive routes to approval then physical count and only approved sheets can print',()=>{
  const {context:c}=setup();
  c.doc={id:7,worksheet_workflow:true,receipt_state:'not_sent'};
  const draft=vm.runInContext('checkbarArchiveActions(doc)',c);
  assert.match(draft,/data-checkbar-action="worksheet"/);assert.doesNotMatch(draft,/\/7\/print/);
  c.doc.worksheet_approved_at='now';
  const approved=vm.runInContext('checkbarArchiveActions(doc)',c);
  assert.match(approved,/data-checkbar-action="edit" data-workflow-primary/);assert.match(approved,/\/7\/print/);
});

function issueSetup(){
  const s=setup(),c=s.context;
  const ref=c.$('#checkbarReference');ref.value='2222';ref.dataset={checkbarMeta:'reference_no'};
  c.document.querySelectorAll=selector=>selector==='[data-checkbar-meta]'?[ref]:[];
  vm.runInContext("checkbarState.requestId='same-key';checkbarState.source={warehouse:'karaj',supplier:'supplier',order_ids:[],expected_token:'token'};checkbarState.lines=[{product_code:'123',cartons:'20',units:'10',conversion_rate:48}];renderCheckbarLines=()=>{};renderCheckbarProducts=()=>{};loadCheckbarPage=()=>{}",c);
  return s;
}
test('success is persistent inside dialog, names saved document and uncounted rows',async()=>{
  const {context:c,nodes}=issueSetup();c.api=async()=>({document:{id:1,number:'CB-000001',warehouse:'karaj',warehouse_name:'Karaj',supplier:'supplier',metadata:{},lines:[{cartons:null,units:null}]}});
  await vm.runInContext('issueCheckbar()',c);
  assert.match(nodes['#checkbarNotice'].textContent,/CB-000001.*موفقیت/);
  assert.match(nodes['#checkbarNotice'].textContent,/1 ردیف شمارش/);
  assert.equal(nodes['#checkbarIssue'].textContent,'ذخیره شد');assert.equal(nodes['#checkbarDownload'].hidden,false);
  assert.equal(nodes['#checkbarNotice'].focused,true);
});
test('invalid draft identifies row and field without posting',async()=>{
  const {context:c,nodes}=issueSetup();c.api=()=>{throw Error('must not post')};
  vm.runInContext("checkbarState.lines[0].cartons='-2'",c);await vm.runInContext('issueCheckbar()',c);
  assert.match(nodes['#checkbarNotice'].textContent,/ردیف 1، کد 123.*کارتن/);assert.equal(nodes['#checkbarIssue'].disabled,false);
  assert.equal(vm.runInContext('checkbarState.pending',c),null);
});
test('network failure retries same payload/key and blocks simultaneous submission',async()=>{
  const {context:c,nodes}=issueSetup();const bodies=[];let reject;
  c.api=(_,options)=>{bodies.push(options.body);return new Promise((_,r)=>reject=r)};
  const first=vm.runInContext('issueCheckbar()',c);await vm.runInContext('issueCheckbar()',c);assert.equal(bodies.length,1);
  reject(new TypeError('offline'));await first;assert.match(nodes['#checkbarNotice'].textContent,/ممکن است سند ثبت شده/);
  c.api=async(_,options)=>{bodies.push(options.body);throw new TypeError('offline')};await vm.runInContext('issueCheckbar()',c);
  assert.equal(bodies[0],bodies[1]);assert.equal(nodes['#checkbarIssue'].textContent,'بررسی و تلاش مجدد');
});
test('explicit validation rejection unlocks drafts for correction',async()=>{
  const {context:c,nodes}=issueSetup();c.api=async()=>{throw Object.assign(new Error('اطلاعات کالا تغییر کرده'),{status:400})};
  await vm.runInContext('issueCheckbar()',c);
  assert.equal(vm.runInContext('checkbarState.pending',c),null);assert.match(nodes['#checkbarNotice'].textContent,/اطلاعات کالا تغییر کرده/);
  assert.equal(nodes['#checkbarIssue'].disabled,false);
});
test('empty quantities require confirmation; explicit zero stays; only confirmed rows are posted',async()=>{
  const {context:c,nodes}=issueSetup();let posted;
  c.api=async(_,options)=>{posted=JSON.parse(options.body);throw new TypeError('offline')};
  vm.runInContext("checkbarState.lines=[{product_code:'blank',cartons:' ',units:'',conversion_rate:12},{product_code:'zero',cartons:'۰',units:'',conversion_rate:12}]",c);
  await vm.runInContext('issueCheckbar()',c);
  assert.equal(posted,undefined);assert.equal(nodes['#checkbarEmptyActions'].hidden,false);
  assert.equal(vm.runInContext('checkbarState.lines.length',c),2);
  await vm.runInContext('saveCheckbarWithoutEmpty()',c);
  assert.deepEqual(posted.lines.map(l=>l.product_code),['zero']);assert.equal(posted.lines[0].cartons,0);
});
test('all-empty draft cannot issue a zero-line document',async()=>{
  const {context:c,nodes}=issueSetup();c.api=()=>{throw Error('must not post')};
  vm.runInContext("checkbarState.lines=[{product_code:'blank',cartons:'',units:'',conversion_rate:12}]",c);
  await vm.runInContext('issueCheckbar()',c);assert.equal(nodes['#checkbarRemoveEmpty'].disabled,true);
  await vm.runInContext('saveCheckbarWithoutEmpty()',c);assert.equal(vm.runInContext('checkbarState.lines.length',c),1);
  assert.match(nodes['#checkbarNotice'].textContent,/حداقل یک کالا/);
});

test('edit uses existing identity and revision and retains zero through empty confirmation',async()=>{
  const {context:c}=issueSetup();let sent;
  vm.runInContext("checkbarState.editing={id:7,revision:2};checkbarState.lines=[{product_code:'blank',units:'',cartons:''},{product_code:'zero',units:'0',cartons:''}]",c);
  c.api=async(url,options)=>{sent={url,options};throw new TypeError('offline')};
  await vm.runInContext('issueCheckbar()',c);assert.equal(sent,undefined);
  await vm.runInContext('saveCheckbarWithoutEmpty()',c);
  assert.equal(sent.url,'/warehouse-assistant/api/checkbars/7');assert.equal(sent.options.method,'PUT');
  const body=JSON.parse(sent.options.body);assert.equal(body.expected_revision,2);assert.equal(body.warehouse,undefined);
  assert.equal(body.lines.length,1);assert.equal(body.lines[0].units,0);
});

test('delete cancellation never sends; uncertain deletion retries same revision and key',async()=>{
  const {context:c}=issueSetup();c.crypto={randomUUID:()=> 'delete-key'};
  vm.runInContext("checkbarState.saved={id:7,number:'CB-000007',revision:2}",c);
  const calls=[];c.api=async(url,options)=>{calls.push({url,options});throw new TypeError('offline')};
  c.confirm=()=>false;await vm.runInContext('deleteSavedCheckbar()',c);assert.equal(calls.length,0);
  c.confirm=()=>true;await vm.runInContext('deleteSavedCheckbar()',c);await vm.runInContext('deleteSavedCheckbar()',c);
  assert.equal(calls.length,2);assert.equal(calls[0].options.method,'DELETE');
  assert.equal(calls[0].options.body,calls[1].options.body);
  assert.equal(JSON.parse(calls[0].options.body).expected_revision,2);
});

test('opening edit keeps historical fields and locks document scope',async()=>{
  const {context:c,nodes}=issueSetup();c.crypto={randomUUID:()=> 'edit-key'};
  c.api=async()=>({document:{id:7,number:'CB-000007',revision:3,worksheet_workflow:true,worksheet_approved_at:'approved',warehouse:'karaj',warehouse_name:'Karaj',supplier:'supplier',metadata:{reference_no:'2222'},lines:[{product_code:'123',cartons:0,units:null,conversion_rate:48,tax:9}]},catalog:[]});
  vm.runInContext("checkbarState.saved={id:7}",c);await vm.runInContext('editSavedCheckbar()',c);
  assert.equal(vm.runInContext('checkbarState.saved',c),null);
  assert.equal(vm.runInContext('checkbarState.editing.revision',c),3);
  assert.equal(vm.runInContext('checkbarDraftStage()',c),false);
  assert.equal(vm.runInContext('checkbarState.lines[0].cartons',c),0);
  assert.equal(nodes['#checkbarWarehouse'].disabled,true);assert.equal(nodes['#checkbarReselect'].hidden,true);
  assert.equal(nodes['#checkbarIssue'].textContent,'ذخیره اصلاحات');
  let body;c.api=async(_,o)=>{body=JSON.parse(o.body);throw new TypeError('offline')};
  await vm.runInContext('issueCheckbar()',c);assert.equal(body.lines[0].tax,9);
});

test('deleted archive exposes history without current download and escapes version authors',()=>{
  const {context:c,nodes}=setup();c.formatRefreshDate=v=>v;
  vm.runInContext("checkbarArchive=[{id:7,number:'CB-000007',deleted:true}];renderCheckbarArchive();renderCheckbarVersions(7,[{revision:2,operation:'delete',created_by:'<author>',created_at:'now'}])",c);
  assert.match(nodes['#checkbarHistoryRows'].innerHTML,/حذف‌شده/);
  assert.doesNotMatch(nodes['#checkbarHistoryRows'].innerHTML,/href=/);
  assert.match(nodes['#checkbarVersions'].innerHTML,/&lt;author>/);
  assert.match(nodes['#checkbarVersions'].innerHTML,/\/7\/revisions\/2\/document.xlsx/);
});


test('reference is required on both create and edit before any request',async()=>{
  for(const editing of [null,{id:7,revision:0}]){
    for(const value of ['', ' ', '۰', '-1', '1.5', 'INV-22', '2147483648', '00000000001']){
      const {context:c,nodes}=issueSetup();let calls=0;
      c.api=async()=>{calls++;throw new Error('must not post')};
      c.editingFixture=editing;vm.runInContext('checkbarState.editing=editingFixture',c);
      c.$('#checkbarReference').value=value;
      await vm.runInContext('issueCheckbar()',c);
      assert.equal(calls,0);assert.equal(vm.runInContext('checkbarState.pending',c),null);
      assert.match(nodes['#checkbarNotice'].textContent,/شماره.*عطف/);
    }
  }
});

test('localized reference is normalized into the frozen save payload',async()=>{
  const {context:c}=issueSetup();let body;
  c.$('#checkbarReference').value=' ۲٢۲۲ ';
  c.api=async(_,options)=>{body=JSON.parse(options.body);throw new TypeError('offline')};
  await vm.runInContext('issueCheckbar()',c);
  assert.equal(body.metadata.reference_no,'2222');
});
