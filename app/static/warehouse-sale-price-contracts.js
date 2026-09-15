/* Assistant-side sale-price rules. Saving never writes Varanegar. */
const salePriceState={contracts:[],catalog:{manufacturers:[],warehouses:[]},items:[],selected:new Set(),editing:null,busy:false,loading:false,request:0};
const sp$=id=>document.getElementById(id);
const saleRuleStatus={draft:'پیش‌نویس',active:'فعال',archived:'بایگانی'};
function salePriceHeaders(){return {'Content-Type':'application/json','X-Warehouse-Settings':'1'}}
function salePriceCanEdit(){return has('warehouse.order.draft')}
function salePriceOptions(select,items,first,value='',key='id'){
  select.innerHTML=`<option value="">${first}</option>`+items.map(item=>`<option value="${esc(item[key])}">${esc(item.name)}</option>`).join('');
  select.value=String(value??'');
}
function salePriceError(error){sp$('salePriceMessage').textContent=error.message;sp$('salePriceMessage').hidden=false}
function salePriceFormula(rule){return `قیمت تولید ${rule.source_includes_tax?'شامل':'بدون'} مالیات · افزایش ${fa(rule.markup_percent)}٪`}
async function loadSalePriceContracts(){
  try{
    const result=await api('/warehouse-assistant/api/sale-price-contracts');
    salePriceState.contracts=result.contracts;salePriceState.catalog=result.catalog;
    salePriceOptions(sp$('salePriceWarehouseFilter'),result.catalog.warehouses,'همهٔ انبارها',sp$('salePriceWarehouseFilter').value,'code');
    salePriceOptions(sp$('salePriceManufacturerFilter'),result.catalog.manufacturers,'همهٔ تولیدکننده‌ها',sp$('salePriceManufacturerFilter').value);
    sp$('salePriceNew').hidden=!salePriceCanEdit();sp$('salePriceMessage').hidden=true;renderSalePriceContracts();
  }catch(error){salePriceError(error)}
}
function renderSalePriceContracts(){
  const warehouse=sp$('salePriceWarehouseFilter').value,manufacturer=Number(sp$('salePriceManufacturerFilter').value),status=sp$('salePriceStatusFilter').value,q=normalizeSearchText(sp$('salePriceSearch').value);
  const rows=salePriceState.contracts.filter(rule=>(!warehouse||rule.warehouse_code===warehouse)&&(!manufacturer||rule.manufacturer_id===manufacturer)&&(!status||rule.status===status)&&normalizeSearchText(`${rule.title} ${rule.manufacturer} ${rule.product_code} ${rule.product_name} ${rule.order_type_name}`).includes(q));
  sp$('salePriceRows').innerHTML=rows.length?rows.map(rule=>`<tr><td><strong>${esc(rule.warehouse_name)}</strong><small>نوع درخواست ${fa(rule.order_type_id)} · ${esc(rule.order_type_name)}</small></td><td><strong>${esc(rule.manufacturer)}</strong><small>${rule.product_code?`${esc(rule.product_code)} · ${esc(rule.product_name)}`:'همهٔ کالاهای تولیدکننده'}</small><small>${esc(rule.title)}</small></td><td dir="ltr">${esc(rule.start_date)}<small>تا ${esc(rule.end_date||'بدون پایان')}</small></td><td>${esc(salePriceFormula(rule))}<small>تخفیف و جایزه جداگانه اعمال می‌شود</small></td><td><span class="sale-price-badge ${rule.status}">${saleRuleStatus[rule.status]}</span></td><td><div class="sale-price-row-actions">${salePriceCanEdit()&&rule.status!=='archived'?`<button type="button" data-sale-price-edit="${esc(rule.id)}">ویرایش</button>`:''}<button type="button" data-sale-price-history="${esc(rule.id)}">سابقه</button>${salePriceCanEdit()&&rule.status!=='archived'?`<button type="button" class="danger-action" data-sale-price-archive="${esc(rule.id)}">بایگانی</button>`:''}</div></td></tr>`).join(''):'<tr><td colspan="6" class="purchase-empty">قاعده‌ای با این فیلتر وجود ندارد.</td></tr>';
  sp$('salePriceCount').textContent=`${fa(rows.length)} قرارداد کالایی قیمت فروش`;
}
function saleSelectionVisibleItems(){
  const query=normalizeSearchText(sp$('saleRuleItemSearch').value);
  return salePriceState.items.filter(item=>normalizeSearchText(`${item.product_code} ${item.manufacturer_product_code||''} ${item.barcode||''} ${item.product_name} ${item.brand||''} ${item.group_level3||item.group_name||''}`).includes(query));
}
function selectedSaleProductCodes(){return sp$('saleRuleSelectionMode').value==='all'?salePriceState.items.map(item=>item.product_code):[...salePriceState.selected]}
function saleTaxLabel(item){return item.tax_status==='known'&&item.tax_rate!==null?`${fa(item.tax_rate)}٪${Number(item.tax_rate)===0?' · معاف':''}`:item.tax_status==='conflict'?'ناسازگار':'نامشخص'}
function renderSaleRuleSelection(){
  const chosen=new Set(selectedSaleProductCodes()),editing=!!salePriceState.editing,all=sp$('saleRuleSelectionMode').value==='all',visible=saleSelectionVisibleItems();
  sp$('saleRuleSelectionRows').innerHTML=visible.map(item=>`<tr><td><input type="checkbox" data-sale-rule-product="${esc(item.product_code)}" aria-label="انتخاب ${esc(item.product_code)}" ${chosen.has(item.product_code)?'checked':''} ${editing||all?'disabled':''}></td><td><span dir="ltr">${esc(item.product_code)}</span></td><td>${esc(item.manufacturer_product_code||'—')}</td><td>${esc(item.barcode||'—')}</td><td><strong>${esc(item.product_name)}</strong></td><td>${esc(item.brand||'—')}</td><td>${esc(item.group_level3||item.group_name||'گروه مشخص نشده')}</td><td>${saleTaxLabel(item)}</td></tr>`).join('')||'<tr><td colspan="8">کالایی در این فهرست نیست.</td></tr>';
  sp$('saleRuleSelectionStatus').textContent=salePriceState.loading?'در حال دریافت فهرست…':`${fa(chosen.size)} کالا انتخاب شده · ${fa(visible.length)} نتیجه · ${fa(salePriceState.items.length)} کالای قابل انتخاب`;
  const old=sp$('saleRuleSampleProduct').value;
  sp$('saleRuleSampleProduct').innerHTML='<option value="">انتخاب کالای نمونه</option>'+salePriceState.items.filter(item=>chosen.has(item.product_code)).map(item=>`<option value="${esc(item.product_code)}">${esc(item.product_code)} · ${esc(item.product_name)}</option>`).join('');
  if(chosen.has(old))sp$('saleRuleSampleProduct').value=old;else if(chosen.size===1)sp$('saleRuleSampleProduct').value=[...chosen][0];
  sp$('saleRuleSave').disabled=salePriceState.busy||salePriceState.loading||!chosen.size;
}
async function loadSaleRuleSelection(level='all'){
  const request=++salePriceState.request,manufacturer=sp$('saleRuleManufacturer').value;
  if(level==='manufacturer'){salePriceOptions(sp$('saleRuleBrand'),[],'همهٔ برندها');salePriceOptions(sp$('saleRuleGroup'),[],'همهٔ گروه‌ها')}
  if(level==='brand')salePriceOptions(sp$('saleRuleGroup'),[],'همهٔ گروه‌ها');
  salePriceState.items=[];salePriceState.selected.clear();salePriceState.loading=!!manufacturer;renderSaleRuleSelection();
  if(!manufacturer){sp$('saleRuleSelectionStatus').textContent='ابتدا تولیدکننده را انتخاب کنید.';return}
  const brand=sp$('saleRuleBrand').value,group=sp$('saleRuleGroup').value,params=new URLSearchParams({manufacturer_id:manufacturer});
  if(brand)params.set('brand_id',brand);if(group)params.set('group_id',group);
  try{
    const result=await api('/warehouse-assistant/api/sale-price-contracts/selection?'+params);
    if(request!==salePriceState.request)return;
    salePriceOptions(sp$('saleRuleBrand'),result.brands,'همهٔ برندها',brand);salePriceOptions(sp$('saleRuleGroup'),result.groups,'همهٔ گروه‌ها',group);
    salePriceState.items=result.items;
    if(salePriceState.editing)salePriceState.items=salePriceState.items.filter(item=>item.product_code===salePriceState.editing.product_code);
    if(salePriceState.editing)salePriceState.items.forEach(item=>salePriceState.selected.add(item.product_code));
    sp$('saleRuleError').textContent='';
  }catch(error){if(request===salePriceState.request)sp$('saleRuleError').textContent=error.message}
  finally{if(request===salePriceState.request){salePriceState.loading=false;renderSaleRuleSelection()}}
}
async function editSalePriceContract(contract=null){
  salePriceState.editing=contract;salePriceState.items=[];salePriceState.selected.clear();salePriceState.loading=false;sp$('saleRuleError').textContent='';sp$('saleRulePreviewOutput').textContent='';
  const rule={warehouse_code:'karaj',manufacturer_id:'',title:'',start_date:salePriceState.catalog.today||'',end_date:'',status:'draft',source_includes_tax:true,markup_percent:'11',note:'',...contract};
  salePriceOptions(sp$('saleRuleWarehouse'),salePriceState.catalog.warehouses,'انتخاب انبار',rule.warehouse_code,'code');salePriceOptions(sp$('saleRuleManufacturer'),salePriceState.catalog.manufacturers,'انتخاب تولیدکننده',rule.manufacturer_id);salePriceOptions(sp$('saleRuleBrand'),[],'همهٔ برندها',rule.selection?.brand_id);salePriceOptions(sp$('saleRuleGroup'),[],'همهٔ گروه‌ها',rule.selection?.group_id);
  sp$('saleRuleSelectionMode').value=contract?'selected':'all';sp$('saleRuleItemSearch').value='';sp$('saleRuleTitle').value=rule.title;sp$('saleRuleStart').value=rule.start_date;sp$('saleRuleEnd').value=rule.end_date;sp$('saleRuleStatus').value=rule.status==='archived'?'draft':rule.status;sp$('saleRuleMarkup').value=rule.markup_percent;sp$('saleRuleIncludesTax').checked=rule.source_includes_tax;sp$('saleRuleNote').value=rule.note;sp$('saleRuleSampleDate').value=rule.start_date;sp$('saleRuleSamplePrice').value='';
  for(const id of ['saleRuleWarehouse','saleRuleManufacturer','saleRuleBrand','saleRuleGroup','saleRuleSelectionMode','saleRuleSelectVisible','saleRuleClearSelection'])sp$(id).disabled=!!contract;
  sp$('salePriceDialogTitle').textContent=contract?`ویرایش ${rule.product_code} · نسخه ${fa(rule.revision)}`:'قرارداد قیمت فروش کالاها';renderSaleRuleSelection();sp$('salePriceDialog').showModal();
  if(rule.manufacturer_id)await loadSaleRuleSelection();
}
function saleRulePayload(){
  const old=salePriceState.editing;
  return {warehouse_code:sp$('saleRuleWarehouse').value,manufacturer_id:Number(sp$('saleRuleManufacturer').value),filter_brand_id:sp$('saleRuleBrand').value?Number(sp$('saleRuleBrand').value):null,filter_group_id:sp$('saleRuleGroup').value?Number(sp$('saleRuleGroup').value):null,scope:'item',product_code:old?.product_code||sp$('saleRuleSampleProduct').value,product_codes:selectedSaleProductCodes(),title:sp$('saleRuleTitle').value,start_date:sp$('saleRuleStart').value,end_date:sp$('saleRuleEnd').value,status:sp$('saleRuleStatus').value,source_includes_tax:sp$('saleRuleIncludesTax').checked,markup_percent:sp$('saleRuleMarkup').value,note:sp$('saleRuleNote').value};
}
function saleRuleBusy(value){
  salePriceState.busy=value;sp$('salePriceFields').disabled=value;sp$('saleRuleSave').disabled=value;sp$('salePriceClose').disabled=value;
  if(!value&&salePriceState.editing)for(const id of ['saleRuleWarehouse','saleRuleManufacturer','saleRuleBrand','saleRuleGroup','saleRuleSelectionMode','saleRuleSelectVisible','saleRuleClearSelection'])sp$(id).disabled=true;
  if(!value)renderSaleRuleSelection();
}
async function saveSalePriceRule(event){
  event.preventDefault();if(salePriceState.busy||salePriceState.loading)return;const payload=saleRulePayload(),old=salePriceState.editing;if(old)payload.expected_revision=old.revision;
  if(!old&&!payload.product_codes.length){sp$('saleRuleError').textContent='حداقل یک کالا انتخاب کنید.';sp$('saleRuleError').focus?.();return}
  saleRuleBusy(true);sp$('saleRuleError').textContent='';
  try{const result=await api('/warehouse-assistant/api/sale-price-contracts/'+(old?encodeURIComponent(old.id):'batch'),{method:old?'PUT':'POST',headers:salePriceHeaders(),body:JSON.stringify(payload)});sp$('salePriceDialog').close();await loadSalePriceContracts();toast(old?'قاعدهٔ فروش با حفظ سابقه ویرایش شد.':`${fa(result.count)} قرارداد کالایی قیمت فروش ذخیره شد.`)}catch(error){sp$('saleRuleError').textContent=error.message;sp$('saleRuleError').focus?.()}finally{saleRuleBusy(false)}
}
async function previewSalePriceRule(){
  if(salePriceState.busy||salePriceState.loading)return;const contract=saleRulePayload(),code=sp$('saleRuleSampleProduct').value;
  if(!selectedSaleProductCodes().includes(code)){sp$('saleRuleError').textContent='کالای نمونه را از اقلام انتخاب‌شده انتخاب کنید.';return}
  contract.scope='item';contract.product_code=code;contract.filter_brand_id=null;contract.filter_group_id=null;
  saleRuleBusy(true);sp$('saleRuleError').textContent='';
  try{const result=await api('/warehouse-assistant/api/sale-price-contracts/preview',{method:'POST',headers:salePriceHeaders(),body:JSON.stringify({contract,product_code:code,on_date:sp$('saleRuleSampleDate').value,manufacturer_price:sp$('saleRuleSamplePrice').value})});sp$('saleRulePreviewOutput').innerHTML=`<span>خالص تولید <b>${fa(result.net_manufacturer_price)}</b></span><span>افزایش ${fa(result.markup_percent)}٪ <b>${fa(result.markup_amount)}</b></span><span>مالیات <b>${fa(result.tax)}</b></span><strong>قیمت پایه فروش: ${fa(result.sale_price)} · با مالیات: ${fa(result.sale_price_with_tax)} ریال</strong><small>${result.price_source==='erp_read_only'?'قیمت تولید از ورانگر فقط‌خواندنی دریافت شد.':'محاسبه با قیمت تولید واردشده در فرم.'}</small>`}catch(error){sp$('saleRulePreviewOutput').textContent='';sp$('saleRuleError').textContent=error.message}finally{saleRuleBusy(false)}
}
async function archiveSalePriceRule(rule){
  if(!confirm(`قاعدهٔ «${rule.title}» بایگانی شود؟ سابقه حفظ می‌شود.`))return;
  try{await api(`/warehouse-assistant/api/sale-price-contracts/${encodeURIComponent(rule.id)}/archive`,{method:'POST',headers:salePriceHeaders(),body:JSON.stringify({expected_revision:rule.revision,confirmed:true})});await loadSalePriceContracts();toast('قاعدهٔ فروش بایگانی شد؛ سابقه محفوظ است.')}catch(error){salePriceError(error)}
}
async function salePriceHistory(rule){
  try{const result=await api(`/warehouse-assistant/api/sale-price-contracts/${encodeURIComponent(rule.id)}/history`);sp$('salePriceHistoryTitle').textContent='سابقهٔ '+rule.title;sp$('salePriceHistoryBody').innerHTML=result.history.map(entry=>{const value=entry.contract;return `<article><strong>نسخه ${fa(value.revision)} · ${saleRuleStatus[value.status]} · ${esc(value.title)}</strong><p>${esc(value.warehouse_name)} · نوع درخواست ${fa(value.order_type_id)} (${esc(value.order_type_name)})</p><p>${esc(value.manufacturer)} · ${esc(value.product_code)} · ${esc(value.product_name)} · افزایش ${fa(value.markup_percent)}٪</p><p>${esc(value.start_date)} تا ${esc(value.end_date||'بدون پایان')} · ${esc(value.note)}</p><small>${esc(entry.actor)} · ${new Date(entry.saved_at).toLocaleString('fa-IR')}</small></article>`}).join('');sp$('salePriceHistoryDialog').showModal()}catch(error){salePriceError(error)}
}
document.addEventListener('DOMContentLoaded',()=>{
  if(!sp$('salePriceView'))return;
  sp$('salePriceNew').addEventListener('click',()=>editSalePriceContract());for(const id of ['salePriceWarehouseFilter','salePriceManufacturerFilter','salePriceStatusFilter'])sp$(id).addEventListener('change',renderSalePriceContracts);sp$('salePriceSearch').addEventListener('input',renderSalePriceContracts);
  sp$('saleRuleManufacturer').addEventListener('change',()=>loadSaleRuleSelection('manufacturer'));sp$('saleRuleBrand').addEventListener('change',()=>loadSaleRuleSelection('brand'));sp$('saleRuleGroup').addEventListener('change',()=>loadSaleRuleSelection('group'));sp$('saleRuleSelectionMode').addEventListener('change',renderSaleRuleSelection);sp$('saleRuleItemSearch').addEventListener('input',renderSaleRuleSelection);
  sp$('saleRuleSelectionRows').addEventListener('change',event=>{const code=event.target.dataset.saleRuleProduct;if(!code)return;if(event.target.checked)salePriceState.selected.add(code);else salePriceState.selected.delete(code);renderSaleRuleSelection()});
  sp$('saleRuleSelectVisible').addEventListener('click',()=>{sp$('saleRuleSelectionMode').value='selected';saleSelectionVisibleItems().forEach(item=>salePriceState.selected.add(item.product_code));renderSaleRuleSelection()});sp$('saleRuleClearSelection').addEventListener('click',()=>{sp$('saleRuleSelectionMode').value='selected';salePriceState.selected.clear();renderSaleRuleSelection()});
  sp$('salePriceClose').addEventListener('click',()=>{if(!salePriceState.busy){salePriceState.request++;sp$('salePriceDialog').close()}});sp$('salePriceForm').addEventListener('submit',saveSalePriceRule);sp$('saleRulePreview').addEventListener('click',previewSalePriceRule);
  sp$('salePriceRows').addEventListener('click',event=>{const button=event.target.closest('button');if(!button)return;const key=button.dataset.salePriceEdit||button.dataset.salePriceHistory||button.dataset.salePriceArchive;const rule=salePriceState.contracts.find(item=>item.id===key);if(!rule)return;if(button.dataset.salePriceEdit)editSalePriceContract(rule);else if(button.dataset.salePriceHistory)salePriceHistory(rule);else archiveSalePriceRule(rule)});sp$('salePriceHistoryClose').addEventListener('click',()=>sp$('salePriceHistoryDialog').close());
});
