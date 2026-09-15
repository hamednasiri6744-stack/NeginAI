const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {readFileSync}=require('node:fs');
const source=readFileSync('app/static/warehouse-transfer-bridge.js','utf8');
function fixture(){
  const nodes=new Proxy({},{get:(t,k)=>t[k]??(t[k]={checked:false,hidden:false,disabled:false,textContent:'',close(){this.closed=true}})});
  const calls=[];let resolve,reject,lastSent;
  const context=vm.createContext({$:s=>nodes[s],document:{addEventListener(){}},fa:String,has:()=>true,toast(){},
    rebalanceState:{openDocument:'1',busy:false},loadTransferRequests:async()=>{},openTransferDocument(){},syncTransferRegistrationButtons(){},readTransferData:url=>context.api(url),
    api:(url,options)=>{calls.push({url,options});if(!options&&lastSent)return Promise.resolve({...lastSent,erp:{status:'confirmed',voucher_no:lastSent.result?.VocherNo}});return new Promise((a,b)=>{resolve=a;reject=b})}});
  vm.runInContext(source,context);
  return {nodes,calls,run:s=>vm.runInContext(s,context),finish:r=>{if(r.status==='sent')lastSent=r;resolve(r)},fail:()=>reject(new Error('offline'))};
}
test('opening a document only reads status and disabled bridge cannot post',async()=>{
  const f=fixture(),work=f.run("loadTransferCredit('1')");
  assert.equal(f.calls[0].options,undefined);f.finish({status:'not_sent',enabled:false,commit_enabled:false});await work;
  await f.run("runTransferCredit('preview')");assert.equal(f.calls.length,1);
  assert.match(f.nodes['#transferCreditMessage'].textContent,/نصب و فعال نشده/);
});
test('successful preflight still requires explicit confirmation before final posting',async()=>{
  const f=fixture();f.run("transferCreditState.key='1';transferCreditState.status={status:'not_sent',enabled:true,commit_enabled:true}");
  const preview=f.run("runTransferCredit('preview')");f.finish({payload:{voucher_date:'1405/06/22',lines:[{}]},preview_token:'local',validation_token:'sql'});await preview;
  await f.run("runTransferCredit('submit')");assert.equal(f.calls.length,1);
  f.nodes['#transferCreditConfirmed'].checked=true;
  const submit=f.run("runTransferCredit('submit')");
  await f.run("runTransferCredit('submit')");assert.equal(f.calls.length,2);
  assert.deepEqual(JSON.parse(f.calls[1].options.body),{preview_token:'local',validation_token:'sql',confirmed:true});
  f.finish({status:'sent',result:{VocherNo:71}});await submit;
  assert.match(f.nodes['#transferCreditMessage'].textContent,/71/);assert.equal(f.nodes['#transferCreditSubmit'].hidden,true);
});
test('lost result exposes only same-request retry, not a new submit',async()=>{
  const f=fixture();f.run("transferCreditState.key='1';transferCreditState.status={status:'not_sent',enabled:true,commit_enabled:true};transferCreditState.preview={preview_token:'local',validation_token:'sql'}");
  f.nodes['#transferCreditConfirmed'].checked=true;
  const work=f.run("runTransferCredit('submit')");f.fail();await work;
  assert.equal(f.nodes['#transferCreditRetry'].hidden,false);assert.equal(f.nodes['#transferCreditSubmit'].hidden,true);
  const retry=f.run("runTransferCredit('retry')");assert.match(f.calls[1].url,/\/credit\/retry$/);assert.equal(f.calls[1].options.body,undefined);
  f.finish({status:'sent',result:{VocherNo:71}});await retry;
});
test('late status response never belongs to another document',async()=>{
  const f=fixture();const work=f.run("loadTransferCredit('1')");f.run("rebalanceState.openDocument='2'");f.finish({status:'sent',result:{VocherNo:99}});await work;
  assert.equal(f.run('transferCreditState.status'),null);
});

test('fresh successful preflight replaces the previous rejection message',async()=>{
  const f=fixture();f.run("transferCreditState.key='1';transferCreditState.status={status:'rejected',enabled:true,commit_enabled:true,result:{Message:'old rejection'}}");
  const work=f.run("runTransferCredit('preview')");
  f.finish({payload:{voucher_date:'1405/06/22',lines:[{}]},preview_token:'local',validation_token:'sql'});await work;
  assert.match(f.nodes['#transferCreditMessage'].textContent,/بررسی موفق/);
  assert.equal(f.nodes['#transferCreditSubmit'].hidden,false);
});

test('reserve exclusion refreshes remaining lines and requires a new preview',async()=>{
  const f=fixture();f.run("transferCreditState.key='1';transferCreditState.status={status:'not_sent',enabled:true,commit_enabled:true};transferCreditState.preview={preview_token:'old'}");
  const work=f.run("runTransferCredit('preview')");
  f.finish({status:'stock_excluded',excluded_items:[{product_code:'00123',product_name:'کالا <b>',requested_quantity:12,on_hand_quantity:2,reserved_quantity:20,shortage_quantity:10}],remaining_item_count:1,document_deleted:false,message:'نیازمند آزادسازی رزرو'});
  await work;
  assert.equal(f.run('transferCreditState.preview'),null);
  assert.equal(f.nodes['#transferCreditSubmit'].hidden,true);
  assert.equal(f.nodes['#transferCreditIssues'].hidden,false);
  assert.equal(f.nodes['#transferCreditIssues'].open,true);
  assert.match(f.nodes['#transferCreditIssuesText'].textContent,/00123 · کالا <b>/);
  assert.match(f.nodes['#transferCreditMessage'].textContent,/دوباره بررسی کنید/);
  await f.run("runTransferCredit('submit')");assert.equal(f.calls.length,1);
});

