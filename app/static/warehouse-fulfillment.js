const fulfillmentState={orders:[],snapshot:null,editing:null,editingSnapshotId:null,workflowFilter:'all'};
const deliveryFinishState={pending:new Map(),busy:false};
// Sent and delivery share a table, but not the user's working context.
const fulfillmentNavigation=new Map();
let fulfillmentScrollRestore=null;
function prepareFulfillmentNavigation(previous,next){
  if(previous===next)return;
  const table=$('#fulfillmentTable'),wrap=table?.closest('.table-wrap');
  const inputs=()=>[...(table?.querySelectorAll('[data-shared-column-filter]')||[])];
  if(['sent','fulfillment'].includes(previous)){
    fulfillmentNavigation.set(previous,{
      search:$('#fulfillmentSearch').value,status:$('#fulfillmentStatusFilter').value,workflow:fulfillmentState.workflowFilter,
      columns:Object.fromEntries(inputs().map(input=>[input.dataset.sharedColumnFilter,input.value])),
      sort:typeof sharedTableSorts!=='undefined'?sharedTableSorts.get(table):null,
      left:wrap?.scrollLeft||0,top:wrap?.scrollTop||0
    });
  }
  if(!['sent','fulfillment'].includes(next))return;
  const saved=fulfillmentNavigation.get(next)||{search:'',status:'open',workflow:'all',columns:{},left:0,top:0};
  $('#fulfillmentSearch').value=saved.search;$('#fulfillmentStatusFilter').value=saved.status;
  fulfillmentState.workflowFilter=saved.workflow;
  inputs().forEach(input=>input.value=saved.columns[input.dataset.sharedColumnFilter]||'');
  if(table&&typeof sharedTableSorts!=='undefined'){if(saved.sort)sharedTableSorts.set(table,saved.sort);else sharedTableSorts.delete(table)}
  fulfillmentScrollRestore={...saved,view:next};
}
function restoreFulfillmentNavigationScroll(){
  const saved=fulfillmentScrollRestore;if(!saved)return;
  fulfillmentScrollRestore=null;
  requestAnimationFrame(()=>{
    if(state.activeView!==saved.view)return;
    const wrap=$('#fulfillmentTable')?.closest('.table-wrap');
    if(wrap){wrap.scrollTop=saved.top;wrap.scrollLeft=saved.left;if(typeof rememberTableScroll==='function')rememberTableScroll(wrap)}
  });
}

function fulfillmentWorkflow(order){
  return order.supplier_portal?.workflow_status||order.supplier_portal?.status||'awaiting_link';
}

function fulfillmentFilterKeys(stage){
  return stage==='sent'?['all','unviewed','awaiting_supplier','changes_requested','awaiting_negin']:['all','supplier_confirmed','awaiting_delivery'];
}
function fulfillmentMatchesWorkflow(order,filter){
  if(filter==='all')return true;
  const workflow=fulfillmentWorkflow(order),portal=order.supplier_portal;
  const unviewed=workflow==='awaiting_supplier'&&portal?.publication_state==='published'&&!portal.first_viewed_at;
  if(filter==='unviewed')return unviewed;
  if(filter==='awaiting_supplier')return !unviewed&&['awaiting_supplier','draft'].includes(workflow);
  return workflow===filter;
}

function fulfillmentStage(order){
  // Preserve historical received/closed orders without fabricating supplier approval.
  if(!order.supplier_portal?.id&&(order.fulfillment?.received_qty>0||['received','closed'].includes(order.fulfillment?.status)))return 'delivery';
  if(order.order_stage)return order.order_stage;
  const workflow=fulfillmentWorkflow(order);
  if(['supplier_confirmed','awaiting_delivery'].includes(workflow))return 'delivery';
  return order.supplier_portal?.dispatch_sent||order.email_delivery?.status==='sent'?'sent':'draft';
}

