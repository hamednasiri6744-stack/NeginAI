/* Live read-only receipt list; a draft invoice also reserves its receipt. */
const unbilledState={items:[],request:0,page:0,pageSize:50,loading:false,loaded:false,selected:new Map(),selectionNotice:''};
const ub$=id=>document.getElementById(id);
function unbilledSelectionBusy(){return typeof purchaseInvoice!=='undefined'&&purchaseInvoice.busy}
function unbilledSelectionReason(receipt,selection=[...unbilledState.selected.values()]){
  if(!receipt?.confirmed)return 'این رسید هنوز تأیید نشده است؛ ابتدا در ورانگر تأیید کنید.';
  if(!receipt.supplier_id||!receipt.stock_id||!receipt.fiscal_year)return 'مشخصات تأمین‌کننده، انبار یا سال مالی رسید کامل نیست.';
  const other=selection.find(r=>r.receipt_id!==receipt.receipt_id);
  if(other&&Number(other.supplier_id)!==Number(receipt.supplier_id))return 'رسیدهای یک فاکتور باید متعلق به یک تأمین‌کننده باشند.';
  if(other&&Number(other.stock_id)!==Number(receipt.stock_id))return 'رسیدهای یک فاکتور باید متعلق به یک انبار باشند.';
  if(other&&Number(other.fiscal_year)!==Number(receipt.fiscal_year))return 'رسیدهای یک فاکتور باید متعلق به یک سال مالی باشند.';
  if(!selection.some(r=>r.receipt_id===receipt.receipt_id)&&selection.length>=20)return 'در هر فاکتور حداکثر ۲۰ رسید انتخاب کنید.';
  return '';
}
function setUnbilledReceiptSelection(receiptId,selected){
  if(unbilledSelectionBusy())return false;
  const id=Number(receiptId),receipt=unbilledState.items.find(r=>r.receipt_id===id);
  if(selected){const reason=unbilledSelectionReason(receipt);if(reason){unbilledError(reason);return false}unbilledState.selected.set(id,receipt)}
  else unbilledState.selected.delete(id);
  unbilledState.selectionNotice='';renderUnbilledReceipts();return true;
}
function reconcileUnbilledSelection(){
  const fresh=new Map(unbilledState.items.map(r=>[r.receipt_id,r])),kept=new Map();let removed=0;
  for(const [id,previous] of unbilledState.selected){
    const receipt=fresh.get(id);
    const changed=receipt&&['supplier_id','stock_id','fiscal_year'].some(key=>Number(receipt[key])!==Number(previous[key]));
    if(!receipt||changed||unbilledSelectionReason(receipt,[...kept.values()])){removed++;continue}
    kept.set(id,receipt);
  }
  unbilledState.selected=kept;
  unbilledState.selectionNotice=removed?`${fa(removed)} رسید از انتخاب‌ها کنار گذاشته شد؛ در فهرست تازه موجود نیست یا شرایط آن تغییر کرده است.`:'';
}
function renderUnbilledSelection(){
  const selected=[...unbilledState.selected.values()],busy=unbilledSelectionBusy();
  if(ub$('unbilledSelectedCount'))ub$('unbilledSelectedCount').textContent=(selected.length?`${fa(selected.length)} رسید انتخاب‌شده · ${selected.map(r=>fa(r.receipt_no)).join('، ')}`:'هیچ رسیدی انتخاب نشده')+(unbilledState.selectionNotice?' · '+unbilledState.selectionNotice:'');
  if(ub$('unbilledCreateInvoice'))ub$('unbilledCreateInvoice').disabled=busy||!selected.length||unbilledState.loading||!unbilledState.loaded;
  if(ub$('unbilledClearSelection'))ub$('unbilledClearSelection').disabled=busy||!selected.length;
}
function clearUnbilledSelection(receiptIds){
  if(receiptIds)for(const id of receiptIds)unbilledState.selected.delete(Number(id));else unbilledState.selected.clear();
  unbilledState.selectionNotice='';renderUnbilledReceipts();
}
function unbilledReceiptActions(receipt){
  const selected=unbilledState.selected.has(receipt.receipt_id),reason=unbilledSelectionReason(receipt),busy=unbilledSelectionBusy();
  const label=selected?'انتخاب‌شده':'افزودن به فاکتور';
  return `<label class="ub-select-receipt" title="${esc(reason||label)}"><input type="checkbox" data-select-purchase-receipt="${receipt.receipt_id}" aria-label="انتخاب رسید ${esc(String(receipt.receipt_no))}" ${selected?'checked':''} ${busy||(!selected&&reason)?'disabled':''}>${label}</label>${reason&&!selected?`<small class="ub-selection-reason">${esc(reason)}</small>`:''}${receipt.confirmed?`<button type="button" data-purchase-receipt="${receipt.receipt_id}" ${busy?'disabled':''}>فاکتور همین رسید</button>`:''}`;
}
function unbilledComment(value){
  const text=String(value||'');
  if(text.length<=100&&text.split('\n').length<=2)return esc(text||'—');
  return `<details><summary aria-label="نمایش توضیحات کامل رسید">${esc(text.replace(/\s+/g,' ').slice(0,85))}…</summary><div>${esc(text)}</div></details>`;
}
function unbilledError(message){ub$('unbilledError').textContent=message;ub$('unbilledError').hidden=!message}
function resetUnbilledReceipts(){
  unbilledState.selected.clear();unbilledState.selectionNotice='';unbilledState.request++;unbilledState.items=[];unbilledState.page=0;unbilledState.loading=false;unbilledState.loaded=false;
  if(!ub$('unbilledView'))return;
  for(const id of ['unbilledYear','unbilledFrom','unbilledTo','unbilledSearch','unbilledStatus'])ub$(id).value='';
  fillUnbilledOptions();ub$('unbilledReadAt').textContent='';unbilledError('');renderUnbilledReceipts();
  ub$('unbilledRefresh').disabled=false;ub$('unbilledView').setAttribute('aria-busy','false');
}
function unbilledOptions(id,items,first){
  const old=ub$(id).value;
  ub$(id).innerHTML=`<option value="">${first}</option>`+items.map(i=>`<option value="${esc(String(i.id??'unknown'))}">${esc(i.name)}</option>`).join('');
  ub$(id).value=items.some(i=>String(i.id??'unknown')===old)?old:'';
}
function fillUnbilledOptions(){
  const stocks=new Map(),makers=new Map();
  for(const r of unbilledState.items){stocks.set(r.stock_id,r.stock_name||'مشخص نشده');for(const m of r.manufacturers)makers.set(m.id,m.name)}
  const options=map=>[...map].map(([id,name])=>({id,name})).sort((a,b)=>a.name.localeCompare(b.name,'fa'));
  unbilledOptions('unbilledStock',options(stocks),'همهٔ انبارها');unbilledOptions('unbilledManufacturer',options(makers),'همهٔ تولیدکنندگان');
}
function unbilledDate(value){
  const date=normalizeSearchText(value).trim();
  if(date&&!/^1[345]\d{2}\/(0[1-9]|1[0-2])\/(0[1-9]|[12]\d|3[01])$/.test(date))throw new Error('تاریخ فیلتر را به صورت سال/ماه/روز وارد کنید؛ مثلاً ۱۴۰۵/۰۶/۱۷.');
  return date;
}
function unbilledColumnValue(row,key){
  const index=Number(key.split(':').at(-1));
  return [row.receipt_no,row.receipt_date,row.stock_name,row.supplier_name,row.manufacturers.map(m=>m.name).join(' '),row.confirmed?'تأییدشده':'تأییدنشده',row.comment][index]??'';
}
function filteredUnbilledReceipts(){
  const from=unbilledDate(ub$('unbilledFrom').value),to=unbilledDate(ub$('unbilledTo').value);
  if(from&&to&&from>to)throw new Error('تاریخ شروع نباید بعد از تاریخ پایان باشد.');
  const stock=ub$('unbilledStock').value,maker=ub$('unbilledManufacturer').value,status=ub$('unbilledStatus').value,q=normalizeSearchText(ub$('unbilledSearch').value).trim();
  const rows=unbilledState.items.filter(r=>(!stock||String(r.stock_id??'unknown')===stock)&&(!maker||r.manufacturers.some(m=>String(m.id??'unknown')===maker))
    &&(!from||r.receipt_date>=from)&&(!to||r.receipt_date<=to)&&(!status||r.confirmed===(status==='confirmed'))
    &&(!q||normalizeSearchText([r.receipt_no,r.receipt_date,r.supplier_reference,r.stock_name,r.supplier_name,r.comment,...r.manufacturers.map(m=>m.name)].join(' ')).includes(q)));
  return typeof querySharedTableItems==='function'?querySharedTableItems(rows,getSharedTableQuery(ub$('unbilledTable')),unbilledColumnValue):rows;
}
function renderUnbilledReceipts(){
  let rows=[];let invalid=false;
  try{rows=filteredUnbilledReceipts();if(unbilledState.loaded)unbilledError('')}catch(error){invalid=true;unbilledError(error.message)}
  const pages=Math.max(1,Math.ceil(rows.length/unbilledState.pageSize));unbilledState.page=Math.min(unbilledState.page,pages-1);
  const start=unbilledState.page*unbilledState.pageSize;
  ub$('unbilledRows').innerHTML=rows.slice(start,start+unbilledState.pageSize).map(r=>`<tr><td dir="ltr">${esc(String(r.receipt_no))}</td><td dir="ltr">${esc(r.receipt_date)}</td><td>${esc(r.stock_name||'مشخص نشده')}</td><td>${esc(r.supplier_name||'مشخص نشده')}</td><td>${r.manufacturers.map(m=>esc(m.name)).join('<br>')}</td><td><span class="ub-status ${r.confirmed?'ub-confirmed':'ub-unconfirmed'}">${r.confirmed?'تأییدشده':'تأییدنشده'}</span></td><td class="ub-comment">${unbilledComment(r.comment)}</td><td class="ub-actions">${unbilledReceiptActions(r)}</td></tr>`).join('')
    ||`<tr><td colspan="8" class="ub-empty">${unbilledState.loading?'در حال دریافت رسیدها از ورانگر…':invalid?'فیلتر تاریخ را اصلاح کنید.':!unbilledState.loaded?'فهرست رسیدها دریافت نشده است.':unbilledState.items.length?'رسیدی مطابق فیلترها پیدا نشد.':'در این سال رسید بدون فاکتور خرید وجود ندارد.'}</td></tr>`;
  renderUnbilledSelection();
  ub$('unbilledCount').textContent=unbilledState.loaded?`${fa(rows.length)} رسید در نمایش از ${fa(unbilledState.items.length)} رسید · ${fa(rows.filter(r=>r.confirmed).length)} تأییدشده`:'';
  ub$('unbilledPage').textContent=rows.length?`${fa(start+1)} تا ${fa(Math.min(start+unbilledState.pageSize,rows.length))}`:'';
  ub$('unbilledPrevious').disabled=unbilledState.page===0||unbilledState.loading;ub$('unbilledNext').disabled=unbilledState.page>=pages-1||unbilledState.loading;
}
async function loadUnbilledReceipts(){
  const request=++unbilledState.request,year=normalizeSearchText(ub$('unbilledYear').value).trim();
  unbilledState.items=[];unbilledState.page=0;unbilledState.loaded=false;unbilledState.loading=true;
  ub$('unbilledReadAt').textContent='';unbilledError('');renderUnbilledReceipts();
  ub$('unbilledRefresh').disabled=true;ub$('unbilledView').setAttribute('aria-busy','true');
  try{
    if(year&&(!/^\d{4}$/.test(year)||Number(year)<1300||Number(year)>1500))throw new Error('سال مالی را بین ۱۳۰۰ و ۱۵۰۰ وارد کنید.');
    const result=await api('/warehouse-assistant/api/unbilled-receipts'+(year?'?'+new URLSearchParams({year}):''));
    if(request!==unbilledState.request)return;
    unbilledState.items=result.items;unbilledState.loaded=true;reconcileUnbilledSelection();ub$('unbilledYear').value=String(result.year);fillUnbilledOptions();
    ub$('unbilledReadAt').textContent='آخرین دریافت: '+new Date(result.read_at).toLocaleString('fa-IR');
  }catch(error){if(request===unbilledState.request){fillUnbilledOptions();unbilledError(error.status===404?'نسخهٔ سرور هنوز فهرست رسیدها را پشتیبانی نمی‌کند.':error.message)}}
  finally{if(request===unbilledState.request){unbilledState.loading=false;ub$('unbilledRefresh').disabled=false;ub$('unbilledView').setAttribute('aria-busy','false');renderUnbilledReceipts()}}
}
document.addEventListener('DOMContentLoaded',()=>{
  if(!ub$('unbilledView'))return;
  ub$('unbilledRows').addEventListener('change',event=>{const input=event.target.closest('[data-select-purchase-receipt]');if(input&&!setUnbilledReceiptSelection(input.dataset.selectPurchaseReceipt,input.checked))input.checked=unbilledState.selected.has(Number(input.dataset.selectPurchaseReceipt))});
  ub$('unbilledCreateInvoice')?.addEventListener('click',()=>openPurchaseInvoice([...unbilledState.selected.keys()]));
  ub$('unbilledClearSelection')?.addEventListener('click',()=>{if(!unbilledSelectionBusy())clearUnbilledSelection()});
  const filter=()=>{unbilledState.page=0;renderUnbilledReceipts()};
  registerSharedTableAdapter(ub$('unbilledTable'),filter);
  ub$('unbilledRefresh').addEventListener('click',loadUnbilledReceipts);
  ub$('unbilledFilters').addEventListener('submit',e=>{e.preventDefault();loadUnbilledReceipts()});
  ub$('unbilledYear').addEventListener('change',()=>{ub$('unbilledFrom').value='';ub$('unbilledTo').value='';loadUnbilledReceipts()});
  for(const id of ['unbilledStock','unbilledManufacturer','unbilledStatus','unbilledFrom','unbilledTo'])ub$(id).addEventListener('change',filter);
  ub$('unbilledSearch').addEventListener('input',filter);
  ub$('unbilledClear').addEventListener('click',()=>{for(const id of ['unbilledStock','unbilledManufacturer','unbilledStatus','unbilledFrom','unbilledTo','unbilledSearch'])ub$(id).value='';ub$('unbilledTable').querySelectorAll('[data-shared-column-filter]').forEach(input=>input.value='');filter()});
  ub$('unbilledPrevious').addEventListener('click',()=>{unbilledState.page--;renderUnbilledReceipts();ub$('unbilledRows').closest('.unbilled-table-scroll').scrollTop=0});
  ub$('unbilledNext').addEventListener('click',()=>{unbilledState.page++;renderUnbilledReceipts();ub$('unbilledRows').closest('.unbilled-table-scroll').scrollTop=0});
});
