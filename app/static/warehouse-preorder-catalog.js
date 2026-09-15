// Local preview additions are not persisted until the existing final-save action.
const preorderCatalog={orderId:null,token:null,items:[],request:0};
function resetPreorderCatalog(order){
  preorderCatalog.request++;preorderCatalog.orderId=order.id;
  preorderCatalog.token=order.email_send_token;preorderCatalog.items=[];
  $('#addPreorderProductsButton').hidden=order.status!=='awaiting_approval'||!state.bootstrap?.preorder_catalog_supported;
  if($('#preorderCatalogDialog').open)$('#preorderCatalogDialog').close();
}
function previewProductCodes(){return new Set([...document.querySelectorAll('#previewPreorderLines tr')].map(row=>row.dataset.productCode))}
function renderPreorderCatalog(){
  const query=normalizeSearchText($('#preorderCatalogSearch').value),existing=previewProductCodes();
  const rows=preorderCatalog.items.filter(item=>normalizeSearchText([item.product_code,item.manufacturer_product_code,item.barcode,item.product_name,item.brand,item.group_level3].join(' ')).includes(query));
  $('#preorderCatalogCount').textContent=`${fa(rows.length)} کالا · تعدادها به کارتن؛ موجودی‌ها به عدد`;
  $('#preorderCatalogRows').innerHTML=rows.map(item=>{
    const present=existing.has(String(item.product_code)),disabled=present||!item.can_add;
    return `<tr data-catalog-code="${esc(item.product_code)}"><td>${esc(item.product_code)}</td><td>${esc(item.manufacturer_product_code||'—')}</td><td>${esc(item.barcode||'—')}</td><td>${esc(item.product_name)}<small>${esc(item.brand)} · هر کارتن ${fa(item.conversion_rate)} عدد${item.ordering_cycle_active?'':' · خارج از چرخهٔ خودکار'}</small></td><td>${fa(item.on_hand_qty)}</td><td>${fa(item.in_transit_qty)}</td><td>${fa(item.effective_procurement_qty)}</td><td>${fa(item.average_daily_out)}</td><td>${item.coverage_days===null?'—':fa(item.coverage_days)}</td><td>${fa(item.approximate_price)}<small>تولید: ${fa(item.manufacturer_price)} · مصرف: ${fa(item.consumer_price)}</small></td><td><input class="catalog-cartons" type="text" inputmode="numeric" value="1" aria-label="کارتن ${esc(item.product_name)}" ${disabled?'disabled':''}></td><td><button type="button" class="secondary-action" data-catalog-add="${esc(item.product_code)}" ${disabled?'disabled':''}>${present?'در سفارش':!item.can_add?'تأمین غیرفعال':'افزودن'}</button></td><td>${esc(item.group_level3||'—')}</td></tr>`;
  }).join('')||'<tr><td colspan="12">کالایی با این جست‌وجو پیدا نشد.</td></tr>';
}
async function openPreorderCatalog(){
  const order=currentPreviewPreorder();if(!order||order.status!=='awaiting_approval')return;
  const request=++preorderCatalog.request,button=$('#addPreorderProductsButton');button.disabled=true;
  try{
    const data=await api(`/warehouse-assistant/api/automatic-preorders/${order.id}/catalog`);
    if(request!==preorderCatalog.request||state.previewPreorderId!==order.id||!$('#preorderPreviewDialog').open)return;
    if(data.expected_token!==preorderCatalog.token)throw Error('سفارش تغییر کرده است؛ صف و پیش‌نمایش را دوباره باز کنید.');
    preorderCatalog.items=data.items||[];
    $('#preorderCatalogTitle').textContent=`کالاهای ${data.supplier} · ${data.warehouse_name}`;
    $('#preorderCatalogSource').textContent=`اطلاعات ذخیره‌شدهٔ سفارش: ${formatRefreshDate(data.snapshot_imported_at)} · قیمت حدودی هر عدد؛ مبلغ نهایی را تأمین‌کننده تأیید می‌کند.`;
    $('#preorderCatalogSearch').value='';renderPreorderCatalog();$('#preorderCatalogDialog').showModal();fitFixedTableColumns($('#preorderCatalogTable'));
  }catch(error){toast(error.message,true)}finally{button.disabled=false}
}
function addCatalogProduct(button){
  const order=currentPreviewPreorder(),code=button.dataset.catalogAdd;
  if(!order||order.id!==preorderCatalog.orderId||order.status!=='awaiting_approval'||previewProductCodes().has(code))return;
  if(previewProductCodes().size>=500){toast('حداکثر ۵۰۰ قلم در سفارش مجاز است.',true);return}
  const item=preorderCatalog.items.find(item=>String(item.product_code)===code);if(!item?.can_add)return;
  const value=normalizeSearchText(button.closest('tr').querySelector('.catalog-cartons').value),cartons=Number(value);
  if(!/^\d+$/.test(value)||!Number.isInteger(cartons)||cartons<1||cartons>1000000){toast('تعداد کارتن باید صحیح و بین ۱ تا یک میلیون باشد.',true);return}
  const line={...item,cartons,order_quantity:cartons*item.conversion_rate,
    system_suggested_cartons:0,unadjusted_suggested_cartons:0,estimated_value:cartons*item.conversion_rate*item.approximate_price};
  $('#previewPreorderLines').insertAdjacentHTML('beforeend',previewPreorderLine(line,true));
  updatePreviewTotals();
  if(previewWorkView==='custom'&&typeof applyColumnOrder==='function')applyColumnOrder('preview');else applyWorkView('preview',previewWorkView);
  renderPreorderCatalog();$('#previewEditAudit').textContent='اقلام افزوده‌شده هنوز ذخیره نشده‌اند؛ «ذخیره تغییرات» را بزنید.';
  if(typeof updateDraftEditorStatus==='function')updateDraftEditorStatus('automatic_preorder');
}
document.addEventListener('DOMContentLoaded',()=>{
  $('#addPreorderProductsButton').addEventListener('click',openPreorderCatalog);
  $('#closePreorderCatalog').addEventListener('click',()=>$('#preorderCatalogDialog').close());
  $('#preorderCatalogSearch').addEventListener('input',renderPreorderCatalog);
  $('#preorderCatalogRows').addEventListener('click',event=>{const button=event.target.closest('[data-catalog-add]');if(button)addCatalogProduct(button)});
});
