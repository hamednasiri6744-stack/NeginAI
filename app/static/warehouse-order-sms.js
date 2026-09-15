// Explicit, user-initiated SMS delivery. No automatic or background sends.
document.addEventListener('DOMContentLoaded',()=>{
  const dialog=$('#orderSmsDialog'),form=$('#orderSmsForm'),mobile=$('#orderSmsMobile');
  const send=$('#orderSmsSend'),error=$('#orderSmsError');
  let selection=null,busy=false;

  function openFrom(button){
    if(button.disabled)return;
    selection={kind:button.dataset.orderSmsKind,id:Number(button.dataset.orderId),number:button.dataset.orderNumber||'',supplier:button.dataset.orderSupplier||''};
    $('#orderSmsNumber').textContent=selection.number;$('#orderSmsSupplier').textContent=selection.supplier;
    mobile.value=button.dataset.orderMobile||'';error.textContent='';dialog.showModal();mobile.focus();
  }
  function close(){if(!busy)dialog.close()}
  document.addEventListener('click',event=>{const button=event.target.closest('[data-order-sms-kind]');if(button)openFrom(button)});
  $('#orderSmsClose').addEventListener('click',close);
  dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault()});
  dialog.addEventListener('close',()=>{selection=null;form.reset();error.textContent=''});
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!selection||!form.reportValidity())return;
    const normalized=normalizeSearchText(mobile.value).replace(/[\s-]/g,'');
    if(!/^(?:\+98|0098|98|0)?9\d{9}$/.test(normalized)){
      error.textContent='شماره موبایل معتبر مانند 09123456789 وارد کنید.';mobile.focus();return;
    }
    busy=true;send.disabled=true;mobile.disabled=true;$('#orderSmsClose').disabled=true;
    send.textContent='در حال ارسال…';error.textContent='';
    const base=selection.kind==='supplier-order'?'supplier-orders':'automatic-preorders';
    try{
      const result=await api(`/warehouse-assistant/api/${base}/${selection.id}/send-sms-link`,{method:'POST',headers:{'Content-Type':'application/json','X-Warehouse-Sms':'1'},body:JSON.stringify({mobile:mobile.value,confirmed:true})});
      dialog.close();toast(`لینک اکسل سفارش ${result.order_number} به ${result.recipient_masked} پیامک شد.`);
    }catch(exception){error.textContent=exception.message;mobile.focus()}
    finally{busy=false;send.disabled=false;mobile.disabled=false;$('#orderSmsClose').disabled=false;send.textContent='تأیید و ارسال پیامک'}
  });
});