function fulfillmentPortalAction(order){
  const workflow=fulfillmentWorkflow(order);
  if(!['awaiting_link','awaiting_negin'].includes(workflow))return '';
  const portalId=Number(order.supplier_portal?.id)||0;
  const kind=order.source_kind==='manual'?'supplier_order':'automatic_preorder';
  const documentId=kind==='supplier_order'?(Number(order.source_supplier_order_id)||Number(order.id)):Number(order.id);
  return portalId&&workflow==='awaiting_negin'?`<button type="button" class="secondary-action" data-supplier-review="${portalId}">بررسی تغییرات تأمین‌کننده</button>`:`<button type="button" class="secondary-action" data-order-portal-kind="${kind}" data-order-portal-id="${documentId}">قرار دادن در کارتابل تأمین‌کننده</button>`;
}

function receiptRate(line){return Math.max(1,Number(line.conversion_rate)||1)}
function receiptCartons(units,line){return String(Number((Number(units)/receiptRate(line)).toFixed(6)))}
function receiptParts(units,line){
  const cartons=Math.floor(Number(units)/receiptRate(line));
  return {cartons:String(cartons),units:String(Number((Number(units)-cartons*receiptRate(line)).toFixed(6)))};
}
function receiptQuantityLabel(units,line){
  const parts=receiptParts(units,line);
  return `${fa(parts.cartons)} کارتن${Number(parts.units)?` + ${fa(parts.units)} عدد`:''}`;
}
function receiptLooseInput(input){return input.closest('tr').querySelector('[data-received-units]')}
// Two additive inputs; the ledger/API remains cumulative base units.
function receiptBaseUnits(line,value,looseValue){
  const text=normalizeSearchText(value),loose=normalizeSearchText(looseValue);
  if(!/^\d+$/.test(text)||!/^\d+(?:\.\d+)?$/.test(loose))throw new Error('کارتن را صحیح و عدد را نامنفی وارد کنید؛ مثلاً ۲ کارتن و ۵ عدد.');
  const units=Number((Number(text)*receiptRate(line)+Number(loose)).toFixed(6));
  if(!Number.isFinite(units))throw new Error('مقدار دریافت نامعتبر است.');
  if(units<line.received_qty||units>line.order_quantity)throw new Error('دریافت تجمعی باید بین دریافت قبلی و تعداد سفارش باشد.');
  return units;
}

function fillCompleteReceipt(code=null){
  const order=fulfillmentState.editing;if(!order||order.fulfillment.status==='received'||order.fulfillment.manual_receive_allowed===false)return;
  const byCode=new Map(order.fulfillment.lines.map(line=>[String(line.product_code),line]));
  document.querySelectorAll('[data-received-product]').forEach(input=>{
    const line=byCode.get(input.dataset.receivedProduct);
    if(line&&!input.disabled&&(code===null||String(code)===String(line.product_code))){
      const parts=receiptParts(line.order_quantity,line);input.value=parts.cartons;receiptLooseInput(input).value=parts.units;
    }
  });
  updateReceiptDraftSummary();
}

function updateReceiptDraftSummary(){
  const order=fulfillmentState.editing;if(!order)return;
  let total=0,valid=true;
  const byCode=new Map(order.fulfillment.lines.map(line=>[String(line.product_code),line]));
  document.querySelectorAll('[data-received-product]').forEach(input=>{
    const loose=receiptLooseInput(input);
    try{const line=byCode.get(input.dataset.receivedProduct);total+=receiptBaseUnits(line,input.value,loose.value);input.removeAttribute('aria-invalid');loose.removeAttribute('aria-invalid')}
    catch{valid=false;input.setAttribute('aria-invalid','true');loose.setAttribute('aria-invalid','true')}
  });
  $('#fulfillmentDraftSummary').textContent=valid?`جمع دریافت تجمعی پس از ثبت: ${fa(total)} عدد`:'مقدار دریافت ردیف مشخص‌شده را اصلاح کنید.';
}

function fulfillmentStatusLabel(info){
  if(info.delivery_ended)return '<span class="fulfillment-status">پایان تحویل</span>';
  if(info.status==='closed')return '<span class="fulfillment-status">مانده بسته شده</span>';
  if(info.status==='received')return '<span class="fulfillment-status is-received">دریافت کامل</span>';
  if(info.received_qty>0)return '<span class="fulfillment-status is-partial">دریافت ناقص</span>';
  return '<span class="fulfillment-status">در انتظار دریافت</span>';
}