test('empty document closes and returns to approved items after reserve rejection',async()=>{
  const f=fixture();f.run("transferCreditState.key='1';transferCreditState.status={status:'not_sent',enabled:true,commit_enabled:true}");
  const work=f.run("runTransferCredit('preview')");
  f.finish({status:'stock_excluded',excluded_items:[{product_code:'00123',product_name:'کالا'}],remaining_item_count:0,document_deleted:true,message:'نیازمند آزادسازی رزرو'});
  await work;
  assert.equal(f.nodes['#transferDocumentDialog'].closed,true);
  assert.equal(f.run('rebalanceState.openDocument'),null);
  assert.equal(f.run('rebalanceState.stage'),'requests');
  assert.match(f.nodes['#transferPendingError'].textContent,/آزادسازی رزرو/);
  assert.equal(f.calls.length,1);
});

test('prior successful registration never claims current confirmation without a live ERP check',()=>{
  const f=fixture();
  for(const status of ['unconfirmed','missing','changed','unknown',null]){
    f.run(`transferCreditState.status={status:'sent',enabled:true,commit_enabled:true,result:{VocherNo:68},erp:{status:${JSON.stringify(status)}}};renderTransferCredit()`);
    assert.match(f.nodes['#transferCreditMessage'].textContent,/68/);
    assert.doesNotMatch(f.nodes['#transferCreditMessage'].textContent,/ثبت و تأیید شد/);
    assert.equal(f.nodes['#transferCreditSubmit'].hidden,true);
    assert.equal(f.nodes['#transferCreditRetry'].hidden,true);
    assert.equal(f.nodes['#transferCreditRefresh'].hidden,false);
  }
});

test('explicit refresh reads current ERP lifecycle without posting or resubmitting credit',async()=>{
  const f=fixture();f.run("transferCreditState.key='1';transferCreditState.status={status:'sent',result:{VocherNo:68}};rebalanceState.requests=[{issued_document_id:1,credit_status:'sent',erp_status:'confirmed'}]");
  const work=f.run("loadTransferCredit('1',{refresh:true})");
  assert.match(f.calls[0].url,/\/credit\/refresh$/);assert.equal(f.calls[0].options.method,'POST');assert.equal(f.calls[0].options.body,undefined);
  f.finish({status:'sent',result:{VocherNo:68},erp:{status:'unconfirmed',voucher_no:68,checked_at:'now'}});await work;
  assert.equal(f.run('rebalanceState.requests[0].erp_status'),'unconfirmed');
  assert.match(f.nodes['#transferCreditMessage'].textContent,/لغو شده/);
  await f.run("runTransferCredit('retry')");assert.equal(f.calls.length,1);
});

test('failed live refresh reports unknown rather than deleted or still confirmed',async()=>{
  const f=fixture();f.run("transferCreditState.key='1';transferCreditState.status={status:'sent',result:{VocherNo:68},erp:{status:'confirmed'}};rebalanceState.requests=[{issued_document_id:1,credit_status:'sent',erp_status:'confirmed'}]");
  const work=f.run("loadTransferCredit('1',{refresh:true})");f.fail();await work;
  assert.equal(f.run('rebalanceState.requests[0].erp_status'),'unknown');
  assert.equal(f.nodes['#transferCreditReturn'].hidden,true);
  assert.match(f.nodes['#transferCreditMessage'].textContent,/قابل دریافت نیست/);
});

test('first successful submit immediately loads current ERP status without overwriting it with stale preview data',async()=>{
  const f=fixture();
  f.run("transferCreditState.key='1';transferCreditState.status={status:'not_sent',enabled:true,commit_enabled:true,erp:null};transferCreditState.preview={preview_token:'local',validation_token:'sql'};rebalanceState.requests=[{issued_document_id:1,credit_status:'not_sent',erp_status:null}]");
  f.nodes['#transferCreditConfirmed'].checked=true;
  const work=f.run("runTransferCredit('submit')");f.finish({status:'sent',result:{VocherNo:68}});await work;
  assert.equal(f.calls.length,2);assert.match(f.calls[1].url,/\/credit$/);assert.equal(f.calls[1].options,undefined);
  assert.equal(f.run('rebalanceState.requests[0].erp_status'),'confirmed');assert.equal(f.run('rebalanceState.requests[0].erp_voucher_no'),68);
  assert.match(f.nodes['#transferCreditMessage'].textContent,/68 · تأییدشده/);
  assert.equal(f.nodes['#transferCreditSubmit'].hidden,true);assert.equal(f.nodes['#transferCreditRetry'].hidden,true);
});
