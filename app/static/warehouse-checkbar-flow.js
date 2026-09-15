// Presentation adapter only: all writes still use the existing guarded actions.
function checkbarFlowModel(){
  const flow=(step,label,target='',blocked=false,hint='')=>({step,label,target,blocked,hint});
  const busy=checkbarState.submitting||receiptBridge.busy||orderMatchingState.loading;
  if(checkbarState.saved){
    if(checkbarState.saved.deleted)return flow(4,'چک‌بار حذف شده','',true,'این سند فقط برای مشاهدهٔ سابقه است.');
    if(checkbarState.saved.worksheet_workflow&&!checkbarState.saved.receipt_confirmed){
      if(!checkbarState.saved.worksheet_approved_at)return flow(3,'تأیید برگه برای چاپ','checkbarApproveWorksheet',!!busy,'برگه ذخیره شده؛ تأیید فقط آن را برای چاپ و شمارش آماده می‌کند.');
      return flow(4,'ثبت شمارش و قیمت انبار','checkbarEdit',!!busy,'ابتدا برگه را چاپ کنید؛ پس از کنترل بار، تعداد واقعی و قیمت‌های جدید را در همین سند ثبت کنید.');
    }
    if(receiptBridge.completed)return flow(5,'رسید در ورانگر ثبت شده','',true,'اصلاح و حذف چک‌بار فقط پس از تأیید حذف سند ورانگر ممکن است.');
    if(receiptBridge.pending)return flow(5,'پیگیری نتیجهٔ ورانگر','checkbarReceiptReconcile',!!busy,'نتیجهٔ درخواست قبلی را بررسی کنید؛ سند جدید نسازید.');
    if(receiptBridge.locked)return flow(5,'بازخوانی وضعیت ورانگر','checkbarReceiptRefresh',!!busy,'تا مشخص‌شدن وضعیت سند، اصلاح و حذف قفل است.');
    return flow(5,receiptBridge.preview?'تأیید و ارسال رسید به ورانگر':$('#checkbarReceiptPanel').hidden?'آماده‌سازی رسید ورانگر':'بررسی آمادگی ارسال','checkbarTransfer',!!busy,'چک‌بار ذخیره شده؛ ثبت رسید ورانگر مرحله‌ای جداگانه است.');
  }
  if(checkbarState.pending)return flow(4,'پیگیری ذخیرهٔ چک‌بار','checkbarIssue',!!busy,'همان درخواست قبلی پیگیری می‌شود؛ اطلاعات را دوباره وارد نکنید.');
  if(!checkbarState.source)return flow(1,'انتخاب بار','',true,'انبار و تأمین‌کننده را انتخاب کنید.');
  if(checkbarImportPending())return flow(2,'تکمیل ورود اقلام','',true,'فایل را بررسی و اقلامش را وارد چک‌بار کنید.');
  if(!checkbarState.lines.length)return flow(2,'افزودن کالا','',true,'کالا را از فایل یا فهرست کالاها اضافه کنید.');
  if(typeof checkbarDraftStage==='function'&&checkbarDraftStage())return flow(2,'ذخیره اولیه چک‌بار','checkbarIssue',!!busy,'تعداد سفارش ثبت است؛ تعدادهای خالی حفظ می‌شوند. شمارش و دریافت کالا در مرحله بعد انجام می‌شود.');
  if(typeof checkbarSkipMatching==='function'&&checkbarSkipMatching())return flow(4,'ثبت شمارش بدون تطبیق','checkbarIssue',!!busy,'تعداد واقعی و قیمت‌ها ذخیره می‌شوند؛ مانده سفارش‌ها تغییری نمی‌کند.');
  if(!orderMatchingState.plan||orderMatchingState.draftSignature!==matchingDraftSignature())return flow(checkbarState.worksheetWorkflow?4:2,busy?'در حال تطبیق…':'بررسی تطبیق سفارش‌ها','checkbarMatchingPrepare',!!busy,'پس از واردکردن تعداد و سند عطف، تطبیق را بررسی کنید.');
  try{
    const rows=matchingRemainders(orderMatchingState.plan,matchingAmounts());
    if(rows.some(row=>row.unallocated_qty<0))return flow(checkbarState.worksheetWorkflow?4:3,'اصلاح تخصیص','',true,'تخصیص نباید بیشتر از تعداد شمارش‌شده باشد.');
    if(!$('#checkbarMatchingConfirmed').checked)return flow(checkbarState.worksheetWorkflow?4:3,'تأیید تطبیق','',true,'تیک تأیید شمارش و تقسیم بین سفارش‌ها را بزنید.');
    if(rows.some(row=>row.unallocated_qty>0)&&!$('#checkbarMatchingExtra').checked)return flow(checkbarState.worksheetWorkflow?4:3,'تأیید دریافت اضافه','',true,'دریافت اضافه یا بدون سفارش، تأیید جداگانه می‌خواهد.');
  }catch{return flow(checkbarState.worksheetWorkflow?4:3,'اصلاح تخصیص','',true,'مقدارهای تخصیص را اصلاح کنید.')}
  return flow(4,'تأیید دریافت و ذخیره','checkbarIssue',!!busy,'با ذخیره، ماندهٔ سفارش کم می‌شود؛ هنوز سند ورانگر ثبت نمی‌شود.');
}

