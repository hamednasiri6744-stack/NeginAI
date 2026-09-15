const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const source=readFileSync('app/static/warehouse-rebalancing.js','utf8');
const html=readFileSync('app/static/warehouse-assistant.html','utf8');
function context(extra={}){
  const ctx=vm.createContext({setTimeout,clearTimeout,document:{addEventListener(){},querySelectorAll:()=>[]},esc:s=>String(s??'').replaceAll('<','&lt;'),fa:String,formatRefreshDate:String,crypto:{getRandomValues:values=>values.fill(7)},...extra});
  vm.runInContext(source,ctx);return code=>vm.runInContext(code,ctx);
}
const offer={product_code:'A',product_name:'<test>',available_cartons:2,conversion_rate:12,source_position:112,destination_position:0,source_daily_demand:2,destination_daily_demand:2};

test('unposted document offers explicit ERP registration before and after status refresh',()=>{
  const run=context({has:()=>true});
  for(const status of [null,undefined,'not_sent','rejected']){
    const markup=run(`transferDocumentActions({key:'6',number:'TR-000006',credit_status:${JSON.stringify(status)},reflected:0})`);
    assert.match(markup,/data-transfer-document-register="6"/);
    assert.match(markup,/ثبت در ورانگر/);
    assert.match(markup,/data-transfer-document-delete="6"/);
  }
});

test('registration rendered during a mutation shows its lock and is re-enabled afterward',()=>{
  const button={disabled:false},nodes=new Proxy({},{get:(t,k)=>t[k]??(t[k]={querySelectorAll:()=>[]})});
  const run=context({has:()=>true,$:s=>nodes[s],document:{addEventListener(){},querySelectorAll:()=>[button]}});
  run('rebalanceState.busy=true');
  assert.match(run("transferDocumentActions({key:'1',number:'TR-1',credit_status:'not_sent',reflected:0})"),/data-transfer-document-register[^>]*disabled/);
  run('syncTransferRegistrationButtons()');assert.equal(button.disabled,true);
  run('rebalanceState.busy=false;syncTransferRegistrationButtons()');assert.equal(button.disabled,false);
});

test('a blocked registration click explains the active operation instead of silently returning',async()=>{
  const notices=[],nodes={textContent:''};const run=context({has:()=>true,toast:t=>notices.push(t),$:()=>nodes});
  run("rebalanceState.busy=true;rebalanceState.requests=[{issued_document_id:1,quantity:12,cartons:1}]");
  await run("openTransferRegistration('1')");
  assert.match(notices.join(' '),/عملیات/);
});

test('read timeout releases the local mutation lock and a late list cannot replace current data',async()=>{
  let expire,finish;const nodes=new Proxy({},{get:(t,k)=>t[k]??(t[k]={querySelectorAll:()=>[]})});
  const run=context({$:s=>nodes[s],setTimeout:f=>{expire=f;return 1},clearTimeout(){},api:()=>new Promise(resolve=>{finish=resolve})});
  run("rebalanceState.stage='documents';rebalanceState.requests=[{issued_document_id:1,quantity:12,cartons:1}]");
  const work=run('mutatePendingTransfer(()=>loadTransferRequests())');
  assert.equal(run('rebalanceState.busy'),true);expire();await work;
  assert.equal(run('rebalanceState.busy'),false);
  assert.match(nodes['#transferRequestStatus'].textContent,/بازخوانی/);
  finish({items:[]});await Promise.resolve();await Promise.resolve();
  assert.equal(run('rebalanceState.requests.length'),1);
});

test('registration dialog survives status timeout, can reload, and never submits without preflight',async()=>{
  let expire;const reads=[],nodes=new Proxy({},{get:(t,k)=>t[k]??(t[k]={open:false,checked:false,hidden:false,disabled:false,textContent:'',showModal(){this.open=true},focus(){},scrollIntoView(){},querySelectorAll:()=>[]})});
  const run=context({$:s=>nodes[s],has:()=>true,toast(){},setTimeout:f=>{expire=f;return 1},clearTimeout(){},
    api:(url,options)=>new Promise(resolve=>reads.push({url,options,resolve}))});
  run(readFileSync('app/static/warehouse-transfer-bridge.js','utf8'));
  run("renderTransferRequests=()=>{};rebalanceState.requests=[{issued_document_id:1,credit_status:'not_sent',quantity:12,cartons:1}]");
  const opened=run("openTransferRegistration('1')");
  assert.equal(nodes['#transferDocumentDialog'].open,true);expire();await opened;
  assert.equal(run('transferCreditState.busy'),false);
  assert.equal(nodes['#transferCreditPreview'].disabled,true);
  assert.match(nodes['#transferCreditMessage'].textContent,/بازخوانی/);
  const reload=run("loadTransferCredit('1')");
  reads[1].resolve({status:'not_sent',enabled:true,commit_enabled:true});await reload;
  reads[0].resolve({status:'sent',enabled:true,result:{VocherNo:999}});await Promise.resolve();await Promise.resolve();
  assert.equal(run('transferCreditState.status.status'),'not_sent');
  assert.equal(nodes['#transferCreditPreview'].disabled,false);
  await run("runTransferCredit('submit')");
  assert.equal(reads.length,2);assert.ok(reads.every(r=>!r.options?.method));
});

