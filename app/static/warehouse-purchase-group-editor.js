function supplierSelectionMatches(item){
  const stock=Number(p$('contractStock').value);
  const eligible=!item.eligible_stock_ids||(stock?item.eligible_stock_ids.includes(stock):item.eligible_stock_ids.length>0);
  const existing=purchaseState.editing?.product_codes?.includes(item.product_code);
  if(!existing&&supplierMemberConflict(item.product_code))return false;
  return (eligible||(p$('contractSelectionMode').value==='members'&&purchaseEditor.selected.has(item.product_code)))
    &&(!p$('contractManufacturer').value||String(item.manufacturer_id)===p$('contractManufacturer').value)
    &&(!p$('contractBrand').value||String(item.brand_id)===p$('contractBrand').value)
    &&(!p$('contractGroup').value||String(item.group_id)===p$('contractGroup').value)
    &&(p$('contractSelectionMode').value!=='members'||purchaseEditor.selected.has(item.product_code));
}
function supplierMemberConflict(code){
  const start=adjustmentDigits(p$('contractStart').value).replaceAll('-','/'),end=adjustmentDigits(p$('contractEnd').value).replaceAll('-','/')||'9999/12/31';
  if(!/^\d{4}\/\d{2}\/\d{2}$/.test(start))return null;
  return purchaseState.contracts.find(r=>r.id!==purchaseState.editing?.id&&r.status==='active'
    &&(!p$('contractStock').value||r.stock_id==null||r.stock_id===Number(p$('contractStock').value))
    &&r.supplier_id===Number(p$('contractSupplier').value)&&(r.product_codes||[r.product_code]).includes(code)
    &&start<=purchaseMemberEnd(r,code)&&r.start_date<=([end,purchaseState.editing?.product_end_dates?.[code]||'9999/12/31'].sort()[0]));
}
async function editSupplierContract(contract=null,copy=false){
  const supplierId=contract?.supplier_id||Number(p$('purchaseSupplier').value);
  if(!supplierId){purchaseMessage('ابتدا تأمین‌کننده را انتخاب کنید.');return}
  purchaseEditor.collection=true;purchaseEditor.group=null;purchaseEditor.items=[];purchaseEditor.selected.clear();
  const request=++purchaseEditor.request;purchaseEditor.loading=true;
  const r={title:'',start_date:purchaseState.catalog.today,end_date:'',status:'draft',basis:'manufacturer',includes_tax:true,
    adjustment_percent:'0',discount_percent:'0',tail_discount_percent:'0',note:'',source_mode:'manual',...contract,supplier_id:supplierId};
  purchaseState.editing=contract?.id&&!copy?contract:null;
  if(copy){r.title+=' · دوره جدید';r.start_date=purchaseState.catalog.today;r.end_date='';r.status='draft'}
  setPurchaseOptions('contractSupplier',purchaseSupplierRows(),'انتخاب تأمین‌کننده',supplierId);
  setContractStock(r,!!contract?.id);
  p$('contractSupplier').disabled=true;
  for(const [id,label] of [['contractManufacturer','همهٔ تولیدکنندگان'],['contractBrand','همهٔ برندها'],['contractGroup','همهٔ گروه‌ها']]){
    setPurchaseOptions(id,[],label);p$(id).disabled=false;p$(id).required=false;
  }
  p$('contractSelectionMode').innerHTML='<option value="selected">کالاهای فاقد قرارداد و اعضای این قرارداد</option><option value="members">فقط کالاهای قرارداد</option>';
  p$('contractSelectionMode').disabled=false;p$('contractSelectionMode').value=contract?'members':'selected';
  for(const id of ['contractSelectVisible','contractClearSelection'])p$(id).disabled=false;
  const fields={Title:'title',AgreementReference:'agreement_reference',SourceMode:'source_mode',Start:'start_date',End:'end_date',Status:'status',Basis:'basis',Discount:'discount_percent',Note:'note',EvidenceRunId:'evidence_run_id'};
  Object.entries(fields).forEach(([id,key])=>p$('contract'+id).value=r[key]??'');
  setContractAdjustment(r.adjustment_percent);p$('contractDiscountFollowing').value=(r.discount_steps||[]).slice(1).map(s=>s.percent).join('، ');
  const tail=tailValue(r);p$('contractTailKind').value=tail.kind;p$('contractTail').value=tail.value;contractTailChanged(tail.basis);
  p$('contractIncludesTax').checked=r.includes_tax;p$('contractError').textContent='';p$('contractMembershipWarning').textContent='';
  p$('contractPreviewOutput').textContent='';p$('contractSamplePrice').value='';p$('contractSampleQty').value='1';p$('contractSampleDate').value=r.start_date;p$('contractItemSearch').value='';
  p$('contractDialogTitle').textContent=`${purchaseState.editing?'ویرایش قرارداد':'قرارداد جدید'} · ${purchaseSupplierRows().find(s=>s.id===supplierId)?.name||r.supplier||''}`;
  purchaseEditor.selected=new Set(r.product_codes|| (r.product_code?[r.product_code]:[]));
  renderContractSelection();p$('purchaseContractDialog').showModal();p$('contractTitle').focus();
  try{
    const result=await api('/warehouse-assistant/api/purchase-contracts/selection?'+new URLSearchParams({supplier_id:supplierId}));
    if(request!==purchaseEditor.request)return;
    purchaseEditor.items=result.items;
    // Retain unavailable old members explicitly until the user removes them.
    for(const code of purchaseEditor.selected)if(!result.items.some(i=>i.product_code===code))purchaseEditor.items.push({product_code:code,product_name:'خارج از فهرست فعلی تأمین‌کننده؛ برای ذخیره از قرارداد حذف شود',tax_status:'unknown'});
    setPurchaseOptions('contractManufacturer',result.manufacturers||[],'همهٔ تولیدکنندگان');
    setPurchaseOptions('contractBrand',result.brands,'همهٔ برندها');setPurchaseOptions('contractGroup',result.groups,'همهٔ گروه‌ها');
  }catch(error){if(request===purchaseEditor.request)p$('contractError').textContent=error.message}
  finally{if(request===purchaseEditor.request){purchaseEditor.loading=false;renderContractSelection()}}
}
document.addEventListener('DOMContentLoaded',()=>{
  for(const id of ['contractStart','contractEnd','contractStatus'])p$(id).addEventListener('input',()=>{if(purchaseEditor.collection)renderContractSelection()});
  p$('contractStock').addEventListener('change',()=>{syncContractSampleStock();if(purchaseEditor.collection)renderContractSelection()});
});