function renderCheckbarFlow(){
  const dialog=$('#checkbarDialog');if(!dialog.open)return;
  const model=checkbarFlowModel(),next=$('#checkbarNextAction'),target=model.target?$('#'+model.target):null;
  if(dialog.dataset.mainAction!==model.target)dialog.dataset.mainAction=model.target;
  const blocked=model.blocked||!target||target.disabled||target.hidden;
  const label=model.label,hint=model.hint;
  if(next.textContent!==label)next.textContent=label;
  if(next.disabled!==blocked)next.disabled=blocked;
  if(next.hidden!==!model.target)next.hidden=!model.target;
  if(next.dataset.targetAction!==model.target)next.dataset.targetAction=model.target;
  if($('#checkbarFlowHint').textContent!==hint)$('#checkbarFlowHint').textContent=hint;
  document.querySelectorAll('[data-checkbar-step]').forEach(node=>{
    const current=Number(node.dataset.checkbarStep)===model.step?'step':null;
    if(current&&node.getAttribute('aria-current')!==current)node.setAttribute('aria-current',current);
    if(!current&&node.hasAttribute('aria-current'))node.removeAttribute('aria-current');
  });
}

function checkbarHasUnsavedWork(){
  if(checkbarState.saved)return false;
  return checkbarState.lines.length>0||checkbarImportPending()||[...document.querySelectorAll('[data-checkbar-meta]')].some(input=>input.value.trim());
}
function checkbarExitBlocked(){return !!(checkbarState.submitting||checkbarState.deletePending||checkbarState.approvalPending||(!checkbarState.saved&&checkbarState.pending)||receiptBridge.busy)}
function closeCheckbarWorkspace(){checkbarState.sequence++;$('#checkbarDialog').close()}
function requestCheckbarClose(){
  if(checkbarExitBlocked()){checkbarNotice('info','عملیات در جریان است یا نتیجه هنوز قطعی نیست؛ ابتدا نتیجهٔ همین درخواست را پیگیری کنید.',true);return}
  if(!checkbarHasUnsavedWork()){closeCheckbarWorkspace();return}
  if(!$('#checkbarExitDialog').open)$('#checkbarExitDialog').showModal();
}
function resolveCheckbarExit(discard){
  $('#checkbarExitDialog').close();
  if(discard&&!checkbarExitBlocked())closeCheckbarWorkspace();
}

document.addEventListener('DOMContentLoaded',()=>{
  const dialog=$('#checkbarDialog');if(!dialog||!$('#checkbarNextAction'))return;
  dialog.dataset.guidedFlow='true';
  let scheduled=false;
  const schedule=()=>{if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;renderCheckbarFlow()})};
  new MutationObserver(schedule).observe(dialog,{subtree:true,childList:true,attributes:true,attributeFilter:['open','hidden','disabled']});
  dialog.addEventListener('input',schedule);dialog.addEventListener('change',schedule);
  $('#checkbarNextAction').addEventListener('click',()=>{
    renderCheckbarFlow();const next=$('#checkbarNextAction');if(next.disabled||!next.dataset.targetAction)return;
    // Preserve the original validation, confirmation and idempotent request path.
    $('#'+next.dataset.targetAction).click();schedule();
  });
  $('#checkbarExitKeep').addEventListener('click',()=>resolveCheckbarExit(false));
  $('#checkbarExitDiscard').addEventListener('click',()=>resolveCheckbarExit(true));
  window.addEventListener('beforeunload',event=>{if(dialog.open&&(checkbarHasUnsavedWork()||checkbarExitBlocked())){event.preventDefault();event.returnValue=''}});
});
