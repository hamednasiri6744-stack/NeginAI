// Supplier proposals are reviewed inside the warehouse; only an explicit decision applies them.
const supplierReviewState={order:null,busy:false,request:0,opener:null};
function supplierReviewContent(order){
  const pending=order.status==='submitted';
  const dateChanged=Boolean(order.proposed_delivery_date&&order.proposed_delivery_date!==order.requested_delivery_date);
  const changed=order.lines.filter(line=>Number(line.original_cartons)!==Number(line.proposed_cartons));
  const statuses={submitted:'منتظر تأیید شما',draft:'پاسخ هنوز توسط تأمین‌کننده ارسال نشده',awaiting_supplier:'منتظر پاسخ تأمین‌کننده',accepted:'تأیید شده؛ در صف تحویل',changes_requested:'برگشت به تأمین‌کننده برای اصلاح',rejected:'پاسخ رد شده',cancelled:'لغو شده'};
  return `<p class="supplier-review-notice">${esc(statuses[order.status]||order.status)}${pending?'؛ تعداد و تاریخ فعلی تا تأیید شما تغییر نمی‌کند.':''}</p>
    ${dateChanged?`<div class="supplier-review-dates"><div>تاریخ تحویل قبلی<strong dir="ltr">${esc(order.requested_delivery_date||'—')}</strong></div><div>تاریخ تحویل پیشنهادی<strong dir="ltr">${esc(order.proposed_delivery_date)}</strong><small>${pending?'منتظر تأیید شما':'پیشنهاد ثبت‌شده'}</small></div></div>`:''}
    ${changed.length?`<p>تغییر تعداد: ${fa(changed.length)} قلم${pending?' · منتظر تأیید شما':''}</p>`:'<p>تعداد کالاها تغییری نکرده است.</p>'}
    ${order.supplier_comment?`<p>توضیح تأمین‌کننده: ${esc(order.supplier_comment)}</p>`:''}
    ${changed.length?`<div class="supplier-review-table" tabindex="0" role="region" aria-label="فقط اقلام تغییرکرده"><table><thead><tr><th>کد کالا</th><th>نام کالا</th><th>عدد در کارتن</th><th>کارتن قبلی</th><th>کارتن پیشنهادی</th><th>اختلاف کارتن</th><th>عدد قبلی</th><th>عدد پیشنهادی</th><th>توضیح</th></tr></thead><tbody>${changed.map(line=>{
      const before=Number(line.original_cartons),after=Number(line.proposed_cartons),delta=after-before,rate=Number(line.conversion_rate)||1;
      return `<tr${delta?' class="supplier-review-changed"':''}><td>${esc(line.product_code)}</td><td>${esc(line.product_name)}</td><td>${fa(rate)}</td><td>${fa(before)}</td><td>${fa(after)}</td><td>${delta?`${delta>0?'افزایش':'کاهش'} ${fa(Math.abs(delta))}`:'بدون تغییر'}</td><td>${fa(before*rate)}</td><td>${fa(after*rate)}</td><td>${esc(line.supplier_note||'—')}</td></tr>`;
    }).join('')}</tbody></table></div>`:''}
    ${order.manager_comment?`<p>آخرین نظر انبار: ${esc(order.manager_comment)}</p>`:''}`;
}
function renderSupplierReview(order){
  supplierReviewState.order=order;
  $('#supplierReviewTitle').textContent=`بررسی پاسخ تأمین‌کننده · ${order.document.number}`;
  $('#supplierReviewSummary').textContent=`${order.document.supplier} · ${order.document.warehouse_name}`;
  $('#supplierReviewContent').innerHTML=supplierReviewContent(order);
  $('#supplierReviewDecision').hidden=order.status!=='submitted';
  $('#supplierReviewConfirm').checked=false;
  $('#supplierReviewComment').value='';
}
async function openSupplierReview(id,opener=null){
  if(supplierReviewState.busy)return;
  const request=++supplierReviewState.request;
  supplierReviewState.order=null;supplierReviewState.opener=opener;
  $('#supplierReviewTitle').textContent='بررسی پاسخ تأمین‌کننده';
  $('#supplierReviewSummary').textContent='';$('#supplierReviewError').textContent='';
  $('#supplierReviewContent').textContent='در حال دریافت پاسخ تأمین‌کننده…';
  $('#supplierReviewDecision').hidden=true;
  if(!$('#supplierReviewDialog').open)$('#supplierReviewDialog').showModal();
  try{
    const order=await api(`/warehouse-assistant/api/supplier-portal/orders/${id}`);
    if(request!==supplierReviewState.request||!$('#supplierReviewDialog').open)return;
    renderSupplierReview(order);
  }catch(error){if(request===supplierReviewState.request){$('#supplierReviewContent').textContent='';$('#supplierReviewError').textContent=error.message}}
}
async function decideSupplierReview(decision){
  const order=supplierReviewState.order;
  if(supplierReviewState.busy||!order||order.status!=='submitted')return;
  const comment=$('#supplierReviewComment').value.trim();
  if(decision==='accept'&&!$('#supplierReviewConfirm').checked){$('#supplierReviewError').textContent='برای اعمال تغییرات، تأیید بررسی تاریخ و تعدادها را علامت بزنید.';return}
  if(decision==='changes_requested'&&!comment){$('#supplierReviewError').textContent='علت برگشت برای اصلاح را بنویسید.';return}
  supplierReviewState.busy=true;$('#supplierReviewError').textContent='';
  document.querySelectorAll('[data-supplier-decision]').forEach(button=>button.disabled=true);
  $('#supplierReviewClose').disabled=true;
  try{
    const result=await api(`/warehouse-assistant/api/supplier-portal/orders/${order.id}/decision`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,expected_revision:order.revision,manager_comment:comment})});
    supplierReviewState.order=null;
    $('#supplierReviewDecision').hidden=true;
    $('#supplierReviewDialog').close();
    toast(decision==='accept'?'تغییرات تأیید شد؛ سفارش به صف تحویل رفت.':'پاسخ برای اصلاح به تأمین‌کننده برگشت؛ تعداد و تاریخ فعلی حفظ شد.');
    try{await Promise.all([loadFulfillmentOrders(),loadOrders(),loadAutomaticPreorders()])}
    catch{ toast('تصمیم ثبت شد، اما بازخوانی جدول انجام نشد؛ جدول سفارش‌ها را بازخوانی کنید.',true); }
    if(!supplierReviewState.opener?.isConnected)$('#refreshFulfillmentButton')?.focus?.();
  }catch(error){
    $('#supplierReviewError').textContent=error.message;
    // Do not retry a possibly committed decision with the same stale display.
    supplierReviewState.order=null;$('#supplierReviewDecision').hidden=true;
    const retry=document.createElement('button');retry.type='button';retry.textContent='بازخوانی پاسخ و وضعیت';
    retry.onclick=()=>openSupplierReview(order.id,supplierReviewState.opener);
    $('#supplierReviewContent').append(retry);
  }finally{
    supplierReviewState.busy=false;$('#supplierReviewClose').disabled=false;
    document.querySelectorAll('[data-supplier-decision]').forEach(button=>button.disabled=false);
  }
}
document.addEventListener('DOMContentLoaded',()=>{
  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-supplier-review]');
    if(button)openSupplierReview(Number(button.dataset.supplierReview),button);
  });
  $('#supplierReviewClose').addEventListener('click',()=>{if(!supplierReviewState.busy)$('#supplierReviewDialog').close()});
  $('#supplierReviewDialog').addEventListener('cancel',event=>{if(supplierReviewState.busy)event.preventDefault()});
  $('#supplierReviewDialog').addEventListener('close',()=>{supplierReviewState.request++;supplierReviewState.order=null;(supplierReviewState.opener?.isConnected?supplierReviewState.opener:$('#refreshFulfillmentButton'))?.focus()});
  document.querySelectorAll('[data-supplier-decision]').forEach(button=>button.addEventListener('click',()=>decideSupplierReview(button.dataset.supplierDecision)));
});
