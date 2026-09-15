// Settings only: no message sending, recipient storage or automatic delivery.
document.addEventListener('DOMContentLoaded',()=>{
  const dialog=$('#smsSettingsDialog'),form=$('#smsSettingsForm');
  const fields=$('#smsSettingsFields'),save=$('#smsSettingsSave'),notice=$('#smsSettingsNotice');
  const password=$('#smsPassword'),visible=$('#smsPasswordVisible');
  let busy=false,loading=false,opening=0;
  function feedback(message,error=false){notice.textContent=message;notice.classList.toggle('is-error',error)}
  function render(value){
    $('#smsUsername').value=value.username||'';$('#smsSource').value=value.source||'';
    password.value='';password.type='password';visible.checked=false;
    password.required=!value.password_configured;
    $('#smsPasswordHint').textContent=value.password_configured?'رمز ذخیره شده است؛ برای حفظ آن، این فیلد را خالی بگذارید.':'رمز وب‌سرویس آسانک را وارد کنید.';
    $('#smsSendUrl').value=value.send_url||'';$('#smsStatusUrl').value=value.status_url||'';
  }
  function close(){if(!busy)dialog.close()}
  $('#smsSettingsButton').addEventListener('click',async()=>{
    if(!state.bootstrap?.sms_settings_admin)return;
    const token=++opening;form.reset();fields.disabled=true;save.disabled=true;loading=true;
    feedback('در حال خواندن تنظیمات…');dialog.showModal();
    try{
      const value=await api('/warehouse-assistant/api/sms-settings');
      if(token!==opening||!dialog.open)return;
      render(value);fields.disabled=false;save.disabled=false;
      feedback(value.configured?'اطلاعات حساب ذخیره شده است.':'اطلاعات حساب را برای راه‌اندازی کامل کنید.');
      $('#smsUsername').focus();
    }catch(error){if(token===opening&&dialog.open)feedback(error.message,true)}
    finally{if(token===opening)loading=false}
  });
  $('#smsSettingsClose').addEventListener('click',close);
  dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault()});
  dialog.addEventListener('close',()=>{++opening;loading=false;form.reset();password.value='';password.type='password'});
  visible.addEventListener('change',()=>{password.type=visible.checked?'text':'password'});
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(busy||loading||fields.disabled||!form.reportValidity())return;
    busy=true;fields.disabled=true;save.disabled=true;$('#smsSettingsClose').disabled=true;
    save.textContent='در حال ذخیره…';feedback('در حال ذخیرهٔ تنظیمات…');
    const payload={username:$('#smsUsername').value,source:$('#smsSource').value,password:password.value};
    // Do not retain the newly entered password after dispatch, even on failure.
    password.value='';
    try{
      const value=await api('/warehouse-assistant/api/sms-settings',{method:'PUT',headers:{'Content-Type':'application/json','X-Warehouse-Settings':'1'},body:JSON.stringify(payload)});
      render(value);feedback('تنظیمات پیامک ذخیره شد.');
    }catch(error){feedback(error.message+' در صورت تغییر رمز، آن را دوباره وارد کنید.',true)}
    finally{payload.password='';busy=false;fields.disabled=false;save.disabled=false;$('#smsSettingsClose').disabled=false;save.textContent='ذخیرهٔ تنظیمات'}
  });
});
