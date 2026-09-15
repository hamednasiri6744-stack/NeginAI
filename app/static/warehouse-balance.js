// Retain an uncertain request unchanged across modal close/reopen in this page.
const fulfillmentBalanceState={order:null,pending:new Map(),busy:false,error:''};

function balanceNotice(message,error=false){
  $('#fulfillmentBalanceNotice').textContent=message;
  $('#fulfillmentBalanceNotice').setAttribute('role',error?'alert':'status');
}

function fillAllFulfillmentBalance(){
  const order=fulfillmentBalanceState.order;
  if(!order||fulfillmentBalanceState.busy||fulfillmentBalanceState.pending.has(order.id))return;
  const reopen=$('#fulfillmentBalanceMode').value==='reopen';
  const byCode=new Map(order.fulfillment.lines.map(line=>[String(line.product_code),line]));
  for(const input of document.querySelectorAll('[data-balance-product]')){
    const line=byCode.get(input.dataset.balanceProduct);
    if(line)input.value=String(fulfillmentBalanceLimit(line,reopen));
  }
  fulfillmentBalanceState.error='';
  balanceNotice('کل ماندهٔ مجاز سفارش انتخاب شد. مقدارها را بررسی کنید و برای ثبت، دکمهٔ عملیات را بزنید.');
}

function fulfillmentBalanceQuantity(value){
  const text=normalizeSearchText(value??'').replaceAll('٫','.');
  if(!text)return 0;
  if(!/^\d+(?:\.\d{1,3})?$/.test(text)||!Number.isFinite(Number(text)))throw new Error('مقدار را به عدد پایه، نامنفی و حداکثر با سه رقم اعشار وارد کنید.');
  return Number(text);
}

function fulfillmentBalanceLimit(line,reopen){return Number(reopen?line.closed_qty||0:line.remaining_qty||0)}

