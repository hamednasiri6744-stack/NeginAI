/* Membership is edited independently of commercial terms, then saved once. */
const purchaseMembers={request:0,contract:null,items:[],selected:new Set(),original:new Set(),tab:'members',endDates:{},checked:new Set(),loading:false,busy:false};
function purchaseMemberEnd(rule,code){return [rule.end_date||'9999/12/31',rule.product_end_dates?.[code]||'9999/12/31'].sort()[0]}
function purchaseMembersEditable(){return purchaseCanEdit()&&purchaseMembers.contract?.status!=='archived'}
function purchaseMemberAvailable(item){
  const r=purchaseMembers.contract;
  if(!r)return false;
  if(item.eligible_stock_ids&&(r.stock_id==null?!item.eligible_stock_ids.length:!item.eligible_stock_ids.includes(r.stock_id)))return false;
  return !purchaseState.contracts.some(other=>other.id!==r.id&&other.supplier_id===r.supplier_id&&other.status==='active'
    &&(r.stock_id==null||other.stock_id==null||r.stock_id===other.stock_id)
    &&r.start_date<=purchaseMemberEnd(other,item.product_code)&&other.start_date<=purchaseMemberEnd(r,item.product_code)
    &&(other.product_codes||[other.product_code]).includes(item.product_code));
}
function purchaseMembersVisible(){
  const query=normalizeSearchText(p$('purchaseMembersSearch').value);
  return purchaseMembers.items.filter(i=>(purchaseMembers.tab==='members'?purchaseMembers.selected.has(i.product_code):
    !purchaseMembers.selected.has(i.product_code)&&purchaseMemberAvailable(i))
    &&normalizeSearchText([i.product_code,i.product_name,i.manufacturer_product_code,i.barcode,i.brand,i.group_level3||i.group_name].join(' ')).includes(query));
}
function renderPurchaseMembers(){
  const edit=purchaseMembersEditable(),locked=purchaseMembers.loading||purchaseMembers.busy;
  const added=[...purchaseMembers.selected].filter(c=>!purchaseMembers.original.has(c)).length;
  const removed=[...purchaseMembers.original].filter(c=>!purchaseMembers.selected.has(c)).length;
  const ending=Object.keys(purchaseMembers.endDates).length;
  const available=purchaseMembers.items.filter(i=>!purchaseMembers.selected.has(i.product_code)&&purchaseMemberAvailable(i)).length;
  p$('purchaseMembersCurrent').textContent=`کالاهای قرارداد (${fa(purchaseMembers.selected.size)})`;
  p$('purchaseMembersAdd').textContent=`افزودن کالا (${fa(available)})`;
  for(const [id,tab] of [['purchaseMembersCurrent','members'],['purchaseMembersAdd','available']]){
    p$(id).setAttribute('aria-pressed',String(tab===purchaseMembers.tab));p$(id).disabled=locked;
  }
  p$('purchaseMembersAdd').hidden=!edit;
  p$('purchaseMembersAddVisible').hidden=!edit||purchaseMembers.tab!=='available';p$('purchaseMembersAddVisible').disabled=locked||!purchaseMembersVisible().length;
  p$('purchaseMembersSave').hidden=!edit;p$('purchaseMembersSave').disabled=locked||!purchaseMembers.selected.size||(!added&&!removed&&!ending);
  p$('purchaseMembersClose').disabled=purchaseMembers.busy;
  p$('purchaseMembersBulk').hidden=!edit||purchaseMembers.tab!=='members';
  p$('purchaseMembersDeleteSelected').disabled=locked||!purchaseMembers.checked.size;
  p$('purchaseMembersSelectVisible').disabled=locked;
  p$('purchaseMembersClearChecked').disabled=locked||!purchaseMembers.checked.size;
  p$('purchaseMembersCheckedCount').textContent=`${fa(purchaseMembers.checked.size)} کالا انتخاب شده`;
  p$('purchaseMembersBulkDate').disabled=locked;
  p$('purchaseMembersChangeCount').textContent=added||removed||ending?`${fa(added)} افزودن · ${fa(removed)} لغو انتخاب · ${fa(ending)} پایان اعتبار · تغییرات هنوز ذخیره نشده‌اند`:'تغییری ثبت نشده است.';
  p$('purchaseMembersRows').innerHTML=purchaseMembers.loading?'<tr><td colspan="9">در حال دریافت کالاها…</td></tr>':purchaseMembersVisible().map(i=>`<tr>
    <td>${edit&&purchaseMembers.tab==='members'&&purchaseMembers.original.has(i.product_code)?`<input type="checkbox" data-purchase-member-check="${esc(i.product_code)}" aria-label="انتخاب ${esc(i.product_code)} برای حذف" ${purchaseMembers.checked.has(i.product_code)?'checked':''} ${locked?'disabled':''}>`:'—'}</td><td>${esc(i.product_code)}</td><td>${esc(i.product_name)}</td><td>${esc(i.manufacturer_product_code||'—')}</td><td>${esc(i.barcode||'—')}</td>
    <td>${esc(i.brand||'—')}</td><td>${esc(i.group_level3||i.group_name||'—')}</td>
    <td>${Object.hasOwn(purchaseMembers.endDates,i.product_code)?`<input type="text" inputmode="numeric" data-purchase-member-end="${esc(i.product_code)}" aria-label="تاریخ پایان ${esc(i.product_code)}" value="${esc(purchaseMembers.endDates[i.product_code])}" placeholder="۱۴۰۵/۰۶/۲۳" ${locked?'disabled':''}>`:
      esc(purchaseMembers.contract.product_end_dates?.[i.product_code]||'بدون پایان اختصاصی')}</td>
    <td>${edit?`<button type="button" data-purchase-member-toggle="${esc(i.product_code)}" ${locked?'disabled':''}>${purchaseMembers.tab!=='members'?'افزودن':Object.hasOwn(purchaseMembers.endDates,i.product_code)?'انصراف از پایان':purchaseMembers.original.has(i.product_code)?(purchaseMembers.contract.product_end_dates?.[i.product_code]?'اصلاح تاریخ پایان':'حذف با تاریخ پایان'):'لغو افزودن'}</button>`:''}
    ${purchaseMembers.original.has(i.product_code)?`<button type="button" data-purchase-member-history="${esc(i.product_code)}">سابقهٔ کالا</button>`:''}</td></tr>`).join('')||'<tr><td colspan="9" class="purchase-empty">کالایی در این فهرست نیست.</td></tr>';
}
async function openPurchaseMembers(r,tab='members'){
  const request=++purchaseMembers.request;
  Object.assign(purchaseMembers,{contract:r,items:[],selected:new Set(r.product_codes||[r.product_code]),original:new Set(r.product_codes||[r.product_code]),tab,endDates:{},checked:new Set(),loading:true,busy:false});
  p$('purchaseMembersTitle').textContent=`کالاهای قرارداد · ${r.title}`;
  p$('purchaseMembersSummary').textContent=`${r.supplier} · ${purchaseStockName(r.stock_id)} · ${r.start_date} تا ${r.end_date||'بدون پایان'}${r.stock_id==null?' · قرارداد مشترک؛ تغییر اعضا برای همهٔ انبارها اعمال می‌شود.':''}`;
  p$('purchaseMembersBulkDate').value='';p$('purchaseMembersSearch').value='';p$('purchaseMembersError').textContent='';renderPurchaseMembers();p$('purchaseMembersDialog').showModal();
  try{
    const result=await api('/warehouse-assistant/api/purchase-contracts/selection?'+new URLSearchParams({supplier_id:r.supplier_id}));
    if(request!==purchaseMembers.request)return;
    purchaseMembers.items=result.items;
    const known=new Set(result.items.map(i=>i.product_code));
    for(const code of purchaseMembers.selected)if(!known.has(code))purchaseMembers.items.push({product_code:code,product_name:'خارج از فهرست فعلی تأمین‌کننده',eligible_stock_ids:[]});
  }catch(error){if(request===purchaseMembers.request)p$('purchaseMembersError').textContent=error.message}
  finally{if(request===purchaseMembers.request){purchaseMembers.loading=false;renderPurchaseMembers()}}
}
function closePurchaseMembers(){
  if(purchaseMembers.busy)return;
  const dirty=Object.keys(purchaseMembers.endDates).length||[...purchaseMembers.selected].some(c=>!purchaseMembers.original.has(c))||[...purchaseMembers.original].some(c=>!purchaseMembers.selected.has(c));
  if(dirty&&!confirm('تغییرات ذخیره‌نشدهٔ کالاهای قرارداد کنار گذاشته شوند؟'))return;
  purchaseMembers.request++;p$('purchaseMembersDialog').close();
}
async function savePurchaseMembers(){
  if(!purchaseMembersEditable()||purchaseMembers.busy||purchaseMembers.loading||!purchaseMembers.selected.size)return;
  purchaseMembers.busy=true;p$('purchaseMembersError').textContent='';renderPurchaseMembers();
  try{
    await api('/warehouse-assistant/api/purchase-contracts/'+encodeURIComponent(purchaseMembers.contract.id)+'/members',{
      method:'PUT',headers:purchaseHeaders(),body:JSON.stringify({expected_revision:purchaseMembers.contract.revision,product_codes:[...purchaseMembers.selected],...(Object.keys(purchaseMembers.endDates).length?{product_end_dates:purchaseMembers.endDates}:{})})});
    purchaseMembers.request++;p$('purchaseMembersDialog').close();await loadPurchaseContracts();toast('کالاهای قرارداد ذخیره شدند.');
  }catch(error){p$('purchaseMembersError').textContent=error.message}
  finally{purchaseMembers.busy=false;renderPurchaseMembers()}
}
function deleteSelectedPurchaseMembers(){
  if(!purchaseMembersEditable()||purchaseMembers.busy||purchaseMembers.loading||!purchaseMembers.checked.size)return;
  const end=adjustmentDigits(p$('purchaseMembersBulkDate').value).replaceAll('-','/');
  if(!/^\d{4}\/\d{2}\/\d{2}$/.test(end)){p$('purchaseMembersError').textContent='تاریخ پایان کالاهای انتخاب‌شده را به صورت ۱۴۰۵/۰۶/۲۳ وارد کنید.';return}
  for(const code of purchaseMembers.checked)if(purchaseMembers.original.has(code))purchaseMembers.endDates[code]=end;
  p$('purchaseMembersError').textContent='';purchaseMembers.checked.clear();renderPurchaseMembers();
}
document.addEventListener('DOMContentLoaded',()=>{
  p$('purchaseMembersDeleteSelected').addEventListener('click',deleteSelectedPurchaseMembers);
  p$('purchaseMembersSelectVisible').addEventListener('click',()=>{purchaseMembersVisible().filter(i=>purchaseMembers.original.has(i.product_code)).forEach(i=>purchaseMembers.checked.add(i.product_code));renderPurchaseMembers()});
  p$('purchaseMembersClearChecked').addEventListener('click',()=>{purchaseMembers.checked.clear();renderPurchaseMembers()});
  p$('purchaseMembersRows').addEventListener('change',e=>{const b=e.target.closest('[data-purchase-member-check]');if(!b||purchaseMembers.busy)return;b.checked?purchaseMembers.checked.add(b.dataset.purchaseMemberCheck):purchaseMembers.checked.delete(b.dataset.purchaseMemberCheck);renderPurchaseMembers()});

  p$('purchaseMembersClose').addEventListener('click',closePurchaseMembers);
  p$('purchaseMembersDialog').addEventListener('cancel',e=>{e.preventDefault();closePurchaseMembers()});
  p$('purchaseMembersSearch').addEventListener('input',renderPurchaseMembers);
  for(const [id,tab] of [['purchaseMembersCurrent','members'],['purchaseMembersAdd','available']])p$(id).addEventListener('click',()=>{purchaseMembers.tab=tab;renderPurchaseMembers()});
  p$('purchaseMembersAddVisible').addEventListener('click',()=>{
    if(!purchaseMembersEditable()||purchaseMembers.loading||purchaseMembers.busy||purchaseMembers.tab!=='available')return;
    purchaseMembersVisible().forEach(i=>purchaseMembers.selected.add(i.product_code));renderPurchaseMembers();
  });
  p$('purchaseMembersRows').addEventListener('click',e=>{
    const b=e.target.closest('[data-purchase-member-toggle]');if(!b||!purchaseMembersEditable()||purchaseMembers.loading||purchaseMembers.busy)return;
    const code=b.dataset.purchaseMemberToggle,item=purchaseMembers.items.find(i=>i.product_code===code);
    if(purchaseMembers.selected.has(code)){
      if(purchaseMembers.original.has(code)){
        if(Object.hasOwn(purchaseMembers.endDates,code))delete purchaseMembers.endDates[code];
        else purchaseMembers.endDates[code]=purchaseMembers.contract.product_end_dates?.[code]||purchaseMembers.contract.end_date||purchaseState.catalog.today||'';
      }else purchaseMembers.selected.delete(code);
    }else if(item&&purchaseMemberAvailable(item))purchaseMembers.selected.add(code);
    renderPurchaseMembers();
  });
  p$('purchaseMembersRows').addEventListener('input',e=>{
    const input=e.target.closest('[data-purchase-member-end]');if(input&&!purchaseMembers.busy)purchaseMembers.endDates[input.dataset.purchaseMemberEnd]=input.value;
  });
  p$('purchaseMembersRows').addEventListener('click',e=>{
    const b=e.target.closest('[data-purchase-member-history]');if(b)purchaseMemberHistory(b.dataset.purchaseMemberHistory);
  });
  p$('purchaseMembersSave').addEventListener('click',savePurchaseMembers);
  p$('purchaseContractRows').addEventListener('click',e=>{const b=e.target.closest('[data-purchase-add-members]');if(b){const r=purchaseState.contracts.find(r=>r.id===b.dataset.purchaseAddMembers);if(r)openPurchaseMembers(r,'available')}});
});

