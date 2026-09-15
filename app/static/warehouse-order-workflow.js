// One explicit portal-link composer for manual and system orders.
const orderPortalState={order:null,kind:null,busy:false,editing:null};
// One save/dirty-state contract for both existing draft editors. No live side effects
// occur until saveDraftEditor sends its single, version-checked request.
const draftEditorConfig={
  supplier_order:{dialog:'#manualEditDialog',date:'#manualDeliveryDate',inputs:'#manualEditLines [data-manual-cartons]',feedback:'#manualDraftStatus'},
  automatic_preorder:{dialog:'#preorderPreviewDialog',date:'#previewDeliveryDate',inputs:'#previewPreorderLines .preview-cartons',feedback:'#previewDeliveryFeedback'}
};
const draftEditorSessions=new Map();
let draftExitRequest=null;
function readDraftEditor(kind){
  const config=draftEditorConfig[kind];
  const lines=[...document.querySelectorAll(config.inputs)].map(input=>({
    product_code:input.dataset.manualCartons||input.closest('tr').dataset.productCode,
    cartons:normalizeSearchText(input.value)
  })).sort((a,b)=>a.product_code.localeCompare(b.product_code));
  return {delivery_date:normalizeSearchText($(config.date).value),lines};
}
function draftEditorDirty(kind){
  const session=draftEditorSessions.get(kind);
  return Boolean(session&&JSON.stringify(readDraftEditor(kind))!==session.baseline);
}
function beginDraftEditor(kind,{dateOnly=false}={}){
  draftEditorSessions.set(kind,{baseline:JSON.stringify(readDraftEditor(kind)),busy:false,dateOnly});
  updateDraftEditorStatus(kind);
}
function updateDraftEditorStatus(kind){
  const node=$(draftEditorConfig[kind].feedback);if(!node)return;
  if(draftEditorSessions.get(kind)?.dateOnly){node.textContent=draftEditorDirty(kind)?'تغییر تاریخ ذخیره نشده است.':'تعدادها قفل است؛ تاریخ تا پیش از انتشار قابل ویرایش است.';return}
  node.textContent=draftEditorDirty(kind)?'تغییرات ذخیره نشده؛ تاریخ و تعداد با هم ذخیره می‌شوند.':'تاریخ و تعداد با «ذخیره تغییرات» ثبت می‌شوند؛ صفر یعنی حذف قلم.';
}
function canCloseDraftEditor(kind){
  return !draftEditorSessions.get(kind)?.busy&&!draftEditorDirty(kind);
}
function requestDraftEditorClose(kind,close){
  if(draftEditorSessions.get(kind)?.busy)return;
  if(canCloseDraftEditor(kind)){close();return}
  draftExitRequest={kind,close};$('#draftExitError').textContent='';
  if(!$('#draftExitDialog').open)$('#draftExitDialog').showModal();
}
async function resolveDraftEditorExit(action){
  const request=draftExitRequest;if(!request)return;
  if(action==='keep'){$('#draftExitDialog').close();draftExitRequest=null;return}
  if(action==='discard'){$('#draftExitDialog').close();draftExitRequest=null;request.close();return}
  const buttons=[...$('#draftExitDialog').querySelectorAll('button')];buttons.forEach(button=>button.disabled=true);
  try{
    if(request.kind==='supplier_order')await saveManualEdit({preventDefault(){}});
    else if(currentPreviewPreorder()?.can_edit)await savePreorderPreview();else await savePreviewDeliveryDate();
    if(canCloseDraftEditor(request.kind)){$('#draftExitDialog').close();draftExitRequest=null;request.close()}
    else $('#draftExitError').textContent='ذخیره کامل نشد؛ تغییرات حفظ شده است. به فرم برگردید و خطا را بررسی کنید.';
  }finally{buttons.forEach(button=>button.disabled=false)}
}
async function saveDraftEditor(kind,order){
  const session=draftEditorSessions.get(kind);
  if(!session||session.busy)throw new Error('فرم در حال ذخیره است؛ منتظر نتیجه بمانید.');
  if(state.bootstrap?.draft_editor_atomic_supported!==true)throw new Error('ذخیرهٔ یکپارچه هنوز روی سرویس فعال نیست؛ تغییرات فرم حفظ شده است. پس از فعال‌سازی نسخهٔ جدید، صفحه را بازخوانی کنید.');
  const draft=readDraftEditor(kind);
  if(draft.delivery_date&&!/^\d{4}\/\d{2}\/\d{2}$/.test(draft.delivery_date))throw new Error('تاریخ شمسی را مانند ۱۴۰۵/۰۶/۲۵ وارد کنید.');
  if(draft.lines.some(line=>!/^\d+$/.test(line.cartons)||Number(line.cartons)>1000000)||!draft.lines.some(line=>Number(line.cartons)>0))throw new Error('تعداد کارتن باید صحیح و بین صفر تا یک میلیون باشد؛ حداقل یک قلم باید باقی بماند.');
  const dialog=$(draftEditorConfig[kind].dialog);
  const controls=[...dialog.querySelectorAll('input,select,button')].map(node=>[node,node.disabled]);
  session.busy=true;dialog.setAttribute('aria-busy','true');controls.forEach(([node])=>node.disabled=true);
  try{
    const result=await api(`/warehouse-assistant/api/${kind==='supplier_order'?'supplier-orders':'automatic-preorders'}/${order.id}/lines`,{
      method:kind==='supplier_order'?'POST':'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({lines:draft.lines.map(line=>({...line,cartons:Number(line.cartons)})),delivery_date:draft.delivery_date,expected_token:kind==='automatic_preorder'?state.previewExpectedToken:order.email_send_token})
    });
    session.baseline=JSON.stringify(draft);
    return result.preorder||result;
  }finally{
    session.busy=false;dialog.removeAttribute('aria-busy');controls.forEach(([node,disabled])=>node.disabled=disabled);
  }
}
function draftOrderActions(order,kind){
  if(order.deleted)return '';
  const manual=kind==='supplier_order',id=Number(order.id);
  const approved=manual?order.is_approved:['approved','send_requested'].includes(order.status);
  const unavailable=order.dispatch_locked===undefined?'وضعیت مجاز عملیات دریافت نشده؛ فهرست را بازخوانی کنید.':order.dispatch_locked?'پس از شروع ارسال یا نتیجه نامشخص، تغییر سفارش مجاز نیست.':'';
  const primary=!unavailable?(approved?'publish':order.can_approve===true?'approve':order.can_edit===true?'edit':''):'';
  const button=(label,attributes,allowed,reason,name)=>`<button type="button" class="${allowed&&!unavailable&&primary===name?'primary':'secondary-action'}" ${attributes} ${allowed&&!unavailable&&primary===name?'data-workflow-primary="true"':''} ${allowed&&!unavailable?'':`disabled title="${esc(unavailable||reason)}"`}>${label}</button>`;
  const action=name=>manual?`data-manual-action="${name}" data-manual-id="${id}"`:`data-preorder-action="${name}" data-preorder-id="${id}"`;
  return button('تأیید',action('approve'),order.can_approve===true&&!approved,approved?'سفارش قبلاً تأیید شده است.':'تأیید این سفارش در وضعیت فعلی مجاز نیست؛ وضعیت سفارش را بازخوانی کنید.','approve')+
    button('لغو تأیید',action('revoke-approval'),order.can_revoke_approval===true,'این سفارش هنوز تأیید نشده است.')+
    button('ویرایش',manual?`data-manual-edit="${id}"`:`data-preorder-edit="${id}"`,order.can_edit===true||order.can_revoke_approval===true,'این سفارش قابل ویرایش نیست.','edit')+
    button('تاریخ تحویل',`data-order-date-kind="${kind}" data-order-date-id="${id}"`,order.can_edit_delivery_date===true,'تاریخ پس از ارسال مستقیم قابل تغییر نیست.')+
    button('حذف',manual?`data-manual-delete="${id}" data-manual-number="${esc(order.order_number)}"`:action('delete'),order.can_delete===true,'این سفارش قابل حذف نیست.')+
    orderPortalButtons({...order,can_send_portal:order.can_send_portal===true&&!unavailable},kind);
}
function orderPortalButtons(order,kind){
  const enabled=order.can_send_portal===true&&!order.dispatch_locked;
  const approved=kind==='supplier_order'?order.is_approved:['approved','send_requested'].includes(order.status);
  const reason=order.dispatch_locked?'ارسال شروع شده است؛ پیش از اقدام دوباره، وضعیت را بررسی کنید.':order.can_send_portal===undefined?'وضعیت انتشار دریافت نشده؛ فهرست را بازخوانی کنید.':!approved?'ابتدا سفارش را تأیید کنید.':'قرار دادن در کارتابل در وضعیت فعلی مجاز نیست؛ وضعیت را بازخوانی کنید.';
  return `<button type="button" class="${enabled?'primary':'secondary-action'}" data-order-portal-kind="${kind}" data-order-portal-id="${order.id}" ${enabled?'data-workflow-primary="true"':`disabled title="${esc(reason)}"`}>قرار دادن در کارتابل تأمین‌کننده</button>${order.dispatch_locked&&order.order_stage==='draft'?'<small role="status">نتیجه ارسال نامشخص؛ نیازمند بررسی</small>':''}`;
}
async function freshWorkflowOrder(kind,id){
  const result=await api(`/warehouse-assistant/api/${kind==='supplier_order'?'supplier-orders':'automatic-preorders'}/${id}`);
  return result.preorder||result;
}
async function openOrderPortal(kind,id){
  if(orderPortalState.busy)return;
  if(!state.bootstrap?.supplier_portal_publication_supported)throw new Error('نسخه جدید کارتابل هنوز روی سرویس فعال نشده است؛ صفحه را پس از راه‌اندازی مجدد بازخوانی کنید.');
  const order=await freshWorkflowOrder(kind,id);
  if(!order.can_send_portal)throw new Error('فقط سفارش تأییدشده و خارج از کارتابل قابل قرار دادن است.');
  orderPortalState.order=order;orderPortalState.kind=kind;
  $('#orderPortalSummary').textContent=`${order.order_number||order.preorder_number} · ${order.supplier} · ${order.warehouse_name}`;
  $('#orderPortalUsername').value=order.contact_mobile||'';
  $('#orderPortalMobile').value=order.contact_mobile||'';$('#orderPortalEmail').value='';
  if(state.bootstrap?.supplier_portal_shared_access_supported){
    const recipient=await api(`/warehouse-assistant/api/supplier-portal/order-recipient?document_kind=${kind}&document_id=${id}`);
    if(recipient.username)$('#orderPortalUsername').value=recipient.username;
    $('#orderPortalMobile').value=recipient.mobile??recipient.username??order.contact_mobile??'';
  }
  $('#orderPortalDate').value=order.requested_delivery_date||order.supplier_portal?.requested_delivery_date||'';
  $('#orderPortalDate').readOnly=false;$('#orderPortalError').textContent='';
  $('#orderPortalAccountLink').href='/supplier-portal-admin';
  $('#orderPortalDialog').showModal();
}
async function sendOrderPortal(event){
  event.preventDefault();if(orderPortalState.busy||!orderPortalState.order)return;
  if(!$('#orderPortalForm').reportValidity())return;
  const kind=orderPortalState.kind,username=normalizeSearchText($('#orderPortalUsername').value).trim();
  const date=normalizeSearchText($('#orderPortalDate').value);
  if(!/^09\d{9}$/.test(username)){$('#orderPortalError').textContent='نام کاربری باید شماره موبایل ۱۱ رقمی با ۰۹ باشد.';return}
  if(!/^\d{4}\/\d{2}\/\d{2}$/.test(date)){$('#orderPortalError').textContent='تاریخ شمسی را مانند ۱۴۰۵/۰۶/۲۵ وارد کنید.';return}
  const notifications=[['sms',$('#orderPortalMobile').value.trim()],['email',$('#orderPortalEmail').value.trim()]].filter(([,recipient])=>recipient);
  orderPortalState.busy=true;$('#orderPortalError').textContent='در حال قرار دادن در کارتابل…';
  $('#orderPortalForm').querySelectorAll('button,input,select').forEach(node=>node.disabled=true);
  let placed=false;
  try{
    let order=orderPortalState.order;
    if(order.staff_delivery_date!==date){
      order=await api(`/warehouse-assistant/api/${kind==='supplier_order'?'supplier-orders':'automatic-preorders'}/${order.id}/delivery-date`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delivery_date:date,expected_token:order.email_send_token})});
      orderPortalState.order=order;
    }
    const assignment=await api('/warehouse-assistant/api/supplier-portal/orders/publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({document_kind:kind,document_id:order.id,requested_delivery_date:date,portal_username:username,expected_token:order.email_send_token})});
    placed=true;
    const feedback=[];
    for(const [channel,recipient] of notifications){
      try{
        await api(`/warehouse-assistant/api/supplier-portal/orders/${assignment.id}/send-${channel}`,{method:'POST',headers:{'Content-Type':'application/json',[channel==='sms'?'X-Warehouse-Supplier-Portal-Sms':'X-Warehouse-Supplier-Portal-Email']:'1'},body:JSON.stringify({confirmed:true,[channel==='sms'?'mobile':'email']:recipient,expected_token:order.email_send_token,expected_revision:assignment.revision})});
        feedback.push(`${channel==='sms'?'پیامک':'ایمیل'}: اطلاع‌رسانی شد`);
      }catch(error){feedback.push(`${channel==='sms'?'پیامک':'ایمیل'}: ${error.message}`)}
    }
    $('#orderPortalDialog').close();orderPortalState.order=null;
    toast('در کارتابل تأمین‌کننده قرار گرفت. '+(feedback.join(' · ')||'اطلاع‌رسانی درخواست نشده بود.'));
    await Promise.all([loadOrders(),loadAutomaticPreorders()]);switchView('sent');
  }catch(error){
    $('#orderPortalError').textContent=placed?'سفارش در کارتابل است؛ بازخوانی ناموفق بود. دوباره قرار ندهید.':error.message;
    await Promise.allSettled([loadOrders(),loadAutomaticPreorders()]);
  }finally{orderPortalState.busy=false;$('#orderPortalForm').querySelectorAll('button,input,select').forEach(node=>node.disabled=false)}
}
async function openManualEdit(id){
  const order=await editableWorkflowOrder('supplier_order',id);if(!order)return;
  if(!order.can_edit)throw new Error('برای ویرایش، ابتدا لغو تأیید کنید؛ پس از ارسال ویرایش ممکن نیست.');
  renderManualDraft(order);
}
function renderManualDraft(order){
  orderPortalState.editing=order;
  $('#manualDeliveryDate').value=order.delivery_date||'';$('#manualDeliveryDate').disabled=!order.can_edit_delivery_date;
  $('#manualEditTitle').textContent=`${order.supplier} · ${order.warehouse_name} · ${order.order_number}`;
  $('#manualEditLines').innerHTML=`<div class="table-wrap"><table><thead><tr><th>کد کالا</th><th>نام کالا</th><th>تعداد نهایی (کارتن)</th><th>تعداد واحد</th><th>ارزش تخمینی</th></tr></thead><tbody>${order.lines.map(line=>`<tr data-product-code="${esc(line.product_code)}"><td>${esc(line.product_code)}</td><td><span class="draft-product-name" tabindex="0" title="${esc(line.product_name)}">${esc(line.product_name)}</span></td><td><input data-manual-cartons="${esc(line.product_code)}" aria-label="کارتن ${esc(line.product_name)}" type="number" min="0" max="1000000" step="1" required value="${line.cartons}"></td><td data-manual-units>${fa(line.order_quantity)}</td><td data-manual-value>${fa(line.estimated_value)}</td></tr>`).join('')}</tbody></table></div>`;
  $('#manualEditError').textContent='';beginDraftEditor('supplier_order');updateManualDraftTotals();
  if(!$('#manualEditDialog').open)$('#manualEditDialog').showModal();
}
function updateManualDraftTotals(){
  const order=orderPortalState.editing;if(!order)return;
  let cartons=0,units=0,value=0;
  document.querySelectorAll('#manualEditLines [data-manual-cartons]').forEach(input=>{
    const line=order.lines.find(item=>String(item.product_code)===input.dataset.manualCartons);
    const count=Number(input.value)||0,quantity=count*Math.max(1,Number(line.conversion_rate)||1),amount=quantity*(Number(line.buy_price)||0);
    cartons+=count;units+=quantity;value+=amount;
    input.closest('tr').querySelector('[data-manual-units]').textContent=fa(quantity);
    input.closest('tr').querySelector('[data-manual-value]').textContent=fa(amount);
  });
  $('#manualDraftTotals').textContent=`جمع: ${fa(cartons)} کارتن · ${fa(units)} عدد · ارزش تخمینی ${fa(value)}`;
}
async function editableWorkflowOrder(kind,id){
  let order=await freshWorkflowOrder(kind,id);
  if(!order.can_edit&&order.can_revoke_approval){
    if(!confirm('برای ویرایش، تأیید قبلی سفارش لغو می‌شود و پس از ویرایش باید دوباره تأیید کنید. ادامه می‌دهید؟'))return null;
    const result=await api(`/warehouse-assistant/api/${kind==='supplier_order'?'supplier-orders':'automatic-preorders'}/${id}/revoke-approval`,{method:'POST'});
    order=result.preorder||result;
    if(kind==='supplier_order')await loadOrders();else await loadAutomaticPreorders();
  }
  return order;
}
async function openSystemEdit(id){
  const order=await editableWorkflowOrder('automatic_preorder',id);if(!order)return;
  if(!order.can_edit)throw new Error('این سفارش پس از ارسال یا با نتیجه نامشخص قابل ویرایش نیست.');
  state.automaticPreorders=state.automaticPreorders.map(item=>item.id===id?order:item);
  openPreorderPreview(id);
}
async function saveManualEdit(event){
  event.preventDefault();const order=orderPortalState.editing;
  if(!order||$('#manualEditSave').disabled)return;
  $('#manualEditSave').disabled=true;
  try{
    const updated=await saveDraftEditor('supplier_order',order);
    renderManualDraft(updated);$('#manualDraftStatus').textContent='تاریخ و تعدادها ذخیره شد.';
    toast('تاریخ و تعدادهای سفارش ذخیره شد.');
    try{await loadOrders()}catch{toast('تغییرات ثبت شد؛ بازخوانی فهرست ناموفق بود.',true)}
  }catch(error){$('#manualEditError').textContent=error.message}finally{$('#manualEditSave').disabled=false}
}

