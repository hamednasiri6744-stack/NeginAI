// Inventory-first proposals. Reads do not reserve stock or change purchases.
const rebalanceState={proposal:null,busy:false,sequence:0,requests:[],direction:'tehran-karaj',stage:'proposals',retry:null,reflection:null,edits:new Map(),requestWarehouse:'all',pendingSelection:new Set(),issueRetry:null};
// Bound only reads. Never time out, cancel or automatically repeat an ERP write.
async function readTransferData(path){
  let timer;
  try{return await Promise.race([api(path),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('دریافت اطلاعات طول کشید؛ بازخوانی را بزنید. این پیام به معنی ناموفق‌بودن ثبت سند نیست.')),20000)})])}
  finally{clearTimeout(timer)}
}
function syncTransferRegistrationButtons(){
  document.querySelectorAll('#transferRequestRows [data-transfer-document-register]').forEach(button=>{
    button.disabled=rebalanceState.busy;
    button.title=rebalanceState.busy?'عملیات قبلی هنوز در حال تکمیل است.':'بررسی موجودی و تأیید نهایی پیش از ثبت';
  });
}
const transferCity=code=>({tehran:'تهران',karaj:'کرج',gilan:'گیلان'})[code]||'';
const transferRoute=r=>r.source+'-'+r.destination;
const transferDocumentKey=r=>String(r.issued_document_id);
function transferLineValue(r){const p=Number(r.estimated_unit_price);return Number.isFinite(p)&&p>0?p*Number(r.quantity):null}
function transferDocuments(rows){
  const groups=new Map();
  for(const r of rows){
    if(!r.issued_document_id)continue;
    const key=transferDocumentKey(r);
    if(!groups.has(key))groups.set(key,{key,number:'TR-'+String(r.issued_document_id).padStart(6,'0'),source:r.source,destination:r.destination,business_date:r.issued_document_date,created_at:r.issued_document_at,created_by:r.issued_document_by,credit_status:r.credit_status,erp_status:r.erp_status,erp_message:r.erp_message,erp_checked_at:r.erp_checked_at,erp_voucher_no:transferCreditNumber(r),lines:[],cartons:0,quantity:0,estimated_value:0,missing_prices:0,reflected:0});
    const d=groups.get(key),value=transferLineValue(r);d.lines.push(r);d.cartons+=Number(r.cartons)||0;d.quantity+=Number(r.quantity)||0;
    if(value===null)d.missing_prices++;else d.estimated_value+=value;
    if(r.reflected_at)d.reflected++;
  }
  return [...groups.values()];
}
function transferDocumentStatus(d){
  if(d.credit_status==='pending'||d.credit_status==='blocked')return 'ثبت بستانکار نیازمند پیگیری';
  if(d.credit_status==='sent'&&d.erp_status!=='confirmed')return ({unconfirmed:'متوقف؛ تأیید بستانکار در ورانگر لازم است',missing:d.reflected?'مغایرت سند خروج با دریافت مقصد':'سند خروج یافت نشد؛ بررسی و بازگشت اقلام',changed:'مغایرت سند ورانگر؛ نیازمند بررسی'})[d.erp_status]||'ثبت قبلی؛ وضعیت فعلی نیازمند بازخوانی';
  return d.reflected===d.lines.length?'دریافت و منعکس‌شده در موجودی':d.reflected?'بخشی دریافت‌شده؛ باقی در راه':d.credit_status==='sent'?'ارسال‌شده از مبدأ؛ در راه مقصد':d.key?'آماده ثبت در ورانگر':'تأییدشده؛ آماده ساخت سند';
}
function transferCreditNumber(r){if(r.erp_voucher_no!=null)return r.erp_voucher_no;try{return r.credit_status==='sent'?JSON.parse(r.credit_result_json||'null')?.VocherNo:null}catch{return null}}
function transferErpLabel(d){
  if(d.credit_status!=='sent')return ['pending','blocked'].includes(d.credit_status)?'در حال پیگیری ثبت':'ثبت نشده';
  return ({confirmed:'تأییدشده',unconfirmed:'تأیید لغو شده',missing:'یافت نشد؛ احتمال حذف',changed:'تغییر کرده؛ مغایرت',unknown:'وضعیت در دسترس نیست'})[d.erp_status]||'هنوز بازخوانی نشده';
}
function transferCanReturn(d){return d.credit_status==='sent'&&d.erp_status==='missing'&&!d.reflected}
function transferDocumentUnposted(d){return !d.reflected&&[null,undefined,'not_sent','rejected'].includes(d.credit_status)}
function transferCanRegister(d){return transferDocumentUnposted(d)&&typeof has==='function'&&has('warehouse.order.draft')&&has('warehouse.receipt.transfer')}
function transferDocumentNote(d){
  const value='مبلغ نمایش‌داده‌شده تخمینی و بر پایه قیمت خرید مبدأ هنگام تأیید است. ';
  if(d.credit_status==='sent')return value+'بستانکار ورانگر '+(d.erp_voucher_no??'—')+' · '+transferErpLabel(d)+'؛ رسید ورود مقصد جداگانه بررسی می‌شود.';
  return value+'این سند داخلی آماده ثبت بستانکار در ورانگر است.';
}
function transferDocumentValue(d){return d.missing_prices?'نامشخص · '+fa(d.missing_prices)+' قلم بدون قیمت':fa(d.estimated_value)}
function transferLineRow(r){
  const permitted=typeof has==='function'&&has('warehouse.receipt.transfer'),fresh=r.current_snapshot_id>r.snapshot_id&&r.source_stock_status==='reflected'&&r.source_stock_snapshot_id===r.current_snapshot_id,confirmed=r.credit_status==='sent'&&r.erp_status==='confirmed';
  const reason=!confirmed?'ابتدا وضعیت تأیید سند خروج ورانگر را بازخوانی کنید.':'ابتدا موجودی هر دو انبار را پس از انتقال کامل به‌روز کنید.';
  const action=r.reflected_at?'—':permitted?'<button type="button" data-balance-reflect="'+r.id+'" '+(fresh&&confirmed?'':'disabled title="'+reason+'"')+'>تطبیق دریافت مقصد</button>':'—';
  const value=transferLineValue(r);
  return '<tr>'+[esc(r.product_code),...['product_name','manufacturer','brand'].map(k=>'<span class="balance-product" title="'+esc(r[k]||'—')+'">'+esc(r[k]||'—')+'</span>'),fa(r.conversion_rate),fa(r.cartons),fa(r.quantity),value===null?'نامشخص':fa(r.estimated_unit_price),value===null?'نامشخص':fa(value),r.reflected_at?'دریافت و منعکس‌شده در موجودی':confirmed?'در انتظار دریافت مقصد':'در انتظار تأیید سند خروج',esc(r.source_document||transferCreditNumber(r)||'—'),esc(r.destination_document||'—'),action].map(x=>'<td>'+x+'</td>').join('')+'</tr>';
}
function openTransferDocument(key,{refreshCredit=true}={}){
  if(rebalanceState.busy&&refreshCredit)return;
  const d=transferDocuments(rebalanceState.requests).find(d=>d.key===key);if(!d)return;
  rebalanceState.openDocument=key;
  $('#transferDocumentTitle').textContent='سند جابه‌جایی '+d.number;
  $('#transferDocumentMeta').textContent=transferCity(d.source)+' به '+transferCity(d.destination)+' · '+d.business_date+' · '+(d.created_by||'');
  $('#transferDocumentSummary').textContent=fa(d.lines.length)+' قلم · '+fa(d.cartons)+' کارتن · '+fa(d.quantity)+' عدد · مبلغ تخمینی: '+transferDocumentValue(d)+' · '+transferDocumentStatus(d);
  $('#transferDocumentNote').textContent=transferDocumentNote(d);
  $('#transferDocumentLines').innerHTML=d.lines.map(transferLineRow).join('');
  const dialog=$('#transferDocumentDialog');if(!dialog.open)dialog.showModal();
  if(typeof fitTableWrapsToViewport==='function')fitTableWrapsToViewport();
  if(refreshCredit&&typeof loadTransferCredit==='function')loadTransferCredit(key);
}
function transferRequestId(){return typeof crypto.randomUUID==='function'?crypto.randomUUID():Array.from(crypto.getRandomValues(new Uint8Array(16)),value=>value.toString(16).padStart(2,'0')).join('')}
async function openTransferRegistration(key){
  const d=transferDocuments(rebalanceState.requests).find(d=>d.key===key);
  if(rebalanceState.busy){
    const message='عملیات قبلی هنوز در حال تکمیل است؛ پس از پایان، ثبت در ورانگر فعال می‌شود.';
    $('#transferRequestStatus').textContent=message;if(typeof toast==='function')toast(message);return;
  }
  if(!d||!transferCanRegister(d))return;
  // Entry into the registration flow only reads status; preflight and final posting stay explicit.
  openTransferDocument(key,{refreshCredit:false});
  $('#transferCreditControls').scrollIntoView({block:'nearest'});
  await loadTransferCredit(key);
  if(rebalanceState.openDocument!==key||!$('#transferDocumentDialog').open)return;
  const controls=$('#transferCreditControls'),preview=$('#transferCreditPreview');
  controls.scrollIntoView({block:'nearest'});
  (preview.hidden||preview.disabled?controls:preview).focus({preventScroll:true});
}
function balanceAfter(o,n){return {source:(o.source_position-n*o.conversion_rate)/o.source_daily_demand,destination:(o.destination_position+n*o.conversion_rate)/o.destination_daily_demand}}
function balanceProposalRow(o){
  const edit=rebalanceState.edits.get(o.product_code),n=edit?.value??o.available_cartons,a=balanceAfter(o,Number(n));
  const textCell=value=>'<span class="balance-product" title="'+esc(value||'—')+'">'+esc(value||'—')+'</span>';
  const cells=['<input type="checkbox" data-balance-selected aria-label="انتخاب '+esc(o.product_name)+'" '+(edit?.selected?'checked':'')+'>',esc(o.product_code),textCell(o.product_name),textCell(o.manufacturer),textCell(o.brand),fa(o.source_position),fa(o.destination_position)];
  const coverage=(before,after,side)=>'<td><bdi dir="ltr">'+fa(before)+' → <strong data-balance-after-'+side+'>'+fa(after)+'</strong></bdi></td>';
  return '<tr data-balance-code="'+esc(o.product_code)+'">'+cells.map(x=>'<td>'+x+'</td>').join('')+coverage(o.source_before_days,a.source,'source')+coverage(o.destination_before_days,a.destination,'destination')+
    '<td><input type="number" min="'+(o.minimum_cartons||1)+'" max="'+o.available_cartons+'" step="1" value="'+esc(n)+'" data-balance-cartons title="هر کارتن '+fa(o.conversion_rate)+' عدد؛ حداقل '+fa(o.minimum_cartons||1)+' کارتن" aria-label="جابه‌جایی '+esc(o.product_name)+' به کارتن">'+((o.minimum_cartons||1)>1?'<small class="balance-minimum">حداقل '+fa(o.minimum_cartons)+' کارتن</small>':'')+'</td>'+
    '<td>'+fa(o.source_consumer_price)+' / '+fa(o.destination_consumer_price)+'</td>'+
    '<td><button type="button" class="secondary-action" data-balance-accept aria-label="تأیید جابه‌جایی '+esc(o.product_name)+'">تأیید این قلم</button><span class="transfer-row-error" role="alert" data-balance-error></span></td></tr>';
}
function visibleBalanceRows(){return [...document.querySelectorAll('#balanceProposalRows tr[data-balance-code]')].filter(r=>!r.hidden&&r.style.display!=='none'&&!r.classList.contains('column-filtered-out'))}
function rememberBalanceRow(row){rebalanceState.edits.set(row.dataset.balanceCode,{value:row.querySelector('[data-balance-cartons]').value,selected:row.querySelector('[data-balance-selected]').checked})}
function updateBalanceSelection(){
  const rows=visibleBalanceRows(),selected=rows.filter(r=>r.querySelector('[data-balance-selected]').checked),all=$('#balanceSelectAll');
  all.checked=rows.length>0&&selected.length===rows.length;all.indeterminate=selected.length>0&&selected.length<rows.length;
  $('#balanceSelectionCount').textContent=fa(selected.length)+' قلم انتخاب‌شده از ردیف‌های نمایان';
  $('#acceptBalanceSelection').disabled=rebalanceState.busy||!selected.length;
}
function filteredTransferRequests(){return rebalanceState.requests.filter(r=>(rebalanceState.direction==='all'||transferRoute(r)===rebalanceState.direction)&&(rebalanceState.requestWarehouse==='all'||r.destination===rebalanceState.requestWarehouse))}
function transferPendingRow(r){
  const value=transferLineValue(r),selectable=!r.reflected_at;
  const context=r.approval_context;
  const captured=n=>n==null?'—':fa(n);
  const coverage=side=>context?'<bdi dir="ltr">'+captured(context[side+'_before_days'])+' → '+captured(context[side+'_after_days'])+'</bdi>':'<span title="اطلاعات زمان تأیید این قلم قدیمی ثبت نشده است">—</span>';
  const reserveNote=r.stock_exclusion_json?'<small class="transfer-row-error" title="در آخرین بررسی موجودی آزاد کافی نبود؛ پس از آزادسازی رزرو در ورانگر دوباره بررسی کنید.">نیازمند آزادسازی رزرو · بررسی مجدد هنگام ثبت</small>':'';
  return '<tr data-pending-id="'+r.id+'">'+[
    selectable?'<input type="checkbox" data-pending-selected aria-label="انتخاب '+esc(r.product_name)+'" '+(rebalanceState.pendingSelection.has(r.id)?'checked':'')+'>':'—',
    esc(r.product_code),...['product_name','manufacturer','brand'].map(k=>'<span class="balance-product" title="'+esc(r[k]||'—')+'">'+esc(r[k]||'—')+'</span>'),transferCity(r.source),transferCity(r.destination),
    captured(context?.source_position),captured(context?.destination_position),coverage('source'),coverage('destination'),
    fa(r.cartons),captured(r.source_consumer_price)+' / '+captured(r.destination_consumer_price),fa(r.quantity),value===null?'نامشخص':fa(value),esc(formatRefreshDate(r.created_at)),
    selectable?reserveNote+'<button type="button" data-pending-revoke="'+r.id+'" aria-label="عدم تأیید '+esc(r.product_name)+'">عدم تأیید</button> <button type="button" data-pending-delete="'+r.id+'" aria-label="حذف '+esc(r.product_name)+'">حذف</button>':'دریافت و منعکس‌شده در موجودی'
  ].map(x=>'<td>'+x+'</td>').join('')+'</tr>';
}
function visiblePendingRows(){return [...document.querySelectorAll('#transferPendingRows tr[data-pending-id]')].filter(r=>!r.hidden&&r.style.display!=='none'&&!r.classList.contains('column-filtered-out')&&r.querySelector('[data-pending-selected]'))}
function selectedPendingIds(){return visiblePendingRows().filter(r=>r.querySelector('[data-pending-selected]').checked).map(r=>Number(r.dataset.pendingId)).sort((a,b)=>a-b)}
function updatePendingSelection(){
  const rows=visiblePendingRows(),ids=selectedPendingIds(),all=$('#transferPendingSelectAll');
  all.checked=rows.length>0&&ids.length===rows.length;all.indeterminate=ids.length>0&&ids.length<rows.length;
  $('#transferPendingSelectionCount').textContent=fa(ids.length)+' قلم انتخاب‌شده از ردیف‌های نمایان';
  $('#createTransferDocuments').disabled=rebalanceState.busy||!ids.length;
  $('#revokeSelectedTransfers').disabled=rebalanceState.busy||!ids.length;
  $('#deleteSelectedTransfers').disabled=rebalanceState.busy||!ids.length;
}
async function mutateSelectedPendingTransfers(action){
  if(rebalanceState.busy||!['delete','revoke'].includes(action))return;
  const ids=selectedPendingIds();
  if(!ids.length)return;
  if(ids.length>500){$('#transferPendingError').textContent='حداکثر ۵۰۰ قلم را در هر نوبت انتخاب کنید.';return}
  const label=action==='delete'?'حذف':'عدم تأیید';
  if(!window.confirm(label+' '+fa(ids.length)+' قلم انتخاب‌شدهٔ نمایان؟ رزرو جابه‌جایی آزاد می‌شود. برای پیشنهاد خرید تازه، محاسبه سفارش را دوباره انجام دهید.'))return;
  return mutatePendingTransfer(async()=>{
    await api('/warehouse-assistant/api/interwarehouse/requests/batch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_ids:ids,action})});
    ids.forEach(id=>rebalanceState.pendingSelection.delete(id));
    toast(label+' انتخاب‌شده‌ها انجام شد؛ رزرو جابه‌جایی آزاد شد.');await loadTransferRequests();
  });
}
async function mutatePendingTransfer(action){
  if(rebalanceState.busy)return;
  rebalanceState.busy=true;$('#transferPendingError').textContent='';
  const controls=[...$('#transfersView').querySelectorAll('button,input,select')],disabled=controls.map(x=>x.disabled);controls.forEach(x=>x.disabled=true);
  try{await action()}catch(error){
    $('#transferPendingError').textContent=error.message;$('#transferRequestStatus').textContent=error.message;
    if(rebalanceState.openDocument&&$('#transferDocumentDialog').open&&typeof transferCreditMessage==='function')transferCreditMessage(error.message);
  }
  finally{rebalanceState.busy=false;controls.forEach((x,i)=>x.disabled=disabled[i]);syncTransferRegistrationButtons();updatePendingSelection()}
}
async function issueSelectedTransfers(){
  const ids=selectedPendingIds();if(!ids.length||rebalanceState.busy)return;
  if(ids.length>500){$('#transferPendingError').textContent='حداکثر ۵۰۰ قلم را در هر نوبت انتخاب کنید.';return}
  const signature=JSON.stringify(ids);
  if(rebalanceState.issueRetry?.signature!==signature)rebalanceState.issueRetry={signature,id:transferRequestId()};
  return mutatePendingTransfer(async()=>{
    const result=await api('/warehouse-assistant/api/interwarehouse/documents',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_ids:ids,request_id:rebalanceState.issueRetry.id})});
    rebalanceState.issueRetry=null;ids.forEach(id=>rebalanceState.pendingSelection.delete(id));rebalanceState.stage='documents';rebalanceState.direction='all';rebalanceState.requestWarehouse='all';
    toast(fa(result.documents.length)+' سند جابه‌جایی به تاریخ امروز و به تفکیک مسیر ساخته شد.');await loadTransferRequests();
  });
}
async function deletePendingTransfer(id){
  const row=rebalanceState.requests.find(r=>r.id===id);
  if(rebalanceState.busy||!row||row.issued_document_id||row.reflected_at)return;
  if(!window.confirm('حذف '+row.product_name+' از جابه‌جایی‌های تأییدشده؟ رزرو آن آزاد می‌شود. برای پیشنهاد خرید تازه، محاسبه سفارش را دوباره انجام دهید.'))return;
  return mutatePendingTransfer(async()=>{
    await api('/warehouse-assistant/api/interwarehouse/requests/'+id,{method:'DELETE'});
    rebalanceState.pendingSelection.delete(id);toast('قلم حذف و رزرو جابه‌جایی آزاد شد.');await loadTransferRequests();
  });
}
async function revokePendingTransfer(id){
  const row=rebalanceState.requests.find(r=>r.id===id);
  if(rebalanceState.busy||!row||row.issued_document_id||row.reflected_at)return;
  if(!window.confirm('تأیید '+row.product_name+' لغو شود؟ رزرو آزاد می‌شود و در صورت داشتن شرایط، دوباره در پیشنهادها می‌آید. برای به‌روزرسانی خرید، محاسبه سفارش را دوباره انجام دهید.'))return;
  return mutatePendingTransfer(async()=>{
    await api('/warehouse-assistant/api/interwarehouse/requests/'+id+'/revoke',{method:'POST'});
    rebalanceState.pendingSelection.delete(id);toast('تأیید قلم لغو و رزرو آن آزاد شد.');await loadTransferRequests();
  });
}
async function deleteTransferDocument(key){
  const d=transferDocuments(rebalanceState.requests).find(d=>d.key===key);
  if(rebalanceState.busy||!d||!transferDocumentUnposted(d))return;
  if(!window.confirm('سند داخلی '+d.number+' حذف شود؟ '+fa(d.lines.length)+' قلم به جابه‌جایی‌های تأییدشده برمی‌گردد؛ رزرو جابه‌جایی حفظ می‌شود.'))return;
  return mutatePendingTransfer(async()=>{
    await api('/warehouse-assistant/api/interwarehouse/documents/'+encodeURIComponent(key),{method:'DELETE'});
    if(rebalanceState.openDocument===key){$('#transferDocumentDialog').close();rebalanceState.openDocument=null}
    rebalanceState.stage='requests';rebalanceState.direction=d.source+'-'+d.destination;rebalanceState.requestWarehouse='all';
    toast('سند حذف شد؛ اقلام به تأییدشده‌ها برگشتند.');await loadTransferRequests();
  });
}
function transferDocumentActions(d){
  return (transferCanRegister(d)?'<button type="button" class="primary" data-transfer-document-register="'+esc(d.key)+'" '+(rebalanceState.busy?'disabled ':'')+'aria-label="ثبت در ورانگر؛ سند '+esc(d.number)+'" title="'+(rebalanceState.busy?'عملیات قبلی هنوز در حال تکمیل است.':'بررسی موجودی و تأیید نهایی پیش از ثبت')+'">ثبت در ورانگر</button> ':'')+
    '<button type="button" data-transfer-document="'+esc(d.key)+'" aria-label="مشاهده سند '+esc(d.number)+'">مشاهده سند و اقلام</button>'+
    (transferCanReturn(d)&&typeof has==='function'&&has('warehouse.receipt.transfer')?' <button type="button" data-transfer-document-return="'+esc(d.key)+'" '+(rebalanceState.busy?'disabled ':'')+'title="بررسی خودکار حذف در ورانگر و بازگشت اقلام به تأییدشده‌ها">حذف سند و بازگشت اقلام</button>':'')+
    (!transferDocumentUnposted(d)?'':' <button type="button" data-transfer-document-delete="'+esc(d.key)+'" aria-label="حذف سند '+esc(d.number)+'">حذف سند داخلی</button>');
}
async function returnTransferDocument(key){
  const d=transferDocuments(rebalanceState.requests).find(d=>d.key===key);
  if(rebalanceState.busy||!d||!transferCanReturn(d)||!has('warehouse.receipt.transfer'))return;
  if(!window.confirm('سند داخلی '+d.number+' حذف و '+fa(d.lines.length)+' قلم به تأییدشده‌ها برگردد؟ نبود بستانکار '+(d.erp_voucher_no??'—')+' و رسید مقصد خودکار بررسی و در صورت نیاز موجودی بازخوانی می‌شود. رزرو اقلام حفظ می‌شود؛ سندی در ورانگر حذف نمی‌شود.'))return;
  return mutatePendingTransfer(async()=>{
    const progress='در حال بررسی حذف سند و رسید مقصد؛ در صورت نیاز موجودی خودکار به‌روزرسانی می‌شود…';
    $('#transferPendingError').textContent='';$('#transferRequestStatus').textContent=progress;
    if(rebalanceState.openDocument===key&&typeof transferCreditMessage==='function')transferCreditMessage(progress);
    await api('/warehouse-assistant/api/interwarehouse/documents/'+encodeURIComponent(key)+'/return-to-approved',{method:'POST'});
    if(rebalanceState.openDocument===key){$('#transferDocumentDialog').close();rebalanceState.openDocument=null}
    rebalanceState.stage='requests';rebalanceState.direction=transferRoute(d);rebalanceState.requestWarehouse='all';
    toast('سند از فهرست حذف شد و اقلام به تأییدشده‌ها برگشتند؛ رزرو اقلام حفظ شده است.');await loadTransferRequests();
  });
}
function renderTransferRequests(){
  const {direction,stage,proposal}=rebalanceState;
  document.querySelectorAll('[data-transfer-direction]').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.transferDirection===direction));b.hidden=stage==='proposals'&&b.dataset.transferDirection==='all'});
  document.querySelectorAll('[data-transfer-stage]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.transferStage===stage)));
  $('#balanceProposalPanel').hidden=stage!=='proposals';$('#balanceRequestPanel').hidden=stage!=='requests';
  $('#balanceDocumentsPanel').hidden=stage!=='documents';$('#transferWarehouseFilters').hidden=stage==='proposals';
  const offers=proposal&&transferRoute(proposal)===direction?proposal.lines:[];
  $('#balanceProposalRows').innerHTML=offers.map(balanceProposalRow).join('')||'<tr><td colspan="12" class="empty-cell">در این مسیر کالای واجد شرایط جابه‌جایی وجود ندارد.</td></tr>';
  document.querySelectorAll('[data-transfer-warehouse]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.transferWarehouse===rebalanceState.requestWarehouse)));
  const rows=filteredTransferRequests();
  $('#balanceSectionTitle').textContent=({requests:'جابه‌جایی‌های تأییدشده',documents:'اسناد جابه‌جایی',proposals:'پیشنهادهای جابه‌جایی'})[stage]+' · '+(direction==='all'?'همه مسیرها':direction.split('-').map(transferCity).join(' به '));
  $('#balanceRuleSummary').textContent=direction.endsWith('-gilan')?'ارسال به گیلان: تهران و کرج حداقل ۳۰؛ گیلان زیر ۲۰ و پس از انتقال حداقل ۲۰ روز · راهنما':'مبدأ بالای ۴۵، مقصد زیر ۱۵ روز؛ حداقل ماندگاری مبدأ ۲۰ روز · راهنما';
  const documents=transferDocuments(rows);
  const pending=rows.filter(r=>!r.issued_document_id);
  $('#transferPendingRows').innerHTML=pending.map(transferPendingRow).join('')||'<tr><td colspan="17" class="empty-cell">قلم تأییدشدهٔ بدون سند در این مسیر وجود ندارد.</td></tr>';
  $('#transferRequestRows').innerHTML=documents.map(d=>'<tr>'+[esc(d.number),esc(d.erp_voucher_no??'—'),'<span title="'+esc((d.erp_message||'')+(d.erp_checked_at?' · بررسی: '+formatRefreshDate(d.erp_checked_at):''))+'">'+transferErpLabel(d)+'</span>',transferDocumentStatus(d),esc(d.business_date),transferCity(d.source)+' به '+transferCity(d.destination),fa(d.lines.length),fa(d.cartons),fa(d.quantity),transferDocumentValue(d),esc(d.created_by||'—'),transferDocumentActions(d)].map((x,i)=>'<td'+(i===11?' class="transfer-document-actions"':'')+'>'+x+'</td>').join('')+'</tr>').join('')||'<tr><td colspan="12" class="empty-cell">برای مسیر و انبار انتخاب‌شده سند جابه‌جایی وجود ندارد.</td></tr>';
  $('#transferRequestCount').textContent=stage==='proposals'?fa(offers.length)+' پیشنهاد':stage==='requests'?fa(pending.length)+' قلم بدون سند':fa(documents.length)+' سند · '+fa(documents.reduce((s,d)=>s+d.lines.length,0))+' قلم';
  if(typeof fitTableWrapsToViewport==='function')fitTableWrapsToViewport();
  updateBalanceSelection();
  updatePendingSelection();
}
async function loadTransferRequests({refreshDocument=true,refreshErp=false}={}){
  const sequence=++rebalanceState.sequence,direction=rebalanceState.direction,status=$('#transferRequestStatus');
  status.textContent=rebalanceState.stage==='proposals'?'در حال بررسی موجودی و سفارش‌های در راه…':'در حال بازخوانی فهرست جابه‌جایی‌ها…';rebalanceState.proposal=null;rebalanceState.edits.clear();renderTransferRequests();
  try{
    const [data,proposal]=await Promise.all([readTransferData('/warehouse-assistant/api/interwarehouse'+(refreshErp?'?refresh_erp=true':'')),rebalanceState.stage==='proposals'?api('/warehouse-assistant/api/interwarehouse/balance/'+direction.replace('-','/')):Promise.resolve(null)]);
    if(sequence!==rebalanceState.sequence)return;
    rebalanceState.requests=data.items;rebalanceState.proposal=proposal;rebalanceState.retry=null;renderTransferRequests();status.textContent='';
    if(refreshDocument&&rebalanceState.openDocument)openTransferDocument(rebalanceState.openDocument);
  }catch(error){if(sequence===rebalanceState.sequence)status.textContent=error.message}
}
async function acceptBalanceRow(row){
  return acceptBalanceRows([row],row.querySelector('[data-balance-accept]'),row.querySelector('[data-balance-error]'));
}
async function acceptSelectedBalanceRows(){
  return acceptBalanceRows(visibleBalanceRows().filter(r=>r.querySelector('[data-balance-selected]').checked),$('#acceptBalanceSelection'),$('#balanceBatchError'));
}
async function acceptBalanceRows(rows,action,error){
  const p=rebalanceState.proposal;if(!p||rebalanceState.busy)return;
  error.textContent='';
  if(!rows.length){error.textContent='حداقل یک قلم نمایان را انتخاب کنید.';return}
  const lines=[];
  for(const row of rows){
    const input=row.querySelector('[data-balance-cartons]'),offer=p.lines.find(x=>x.product_code===row.dataset.balanceCode),cartons=Number(input.value);
    row.querySelector('[data-balance-error]').textContent='';
    if(!offer||!Number.isInteger(cartons)||cartons<(offer.minimum_cartons||1)||cartons>offer.available_cartons){error.textContent=offer?'مقدار باید کارتن کامل، از '+fa(offer.minimum_cartons||1)+' تا '+fa(offer.available_cartons)+' باشد.':'پیشنهاد معتبر نیست؛ بازخوانی کنید.';row.querySelector('[data-balance-error]').textContent=error.textContent;input.focus();return}
    lines.push({product_code:offer.product_code,cartons});
  }
  lines.sort((a,b)=>a.product_code.localeCompare(b.product_code));
  const signature=JSON.stringify([p.source,p.destination,p.expected_token,lines]);
  if(rebalanceState.retry?.signature!==signature)rebalanceState.retry={signature,id:transferRequestId()};
  const previousLabel=action.textContent;rebalanceState.busy=true;action.textContent='در حال ثبت…';
  const controls=[...$('#transfersView').querySelectorAll('button,input,select')],disabled=controls.map(x=>x.disabled);controls.forEach(x=>x.disabled=true);
  try{
    const result=await api('/warehouse-assistant/api/interwarehouse/balance/'+p.source+'/'+p.destination+'/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lines,expected_token:p.expected_token,request_id:rebalanceState.retry.id})});
    rebalanceState.proposal=null;rebalanceState.stage='requests';rebalanceState.direction=transferRoute(p);rebalanceState.requestWarehouse='all';
    toast('جابه‌جایی تأیید شد؛ '+fa(result.reduced_purchase_quantity)+' عدد از پیش‌سفارش‌ها کم شد. انتقال فیزیکی انجام نشده است.');
    await loadTransferRequests();
    try{await Promise.all([loadOrders(),loadAutomaticPreorders()])}catch{toast('جابه‌جایی ثبت شد؛ فهرست سفارش‌ها را بازخوانی کنید.',true)}
  }catch(exc){error.textContent=exc.message}
  finally{rebalanceState.busy=false;action.textContent=previousLabel;controls.forEach((node,i)=>node.disabled=disabled[i]);syncTransferRegistrationButtons();updateBalanceSelection()}
}
function openBalanceReflection(id){
  if(rebalanceState.busy)return;
  const row=rebalanceState.requests.find(x=>x.id===id);
  if(!row||row.reflected_at||row.credit_status!=='sent'||row.erp_status!=='confirmed'||row.source_stock_status!=='reflected'||row.source_stock_snapshot_id!==row.current_snapshot_id||row.current_snapshot_id<=row.snapshot_id)return;
  rebalanceState.reflection={id:row.id,snapshot_id:row.current_snapshot_id};
  $('#balanceReflectionForm').reset();$('#balanceReflectionError').textContent='';$('#balanceSourceDocument').value=String(transferCreditNumber(row)||row.source_document||'');
  $('#balanceReflectionItem').textContent=row.product_name+' · '+fa(row.cartons)+' کارتن · '+transferCity(row.source)+' به '+transferCity(row.destination);
  $('#balanceReflectionDialog').showModal();
}
async function saveBalanceReflection(event){
  event.preventDefault();if(rebalanceState.busy||!rebalanceState.reflection)return;
  const form=$('#balanceReflectionForm');if(!form.reportValidity())return;
  const selection=rebalanceState.reflection,controls=[...form.querySelectorAll('input,button')];
  const payload={snapshot_id:selection.snapshot_id,source_document:$('#balanceSourceDocument').value.trim(),destination_document:$('#balanceDestinationDocument').value.trim(),confirmed:$('#balanceReflectedConfirmed').checked};
  rebalanceState.busy=true;controls.forEach(x=>x.disabled=true);$('#balanceReflectionError').textContent='';
  try{
    await api('/warehouse-assistant/api/interwarehouse/requests/'+selection.id+'/reflect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    $('#balanceReflectionDialog').close();rebalanceState.reflection=null;
    toast('تطبیق ثبت شد؛ این انتقال دیگر جداگانه در موجودی مبنای سفارش شمرده نمی‌شود.');await loadTransferRequests();
  }catch(error){$('#balanceReflectionError').textContent=error.message}
  finally{rebalanceState.busy=false;controls.forEach(x=>x.disabled=false);syncTransferRegistrationButtons()}
}
document.addEventListener('DOMContentLoaded',()=>{
  $('#transferPendingSelectAll').addEventListener('change',event=>{if(rebalanceState.busy)return;visiblePendingRows().forEach(row=>{row.querySelector('[data-pending-selected]').checked=event.target.checked;const id=Number(row.dataset.pendingId);if(event.target.checked)rebalanceState.pendingSelection.add(id);else rebalanceState.pendingSelection.delete(id)});updatePendingSelection()});
  $('#transferPendingRows').addEventListener('change',event=>{if(rebalanceState.busy||!event.target.matches('[data-pending-selected]'))return;const id=Number(event.target.closest('tr[data-pending-id]').dataset.pendingId);if(event.target.checked)rebalanceState.pendingSelection.add(id);else rebalanceState.pendingSelection.delete(id);updatePendingSelection()});
  $('#transferPendingRows').addEventListener('click',event=>{const b=event.target.closest('[data-pending-delete],[data-pending-revoke]');if(b&&!b.disabled){if(b.dataset.pendingRevoke)revokePendingTransfer(Number(b.dataset.pendingRevoke));else deletePendingTransfer(Number(b.dataset.pendingDelete))}});
  $('#createTransferDocuments').addEventListener('click',issueSelectedTransfers);
  $('#revokeSelectedTransfers').addEventListener('click',()=>mutateSelectedPendingTransfers('revoke'));
  $('#deleteSelectedTransfers').addEventListener('click',()=>mutateSelectedPendingTransfers('delete'));
  new MutationObserver(updatePendingSelection).observe($('#transferPendingRows'),{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','style','class']});
  $('#balanceSelectAll').addEventListener('change',event=>{if(rebalanceState.busy)return;visibleBalanceRows().forEach(row=>{row.querySelector('[data-balance-selected]').checked=event.target.checked;rememberBalanceRow(row)});updateBalanceSelection()});
  $('#balanceProposalRows').addEventListener('change',event=>{if(event.target.matches('[data-balance-selected]')){rememberBalanceRow(event.target.closest('tr[data-balance-code]'));updateBalanceSelection()}});
  $('#acceptBalanceSelection').addEventListener('click',acceptSelectedBalanceRows);
  document.querySelectorAll('[data-transfer-warehouse]').forEach(b=>b.addEventListener('click',()=>{if(!rebalanceState.busy){rebalanceState.requestWarehouse=b.dataset.transferWarehouse;rebalanceState.direction='all';renderTransferRequests()}}));
  new MutationObserver(updateBalanceSelection).observe($('#balanceProposalRows'),{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','style','class']});
  $('#balanceReflectionForm').addEventListener('submit',saveBalanceReflection);
  $('#closeBalanceReflection').addEventListener('click',()=>{if(!rebalanceState.busy)$('#balanceReflectionDialog').close()});
  $('#balanceReflectionDialog').addEventListener('cancel',event=>{if(rebalanceState.busy)event.preventDefault()});
  $('#transferRequestRows').addEventListener('click',event=>{const button=event.target.closest('[data-transfer-document],[data-transfer-document-register],[data-transfer-document-delete],[data-transfer-document-return]');if(button&&!button.disabled){if(button.dataset.transferDocumentRegister)openTransferRegistration(button.dataset.transferDocumentRegister);else if(button.dataset.transferDocumentReturn)returnTransferDocument(button.dataset.transferDocumentReturn);else if(button.dataset.transferDocumentDelete)deleteTransferDocument(button.dataset.transferDocumentDelete);else openTransferDocument(button.dataset.transferDocument)}});
  $('#transferDocumentLines').addEventListener('click',event=>{const button=event.target.closest('[data-balance-reflect]');if(button&&!button.disabled)openBalanceReflection(Number(button.dataset.balanceReflect))});
  $('#closeTransferDocument').addEventListener('click',()=>{if(!rebalanceState.busy)$('#transferDocumentDialog').close()});
  $('#transferDocumentDialog').addEventListener('cancel',event=>{if(rebalanceState.busy)event.preventDefault()});
  $('#transferDocumentDialog').addEventListener('close',()=>{rebalanceState.openDocument=null});
  $('#refreshTransfersButton').addEventListener('click',()=>{if(!rebalanceState.busy)loadTransferRequests({refreshErp:true})});
  document.querySelectorAll('[data-transfer-direction]').forEach(b=>b.addEventListener('click',()=>{if(rebalanceState.busy)return;rebalanceState.direction=b.dataset.transferDirection;rebalanceState.requestWarehouse='all';if(rebalanceState.stage!=='proposals')renderTransferRequests();else loadTransferRequests()}));
  document.querySelectorAll('[data-transfer-stage]').forEach(b=>b.addEventListener('click',()=>{if(rebalanceState.busy||rebalanceState.stage===b.dataset.transferStage)return;rebalanceState.stage=b.dataset.transferStage;if(rebalanceState.direction==='all'&&rebalanceState.stage==='proposals')rebalanceState.direction='tehran-karaj';rebalanceState.requestWarehouse='all';loadTransferRequests()}));
  $('#balanceProposalRows').addEventListener('click',event=>{const button=event.target.closest('[data-balance-accept]');if(button&&!button.disabled)acceptBalanceRow(button.closest('tr[data-balance-code]'))});
  $('#balanceProposalRows').addEventListener('input',event=>{
    if(!event.target.matches('[data-balance-cartons]'))return;
    const row=event.target.closest('tr[data-balance-code]'),o=rebalanceState.proposal?.lines.find(x=>x.product_code===row.dataset.balanceCode),n=Number(event.target.value);
    if(!o)return;
    rememberBalanceRow(row);
    const valid=Number.isInteger(n)&&n>=(o.minimum_cartons||1)&&n<=o.available_cartons,a=balanceAfter(o,n);
    event.target.setAttribute('aria-invalid',String(!valid));
    row.querySelector('[data-balance-error]').textContent=valid?'':'مقدار مجاز: '+fa(o.minimum_cartons||1)+' تا '+fa(o.available_cartons)+' کارتن.';
    row.querySelector('[data-balance-after-source]').textContent=valid?fa(a.source):'—';
    row.querySelector('[data-balance-after-destination]').textContent=valid?fa(a.destination):'—';
  });
});