function supplierConfirmationLabel(portal){
  if(!portal)return '<span class="fulfillment-status">آمادهٔ قرار دادن در کارتابل</span>';
  if(portal.legacy_delivery_sent&&!portal.dispatch_sent)return '<span class="fulfillment-status">ارسال قدیمی؛ منتظر لینک کارتابل</span>';
  const workflow=portal.workflow_status||portal.status;
  const labels={awaiting_link:'آمادهٔ قرار دادن در کارتابل',awaiting_supplier:'در انتظار واکنش تأمین‌کننده',draft:'در حال تکمیل پاسخ تأمین‌کننده',supplier_confirmed:'تأییدشده با تأمین‌کننده',awaiting_negin:'منتظر تأیید نگین',changes_requested:'در انتظار اصلاح تأمین‌کننده',awaiting_delivery:'در انتظار تحویل سفارش',rejected:'پاسخ ردشده',cancelled:'لغوشده'};
  const cls=['supplier_confirmed','awaiting_delivery'].includes(workflow)?' is-received':workflow==='awaiting_negin'?' is-partial':'';
  return `<span class="fulfillment-status${cls}" title="تحویل درخواستی: ${esc(portal.requested_delivery_date||'—')} · پیشنهاد تأمین‌کننده: ${esc(portal.proposed_delivery_date||'—')}">${esc(portal.publication_state==='published'&&workflow==='awaiting_supplier'?'قرار گرفته در کارتابل':labels[workflow]||workflow)}</span>${portal.pending_quantity_changes?`<small class="order-delivery-pending">درخواست تغییر تعداد ${fa(portal.pending_quantity_changes)} قلم · منتظر تأیید شما</small>`:''}`;
}

function portalViewedLabel(portal){
  if(portal?.first_viewed_at)return `مشاهده شد<small>${esc(formatRefreshDate(portal.first_viewed_at))}</small>`;
  return portal?.publication_state==='published'?'هنوز مشاهده نشده':'سابقهٔ مشاهده نامشخص';
}
function portalNotificationLabel(portal){
  return ({sent:'اطلاع‌رسانی شد',pending_or_unknown:'در جریان / نتیجه نامشخص',not_sent:'اطلاع‌رسانی نشده'})[portal?.notification_status]||'—';
}

function fulfillmentActions(order){
  if(fulfillmentStage(order)==='sent'){
    const kind=order.source_kind==='manual'?'supplier_order':'automatic_preorder';
    const id=kind==='supplier_order'?order.source_supplier_order_id:order.id;
    return `${order.supplier_portal?.id?`<button type="button" class="${fulfillmentWorkflow(order)==='awaiting_negin'?'primary':'secondary-action'}" data-workflow-primary="true" data-supplier-review="${order.supplier_portal.id}">${fulfillmentWorkflow(order)==='awaiting_negin'?'بررسی تغییرات تأمین‌کننده':'مشاهده پاسخ و وضعیت'}</button>`:`<button type="button" class="secondary-action" data-order-portal-kind="${kind}" data-order-portal-id="${id}">قرار دادن در کارتابل تأمین‌کننده</button>`}${order.supplier_portal?.can_withdraw?`<button type="button" class="secondary-action" data-portal-withdraw="${order.supplier_portal.id}" data-revision="${order.supplier_portal.revision}">حذف از کارتابل</button>`:''}`;
  }
  const awaiting=order.fulfillment.status==='awaiting_supply';
  const portalAction=fulfillmentPortalAction(order);
  const checkbarAction=awaiting?`<button class="primary" data-workflow-primary="true" type="button" data-fulfillment-checkbar="${order.id}">چک‌بار مانده</button>`:'';
  const finishAction=!order.fulfillment.delivery_ended?`<button class="secondary-action" type="button" data-fulfillment-finish="${order.id}"${deliveryFinishState.busy?' disabled':''}>${deliveryFinishState.pending.has(order.id)?'پیگیری پایان تحویل':'پایان تحویل'}</button>`:'';
  const primaryAction=portalAction||checkbarAction;
  const menuCheckbar=portalAction?checkbarAction:'';
  return `<div class="preorder-actions fulfillment-work-actions">${primaryAction}${finishAction}<details class="row-actions-menu"><summary aria-label="سایر عملیات سفارش ${esc(order.preorder_number)}">سایر عملیات</summary><div>${menuCheckbar}<button class="secondary-action" type="button" data-fulfillment-balance="${order.id}">دریافت‌ها و ماندهٔ سفارش</button><a href="/warehouse-assistant/api/automatic-preorders/${order.id}/document.xlsx" aria-label="دانلود اکسل ${esc(order.preorder_number)}">اکسل</a></div></details></div>`;
}