const orderDateState={order:null,kind:null,busy:false};
async function openOrderDate(kind,id){
  if(orderDateState.busy)return;
  if(state.bootstrap?.order_delivery_date_supported!==true)throw new Error('ثبت تاریخ تحویل نیازمند فعال‌شدن نسخه جدید سرویس انبار است؛ پس از راه‌اندازی مجدد صفحه را بازخوانی کنید.');
  const order=await freshWorkflowOrder(kind,id);
  if(!order.can_edit_delivery_date)throw new Error('تاریخ پس از قرار دادن در کارتابل قابل تغییر نیست.');
  orderDateState.order=order;orderDateState.kind=kind;
  $('#orderDateSummary').textContent=`${order.order_number||order.preorder_number} · ${order.supplier} · ${order.warehouse_name}`;
  $('#orderDeliveryDate').value=order.requested_delivery_date||order.supplier_portal?.requested_delivery_date||'';
  $('#orderDateError').textContent='';$('#orderDateDialog').showModal();
}
async function saveOrderDate(event){
  event.preventDefault();if(orderDateState.busy||!orderDateState.order)return;
  const value=normalizeSearchText($('#orderDeliveryDate').value);
  if(!/^\d{4}\/\d{2}\/\d{2}$/.test(value)){$('#orderDateError').textContent='تاریخ شمسی را مانند ۱۴۰۵/۰۶/۲۵ وارد کنید.';return}
  orderDateState.busy=true;$('#orderDateSave').disabled=true;$('#orderDateError').textContent='';
  try{
    const order=orderDateState.order,kind=orderDateState.kind;
    await api(`/warehouse-assistant/api/${kind==='supplier_order'?'supplier-orders':'automatic-preorders'}/${order.id}/delivery-date`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delivery_date:value,expected_token:order.email_send_token})});
    $('#orderDateDialog').close();orderDateState.order=null;
    await Promise.all([loadOrders(),loadAutomaticPreorders()]);toast('تاریخ تحویل ذخیره شد.');
  }catch(error){$('#orderDateError').textContent=error.message;toast(error.message,true)}
  finally{orderDateState.busy=false;$('#orderDateSave').disabled=false}
}
document.addEventListener('DOMContentLoaded',()=>{
  document.addEventListener('click',event=>{
    const date=event.target.closest('[data-order-date-kind]');
    if(date&&!date.disabled){date.disabled=true;openOrderDate(date.dataset.orderDateKind,Number(date.dataset.orderDateId)).catch(error=>toast(error.message,true)).finally(()=>date.disabled=false)}
    const portal=event.target.closest('[data-order-portal-kind]');
    if(portal&&!portal.disabled){portal.disabled=true;openOrderPortal(portal.dataset.orderPortalKind,Number(portal.dataset.orderPortalId)).catch(error=>toast(error.message,true)).finally(()=>portal.disabled=false)}
    const edit=event.target.closest('[data-manual-edit],[data-preorder-edit]');
    if(edit&&!edit.disabled){edit.disabled=true;const work=edit.dataset.manualEdit?openManualEdit(Number(edit.dataset.manualEdit)):openSystemEdit(Number(edit.dataset.preorderEdit));work.catch(error=>toast(error.message,true)).finally(()=>edit.disabled=false)}
  });
  $('#orderPortalForm').addEventListener('submit',sendOrderPortal);
  $('#orderPortalClose').addEventListener('click',()=>$('#orderPortalDialog').close());
  $('#orderPortalDialog').addEventListener('cancel',event=>{if(orderPortalState.busy)event.preventDefault()});
  $('#manualEditClose').addEventListener('click',()=>requestDraftEditorClose('supplier_order',()=>$('#manualEditDialog').close()));
  $('#manualEditForm').addEventListener('submit',saveManualEdit);
  $('#orderDateForm').addEventListener('submit',saveOrderDate);
  $('#orderDateClose').addEventListener('click',()=>{if(!orderDateState.busy)$('#orderDateDialog').close()});
  $('#orderDateDialog').addEventListener('cancel',event=>{if(orderDateState.busy)event.preventDefault()});
  $('#previewDeliverySave')?.addEventListener('click',savePreviewDeliveryDate);
  for(const [kind,config] of Object.entries(draftEditorConfig)){
    const dialog=$(config.dialog);
    dialog.addEventListener('input',()=>{updateDraftEditorStatus(kind);if(kind==='supplier_order')updateManualDraftTotals()});
    dialog.addEventListener('cancel',event=>{
      if(event.defaultPrevented||dialog.classList.contains('workspace-fullscreen'))return;
      event.preventDefault();requestDraftEditorClose(kind,()=>dialog.close());
    });
    dialog.addEventListener('close',()=>{draftEditorSessions.delete(kind);if(kind==='supplier_order')orderPortalState.editing=null;else state.previewPreorderId=null});
  }
  document.querySelectorAll('[data-draft-exit]').forEach(button=>button.addEventListener('click',()=>resolveDraftEditorExit(button.dataset.draftExit)));
  $('#draftExitDialog').addEventListener('cancel',event=>{event.preventDefault();if(!draftEditorSessions.get(draftExitRequest?.kind)?.busy)resolveDraftEditorExit('keep')});
  window.addEventListener('beforeunload',event=>{
    if(Object.entries(draftEditorConfig).some(([kind,config])=>$(config.dialog).open&&(draftEditorSessions.get(kind)?.busy||draftEditorDirty(kind)))){event.preventDefault();event.returnValue=''}
  });
});