test('ERP registration is absent for posted, uncertain, received or unauthorized documents',()=>{
  const run=context({has:()=>true});
  for(const status of ['sent','pending','blocked','unknown']){
    const markup=run(`transferDocumentActions({key:'1',number:'TR-000001',credit_status:'${status}',erp_status:'missing',reflected:0})`);
    assert.doesNotMatch(markup,/data-transfer-document-register|data-transfer-document-delete/);
  }
  assert.doesNotMatch(run("transferDocumentActions({key:'1',credit_status:'not_sent',reflected:1})"),/data-transfer-document-register/);
  for(const missing of ['warehouse.order.draft','warehouse.receipt.transfer']){
    const restricted=context({has:cap=>cap!==missing});
    assert.doesNotMatch(restricted("transferDocumentActions({key:'1',credit_status:'not_sent',reflected:0})"),/data-transfer-document-register/);
  }
});

test('registration entry opens the selected document and reads status without preflight or posting',async()=>{
  const calls=[],nodes=new Proxy({},{get:(t,k)=>t[k]??(t[k]={open:false,showModal(){this.open=true},focus(){this.focused=true},scrollIntoView(){this.scrolled=true}})});
  const run=context({$:s=>nodes[s],has:()=>true,loadTransferCredit:async key=>{calls.push(key)}});
  run("rebalanceState.requests=[{issued_document_id:6,credit_status:'not_sent',quantity:12,cartons:1}]");
  await run("openTransferRegistration('6')");
  assert.deepEqual(calls,['6']);assert.equal(run('rebalanceState.openDocument'),'6');
  assert.equal(nodes['#transferDocumentDialog'].open,true);
  assert.equal(nodes['#transferCreditControls'].scrolled,true);
  run("rebalanceState.busy=true");await run("openTransferRegistration('6')");assert.equal(calls.length,1);
  run("rebalanceState.busy=false;rebalanceState.requests[0].credit_status='sent'");
  await run("openTransferRegistration('6')");assert.equal(calls.length,1);
});

test('credit status and source voucher do not imply destination receipt',()=>{
  const run=context();
  assert.match(run("transferDocumentStatus({credit_status:'pending',reflected:0,lines:[{}]})"),/پیگیری/);
  assert.match(run("transferDocumentStatus({credit_status:'sent',erp_status:'confirmed',reflected:0,lines:[{}]})"),/در راه مقصد/);
  assert.equal(run("transferCreditNumber({credit_status:'sent',credit_result_json:'{\"VocherNo\":71}'})"),71);
  assert.equal(run("transferCreditNumber({credit_status:'pending',credit_result_json:'{\"VocherNo\":71}'})"),null);
});
test('standalone proposal provides editable cartons, one action and resulting coverage',()=>{
  const run=context({offer}),markup=run('balanceProposalRow(offer)');
  assert.match(markup,/max="2"/);assert.match(markup,/value="2"/);assert.match(markup,/data-balance-accept/);
  assert.match(markup,/&lt;test>/);
  const after=run('balanceAfter(offer,2)');assert.equal(after.source,44);assert.equal(after.destination,12);
});
test('request identity works over LAN HTTP without randomUUID',()=>assert.match(context()('transferRequestId()'),/^[a-f0-9]{32}$/));
function fixture(value=1){
  const input={value:String(value),disabled:false,focus(){this.focused=true}},action={textContent:'تأیید جابه‌جایی',disabled:false},error={textContent:''};
  const row={dataset:{balanceCode:'A'},querySelector:s=>s==='[data-balance-cartons]'?input:s==='[data-balance-error]'?error:action};
  const nodes=new Proxy({},{get:(t,k)=>t[k]??(t[k]={querySelectorAll:()=>[input,action]})});
  const posts=[],notices=[];let resolve,reject;
  const run=context({$:s=>nodes[s],row,offer,toast:t=>notices.push(t),loadOrders:async()=>{},loadAutomaticPreorders:async()=>{},
    api:async(url,options)=>{if(!options)return url.endsWith('/tehran/karaj')?{source:'tehran',destination:'karaj',lines:[]}:{items:[]};posts.push(JSON.parse(options.body));return new Promise((a,b)=>{resolve=a;reject=b})}});
  run("rebalanceState.proposal={source:'tehran',destination:'karaj',expected_token:'token',lines:[offer]};");
  return {run,row,input,action,error,nodes,posts,notices,finish:()=>resolve({reduced_purchase_quantity:12}),fail:()=>reject(new Error('network'))};
}
test('one click transfers only its row and blocks simultaneous submissions',async()=>{
  const f=fixture(),work=f.run('acceptBalanceRow(row)');await f.run('acceptBalanceRow(row)');
  assert.equal(f.posts.length,1);assert.deepEqual(f.posts[0].lines,[{product_code:'A',cartons:1}]);
  assert.equal(f.posts[0].expected_token,'token');assert.ok(f.posts[0].request_id);assert.equal(f.input.disabled,true);
  f.finish();await work;assert.equal(f.run('rebalanceState.stage'),'requests');assert.equal(f.input.disabled,false);
});
test('invalid or above-ceiling quantity does not submit',async()=>{
  for(const n of [0,-1,1.5,3,NaN]){const f=fixture(n);await f.run('acceptBalanceRow(row)');assert.equal(f.posts.length,0);assert.match(f.error.textContent,/کارتن کامل/);assert.equal(f.input.focused,true)}
});