function renderFulfillmentBalance(preserveInputs=false){
  const order=fulfillmentBalanceState.order;if(!order)return;
  const pending=fulfillmentBalanceState.pending.get(order.id),info=order.fulfillment;
  const identity=new Map(info.lines.map(line=>[String(line.product_code),line]));
  if(pending)$('#fulfillmentBalanceMode').value=pending.reopen?'reopen':'close';
  const reopen=$('#fulfillmentBalanceMode').value==='reopen';
  const draft=preserveInputs===true?new Map([...document.querySelectorAll('[data-balance-product]')].map(input=>[input.dataset.balanceProduct,input.value])):new Map();
  $('#fulfillmentBalanceTitle').textContent=`دریافت‌ها و مانده ${order.preorder_number} · ${order.supplier}`;
  $('#fulfillmentBalanceSummary').textContent=`دریافت ${fa(info.received_qty||0)} عدد · مانده در راه ${fa(info.remaining_qty||0)} عدد · بسته‌شده ${fa(info.closed_qty||0)} عدد`;
  replaceTableRows($('#fulfillmentBalanceLines'),info.lines.map(line=>{
    const limit=fulfillmentBalanceLimit(line,reopen),frozen=pending?.lines.find(item=>item.product_code===line.product_code);
    return `<tr><td>${esc(line.product_code)}</td><td>${esc(line.manufacturer_product_code||'—')}</td><td>${esc(line.barcode||'—')}</td><td>${esc(line.product_name)}</td><td>${esc(line.group_level3||'—')}</td><td>${fa(line.order_quantity)}</td><td>${fa(line.received_qty)}</td><td>${fa(line.remaining_qty)}</td><td>${fa(line.closed_qty||0)}</td><td><input type="text" inputmode="decimal" autocomplete="off" data-balance-product="${esc(line.product_code)}" value="${esc(frozen?frozen.quantity:draft.get(String(line.product_code))??'')}" placeholder="حداکثر ${fa(limit)}" aria-label="${reopen?'بازگشایی':'بستن'} ${esc(line.product_name)} به عدد" ${pending||limit<=0?'disabled':''}></td></tr>`;
  }).join(''));
  replaceTableRows($('#fulfillmentBalanceHistory'),(info.history||[]).map(row=>{const item=identity.get(String(row.product_code))||{};return `<tr><td>${esc(formatRefreshDate(row.recorded_at))}</td><td>${esc(row.product_code)}</td><td>${esc(item.manufacturer_product_code||'—')}</td><td>${esc(item.barcode||'—')}</td><td>${esc(item.group_level3||'—')}</td><td>${Number(row.quantity)<0?'بازگشایی':'بستن'} ${fa(Math.abs(Number(row.quantity)))} عدد</td><td>${esc(row.reason)}</td><td>${esc(row.recorded_by)}</td></tr>`}).join('')||'<tr><td colspan="8">عملیاتی برای بستن یا بازگشایی مانده ثبت نشده است.</td></tr>');
  const statusLabels={checkbar_confirmed:'چک‌بار تأییدشده؛ هنوز به ورانگر منتقل نشده',pending:'در انتظار تعیین نتیجه',sent:'ثبت موفق',rejected:'رد شده'},stockLabels={waiting:'در انتظار انعکاس موجودی',reflected:'در موجودی منعکس شده',review:'نیازمند بررسی'};
  replaceTableRows($('#fulfillmentLinkedReceipts'),(info.linked_receipts||[]).map(row=>{const item=identity.get(String(row.product_code))||{};return `<tr><td>${fa(row.document_id)}</td><td>${esc(row.product_code)}</td><td>${esc(item.manufacturer_product_code||'—')}</td><td>${esc(item.barcode||'—')}</td><td>${esc(item.group_level3||'—')}</td><td>${fa(row.quantity)}</td><td>${esc(statusLabels[row.status]||row.status)}</td><td>${esc(stockLabels[row.stock_status]||row.stock_status||'—')}</td></tr>`}).join('')||'<tr><td colspan="8">هنوز رسیدی از چک‌بار به این سفارش متصل نشده است.</td></tr>');
  $('#fulfillmentBalanceReason').disabled=!!pending;
  if(pending)$('#fulfillmentBalanceReason').value=pending.reason;
  $('#fulfillmentBalanceMode').disabled=!!pending;
  $('#fillAllFulfillmentBalance').disabled=!!pending||fulfillmentBalanceState.busy;
  $('#fillAllFulfillmentBalance').textContent=reopen?'انتخاب کل ماندهٔ بسته‌شده':'انتخاب کل ماندهٔ سفارش';
  $('#saveFulfillmentBalance').textContent=pending?'پیگیری همان درخواست':reopen?'بازگشایی مانده':'خارج کردن مانده از چرخه';
  $('#saveFulfillmentBalance').disabled=fulfillmentBalanceState.busy||(!pending&&!info.lines.some(line=>fulfillmentBalanceLimit(line,reopen)>0));
  balanceNotice(fulfillmentBalanceState.error||(pending?'نتیجه درخواست قبلی هنوز قطعی نیست. برای جلوگیری از ثبت تکراری، همان درخواست پیگیری می‌شود.':reopen?'مقدار بازگشایی‌شده دوباره در راه محسوب می‌شود.':'مقدار هر کالا را وارد کنید یا «انتخاب کل ماندهٔ سفارش» را بزنید؛ سپس ثبت کنید.'),!!fulfillmentBalanceState.error);
  if(info.delivery_ended){
    for(const id of ['fulfillmentBalanceReason','fulfillmentBalanceMode','fillAllFulfillmentBalance','saveFulfillmentBalance'])$('#'+id).disabled=true;
    document.querySelectorAll('[data-balance-product]').forEach(input=>input.disabled=true);
    balanceNotice(`پایان تحویل ثبت شده است؛ مانده با تغییر چک‌بار باز نمی‌شود. ثبت‌کننده: ${info.completion?.recorded_by||'—'} · ${formatRefreshDate(info.completion?.recorded_at)}`);
  }
}

async function openFulfillmentBalance(id,mode=null){
  if(fulfillmentBalanceState.busy)return;
  try{
    await loadFulfillmentOrders();
    const order=fulfillmentState.orders.find(item=>Number(item.id)===Number(id));if(!order)return;
    fulfillmentBalanceState.order=order;
    fulfillmentBalanceState.error='';
    $('#fulfillmentBalanceReason').value='';
    $('#fulfillmentBalanceMode').value=mode||(Number(order.fulfillment.remaining_qty)>0?'close':'reopen');
    renderFulfillmentBalance();$('#fulfillmentBalanceDialog').showModal();
  }catch(error){toast(error.message,true)}
}