async function persistEmbeddedDelivery(kind,order,input){
  return api(`/warehouse-assistant/api/${kind==='supplier_order'?'supplier-orders':'automatic-preorders'}/${order.id}/delivery-date`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delivery_date:normalizeSearchText(input.value),expected_token:order.email_send_token})});
}
async function savePreviewDeliveryDate(){
  const order=currentPreviewPreorder();if(!order)return;
  if(order.can_edit){await savePreorderPreview();return}
  const button=$('#previewDeliverySave');button.disabled=true;
  const input=$('#previewDeliveryDate'),wasDisabled=input.disabled;input.disabled=true;
  const session=draftEditorSessions.get('automatic_preorder');if(session)session.busy=true;
  try{
    const updated=await persistEmbeddedDelivery('automatic_preorder',order,$('#previewDeliveryDate'));
    state.automaticPreorders=state.automaticPreorders.map(item=>item.id===order.id?updated:item);
    state.previewExpectedToken=updated.email_send_token;
    $('#previewDeliveryDate').value=updated.delivery_date;$('#previewDeliveryFeedback').textContent='تاریخ تحویل ذخیره شد.';
    beginDraftEditor('automatic_preorder',{dateOnly:true});$('#previewDeliveryFeedback').textContent='تاریخ تحویل ذخیره شد.';
    renderAutomaticPreorders();
  }catch(error){$('#previewDeliveryFeedback').textContent=error.message}finally{button.disabled=false;input.disabled=wasDisabled;if(session)session.busy=false}
}
