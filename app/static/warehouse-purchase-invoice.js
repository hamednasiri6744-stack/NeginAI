/* Explicit receipt -> preview -> unconfirmed purchase invoice. */
const purchaseInvoice={receipt:null,receipts:[],preview:null,request:null,busy:false,generation:0};
const pi$=id=>document.getElementById(id);
const invoiceAmount=value=>value===null||value===undefined||value===''?'—':fa(value);
function invoiceToday(){
  if(purchaseState.catalog.today)return purchaseState.catalog.today;
  const parts=new Intl.DateTimeFormat('en-US-u-ca-persian',{timeZone:'Asia/Tehran',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  return ['year','month','day'].map(type=>parts.find(part=>part.type===type).value).join('/');
}
function resetPurchaseInvoice(){purchaseInvoice.generation++;purchaseInvoice.receipt=null;purchaseInvoice.receipts=[];purchaseInvoice.preview=null;purchaseInvoice.request=null;purchaseInvoice.busy=false;if(pi$('purchaseInvoiceDialog')?.open)pi$('purchaseInvoiceDialog').close()}
function invoiceMessage(value){pi$('invoiceMessage').textContent=value;pi$('invoiceMessage').hidden=!value}
function invoiceBusy(value){purchaseInvoice.busy=value;pi$('invoiceFields').disabled=value;pi$('invoicePreview').disabled=value;pi$('invoiceClose').disabled=value;pi$('invoiceCommit').disabled=value||!purchaseInvoice.preview?.ready||!purchaseInvoice.preview?.commit_enabled||!purchaseInvoice.preview?.bridge_enabled;if(typeof renderUnbilledReceipts==='function')renderUnbilledReceipts()}
function openPurchaseInvoice(receiptIds){
  if(purchaseInvoice.busy)return;
  if(!unbilledState.loaded||unbilledState.loading){unbilledError('ابتدا فهرست رسیدها را با موفقیت از ورانگر دریافت کنید.');return}
  const ids=[...new Set((Array.isArray(receiptIds)?receiptIds:[receiptIds]).map(Number))];
  const receipts=ids.map(id=>unbilledState.items.find(r=>r.receipt_id===id));
  if(!ids.length||ids.length>20||receipts.some(r=>!r)){unbilledError('یک تا ۲۰ رسید موجود را انتخاب کنید.');return}
  const reason=receipts.map(r=>unbilledSelectionReason(r,receipts)).find(Boolean);
  if(reason){unbilledError(reason);return}
  resetPurchaseInvoice();purchaseInvoice.receipts=receipts;purchaseInvoice.receipt=receipts[0];
  pi$('invoiceTitle').textContent=`یک فاکتور خرید از ${fa(receipts.length)} رسید · ${receipts[0].supplier_name}`;
  pi$('invoiceReceipts').innerHTML=`<strong>${esc(receipts[0].stock_name)} · سال ${fa(receipts[0].fiscal_year)}</strong><span>${receipts.map(r=>`رسید ${esc(String(r.receipt_no))} (${esc(r.receipt_date)})`).join(' · ')}</span>`;
  pi$('invoiceSupplierNo').value='';pi$('invoiceSupplierDate').value=invoiceToday();
  pi$('invoiceVoucherDate').value=pi$('invoiceSupplierDate').value;pi$('invoiceComment').value=receipts.length===1?(receipts[0].comment||''):'';
  clearInvoiceAmounts();
  invoiceMessage('شماره و تاریخ واقعی فاکتور شرکت را وارد کنید. تمام رسیدهای بالا به یک فاکتور تأییدنشده متصل می‌شوند؛ قیمت و قرارداد هر کالا برای تاریخ سند و همین انبار بررسی می‌شود.');
  invoiceBusy(false);pi$('purchaseInvoiceDialog').showModal();pi$('invoiceSupplierNo').focus();
}
function invoiceReceiptSources(item){
  return (item.receipt_sources||[]).map(r=>`رسید ${esc(String(r.receipt_no))}: ${fa(r.quantity)} عدد`).join(' · ');
}
const invoiceBasisNames={manufacturer:'قیمت تولید',consumer:'قیمت مصرف',announced:'قیمت اعلامی',purchase:'قیمت خرید'};
const invoiceTailBasisNames={net_before_tax:'خالص قبل از مالیات',gross:'مبلغ کل قبل از تخفیف',after_tax:'جمع پس از ارزش افزوده',invoice:'کل فاکتور',unit:'هر واحد کالا'};
function clearInvoiceAmounts(){pi$('invoiceRows').innerHTML='';pi$('invoiceTotal').textContent='';pi$('invoiceSummary').innerHTML='';pi$('invoiceSummary').hidden=true;pi$('invoiceSteps').innerHTML='';pi$('invoiceSteps').hidden=true}
function renderInvoiceAmounts(result){
  const money=v=>esc(invoiceAmount(v));
  pi$('invoiceRows').innerHTML=result.items.map(r=>{
    const a=r.amounts||{},p=r.pricing||{};
    const discounts=p.discount_steps||[{percent:p.discount_percent}];
    return `<tr><td class="pi-code">${esc(r.product_code)}</td><td>${esc(r.manufacturer_product_code||'—')}</td><td>${esc(r.barcode||'—')}</td><td class="pi-product">${esc(r.product_name)}<small class="pi-receipt-sources">${invoiceReceiptSources(r)}</small></td><td>${esc(r.group_level3||'—')}</td><td class="pi-number">${money(r.quantity)}</td><td class="pi-number">${money(r.source_price)}<small>${esc(invoiceBasisNames[p.basis]||'قیمت مبنا')}</small></td><td class="pi-number">${money(a.unit_price)}</td><td class="pi-number">${money(a.gross)}</td><td class="pi-number">${p.discount_percent==null?'—':discounts.map(s=>esc(fa(s.percent))+'٪').join(' سپس ')}</td><td class="pi-number pi-deduction">${money(a.discount)}</td><td class="pi-number">${money(a.net_before_tax)}</td><td class="pi-number">${money(a.tax)}<small>${r.tax_rate==null?'':esc(fa(r.tax_rate))+'٪'}</small></td><td class="pi-number">${money(a.after_tax)}</td></tr>`;
  }).join('');
  const s=result.summary;
  pi$('invoiceSummary').hidden=!s;
  if(s){
    const row=(label,value,cls='')=>`<div class="pi-sum-row ${cls}"><span>${label}</span><strong>${money(value)} <small>ریال</small></strong></div>`;
    pi$('invoiceSummary').innerHTML=`<div class="pi-summary-note"><strong>جمع‌بندی فاکتور</strong><p>جمع تمام اقلام فاکتور؛ فیلتر جدول این مبالغ را تغییر نمی‌دهد.</p><p>تخفیف انتهایی پس از افزودن ارزش افزوده کسر می‌شود. مبنای محاسبهٔ آن طبق قرارداد در مقابل هر تخفیف آمده است.</p></div><div class="pi-totals">${row('مبلغ کل اقلام',s.gross)}${row('کسر تخفیف ستونی',s.discount,'pi-deduction')}${row('خالص قبل از مالیات',s.net_before_tax)}${row('افزودن ارزش افزوده',s.tax)}${row('جمع با ارزش افزوده',s.after_tax,'pi-subtotal')}${(s.tail_discounts||[]).map(t=>row(`تخفیف انتهایی ${t.kind==='percent'?esc(fa(t.value))+'٪':'مبلغی'}<small>مبنا: ${esc(invoiceTailBasisNames[t.basis]||t.basis)}${t.kind==='percent'?' · '+money(t.base)+' ریال':''}</small>`,t.amount,'pi-tail')).join('')}${row('قابل پرداخت به تأمین‌کننده',s.total,'pi-payable')}</div>`;
  }
  const priced=result.items.filter(r=>r.pricing&&r.amounts);
  pi$('invoiceSteps').hidden=!priced.length;
  pi$('invoiceSteps').innerHTML=priced.length?`<summary>مراحل محاسبه طبق قرارداد · ${esc(fa(priced.length))} قلم</summary><ol>${priced.map(r=>{
    const p=r.pricing,a=r.amounts;
    const adjust=Number(p.adjustment_percent||0);
    return `<li><strong>${esc(r.product_code)} · ${esc(r.product_name)}</strong><span>${esc(invoiceBasisNames[p.basis]||'قیمت مبنا')}: ${money(r.source_price)} ریال</span><span>${p.includes_tax?'خارج کردن ارزش افزودهٔ '+esc(fa(r.tax_rate))+'٪ از قیمت مبنا':'قیمت مبنا بدون ارزش افزوده'}${adjust?' · '+(adjust>0?'افزایش':'کاهش')+' تجاری '+esc(fa(Math.abs(adjust)))+'٪':''} ← فی بدون مالیات: ${money(a.unit_price)} ریال</span><span>تخفیف ستونی: ${(p.discount_steps||[]).map((step,i)=>`مرحلهٔ ${esc(fa(i+1))}: ${esc(fa(step.percent))}٪`).join(' ← ')} · مبلغ: ${money(a.discount)} ریال</span><span>خالص: ${money(a.net_before_tax)} + ارزش افزوده: ${money(a.tax)} = ${money(a.after_tax)} ریال</span></li>`;
  }).join('')}</ol>`:'';
  pi$('invoiceTotal').textContent=result.total?`قابل پرداخت: ${fa(result.total)} ریال`:'';
}
async function previewPurchaseInvoice(){
  if(purchaseInvoice.busy||!purchaseInvoice.receipt)return;
  const generation=purchaseInvoice.generation;
  purchaseInvoice.preview=null;
  purchaseInvoice.request={receipt_ids:purchaseInvoice.receipts.map(r=>r.receipt_id),supplier_invoice_no:pi$('invoiceSupplierNo').value,supplier_invoice_date:pi$('invoiceSupplierDate').value,voucher_date:pi$('invoiceVoucherDate').value,comment:pi$('invoiceComment').value};
  invoiceBusy(true);invoiceMessage('در حال کنترل رسید، قیمت‌های معتبر و قرارداد کالاها…');clearInvoiceAmounts();
  try{
    const result=await api('/warehouse-assistant/api/purchase-invoices/preview',{method:'POST',headers:purchaseHeaders(),body:JSON.stringify(purchaseInvoice.request)});
    if(generation!==purchaseInvoice.generation)return;
    purchaseInvoice.preview=result;
    renderInvoiceAmounts(result);
    invoiceMessage(result.errors.length?result.errors.join('\n'):!result.bridge_enabled||!result.commit_enabled?(result.bridge_message||'محاسبات آماده است؛ اتصال پل خرید هنوز آماده نیست.'):'محاسبات آماده است؛ با ثبت، فاکتور تأییدنشده به تمام رسیدهای انتخاب‌شده متصل می‌شود.');
  }catch(error){if(generation===purchaseInvoice.generation)invoiceMessage(error.message)}finally{if(generation===purchaseInvoice.generation)invoiceBusy(false)}
}
async function transferPurchaseInvoice(){
  const p=purchaseInvoice.preview;if(purchaseInvoice.busy||!p?.ready||!p.commit_enabled||!p.bridge_enabled)return;
  if(!window.confirm(`فاکتور خرید تأییدنشده برای ${fa(purchaseInvoice.receipts.length)} رسید (${purchaseInvoice.receipts.map(r=>fa(r.receipt_no)).join('، ')}) با مبلغ ${fa(p.total)} ریال ثبت شود؟`))return;
  invoiceBusy(true);const generation=purchaseInvoice.generation;
  try{
    const result=await api('/warehouse-assistant/api/purchase-invoices/transfer',{method:'POST',headers:purchaseHeaders(),body:JSON.stringify({...purchaseInvoice.request,confirmed:true,preview_token:p.preview_token})});
    if(generation!==purchaseInvoice.generation)return;
    invoiceMessage(result.BridgeStatus==='sent'?`فاکتور خرید ${result.InvoiceNo} به‌صورت تأییدنشده ثبت و به ${fa(purchaseInvoice.receipts.length)} رسید متصل شد.`:(result.Message||'ثبت انجام نشد؛ وضعیت پل را بررسی کنید.'));
    if(result.BridgeStatus==='sent'){purchaseInvoice.preview=null;clearUnbilledSelection(purchaseInvoice.request.receipt_ids);await loadUnbilledReceipts()}
  }catch(error){if(generation===purchaseInvoice.generation)invoiceMessage(error.message)}finally{if(generation===purchaseInvoice.generation)invoiceBusy(false)}
}
document.addEventListener('DOMContentLoaded',()=>{
  if(!document.getElementById('unbilledView'))return;
  const dialog=document.createElement('dialog');dialog.id='purchaseInvoiceDialog';dialog.dir='rtl';
  dialog.innerHTML=`<div class="pi-head"><div><small>پیش‌نویس فاکتور خرید · مبالغ به ریال</small><h2 id="invoiceTitle">فاکتور خرید</h2></div><button id="invoiceClose" type="button">بستن</button></div><div class="pi-body"><div id="invoiceReceipts" class="pi-receipts" aria-label="رسیدهای انتخاب‌شده"></div><fieldset id="invoiceFields"><label>شماره واقعی فاکتور تأمین‌کننده<input id="invoiceSupplierNo" inputmode="numeric" maxlength="10"></label><label>تاریخ فاکتور تأمین‌کننده<input id="invoiceSupplierDate" dir="ltr" maxlength="10"></label><label>تاریخ ثبت سند<input id="invoiceVoucherDate" dir="ltr" maxlength="10"></label><label>توضیحات<input id="invoiceComment" maxlength="200"></label></fieldset><p id="invoiceMessage" role="status"></p><div class="pi-table"><table id="purchaseInvoicePreviewTable" aria-label="پیش‌نمایش فاکتور خرید"><thead><tr><th>کد کالا</th><th>کد کالای تولیدکننده</th><th>بارکد</th><th>نام کالا</th><th>گروه سطح ۳</th><th>تعداد پایه</th><th>قیمت مبنا</th><th>فی بدون مالیات</th><th>مبلغ کل</th><th>تخفیف ٪</th><th>مبلغ تخفیف</th><th>خالص قبل از مالیات</th><th>ارزش افزوده</th><th>جمع با مالیات</th></tr></thead><tbody id="invoiceRows"></tbody></table></div><section id="invoiceSummary" class="pi-summary" aria-label="جمع‌بندی فاکتور" hidden></section><details id="invoiceSteps" class="pi-steps" hidden></details></div><div class="pi-footer"><strong id="invoiceTotal"></strong><button id="invoicePreview" type="button">بررسی قیمت و پیش‌نمایش</button><button id="invoiceCommit" type="button" disabled>ثبت فاکتور تأییدنشده در ورانگر</button></div>`;
  document.body.appendChild(dialog);
  document.addEventListener('click',e=>{const b=e.target.closest('[data-purchase-receipt]');if(b)openPurchaseInvoice(b.dataset.purchaseReceipt)});
  pi$('invoiceClose').addEventListener('click',()=>{if(!purchaseInvoice.busy)resetPurchaseInvoice()});
  dialog.addEventListener('cancel',e=>{if(purchaseInvoice.busy)e.preventDefault();else resetPurchaseInvoice()});
  pi$('invoicePreview').addEventListener('click',previewPurchaseInvoice);pi$('invoiceCommit').addEventListener('click',transferPurchaseInvoice);
  pi$('invoiceFields').addEventListener('input',()=>{purchaseInvoice.preview=null;pi$('invoiceCommit').disabled=true;clearInvoiceAmounts();invoiceMessage('اطلاعات تغییر کرد؛ پیش‌نمایش را دوباره محاسبه کنید.')});
});