test('Gilan minimum is visible and below-minimum quantity never submits',async()=>{
  const f=fixture(1);f.run('rebalanceState.proposal.lines[0]={...rebalanceState.proposal.lines[0],minimum_cartons:2}');
  const markup=f.run('balanceProposalRow(rebalanceState.proposal.lines[0])');
  assert.match(markup,/min="2"/);assert.match(markup,/حداقل 2 کارتن/);
  await f.run('acceptBalanceRow(row)');assert.equal(f.posts.length,0);assert.match(f.error.textContent,/از 2 تا 2/);
  f.input.value='2';const work=f.run('acceptBalanceRow(row)');assert.equal(f.posts.length,1);f.finish();await work;
});

test('Gilan route explains the 30/20 rule without an upper coverage cap',()=>{
  const f=fixture();f.run("rebalanceState.direction='tehran-gilan';renderTransferRequests()");
  assert.match(f.nodes['#balanceRuleSummary'].textContent,/تهران و کرج حداقل ۳۰/);
  assert.match(html,/بدون سقف روز پوشش/);
});
test('uncertain response retries the same id without losing amount',async()=>{
  const f=fixture(),work=f.run('acceptBalanceRow(row)');f.fail();await work;
  assert.equal(f.input.value,'1');assert.equal(f.error.textContent,'network');
  const retry=f.run('acceptBalanceRow(row)');assert.equal(f.posts[1].request_id,f.posts[0].request_id);f.finish();await retry;
});
test('separate directional menus and stages do not mix requests',()=>{
  const f=fixture();
  f.run("rebalanceState.requests=[{source:'tehran',destination:'karaj',product_code:'THR',cartons:2},{source:'karaj',destination:'tehran',product_code:'KRJ',cartons:3}];renderTransferRequests()");
  assert.match(f.nodes['#transferPendingRows'].innerHTML,/THR/);assert.doesNotMatch(f.nodes['#transferPendingRows'].innerHTML,/KRJ/);
  assert.doesNotMatch(f.nodes['#transferRequestRows'].innerHTML,/data-transfer-document/);
  assert.equal(f.nodes['#balanceRequestPanel'].hidden,true);
  f.run("rebalanceState.direction='karaj-tehran';rebalanceState.stage='requests';rebalanceState.requestWarehouse='tehran';renderTransferRequests()");
  assert.match(f.nodes['#transferPendingRows'].innerHTML,/KRJ/);assert.doesNotMatch(f.nodes['#transferPendingRows'].innerHTML,/THR/);
  assert.equal(f.nodes['#balanceProposalPanel'].hidden,true);
  f.run("rebalanceState.requestWarehouse='all';rebalanceState.direction='all';renderTransferRequests()");
  assert.match(f.nodes['#transferPendingRows'].innerHTML,/KRJ/);assert.match(f.nodes['#transferPendingRows'].innerHTML,/THR/);
});
test('ordering returns to purchase only; transfers have a standalone page',()=>{
  for(const id of ['transfersView','balanceProposalPanel','balanceRequestPanel'])assert.match(html,new RegExp('id="'+id+'"'));
  for(const s of ['tehran','karaj','gilan'])for(const d of ['tehran','karaj','gilan'])if(s!==d)assert.match(html,new RegExp('data-transfer-direction="'+s+'-'+d+'"'));
  assert.doesNotMatch(html,/data-order-column="transfer_supply"|manualTransferActions|systemTransferActions/);
  for(const file of ['warehouse-assistant.js','warehouse-order-workflow.js'])assert.doesNotMatch(readFileSync('app/static/'+file,'utf8'),/loadOrderTransfers\(|decorateOrderingTransfers\(/);
});

test('stock reconciliation requires a newer snapshot and receipt permission',()=>{
  const nodes=new Proxy({},{get:(t,k)=>t[k]??(t[k]={})});
  const run=context({$:s=>nodes[s],has:()=>true});
  run("rebalanceState.requests=[{id:1,credit_status:'sent',erp_status:'confirmed',source_stock_status:'reflected',source_stock_snapshot_id:5,source:'tehran',destination:'karaj',cartons:1,snapshot_id:4,current_snapshot_id:4}];renderTransferRequests()");
  assert.match(run('transferLineRow(rebalanceState.requests[0])'),/data-balance-reflect="1" disabled/);
  run('rebalanceState.requests[0].current_snapshot_id=5;renderTransferRequests()');
  assert.doesNotMatch(run('transferLineRow(rebalanceState.requests[0])'),/data-balance-reflect="1" disabled/);
  run("rebalanceState.requests[0].reflected_at='now';renderTransferRequests()");
  assert.doesNotMatch(run('transferLineRow(rebalanceState.requests[0])'),/data-balance-reflect/);
  assert.match(nodes['#transferPendingRows'].innerHTML,/دریافت و منعکس‌شده/);
});

test('reflection form records both document numbers and explicit confirmation',()=>{
  for(const id of ['balanceSourceDocument','balanceDestinationDocument','balanceReflectedConfirmed'])assert.match(html,new RegExp('id="'+id+'"[^>]*required'));
  assert.match(source,/snapshot_id:selection.snapshot_id/);
  assert.match(source,/confirmed:\$\('#balanceReflectedConfirmed'\).checked/);
});

test('batch submits selected rows once, preserving their individual quantities',async()=>{
  const f=fixture();f.run("rebalanceState.proposal.lines.push({...offer,product_code:'B'})");
  f.run('batchRows=[row]');
  // Independent fake row stays in the same JS context as the row handler.
  f.run("batchRows.push({dataset:{balanceCode:'B'},querySelector:s=>s==='[data-balance-cartons]'?{value:'2'}:{textContent:''}})");
  const work=f.run("acceptBalanceRows(batchRows,row.querySelector('[data-balance-accept]'),row.querySelector('[data-balance-error]'))");
  assert.deepEqual(f.posts[0].lines,[{product_code:'A',cartons:1},{product_code:'B',cartons:2}]);
  f.finish();await work;assert.equal(f.posts.length,1);
});

test('batch validation stops the whole request when a selected amount is invalid',async()=>{
  const f=fixture();f.run("rebalanceState.proposal.lines.push({...offer,product_code:'B'});badInput={value:'3',focus(){}};badRow={dataset:{balanceCode:'B'},querySelector:s=>s==='[data-balance-cartons]'?badInput:{textContent:''}}");
  await f.run("acceptBalanceRows([row,badRow],row.querySelector('[data-balance-accept]'),row.querySelector('[data-balance-error]'))");
  assert.equal(f.posts.length,0);assert.match(f.error.textContent,/کارتن کامل/);
});

test('hidden filtered rows are not part of visible batch selection',()=>{
  const rows=[{hidden:false,style:{},classList:{contains:()=>false}},{hidden:false,style:{},classList:{contains:()=>true}},{hidden:true,style:{},classList:{contains:()=>false}}];
  assert.equal(context({document:{addEventListener(){},querySelectorAll:()=>rows}})('visibleBalanceRows().length'),1);
});

test('manufacturer and brand render escaped and checkbox edits survive redraw',()=>{
  const run=context({offer});run("rebalanceState.edits.set('A',{value:'1',selected:true})");
  const markup=run("balanceProposalRow({...offer,manufacturer:'<maker>',brand:'Brand'})");
  assert.match(markup,/&lt;maker>/);assert.match(markup,/Brand/);assert.match(markup,/value="1"/);assert.match(markup,/data-balance-selected aria-label="[^"]*" checked/);
});

test('destination filter has all three warehouses plus all',()=>{
  for(const value of ['all','tehran','karaj','gilan'])assert.match(html,new RegExp('<button[^>]+data-transfer-warehouse="'+value+'"'));
  assert.match(source,/filteredTransferRequests/);
  assert.match(html,/id="balanceSelectAll"/);assert.match(html,/id="acceptBalanceSelection"/);
});

test('six confirmed route sections isolate source and destination, with trade name',()=>{
  const f=fixture();
  f.run("rebalanceState.stage='requests';rebalanceState.requests=['tehran','karaj','gilan'].flatMap(source=>['tehran','karaj','gilan'].filter(d=>d!==source).map(destination=>({source,destination,product_code:source+'-'+destination,brand:'Trade name',cartons:1})))");
  for(const s of ['tehran','karaj','gilan'])for(const d of ['tehran','karaj','gilan'])if(s!==d){
    f.run(`rebalanceState.direction='${s}-${d}';renderTransferRequests()`);
    const markup=f.nodes['#transferPendingRows'].innerHTML;
    assert.equal((markup.match(/<tr /g)||[]).length,1);assert.match(markup,new RegExp(s+'-'+d));
    assert.match(f.run('transferLineRow(filteredTransferRequests()[0])'),/Trade name/);
  }
  f.run("rebalanceState.direction='all';rebalanceState.requestWarehouse='gilan';renderTransferRequests()");
  assert.equal((f.nodes['#transferPendingRows'].innerHTML.match(/<tr /g)||[]).length,2);
});

test('only explicit issued identity groups documents, independent of confirmation batch',()=>{
  const run=context();
  const docs=run("transferDocuments([{batch_id:1,issued_document_id:1,source:'tehran',destination:'karaj',cartons:2,quantity:24,estimated_unit_price:70,issued_document_at:'2026-09-13',issued_document_date:'1405/06/22',issued_document_by:'user'},{batch_id:2,issued_document_id:1,source:'tehran',destination:'karaj',cartons:3,quantity:18,estimated_unit_price:100},{batch_id:2,source:'tehran',destination:'karaj',cartons:1,quantity:12,estimated_unit_price:70},{batch_id:3,issued_document_id:2,source:'tehran',destination:'gilan',cartons:1,quantity:12,estimated_unit_price:70}])");
  assert.equal(docs.length,2);assert.equal(docs[0].number,'TR-000001');assert.equal(docs[0].lines.length,2);
  assert.equal(docs[0].cartons,5);assert.equal(docs[0].quantity,42);assert.equal(docs[0].estimated_value,3480);
  assert.equal(docs[0].created_at,'2026-09-13');assert.equal(docs[0].created_by,'user');
});

test('missing price is unknown and partial receipt keeps document in transit',()=>{
  const run=context();run("d=transferDocuments([{issued_document_id:1,source:'tehran',destination:'karaj',quantity:12,cartons:1,estimated_unit_price:70,reflected_at:'now'},{issued_document_id:1,source:'tehran',destination:'karaj',quantity:12,cartons:1,estimated_unit_price:null}])[0]");
  assert.match(run('transferDocumentValue(d)'),/نامشخص/);assert.match(run('transferDocumentStatus(d)'),/بخشی/);
  for(const price of [null,0,-1,NaN,undefined])assert.equal(context({price})('transferLineValue({estimated_unit_price:price,quantity:12})'),null);
});

test('document opens only its lines, escaped names, and keeps fullscreen and close controls',()=>{
  const nodes=new Proxy({},{get:(t,k)=>t[k]??(t[k]={open:false,showModal(){this.open=true}})});
  const run=context({$:s=>nodes[s]});
  run("rebalanceState.requests=[{issued_document_id:3,source:'tehran',destination:'karaj',product_name:'<unsafe>',brand:'Trade',cartons:1,quantity:12,estimated_unit_price:70},{issued_document_id:4,source:'tehran',destination:'karaj',product_name:'excluded'}];openTransferDocument('3')");
  assert.equal(nodes['#transferDocumentDialog'].open,true);assert.match(nodes['#transferDocumentTitle'].textContent,/TR-000003/);
  assert.match(nodes['#transferDocumentLines'].innerHTML,/&lt;unsafe>/);assert.doesNotMatch(nodes['#transferDocumentLines'].innerHTML,/excluded/);
  assert.match(nodes['#transferDocumentSummary'].textContent,/840/);
  assert.match(html,/id="closeTransferDocument"/);assert.match(readFileSync('app/static/warehouse-fullscreen.js','utf8'),/'transferDocumentDialog'/);
});

function pendingFixture(){
  const rows=[1,2].map(id=>({dataset:{pendingId:String(id)},hidden:id===2,style:{},classList:{contains:()=>false},querySelector:()=>({checked:true})}));
  const nodes=new Proxy({},{get:(t,k)=>t[k]??(t[k]={querySelectorAll:()=>[]})});
  const calls=[];let resolve,reject;
  const run=context({$:s=>nodes[s],window:{confirm:()=>true},toast:()=>{},document:{addEventListener(){},querySelectorAll:s=>s.includes('tr[data-pending-id]')?rows:[]},
    api:async(url,options)=>{if(!options)return {items:[]};calls.push({url,...options});return new Promise((a,b)=>{resolve=a;reject=b})}});
  run("rebalanceState.stage='requests';rebalanceState.requests=[{id:1,product_name:'A',source:'tehran',destination:'karaj'}]");
  return {run,nodes,calls,finish:()=>resolve({documents:[{id:1}]}),fail:()=>reject(new Error('network'))};
}

test('bulk revoke and delete use one request for visible selections only and block duplicate clicks',async()=>{
  for(const action of ['delete','revoke']){
    const f=pendingFixture();f.run('rebalanceState.pendingSelection.add(1);rebalanceState.pendingSelection.add(2)');
    const work=f.run(`mutateSelectedPendingTransfers('${action}')`);
    await f.run(`mutateSelectedPendingTransfers('${action}')`);
    assert.equal(f.calls.length,1);assert.match(f.calls[0].url,/requests\/batch$/);
    assert.deepEqual(JSON.parse(f.calls[0].body),{request_ids:[1],action});
    f.finish();await work;
    assert.equal(f.run('rebalanceState.pendingSelection.has(1)'),false);
    assert.equal(f.run('rebalanceState.pendingSelection.has(2)'),true);
  }
});

test('bulk cancellation is harmless and failed request preserves selection with visible error',async()=>{
  const f=pendingFixture();f.run('window.confirm=()=>false');
  await f.run("mutateSelectedPendingTransfers('delete')");assert.equal(f.calls.length,0);
  f.run('window.confirm=()=>true;rebalanceState.pendingSelection.add(1)');
  const work=f.run("mutateSelectedPendingTransfers('revoke')");f.fail();await work;
  assert.equal(f.nodes['#transferPendingError'].textContent,'network');
  assert.equal(f.run('rebalanceState.pendingSelection.has(1)'),true);
  assert.equal(f.run('rebalanceState.busy'),false);
});

test('approved table contains every proposal column and renders frozen coverage including zero',()=>{
  const headers=id=>[...html.match(new RegExp('<table id="'+id+'"[\\s\\S]*?<thead>([\\s\\S]*?)</thead>'))[1].matchAll(/<th(?:\s[^>]*)?>(.*?)<\/th>/g)].map(m=>m[1]);
  const approved=headers('transferPendingTable');
  for(const heading of headers('balanceProposalTable'))assert.ok(approved.includes(heading),heading);
  const run=context();
  const markup=run(`transferPendingRow({id:1,quantity:12,cartons:1,source_consumer_price:120,destination_consumer_price:100,approval_context:{source_position:112,destination_position:0,source_before_days:56,source_after_days:50,destination_before_days:0,destination_after_days:6}})`);
  assert.equal((markup.match(/<td>/g)||[]).length,approved.length);
  assert.match(markup,/56 → 50/);assert.match(markup,/0 → 6/);assert.match(markup,/>0<\/td>/);assert.match(markup,/120 \/ 100/);
  assert.match(run('transferPendingRow({id:1,quantity:12,cartons:1})'),/اطلاعات زمان تأیید این قلم قدیمی ثبت نشده است/);
});
test('explicit issue submits only visible selected ids and retries without duplicate documents',async()=>{
  const f=pendingFixture(),work=f.run('issueSelectedTransfers()');
  await f.run('issueSelectedTransfers()');assert.equal(f.calls.length,1);
  assert.deepEqual(JSON.parse(f.calls[0].body).request_ids,[1]);
  f.fail();await work;assert.equal(f.nodes['#transferPendingError'].textContent,'network');
  const retry=f.run('issueSelectedTransfers()');
  assert.equal(JSON.parse(f.calls[0].body).request_id,JSON.parse(f.calls[1].body).request_id);
  f.finish();await retry;assert.equal(f.run('rebalanceState.stage'),'documents');
  assert.equal(f.run('rebalanceState.issueRetry'),null);
});
test('delete pending is guarded, cancelled confirmation is harmless, and issued rows cannot be removed',async()=>{
  const f=pendingFixture();f.run('window.confirm=()=>false');await f.run('deletePendingTransfer(1)');assert.equal(f.calls.length,0);
  f.run('window.confirm=()=>true;rebalanceState.requests[0].issued_document_id=1');await f.run('deletePendingTransfer(1)');assert.equal(f.calls.length,0);
  f.run('rebalanceState.requests[0].issued_document_id=null');const work=f.run('deletePendingTransfer(1)');
  assert.equal(f.calls[0].method,'DELETE');assert.match(f.calls[0].url,/requests\/1$/);f.finish();await work;
});
test('staging is flat, selectable and deletable while issued lines leave staging',()=>{
  const f=fixture();f.run("rebalanceState.stage='requests';rebalanceState.requests=[{id:1,product_code:'PENDING',product_name:'item',source:'tehran',destination:'karaj',cartons:1},{id:2,product_code:'ISSUED',source:'tehran',destination:'karaj',issued_document_id:3,cartons:1}];renderTransferRequests()");
  const markup=f.nodes['#transferPendingRows'].innerHTML;
  assert.match(markup,/PENDING/);assert.doesNotMatch(markup,/ISSUED/);assert.match(markup,/data-pending-selected/);assert.match(markup,/data-pending-delete="1"/);
  assert.match(f.nodes['#transferRequestRows'].innerHTML,/TR-000003/);
  assert.equal(f.nodes['#balanceRequestPanel'].hidden,false);assert.equal(f.nodes['#balanceDocumentsPanel'].hidden,true);
});

test('revoke confirmation is explicit, guarded and uses a separate action',async()=>{
  const f=pendingFixture();
  assert.match(f.run('transferPendingRow(rebalanceState.requests[0])'),/data-pending-revoke="1"/);
  f.run('window.confirm=()=>false');await f.run('revokePendingTransfer(1)');assert.equal(f.calls.length,0);
  f.run('window.confirm=()=>true;rebalanceState.requests[0].issued_document_id=1');await f.run('revokePendingTransfer(1)');assert.equal(f.calls.length,0);
  f.run('rebalanceState.requests[0].issued_document_id=null');const work=f.run('revokePendingTransfer(1)');
  assert.equal(f.calls[0].method,'POST');assert.match(f.calls[0].url,/requests\/1\/revoke$/);f.finish();await work;
});

test('delete document returns to its confirmed route and hides deletion for reflected documents',async()=>{
  const f=pendingFixture();f.run("rebalanceState.stage='documents';rebalanceState.requests[0].issued_document_id=3");
  assert.match(f.run('transferDocumentActions(transferDocuments(rebalanceState.requests)[0])'),/data-transfer-document-delete="3"/);
  f.run('window.confirm=()=>false');await f.run("deleteTransferDocument('3')");assert.equal(f.calls.length,0);
  f.run('window.confirm=()=>true');const work=f.run("deleteTransferDocument('3')");
  assert.match(f.calls[0].url,/documents\/3$/);assert.equal(f.calls[0].method,'DELETE');
  f.finish();await work;assert.equal(f.run('rebalanceState.stage'),'requests');assert.equal(f.run('rebalanceState.direction'),'tehran-karaj');
  assert.doesNotMatch(f.run("transferDocumentActions({key:'4',number:'TR-4',reflected:1})"),/data-transfer-document-delete/);
});

test('failed document delete stays in documents and shows a visible error',async()=>{
  const f=pendingFixture();f.run("rebalanceState.stage='documents';rebalanceState.requests[0].issued_document_id=3");
  const work=f.run("deleteTransferDocument('3')");f.fail();await work;
  assert.equal(f.run('rebalanceState.stage'),'documents');assert.equal(f.nodes['#transferRequestStatus'].textContent,'network');
});

test('new row actions have compact nonwrapping widths rather than taller rows',()=>{
  const css=readFileSync('app/static/warehouse-operations.css','utf8');
  assert.match(html,/data-user-column-width="150">عملیات/);
  assert.match(html,/data-user-column-width="230">عملیات/);
  assert.match(css,/:is\(#transferPendingTable,#transferDocumentsTable\) button\{white-space:nowrap/);
  assert.match(css,/#transferDocumentsTable td\{white-space:nowrap;overflow:hidden;text-overflow:ellipsis/);
});

test('live ERP lifecycle overrides prior sent status and keeps original voucher number',()=>{
  const run=context();
  run("row={issued_document_id:1,credit_status:'sent',credit_result_json:'{\"VocherNo\":68}',quantity:24,cartons:1}");
  for(const [status,text] of [['confirmed','در راه مقصد'],['unconfirmed','متوقف'],['missing','یافت نشد'],['changed','مغایرت'],['unknown','بازخوانی'],[null,'بازخوانی']]){
    run(`row.erp_status=${JSON.stringify(status)};d=transferDocuments([row])[0]`);
    assert.equal(run('d.erp_voucher_no'),68);
    assert.match(run('transferDocumentStatus(d)'),new RegExp(text));
    assert.doesNotMatch(run('transferDocumentNote(d)'),/سند ورانگر نیست/);
    assert.match(run('transferDocumentNote(d)'),/68/);
    if(status!=='confirmed')assert.doesNotMatch(run('transferDocumentStatus(d)'),/در راه مقصد/);
  }
  assert.match(run("transferDocumentStatus({key:'1',lines:[{}],reflected:0})"),/آماده ثبت در ورانگر/);
});

test('missing ERP document permits return only before destination receipt',()=>{
  const run=context({has:()=>true});run("d={key:'1',number:'TR-000001',credit_status:'sent',erp_status:'missing',reflected:0}");
  assert.match(run('transferDocumentActions(d)'),/data-transfer-document-return/);
  assert.doesNotMatch(run('transferDocumentActions(d)'),/data-transfer-document-delete/);
  for(const status of ['confirmed','unconfirmed','changed','unknown',null]){
    run(`d.erp_status=${JSON.stringify(status)}`);assert.doesNotMatch(run('transferDocumentActions(d)'),/data-transfer-document-return/);
  }
  run("d.erp_status='missing';d.reflected=1");assert.doesNotMatch(run('transferDocumentActions(d)'),/data-transfer-document-return/);
});

test('return action is hidden without transfer permission',()=>{
  const run=context({has:()=>false});
  assert.doesNotMatch(run("transferDocumentActions({key:'1',credit_status:'sent',erp_status:'missing',reflected:0})"),/data-transfer-document-return/);
});

test('confirmed ERP still needs source reflection in the exact current snapshot before destination reconciliation',()=>{
  const run=context({has:()=>true});
  for(const proof of [{},{source_stock_status:'review',source_stock_snapshot_id:20},{source_stock_status:'reflected',source_stock_snapshot_id:19}]){
    const markup=run(`transferLineRow({id:4,credit_status:'sent',erp_status:'confirmed',snapshot_id:1,current_snapshot_id:20,...${JSON.stringify(proof)}})`);
    assert.match(markup,/data-balance-reflect="4" disabled/);
  }
  const current=run("transferLineRow({id:4,credit_status:'sent',erp_status:'confirmed',snapshot_id:1,current_snapshot_id:20,source_stock_status:'reflected',source_stock_snapshot_id:20})");
  assert.doesNotMatch(current,/data-balance-reflect="4" disabled/);
});

test('newer snapshot never enables destination reconciliation for an unconfirmed or missing credit',()=>{
  const run=context({has:()=>true});
  for(const erp_status of ['unknown','missing','changed','unconfirmed',null]){
    const markup=run(`transferLineRow({id:4,credit_status:'sent',erp_status:${JSON.stringify(erp_status)},snapshot_id:1,current_snapshot_id:20})`);
    assert.match(markup,/data-balance-reflect="4" disabled/);
    assert.doesNotMatch(markup,/در راه مقصد/);
  }
});

test('return from ERP deletion requires explicit user action and preserves staging route',async()=>{
  const f=pendingFixture();f.run("has=()=>true;rebalanceState.stage='documents';Object.assign(rebalanceState.requests[0],{issued_document_id:3,credit_status:'sent',erp_status:'missing',erp_voucher_no:68})");
  f.run('window.confirm=()=>false');await f.run("returnTransferDocument('3')");assert.equal(f.calls.length,0);
  f.run('window.confirm=()=>true');const work=f.run("returnTransferDocument('3')");
  assert.match(f.nodes['#transferRequestStatus'].textContent,/خودکار/);
  await f.run("returnTransferDocument('3')");assert.equal(f.calls.length,1);
  assert.match(f.calls[0].url,/documents\/3\/return-to-approved$/);assert.equal(f.calls[0].method,'POST');
  f.finish();await work;assert.equal(f.run('rebalanceState.stage'),'requests');assert.equal(f.run('rebalanceState.direction'),'tehran-karaj');
});

test('document recovery action is explicit and can wrap inside saved narrow action columns',()=>{
  const f=fixture();f.run("has=()=>true;rebalanceState.stage='documents';rebalanceState.requests=[{id:1,issued_document_id:3,source:'tehran',destination:'karaj',credit_status:'sent',erp_status:'missing'}];renderTransferRequests()");
  assert.match(f.nodes['#transferRequestRows'].innerHTML,/<td class="transfer-document-actions">/);
  assert.match(f.nodes['#transferRequestRows'].innerHTML,/حذف سند و بازگشت اقلام/);
  const css=readFileSync('app/static/warehouse-operations.css','utf8');
  assert.match(css,/td\.transfer-document-actions\{white-space:normal;overflow:visible/);
});

test('blocked recovery displays inline error in the open document and allows another attempt',async()=>{
  const f=pendingFixture();
  f.run("has=()=>true;transferCreditMessage=message=>$('#transferCreditMessage').textContent=message;rebalanceState.stage='documents';rebalanceState.openDocument='3';$('#transferDocumentDialog').open=true;Object.assign(rebalanceState.requests[0],{issued_document_id:3,credit_status:'sent',erp_status:'missing',erp_voucher_no:68})");
  const work=f.run("returnTransferDocument('3')");f.fail();await work;
  assert.equal(f.nodes['#transferCreditMessage'].textContent,'network');assert.equal(f.nodes['#transferDocumentDialog'].open,true);
  assert.equal(f.run('rebalanceState.openDocument'),'3');assert.equal(f.run('rebalanceState.busy'),false);
  assert.match(f.run('transferDocumentActions(transferDocuments(rebalanceState.requests)[0])'),/data-transfer-document-return/);
});
