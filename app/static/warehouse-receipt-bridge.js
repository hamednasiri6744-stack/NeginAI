const receiptBridge={sequence:0,doc:null,preview:null,pending:false,completed:false,busy:false,locked:false};
function receiptDocuments(result){
  try{return result?.PriceWorkflowVersion===2?JSON.parse(result.DocumentsJson):[]}catch{return []}
}
function receiptDocumentSummary(result){
  const names={confirmed_receipt:'رسید تأییدشده',unpriced_receipt:'رسید فاقد قیمت، تأییدنشده',price_reserve:'رزرو بابت تغییر قیمت'};
  return receiptDocuments(result).map(d=>`${names[d.Role]||'سند'}: ${fa(d.VocherNo)}`).join(' · ');
}

function receiptMessage(message,kind='info'){
  $('#checkbarReceiptStatus').textContent=message;
  $('#checkbarReceiptProgress').textContent=message;
  $('#checkbarReceiptProgress').hidden=!message;
  if(typeof checkbarNotice==='function'&&message)checkbarNotice(kind,message);
}

function receiptActionLabel(){
  $('#checkbarTransfer').textContent=receiptBridge.busy?'در حال بررسی نتیجه…':receiptBridge.preview?'تأیید و ارسال رسید به ورانگر':$('#checkbarReceiptPanel').hidden?'آماده‌سازی رسید ورانگر':'بررسی آمادگی ارسال به ورانگر';
}

async function advanceCheckbarReceipt(){
  if(!receiptBridge.doc||receiptBridge.busy||receiptBridge.pending||receiptBridge.completed||receiptBridge.locked)return;
  if($('#checkbarReceiptPanel').hidden){
    $('#checkbarReceiptPanel').hidden=false;
    receiptMessage('هنوز رسیدی ارسال نشده است. تاریخ و شماره سند عطف را بررسی کنید و سپس «بررسی آمادگی ارسال به ورانگر» را بزنید.');
    receiptActionLabel();$('#checkbarReceiptDate').focus();return;
  }
  if(receiptBridge.preview)return submitCheckbarReceipt();
  return previewCheckbarReceipt();
}

function resetCheckbarReceipt(){
  if(typeof resetOrderMatching==='function')resetOrderMatching();
  receiptBridge.sequence++;receiptBridge.doc=null;receiptBridge.preview=null;receiptBridge.pending=false;receiptBridge.busy=false;
  receiptBridge.completed=false;receiptBridge.locked=false;
  $('#checkbarTransfer').hidden=true;$('#checkbarReceiptPanel').hidden=true;
  $('#checkbarReceiptSubmit').hidden=true;$('#checkbarReceiptReconcile').hidden=true;
  $('#checkbarReceiptLines').innerHTML='';$('#checkbarReceiptStatus').textContent='';
  $('#checkbarReceiptProgress').textContent='';$('#checkbarReceiptProgress').hidden=true;
  $('#checkbarReceiptHistory').textContent='';
  $('#checkbarReceiptTableWrap').hidden=true;$('#checkbarReceiptTitle').textContent='رسید انبار در ورانگر';
  receiptActionLabel();
  $('#checkbarMatchingPrepare').hidden=true;
}

