// Physical checkbar rows stay intact; allocations only divide their counted quantity.
const orderMatchingState={plan:null,loading:false,sequence:0,documentId:null,draftSignature:null};
function resetOrderMatching(){
  orderMatchingState.sequence++;orderMatchingState.plan=null;orderMatchingState.loading=false;orderMatchingState.documentId=null;orderMatchingState.draftSignature=null;
  $('#checkbarMatching').hidden=true;$('#checkbarMatchingRows').innerHTML='';
  $('#checkbarMatching').open=false;
  $('#checkbarMatchingConfirmed').checked=false;$('#checkbarMatchingExtra').checked=false;
}
function matchingDraftSignature(){
  return JSON.stringify({source:checkbarState.source&&{warehouse:checkbarState.source.warehouse,supplier:checkbarState.source.supplier,expected_token:checkbarState.source.expected_token},lines:checkbarState.lines,editing:checkbarState.editing,
    metadata:[...document.querySelectorAll('[data-checkbar-meta]')].map(input=>[input.dataset.checkbarMeta,input.value])});
}
function invalidateDraftOrderMatching(){
  if(checkbarState.saved||checkbarState.pending)return;
  const button=$('#checkbarMatchingPrepare');if(button)button.hidden=!checkbarState.source||(typeof checkbarDraftStage==='function'&&checkbarDraftStage())||(typeof checkbarSkipMatching==='function'&&checkbarSkipMatching());
  if(orderMatchingState.draftSignature&&orderMatchingState.draftSignature!==matchingDraftSignature()){
    resetOrderMatching();$('#checkbarMatchingSummary').textContent='اطلاعات تغییر کرده است؛ تطبیق سفارش‌ها را دوباره بررسی کنید.';
  }
}
async function refreshFulfillmentAfterCheckbar(){
  state.suggestions=null;state.automaticPreview=null;
  const jobs=[];
  if(typeof loadFulfillmentOrders==='function')jobs.push(loadFulfillmentOrders());
  if(typeof loadInventory==='function')jobs.push(loadInventory(true));
  await Promise.allSettled(jobs);
}
function matchingAmounts(){
  return [...document.querySelectorAll('[data-matching-row]')].map(input=>{
    const value=normalizeSearchText(input.value).replace(/[,٬]/g,'');
    if(!/^\d+(?:\.\d{1,3})?$/.test(value)||!Number.isFinite(Number(value)))throw Error('مقدار تخصیص باید عدد غیرمنفی با حداکثر سه رقم اعشار باشد.');
    return {source_row:Number(input.dataset.matchingRow),preorder_id:Number(input.dataset.matchingOrder),quantity:Number(value)};
  });
}
function matchingRemainders(plan,allocations){
  return plan.rows.map(row=>{
    const total=allocations.filter(a=>a.source_row===row.source_row).reduce((sum,a)=>sum+Math.round(a.quantity*1000),0);
    return {...row,unallocated_qty:(Math.round(Number(row.actual_qty)*1000)-total)/1000};
  });
}
function updateMatchingSummary(){
  try{
    const rows=matchingRemainders(orderMatchingState.plan,matchingAmounts());
    if(rows.some(r=>r.unallocated_qty<0))throw Error('جمع تخصیص از تعداد شمارش‌شده بیشتر است.');
    const extras=rows.filter(r=>r.unallocated_qty>0);
    $('#checkbarMatchingSummary').textContent=extras.length?extras.map(r=>`${r.product_code}: ${fa(r.unallocated_qty)} عدد اضافه بر تخصیص سفارش`).join(' · '):'تمام تعداد شمارش‌شده به سفارش‌های در راه تخصیص یافته است.';
    $('#checkbarMatchingExtraLabel').hidden=!extras.length;
    return extras.length>0;
  }catch(error){$('#checkbarMatchingSummary').textContent=error.message;return null}
}
function renderOrderMatching(plan,readonly=false){
  if(plan.skipped){resetOrderMatching();return;}
  orderMatchingState.plan=plan;$('#checkbarMatching').hidden=false;
  $('#checkbarMatchingRemainingHeading').textContent=readonly?'مانده پیش از این دریافت':'مانده فعلی سفارش';
  $('#checkbarMatchingRows').innerHTML=plan.rows.map(row=>{
    const orders=row.orders.length?row.orders:[null];
    return orders.map((order,index)=>`<tr><td>${index?'':fa(row.source_row)}</td><td>${index?'':esc(row.product_code)}</td><td>${index?'':esc(row.manufacturer_product_code||'—')}</td><td>${index?'':esc(row.barcode||'—')}</td><td>${index?'':esc(row.product_name)}</td><td>${index?'':esc(row.group_level3||'—')}</td><td>${index?'':fa(row.actual_qty)}</td><td>${order?esc(order.number):'بدون سفارش باز'}</td><td>${order?fa(order.remaining_qty):'—'}${order?.reserved_qty?`<small>رزرو انتقال: ${fa(order.reserved_qty)}</small>`:''}</td><td>${order?`<input type="text" inputmode="decimal" value="${plan.allocations.find(a=>a.source_row===row.source_row&&a.preorder_id===order.preorder_id)?.quantity||0}" data-matching-row="${row.source_row}" data-matching-order="${order.preorder_id}" aria-label="تخصیص ردیف ${row.source_row} به سفارش ${esc(order.number)}" ${readonly?'disabled':''}>`:'۰'}</td></tr>`).join('');
  }).join('');
  for(const id of ['checkbarMatchingConfirmed','checkbarMatchingExtra','checkbarMatchingReload'])$('#'+id).disabled=readonly;
  $('#checkbarMatchingConfirmed').checked=readonly;$('#checkbarMatchingExtra').checked=readonly;
  updateMatchingSummary();
}
async function loadOrderMatching(){
  $('#checkbarMatching').open=true;
  const draft=!!checkbarState.source&&!checkbarState.saved;
  if(orderMatchingState.loading||receiptBridge.busy||receiptBridge.pending||checkbarState.pending)return;
  if(draft)return loadDraftOrderMatching();
  if(!receiptBridge.doc)return;
  if(receiptBridge.doc.receipt_confirmed){renderOrderMatching(receiptBridge.doc.order_matching,true);return;}
  const seq=++orderMatchingState.sequence,doc=receiptBridge.doc;
  orderMatchingState.loading=true;orderMatchingState.plan=null;receiptBridge.preview=null;
  $('#checkbarReceiptSubmit').hidden=true;$('#checkbarMatching').hidden=false;
  $('#checkbarMatchingSummary').textContent='در حال تطبیق با تمام سفارش‌های باز همین انبار و تأمین‌کننده…';
  $('#checkbarMatchingRows').innerHTML='';$('#checkbarMatchingConfirmed').checked=false;$('#checkbarMatchingExtra').checked=false;
  try{
    const plan=await api(`/warehouse-assistant/api/checkbars/${doc.id}/order-matching`);
    if(seq!==orderMatchingState.sequence||receiptBridge.doc?.id!==doc.id)return;
    orderMatchingState.documentId=doc.id;renderOrderMatching(plan);
  }catch(error){if(seq===orderMatchingState.sequence)$('#checkbarMatchingSummary').textContent=error.message}
  finally{if(seq===orderMatchingState.sequence)orderMatchingState.loading=false}
}
async function loadDraftOrderMatching(){
  $('#checkbarMatching').open=true;
  if(checkbarState.submitting||checkbarState.pending||checkbarImportPending())return;
  if(checkbarState.lines.some(line=>checkbarActual(line)===null)){await issueCheckbar();return;}
  let payload;
  try{payload=checkbarIssuePayload()}catch(error){checkbarNotice('error',error.message,true);return}
  const seq=++orderMatchingState.sequence,signature=matchingDraftSignature();
  orderMatchingState.loading=true;orderMatchingState.plan=null;orderMatchingState.draftSignature=signature;
  $('#checkbarMatching').hidden=false;$('#checkbarMatchingSummary').textContent='در حال بررسی همهٔ سفارش‌های در راه این تأمین‌کننده…';
  $('#checkbarMatchingRows').innerHTML='';$('#checkbarMatchingConfirmed').checked=false;
  try{
    const plan=await api('/warehouse-assistant/api/checkbars/matching-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(seq!==orderMatchingState.sequence||signature!==matchingDraftSignature())return;
    renderOrderMatching(plan);orderMatchingState.documentId=checkbarState.editing?.id||null;
    $('#checkbarMatching').scrollIntoView?.({block:'nearest'});
  }catch(error){if(seq===orderMatchingState.sequence)$('#checkbarMatchingSummary').textContent=error.message}
  finally{if(seq===orderMatchingState.sequence)orderMatchingState.loading=false}
}
function orderMatchingRequest(forDraft=false){
  if(!forDraft&&receiptBridge.doc?.receipt_confirmed)return {};
  if(!orderMatchingState.plan||orderMatchingState.loading||(forDraft?orderMatchingState.draftSignature!==matchingDraftSignature():orderMatchingState.documentId!==receiptBridge.doc?.id))throw Error('ابتدا «بررسی و تطبیق سفارش‌های در راه» را بزنید؛ پس از تغییر اطلاعات، تطبیق باید دوباره انجام شود.');
  const extra=updateMatchingSummary();
  if(extra===null)throw Error('مقدارهای تخصیص را اصلاح کنید.');
  if(!$('#checkbarMatchingConfirmed').checked)throw Error('تعداد شمارش‌شده و تقسیم آن بین سفارش‌ها را تأیید کنید.');
  if(extra&&!$('#checkbarMatchingExtra').checked)throw Error('تحویل اضافه بر سفارش یا بدون سفارش را تأیید کنید.');
  return {allocations:matchingAmounts(),allocation_revision:orderMatchingState.plan.revision,...(forDraft?{}:{matching_confirmed:true}),accept_unallocated:!!extra};
}
function matchingTransferState(data){
  if(['sent','pending'].includes(data.status)&&data.order_matching)renderOrderMatching(data.order_matching,true);
}
document.addEventListener('DOMContentLoaded',()=>{
  $('#checkbarMatchingPrepare').addEventListener('click',loadOrderMatching);
  $('#checkbarTransfer').addEventListener('click',loadOrderMatching);
  $('#checkbarMatchingReload').addEventListener('click',loadOrderMatching);
  $('#checkbarMatchingRows').addEventListener('input',()=>{
    receiptBridge.preview=null;$('#checkbarReceiptSubmit').hidden=true;
    $('#checkbarMatchingConfirmed').checked=false;$('#checkbarMatchingExtra').checked=false;updateMatchingSummary();
  });
  for(const id of ['checkbarMatchingConfirmed','checkbarMatchingExtra'])$('#'+id).addEventListener('change',()=>{receiptBridge.preview=null;$('#checkbarReceiptSubmit').hidden=true});
});
