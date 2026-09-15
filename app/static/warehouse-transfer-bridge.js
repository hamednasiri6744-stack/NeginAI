// ERP writes are explicit, permission-gated, and never run while opening a document.
const transferCreditState={key:null,sequence:0,busy:false,preview:null,status:null,uncertain:false};
function transferCreditMessage(value){$('#transferCreditMessage').textContent=value||''}
function transferCreditErpMessage(data){
  const erp=data.erp||{},number=erp.voucher_no??data.result?.VocherNo??'—',prefix='بستانکار ورانگر '+number+' · ';
  const messages={confirmed:'تأییدشده؛ دریافت مقصد را جداگانه تطبیق دهید.',unconfirmed:'تأیید لغو شده؛ تأیید همان سند را در ورانگر پیگیری کنید.',missing:'یافت نشد؛ احتمال حذف وجود دارد. پس از بررسی و در صورت نبود دریافت مقصد، اقلام را به تأییدشده‌ها برگردانید.',changed:'اطلاعات سند تغییر کرده؛ مغایرت را بررسی و اصلاح کنید.',unknown:'وضعیت فعلی قابل دریافت نیست؛ بازخوانی کنید.'};
  return prefix+(messages[erp.status]||'قبلاً ثبت شده؛ وضعیت فعلی هنوز بازخوانی نشده است.');
}
function syncTransferCreditRows(key,data){
  if(!Array.isArray(rebalanceState.requests))return;
  const erp=data.erp||{};
  for(const row of rebalanceState.requests){
    if(String(row.issued_document_id)!==String(key))continue;
    row.credit_status=data.status;
    if(data.result)row.credit_result_json=JSON.stringify(data.result);
    row.erp_status=erp.status||null;row.erp_message=erp.message||'';row.erp_checked_at=erp.checked_at||null;row.erp_voucher_no=erp.voucher_no??data.result?.VocherNo??null;
  }
  if(typeof renderTransferRequests==='function')renderTransferRequests();
  if(rebalanceState.openDocument===key)openTransferDocument(key,{refreshCredit:false});
}
function renderTransferStockIssues(items=[]){
  $('#transferCreditIssues').hidden=!items.length;
  $('#transferCreditIssuesCount').textContent=fa(items.length)+' قلم کنارگذاشته‌شده از سند؛ هماهنگی آزادسازی رزرو';
  $('#transferCreditIssuesText').textContent=items.map(r=>r.product_code+' · '+r.product_name+' — تعداد سند: '+fa(r.requested_quantity)+'؛ موجودی آزاد: '+fa(r.on_hand_quantity)+'؛ رزرو: '+fa(r.reserved_quantity)+'؛ کمبود آزاد: '+fa(r.shortage_quantity)+' عدد').join('\n');
}
function renderTransferCredit(){
  const s=transferCreditState,data=s.status||{},permitted=typeof has==='function'&&has('warehouse.receipt.transfer');
  const known=data.status||'not_sent',uncertain=s.uncertain||known==='pending'||known==='blocked';
  $('#transferCreditPreview').hidden=!permitted||uncertain||known==='sent';
  $('#transferCreditPreview').disabled=s.busy||!data.enabled;
  $('#transferCreditSubmit').hidden=!permitted||!s.preview||uncertain||known==='sent';
  $('#transferCreditConfirmation').hidden=$('#transferCreditSubmit').hidden;
  $('#transferCreditSubmit').disabled=s.busy||!data.commit_enabled||!$('#transferCreditConfirmed').checked;
  $('#transferCreditRetry').hidden=!permitted||!uncertain;
  $('#transferCreditRetry').disabled=s.busy||!data.commit_enabled;
  $('#transferCreditRefresh').hidden=known!=='sent';$('#transferCreditRefresh').disabled=s.busy;
  const documentRows=(rebalanceState.requests||[]).filter(r=>String(r.issued_document_id)===String(s.key));
  $('#transferCreditReturn').hidden=!permitted||known!=='sent'||data.erp?.status!=='missing'||!documentRows.length||documentRows.some(r=>r.reflected_at);
  $('#transferCreditReturn').disabled=s.busy;
  $('#transferCreditConfirmed').disabled=s.busy;
  renderTransferStockIssues(data.stock_exclusions||[]);
  if(known==='sent')transferCreditMessage(transferCreditErpMessage(data)+(data.inventory_message?' '+data.inventory_message:''));
  else if(uncertain)transferCreditMessage(data.result?.Message||'نتیجهٔ ثبت نیازمند پیگیری است؛ سند را دوباره نسازید.');
  else if(!data.enabled)transferCreditMessage('پل بستانکار هنوز نصب و فعال نشده است. سند داخلی تغییری نکرده است.');
  else if(known==='rejected'&&!s.preview)transferCreditMessage(data.result?.Message||'ثبت برگشت خورد؛ اطلاعات را دوباره بررسی کنید.');
}
async function loadTransferCredit(key,{refresh=false}={}){
  const previous=transferCreditState.key===key?transferCreditState.status:null;
  const seq=++transferCreditState.sequence;
  Object.assign(transferCreditState,{key,busy:true,preview:null,status:null,uncertain:false});
  $('#transferCreditConfirmed').checked=false;renderTransferCredit();transferCreditMessage('در حال خواندن وضعیت ثبت…');
  try{
    const path='/warehouse-assistant/api/interwarehouse/documents/'+encodeURIComponent(key)+'/credit';
    const data=await (refresh?api(path+'/refresh',{method:'POST'}):readTransferData(path));
    if(seq!==transferCreditState.sequence||rebalanceState.openDocument!==key)return;
    transferCreditState.status=data;syncTransferCreditRows(key,data);transferCreditMessage('ثبت بستانکار، موجودی مبدأ را کم می‌کند؛ به معنی دریافت مقصد نیست.');
  }catch(error){if(seq===transferCreditState.sequence){
    if(previous?.status==='sent'){transferCreditState.status={...previous,erp:{status:'unknown',voucher_no:previous.erp?.voucher_no??previous.result?.VocherNo,message:error.message}};syncTransferCreditRows(key,transferCreditState.status)}
    transferCreditMessage('وضعیت دریافت نشد: '+error.message);$('#transferCreditRefresh').hidden=false;$('#transferCreditRefresh').disabled=false;
  }}
  finally{if(seq===transferCreditState.sequence){transferCreditState.busy=false;if(transferCreditState.status)renderTransferCredit()}}
}
async function runTransferCredit(action){
  const s=transferCreditState,key=s.key;
  if(s.busy||rebalanceState.busy||!key||rebalanceState.openDocument!==key||!s.status||!has('warehouse.receipt.transfer'))return;
  if(s.status.status==='sent')return;
  if(action==='submit'&&(!s.preview||!s.status.commit_enabled||!$('#transferCreditConfirmed').checked))return;
  if(action==='preview'&&!s.status.enabled)return;
  if(action==='retry'&&!s.status.commit_enabled)return;
  s.busy=true;rebalanceState.busy=true;renderTransferCredit();transferCreditMessage(action==='preview'?'در حال بررسی سند…':'در حال ثبت یا پیگیری بستانکار…');
  try{
    const options={method:'POST'};
    if(action==='submit'){options.headers={'Content-Type':'application/json'};options.body=JSON.stringify({preview_token:s.preview.preview_token,validation_token:s.preview.validation_token,confirmed:true})}
    const result=await api('/warehouse-assistant/api/interwarehouse/documents/'+encodeURIComponent(key)+'/credit/'+action,options);
    if(result.excluded_items?.length){
      s.preview=null;s.uncertain=false;$('#transferCreditConfirmed').checked=false;
      s.status={...s.status,status:result.status==='rejected'?'rejected':'not_sent',result:result.result,stock_exclusions:result.stock_exclusions||result.excluded_items};
      // Keep the rejection notice visible after the remaining rows refresh.
      if(s.status.result)s.status.result={...s.status.result,Message:result.message};
      if(result.document_deleted){
        $('#transferDocumentDialog').close();rebalanceState.openDocument=null;
        rebalanceState.stage='requests';rebalanceState.direction='all';rebalanceState.requestWarehouse='all';
      }
      await loadTransferRequests({refreshDocument:false});
      if(!result.document_deleted)openTransferDocument(key,{refreshCredit:false});
      transferCreditMessage(result.message+(result.document_deleted?' سند خالی از فهرست فعال خارج شد.':' اقلام باقی‌مانده را دوباره بررسی کنید.'));
      $('#transferPendingError').textContent=result.message;
      $('#transferCreditIssues').open=true;
      toast(fa(result.excluded_items.length)+' قلم نیازمند آزادسازی رزرو به تأییدشده‌ها برگشت.');
    }else if(action==='preview'){
      s.preview=result;$('#transferCreditConfirmed').checked=false;
      transferCreditMessage('بررسی موفق: '+result.payload.voucher_date+' · '+fa(result.payload.lines.length)+' قلم. ثبت و تأیید نهایی موجودی مبدأ را کم می‌کند.');
    }else{
      s.preview=null;s.uncertain=result.status==='pending'||result.status==='blocked';s.status={...s.status,...result};
      if(result.status==='sent')toast('بستانکار '+result.result.VocherNo+' ثبت و تأیید شد.');
      if(result.inventory_sync==='refresh_required')toast(result.inventory_message);
      // Refresh only local lists, not physical receiving or supplier orders.
      await loadTransferRequests({refreshDocument:false});
      if(result.status==='sent'){
        // Keep the posting lock until a fresh status read completes. A read failure
        // never turns a known successful write into an uncertain write/retry.
        try{s.status=await readTransferData('/warehouse-assistant/api/interwarehouse/documents/'+encodeURIComponent(key)+'/credit')}
        catch(error){s.status={...s.status,erp:{status:'unknown',voucher_no:result.result?.VocherNo,message:error.message}}}
        syncTransferCreditRows(key,s.status);
        if(result.inventory_sync==='refresh_required')s.status.inventory_message=result.inventory_message;
      }
      openTransferDocument(key,{refreshCredit:false});
    }
  }catch(error){
    if(action!=='preview'){s.uncertain=true;s.preview=null}
    transferCreditMessage(action==='preview'?error.message:'پاسخ ثبت دریافت نشد؛ «پیگیری ثبت» را بزنید. هیچ درخواست تازه‌ای نسازید.');
  }finally{s.busy=false;rebalanceState.busy=false;syncTransferRegistrationButtons();renderTransferCredit()}
}
document.addEventListener('DOMContentLoaded',()=>{
  $('#transferCreditPreview').addEventListener('click',()=>runTransferCredit('preview'));
  $('#transferCreditSubmit').addEventListener('click',()=>runTransferCredit('submit'));
  $('#transferCreditRetry').addEventListener('click',()=>runTransferCredit('retry'));
  $('#transferCreditRefresh').addEventListener('click',()=>{if(!transferCreditState.busy&&!rebalanceState.busy&&rebalanceState.openDocument)loadTransferCredit(rebalanceState.openDocument,{refresh:true})});
  $('#transferCreditReturn').addEventListener('click',()=>{if(!transferCreditState.busy&&rebalanceState.openDocument)returnTransferDocument(rebalanceState.openDocument)});
  $('#transferCreditConfirmed').addEventListener('change',renderTransferCredit);
});