function receiptBridgeState(data){
  if(typeof matchingTransferState==='function')matchingTransferState(data);
  const sent=data.status==='sent',pending=data.status==='pending';
  receiptBridge.completed=sent;
  receiptBridge.locked=!!data.receipt?.locked||sent||pending;
  receiptBridge.pending=pending;receiptBridge.preview=null;
  $('#checkbarReceiptPriceHint').hidden=receiptBridge.locked;
  $('#checkbarReceiptTableWrap').hidden=true;
  $('#checkbarReceiptSubmit').hidden=true;$('#checkbarReceiptReconcile').hidden=!pending||!has('warehouse.receipt.transfer');
  $('#checkbarReceiptFields').hidden=sent||pending;
  $('#checkbarReceiptPreview').hidden=sent||pending||!has('warehouse.receipt.transfer');
  $('#checkbarEdit').disabled=receiptBridge.locked;$('#checkbarDelete').disabled=receiptBridge.locked;
  $('#checkbarReceiptRefresh').hidden=!sent&&!pending&&!data.transfer_history?.length&&!data.receipt?.locked;
  $('#checkbarReceiptHistory').textContent=(data.transfer_history||[]).map(r=>`سند قبلی ${fa(r.result.VocherNo)} · نسخه ${fa(r.revision)} · حذف‌شده در ورانگر`).join(' | ');
  if(sent){
    state.suggestions=null;state.automaticPreview=null;
    if(typeof loadFulfillmentOrders==='function')loadFulfillmentOrders().catch(()=>{});
    if(typeof loadInventory==='function')loadInventory(true).catch(()=>{});
    $('#checkbarTransfer').hidden=true;$('#checkbarReceiptPanel').hidden=false;
    $('#checkbarReceiptStatus').textContent=receiptDocumentSummary(data.result)||`سند ورانگر شماره ${fa(data.receipt?.number||data.result.VocherNo)} · نسخهٔ چک‌بار ${fa(data.revision)} · ${data.receipt?.confirmed?'تأییدشده':'ثبت‌شده'}. تا زمان وجود سند ورانگر، اصلاح و حذف چک‌بار قفل است.`;
  }else if(pending){
    $('#checkbarTransfer').hidden=true;$('#checkbarReceiptPanel').hidden=false;
    $('#checkbarReceiptStatus').textContent=data.result?.Message||'نتیجهٔ انتقال در انتظار پیگیری است. همان درخواست پیگیری می‌شود.';
  }else if(data.status==='rejected'){
    $('#checkbarReceiptPanel').hidden=false;$('#checkbarReceiptStatus').textContent=data.result?.Message||'رسید ثبت نشد؛ اطلاعات را بررسی کنید.';
  }
  if(data.receipt?.state==='deleted'){
    receiptBridge.completed=false;receiptBridge.locked=false;
    $('#checkbarReceiptPanel').hidden=false;$('#checkbarTransfer').hidden=!has('warehouse.receipt.transfer')||!!receiptBridge.doc?.deleted;
    receiptMessage(`سند ورانگر شماره ${fa(data.receipt.number)} حذف شده است. می‌توانید چک‌بار را اصلاح یا حذف کنید، یا پس از بررسی دوباره رسید بسازید. سابقهٔ سند قبلی حفظ می‌شود.`,'info');
  }else if(['unknown','review'].includes(data.receipt?.state)){
    $('#checkbarReceiptPanel').hidden=false;$('#checkbarTransfer').hidden=true;
    receiptMessage(`وضعیت سند ورانگر${data.receipt.number?' شماره '+fa(data.receipt.number):''} قطعی نیست؛ تا بررسی موفق، چک‌بار قفل می‌ماند.`,'error');
  }
  if(['sent','pending','rejected'].includes(data.status)&&!['deleted','unknown','review'].includes(data.receipt?.state))receiptMessage($('#checkbarReceiptStatus').textContent,sent?'success':pending?'info':'error');
  if(receiptBridge.locked)$('#checkbarReceiptProgress').hidden=true;
  if(typeof updateCheckbarArchiveReceipt==='function'&&receiptBridge.doc)updateCheckbarArchiveReceipt(receiptBridge.doc.id,data);
  receiptActionLabel();
}

async function refreshCheckbarReceipt(doc){
  resetCheckbarReceipt();receiptBridge.doc=doc;const seq=receiptBridge.sequence;
  if(doc.worksheet_workflow&&!doc.receipt_confirmed){receiptBridge.locked=false;$('#checkbarEdit').disabled=false;$('#checkbarDelete').disabled=false;return}
  $('#checkbarMatchingPrepare').hidden=true;
  if(doc.receipt_confirmed&&doc.order_matching)renderOrderMatching(doc.order_matching,true);
  $('#checkbarTransfer').hidden=!!doc.deleted||!has('warehouse.receipt.transfer');
  $('#checkbarTransfer').disabled=true;
  receiptBridge.locked=true;$('#checkbarEdit').disabled=true;$('#checkbarDelete').disabled=true;
  $('#checkbarReceiptDate').value=doc.metadata?.date||'';
  $('#checkbarReceiptReference').value=doc.metadata?.reference_no||'';$('#checkbarReceiptComment').value=(doc.metadata?.note||'').slice(0,220);
  $('#checkbarReceiptFields').hidden=false;$('#checkbarReceiptPreview').hidden=false;
  try{
    const data=await api(`/warehouse-assistant/api/checkbars/${doc.id}/receipt-transfer`,{cache:'no-store'});
    if(seq!==receiptBridge.sequence)return;
    receiptBridgeState(data);
    if(!data.enabled&&data.status!=='sent'&&data.status!=='pending'&&!['deleted','unknown','review'].includes(data.receipt?.state))receiptMessage('پل رسید هنوز روی سرور فعال نشده است. اطلاعات محلی را می‌توانید بررسی کنید.');
  }catch(error){
    if(seq!==receiptBridge.sequence)return;
    $('#checkbarReceiptPanel').hidden=false;receiptMessage('وضعیت انتقال خوانده نشد؛ برای بررسی، چک‌بار را دوباره باز کنید.','error');
    $('#checkbarReceiptRefresh').hidden=false;
    return;
  }
  if(seq===receiptBridge.sequence)$('#checkbarTransfer').disabled=false;
}