async function saveFulfillmentBalance(){
  const order=fulfillmentBalanceState.order;if(!order||fulfillmentBalanceState.busy)return;
  if(order.fulfillment.delivery_ended){balanceNotice('تحویل این سفارش پایان یافته است؛ بازگشایی مانده مجاز نیست.',true);return}
  fulfillmentBalanceState.error='';
  let payload=fulfillmentBalanceState.pending.get(order.id);
  if(!payload){
    try{
      // The neutral marker also supports running servers predating optional API reasons.
      const reopen=$('#fulfillmentBalanceMode').value==='reopen',reason=$('#fulfillmentBalanceReason').value.trim()||'بدون توضیح';
      const byCode=new Map(order.fulfillment.lines.map(line=>[String(line.product_code),line])),lines=[];
      for(const input of document.querySelectorAll('[data-balance-product]')){
        const line=byCode.get(input.dataset.balanceProduct),quantity=fulfillmentBalanceQuantity(input.value);
        if(!line||quantity>fulfillmentBalanceLimit(line,reopen))throw new Error('مقدار عملیات از مانده مجاز بیشتر است.');
        if(quantity>0)lines.push({product_code:line.product_code,quantity});
      }
      if(!lines.length)throw new Error('مقدار حداقل یک کالا را وارد کنید یا دکمهٔ «انتخاب کل مانده» را بزنید. دلیل اختیاری است.');
      const total=Number(lines.reduce((sum,line)=>sum+line.quantity,0).toFixed(3));
      if(!confirm(`${reopen?'بازگشایی':'بستن'} مانده ${order.preorder_number}: ${fa(total)} عدد در ${fa(lines.length)} قلم؟\nدلیل: ${reason}\n${reopen?'این مقدار دوباره در راه محسوب می‌شود.':'این مقدار از در راه خارج می‌شود و سابقه آن حفظ خواهد شد.'}`))return;
      payload={expected_revision:order.fulfillment.revision,request_id:checkbarRequestId(),reason,lines,reopen,confirmed:true};
      fulfillmentBalanceState.pending.set(order.id,payload);
    }catch(error){fulfillmentBalanceState.error=error.message;balanceNotice(error.message,true);return}
  }
  fulfillmentBalanceState.busy=true;renderFulfillmentBalance();
  try{
    await api(`/warehouse-assistant/api/fulfillment-orders/${order.id}/balance`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    fulfillmentBalanceState.pending.delete(order.id);
    $('#fulfillmentBalanceDialog').close();fulfillmentBalanceState.order=null;
    state.suggestions=null;state.automaticPreview=null;
    try{
      await loadFulfillmentOrders();
      if(typeof reloadWarehouseDataViews==='function')await reloadWarehouseDataViews();
      toast('مانده سفارش به‌روز شد و سابقه عملیات حفظ شد.');
    }catch(error){toast(`عملیات ثبت شد؛ بازخوانی نمایش انجام نشد: ${error.message}`,true)}
  }catch(error){
    // A definite client rejection has no unknown commit to replay. Timeouts/server errors retain the exact intent.
    if([400,401,403,404,409,422].includes(error.status))fulfillmentBalanceState.pending.delete(order.id);
    fulfillmentBalanceState.error=error.message;
  }finally{fulfillmentBalanceState.busy=false;if(fulfillmentBalanceState.order)renderFulfillmentBalance(true)}
}

document.addEventListener('DOMContentLoaded',()=>{
  $('#fulfillmentBalanceMode').addEventListener('change',()=>{fulfillmentBalanceState.error='';renderFulfillmentBalance()});
  $('#fillAllFulfillmentBalance').addEventListener('click',fillAllFulfillmentBalance);
  $('#saveFulfillmentBalance').addEventListener('click',saveFulfillmentBalance);
  $('#closeFulfillmentBalance').addEventListener('click',()=>{if(!fulfillmentBalanceState.busy)$('#fulfillmentBalanceDialog').close()});
  $('#fulfillmentBalanceDialog').addEventListener('cancel',event=>{if(fulfillmentBalanceState.busy)event.preventDefault()});
});
