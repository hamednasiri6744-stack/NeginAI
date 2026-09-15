/* A reviewed selection becomes independent item contracts in one transaction. */
const purchaseEditor={items:[],selected:new Set(),request:0,loading:false,group:null};
function adjustmentDigits(value){return String(value).trim().replace(/[۰-۹]/g,c=>String(c.charCodeAt(0)-1776)).replace(/[٠-٩]/g,c=>String(c.charCodeAt(0)-1632)).replace(/٫/g,'.')}
function setContractAdjustment(value){
  const signed=adjustmentDigits(value);
  p$('contractAdjustmentDirection').value=Number(signed)<0?'decrease':'increase';
  p$('contractAdjustment').value=signed.replace(/^[+-]/,'');
}
function contractAdjustmentValue(){
  const amount=adjustmentDigits(p$('contractAdjustment').value),direction=p$('contractAdjustmentDirection').value;
  if(!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(amount)||Number(amount)>100)throw new Error('درصد تغییر قیمت پایه را بین صفر و ۱۰۰ و بدون علامت وارد کنید؛ جهت را از کاهش یا افزایش انتخاب کنید.');
  if(!['increase','decrease'].includes(direction))throw new Error('کاهش یا افزایش قیمت پایه را انتخاب کنید.');
  return Number(amount)===0?'0':(direction==='decrease'?'-':'')+amount;
}
const tailBases={percent:{net_before_tax:'مانده پس از تخفیف ستون، قبل از مالیات',gross:'مبلغ پایه قبل از تخفیف ستون و مالیات',after_tax:'جمع پس از تخفیف ستون و مالیات'},fixed:{invoice:'یک مبلغ برای کل اقلام این قرارداد در فاکتور',unit:'مبلغ برای هر واحد پایه کالا'}};
function tailValue(rule){return rule.tail_discount||{kind:'percent',basis:'net_before_tax',value:rule.tail_discount_percent??'0'}}
function tailDescription(rule){const t=tailValue(rule);return `${fa(t.value)}${t.kind==='percent'?'٪':' ریال'} · ${tailBases[t.kind]?.[t.basis]||'مبنای نامشخص'}`}
function contractTailChanged(basis){
  const kind=p$('contractTailKind').value,previous=basis||p$('contractTailBasis').value;
  p$('contractTailBasis').innerHTML=Object.entries(tailBases[kind]).map(([value,label])=>`<option value="${value}">${label}</option>`).join('');
  if(tailBases[kind][previous])p$('contractTailBasis').value=previous;
  p$('contractTailLabel').textContent=kind==='percent'?'درصد تخفیف انتهایی':'مبلغ تخفیف انتهایی · ریال';
  contractFormulaHelp();
}
function contractFormulaHelp(){
  const kind=p$('contractTailKind').value,basis=p$('contractTailBasis').value;
  p$('contractFormulaHelp').textContent='هر مرحلهٔ تخفیف ستون از ماندهٔ مرحلهٔ قبل کم می‌شود؛ مالیات پس از آخرین مرحله محاسبه می‌شود. '+(kind==='percent'?`تخفیف انتهایی درصدی از «${tailBases.percent[basis]}» است و از جمع نهایی کم می‌شود.`:basis==='invoice'?'مبلغ ثابت، یک‌بار برای اقلام همین گروه قرارداد در فاکتور کسر و متناسب با مبلغ اقلام سرشکن می‌شود؛ به تعداد کالا تکرار نمی‌شود.':'مبلغ ثابت در تعداد واحد پایه هر قلم ضرب و از جمع نهایی کسر می‌شود.');
  p$('contractPreviewOutput').textContent='';
}
function setPurchaseOptions(id,items,first,value=''){
  p$(id).innerHTML=`<option value="">${first}</option>`+items.map(i=>`<option value="${i.id}">${esc(i.name)}</option>`).join('');p$(id).value=String(value??'');
}
function syncContractSampleStock(){
  const stock=p$('contractStock').value;
  p$('contractSampleStock').disabled=!!stock;
  p$('contractSampleStock').value=stock||p$('purchaseStock').value||'1';
  p$('contractPreviewOutput').textContent='';
}
function setContractStock(r,existing){
  setPurchaseOptions('contractStock',purchaseState.catalog.stocks||[],'همهٔ انبارها · شرایط یکسان',existing?(r.stock_id??''):(r.stock_id??(p$('purchaseStock').value||'1')));
  syncContractSampleStock();
}
function selectionVisibleItems(){const q=normalizeSearchText(p$('contractItemSearch').value);return purchaseEditor.items.filter(i=>normalizeSearchText(`${i.product_code} ${i.manufacturer_product_code||''} ${i.barcode||''} ${i.product_name} ${i.brand} ${i.group_level3||i.group_name||''}`).includes(q)&&(!purchaseEditor.collection||supplierSelectionMatches(i)))}
function selectedProductCodes(){return !purchaseEditor.collection&&p$('contractSelectionMode').value==='all'?purchaseEditor.items.map(i=>i.product_code):[...purchaseEditor.selected]}
function renderContractSelection(){
  const chosen=new Set(selectedProductCodes()),editing=!!purchaseState.editing&&!purchaseEditor.collection,all=!purchaseEditor.collection&&p$('contractSelectionMode').value==='all';
  const visible=selectionVisibleItems();
  p$('contractSelectionRows').innerHTML=visible.map(i=>`<tr><td><input type="checkbox" data-contract-product="${esc(i.product_code)}" aria-label="انتخاب ${esc(i.product_code)}" ${chosen.has(i.product_code)?'checked':''} ${editing||all?'disabled':''}></td><td><span dir="ltr">${esc(i.product_code)}</span></td><td>${esc(i.manufacturer_product_code||'—')}</td><td>${esc(i.barcode||'—')}</td><td><strong>${esc(i.product_name)}</strong>${purchaseEditor.collection&&supplierMemberConflict(i.product_code)?`<small class="purchase-missing">تداخل با ${esc(supplierMemberConflict(i.product_code).title)}</small>`:''}</td><td>${esc(i.brand||'—')}</td><td>${esc(i.group_level3||i.group_name||'گروه مشخص نشده')}</td><td>${purchaseTaxLabel(i)}</td></tr>`).join('')||'<tr><td colspan="8">کالایی در این فهرست نیست.</td></tr>';
  p$('contractSelectionStatus').textContent=purchaseEditor.loading?'در حال دریافت فهرست…':`${fa(chosen.size)} کالا انتخاب شده · ${fa(visible.length)} نتیجه · ${fa(purchaseEditor.items.length)} کالا در فهرست تأمین‌کننده`;
  const old=p$('contractSampleProduct').value;
  p$('contractSampleProduct').innerHTML='<option value="">انتخاب کالای نمونه</option>'+purchaseEditor.items.filter(i=>chosen.has(i.product_code)).map(i=>`<option value="${esc(i.product_code)}">${esc(i.product_code)} · ${esc(i.product_name)}</option>`).join('');
  p$('contractSampleProduct').value=old;
  if(chosen.size===1)p$('contractSampleProduct').value=[...chosen][0];
  p$('contractSave').disabled=purchaseState.busy||purchaseEditor.loading||!chosen.size;
  if(purchaseEditor.collection){
    const conflicts=[...chosen].filter(code=>supplierMemberConflict(code));
    p$('contractMembershipWarning').textContent=conflicts.length?`${fa(conflicts.length)} کالای انتخاب‌شده در این انبار و بازه عضو قرارداد دیگری است؛ فقط کالاهای فاقد قرارداد قابل افزودن‌اند.`:'';
    if(conflicts.length)p$('contractSave').disabled=true;
    if(purchaseState.editing?.product_codes?.some(code=>!chosen.has(code))){p$('contractSave').disabled=true;p$('contractMembershipWarning').textContent='برای حذف کالای موجود، در مدیریت کالاهای قرارداد تاریخ پایان اعتبار آن را ثبت کنید؛ سابقهٔ کالا پاک نمی‌شود.'}
  }
}
async function loadContractSelection(level='all'){
  if(purchaseEditor.collection){renderContractSelection();return}
  const request=++purchaseEditor.request,mid=p$('contractManufacturer').value;
  if(level==='manufacturer'){setPurchaseOptions('contractBrand',[],'همهٔ برندها');setPurchaseOptions('contractGroup',[],'همهٔ گروه‌ها');setPurchaseOptions('contractSupplier',[],'انتخاب تأمین‌کننده')}
  if(level==='brand'){setPurchaseOptions('contractGroup',[],'همهٔ گروه‌ها')}
  purchaseEditor.items=[];purchaseEditor.selected.clear();purchaseEditor.loading=!!mid;renderContractSelection();
  if(!mid){p$('contractSelectionStatus').textContent='ابتدا تولیدکننده را انتخاب کنید.';return}
  const brand=p$('contractBrand').value,group=p$('contractGroup').value,supplier=p$('contractSupplier').value;
  const params=new URLSearchParams({manufacturer_id:mid});if(brand)params.set('brand_id',brand);if(group)params.set('group_id',group);
  try{
    const result=await api('/warehouse-assistant/api/purchase-contracts/selection?'+params);
    if(request!==purchaseEditor.request)return;
    setPurchaseOptions('contractBrand',result.brands,'همهٔ برندها',brand);setPurchaseOptions('contractGroup',result.groups,'همهٔ گروه‌ها',group);
    const manufacturer=purchaseState.catalog.manufacturers.find(m=>String(m.id)===mid);
    const preferred=result.suppliers.find(s=>String(s.id)===supplier)||result.suppliers.find(s=>normalizeSearchText(s.name)===normalizeSearchText(manufacturer?.name))||(result.suppliers.length===1?result.suppliers[0]:null);
    setPurchaseOptions('contractSupplier',result.suppliers,'انتخاب تأمین‌کننده',preferred?.id);
    purchaseEditor.items=result.items.filter(i=>i.supplier_ids.includes(Number(p$('contractSupplier').value)));
    if(purchaseEditor.group)purchaseEditor.items=purchaseEditor.items.filter(i=>purchaseEditor.group.some(r=>r.product_code===i.product_code));
    else if(purchaseState.editing?.scope==='item')purchaseEditor.items=purchaseEditor.items.filter(i=>i.product_code===purchaseState.editing.product_code);
    if(purchaseState.editing)purchaseEditor.items.forEach(i=>purchaseEditor.selected.add(i.product_code));
    p$('contractError').textContent='';
  }catch(error){if(request===purchaseEditor.request)p$('contractError').textContent=error.message}
  finally{if(request===purchaseEditor.request){purchaseEditor.loading=false;renderContractSelection()}}
}
async function editPurchaseContract(contract=null,copy=false,group=null){
  if(purchaseState.catalog.contract_structure==='supplier_contracts'){return editSupplierContract(contract,copy)}
  purchaseEditor.group=group;
  purchaseEditor.request++;purchaseEditor.items=[];purchaseEditor.selected.clear();purchaseEditor.loading=false;
  const r={supplier_id:'',manufacturer_id:'',title:'',start_date:purchaseState.catalog.today,end_date:'',status:'draft',basis:'manufacturer',includes_tax:true,adjustment_percent:'0',discount_percent:'0',agreement_reference:'',source_mode:'manual',evidence_run_id:'',note:'',...contract};
  purchaseState.editing=copy||!contract?.id?null:contract;
  if(copy){r.start_date=purchaseState.catalog.today;r.end_date='';r.status='draft';r.title+=' · دوره جدید'}
  setPurchaseOptions('contractManufacturer',purchaseState.catalog.manufacturers||[],'انتخاب تولیدکننده',r.manufacturer_id);
  setPurchaseOptions('contractSupplier',purchaseState.catalog.suppliers,'انتخاب تأمین‌کننده',r.supplier_id);
  setContractStock(r,!!contract?.id);
  setPurchaseOptions('contractBrand',[],'همهٔ برندها');setPurchaseOptions('contractGroup',[],'همهٔ گروه‌ها');
  const fields={Title:'title',AgreementReference:'agreement_reference',SourceMode:'source_mode',Start:'start_date',End:'end_date',Status:'status',Basis:'basis',Discount:'discount_percent',Note:'note'};
  Object.entries(fields).forEach(([id,key])=>p$('contract'+id).value=r[key]??'');
  p$('contractEvidenceRunId').value=r.evidence_run_id||'';
  setContractAdjustment(r.adjustment_percent);
  p$('contractDiscountFollowing').value=(r.discount_steps||[]).slice(1).map(s=>s.percent).join('، ');
  const tail=tailValue(r);p$('contractTailKind').value=tail.kind;p$('contractTail').value=tail.value;contractTailChanged(tail.basis);
  p$('contractIncludesTax').checked=r.includes_tax;p$('contractError').textContent='';p$('contractPreviewOutput').textContent='';p$('contractSamplePrice').value='';p$('contractSampleQty').value='1';p$('contractSampleDate').value=r.start_date||purchaseState.catalog.today||'';p$('contractItemSearch').value='';
  p$('contractSelectionMode').value=contract?.scope==='item'?'selected':'all';
  for(const id of ['contractManufacturer','contractBrand','contractGroup','contractSupplier','contractSelectionMode','contractSelectVisible','contractClearSelection'])p$(id).disabled=!!purchaseState.editing;
  p$('contractManufacturer').required=!purchaseState.editing;
  p$('contractDialogTitle').textContent=group?`ویرایش مشترک ${fa(group.length)} قرارداد کالا`:purchaseState.editing?`ویرایش ${r.product_code||'قرارداد قبلی'} · نسخه ${fa(r.revision)}`:'قرارداد کالاها';
  renderContractSelection();p$('purchaseContractDialog').showModal();p$('contractTitle').focus();
  if(r.manufacturer_id){
    await loadContractSelection();
    if(copy&&r.product_code){purchaseEditor.selected=new Set(purchaseEditor.items.some(i=>i.product_code===r.product_code)?[r.product_code]:[]);renderContractSelection()}
  }else if(contract){
    // Existing general agreements remain editable without rewriting their scope.
    purchaseEditor.loading=true;
    try{const result=await api('/warehouse-assistant/api/purchase-contracts/products?'+new URLSearchParams({supplier_id:r.supplier_id,on_date:purchaseState.catalog.today,limit:500}));purchaseEditor.items=result.items.filter(i=>r.scope!=='item'||i.product_code===r.product_code);purchaseEditor.items.forEach(i=>purchaseEditor.selected.add(i.product_code))}
    catch(error){p$('contractError').textContent=error.message}finally{purchaseEditor.loading=false;renderContractSelection()}
  }
}
function contractPayload(){
  const old=purchaseState.editing;
  return {supplier_id:Number(p$('contractSupplier').value),stock_id:p$('contractStock').value?Number(p$('contractStock').value):null,manufacturer_id:Number(p$('contractManufacturer').value),filter_brand_id:p$('contractBrand').value?Number(p$('contractBrand').value):null,filter_group_id:p$('contractGroup').value?Number(p$('contractGroup').value):null,
    scope:purchaseEditor.collection?'collection':old?.scope||'item',brand_id:old?.brand_id||null,product_code:old?.product_code||p$('contractSampleProduct').value,
    product_codes:selectedProductCodes(),title:p$('contractTitle').value,start_date:p$('contractStart').value,end_date:p$('contractEnd').value,status:p$('contractStatus').value,
    basis:p$('contractBasis').value,includes_tax:p$('contractIncludesTax').checked,adjustment_percent:contractAdjustmentValue(),discount_percent:p$('contractDiscount').value,discount_steps:contractDiscountSteps(),
    tail_discount:{kind:p$('contractTailKind').value,basis:p$('contractTailBasis').value,value:p$('contractTail').value},agreement_reference:p$('contractAgreementReference').value,
    source_mode:p$('contractSourceMode').value,evidence_run_id:p$('contractEvidenceRunId').value,note:p$('contractNote').value};
}
function contractDiscountSteps(){
  const rest=p$('contractDiscountFollowing').value.trim();
  const values=[p$('contractDiscount').value,...(rest?rest.split(/[,،;]/):[])];
  if(values.length>5||values.some(v=>!String(v).trim()))throw new Error('حداکثر پنج مرحلهٔ تخفیف؛ بین درصدها ویرگول بگذارید.');
  return values.map(v=>({percent:String(v).trim()}));
}
function contractBusy(value){purchaseState.busy=value;p$('contractPreview').disabled=value;p$('contractClose').disabled=value;p$('contractFields').disabled=value;p$('contractSave').disabled=value||purchaseEditor.loading||!selectedProductCodes().length;if(purchaseEditor.collection)renderContractSelection()}
async function savePurchaseContract(event){
  event.preventDefault();if(purchaseState.busy||purchaseEditor.loading)return;
  let payload;try{payload=contractPayload()}catch(error){p$('contractError').textContent=error.message;return}
  const old=purchaseState.editing;if(old)payload.expected_revision=old.revision;
  if(!old&&!payload.product_codes.length){p$('contractError').textContent='حداقل یک کالا انتخاب کنید.';return}
  contractBusy(true);p$('contractError').textContent='';
  try{
    if(purchaseEditor.group)payload.contract_versions=Object.fromEntries(purchaseEditor.group.map(r=>[r.id,r.revision]));
    const path=purchaseEditor.collection?(old?'/'+encodeURIComponent(old.id):''):'/'+(purchaseEditor.group?'batch-edit':old?encodeURIComponent(old.id):'batch');
    const result=await api('/warehouse-assistant/api/purchase-contracts'+path,{method:old&&!purchaseEditor.group?'PUT':'POST',headers:purchaseHeaders(),body:JSON.stringify(payload)});
    p$('purchaseContractDialog').close();await loadPurchaseContracts();toast(purchaseEditor.collection?`قرارداد با ${fa(result.product_codes.length)} کالا ذخیره شد.`:old?'قرارداد کالا با حفظ نسخهٔ قبلی ذخیره شد.':`${fa(result.count)} قرارداد کالا ذخیره شد.`);
  }catch(error){p$('contractError').textContent=error.message}finally{contractBusy(false)}
}
async function previewPurchaseContract(){
  if(purchaseState.busy||purchaseEditor.loading)return;
  let contract;try{contract=contractPayload()}catch(error){p$('contractError').textContent=error.message;return}
  const code=p$('contractSampleProduct').value;
  if(!selectedProductCodes().includes(code)){p$('contractError').textContent='کالای نمونه را از اقلام انتخاب‌شده انتخاب کنید.';return}
  contract.scope='item';contract.product_code=code;contract.brand_id=null;
  contractBusy(true);p$('contractError').textContent='';
  try{
    const r=await api('/warehouse-assistant/api/purchase-contracts/preview',{method:'POST',headers:purchaseHeaders(),body:JSON.stringify({contract,product_code:code,price:p$('contractSamplePrice').value,on_date:p$('contractSampleDate').value,stock_id:Number(p$('contractSampleStock').value),quantity:p$('contractSampleQty').value})});
    p$('contractPreviewOutput').innerHTML=`<span>قیمت پایه <b>${fa(r.unit_price)}</b></span><span>تخفیف ستون <b>${fa(r.discount)}</b></span><span>مانده قبل از مالیات <b>${fa(r.net_before_tax)}</b></span><span>مالیات ${fa(r.tax_rate)}٪ <b>${fa(r.tax)}</b></span><span>تخفیف انتهایی <b>${fa(r.tail_discount)}</b></span><strong>نهایی: ${fa(r.total)} ریال</strong>`;
  }catch(error){p$('contractPreviewOutput').textContent='';p$('contractError').textContent=error.message}finally{contractBusy(false)}
}
document.addEventListener('DOMContentLoaded',()=>{
  if(!p$('purchaseView'))return;
  p$('contractManufacturer').addEventListener('change',()=>loadContractSelection('manufacturer'));
  p$('contractBrand').addEventListener('change',()=>loadContractSelection('brand'));
  p$('contractGroup').addEventListener('change',()=>loadContractSelection('group'));
  p$('contractSupplier').addEventListener('change',()=>loadContractSelection('supplier'));
  p$('contractSelectionMode').addEventListener('change',renderContractSelection);
  p$('contractItemSearch').addEventListener('input',renderContractSelection);
  p$('contractSelectionRows').addEventListener('change',e=>{const code=e.target.dataset.contractProduct;if(!code)return;if(e.target.checked)purchaseEditor.selected.add(code);else purchaseEditor.selected.delete(code);renderContractSelection()});
  p$('contractSelectVisible').addEventListener('click',()=>{const visible=selectionVisibleItems();p$('contractSelectionMode').value='selected';visible.forEach(i=>purchaseEditor.selected.add(i.product_code));renderContractSelection()});
  p$('contractClearSelection').addEventListener('click',()=>{p$('contractSelectionMode').value='selected';purchaseEditor.selected.clear();renderContractSelection()});
  p$('contractTailKind').addEventListener('change',()=>contractTailChanged());p$('contractTailBasis').addEventListener('change',contractFormulaHelp);
  p$('contractSourceMode').addEventListener('change',()=>{if(p$('contractSourceMode').value!=='discovered')p$('contractEvidenceRunId').value=''});
  p$('contractAdjustmentDirection').addEventListener('change',contractFormulaHelp);p$('contractAdjustment').addEventListener('input',contractFormulaHelp);
  p$('contractClose').addEventListener('click',()=>{if(!purchaseState.busy){purchaseEditor.request++;p$('purchaseContractDialog').close()}});
  p$('purchaseContractDialog').addEventListener('cancel',e=>{if(purchaseState.busy)e.preventDefault();else purchaseEditor.request++});
  p$('contractForm').addEventListener('submit',savePurchaseContract);p$('contractPreview').addEventListener('click',previewPurchaseContract);
});