function receiptInput(){
  return {expected_revision:receiptBridge.doc.revision||0,
    voucher_date:normalizeSearchText($('#checkbarReceiptDate').value),
    reference_no:normalizeSearchText($('#checkbarReceiptReference').value).trim(),comment:$('#checkbarReceiptComment').value};
}

function receiptBusy(value){
  receiptBridge.busy=value;checkbarState.submitting=value;
  for(const id of ['checkbarReceiptPreview','checkbarReceiptSubmit','checkbarReceiptReconcile','checkbarTransfer'])$('#'+id).disabled=value;
  for(const id of ['checkbarEdit','checkbarDelete'])$('#'+id).disabled=value||receiptBridge.locked;
  for(const id of ['checkbarReceiptDate','checkbarReceiptReference','checkbarReceiptComment'])$('#'+id).disabled=value;
  if(typeof orderMatchingState!=='undefined'){
    document.querySelectorAll('[data-matching-row]').forEach(input=>input.disabled=value||receiptBridge.pending||receiptBridge.completed||!!receiptBridge.doc?.receipt_confirmed);
    for(const id of ['checkbarMatchingConfirmed','checkbarMatchingExtra','checkbarMatchingReload'])$('#'+id).disabled=value||receiptBridge.pending||receiptBridge.completed||!!receiptBridge.doc?.receipt_confirmed;
  }
  receiptActionLabel();
}