async function finishFulfillmentDelivery(id){
  if(deliveryFinishState.busy)return;
  if(!state.bootstrap?.delivery_completion_supported){toast('پایان تحویل پس از فعال‌سازی نسخهٔ جدید سرویس در دسترس است.',true);return}
  let payload=deliveryFinishState.pending.get(id);
  deliveryFinishState.busy=true;
  try{
    if(!payload){
      await loadFulfillmentOrders();
      const order=fulfillmentState.orders.find(item=>Number(item.id)===Number(id));
      if(!order||order.fulfillment.delivery_ended)return;
      if(!confirm(`تحویل سفارش ${order.preorder_number} پایان یابد؟\nماندهٔ دریافت‌نشده: ${fa(order.fulfillment.remaining_qty)} عدد.\nمانده بسته می‌شود؛ حتی حذف یا اصلاح چک‌بار مرتبط، این سفارش را به صف دریافت برنمی‌گرداند. مقدار دریافت واقعی و سوابق حفظ می‌شوند.`))return;
      payload={expected_revision:order.fulfillment.revision,request_id:checkbarRequestId(),confirmed:true};
      deliveryFinishState.pending.set(id,payload);
    }
    renderFulfillmentOrders();
    await api(`/warehouse-assistant/api/fulfillment-orders/${id}/finish`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    deliveryFinishState.pending.delete(id);state.suggestions=null;state.automaticPreview=null;
    try{await loadFulfillmentOrders();if(typeof reloadWarehouseDataViews==='function')await reloadWarehouseDataViews();toast('پایان تحویل ثبت شد؛ این سفارش دیگر به صف دریافت برنمی‌گردد.')}
    catch(error){toast(`پایان تحویل ثبت شد؛ فهرست را بازخوانی کنید: ${error.message}`,true)}
  }catch(error){
    if([400,401,403,404,409,422].includes(error.status))deliveryFinishState.pending.delete(id);
    toast(deliveryFinishState.pending.has(id)?'نتیجهٔ پایان تحویل قطعی نیست؛ «پیگیری پایان تحویل» را بزنید.':error.message,true);
  }finally{deliveryFinishState.busy=false;renderFulfillmentOrders()}
}

function fulfillmentMatchesStatus(info,filter){
  if(filter==='all')return true;
  if(filter==='partial')return info.status==='awaiting_supply'&&Number(info.received_qty)>0;
  if(filter==='closed'||filter==='received')return info.status===filter;
  return info.status==='awaiting_supply';
}

async function openCheckbarForOrder(id){
  if(!state.bootstrap?.delivery_completion_supported){toast('چک‌بار مانده پس از فعال‌سازی نسخهٔ جدید سرویس در دسترس است.',true);return}
  const order=fulfillmentState.orders.find(item=>Number(item.id)===Number(id));
  if(!order||order.fulfillment.status!=='awaiting_supply')return;
  try{
    await openCheckbar();
    if(!$('#checkbarDialog').open)return;
    $('#checkbarWarehouse').value=order.warehouse_code;
    await checkbarLoadContext(true);
    $('#checkbarSupplier').value=order.supplier;
    await checkbarLoadContext();
    if(!$('#checkbarDialog').open)return;
    checkbarState.remainingOrderId=Number(id);
    $('#checkbarIncludeOrderItems').checked=true;
    await checkbarPrepare();
    $('#checkbarPrepare').disabled=!$('#checkbarSupplier').value;
    $('#checkbarSourceStatus').textContent=`چک‌بار ماندهٔ ${order.preorder_number}؛ تعداد واقعی دریافت را وارد کنید.`;
  }catch(error){toast(error.message,true)}
}

async function loadFulfillmentOrders(){
  if(!has('warehouse.order.draft'))return;
  const result=await api('/warehouse-assistant/api/fulfillment-orders?include_completed=true');
  fulfillmentState.orders=result.orders||[];fulfillmentState.snapshot=result.snapshot;
  renderFulfillmentOrders();
}

function renderFulfillmentOrders(){
  const stage=state.activeView==='sent'?'sent':'delivery';
  const stageOrders=fulfillmentState.orders.filter(order=>fulfillmentStage(order)===stage);
  const open=stageOrders.filter(order=>order.fulfillment.status==='awaiting_supply');
  $('#fulfillmentMenuBadge').textContent=fa(fulfillmentState.orders.filter(order=>fulfillmentStage(order)==='delivery'&&order.fulfillment.status==='awaiting_supply').length);
  $('#sentMenuBadge').textContent=fa(fulfillmentState.orders.filter(order=>fulfillmentStage(order)==='sent').length);
  $('#orderStageTitle').textContent=stage==='sent'?'کارتابل تأمین‌کننده':'پیگیری تحویل';
  $('#orderStageHelp').textContent=stage==='sent'?'پیگیری پاسخ تأمین‌کننده؛ تغییر تعداد یا تاریخ تحویل فقط با تأیید نگین وارد صف تحویل می‌شود.':'سفارش‌های دارای تأیید تأمین‌کننده و سوابق دریافت‌های قبلی؛ پیگیری تحویل کامل یا جزئی.';
  const filterKeys=fulfillmentFilterKeys(stage);
  if(!filterKeys.includes(fulfillmentState.workflowFilter))fulfillmentState.workflowFilter='all';
  document.querySelectorAll('[data-workflow-filter]').forEach(node=>{
    node.hidden=!filterKeys.includes(node.dataset.workflowFilter);
    node.setAttribute('aria-pressed',String(node.dataset.workflowFilter===fulfillmentState.workflowFilter));
  });
  const query=normalizeSearchText($('#fulfillmentSearch').value);
  const filter=$('#fulfillmentStatusFilter').value;
  $('#fulfillmentStatusFilter').closest('label').hidden=stage==='sent';
  const scopeOrders=stage==='sent'?stageOrders:stageOrders.filter(order=>fulfillmentMatchesStatus(order.fulfillment,filter));
  const workflowCounts=Object.fromEntries(filterKeys.map(key=>[key,scopeOrders.filter(order=>fulfillmentMatchesWorkflow(order,key)).length]));
  document.querySelectorAll('[data-workflow-count]').forEach(node=>node.textContent=fa(workflowCounts[node.dataset.workflowCount]||0));
  const rows=scopeOrders.filter(order=>
    fulfillmentMatchesWorkflow(order,fulfillmentState.workflowFilter)&&
    normalizeSearchText(`${order.preorder_number} ${order.order_number||''} ${order.supplier} ${order.warehouse_name} ${order.delivery_date||''} ${order.pending_delivery_date||''}`).includes(query));
  $('#fulfillmentSummary').textContent=`${fa(open.length)} سفارش باز در این مرحله · ${fa(rows.length)} سفارش در نمایش`;
  replaceTableRows($('#fulfillmentRows'),rows.map(order=>`<tr><td data-fulfillment-column="number" class="fulfillment-number" title="${esc(order.preorder_number)}">${esc(order.preorder_number)}<small>${order.source_kind==='manual'?'سفارش دستی':'سفارش اتوماتیک'}</small></td><td data-fulfillment-column="supplier">${expandableCellText(order.supplier)}</td><td data-fulfillment-column="supplier-confirmation">${supplierConfirmationLabel(order.supplier_portal)}</td><td data-fulfillment-column="warehouse">${esc(order.warehouse_name)}</td><td data-fulfillment-column="sent" class="fulfillment-number">${esc(formatRefreshDate(order.dispatched_at))}</td><td data-fulfillment-column="delivery_date">${orderDeliveryDateCell(order)}</td><td data-fulfillment-column="viewed">${portalViewedLabel(order.supplier_portal)}</td><td data-fulfillment-column="notification">${portalNotificationLabel(order.supplier_portal)}</td><td data-fulfillment-column="remaining" class="fulfillment-remaining"><div>دریافت ${fa(order.fulfillment.received_qty||0)} عدد</div><strong>مانده ${fa(order.fulfillment.remaining_cartons)} کارتن</strong></td><td data-fulfillment-column="status">${fulfillmentStatusLabel(order.fulfillment)}</td><td data-fulfillment-column="actions">${fulfillmentActions(order)}</td></tr>`).join('')||`<tr><td colspan="11" class="empty-cell">${query?'سفارشی با این جست‌وجو پیدا نشد.':'در این مرحله سفارشی وجود ندارد.'}</td></tr>`);
  restoreFulfillmentNavigationScroll();
}

async function openFulfillmentReceipt(id){
  try{
    await loadFulfillmentOrders();
    const order=fulfillmentState.orders.find(item=>item.id===id);if(!order)return;
    fulfillmentState.editing=order;
    fulfillmentState.editingSnapshotId=fulfillmentState.snapshot?.id;
    $('#fulfillmentReceiptTitle').textContent=`دریافت ${order.preorder_number} · ${order.supplier}`;
    const completed=order.fulfillment.status==='received'||order.fulfillment.manual_receive_allowed===false;
    replaceTableRows($('#fulfillmentReceiptLines'),order.fulfillment.lines.map(line=>`<tr><td>${esc(line.product_code)}</td><td>${esc(line.manufacturer_product_code||'—')}</td><td>${esc(line.barcode||'—')}</td><td>${esc(line.product_name)}<small class="receipt-pack-size">هر کارتن ${fa(receiptRate(line))} عدد</small></td><td class="receipt-ordered">${receiptQuantityLabel(line.order_quantity,line)}</td><td>${receiptQuantityLabel(line.received_qty,line)}</td><td class="receipt-quantity-cell"><input data-received-product="${esc(line.product_code)}" type="text" inputmode="numeric" autocomplete="off" value="${receiptParts(line.received_qty,line).cartons}" aria-describedby="fulfillmentReceiptHelp" aria-label="دریافت تجمعی کارتن ${esc(line.product_name)}" ${completed?'disabled':''}></td><td class="receipt-quantity-cell"><input data-received-units type="text" inputmode="decimal" autocomplete="off" value="${receiptParts(line.received_qty,line).units}" aria-describedby="fulfillmentReceiptHelp" aria-label="دریافت تجمعی عدد ${esc(line.product_name)}" ${completed?'disabled':''}></td><td><button type="button" class="secondary-action receipt-full-button" data-receive-full="${esc(line.product_code)}" aria-label="دریافت کامل ${esc(line.product_name)}" ${completed||line.received_qty>=line.order_quantity?'disabled':''}>${line.received_qty>=line.order_quantity?'کامل شده':'دریافت کامل'}</button></td><td>${esc(line.group_level3||'—')}</td></tr>`).join(''));
    $('#fillAllFulfillmentReceipt').disabled=completed;
    $('#fulfillmentOrderSummary').textContent=`${fa(order.fulfillment.lines.length)} قلم · جمع سفارش ${fa(order.fulfillment.lines.reduce((sum,line)=>sum+Number(line.order_quantity)/receiptRate(line),0))} کارتن`;
    updateReceiptDraftSummary();
    $('#fulfillmentReceiptReference').value='';$('#fulfillmentInventoryReflected').checked=false;
    $('#fulfillmentReceiptReference').disabled=completed;
    $('#fulfillmentInventoryReflected').disabled=completed;
    $('#saveFulfillmentReceipt').disabled=completed;
    $('#fulfillmentReceiptDialog').showModal();
  }catch(error){toast(error.message,true)}
}

async function saveFulfillmentReceipt(){
  const order=fulfillmentState.editing;if(!order)return;
  if(order.fulfillment.manual_receive_allowed===false||order.fulfillment.status==='received')return;
  const reference=$('#fulfillmentReceiptReference').value.trim();
  if(!reference||!$('#fulfillmentInventoryReflected').checked){toast('شماره رسید و تأیید بازخوانی موجودی پس از ثبت رسید در ورانگر لازم است.',true);return}
  const inputs=[...document.querySelectorAll('[data-received-product]')];
  let receiptLines;
  try{
    const byCode=new Map(order.fulfillment.lines.map(line=>[String(line.product_code),line]));
    receiptLines=inputs.map(input=>({product_code:input.dataset.receivedProduct,received_qty:receiptBaseUnits(byCode.get(input.dataset.receivedProduct),input.value,receiptLooseInput(input).value)}));
  }catch(error){updateReceiptDraftSummary();toast(error.message,true);return}
  const button=$('#saveFulfillmentReceipt');button.disabled=true;
  try{
    await api(`/warehouse-assistant/api/fulfillment-orders/${order.id}/receive`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      expected_revision:order.fulfillment.revision,snapshot_id:fulfillmentState.editingSnapshotId,
      inventory_reflected:true,reference,lines:receiptLines})});
    $('#fulfillmentReceiptDialog').close();fulfillmentState.editing=null;
    state.suggestions=null;state.automaticPreview=null;
    await loadFulfillmentOrders();
    toast('دریافت ثبت شد؛ فقط باقی‌ماندهٔ بار در راه در پیشنهادهای بعدی لحاظ می‌شود.');
  }catch(error){toast(error.message,true)}finally{button.disabled=false}
}