async function purchaseMemberHistory(code){
  const contract=purchaseMembers.contract,request=purchaseMembers.request;
  try{
    const result=await api('/warehouse-assistant/api/purchase-contracts/'+encodeURIComponent(contract.id)+'/members/'+encodeURIComponent(code)+'/history');
    if(request!==purchaseMembers.request||!p$('purchaseMembersDialog').open)return;
    p$('purchaseHistoryTitle').textContent='سابقهٔ کالا '+code+' · '+contract.title;
    p$('purchaseHistoryBody').innerHTML=result.history.map(h=>`<article><strong>${esc(h.product_code)} · نسخه ${fa(h.contract.revision)}</strong><p>${esc(purchaseStockName(h.contract.stock_id))} · شروع ${esc(h.contract.start_date)} · پایان کالا: ${esc(h.member_end_date||h.contract.end_date||'بدون پایان')}</p><p>${h.member_present?'عضو قرارداد؛ سابقه محفوظ است':'حذف در نسخهٔ قدیمی'}</p><small>${esc(h.actor)} · ${new Date(h.saved_at).toLocaleString('fa-IR')}</small></article>`).join('')||'<p>سابقه‌ای ثبت نشده است.</p>';
    p$('purchaseHistoryDialog').showModal();
  }catch(error){p$('purchaseMembersError').textContent=error.message}
}