async function previewCheckbarReceipt(){
  if(!receiptBridge.doc||receiptBridge.busy||receiptBridge.pending||receiptBridge.locked)return;
  const seq=receiptBridge.sequence,request=receiptInput(),id=receiptBridge.doc.id;
  if(typeof orderMatchingRequest==='function'){
    try{Object.assign(request,orderMatchingRequest())}
    catch(error){receiptMessage(error.message,'error');return}
  }
  if(!/^[0-9]{1,10}$/.test(request.reference_no)||Number(request.reference_no)<1||Number(request.reference_no)>2147483647){
    receiptBridge.preview=null;$('#checkbarReceiptSubmit').hidden=true;
    receiptMessage('شمارهٔ سند عطف تأمین‌کننده الزامی است؛ عدد صحیح مثبت وارد کنید.','error');
    $('#checkbarReceiptReference').focus();return;
  }
  receiptBridge.preview=null;$('#checkbarReceiptSubmit').hidden=true;receiptBusy(true);
  receiptMessage('در حال بررسی اطلاعات اجباری در ورانگر… هنوز رسیدی ارسال نشده است.');
  try{
    const data=await api(`/warehouse-assistant/api/checkbars/${id}/receipt-preview`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
    if(seq!==receiptBridge.sequence)return;
    if(['sent','pending'].includes(data.status)){receiptBridgeState(data);return}
    $('#checkbarReceiptLines').innerHTML=(data.payload?.lines||[]).map(line=>`<tr><td>${fa(line.source_row)}</td><td>${esc(line.product_code)}</td><td>${esc(line.manufacturer_product_code||'—')}</td><td>${esc(line.barcode||'—')}</td><td>${esc(line.group_level3||'—')}</td><td>${fa(line.quantity)}</td><td><span dir="ltr">${esc(line.item_comment)}</span>${line.price_mode?`<small>${({changed:'رسید تأییدشده + رزرو تغییر قیمت',unchanged:'رسید تأییدشده',unpriced:'رسید جدا، تأییدنشده'})[line.price_mode]||''}</small>`:''}</td></tr>`).join('');
    $('#checkbarReceiptTableWrap').hidden=!data.payload?.lines?.length;
    const zeros=data.payload?.zero_rows||[];
    $('#checkbarReceiptStatus').textContent=(data.result?.Message||'')+(zeros.length?`\nردیف‌های ${zeros.map(fa).join('، ')} تعداد صفر دارند و وارد رسید نمی‌شوند؛ در چک‌بار حفظ می‌شوند.`:'');
    if(data.status==='ready'){
      $('#checkbarReceiptStatus').textContent+=`\n${receiptBridge.doc.supplier} · ${receiptBridge.doc.warehouse_name} · سال مالی ${fa(data.result.AccYear)} · شناسه تأمین‌کننده ${fa(data.result.SupplierRef)} · شماره سند عطف ${fa(request.reference_no)}`;
      receiptBridge.priceWorkflow=data.payload?.price_workflow_version===2;
      receiptBridge.preview={...request,preview_token:data.preview_token,validation_token:data.result.ValidationToken};
      $('#checkbarReceiptSubmit').hidden=!data.commit_enabled;
      if(!data.commit_enabled)$('#checkbarReceiptStatus').textContent+='\nبررسی موفق بود؛ امکان ارسال هنوز روی سرور فعال نشده است.';
      else $('#checkbarReceiptStatus').textContent+='\nآمادهٔ ارسال است؛ برای ساخت رسید، «تأیید و ارسال رسید به ورانگر» را بزنید.';
      // A successful read-only preview must not enable the footer commit action.
      if(!data.commit_enabled)receiptBridge.preview=null;
    }
    receiptMessage($('#checkbarReceiptStatus').textContent||'بررسی موفق نبود و رسیدی ارسال نشد؛ اطلاعات رسید را بررسی کنید.',data.status==='ready'?'info':'error');
  }catch(error){if(seq===receiptBridge.sequence)receiptMessage(error.message,'error')}
  finally{if(seq===receiptBridge.sequence)receiptBusy(false)}
}

async function submitCheckbarReceipt(reconcile=false){
  if(receiptBridge.busy||!receiptBridge.doc||(!reconcile&&(!receiptBridge.preview||receiptBridge.locked)))return;
  if(!reconcile&&!confirm(receiptBridge.priceWorkflow?`اسناد چک‌بار ${receiptBridge.doc.number} طبق پیش‌نمایش ثبت شوند؟ اقلام قیمت‌دار تأیید و اقلام تغییرقیمت‌دار رزرو می‌شوند؛ اقلام فاقد قیمت در رسید جدا و تأییدنشده می‌مانند.`:`از چک‌بار ${receiptBridge.doc.number} یک رسید انبار سالم تأییدنشده در ورانگر ساخته شود؟ ردیف‌های صفر وارد رسید نمی‌شوند.`))return;
  const seq=receiptBridge.sequence,id=receiptBridge.doc.id,payload=receiptBridge.preview;
  receiptBusy(true);receiptBridge.preview=null;$('#checkbarReceiptSubmit').hidden=true;
  try{
    const options={method:'POST',headers:{'Content-Type':'application/json'}};
    if(!reconcile)options.body=JSON.stringify(payload);
    const data=await api(`/warehouse-assistant/api/checkbars/${id}/receipt-${reconcile?'reconcile':'transfer'}`,options);
    if(seq!==receiptBridge.sequence)return;
    receiptBridgeState(data);
  }catch(error){
    if(seq!==receiptBridge.sequence)return;
    // Even after an HTTP error, query status before offering a new transfer.
    try{
      const status=await api(`/warehouse-assistant/api/checkbars/${id}/receipt-transfer`);
      if(seq!==receiptBridge.sequence)return;
      receiptBridgeState(status);
    }
    catch{if(seq===receiptBridge.sequence)receiptBridgeState({status:'pending',result:{Message:'پاسخ انتقال دریافت نشد؛ پیگیری انتقال را بزنید.'}})}
    if(seq===receiptBridge.sequence&&!receiptBridge.pending&&!receiptBridge.completed)receiptMessage(error.message,'error');
  }finally{if(seq===receiptBridge.sequence)receiptBusy(false)}
}

document.addEventListener('DOMContentLoaded',()=>{
  $('#checkbarReceiptRefresh').addEventListener('click',()=>{if(receiptBridge.doc&&!receiptBridge.busy)refreshCheckbarReceipt(receiptBridge.doc)});
  $('#checkbarTransfer').addEventListener('click',advanceCheckbarReceipt);
  $('#checkbarReceiptPreview').addEventListener('click',previewCheckbarReceipt);
  $('#checkbarReceiptSubmit').addEventListener('click',()=>submitCheckbarReceipt());
  $('#checkbarReceiptReconcile').addEventListener('click',()=>submitCheckbarReceipt(true));
  for(const id of ['checkbarReceiptDate','checkbarReceiptReference','checkbarReceiptComment'])$('#'+id).addEventListener('input',()=>{
    receiptBridge.preview=null;$('#checkbarReceiptSubmit').hidden=true;
    receiptActionLabel();
    if(!receiptBridge.busy)receiptMessage('اطلاعات رسید تغییر کرد؛ پیش از ارسال دوباره بررسی کنید. هنوز ارسال جدیدی انجام نشده است.');
  });
});