document.addEventListener('DOMContentLoaded',()=>{
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-portal-withdraw]');if(!button||button.disabled)return;
    if(!confirm('سفارش از کارتابل برداشته و به پیش‌سفارش برگردد؟ فقط اگر هنوز مشاهده نشده باشد انجام می‌شود.'))return;
    button.disabled=true;
    try{
      const result=await api(`/warehouse-assistant/api/supplier-portal/orders/${button.dataset.portalWithdraw}/withdraw`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed:true,expected_revision:Number(button.dataset.revision)})});
      await Promise.all([loadOrders(),loadAutomaticPreorders()]);selectPreparedOrderKind(result.document_kind==='supplier_order'?'manual':'system');toast('از کارتابل برداشته شد و به پیش‌سفارش برگشت.');
    }catch(error){toast(error.message,true);await loadFulfillmentOrders()}finally{button.disabled=false}
  });
  $('#refreshFulfillmentButton').addEventListener('click',()=>loadFulfillmentOrders().catch(error=>toast(error.message,true)));
  $('#fulfillmentSearch').addEventListener('input',renderFulfillmentOrders);
  $('#fulfillmentStatusFilter').addEventListener('change',renderFulfillmentOrders);
  $('#fulfillmentWorkflowFilters').addEventListener('click',event=>{const button=event.target.closest('[data-workflow-filter]');if(!button)return;fulfillmentState.workflowFilter=button.dataset.workflowFilter;document.querySelectorAll('[data-workflow-filter]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));renderFulfillmentOrders()});
  $('#fulfillmentRows').addEventListener('click',event=>{
    const receipt=event.target.closest('[data-fulfillment-receive]');if(receipt)openFulfillmentReceipt(Number(receipt.dataset.fulfillmentReceive));
    const checkbar=event.target.closest('[data-fulfillment-checkbar]');if(checkbar)openCheckbarForOrder(Number(checkbar.dataset.fulfillmentCheckbar));
    const balance=event.target.closest('[data-fulfillment-balance]');if(balance)openFulfillmentBalance(Number(balance.dataset.fulfillmentBalance));
    const finish=event.target.closest('[data-fulfillment-finish]');if(finish&&!finish.disabled)finishFulfillmentDelivery(Number(finish.dataset.fulfillmentFinish));
  });
  $('#saveFulfillmentReceipt').addEventListener('click',saveFulfillmentReceipt);
  $('#fillAllFulfillmentReceipt').addEventListener('click',()=>fillCompleteReceipt());
  $('#fulfillmentReceiptLines').addEventListener('click',event=>{const button=event.target.closest('[data-receive-full]');if(button)fillCompleteReceipt(button.dataset.receiveFull)});
  $('#fulfillmentReceiptLines').addEventListener('input',updateReceiptDraftSummary);
  $('#closeFulfillmentReceipt').addEventListener('click',()=>$('#fulfillmentReceiptDialog').close());
});
